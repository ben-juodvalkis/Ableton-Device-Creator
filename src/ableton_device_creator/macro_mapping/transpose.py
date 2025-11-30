"""
Transpose parameter mapping utilities.

This module consolidates functionality from:
- batch_add_transpose_mapping.py
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Union
import logging

from ..core import decode_adg, encode_adg

logger = logging.getLogger(__name__)


class TransposeMapper:
    """
    Map transpose parameters to macros in instrument racks.

    Consolidates functionality from batch_add_transpose_mapping.py

    The transpose parameter range is ±48 semitones:
    - Macro value 0 = -48 semitones (lowest)
    - Macro value 63.5 = 0 semitones (center, no transpose)
    - Macro value 127 = +48 semitones (highest)

    Example:
        >>> mapper = TransposeMapper("input.adg")
        >>> mapper.add_transpose_mapping(macro_index=15)  # Map to Macro 16
        >>> mapper.save("output.adg")
    """

    def __init__(self, rack_path: Union[str, Path]):
        """
        Initialize transpose mapper with instrument rack.

        Args:
            rack_path: Path to instrument rack .adg file
        """
        self.rack_path = Path(rack_path)
        if not self.rack_path.exists():
            raise FileNotFoundError(f"Rack not found: {self.rack_path}")

        # Decode and parse XML
        xml_content = decode_adg(self.rack_path)
        self.root = ET.fromstring(xml_content)

        # Statistics
        self.stats = {
            'transpose_params_found': 0,
            'mappings_added': 0,
            'mappings_already_exist': 0,
            'macros_updated': 0
        }

    def add_transpose_mapping(
        self,
        macro_index: int,
        macro_value: float = 63.5
    ) -> 'TransposeMapper':
        """
        Add transpose-to-macro mappings to all MultiSampler/Simpler devices.

        Args:
            macro_index: Target macro index (0-15 for Macros 1-16)
            macro_value: Initial macro value (0-127, default 63.5 = center = 0 transpose)

        Returns:
            Self for method chaining

        Example:
            >>> mapper.add_transpose_mapping(macro_index=15, macro_value=63.5)
        """
        if not 0 <= macro_index <= 15:
            raise ValueError(f"Macro index must be 0-15, got {macro_index}")
        if not 0 <= macro_value <= 127:
            raise ValueError(f"Macro value must be 0-127, got {macro_value}")

        # Find all TransposeKey parameters in MultiSampler/Simpler devices
        transpose_keys = self.root.findall('.//TransposeKey')
        self.stats['transpose_params_found'] = len(transpose_keys)

        logger.info(f"Found {len(transpose_keys)} transpose parameters")

        for transpose_key in transpose_keys:
            # Check if KeyMidi already exists
            existing_keymidi = transpose_key.find('KeyMidi')

            if existing_keymidi is not None:
                # Check if it's mapped to our target macro
                controller = existing_keymidi.find('NoteOrController')
                if controller is not None and controller.get('Value') == str(macro_index):
                    self.stats['mappings_already_exist'] += 1
                    continue

            # Add KeyMidi mapping
            keymidi = self._create_keymidi_element(macro_index)

            # Find insertion point (after LomId)
            lom_id_index = None
            for i, child in enumerate(transpose_key):
                if child.tag == 'LomId':
                    lom_id_index = i
                    break

            if lom_id_index is not None:
                transpose_key.insert(lom_id_index + 1, keymidi)
                self.stats['mappings_added'] += 1

        # Update macro settings in the parent instrument rack
        self._update_macro_settings(macro_index, macro_value)

        logger.info(f"Added {self.stats['mappings_added']} transpose mappings to Macro {macro_index + 1}")

        return self

    def _create_keymidi_element(self, macro_index: int) -> ET.Element:
        """
        Create a KeyMidi mapping element for macro control.

        Args:
            macro_index: Macro index (0-15 for Macros 1-16)

        Returns:
            KeyMidi element ready to insert into parameter
        """
        keymidi = ET.Element('KeyMidi')
        ET.SubElement(keymidi, 'PersistentKeyString').set('Value', '')
        ET.SubElement(keymidi, 'IsNote').set('Value', 'false')
        ET.SubElement(keymidi, 'Channel').set('Value', '16')
        ET.SubElement(keymidi, 'NoteOrController').set('Value', str(macro_index))
        ET.SubElement(keymidi, 'LowerRangeNote').set('Value', '-1')
        ET.SubElement(keymidi, 'UpperRangeNote').set('Value', '-1')
        ET.SubElement(keymidi, 'ControllerMapMode').set('Value', '0')
        return keymidi

    def _update_macro_settings(self, macro_index: int, macro_value: float) -> None:
        """
        Update macro control settings.

        Args:
            macro_index: Macro index (0-15)
            macro_value: Macro value (0-127)
        """
        # Find MacroControls and MacroDefaults
        macro_control_path = f'.//MacroControls.{macro_index}'
        macro_default_path = f'.//MacroDefaults.{macro_index}'

        macro_control = self.root.find(macro_control_path)
        if macro_control is not None:
            manual = macro_control.find('Manual')
            if manual is not None:
                # Set to specified value (default 63.5 = center = 0 transpose)
                manual.set('Value', str(macro_value))
                self.stats['macros_updated'] += 1

        macro_default = self.root.find(macro_default_path)
        if macro_default is not None:
            # Set to -1 to preserve current value on load
            macro_default.set('Value', '-1')

    def get_stats(self) -> Dict:
        """
        Get mapping statistics.

        Returns:
            Dictionary with statistics

        Example:
            >>> stats = mapper.get_stats()
            >>> print(f"Added {stats['mappings_added']} mappings")
        """
        return self.stats.copy()

    def save(self, output_path: Union[str, Path]) -> Path:
        """
        Save rack with transpose mappings to file.

        Args:
            output_path: Where to save .adg file

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        xml_string = ET.tostring(self.root, encoding='unicode', xml_declaration=True)
        encode_adg(xml_string, output_path)

        logger.info(f"Saved rack with transpose mappings to {output_path}")

        return output_path
