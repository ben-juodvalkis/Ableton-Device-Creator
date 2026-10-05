#!/usr/bin/env python3
"""
Abbey Road accessory racks, rebuilt from the multi-mic renders only: claps,
snaps, spoons, stick hits, snare rims, woodblocks, choppers and muted cowbells
from the 15 multi-mic kits, in full, Lite (8 layers x 3 takes) and UltraLite
(4 x 2) versions. Supersedes create_abbey_road_aux_racks.py (stereo renders).

Every pad is the multi-mic pad of create_abbey_road_multimic_kits: one Sampler,
round robin off, each take on a thin velocity slice inside its measured layer,
every mic of the take on that slice, crossfaded on the Sample Selector. Kits
whose presets advance the close mics start at frame 168 (LEAD).

## Racks (every one fills all 32 pads - Ben's controller has 32)

The 90 sounds in scope, kits in library order within each type:

    Claps            28 claps (solo + multi side by side, 14 kits), Ivory's
                     finger snaps and spoons, Autumn's kick shell
    Sticks & Rims    15 stick hits, 15 snare rims, 2 woodblocks
    Bells & Blocks   14 muted cowbells, 6 choppers, all 8 woodblocks, and the
                     snap / spoons / kick shell again (re-used to fill 32)

and two combos, one kit per row of four pads (clap solo, clap multi, stick,
snare rim; Ivory has snaps and spoons instead of claps). Combo 2's Studio
Drummer rows are back now Garage/Stadium are rendered from their own mapping.
Open cowbells stay out. Not captured anywhere: Autumn's woodblock (hidden
behind the triangle on note 26) and everything from the Brushes kits.

The donor is the curated stereo `xFull/Abbey Road Old Full/Session.adg`, 32
bare-Sampler pads identical apart from samples/name/note/colour (checked).
Only each pad's `SampleParts`, `Name`, colour and `RoundRobin` (off) are
spliced, string-level; the verifier checks nothing else moved.

Usage:
    PYTHONPATH=src uv run --no-project --with numpy --with soundfile \\
        python scripts/create_abbey_road_aux_multimic_racks.py [--plan] [--size full|lite|ultralite]
"""

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler.multisample import MultisampleRackCreator
from create_abbey_road_aux_racks import COLORS, art_key, normalised, pad_label, pad_spans, \
    set_direct_child, xml_attr
from create_abbey_road_multimic_kits import LEAD
from create_abbey_road_multimic_sampler import DONOR as ZONE_DONOR, SOURCE_ROOT, build_zones

INSTRUMENTS = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/Looping Presets/Instruments"
)
DONOR = INSTRUMENTS / "xFull/Abbey Road Old Full/Session.adg"
# size -> (max layers, max takes, output folder)
SIZES = {
    "full": (None, None, INSTRUMENTS / "xFull/Abbey Road Aux Multi-Mic"),
    "lite": (8, 3, INSTRUMENTS / "xFull/Abbey Road Aux Multi-Mic Lite"),
    "ultralite": (4, 2, INSTRUMENTS / "Sidebar/Perc/Claps and Snaps"),
}

# Library order: (render kit, rack-name prefix used across the library)
KITS = [
    ("Autumn", "50s Autumn"), ("Spring", "50s Spring"),
    ("Early 60s", "60s Early 60s"), ("Late 60s", "60s Late 60s"),
    ("Open", "70s Open"), ("Tight", "70s Tight"),
    ("Black", "80s Black"), ("Chrome", "80s Chrome"),
    ("Sparkle", "Modern Sparkle"), ("White", "Modern White"),
    ("Garage", "Garage"), ("Session", "Session"), ("Stadium", "Stadium"),
    ("Ebony", "Vintage Ebony"), ("Ivory", "Vintage Ivory"),
]

NO_OPEN = r"^(?!.*open)"  # open cowbells are left out
CLAPS = (r"clap", r"^(solo|multi)$", "clap")
SNAPS = (r"^finger$", r"snaps", "click")
SPOONS = (r"^spoons$", r".", "click")
SHELL = (r"^kick shell$", r".", "kick")
STICKS = (r"stick", r".", "click")
RIMS = (r"^snare", r"^rim only$", "snare")
WOODBLOCKS = (r"wood ?block", r".", "block")
CHOPPERS = (r"chopper", r".", "block")
COWBELLS = (r"cowbell", NO_OPEN, "bell")

# Each rule runs across all kits before the next, so a type sits together.
# A (rule, n) pair takes only the first n matches.
RACKS = {
    "Claps": [CLAPS, SNAPS, SPOONS, SHELL],
    "Sticks & Rims": [STICKS, RIMS, (WOODBLOCKS, 2)],
    "Bells & Blocks": [COWBELLS, CHOPPERS, WOODBLOCKS, SNAPS, SPOONS, SHELL],
}
POOL = [CLAPS, SNAPS, SPOONS, SHELL, STICKS, RIMS, WOODBLOCKS, CHOPPERS, COWBELLS]

COMBO_ROW = [(r"clap", r"^solo$", "clap"), (r"clap", r"^multi$", "clap"), STICKS, RIMS]
COMBO_ROWS = {
    # Ivory has no claps; its hand sounds are finger snaps and spoons.
    "Vintage Ivory": [SNAPS, (r"^spoons$", r"closed", "click"), STICKS, RIMS],
}
COMBOS = {
    "Combo 1 (50s-80s)": [
        "50s Autumn", "50s Spring", "60s Early 60s", "60s Late 60s",
        "70s Open", "70s Tight", "80s Black", "80s Chrome",
    ],
    "Combo 2 (Modern Studio Vintage)": [
        "Modern Sparkle", "Modern White", "Garage", "Session", "Stadium",
        "Vintage Ebony", "Vintage Ivory",
        # Top row, so no pad is empty: the vintage kits' leftover percussion.
        [("Vintage Ebony", r"cowbell", r"^muted$", "bell"),
         ("50s Spring", r"cowbell", r".", "bell"),
         ("Vintage Ivory", r"wood ?block", r".", "block"),
         ("Vintage Ivory", r"^spoons$", r"open", "click")],
    ],
}


def catalog():
    """[(rack prefix, render kit, [(piece, articulation)])] from the measured
    layer tables - only what was rendered."""
    out = []
    for kit, name in KITS:
        rows = csv.DictReader(open(SOURCE_ROOT / f"{kit} Kit Multi-Mic" / "velocity_layers.csv"))
        arts = sorted({(r["drum_piece"], r["articulation"]) for r in rows},
                      key=lambda pa: (pa[0], art_key(pa[1])))
        out.append((name, kit, arts))
    return out


def plan():
    """rack -> [(pad name, colour, render kit, piece, articulation)]"""
    cat = catalog()

    def matches(rule):
        inst_re, art_re, color = rule
        return [(f"{name} - {pad_label(p, a)}", COLORS[color], kit, p, a)
                for name, kit, arts in cat for p, a in arts
                if re.search(inst_re, p, re.I) and re.search(art_re, a, re.I)]

    racks = {}
    for rack, rules in RACKS.items():
        pads = []
        for rule in rules:
            rule, n = rule if isinstance(rule[1], int) else (rule, None)
            pads += matches(rule)[:n]
        racks[rack] = pads

    by_name = {name: (kit, arts) for name, kit, arts in cat}
    for rack, kits in COMBOS.items():
        rows = []
        for row in kits:
            rows += ([(row,) + r for r in COMBO_ROWS.get(row, COMBO_ROW)]
                     if isinstance(row, str) else row)
        pads = []
        for name, inst_re, art_re, color in rows:
            kit, arts = by_name[name]
            hits = [(p, a) for p, a in arts if re.search(inst_re, p, re.I) and re.search(art_re, a, re.I)]
            if len(hits) != 1:
                raise SystemExit(f"{rack}: {name} has {len(hits)} matches for {inst_re} / {art_re}")
            p, a = hits[0]
            pads.append((f"{name} - {pad_label(p, a)}", COLORS[color], kit, p, a))
        racks[rack] = pads

    for rack, pads in racks.items():
        if len(pads) != 32:
            raise SystemExit(f"{rack}: {len(pads)} pads - every rack fills all 32")
        names = [p[0] for p in pads]
        if len(set(names)) != 32:
            raise SystemExit(f"{rack}: a sound sits on two pads")
    placed = {p[0] for pads in racks.values() for p in pads}
    pool = [p for rule in POOL for p in matches(rule)]
    missing = [p[0] for p in pool if p[0] not in placed]
    if missing:
        raise SystemExit(f"sounds on no rack: {missing}")
    return racks, len(pool)


def unedited(xml: str):
    """The rack with every spliced field taken out: the text between pads, and
    each pad normalised (no samples, name, note, colour) less RoundRobin and
    AutoColored."""
    spans = pad_spans(xml)
    between = [xml[e:s] for (_, e), (s, _) in zip([(0, 0)] + spans, spans + [(len(xml), 0)])]
    pads = [re.sub(r'<(RoundRobin|AutoColored) Value="(true|false)" />', "",
                   normalised(xml[s:e])) for s, e in spans]
    return between, pads


def build_rack(donor, spans, pads, size, stats):
    max_layers, max_takes, _ = SIZES[size]
    creator = MultisampleRackCreator(template=ZONE_DONOR)
    out, cursor, built = [], 0, []
    for (start, end), (name, color, kit, piece, art) in zip(spans, pads):
        lead = LEAD.get(kit, 0)
        zones, report, mics = build_zones(
            SOURCE_ROOT / f"{kit} Kit Multi-Mic", piece, art, verbose=False, sample_start=lead,
            **({"max_layers": max_layers, "max_takes": max_takes} if max_layers else {}))
        stats["takes"] += report["takes"]
        stats["kept"] += report["kept"]
        stats["zones"] += len(zones)
        pad = donor[start:end]
        parts = ET.Element("SampleParts")
        for i, z in enumerate(zones):
            parts.append(creator._sample_part(i, z))
        sp = re.search(r"<SampleParts>.*?</SampleParts>", pad, re.S)
        pad = pad[:sp.start()] + ET.tostring(parts, encoding="unicode") + pad[sp.end():]
        rr = list(re.finditer(r'<RoundRobin Value="true" />', pad))
        if len(rr) != 1:
            raise SystemExit(f"{name}: expected one RoundRobin=true, found {len(rr)}")
        pad = pad[:rr[0].start()] + '<RoundRobin Value="false" />' + pad[rr[0].end():]
        pad = set_direct_child(pad, "Name", xml_attr(name))
        pad = set_direct_child(pad, "DocumentColorIndex", str(color))
        pad = set_direct_child(pad, "AutoColored", "false")
        out.append(donor[cursor:start] + pad)
        cursor = end
        built.append((name, color, zones, lead))
    out.append(donor[cursor:])
    return "".join(out), built


def verify(donor, result, built):
    """Outside the zone maps, RoundRobin, names and colours the rack is the
    donor; every velocity plays exactly one take on every mic of the piece."""
    (d_between, d_pads), (r_between, r_pads) = unedited(donor), unedited(result)
    if d_between != r_between or set(r_pads) != {d_pads[0]}:
        raise SystemExit("verify: rack changed outside SampleParts/RoundRobin/Name/colour")
    pads = ET.fromstring(result).findall(".//BranchPresets/DrumBranchPreset")
    assert len(pads) == len(built) == 32
    for pad, (name, color, zones, lead) in zip(pads, built):
        assert pad.find("Name").get("Value") == name
        assert pad.find("DocumentColorIndex").get("Value") == str(color)
        assert pad.find("AutoColored").get("Value") == "false"
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
    ap.add_argument("--plan", action="store_true", help="print the pads, write nothing")
    ap.add_argument("--size", choices=SIZES, action="append", help="default: all three")
    args = ap.parse_args()

    racks, pool = plan()
    print(f"{pool} sounds in scope")
    for rack, pads in racks.items():
        print(f"\n{rack}")
        for i, (name, *_rest) in enumerate(pads):
            print(f"  {36 + i:3}  {name}")
    if args.plan:
        return

    donor = decode_adg(DONOR)
    # The donor's three hi-hat pads carry choke group 1 (applied 2026-10-05);
    # these racks have no hi-hats, so every pad gets the others' "no choke".
    chokes = re.findall(r'<ChokeGroup Value="\d+" />', donor)
    if len(chokes) != 32:
        raise SystemExit(f"donor: {len(chokes)} ChokeGroup fields, expected one per pad")
    donor = re.sub(r'<ChokeGroup Value="\d+" />', '<ChokeGroup Value="0" />', donor)
    spans = pad_spans(donor)
    if len({normalised(donor[s:e]) for s, e in spans}) != 1:
        raise SystemExit("donor pads differ beyond samples/name/note/colour - refusing")
    for size in args.size or list(SIZES):
        out_dir = SIZES[size][2]
        out_dir.mkdir(parents=True, exist_ok=True)
        for rack, pads in racks.items():
            stats = defaultdict(int)
            result, built = build_rack(donor, spans, pads, size, stats)
            verify(donor, result, built)
            encode_adg(result, out_dir / f"{rack}.adg")
            print(f"[{size}] {rack}: {stats['takes']} takes -> {stats['kept']}, "
                  f"{stats['zones']} zones (verified)")


if __name__ == "__main__":
    main()
