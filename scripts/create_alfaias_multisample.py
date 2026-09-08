#!/usr/bin/env python3
"""
Create Alfaias Multisample — Single-key velocity-layered round-robin Sampler.

Source folder naming convention: "Alfaias-<Note>-V<velocity>-<RRid>.wav"
(e.g. "Alfaias-C#4-V29-BRWQ.wav"). All samples share one root note (C#4) and
are grouped into velocity layers; samples within a layer are round-robin
alternates.

Velocity layer centers found in the source folder: 1, 15, 29, 43, 57, 71, 85,
99, 113, 127. Bin boundaries are the midpoints between adjacent centers, so
the full 1-127 velocity range is covered with no gaps or overlaps. Round
robin is enabled via the MultiSampleMap's native RoundRobin/RoundRobinMode
flags (Cyclic), so Ableton auto-alternates among samples that share the same
key + velocity range.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_alfaias_multisample.py
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, parse_velocity_layers, velocity_bins

SOURCE_DIR = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Heavyocity/Damage/Ethnic/Alfaias/Close"
)
TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "sampler-rack.adg"
OUTPUT_PATH = Path(__file__).parent.parent / "output" / "Alfaias_Close_Multisample.adg"


def build_multisample(root_note: int, layers: dict) -> str:
    creator = SamplerCreator(template=TEMPLATE_PATH)
    template_xml = decode_adg(TEMPLATE_PATH)

    root = ET.fromstring(template_xml)
    sample_map = root.find(".//MultiSampleMap")
    if sample_map is None:
        raise ValueError("Template missing MultiSampleMap element")

    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")

    for center, vel_min, vel_max in velocity_bins(layers.keys()):
        print(f"  V{center}: velocity {vel_min}-{vel_max}, {len(layers[center])} round-robin samples")
    for part in build_sample_parts(creator, layers, root_note):
        new_parts.append(part)

    enable_round_robin(sample_map)

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def main():
    if not TEMPLATE_PATH.exists():
        print(f"Error: Template not found: {TEMPLATE_PATH}")
        sys.exit(1)

    if not SOURCE_DIR.exists():
        print(f"Error: Source directory not found: {SOURCE_DIR}")
        sys.exit(1)

    print(f"Scanning: {SOURCE_DIR}")
    root_note, layers = parse_velocity_layers(SOURCE_DIR)
    total_samples = sum(len(v) for v in layers.values())
    print(f"Root note: {root_note} (MIDI), {len(layers)} velocity layers, {total_samples} samples\n")

    xml_string = build_multisample(root_note, layers)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(xml_string, OUTPUT_PATH)
    print(f"\nCreated: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
