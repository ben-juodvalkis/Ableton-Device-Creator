#!/usr/bin/env python3
"""
Create Alt Strings Pizz Sampler — a single Sampler device (.adv, no rack
wrapper) from Spitfire's Alternative Strings Pizzicato Quartet raw
samples.

Source: Alternative_Strings_Pizz/AltStringsPizzQuartet_<Note>_<MidiNum>_
v<Velocity>_rr<N>.wav — the MIDI number is embedded directly in the
filename (e.g. "C4_060"), so there's no note-name convention to
reverse-engineer — confirmed scientific pitch (C4=60), same as the OAE
library, still the opposite of this project's usual C3=60 convention
elsewhere.

Originally fully chromatic (every semitone C1-C#7, 1166 files), but the
source folder has since been pruned of duplicates down to whole-tone
spacing (600 files, ~39 notes, roughly every 2 semitones — with one
irregular 1-semitone gap where the pruning didn't land evenly). Each
recorded note's KeyRange is stretched via multisample_utils.pitch_zones()
to fill the gap to its neighbors, same technique as the OAE Evo sampler's
sparse chromatic mapping. If the source folder changes density again,
this script adapts automatically — it never assumes a fixed note spacing.

Each note still gets velocity (25/70/110) + round-robin layering like the
Damage workflow, via multisample_utils.build_sample_parts() with an
explicit key_min/key_max zone and a start_index offset so every note's
parts share one globally-unique Id space in the final SampleParts list.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_alt_strings_pizz.py
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, pitch_zones

SOURCE_DIR = Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Spitfire/Alternative Strings Pizz/Alternative_Strings_Pizz")
DONOR_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler-rack.adg"
OUTPUT_PATH = SOURCE_DIR.parent / "Instruments" / "Alt Strings Pizz Quartet.adv"

FILENAME_RE = re.compile(r"^AltStringsPizzQuartet_[A-G]#?-?\d+_(\d+)_v(\d+)_rr(\d+)\.wav$", re.IGNORECASE)


def parse_library(folder: Path) -> dict:
    """{midi_note: {velocity_center: [sample_paths]}}"""
    by_note = {}
    for f in folder.glob("*.wav"):
        m = FILENAME_RE.match(f.name)
        if not m:
            continue
        note, velocity = int(m.group(1)), int(m.group(2))
        by_note.setdefault(note, {}).setdefault(velocity, []).append(f)
    return by_note


def main():
    if not DONOR_TEMPLATE.exists():
        print(f"Error: Donor template not found: {DONOR_TEMPLATE}")
        sys.exit(1)
    if not SOURCE_DIR.exists():
        print(f"Error: Source directory not found: {SOURCE_DIR}")
        sys.exit(1)

    print(f"Scanning: {SOURCE_DIR}")
    by_note = parse_library(SOURCE_DIR)
    total_files = sum(len(v) for layers in by_note.values() for v in layers.values())
    print(f"  {len(by_note)} recorded notes, {total_files} samples total\n")

    creator = SamplerCreator(template=DONOR_TEMPLATE)
    donor_xml = decode_adg(DONOR_TEMPLATE)
    donor_root = ET.fromstring(donor_xml)
    multi_sampler = donor_root.find(".//MultiSampler")
    if multi_sampler is None:
        raise ValueError("Donor template missing a MultiSampler device")

    sample_map = multi_sampler.find(".//MultiSampleMap")
    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")

    index = 0
    for note, key_min, key_max in pitch_zones(by_note.keys()):
        layers = by_note[note]
        parts = build_sample_parts(creator, layers, note, start_index=index, key_min=key_min, key_max=key_max)
        for part in parts:
            new_parts.append(part)
        index += len(parts)
        print(f"  Note {note:3}: zone {key_min}-{key_max}, {len(parts)} samples")

    enable_round_robin(sample_map)
    print(f"\nBuilt {index} sample parts across {len(by_note)} notes")

    # Bare device — extract just the MultiSampler, drop the Instrument
    # Rack wrapper (GroupDevicePreset/InstrumentGroupDevice/BranchPresets).
    root = ET.Element("Ableton", donor_root.attrib)
    root.append(multi_sampler)
    xml_string = ET.tostring(root, encoding="unicode", xml_declaration=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(xml_string, OUTPUT_PATH)
    print(f"\nCreated: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
