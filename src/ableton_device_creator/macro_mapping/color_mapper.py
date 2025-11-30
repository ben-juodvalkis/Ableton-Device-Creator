"""
Drum pad color coding utilities.

This module consolidates functionality from:
- apply_drum_rack_colors.py
- apply_color_coding.py
- batch_apply_colors.py
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Union
import logging

from ..core import decode_adg, encode_adg

logger = logging.getLogger(__name__)


# Ableton DocumentColorIndex values
DRUM_COLORS = {
    'kick': 60,        # Red
    'snare': 13,       # Yellow
    'rim': 13,         # Yellow
    'clap': 13,        # Yellow
    'snap': 13,        # Yellow
    'tom': 9,          # Orange
    'shaker': 26,      # Green
    'cabasa': 26,      # Green
    'percussion': 26,  # Green
    'perc': 26,        # Green
    'cowbell': 26,     # Green
    'conga': 26,       # Green
    'closed_hihat': 41,# Cyan
    'closedhh': 41,    # Cyan
    'closed': 41,      # Cyan (when contains 'hh' or 'hat')
    'pedalhh': 41,     # Cyan
    'cymbal': 45,      # Blue
    'crash': 45,       # Blue
    'ride': 45,        # Blue
    'open_hihat': 43,  # Light Blue
    'openhh': 43,      # Light Blue
    'open': 43,        # Light Blue (when contains 'hh' or 'hat')
    'default': 0       # Default
}


class DrumPadColorMapper:
    """
    Apply color coding to drum rack pads based on sample names.

    Consolidates functionality from:
    - apply_drum_rack_colors.py
    - apply_color_coding.py

    Example:
        >>> colorizer = DrumPadColorMapper("input.adg")
        >>> colorizer.apply_colors()
        >>> colorizer.save("colored.adg")
    """

    def __init__(self, rack_path: Union[str, Path], color_scheme: Optional[Dict[str, int]] = None):
        """
        Initialize color mapper with drum rack.

        Args:
            rack_path: Path to drum rack .adg file
            color_scheme: Custom color mapping (uses DRUM_COLORS if None)
        """
        self.rack_path = Path(rack_path)
        if not self.rack_path.exists():
            raise FileNotFoundError(f"Rack not found: {self.rack_path}")

        self.color_scheme = color_scheme or DRUM_COLORS

        # Decode and parse XML
        xml_content = decode_adg(self.rack_path)
        self.root = ET.fromstring(xml_content)

        # Statistics
        self.stats = {
            'colored': 0,
            'skipped': 0,
            'by_category': {}
        }

    def apply_colors(self) -> 'DrumPadColorMapper':
        """
        Apply color coding to all drum pads based on sample names.

        Returns:
            Self for method chaining

        Example:
            >>> colorizer.apply_colors()
        """
        # Find all drum pads
        pads = self.root.findall('.//DrumBranchPreset')

        # Sort by ReceivingNote DESCENDING (pad 1 = highest MIDI note)
        pads.sort(
            key=lambda pad: int(pad.find('.//ZoneSettings/ReceivingNote').get('Value')),
            reverse=True
        )

        logger.info(f"Found {len(pads)} pads")

        # Build color map: pad_index → color_index
        pad_colors = {}

        for i, pad in enumerate(pads):
            # Get sample path
            sample_path = self._get_sample_path_from_pad(pad)

            if not sample_path:
                self.stats['skipped'] += 1
                continue

            # Categorize and get color
            category = self._categorize_sample(sample_path)
            color_index = self.color_scheme.get(category, self.color_scheme['default'])

            # Track stats
            if category not in self.stats['by_category']:
                self.stats['by_category'][category] = 0
            self.stats['by_category'][category] += 1

            # Store color for this pad
            pad_colors[i] = color_index
            self.stats['colored'] += 1

            sample_name = Path(sample_path).name
            logger.debug(f"Pad {i+1}: {sample_name} [{category}] Color {color_index}")

        # Apply colors using string replacement (preserves formatting)
        self._apply_colors_to_xml(pad_colors)

        logger.info(f"Colored {self.stats['colored']} pads, skipped {self.stats['skipped']}")

        return self

    def _get_sample_path_from_pad(self, pad: ET.Element) -> Optional[str]:
        """
        Extract sample path or name from a drum pad.

        Args:
            pad: DrumBranchPreset element

        Returns:
            Sample path/name string, or None if not found
        """
        # Try to find any Name element with meaningful value
        for name_elem in pad.findall('.//Name'):
            name_value = name_elem.get('Value')
            if name_value and len(name_value) > 3:
                # Skip if it looks like a pack name
                if 'Pack' not in name_value and 'Library' not in name_value:
                    return name_value

        # Try DrumCell path
        drumcell_path = pad.find('.//DrumCell/UserSample/Value/SampleRef/FileRef/Path')
        if drumcell_path is not None:
            return drumcell_path.get('Value')

        # Try Simpler path (multi-sample)
        simpler_path = pad.find('.//OriginalSimpler/MultiSampleMap/SampleParts/MultiSamplePart/SampleRef/FileRef/Path')
        if simpler_path is not None:
            return simpler_path.get('Value')

        return None

    def _categorize_sample(self, sample_path: str) -> str:
        """
        Categorize a sample by its filename.

        Args:
            sample_path: Full path to sample file

        Returns:
            Category key matching color scheme keys
        """
        if not sample_path:
            return 'default'

        filename = Path(sample_path).stem.lower()

        # Check for specific categories (order matters!)
        if 'kick' in filename:
            return 'kick'
        elif 'snare' in filename:
            return 'snare'
        elif 'rim' in filename or 'sidestick' in filename or 'stick' in filename:
            return 'rim'
        elif 'clap' in filename or 'snap' in filename:
            return 'clap'
        elif 'closedhh' in filename or ('closed' in filename and ('hh' in filename or 'hat' in filename)):
            return 'closed_hihat'
        elif 'openhh' in filename or ('open' in filename and ('hh' in filename or 'hat' in filename)):
            return 'open_hihat'
        elif 'pedalhh' in filename or 'pedal' in filename:
            return 'closed_hihat'
        elif 'tom' in filename:
            return 'tom'
        elif 'shaker' in filename or 'cabasa' in filename:
            return 'shaker'
        elif 'cymbal' in filename or 'crash' in filename or 'ride' in filename:
            return 'cymbal'
        elif 'perc' in filename or 'cowbell' in filename or 'bell' in filename or \
             'cuica' in filename or 'conga' in filename:
            return 'percussion'
        else:
            return 'default'

    def _apply_colors_to_xml(self, pad_colors: Dict[int, int]) -> None:
        """
        Apply colors to XML using string replacement.

        This preserves exact formatting and structure.

        Args:
            pad_colors: Dict mapping pad_index → color_index
        """
        # Convert to string
        xml_string = ET.tostring(self.root, encoding='unicode', xml_declaration=True)

        # Find all DrumBranchPreset sections
        drum_branch_sections = list(re.finditer(
            r'<DrumBranchPreset>(.*?)</DrumBranchPreset>',
            xml_string,
            re.DOTALL
        ))

        logger.debug(f"Found {len(drum_branch_sections)} DrumBranchPreset sections in XML")

        # Apply colors via string replacement
        for pad_index, color_index in pad_colors.items():
            if pad_index < len(drum_branch_sections):
                section_match = drum_branch_sections[pad_index]
                section = section_match.group(1)

                # Check if DocumentColorIndex exists
                if '<DocumentColorIndex' in section:
                    # Update existing
                    new_section = re.sub(
                        r'<DocumentColorIndex Value="\d+" />',
                        f'<DocumentColorIndex Value="{color_index}" />',
                        section
                    )
                    # Update AutoColored
                    new_section = re.sub(
                        r'<AutoColored Value="true" />',
                        r'<AutoColored Value="false" />',
                        new_section
                    )
                else:
                    # Insert new elements after SessionViewBranchWidth
                    new_section = re.sub(
                        r'(<SessionViewBranchWidth Value="\d+" />)',
                        rf'\1\n\t\t\t\t<DocumentColorIndex Value="{color_index}" />\n\t\t\t\t<AutoColored Value="false" />\n\t\t\t\t<AutoColorScheme Value="0" />',
                        section
                    )

                # Replace in full XML
                xml_string = xml_string.replace(
                    section_match.group(0),
                    f'<DrumBranchPreset>{new_section}</DrumBranchPreset>'
                )

        # Update root from modified string
        self.root = ET.fromstring(xml_string)

    def get_stats(self) -> Dict:
        """
        Get coloring statistics.

        Returns:
            Dictionary with statistics

        Example:
            >>> stats = colorizer.get_stats()
            >>> print(f"Colored {stats['colored']} pads")
        """
        return self.stats.copy()

    def save(self, output_path: Union[str, Path]) -> Path:
        """
        Save colored rack to file.

        Args:
            output_path: Where to save .adg file

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        xml_string = ET.tostring(self.root, encoding='unicode', xml_declaration=True)
        encode_adg(xml_string, output_path)

        logger.info(f"Saved colored rack to {output_path}")

        return output_path
