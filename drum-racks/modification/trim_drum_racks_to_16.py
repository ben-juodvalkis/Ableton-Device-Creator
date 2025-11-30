#!/usr/bin/env python3
"""
Trim Drum Racks to 16 Pads

Ensures all drum racks in a file have exactly 16 pads by removing pads from the top
(highest MIDI notes = highest pad numbers).

Keeps pads 1-16 (highest MIDI notes), removes pads 17+ (lowest MIDI notes).

Usage:
    python3 trim_drum_racks_to_16.py input.adg output.adg
    python3 trim_drum_racks_to_16.py input.adg output.adg --dry-run
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def find_drum_rack_presets(xml_root: ET.Element) -> List[Tuple[ET.Element, ET.Element]]:
    """
    Find all GroupDevicePresets that contain DrumGroupDevices.

    Returns list of (GroupDevicePreset, DrumGroupDevice) tuples.
    """
    results = []

    # Find all GroupDevicePresets
    for group_preset in xml_root.findall('.//GroupDevicePreset'):
        # Check if it contains a DrumGroupDevice
        drum_device = group_preset.find('.//DrumGroupDevice')
        if drum_device is not None:
            results.append((group_preset, drum_device))

    return results


def get_pad_name(pad: ET.Element) -> str:
    """Extract a readable name from a drum pad."""
    # Try DeviceName
    device_name = pad.find('.//DeviceName')
    if device_name is not None:
        name = device_name.get('Value')
        if name:
            return name

    # Try sample file name
    file_ref = pad.find('.//FileRef/Name')
    if file_ref is not None:
        name = file_ref.get('Value', '')
        if name:
            return name.replace('.wav', '').replace('.aif', '').replace('.aiff', '')

    return "(empty)"


def get_pads_to_remove(group_preset: ET.Element, drum_device: ET.Element) -> List[Tuple[ET.Element, int, str]]:
    """
    Get list of pads that would be removed to trim to 16.

    Returns:
        List of (pad_element, midi_note, pad_name) tuples for pads 17+
    """
    branch_presets = group_preset.find('BranchPresets')
    if branch_presets is None:
        return []

    pads = branch_presets.findall('DrumBranchPreset')
    if len(pads) <= 16:
        return []

    # Sort by ReceivingNote DESCENDING (highest MIDI = pad 1)
    pads_with_midi = []
    for pad in pads:
        receiving_note = pad.find('.//ReceivingNote')
        if receiving_note is not None:
            midi_note = int(receiving_note.get('Value'))
            pads_with_midi.append((pad, midi_note))

    pads_with_midi.sort(key=lambda x: x[1], reverse=True)

    # Pads to remove are 17+ (indices 16+)
    pads_to_remove = []
    for idx, (pad, midi) in enumerate(pads_with_midi[16:], start=17):
        name = get_pad_name(pad)
        pads_to_remove.append((pad, midi, name))

    return pads_to_remove


def trim_drum_rack_to_16(group_preset: ET.Element, drum_device: ET.Element, verbose: bool = False) -> Tuple[int, List[str]]:
    """
    Trim a drum rack to exactly 16 pads.

    Keeps pads 1-16 (highest MIDI notes), removes pads 17+ (lowest MIDI notes).

    Args:
        group_preset: The GroupDevicePreset containing the drum rack
        drum_device: The DrumGroupDevice element
        verbose: If True, return names of removed pads

    Returns:
        Tuple of (number of pads removed, list of removed pad names)
    """
    # Find BranchPresets (sibling to Device in GroupDevicePreset)
    branch_presets = group_preset.find('BranchPresets')

    if branch_presets is None:
        return 0, []

    # Get all drum pads
    pads = branch_presets.findall('DrumBranchPreset')

    if len(pads) <= 16:
        return 0, []  # Already 16 or fewer

    # Sort by ReceivingNote DESCENDING (highest MIDI = pad 1)
    pads_with_midi = []
    for pad in pads:
        receiving_note = pad.find('.//ReceivingNote')
        if receiving_note is not None:
            midi_note = int(receiving_note.get('Value'))
            pads_with_midi.append((pad, midi_note))

    pads_with_midi.sort(key=lambda x: x[1], reverse=True)

    # Keep first 16 (pads 1-16), remove the rest (pads 17+)
    pads_to_remove = pads_with_midi[16:]

    # Get names of removed pads if verbose
    removed_names = []
    if verbose:
        for pad, midi in pads_to_remove:
            name = get_pad_name(pad)
            removed_names.append(f"Pad {len(pads_with_midi) - pads_to_remove.index((pad, midi))}: {name} (MIDI {midi})")

    # Remove pads from BranchPresets
    for pad, midi in pads_to_remove:
        branch_presets.remove(pad)

    return len(pads_to_remove), removed_names


def trim_drum_racks_to_16(
    input_path: Path,
    output_path: Path,
    dry_run: bool = False,
    quiet: bool = False
) -> dict:
    """
    Trim all drum racks in a file to exactly 16 pads.

    Args:
        input_path: Path to input .adg file
        output_path: Path for output file
        dry_run: If True, analyze only without modifying
        quiet: If True, suppress detailed output

    Returns:
        Statistics dictionary
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not quiet:
        print(f"\n{'='*70}")
        print(f"TRIM DRUM RACKS TO 16 PADS")
        print(f"{'='*70}\n")
        print(f"Input: {input_path.name}")

        if dry_run:
            print("DRY RUN - No changes will be made\n")

    # Decode input
    xml_content = decode_adg(input_path)
    root = ET.fromstring(xml_content)

    # Find all drum rack presets
    drum_presets = find_drum_rack_presets(root)

    if not quiet:
        print(f"Found {len(drum_presets)} drum rack(s)\n")

    stats = {
        'racks_found': len(drum_presets),
        'racks_trimmed': 0,
        'total_pads_removed': 0,
        'racks_unchanged': 0
    }

    for i, (group_preset, drum_device) in enumerate(drum_presets):
        user_name = drum_device.find('UserName')
        drum_name = user_name.get('Value') if user_name is not None else 'Unknown'

        # Count current pads
        branch_presets = group_preset.find('BranchPresets')
        if branch_presets is not None:
            current_pads = branch_presets.findall('DrumBranchPreset')
            num_pads = len(current_pads)

            if not quiet:
                print(f"Drum Rack {i+1}: '{drum_name}'")
                print(f"  Current pads: {num_pads}")

            if num_pads <= 16:
                if not quiet:
                    print(f"  ✓ Already ≤16 pads, no changes needed")
                stats['racks_unchanged'] += 1
            else:
                pads_to_remove_count = num_pads - 16
                if not quiet:
                    print(f"  → Will remove {pads_to_remove_count} pad(s) from top (highest pad numbers)")

                # Get list of pads that would be removed
                pads_to_remove_info = get_pads_to_remove(group_preset, drum_device)

                if pads_to_remove_info and not quiet:
                    print(f"  Removing:")
                    for pad_elem, midi, name in pads_to_remove_info:
                        print(f"    - {name} (MIDI {midi})")

                if not dry_run:
                    # Actually remove the pads
                    removed_count, _ = trim_drum_rack_to_16(group_preset, drum_device, verbose=False)
                    if not quiet:
                        print(f"  ✓ Removed {removed_count} pad(s)")
                    stats['racks_trimmed'] += 1
                    stats['total_pads_removed'] += removed_count
                else:
                    stats['racks_trimmed'] += 1
                    stats['total_pads_removed'] += pads_to_remove_count

            if not quiet:
                print()

    if not dry_run and stats['racks_trimmed'] > 0:
        # Convert to XML and encode
        trimmed_xml = ET.tostring(root, encoding='unicode', xml_declaration=True)

        if not quiet:
            print(f"Writing trimmed rack: {output_path.name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(trimmed_xml, output_path)

    if not quiet:
        print(f"{'='*70}")
        print(f"{'DRY RUN - ' if dry_run else ''}SUMMARY")
        print(f"{'='*70}")
        print(f"Racks found:     {stats['racks_found']}")
        print(f"Racks trimmed:   {stats['racks_trimmed']}")
        print(f"Racks unchanged: {stats['racks_unchanged']}")
        print(f"Pads removed:    {stats['total_pads_removed']}")

        if not dry_run and stats['racks_trimmed'] > 0:
            print(f"\nOutput: {output_path}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Trim all drum racks in a file to exactly 16 pads',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Trim drum racks
    python3 trim_drum_racks_to_16.py input.adg output.adg

    # Preview what would be trimmed
    python3 trim_drum_racks_to_16.py input.adg output.adg --dry-run

Strategy:
    - Keeps pads 1-16 (highest MIDI notes = bottom pads on controller)
    - Removes pads 17+ (lowest MIDI notes = top pads on controller)
    - Preserves kick, snare, clap, hats on lower pads
    - Removes melodic/auxiliary elements from upper pads
        """
    )

    parser.add_argument('input', type=Path, help='Input .adg file')
    parser.add_argument('output', type=Path, help='Output .adg file')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')

    args = parser.parse_args()

    try:
        trim_drum_racks_to_16(
            args.input,
            args.output,
            args.dry_run
        )

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
