#!/usr/bin/env python3
"""
Generate CC Preset Map

Analyzes a drum rack and generates a "preset map" showing what MIDI CC values
should be set on your controller to match the current parameter values (neutral state).

Useful for:
- Setting up hardware controllers
- Creating controller presets
- Understanding current parameter states

Usage:
    python3 generate_cc_preset_map.py input.adg
    python3 generate_cc_preset_map.py input.adg --output preset_map.txt
    python3 generate_cc_preset_map.py input.adg --format json
"""

import argparse
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.decoder import decode_adg


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


def analyze_drum_rack(input_path: Path) -> Dict:
    """Analyze drum rack and extract CC mappings with current values."""
    xml = decode_adg(input_path)
    root = ET.fromstring(xml)

    drumcells = root.findall('.//DrumCell')

    if not drumcells:
        return {'error': 'No DrumCell devices found'}

    # Track CC mappings and their values across all pads
    cc_data = defaultdict(lambda: {
        'param_name': '',
        'values': [],
        'cc_values': [],
        'param_range': (0, 0),
        'channel': 16
    })

    for i, drumcell in enumerate(drumcells, 1):
        # Check common parameters
        params_to_check = [
            ('Voice_Transpose', 'Transpose'),
            ('Voice_Detune', 'Detune'),
            ('Voice_VelocityToVolume', 'Velocity→Volume'),
            ('Voice_ModulationTarget', 'Mod Target'),
            ('Voice_PlaybackStart', 'Sample Start'),
            ('Voice_PlaybackLength', 'Sample Length'),
            ('Voice_Decay', 'Decay'),
            ('Voice_SamplePitch', 'Sample Pitch'),
        ]

        for param_name, display_name in params_to_check:
            param = drumcell.find(f'.//{param_name}')
            if param is not None:
                keymidi = param.find('./KeyMidi')
                manual = param.find('./Manual')

                if keymidi is not None and manual is not None:
                    cc_elem = keymidi.find('./NoteOrController')
                    channel_elem = keymidi.find('./Channel')

                    if cc_elem is not None:
                        cc_num = int(cc_elem.get('Value'))
                        param_value = float(manual.get('Value', '0'))
                        param_min, param_max = get_parameter_range(param)
                        cc_value = parameter_to_cc_value(param_value, param_min, param_max)

                        cc_data[cc_num]['param_name'] = display_name
                        cc_data[cc_num]['values'].append(param_value)
                        cc_data[cc_num]['cc_values'].append(cc_value)
                        cc_data[cc_num]['param_range'] = (param_min, param_max)

                        if channel_elem is not None:
                            cc_data[cc_num]['channel'] = int(channel_elem.get('Value'))

    # Calculate statistics
    result = {
        'file': input_path.name,
        'drumcell_count': len(drumcells),
        'cc_mappings': {}
    }

    for cc_num, data in sorted(cc_data.items()):
        values = data['values']
        cc_values = data['cc_values']

        result['cc_mappings'][cc_num] = {
            'parameter': data['param_name'],
            'channel': data['channel'],
            'param_range': data['param_range'],
            'avg_param_value': sum(values) / len(values),
            'avg_cc_value': int(round(sum(cc_values) / len(cc_values))),
            'min_cc_value': min(cc_values),
            'max_cc_value': max(cc_values),
            'unique_values': len(set(cc_values)),
            'all_same': len(set(cc_values)) == 1,
        }

    return result


def format_text_report(data: Dict) -> str:
    """Format analysis as human-readable text report."""
    if 'error' in data:
        return f"Error: {data['error']}\n"

    lines = []
    lines.append("=" * 80)
    lines.append("MIDI CC PRESET MAP")
    lines.append("=" * 80)
    lines.append(f"\nFile: {data['file']}")
    lines.append(f"DrumCell Devices: {data['drumcell_count']}")
    lines.append(f"CC Mappings Found: {len(data['cc_mappings'])}")

    lines.append("\n" + "=" * 80)
    lines.append("RECOMMENDED CONTROLLER SETTINGS")
    lines.append("=" * 80)
    lines.append("\nSet your MIDI controller to these values for neutral sound:\n")

    for cc_num, info in sorted(data['cc_mappings'].items()):
        lines.append(f"CC#{cc_num:3d} (Ch {info['channel']:2d}) - {info['parameter']:20s}")
        lines.append(f"  └─ Set to: {info['avg_cc_value']:3d}")

        if not info['all_same']:
            lines.append(f"     (Range across pads: {info['min_cc_value']}-{info['max_cc_value']}, "
                        f"{info['unique_values']} unique values)")

        param_min, param_max = info['param_range']
        lines.append(f"     (Parameter range: {param_min:.2f} to {param_max:.2f})")

    lines.append("\n" + "=" * 80)
    lines.append("QUICK REFERENCE")
    lines.append("=" * 80)
    lines.append("\nChannel 16 CCs to set:\n")

    for cc_num, info in sorted(data['cc_mappings'].items()):
        lines.append(f"  CC{cc_num:3d} = {info['avg_cc_value']:3d}  # {info['parameter']}")

    lines.append("\n" + "=" * 80)

    return "\n".join(lines)


def format_json_report(data: Dict) -> str:
    """Format analysis as JSON."""
    return json.dumps(data, indent=2)


def format_csv_report(data: Dict) -> str:
    """Format analysis as CSV."""
    if 'error' in data:
        return f"Error,{data['error']}\n"

    lines = []
    lines.append("CC_Number,Channel,Parameter,Recommended_Value,Min_Value,Max_Value,All_Pads_Same,Param_Min,Param_Max")

    for cc_num, info in sorted(data['cc_mappings'].items()):
        param_min, param_max = info['param_range']
        lines.append(f"{cc_num},{info['channel']},{info['parameter']},{info['avg_cc_value']},"
                    f"{info['min_cc_value']},{info['max_cc_value']},{info['all_same']},"
                    f"{param_min:.2f},{param_max:.2f}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Generate MIDI CC preset map for drum rack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Display preset map
    python3 generate_cc_preset_map.py my_rack.adg

    # Save to file
    python3 generate_cc_preset_map.py my_rack.adg --output preset_map.txt

    # JSON format (for loading into other tools)
    python3 generate_cc_preset_map.py my_rack.adg --format json --output preset.json

    # CSV format (for spreadsheets)
    python3 generate_cc_preset_map.py my_rack.adg --format csv --output preset.csv
        """
    )

    parser.add_argument('input', type=Path, help='Input drum rack (.adg file)')
    parser.add_argument('--output', type=Path, help='Output file (default: stdout)')
    parser.add_argument(
        '--format',
        choices=['text', 'json', 'csv'],
        default='text',
        help='Output format (default: text)'
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"✗ Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    try:
        # Analyze drum rack
        data = analyze_drum_rack(args.input)

        # Format output
        if args.format == 'json':
            output = format_json_report(data)
        elif args.format == 'csv':
            output = format_csv_report(data)
        else:
            output = format_text_report(data)

        # Write or print
        if args.output:
            args.output.write_text(output)
            print(f"✓ Preset map written to: {args.output}")
        else:
            print(output)

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
