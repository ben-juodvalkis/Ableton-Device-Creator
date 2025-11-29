#!/usr/bin/env python3
"""
Expand Instrument Racks in Drum Rack Chains

Applies the following transformations to all InstrumentGroupDevice racks
found within a drum rack's chains:

1. Expands macro visibility to show all 16 macros
2. Adds CC#15 mapping to Macro 6 (Sample Start control)
3. Expands Voice_Transpose range from ±24 to ±48 semitones
4. Sets Macro 15 to 63.5 with no default reset

Usage:
    python3 expand_instrument_racks.py input.adg output.adg
    python3 expand_instrument_racks.py input.adg output.adg --dry-run
    python3 expand_instrument_racks.py input.adg output.adg --cc 15 --macro 6
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def create_keymidi_element(cc_number: int, channel: int = 16) -> ET.Element:
    """Create a KeyMidi XML element for MIDI CC mapping."""
    keymidi = ET.Element('KeyMidi')
    ET.SubElement(keymidi, 'PersistentKeyString').set('Value', '')
    ET.SubElement(keymidi, 'IsNote').set('Value', 'false')
    ET.SubElement(keymidi, 'Channel').set('Value', str(channel))
    ET.SubElement(keymidi, 'NoteOrController').set('Value', str(cc_number))
    ET.SubElement(keymidi, 'LowerRangeNote').set('Value', '-1')
    ET.SubElement(keymidi, 'UpperRangeNote').set('Value', '-1')
    ET.SubElement(keymidi, 'ControllerMapMode').set('Value', '0')
    return keymidi


def expand_instrument_rack(rack: ET.Element, cc_number: int = 15, macro_index: int = 6, expand_transpose: bool = True) -> Dict[str, int]:
    """
    Apply expansion transformations to a single InstrumentGroupDevice.

    Args:
        rack: InstrumentGroupDevice XML element
        cc_number: CC number to map to macro
        macro_index: Macro index (0-15) to map CC to
        expand_transpose: If True, expand transpose ranges from ±24 to ±48

    Returns:
        Dictionary of changes made
    """
    changes = {
        'macros_expanded': 0,
        'macro_panel_shown': 0,
        'cc_mappings_added': 0,
        'transpose_ranges_expanded': 0,
        'macro15_modified': 0,
    }

    # 1. Expand macro visibility to 16
    num_visible = rack.find('.//NumVisibleMacroControls')
    if num_visible is not None:
        old_val = num_visible.get('Value')
        if old_val != '16':
            num_visible.set('Value', '16')
            changes['macros_expanded'] = 1

    # 2. Make macro controls visible
    are_visible = rack.find('.//AreMacroControlsVisible')
    if are_visible is not None:
        old_val = are_visible.get('Value')
        if old_val != 'true':
            are_visible.set('Value', 'true')
            changes['macro_panel_shown'] = 1

    # 3. Add CC mapping to specified macro
    macro = rack.find(f'.//MacroControls.{macro_index}')
    if macro is not None:
        existing_keymidi = macro.find('./KeyMidi')
        if existing_keymidi is None:
            # Create and insert KeyMidi before Manual element
            keymidi = create_keymidi_element(cc_number)
            manual = macro.find('./Manual')
            if manual is not None:
                children = list(macro)
                manual_index_pos = children.index(manual)
                macro.insert(manual_index_pos, keymidi)
                changes['cc_mappings_added'] = 1

    # 4. Modify Macro 15
    macro15 = rack.find('.//MacroControls.15')
    if macro15 is not None:
        manual = macro15.find('./Manual')
        if manual is not None:
            old_val = manual.get('Value')
            if old_val != '63.5':
                manual.set('Value', '63.5')
                changes['macro15_modified'] = 1

    macro15_default = rack.find('.//MacroDefaults.15')
    if macro15_default is not None:
        old_val = macro15_default.get('Value')
        if old_val != '-1':
            macro15_default.set('Value', '-1')

    # 5. Set Macro 4 (index 3) to 63.5 on parent DrumGroupDevice only
    if rack.tag == 'DrumGroupDevice':
        macro4 = rack.find('.//MacroControls.3')
        if macro4 is not None:
            manual = macro4.find('./Manual')
            if manual is not None:
                old_val = manual.get('Value')
                if old_val != '63.5':
                    manual.set('Value', '63.5')
                    changes['macro15_modified'] += 1  # Reusing this counter

    # 6. Expand transpose ranges in all chains (if enabled)
    if expand_transpose:
        # Check both Voice_Transpose (DrumCell) and TransposeKey (MultiSampler)
        transpose_params = rack.findall('.//Voice_Transpose') + rack.findall('.//TransposeKey')
        for transpose in transpose_params:
            midi_range = transpose.find('./MidiControllerRange')
            if midi_range is not None:
                min_elem = midi_range.find('./Min')
                max_elem = midi_range.find('./Max')

                if min_elem is not None and max_elem is not None:
                    old_min = min_elem.get('Value')
                    old_max = max_elem.get('Value')

                    # Expand from ±24 to ±48
                    if old_min in ['-24', '-24.0'] and old_max in ['24', '24.0']:
                        min_elem.set('Value', '-48')
                        max_elem.set('Value', '48')
                        changes['transpose_ranges_expanded'] += 1

    return changes


def process_drum_rack(
    input_path: Path,
    output_path: Path,
    cc_number: int = 3,
    macro_index: int = 6,
    expand_transpose: bool = True,
    dry_run: bool = False
) -> Dict:
    """
    Process all InstrumentGroupDevice racks in a drum rack file.

    Args:
        input_path: Input .adg file
        output_path: Output .adg file
        cc_number: CC number to map
        macro_index: Macro index (0-15) to map CC to
        expand_transpose: If True, expand transpose ranges from ±24 to ±48
        dry_run: If True, don't write output file

    Returns:
        Statistics dictionary
    """
    print(f"\n{'='*80}")
    print(f"EXPAND INSTRUMENT RACKS")
    print(f"{'='*80}\n")

    print(f"Input:  {input_path.name}")
    print(f"Output: {output_path.name}")
    print(f"Mapping: CC#{cc_number} → Macro {macro_index + 1}")

    if dry_run:
        print("Mode:   DRY RUN (no files will be modified)\n")

    # Decode drum rack
    xml = decode_adg(input_path)
    root = ET.fromstring(xml)

    # Find all InstrumentGroupDevice elements AND top-level DrumGroupDevice
    instrument_racks = root.findall('.//InstrumentGroupDevice')
    drum_racks = root.findall('.//DrumGroupDevice')

    # Combine both types - we'll process all racks
    all_racks = instrument_racks + drum_racks

    print(f"\nFound {len(instrument_racks)} InstrumentGroupDevice(s) and {len(drum_racks)} DrumGroupDevice(s)")

    if not all_racks:
        print("\n⚠️  No rack devices found in file")
        return {'instrument_racks': 0}

    # Process each rack
    total_stats = {
        'instrument_racks': len(instrument_racks),
        'drum_racks': len(drum_racks),
        'macros_expanded': 0,
        'macro_panel_shown': 0,
        'cc_mappings_added': 0,
        'transpose_ranges_expanded': 0,
        'macro15_modified': 0,
    }

    print("\nProcessing racks...")
    for i, rack in enumerate(all_racks, 1):
        # Find rack name for better reporting
        user_name = rack.find('.//UserName')
        rack_type = rack.tag
        rack_name = user_name.get('Value') if user_name is not None else f'{rack_type} {i}'

        changes = expand_instrument_rack(rack, cc_number, macro_index, expand_transpose)

        # Aggregate stats
        for key in changes:
            total_stats[key] += changes[key]

        # Report changes for this rack
        change_list = []
        if changes['macros_expanded']:
            change_list.append('expanded macros to 16')
        if changes['macro_panel_shown']:
            change_list.append('made macros visible')
        if changes['cc_mappings_added']:
            change_list.append(f'added CC#{cc_number} mapping')
        if changes['transpose_ranges_expanded']:
            change_list.append(f'expanded {changes["transpose_ranges_expanded"]} transpose range(s)')
        if changes['macro15_modified']:
            change_list.append('modified macro 15')

        if change_list:
            print(f"  [{i}] {rack_name}: {', '.join(change_list)}")
        else:
            print(f"  [{i}] {rack_name}: no changes needed")

    # 7. Expand ALL transpose ranges in the entire file (not just within racks)
    if expand_transpose:
        print(f"\nExpanding transpose ranges globally...")
        transpose_params = root.findall('.//Voice_Transpose') + root.findall('.//TransposeKey')

        for transpose in transpose_params:
            midi_range = transpose.find('./MidiControllerRange')
            if midi_range is not None:
                min_elem = midi_range.find('./Min')
                max_elem = midi_range.find('./Max')

                if min_elem is not None and max_elem is not None:
                    old_min = min_elem.get('Value')
                    old_max = max_elem.get('Value')

                    # Expand from ±24 to ±48
                    if old_min in ['-24', '-24.0'] and old_max in ['24', '24.0']:
                        min_elem.set('Value', '-48')
                        max_elem.set('Value', '48')
                        total_stats['transpose_ranges_expanded'] += 1
                        print(f"  ✓ Expanded transpose range: -24/+24 → -48/+48")

    if not dry_run:
        # Convert back to XML string
        xml_output = ET.tostring(root, encoding='unicode', xml_declaration=True)

        # Encode to .adg
        print(f"\nWriting output: {output_path.name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(xml_output, output_path)

    return total_stats


def main():
    parser = argparse.ArgumentParser(
        description='Expand and map InstrumentGroupDevice racks in drum racks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process drum rack with default settings
    python3 expand_instrument_racks.py input.adg output.adg

    # Custom CC and macro mapping
    python3 expand_instrument_racks.py input.adg output.adg --cc 16 --macro 8

    # Preview changes without writing
    python3 expand_instrument_racks.py input.adg output.adg --dry-run

What this script does:
    1. Shows all 16 macros on all racks (NumVisibleMacroControls = 16)
    2. Makes macro panel visible (AreMacroControlsVisible = true)
    3. Adds CC mapping to all racks (default: CC#3 → Macro 7)
    4. Sets Macro 4 to 63.5 on parent DrumGroupDevice
    5. Expands transpose range from ±24 to ±48 semitones globally (TransposeKey, Voice_Transpose)
    6. Sets Macro 15 to 63.5 with no default reset on all racks
        """
    )

    parser.add_argument('input', type=Path, help='Input drum rack (.adg file)')
    parser.add_argument('output', type=Path, help='Output drum rack (.adg file)')
    parser.add_argument('--cc', type=int, default=3, help='CC number to map (default: 3)')
    parser.add_argument('--macro', type=int, default=7,
                       help='Macro index 1-16 to map CC to (default: 7)')
    parser.add_argument('--no-expand-transpose', action='store_true',
                       help='Don\'t expand transpose ranges from ±24 to ±48')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without modifying files')

    args = parser.parse_args()

    # Validate inputs
    if not args.input.exists():
        print(f"✗ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.macro < 1 or args.macro > 16:
        print(f"✗ Error: Macro index must be 1-16, got {args.macro}", file=sys.stderr)
        sys.exit(1)

    if args.cc < 0 or args.cc > 127:
        print(f"✗ Error: CC number must be 0-127, got {args.cc}", file=sys.stderr)
        sys.exit(1)

    # Convert macro from 1-indexed to 0-indexed
    macro_index = args.macro - 1

    try:
        # Process drum rack
        stats = process_drum_rack(
            args.input,
            args.output,
            args.cc,
            macro_index,
            expand_transpose=not args.no_expand_transpose,
            dry_run=args.dry_run
        )

        # Print summary
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}\n")

        print(f"InstrumentGroupDevices processed: {stats['instrument_racks']}")
        print(f"DrumGroupDevices processed:       {stats.get('drum_racks', 0)}")
        print(f"Macros expanded:                  {stats['macros_expanded']}")
        print(f"Macro panels shown:               {stats['macro_panel_shown']}")
        print(f"CC mappings added:                {stats['cc_mappings_added']}")
        print(f"Transpose ranges expanded:        {stats['transpose_ranges_expanded']}")
        print(f"Macro 15 modifications:           {stats['macro15_modified']}")

        if args.dry_run:
            print("\n⚠️  DRY RUN - No files were modified")
        else:
            print(f"\n✓ SUCCESS - Output written to: {args.output}")

        print(f"\n{'='*80}\n")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
