#!/usr/bin/env python3
"""
Batch Trim Drum Racks to 16 Pads

Process all .adg files in a directory (recursively) and trim drum racks to 16 pads.

Usage:
    python3 batch_trim_to_16.py input_dir output_dir
    python3 batch_trim_to_16.py input_dir output_dir --dry-run
    python3 batch_trim_to_16.py input_dir output_dir --in-place
"""

import argparse
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from drum_rack.trim_drum_racks_to_16 import trim_drum_racks_to_16


def batch_trim_to_16(
    input_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
    in_place: bool = False
) -> dict:
    """
    Process all .adg files recursively, trimming drum racks to 16 pads.

    Args:
        input_dir: Root directory to search for .adg files
        output_dir: Output directory (preserves subdirectory structure)
        dry_run: If True, analyze only without modifying
        in_place: If True, overwrite original files (ignores output_dir)

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
        return {'processed': 0, 'skipped': 0, 'errors': 0, 'total_pads_removed': 0}

    print(f"\n{'='*70}")
    print(f"BATCH TRIM DRUM RACKS TO 16 PADS")
    print(f"{'='*70}\n")
    print(f"Input directory: {input_dir}")
    if in_place:
        print(f"Mode: IN-PLACE (will overwrite original files)")
    else:
        print(f"Output directory: {output_dir}")
    print(f"Found {len(adg_files)} .adg files")

    if dry_run:
        print(f"\n{'='*70}")
        print(f"DRY RUN - No files will be modified")
        print(f"{'='*70}")

    print()

    # Create output directory if needed
    if not dry_run and not in_place:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Process files
    global_stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'total_pads_removed': 0,
        'racks_trimmed': 0,
        'racks_unchanged': 0
    }

    for idx, input_path in enumerate(adg_files):
        # Compute relative path to preserve directory structure
        rel_path = input_path.relative_to(input_dir)

        if in_place:
            output_path = input_path
        else:
            output_path = output_dir / rel_path
            output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[{idx+1}/{len(adg_files)}] {rel_path}")

        try:
            # Trim the rack (quiet mode for batch processing)
            stats = trim_drum_racks_to_16(
                input_path,
                output_path,
                dry_run,
                quiet=True
            )

            if stats['racks_trimmed'] > 0:
                print(f"  ✓ Trimmed {stats['racks_trimmed']} rack(s), removed {stats['total_pads_removed']} pad(s)")
                global_stats['processed'] += 1
                global_stats['racks_trimmed'] += stats['racks_trimmed']
                global_stats['total_pads_removed'] += stats['total_pads_removed']
            else:
                print(f"  - No changes needed")
                global_stats['skipped'] += 1

            global_stats['racks_unchanged'] += stats['racks_unchanged']
            print()

        except Exception as e:
            print(f"  ✗ Error: {e}\n")
            global_stats['errors'] += 1
            continue

    # Print summary
    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING {'DRY RUN ' if dry_run else ''}COMPLETE")
    print(f"{'='*70}")
    print(f"Files processed: {global_stats['processed']}")
    print(f"Files unchanged: {global_stats['skipped']}")
    print(f"Errors:          {global_stats['errors']}")
    print(f"\nDrum racks trimmed:  {global_stats['racks_trimmed']}")
    print(f"Drum racks unchanged: {global_stats['racks_unchanged']}")
    print(f"Total pads removed:   {global_stats['total_pads_removed']}")

    if not dry_run and not in_place and global_stats['processed'] > 0:
        print(f"\nOutput directory: {output_dir}")

    return global_stats


def main():
    parser = argparse.ArgumentParser(
        description='Batch trim drum racks to 16 pads',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process all files, preserve directory structure
    python3 batch_trim_to_16.py input_dir/ output_dir/

    # Preview what would be done
    python3 batch_trim_to_16.py input_dir/ output_dir/ --dry-run

    # Modify files in place (CAUTION!)
    python3 batch_trim_to_16.py input_dir/ . --in-place

Notes:
    - Processes all .adg files recursively
    - Preserves directory structure in output
    - Keeps pads 1-16 (bottom pads with essential drums)
    - Removes pads 17+ (top pads with auxiliary/melodic elements)
    - Multiple drum racks per file are all trimmed
        """
    )

    parser.add_argument('input_dir', type=Path, help='Input directory with .adg files')
    parser.add_argument('output_dir', type=Path, help='Output directory')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    parser.add_argument('--in-place', action='store_true', help='Modify files in place (CAUTION!)')

    args = parser.parse_args()

    try:
        stats = batch_trim_to_16(
            args.input_dir,
            args.output_dir,
            args.dry_run,
            args.in_place
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
