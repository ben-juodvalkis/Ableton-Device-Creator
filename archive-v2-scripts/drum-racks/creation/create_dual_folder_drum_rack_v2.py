#!/usr/bin/env python3
"""
Create Dual-Folder Drum Rack by Only Changing Sample References

Uses existing 32-Pad MultiVelocity Template and ONLY changes file paths.
No structural changes - preserves all velocity mappings, device settings, etc.

Usage:
    python3 create_dual_folder_drum_rack_v2.py folder1 folder2 output.adg
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


def note_name_to_midi(note_name: str) -> int:
    """Convert note name (e.g., 'C1', 'A#2') to MIDI note number."""
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
    
    if note_part not in note_map:
        raise ValueError(f"Invalid note: {note_part}")
    
    return (octave + 1) * 12 + note_map[note_part]


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


def organize_samples_by_note(sample_folder: Path, folder_name: str) -> Dict[str, List[Tuple[int, str]]]:
    """Organize samples by note name with velocity layers."""
    samples_by_note = defaultdict(list)
    
    print(f"Scanning samples in {folder_name}: {sample_folder}")
    
    for ext in ['*.aif', '*.wav']:
        for sample_file in sample_folder.glob(ext):
            parsed = parse_auto_sampled_filename(sample_file.name)
            if parsed:
                kit_name, note_name, velocity = parsed
                samples_by_note[note_name].append((velocity, str(sample_file)))
    
    # Sort velocity layers for each note
    for note_name in samples_by_note:
        samples_by_note[note_name].sort(key=lambda x: x[0])
    
    print(f"  Found samples for {len(samples_by_note)} notes:")
    for note_name, velocity_layers in samples_by_note.items():
        velocities = [v for v, _ in velocity_layers]
        print(f"    {note_name}: {len(velocity_layers)} layers (V{min(velocities)}-V{max(velocities)})")
    
    return dict(samples_by_note)


def replace_sample_references_only(
    template_root: ET.Element,
    folder1_samples: Dict[str, List[Tuple[int, str]]],
    folder2_samples: Dict[str, List[Tuple[int, str]]]
) -> ET.Element:
    """
    Replace ONLY the sample file references in the template.
    Preserves all other structure, velocity mappings, device settings, etc.
    """
    
    # Get all drum branches (should be 32)
    branches = template_root.findall('.//DrumBranchPreset')
    
    if len(branches) != 32:
        raise ValueError(f"Template should have 32 branches, found {len(branches)}")
    
    # Prepare sample mappings
    # Folder 1: Pads 1-16, Folder 2: Pads 17-32
    folder1_notes = sorted(folder1_samples.keys(), key=note_name_to_midi)[:16]
    folder2_notes = sorted(folder2_samples.keys(), key=note_name_to_midi)[:16]
    
    print(f"\nReplacing sample references:")
    print(f"Folder 1 (Pads 1-16): {len(folder1_notes)} notes")
    print(f"Folder 2 (Pads 17-32): {len(folder2_notes)} notes")
    
    total_replaced = 0
    
    # Process each branch
    for i, branch in enumerate(branches):
        pad_number = i + 1
        
        # Determine which folder and note to use
        if pad_number <= 16 and pad_number <= len(folder1_notes):
            # Folder 1 (Pads 1-16)
            note_name = folder1_notes[pad_number - 1]
            velocity_samples = folder1_samples[note_name]
            folder_prefix = "F1"
        elif pad_number > 16 and (pad_number - 16) <= len(folder2_notes):
            # Folder 2 (Pads 17-32)
            note_name = folder2_notes[pad_number - 17]
            velocity_samples = folder2_samples[note_name]
            folder_prefix = "F2"
        else:
            # No samples available for this pad - skip
            print(f"  Pad {pad_number:2d}: No samples available - keeping template references")
            continue
        
        # Update branch name
        name_element = branch.find('Name')
        if name_element is not None:
            name_element.set('Value', f"{folder_prefix}-{note_name}")
        
        # Find all sample references in this branch
        sample_refs = branch.findall('.//SampleRef/FileRef')
        
        if len(sample_refs) != len(velocity_samples):
            print(f"  Pad {pad_number:2d} ({folder_prefix}-{note_name}): WARNING - Template has {len(sample_refs)} refs, we have {len(velocity_samples)} samples")
        
        # Replace sample file paths
        samples_replaced = 0
        for j, file_ref in enumerate(sample_refs):
            if j < len(velocity_samples):
                velocity, sample_path = velocity_samples[j]
                
                # Update absolute path
                path_element = file_ref.find('Path')
                if path_element is not None:
                    path_element.set('Value', sample_path)
                
                # Update relative path (create one for portability)
                rel_path_element = file_ref.find('RelativePath')
                if rel_path_element is not None:
                    rel_path = "../../" + '/'.join(sample_path.split('/')[-3:])
                    rel_path_element.set('Value', rel_path)
                
                samples_replaced += 1
        
        total_replaced += samples_replaced
        print(f"  Pad {pad_number:2d} ({folder_prefix}-{note_name}): {samples_replaced} sample refs updated")
    
    print(f"\nTotal sample references replaced: {total_replaced}")
    
    return template_root


def create_dual_folder_drum_rack_v2(
    folder1: Path,
    folder2: Path,
    output_path: Path
) -> Path:
    """Create dual-folder drum rack by only changing sample references."""
    
    # Use 32-Pad template
    template_path = Path(__file__).parent.parent.parent / 'templates/Drum Racks/32-Pad MultiVelocity Template.adg'
    
    if not template_path.exists():
        raise FileNotFoundError(f"32-Pad template not found: {template_path}")
    
    if not folder1.exists():
        raise FileNotFoundError(f"Folder 1 not found: {folder1}")
    
    if not folder2.exists():
        raise FileNotFoundError(f"Folder 2 not found: {folder2}")
    
    print(f"\n{'='*70}")
    print(f"CREATING DUAL-FOLDER DRUM RACK (Reference Replacement Only)")
    print(f"{'='*70}\n")
    print(f"Template: {template_path.name}")
    print(f"Folder 1 (Pads 1-16): {folder1.name}")
    print(f"Folder 2 (Pads 17-32): {folder2.name}")
    
    # Load template
    template_xml = decode_adg(template_path)
    template_root = ET.fromstring(template_xml)
    
    # Organize samples from both folders
    folder1_samples = organize_samples_by_note(folder1, "Folder 1")
    folder2_samples = organize_samples_by_note(folder2, "Folder 2")
    
    if not folder1_samples and not folder2_samples:
        raise ValueError(f"No valid Auto Sampled files found in either folder")
    
    # Replace sample references only
    updated_root = replace_sample_references_only(template_root, folder1_samples, folder2_samples)
    
    # Convert back to XML string
    result_xml = ET.tostring(updated_root, encoding='unicode', xml_declaration=True)
    
    # Encode to .adg
    print(f"\nWriting dual-folder drum rack: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(result_xml, output_path)
    
    print(f"\n{'='*70}")
    print(f"✓ REFERENCE REPLACEMENT COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {output_path}")
    print(f"Method: Only sample references changed")
    print(f"Structure: Preserved from 32-Pad template")
    print(f"Folder 1 notes: {len(folder1_samples)} ({', '.join(sorted(folder1_samples.keys(), key=note_name_to_midi)[:16])})")
    print(f"Folder 2 notes: {len(folder2_samples)} ({', '.join(sorted(folder2_samples.keys(), key=note_name_to_midi)[:16])})")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Create dual-folder drum rack by only changing sample references in 32-Pad template')
    
    parser.add_argument('folder1', type=Path, help='Path to first sample folder (pads 1-16)')
    parser.add_argument('folder2', type=Path, help='Path to second sample folder (pads 17-32)')
    parser.add_argument('output', type=Path, help='Output drum rack path (.adg file)')
    
    args = parser.parse_args()
    
    try:
        create_dual_folder_drum_rack_v2(args.folder1, args.folder2, args.output)
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()