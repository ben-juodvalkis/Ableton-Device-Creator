#!/usr/bin/env python3
"""
Multi-mic versions of the 12 curated Abbey Road 32-pad racks (the kits rendered
multi-out: 50s, 60s, 70s, 80s, Modern and Vintage, not the Brushes variants).

Donor is the library's own rack, `xFull/Abbey Road/<rack>.adg`: same pads,
notes, names, colours, macros and curation. Only each pad's `SampleParts` is
swapped for the multi-mic zone map built by create_abbey_road_multimic_sampler
(Close/OH/Room on the Sample Selector, takes on thin velocity slices, layer
ranges from the measured velocity_layers.csv), and its `RoundRobin` turned off,
since the take is now chosen by velocity. Edits are string-level splices: a
Live-saved rack re-serialised through ElementTree parses but will not load.

## Right-Left Alternating pads

Kontakt's alternating note plays the Left Hand and Right Hand recordings by
turns, so the render has no alternating articulation of its own (Spring's snare
is the exception and is used as rendered). Left and Right were measured with
different layer boundaries in most pieces, so they cannot be merged onto one
velocity axis without slicing layers to a velocity or two. Instead the pad takes
one hand, whichever is not already on another pad (Right first; the racks put
Center Right Hand toms on 47/48/50, so 41/43/45 usually become their Left Hand
pair). Where both hands already have pads (Early 60s Tom 2, Open and Tight
Tom 1), it takes an unused articulation of the same drum (SPARE_PREFERENCE), and
a Choke pad - chokes were not rendered - an unused articulation of the same
cymbal. No sound appears on two pads. The pad name is changed to say which.

CompST (the 80s compressed room) gets the end of the Sample Selector; the 80s
kits and the three "lead 168" kits are described in create_abbey_road_multimic_sampler.

Usage:
    PYTHONPATH=src uv run --no-project --with numpy --with soundfile \\
        python scripts/create_abbey_road_multimic_kits.py [--plan] [--kit Autumn]
"""

import argparse
import csv
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler.multisample import MultisampleRackCreator
from create_abbey_road_aux_racks import pad_spans, set_direct_child, xml_attr
from create_abbey_road_multimic_sampler import DONOR, OUTPUT_DIR, SOURCE_ROOT, build_zones

INSTRUMENTS = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments"
)
# curated rack name (xFull/Abbey Road/<name>.adg, also the output name) -> render kit
KITS = {
    "50s Autumn": "Autumn", "50s Spring": "Spring",
    "60s Early 60s": "Early 60s", "60s Late 60s": "Late 60s",
    "70s Open": "Open", "70s Tight": "Tight",
    "80s Black": "Black", "80s Chrome": "Chrome",
    "Modern Sparkle": "Sparkle", "Modern White": "White",
    "Vintage Ebony": "Ebony", "Vintage Ivory": "Ivory",
}
# Presets that advance their close mics: every stem starts this many samples
# before the hit (measured: earliest onset 169-180 frames, vs 1-17 elsewhere).
LEAD = {"Early 60s": 168, "Open": 168, "Chrome": 168}
ALT = "Right-Left Alternating"
# Choke notes were not rendered; a pad that held one takes the first unused
# articulation of the same cymbal, in this order of preference.
CHOKE_PREFERENCE = ["Tip", "Edge", "Bell"]
# An alternating pad whose Right and Left Hand both already have pads takes an
# unused articulation of the same drum instead, in this order.
SPARE_PREFERENCE = ["Rimshot", "Rim Only"]
STEM_RE = re.compile(r"-[A-G]#?-?\d+-V\d+-\w+\.wav$")


def pad_articulation(pad: ET.Element):
    """(piece, articulation) of a curated pad, read from its first sample."""
    path = pad.find(".//SampleParts/MultiSamplePart/SampleRef/FileRef/Path").get("Value")
    piece = os.path.basename(os.path.dirname(path))
    stem = STEM_RE.sub("", os.path.basename(path))
    return piece, stem[len(piece) + 1:]


def plan_kit(kit: str, donor: str):
    kit_dir = SOURCE_ROOT / f"{kit} Kit Multi-Mic"
    rendered = {(r["drum_piece"], r["articulation"])
                for r in csv.DictReader(open(kit_dir / "velocity_layers.csv"))}
    pads = ET.fromstring(donor).findall(".//BranchPresets/DrumBranchPreset")
    wanted = [pad_articulation(p) for p in pads]

    uses = []
    for piece, art in wanted:
        use, note = art, None
        if (piece, art) not in rendered and art.endswith(ALT):
            stem = art[: -len(ALT)]
            hands = [stem + "Right Hand", stem + "Left Hand"]
            free = [h for h in hands if (piece, h) not in wanted]
            # Both hands already on their own pads: fall through to a spare.
            use = free[0] if free else None
            note = f"alternating not rendered -> {use}"
        uses.append((use, note))

    taken = {(p, u) for (p, _), (u, _) in zip(wanted, uses) if u}
    for i, ((piece, art), (use, note)) in enumerate(zip(wanted, uses)):
        if use is not None and ((piece, use) in rendered or art != "Choke"):
            continue
        prefs = CHOKE_PREFERENCE if art == "Choke" else SPARE_PREFERENCE
        spare = sorted((a for p, a in rendered if p == piece and (p, a) not in taken),
                       key=lambda a: (prefs.index(a) if a in prefs else len(prefs), a))
        if not spare:
            raise SystemExit(f"{kit}: {piece} / {art} has no unused articulation to stand in")
        taken.add((piece, spare[0]))
        why = "choke not rendered" if art == "Choke" else "alternating not rendered, both hands on pads"
        uses[i] = (spare[0], f"{why} -> {spare[0]}")

    plan = []
    for pad, (piece, art), (use, note) in zip(pads, wanted, uses):
        if (piece, use) not in rendered:
            raise SystemExit(f"{kit}: {piece} / {use} has no multi-mic render")
        name = pad.find("Name").get("Value")
        if use != art:
            name = name.replace(art.replace("Right-Left", "Right/Left"), use).replace(art, use)
        plan.append((piece, use, name, note))
    return kit_dir, plan


def build_kit(rack: str, verbose: bool):
    kit = KITS[rack]
    donor = decode_adg(INSTRUMENTS / f"xFull/Abbey Road/{rack}.adg")
    kit_dir, plan = plan_kit(kit, donor)
    lead = LEAD.get(kit, 0)
    spans = pad_spans(donor)
    creator = MultisampleRackCreator(template=DONOR)

    pieces, cursor, built = [], 0, []
    totals = defaultdict(int)
    for (start, end), (piece, art, name, note) in zip(spans, plan):
        print(f"\n[{len(built) + 36}] {name}" + (f"   ({note})" if note else ""))
        zones, report, mics = build_zones(kit_dir, piece, art, verbose=verbose, sample_start=lead)
        print(f"     {report['layers']} layers, {report['takes']} takes -> {report['kept']} "
              f"(-{len(report['dropped'])} twins), {len(zones)} zones, mics {'/'.join(mics)}")
        for layer, extra in report["merged"]:
            print(f"     layer {layer}: {extra} take(s) left out - fewer velocities than takes")
        for k in ("takes", "kept"):
            totals[k] += report[k]
        totals["zones"] += len(zones)

        pad = donor[start:end]
        parts = ET.Element("SampleParts")
        for i, zone in enumerate(zones):
            parts.append(creator._sample_part(i, zone))
        sp = re.search(r"<SampleParts>.*?</SampleParts>", pad, re.S)
        pad = pad[:sp.start()] + ET.tostring(parts, encoding="unicode") + pad[sp.end():]
        rr = list(re.finditer(r'<RoundRobin Value="true" />', pad))
        if len(rr) != 1:
            raise SystemExit(f"{name}: expected one RoundRobin=true, found {len(rr)}")
        pad = pad[:rr[0].start()] + '<RoundRobin Value="false" />' + pad[rr[0].end():]
        pad = set_direct_child(pad, "Name", xml_attr(name))
        pieces.append(donor[cursor:start] + pad)
        cursor = end
        built.append((name, zones))
    pieces.append(donor[cursor:])
    result = "".join(pieces)
    verify(donor, result, built, lead)
    return result, totals


def strip_edits(xml: str) -> str:
    xml = re.sub(r"<SampleParts>.*?</SampleParts>", "", xml, flags=re.S)
    xml = re.sub(r'<RoundRobin Value="(true|false)" />', "", xml)
    return re.sub(r'(<DrumBranchPreset Id="\d+">\s*<Name Value=)"[^"]*"', r"\1", xml)


def verify(donor: str, result: str, built, lead: int = 0) -> None:
    """Outside the zone maps, RoundRobin and pad names, the rack is untouched;
    every pad's zones are the planned ones, start at the kit's lead-in, and every
    velocity plays exactly one take on every mic the piece has."""
    if strip_edits(donor) != strip_edits(result):
        raise SystemExit("verify: rack changed outside SampleParts/RoundRobin/Name")
    pads = ET.fromstring(result).findall(".//BranchPresets/DrumBranchPreset")
    assert len(pads) == len(built) == 32
    for pad, (name, zones) in zip(pads, built):
        assert pad.find("Name").get("Value") == name
        assert pad.find(".//MultiSampleMap/RoundRobin").get("Value") == "false"
        parts = pad.findall(".//SampleParts/MultiSamplePart")
        paths = [p.find("SampleRef/FileRef/Path").get("Value") for p in parts]
        assert sorted(paths) == sorted(str(Path(z.sample).resolve()) for z in zones), name
        assert all(Path(p).is_file() for p in paths), name
        assert all(int(p.find("SampleStart").get("Value")) == lead for p in parts), name
        mics = {re.search(r" (Close|OH|Room|CompST)-", p).group(1) for p in paths}
        by_vel = defaultdict(list)
        for p in parts:
            vr = p.find("VelocityRange")
            for v in range(int(vr.find("Min").get("Value")), int(vr.find("Max").get("Value")) + 1):
                by_vel[v].append(p.find("Name").get("Value"))
        assert set(by_vel) == set(range(1, 128)), name
        for v, names in by_vel.items():
            assert len(names) == len(mics) and len({n[-4:] for n in names}) == 1, (name, v)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kit", choices=KITS, action="append")
    ap.add_argument("--plan", action="store_true", help="show the pad plan, write nothing")
    ap.add_argument("--verbose", action="store_true", help="print every layer's slices")
    args = ap.parse_args()

    for rack in args.kit or KITS:
        print(f"\n===== {rack} =====")
        if args.plan:
            donor = decode_adg(INSTRUMENTS / f"xFull/Abbey Road/{rack}.adg")
            for i, (piece, art, name, note) in enumerate(plan_kit(KITS[rack], donor)[1]):
                print(f"  {36 + i}  {name}" + (f"   ({note})" if note else ""))
            continue
        result, totals = build_kit(rack, args.verbose)
        out = OUTPUT_DIR / f"{rack}.adg"
        out.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(result, out)
        print(f"\nwrote {out}: {totals['takes']} takes, {totals['kept']} kept, "
              f"{totals['zones']} zones (verified)")


if __name__ == "__main__":
    main()
