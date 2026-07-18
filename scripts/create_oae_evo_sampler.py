#!/usr/bin/env python3
"""
Create OAE Evo Sampler — recreates one Ólafur Arnalds "Evolution" (a named,
time-evolving string articulation) as a single bare Sampler device (.adv,
no Instrument Rack wrapper), with Violin 1 + Violin 2 + Viola + Cello all
layered together.

Background: /Users/Shared/Music/Soundbanks/Spitfire/Spitfire Ólafur Arnalds
Evolutions library ships 16 numbered "Evolutions" (Instruments/Instruments
main mics/Individual Evolutions/), each with 5 variants — Violin 1, Violin
2, Viola, Cello, Ensemble. EVO_NAMES below is that list, confirmed against
the library's own patch names. Our extracted samples
(autosampler/output/OAE_Extracted) cover 12 of the 16, split across two
mixes with different coverage (Mix_0: evos 1-3, 10-16; Mix_1: evos 3-5).

Filenames: Island_OliStrings_<voice>_evo<N>_processed_mix_<Note>.wav —
each (voice, evo, note) is exactly one file, no round-robin, no velocity
layers. This is a plain sparse chromatic map, not a Damage/Abbey-Road-style
velocity-layered instrument.

IMPORTANT — note names here use SCIENTIFIC PITCH notation (C4=60), unlike
Damage/Abbey Road's convention elsewhere in this project (C3=60). Verified
against Mix_0/manifest.csv's expected_midi column (e.g. "A4" -> 69, "C2"
-> 36). Using the wrong formula would put every note an octave off — see
note_name_to_midi_scientific() below. Do not reuse
multisample_utils.note_name_to_midi() for this library.

Layering mechanism: each voice's samples are mapped across sparse
KeyRange zones (split at the midpoint between neighboring recorded notes,
stretched to fill the full 0-127 range at the outer edges — see
pitch_zones()). All 4 voices' parts share the same VelocityRange (1-127),
so at any given note there are 4 overlapping parts (one per voice) and
Ableton's Sampler plays them simultaneously — the same overlapping-zone
mechanism this project already uses for velocity layers, just applied on
the key axis instead, with no RoundRobin needed since there's exactly one
sample per (voice, zone).

Usage:
    export PYTHONPATH=src
    python3 scripts/create_oae_evo_sampler.py
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator

LIBRARY_ROOT = Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Spitfire/Olafur Arnalds Evolutions")
DONOR_TEMPLATE = Path(__file__).parent.parent / "templates" / "oae_evo_sampler_template.adv"
OUTPUT_DIR = LIBRARY_ROOT / "Instruments"

# Confirmed against Spitfire's own "Individual Evolutions" patch list.
EVO_NAMES = {
    1: "Subtle - Sul Tasto", 2: "Subtle - Long Wave", 3: "Subtle - Multi Waves",
    4: "Subtle - Tasto to Ord", 5: "Subtle - Tasto to Pont",
    6: "Thrills - Tasto Trem", 7: "Thrills - Tasto Trem Varispeed",
    8: "Thrills - Med to Fast Trem", 9: "Thrills - Hectic 8ve Trills",
    10: "Episodic - Vibrato", 11: "Episodic - Sul Pont", 12: "Episodic - Trem",
    13: "Dissonants - Slow Pitch Bend", 14: "Dissonants - Pitching Episodic",
    15: "Dissonants - Wow Effect", 16: "Dissonants - Pont 8ve Harms",
}

VOICES = [("v1", "Violin 1"), ("v2", "Violin 2"), ("vla", "Viola"), ("cello", "Cello")]

NOTE_OFFSETS = {
    "C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
    "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11,
}
NOTE_RE = re.compile(r"^([A-G]#?)(-?\d+)$")
FILENAME_RE = re.compile(r"^Island_OliStrings_([a-zA-Z0-9]+)_evo(\d+)_processed_mix_([A-G]#?-?\d+)\.wav$")


def note_name_to_midi_scientific(note_name: str) -> int:
    """Scientific pitch notation (C4=60) — confirmed against manifest.csv's
    expected_midi column. NOT this project's usual C3=60 convention."""
    m = NOTE_RE.match(note_name)
    if not m:
        raise ValueError(f"Unrecognized note name: {note_name}")
    letter, octave = m.group(1), int(m.group(2))
    return (octave + 1) * 12 + NOTE_OFFSETS[letter]


MIX_FOLDER_NAMES = ["Mix_0", "Mix_1"]


def find_evo_samples(voice: str, evo: int):
    """{midi_note: sample_path} for one voice's recordings of one evo,
    searching every mix folder (first with data wins) — a single mix isn't
    guaranteed to cover every voice for every evo. Confirmed case: evo 3
    has cello+Violin 1 in Mix_0 but Violin 2+Viola only in Mix_1; neither
    mix alone is complete. Returns (notes_dict, mix_name_used)."""
    for mix_name in MIX_FOLDER_NAMES:
        mix_folder = LIBRARY_ROOT / mix_name
        notes = {}
        for f in mix_folder.glob(f"Island_OliStrings_{voice}_evo{evo}_processed_mix_*.wav"):
            m = FILENAME_RE.match(f.name)
            if m:
                notes[note_name_to_midi_scientific(m.group(3))] = f
        if notes:
            return notes, mix_name
    return {}, None


def pitch_zones(notes) -> list:
    """Contiguous KeyRange zones from sparse recorded notes, split at the
    midpoint between neighbors and stretched to the full 0-127 range at
    the outer edges — same technique as multisample_utils.velocity_bins()
    but on the key axis."""
    notes = sorted(notes)
    zones = []
    for i, note in enumerate(notes):
        key_min = 0 if i == 0 else (notes[i - 1] + note) // 2 + 1
        key_max = 127 if i == len(notes) - 1 else (note + notes[i + 1]) // 2
        zones.append((note, key_min, key_max))
    return zones


def build_evo_sampler(evo: int) -> str:
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
    for voice, voice_label in VOICES:
        by_note, mix_used = find_evo_samples(voice, evo)
        if not by_note:
            print(f"  {voice_label}: no samples found for evo {evo} in any mix — skipping voice")
            continue

        zones = pitch_zones(by_note.keys())
        print(f"  {voice_label}: {len(zones)} notes from {mix_used}, zones {zones[0][1]}-{zones[-1][2]}")
        for note, key_min, key_max in zones:
            part = creator._create_sample_part(
                index=index,
                sample_path=by_note[note],
                key_min=key_min,
                key_max=key_max,
                root_key=note,
            )
            name_elem = part.find("Name")
            name_elem.set("Value", f"{voice_label} - {by_note[note].stem}")
            new_parts.append(part)
            index += 1

    # Bare device — extract just the MultiSampler, drop the Instrument
    # Rack wrapper (GroupDevicePreset/InstrumentGroupDevice/BranchPresets).
    root = ET.Element("Ableton", donor_root.attrib)
    root.append(multi_sampler)

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def main():
    if not DONOR_TEMPLATE.exists():
        print(f"Error: Donor template not found: {DONOR_TEMPLATE}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for evo in sorted(EVO_NAMES):
        evo_name = EVO_NAMES[evo]
        print(f"=== Evo {evo:02d} - {evo_name} ===")
        xml_string = build_evo_sampler(evo)

        output_path = OUTPUT_DIR / f"OAE Evo {evo:02d} - {evo_name.replace(' - ', ' ')}.adv"
        encode_adg(xml_string, output_path)
        print(f"Created: {output_path}\n")
        results[evo] = True
        results[evo] = True

    print("Summary:")
    for evo, ok in results.items():
        print(f"  {'OK' if ok else 'SKIP'}: Evo {evo:02d} - {EVO_NAMES[evo]}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
