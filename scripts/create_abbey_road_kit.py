#!/usr/bin/env python3
"""
Create Abbey Road Kits — builds a Drum Rack per Native Instruments Abbey
Road Drummer kit, matching AbbeyRoadStudioDrummer_Mapping.csv exactly: one
pad per articulation, placed at its official MIDI note.

Unlike the Damage workflow (one fixed 32-pad grid, one instrument per pad,
all forced onto a shared internal note), each kit's articulation count
varies (Autumn Kit maps to 74 distinct notes after collisions/missing
samples), so pads are generated dynamically — one clone of the donor's
Sampler-loaded pad per surviving CSV row, not a fixed 32. The donor's
rack-level state (macros, colors, view settings) is otherwise untouched,
same principle as the Damage workflow: never reconstruct anything beyond
what has to change.

The sample filenames already match the CSV (e.g. "Kick Drum Dampened-C3-
V1-2XDH.wav" for the CSV row "Kick Drum,Dampened,60" — C3 = MIDI 60 in
this codebase's convention), so the CSV isn't strictly required to find
files, but it's the authoritative source of which MIDI note each
articulation belongs on, and it's what surfaces collisions.

Collision handling: some notes are claimed by two articulations in the
CSV (e.g. two different Brush hits sharing one note — presumably resolved
via keyswitching in the original Kontakt instrument, which a plain Drum
Rack can't replicate). PRIORITY_KEYWORDS resolves these deterministically
by drum-piece importance — the higher-priority piece keeps the note, and
if that piece turns out to have no actual sample files for the note, the
next-priority candidate is tried instead (a CSV row isn't proof samples
exist — see Cymbal 3/Ride in Autumn Kit, which the CSV maps to Edge/
Choke/Brush articulations that were never actually recorded).

Drum-piece naming varies a lot between kits (e.g. "Kick" vs "Kick Drum",
"Cymbal 4 (China)", "Perc 5 (Timbale)"), so priority/coloring is keyword-
based rather than an exact-name lookup table.

IMPORTANT — ZoneSettings/ReceivingNote is stored inverted: the value
written to the XML is `128 - actual_trigger_note`, not the trigger note
itself. Confirmed empirically (stored 127 played back as MIDI note 1;
stored 80 played back as C2/MIDI 48) — this only affects ReceivingNote,
not SendingNote or the Sampler's own KeyRange/RootKey, which behave as
plain direct MIDI numbers. Every write to ReceivingNote in this file must
go through to_receiving_note_value().

Usage:
    export PYTHONPATH=src
    python3 scripts/create_abbey_road_kit.py
"""

import copy
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin

LIBRARY_ROOT = Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Native Instruments/Abbey Road Autosamples")
MAPPING_CSV = LIBRARY_ROOT / "AbbeyRoadStudioDrummer_Mapping.csv"
DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler_drum_rack_template.adg"
OUTPUT_DIR = LIBRARY_ROOT / "Drum Racks"

PAD_ROOT_NOTE = 60  # internal Sampler root — same convention as the Damage workflow

# Canonical drum-kit importance, checked in order — first match wins.
# "kick shell" must precede "kick" since it's a distinct, lower-priority
# piece that happens to contain the substring "kick".
PRIORITY_KEYWORDS = [
    (r"kick shell", 6),
    (r"kick", 0),
    (r"snare", 1),
    (r"hi.?hat", 2),
    (r"cymbal|crash|ride|china|splash|sizzle|pang", 3),
    (r"tom", 4),
    (r"clap", 5),
    (r"bongo|cowbell|tambourine|timbale|perc", 7),
    (r"stick|finger|spoon|sand paper", 8),
    (r"triangle|woodblock", 9),
]

# DocumentColorIndex per drum-piece family, same keyword scheme — reused,
# validated indices as the Damage workflow's CATEGORY_COLORS.
PIECE_COLOR_KEYWORDS = [
    (r"kick", 60),
    (r"snare", 59),
    (r"hi.?hat", 62),
    (r"cymbal|crash|ride|china|splash|sizzle|pang", 45),
    (r"tom", 49),
    (r"clap", 58),
    (r"bongo|cowbell|tambourine|timbale|perc", 26),
    (r"stick|finger|spoon|sand paper|triangle|woodblock", 16),
]


def priority(drum_piece: str) -> int:
    for pattern, rank in PRIORITY_KEYWORDS:
        if re.search(pattern, drum_piece, re.IGNORECASE):
            return rank
    return 99


def piece_color(drum_piece: str):
    for pattern, color in PIECE_COLOR_KEYWORDS:
        if re.search(pattern, drum_piece, re.IGNORECASE):
            return color
    return None


def to_receiving_note_value(trigger_note: int) -> int:
    """ZoneSettings/ReceivingNote stores 128 - actual_trigger_note, not the
    trigger note itself — confirmed empirically, see module docstring."""
    return 128 - trigger_note


def discover_kits(library_root: Path) -> dict:
    """Find every "<Era Drummer>/<Kit Name>" folder in the library."""
    kits = {}
    for era_dir in sorted(p for p in library_root.iterdir() if p.is_dir()):
        if era_dir.name == "Drum Racks":  # our own output, not a source kit
            continue
        for kit_dir in sorted(p for p in era_dir.iterdir() if p.is_dir()):
            kits[kit_dir.name] = kit_dir
    return kits


def era_short_name(kit_folder: Path) -> str:
    """"50s Drummer" -> "50s", "Studio Drummer" -> "Studio", etc."""
    return kit_folder.parent.name.replace(" Drummer", "")


def load_mapping(kit_name: str) -> dict:
    """Read the CSV for one kit; group rows by MIDI note, each note's
    candidates sorted by priority (most important first). Collisions
    aren't resolved here — a candidate might turn out to have no actual
    sample files, so the caller falls back through the sorted list until
    one has real samples."""
    by_note = {}
    with open(MAPPING_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["kit_name"] == kit_name:
                note = int(row["midi_note"])
                by_note.setdefault(note, []).append((row["drum_piece"], row["articulation"]))
    for note in by_note:
        by_note[note].sort(key=lambda r: priority(r[0]))
    return by_note


def find_articulation_samples(folder: Path, prefix: str) -> dict:
    """Group one articulation's samples by velocity layer. Filenames share a
    folder with every other articulation of the same drum piece, so match
    on the exact "<drum piece> <articulation>-" prefix."""
    if not folder.is_dir():
        return {}
    pattern = re.compile(rf"^{re.escape(prefix)}-([A-G]#?-?\d+)-V(\d+)-([A-Za-z0-9]+)\.wav$", re.IGNORECASE)
    layers = {}
    for f in folder.glob("*.wav"):
        m = pattern.match(f.name)
        if m:
            layers.setdefault(int(m.group(2)), []).append(f)
    return layers


def color_pad(pad: ET.Element, drum_piece: str) -> None:
    color = piece_color(drum_piece)
    if color is None:
        return
    color_elem = pad.find("DocumentColorIndex")
    if color_elem is not None:
        color_elem.set("Value", str(color))
    auto_colored = pad.find("AutoColored")
    if auto_colored is not None:
        auto_colored.set("Value", "false")


def build_kit(kit_name: str, kit_folder: Path, donor_pad: ET.Element, creator: SamplerCreator) -> bool:
    output_path = OUTPUT_DIR / f"AR {era_short_name(kit_folder)} {kit_name}.adg"
    print(f"\n=== {kit_name} ===")

    mapping = load_mapping(kit_name)
    if not mapping:
        print("  No CSV rows for this kit — skipping.")
        return False
    print(f"  {len(mapping)} distinct notes in CSV")

    rack_xml = decode_adg(DRUM_RACK_TEMPLATE)
    rack_root = ET.fromstring(rack_xml)
    branch_presets = rack_root.find(".//BranchPresets")
    for old_pad in list(branch_presets):
        branch_presets.remove(old_pad)

    built = 0
    skipped_notes = []
    for idx, note in enumerate(sorted(mapping.keys())):
        candidates = mapping[note]
        drum_piece = articulation = None
        layers = None
        for candidate_piece, candidate_articulation in candidates:
            folder = kit_folder / candidate_piece
            prefix = f"{candidate_piece} {candidate_articulation.replace('/', '-')}"
            found = find_articulation_samples(folder, prefix)
            if found:
                drum_piece, articulation, layers = candidate_piece, candidate_articulation, found
                break

        if layers is None:
            print(f"  SKIP note {note}: no samples for any candidate ({', '.join(f'{p}/{a}' for p, a in candidates)})")
            skipped_notes.append(note)
            continue

        if len(candidates) > 1:
            dropped = [f"{p}/{a}" for p, a in candidates if (p, a) != (drum_piece, articulation)]
            print(f"  Note {note}: {len(candidates)} candidates, using {drum_piece}/{articulation} (dropped: {dropped})")

        pad = copy.deepcopy(donor_pad)
        pad.set("Id", str(idx))

        recv = pad.find(".//ZoneSettings/ReceivingNote")
        recv.set("Value", str(to_receiving_note_value(note)))

        sample_map = pad.find(".//MultiSampleMap")
        old_parts = sample_map.find("SampleParts")
        if old_parts is not None:
            sample_map.remove(old_parts)
        new_parts = ET.SubElement(sample_map, "SampleParts")
        for part in build_sample_parts(creator, layers, PAD_ROOT_NOTE):
            new_parts.append(part)
        enable_round_robin(sample_map)
        color_pad(pad, drum_piece)

        name_elem = pad.find("Name")
        if name_elem is not None:
            name_elem.set("Value", f"{drum_piece} - {articulation}")

        branch_presets.append(pad)
        built += 1

    if skipped_notes:
        print(f"  {len(skipped_notes)} notes had no samples for any candidate.")

    if built == 0:
        print("  No pads built — skipping output.")
        return False

    xml_string = ET.tostring(rack_root, encoding="unicode", xml_declaration=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    encode_adg(xml_string, output_path)
    print(f"  Created: {output_path} ({built} pads)")
    return True


def main():
    if not DRUM_RACK_TEMPLATE.exists():
        print(f"Error: Drum rack template not found: {DRUM_RACK_TEMPLATE}")
        sys.exit(1)

    kits = discover_kits(LIBRARY_ROOT)
    print(f"Discovered {len(kits)} kit folders")

    donor_xml = decode_adg(DRUM_RACK_TEMPLATE)
    donor_root = ET.fromstring(donor_xml)
    donor_pad = copy.deepcopy(donor_root.find(".//BranchPresets/DrumBranchPreset"))
    if donor_pad is None:
        raise ValueError("Donor template missing a DrumBranchPreset to clone")

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)

    results = {}
    for kit_name, kit_folder in kits.items():
        results[kit_name] = build_kit(kit_name, kit_folder, donor_pad, creator)

    print("\nSummary:")
    for kit_name, ok in results.items():
        print(f"  {'OK' if ok else 'FAILED'}: {kit_name}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
