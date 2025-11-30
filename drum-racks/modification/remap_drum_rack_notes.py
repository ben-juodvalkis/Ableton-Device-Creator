#!/usr/bin/env python3
"""
Remap Drum Rack MIDI Notes

Shifts all drum pad MIDI notes by a specified amount and updates the view scroll position.

Usage:
    python3 remap_drum_rack_notes.py input.adg output.adg --shift 28 --scroll-shift 7
    python3 remap_drum_rack_notes.py input.adg output.adg --shift 28 --scroll-shift 7 --verbose
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def remap_midi_notes(xml_content: str, shift: int, scroll_shift: int = 0, verbose: bool = False) -> str:
    """
    Shift all MIDI notes in a drum rack by a specified amount.

    Args:
        xml_content: XML content string
        shift: Amount to shift MIDI notes (can be positive or negative)
        scroll_shift: Amount to shift the pad scroll position
        verbose: Print detailed information

    Returns:
        Modified XML content
    """
    root = ET.fromstring(xml_content)

    # Find all drum pads
    drum_pads = root.findall('.//DrumBranchPreset')

    print(f"\nFound {len(drum_pads)} drum pads")
    print(f"Shifting MIDI notes by: {shift:+d}")
    if scroll_shift != 0:
        print(f"Shifting view scroll by: {scroll_shift:+d}")

    changes = []

    # Shift MIDI notes for each pad
    for i, pad in enumerate(drum_pads):
        zone_settings = pad.find('.//ZoneSettings/ReceivingNote')
        if zone_settings is not None:
            old_note = int(zone_settings.get('Value'))
            new_note = old_note + shift

            # Clamp to valid MIDI range (0-127)
            if new_note < 0:
                print(f"  Warning: Pad {i+1} note {old_note} + {shift} = {new_note} is below 0, clamping to 0")
                new_note = 0
            elif new_note > 127:
                print(f"  Warning: Pad {i+1} note {old_note} + {shift} = {new_note} is above 127, clamping to 127")
                new_note = 127

            zone_settings.set('Value', str(new_note))
            changes.append((i+1, old_note, new_note))

            if verbose:
                print(f"  Pad {i+1}: MIDI {old_note} → {new_note}")

    # Shift the pad scroll position if requested
    if scroll_shift != 0:
        scroll_elem = root.find('.//PadScrollPosition')
        if scroll_elem is not None:
            old_scroll = int(scroll_elem.get('Value'))
            new_scroll = old_scroll + scroll_shift

            # Clamp to reasonable range (0-127)
            new_scroll = max(0, min(127, new_scroll))

            scroll_elem.set('Value', str(new_scroll))
            print(f"\nView scroll position: {old_scroll} → {new_scroll}")
        else:
            print("\n  Warning: PadScrollPosition not found in XML")

    print(f"\nSuccessfully shifted {len(changes)} pad MIDI notes")

    return ET.tostring(root, encoding='unicode', xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(
        description='Remap MIDI notes in a drum rack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Shift all notes up by 28 semitones (matching your example: 64→92)
    python3 remap_drum_rack_notes.py input.adg output.adg --shift 28

    # Shift notes and view position (matching your rack-remap.adg changes)
    python3 remap_drum_rack_notes.py input.adg output.adg --shift 28 --scroll-shift 7

    # Shift notes down by 12 semitones (one octave down)
    python3 remap_drum_rack_notes.py input.adg output.adg --shift -12

    # Verbose output
    python3 remap_drum_rack_notes.py input.adg output.adg --shift 28 --verbose
        """
    )

    parser.add_argument('input', type=Path, help='Input drum rack (.adg file)')
    parser.add_argument('output', type=Path, help='Output drum rack (.adg file)')
    parser.add_argument(
        '--shift',
        type=int,
        required=True,
        help='Amount to shift MIDI notes (e.g., 28 for two octaves + 4 semitones up)'
    )
    parser.add_argument(
        '--scroll-shift',
        type=int,
        default=0,
        help='Amount to shift the pad scroll position (default: 0)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed information about each pad'
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.input.exists():
        print(f"✗ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.output.exists():
        response = input(f"⚠ Output file already exists: {args.output}\nOverwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    try:
        print(f"\n{'='*80}")
        print(f"REMAPPING DRUM RACK NOTES")
        print(f"{'='*80}")
        print(f"\nInput:  {args.input}")
        print(f"Output: {args.output}")

        # Decode the ADG file
        xml_content = decode_adg(args.input)

        # Remap the MIDI notes
        transformed_xml = remap_midi_notes(
            xml_content,
            args.shift,
            args.scroll_shift,
            args.verbose
        )

        # Encode back to ADG
        encode_adg(transformed_xml, args.output)

        print(f"\n✓ Successfully created: {args.output}")
        print(f"\n{'='*80}\n")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
