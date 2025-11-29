#!/usr/bin/env python3
"""
Disable Auto-Coloring on Drum Pads

Sets all drum pads to manual coloring (AutoColored=false) with a specified color.
This is the equivalent of clicking "Color from: Automatically" in Ableton to set
all pads to the same color.

Usage:
    python3 disable_auto_color.py input.adg output.adg
    python3 disable_auto_color.py input.adg output.adg --color 0
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def disable_auto_color(
    input_path: Path,
    output_path: Path,
    color_index: int = 0,
    dry_run: bool = False
) -> dict:
    """
    Disable auto-coloring on all drum pads.

    Args:
        input_path: Path to input .adg file
        output_path: Path for output file
        color_index: Color to apply (0 = default/orange, see Ableton colors)
        dry_run: If True, analyze only

    Returns:
        Statistics dictionary
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"\n{'='*70}")
    print(f"DISABLE AUTO-COLORING ON DRUM PADS")
    print(f"{'='*70}\n")
    print(f"Input: {input_path.name}")
    print(f"Color index: {color_index}")

    if dry_run:
        print("DRY RUN - No changes will be made\n")

    # Decode input
    xml_content = decode_adg(input_path)
    root = ET.fromstring(xml_content)

    # Find all drum pads
    drum_pads = root.findall('.//DrumBranchPreset')

    print(f"Found {len(drum_pads)} drum pads\n")

    stats = {
        'pads_found': len(drum_pads),
        'pads_changed': 0
    }

    for pad in drum_pads:
        # Set AutoColored to false
        auto_colored = pad.find('AutoColored')
        if auto_colored is None:
            auto_colored = ET.SubElement(pad, 'AutoColored')

        old_auto = auto_colored.get('Value', 'N/A')
        if not dry_run:
            auto_colored.set('Value', 'false')

        # Set DocumentColorIndex
        color_elem = pad.find('DocumentColorIndex')
        if color_elem is None:
            color_elem = ET.SubElement(pad, 'DocumentColorIndex')

        old_color = color_elem.get('Value', 'N/A')
        if not dry_run:
            color_elem.set('Value', str(color_index))

        # Set AutoColorScheme (always 0 for manual)
        scheme_elem = pad.find('AutoColorScheme')
        if scheme_elem is None:
            scheme_elem = ET.SubElement(pad, 'AutoColorScheme')

        if not dry_run:
            scheme_elem.set('Value', '0')

        stats['pads_changed'] += 1

    if not dry_run:
        # Convert to XML and encode
        output_xml = ET.tostring(root, encoding='unicode', xml_declaration=True)

        print(f"Writing output: {output_path.name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(output_xml, output_path)

    print(f"\n{'='*70}")
    print(f"{'DRY RUN - ' if dry_run else ''}SUMMARY")
    print(f"{'='*70}")
    print(f"Pads found:    {stats['pads_found']}")
    print(f"Pads changed:  {stats['pads_changed']}")

    if not dry_run:
        print(f"\nOutput: {output_path}")
        print(f"All pads set to: AutoColored=false, DocumentColorIndex={color_index}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Disable auto-coloring on drum pads',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Set all pads to default color (0)
    python3 disable_auto_color.py input.adg output.adg

    # Set all pads to specific color
    python3 disable_auto_color.py input.adg output.adg --color 60

    # Preview changes
    python3 disable_auto_color.py input.adg output.adg --dry-run

Ableton Color Indices (common values):
    0  = Default (orange)
    13 = Yellow
    26 = Green
    41 = Cyan
    45 = Blue
    60 = Red
        """
    )

    parser.add_argument('input', type=Path, help='Input .adg file')
    parser.add_argument('output', type=Path, help='Output .adg file')
    parser.add_argument('--color', type=int, default=0, help='Color index (default: 0)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')

    args = parser.parse_args()

    try:
        disable_auto_color(
            args.input,
            args.output,
            args.color,
            args.dry_run
        )

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
