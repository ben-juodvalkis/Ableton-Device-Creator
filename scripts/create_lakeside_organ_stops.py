#!/usr/bin/env python3
"""
Create Lakeside Organ Stops — one bare Sampler device (.adv, no rack
wrapper) per stop of Soundiron's Lakeside Pipe Organ, Close mic only.

Source: Samples/close/pipe_organ_cls_<stop>_<index>[_rel].wav. Per the
manual (Documentation/*.pdf), this is 6 stops, not 5 folders — stop 6
(Pedalboard) shares stop 5's "05" filename prefix but uses a literal
"pedal" marker instead of a numeric index, rather than getting its own
prefix. Stops 1-5 span a standard 61-note manual (5 octaves); Stop 6
spans a 32-note pedalboard.

No velocity dimension (real pipe organs aren't velocity-sensitive — the
manual confirms no velocity control exists) and no round-robin (each
index is exactly one sample). Every note also has a paired "_rel" release
-trigger sample (the sound of the pipe cutting off) — SKIPPED in this
first pass, since Ableton's release-trigger zone field hasn't been
confirmed against a real donor yet. Building sustain-only for now.

IMPORTANT — the index-to-MIDI-note mapping is NOT independently
confirmed. There's no manifest or embedded MIDI number in these
filenames (unlike every other library this project has handled), and a
DIY autocorrelation pitch check gave inconsistent results (likely the
organ's own documented wind/blower noise floor confusing it). Current
assumption, from the cleanest reads obtained: manual index 1 = MIDI 36
(C2), pedal index 1 = MIDI 24 (C1), both simple chromatic runs from
there. VERIFY BY EAR before trusting this for real use — the lowest note
of each device is the most-likely-correct one to check first.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_lakeside_organ_stops.py
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator

SAMPLES_DIR = Path("/Users/Shared/Music/Soundbanks/Soundiron/Soundiron Lakeside Pipe Organ/Samples/close")
DONOR_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler-rack.adg"
OUTPUT_DIR = Path("/Users/Shared/Music/Soundbanks/Soundiron/Soundiron Lakeside Pipe Organ/Instruments (Rebuilt)")

MANUAL_START_NOTE = 36  # C2 — UNVERIFIED, see module docstring
PEDAL_START_NOTE = 24  # C1 — UNVERIFIED, see module docstring

STOP_NAMES = {
    1: "Stop 1 (Wooden, warm-soft)",
    2: "Stop 2 (Wooden + high metal octave)",
    3: "Stop 3 (More metal, unison + high octave)",
    4: "Stop 4 (Full metal, brightest)",
    5: "Stop 5 (Mid-bright, low-end body)",
}

MANUAL_RE = re.compile(r"^pipe_organ_cls_(\d+)_(\d+)\.wav$")
PEDAL_RE = re.compile(r"^pipe_organ_cls_05_pedal_(\d+)\.wav$")


def build_manual_stop(stop_num: int) -> dict:
    """{midi_note: sample_path} for one manual stop (1-5), sustain only."""
    prefix = f"{stop_num:02d}"
    by_note = {}
    for f in SAMPLES_DIR.glob(f"pipe_organ_cls_{prefix}_*.wav"):
        m = MANUAL_RE.match(f.name)
        if not m or m.group(1) != prefix:
            continue
        index = int(m.group(2))
        note = MANUAL_START_NOTE + index - 1
        by_note[note] = f
    return by_note


def build_pedal_stop() -> dict:
    """{midi_note: sample_path} for Stop 6 (Pedalboard), sustain only."""
    by_note = {}
    for f in SAMPLES_DIR.glob("pipe_organ_cls_05_pedal_*.wav"):
        m = PEDAL_RE.match(f.name)
        if not m:
            continue
        index = int(m.group(1))
        note = PEDAL_START_NOTE + index - 1
        by_note[note] = f
    return by_note


def build_stop_sampler(stop_label: str, by_note: dict) -> str:
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

    notes = sorted(by_note.keys())
    for i, note in enumerate(notes):
        # each recorded note is its own exact key (no stretching needed —
        # every semitone in range has a real sample)
        part = creator._create_sample_part(
            index=i,
            sample_path=by_note[note],
            key_min=note,
            key_max=note,
            root_key=note,
        )
        new_parts.append(part)

    print(f"  {stop_label}: {len(notes)} notes, range {notes[0]}-{notes[-1]}")

    # Bare device — extract just the MultiSampler, drop the Instrument
    # Rack wrapper (GroupDevicePreset/InstrumentGroupDevice/BranchPresets).
    root = ET.Element("Ableton", donor_root.attrib)
    root.append(multi_sampler)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def main():
    if not DONOR_TEMPLATE.exists():
        print(f"Error: Donor template not found: {DONOR_TEMPLATE}")
        sys.exit(1)
    if not SAMPLES_DIR.exists():
        print(f"Error: Samples directory not found: {SAMPLES_DIR}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Building manual stops 1-5:")
    for stop_num, stop_label in STOP_NAMES.items():
        by_note = build_manual_stop(stop_num)
        if not by_note:
            print(f"  {stop_label}: no samples found — skipping")
            continue
        xml_string = build_stop_sampler(stop_label, by_note)
        output_path = OUTPUT_DIR / f"Lakeside Organ - Stop {stop_num}.adv"
        encode_adg(xml_string, output_path)
        print(f"  Created: {output_path}")

    print("\nBuilding Stop 6 (Pedalboard):")
    by_note = build_pedal_stop()
    if by_note:
        xml_string = build_stop_sampler("Stop 6 (Pedalboard)", by_note)
        output_path = OUTPUT_DIR / "Lakeside Organ - Stop 6 (Pedalboard).adv"
        encode_adg(xml_string, output_path)
        print(f"  Created: {output_path}")
    else:
        print("  No pedal samples found — skipping")


if __name__ == "__main__":
    main()
