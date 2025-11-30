#!/usr/bin/env python3
"""
Batch Apply Color Coding

Process all .adg files in a directory (recursively) and apply color coding
to drum pads based on their names.

Usage:
    python3 batch_apply_colors.py input_dir output_dir
    python3 batch_apply_colors.py input_dir output_dir --dry-run
"""

import argparse
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from drum_rack.apply_color_coding import apply_color_coding


def batch_apply_colors(
    input_dir: Path,
    output_dir: Path,
    dry_run: bool = False
) -> dict:
    """
    Process all .adg files recursively, applying color coding.

    Args:
        input_dir: Root directory to search for .adg files
        output_dir: Output directory (preserves subdirectory structure)
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
    print(f"BATCH APPLY COLOR CODING")
    print(f"{'='*70}\n")
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
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
        'errors': 0,
        'total_pads_colored': 0
    }

    for idx, input_path in enumerate(adg_files):
        # Compute relative path to preserve directory structure
        rel_path = input_path.relative_to(input_dir)
        output_path = output_dir / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[{idx+1}/{len(adg_files)}] {rel_path}")

        try:
            # Apply color coding (quiet mode)
            stats = apply_color_coding(
                input_path,
                output_path,
                dry_run,
                quiet=True
            )

            if stats['pads_colored'] > 0:
                print(f"  ✓ Colored {stats['pads_colored']} pad(s)")
                global_stats['processed'] += 1
                global_stats['total_pads_colored'] += stats['pads_colored']

        except Exception as e:
            print(f"  ✗ Error: {e}")
            global_stats['errors'] += 1
            continue

    # Print summary
    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING {'DRY RUN ' if dry_run else ''}COMPLETE")
    print(f"{'='*70}")
    print(f"Files processed:     {global_stats['processed']}")
    print(f"Errors:              {global_stats['errors']}")
    print(f"Total pads colored:  {global_stats['total_pads_colored']}")

    if not dry_run and global_stats['processed'] > 0:
        print(f"\nOutput directory: {output_dir}")

    return global_stats


def main():
    parser = argparse.ArgumentParser(
        description='Batch apply color coding to drum pads',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process all files
    python3 batch_apply_colors.py input_dir/ output_dir/

    # Preview what would be done
    python3 batch_apply_colors.py input_dir/ output_dir/ --dry-run

Color Scheme:
    Kick:          Red (60)
    Snare/Clap:    Yellow (13)
    Tom:           Orange (9)
    Hihat (closed):Cyan (41)
    Hihat (open):  Light Blue (43)
    Cymbal:        Blue (45)
    Shaker:        Green (26)
    Percussion:    Green (26)
    Default:       Orange (0)
        """
    )

    parser.add_argument('input_dir', type=Path, help='Input directory with .adg files')
    parser.add_argument('output_dir', type=Path, help='Output directory')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')

    args = parser.parse_args()

    try:
        stats = batch_apply_colors(
            args.input_dir,
            args.output_dir,
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
