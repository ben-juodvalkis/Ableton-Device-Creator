#!/usr/bin/env python3
"""
Create Multi-Velocity Drum Rack by updating sample references in existing template

Takes your working 16-pad template and just updates the sample file paths.
This ensures 100% compatibility since we're using a known-working structure.

Usage:
    python3 create_from_template.py sample_folder output.adg --template your_template.adg
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from collections import defaultdict

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def parse_auto_sampled_filename(filename: str) -> Optional[Tuple[str, str, int]]:
    """Parse Auto Sampled filename format."""
    pattern = r'^(.+?)-([A-G]#?\d+)-V(\d+)-[A-Z0-9]+\.(aif|wav)$'
    match = re.match(pattern, filename)
    
    if match:
        kit_name = match.group(1)
        note_name = match.group(2)
        velocity = int(match.group(3))
        return kit_name, note_name, velocity
    
    return None


def organize_samples_by_note(sample_folder: Path) -> Dict[str, List[Tuple[int, str]]]:
    """Organize samples by note name with velocity layers."""
    samples_by_note = defaultdict(list)
    
    print(f"Scanning samples in: {sample_folder}")
    
    for ext in ['*.aif', '*.wav']:
        for sample_file in sample_folder.glob(ext):
            parsed = parse_auto_sampled_filename(sample_file.name)
            if parsed:
                kit_name, note_name, velocity = parsed
                samples_by_note[note_name].append((velocity, str(sample_file)))
    
    # Sort velocity layers for each note
    for note_name in samples_by_note:
        samples_by_note[note_name].sort(key=lambda x: x[0])
    
    print(f"Found samples for {len(samples_by_note)} notes:")
    for note_name, velocity_layers in samples_by_note.items():
        velocities = [v for v, _ in velocity_layers]
        print(f"  {note_name}: {len(velocity_layers)} layers (V{min(velocities)}-V{max(velocities)})")
    
    return dict(samples_by_note)


def note_name_to_midi(note_name: str) -> int:
    """Convert note name to MIDI note number."""
    if '#' in note_name:
        note_part = note_name[:-1]
        octave = int(note_name[-1])
    else:
        note_part = note_name[:-1]
        octave = int(note_name[-1])
    
    note_map = {
        'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 
        'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11
    }
    
    return (octave + 1) * 12 + note_map[note_part]


def update_template_with_samples(
    template_path: Path,
    sample_folder: Path,
    output_path: Path
) -> Path:
    """
    Update template drum rack with new sample references.
    
    Args:
        template_path: Path to your working 16-pad template
        sample_folder: Path to Auto Sampled folder
        output_path: Path for output drum rack
    
    Returns:
        Path to created drum rack
    """
    
    print(f"\n{'='*70}")
    print(f"UPDATING TEMPLATE WITH NEW SAMPLES")
    print(f"{'='*70}\n")
    print(f"Template: {template_path.name}")
    
    # Load template
    template_xml = decode_adg(template_path)
    template_root = ET.fromstring(template_xml)
    
    # Organize samples by note
    samples_by_note = organize_samples_by_note(sample_folder)
    
    if not samples_by_note:
        raise ValueError(f"No valid Auto Sampled files found in {sample_folder}")
    
    # Get all drum branches from template
    branches = template_root.findall('.//DrumBranchPreset')
    print(f"\nTemplate has {len(branches)} drum pads")
    
    # Sort notes by MIDI note number for consistent assignment
    sorted_notes = sorted(samples_by_note.keys(), key=note_name_to_midi)
    print(f"Will assign notes: {', '.join(sorted_notes[:len(branches)])}")
    
    # Update each branch with samples
    updated_pads = 0
    
    for i, note_name in enumerate(sorted_notes):
        if i >= len(branches):
            print(f"Skipping {note_name} - no more template pads available")
            break
            
        branch = branches[i]
        velocity_layers = samples_by_note[note_name]
        
        if not velocity_layers:
            continue
        
        # Update branch name
        name_elem = branch.find('Name')
        if name_elem is not None:
            name_elem.set('Value', note_name)
        
        # Find all MultiSamplePart elements in this branch
        sample_parts = branch.findall('.//MultiSamplePart')
        
        print(f"  Pad {i+1} ({note_name}): {len(sample_parts)} template slots, {len(velocity_layers)} samples")
        
        # Update sample references in each part
        for j, (velocity, sample_path) in enumerate(velocity_layers):
            if j >= len(sample_parts):
                print(f"    Warning: More samples than template slots for {note_name}")
                break
                
            part = sample_parts[j]
            
            # Update name
            name_elem = part.find('Name')
            if name_elem is not None:
                name_elem.set('Value', Path(sample_path).stem)
            
            # Update file reference
            sample_ref = part.find('.//SampleRef/FileRef/Path')
            if sample_ref is not None:
                sample_ref.set('Value', sample_path)
                
            # Update relative path
            rel_path_elem = part.find('.//SampleRef/FileRef/RelativePath')
            if rel_path_elem is not None:
                rel_path = "../../" + '/'.join(sample_path.split('/')[-3:])
                rel_path_elem.set('Value', rel_path)
            
            print(f"    Layer {j+1}: V{velocity} = {Path(sample_path).name}")
        
        updated_pads += 1
    
    # Convert back to XML and save
    result_xml = ET.tostring(template_root, encoding='unicode', xml_declaration=True)
    
    print(f"\nWriting updated drum rack: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(result_xml, output_path)
    
    print(f"\n{'='*70}")
    print(f"✓ UPDATE COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {output_path}")
    print(f"Updated pads: {updated_pads}")
    print(f"File size: {output_path.stat().st_size:,} bytes")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Update template drum rack with Auto Sampled folder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use default 16-pad MultiVelocity template
    python3 create_from_template.py "/path/to/samples" output.adg
    
    # Use custom template
    python3 create_from_template.py "/path/to/samples" output.adg --template "/path/to/my_template.adg"

This approach:
    - Uses proven working 16-pad template structure
    - Only updates sample file references 
    - Preserves all device settings and parameters
    - Guarantees Ableton compatibility
    - Default template: 16-Pad MultiVelocity Template.adg
        """
    )
    
    parser.add_argument(
        'sample_folder',
        type=Path,
        help='Path to folder containing Auto Sampled files'
    )
    parser.add_argument(
        'output',
        type=Path,
        help='Output drum rack path (.adg file)'
    )
    parser.add_argument(
        '--template',
        type=Path,
        default=None,
        help='Template drum rack to use (defaults to built-in)'
    )
    
    args = parser.parse_args()
    
    # Use provided template or default
    if args.template is None:
        # Use your working 16-pad template as default
        template_path = Path(__file__).parent.parent.parent / 'templates/Drum Racks/16-Pad MultiVelocity Template.adg'
    else:
        template_path = args.template
    
    if not template_path.exists():
        print(f"✗ Template not found: {template_path}")
        sys.exit(1)
    
    try:
        update_template_with_samples(
            template_path,
            args.sample_folder,
            args.output
        )
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()