#!/usr/bin/env python3
"""
Apply Color Coding to Drum Rack Pads

Colors drum pads based on sample filenames using Ableton's DocumentColorIndex system.

Color Scheme:
- Kick:        Red (60)
- Snare/Clap:  Yellow (13)
- Tom:         Orange (9)
- Shaker/Perc: Green (26)
- Closed HH:   Cyan (41)
- Cymbal:      Blue (45)
- Open HH:     Light Blue (43)
- Default:     Default (0)

Usage:
    python3 apply_drum_rack_colors.py input.adg output.adg
    python3 apply_drum_rack_colors.py input.adg --in-place
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


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


def categorize_sample(sample_path: str) -> str:
    """
    Categorize a sample by its filename.

    Args:
        sample_path: Full path to sample file

    Returns:
        Category key matching DRUM_COLORS keys
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


def get_sample_path_from_pad(pad: ET.Element) -> Optional[str]:
    """
    Extract sample path or name from a drum pad (DrumCell or Simpler).

    Args:
        pad: DrumBranchPreset element

    Returns:
        Sample path/name string, or None if not found
    """
    # Try to find any Name element with a meaningful value
    # These usually contain the sample/preset name
    for name_elem in pad.findall('.//Name'):
        name_value = name_elem.get('Value')
        if name_value and len(name_value) > 3:  # Skip very short/empty
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


def apply_drum_rack_colors(
    rack_path: Path,
    output_path: Path,
    color_scheme: str = 'default'
) -> Path:
    """
    Apply color coding to drum rack pads based on sample names.

    Args:
        rack_path: Path to input drum rack (.adg)
        output_path: Path for colored output rack
        color_scheme: Color scheme to use (currently only 'default' supported)

    Returns:
        Path to created colored rack

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If drum rack structure is invalid
    """
    # Validate input
    if not rack_path.exists():
        raise FileNotFoundError(f"Rack not found: {rack_path}")

    print(f"\n{'='*70}")
    print(f"APPLYING DRUM RACK COLORS")
    print(f"{'='*70}\n")

    # Decode rack
    print(f"Reading: {rack_path.name}")
    xml_content = decode_adg(rack_path)
    root = ET.fromstring(xml_content)

    # Find all drum pads
    pads = root.findall('.//DrumBranchPreset')

    # Sort by ReceivingNote DESCENDING (pad 1 = highest MIDI note)
    pads.sort(
        key=lambda pad: int(pad.find('.//ZoneSettings/ReceivingNote').get('Value')),
        reverse=True
    )

    print(f"Found {len(pads)} pads\n")

    # Apply colors
    colored_count = 0
    skipped_count = 0
    color_stats = {}

    # Build color map: pad_index → color_index
    pad_colors = {}

    for i, pad in enumerate(pads):
        # Get sample path
        sample_path = get_sample_path_from_pad(pad)

        if not sample_path:
            skipped_count += 1
            continue

        # Categorize and get color
        category = categorize_sample(sample_path)
        color_index = DRUM_COLORS.get(category, DRUM_COLORS['default'])

        # Track stats
        if category not in color_stats:
            color_stats[category] = 0
        color_stats[category] += 1

        # Store color for this pad
        pad_colors[i] = color_index
        colored_count += 1

        # Log sample
        sample_name = Path(sample_path).name
        print(f"  Pad {i+1:2d}: {sample_name[:50]:50s} [{category:15s}] Color {color_index}")

    # Convert to string for regex-based color application
    xml_string = ET.tostring(root, encoding='unicode', xml_declaration=True)

    # Apply colors using STRING REPLACEMENT (like macro config script)
    # This preserves exact formatting and structure
    import re

    # For each pad, find and replace/insert color elements
    drum_branch_sections = list(re.finditer(r'<DrumBranchPreset>(.*?)</DrumBranchPreset>', xml_string, re.DOTALL))

    print(f"\nApplying colors via string replacement to {len(drum_branch_sections)} pads...")

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
            xml_string = xml_string.replace(section_match.group(0), f'<DrumBranchPreset>{new_section}</DrumBranchPreset>')

    colored_xml = xml_string

    # Encode to .adg
    print(f"\nWriting colored rack: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(colored_xml, output_path)

    print(f"\n{'='*70}")
    print(f"✓ COLORING COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {output_path}")
    print(f"Colored: {colored_count} pads")
    print(f"Skipped: {skipped_count} pads (no sample)")

    if color_stats:
        print(f"\nColor Distribution:")
        for category in sorted(color_stats.keys()):
            count = color_stats[category]
            color_idx = DRUM_COLORS.get(category, 0)
            print(f"  {category:15s}: {count:3d} pads (color {color_idx})")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Apply color coding to drum rack pads based on sample names',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Color a drum rack
    python3 apply_drum_rack_colors.py input.adg colored.adg

    # Color in-place
    python3 apply_drum_rack_colors.py my_rack.adg --in-place

Color Scheme:
    Kick:        Red (60)
    Snare/Clap:  Yellow (13)
    Tom:         Orange (9)
    Shaker/Perc: Green (26)
    Closed HH:   Cyan (41)
    Cymbal:      Blue (45)
    Open HH:     Light Blue (43)
        """
    )

    parser.add_argument('input', type=Path, help='Input drum rack (.adg file)')
    parser.add_argument('output', type=Path, nargs='?', help='Output rack path (required unless --in-place)')
    parser.add_argument('--in-place', action='store_true', help='Modify input file directly')

    args = parser.parse_args()

    # Validate arguments
    if not args.in_place and not args.output:
        parser.error("Either provide an output file or use --in-place")

    # Determine output path
    output_path = args.input if args.in_place else args.output

    try:
        apply_drum_rack_colors(args.input, output_path)

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
