#!/usr/bin/env python3
"""
Batch Process Dual-Chain Drum Racks

Complete pipeline:
1. Trim all drum racks to 16 pads
2. Shift second chain MIDI notes down by 16

Usage:
    python3 batch_process_dual_racks.py input_dir output_dir
    python3 batch_process_dual_racks.py input_dir output_dir --dry-run
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg
from drum_rack.trim_drum_racks_to_16 import find_drum_rack_presets, trim_drum_rack_to_16
from drum_rack.shift_second_chain_midi import find_chain_drum_racks, shift_drum_rack_midi


def process_dual_rack(
    input_path: Path,
    output_path: Path,
    shift_amount: int = -16,
    dry_run: bool = False
) -> dict:
    """
    Process a dual-chain rack: trim to 16 pads, then shift second chain.

    Args:
        input_path: Path to input .adg file
        output_path: Path for output file
        shift_amount: MIDI shift for second chain (default: -16)
        dry_run: If True, analyze only

    Returns:
        Statistics dictionary
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Decode input
    xml_content = decode_adg(input_path)
    root = ET.fromstring(xml_content)

    stats = {
        'racks_trimmed': 0,
        'pads_removed': 0,
        'racks_shifted': 0,
        'pads_shifted': 0
    }

    # Step 1: Trim all drum racks to 16 pads
    drum_presets = find_drum_rack_presets(root)

    for group_preset, drum_device in drum_presets:
        branch_presets = group_preset.find('BranchPresets')
        if branch_presets is not None:
            current_pads = branch_presets.findall('DrumBranchPreset')
            if len(current_pads) > 16:
                removed_count, _ = trim_drum_rack_to_16(group_preset, drum_device, verbose=False)
                stats['racks_trimmed'] += 1
                stats['pads_removed'] += removed_count

    # Step 2: Shift second chain MIDI notes
    chain_drum_racks = find_chain_drum_racks(root)
    chain_1_racks = [r for r in chain_drum_racks if r[2] == 1]

    for group_preset, drum_device, _ in chain_1_racks:
        shifted = shift_drum_rack_midi(group_preset, shift_amount)
        if shifted > 0:
            stats['racks_shifted'] += 1
            stats['pads_shifted'] += shifted

    # Write output if not dry run
    if not dry_run:
        processed_xml = ET.tostring(root, encoding='unicode', xml_declaration=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(processed_xml, output_path)

    return stats


def batch_process_dual_racks(
    input_dir: Path,
    output_dir: Path,
    shift_amount: int = -16,
    dry_run: bool = False
) -> dict:
    """
    Process all .adg files: trim to 16 pads and shift second chain.

    Args:
        input_dir: Root directory to search for .adg files
        output_dir: Output directory (preserves subdirectory structure)
        shift_amount: MIDI shift for second chain (default: -16)
        dry_run: If True, analyze only

    Returns:
        Statistics dictionary
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    if not input_dir.is_dir():
        raise ValueError(f"Input path is not a directory: {input_dir}")

    # Find all .adg files recursively
    adg_files = sorted(input_dir.rglob('*.adg'))

    if len(adg_files) == 0:
        print(f"⚠️  No .adg files found in {input_dir}")
        return {'processed': 0, 'errors': 0}

    print(f"\n{'='*70}")
    print(f"BATCH PROCESS DUAL-CHAIN DRUM RACKS")
    print(f"{'='*70}\n")
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Operations:")
    print(f"  1. Trim all drum racks to 16 pads")
    print(f"  2. Shift second chain MIDI {shift_amount:+d} notes")
    print(f"\nFound {len(adg_files)} .adg files")

    if dry_run:
        print(f"\n{'='*70}")
        print(f"DRY RUN - No files will be modified")
        print(f"{'='*70}")

    print()

    # Create output directory if needed
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Process files
    global_stats = {
        'processed': 0,
        'errors': 0,
        'total_racks_trimmed': 0,
        'total_pads_removed': 0,
        'total_racks_shifted': 0,
        'total_pads_shifted': 0
    }

    for idx, input_path in enumerate(adg_files):
        # Compute relative path to preserve directory structure
        rel_path = input_path.relative_to(input_dir)
        output_path = output_dir / rel_path

        print(f"[{idx+1}/{len(adg_files)}] {rel_path}")

        try:
            # Process the rack
            stats = process_dual_rack(
                input_path,
                output_path,
                shift_amount,
                dry_run
            )

            # Report what was done
            actions = []
            if stats['racks_trimmed'] > 0:
                actions.append(f"trimmed {stats['racks_trimmed']} rack(s), removed {stats['pads_removed']} pad(s)")
            if stats['racks_shifted'] > 0:
                actions.append(f"shifted {stats['racks_shifted']} rack(s), {stats['pads_shifted']} pad(s)")

            if actions:
                print(f"  ✓ {', '.join(actions)}")
                global_stats['processed'] += 1
            else:
                print(f"  - No changes needed")

            global_stats['total_racks_trimmed'] += stats['racks_trimmed']
            global_stats['total_pads_removed'] += stats['pads_removed']
            global_stats['total_racks_shifted'] += stats['racks_shifted']
            global_stats['total_pads_shifted'] += stats['pads_shifted']

        except Exception as e:
            print(f"  ✗ Error: {e}")
            global_stats['errors'] += 1
            import traceback
            traceback.print_exc()
            continue

    # Print summary
    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING {'DRY RUN ' if dry_run else ''}COMPLETE")
    print(f"{'='*70}")
    print(f"Files processed:     {global_stats['processed']}")
    print(f"Errors:              {global_stats['errors']}")
    print(f"\nTrimming:")
    print(f"  Drum racks trimmed:  {global_stats['total_racks_trimmed']}")
    print(f"  Pads removed:        {global_stats['total_pads_removed']}")
    print(f"\nShifting:")
    print(f"  Drum racks shifted:  {global_stats['total_racks_shifted']}")
    print(f"  Pads shifted:        {global_stats['total_pads_shifted']}")

    if not dry_run and global_stats['processed'] > 0:
        print(f"\nOutput directory: {output_dir}")

    return global_stats


def main():
    parser = argparse.ArgumentParser(
        description='Batch process dual-chain racks: trim to 16 pads and shift second chain',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process all files
    python3 batch_process_dual_racks.py input_dir/ output_dir/

    # Preview what would be done
    python3 batch_process_dual_racks.py input_dir/ output_dir/ --dry-run

    # Custom shift amount
    python3 batch_process_dual_racks.py input_dir/ output_dir/ --shift -32

Pipeline:
    1. Trim all drum racks to exactly 16 pads (keeps bottom pads)
    2. Shift second chain MIDI notes down by 16 (default)

Result:
    Chain 1: Pads 1-16 at higher MIDI notes
    Chain 2: Pads 17-32 at lower MIDI notes (shifted down)
        """
    )

    parser.add_argument('input_dir', type=Path, help='Input directory with .adg files')
    parser.add_argument('output_dir', type=Path, help='Output directory')
    parser.add_argument('--shift', type=int, default=-16, help='MIDI shift for chain 2 (default: -16)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')

    args = parser.parse_args()

    try:
        stats = batch_process_dual_racks(
            args.input_dir,
            args.output_dir,
            args.shift,
            args.dry_run
        )

        # Exit with error code if there were errors
        if stats['errors'] > 0:
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
