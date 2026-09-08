"""
Dissolve the nested rack on each Drum Rack pad, string-level.

Kits built on a donor template often carry a whole Instrument Rack on every pad
just to hold one instrument plus a couple of effects, with the rack's macros
mapped down onto them. Live's "Ungroup" on such a rack lifts the chain's devices
into the pad chain and throws the wrapper away. This module does the same thing
to every pad of a preset at once.

Live's ungroup does three things, all reproduced here:

1. replaces the pad's ``GroupDevicePreset`` with the ``AbletonDevicePreset``
   blocks of the rack's single chain, in order;
2. deletes every ``KeyMidi`` that addressed the dissolved rack's macros - those
   macros no longer exist. Mappings inside a rack *nested deeper* still address
   their own rack and are kept;
3. resets the mapping range of each unmapped parameter to the parameter's full
   range (``MidiCCOnOffThresholds`` back to 64/127, ``MidiControllerRange`` back
   to the values in ``PARAM_RANGES``).

Stored values are *not* touched. Unlike an unmap of a script-generated kit,
there is nothing to bake: a preset Live itself saved already holds the
macro-driven value in each mapped parameter's ``Manual``, and the golden pair
this module was measured against confirms Live rewrites no ``Manual`` when it
ungroups. Step 3 is cosmetic - a mapping range is inert once its ``KeyMidi`` is
gone - so a parameter whose full range is not in ``PARAM_RANGES`` keeps its
stored range and is reported rather than guessed at.

A pad is only dissolved when the wrapper adds nothing of its own: exactly one
chain, no return chains, full key and velocity range, centred pan, unmuted,
nothing soloed. Anything else is left alone with a reason, because splicing two
parallel chains into one series chain would change the sound.

Chain *level* is the exception, and the one place this departs from Live. Live
throws the chain fader away; here its gain is folded into the pad's own fader
instead, which is exact - two faders in series multiply, and both are stored as
the same linear gain. The pad is only refused when that cannot be done: the pad
has no fader, its fader is macro-mapped (Live ignores a mapped parameter's
stored value, so writing the product would silently do nothing), or the product
would leave the fader's range. Pass ``fold_volume=False`` for Live's behaviour.

All edits are performed on the XML text. The file is never re-serialised through
ElementTree (re-serialised Live 12 files parse but do not load). ElementTree is
used read-only, to verify the result.

Measured on Live 12.4.1's own ungroup of a Session Drums Club pad (2026-09-08):
before/after of one pad holding an Instrument Rack over a Sampler and an EQ
Eight, 16 mappings. The only other differences in that pair were incidental to
the resave - ``RoundRobinRandomSeed``, and an off Shaper's empty slot - and are
not reproduced.

The functions in this module perform no I/O.
"""

import re
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..macro_mapping.unmap import format_live_float

__all__ = [
    "PadPlan",
    "UngroupReport",
    "ungroup_pads",
    "plan_ungroup",
    "verify_ungroup",
    "DISSOLVABLE",
    "PARAM_RANGES",
    "BOOL_THRESHOLDS",
    "VOLUME_MIN",
    "VOLUME_MAX",
]

# A mixer fader's full range, as a linear gain: -70 dB to +6 dB. Measured across
# 1863 unmapped AudioBranchMixerDevice/Volume parameters in the library, which
# all carry exactly this pair.
VOLUME_MIN = 0.0003162277571
VOLUME_MAX = 1.99526238

# Rack classes whose pad wrapper may be dissolved. A nested Drum Rack is not one
# of them: its chains route by note, so there is no single chain to lift.
DISSOLVABLE = frozenset(
    {"InstrumentGroupDevice", "AudioEffectGroupDevice", "MidiEffectGroupDevice"}
)

# Live's threshold pair for an unmapped on/off parameter. Universal: all 1111
# unmapped booleans in the measured library file carry it, and every parameter
# that carried anything else was mapped.
BOOL_THRESHOLDS = ("64", "127")

# (device class, parameter path within the device) -> the parameter's full range,
# which is what Live writes into MidiControllerRange when the mapping goes.
# Every entry is read off Live 12.4.1's own ungroup of the golden pair; a band
# index is written ``Bands.*`` and matches any band.
PARAM_RANGES: Dict[Tuple[str, str], Tuple[str, str]] = {
    ("MultiSampler", "Pitch/TransposeKey"): ("-48", "48"),
    ("MultiSampler", "VolumeAndPan/Volume"): ("-36", "36"),
    ("MultiSampler", "VolumeAndPan/Envelope/AttackTime"): ("0.1000000015", "20000"),
    ("MultiSampler", "VolumeAndPan/Envelope/DecayTime"): ("1", "60000"),
    ("MultiSampler", "VolumeAndPan/Envelope/ReleaseTime"): ("1", "60000"),
    ("Eq8", "GlobalGain"): ("-12", "12"),
    ("Eq8", "Scale"): ("-2", "2"),
    ("Eq8", "Bands.*/ParameterA/Freq"): ("10", "22000"),
}


def _float32(x: float) -> float:
    """Round to the nearest single-precision value, the precision Live stores."""
    return struct.unpack("f", struct.pack("f", x))[0]


_TAG_RX = re.compile(r'<(/?)([A-Za-z_][\w.\-]*)((?:\s+[\w.\-:]+\s*=\s*"[^"]*")*)\s*(/?)>')
_BAND_RX = re.compile(r"^Bands\.\d+/")
_VALUE_RX = re.compile(r'(<(?:Min|Max) Value=")([^"]*)(" />)')


# --------------------------------------------------------------------------- #
# A read-only span tree over the text
# --------------------------------------------------------------------------- #


class _Node:
    """One element's span in the XML text, with its children."""

    __slots__ = ("tag", "start", "end", "inner_start", "inner_end", "children", "parent")

    def __init__(self, tag: str, start: int, inner_start: int) -> None:
        self.tag = tag
        self.start = start
        self.end = -1
        self.inner_start = inner_start
        self.inner_end = -1
        self.children: List["_Node"] = []
        self.parent: Optional["_Node"] = None

    def child(self, tag: str) -> Optional["_Node"]:
        for c in self.children:
            if c.tag == tag:
                return c
        return None

    def each(self, tag: str) -> List["_Node"]:
        return [c for c in self.children if c.tag == tag]

    def descendants(self, tag: str) -> List["_Node"]:
        out: List["_Node"] = []
        stack = list(self.children)
        while stack:
            n = stack.pop()
            if n.tag == tag:
                out.append(n)
            stack.extend(n.children)
        return out

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<%s %d:%d>" % (self.tag, self.start, self.end)


def _spans(xml: str) -> _Node:
    """Parse the text into a tree of element spans.

    Live's XML has no comments, no CDATA and no processing instruction past the
    declaration, so a tag scanner that understands quoted attribute values is
    enough - and unlike ElementTree it keeps every byte addressable.
    """
    root: Optional[_Node] = None
    stack: List[_Node] = []
    for m in _TAG_RX.finditer(xml):
        closing, tag, _attrs, self_closing = m.groups()
        if closing:
            if not stack or stack[-1].tag != tag:
                raise ValueError("unbalanced </%s> at offset %d" % (tag, m.start()))
            node = stack.pop()
            node.inner_end = m.start()
            node.end = m.end()
            continue
        node = _Node(tag, m.start(), m.end())
        if self_closing:
            node.inner_end = m.end()
            node.end = m.end()
        if stack:
            node.parent = stack[-1]
            stack[-1].children.append(node)
        elif root is None:
            root = node
        if not self_closing:
            stack.append(node)
    if stack:
        raise ValueError("unclosed <%s>" % stack[-1].tag)
    if root is None:
        raise ValueError("no elements found")
    return root


def _line_span(xml: str, start: int, end: int) -> Tuple[int, int]:
    """Widen a span to whole lines when it has its lines to itself."""
    line_start = xml.rfind("\n", 0, start) + 1
    line_end = xml.find("\n", end)
    line_end = len(xml) if line_end == -1 else line_end + 1
    if xml[line_start:start].strip() == "" and xml[end : line_end - 1].strip() == "":  # noqa: E203
        return line_start, line_end
    return start, end


def _indent_at(xml: str, pos: int) -> str:
    line_start = xml.rfind("\n", 0, pos) + 1
    return xml[line_start:pos] if xml[line_start:pos].strip() == "" else ""


def _dedent(text: str, prefix: str) -> str:
    """Drop one leading ``prefix`` from every line that starts with it."""
    if not prefix:
        return text
    return "\n".join(
        line[len(prefix) :] if line.startswith(prefix) else line  # noqa: E203
        for line in text.split("\n")
    )


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #


@dataclass
class PadPlan:
    """One pad's outcome."""

    note: str
    index: int = -1  # the pad's position among the rack's chains, its real identity
    rack_class: str = ""
    devices: List[str] = field(default_factory=list)
    key_midi_removed: int = 0
    # Mappings that die with the wrapper rather than with a lifted device: the
    # chain mixer's own parameters go when the chain does. Live discards these
    # too. The chain is only dissolved when its mixer is at unity, so nothing
    # audible is lost - but the macro that rode it is gone.
    key_midi_dropped_with_chain: int = 0
    key_midi_kept: int = 0  # mappings owned by a rack nested deeper
    ranges_reset: int = 0
    ranges_left: List[str] = field(default_factory=list)
    # The chain gain that was folded into the pad's own fader, if any, and what
    # that fader went from and to.
    chain_volume_folded: Optional[float] = None
    chain_volume_was_mapped: bool = False
    pad_volume: Optional[Tuple[str, str]] = None
    skipped: str = ""  # reason; empty when the pad was dissolved


@dataclass
class UngroupReport:
    """Outcome of one preset."""

    root_class: str = ""
    is_drum_rack: bool = False
    reason: str = ""
    pads: List[PadPlan] = field(default_factory=list)

    @property
    def ungrouped(self) -> int:
        return sum(1 for p in self.pads if not p.skipped and p.devices)

    @property
    def skipped(self) -> int:
        return sum(1 for p in self.pads if p.skipped)

    @property
    def key_midi_removed(self) -> int:
        return sum(p.key_midi_removed for p in self.pads)

    @property
    def ranges_reset(self) -> int:
        return sum(p.ranges_reset for p in self.pads)

    @property
    def ranges_left(self) -> List[str]:
        return sorted({r for p in self.pads for r in p.ranges_left})

    @property
    def changed(self) -> bool:
        return self.ungrouped > 0


# --------------------------------------------------------------------------- #
# Planning
# --------------------------------------------------------------------------- #


def _root_device(root: _Node) -> Tuple[str, Optional[_Node]]:
    """(class name, the top GroupDevicePreset) of the preset's root device."""
    top = root.child("GroupDevicePreset")
    if top is None:
        return "", None
    device = top.child("Device")
    if device is None or not device.children:
        return "", None
    return device.children[0].tag, top


def _pads(top: _Node) -> List[_Node]:
    branches = top.child("BranchPresets")
    return branches.each("DrumBranchPreset") if branches is not None else []


def _chain_volume(xml: str, branch: _Node) -> Tuple[Optional[_Node], float, bool]:
    """(the chain's Volume Manual node, its gain, whether the parameter is mapped)."""
    mixer = branch.child("MixerPreset")
    if mixer is None:
        return None, 1.0, False
    for node in mixer.descendants("Volume"):
        manual = node.child("Manual")
        if manual is None:
            return None, 1.0, False
        value = _attr(xml, manual, "Value")
        return manual, float(value) if value else 1.0, node.child("KeyMidi") is not None
    return None, 1.0, False


def _pass_through(xml: str, branch: _Node) -> str:
    """Empty when the chain adds nothing but level, else why it cannot be lifted.

    Volume is not checked here: a chain gain is preserved by folding it into the
    pad's own fader (see ``_fold_edit``), which is exact because both are the
    same linear gain. Pan, mute and a partial zone have no such composition.
    """
    solo = branch.child("IsSoloed")
    if solo is not None and _attr(xml, solo, "Value") != "false":
        return "chain is soloed"
    zone = branch.child("ZoneSettings")
    if zone is not None:
        key = zone.child("KeyRange")
        if key is not None:
            lo, hi = _attr_of(xml, key, "Min"), _attr_of(xml, key, "Max")
            if (lo, hi) != ("0", "127"):
                return "chain key range is %s-%s, not the full keyboard" % (lo, hi)
        vel = zone.child("VelocityRange")
        if vel is not None:
            lo, hi = _attr_of(xml, vel, "Min"), _attr_of(xml, vel, "Max")
            if (lo, hi) != ("1", "127"):
                return "chain velocity range is %s-%s, not the full range" % (lo, hi)
    mixer = branch.child("MixerPreset")
    if mixer is not None:
        for node in mixer.descendants("Pan"):
            manual = node.child("Manual")
            value = _attr(xml, manual, "Value") if manual is not None else None
            if value is not None and float(value) != 0.0:
                return "chain pan is %s, not 0" % value
            break
        for node in mixer.descendants("Speaker"):
            manual = node.child("Manual")
            if manual is not None and _attr(xml, manual, "Value") == "false":
                return "chain is muted"
            break
    return ""


def _fold_edit(
    xml: str, pad: _Node, branch: _Node, plan: PadPlan
) -> Tuple[str, Optional[Tuple[int, int, str]]]:
    """Fold the chain's gain into the pad's own fader. Returns (reason, edit).

    Two faders in series multiply, and both are stored as the same linear gain,
    so the product is the level exactly. Live throws the chain fader away
    instead; this keeps it, which is the whole reason the pad can be dissolved
    at all when its chain is not at unity.
    """
    _, gain, chain_mapped = _chain_volume(xml, branch)
    if gain == 1.0:
        return "", None

    pad_manual, pad_gain, pad_mapped = _chain_volume(xml, pad)
    if pad_manual is None:
        return "chain volume is %s and the pad has no fader to fold it into" % gain, None
    if pad_mapped:
        # A mapped parameter's stored value is ignored by Live, so writing the
        # product here would silently do nothing.
        return "chain volume is %s and the pad's own fader is macro-mapped" % gain, None

    product = _float32(pad_gain * gain)
    if not VOLUME_MIN <= product <= VOLUME_MAX:
        return (
            "chain volume %s times the pad's %s leaves the fader's range" % (gain, pad_gain),
            None,
        )

    plan.chain_volume_folded = gain
    plan.chain_volume_was_mapped = chain_mapped
    # The "from" value is what the file actually stored, not a reformatting of it.
    plan.pad_volume = (_attr(xml, pad_manual, "Value") or "", format_live_float(product))
    start, end = pad_manual.start, pad_manual.end
    return "", (start, end, '<Manual Value="%s" />' % format_live_float(product))


def _attr(xml: str, node: _Node, name: str) -> Optional[str]:
    m = re.search(
        r'\b%s="([^"]*)"' % re.escape(name), xml[node.start : node.inner_start]
    )  # noqa: E203
    return m.group(1) if m else None


def _attr_of(xml: str, node: _Node, child: str) -> Optional[str]:
    c = node.child(child)
    return _attr(xml, c, "Value") if c is not None else None


def _param_path(node: _Node, device: _Node) -> str:
    """Path of a parameter element relative to its device element."""
    parts: List[str] = []
    cur: Optional[_Node] = node
    while cur is not None and cur is not device:
        parts.append(cur.tag)
        cur = cur.parent
    return "/".join(reversed(parts))


def _owned_mappings(rack: _Node) -> List[_Node]:
    """KeyMidi elements that address ``rack``'s macros: those not inside a deeper rack."""
    out: List[_Node] = []
    stack = list(rack.children)
    while stack:
        n = stack.pop()
        if n.tag == "KeyMidi":
            out.append(n)
            continue
        if n.tag == "GroupDevicePreset" and n is not rack:
            continue  # a rack nested deeper owns everything under it
        stack.extend(n.children)
    return out


def _enclosing_device(node: _Node, stop: _Node) -> Optional[_Node]:
    """The ``<Device>`` payload element a parameter belongs to."""
    cur = node.parent
    device: Optional[_Node] = None
    while cur is not None and cur is not stop:
        if cur.parent is not None and cur.parent.tag == "Device":
            device = cur
        cur = cur.parent
    return device


def plan_ungroup(
    xml: str, fold_volume: bool = True
) -> Tuple[UngroupReport, List[Tuple[int, int, str]]]:
    """Classify the preset and build the (start, end, replacement) edits."""
    tree = _spans(xml)
    root_class, top = _root_device(tree)
    report = UngroupReport(root_class=root_class, is_drum_rack=root_class == "DrumGroupDevice")
    if top is None:
        report.reason = "no device preset found"
        return report, []
    if not report.is_drum_rack:
        report.reason = "root device is %s, not a Drum Rack" % (root_class or "unknown")
        return report, []

    edits: List[Tuple[int, int, str]] = []
    for index, pad in enumerate(_pads(top)):
        zone = pad.child("ZoneSettings")
        note = (_attr_of(xml, zone, "ReceivingNote") if zone is not None else None) or "?"
        presets = pad.child("DevicePresets")
        racks = presets.each("GroupDevicePreset") if presets is not None else []
        if not racks:
            report.pads.append(
                PadPlan(note=note, index=index, skipped="no nested rack on this pad")
            )
            continue
        for rack in racks:
            plan, pad_edits = _plan_pad(xml, note, index, pad, rack, fold_volume)
            report.pads.append(plan)
            edits.extend(pad_edits)
    return report, edits


def _plan_pad(
    xml: str, note: str, index: int, pad: _Node, rack: _Node, fold_volume: bool
) -> Tuple[PadPlan, List[Tuple[int, int, str]]]:
    device = rack.child("Device")
    rack_class = device.children[0].tag if device is not None and device.children else ""
    plan = PadPlan(note=note, index=index, rack_class=rack_class)

    if rack_class not in DISSOLVABLE:
        plan.skipped = "%s cannot be dissolved into a pad chain" % (rack_class or "unknown device")
        return plan, []

    branch_presets = rack.child("BranchPresets")
    branches = list(branch_presets.children) if branch_presets is not None else []
    if len(branches) != 1:
        plan.skipped = "rack has %d chains; only a single chain can be lifted" % len(branches)
        return plan, []
    returns = rack.child("ReturnBranchPresets")
    if returns is not None and returns.children:
        plan.skipped = "rack has %d return chains" % len(returns.children)
        return plan, []

    branch = branches[0]
    reason = _pass_through(xml, branch)
    if reason:
        plan.skipped = reason
        return plan, []

    if fold_volume:
        reason, fold = _fold_edit(xml, pad, branch, plan)
    else:
        _, gain, _ = _chain_volume(xml, branch)
        reason, fold = ("chain volume is %s, not 1" % gain if gain != 1.0 else ""), None
    if reason:
        plan.skipped = reason
        return plan, []

    inner = branch.child("DevicePresets")
    blocks = list(inner.children) if inner is not None else []
    if not blocks:
        plan.skipped = "rack chain holds no devices"
        return plan, []

    for b in blocks:
        d = b.child("Device")
        plan.devices.append(d.children[0].tag if d is not None and d.children else b.tag)

    # The text to lift, and the mappings inside it that die with the rack.
    body_start, body_end = _line_span(xml, blocks[0].start, blocks[-1].end)
    owned = _owned_mappings(rack)
    mappings = [m for m in owned if body_start <= m.start < body_end]
    plan.key_midi_dropped_with_chain = len(owned) - len(mappings)
    plan.key_midi_kept = len(rack.descendants("KeyMidi")) - len(owned)

    body = _reset_and_strip(xml, body_start, body_end, mappings, rack, plan)

    # Re-indent from the chain's depth to the pad's.
    old_indent = _indent_at(xml, blocks[0].start)
    new_indent = _indent_at(xml, rack.start)
    if old_indent.startswith(new_indent):
        body = _dedent(body, old_indent[len(new_indent) :])  # noqa: E203

    plan.key_midi_removed = len(mappings)
    start, end = _line_span(xml, rack.start, rack.end)
    edits = [(start, end, body)]
    if fold is not None:
        edits.append(fold)
    return plan, edits


def _reset_and_strip(
    xml: str,
    body_start: int,
    body_end: int,
    mappings: List[_Node],
    rack: _Node,
    plan: PadPlan,
) -> str:
    """Cut each mapping out of the lifted text and restore its parameter's range."""
    out: List[str] = []
    pos = body_start
    for km in sorted(mappings, key=lambda n: n.start):
        param = km.parent
        cut_start, cut_end = _line_span(xml, km.start, km.end)
        out.append(xml[pos:cut_start])
        pos = cut_end

        # The parameter's range field sits after the KeyMidi, inside the same element.
        target, full = _range_target(xml, param, rack, plan)
        if target is not None and full is not None:
            out.append(_rewrite_range(xml, pos, target, full))
            pos = target.end
            plan.ranges_reset += 1
    out.append(xml[pos:body_end])
    return "".join(out)


def _range_target(
    xml: str, param: Optional[_Node], rack: _Node, plan: PadPlan
) -> Tuple[Optional[_Node], Optional[Tuple[str, str]]]:
    """The range element to reset for a just-unmapped parameter, and its full range."""
    if param is None:
        return None, None
    thresholds = param.child("MidiCCOnOffThresholds")
    if thresholds is not None:
        return thresholds, BOOL_THRESHOLDS
    rng = param.child("MidiControllerRange")
    if rng is None:
        return None, None
    device = _enclosing_device(param, rack)
    if device is None:
        return None, None
    path = _param_path(param, device)
    key = (device.tag, path)
    if key not in PARAM_RANGES:
        key = (device.tag, _BAND_RX.sub(lambda m: "Bands.*/", path))
    full = PARAM_RANGES.get(key)
    if full is None:
        label = "%s %s" % (device.tag, path)
        if label not in plan.ranges_left:
            plan.ranges_left.append(label)
        return None, None
    return rng, full


def _rewrite_range(xml: str, pos: int, target: _Node, full: Tuple[str, str]) -> str:
    """Text from ``pos`` to the end of ``target``, with Min/Max set to ``full``."""
    head = xml[pos : target.inner_start]  # noqa: E203
    values = iter(full)
    body = _VALUE_RX.sub(
        lambda m: m.group(1) + next(values, m.group(2)) + m.group(3),
        xml[target.inner_start : target.end],
    )  # noqa: E203
    return head + body


def ungroup_pads(xml: str, fold_volume: bool = True) -> Tuple[str, UngroupReport]:
    """Dissolve every pad's nested rack. Returns the new text and a report.

    With ``fold_volume`` a chain that is not at unity has its gain folded into
    the pad's own fader, so the level survives; Live instead discards the chain
    fader, and ``fold_volume=False`` reproduces that by refusing the pad.
    """
    report, edits = plan_ungroup(xml, fold_volume)
    text = xml
    for start, end, body in sorted(edits, key=lambda e: e[0], reverse=True):
        text = text[:start] + body + text[end:]
    return text, report


# --------------------------------------------------------------------------- #
# Verification (read-only ElementTree on both texts)
# --------------------------------------------------------------------------- #

_RANGE_TAGS = ("MidiControllerRange", "MidiCCOnOffThresholds")


def _canon(e: ET.Element) -> object:
    """Canonical form of an element: tag, attributes, text and children, in order."""
    return (
        e.tag,
        tuple(sorted(e.attrib.items())),
        (e.text or "").strip(),
        tuple(_canon(c) for c in e),
    )


def _compare_unmapped(before: ET.Element, after: ET.Element, path: str, out: List[str]) -> None:
    """Assert ``after`` is ``before`` minus its mappings and their now-inert ranges.

    Walks both trees together, so a range field is only excused where the
    original actually carried a ``KeyMidi``: an unmapped parameter's range must
    still match exactly.
    """
    if before.tag != after.tag:
        out.append("%s: %s became %s" % (path, before.tag, after.tag))
        return
    if before.attrib != after.attrib:
        out.append("%s: attributes changed" % path)
    if (before.text or "").strip() != (after.text or "").strip():
        out.append("%s: text changed" % path)
    was_mapped = before.find("KeyMidi") is not None
    kids_b = [c for c in before if c.tag != "KeyMidi"]
    kids_a = list(after)
    if after.find("KeyMidi") is not None:
        out.append("%s: a mapping survived" % path)
        return
    if len(kids_b) != len(kids_a):
        out.append("%s: %d children, expected %d" % (path, len(kids_a), len(kids_b)))
        return
    for b, a in zip(kids_b, kids_a):
        if was_mapped and b.tag in _RANGE_TAGS:
            continue  # Live resets the mapping range; inert once the KeyMidi is gone
        _compare_unmapped(b, a, "%s/%s" % (path, b.tag), out)


def _pad_devices(pad: ET.Element) -> List[ET.Element]:
    """The plain devices sitting directly in a chain, racks excluded."""
    presets = pad.find("DevicePresets")
    out = []
    for p in presets if presets is not None else []:
        if p.tag != "AbletonDevicePreset":
            continue
        d = p.find("Device")
        if d is not None and len(d):
            out.append(d[0])
    return out


def _root_pads(root: ET.Element) -> List[ET.Element]:
    """The root rack's own chains - not the pads of any Drum Rack nested inside one."""
    branches = root.find("GroupDevicePreset/BranchPresets")
    return [c for c in branches if c.tag == "DrumBranchPreset"] if branches is not None else []


def _check_mixer(pb: ET.Element, pa: ET.Element, plan: PadPlan, note: str) -> List[str]:
    """The pad's mixer may move in exactly one way: its fader takes the folded gain."""
    mb, ma = pb.find("MixerPreset"), pa.find("MixerPreset")
    if (mb is None) != (ma is None):
        return ["pad %s: MixerPreset changed" % note]
    if mb is None:
        return []
    if plan.chain_volume_folded is None:
        return [] if _canon(mb) == _canon(ma) else ["pad %s: MixerPreset changed" % note]

    fader_b = mb.find(".//AudioBranchMixerDevice/Volume/Manual")
    fader_a = ma.find(".//AudioBranchMixerDevice/Volume/Manual")
    if fader_b is None or fader_a is None:
        return ["pad %s: the fader to fold into is gone" % note]

    want = format_live_float(_float32(float(fader_b.get("Value")) * plan.chain_volume_folded))
    if fader_a.get("Value") != want:
        return [
            "pad %s: fader is %s, expected %s x %s = %s"
            % (note, fader_a.get("Value"), fader_b.get("Value"), plan.chain_volume_folded, want)
        ]
    # Nothing else in the mixer may have moved: compare with the fader neutralised.
    old = fader_b.get("Value")
    fader_b.set("Value", want)
    same = _canon(mb) == _canon(ma)
    fader_b.set("Value", old)
    return [] if same else ["pad %s: MixerPreset changed beyond its fader" % note]


def verify_ungroup(original: str, result: str, report: UngroupReport) -> List[str]:
    """Check the rewritten preset against the original. Empty list means it holds."""
    failures: List[str] = []
    try:
        before = ET.fromstring(original)
        after = ET.fromstring(result)
    except ET.ParseError as e:
        return ["result does not parse: %s" % e]

    pads_b = _root_pads(before)
    pads_a = _root_pads(after)
    if len(pads_b) != len(pads_a):
        return ["pad count changed: %d -> %d" % (len(pads_b), len(pads_a))]

    def note(p: ET.Element) -> str:
        n = p.find("ZoneSettings/ReceivingNote")
        return n.get("Value") if n is not None else "?"

    plans = {p.index: p for p in report.pads}
    for i, (pb, pa) in enumerate(zip(pads_b, pads_a)):
        if note(pb) != note(pa):
            failures.append("pad %d moved from note %s to %s" % (i, note(pb), note(pa)))
            continue
        plan = plans.get(i)
        if plan is None or plan.skipped:
            if _canon(pb) != _canon(pa):
                failures.append("pad %s was not dissolved but changed" % note(pb))
            continue

        # The pad's own settings must be untouched, bar a folded chain gain.
        for tag in ("ZoneSettings", "Name", "DocumentColorIndex", "AutoColored"):
            eb, ea = pb.find(tag), pa.find(tag)
            if (eb is None) != (ea is None) or (eb is not None and _canon(eb) != _canon(ea)):
                failures.append("pad %s: %s changed" % (note(pb), tag))
        failures.extend(_check_mixer(pb, pa, plan, note(pb)))

        # The lifted devices must be the rack's chain, in order and intact.
        rack = pb.find("DevicePresets/GroupDevicePreset")
        if rack is None:
            failures.append("pad %s: no rack found in the original" % note(pb))
            continue
        chain = rack.find("BranchPresets")
        src = _pad_devices(chain[0]) if chain is not None and len(chain) else []
        dst = _pad_devices(pa)
        if [d.tag for d in dst] != [d.tag for d in src]:
            failures.append(
                "pad %s: devices are %s, expected %s"
                % (note(pb), [d.tag for d in dst], [d.tag for d in src])
            )
            continue
        for a, b in zip(src, dst):
            _compare_unmapped(a, b, "pad %s/%s" % (note(pb), a.tag), failures)
        if pa.find("DevicePresets/GroupDevicePreset") is not None:
            failures.append("pad %s: a rack is still there" % note(pb))

    # Nothing outside the pads may move.
    if _canon_without_pads(before.find("GroupDevicePreset")) != _canon_without_pads(
        after.find("GroupDevicePreset")
    ):
        failures.append("the Drum Rack's own settings changed")
    return failures


def _canon_without_pads(top: Optional[ET.Element]) -> object:
    """Canonical form of the root preset with every pad's DevicePresets blanked out."""
    if top is None:
        return None

    def walk(e: ET.Element) -> object:
        kids = []
        for c in e:
            # Both are checked per pad, in detail: the devices against the rack's
            # chain, the mixer against its folded fader.
            if e.tag == "DrumBranchPreset" and c.tag in ("DevicePresets", "MixerPreset"):
                kids.append((c.tag, "<pad>"))
                continue
            kids.append(walk(c))
        return (e.tag, tuple(sorted(e.attrib.items())), (e.text or "").strip(), tuple(kids))

    return walk(top)
