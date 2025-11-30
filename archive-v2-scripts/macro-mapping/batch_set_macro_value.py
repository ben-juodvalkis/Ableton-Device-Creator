#!/usr/bin/env python3
"""
Batch Set Macro Value

Recursively processes all .adg files in a directory, setting a specific macro value
while preserving the folder structure.

Usage:
    python3 batch_set_macro_value.py input_folder output_folder --macro 16 --value 42
"""

import argparse
import sys
from pathlib import Path
import re

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def set_macro_value(xml_content: str, macro_idx: int, value: int) -> str:
    """
    Set the Manual value for a specific macro.

    Args:
        xml_content: Decoded .adg XML
        macro_idx: Macro index (0-15 for macros 1-16)
        value: Value to set (0-127)

    Returns:
        Modified XML
    """
    # Pattern: Find MacroControls.{macro_idx} and change its Manual value
    pattern = rf'(<MacroControls\.{macro_idx}>[\s\S]*?<Manual Value=")([^"]+)(")'

    # Replace with new value
    modified = re.sub(pattern, rf'\g<1>{value}\3', xml_content, count=1)

    return modified


def process_file(
    input_path: Path,
    output_path: Path,
    macro_idx: int,
    value: int
) -> tuple[bool, str]:
    """
    Process a single drum rack file.

    Returns:
        (success, error_message)
    """
    try:
        # Decode the ADG file
        xml_content = decode_adg(input_path)

        # Set macro value
        modified_xml = set_macro_value(xml_content, macro_idx, value)

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Encode back to ADG
        encode_adg(modified_xml, output_path)

        return True, None

    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description='Batch set macro value in drum racks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Set macro 16 to value 42 for all racks
    python3 batch_set_macro_value.py \\
        ~/Desktop/Remapped \\
        ~/Desktop/Remapped_Macro42 \\
        --macro 16 --value 42

    # Preview without processing
    python3 batch_set_macro_value.py \\
        ~/Desktop/Remapped \\
        ~/Desktop/Remapped_Macro42 \\
        --macro 16 --value 42 --dry-run
        """
    )

    parser.add_argument('input_folder', type=Path, help='Input folder containing .adg files')
    parser.add_argument('output_folder', type=Path, help='Output folder (preserves structure)')
    parser.add_argument(
        '--macro',
        type=int,
        required=True,
        help='Macro number to set (1-16)'
    )
    parser.add_argument(
        '--value',
        type=int,
        required=True,
        help='Value to set (0-127)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview files that would be processed without actually processing them'
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )

    args = parser.parse_args()

    # Validate input folder
    if not args.input_folder.exists():
        print(f"✗ Error: Input folder not found: {args.input_folder}", file=sys.stderr)
        sys.exit(1)

    if not args.input_folder.is_dir():
        print(f"✗ Error: Input path is not a directory: {args.input_folder}", file=sys.stderr)
        sys.exit(1)

    # Validate macro number
    if not 1 <= args.macro <= 16:
        print(f"✗ Error: Macro number must be 1-16, got {args.macro}", file=sys.stderr)
        sys.exit(1)

    # Validate value
    if not 0 <= args.value <= 127:
        print(f"✗ Error: Value must be 0-127, got {args.value}", file=sys.stderr)
        sys.exit(1)

    # Find all .adg files
    adg_files = list(args.input_folder.rglob("*.adg"))

    if not adg_files:
        print(f"✗ Error: No .adg files found in {args.input_folder}", file=sys.stderr)
        sys.exit(1)

    # Convert macro number to index (1-16 -> 0-15)
    macro_idx = args.macro - 1

    print(f"\n{'='*80}")
    print(f"BATCH SET MACRO VALUE")
    print(f"{'='*80}\n")
    print(f"Input folder:  {args.input_folder}")
    print(f"Output folder: {args.output_folder}")
    print(f"Macro:         {args.macro}")
    print(f"Value:         {args.value}")
    print(f"Files found:   {len(adg_files)}")

    if args.dry_run:
        print(f"\n⚠ DRY RUN MODE - No files will be modified\n")

    # Confirm before proceeding
    if not args.dry_run and not args.yes:
        print(f"\nThis will process {len(adg_files)} drum rack files.")
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    print(f"\n{'='*80}")
    print(f"PROCESSING")
    print(f"{'='*80}\n")

    # Process each file
    success_count = 0
    error_count = 0
    errors = []

    for i, input_path in enumerate(adg_files, 1):
        # Calculate relative path to preserve folder structure
        rel_path = input_path.relative_to(args.input_folder)
        output_path = args.output_folder / rel_path

        # Show progress
        print(f"[{i}/{len(adg_files)}] {rel_path}")

        if args.dry_run:
            print(f"  → Would create: {output_path}")
            success_count += 1
            continue

        # Process the file
        success, error = process_file(
            input_path,
            output_path,
            macro_idx,
            args.value
        )

        if success:
            print(f"  ✓ Created: {output_path}")
            success_count += 1
        else:
            print(f"  ✗ Error: {error}")
            error_count += 1
            errors.append((rel_path, error))

    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}\n")
    print(f"Total files:  {len(adg_files)}")
    print(f"Successful:   {success_count}")
    print(f"Errors:       {error_count}")

    if errors:
        print(f"\nFailed files:")
        for rel_path, error in errors:
            print(f"  • {rel_path}")
            print(f"    {error}")

    if not args.dry_run and success_count > 0:
        print(f"\n✓ Output folder: {args.output_folder}")

    print(f"\n{'='*80}\n")

    sys.exit(0 if error_count == 0 else 1)


if __name__ == '__main__':
    main()
