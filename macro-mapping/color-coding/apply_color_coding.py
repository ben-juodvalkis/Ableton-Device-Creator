#!/usr/bin/env python3
"""
Apply Color Coding to Drum Pads

Applies color coding to drum pads based on sample/device names.
Sets AutoColored=false and assigns colors by drum type.

Color scheme:
- Kick: Red (60)
- Snare/Rim/Clap: Yellow (13)
- Tom: Orange (9)
- Shaker: Green (26)
- Percussion: Green (26)
- Closed Hihat: Cyan (41)
- Cymbal: Blue (45)
- Open Hihat: Light Blue (43)
- Default: Orange (0)

Usage:
    python3 apply_color_coding.py input.adg output.adg
    python3 apply_color_coding.py input.adg output.adg --dry-run
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


# Color mapping for different drum types
DRUM_COLORS = {
    'kick': 60,           # Red
    'snare': 13,          # Yellow
    'rim': 13,            # Yellow
    'clap': 13,           # Yellow
    'tom': 9,             # Orange
    'shaker': 26,         # Green
    'percussion': 26,     # Green
    'closed_hihat': 41,   # Cyan
    'cymbal': 45,         # Blue
    'open_hihat': 43,     # Light Blue
    'default': 0          # Default/Orange
}


def categorize_pad(pad: ET.Element) -> str:
    """
    Categorize a drum pad by its name/sample.

    Returns category key matching DRUM_COLORS keys.
    """
    # Try to get pad name from various sources
    name = None

    # Try MultiSamplePart/Name (for OriginalSimpler/Simpler/MultiSampler)
    sample_name = pad.find('.//MultiSamplePart/Name')
    if sample_name is not None:
        name = sample_name.get('Value', '')

    # Try DrumCell UserName
    if not name:
        drumcell = pad.find('.//DrumCell')
        if drumcell is not None:
            user_name = drumcell.find('UserName')
            if user_name is not None:
                name = user_name.get('Value', '')

    # Try FileRef Path as fallback
    if not name:
        path_elem = pad.find('.//FileRef/Path')
        if path_elem is not None:
            path = path_elem.get('Value', '')
            if path:
                name = Path(path).stem

    # Try DeviceName as last resort
    if not name:
        device_name = pad.find('.//DeviceName')
        if device_name is not None:
            name = device_name.get('Value', '')

    if not name:
        return 'default'

    filename = name.lower()

    # Categorize based on name
    if 'kick' in filename or 'bd' in filename:
        return 'kick'
    elif 'snare' in filename or 'sd' in filename:
        return 'snare'
    elif 'rim' in filename or 'sidestick' in filename or 'stick' in filename:
        return 'rim'
    elif 'clap' in filename or 'snap' in filename or 'cp' in filename:
        return 'clap'
    elif 'closedhh' in filename or 'closed' in filename or 'chh' in filename:
        return 'closed_hihat'
    elif 'openhh' in filename or 'open' in filename or 'ohh' in filename:
        return 'open_hihat'
    elif 'pedalhh' in filename or 'pedal' in filename:
        return 'closed_hihat'
    elif 'tom' in filename or 'lt' in filename or 'mt' in filename or 'ht' in filename:
        return 'tom'
    elif 'shaker' in filename or 'cabasa' in filename or 'maraca' in filename:
        return 'shaker'
    elif 'cymbal' in filename or 'crash' in filename or 'ride' in filename or 'cy' in filename:
        return 'cymbal'
    elif 'perc' in filename or 'cowbell' in filename or 'bell' in filename or \
         'conga' in filename or 'bongo' in filename or 'clave' in filename:
        return 'percussion'
    elif 'hat' in filename or 'hh' in filename:
        return 'closed_hihat'
    else:
        return 'default'


def apply_color_coding(
    input_path: Path,
    output_path: Path,
    dry_run: bool = False,
    quiet: bool = False
) -> dict:
    """
    Apply color coding to all drum pads based on their names.

    Args:
        input_path: Path to input .adg file
        output_path: Path for output file
        dry_run: If True, analyze only
        quiet: If True, suppress detailed output

    Returns:
        Statistics dictionary
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not quiet:
        print(f"\n{'='*70}")
        print(f"APPLY COLOR CODING TO DRUM PADS")
        print(f"{'='*70}\n")
        print(f"Input: {input_path.name}")

        if dry_run:
            print("DRY RUN - No changes will be made\n")

    # Decode input
    xml_content = decode_adg(input_path)
    root = ET.fromstring(xml_content)

    # Find all drum pads
    drum_pads = root.findall('.//DrumBranchPreset')

    if not quiet:
        print(f"Found {len(drum_pads)} drum pads\n")

    stats = {
        'pads_found': len(drum_pads),
        'pads_colored': 0,
        'color_counts': {}
    }

    # Color each pad
    for pad in drum_pads:
        # Categorize the pad
        category = categorize_pad(pad)
        color_index = DRUM_COLORS.get(category, DRUM_COLORS['default'])

        # Track color usage
        if category not in stats['color_counts']:
            stats['color_counts'][category] = 0
        stats['color_counts'][category] += 1

        if not dry_run:
            # Set AutoColored to false
            auto_colored = pad.find('AutoColored')
            if auto_colored is None:
                auto_colored = ET.SubElement(pad, 'AutoColored')
            auto_colored.set('Value', 'false')

            # Set DocumentColorIndex
            color_elem = pad.find('DocumentColorIndex')
            if color_elem is None:
                color_elem = ET.SubElement(pad, 'DocumentColorIndex')
            color_elem.set('Value', str(color_index))

            # Set AutoColorScheme
            scheme_elem = pad.find('AutoColorScheme')
            if scheme_elem is None:
                scheme_elem = ET.SubElement(pad, 'AutoColorScheme')
            scheme_elem.set('Value', '0')

        stats['pads_colored'] += 1

    if not dry_run:
        # Convert to XML and encode
        output_xml = ET.tostring(root, encoding='unicode', xml_declaration=True)

        if not quiet:
            print(f"Writing colored rack: {output_path.name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(output_xml, output_path)

    if not quiet:
        print(f"\n{'='*70}")
        print(f"{'DRY RUN - ' if dry_run else ''}COLOR CODING SUMMARY")
        print(f"{'='*70}")
        print(f"Pads found:   {stats['pads_found']}")
        print(f"Pads colored: {stats['pads_colored']}")
        print(f"\nColor distribution:")
        for category, count in sorted(stats['color_counts'].items()):
            color_idx = DRUM_COLORS.get(category, 0)
            print(f"  {category:<15} (color {color_idx:>3}): {count} pad(s)")

        if not dry_run:
            print(f"\nOutput: {output_path}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Apply color coding to drum pads based on names',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Apply color coding
    python3 apply_color_coding.py input.adg output.adg

    # Preview what would be colored
    python3 apply_color_coding.py input.adg output.adg --dry-run

Color Scheme:
    Kick:          Red (60)
    Snare/Clap:    Yellow (13)
    Tom:           Orange (9)
    Hihat (closed):Cyan (41)
    Hihat (open):  Light Blue (43)
    Cymbal:        Blue (45)
    Shaker:        Green (26)
    Percussion:    Green (26)
    Default:       Orange (0)
        """
    )

    parser.add_argument('input', type=Path, help='Input .adg file')
    parser.add_argument('output', type=Path, help='Output .adg file')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')

    args = parser.parse_args()

    try:
        apply_color_coding(
            args.input,
            args.output,
            args.dry_run
        )

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
