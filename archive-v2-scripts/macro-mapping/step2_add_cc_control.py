#!/usr/bin/env python3
"""
Step 2: Add CC Control device to drum rack.
Injects the complete CC Control device block before the AU plugin.
"""

import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'utils'))
from decoder import decode_adg
from encoder import encode_adg


def load_cc_control_template():
    """Load the CC Control device template from step 2"""
    template_path = Path('/Users/Music/Desktop/steps/step 2.adg')

    if not template_path.exists():
        raise Exception(f"Template file not found: {template_path}")

    template_xml = decode_adg(template_path)

    # Extract the CC Control block
    cc_match = re.search(
        r'(<AbletonDevicePreset Id="0">.*?<MidiCcControl.*?</MidiCcControl>.*?</AbletonDevicePreset>)',
        template_xml,
        re.DOTALL
    )

    if not cc_match:
        raise Exception("Could not extract CC Control block from template")

    return cc_match.group(1)


def add_cc_control_device(xml_content: str, cc_template: str) -> str:
    """
    Add CC Control device by inserting it before the AU plugin and updating IDs.

    Changes:
    1. Find: <AuPreset Id="0">
    2. Replace with: <AbletonDevicePreset...CC Control (Id="0")...</AbletonDevicePreset>\n<AuPreset Id="1">

    CRITICAL: Must change AuPreset Id from "0" to "1" to avoid duplicate IDs!
    """

    # Check if already has CC Control
    if '<MidiCcControl' in xml_content:
        print('⚠ CC Control device already exists, skipping')
        return xml_content

    # Find the <AuPreset Id="0"> after DevicePresets
    # Pattern: Look for DevicePresets followed by tabs and AuPreset
    pattern = r'(<DevicePresets>\s+)(<AuPreset Id="0">)'

    # Replacement: Insert CC Control block AND change AuPreset Id to "1"
    replacement = rf'\1{cc_template}\n\t\t\t\t\t<AuPreset Id="1">'

    modified = re.sub(pattern, replacement, xml_content, count=1)

    if modified == xml_content:
        print('⚠ Warning: Could not find injection point (AuPreset after DevicePresets)')
        return xml_content

    print('✓ Injected CC Control device (Id="0") before AU plugin (Id="1")')

    return modified


def main():
    if len(sys.argv) < 3:
        print('Usage: python3 step2_add_cc_control.py <input.adg> <output.adg>')
        print('')
        print('Example:')
        print('  python3 step2_add_cc_control.py "step 1.adg" "step 2.adg"')
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f'Error: Input not found: {input_path}')
        return 1

    print(f'Adding CC Control device to: {input_path.name}')
    print('=' * 70)

    # Load template
    print('Loading CC Control template from step 2...')
    cc_template = load_cc_control_template()
    print(f'Template size: {len(cc_template):,} chars')

    # Decode
    xml = decode_adg(input_path)
    print(f'Input size: {len(xml):,} chars')

    # Add CC Control
    modified = add_cc_control_device(xml, cc_template)

    # Encode
    encode_adg(modified, output_path)

    print(f'Output size: {len(modified):,} chars')
    print(f'Change: {len(modified) - len(xml):+,} chars')
    print(f'\n✓ Created: {output_path}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
