#!/usr/bin/env python3
"""
Wrap Device in Instrument Rack (Template-Based)

Uses a working template rack and replaces the nested device content.
This ensures all Ableton-required elements are present and properly structured.

Usage:
    python3 wrap_device_in_rack_template.py input.adg output.adg
    python3 wrap_device_in_rack_template.py input.adg output.adg --name "My Rack"
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


# Path to the template
TEMPLATE_PATH = Path(__file__).parent.parent / 'templates' / 'instrument_rack_wrapper_template.xml'


def load_template() -> ET.Element:
    """Load the template rack XML."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Template not found: {TEMPLATE_PATH}\n"
            f"Please ensure the template file exists."
        )

    with open(TEMPLATE_PATH, 'r') as f:
        xml_content = f.read()

    return ET.fromstring(xml_content)


def extract_group_device_preset(xml_root: ET.Element) -> ET.Element:
    """
    Extract the GroupDevicePreset from source device.

    Args:
        xml_root: Source device XML root

    Returns:
        The GroupDevicePreset element
    """
    group_preset = xml_root.find('.//GroupDevicePreset')
    if group_preset is None:
        raise ValueError("Could not find GroupDevicePreset in source device")

    return group_preset


def wrap_device_in_rack(
    input_path: Path,
    output_path: Path,
    rack_name: str = "",
    chain_name: str = ""
) -> Path:
    """
    Wrap a device using the template approach.

    Args:
        input_path: Path to input device (.adg)
        output_path: Path for output wrapped rack
        rack_name: Name for the wrapper rack
        chain_name: Name for the chain

    Returns:
        Path to created wrapped rack
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"\n{'='*70}")
    print(f"WRAPPING DEVICE IN INSTRUMENT RACK (Template-Based)")
    print(f"{'='*70}\n")
    print(f"Input: {input_path.name}")

    # Load template
    print("Loading template...")
    template_root = load_template()

    # Load source device
    print(f"Loading source device...")
    source_xml = decode_adg(input_path)
    source_root = ET.fromstring(source_xml)

    # Extract source GroupDevicePreset
    source_group_preset = extract_group_device_preset(source_root)
    print(f"Extracted source GroupDevicePreset")

    # Find the nested GroupDevicePreset in template that we need to replace
    # Path: InstrumentBranchPreset > DevicePresets > GroupDevicePreset
    template_branch = template_root.find('.//InstrumentBranchPreset')
    if template_branch is None:
        raise ValueError("Template is missing InstrumentBranchPreset")

    template_device_presets = template_branch.find('DevicePresets')
    if template_device_presets is None:
        raise ValueError("Template is missing DevicePresets in branch")

    # Remove the existing GroupDevicePreset from template
    existing_preset = template_device_presets.find('GroupDevicePreset')
    if existing_preset is not None:
        template_device_presets.remove(existing_preset)

    # Add source GroupDevicePreset (but ensure it has Id="0")
    source_group_preset.set('Id', '0')
    template_device_presets.append(source_group_preset)

    print(f"Replaced template device with source device")

    # Update rack name if provided
    if rack_name:
        outer_rack = template_root.find('.//InstrumentGroupDevice')
        if outer_rack is not None:
            user_name = outer_rack.find('UserName')
            if user_name is not None:
                user_name.set('Value', rack_name)

            # Also update DisplayName
            display_name = outer_rack.find('DisplayName')
            if display_name is not None:
                display_user_name = display_name.find('UserName')
                if display_user_name is not None:
                    display_user_name.set('Value', rack_name)

        print(f"Set rack name: '{rack_name}'")

    # Update chain name if provided
    if chain_name:
        chain_name_elem = template_branch.find('Name')
        if chain_name_elem is not None:
            chain_name_elem.set('Value', chain_name)
        print(f"Set chain name: '{chain_name}'")

    # Convert to XML string
    wrapped_xml = ET.tostring(template_root, encoding='unicode', xml_declaration=True)

    # Encode to .adg
    print(f"\nWriting wrapped rack: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(wrapped_xml, output_path)

    print(f"\n{'='*70}")
    print(f"✓ WRAPPING COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Wrap a device in an Instrument Rack using a template',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic wrapping
    python3 wrap_device_in_rack_template.py input.adg output.adg

    # With custom name
    python3 wrap_device_in_rack_template.py drum_kit.adg wrapped_kit.adg --name "My Drum Kit"

    # With rack and chain names
    python3 wrap_device_in_rack_template.py synth.adg wrapped.adg --name "Synth" --chain-name "Main"
        """
    )

    parser.add_argument('input', type=Path, help='Input device file (.adg)')
    parser.add_argument('output', type=Path, help='Output wrapped rack path')
    parser.add_argument('--name', default='', help='Name for the wrapper rack')
    parser.add_argument('--chain-name', default='', help='Name for the chain')

    args = parser.parse_args()

    try:
        wrap_device_in_rack(
            args.input,
            args.output,
            args.name,
            args.chain_name
        )

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
