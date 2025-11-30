#!/usr/bin/env python3
"""
Create Drum Rack by Note Name

Takes a donor .adg template with DrumCell devices and replaces samples
ordered by chromatic note name (C1, C#1, D1, ... G3).

Perfect for Auto Sampled folders with note-named samples.

Usage:
    python3 main_by_note_name.py template.adg "/path/to/sample_folder" output.adg
"""

import argparse
import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple

# Add the python directory to the Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg
from utils.transformer import transform_xml


def note_name_to_midi(note_name: str) -> int:
    """Convert note name (e.g., 'C1', 'A#2') to MIDI note number."""
    # Handle sharp notes
    if '#' in note_name:
        note_part = note_name[:-1]  # e.g., 'A#1' -> 'A#'
        octave = int(note_name[-1])
    else:
        note_part = note_name[:-1]  # e.g., 'C1' -> 'C'
        octave = int(note_name[-1])

    # Note mapping (C=0, C#=1, D=2, D#=3, E=4, F=5, F#=6, G=7, G#=8, A=9, A#=10, B=11)
    note_map = {
        'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
        'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11
    }

    if note_part not in note_map:
        raise ValueError(f"Invalid note: {note_part}")

    # MIDI note = (octave + 1) * 12 + note_offset
    # This gives us C1=24, C2=36, C3=48, etc.
    return (octave + 1) * 12 + note_map[note_part]


def parse_sample_filename(filename: str) -> Optional[str]:
    """
    Extract note name from Auto Sampled filename format.

    Examples:
        '1 by 1-C1-V127-8SHA.aif' -> 'C1'
        'Kit Name-A#2-V127-HASH.wav' -> 'A#2'

    Args:
        filename: Sample filename

    Returns:
        Note name (e.g., 'C1', 'A#2') or None if invalid
    """
    # Pattern: anything-NOTE-V###-ID.extension where NOTE is like C1, A#2, etc.
    pattern = r'^[^-]+-([A-G]#?\d+)-V\d+-[A-Z0-9]+\.(aif|wav)$'
    match = re.match(pattern, filename)
    if match:
        return match.group(1)  # Return the note part
    return None


def get_samples_ordered_by_note(sample_folder: Path) -> List[str]:
    """
    Get all samples from folder ordered by chromatic note name.

    Args:
        sample_folder: Path to folder containing Auto Sampled files

    Returns:
        List of 32 sample paths ordered C1, C#1, D1... G3 (None for missing notes)
    """
    # Collect samples by note name
    samples_by_note = {}

    # Look for .aif and .wav files
    for ext in ['*.aif', '*.wav']:
        for sample_file in sample_folder.glob(ext):
            note_name = parse_sample_filename(sample_file.name)
            if note_name:
                samples_by_note[note_name] = str(sample_file)

    print(f"\nFound {len(samples_by_note)} samples with note names:")

    # Generate chromatic note order from C1 to G3 (32 notes for drum rack)
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    ordered_samples = []

    pad_index = 0
    for octave in range(1, 4):  # Octaves 1, 2, 3
        for note in notes:
            if pad_index >= 32:  # Stop at 32 pads
                break

            note_name = f"{note}{octave}"

            # Add sample if we have it, otherwise None
            if note_name in samples_by_note:
                ordered_samples.append(samples_by_note[note_name])
                print(f"  Pad {pad_index + 1:2d}: {note_name:4s} -> {Path(samples_by_note[note_name]).name}")
            else:
                ordered_samples.append(None)
                print(f"  Pad {pad_index + 1:2d}: {note_name:4s} -> (empty)")

            pad_index += 1

            # Special case: G3 is the 32nd pad (last one)
            if note_name == "G3":
                break

        if pad_index >= 32:
            break

    # Ensure we have exactly 32 entries
    while len(ordered_samples) < 32:
        ordered_samples.append(None)

    sample_count = sum(1 for s in ordered_samples if s is not None)
    print(f"\nTotal samples mapped: {sample_count}/32")

    return ordered_samples[:32]


def main():
    parser = argparse.ArgumentParser(
        description='Create drum rack from samples ordered by note name',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 main_by_note_name.py template.adg sample_folder output.adg

    python3 main_by_note_name.py \\
        "/path/to/template.adg" \\
        "/Users/Shared/Music/Soundbanks/Konkrete/1 by 1" \\
        "1 by 1.adg"

Sample Format:
    Samples must follow Auto Sampled format:
    KitName-NoteName-V###-HASH.extension

    Examples:
        1 by 1-C1-V127-8SHA.aif
        Kit Name-A#2-V127-HASH.wav

Features:
    - Orders samples chromatically: C1, C#1, D1, ... G3
    - Uses DrumCell devices from template
    - Preserves all template settings (macros, effects, etc.)
    - Maps to 32 drum rack pads
        """
    )

    parser.add_argument(
        'template_file',
        type=str,
        help='Input template .adg file path (with DrumCell devices)'
    )
    parser.add_argument(
        'sample_folder',
        type=str,
        help='Path to folder containing Auto Sampled files'
    )
    parser.add_argument(
        'output_file',
        type=str,
        help='Output .adg file path'
    )

    try:
        args = parser.parse_args()
        template_path = Path(args.template_file)
        sample_folder = Path(args.sample_folder)
        output_path = Path(args.output_file)

        # Validate inputs
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        if not sample_folder.exists():
            raise FileNotFoundError(f"Sample folder not found: {sample_folder}")

        print(f"Template: {template_path}")
        print(f"Samples:  {sample_folder}")
        print(f"Output:   {output_path}")

        # Get samples ordered by note name
        ordered_samples = get_samples_ordered_by_note(sample_folder)

        # Check if we found any samples
        sample_count = sum(1 for s in ordered_samples if s is not None)
        if sample_count == 0:
            raise ValueError(f"No valid Auto Sampled files found in {sample_folder}")

        # Decode the template ADG file to XML
        print(f"\nDecoding template...")
        xml_content = decode_adg(template_path)

        # Transform the XML with our ordered samples
        print(f"\nReplacing samples in DrumCell devices...")
        transformed_xml = transform_xml(xml_content, ordered_samples)

        # Encode back to ADG
        print(f"\nEncoding to .adg format...")
        encode_adg(transformed_xml, output_path)

        print(f"\n✓ Successfully created: {output_path}")
        print(f"  Samples: {sample_count}/32 pads filled")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
