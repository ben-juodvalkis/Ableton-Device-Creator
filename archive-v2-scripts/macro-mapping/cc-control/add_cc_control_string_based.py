#!/usr/bin/env python3
"""
String-based CC Control injector - preserves exact XML formatting.
Uses regex string replacement instead of XML parsing to avoid formatting changes.
"""

import sys
import argparse
import re
from pathlib import Path
from typing import List, Tuple

sys.path.append(str(Path(__file__).parent / 'utils'))
from decoder import decode_adg
from encoder import encode_adg


def add_cc_control_string_based(xml_content: str, slot: int, cc_num: int, macro_idx: int) -> str:
    """
    Add CC Control device using pure string manipulation.
    Loads a reference template from the manual example and injects it.
    """

    # Load the CC Control device from our working manual example
    template_path = Path('/Users/Music/Desktop/steps/drum step 2 add cc control.adg')
    if not template_path.exists():
        raise Exception(f"Template not found: {template_path}")

    template_xml = decode_adg(template_path)

    # Extract just the CC Control device section
    cc_match = re.search(
        r'(<AbletonDevicePreset Id="0">.*?<MidiCcControl.*?</MidiCcControl>.*?</AbletonDevicePreset>)',
        template_xml,
        re.DOTALL
    )

    if not cc_match:
        raise Exception("Could not extract CC Control from template")

    cc_device_block = cc_match.group(1)

    # Configure the CC number for the specified slot
    cc_device_block = re.sub(
        rf'(<CustomFloatTargets\.{slot} Value=")(\d+)(")',
        rf'\g<1>{cc_num}\3',
        cc_device_block
    )

    # Add KeyMidi mapping
    key_midi_xml = f'''<KeyMidi>
										<PersistentKeyString Value="" />
										<IsNote Value="false" />
										<Channel Value="16" />
										<NoteOrController Value="{macro_idx}" />
										<LowerRangeNote Value="-1" />
										<UpperRangeNote Value="-1" />
										<ControllerMapMode Value="0" />
									</KeyMidi>
									'''

    # Insert KeyMidi after LomId in the target CustomFloatValues slot
    pattern = rf'(<CustomFloatValues\.{slot}>[\s\S]*?<LomId Value="0" />)'
    cc_device_block = re.sub(pattern, rf'\1\n\t\t\t\t\t\t\t\t\t{key_midi_xml}', cc_device_block)

    # Find DevicePresets section and inject CC Control before first device
    device_presets_pattern = r'(<DevicePresets>\s+)(<(?:Au|AbletonDevice)Preset)'
    replacement = rf'\1{cc_device_block}\n\t\t\t\t\t\2'

    modified_xml = re.sub(device_presets_pattern, replacement, xml_content, count=1)

    if modified_xml == xml_content:
        raise Exception("Could not find injection point in DevicePresets")

    return modified_xml


def main():
    parser = argparse.ArgumentParser(
        description='Add CC Control to drum rack (string-based, preserves formatting)'
    )
    parser.add_argument('input', type=Path, help='Input .adg file')
    parser.add_argument('output', type=Path, help='Output .adg file')
    parser.add_argument('--slot', type=int, required=True, help='CC Control slot (0-11)')
    parser.add_argument('--cc', type=int, required=True, help='MIDI CC number (0-127)')
    parser.add_argument('--macro', type=int, required=True, help='Macro index (0-15)')

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input not found: {args.input}")
        return 1

    print(f"Processing: {args.input.name}")
    print(f"Config: Custom {'BCDEFGHIJKLM'[args.slot]} (slot {args.slot}) → CC {args.cc} → Macro {args.macro + 1}")

    # Decode
    xml = decode_adg(args.input)

    # Modify
    modified = add_cc_control_string_based(xml, args.slot, args.cc, args.macro)

    # Encode
    encode_adg(modified, args.output)

    print(f"✓ Created: {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
