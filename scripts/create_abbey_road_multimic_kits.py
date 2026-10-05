#!/usr/bin/env python3
"""
Multi-mic versions of the curated 50s Autumn and 50s Spring 32-pad racks.

Donor is the library's own rack, `xFull/Abbey Road/50s <Kit>.adg`: same pads,
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
one hand: Left when the same piece's Right Hand already has a pad (the racks put
Center Right Hand toms on 47/48/50, so 41/43/45 become their Left Hand pair),
Right otherwise. The pad name is changed to say which.

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
KITS = ["Autumn", "Spring"]
ALT = "Right-Left Alternating"
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

    plan = []
    for pad, (piece, art) in zip(pads, wanted):
        use, note = art, None
        if (piece, art) not in rendered and art.endswith(ALT):
            stem = art[: -len(ALT)]
            right, left = stem + "Right Hand", stem + "Left Hand"
            use = left if (piece, right) in wanted else right
            note = f"alternating not rendered -> {use}"
        if (piece, use) not in rendered:
            raise SystemExit(f"{kit}: {piece} / {use} has no multi-mic render")
        name = pad.find("Name").get("Value")
        if use != art:
            name = name.replace(art.replace("Right-Left", "Right/Left"), use).replace(art, use)
        plan.append((piece, use, name, note))
    return kit_dir, plan


def build_kit(kit: str, verbose: bool):
    donor_path = INSTRUMENTS / f"xFull/Abbey Road/50s {kit}.adg"
    donor = decode_adg(donor_path)
    kit_dir, plan = plan_kit(kit, donor)
    spans = pad_spans(donor)
    creator = MultisampleRackCreator(template=DONOR)

    pieces, cursor, built = [], 0, []
    totals = defaultdict(int)
    for (start, end), (piece, art, name, note) in zip(spans, plan):
        print(f"\n[{len(built) + 36}] {name}" + (f"   ({note})" if note else ""))
        zones, report, mics = build_zones(kit_dir, piece, art, verbose=verbose)
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
    verify(donor, result, built)
    return result, totals


def strip_edits(xml: str) -> str:
    xml = re.sub(r"<SampleParts>.*?</SampleParts>", "", xml, flags=re.S)
    xml = re.sub(r'<RoundRobin Value="(true|false)" />', "", xml)
    return re.sub(r'(<DrumBranchPreset Id="\d+">\s*<Name Value=)"[^"]*"', r"\1", xml)


def verify(donor: str, result: str, built) -> None:
    """Outside the zone maps, RoundRobin and pad names, the rack is untouched;
    every pad's zones are the planned ones and every velocity plays exactly one
    take on every mic the piece has."""
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
        mics = {re.search(r" (Close|OH|Room)-", p).group(1) for p in paths}
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

    for kit in args.kit or KITS:
        print(f"\n===== 50s {kit} =====")
        if args.plan:
            donor = decode_adg(INSTRUMENTS / f"xFull/Abbey Road/50s {kit}.adg")
            for i, (piece, art, name, note) in enumerate(plan_kit(kit, donor)[1]):
                print(f"  {36 + i}  {name}" + (f"   ({note})" if note else ""))
            continue
        result, totals = build_kit(kit, args.verbose)
        out = OUTPUT_DIR / f"50s {kit}.adg"
        out.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(result, out)
        print(f"\nwrote {out}: {totals['takes']} takes, {totals['kept']} kept, "
              f"{totals['zones']} zones (verified)")


if __name__ == "__main__":
    main()
