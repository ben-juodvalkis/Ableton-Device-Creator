#!/usr/bin/env python3
"""
Batch Shift Second Chain MIDI

Process all .adg files in a directory (recursively) and shift the second chain's
drum rack MIDI notes down by 16.

Usage:
    python3 batch_shift_second_chain.py input_dir output_dir
    python3 batch_shift_second_chain.py input_dir output_dir --dry-run
    python3 batch_shift_second_chain.py input_dir output_dir --shift -32
"""

import argparse
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from drum_rack.shift_second_chain_midi import shift_second_chain_midi


def batch_shift_second_chain(
    input_dir: Path,
    output_dir: Path,
    shift_amount: int = -16,
    dry_run: bool = False
) -> dict:
    """
    Process all .adg files recursively, shifting second chain MIDI notes.

    Args:
        input_dir: Root directory to search for .adg files
        output_dir: Output directory (preserves subdirectory structure)
        shift_amount: MIDI shift amount (default: -16)
        dry_run: If True, analyze only without modifying

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
        return {'processed': 0, 'skipped': 0, 'errors': 0}

    print(f"\n{'='*70}")
    print(f"BATCH SHIFT SECOND CHAIN MIDI NOTES")
    print(f"{'='*70}\n")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Shift amount: {shift_amount:+d} MIDI notes")
    print(f"Found {len(adg_files)} .adg files")

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
        'skipped': 0,
        'errors': 0,
        'total_pads_shifted': 0,
        'racks_shifted': 0
    }

    for idx, input_path in enumerate(adg_files):
        # Compute relative path to preserve directory structure
        rel_path = input_path.relative_to(input_dir)
        output_path = output_dir / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[{idx+1}/{len(adg_files)}] {rel_path}")

        try:
            # Shift the rack (quiet mode for batch processing)
            stats = shift_second_chain_midi(
                input_path,
                output_path,
                shift_amount,
                dry_run,
                quiet=True
            )

            if stats['racks_shifted'] > 0:
                print(f"  ✓ Shifted {stats['racks_shifted']} rack(s), {stats['pads_shifted']} pad(s)")
                global_stats['processed'] += 1
                global_stats['racks_shifted'] += stats['racks_shifted']
                global_stats['total_pads_shifted'] += stats['pads_shifted']
            else:
                print(f"  - No second chain or no drum racks to shift")
                global_stats['skipped'] += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            global_stats['errors'] += 1
            continue

    # Print summary
    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING {'DRY RUN ' if dry_run else ''}COMPLETE")
    print(f"{'='*70}")
    print(f"Files processed:     {global_stats['processed']}")
    print(f"Files skipped:       {global_stats['skipped']}")
    print(f"Errors:              {global_stats['errors']}")
    print(f"\nDrum racks shifted:  {global_stats['racks_shifted']}")
    print(f"Total pads shifted:  {global_stats['total_pads_shifted']}")

    if not dry_run and global_stats['processed'] > 0:
        print(f"\nOutput directory: {output_dir}")

    return global_stats


def main():
    parser = argparse.ArgumentParser(
        description='Batch shift second chain MIDI notes in dual-chain racks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process all files, shift down by 16
    python3 batch_shift_second_chain.py input_dir/ output_dir/

    # Preview what would be done
    python3 batch_shift_second_chain.py input_dir/ output_dir/ --dry-run

    # Custom shift amount
    python3 batch_shift_second_chain.py input_dir/ output_dir/ --shift -32

Result:
    Chain 1: Pads remain at original MIDI notes
    Chain 2: Pads shift by specified amount (default: -16)

This allows both drum racks to occupy separate MIDI ranges on a 32-pad controller.
        """
    )

    parser.add_argument('input_dir', type=Path, help='Input directory with .adg files')
    parser.add_argument('output_dir', type=Path, help='Output directory')
    parser.add_argument('--shift', type=int, default=-16, help='MIDI shift amount (default: -16)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')

    args = parser.parse_args()

    try:
        stats = batch_shift_second_chain(
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
