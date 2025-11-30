#!/usr/bin/env python3
"""
Wrap Two Devices in Dual-Chain Instrument Rack

Creates an Instrument Rack with two chains, each containing one device.
Uses a working template to ensure all Ableton-required elements are present.

Usage:
    python3 wrap_two_devices_in_rack.py device1.adg device2.adg output.adg
    python3 wrap_two_devices_in_rack.py device1.adg device2.adg output.adg --name "Dual Rack"
    python3 wrap_two_devices_in_rack.py device1.adg device2.adg output.adg --chain1 "Kit A" --chain2 "Kit B"
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


# Path to the dual-device template
TEMPLATE_PATH = Path(__file__).parent.parent / 'templates' / 'dual_device_rack_template.xml'


def load_template() -> ET.Element:
    """Load the dual-device template rack XML."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Template not found: {TEMPLATE_PATH}\n"
            f"Please ensure the dual-device template file exists."
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


def get_device_name(xml_root: ET.Element) -> str:
    """
    Extract the device name from source device.

    Tries multiple locations to find a meaningful name:
    1. UserName in the main device (InstrumentGroupDevice, DrumGroupDevice, etc.)
    2. UserName in nested devices (for already-wrapped racks)
    3. Falls back to empty string if not found

    Args:
        xml_root: Source device XML root

    Returns:
        Device name or empty string
    """
    # Try to find any GroupDevice (InstrumentGroupDevice, DrumGroupDevice, etc.)
    device = xml_root.find('.//GroupDevicePreset/Device/*')

    if device is not None:
        user_name_elem = device.find('UserName')
        if user_name_elem is not None:
            name = user_name_elem.get('Value', '')
            if name:
                return name

    # If main device has no name, try to find a nested device name
    # (for already-wrapped racks)
    nested_devices = xml_root.findall('.//*[@Id]')
    for nested_device in nested_devices:
        if nested_device.tag in ['InstrumentGroupDevice', 'DrumGroupDevice', 'AudioEffectGroupDevice']:
            user_name_elem = nested_device.find('UserName')
            if user_name_elem is not None:
                name = user_name_elem.get('Value', '')
                if name:
                    return name

    return ""


def wrap_two_devices_in_rack(
    device1_path: Path,
    device2_path: Path,
    output_path: Path,
    rack_name: str = "",
    chain1_name: str = "",
    chain2_name: str = ""
) -> Path:
    """
    Wrap two devices in a dual-chain Instrument Rack.

    Args:
        device1_path: Path to first device (.adg)
        device2_path: Path to second device (.adg)
        output_path: Path for output wrapped rack
        rack_name: Name for the wrapper rack
        chain1_name: Name for first chain
        chain2_name: Name for second chain

    Returns:
        Path to created wrapped rack
    """
    if not device1_path.exists():
        raise FileNotFoundError(f"Device 1 not found: {device1_path}")
    if not device2_path.exists():
        raise FileNotFoundError(f"Device 2 not found: {device2_path}")

    print(f"\n{'='*70}")
    print(f"WRAPPING TWO DEVICES IN DUAL-CHAIN INSTRUMENT RACK")
    print(f"{'='*70}\n")
    print(f"Device 1: {device1_path.name}")
    print(f"Device 2: {device2_path.name}")

    # Load template
    print("\nLoading template...")
    template_root = load_template()

    # Load source devices
    print(f"Loading source devices...")
    device1_xml = decode_adg(device1_path)
    device1_root = ET.fromstring(device1_xml)
    device1_preset = extract_group_device_preset(device1_root)
    device1_name = get_device_name(device1_root)

    device2_xml = decode_adg(device2_path)
    device2_root = ET.fromstring(device2_xml)
    device2_preset = extract_group_device_preset(device2_root)
    device2_name = get_device_name(device2_root)

    print(f"Extracted GroupDevicePresets from both devices")
    print(f"  Device 1 name: '{device1_name}'")
    print(f"  Device 2 name: '{device2_name}'")

    # Find the BranchPresets in template
    template_group_preset = template_root.find('.//GroupDevicePreset')
    branch_presets = template_group_preset.find('BranchPresets')

    if branch_presets is None:
        raise ValueError("Template is missing BranchPresets")

    # Get the two chains
    chains = branch_presets.findall('InstrumentBranchPreset')
    if len(chains) != 2:
        raise ValueError(f"Template should have 2 chains, found {len(chains)}")

    # Replace device in chain 1
    chain1 = chains[0]
    chain1_device_presets = chain1.find('DevicePresets')
    existing_preset1 = chain1_device_presets.find('GroupDevicePreset')
    if existing_preset1 is not None:
        chain1_device_presets.remove(existing_preset1)
    device1_preset.set('Id', '0')
    chain1_device_presets.append(device1_preset)

    # Replace device in chain 2
    chain2 = chains[1]
    chain2_device_presets = chain2.find('DevicePresets')
    existing_preset2 = chain2_device_presets.find('GroupDevicePreset')
    if existing_preset2 is not None:
        chain2_device_presets.remove(existing_preset2)
    device2_preset.set('Id', '0')
    chain2_device_presets.append(device2_preset)

    print(f"Replaced template devices with source devices")

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

    # Update chain names (use provided name or auto-detected device name)
    final_chain1_name = chain1_name if chain1_name else device1_name
    final_chain2_name = chain2_name if chain2_name else device2_name

    if final_chain1_name:
        chain1_name_elem = chain1.find('Name')
        if chain1_name_elem is not None:
            chain1_name_elem.set('Value', final_chain1_name)
        print(f"Set chain 1 name: '{final_chain1_name}'")

    if final_chain2_name:
        chain2_name_elem = chain2.find('Name')
        if chain2_name_elem is not None:
            chain2_name_elem.set('Value', final_chain2_name)
        print(f"Set chain 2 name: '{final_chain2_name}'")

    # Convert to XML string
    wrapped_xml = ET.tostring(template_root, encoding='unicode', xml_declaration=True)

    # Encode to .adg
    print(f"\nWriting dual-chain rack: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(wrapped_xml, output_path)

    print(f"\n{'='*70}")
    print(f"✓ DUAL-CHAIN WRAPPING COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {output_path}")
    print(f"  Chain 1: {final_chain1_name or '(empty)'}")
    print(f"  Chain 2: {final_chain2_name or '(empty)'}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Wrap two devices in a dual-chain Instrument Rack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic wrapping
    python3 wrap_two_devices_in_rack.py kit1.adg kit2.adg output.adg

    # With rack name
    python3 wrap_two_devices_in_rack.py kit1.adg kit2.adg dual.adg --name "Dual Drums"

    # With chain names
    python3 wrap_two_devices_in_rack.py kit1.adg kit2.adg dual.adg \\
        --name "Dual Kit" --chain1 "Kit A" --chain2 "Kit B"
        """
    )

    parser.add_argument('device1', type=Path, help='First device file (.adg)')
    parser.add_argument('device2', type=Path, help='Second device file (.adg)')
    parser.add_argument('output', type=Path, help='Output dual-chain rack path')
    parser.add_argument('--name', default='', help='Name for the wrapper rack')
    parser.add_argument('--chain1', default='', help='Name for first chain')
    parser.add_argument('--chain2', default='', help='Name for second chain')

    args = parser.parse_args()

    try:
        wrap_two_devices_in_rack(
            args.device1,
            args.device2,
            args.output,
            args.name,
            args.chain1,
            args.chain2
        )

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
