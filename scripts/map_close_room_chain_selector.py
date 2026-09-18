"""
Map each Close/Room pad's chain selector back to the pad's own "Room" macro.

The Damage Close/Room racks (see ``create_damage_close_room_racks.py``) put a
nested Instrument Rack on every pad: a Close chain and a Room chain crossfaded
by the chain selector, which the pad rack's Macro 7 "Room" drives. ``adc
drum-rack unmap`` stripped that mapping from all of them. It treated a rack's
own parameters as belonging to the enclosing rack, which is right for
``MacroControls.N`` and wrong for ``ChainSelector``: a top-level Instrument
Rack's mapped chain selector (the Chamber Strings shorts' "Close/Far", the
Winds sections' "Articulation") has no outer rack to address, so the
``KeyMidi`` on a chain selector drives the rack's *own* macro. With the mapping
gone, "Room" turned nothing and every pad was stuck on the Close mic.

This puts it back: one ``KeyMidi`` (``Channel`` 16, ``NoteOrController`` 6) in
each qualifying pad rack's ``ChainSelector``, right after its ``LomId`` - the
block Live 12.4.15 wrote when Ben remapped ``Damage Lite/Acoustic/Ethnic
Drums`` by hand (2026-09-18). ``--golden`` checks the result against that
Live-saved file, chain selector for chain selector.

A pad is changed only when it is unambiguously a Close/Room pad: a nested
Instrument Rack with exactly two chains whose selector zones are the donor's
crossfade (Close 0-126 fading out, Room 1-127 fading in), Macro 7 named "Room",
and no mapping on the chain selector yet. The pad rack must carry Macro 7 at
the value its chain selector already sits on, so mapping it changes nothing
you can hear on load; a pad where they disagree is reported, not written.

The root Drum Rack gets nothing - the Looping surface drives "Room" on each
pad by name, and a kit must carry no root mappings (see ``unmap``).

Edits are string-level on the decoded XML; ElementTree decides which chain
selectors, never writes. Output always goes to a separate tree - this script
has no in-place mode.

Usage:
    PYTHONPATH=src python3 scripts/map_close_room_chain_selector.py ROOT [ROOT ...]
        [--out DIR] [--golden LIVE_SAVED.adg --golden-source ORIGINAL.adg]

Without ``--out`` it only reports.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from ableton_device_creator.core import decode_adg, encode_adg  # noqa: E402

ROOM_MACRO = 6  # Macro 7, zero-based as NoteOrController stores it
ROOM_NAME = "Room"
CLOSE_ZONE = (0, 126, 0, 0)
ROOM_ZONE = (1, 127, 127, 127)

_CHAIN_SELECTOR_HEAD = re.compile(r"<ChainSelector>\n([ \t]*)<LomId Value=\"-?\d+\" />\n")


def key_midi_block(indent: str, macro: int = ROOM_MACRO) -> str:
    """The block exactly as Live writes it, at the chain selector's child indent."""
    lines = [
        "<KeyMidi>",
        '\t<PersistentKeyString Value="" />',
        '\t<IsNote Value="false" />',
        '\t<Channel Value="16" />',
        '\t<NoteOrController Value="%d" />' % macro,
        '\t<LowerRangeNote Value="-1" />',
        '\t<UpperRangeNote Value="-1" />',
        '\t<ControllerMapMode Value="0" />',
        "</KeyMidi>",
    ]
    return "".join(indent + line + "\n" for line in lines)


@dataclass
class PadResult:
    index: int
    name: str
    action: str  # "mapped", "already mapped", or a skip reason


@dataclass
class RackResult:
    path: str
    root: str = ""
    pads: List[PadResult] = field(default_factory=list)
    error: str = ""

    @property
    def mapped(self) -> int:
        return sum(1 for p in self.pads if p.action == "mapped")


def _val(el: Optional[ET.Element], tag: str) -> Optional[str]:
    node = el.find(tag) if el is not None else None
    return node.get("Value") if node is not None else None


def _zone(chain: ET.Element) -> Optional[Tuple[int, ...]]:
    rng = chain.find("BranchSelectorRange")
    try:
        return tuple(int(_val(rng, t)) for t in ("Min", "Max", "CrossfadeMin", "CrossfadeMax"))
    except (TypeError, ValueError):
        return None


def _classify_pad(pad: ET.Element) -> Tuple[Optional[ET.Element], str]:
    """(the pad rack's ChainSelector to map, or None, and why)."""
    racks = pad.findall("./DevicePresets/GroupDevicePreset")
    if len(racks) != 1:
        return None, "not one nested rack"
    group = racks[0]
    rack = group.find("./Device/InstrumentGroupDevice")
    if rack is None:
        return None, "nested rack is not an Instrument Rack"
    chains = group.findall("./BranchPresets/InstrumentBranchPreset")
    if sorted(filter(None, (_zone(c) for c in chains))) != [CLOSE_ZONE, ROOM_ZONE] or len(chains) != 2:
        return None, "chains are not the Close/Room crossfade"
    if _val(rack, "MacroDisplayNames.%d" % ROOM_MACRO) != ROOM_NAME:
        return None, "Macro 7 is not named Room"
    selector = rack.find("ChainSelector")
    if selector is None:
        return None, "no chain selector"
    if selector.find("KeyMidi") is not None:
        channel = _val(selector.find("KeyMidi"), "Channel")
        target = _val(selector.find("KeyMidi"), "NoteOrController")
        if (channel, target) == ("16", str(ROOM_MACRO)):
            return None, "already mapped"
        return None, "chain selector mapped elsewhere"
    if rack.find("MacroControls.%d/KeyMidi" % ROOM_MACRO) is not None:
        return None, "Room macro is itself mapped"
    macro = _val(rack, "MacroControls.%d/Manual" % ROOM_MACRO)
    manual = _val(selector, "Manual")
    lo = _val(selector, "MidiControllerRange/Min")
    hi = _val(selector, "MidiControllerRange/Max")
    try:
        driven = float(lo) + (float(hi) - float(lo)) * float(macro) / 127.0
        if round(driven) != int(float(manual)):
            return None, "Room macro (%s) would move the selector from %s" % (macro, manual)
    except (TypeError, ValueError):
        return None, "unreadable Room macro or selector value"
    return selector, "mapped"


def plan(xml: str, result: RackResult) -> Tuple[List[int], List[str]]:
    """Text offsets at which to insert a block (one per pad to map, ascending),
    and the child indent of each of those chain selectors."""
    tree = ET.fromstring(xml)
    root = tree.find("./GroupDevicePreset/Device")
    result.root = root[0].tag if root is not None and len(root) else ""
    if result.root != "DrumGroupDevice":
        return [], []

    # ElementTree picks the chain selectors; the text is addressed by document
    # order, which is the same order a left-to-right scan meets them in.
    selectors = list(tree.iter("ChainSelector"))
    heads = list(_CHAIN_SELECTOR_HEAD.finditer(xml))
    if len(heads) != len(selectors) or len(re.findall(r"<ChainSelector[\s/>]", xml)) != len(selectors):
        raise ValueError("chain selectors in the text do not line up with the tree")
    order = {id(el): i for i, el in enumerate(selectors)}

    targets = []
    pads = tree.findall("./GroupDevicePreset/BranchPresets/DrumBranchPreset")
    for i, pad in enumerate(pads):
        selector, why = _classify_pad(pad)
        result.pads.append(PadResult(index=i, name=_val(pad, "Name") or "", action=why))
        if selector is not None:
            targets.append(order[id(selector)])
    return [heads[t].end() for t in sorted(targets)], [heads[t].group(1) for t in sorted(targets)]


def apply(xml: str, offsets: List[int], indents: List[str]) -> str:
    out, cursor = [], 0
    for at, indent in zip(offsets, indents):
        out.append(xml[cursor:at])
        out.append(key_midi_block(indent))
        cursor = at
    out.append(xml[cursor:])
    return "".join(out)


def verify(original: str, result: str, offsets: List[int], indents: List[str]) -> List[str]:
    failures = []
    try:
        tree = ET.fromstring(result)
    except ET.ParseError as exc:
        return ["result does not parse: %s" % exc]
    # Cut the inserted blocks back out: what remains must be the original, byte for byte.
    shift, rebuilt, cursor = 0, [], 0
    for at, indent in zip(offsets, indents):
        block = key_midi_block(indent)
        pos = at + shift
        if result[pos:pos + len(block)] != block:
            failures.append("block missing at offset %d" % at)
            return failures
        rebuilt.append(result[cursor:pos])
        cursor = pos + len(block)
        shift += len(block)
    rebuilt.append(result[cursor:])
    if "".join(rebuilt) != original:
        failures.append("text outside the inserted blocks changed")
    added = result.count("<KeyMidi>") - original.count("<KeyMidi>")
    if added != len(offsets):
        failures.append("%d KeyMidi added, expected %d" % (added, len(offsets)))

    # Every new block must sit on a pad rack's own chain selector, addressing Room.
    def room_mapped(xml_tree: ET.Element) -> int:
        n = 0
        for pad in xml_tree.findall("./GroupDevicePreset/BranchPresets/DrumBranchPreset"):
            sel = pad.find("./DevicePresets/GroupDevicePreset/Device/InstrumentGroupDevice/ChainSelector")
            km = sel.find("KeyMidi") if sel is not None else None
            if km is not None and (_val(km, "Channel"), _val(km, "NoteOrController")) == ("16", str(ROOM_MACRO)):
                n += 1
        return n

    gained = room_mapped(tree) - room_mapped(ET.fromstring(original))
    if gained != len(offsets):
        failures.append("%d pad chain selectors newly mapped to Room, expected %d" % (gained, len(offsets)))
    root_sel = tree.find("./GroupDevicePreset/Device/DrumGroupDevice/ChainSelector")
    if root_sel is not None and root_sel.find("KeyMidi") is not None:
        failures.append("root chain selector carries a mapping")
    return failures


def chain_selector_blocks(xml: str) -> List[str]:
    return re.findall(r"<ChainSelector>.*?</ChainSelector>", xml, re.S)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("roots", nargs="+", type=Path, help="folders (or .adg files) to process")
    ap.add_argument("--out", type=Path, help="staging folder; each root is mirrored under it by name")
    ap.add_argument("--golden", type=Path, help="a Live-saved preset remapped by hand")
    ap.add_argument("--golden-source", type=Path, help="the preset the golden was made from")
    ap.add_argument("--report", type=Path, help="write a JSON report here")
    args = ap.parse_args()

    if args.golden:
        if not args.golden_source:
            ap.error("--golden needs --golden-source")
        src = decode_adg(args.golden_source)
        res = RackResult(path=str(args.golden_source))
        offsets, indents = plan(src, res)
        ours = chain_selector_blocks(apply(src, offsets, indents))
        live = chain_selector_blocks(decode_adg(args.golden))
        same = sum(a == b for a, b in zip(ours, live))
        print("golden: %d of %d chain selectors identical to Live's (%d mapped)" % (same, len(live), len(offsets)))
        if len(ours) != len(live) or same != len(live):
            print("golden MISMATCH")
            return 1

    results: List[RackResult] = []
    for root in args.roots:
        files = [root] if root.is_file() else sorted(root.rglob("*.adg"))
        base = root.parent if root.is_file() else root
        for f in files:
            if ".adc-tmp" in f.name:
                continue
            rel = f.relative_to(base)
            res = RackResult(path=str(Path(root.name) / rel) if root.is_dir() else f.name)
            results.append(res)
            try:
                xml = decode_adg(f)
                offsets, indents = plan(xml, res)
                if not offsets:
                    continue
                out_xml = apply(xml, offsets, indents)
                failures = verify(xml, out_xml, offsets, indents)
                if failures:
                    res.error = "; ".join(failures)
                    continue
                if args.out:
                    target = args.out / root.name / rel if root.is_dir() else args.out / f.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    encode_adg(out_xml, target)
                    if decode_adg(target) != out_xml:
                        res.error = "gzip round-trip mismatch"
            except Exception as exc:  # report and keep going
                res.error = "%s: %s" % (type(exc).__name__, exc)

    actions = Counter(p.action for r in results for p in r.pads)
    racks_changed = sum(1 for r in results if r.mapped and not r.error)
    print("racks: %d scanned, %d with pads mapped, %d errors" % (
        len(results), racks_changed, sum(1 for r in results if r.error)))
    for action, n in actions.most_common():
        print("  pads %-50s %d" % (action, n))
    for r in results:
        if r.error:
            print("  ERROR %s: %s" % (r.path, r.error))
        elif r.root and r.root != "DrumGroupDevice":
            print("  skipped %s: root is %s" % (r.path, r.root))
        odd = Counter(p.action for p in r.pads if p.action not in ("mapped", "already mapped"))
        if odd:
            print("  %s: %d mapped, left alone %s" % (r.path, r.mapped, dict(odd)))
    if args.report:
        args.report.write_text(json.dumps([asdict(r) for r in results], indent=1))
    return 1 if any(r.error for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
