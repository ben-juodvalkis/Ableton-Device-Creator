#!/usr/bin/env python3
"""
Wrap Device in Instrument Rack

Wraps any Ableton device (.adg file) inside an Instrument Rack with a single chain.

This is useful for:
- Creating a consistent container for devices
- Adding macro controls to devices
- Combining multiple devices later

Usage:
    python3 wrap_device_in_rack.py input.adg output.adg
    python3 wrap_device_in_rack.py input.adg output.adg --name "My Custom Rack"
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def extract_group_device_preset_content(xml_root: ET.Element) -> ET.Element:
    """
    Extract the complete GroupDevicePreset from a .adg file.

    This extracts the entire GroupDevicePreset element which contains both
    the Device and the BranchPresets.

    Args:
        xml_root: Parsed XML root element from source .adg

    Returns:
        The complete GroupDevicePreset element
    """
    # The structure is: Ableton > GroupDevicePreset
    group_preset = xml_root.find('.//GroupDevicePreset')

    if group_preset is None:
        raise ValueError("Could not find GroupDevicePreset element in source file")

    return group_preset


def create_wrapper_rack(
    source_group_preset: ET.Element,
    rack_name: str = "",
    chain_name: str = ""
) -> ET.Element:
    """
    Create an Instrument Rack wrapper containing the device.

    Args:
        source_group_preset: The complete GroupDevicePreset element from source
        rack_name: Name for the outer rack (default: empty)
        chain_name: Name for the chain (default: empty)

    Returns:
        Complete Ableton XML root element with wrapped device
    """
    # Create the outer structure
    ableton = ET.Element('Ableton', {
        'MajorVersion': '5',
        'MinorVersion': '12.0_12300',
        'SchemaChangeCount': '1',
        'Creator': 'Ableton Live 12.3b12',
        'Revision': 'a51ffacdd96935f4e75c565b931d9d81c161dfb8'
    })

    group_device_preset = ET.SubElement(ableton, 'GroupDevicePreset')
    ET.SubElement(group_device_preset, 'OverwriteProtectionNumber', {'Value': '3075'})

    device_wrapper = ET.SubElement(group_device_preset, 'Device')

    # Create the outer Instrument Rack
    instrument_group = ET.SubElement(device_wrapper, 'InstrumentGroupDevice', {'Id': '0'})

    # Add basic rack properties
    ET.SubElement(instrument_group, 'LomId', {'Value': '0'})
    ET.SubElement(instrument_group, 'LomIdView', {'Value': '0'})
    ET.SubElement(instrument_group, 'IsExpanded', {'Value': 'true'})
    ET.SubElement(instrument_group, 'BreakoutIsExpanded', {'Value': 'false'})

    # On parameter
    on_param = ET.SubElement(instrument_group, 'On')
    ET.SubElement(on_param, 'LomId', {'Value': '0'})
    ET.SubElement(on_param, 'Manual', {'Value': 'true'})
    on_auto = ET.SubElement(on_param, 'AutomationTarget', {'Id': '0'})
    ET.SubElement(on_auto, 'LockEnvelope', {'Value': '0'})
    on_midi = ET.SubElement(on_param, 'MidiCCOnOffThresholds')
    ET.SubElement(on_midi, 'Min', {'Value': '64'})
    ET.SubElement(on_midi, 'Max', {'Value': '127'})

    # Other basic properties
    ET.SubElement(instrument_group, 'ModulationSourceCount', {'Value': '0'})
    ET.SubElement(instrument_group, 'ParametersListWrapper', {'LomId': '0'})
    ET.SubElement(instrument_group, 'Pointee', {'Id': '0'})
    ET.SubElement(instrument_group, 'LastSelectedTimeableIndex', {'Value': '0'})
    ET.SubElement(instrument_group, 'LastSelectedClipEnvelopeIndex', {'Value': '0'})

    # Empty LastPresetRef
    last_preset = ET.SubElement(instrument_group, 'LastPresetRef')
    ET.SubElement(last_preset, 'Value')

    ET.SubElement(instrument_group, 'LockedScripts')
    ET.SubElement(instrument_group, 'IsFolded', {'Value': 'false'})
    ET.SubElement(instrument_group, 'ShouldShowPresetName', {'Value': 'true'})
    ET.SubElement(instrument_group, 'UserName', {'Value': rack_name})
    ET.SubElement(instrument_group, 'Annotation', {'Value': ''})

    source_context = ET.SubElement(instrument_group, 'SourceContext')
    ET.SubElement(source_context, 'Value')

    ET.SubElement(instrument_group, 'MpePitchBendUsesTuning', {'Value': 'true'})
    ET.SubElement(instrument_group, 'ViewData', {'Value': '{}'})
    ET.SubElement(instrument_group, 'OverwriteProtectionNumber', {'Value': '3075'})
    ET.SubElement(instrument_group, 'Branches')
    ET.SubElement(instrument_group, 'IsBranchesListVisible', {'Value': 'false'})
    ET.SubElement(instrument_group, 'IsReturnBranchesListVisible', {'Value': 'false'})
    ET.SubElement(instrument_group, 'IsRangesEditorVisible', {'Value': 'false'})
    ET.SubElement(instrument_group, 'AreDevicesVisible', {'Value': 'true'})

    # 8 macro controls (default state)
    ET.SubElement(instrument_group, 'NumVisibleMacroControls', {'Value': '8'})
    for i in range(16):  # Ableton has 16 macros total (8 visible by default)
        macro = ET.SubElement(instrument_group, f'MacroControls.{i}')
        ET.SubElement(macro, 'LomId', {'Value': '0'})
        ET.SubElement(macro, 'Manual', {'Value': '0'})
        midi_range = ET.SubElement(macro, 'MidiControllerRange')
        ET.SubElement(midi_range, 'Min', {'Value': '0'})
        ET.SubElement(midi_range, 'Max', {'Value': '127'})
        auto_target = ET.SubElement(macro, 'AutomationTarget', {'Id': '0'})
        ET.SubElement(auto_target, 'LockEnvelope', {'Value': '0'})
        mod_target = ET.SubElement(macro, 'ModulationTarget', {'Id': '0'})
        ET.SubElement(mod_target, 'LockEnvelope', {'Value': '0'})

    # DisplayName
    display_name = ET.SubElement(instrument_group, 'DisplayName')
    ET.SubElement(display_name, 'EffectiveName', {'Value': 'Instrument Rack'})
    ET.SubElement(display_name, 'UserName', {'Value': rack_name})
    ET.SubElement(display_name, 'Annotation', {'Value': ''})
    ET.SubElement(display_name, 'MemorizedFirstClipName', {'Value': ''})

    # BranchPresets - this is where the chain goes
    branch_presets = ET.SubElement(instrument_group, 'BranchPresets')

    # Create a single chain
    instrument_branch = ET.SubElement(branch_presets, 'InstrumentBranchPreset', {'Id': '0'})
    ET.SubElement(instrument_branch, 'Name', {'Value': chain_name})
    ET.SubElement(instrument_branch, 'IsSoloed', {'Value': 'false'})

    # DevicePresets - this contains the wrapped device
    device_presets = ET.SubElement(instrument_branch, 'DevicePresets')

    # Add the source GroupDevicePreset as a child
    # This preserves the entire device structure (Device + BranchPresets)
    device_presets.append(source_group_preset)

    # Add MixerPreset for the chain
    mixer_preset = ET.SubElement(instrument_branch, 'MixerPreset')
    # ... (mixer preset is complex, but we can copy from template)
    # For now, we'll add minimal mixer settings

    # Add more rack settings
    ET.SubElement(instrument_group, 'ReturnBranchPresets')

    midi_targets = ET.SubElement(instrument_group, 'MidiTargets')
    ET.SubElement(midi_targets, 'KeyRangeMappingTarget')
    ET.SubElement(midi_targets, 'VelocityRangeMappingTarget')

    return ableton


def wrap_device_in_rack(
    input_path: Path,
    output_path: Path,
    rack_name: str = "",
    chain_name: str = ""
) -> Path:
    """
    Wrap a device in an Instrument Rack with a single chain.

    Args:
        input_path: Path to input device (.adg)
        output_path: Path for output wrapped rack
        rack_name: Name for the wrapper rack (default: empty)
        chain_name: Name for the chain (default: empty)

    Returns:
        Path to created wrapped rack
    """
    # Validate input
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"\n{'='*70}")
    print(f"WRAPPING DEVICE IN INSTRUMENT RACK")
    print(f"{'='*70}\n")
    print(f"Input: {input_path.name}")

    # Decode input device
    xml_content = decode_adg(input_path)
    root = ET.fromstring(xml_content)

    # Extract GroupDevicePreset
    group_preset = extract_group_device_preset_content(root)
    print(f"Extracted GroupDevicePreset")

    # Create wrapper rack
    wrapped_root = create_wrapper_rack(group_preset, rack_name, chain_name)
    print(f"Created wrapper rack structure")

    # Convert to XML string
    wrapped_xml = ET.tostring(wrapped_root, encoding='unicode', xml_declaration=True)

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
        description='Wrap a device in an Instrument Rack with a single chain',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic wrapping
    python3 wrap_device_in_rack.py input.adg output.adg

    # With custom name
    python3 wrap_device_in_rack.py drum_kit.adg wrapped_kit.adg --name "My Drum Kit"

    # With rack and chain names
    python3 wrap_device_in_rack.py synth.adg wrapped.adg --name "Synth Rack" --chain-name "Main"
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
