#!/usr/bin/env python3
"""
Batch convert all Simplers to DrumCells in a directory of drum racks

Recursively finds all .adg files in a directory, converts Simplers to DrumCells,
and saves the results with a suffix or to an output directory.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.decoder import decode_adg
from utils.encoder import encode_adg

# Import the drum rack converter
from conversion.drum_rack_simpler_to_drumcell import find_and_convert_simplers
import xml.etree.ElementTree as ET


def process_drum_rack(input_path, output_path, dry_run=False):
    """Process a single drum rack file"""
    try:
        # Decode drum rack
        rack_xml = decode_adg(input_path)
        rack_root = ET.fromstring(rack_xml)

        # Check if it has any Simplers
        simplers = rack_root.findall('.//OriginalSimpler')
        if len(simplers) == 0:
            return {'status': 'skipped', 'reason': 'no_simplers', 'converted': 0}

        if dry_run:
            return {'status': 'would_convert', 'converted': len(simplers)}

        # Convert all simplers
        converted, skipped = find_and_convert_simplers(rack_root)

        if converted == 0:
            return {'status': 'skipped', 'reason': 'no_conversion', 'converted': 0}

        # Encode result
        result_xml = ET.tostring(rack_root, encoding='unicode', xml_declaration=True)
        encode_adg(result_xml, output_path)

        return {'status': 'success', 'converted': converted, 'skipped': skipped}

    except Exception as e:
        return {'status': 'error', 'error': str(e), 'converted': 0}


def main():
    parser = argparse.ArgumentParser(
        description='Batch convert all Simplers to DrumCells in drum racks'
    )
    parser.add_argument(
        'input_dir',
        type=str,
        help='Directory containing .adg drum rack files'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory (if not specified, files are saved with suffix)'
    )
    parser.add_argument(
        '--suffix',
        type=str,
        default=' (converted)',
        help='Suffix to add to filenames (default: " (converted)")'
    )
    parser.add_argument(
        '--in-place',
        action='store_true',
        help='Overwrite original files (DANGEROUS!)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be converted without actually converting'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress per-file output'
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)

    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)

    # Find all .adg files
    adg_files = list(input_dir.rglob('*.adg'))

    print("="*80)
    print("🥁 BATCH DRUM RACK CONVERSION")
    print("="*80)
    print(f"\nInput directory: {input_dir}")
    print(f"Found: {len(adg_files)} drum rack files")

    if args.dry_run:
        print("Mode: DRY RUN (no files will be modified)")
    elif args.in_place:
        print("Mode: IN-PLACE (original files will be OVERWRITTEN)")
        response = input("\n⚠️  This will overwrite original files. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    elif args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")
    else:
        print(f"Mode: Saving with suffix '{args.suffix}'")

    print("\n" + "="*80)
    print("PROCESSING FILES")
    print("="*80 + "\n")

    # Statistics
    stats = {
        'total': len(adg_files),
        'converted': 0,
        'skipped': 0,
        'errors': 0,
        'total_simplers': 0,
        'multisample_skipped': 0
    }

    start_time = datetime.now()

    for idx, input_path in enumerate(adg_files, 1):
        # Determine output path
        if args.in_place:
            output_path = input_path
        elif args.output_dir:
            # Preserve directory structure
            rel_path = input_path.relative_to(input_dir)
            output_path = Path(args.output_dir) / rel_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Add suffix
            stem = input_path.stem
            output_path = input_path.parent / f"{stem}{args.suffix}.adg"

        if not args.quiet:
            print(f"[{idx}/{len(adg_files)}] {input_path.relative_to(input_dir)}")

        result = process_drum_rack(input_path, output_path, args.dry_run)

        if result['status'] == 'success':
            stats['converted'] += 1
            stats['total_simplers'] += result['converted']
            if not args.quiet:
                print(f"  ✓ Converted {result['converted']} Simpler(s)")
        elif result['status'] == 'would_convert':
            stats['converted'] += 1
            stats['total_simplers'] += result['converted']
            if not args.quiet:
                print(f"  → Would convert {result['converted']} Simpler(s)")
        elif result['status'] == 'skipped':
            stats['skipped'] += 1
            if not args.quiet:
                reason = result.get('reason', 'unknown')
                print(f"  ⏭️  Skipped ({reason})")
        elif result['status'] == 'error':
            stats['errors'] += 1
            print(f"  ✗ Error: {result['error']}")

    elapsed = datetime.now() - start_time

    # Final summary
    print("\n" + "="*80)
    print("✅ BATCH CONVERSION COMPLETE")
    print("="*80)
    print(f"\nProcessed: {stats['total']} files in {elapsed.total_seconds():.1f}s")
    print(f"  Converted: {stats['converted']} racks ({stats['total_simplers']} Simplers)")
    print(f"  Skipped:   {stats['skipped']} racks (no Simplers)")
    print(f"  Errors:    {stats['errors']} racks")

    if not args.dry_run and stats['converted'] > 0:
        if args.in_place:
            print(f"\n⚠️  Original files have been overwritten")
        elif args.output_dir:
            print(f"\n✨ Output saved to: {args.output_dir}")
        else:
            print(f"\n✨ Converted files saved with suffix '{args.suffix}'")

    print("="*80 + "\n")


if __name__ == '__main__':
    main()
