#!/usr/bin/env python3
"""
Abbey Road accessory racks: the claps, snaps, stick clicks, rims, cowbells and
blocks from every Abbey Road Drummer kit, gathered into full 32-pad racks
(Ben's controller has 32 pads; no rack leaves one empty).

Four category racks, one pad per (kit, articulation), kits in library order -
the 112 sounds in scope once each, plus 16 re-used to fill the last rack:

    Claps                   solo + multi side by side, 16 kits
    Claps, Snaps & Sticks   2 kits' claps, finger snaps, 18 stick clicks,
                            spoons, kick shells, 5 snare rims
    Rims & Woodblocks       14 snare rims, 16 woodblocks, 2 choppers
    Bells & Blocks          12 cowbells (no open ones), 6 choppers,
                            14 woodblocks (re-used)

and two combos, one kit per row of four pads (see COMBOS).

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

# A rule is (instrument folder regex, articulation regex, colour key[, regex
# the pad name must NOT match]). Each rule runs across all kits before the
# next, so sounds of one type sit together, kits in library order.
#
# Every rack is a full 32 pads (Ben's controller has 32). POOL is every sound
# in scope once, in order, cut into consecutive racks of 32; it comes to 112,
# so the last rack is defined on its own and re-uses 16 pads from the third.
NO_OPEN = r"^(?!.*open)"  # open cowbells are left out
POOL = [
    (r"clap", r"^(solo|multi)$", "clap"),  # solo and multi side by side per kit
    (r"^finger$", r"snaps", "click"),
    (r"stick", r".", "click"),
    (r"^spoons$", r".", "click"),
    (r"^kick shell$", r".", "kick"),
    (r"^snare", r"^rim only$", "snare"),
    (r"wood ?block", r".", "block"),
    (r"chopper", r".", "block"),
    (r"cowbell", NO_OPEN, "bell"),
]
POOL_RACKS = ["Claps", "Claps, Snaps & Sticks", "Rims & Woodblocks"]
RACKS = {
    "Bells & Blocks": [
        (r"cowbell", NO_OPEN, "bell"),
        (r"chopper", r".", "block"),
        (r"wood ?block", r".", "block", r"^Stadium - .* Double$"),
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
        # Top row, so no pad is empty: the vintage kits' leftover percussion.
        [("Vintage Ebony", r"cowbell", r"^muted$", "bell"),
         ("50s Spring", r"cowbell", r".", "bell"),
         ("Vintage Ivory", r"wood ?block", r".", "block"),
         ("Vintage Ivory", r"^spoons$", r"open", "click")],
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


ORDER = {"high": 0, "hi": 0, "solo": 0, "mid": 1, "multi": 1, "low": 2}


def art_key(art: str):
    """High before Mid before Low, Solo before Multi, then alphabetical."""
    words = art.lower().split()
    return (min((ORDER[w] for w in words if w in ORDER), default=1), art)


def plan_racks():
    """rack -> [(pad name, colour, {velocity: [paths]})]"""
    catalog = [(name, LIBRARY_ROOT / rel, kit_articulations(LIBRARY_ROOT / rel)) for rel, name in KITS]
    def expand(rules):
        pads = []
        for inst_re, art_re, color, *skip in rules:
            for kit_name, kit_dir, arts in catalog:
                for inst, art in arts:
                    if re.search(inst_re, inst, re.I) and re.search(art_re, art, re.I):
                        name = f"{kit_name} - {pad_label(inst, art)}"
                        if skip and re.search(skip[0], name):
                            continue
                        layers = find_articulation_samples(kit_dir / inst, f"{inst} {art}")
                        pads.append((name, COLORS[color], layers))
        return pads

    plan = {}
    pool = expand(POOL)
    for i, rack in enumerate(POOL_RACKS):
        plan[rack] = pool[32 * i:32 * (i + 1)]
    for rack, rules in RACKS.items():
        plan[rack] = expand(rules)
    for rack, pads in plan.items():
        if len(pads) != 32:
            raise ValueError(f"{rack}: {len(pads)} pads - every rack fills all 32")
    placed = {name for pads in plan.values() for name, _, _ in pads}
    missing = [name for name, _, _ in pool if name not in placed]
    if missing:
        raise ValueError(f"sounds on no rack: {missing}")

    # Combos: one row of four pads per kit, so a 4x4 grid steps kit by kit.
    by_name = {name: (kit_dir, arts) for name, kit_dir, arts in catalog}
    for rack, kits in COMBOS.items():
        pads = []
        rows = []
        for row in kits:
            if isinstance(row, str):
                rows.extend((row,) + rule for rule in COMBO_ROWS.get(row, COMBO_ROW))
            else:
                rows.extend(row)
        for kit_name, inst_re, art_re, color in rows:
            kit_dir, arts = by_name[kit_name]
            hits = [(i, a) for i, a in arts if re.search(inst_re, i, re.I) and re.search(art_re, a, re.I)]
            if len(hits) != 1:
                raise ValueError(f"{rack}: {kit_name} has {len(hits)} matches for {inst_re} / {art_re}")
            inst, art = hits[0]
            layers = find_articulation_samples(kit_dir / inst, f"{inst} {art}")
            pads.append((f"{kit_name} - {pad_label(inst, art)}", COLORS[color], layers))
        if len(pads) != 32:
            raise ValueError(f"{rack}: {len(pads)} pads - combos fill all 32, no empty pads")
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
