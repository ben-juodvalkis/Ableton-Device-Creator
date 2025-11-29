#!/usr/bin/env python3
"""
Batch Battery Kit Processor - Organized & Color-Coded

Processes all .nbkt files in a Battery Kits folder and creates organized,
color-coded Ableton drum racks with TWO kits per rack (pads 1-16 and 17-32).

Features:
- Filters out "Lick" samples (too long for drum use)
- Smart pad assignment based on sample type
- Color-coded pads by instrument category
- Dual-kit support (pads 1-16 + 17-32)

Usage:
    python3 batch_battery_kits_organized.py <template.adg> <battery_kits_folder> [--output-folder <path>]

Example:
    python3 batch_battery_kits_organized.py \
        templates/input_rack.adg \
        "/path/to/Expansions/Library/Sounds/Battery Kits"
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Import the organized kit processor
from main_battery_kit_organized import create_organized_dual_kit_rack


def process_all_kits(template_path: Path,
                     battery_kits_folder: Path,
                     output_folder: Optional[Path] = None) -> None:
    """
    Process all .nbkt files in the Battery Kits folder, creating organized dual-kit racks.

    Args:
        template_path: Path to the ADG template file
        battery_kits_folder: Path to the Battery Kits folder
        output_folder: Optional output folder path
    """
    # Find all .nbkt files
    nbkt_files = sorted(battery_kits_folder.glob("*.nbkt"))

    if not nbkt_files:
        print(f"No .nbkt files found in: {battery_kits_folder}")
        return

    print(f"Found {len(nbkt_files)} Battery Kit(s)")
    print(f"Creating {len(nbkt_files) // 2} organized dual-kit drum racks (2 kits per rack)")
    print(f"Features: Smart pad layout, color-coded, Lick samples filtered")
    print(f"=" * 70)

    successful = 0
    failed = 0
    skipped = 0

    # Process kits in pairs
    for i in range(0, len(nbkt_files), 2):
        kit_1_path = nbkt_files[i]

        # Check if we have a second kit
        if i + 1 < len(nbkt_files):
            kit_2_path = nbkt_files[i + 1]
            pair_num = (i // 2) + 1
            total_pairs = (len(nbkt_files) + 1) // 2

            print(f"\n[{pair_num}/{total_pairs}] Processing pair:")
            print(f"  Kit 1: {kit_1_path.name}")
            print(f"  Kit 2: {kit_2_path.name}")
            print("-" * 70)

            try:
                create_organized_dual_kit_rack(template_path, kit_1_path, kit_2_path, output_folder)
                successful += 1

            except ValueError as e:
                # Kit has no matching samples - skip
                print(f"⚠ Skipped: {e}")
                skipped += 1

            except Exception as e:
                print(f"✗ Failed: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
                continue

        else:
            # Odd number of kits - last kit is unpaired
            print(f"\n⚠ Unpaired kit (skipping): {kit_1_path.name}")
            print("  Note: Need pairs of kits for dual-kit racks")
            skipped += 1

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total kits: {len(nbkt_files)}")
    print(f"✓ Successful organized dual racks: {successful}")
    print(f"⚠ Skipped: {skipped}")
    print(f"✗ Failed: {failed}")


def main():
    parser = argparse.ArgumentParser(
        description='Batch process Battery Kit files to organized, color-coded dual-kit drum racks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Features:
  - Smart pad layout (Kicks on 1-2, Snares on 3-5, etc.)
  - Color-coded pads by instrument type
  - Filters out "Lick" samples (too long for drum use)
  - Two complete kits per rack (pads 1-16 + 17-32)

Example:
    python3 batch_battery_kits_organized.py \\
        templates/input_rack.adg \\
        "/path/to/Library/Sounds/Battery Kits"
        """
    )

    parser.add_argument('template', type=str,
                       help='Path to ADG template file')
    parser.add_argument('battery_kits_folder', type=str,
                       help='Path to Battery Kits folder containing .nbkt files')
    parser.add_argument('--output-folder', type=str, default=None,
                       help='Optional: Output folder for .adg files')

    args = parser.parse_args()

    try:
        template_path = Path(args.template)
        kits_folder = Path(args.battery_kits_folder)

        # Validate inputs
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        if not kits_folder.exists():
            raise FileNotFoundError(f"Battery Kits folder not found: {kits_folder}")

        if not kits_folder.is_dir():
            raise ValueError(f"Not a directory: {kits_folder}")

        # Process output folder
        output_folder = Path(args.output_folder) if args.output_folder else None

        # Process all kits
        process_all_kits(template_path, kits_folder, output_folder)

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
