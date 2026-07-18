#!/usr/bin/env python3
"""
Create Moonkit Racks — a Damage-style Drum Rack per kit across Soniccouture's
Moonkits collections (LIBRARY_ROOTS — Jazzy_Brushes's 27 kits and
Moonkits/Moonkits's 18, one rack each; add more roots here if more
collections show up, they all share the same convention).

Source: <KitName>/<KitName>_<Piece>_<Note>_<MidiNum>_v<Velocity>_rr<N>.wav
— same convention as the standalone Aquarium_Groove kit this project
already built (that kit turns out to be one of 27 here). The MIDI number
is embedded directly (no note-name convention to reverse-engineer). Piece
names repeat at different notes (Snare at up to 3 notes, Floor_Tom at up
to 4, Tom at up to 3) — each (piece, note) pair is its own distinct
playable element, 15-23 per kit depending on the kit. 10 velocity layers
(1/15/29/43/57/71/85/99/113/127, same ladder as Damage), up to 4
round-robin takes.

Unlike the original single-kit Aquarium_Groove script (which reused all
32 of the donor rack's pre-built pads and left the rest with the donor's
default empty Sampler), this clones the donor's pad dynamically — one
clone per real instrument, same technique as the Abbey Road racks — so a
kit with 19 instruments produces a 19-pad rack with zero empty-chain
pads, not 19 filled + 13 dead ones.

One rack per kit (not combined) — each gets however many pads it
naturally has, notes counting down from 92 (this project's usual pad-1
convention: first instrument, sorted by its own source note ascending,
lands on the highest pad note).

Usage:
    export PYTHONPATH=src
    python3 scripts/create_moonkit_racks.py
"""

import copy
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, velocity_bins

LIBRARY_ROOTS = [
    Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Soniccouture/Moonkits/Jazzy_Brushes"),
    Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Soniccouture/Moonkits/Moonkits"),
    Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Soniccouture/Moonkits/Urban_and_Contemporary"),
]
DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler_drum_rack_template.adg"

PAD_ROOT_NOTE = 60  # C3 — matches every pad's fixed SendingNote, same as the Damage workflow
FIRST_NOTE = 92  # highest note used — same "pad 1" convention as the rest of this project

# DocumentColorIndex per piece family — same reused, validated indices as
# the Damage/Abbey Road/Aquarium Groove workflows.
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


def discover_kits(library_root: Path) -> dict:
    return {p.name: p for p in sorted(library_root.iterdir()) if p.is_dir() and p.name != "Drum Racks"}


def parse_kit(kit_name: str, kit_folder: Path) -> dict:
    """{(piece, midi_note): {velocity_center: [sample_paths]}}"""
    pattern = re.compile(rf"^{re.escape(kit_name)}_(.+)_[A-G]#?-?\d+_(\d+)_v(\d+)_rr(\d+)\.wav$", re.IGNORECASE)
    instruments = {}
    for f in kit_folder.glob("*.wav"):
        m = pattern.match(f.name)
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


def build_kit(kit_name: str, kit_folder: Path, donor_pad: ET.Element, creator: SamplerCreator, output_dir: Path) -> bool:
    output_path = output_dir / f"Drum_Rack_{kit_name.replace(' ', '_')}.adg"
    print(f"\n=== {kit_name} ===")

    instruments = parse_kit(kit_name, kit_folder)
    if not instruments:
        print("  No usable samples for this kit — skipping.")
        return False

    ordered = sorted(instruments.items(), key=lambda kv: kv[0][1])  # by source note ascending
    print(f"  {len(ordered)} instruments, notes {FIRST_NOTE - len(ordered) + 1}-{FIRST_NOTE}")

    rack_xml = decode_adg(DRUM_RACK_TEMPLATE)
    rack_root = ET.fromstring(rack_xml)
    branch_presets = rack_root.find(".//BranchPresets")
    for old_pad in list(branch_presets):
        branch_presets.remove(old_pad)

    for idx, ((piece, source_note), layers) in enumerate(ordered):
        note = FIRST_NOTE - idx

        pad = copy.deepcopy(donor_pad)
        pad.set("Id", str(idx))

        recv = pad.find(".//ZoneSettings/ReceivingNote")
        recv.set("Value", str(note))

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

        branch_presets.append(pad)

        layer_summary = ", ".join(f"V{c}:{len(layers[c])}" for c, _, _ in velocity_bins(layers.keys()))
        print(f"  Note {note}: {piece} (source note {source_note}) — {layer_summary}")

    xml_string = ET.tostring(rack_root, encoding="unicode", xml_declaration=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    encode_adg(xml_string, output_path)
    print(f"  Created: {output_path} ({len(ordered)} pads)")
    return True


def main():
    if not DRUM_RACK_TEMPLATE.exists():
        print(f"Error: Drum rack template not found: {DRUM_RACK_TEMPLATE}")
        sys.exit(1)

    donor_xml = decode_adg(DRUM_RACK_TEMPLATE)
    donor_root = ET.fromstring(donor_xml)
    donor_pad = copy.deepcopy(donor_root.find(".//BranchPresets/DrumBranchPreset"))
    if donor_pad is None:
        raise ValueError("Donor template missing a DrumBranchPreset to clone")

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)

    results = {}
    for library_root in LIBRARY_ROOTS:
        print(f"\n########## {library_root.name} ##########")
        kits = discover_kits(library_root)
        print(f"Discovered {len(kits)} kits")
        output_dir = library_root / "Drum Racks"

        for kit_name, kit_folder in kits.items():
            results[f"{library_root.name}/{kit_name}"] = build_kit(kit_name, kit_folder, donor_pad, creator, output_dir)

    print("\nSummary:")
    for kit_name, ok in results.items():
        print(f"  {'OK' if ok else 'FAILED'}: {kit_name}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
