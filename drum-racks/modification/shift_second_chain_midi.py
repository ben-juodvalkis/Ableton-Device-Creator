#!/usr/bin/env python3
"""
Shift Second Chain Drum Rack MIDI Notes

In a dual-chain rack, shifts all MIDI notes in the second chain's drum rack up by 16.
This prevents overlap between the two drum racks.

Chain 1: Pads remain at original MIDI notes
Chain 2: All pads shift up by 16 MIDI notes

Usage:
    python3 shift_second_chain_midi.py input.adg output.adg
    python3 shift_second_chain_midi.py input.adg output.adg --dry-run
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


def find_chain_drum_racks(xml_root: ET.Element) -> List[Tuple[ET.Element, ET.Element, int]]:
    """
    Find all drum racks organized by chain.

    Returns:
        List of (GroupDevicePreset, DrumGroupDevice, chain_index) tuples
    """
    results = []

    # Find the outer InstrumentGroupDevice (the dual-chain rack)
    outer_rack = xml_root.find('.//InstrumentGroupDevice')
    if outer_rack is None:
        return results

    # Find its BranchPresets (the chains)
    outer_group_preset = xml_root.find('.//GroupDevicePreset')
    outer_branch_presets = outer_group_preset.find('BranchPresets')

    if outer_branch_presets is None:
        return results

    # Get all chains
    chains = outer_branch_presets.findall('InstrumentBranchPreset')

    # For each chain, find drum racks
    for chain_idx, chain in enumerate(chains):
        # Find all GroupDevicePresets in this chain that contain DrumGroupDevices
        device_presets = chain.find('DevicePresets')
        if device_presets is not None:
            # Search recursively for all GroupDevicePresets containing DrumGroupDevices
            for group_preset in device_presets.findall('.//GroupDevicePreset'):
                drum_device = group_preset.find('.//DrumGroupDevice')
                if drum_device is not None:
                    results.append((group_preset, drum_device, chain_idx))

    return results


def shift_drum_rack_midi(group_preset: ET.Element, shift_amount: int) -> int:
    """
    Shift all MIDI notes in a drum rack by a specified amount.

    Args:
        group_preset: The GroupDevicePreset containing the drum rack
        shift_amount: Amount to shift MIDI notes (positive = up, negative = down)

    Returns:
        Number of pads shifted
    """
    # Find BranchPresets (sibling to Device in GroupDevicePreset)
    branch_presets = group_preset.find('BranchPresets')

    if branch_presets is None:
        return 0

    # Get all drum pads
    pads = branch_presets.findall('DrumBranchPreset')

    if len(pads) == 0:
        return 0

    # Shift each pad's ReceivingNote
    for pad in pads:
        receiving_note = pad.find('.//ReceivingNote')
        if receiving_note is not None:
            current_note = int(receiving_note.get('Value'))
            new_note = current_note + shift_amount
            receiving_note.set('Value', str(new_note))

    return len(pads)


def shift_second_chain_midi(
    input_path: Path,
    output_path: Path,
    shift_amount: int = -16,
    dry_run: bool = False,
    quiet: bool = False
) -> dict:
    """
    Shift MIDI notes in second chain's drum rack(s).

    Args:
        input_path: Path to input dual-chain rack
        output_path: Path for output file
        shift_amount: MIDI notes to shift (default: -16 for down)
        dry_run: If True, analyze only without modifying
        quiet: If True, suppress detailed output

    Returns:
        Statistics dictionary
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not quiet:
        print(f"\n{'='*70}")
        print(f"SHIFT SECOND CHAIN DRUM RACK MIDI NOTES")
        print(f"{'='*70}\n")
        print(f"Input: {input_path.name}")
        print(f"Shift amount: {shift_amount:+d} MIDI notes")

        if dry_run:
            print("DRY RUN - No changes will be made\n")

    # Decode input
    xml_content = decode_adg(input_path)
    root = ET.fromstring(xml_content)

    # Find drum racks by chain
    chain_drum_racks = find_chain_drum_racks(root)

    if len(chain_drum_racks) == 0:
        if not quiet:
            print("⚠️  No drum racks found in file")
        return {'chains_found': 0, 'racks_shifted': 0, 'pads_shifted': 0}

    # Group by chain
    chain_0_racks = [r for r in chain_drum_racks if r[2] == 0]
    chain_1_racks = [r for r in chain_drum_racks if r[2] == 1]

    if not quiet:
        print(f"Found:")
        print(f"  Chain 1 (index 0): {len(chain_0_racks)} drum rack(s)")
        print(f"  Chain 2 (index 1): {len(chain_1_racks)} drum rack(s)")
        print()

    stats = {
        'chains_found': len(set(r[2] for r in chain_drum_racks)),
        'racks_shifted': 0,
        'pads_shifted': 0
    }

    # Process chain 1 racks (no shift)
    if chain_0_racks and not quiet:
        print("Chain 1 (no shift):")
        for group_preset, drum_device, _ in chain_0_racks:
            user_name = drum_device.find('UserName')
            drum_name = user_name.get('Value') if user_name is not None else 'Unknown'

            branch_presets = group_preset.find('BranchPresets')
            if branch_presets is not None:
                pads = branch_presets.findall('DrumBranchPreset')
                print(f"  - '{drum_name}' ({len(pads)} pads) - no change")
        print()

    # Process chain 2 racks (shift by shift_amount)
    if chain_1_racks:
        if not quiet:
            print(f"Chain 2 (shift {shift_amount:+d} MIDI notes):")

        for group_preset, drum_device, _ in chain_1_racks:
            user_name = drum_device.find('UserName')
            drum_name = user_name.get('Value') if user_name is not None else 'Unknown'

            branch_presets = group_preset.find('BranchPresets')
            if branch_presets is not None:
                pads = branch_presets.findall('DrumBranchPreset')

                # Get MIDI range before shift
                if pads:
                    midi_notes = []
                    for pad in pads:
                        rn = pad.find('.//ReceivingNote')
                        if rn is not None:
                            midi_notes.append(int(rn.get('Value')))

                    if not quiet:
                        old_range = f"{min(midi_notes)}-{max(midi_notes)}" if midi_notes else "N/A"
                        new_range = f"{min(midi_notes) + shift_amount}-{max(midi_notes) + shift_amount}" if midi_notes else "N/A"

                        print(f"  - '{drum_name}' ({len(pads)} pads)")
                        print(f"      Old MIDI range: {old_range}")
                        print(f"      New MIDI range: {new_range}")

                    if not dry_run:
                        shifted = shift_drum_rack_midi(group_preset, shift_amount)
                        stats['racks_shifted'] += 1
                        stats['pads_shifted'] += shifted
                    else:
                        stats['racks_shifted'] += 1
                        stats['pads_shifted'] += len(pads)

        if not quiet:
            print()

    if not dry_run and stats['racks_shifted'] > 0:
        # Convert to XML and encode
        shifted_xml = ET.tostring(root, encoding='unicode', xml_declaration=True)

        if not quiet:
            print(f"Writing shifted rack: {output_path.name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(shifted_xml, output_path)

    if not quiet:
        print(f"{'='*70}")
        print(f"{'DRY RUN - ' if dry_run else ''}SUMMARY")
        print(f"{'='*70}")
        print(f"Chains found:    {stats['chains_found']}")
        print(f"Racks shifted:   {stats['racks_shifted']} (chain 2 only)")
        print(f"Pads shifted:    {stats['pads_shifted']}")

        if not dry_run and stats['racks_shifted'] > 0:
            print(f"\nOutput: {output_path}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Shift MIDI notes in second chain drum rack(s) up by 16',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Shift second chain up by 16
    python3 shift_second_chain_midi.py input.adg output.adg

    # Preview changes
    python3 shift_second_chain_midi.py input.adg output.adg --dry-run

    # Custom shift amount
    python3 shift_second_chain_midi.py input.adg output.adg --shift 32

Result:
    Chain 1: Pads remain at original MIDI notes (e.g., 60-76)
    Chain 2: Pads shift up (e.g., 60-76 becomes 76-92)

This allows both drum racks to be played on a 32-pad controller without overlap.
        """
    )

    parser.add_argument('input', type=Path, help='Input dual-chain rack (.adg)')
    parser.add_argument('output', type=Path, help='Output file')
    parser.add_argument('--shift', type=int, default=16, help='MIDI shift amount (default: 16)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')

    args = parser.parse_args()

    try:
        shift_second_chain_midi(
            args.input,
            args.output,
            args.shift,
            args.dry_run
        )

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
