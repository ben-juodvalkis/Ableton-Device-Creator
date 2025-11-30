#!/usr/bin/env python3
"""
Add CC Control device to Ableton drum rack and map parameters to macros.

This script:
1. Decodes a drum rack .adg file
2. Inserts a CC Control MIDI device before existing devices
3. Maps CC Control custom parameters to specified drum rack macros
4. Saves the modified .adg file

Usage:
    python3 add_cc_control_to_drum_rack.py input.adg output.adg --mappings 3:119:15

Arguments:
    input.adg: Source drum rack file
    output.adg: Destination file (will be created/overwritten)
    --mappings: Comma-separated list of slot:cc:macro triplets
                slot = CC Control parameter slot (0-11 for Custom B-M)
                cc = MIDI CC number to send (0-127)
                macro = Drum rack macro index (0-15 for macros 1-16)
                Example: "3:119:15" = Custom E sends CC 119, maps to Macro 16
"""

import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

# Import local utilities
sys.path.append(str(Path(__file__).parent / 'utils'))
from decoder import decode_adg
from encoder import encode_adg


# CC Control device XML template (from step 2 analysis)
CC_CONTROL_TEMPLATE = '''<MidiCcControl Id="0">
								<LomId Value="0" />
								<LomIdView Value="0" />
								<IsExpanded Value="true" />
								<BreakoutIsExpanded Value="false" />
								<On>
									<LomId Value="0" />
									<Manual Value="true" />
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<MidiCCOnOffThresholds>
										<Min Value="64" />
										<Max Value="127" />
									</MidiCCOnOffThresholds>
								</On>
								<ModulationSourceCount Value="0" />
								<ParametersListWrapper LomId="0" />
								<Pointee Id="0" />
								<LastSelectedTimeableIndex Value="0" />
								<LastSelectedClipEnvelopeIndex Value="0" />
								<LastPresetRef>
									<Value>
										<AbletonDefaultPresetRef Id="0">
											<FileRef>
												<RelativePathType Value="7" />
												<RelativePath Value="Devices/MIDI Effects/CC Control" />
												<Path Value="/Applications/Ableton Live 12 Beta.app/Contents/App-Resources/Builtin/Devices/MIDI Effects/CC Control" />
												<Type Value="2" />
												<LivePackName Value="" />
												<LivePackId Value="" />
												<OriginalFileSize Value="0" />
												<OriginalCrc Value="0" />
												<SourceHint Value="" />
											</FileRef>
											<DeviceId Name="" />
										</AbletonDefaultPresetRef>
									</Value>
								</LastPresetRef>
								<LockedScripts />
								<IsFolded Value="false" />
								<ShouldShowPresetName Value="true" />
								<UserName Value="" />
								<Annotation Value="" />
								<SourceContext>
									<Value />
								</SourceContext>
								<MpePitchBendUsesTuning Value="true" />
								<ViewData Value="{}" />
								<OverwriteProtectionNumber Value="3075" />
								<ModWheel>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</ModWheel>
								<PitchBend>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="-64" />
										<Max Value="64" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</PitchBend>
								<Pressure>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</Pressure>
								<CustomBoolName Value="Custom A" />
								<CustomBoolTarget Value="64" />
								<CustomBoolValue>
									<LomId Value="0" />
									<Manual Value="false" />
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<MidiCCOnOffThresholds>
										<Min Value="64" />
										<Max Value="127" />
									</MidiCCOnOffThresholds>
								</CustomBoolValue>
								<CustomFloatNames.0 Value="Custom B" />
								<CustomFloatNames.1 Value="Custom C" />
								<CustomFloatNames.2 Value="Custom D" />
								<CustomFloatNames.3 Value="Custom E" />
								<CustomFloatNames.4 Value="Custom F" />
								<CustomFloatNames.5 Value="Custom G" />
								<CustomFloatNames.6 Value="Custom H" />
								<CustomFloatNames.7 Value="Custom I" />
								<CustomFloatNames.8 Value="Custom J" />
								<CustomFloatNames.9 Value="Custom K" />
								<CustomFloatNames.10 Value="Custom L" />
								<CustomFloatNames.11 Value="Custom M" />
								<CustomFloatTargets.0 Value="0" />
								<CustomFloatTargets.1 Value="0" />
								<CustomFloatTargets.2 Value="0" />
								<CustomFloatTargets.3 Value="0" />
								<CustomFloatTargets.4 Value="0" />
								<CustomFloatTargets.5 Value="0" />
								<CustomFloatTargets.6 Value="0" />
								<CustomFloatTargets.7 Value="0" />
								<CustomFloatTargets.8 Value="0" />
								<CustomFloatTargets.9 Value="0" />
								<CustomFloatTargets.10 Value="0" />
								<CustomFloatTargets.11 Value="0" />
								<CustomFloatValues.0>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.0>
								<CustomFloatValues.1>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.1>
								<CustomFloatValues.2>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.2>
								<CustomFloatValues.3>
									<LomId Value="0" />
									<Manual Value="63" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.3>
								<CustomFloatValues.4>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.4>
								<CustomFloatValues.5>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.5>
								<CustomFloatValues.6>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.6>
								<CustomFloatValues.7>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.7>
								<CustomFloatValues.8>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.8>
								<CustomFloatValues.9>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.9>
								<CustomFloatValues.10>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.10>
								<CustomFloatValues.11>
									<LomId Value="0" />
									<Manual Value="0" />
									<MidiControllerRange>
										<Min Value="0" />
										<Max Value="127" />
									</MidiControllerRange>
									<AutomationTarget Id="0">
										<LockEnvelope Value="0" />
									</AutomationTarget>
									<ModulationTarget Id="0">
										<LockEnvelope Value="0" />
									</ModulationTarget>
								</CustomFloatValues.11>
							</MidiCcControl>'''


def parse_mappings(mapping_str: str) -> List[Tuple[int, int, int]]:
    """
    Parse mapping string into list of (slot, cc_number, macro_index) tuples.

    Args:
        mapping_str: String like "3:119:15,4:120:14"

    Returns:
        List of (slot, cc_number, macro_index) tuples
    """
    mappings = []
    for triplet in mapping_str.split(','):
        parts = triplet.split(':')
        if len(parts) != 3:
            raise ValueError(f"Invalid mapping format: {triplet}. Expected slot:cc:macro")
        slot, cc, macro = parts
        mappings.append((int(slot), int(cc), int(macro)))
    return mappings


def add_cc_control_device(xml_content: str, mappings: List[Tuple[int, int, int]]) -> str:
    """
    Add CC Control device to drum rack and configure mappings.

    Args:
        xml_content: Decoded .adg XML string
        mappings: List of (slot, cc_number, macro_index) tuples

    Returns:
        Modified XML string
    """
    root = ET.fromstring(xml_content)

    # Find the DevicePresets section
    device_presets = root.find('.//DevicePresets')
    if device_presets is None:
        raise Exception("Could not find DevicePresets element in XML")

    # Check if there's already a CC Control device
    existing_cc = device_presets.find('.//MidiCcControl')
    if existing_cc is not None:
        print("Warning: CC Control device already exists, will reconfigure it")
        return configure_cc_control_mappings(xml_content, mappings)

    # Get the existing device preset (usually AuPreset)
    existing_preset = device_presets[0]

    # Create CC Control wrapper
    cc_preset = ET.Element('AbletonDevicePreset', {'Id': '0'})
    cc_preset.set('OverwriteProtectionNumber', '3075')

    # Add Device wrapper
    device_wrapper = ET.SubElement(cc_preset, 'Device')

    # Parse and insert CC Control device
    cc_control = ET.fromstring(CC_CONTROL_TEMPLATE)
    device_wrapper.append(cc_control)

    # Configure CC numbers and KeyMidi mappings
    for slot, cc_num, macro_idx in mappings:
        # Validate slot range
        if slot < 0 or slot > 11:
            print(f"Warning: Slot {slot} out of range (0-11), skipping")
            continue

        # Update CustomFloatTargets
        target_elem = cc_control.find(f'.//CustomFloatTargets.{slot}')
        if target_elem is not None:
            target_elem.set('Value', str(cc_num))

        # Add KeyMidi mapping to CustomFloatValues
        float_value = cc_control.find(f'.//CustomFloatValues.{slot}')
        if float_value is not None:
            # Insert KeyMidi element after LomId
            lom_id = float_value.find('LomId')
            if lom_id is not None:
                key_midi = ET.Element('KeyMidi')
                ET.SubElement(key_midi, 'PersistentKeyString', {'Value': ''})
                ET.SubElement(key_midi, 'IsNote', {'Value': 'false'})
                ET.SubElement(key_midi, 'Channel', {'Value': '16'})
                ET.SubElement(key_midi, 'NoteOrController', {'Value': str(macro_idx)})
                ET.SubElement(key_midi, 'LowerRangeNote', {'Value': '-1'})
                ET.SubElement(key_midi, 'UpperRangeNote', {'Value': '-1'})
                ET.SubElement(key_midi, 'ControllerMapMode', {'Value': '0'})

                # Insert after LomId
                idx = list(float_value).index(lom_id)
                float_value.insert(idx + 1, key_midi)

    # Add preset reference
    preset_ref = ET.SubElement(cc_preset, 'PresetRef')
    ableton_ref = ET.SubElement(preset_ref, 'AbletonDefaultPresetRef', {'Id': '0'})
    file_ref = ET.SubElement(ableton_ref, 'FileRef')
    ET.SubElement(file_ref, 'RelativePathType', {'Value': '7'})
    ET.SubElement(file_ref, 'RelativePath', {'Value': 'Devices/MIDI Effects/CC Control'})
    ET.SubElement(file_ref, 'Path', {'Value': '/Applications/Ableton Live 12 Beta.app/Contents/App-Resources/Builtin/Devices/MIDI Effects/CC Control'})
    ET.SubElement(file_ref, 'Type', {'Value': '2'})
    ET.SubElement(file_ref, 'LivePackName', {'Value': ''})
    ET.SubElement(file_ref, 'LivePackId', {'Value': ''})
    ET.SubElement(file_ref, 'OriginalFileSize', {'Value': '0'})
    ET.SubElement(file_ref, 'OriginalCrc', {'Value': '0'})
    ET.SubElement(file_ref, 'SourceHint', {'Value': ''})
    ET.SubElement(ableton_ref, 'DeviceId', {'Name': ''})

    # Insert CC Control before existing device
    device_presets.insert(0, cc_preset)
    device_presets.insert(1, existing_preset)

    # Remove the original (now duplicate) preset
    device_presets.remove(device_presets[2])

    return ET.tostring(root, encoding='unicode', xml_declaration=True)


def configure_cc_control_mappings(xml_content: str, mappings: List[Tuple[int, int, int]]) -> str:
    """
    Configure existing CC Control device with macro mappings.

    Args:
        xml_content: Decoded .adg XML string
        mappings: List of (slot, cc_number, macro_index) tuples

    Returns:
        Modified XML string
    """
    root = ET.fromstring(xml_content)

    # Find CC Control device
    cc_control = root.find('.//MidiCcControl')
    if cc_control is None:
        raise Exception("CC Control device not found")

    # Update CC numbers and add KeyMidi mappings
    for slot, cc_num, macro_idx in mappings:
        # Validate slot range
        if slot < 0 or slot > 11:
            print(f"Warning: Slot {slot} out of range (0-11), skipping")
            continue

        # Update CustomFloatTargets
        target_elem = cc_control.find(f'.//CustomFloatTargets.{slot}')
        if target_elem is not None:
            target_elem.set('Value', str(cc_num))

        # Add/update KeyMidi element in CustomFloatValues
        float_value = cc_control.find(f'.//CustomFloatValues.{slot}')
        if float_value is not None:
            # Remove existing KeyMidi if present
            existing_key = float_value.find('.//KeyMidi')
            if existing_key is not None:
                float_value.remove(existing_key)

            # Insert new KeyMidi element after LomId
            lom_id = float_value.find('LomId')
            if lom_id is not None:
                key_midi = ET.Element('KeyMidi')
                ET.SubElement(key_midi, 'PersistentKeyString', {'Value': ''})
                ET.SubElement(key_midi, 'IsNote', {'Value': 'false'})
                ET.SubElement(key_midi, 'Channel', {'Value': '16'})
                ET.SubElement(key_midi, 'NoteOrController', {'Value': str(macro_idx)})
                ET.SubElement(key_midi, 'LowerRangeNote', {'Value': '-1'})
                ET.SubElement(key_midi, 'UpperRangeNote', {'Value': '-1'})
                ET.SubElement(key_midi, 'ControllerMapMode', {'Value': '0'})

                # Insert after LomId
                idx = list(float_value).index(lom_id)
                float_value.insert(idx + 1, key_midi)

    return ET.tostring(root, encoding='unicode', xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(
        description='Add CC Control device to drum rack and map to macros'
    )
    parser.add_argument('input', type=Path, help='Input drum rack .adg file')
    parser.add_argument('output', type=Path, help='Output .adg file')
    parser.add_argument(
        '--mappings',
        type=str,
        required=True,
        help='Slot:CC:Macro mappings (e.g., "3:119:15" = Custom E→CC119→Macro16)'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup of original file'
    )

    args = parser.parse_args()

    # Validate input
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    # Parse mappings
    try:
        mappings = parse_mappings(args.mappings)
        print(f"Configuring {len(mappings)} mappings:")
        for slot, cc_num, macro_idx in mappings:
            custom_letter = 'BCDEFGHIJKLM'[slot] if slot < 12 else '?'
            print(f"  Custom {custom_letter} (slot {slot}) → CC {cc_num} → Macro {macro_idx + 1}")
    except Exception as e:
        print(f"Error parsing mappings: {e}")
        return 1

    # Create backup if requested
    if args.backup:
        backup_path = args.input.with_suffix('.adg.backup')
        import shutil
        shutil.copy2(args.input, backup_path)
        print(f"Created backup: {backup_path}")

    # Decode input file
    print(f"\nDecoding: {args.input}")
    xml_content = decode_adg(args.input)

    # Add CC Control device and configure mappings
    print("Adding CC Control device...")
    modified_xml = add_cc_control_device(xml_content, mappings)

    # Encode output file
    print(f"Encoding: {args.output}")
    encode_adg(modified_xml, args.output)

    print(f"\n✓ Successfully created: {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
