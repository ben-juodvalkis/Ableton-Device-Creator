#!/usr/bin/env python3
"""
Batch Wrap Device Pairs

Process all .adg files in a directory and create dual-chain racks for each pair.

Usage:
    python3 batch_wrap_pairs.py input_dir output_dir
    python3 batch_wrap_pairs.py input_dir output_dir --rack-prefix "Dual"
    python3 batch_wrap_pairs.py input_dir output_dir --dry-run
"""

import argparse
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from drum_rack.wrap_two_devices_in_rack import wrap_two_devices_in_rack


def batch_wrap_pairs(
    input_dir: Path,
    output_dir: Path,
    rack_prefix: str = "",
    dry_run: bool = False
) -> dict:
    """
    Process all .adg files in a directory, pairing them up sequentially.

    Args:
        input_dir: Directory containing source .adg files
        output_dir: Directory for output dual-chain racks
        rack_prefix: Optional prefix for rack names (e.g., "Dual ")
        dry_run: If True, only show what would be done

    Returns:
        Dictionary with statistics
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    if not input_dir.is_dir():
        raise ValueError(f"Input path is not a directory: {input_dir}")

    # Find all .adg files
    adg_files = sorted(input_dir.glob('*.adg'))

    if len(adg_files) == 0:
        print(f"⚠️  No .adg files found in {input_dir}")
        return {'processed': 0, 'skipped': 0, 'errors': 0}

    print(f"\n{'='*70}")
    print(f"BATCH DUAL-CHAIN WRAPPING")
    print(f"{'='*70}\n")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Found {len(adg_files)} devices")
    print(f"Will create {len(adg_files) // 2} dual-chain racks")

    if len(adg_files) % 2 != 0:
        print(f"⚠️  Note: Odd number of files - last file will be skipped")

    if dry_run:
        print(f"\n{'='*70}")
        print(f"DRY RUN - No files will be created")
        print(f"{'='*70}")

    print()

    # Create output directory
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Process pairs
    stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0
    }

    for i in range(0, len(adg_files) - 1, 2):
        device1_path = adg_files[i]
        device2_path = adg_files[i + 1]

        # Create output filename from both device names
        device1_name = device1_path.stem
        device2_name = device2_path.stem

        # Create a meaningful rack name
        rack_name = f"{rack_prefix}{device1_name} + {device2_name}" if rack_prefix else f"{device1_name} + {device2_name}"
        output_filename = f"{device1_name} + {device2_name}.adg"
        output_path = output_dir / output_filename

        print(f"[{i//2 + 1}/{len(adg_files)//2}] Creating: {output_filename}")
        print(f"  Device 1: {device1_name}")
        print(f"  Device 2: {device2_name}")

        if dry_run:
            print(f"  → Would create: {output_path}")
            stats['processed'] += 1
            print()
            continue

        try:
            # Wrap the two devices
            wrap_two_devices_in_rack(
                device1_path,
                device2_path,
                output_path,
                rack_name=rack_name,
                chain1_name="",  # Let it auto-detect
                chain2_name=""   # Let it auto-detect
            )
            stats['processed'] += 1
            print(f"  ✓ Created: {output_path.name}\n")

        except Exception as e:
            print(f"  ✗ Error: {e}\n")
            stats['errors'] += 1
            continue

    # Handle leftover file if odd number
    if len(adg_files) % 2 != 0:
        leftover = adg_files[-1]
        print(f"⚠️  Skipped (odd file): {leftover.name}")
        stats['skipped'] = 1

    # Print summary
    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"Processed: {stats['processed']} dual-chain racks")
    print(f"Skipped:   {stats['skipped']} files")
    print(f"Errors:    {stats['errors']} failures")

    if not dry_run and stats['processed'] > 0:
        print(f"\nOutput directory: {output_dir}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Batch wrap device pairs into dual-chain racks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process all files in a directory
    python3 batch_wrap_pairs.py input_dir/ output_dir/

    # Add prefix to rack names
    python3 batch_wrap_pairs.py input_dir/ output_dir/ --rack-prefix "Dual "

    # Preview what would be done
    python3 batch_wrap_pairs.py input_dir/ output_dir/ --dry-run

Notes:
    - Files are paired sequentially (alphabetically sorted)
    - Device names are auto-detected from source files
    - Chain names are auto-set to device names
    - If odd number of files, last file is skipped
        """
    )

    parser.add_argument('input_dir', type=Path, help='Input directory with .adg files')
    parser.add_argument('output_dir', type=Path, help='Output directory for dual-chain racks')
    parser.add_argument('--rack-prefix', default='', help='Prefix for rack names (e.g., "Dual ")')
    parser.add_argument('--dry-run', action='store_true', help='Preview without creating files')

    args = parser.parse_args()

    try:
        stats = batch_wrap_pairs(
            args.input_dir,
            args.output_dir,
            args.rack_prefix,
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
