"""
Drum rack modification utilities.

This module provides tools for modifying existing drum racks:
- Remap MIDI notes (shift which keys trigger which pads)
- Trim to 16 pads
- Merge multiple racks
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

from ..core import decode_adg, encode_adg

logger = logging.getLogger(__name__)


class DrumRackModifier:
    """
    Modify existing drum racks.

    Consolidates functionality from:
    - remap_drum_rack_notes.py
    - trim_drum_rack_to_16.py
    - merge_drum_racks.py

    Example:
        >>> modifier = DrumRackModifier("input.adg")
        >>> modifier.remap_notes(shift=28)  # Shift up 2 octaves + 4 semitones
        >>> modifier.save("output.adg")
    """

    def __init__(self, rack_path: Union[str, Path]):
        """
        Initialize modifier with drum rack.

        Args:
            rack_path: Path to drum rack .adg file
        """
        self.rack_path = Path(rack_path)
        if not self.rack_path.exists():
            raise FileNotFoundError(f"Rack not found: {self.rack_path}")

        # Decode and parse XML
        xml_content = decode_adg(self.rack_path)
        self.root = ET.fromstring(xml_content)

        # Statistics
        self.stats = {
            'notes_remapped': 0,
            'pads_found': 0,
            'scroll_updated': False,
        }

    def remap_notes(
        self,
        shift: int,
        scroll_shift: int = 0,
        clamp: bool = True
    ) -> 'DrumRackModifier':
        """
        Shift all MIDI note assignments by a specified amount.

        This changes which MIDI notes trigger which pads, effectively
        "transposing" the keyboard layout of the drum rack.

        Args:
            shift: Amount to shift MIDI notes (positive = up, negative = down)
            scroll_shift: Amount to shift pad view scroll position
            clamp: If True, clamp notes to valid MIDI range (0-127)

        Returns:
            Self for method chaining

        Example:
            >>> # Shift all pads up 2 octaves (24 semitones)
            >>> modifier.remap_notes(shift=24)
            >>>
            >>> # Shift down 1 octave
            >>> modifier.remap_notes(shift=-12)
            >>>
            >>> # Shift up and adjust view
            >>> modifier.remap_notes(shift=28, scroll_shift=7)
        """
        # Find all drum pads
        drum_pads = self.root.findall('.//DrumBranchPreset')
        self.stats['pads_found'] = len(drum_pads)

        logger.info(f"Found {len(drum_pads)} drum pads, shifting by {shift:+d}")

        # Shift MIDI notes for each pad
        changes = []
        for i, pad in enumerate(drum_pads):
            zone_settings = pad.find('.//ZoneSettings/ReceivingNote')
            if zone_settings is not None:
                old_note = int(zone_settings.get('Value'))
                new_note = old_note + shift

                # Clamp to valid MIDI range if requested
                if clamp:
                    if new_note < 0:
                        logger.warning(f"Pad {i+1} note {old_note} + {shift} = {new_note} < 0, clamping to 0")
                        new_note = 0
                    elif new_note > 127:
                        logger.warning(f"Pad {i+1} note {old_note} + {shift} = {new_note} > 127, clamping to 127")
                        new_note = 127

                zone_settings.set('Value', str(new_note))
                changes.append((i+1, old_note, new_note))
                logger.debug(f"Pad {i+1}: MIDI {old_note} → {new_note}")

        self.stats['notes_remapped'] = len(changes)

        # Shift the pad scroll position if requested
        if scroll_shift != 0:
            scroll_elem = self.root.find('.//PadScrollPosition')
            if scroll_elem is not None:
                old_scroll = int(scroll_elem.get('Value'))
                new_scroll = old_scroll + scroll_shift

                # Clamp to reasonable range (0-127)
                new_scroll = max(0, min(127, new_scroll))

                scroll_elem.set('Value', str(new_scroll))
                self.stats['scroll_updated'] = True
                logger.info(f"View scroll: {old_scroll} → {new_scroll}")

        logger.info(f"Remapped {len(changes)} pad MIDI notes")

        return self

    def get_note_mappings(self) -> Dict[int, int]:
        """
        Get current MIDI note mappings.

        Returns:
            Dict mapping pad_index → MIDI note number

        Example:
            >>> mappings = modifier.get_note_mappings()
            >>> print(f"Pad 1 responds to MIDI note {mappings[0]}")
        """
        drum_pads = self.root.findall('.//DrumBranchPreset')
        mappings = {}

        for i, pad in enumerate(drum_pads):
            zone_settings = pad.find('.//ZoneSettings/ReceivingNote')
            if zone_settings is not None:
                note = int(zone_settings.get('Value'))
                mappings[i] = note

        return mappings

    def set_note_mapping(self, pad_index: int, midi_note: int) -> 'DrumRackModifier':
        """
        Set MIDI note for a specific pad.

        Args:
            pad_index: Pad index (0-based)
            midi_note: MIDI note number (0-127)

        Returns:
            Self for method chaining

        Example:
            >>> # Map pad 0 to middle C (MIDI 60)
            >>> modifier.set_note_mapping(0, 60)
        """
        if not 0 <= midi_note <= 127:
            raise ValueError(f"MIDI note must be 0-127, got {midi_note}")

        drum_pads = self.root.findall('.//DrumBranchPreset')
        if not 0 <= pad_index < len(drum_pads):
            raise ValueError(f"Pad index must be 0-{len(drum_pads)-1}, got {pad_index}")

        pad = drum_pads[pad_index]
        zone_settings = pad.find('.//ZoneSettings/ReceivingNote')
        if zone_settings is not None:
            old_note = int(zone_settings.get('Value'))
            zone_settings.set('Value', str(midi_note))
            logger.info(f"Pad {pad_index}: MIDI {old_note} → {midi_note}")

        return self

    def get_stats(self) -> Dict:
        """
        Get modification statistics.

        Returns:
            Dictionary with statistics

        Example:
            >>> stats = modifier.get_stats()
            >>> print(f"Remapped {stats['notes_remapped']} notes")
        """
        return self.stats.copy()

    def save(self, output_path: Union[str, Path]) -> Path:
        """
        Save modified rack to file.

        Args:
            output_path: Where to save .adg file

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        xml_string = ET.tostring(self.root, encoding='unicode', xml_declaration=True)
        encode_adg(xml_string, output_path)

        logger.info(f"Saved modified rack to {output_path}")

        return output_path
