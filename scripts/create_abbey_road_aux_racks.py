#!/usr/bin/env python3
"""
Abbey Road accessory racks: the claps, snaps, stick clicks, rims, cowbells and
blocks from every Abbey Road Drummer kit, gathered into category racks.

Six racks, one pad per (kit, articulation), kits in library order:

    Claps Solo & Snaps      18 solo claps + Ivory's finger snaps
    Claps Multi             18 multi-person claps
    Sticks & Clicks         18 stick clicks + spoons + kick shell
    Snare Rims              19 snare "rim only" hits
    Cowbells                22
    Woodblocks & Choppers   16 woodblocks + 6 choppers

The donor is a Live-saved library rack, `xFull/Abbey Road/Session.adg`: 32
bare-Sampler pads at C1-G3 that are identical apart from their samples, name,
note and colour (checked at run time - the build refuses a donor where that is
not true). Each output fills the donor's pads in document order (C1 upward)
and deletes the rest. Only each pad's `SampleParts`, `Name` and
`DocumentColorIndex`/`AutoColored` are rewritten, string-level, so the
library's curation (unmapped, macros hidden, 0.2 ms amp attack) carries over.
ReceivingNote is never touched.

Every sample is a 10-layer x ~6-take multisample on one recorded note, built
with the same `build_sample_parts` as the original Abbey Road kits, round
robin on.

Usage:
    PYTHONPATH=src python3 scripts/create_abbey_road_aux_racks.py --plan
    PYTHONPATH=src python3 scripts/create_abbey_road_aux_racks.py
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin
from create_abbey_road_kit import LIBRARY_ROOT, PAD_ROOT_NOTE, find_articulation_samples

INSTRUMENTS = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/Looping Presets/Instruments"
)
DONOR = INSTRUMENTS / "xFull/Abbey Road/Session.adg"
OUTPUT_DIR = INSTRUMENTS / "xFull/Abbey Road Aux"

# Library order, and the names the existing Abbey Road racks use.
KITS = [
    ("50s Drummer/Autumn Kit", "50s Autumn"),
    ("50s Drummer/Autumn Kit Brushes", "50s Autumn Brushes"),
    ("50s Drummer/Spring Kit", "50s Spring"),
    ("50s Drummer/Spring Kit Brushes", "50s Spring Brushes"),
    ("60s Drummer/Early 60s Kit", "60s Early 60s"),
    ("60s Drummer/Late 60s Kit", "60s Late 60s"),
    ("70s Drummer/Open Kit", "70s Open"),
    ("70s Drummer/Tight Kit", "70s Tight"),
    ("80s Drummer/Black Kit", "80s Black"),
    ("80s Drummer/Chrome Kit", "80s Chrome"),
    ("Modern Drummer/Sparkle Kit", "Modern Sparkle"),
    ("Modern Drummer/White Kit", "Modern White"),
    ("Studio Drummer/Garage Kit", "Garage"),
    ("Studio Drummer/Session Kit", "Session"),
    ("Studio Drummer/Stadium Kit", "Stadium"),
    ("Vintage Drummer/Ebony Kit", "Vintage Ebony"),
    ("Vintage Drummer/Ebony Kit Brushes", "Vintage Ebony Brushes"),
    ("Vintage Drummer/Ivory Kit", "Vintage Ivory"),
    ("Vintage Drummer/Ivory Kit Brushes", "Vintage Ivory Brushes"),
]

COLORS = {"clap": 58, "click": 16, "kick": 60, "snare": 59, "bell": 26, "block": 16}

# rack -> list of (instrument folder regex, articulation regex, colour key).
# Each rule is applied across all kits before the next rule, so a rack reads
# as one sound type at a time, kits in library order within it.
RACKS = {
    "Claps Solo & Snaps": [
        (r"clap", r"^solo$", "clap"),
        (r"^finger$", r"snaps", "click"),
    ],
    "Claps Multi": [
        (r"clap", r"^multi$", "clap"),
    ],
    "Sticks & Clicks": [
        (r"stick", r".", "click"),
        (r"^spoons$", r".", "click"),
        (r"^kick shell$", r".", "kick"),
    ],
    "Snare Rims": [
        (r"^snare", r"^rim only$", "snare"),
    ],
    "Cowbells": [
        (r"cowbell", r".", "bell"),
    ],
    "Woodblocks & Choppers": [
        (r"wood ?block", r".", "block"),
        (r"chopper", r".", "block"),
    ],
}

# Combo racks: each kit is one row of four pads - clap solo, clap multi,
# stick click, snare rim - so on a 4x4 grid moving up a row changes kit.
# Brushes kits are left out: same instruments as their stick-kit twins.
COMBO_ROW = [
    (r"clap", r"^solo$", "clap"),
    (r"clap", r"^multi$", "clap"),
    (r"stick", r".", "click"),
    (r"^snare", r"^rim only$", "snare"),
]
COMBO_ROWS = {
    # Ivory has no claps; its hand sounds are finger snaps and spoons.
    "Vintage Ivory": [
        (r"^finger$", r".", "click"),
        (r"^spoons$", r"closed", "click"),
        (r"stick", r".", "click"),
        (r"^snare", r"^rim only$", "snare"),
    ],
}
COMBOS = {
    "Combo 1 (50s-80s)": [
        "50s Autumn", "50s Spring", "60s Early 60s", "60s Late 60s",
        "70s Open", "70s Tight", "80s Black", "80s Chrome",
    ],
    "Combo 2 (Modern Studio Vintage)": [
        "Modern Sparkle", "Modern White", "Garage", "Session", "Stadium",
        "Vintage Ebony", "Vintage Ivory",
    ],
}

SAMPLE_RE = re.compile(r"^(.+)-([A-G]#?-?\d+)-V(\d+)-([A-Za-z0-9]+)\.wav$", re.IGNORECASE)


def kit_articulations(kit_dir: Path):
    """[(instrument, articulation)] for every recorded articulation in a kit."""
    out = []
    for inst in sorted(p for p in kit_dir.iterdir() if p.is_dir()):
        arts = set()
        for wav in inst.glob("*.wav"):
            m = SAMPLE_RE.match(wav.name)
            if m and m.group(1).startswith(inst.name + " "):
                arts.add(m.group(1)[len(inst.name) + 1:])
        out.extend((inst.name, a) for a in sorted(arts, key=art_key))
    return out


def pad_label(inst: str, art: str) -> str:
    """"Perc 1 (Stick Hit)" -> "Stick Hit", "Snare Drum 1 2 & 3" -> "Snare",
    and "Stick Hit Hit" -> "Stick Hit"."""
    inst = re.sub(r"^Perc \d+ \((.*)\)$", r"\1", inst)
    if inst.lower().startswith("snare"):
        inst = "Snare"
    words = f"{inst} {art}".split()
    return " ".join(w for i, w in enumerate(words) if i == 0 or w != words[i - 1])


ORDER = {"high": 0, "hi": 0, "mid": 1, "low": 2}


def art_key(art: str):
    """High before Mid before Low, then alphabetical."""
    words = art.lower().split()
    return (min((ORDER[w] for w in words if w in ORDER), default=1), art)


def plan_racks():
    """rack -> [(pad name, colour, {velocity: [paths]})]"""
    catalog = [(name, LIBRARY_ROOT / rel, kit_articulations(LIBRARY_ROOT / rel)) for rel, name in KITS]
    plan = {}
    for rack, rules in RACKS.items():
        pads = []
        for inst_re, art_re, color in rules:
            for kit_name, kit_dir, arts in catalog:
                for inst, art in arts:
                    if re.search(inst_re, inst, re.I) and re.search(art_re, art, re.I):
                        layers = find_articulation_samples(kit_dir / inst, f"{inst} {art}")
                        pads.append((f"{kit_name} - {pad_label(inst, art)}", COLORS[color], layers))
        if len(pads) > 32:
            raise ValueError(f"{rack}: {len(pads)} pads, the donor has 32")
        plan[rack] = pads

    # Combos: one row of four pads per kit, so a 4x4 grid steps kit by kit.
    by_name = {name: (kit_dir, arts) for name, kit_dir, arts in catalog}
    for rack, kits in COMBOS.items():
        pads = []
        for kit_name in kits:
            kit_dir, arts = by_name[kit_name]
            for inst_re, art_re, color in COMBO_ROWS.get(kit_name, COMBO_ROW):
                hits = [(i, a) for i, a in arts if re.search(inst_re, i, re.I) and re.search(art_re, a, re.I)]
                if len(hits) != 1:
                    raise ValueError(f"{rack}: {kit_name} has {len(hits)} matches for {inst_re} / {art_re}")
                inst, art = hits[0]
                layers = find_articulation_samples(kit_dir / inst, f"{inst} {art}")
                pads.append((f"{kit_name} - {pad_label(inst, art)}", COLORS[color], layers))
        if len(pads) > 32:
            raise ValueError(f"{rack}: {len(pads)} pads, the donor has 32")
        plan[rack] = pads
    return plan


def pad_spans(xml: str):
    spans = [(m.start(), m.end()) for m in
             re.finditer(r'<DrumBranchPreset Id="\d+">.*?</DrumBranchPreset>', xml, re.S)]
    root = ET.fromstring(xml)
    if len(spans) != len(root.findall(".//BranchPresets/DrumBranchPreset")):
        raise ValueError("pad spans do not match the parsed pads")
    return spans


def normalised(pad: str) -> str:
    pad = re.sub(r"<SampleParts>.*?</SampleParts>", "", pad, flags=re.S)
    pad = re.sub(r'<DrumBranchPreset Id="\d+">', "", pad)
    for tag in ("Name", "ReceivingNote", "DocumentColorIndex", "RoundRobinRandomSeed"):
        pad = re.sub(rf'<{tag} Value="[^"]*" />', "", pad)
    return pad


def set_direct_child(pad: str, tag: str, value: str) -> str:
    """Rewrite the pad's own <tag Value=...> (a direct child of the
    DrumBranchPreset), located by document-order index - the Sampler inside
    carries fields of the same names."""
    root = ET.fromstring(pad)
    child = root.find(tag)
    index = [e for e in root.iter(tag)].index(child)
    matches = list(re.finditer(rf'<{tag} Value="[^"]*" />', pad))
    m = matches[index]
    return pad[:m.start()] + f'<{tag} Value="{value}" />' + pad[m.end():]


def xml_attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def build_rack(donor: str, spans, pads, creator: SamplerCreator) -> str:
    pieces, cursor = [], 0
    for i, (start, end) in enumerate(spans):
        if i < len(pads):
            name, color, layers = pads[i]
            pad = donor[start:end]
            parts = ET.Element("SampleParts")
            for part in build_sample_parts(creator, layers, PAD_ROOT_NOTE):
                parts.append(part)
            parts_text = ET.tostring(parts, encoding="unicode")
            sp = re.search(r"<SampleParts>.*?</SampleParts>", pad, re.S)
            pad = pad[:sp.start()] + parts_text + pad[sp.end():]
            pad = set_direct_child(pad, "Name", xml_attr(name))
            pad = set_direct_child(pad, "DocumentColorIndex", str(color))
            pad = set_direct_child(pad, "AutoColored", "false")
            pieces.append(donor[cursor:start] + pad)
        else:
            # drop the pad and the indentation before it
            ws = len(donor[cursor:start]) - len(donor[cursor:start].rstrip())
            pieces.append(donor[cursor:start - ws])
        cursor = end
    pieces.append(donor[cursor:])
    return "".join(pieces)


def verify(result: str, pads) -> None:
    root = ET.fromstring(result)
    built = root.findall(".//BranchPresets/DrumBranchPreset")
    assert len(built) == len(pads), (len(built), len(pads))
    for i, (pad, (name, color, layers)) in enumerate(zip(built, pads)):
        assert pad.find("Name").get("Value") == name
        assert pad.find("DocumentColorIndex").get("Value") == str(color)
        assert pad.find("AutoColored").get("Value") == "false"
        assert int(pad.find("ZoneSettings/ReceivingNote").get("Value")) == 92 - i
        paths = [p.get("Value") for p in pad.findall(".//MultiSamplePart/SampleRef/FileRef/Path")]
        want = sorted(str(p) for ps in layers.values() for p in ps)
        assert sorted(paths) == want, name
        assert all(Path(p).is_file() for p in paths)
        rr = pad.find(".//MultiSampleMap/RoundRobin")
        assert rr is not None and rr.get("Value") == "true"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--plan", action="store_true", help="print the pads and write nothing")
    args = ap.parse_args()

    plan = plan_racks()
    for rack, pads in plan.items():
        print(f"\n{rack} ({len(pads)} pads)")
        for i, (name, _, layers) in enumerate(pads):
            n = sum(len(v) for v in layers.values())
            print(f"  {36 + i:3}  {name}  [{len(layers)} layers, {n} samples]")
    if args.plan:
        return

    donor = decode_adg(DONOR)
    spans = pad_spans(donor)
    if len({normalised(donor[s:e]) for s, e in spans}) != 1:
        raise SystemExit("donor pads differ beyond samples/name/note/colour - refusing")

    creator = SamplerCreator(template=DONOR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for rack, pads in plan.items():
        result = build_rack(donor, spans, pads, creator)
        verify(result, pads)
        out = OUTPUT_DIR / f"{rack}.adg"
        encode_adg(result, out)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
