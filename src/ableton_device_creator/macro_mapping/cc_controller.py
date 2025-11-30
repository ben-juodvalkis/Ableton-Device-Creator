"""
CC Control mapping utilities for drum racks.

This module consolidates functionality from:
- add_cc_control_to_drum_rack.py
- add_cc_control_string_based.py
- apply_cc_mappings_preserve_values.py
- configure_drum_rack_macros.py
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging

from ..core import decode_adg, encode_adg

logger = logging.getLogger(__name__)


# CC Control device XML template
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


class CCControlMapper:
    """
    Add and configure CC Control MIDI device in drum racks.

    Consolidates functionality from:
    - add_cc_control_to_drum_rack.py
    - apply_cc_mappings_preserve_values.py
    - configure_drum_rack_macros.py

    Example:
        >>> mapper = CCControlMapper("input.adg")
        >>> mapper.add_cc_mappings({
        ...     3: (119, 15),  # Custom E → CC 119 → Macro 16
        ...     4: (120, 14),  # Custom F → CC 120 → Macro 15
        ... })
        >>> mapper.save("output.adg")
    """

    def __init__(self, rack_path: Union[str, Path]):
        """
        Initialize CC Control mapper with drum rack.

        Args:
            rack_path: Path to drum rack .adg file
        """
        self.rack_path = Path(rack_path)
        if not self.rack_path.exists():
            raise FileNotFoundError(f"Rack not found: {self.rack_path}")

        # Decode and parse XML
        xml_content = decode_adg(self.rack_path)
        self.root = ET.fromstring(xml_content)

    def add_cc_mappings(
        self,
        mappings: Dict[int, Tuple[int, int]],
        insert_device: bool = True
    ) -> 'CCControlMapper':
        """
        Add CC Control mappings to drum rack macros.

        Args:
            mappings: Dict mapping slot → (cc_number, macro_index)
                     Example: {3: (119, 15)} means Custom E → CC 119 → Macro 16
            insert_device: If True, insert CC Control device if not present

        Returns:
            Self for method chaining

        Example:
            >>> mapper.add_cc_mappings({
            ...     0: (102, 0),   # Custom B → CC 102 → Macro 1
            ...     1: (103, 1),   # Custom C → CC 103 → Macro 2
            ...     3: (119, 15),  # Custom E → CC 119 → Macro 16
            ... })
        """
        # Check if CC Control device exists
        device_presets = self.root.find('.//DevicePresets')
        if device_presets is None:
            raise ValueError("Could not find DevicePresets element in rack")

        cc_control = device_presets.find('.//MidiCcControl')

        if cc_control is None and insert_device:
            logger.info("CC Control device not found, inserting...")
            self._insert_cc_control_device()
            cc_control = device_presets.find('.//MidiCcControl')
        elif cc_control is None:
            raise ValueError("CC Control device not found and insert_device=False")

        # Apply mappings
        for slot, (cc_num, macro_idx) in mappings.items():
            self._configure_cc_slot(cc_control, slot, cc_num, macro_idx)
            logger.info(f"Mapped Custom {self._slot_to_letter(slot)} → CC {cc_num} → Macro {macro_idx + 1}")

        return self

    def _insert_cc_control_device(self) -> None:
        """Insert CC Control device at beginning of device chain."""
        device_presets = self.root.find('.//DevicePresets')
        existing_preset = device_presets[0]

        # Create CC Control wrapper
        cc_preset = ET.Element('AbletonDevicePreset', {'Id': '0'})
        cc_preset.set('OverwriteProtectionNumber', '3075')

        # Add Device wrapper
        device_wrapper = ET.SubElement(cc_preset, 'Device')

        # Parse and insert CC Control device
        cc_control = ET.fromstring(CC_CONTROL_TEMPLATE)
        device_wrapper.append(cc_control)

        # Add preset reference
        preset_ref = ET.SubElement(cc_preset, 'PresetRef')
        ableton_ref = ET.SubElement(preset_ref, 'AbletonDefaultPresetRef', {'Id': '0'})
        file_ref = ET.SubElement(ableton_ref, 'FileRef')
        ET.SubElement(file_ref, 'RelativePathType', {'Value': '7'})
        ET.SubElement(file_ref, 'RelativePath', {'Value': 'Devices/MIDI Effects/CC Control'})
        ET.SubElement(file_ref, 'Path', {
            'Value': '/Applications/Ableton Live 12 Beta.app/Contents/App-Resources/Builtin/Devices/MIDI Effects/CC Control'
        })
        ET.SubElement(file_ref, 'Type', {'Value': '2'})
        ET.SubElement(file_ref, 'LivePackName', {'Value': ''})
        ET.SubElement(file_ref, 'LivePackId', {'Value': ''})
        ET.SubElement(file_ref, 'OriginalFileSize', {'Value': '0'})
        ET.SubElement(file_ref, 'OriginalCrc', {'Value': '0'})
        ET.SubElement(file_ref, 'SourceHint', {'Value': ''})
        ET.SubElement(ableton_ref, 'DeviceId', {'Name': ''})

        # Insert CC Control before existing device
        device_presets.insert(0, cc_preset)

    def _configure_cc_slot(
        self,
        cc_control: ET.Element,
        slot: int,
        cc_num: int,
        macro_idx: int
    ) -> None:
        """
        Configure a single CC Control slot.

        Args:
            cc_control: MidiCcControl element
            slot: Slot index (0-11 for Custom B-M)
            cc_num: MIDI CC number (0-127)
            macro_idx: Macro index (0-15 for Macros 1-16)
        """
        if not 0 <= slot <= 11:
            raise ValueError(f"Slot must be 0-11, got {slot}")
        if not 0 <= cc_num <= 127:
            raise ValueError(f"CC number must be 0-127, got {cc_num}")
        if not 0 <= macro_idx <= 15:
            raise ValueError(f"Macro index must be 0-15, got {macro_idx}")

        # Update CustomFloatTargets (CC number)
        target_elem = cc_control.find(f'.//CustomFloatTargets.{slot}')
        if target_elem is not None:
            target_elem.set('Value', str(cc_num))

        # Add/update KeyMidi mapping in CustomFloatValues
        float_value = cc_control.find(f'.//CustomFloatValues.{slot}')
        if float_value is not None:
            # Remove existing KeyMidi if present
            existing_key = float_value.find('.//KeyMidi')
            if existing_key is not None:
                float_value.remove(existing_key)

            # Insert new KeyMidi element after LomId
            lom_id = float_value.find('LomId')
            if lom_id is not None:
                key_midi = self._create_keymidi_element(macro_idx)
                idx = list(float_value).index(lom_id)
                float_value.insert(idx + 1, key_midi)

    def _create_keymidi_element(self, macro_idx: int) -> ET.Element:
        """
        Create KeyMidi element for macro mapping.

        Args:
            macro_idx: Macro index (0-15)

        Returns:
            KeyMidi element
        """
        key_midi = ET.Element('KeyMidi')
        ET.SubElement(key_midi, 'PersistentKeyString', {'Value': ''})
        ET.SubElement(key_midi, 'IsNote', {'Value': 'false'})
        ET.SubElement(key_midi, 'Channel', {'Value': '16'})
        ET.SubElement(key_midi, 'NoteOrController', {'Value': str(macro_idx)})
        ET.SubElement(key_midi, 'LowerRangeNote', {'Value': '-1'})
        ET.SubElement(key_midi, 'UpperRangeNote', {'Value': '-1'})
        ET.SubElement(key_midi, 'ControllerMapMode', {'Value': '0'})
        return key_midi

    def _slot_to_letter(self, slot: int) -> str:
        """Convert slot index to letter (0→B, 1→C, etc.)."""
        if 0 <= slot <= 11:
            return 'BCDEFGHIJKLM'[slot]
        return '?'

    def save(self, output_path: Union[str, Path]) -> Path:
        """
        Save modified rack to file.

        Args:
            output_path: Where to save .adg file

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        xml_string = ET.tostring(self.root, encoding='unicode', xml_declaration=True)
        encode_adg(xml_string, output_path)
        logger.info(f"Saved rack with CC mappings to {output_path}")
        return output_path


def parse_mapping_string(mapping_str: str) -> Dict[int, Tuple[int, int]]:
    """
    Parse mapping string into dictionary.

    Args:
        mapping_str: String like "3:119:15,4:120:14"

    Returns:
        Dict mapping slot → (cc_number, macro_index)

    Example:
        >>> parse_mapping_string("3:119:15")
        {3: (119, 15)}
    """
    mappings = {}
    for triplet in mapping_str.split(','):
        parts = triplet.strip().split(':')
        if len(parts) != 3:
            raise ValueError(f"Invalid mapping format: {triplet}. Expected slot:cc:macro")
        slot, cc, macro = map(int, parts)
        mappings[slot] = (cc, macro)
    return mappings
