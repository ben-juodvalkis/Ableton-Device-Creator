#!/usr/bin/env python3
"""
Merge Drum Racks

Combines two drum racks into a single 32-pad rack:
- Pads 1-16: First 16 pads from Rack A
- Pads 17-32: First 16 pads from Rack B

Usage:
    python3 merge_drum_racks.py rack_a.adg rack_b.adg output.adg
    python3 merge_drum_racks.py rack_a.adg rack_b.adg output.adg --pads-per-rack 8
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def get_drum_pads(xml_root: ET.Element) -> List[ET.Element]:
    """
    Extract and sort drum pads from a drum rack.

    Args:
        xml_root: Parsed XML root element

    Returns:
        List of DrumBranchPreset elements sorted by MIDI note (descending)
    """
    # Find all drum pads
    pads = xml_root.findall('.//DrumBranchPreset')

    # Sort by ReceivingNote DESCENDING (Ableton uses highest note for pad 1)
    pads.sort(
        key=lambda pad: int(pad.find('.//ZoneSettings/ReceivingNote').get('Value')),
        reverse=True
    )

    return pads


def update_pad_midi_note(pad: ET.Element, new_note: int):
    """
    Update the MIDI receiving note for a drum pad.

    Args:
        pad: DrumBranchPreset element
        new_note: New MIDI note number (33-64 for 32-pad rack)
    """
    zone_settings = pad.find('.//ZoneSettings')
    if zone_settings is not None:
        receiving_note = zone_settings.find('ReceivingNote')
        if receiving_note is not None:
            receiving_note.set('Value', str(new_note))


def copy_device_content(source_pad: ET.Element, target_pad: ET.Element):
    """
    Copy device content from source pad to target pad.

    Replaces the DevicePresets section while preserving target's color structure.

    Args:
        source_pad: Source DrumBranchPreset element
        target_pad: Target DrumBranchPreset element (from template)
    """
    # Find DevicePresets in both
    source_devices = source_pad.find('DevicePresets')
    target_devices = target_pad.find('DevicePresets')

    if source_devices is not None and target_devices is not None:
        # Clear target's device presets
        target_devices.clear()
        target_devices.attrib.clear()

        # Copy all children from source
        for child in source_devices:
            target_devices.append(child)

        # Copy attributes
        for key, value in source_devices.attrib.items():
            target_devices.set(key, value)

    # Also copy MixerPreset
    source_mixer = source_pad.find('MixerPreset')
    target_mixer = target_pad.find('MixerPreset')

    if source_mixer is not None and target_mixer is not None:
        target_mixer.clear()
        target_mixer.attrib.clear()

        for child in source_mixer:
            target_mixer.append(child)

        for key, value in source_mixer.attrib.items():
            target_mixer.set(key, value)


def merge_drum_racks(
    rack_a_path: Path,
    rack_b_path: Path,
    output_path: Path,
    pads_per_rack: int = 16
) -> Path:
    """
    Merge two drum racks into a single 32-pad rack.

    Args:
        rack_a_path: Path to first drum rack (.adg)
        rack_b_path: Path to second drum rack (.adg)
        output_path: Path for merged output rack
        pads_per_rack: Number of pads to take from each rack (default: 16)

    Returns:
        Path to created merged rack

    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If racks don't have enough pads or invalid parameters
    """
    # Validate inputs
    if not rack_a_path.exists():
        raise FileNotFoundError(f"Rack A not found: {rack_a_path}")
    if not rack_b_path.exists():
        raise FileNotFoundError(f"Rack B not found: {rack_b_path}")
    if pads_per_rack < 1 or pads_per_rack > 32:
        raise ValueError(f"pads_per_rack must be 1-32, got {pads_per_rack}")

    print(f"\n{'='*70}")
    print(f"MERGING DRUM RACKS")
    print(f"{'='*70}\n")

    # Decode both racks
    print(f"Reading Rack A: {rack_a_path.name}")
    xml_a = decode_adg(rack_a_path)
    root_a = ET.fromstring(xml_a)

    print(f"Reading Rack B: {rack_b_path.name}")
    xml_b = decode_adg(rack_b_path)
    root_b = ET.fromstring(xml_b)

    # Get drum pads from both racks
    pads_a = get_drum_pads(root_a)
    pads_b = get_drum_pads(root_b)

    print(f"\nRack A: {len(pads_a)} pads (using first {min(len(pads_a), pads_per_rack)})")
    print(f"Rack B: {len(pads_b)} pads (using first {min(len(pads_b), pads_per_rack)})")

    # Validate we have enough pads
    if len(pads_a) < pads_per_rack:
        print(f"⚠️  Warning: Rack A has only {len(pads_a)} pads (requested {pads_per_rack})")
    if len(pads_b) < pads_per_rack:
        print(f"⚠️  Warning: Rack B has only {len(pads_b)} pads (requested {pads_per_rack})")

    # Take first N pads from each rack
    selected_pads_a = pads_a[:pads_per_rack]
    selected_pads_b = pads_b[:pads_per_rack]

    # Use Rack A as the base structure
    merged_root = root_a

    # Find the BranchPresets container in merged rack
    preset_container = merged_root.find('.//GroupDevicePreset/BranchPresets')
    if preset_container is None:
        preset_container = merged_root.find('.//BranchPresets')

    if preset_container is None:
        raise ValueError("Could not find BranchPresets in drum rack structure")

    # Clear existing pads
    preset_container.clear()

    # Calculate MIDI note assignments
    # Standard: Pad 1 = MIDI 64, Pad 32 = MIDI 33 (higher MIDI = lower pad number)
    # Shift down 28 pads: Pad 1 = MIDI 92, Pad 32 = MIDI 61 (MIDI notes HIGHER by 28)
    # Note: In drum racks, LOWER pad numbers use HIGHER MIDI notes
    total_pads = len(selected_pads_a) + len(selected_pads_b)
    # Standard: base_note = 65 - total_pads (for pad 32 = MIDI 33)
    # 28 pads lower = MIDI notes HIGHER by 28
    base_note = (65 + 28) - total_pads  # Pad positions 28 lower = MIDI notes 28 higher

    print(f"\nMerging {len(selected_pads_a) + len(selected_pads_b)} pads...")
    print(f"MIDI notes: {base_note + total_pads - 1} → {base_note}")

    # Add pads from Rack A (pads 1-16)
    for i, pad in enumerate(selected_pads_a):
        new_note = (base_note + total_pads - 1) - i
        update_pad_midi_note(pad, new_note)
        preset_container.append(pad)
        print(f"  Pad {i+1:2d}: MIDI {new_note} (from Rack A)")

    # Add pads from Rack B (pads 17-32)
    for i, pad in enumerate(selected_pads_b):
        new_note = (base_note + total_pads - 1) - (len(selected_pads_a) + i)
        update_pad_midi_note(pad, new_note)
        preset_container.append(pad)
        print(f"  Pad {len(selected_pads_a) + i + 1:2d}: MIDI {new_note} (from Rack B)")

    # Convert back to XML string
    merged_xml = ET.tostring(merged_root, encoding='unicode', xml_declaration=True)

    # Encode to .adg
    print(f"\nWriting merged rack: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(merged_xml, output_path)

    print(f"\n{'='*70}")
    print(f"✓ MERGE COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {output_path}")
    print(f"Total pads: {total_pads}")
    print(f"  From Rack A: {len(selected_pads_a)}")
    print(f"  From Rack B: {len(selected_pads_b)}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Merge two drum racks into a single 32-pad rack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Merge two 16-pad racks
    python3 merge_drum_racks.py kick_rack.adg snare_rack.adg merged.adg

    # Merge with custom pad count
    python3 merge_drum_racks.py rack_a.adg rack_b.adg output.adg --pads-per-rack 8

    # Each rack contributes equal pads (default 16)
    # Rack A → Pads 1-16, Rack B → Pads 17-32
        """
    )

    parser.add_argument('rack_a', type=Path, help='First drum rack (.adg file)')
    parser.add_argument('rack_b', type=Path, help='Second drum rack (.adg file)')
    parser.add_argument('output', type=Path, help='Output merged rack path')
    parser.add_argument(
        '--pads-per-rack',
        type=int,
        default=16,
        help='Number of pads to take from each rack (default: 16)'
    )

    args = parser.parse_args()

    try:
        merge_drum_racks(
            args.rack_a,
            args.rack_b,
            args.output,
            args.pads_per_rack
        )

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
