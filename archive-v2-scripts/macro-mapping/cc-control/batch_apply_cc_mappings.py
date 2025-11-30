#!/usr/bin/env python3
"""
Batch Apply DrumCell CC Mappings

Applies MIDI CC mappings to all drum racks in a directory.

Usage:
    python3 batch_apply_cc_mappings.py input_dir/ output_dir/
    python3 batch_apply_cc_mappings.py input_dir/ output_dir/ --template custom.adg
    python3 batch_apply_cc_mappings.py input_dir/ output_dir/ --dry-run
    python3 batch_apply_cc_mappings.py input_dir/ output_dir/ --in-place
"""

import argparse
import sys
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from apply_drumcell_cc_mappings import (
    extract_mappings_from_template,
    process_drum_rack,
    DEFAULT_MAPPINGS
)


def find_drum_racks(directory: Path) -> List[Path]:
    """Find all .adg files in directory."""
    return sorted(directory.glob('*.adg'))


def main():
    parser = argparse.ArgumentParser(
        description='Batch apply MIDI CC mappings to drum racks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process directory with default mappings
    python3 batch_apply_cc_mappings.py input_racks/ output_racks/

    # Use custom template
    python3 batch_apply_cc_mappings.py input_racks/ output_racks/ \\
        --template /Users/Music/Desktop/mapped.adg

    # In-place modification (overwrites originals)
    python3 batch_apply_cc_mappings.py racks/ --in-place

    # Dry run to preview
    python3 batch_apply_cc_mappings.py input_racks/ output_racks/ --dry-run
        """
    )

    parser.add_argument(
        'input_dir',
        type=Path,
        help='Input directory containing .adg files'
    )
    parser.add_argument(
        'output_dir',
        nargs='?',
        type=Path,
        help='Output directory (not needed with --in-place)'
    )
    parser.add_argument(
        '--template',
        type=Path,
        help='Template .adg file to extract mappings from'
    )
    parser.add_argument(
        '--channel',
        type=int,
        default=16,
        help='MIDI channel for mappings (1-16, default: 16)'
    )
    parser.add_argument(
        '--in-place',
        action='store_true',
        help='Modify files in-place (overwrites originals)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without modifying files'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress per-file output'
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.input_dir.exists():
        print(f"✗ Error: Input directory not found: {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    if not args.input_dir.is_dir():
        print(f"✗ Error: Not a directory: {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    if not args.in_place and not args.output_dir:
        print("✗ Error: Must specify output_dir or use --in-place", file=sys.stderr)
        sys.exit(1)

    if args.output_dir and not args.in_place:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.template and not args.template.exists():
        print(f"✗ Error: Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    # Find drum racks
    drum_racks = find_drum_racks(args.input_dir)

    if not drum_racks:
        print(f"✗ Error: No .adg files found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"BATCH APPLY CC MAPPINGS")
    print(f"{'='*80}\n")

    print(f"Input directory:  {args.input_dir}")
    if args.in_place:
        print(f"Mode:             In-place (will overwrite originals)")
    else:
        print(f"Output directory: {args.output_dir}")

    if args.dry_run:
        print(f"Mode:             DRY RUN (no files will be modified)")

    print(f"Found:            {len(drum_racks)} drum rack(s)")

    # Extract mappings
    if args.template:
        print(f"\nExtracting mappings from: {args.template.name}")
        mappings = extract_mappings_from_template(args.template)
    else:
        print(f"\nUsing default CC mappings")
        mappings = DEFAULT_MAPPINGS

    # Override channel if specified
    if args.channel != 16:
        print(f"Overriding channel to: {args.channel}")
        for mapping in mappings:
            mapping.channel = args.channel

    print(f"\nProcessing {len(drum_racks)} racks...\n")

    # Process each rack
    total_stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'drumcells': 0,
        'mappings_added': 0,
        'mappings_updated': 0,
    }

    for i, input_path in enumerate(drum_racks, 1):
        try:
            if args.in_place:
                output_path = input_path
            else:
                output_path = args.output_dir / input_path.name

            if not args.quiet:
                print(f"[{i}/{len(drum_racks)}] {input_path.name}")

            stats = process_drum_rack(
                input_path,
                output_path,
                mappings,
                dry_run=args.dry_run or args.quiet
            )

            total_stats['processed'] += 1
            total_stats['drumcells'] += stats['drumcells']
            total_stats['mappings_added'] += stats['mappings_added']
            total_stats['mappings_updated'] += stats['mappings_updated']

            if not args.quiet:
                print(f"  ✓ {stats['drumcells']} DrumCells, "
                      f"{stats['mappings_added'] + stats['mappings_updated']} mappings applied\n")

        except Exception as e:
            total_stats['errors'] += 1
            print(f"  ✗ Error: {e}\n")
            if not args.quiet:
                import traceback
                traceback.print_exc()

    # Print summary
    print(f"\n{'='*80}")
    print(f"BATCH SUMMARY")
    print(f"{'='*80}\n")

    print(f"Processed:           {total_stats['processed']} racks")
    print(f"Errors:              {total_stats['errors']}")
    print(f"Total DrumCells:     {total_stats['drumcells']}")
    print(f"Mappings added:      {total_stats['mappings_added']}")
    print(f"Mappings updated:    {total_stats['mappings_updated']}")
    print(f"Total operations:    {total_stats['mappings_added'] + total_stats['mappings_updated']}")

    if args.dry_run:
        print("\n⚠️  DRY RUN - No files were modified")
    elif args.in_place:
        print(f"\n✓ SUCCESS - {total_stats['processed']} files modified in-place")
    else:
        print(f"\n✓ SUCCESS - Output written to: {args.output_dir}")

    print(f"\n{'='*80}\n")

    sys.exit(0 if total_stats['errors'] == 0 else 1)


if __name__ == '__main__':
    main()
