#!/usr/bin/env python3
"""
Apply DrumCell CC Mappings with Neutral Macro Values

Applies MIDI CC mappings to DrumCell parameters AND sets corresponding macro
values so that mappings are "neutral" (don't change the sound when mapped).

For example:
- Transpose = 5 semitones (range -48 to +48)
- Macro CC value = 70 (maps 5 to MIDI 0-127 range)

Usage:
    python3 apply_drumcell_cc_mappings_with_macros.py input.adg output.adg
    python3 apply_drumcell_cc_mappings_with_macros.py input.adg output.adg --template custom.adg
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


@dataclass
class CCMapping:
    """Represents a MIDI CC mapping configuration with parameter range."""
    parameter_path: str  # XPath to parameter (e.g., './/Voice_Transpose')
    cc_number: int
    channel: int = 16
    description: str = ""
    param_min: float = 0.0  # Parameter's min value
    param_max: float = 127.0  # Parameter's max value


# Default mapping template with parameter ranges
DEFAULT_MAPPINGS = [
    CCMapping('.//Voice_Transpose', 3, 16, "Transpose (pitch)", -48.0, 48.0),
    CCMapping('.//Voice_Detune', 4, 16, "Detune (cents)", -50.0, 50.0),
    CCMapping('.//Voice_VelocityToVolume', 12, 16, "Velocity to Volume", 0.0, 1.0),
    CCMapping('.//Voice_ModulationTarget', 14, 16, "Modulation Target", 0.0, 1.0),
    CCMapping('.//Voice_PlaybackStart', 15, 16, "Sample Start", 0.0, 1.0),
    CCMapping('.//Voice_PlaybackLength', 16, 16, "Sample Length", 0.0, 1.0),
    CCMapping('.//Voice_Decay', 17, 16, "Decay Time", 0.0001, 20.0),
    CCMapping('.//Voice_SamplePitch', 18, 16, "Sample Pitch", -48.0, 48.0),
    CCMapping('.//Volume/Manual', 7, 16, "Volume", 0.0, 1.0),
    CCMapping('.//Pan/Manual', 10, 16, "Pan", -1.0, 1.0),
]


def get_parameter_range(parameter: ET.Element) -> Tuple[float, float]:
    """
    Extract parameter min/max range from MidiControllerRange element.

    Args:
        parameter: Parameter element

    Returns:
        (min_value, max_value) tuple
    """
    midi_range = parameter.find('./MidiControllerRange')
    if midi_range is not None:
        min_elem = midi_range.find('./Min')
        max_elem = midi_range.find('./Max')

        if min_elem is not None and max_elem is not None:
            try:
                min_val = float(min_elem.get('Value', '0'))
                max_val = float(max_elem.get('Value', '127'))
                return (min_val, max_val)
            except (ValueError, TypeError):
                pass

    return (0.0, 127.0)


def parameter_to_cc_value(param_value: float, param_min: float, param_max: float) -> int:
    """
    Convert parameter value to MIDI CC value (0-127).

    Args:
        param_value: Current parameter value
        param_min: Parameter minimum value
        param_max: Parameter maximum value

    Returns:
        MIDI CC value (0-127)
    """
    # Normalize to 0-1 range
    if param_max == param_min:
        normalized = 0.5
    else:
        normalized = (param_value - param_min) / (param_max - param_min)

    # Clamp to 0-1
    normalized = max(0.0, min(1.0, normalized))

    # Scale to MIDI CC range (0-127)
    cc_value = int(round(normalized * 127.0))

    return cc_value


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


def apply_cc_mapping_to_parameter(
    parameter: ET.Element,
    cc_number: int,
    channel: int = 16,
    set_neutral: bool = True
) -> Tuple[bool, Optional[int]]:
    """
    Apply MIDI CC mapping to a parameter element.

    Args:
        parameter: Parameter element (e.g., Voice_Transpose)
        cc_number: MIDI CC number
        channel: MIDI channel
        set_neutral: If True, calculate and return neutral CC value

    Returns:
        (was_added, neutral_cc_value) tuple
    """
    # Get current parameter value
    neutral_cc_value = None

    if set_neutral:
        manual_elem = parameter.find('./Manual')
        if manual_elem is not None:
            try:
                param_value = float(manual_elem.get('Value', '0'))
                param_min, param_max = get_parameter_range(parameter)
                neutral_cc_value = parameter_to_cc_value(param_value, param_min, param_max)
            except (ValueError, TypeError):
                pass

    # Check if KeyMidi already exists
    existing_keymidi = parameter.find('./KeyMidi')

    if existing_keymidi is not None:
        # Update existing mapping
        cc_elem = existing_keymidi.find('./NoteOrController')
        if cc_elem is not None:
            old_cc = cc_elem.get('Value')
            cc_elem.set('Value', str(cc_number))

            channel_elem = existing_keymidi.find('./Channel')
            if channel_elem is not None:
                channel_elem.set('Value', str(channel))

            return (old_cc != str(cc_number), neutral_cc_value)
    else:
        # Create new KeyMidi element
        keymidi = create_keymidi_element(cc_number, channel)

        # Insert KeyMidi before Manual element (proper Ableton ordering)
        manual_elem = parameter.find('./Manual')
        if manual_elem is not None:
            children = list(parameter)
            manual_index = children.index(manual_elem)
            parameter.insert(manual_index, keymidi)
        else:
            parameter.insert(0, keymidi)

        return (True, neutral_cc_value)

    return (False, neutral_cc_value)


def find_or_create_macro_for_cc(
    root: ET.Element,
    cc_number: int,
    channel: int
) -> Optional[ET.Element]:
    """
    Find rack macro control that's mapped to a specific CC.

    Args:
        root: XML root element
        cc_number: MIDI CC number to find
        channel: MIDI channel

    Returns:
        MacroControls element or None
    """
    # Find InstrumentGroupDevice (the rack)
    rack = root.find('.//InstrumentGroupDevice')
    if rack is None:
        return None

    # Search MacroControls.0 through MacroControls.15
    for i in range(16):
        macro = rack.find(f'.//MacroControls.{i}')
        if macro is not None:
            keymidi = macro.find('./KeyMidi')
            if keymidi is not None:
                cc_elem = keymidi.find('./NoteOrController')
                channel_elem = keymidi.find('./Channel')

                if cc_elem is not None and channel_elem is not None:
                    if (int(cc_elem.get('Value', '-1')) == cc_number and
                        int(channel_elem.get('Value', '-1')) == channel):
                        return macro

    return None


def set_macro_value(macro: ET.Element, value: float):
    """
    Set macro's Manual value.

    Args:
        macro: MacroControls element
        value: Value to set (0-127)
    """
    manual = macro.find('./Manual')
    if manual is not None:
        manual.set('Value', str(value))


def extract_mappings_from_template(template_path: Path) -> List[CCMapping]:
    """Extract CC mappings from a template drum rack."""
    print(f"Extracting mappings from template: {template_path.name}")

    xml = decode_adg(template_path)
    root = ET.fromstring(xml)

    mappings = []

    # Find first DrumCell with KeyMidi mappings
    drumcells = root.findall('.//DrumCell')

    if not drumcells:
        print("  ⚠️  No DrumCell devices found in template")
        return DEFAULT_MAPPINGS

    # Analyze first DrumCell
    drumcell = drumcells[0]

    param_names = [
        'Voice_Transpose',
        'Voice_Detune',
        'Voice_VelocityToVolume',
        'Voice_ModulationTarget',
        'Voice_PlaybackStart',
        'Voice_PlaybackLength',
        'Voice_Decay',
        'Voice_SamplePitch',
    ]

    for param_name in param_names:
        param = drumcell.find(f'.//{param_name}')
        if param is not None:
            keymidi = param.find('./KeyMidi')
            if keymidi is not None:
                cc_elem = keymidi.find('./NoteOrController')
                channel_elem = keymidi.find('./Channel')

                if cc_elem is not None and channel_elem is not None:
                    cc_number = int(cc_elem.get('Value'))
                    channel = int(channel_elem.get('Value'))

                    # Get parameter range
                    param_min, param_max = get_parameter_range(param)

                    mappings.append(CCMapping(
                        f'.//{param_name}',
                        cc_number,
                        channel,
                        param_name.replace('_', ' '),
                        param_min,
                        param_max
                    ))

    if mappings:
        print(f"  ✓ Extracted {len(mappings)} mappings from template")
        for mapping in mappings:
            print(f"    • {mapping.description}: CC#{mapping.cc_number} "
                  f"(Ch {mapping.channel}, range {mapping.param_min:.1f}-{mapping.param_max:.1f})")
    else:
        print("  ⚠️  No mappings found in template, using defaults")
        return DEFAULT_MAPPINGS

    return mappings


def process_drum_rack(
    input_path: Path,
    output_path: Path,
    mappings: List[CCMapping],
    set_macros: bool = True,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Apply CC mappings to all DrumCell devices in a drum rack.

    Args:
        input_path: Input .adg file
        output_path: Output .adg file
        mappings: List of CCMapping objects to apply
        set_macros: If True, set neutral macro values
        dry_run: If True, don't write output file

    Returns:
        Statistics dictionary
    """
    print(f"\n{'='*80}")
    print(f"PROCESSING DRUM RACK")
    print(f"{'='*80}\n")

    print(f"Input:  {input_path.name}")
    print(f"Output: {output_path.name}")

    if set_macros:
        print(f"Mode:   Set neutral macro values")

    if dry_run:
        print("Mode:   DRY RUN (no files will be modified)")

    # Decode rack
    xml = decode_adg(input_path)
    root = ET.fromstring(xml)

    # Find all DrumCell devices
    drumcells = root.findall('.//DrumCell')

    print(f"\nFound {len(drumcells)} DrumCell devices")

    if not drumcells:
        print("\n⚠️  No DrumCell devices found in rack")
        return {'drumcells': 0, 'mappings_added': 0, 'mappings_updated': 0}

    stats = {
        'drumcells': len(drumcells),
        'mappings_added': 0,
        'mappings_updated': 0,
        'mappings_skipped': 0,
        'macros_set': 0,
    }

    # Track CC values for macro setting (average across all pads)
    cc_values: Dict[int, List[int]] = {}

    print(f"\nApplying {len(mappings)} CC mappings per DrumCell...")

    # Process each DrumCell
    for i, drumcell in enumerate(drumcells, 1):
        if dry_run and i <= 3:  # Show first 3 in dry run
            print(f"\n[{i}/{len(drumcells)}] DrumCell {i}")

        # Apply each mapping
        for mapping in mappings:
            parameter = drumcell.find(mapping.parameter_path)

            if parameter is not None:
                was_added, neutral_cc = apply_cc_mapping_to_parameter(
                    parameter,
                    mapping.cc_number,
                    mapping.channel,
                    set_neutral=set_macros
                )

                if was_added:
                    stats['mappings_added'] += 1
                else:
                    stats['mappings_updated'] += 1

                # Track neutral CC value for this mapping
                if neutral_cc is not None:
                    if mapping.cc_number not in cc_values:
                        cc_values[mapping.cc_number] = []
                    cc_values[mapping.cc_number].append(neutral_cc)

                if dry_run and i <= 3:
                    param_val = parameter.find('./Manual').get('Value')
                    if neutral_cc is not None:
                        print(f"  ✓ {mapping.description}: CC#{mapping.cc_number} "
                              f"(value={param_val} → CC={neutral_cc})")
                    else:
                        print(f"  ✓ {mapping.description}: CC#{mapping.cc_number}")
            else:
                stats['mappings_skipped'] += 1

    # Set macro values (use average of all pad values)
    if set_macros and cc_values:
        print(f"\nSetting neutral macro values...")

        for cc_num, values in cc_values.items():
            avg_value = sum(values) / len(values)

            # Find corresponding macro
            macro = find_or_create_macro_for_cc(root, cc_num, mappings[0].channel)

            if macro is not None:
                set_macro_value(macro, avg_value)
                stats['macros_set'] += 1

                # Find mapping description
                desc = next((m.description for m in mappings if m.cc_number == cc_num), f"CC#{cc_num}")
                print(f"  ✓ Set macro for CC#{cc_num} ({desc}): {avg_value:.1f}")
            else:
                if dry_run:
                    print(f"  ⚠️  No macro found for CC#{cc_num}")

    if not dry_run:
        # Convert back to XML string
        xml_output = ET.tostring(root, encoding='unicode', xml_declaration=True)

        # Encode to .adg
        print(f"\nWriting output: {output_path.name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(xml_output, output_path)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Apply MIDI CC mappings with neutral macro values to drum racks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Apply mappings with neutral macro values
    python3 apply_drumcell_cc_mappings_with_macros.py input.adg output.adg

    # Use custom template
    python3 apply_drumcell_cc_mappings_with_macros.py input.adg output.adg \\
        --template /Users/Music/Desktop/mapped.adg

    # Don't set macro values (just add CC mappings)
    python3 apply_drumcell_cc_mappings_with_macros.py input.adg output.adg --no-macros

    # Dry run
    python3 apply_drumcell_cc_mappings_with_macros.py input.adg output.adg --dry-run
        """
    )

    parser.add_argument('input', type=Path, help='Input drum rack (.adg file)')
    parser.add_argument('output', type=Path, help='Output drum rack (.adg file)')
    parser.add_argument('--template', type=Path, help='Template .adg file to extract mappings from')
    parser.add_argument('--channel', type=int, default=16, help='MIDI channel (1-16, default: 16)')
    parser.add_argument('--no-macros', action='store_true', help='Don\'t set neutral macro values')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')

    args = parser.parse_args()

    # Validate inputs
    if not args.input.exists():
        print(f"✗ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.template and not args.template.exists():
        print(f"✗ Error: Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    try:
        # Extract mappings from template or use defaults
        if args.template:
            mappings = extract_mappings_from_template(args.template)
        else:
            print("Using default CC mappings")
            mappings = DEFAULT_MAPPINGS

        # Override channel if specified
        if args.channel != 16:
            print(f"Overriding channel to: {args.channel}")
            for mapping in mappings:
                mapping.channel = args.channel

        # Process drum rack
        stats = process_drum_rack(
            args.input,
            args.output,
            mappings,
            set_macros=not args.no_macros,
            dry_run=args.dry_run
        )

        # Print summary
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}\n")

        print(f"DrumCell devices:    {stats['drumcells']}")
        print(f"Mappings added:      {stats['mappings_added']}")
        print(f"Mappings updated:    {stats['mappings_updated']}")
        print(f"Mappings skipped:    {stats['mappings_skipped']}")
        print(f"Macros set:          {stats.get('macros_set', 0)}")
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
