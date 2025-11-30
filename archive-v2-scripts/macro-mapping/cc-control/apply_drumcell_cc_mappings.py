#!/usr/bin/env python3
"""
Apply DrumCell CC Mappings to Drum Rack

Extracts MIDI CC mapping pattern from a template drum rack and applies it to all
DrumCell devices in a target drum rack.

Supports:
- Voice_Transpose (CC#3)
- Voice_VelocityToVolume (CC#12)
- Voice_ModulationTarget (CC#14)
- Voice_PlaybackStart (CC#15)
- Voice_PlaybackLength (CC#16)
- Voice_Decay (CC#17)
- Voice_SamplePitch (CC#18)
- Filter parameters, Volume, Pan, etc.

Usage:
    # Use built-in template
    python3 apply_drumcell_cc_mappings.py input.adg output.adg

    # Use custom template
    python3 apply_drumcell_cc_mappings.py input.adg output.adg --template custom.adg

    # Dry run (show what would be mapped)
    python3 apply_drumcell_cc_mappings.py input.adg output.adg --dry-run

    # Custom channel and CC assignments
    python3 apply_drumcell_cc_mappings.py input.adg output.adg --channel 1 --transpose-cc 20
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


@dataclass
class CCMapping:
    """Represents a MIDI CC mapping configuration."""
    parameter_path: str  # XPath to parameter (e.g., './/Voice_Transpose')
    cc_number: int
    channel: int = 16
    description: str = ""


# Default mapping template (extracted from your mapped.adg)
DEFAULT_MAPPINGS = [
    CCMapping('.//Voice_Transpose', 3, 16, "Transpose (pitch)"),
    CCMapping('.//Voice_VelocityToVolume', 12, 16, "Velocity to Volume"),
    CCMapping('.//Voice_ModulationTarget', 14, 16, "Modulation Target"),
    CCMapping('.//Voice_PlaybackStart', 15, 16, "Sample Start"),
    CCMapping('.//Voice_PlaybackLength', 16, 16, "Sample Length"),
    CCMapping('.//Voice_Decay', 17, 16, "Decay Time"),
    CCMapping('.//Voice_SamplePitch', 18, 16, "Sample Pitch"),
    CCMapping('.//Volume/Manual', 7, 16, "Volume"),
    CCMapping('.//Pan/Manual', 10, 16, "Pan"),
]


def create_keymidi_element(cc_number: int, channel: int = 16) -> ET.Element:
    """
    Create a KeyMidi XML element for MIDI CC mapping.

    Args:
        cc_number: MIDI CC number (0-127)
        channel: MIDI channel (1-16)

    Returns:
        KeyMidi Element
    """
    keymidi = ET.Element('KeyMidi')

    # Add child elements
    ET.SubElement(keymidi, 'PersistentKeyString').set('Value', '')
    ET.SubElement(keymidi, 'IsNote').set('Value', 'false')
    ET.SubElement(keymidi, 'Channel').set('Value', str(channel))
    ET.SubElement(keymidi, 'NoteOrController').set('Value', str(cc_number))
    ET.SubElement(keymidi, 'LowerRangeNote').set('Value', '-1')
    ET.SubElement(keymidi, 'UpperRangeNote').set('Value', '-1')
    ET.SubElement(keymidi, 'ControllerMapMode').set('Value', '0')

    return keymidi


def extract_mappings_from_template(template_path: Path) -> List[CCMapping]:
    """
    Extract CC mappings from a template drum rack.

    Analyzes the first DrumCell device and extracts all KeyMidi mappings.

    Args:
        template_path: Path to template .adg file

    Returns:
        List of CCMapping objects
    """
    print(f"Extracting mappings from template: {template_path.name}")

    xml = decode_adg(template_path)
    root = ET.fromstring(xml)

    mappings = []

    # Find first DrumCell with KeyMidi mappings
    drumcells = root.findall('.//DrumCell')

    if not drumcells:
        print("  ⚠️  No DrumCell devices found in template")
        return DEFAULT_MAPPINGS

    # Analyze first DrumCell
    drumcell = drumcells[0]

    # Common parameters to check
    param_names = [
        'Voice_Transpose',
        'Voice_Detune',
        'Voice_VelocityToVolume',
        'Voice_ModulationTarget',
        'Voice_PlaybackStart',
        'Voice_PlaybackLength',
        'Voice_Decay',
        'Voice_SamplePitch',
    ]

    for param_name in param_names:
        param = drumcell.find(f'.//{param_name}')
        if param is not None:
            keymidi = param.find('./KeyMidi')
            if keymidi is not None:
                cc_elem = keymidi.find('./NoteOrController')
                channel_elem = keymidi.find('./Channel')

                if cc_elem is not None and channel_elem is not None:
                    cc_number = int(cc_elem.get('Value'))
                    channel = int(channel_elem.get('Value'))

                    mappings.append(CCMapping(
                        f'.//{param_name}',
                        cc_number,
                        channel,
                        param_name.replace('_', ' ')
                    ))

    if mappings:
        print(f"  ✓ Extracted {len(mappings)} mappings from template")
        for mapping in mappings:
            print(f"    • {mapping.description}: CC#{mapping.cc_number} (Ch {mapping.channel})")
    else:
        print("  ⚠️  No mappings found in template, using defaults")
        return DEFAULT_MAPPINGS

    return mappings


def apply_cc_mapping_to_parameter(
    parameter: ET.Element,
    cc_number: int,
    channel: int = 16
) -> bool:
    """
    Apply MIDI CC mapping to a parameter element.

    Args:
        parameter: Parameter element (e.g., Voice_Transpose)
        cc_number: MIDI CC number
        channel: MIDI channel

    Returns:
        True if mapping was added, False if already existed
    """
    # Check if KeyMidi already exists
    existing_keymidi = parameter.find('./KeyMidi')

    if existing_keymidi is not None:
        # Update existing mapping
        cc_elem = existing_keymidi.find('./NoteOrController')
        if cc_elem is not None:
            old_cc = cc_elem.get('Value')
            cc_elem.set('Value', str(cc_number))

            channel_elem = existing_keymidi.find('./Channel')
            if channel_elem is not None:
                channel_elem.set('Value', str(channel))

            return old_cc != str(cc_number)
    else:
        # Create new KeyMidi element
        keymidi = create_keymidi_element(cc_number, channel)

        # Insert KeyMidi before Manual element (proper Ableton ordering)
        manual_elem = parameter.find('./Manual')
        if manual_elem is not None:
            # Find index of Manual element
            children = list(parameter)
            manual_index = children.index(manual_elem)
            parameter.insert(manual_index, keymidi)
        else:
            # No Manual element, add at beginning
            parameter.insert(0, keymidi)

        return True


def process_drum_rack(
    input_path: Path,
    output_path: Path,
    mappings: List[CCMapping],
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Apply CC mappings to all DrumCell devices in a drum rack.

    Args:
        input_path: Input .adg file
        output_path: Output .adg file
        mappings: List of CCMapping objects to apply
        dry_run: If True, don't write output file

    Returns:
        Statistics dictionary
    """
    print(f"\n{'='*80}")
    print(f"PROCESSING DRUM RACK")
    print(f"{'='*80}\n")

    print(f"Input:  {input_path.name}")
    print(f"Output: {output_path.name}")

    if dry_run:
        print("Mode:   DRY RUN (no files will be modified)")

    # Decode rack
    xml = decode_adg(input_path)
    root = ET.fromstring(xml)

    # Find all DrumCell devices
    drumcells = root.findall('.//DrumCell')

    print(f"\nFound {len(drumcells)} DrumCell devices")

    if not drumcells:
        print("\n⚠️  No DrumCell devices found in rack")
        return {'drumcells': 0, 'mappings_added': 0, 'mappings_updated': 0}

    stats = {
        'drumcells': len(drumcells),
        'mappings_added': 0,
        'mappings_updated': 0,
        'mappings_skipped': 0,
    }

    print(f"\nApplying {len(mappings)} CC mappings per DrumCell...")

    # Process each DrumCell
    for i, drumcell in enumerate(drumcells, 1):
        # Get pad info for better logging
        pad_name = None
        user_name = drumcell.find('.//UserName')
        if user_name is not None:
            pad_name = user_name.get('Value', '')

        if not pad_name:
            # Try to get sample name
            file_ref = drumcell.find('.//FileRef/Name')
            if file_ref is not None:
                pad_name = file_ref.get('Value', '')

        pad_label = f"DrumCell {i}" if not pad_name else f"DrumCell {i} ({pad_name})"

        if dry_run:
            print(f"\n[{i}/{len(drumcells)}] {pad_label}")

        # Apply each mapping
        for mapping in mappings:
            parameter = drumcell.find(mapping.parameter_path)

            if parameter is not None:
                was_added = apply_cc_mapping_to_parameter(
                    parameter,
                    mapping.cc_number,
                    mapping.channel
                )

                if was_added:
                    stats['mappings_added'] += 1
                    if dry_run:
                        print(f"  ✓ Would add: {mapping.description} → CC#{mapping.cc_number}")
                else:
                    stats['mappings_updated'] += 1
                    if dry_run:
                        print(f"  ↻ Would update: {mapping.description} → CC#{mapping.cc_number}")
            else:
                stats['mappings_skipped'] += 1
                if dry_run:
                    print(f"  ⊘ Skip (not found): {mapping.description}")

    if not dry_run:
        # Convert back to XML string
        xml_output = ET.tostring(root, encoding='unicode', xml_declaration=True)

        # Encode to .adg
        print(f"\nWriting output: {output_path.name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(xml_output, output_path)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Apply MIDI CC mappings to DrumCell devices in a drum rack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use built-in default mappings
    python3 apply_drumcell_cc_mappings.py input.adg output.adg

    # Extract mappings from template
    python3 apply_drumcell_cc_mappings.py input.adg output.adg \\
        --template /Users/Music/Desktop/mapped.adg

    # Dry run to preview changes
    python3 apply_drumcell_cc_mappings.py input.adg output.adg --dry-run

    # Custom MIDI channel
    python3 apply_drumcell_cc_mappings.py input.adg output.adg --channel 1

Default CC Mappings (Channel 16):
    CC#3  - Voice_Transpose (Pitch)
    CC#7  - Volume
    CC#10 - Pan
    CC#12 - Voice_VelocityToVolume
    CC#14 - Voice_ModulationTarget
    CC#15 - Voice_PlaybackStart (Sample Start)
    CC#16 - Voice_PlaybackLength
    CC#17 - Voice_Decay
    CC#18 - Voice_SamplePitch
        """
    )

    parser.add_argument(
        'input',
        type=Path,
        help='Input drum rack (.adg file)'
    )
    parser.add_argument(
        'output',
        type=Path,
        help='Output drum rack (.adg file)'
    )
    parser.add_argument(
        '--template',
        type=Path,
        help='Template .adg file to extract mappings from (optional)'
    )
    parser.add_argument(
        '--channel',
        type=int,
        default=16,
        help='MIDI channel for mappings (1-16, default: 16)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without modifying files'
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.input.exists():
        print(f"✗ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.template and not args.template.exists():
        print(f"✗ Error: Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    if args.channel < 1 or args.channel > 16:
        print(f"✗ Error: Channel must be 1-16, got {args.channel}", file=sys.stderr)
        sys.exit(1)

    try:
        # Extract mappings from template or use defaults
        if args.template:
            mappings = extract_mappings_from_template(args.template)
        else:
            print("Using default CC mappings")
            mappings = DEFAULT_MAPPINGS

        # Override channel if specified
        if args.channel != 16:
            print(f"Overriding channel to: {args.channel}")
            for mapping in mappings:
                mapping.channel = args.channel

        # Process drum rack
        stats = process_drum_rack(
            args.input,
            args.output,
            mappings,
            args.dry_run
        )

        # Print summary
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}\n")

        print(f"DrumCell devices:    {stats['drumcells']}")
        print(f"Mappings added:      {stats['mappings_added']}")
        print(f"Mappings updated:    {stats['mappings_updated']}")
        print(f"Mappings skipped:    {stats['mappings_skipped']}")
        print(f"Total operations:    {stats['mappings_added'] + stats['mappings_updated']}")

        if args.dry_run:
            print("\n⚠️  DRY RUN - No files were modified")
        else:
            print(f"\n✓ SUCCESS - Output written to: {args.output}")

        print(f"\n{'='*80}\n")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
