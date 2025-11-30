#!/usr/bin/env python3
"""
Apply CC Mappings While Preserving Current Values

Maps MIDI CCs to DrumCell parameters and sets the initial CC value to match
the current parameter value, so each pad keeps its unique sound.

For example, if Pad 1 has Transpose=5 and Pad 2 has Transpose=-3:
- Both get mapped to CC#3
- But Pad 1's initial CC value is calculated for +5 semitones
- And Pad 2's initial CC value is calculated for -3 semitones

This way, moving the controller from these starting positions will modulate
from the original sound, not reset it.

Usage:
    python3 apply_cc_mappings_preserve_values.py input.adg output.adg
    python3 apply_cc_mappings_preserve_values.py input.adg output.adg --cc-map "transpose:3,decay:17"
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


@dataclass
class ParameterMapping:
    """Parameter to CC mapping with range information."""
    param_path: str
    cc_number: int
    param_name: str
    channel: int = 16


# Default CC mappings
DEFAULT_CC_MAP = {
    'Voice_Transpose': 3,
    'Voice_Detune': 4,
    'Voice_VelocityToVolume': 12,
    'Voice_ModulationTarget': 14,
    'Voice_PlaybackStart': 15,
    'Voice_PlaybackLength': 16,
    'Voice_Decay': 17,
    'Voice_SamplePitch': 18,
}


def get_parameter_range(parameter: ET.Element) -> Tuple[float, float]:
    """Extract parameter min/max range from MidiControllerRange."""
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

    This is the key calculation that preserves the current parameter value.
    """
    if param_max == param_min:
        normalized = 0.5
    else:
        normalized = (param_value - param_min) / (param_max - param_min)

    # Clamp to 0-1
    normalized = max(0.0, min(1.0, normalized))

    # Scale to MIDI CC range
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


def apply_cc_mapping_with_value_preservation(
    parameter: ET.Element,
    cc_number: int,
    channel: int = 16
) -> Tuple[bool, Optional[int], Optional[float]]:
    """
    Apply CC mapping to parameter and calculate neutral CC value.

    Returns:
        (was_added, neutral_cc_value, param_value) tuple
    """
    # Get current parameter value
    manual_elem = parameter.find('./Manual')
    if manual_elem is None:
        return (False, None, None)

    try:
        param_value = float(manual_elem.get('Value', '0'))
    except (ValueError, TypeError):
        return (False, None, None)

    # Get parameter range
    param_min, param_max = get_parameter_range(parameter)

    # Calculate what CC value matches current parameter value
    neutral_cc_value = parameter_to_cc_value(param_value, param_min, param_max)

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

            return (old_cc != str(cc_number), neutral_cc_value, param_value)
    else:
        # Create new KeyMidi element
        keymidi = create_keymidi_element(cc_number, channel)

        # Insert before Manual element (proper Ableton ordering)
        children = list(parameter)
        manual_index = children.index(manual_elem)
        parameter.insert(manual_index, keymidi)

        return (True, neutral_cc_value, param_value)

    return (False, neutral_cc_value, param_value)


def process_drum_rack(
    input_path: Path,
    output_path: Path,
    cc_map: Dict[str, int],
    channel: int = 16,
    dry_run: bool = False
) -> Dict:
    """
    Apply CC mappings to all DrumCell devices while preserving values.

    Returns:
        Statistics and per-pad CC values
    """
    print(f"\n{'='*80}")
    print(f"APPLY CC MAPPINGS (VALUE-PRESERVING)")
    print(f"{'='*80}\n")

    print(f"Input:  {input_path.name}")
    print(f"Output: {output_path.name}")

    if dry_run:
        print("Mode:   DRY RUN (no files will be modified)")

    # Decode rack
    xml = decode_adg(input_path)
    root = ET.fromstring(xml)

    # Find all DrumCell devices
    drumcells = root.findall('.//DrumCell')

    print(f"\nFound {len(drumcells)} DrumCell devices")
    print(f"Applying {len(cc_map)} CC mappings per device\n")

    if not drumcells:
        print("⚠️  No DrumCell devices found in rack")
        return {'error': 'No DrumCell devices found'}

    stats = {
        'drumcells': len(drumcells),
        'mappings_added': 0,
        'mappings_updated': 0,
        'mappings_skipped': 0,
        'pad_data': []
    }

    # Process each DrumCell
    for i, drumcell in enumerate(drumcells, 1):
        pad_info = {
            'pad_number': i,
            'cc_values': {}
        }

        # Get pad name for display
        pad_name = None
        user_name = drumcell.find('.//UserName')
        if user_name is not None:
            pad_name = user_name.get('Value', '')

        if not pad_name:
            file_ref = drumcell.find('.//FileRef/Name')
            if file_ref is not None:
                pad_name = file_ref.get('Value', '')

        if dry_run:
            print(f"[Pad {i:2d}] {pad_name or '(unnamed)'}")

        # Apply each CC mapping
        for param_name, cc_num in cc_map.items():
            param = drumcell.find(f'.//{param_name}')

            if param is not None:
                was_added, neutral_cc, param_val = apply_cc_mapping_with_value_preservation(
                    param,
                    cc_num,
                    channel
                )

                if was_added:
                    stats['mappings_added'] += 1
                else:
                    stats['mappings_updated'] += 1

                # Store CC value info
                if neutral_cc is not None:
                    pad_info['cc_values'][cc_num] = {
                        'parameter': param_name,
                        'param_value': param_val,
                        'cc_value': neutral_cc
                    }

                    if dry_run:
                        param_min, param_max = get_parameter_range(param)
                        print(f"  CC#{cc_num:3d} {param_name:25s} = {param_val:8.3f} "
                              f"(range {param_min:.1f}-{param_max:.1f}) → CC={neutral_cc:3d}")
            else:
                stats['mappings_skipped'] += 1

        stats['pad_data'].append(pad_info)

        if dry_run:
            print()

    if not dry_run:
        # Convert back to XML string
        xml_output = ET.tostring(root, encoding='unicode', xml_declaration=True)

        # Encode to .adg
        print(f"Writing output: {output_path.name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(xml_output, output_path)

    return stats


def generate_controller_preset_file(stats: Dict, output_path: Path):
    """
    Generate a text file showing the CC values for each pad.

    This can be used to program a hardware controller.
    """
    lines = []
    lines.append("=" * 80)
    lines.append("MIDI CONTROLLER PRESET - PER-PAD CC VALUES")
    lines.append("=" * 80)
    lines.append("\nEach pad has unique CC values that preserve its original sound.\n")

    # Find all unique CCs
    all_ccs = set()
    for pad in stats['pad_data']:
        all_ccs.update(pad['cc_values'].keys())

    sorted_ccs = sorted(all_ccs)

    # Header
    lines.append(f"{'Pad':<6} " + " ".join(f"CC{cc:>3d}" for cc in sorted_ccs))
    lines.append("-" * 80)

    # Each pad
    for pad in stats['pad_data']:
        pad_num = pad['pad_number']
        cc_vals = " ".join(
            f"{pad['cc_values'].get(cc, {}).get('cc_value', '---'):>6}"
            for cc in sorted_ccs
        )
        lines.append(f"Pad {pad_num:<2d} {cc_vals}")

    lines.append("\n" + "=" * 80)
    lines.append("CC PARAMETER NAMES")
    lines.append("=" * 80)

    # Show what each CC controls
    if stats['pad_data']:
        first_pad = stats['pad_data'][0]
        for cc in sorted_ccs:
            if cc in first_pad['cc_values']:
                param_name = first_pad['cc_values'][cc]['parameter']
                lines.append(f"CC#{cc:3d} = {param_name}")

    lines.append("\n" + "=" * 80)

    output_path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(
        description='Apply CC mappings while preserving current parameter values',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use default CC mappings
    python3 apply_cc_mappings_preserve_values.py input.adg output.adg

    # Custom CC mappings
    python3 apply_cc_mappings_preserve_values.py input.adg output.adg \\
        --cc-map "Voice_Transpose:3,Voice_Decay:17,Voice_PlaybackStart:15"

    # Generate controller preset file
    python3 apply_cc_mappings_preserve_values.py input.adg output.adg \\
        --preset-file controller_preset.txt

    # Dry run to see what would happen
    python3 apply_cc_mappings_preserve_values.py input.adg output.adg --dry-run

Default CC Mappings:
    Voice_Transpose         → CC#3
    Voice_Detune            → CC#4
    Voice_VelocityToVolume  → CC#12
    Voice_ModulationTarget  → CC#14
    Voice_PlaybackStart     → CC#15
    Voice_PlaybackLength    → CC#16
    Voice_Decay             → CC#17
    Voice_SamplePitch       → CC#18
        """
    )

    parser.add_argument('input', type=Path, help='Input drum rack (.adg file)')
    parser.add_argument('output', type=Path, help='Output drum rack (.adg file)')
    parser.add_argument(
        '--cc-map',
        type=str,
        help='Custom CC mappings (format: "param1:cc1,param2:cc2")'
    )
    parser.add_argument(
        '--channel',
        type=int,
        default=16,
        help='MIDI channel (1-16, default: 16)'
    )
    parser.add_argument(
        '--preset-file',
        type=Path,
        help='Generate controller preset file with per-pad CC values'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without modifying files'
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.input.exists():
        print(f"✗ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Parse CC map
    if args.cc_map:
        cc_map = {}
        for mapping in args.cc_map.split(','):
            param, cc = mapping.split(':')
            cc_map[param.strip()] = int(cc.strip())
    else:
        cc_map = DEFAULT_CC_MAP

    try:
        # Process drum rack
        stats = process_drum_rack(
            args.input,
            args.output,
            cc_map,
            args.channel,
            args.dry_run
        )

        if 'error' in stats:
            print(f"\n✗ Error: {stats['error']}")
            sys.exit(1)

        # Print summary
        print(f"{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}\n")

        print(f"DrumCell devices:    {stats['drumcells']}")
        print(f"Mappings added:      {stats['mappings_added']}")
        print(f"Mappings updated:    {stats['mappings_updated']}")
        print(f"Mappings skipped:    {stats['mappings_skipped']}")
        print(f"Total operations:    {stats['mappings_added'] + stats['mappings_updated']}")

        # Generate preset file
        if args.preset_file and not args.dry_run:
            generate_controller_preset_file(stats, args.preset_file)
            print(f"\n✓ Controller preset file: {args.preset_file}")

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
