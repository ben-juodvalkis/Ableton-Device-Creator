#!/usr/bin/env python3
"""
Batch Add Transpose-to-Macro Mapping

Maps the Transpose parameter of MultiSampler/Simpler devices within drum racks
to a specified macro in the parent instrument rack.

Based on the mapping pattern:
- Finds TransposeKey elements in MultiSampler/Simpler devices
- Adds KeyMidi mapping block (Channel 16, NoteOrController = macro index)
- Sets macro manual value to 63.5 (center position)
- Sets macro default to -1 (preserve current value on load)

Usage:
    # Map transpose to Macro 16 for all racks
    python3 batch_add_transpose_mapping.py input_dir/ output_dir/ --macro 15

    # Preview changes without writing
    python3 batch_add_transpose_mapping.py input_dir/ output_dir/ --macro 15 --dry-run

    # Process single file
    python3 batch_add_transpose_mapping.py input.adg output.adg --macro 15
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def create_keymidi_element(macro_index: int) -> ET.Element:
    """
    Create a KeyMidi mapping element for macro control.

    Args:
        macro_index: Macro index (0-15 for Macros 1-16)

    Returns:
        KeyMidi element ready to insert into parameter
    """
    keymidi = ET.Element('KeyMidi')

    ET.SubElement(keymidi, 'PersistentKeyString').set('Value', '')
    ET.SubElement(keymidi, 'IsNote').set('Value', 'false')
    ET.SubElement(keymidi, 'Channel').set('Value', '16')
    ET.SubElement(keymidi, 'NoteOrController').set('Value', str(macro_index))
    ET.SubElement(keymidi, 'LowerRangeNote').set('Value', '-1')
    ET.SubElement(keymidi, 'UpperRangeNote').set('Value', '-1')
    ET.SubElement(keymidi, 'ControllerMapMode').set('Value', '0')

    return keymidi


def add_transpose_mapping(
    root: ET.Element,
    macro_index: int,
    macro_value: float = 63.5
) -> Dict[str, int]:
    """
    Add transpose-to-macro mappings to all MultiSampler/Simpler devices.

    Args:
        root: XML root element
        macro_index: Target macro index (0-15 for Macros 1-16)
        macro_value: Initial macro value (0-127, default 63.5 = center)

    Returns:
        Statistics dictionary with counts
    """
    stats = {
        'transpose_params_found': 0,
        'mappings_added': 0,
        'mappings_already_exist': 0,
        'macros_updated': 0
    }

    # Find all TransposeKey parameters in MultiSampler/Simpler devices
    # These can be in drum pads within drum racks
    transpose_keys = root.findall('.//TransposeKey')

    stats['transpose_params_found'] = len(transpose_keys)

    for transpose_key in transpose_keys:
        # Check if KeyMidi already exists
        existing_keymidi = transpose_key.find('KeyMidi')

        if existing_keymidi is not None:
            # Check if it's mapped to our target macro
            controller = existing_keymidi.find('NoteOrController')
            if controller is not None and controller.get('Value') == str(macro_index):
                stats['mappings_already_exist'] += 1
                continue

        # Add KeyMidi mapping
        # Insert after LomId, before Manual
        keymidi = create_keymidi_element(macro_index)

        # Find insertion point (after LomId)
        lom_id_index = None
        for i, child in enumerate(transpose_key):
            if child.tag == 'LomId':
                lom_id_index = i
                break

        if lom_id_index is not None:
            transpose_key.insert(lom_id_index + 1, keymidi)
            stats['mappings_added'] += 1

    # Update macro settings in the parent instrument rack
    # Find MacroControls and MacroDefaults
    macro_control_path = f'.//MacroControls.{macro_index}'
    macro_default_path = f'.//MacroDefaults.{macro_index}'

    macro_control = root.find(macro_control_path)
    if macro_control is not None:
        manual = macro_control.find('Manual')
        if manual is not None:
            # Set to center position (63.5 for ±48 semitone range = 0 transpose)
            manual.set('Value', str(macro_value))
            stats['macros_updated'] += 1

    macro_default = root.find(macro_default_path)
    if macro_default is not None:
        # Set to -1 to preserve current value on load
        macro_default.set('Value', '-1')

    return stats


def process_single_file(
    input_path: Path,
    output_path: Path,
    macro_index: int,
    macro_value: float = 63.5,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Process a single .adg file.

    Args:
        input_path: Path to input .adg file
        output_path: Path for output file
        macro_index: Target macro index (0-15)
        macro_value: Initial macro value (0-127)
        dry_run: If True, analyze only

    Returns:
        Statistics dictionary
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Decode input
    xml_content = decode_adg(input_path)
    root = ET.fromstring(xml_content)

    # Add transpose mappings
    stats = add_transpose_mapping(root, macro_index, macro_value)

    # Write output if not dry run
    if not dry_run and (stats['mappings_added'] > 0 or stats['macros_updated'] > 0):
        processed_xml = ET.tostring(root, encoding='unicode', xml_declaration=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(processed_xml, output_path)

    return stats


def batch_add_transpose_mapping(
    input_path: Path,
    output_path: Path,
    macro_index: int,
    macro_value: float = 63.5,
    dry_run: bool = False
) -> Dict:
    """
    Process .adg file(s) to add transpose-to-macro mappings.

    Args:
        input_path: Input file or directory
        output_path: Output file or directory
        macro_index: Target macro index (0-15 for Macros 1-16)
        macro_value: Initial macro value (0-127, default 63.5)
        dry_run: If True, analyze only

    Returns:
        Global statistics dictionary
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    # Determine if processing single file or directory
    if input_path.is_file():
        adg_files = [input_path]
        is_dir = False
    else:
        adg_files = sorted(input_path.rglob('*.adg'))
        is_dir = True

    if len(adg_files) == 0:
        print(f"⚠️  No .adg files found in {input_path}")
        return {'processed': 0, 'errors': 0}

    print(f"\n{'='*70}")
    print(f"BATCH ADD TRANSPOSE-TO-MACRO MAPPING")
    print(f"{'='*70}\n")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Target: Macro {macro_index + 1} (index {macro_index})")
    print(f"Value:  {macro_value} (0-127 range)")
    print(f"\nFound {len(adg_files)} .adg file(s)")

    if dry_run:
        print(f"\n{'='*70}")
        print(f"DRY RUN - No files will be modified")
        print(f"{'='*70}")

    print()

    # Create output directory if needed
    if not dry_run and is_dir:
        output_path.mkdir(parents=True, exist_ok=True)

    # Process files
    global_stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'total_transpose_params': 0,
        'total_mappings_added': 0,
        'total_mappings_exist': 0,
        'total_macros_updated': 0
    }

    for idx, input_file in enumerate(adg_files):
        # Compute output path
        if is_dir:
            rel_path = input_file.relative_to(input_path)
            output_file = output_path / rel_path
        else:
            output_file = output_path

        file_display = input_file.name if not is_dir else str(input_file.relative_to(input_path))
        print(f"[{idx+1}/{len(adg_files)}] {file_display}")

        try:
            # Process the file
            stats = process_single_file(
                input_file,
                output_file,
                macro_index,
                macro_value,
                dry_run
            )

            # Report results
            if stats['mappings_added'] > 0 or stats['macros_updated'] > 0:
                actions = []
                if stats['mappings_added'] > 0:
                    actions.append(f"added {stats['mappings_added']} mapping(s)")
                if stats['mappings_already_exist'] > 0:
                    actions.append(f"{stats['mappings_already_exist']} already mapped")
                if stats['macros_updated'] > 0:
                    actions.append(f"updated macro")

                print(f"  ✓ {', '.join(actions)}")
                global_stats['processed'] += 1
            else:
                if stats['transpose_params_found'] == 0:
                    print(f"  - No transpose parameters found")
                else:
                    print(f"  - All mappings already exist")
                global_stats['skipped'] += 1

            global_stats['total_transpose_params'] += stats['transpose_params_found']
            global_stats['total_mappings_added'] += stats['mappings_added']
            global_stats['total_mappings_exist'] += stats['mappings_already_exist']
            global_stats['total_macros_updated'] += stats['macros_updated']

        except Exception as e:
            print(f"  ✗ Error: {e}")
            global_stats['errors'] += 1
            if '--verbose' in sys.argv:
                import traceback
                traceback.print_exc()
            continue

    # Print summary
    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING {'DRY RUN ' if dry_run else ''}COMPLETE")
    print(f"{'='*70}")
    print(f"Files processed:        {global_stats['processed']}")
    print(f"Files skipped:          {global_stats['skipped']}")
    print(f"Errors:                 {global_stats['errors']}")
    print(f"\nTranspose parameters:   {global_stats['total_transpose_params']}")
    print(f"Mappings added:         {global_stats['total_mappings_added']}")
    print(f"Mappings already exist: {global_stats['total_mappings_exist']}")
    print(f"Macros updated:         {global_stats['total_macros_updated']}")

    if not dry_run and global_stats['processed'] > 0:
        print(f"\nOutput: {output_path}")

    return global_stats


def main():
    parser = argparse.ArgumentParser(
        description='Batch add transpose-to-macro mappings to instrument racks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Map transpose to Macro 16 for all racks in directory
    python3 batch_add_transpose_mapping.py input_dir/ output_dir/ --macro 15

    # Process single file
    python3 batch_add_transpose_mapping.py input.adg output.adg --macro 15

    # Preview changes
    python3 batch_add_transpose_mapping.py input_dir/ output_dir/ --macro 15 --dry-run

    # Use custom macro value (default 63.5 = center = 0 transpose)
    python3 batch_add_transpose_mapping.py input.adg output.adg --macro 15 --value 70

Macro Indices:
    --macro 0  = Macro 1
    --macro 7  = Macro 8
    --macro 15 = Macro 16 (default)

Macro Value:
    For transpose (±48 semitones):
    - 0     = -48 semitones (lowest)
    - 63.5  = 0 semitones (center, no transpose)
    - 127   = +48 semitones (highest)
        """
    )

    parser.add_argument('input', type=Path, help='Input .adg file or directory')
    parser.add_argument('output', type=Path, help='Output .adg file or directory')
    parser.add_argument(
        '--macro',
        type=int,
        default=15,
        choices=range(16),
        help='Target macro index (0-15 for Macros 1-16, default: 15)'
    )
    parser.add_argument(
        '--value',
        type=float,
        default=63.5,
        help='Initial macro value (0-127, default: 63.5 = center)'
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    parser.add_argument('--verbose', action='store_true', help='Show detailed error traces')

    args = parser.parse_args()

    # Validate macro value
    if not 0 <= args.value <= 127:
        print(f"✗ Error: Macro value must be 0-127, got {args.value}", file=sys.stderr)
        sys.exit(1)

    try:
        stats = batch_add_transpose_mapping(
            args.input,
            args.output,
            args.macro,
            args.value,
            args.dry_run
        )

        # Exit with error code if there were errors
        if stats['errors'] > 0:
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
