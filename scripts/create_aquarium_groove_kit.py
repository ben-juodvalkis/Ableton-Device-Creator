#!/usr/bin/env python3
"""
Create Aquarium Groove Kit — a Damage-style 32-pad Drum Rack from a single
real acoustic kit's raw samples (a flat folder, not the Damage library's
per-instrument-folder structure).

Source: Aquarium_Groove_<Piece>_<Note>_<MidiNum>_v<Velocity>_rr<N>.wav —
e.g. "Aquarium_Groove_Snare_D2_038_v057_rr2.wav". The MIDI number is
embedded directly (no note-name convention to reverse-engineer). Some
piece names repeat at different notes (Snare at D2/D#2/E2, Floor_Tom at
C3/C#3/E3/G3, Tom at D3/D#3/F3, Ride at 3 mic positions/techniques) — each
(piece, note) pair is treated as its own distinct playable element, 20
total. 10 velocity layers (1/15/29/43/57/71/85/99/113/127, same ladder as
the Damage workflow), up to 4 round-robin takes.

Same "Damage-style" principle as the rest of this project: the donor rack
(templates/sampler_drum_rack_template.adg) already has 32 pads with a real
Sampler loaded and macros/colors/mixer configured by hand in Ableton.
Every pad's SendingNote is fixed at 60 (C3) regardless of trigger note, so
every embedded Sampler's SampleParts are built on a single fixed root
note (60) — the source note embedded in each filename is only used to
group samples into their velocity layers, not to place them on the
keyboard. This script only ever touches each pad's
MultiSampleMap/SampleParts — nothing about the rack itself is
reconstructed.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_aquarium_groove_kit.py
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, velocity_bins

SOURCE_DIR = Path("/Users/Music/Desktop/Aquarium_Groove")
DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler_drum_rack_template.adg"
OUTPUT_PATH = SOURCE_DIR.parent / "Drum_Rack_Aquarium_Groove.adg"

PAD_ROOT_NOTE = 60  # C3 — matches every pad's fixed SendingNote, same as the Damage workflow

FILENAME_RE = re.compile(r"^Aquarium_Groove_(.+)_[A-G]#?-?\d+_(\d+)_v(\d+)_rr(\d+)\.wav$", re.IGNORECASE)

# DocumentColorIndex per piece family — same reused, validated indices as
# the Damage/Abbey Road workflows.
PIECE_COLOR_KEYWORDS = [
    (r"kick", 60),
    (r"snare", 59),
    (r"rim", 58),
    (r"hat", 62),
    (r"crash|ride", 45),
    (r"tom", 49),
]


def piece_color(piece: str):
    for pattern, color in PIECE_COLOR_KEYWORDS:
        if re.search(pattern, piece, re.IGNORECASE):
            return color
    return None


def parse_library(folder: Path) -> dict:
    """{(piece, midi_note): {velocity_center: [sample_paths]}}"""
    instruments = {}
    for f in folder.glob("*.wav"):
        m = FILENAME_RE.match(f.name)
        if not m:
            continue
        piece, note, velocity = m.group(1), int(m.group(2)), int(m.group(3))
        instruments.setdefault((piece, note), {}).setdefault(velocity, []).append(f)
    return instruments


def color_pad(pad: ET.Element, piece: str) -> None:
    color = piece_color(piece)
    if color is None:
        return
    color_elem = pad.find("DocumentColorIndex")
    if color_elem is not None:
        color_elem.set("Value", str(color))
    auto_colored = pad.find("AutoColored")
    if auto_colored is not None:
        auto_colored.set("Value", "false")


def main():
    if not DRUM_RACK_TEMPLATE.exists():
        print(f"Error: Drum rack template not found: {DRUM_RACK_TEMPLATE}")
        sys.exit(1)
    if not SOURCE_DIR.exists():
        print(f"Error: Source directory not found: {SOURCE_DIR}")
        sys.exit(1)

    print(f"Scanning: {SOURCE_DIR}")
    instruments = parse_library(SOURCE_DIR)
    total_files = sum(len(v) for layers in instruments.values() for v in layers.values())
    print(f"  {len(instruments)} instruments (piece+note), {total_files} samples total\n")

    rack_xml = decode_adg(DRUM_RACK_TEMPLATE)
    rack_root = ET.fromstring(rack_xml)
    pads = rack_root.findall(".//BranchPresets/DrumBranchPreset")
    pads.sort(key=lambda p: int(p.find(".//ZoneSettings/ReceivingNote").get("Value")), reverse=True)

    if len(instruments) > len(pads):
        print(f"Error: {len(instruments)} instruments but only {len(pads)} pads available")
        sys.exit(1)

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)

    # Stable order: by original note ascending, so the pad layout roughly
    # mirrors the source kit's own low-to-high arrangement.
    ordered = sorted(instruments.items(), key=lambda kv: kv[0][1])

    built = 0
    for pad, ((piece, source_note), layers) in zip(pads, ordered):
        note = pad.find(".//ZoneSettings/ReceivingNote").get("Value")
        layer_summary = ", ".join(f"V{c}:{len(layers[c])}" for c, _, _ in velocity_bins(layers.keys()))
        print(f"  Note {note}: {piece} (source note {source_note}) — {len(layers)} velocity layers ({layer_summary})")

        sample_map = pad.find(".//MultiSampleMap")
        old_parts = sample_map.find("SampleParts")
        if old_parts is not None:
            sample_map.remove(old_parts)
        new_parts = ET.SubElement(sample_map, "SampleParts")
        for part in build_sample_parts(creator, layers, PAD_ROOT_NOTE):
            new_parts.append(part)
        enable_round_robin(sample_map)
        color_pad(pad, piece)

        name_elem = pad.find("Name")
        if name_elem is not None:
            name_elem.set("Value", f"{piece} ({source_note})")

        built += 1

    xml_string = ET.tostring(rack_root, encoding="unicode", xml_declaration=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(xml_string, OUTPUT_PATH)
    print(f"\nCreated: {OUTPUT_PATH} ({built} pads)")


if __name__ == "__main__":
    main()
