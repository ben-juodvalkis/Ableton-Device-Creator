#!/usr/bin/env python3
"""
Apply Template Mappings to Drum Rack

Extracts CC mappings and macro values from a template drum rack and applies
them to a target drum rack, preserving each pad's unique parameter values.

This script:
1. Extracts CC mappings from template (parameter → CC#)
2. Extracts macro values from template
3. Applies CC mappings to all DrumCells in target
4. Sets macro Manual and Default values in target drum racks

Works with:
- Simple DrumGroupDevice racks
- Nested InstrumentGroupDevice with multiple drum rack chains
- Dual-chain 32-pad performance racks

Usage:
    python3 apply_template_mappings.py input.adg output.adg --template map.adg
    python3 apply_template_mappings.py input.adg output.adg --template map.adg --dry-run
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def extract_cc_mappings(template_path: Path) -> Dict[str, int]:
    """
    Extract parameter → CC mappings from template.

    Returns:
        Dict mapping parameter names to CC numbers
    """
    xml = decode_adg(template_path)
    root = ET.fromstring(xml)

    mappings = {}

    # Find all KeyMidi elements
    all_keymidi = root.findall('.//KeyMidi')

    for keymidi in all_keymidi:
        # Find parent parameter
        for elem in root.iter():
            if keymidi in list(elem):
                param_name = elem.tag

                cc = keymidi.find('./NoteOrController')
                if cc is not None and param_name not in mappings:
                    mappings[param_name] = int(cc.get('Value'))
                break

    return mappings


def extract_macro_values(template_path: Path) -> List[float]:
    """
    Extract macro Manual values from template.

    Returns:
        List of 16 macro values
    """
    xml = decode_adg(template_path)
    root = ET.fromstring(xml)

    # Find first DrumGroupDevice
    drum_rack = root.find('.//DrumGroupDevice')

    if drum_rack is None:
        return [0] * 16

    macro_values = []

    for i in range(16):
        macro = drum_rack.find(f'.//MacroControls.{i}')
        if macro is not None:
            manual = macro.find('./Manual')
            if manual is not None:
                try:
                    val = float(manual.get('Value', '0'))
                    macro_values.append(val)
                except ValueError:
                    macro_values.append(0.0)
            else:
                macro_values.append(0.0)
        else:
            macro_values.append(0.0)

    return macro_values


def extract_effect_on_thresholds(template_path: Path) -> Tuple[int, int]:
    """
    Extract Effect_On MidiCCOnOffThresholds from template.

    Returns:
        (min, max) tuple
    """
    xml = decode_adg(template_path)
    root = ET.fromstring(xml)

    # Find first DrumCell with Effect_On
    drumcell = root.find('.//DrumCell')
    if drumcell is not None:
        effect_on = drumcell.find('.//Effect_On')
        if effect_on is not None:
            thresholds = effect_on.find('.//MidiCCOnOffThresholds')
            if thresholds is not None:
                min_elem = thresholds.find('./Min')
                max_elem = thresholds.find('./Max')
                if min_elem is not None and max_elem is not None:
                    return (int(min_elem.get('Value')), int(max_elem.get('Value')))

    # Default thresholds
    return (64, 127)


def get_parameter_range(parameter: ET.Element) -> Tuple[float, float]:
    """Extract parameter min/max range."""
    midi_range = parameter.find('./MidiControllerRange')
    if midi_range is not None:
        min_elem = midi_range.find('./Min')
        max_elem = midi_range.find('./Max')
        if min_elem is not None and max_elem is not None:
            try:
                return (float(min_elem.get('Value', '0')), float(max_elem.get('Value', '127')))
            except (ValueError, TypeError):
                pass
    return (0.0, 127.0)


def parameter_to_cc_value(param_value: float, param_min: float, param_max: float) -> int:
    """Convert parameter value to MIDI CC value (0-127)."""
    if param_max == param_min:
        normalized = 0.5
    else:
        normalized = (param_value - param_min) / (param_max - param_min)
    normalized = max(0.0, min(1.0, normalized))
    return int(round(normalized * 127.0))


def create_keymidi_element(cc_number: int, channel: int = 16) -> ET.Element:
    """Create a KeyMidi XML element."""
    keymidi = ET.Element('KeyMidi')
    ET.SubElement(keymidi, 'PersistentKeyString').set('Value', '')
    ET.SubElement(keymidi, 'IsNote').set('Value', 'false')
    ET.SubElement(keymidi, 'Channel').set('Value', str(channel))
    ET.SubElement(keymidi, 'NoteOrController').set('Value', str(cc_number))
    ET.SubElement(keymidi, 'LowerRangeNote').set('Value', '-1')
    ET.SubElement(keymidi, 'UpperRangeNote').set('Value', '-1')
    ET.SubElement(keymidi, 'ControllerMapMode').set('Value', '0')
    return keymidi


def apply_cc_mapping(
    parameter: ET.Element,
    cc_number: int,
    channel: int = 16,
    is_boolean: bool = False
) -> Tuple[bool, Optional[int]]:
    """
    Apply CC mapping to parameter and calculate neutral CC value.

    Args:
        parameter: Parameter element
        cc_number: MIDI CC number
        channel: MIDI channel
        is_boolean: True if parameter is boolean (Effect_On)

    Returns:
        (was_added, neutral_cc_value) tuple
    """
    manual_elem = parameter.find('./Manual')
    if manual_elem is None:
        return (False, None)

    # Calculate neutral CC value
    neutral_cc_value = None

    if is_boolean:
        # Boolean parameter
        val_str = manual_elem.get('Value', 'false')
        neutral_cc_value = 127 if val_str.lower() == 'true' else 0
    else:
        # Numeric parameter
        try:
            param_value = float(manual_elem.get('Value', '0'))
            param_min, param_max = get_parameter_range(parameter)
            neutral_cc_value = parameter_to_cc_value(param_value, param_min, param_max)
        except (ValueError, TypeError):
            pass

    # Check if KeyMidi already exists
    existing_keymidi = parameter.find('./KeyMidi')

    if existing_keymidi is not None:
        # Update existing
        cc_elem = existing_keymidi.find('./NoteOrController')
        if cc_elem is not None:
            old_cc = cc_elem.get('Value')
            cc_elem.set('Value', str(cc_number))
            return (old_cc != str(cc_number), neutral_cc_value)
    else:
        # Create new
        keymidi = create_keymidi_element(cc_number, channel)
        children = list(parameter)
        manual_index = children.index(manual_elem)
        parameter.insert(manual_index, keymidi)
        return (True, neutral_cc_value)

    return (False, neutral_cc_value)


def apply_template_to_rack(
    input_path: Path,
    output_path: Path,
    template_path: Path,
    channel: int = 16,
    dry_run: bool = False
) -> Dict:
    """Apply template mappings and macro values to target rack."""

    print(f"\n{'='*80}")
    print(f"APPLY TEMPLATE MAPPINGS")
    print(f"{'='*80}\n")

    print(f"Template: {template_path.name}")
    print(f"Input:    {input_path.name}")
    print(f"Output:   {output_path.name}")

    if dry_run:
        print("Mode:     DRY RUN\n")

    # Extract from template
    print("Extracting from template...")
    cc_mappings = extract_cc_mappings(template_path)
    macro_values = extract_macro_values(template_path)
    effect_on_thresholds = extract_effect_on_thresholds(template_path)

    print(f"  ✓ Found {len(cc_mappings)} CC mappings")
    print(f"  ✓ Extracted 16 macro values")
    print(f"  ✓ Effect_On thresholds: Min={effect_on_thresholds[0]}, Max={effect_on_thresholds[1]}")

    # Load target rack
    xml = decode_adg(input_path)
    root = ET.fromstring(xml)

    # Find all DrumCells
    drumcells = root.findall('.//DrumCell')
    print(f"\nFound {len(drumcells)} DrumCell devices in target")

    stats = {
        'drumcells': len(drumcells),
        'mappings_added': 0,
        'mappings_updated': 0,
        'effect_on_updated': 0,
    }

    # Apply CC mappings to all DrumCells
    print(f"\nApplying {len(cc_mappings)} CC mappings to each DrumCell...")

    for drumcell in drumcells:
        for param_name, cc_num in cc_mappings.items():
            is_boolean = param_name == 'Effect_On'
            param = drumcell.find(f'.//{param_name}')

            if param is not None:
                was_added, _ = apply_cc_mapping(param, cc_num, channel, is_boolean)

                if was_added:
                    stats['mappings_added'] += 1
                else:
                    stats['mappings_updated'] += 1

                # Update Effect_On thresholds
                if is_boolean:
                    thresholds = param.find('.//MidiCCOnOffThresholds')
                    if thresholds is not None:
                        min_elem = thresholds.find('./Min')
                        max_elem = thresholds.find('./Max')
                        if min_elem is not None:
                            min_elem.set('Value', str(effect_on_thresholds[0]))
                        if max_elem is not None:
                            max_elem.set('Value', str(effect_on_thresholds[1]))
                        stats['effect_on_updated'] += 1

    # Set macro values for all DrumGroupDevices
    drum_racks = root.findall('.//DrumGroupDevice')
    print(f"\nSetting macro values for {len(drum_racks)} DrumGroupDevice(s)...")

    for rack_num, drum_rack in enumerate(drum_racks, 1):
        for i in range(16):
            # Set Manual value
            macro = drum_rack.find(f'.//MacroControls.{i}')
            if macro is not None:
                manual = macro.find('./Manual')
                if manual is not None:
                    manual.set('Value', str(macro_values[i]))

            # Set Default value
            default_elem = drum_rack.find(f'.//MacroDefaults.{i}')
            if default_elem is not None:
                default_elem.set('Value', str(macro_values[i]))

        print(f"  ✓ Drum Rack {rack_num}: Set all 16 macros")

    if not dry_run:
        # Save output
        xml_output = ET.tostring(root, encoding='unicode', xml_declaration=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(xml_output, output_path)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Apply template CC mappings and macro values to drum rack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Apply template to a drum rack
    python3 apply_template_mappings.py input.adg output.adg --template map.adg

    # Dry run to preview
    python3 apply_template_mappings.py input.adg output.adg --template map.adg --dry-run

    # Custom MIDI channel
    python3 apply_template_mappings.py input.adg output.adg --template map.adg --channel 1

What this script does:
    1. Reads CC mappings from template (which parameters map to which CCs)
    2. Reads macro values from template
    3. Applies CC mappings to ALL DrumCells in target (preserving values)
    4. Sets macro Manual and Default values for all DrumGroupDevices in target
        """
    )

    parser.add_argument('input', type=Path, help='Input drum rack (.adg file)')
    parser.add_argument('output', type=Path, help='Output drum rack (.adg file)')
    parser.add_argument('--template', type=Path, required=True, help='Template .adg file')
    parser.add_argument('--channel', type=int, default=16, help='MIDI channel (1-16, default: 16)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without modifying files')

    args = parser.parse_args()

    # Validate
    if not args.input.exists():
        print(f"✗ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.template.exists():
        print(f"✗ Error: Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    try:
        stats = apply_template_to_rack(
            args.input,
            args.output,
            args.template,
            args.channel,
            args.dry_run
        )

        # Summary
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}\n")

        print(f"DrumCell devices:    {stats['drumcells']}")
        print(f"Mappings added:      {stats['mappings_added']}")
        print(f"Mappings updated:    {stats['mappings_updated']}")
        print(f"Effect_On updated:   {stats['effect_on_updated']}")
        print(f"Total operations:    {stats['mappings_added'] + stats['mappings_updated']}")

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
