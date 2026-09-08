"""
Remove macro mappings from Drum Rack presets, string-level.

A macro mapping in an ``.adg`` is a ``<KeyMidi>`` block inside the mapped
parameter's element (``Channel`` 16, ``NoteOrController`` = macro index).
Live's own "unmap" does three things, all reproduced here:

1. deletes the ``KeyMidi`` block;
2. writes the value the macro was driving into the parameter's ``<Manual>``
   (the stored value of a mapped parameter is otherwise ignored by Live and is
   frequently stale in script-generated kits);
3. sets every ``MacroDefaults.N`` of the rack to ``-1``.

Macro names, macro positions and everything else are left untouched.

Only the mappings that belong to the *root* rack are removed by default. A
``KeyMidi`` always addresses the macros of the innermost rack around it, so a
mapping inside a nested Instrument Rack's chains belongs to that nested rack
and is left alone (Live's unmap on the outer rack behaves the same way).
Mappings that chain a root macro to a nested rack's macro *are* root-owned and
are removed.

All edits are performed on the XML text with anchored regular expressions.
The file is never re-serialised through ElementTree (re-serialised Live 12
files parse but do not load). ElementTree is used read-only, to classify the
rack, to look up macro values and ranges, and to verify the result.

The functions in this module perform no I/O.
"""

import math
import re
import struct
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

__all__ = [
    "RackInfo",
    "BakeDecision",
    "UnmapReport",
    "classify_rack",
    "strip_key_midi",
    "reset_macro_defaults",
    "bake_plan",
    "unmap_drum_rack",
    "verify_unmap",
    "effective_value",
    "format_live_float",
    "GROUP_DEVICE_TAGS",
]

GROUP_DEVICE_TAGS = frozenset(
    {"DrumGroupDevice", "InstrumentGroupDevice", "AudioEffectGroupDevice", "MidiEffectGroupDevice"}
)

MACRO_CHANNEL = "16"
MACRO_COUNT = 16

# Curve kinds. How Live interpolates a mapped parameter between the mapping's
# Min and Max as the macro travels 0..127 (t = value / 127).
LINEAR = "linear"  # value = lo + t * (hi - lo)              (stored units, dB for dB params)
LOG = "log"  # value = lo * (hi / lo) ** t              (times, frequencies)
POW2 = "pow2"  # value = lo + t**2 * (hi - lo)
POW3 = "pow3"  # value = lo + t**3 * (hi - lo)
POW5 = "pow5"  # value = lo + t**5 * (hi - lo)
INT = "int"  # LINEAR rounded to the nearest whole number (semitones, cents)
ENUM = "enum"  # INT over an enumeration (0..N)
ONOFF = "onoff"  # switch: on when the macro value exceeds the Min threshold
FADER = "fader"  # mixer fader: stored as gain, linear in dB above the knee
GAIN_DB = "gain_db"  # stored as gain, interpolated linearly in dB

# (device class, parameter tag) -> curve kind.
#
# Verification sources, all measured on the library on 2026-09-07:
#   golden   – Live 12.4.15b1's own unmap of " 606 + 808.adg" (Attack 85 -> 0.3531 s, Volume
#              42 -> -12.19 dB, VelocityToVolume 0 -> 0, ModulationAmount 0 -> -1,
#              ModulationTarget 20 -> 1).
#   library  – kits saved by Live with the macro at a mid position, where the stored value must
#              equal the macro-driven one (Simpler/Sampler envelope times and Freq, chained
#              rack macros, Timeable, DryWet, Drive, StereoGain).
#   midpoint – the pipeline template's DrumCell FX-2 members, saved at macro 63.5, whose stored
#              values are exact rationals of the curve at t = 0.5 (e.g. PunchTime
#              0.06 + 0.94 / 8, RingModFrequency 1 + 4999 / 32, SubOscFrequency sqrt(30 * 120)).
#   rig      – Live 12.4.15b1 itself: ``str_for_value`` of a DrumCell's parameters at normalized
#              0, 0.25, 0.5, 0.75 and 1 (Live interpolates linearly in that normalized space,
#              ADR-428), e.g. Attack 2.11 ms / 44.7 ms / 946 ms, RM Freq 5.88 Hz / 157 Hz /
#              1.19 kHz, Stretch Factor 2.19 / 5.75 / 11.69.
CURVES: Dict[Tuple[str, str], str] = {
    # DrumCell
    ("DrumCell", "Voice_Transpose"): INT,  # golden (63.5 -> 0), ADR-428 (80 -> 12)
    ("DrumCell", "Voice_Detune"): LINEAR,
    ("DrumCell", "Voice_VelocityToVolume"): LINEAR,  # golden, rig
    ("DrumCell", "Voice_ModulationTarget"): ENUM,  # golden
    ("DrumCell", "Voice_ModulationSource"): ENUM,
    ("DrumCell", "Voice_ModulationAmount"): LINEAR,  # golden, rig
    ("DrumCell", "Voice_Envelope_Attack"): LOG,  # golden, rig
    ("DrumCell", "Voice_Envelope_Decay"): LOG,  # library (macro 40 -> 31.98 ms), rig
    ("DrumCell", "Voice_Envelope_Mode"): ENUM,
    ("DrumCell", "Voice_PlaybackStart"): LINEAR,  # library (macro 32 -> 0.25197), rig
    ("DrumCell", "Voice_PlaybackLength"): LINEAR,
    ("DrumCell", "Volume"): LINEAR,  # golden, rig (stored in dB)
    ("DrumCell", "Voice_Filter_On"): ONOFF,
    ("DrumCell", "Voice_Filter_Frequency"): LOG,  # rig
    ("DrumCell", "Voice_Filter_Resonance"): LINEAR,
    ("DrumCell", "Voice_Filter_Type"): ENUM,
    ("DrumCell", "Effect_On"): ONOFF,  # ADR-428 (1.0 off, 1.2 on)
    ("DrumCell", "Effect_Type"): ENUM,
    ("DrumCell", "Effect_PitchEnvelopeAmount"): LINEAR,  # rig
    ("DrumCell", "Effect_PitchEnvelopeDecay"): POW3,  # midpoint, rig
    ("DrumCell", "Effect_SubOscAmount"): LINEAR,
    ("DrumCell", "Effect_SubOscFrequency"): LOG,  # midpoint, rig
    ("DrumCell", "Effect_NoiseAmount"): LINEAR,
    ("DrumCell", "Effect_NoiseFrequency"): POW2,  # midpoint, rig
    ("DrumCell", "Effect_LoopOffset"): LINEAR,
    ("DrumCell", "Effect_LoopLength"): POW2,  # midpoint, rig
    ("DrumCell", "Effect_StretchFactor"): POW2,  # rig
    ("DrumCell", "Effect_StretchGrainSize"): POW2,  # midpoint, rig
    ("DrumCell", "Effect_PunchAmount"): LINEAR,
    ("DrumCell", "Effect_PunchTime"): POW3,  # midpoint, rig
    ("DrumCell", "Effect_EightBitResamplingRate"): LOG,  # rig
    ("DrumCell", "Effect_EightBitFilterDecay"): LOG,  # midpoint, rig
    ("DrumCell", "Effect_FmAmount"): LINEAR,
    ("DrumCell", "Effect_FmFrequency"): LOG,  # midpoint, rig
    ("DrumCell", "Effect_RingModAmount"): LINEAR,
    ("DrumCell", "Effect_RingModFrequency"): POW5,  # midpoint, rig
    # Simpler / Sampler
    ("OriginalSimpler", "AttackTime"): LOG,  # library
    ("OriginalSimpler", "DecayTime"): LOG,  # library
    ("OriginalSimpler", "ReleaseTime"): LOG,  # library
    ("OriginalSimpler", "TransposeKey"): INT,
    ("OriginalSimpler", "TransposeFine"): INT,  # library
    ("OriginalSimpler", "Amount"): INT,  # library (semitones)
    ("MultiSampler", "AttackTime"): LOG,
    ("MultiSampler", "DecayTime"): LOG,  # library
    ("MultiSampler", "ReleaseTime"): LOG,  # library
    ("MultiSampler", "TransposeKey"): INT,
    ("MultiSampler", "TransposeFine"): INT,  # library
    ("MultiSampler", "Amount"): INT,  # library
    ("MultiSampler", "Freq"): LOG,  # library
    ("MultiSampler", "FreqFixed"): LOG,  # library
    # Chain mixer
    ("AudioBranchMixerDevice", "Volume"): FADER,
    ("AudioBranchMixerDevice", "Send"): FADER,
    # A few effects seen in factory kits
    ("Delay", "DryWet"): LINEAR,  # library
    ("Echo", "DryWet"): LINEAR,  # library
    ("Hybrid", "DryWet"): LINEAR,  # library
    ("Redux2", "DryWet"): LINEAR,  # library
    ("AutoFilter", "Drive"): LINEAR,  # library
    ("StereoGain", "Gain"): GAIN_DB,  # library
    ("MxDeviceAudioEffect", "Timeable"): LINEAR,  # library
    ("MxDeviceMidiEffect", "Timeable"): LINEAR,  # library
}

# Nested rack macros chained to a root macro, and chain selectors.
for _cls in GROUP_DEVICE_TAGS:
    for _n in range(MACRO_COUNT):
        CURVES[(_cls, "MacroControls.%d" % _n)] = LINEAR  # library (64 -> 64, 95.2 -> 95.2)
    CURVES[(_cls, "ChainSelector")] = INT

# Enumerations mapped without an explicit MidiControllerRange (Live 12.1 schema)
# span the whole enumeration.
DEFAULT_ENUM_RANGES: Dict[Tuple[str, str], Tuple[int, int]] = {
    ("DrumCell", "Effect_Type"): (0, 8),
    ("DrumCell", "Voice_ModulationTarget"): (0, 5),
    ("DrumCell", "Voice_ModulationSource"): (0, 5),
    ("DrumCell", "Voice_Filter_Type"): (0, 3),
}

# Live interpolates in the parameter's normalized (knob) space. For the power-law
# parameters that space is defined by the parameter's full range, which the mapping
# needs when it covers only part of that range. (Linear and logarithmic parameters
# come out the same whichever sub-range is mapped.)
FULL_RANGES: Dict[Tuple[str, str], Tuple[float, float]] = {
    ("DrumCell", "Effect_PitchEnvelopeDecay"): (0.004999999888, 2.0),
    ("DrumCell", "Effect_NoiseFrequency"): (180.0, 15000.0),
    ("DrumCell", "Effect_LoopLength"): (0.009999999776, 0.5),
    ("DrumCell", "Effect_StretchFactor"): (1.0, 20.0),
    ("DrumCell", "Effect_StretchGrainSize"): (0.004999999888, 0.3000000119),
    ("DrumCell", "Effect_PunchTime"): (0.05999999866, 1.0),
    ("DrumCell", "Effect_RingModFrequency"): (1.0, 5000.0),
}

# Live's mixer fader: 0 dB at 85 % of the travel, +6 dB at the top, 40 dB per
# unit of travel down to -18 dB at 40 %. Below that the taper is steeper and is
# not modelled; the bottom of the fader (-70 dB, shown as -inf) is position 0.
FADER_KNEE = 0.4
FADER_BOTTOM_GAIN = 10 ** (-70 / 20.0)

# A stored value is left alone when it is already within this fraction of the
# mapping's span of the macro-driven value (float noise, not a real change).
KEEP_TOLERANCE = 1e-4

_KEY_MIDI_RX = re.compile(r"<KeyMidi>.*?</KeyMidi>", re.S)
_MANUAL_AFTER_RX = re.compile(r'(?:\n[ \t]*)?<Manual Value="([^"]*)" />')
_MACRO_DEFAULT_RX = re.compile(r'^([ \t]*)<MacroDefaults\.(\d+) Value="([^"]*)" />', re.M)


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #


@dataclass
class RackInfo:
    """What ``classify_rack`` learns about a preset without modifying it."""

    root_class: str
    key_midi_count: int
    nested_drum_racks: int
    macro_names: List[str]
    has_macro_control_index: bool
    key_midi_root: int = 0
    key_midi_nested: int = 0
    nested_group_devices: Dict[str, int] = field(default_factory=dict)
    non_macro_key_midi: int = 0
    macro_values: List[float] = field(default_factory=list)

    @property
    def is_drum_rack(self) -> bool:
        return self.root_class == "DrumGroupDevice"

    @property
    def is_instrument_rack_with_drum_rack(self) -> bool:
        return self.root_class == "InstrumentGroupDevice" and self.nested_drum_racks > 0


@dataclass
class BakeDecision:
    """What happens to one mapped parameter's ``Manual`` when its mapping goes."""

    index: int  # KeyMidi block index in document order
    root_owned: bool
    device_class: str
    param: str
    macro_index: int
    macro_value: float
    stored: str
    new_value: Optional[str]  # None: keep the stored value
    reason: str  # "baked" | "consistent" | "endpoint" | "unknown-curve" | "unknown-range"
    kind: Optional[str] = None


@dataclass
class UnmapReport:
    """Outcome of ``unmap_drum_rack``."""

    removed: int
    removed_nested: int
    baked: int
    kept: int
    unknown: int
    macro_defaults_changed: int
    decisions: List[BakeDecision]

    @property
    def unknown_params(self) -> List[str]:
        return sorted(
            {
                "%s/%s@%g" % (d.device_class, d.param, d.macro_value)
                for d in self.decisions
                if d.reason.startswith("unknown")
            }
        )

    def decisions_by_index(self) -> List[Optional[BakeDecision]]:
        """Decisions indexed by KeyMidi document position (None where not in scope)."""
        size = max((d.index for d in self.decisions), default=-1) + 1
        out: List[Optional[BakeDecision]] = [None] * size
        for d in self.decisions:
            out[d.index] = d
        return out


# --------------------------------------------------------------------------- #
# Read-only analysis (ElementTree)
# --------------------------------------------------------------------------- #


def _root_device(tree: ET.Element) -> Optional[ET.Element]:
    """The preset's top device: first child of ``GroupDevicePreset/Device``, else of the root."""
    device = tree.find("GroupDevicePreset/Device")
    if device is not None and len(device):
        return device[0]
    for child in tree:
        if child.tag not in ("GroupDevicePreset",):
            return child
    return None


def _macro_values(device: Optional[ET.Element]) -> List[float]:
    values: List[float] = []
    if device is None:
        return values
    for n in range(MACRO_COUNT):
        manual = device.find("MacroControls.%d/Manual" % n)
        if manual is None:
            break
        try:
            values.append(float(manual.get("Value", "0")))
        except ValueError:
            values.append(0.0)
    return values


def _macro_names(device: Optional[ET.Element]) -> List[str]:
    names: List[str] = []
    if device is None:
        return names
    for n in range(MACRO_COUNT):
        el = device.find("MacroDisplayNames.%d" % n)
        if el is None:
            break
        names.append(el.get("Value", ""))
    return names


@dataclass
class _Mapping:
    """One KeyMidi block, in document order, with the context needed to bake it."""

    element: ET.Element  # the KeyMidi element
    param: ET.Element  # its parent (the mapped parameter)
    device_class: str
    scope_depth: int  # 0 = owned by the root rack
    macro_values: List[float]  # macros of the owning rack


def _iter_mappings(tree: ET.Element) -> List[_Mapping]:
    """Every KeyMidi in document order with its owning rack.

    Ownership follows the preset structure: a ``GroupDevicePreset`` owns everything
    inside it except its own ``Device`` subtree (the rack's own parameters, which
    belong to the enclosing rack).
    """
    out: List[_Mapping] = []

    def walk(el: ET.Element, device_class: str, frames: List[List[float]]) -> None:
        if el.tag == "GroupDevicePreset":
            device = el.find("Device")
            rack = device[0] if device is not None and len(device) else None
            frame = _macro_values(rack)
            for child in el:
                if child.tag == "Device":
                    walk(child, device_class, frames)
                else:
                    walk(child, device_class, frames + [frame])
            return
        for child in el:
            if child.tag == "KeyMidi":
                out.append(
                    _Mapping(
                        element=child,
                        param=el,
                        device_class=device_class,
                        scope_depth=max(0, len(frames) - 1),
                        macro_values=frames[-1] if frames else [],
                    )
                )
                continue
            cls = child.tag if el.tag == "Device" else device_class
            walk(child, cls, frames)

    walk(tree, "", [])
    return out


def classify_rack(xml: str) -> RackInfo:
    """Describe a preset: root device class, mapping counts, nested racks, macro names."""
    tree = ET.fromstring(xml)
    root_device = _root_device(tree)
    root_class = root_device.tag if root_device is not None else ""
    mappings = _iter_mappings(tree)

    nested: Counter = Counter()
    for device in tree.iter("Device"):
        for child in device:
            if child.tag in GROUP_DEVICE_TAGS and child is not root_device:
                nested[child.tag] += 1

    has_mci = any(el.get("Value", "-1") != "-1" for el in tree.iter("MacroControlIndex"))
    non_macro = 0
    for m in mappings:
        channel = m.element.find("Channel")
        if channel is None or channel.get("Value") != MACRO_CHANNEL:
            non_macro += 1

    return RackInfo(
        root_class=root_class,
        key_midi_count=len(mappings),
        nested_drum_racks=nested.get("DrumGroupDevice", 0),
        macro_names=_macro_names(root_device),
        has_macro_control_index=has_mci,
        key_midi_root=sum(1 for m in mappings if m.scope_depth == 0),
        key_midi_nested=sum(1 for m in mappings if m.scope_depth > 0),
        nested_group_devices=dict(nested),
        non_macro_key_midi=non_macro,
        macro_values=_macro_values(root_device),
    )


# --------------------------------------------------------------------------- #
# Curves
# --------------------------------------------------------------------------- #


def _float32(x: float) -> float:
    """Round to the nearest single-precision value, the precision Live stores."""
    return struct.unpack("f", struct.pack("f", x))[0]


def format_live_float(x: float) -> str:
    """Format a float the way Live writes it (float32, 9 significant digits, 10 below 1)."""
    x = _float32(x)
    if x == 0:
        return "0"
    text = "%.10g" % x if abs(x) < 1 else "%.9g" % x
    if "e" not in text and "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _fader_pos(gain: float) -> Optional[float]:
    if gain <= FADER_BOTTOM_GAIN * 1.0001:
        return 0.0
    db = 20 * math.log10(gain)
    pos = (db + 34.0) / 40.0
    return pos if pos >= FADER_KNEE else None


def _fader_gain(pos: float) -> Optional[float]:
    if pos <= 0:
        return FADER_BOTTOM_GAIN
    if pos < FADER_KNEE:
        return None
    return 10 ** ((40.0 * pos - 34.0) / 20.0)


def effective_value(
    kind: str,
    t: float,
    lo: float,
    hi: float,
    full: Optional[Tuple[float, float]] = None,
) -> Optional[float]:
    """The value a macro at travel ``t`` (0..1) drives a parameter mapped over ``lo..hi``.

    ``full`` is the parameter's whole range, needed by the power-law kinds when the
    mapping covers only part of it. Returns None when the curve is not known here.
    """
    if kind == LINEAR:
        return lo + t * (hi - lo)
    if kind in (INT, ENUM):
        return float(math.floor(lo + t * (hi - lo) + 0.5))
    if kind == LOG:
        if lo <= 0 or hi <= 0:
            return None
        return lo * (hi / lo) ** t
    if kind in (POW2, POW3, POW5):
        power = {POW2: 2.0, POW3: 3.0, POW5: 5.0}[kind]
        pmin, pmax = full if full is not None else (lo, hi)
        span = pmax - pmin
        if span == 0:
            return None
        # normalized knob position of each end of the mapping, then a linear
        # sweep between them in that space
        try:
            n_lo = ((lo - pmin) / span) ** (1.0 / power)
            n_hi = ((hi - pmin) / span) ** (1.0 / power)
        except (ValueError, ZeroDivisionError):
            return None
        if isinstance(n_lo, complex) or isinstance(n_hi, complex):
            return None
        n = n_lo + t * (n_hi - n_lo)
        return pmin + (n**power) * span
    if kind == GAIN_DB:
        if lo <= 0 or hi <= 0:
            return None
        db = 20 * math.log10(lo) + t * (20 * math.log10(hi) - 20 * math.log10(lo))
        return 10 ** (db / 20.0)
    if kind == FADER:
        p_lo, p_hi = _fader_pos(lo), _fader_pos(hi)
        if p_lo is None or p_hi is None:
            return None
        return _fader_gain(p_lo + t * (p_hi - p_lo))
    return None


def _decide(mapping: _Mapping, index: int) -> BakeDecision:
    """Work out what the parameter's Manual must become once its mapping is removed."""
    param = mapping.param
    manual_el = param.find("Manual")
    stored = manual_el.get("Value", "") if manual_el is not None else ""
    noc = mapping.element.find("NoteOrController")
    macro_index = int(noc.get("Value", "-1")) if noc is not None else -1
    macro_value = (
        mapping.macro_values[macro_index]
        if 0 <= macro_index < len(mapping.macro_values)
        else float("nan")
    )
    base = dict(
        index=index,
        root_owned=mapping.scope_depth == 0,
        device_class=mapping.device_class,
        param=param.tag,
        macro_index=macro_index,
        macro_value=macro_value,
        stored=stored,
    )
    key = (mapping.device_class, param.tag)
    kind = CURVES.get(key)
    if manual_el is None or math.isnan(macro_value):
        return BakeDecision(new_value=None, reason="unknown-range", kind=kind, **base)
    t = max(0.0, min(1.0, macro_value / 127.0))

    # Switches
    thresholds = param.find("MidiCCOnOffThresholds")
    if thresholds is not None or stored in ("true", "false"):
        if thresholds is None:
            return BakeDecision(new_value=None, reason="unknown-range", kind=ONOFF, **base)
        on_above = float(thresholds.find("Min").get("Value"))
        new = "true" if macro_value > on_above else "false"
        if new == stored:
            return BakeDecision(new_value=None, reason="consistent", kind=ONOFF, **base)
        return BakeDecision(new_value=new, reason="baked", kind=ONOFF, **base)

    # Range
    rng = param.find("MidiControllerRange")
    lo = hi = None
    if rng is not None and rng.find("Min") is not None:
        lo, hi = float(rng.find("Min").get("Value")), float(rng.find("Max").get("Value"))
    elif key in DEFAULT_ENUM_RANGES:
        lo, hi = DEFAULT_ENUM_RANGES[key]
    if lo is None:
        return BakeDecision(new_value=None, reason="unknown-range", kind=kind, **base)

    integral = kind in (INT, ENUM) or (kind is None and _looks_integral(stored, lo, hi))

    # The endpoints hold for every monotonic curve, known or not.
    if t == 0.0:
        value: Optional[float] = float(lo)
        reason = "endpoint"
    elif t == 1.0:
        value = float(hi)
        reason = "endpoint"
    elif kind is None:
        return BakeDecision(new_value=None, reason="unknown-curve", kind=None, **base)
    else:
        value = effective_value(kind, t, lo, hi, FULL_RANGES.get(key))
        reason = "baked"
        if value is None:
            return BakeDecision(new_value=None, reason="unknown-curve", kind=kind, **base)

    try:
        stored_f = float(stored)
    except ValueError:
        stored_f = float("nan")
    span = abs(hi - lo) or max(abs(lo), 1.0)
    if not math.isnan(stored_f) and abs(stored_f - value) <= KEEP_TOLERANCE * span:
        return BakeDecision(new_value=None, reason="consistent", kind=kind, **base)

    text = str(int(round(value))) if integral else format_live_float(value)
    if text == stored:
        return BakeDecision(new_value=None, reason="consistent", kind=kind, **base)
    return BakeDecision(new_value=text, reason=reason, kind=kind, **base)


def _looks_integral(stored: str, lo: float, hi: float) -> bool:
    return (
        re.fullmatch(r"-?\d+", stored or "") is not None
        and float(lo).is_integer()
        and float(hi).is_integer()
    )


def bake_plan(xml: str) -> List[BakeDecision]:
    """One decision per KeyMidi block in document order (read-only)."""
    tree = ET.fromstring(xml)
    return [_decide(m, i) for i, m in enumerate(_iter_mappings(tree))]


# --------------------------------------------------------------------------- #
# String-level edits
# --------------------------------------------------------------------------- #


def _block_span(xml: str, start: int, end: int) -> Tuple[int, int]:
    """Widen a block's span to whole lines when the block has a line to itself."""
    line_start = xml.rfind("\n", 0, start) + 1
    line_end = xml.find("\n", end)
    line_end = len(xml) if line_end == -1 else line_end + 1
    if xml[line_start:start].strip() == "" and xml[end : line_end - 1].strip() == "":
        return line_start, line_end
    return start, end


def _rewrite(xml: str, remove: List[bool], new_manual: List[Optional[str]]) -> Tuple[str, int]:
    """Drop the selected KeyMidi blocks and rewrite the Manual that follows each of them."""
    blocks = list(_KEY_MIDI_RX.finditer(xml))
    if len(blocks) != len(remove):
        raise ValueError(
            "KeyMidi count mismatch: %d in text, %d in tree" % (len(blocks), len(remove))
        )
    out: List[str] = []
    pos = 0
    removed = 0
    for i, m in enumerate(blocks):
        if not remove[i]:
            continue
        start, end = _block_span(xml, m.start(), m.end())
        out.append(xml[pos:start])
        removed += 1
        pos = end
        if new_manual[i] is not None:
            after = _MANUAL_AFTER_RX.match(xml, m.end())
            if after is None:
                raise ValueError("KeyMidi block %d is not followed by its Manual" % i)
            head = xml[m.end() : after.start(1)]
            tail = xml[after.end(1) : after.end()]
            # ``head`` starts right after </KeyMidi>; when the block sat on its own
            # lines that newline has already been consumed with the block.
            if start != m.start():
                head = head.lstrip("\n")
            out.append(head + new_manual[i] + tail)
            pos = after.end()
    out.append(xml[pos:])
    return "".join(out), removed


def strip_key_midi(xml: str, include_nested: bool = False) -> Tuple[str, int]:
    """Remove KeyMidi blocks owned by the root rack (all of them with ``include_nested``).

    Returns the new text and the number of blocks removed. Stored values are not
    touched; see ``unmap_drum_rack`` for the full unmap.
    """
    tree = ET.fromstring(xml)
    mappings = _iter_mappings(tree)
    remove = [include_nested or m.scope_depth == 0 for m in mappings]
    return _rewrite(xml, remove, [None] * len(mappings))


def _root_device_span(xml: str) -> Optional[Tuple[int, int, str]]:
    """(start, end, child_indent) of the root device element in the text."""
    m = re.search(r"^([ \t]*)<Device>[ \t]*\n([ \t]*)<(\w+)", xml, re.M)
    if m is None:
        return None
    indent, tag = m.group(2), m.group(3)
    close = re.compile(r"^%s</%s>" % (re.escape(indent), re.escape(tag)), re.M)
    end = close.search(xml, m.end())
    if end is None:
        return None
    # The rack's own children are indented like the line after its opening tag.
    child = re.match(r"[^\n]*\n([ \t]*)", xml[m.start(2) :])  # noqa: E203
    child_indent = child.group(1) if child else indent + "\t"
    return m.start(2), end.end(), child_indent


def reset_macro_defaults(xml: str) -> Tuple[str, int]:
    """Set the root rack's ``MacroDefaults.0..15`` to ``-1`` (nested racks untouched)."""
    span = _root_device_span(xml)
    if span is None:
        return xml, 0
    start, end, child_indent = span
    changed = 0

    def sub(m: "re.Match[str]") -> str:
        nonlocal changed
        if m.group(1) != child_indent or int(m.group(2)) >= MACRO_COUNT:
            return m.group(0)
        if m.group(3) == "-1":
            return m.group(0)
        changed += 1
        return '%s<MacroDefaults.%s Value="-1" />' % (m.group(1), m.group(2))

    body = _MACRO_DEFAULT_RX.sub(sub, xml[start:end])
    return xml[:start] + body + xml[end:], changed


def unmap_drum_rack(
    xml: str, include_nested: bool = False, bake: bool = True
) -> Tuple[str, UnmapReport]:
    """Full unmap of a Drum Rack preset: strip, bake, reset macro defaults."""
    decisions = bake_plan(xml)
    remove = [include_nested or d.root_owned for d in decisions]
    new_manual = [d.new_value if (bake and remove[i]) else None for i, d in enumerate(decisions)]
    text, removed = _rewrite(xml, remove, new_manual)
    text, defaults_changed = reset_macro_defaults(text)
    applied = [d for i, d in enumerate(decisions) if remove[i]]
    report = UnmapReport(
        removed=removed,
        removed_nested=sum(1 for d in applied if not d.root_owned),
        baked=sum(1 for d in applied if bake and d.new_value is not None),
        kept=sum(1 for d in applied if not (bake and d.new_value is not None)),
        unknown=sum(1 for d in applied if d.reason.startswith("unknown")),
        macro_defaults_changed=defaults_changed,
        decisions=applied,
    )
    return text, report


# --------------------------------------------------------------------------- #
# Verification (read-only ElementTree on both texts)
# --------------------------------------------------------------------------- #

COUNTED_TAGS = ("DrumBranchPreset", "DrumCell", "OriginalSimpler", "MultiSampler")


def _paths(root: ET.Element, skip: Optional[set] = None) -> Counter:
    """Multiset of element paths; ``skip`` holds KeyMidi elements to leave out."""
    counter: Counter = Counter()

    def walk(el: ET.Element, prefix: str) -> None:
        if skip is not None and el in skip:
            return
        path = prefix + "/" + el.tag
        counter[path] += 1
        for child in el:
            walk(child, path)

    walk(root, "")
    return counter


def _iter_pairs(
    a: ET.Element, b: ET.Element, skip_a: set, path: str
) -> Iterator[Tuple[str, ET.Element, ET.Element]]:
    """Walk two trees in step, skipping the removed subtrees of the first."""
    yield path, a, b
    kids_a = [c for c in a if c not in skip_a]
    kids_b = list(b)
    if len(kids_a) != len(kids_b):
        raise ValueError(
            "child count differs under %s: %d vs %d" % (path, len(kids_a), len(kids_b))
        )
    for ca, cb in zip(kids_a, kids_b):
        for item in _iter_pairs(ca, cb, skip_a, path + "/" + ca.tag):
            yield item


def verify_unmap(
    original: str, result: str, report: UnmapReport, include_nested: bool = False
) -> List[str]:
    """Every way the result may differ from the original, other than the unmap itself.

    Returns a list of failure descriptions; empty means the result is exactly the
    original minus the removed KeyMidi subtrees, plus the planned Manual bakes and
    the root MacroDefaults reset.
    """
    failures: List[str] = []
    try:
        tree_a = ET.fromstring(original)
        tree_b = ET.fromstring(result)
    except ET.ParseError as e:
        return ["result is not well-formed XML: %s" % e]

    mappings_a = _iter_mappings(tree_a)
    removed_set = {m.element for m in mappings_a if include_nested or m.scope_depth == 0}
    mappings_b = _iter_mappings(tree_b)
    root_left = sum(1 for m in mappings_b if m.scope_depth == 0)
    nested_left = sum(1 for m in mappings_b if m.scope_depth > 0)
    nested_before = sum(1 for m in mappings_a if m.scope_depth > 0)
    if root_left:
        failures.append("%d root-owned KeyMidi blocks remain" % root_left)
    if include_nested and nested_left:
        failures.append("%d nested KeyMidi blocks remain" % nested_left)
    if not include_nested and nested_left != nested_before:
        failures.append("nested KeyMidi changed: %d -> %d" % (nested_before, nested_left))
    if len(removed_set) != report.removed:
        failures.append(
            "removed count %d does not match the %d blocks in scope"
            % (report.removed, len(removed_set))
        )

    root_a, root_b = _root_device(tree_a), _root_device(tree_b)
    if root_a is None or root_b is None or root_a.tag != root_b.tag:
        failures.append("root device class changed")
        return failures
    if _macro_names(root_a) != _macro_names(root_b):
        failures.append("MacroDisplayNames changed")
    for n in range(MACRO_COUNT):
        el = root_b.find("MacroDefaults.%d" % n)
        if el is not None and el.get("Value") != "-1":
            failures.append("MacroDefaults.%d is %s, not -1" % (n, el.get("Value")))

    for tag in COUNTED_TAGS:
        ca, cb = len(tree_a.findall(".//" + tag)), len(tree_b.findall(".//" + tag))
        if ca != cb:
            failures.append("%s count changed: %d -> %d" % (tag, ca, cb))

    expected_paths = _paths(tree_a, skip=removed_set)
    if expected_paths != _paths(tree_b):
        failures.append("element-path multiset differs from original minus KeyMidi")
        return failures

    baked_expected = {
        m.param: d.new_value
        for m, d in zip(mappings_a, report.decisions_by_index())
        if d is not None and d.new_value is not None
    }
    parent_of = {child: parent for parent in tree_a.iter() for child in parent}
    seen_bakes = 0
    try:
        for path, ea, eb in _iter_pairs(tree_a, tree_b, removed_set, ""):
            if ea.tag != eb.tag:
                failures.append("tag differs at %s: %s vs %s" % (path, ea.tag, eb.tag))
                break
            if ea.attrib == eb.attrib and (ea.text or "").strip() == (eb.text or "").strip():
                continue
            if ea.tag == "Manual" and ea.attrib.keys() == eb.attrib.keys() == {"Value"}:
                parent_expect = baked_expected.get(parent_of.get(ea))
                if parent_expect is not None and eb.get("Value") == parent_expect:
                    seen_bakes += 1
                    continue
            if (
                ea.tag.startswith("MacroDefaults.")
                and parent_of.get(ea) is root_a
                and eb.get("Value") == "-1"
            ):
                continue
            failures.append(
                "unexpected change at %s: %s -> %s" % (path, dict(ea.attrib), dict(eb.attrib))
            )
            if len(failures) > 20:
                break
    except ValueError as e:
        failures.append(str(e))
    if seen_bakes != report.baked:
        failures.append("baked %d Manual values, expected %d" % (seen_bakes, report.baked))
    return failures
