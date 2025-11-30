#!/usr/bin/env python3
"""
Batch Remap Drum Rack MIDI Notes

Recursively processes all .adg files in a directory, remapping MIDI notes
while preserving the folder structure.

Usage:
    python3 batch_remap_drum_racks.py input_folder output_folder --shift 28 --scroll-shift 7
"""

import argparse
import sys
from pathlib import Path
from typing import Tuple
import xml.etree.ElementTree as ET

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def remap_midi_notes(xml_content: str, shift: int, scroll_shift: int = 0) -> str:
    """
    Shift all MIDI notes in a drum rack by a specified amount.

    Args:
        xml_content: XML content string
        shift: Amount to shift MIDI notes
        scroll_shift: Amount to shift the pad scroll position

    Returns:
        Modified XML content
    """
    root = ET.fromstring(xml_content)

    # Find all drum pads
    drum_pads = root.findall('.//DrumBranchPreset')

    # Shift MIDI notes for each pad
    for pad in drum_pads:
        zone_settings = pad.find('.//ZoneSettings/ReceivingNote')
        if zone_settings is not None:
            old_note = int(zone_settings.get('Value'))
            new_note = old_note + shift

            # Clamp to valid MIDI range (0-127)
            new_note = max(0, min(127, new_note))
            zone_settings.set('Value', str(new_note))

    # Shift the pad scroll position if requested
    if scroll_shift != 0:
        scroll_elem = root.find('.//PadScrollPosition')
        if scroll_elem is not None:
            old_scroll = int(scroll_elem.get('Value'))
            new_scroll = old_scroll + scroll_shift
            new_scroll = max(0, min(127, new_scroll))
            scroll_elem.set('Value', str(new_scroll))

    return ET.tostring(root, encoding='unicode', xml_declaration=True)


def process_rack(
    input_path: Path,
    output_path: Path,
    shift: int,
    scroll_shift: int
) -> Tuple[bool, str]:
    """
    Process a single drum rack file.

    Returns:
        (success, error_message)
    """
    try:
        # Decode the ADG file
        xml_content = decode_adg(input_path)

        # Remap the MIDI notes
        transformed_xml = remap_midi_notes(xml_content, shift, scroll_shift)

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Encode back to ADG
        encode_adg(transformed_xml, output_path)

        return True, None

    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description='Batch remap MIDI notes in drum racks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Remap all racks in a folder
    python3 batch_remap_drum_racks.py \\
        ~/Desktop/NI_Expansion_Kits \\
        ~/Desktop/NI_Expansion_Kits_Remapped \\
        --shift 28 --scroll-shift 7

    # Preview without processing
    python3 batch_remap_drum_racks.py \\
        ~/Desktop/NI_Expansion_Kits \\
        ~/Desktop/NI_Expansion_Kits_Remapped \\
        --shift 28 --dry-run
        """
    )

    parser.add_argument('input_folder', type=Path, help='Input folder containing .adg files')
    parser.add_argument('output_folder', type=Path, help='Output folder (preserves structure)')
    parser.add_argument(
        '--shift',
        type=int,
        required=True,
        help='Amount to shift MIDI notes (e.g., 28)'
    )
    parser.add_argument(
        '--scroll-shift',
        type=int,
        default=0,
        help='Amount to shift the pad scroll position (default: 0)'
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

    # Find all .adg files
    adg_files = list(args.input_folder.rglob("*.adg"))

    if not adg_files:
        print(f"✗ Error: No .adg files found in {args.input_folder}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"BATCH REMAP DRUM RACKS")
    print(f"{'='*80}\n")
    print(f"Input folder:  {args.input_folder}")
    print(f"Output folder: {args.output_folder}")
    print(f"MIDI shift:    {args.shift:+d} semitones")
    if args.scroll_shift != 0:
        print(f"Scroll shift:  {args.scroll_shift:+d}")
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

        # Process the rack
        success, error = process_rack(
            input_path,
            output_path,
            args.shift,
            args.scroll_shift
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
