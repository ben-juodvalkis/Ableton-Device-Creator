#!/usr/bin/env python3
"""
Create Stroh Violin Samplers — three bare Sampler devices (.adv, no rack
wrapper), one per articulation, from Impact Soundworks' Stroh Violin raw
extracted samples.

Source: StrohViolin_Extracted/strohgeige <articulation-specific name>.wav.
Three pitched articulations, each sparsely recorded (not every semitone —
mostly whole-tone spaced) and stretched to fill the gaps via
multisample_utils.pitch_zones(), same technique as Alt Strings Pizz:

- Sustain:   "strohgeige <Note> <ff|mf|p|pp> RR<N>.wav" — 21 notes, 3
  dynamic layers (occasionally pp substitutes for p at the extremes) each
  with ~2 round-robin takes. Dynamics have no numeric velocity in the
  filename, so they're mapped to fixed velocity centers (DYNAMIC_VELOCITY)
  and binned the same way Damage/Aquarium's numeric velocities are.
- Pizzicato: "strohgeige pizz <Note>_<NNN>.wav" — 20 notes, no dynamics,
  4-7 round-robin takes per note (single velocity bin spanning 1-127).
- Spiccato:  "strohgeige spicc <Note> [empty] uncut_<NNN>[ (n)].wav" — 24
  notes, no dynamics, 15-22 round-robin takes per note. "empty uncut" vs
  "uncut" is NOT a per-note choice: each note uses exactly one label
  exclusively, so both are parsed as the same round-robin group.

NOT included (see conversation — explicitly scoped out for this pass):
- Release-trigger samples (7 of the 21 sustain notes have a matching
  "<Note> Release.wav") — same open question as the Lakeside Pipe Organ:
  no confirmed way to wire a genuine release-trigger zone into Ableton's
  Sampler yet.
- The unpitched "dirt"/"sust dirt" one-shots (~33 files, a noise/grit
  texture layer, not a keyed articulation).
- IR Samples/Grammophon 4.wav (a convolution reverb impulse response, not
  an instrument sample).

Note names use German sharp spelling (Cis/Dis/Fis = C#/D#/F#) with
scientific pitch octave numbering (C4=60) — confirmed empirically: mapping
this way puts pizzicato+spiccato's combined notes on a clean, continuous,
non-overlapping ladder from C1 to B4 with no huge gaps or reversals; the
project's usual C3=60 convention did not fit anywhere near as cleanly.
On top of that, GLOBAL_TRANSPOSE shifts everything up 2 octaves (+24) —
confirmed by ear against the first build (what played at C0 should play
at C2).

Usage:
    export PYTHONPATH=src
    python3 scripts/create_stroh_violin_samplers.py
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, pitch_zones

SOURCE_DIR = Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Impact Soundworks/StrohViolin_Extracted")
DONOR_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler-rack.adg"
OUTPUT_DIR = SOURCE_DIR.parent / "Instruments"

NOTE_OFFSETS = {
    "C": 0, "Cis": 1, "D": 2, "Dis": 3, "E": 4, "F": 5,
    "Fis": 6, "G": 7, "Gis": 8, "A": 9, "Ais": 10, "B": 11,
}
NOTE_RE = re.compile(r"^([A-Za-z]+)(-?\d+)$")

SUSTAIN_RE = re.compile(r"^strohgeige ([A-Za-z]+\d+) (ff|mf|p|pp) RR(\d+)\.wav$", re.IGNORECASE)
PIZZ_RE = re.compile(r"^strohgeige pizz ([A-Za-z]+\d+)_(\d+)\.wav$", re.IGNORECASE)
SPICC_RE = re.compile(r"^strohgeige spicc ([A-Za-z]+\d+) (?:empty uncut|uncut)_(\d+)(?: \(\d+\))?\.wav$", re.IGNORECASE)

DYNAMIC_VELOCITY = {"pp": 16, "p": 48, "mf": 85, "ff": 120}
SINGLE_LAYER_VELOCITY = 64  # arbitrary center — pizz/spicc have no dynamics, one bin spans 1-127

# Confirmed by ear against the first build: what played at C0 should play
# at C2, i.e. +2 octaves. Applied to every parsed note before pitch_zones()
# so the stretched top/bottom edges still snap to 127/0 after the shift
# (full keyboard coverage preserved, not just the mapped notes moved).
GLOBAL_TRANSPOSE = 24


def note_name_to_midi_scientific(note_name: str) -> int:
    """Scientific pitch notation (C4=60), German sharp spelling — see
    module docstring for why this convention was chosen."""
    m = NOTE_RE.match(note_name)
    if not m:
        raise ValueError(f"Unrecognized note name: {note_name}")
    letter, octave = m.group(1), int(m.group(2))
    return (octave + 1) * 12 + NOTE_OFFSETS[letter] + GLOBAL_TRANSPOSE


def parse_sustain(folder: Path) -> dict:
    """{midi_note: {velocity_center: [sample_paths]}}"""
    by_note = {}
    for f in folder.glob("*.wav"):
        m = SUSTAIN_RE.match(f.name)
        if not m:
            continue
        note = note_name_to_midi_scientific(m.group(1))
        velocity = DYNAMIC_VELOCITY[m.group(2).lower()]
        by_note.setdefault(note, {}).setdefault(velocity, []).append(f)
    return by_note


def parse_single_layer(folder: Path, pattern: re.Pattern) -> dict:
    """{midi_note: {SINGLE_LAYER_VELOCITY: [sample_paths]}} — round robin
    only, no dynamics."""
    by_note = {}
    for f in folder.glob("*.wav"):
        m = pattern.match(f.name)
        if not m:
            continue
        note = note_name_to_midi_scientific(m.group(1))
        by_note.setdefault(note, {}).setdefault(SINGLE_LAYER_VELOCITY, []).append(f)
    return by_note


ARTICULATIONS = [
    ("Sustain", parse_sustain),
    ("Pizzicato", lambda folder: parse_single_layer(folder, PIZZ_RE)),
    ("Spiccato", lambda folder: parse_single_layer(folder, SPICC_RE)),
]


def build_sampler(name: str, by_note: dict) -> None:
    total_files = sum(len(v) for layers in by_note.values() for v in layers.values())
    print(f"\n=== {name} ===")
    print(f"  {len(by_note)} recorded notes, {total_files} samples total")

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
    print(f"  Built {index} sample parts across {len(by_note)} notes")

    # Bare device — extract just the MultiSampler, drop the Instrument
    # Rack wrapper (GroupDevicePreset/InstrumentGroupDevice/BranchPresets).
    root = ET.Element("Ableton", donor_root.attrib)
    root.append(multi_sampler)
    xml_string = ET.tostring(root, encoding="unicode", xml_declaration=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"Stroh Violin - {name}.adv"
    encode_adg(xml_string, output_path)
    print(f"  Created: {output_path}")


def main():
    if not DONOR_TEMPLATE.exists():
        print(f"Error: Donor template not found: {DONOR_TEMPLATE}")
        sys.exit(1)
    if not SOURCE_DIR.exists():
        print(f"Error: Source directory not found: {SOURCE_DIR}")
        sys.exit(1)

    print(f"Scanning: {SOURCE_DIR}")
    for name, parse_fn in ARTICULATIONS:
        by_note = parse_fn(SOURCE_DIR)
        if not by_note:
            print(f"\n=== {name} ===\n  No samples found — skipping")
            continue
        build_sampler(name, by_note)


if __name__ == "__main__":
    main()
