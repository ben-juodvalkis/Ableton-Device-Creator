#!/usr/bin/env python3
"""
Create Multi-Velocity Drum Rack from Two Auto Sampled Folders

Combines two 16-pad sample sets into a single 32-pad drum rack:
- Folder 1: Pads 1-16 (MIDI notes 92-77)
- Folder 2: Pads 17-32 (MIDI notes 76-61)

Usage:
    python3 create_dual_folder_drum_rack.py folder1 folder2 output.adg
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


def drum_pad_to_midi(pad_number: int) -> int:
    """Convert drum pad number to MIDI note (where pad 1 = MIDI 92)."""
    return 93 - pad_number


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


def create_velocity_ranges(velocity_layers: List[Tuple[int, str]]) -> List[Tuple[int, int, str]]:
    """Create velocity ranges for MultiSampler from sorted velocity layers."""
    if not velocity_layers:
        return []
    
    ranges = []
    num_layers = len(velocity_layers)
    
    for i, (velocity, file_path) in enumerate(velocity_layers):
        if i == 0:
            if num_layers == 1:
                vel_min, vel_max = 1, 127
            else:
                next_velocity = velocity_layers[i + 1][0]
                vel_min = 1
                vel_max = (velocity + next_velocity) // 2
        elif i == num_layers - 1:
            prev_velocity = velocity_layers[i - 1][0]
            vel_min = (prev_velocity + velocity) // 2 + 1
            vel_max = 127
        else:
            prev_velocity = velocity_layers[i - 1][0]
            next_velocity = velocity_layers[i + 1][0]
            vel_min = (prev_velocity + velocity) // 2 + 1
            vel_max = (velocity + next_velocity) // 2
        
        ranges.append((vel_min, vel_max, file_path))
    
    return ranges


def update_multisampler_template(
    template_multisampler: ET.Element,
    note_name: str,
    velocity_ranges: List[Tuple[int, int, str]]
) -> ET.Element:
    """
    Update template MultiSampler with new velocity ranges and samples.
    """
    # Deep copy the template
    new_multisampler = ET.fromstring(ET.tostring(template_multisampler))
    
    # Find the MultiSampleMap/SampleParts container
    sample_parts_container = new_multisampler.find('.//MultiSampleMap/SampleParts')
    if sample_parts_container is None:
        raise ValueError("Template MultiSampler missing SampleParts structure")
    
    # Clear existing sample parts
    sample_parts_container.clear()
    
    # Get the root key for this note
    root_key = note_name_to_midi(note_name)
    
    # Create new sample parts based on velocity ranges
    for i, (vel_min, vel_max, file_path) in enumerate(velocity_ranges):
        # Create relative path
        rel_path = "../../" + '/'.join(file_path.split('/')[-3:])
        
        # Create MultiSamplePart element
        part = ET.SubElement(sample_parts_container, 'MultiSamplePart')
        part.set('Id', str(i))
        part.set('InitUpdateAreSlicesFromOnsetsEditableAfterRead', 'false')
        part.set('HasImportedSlicePoints', 'false')
        part.set('NeedsAnalysisData', 'false')
        
        # Add required child elements
        ET.SubElement(part, 'LomId').set('Value', '0')
        ET.SubElement(part, 'Name').set('Value', Path(file_path).stem)
        ET.SubElement(part, 'Selection').set('Value', 'true' if i == 0 else 'false')
        ET.SubElement(part, 'IsActive').set('Value', 'true')
        ET.SubElement(part, 'Solo').set('Value', 'false')
        
        # Key range (full range)
        key_range = ET.SubElement(part, 'KeyRange')
        ET.SubElement(key_range, 'Min').set('Value', '0')
        ET.SubElement(key_range, 'Max').set('Value', '127')
        ET.SubElement(key_range, 'CrossfadeMin').set('Value', '0')
        ET.SubElement(key_range, 'CrossfadeMax').set('Value', '127')
        
        # Velocity range (specific to this layer)
        vel_range = ET.SubElement(part, 'VelocityRange')
        ET.SubElement(vel_range, 'Min').set('Value', str(vel_min))
        ET.SubElement(vel_range, 'Max').set('Value', str(vel_max))
        ET.SubElement(vel_range, 'CrossfadeMin').set('Value', str(vel_min))
        ET.SubElement(vel_range, 'CrossfadeMax').set('Value', str(vel_max))
        
        # Selector range
        sel_range = ET.SubElement(part, 'SelectorRange')
        ET.SubElement(sel_range, 'Min').set('Value', '0')
        ET.SubElement(sel_range, 'Max').set('Value', '127')
        ET.SubElement(sel_range, 'CrossfadeMin').set('Value', '0')
        ET.SubElement(sel_range, 'CrossfadeMax').set('Value', '127')
        
        # Root key and other parameters
        ET.SubElement(part, 'RootKey').set('Value', str(root_key))
        ET.SubElement(part, 'Detune').set('Value', '0')
        ET.SubElement(part, 'TuneScale').set('Value', '0')
        ET.SubElement(part, 'Panorama').set('Value', '0')
        ET.SubElement(part, 'Volume').set('Value', '1')
        ET.SubElement(part, 'Link').set('Value', 'false')
        ET.SubElement(part, 'SampleStart').set('Value', '0')
        ET.SubElement(part, 'SampleEnd').set('Value', '0')  # Let Ableton auto-detect
        
        # Sustain loop
        sustain_loop = ET.SubElement(part, 'SustainLoop')
        ET.SubElement(sustain_loop, 'Start').set('Value', '0')
        ET.SubElement(sustain_loop, 'End').set('Value', '0')
        ET.SubElement(sustain_loop, 'Mode').set('Value', '0')
        ET.SubElement(sustain_loop, 'Crossfade').set('Value', '0')
        ET.SubElement(sustain_loop, 'Detune').set('Value', '0')
        
        # Release loop
        release_loop = ET.SubElement(part, 'ReleaseLoop')
        ET.SubElement(release_loop, 'Start').set('Value', '0')
        ET.SubElement(release_loop, 'End').set('Value', '0')
        ET.SubElement(release_loop, 'Mode').set('Value', '3')
        ET.SubElement(release_loop, 'Crossfade').set('Value', '0')
        ET.SubElement(release_loop, 'Detune').set('Value', '0')
        
        # Sample reference
        sample_ref = ET.SubElement(part, 'SampleRef')
        file_ref = ET.SubElement(sample_ref, 'FileRef')
        ET.SubElement(file_ref, 'RelativePathType').set('Value', '3')
        ET.SubElement(file_ref, 'RelativePath').set('Value', rel_path)
        ET.SubElement(file_ref, 'Path').set('Value', file_path)
        ET.SubElement(file_ref, 'Type').set('Value', '1')
        ET.SubElement(file_ref, 'LivePackName').set('Value', '')
        ET.SubElement(file_ref, 'LivePackId').set('Value', '')
        ET.SubElement(file_ref, 'OriginalFileSize').set('Value', '0')
        ET.SubElement(file_ref, 'OriginalCrc').set('Value', '0')
        ET.SubElement(file_ref, 'SourceHint').set('Value', '')
        
        # Additional required elements for Ableton compatibility
        ET.SubElement(part, 'SliceCount').set('Value', '1')
        
        # Modulation connections (empty)
        mod_connections = ET.SubElement(part, 'ModulationConnections')
        mod_connections.set('Id', '0')
        
        # Sample settings
        sample_parts = ET.SubElement(part, 'SampleParts')
        sample_parts.set('Id', '0')
    
    return new_multisampler


def create_dual_folder_drum_rack(
    folder1: Path,
    folder2: Path,
    output_path: Path,
    template_path: Optional[Path] = None
) -> Path:
    """Create a dual-folder drum rack with 32 pads."""
    
    # Use default template if not provided
    if template_path is None:
        template_path = Path(__file__).parent.parent.parent / 'templates/Drum Racks/16-Pad MultiVelocity Template.adg'
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    if not folder1.exists():
        raise FileNotFoundError(f"Folder 1 not found: {folder1}")
    
    if not folder2.exists():
        raise FileNotFoundError(f"Folder 2 not found: {folder2}")
    
    print(f"\n{'='*70}")
    print(f"CREATING DUAL-FOLDER DRUM RACK (32 Pads)")
    print(f"{'='*70}\n")
    print(f"Template: {template_path.name}")
    print(f"Folder 1 (Pads 1-16): {folder1.name}")
    print(f"Folder 2 (Pads 17-32): {folder2.name}")
    
    # Load template
    template_xml = decode_adg(template_path)
    template_root = ET.fromstring(template_xml)
    
    # Extract template MultiSampler and DrumBranchPreset
    template_multisampler = template_root.find('.//MultiSampler')
    if template_multisampler is None:
        raise ValueError("Template missing MultiSampler device")
    
    template_branch = template_root.find('.//DrumBranchPreset')
    if template_branch is None:
        raise ValueError("Template missing DrumBranchPreset structure")
    
    # Organize samples from both folders
    samples_folder1 = organize_samples_by_note(folder1, "Folder 1")
    samples_folder2 = organize_samples_by_note(folder2, "Folder 2")
    
    if not samples_folder1 and not samples_folder2:
        raise ValueError(f"No valid Auto Sampled files found in either folder")
    
    # Find the BranchPresets container in template
    branch_presets_container = template_root.find('.//BranchPresets')
    if branch_presets_container is None:
        raise ValueError("Template missing BranchPresets structure")
    
    # Clear existing branches
    branch_presets_container.clear()
    
    # Create drum branches
    total_velocity_layers = 0
    total_pads = 0
    
    print(f"\nCreating drum pads:")
    
    # Process Folder 1 (Pads 1-16)
    if samples_folder1:
        sorted_notes_1 = sorted(samples_folder1.keys(), key=note_name_to_midi)[:16]  # Limit to 16
        
        for i, note_name in enumerate(sorted_notes_1):
            velocity_layers = samples_folder1[note_name]
            
            if not velocity_layers:
                continue
            
            # Calculate drum pad MIDI note (Pads 1-16)
            pad_number = i + 1
            pad_midi_note = drum_pad_to_midi(pad_number)
            sending_note = 60  # Always send MIDI 60 (C4) to the sampler
            
            # Create velocity ranges
            velocity_ranges = create_velocity_ranges(velocity_layers)
            total_velocity_layers += len(velocity_ranges)
            
            # Update MultiSampler template with new samples
            updated_multisampler = update_multisampler_template(
                template_multisampler, note_name, velocity_ranges
            )
            
            # Create DrumBranchPreset using template structure
            branch_xml_str = ET.tostring(template_branch, encoding='unicode')
            new_branch = ET.fromstring(branch_xml_str)  # Deep copy
            
            # Update branch properties
            new_branch.set('Id', '0')
            new_branch.find('Name').set('Value', f"F1-{note_name}")
            
            # Replace the MultiSampler in the branch
            device_container = new_branch.find('.//Device')
            old_multisampler = device_container.find('MultiSampler')
            if old_multisampler is not None:
                device_container.remove(old_multisampler)
            device_container.append(updated_multisampler)
            
            # Update zone settings
            zone_settings = new_branch.find('ZoneSettings')
            zone_settings.find('ReceivingNote').set('Value', str(pad_midi_note))
            zone_settings.find('SendingNote').set('Value', str(sending_note))
            
            # Add to BranchPresets
            branch_presets_container.append(new_branch)
            
            # Log creation
            ranges_str = ', '.join([f"V{vmin}-{vmax}" for vmin, vmax, _ in velocity_ranges])
            print(f"  Pad {pad_number:2d} (F1-{note_name}): {len(velocity_layers)} layers ({ranges_str})")
            total_pads += 1
    
    # Process Folder 2 (Pads 17-32)
    if samples_folder2:
        sorted_notes_2 = sorted(samples_folder2.keys(), key=note_name_to_midi)[:16]  # Limit to 16
        
        for i, note_name in enumerate(sorted_notes_2):
            velocity_layers = samples_folder2[note_name]
            
            if not velocity_layers:
                continue
            
            # Calculate drum pad MIDI note (Pads 17-32)
            pad_number = i + 17
            pad_midi_note = drum_pad_to_midi(pad_number)
            sending_note = 60  # Always send MIDI 60 (C4) to the sampler
            
            # Create velocity ranges
            velocity_ranges = create_velocity_ranges(velocity_layers)
            total_velocity_layers += len(velocity_ranges)
            
            # Update MultiSampler template with new samples
            updated_multisampler = update_multisampler_template(
                template_multisampler, note_name, velocity_ranges
            )
            
            # Create DrumBranchPreset using template structure
            branch_xml_str = ET.tostring(template_branch, encoding='unicode')
            new_branch = ET.fromstring(branch_xml_str)  # Deep copy
            
            # Update branch properties
            new_branch.set('Id', '0')
            new_branch.find('Name').set('Value', f"F2-{note_name}")
            
            # Replace the MultiSampler in the branch
            device_container = new_branch.find('.//Device')
            old_multisampler = device_container.find('MultiSampler')
            if old_multisampler is not None:
                device_container.remove(old_multisampler)
            device_container.append(updated_multisampler)
            
            # Update zone settings
            zone_settings = new_branch.find('ZoneSettings')
            zone_settings.find('ReceivingNote').set('Value', str(pad_midi_note))
            zone_settings.find('SendingNote').set('Value', str(sending_note))
            
            # Add to BranchPresets
            branch_presets_container.append(new_branch)
            
            # Log creation
            ranges_str = ', '.join([f"V{vmin}-{vmax}" for vmin, vmax, _ in velocity_ranges])
            print(f"  Pad {pad_number:2d} (F2-{note_name}): {len(velocity_layers)} layers ({ranges_str})")
            total_pads += 1
    
    # Convert back to XML string
    result_xml = ET.tostring(template_root, encoding='unicode', xml_declaration=True)
    
    # Encode to .adg
    print(f"\nWriting dual-folder drum rack: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(result_xml, output_path)
    
    print(f"\n{'='*70}")
    print(f"✓ DUAL-FOLDER CREATION COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {output_path}")
    print(f"Total drum pads: {total_pads}")
    print(f"Total velocity layers: {total_velocity_layers}")
    print(f"Folder 1 notes: {len(samples_folder1)} ({', '.join(sorted(samples_folder1.keys(), key=note_name_to_midi)[:16])})")
    print(f"Folder 2 notes: {len(samples_folder2)} ({', '.join(sorted(samples_folder2.keys(), key=note_name_to_midi)[:16])})")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Create dual-folder drum rack with 32 pads from two Auto Sampled folders')
    
    parser.add_argument('folder1', type=Path, help='Path to first sample folder (pads 1-16)')
    parser.add_argument('folder2', type=Path, help='Path to second sample folder (pads 17-32)')
    parser.add_argument('output', type=Path, help='Output drum rack path (.adg file)')
    parser.add_argument('--template', type=Path, default=None, help='Optional template drum rack')
    
    args = parser.parse_args()
    
    try:
        create_dual_folder_drum_rack(args.folder1, args.folder2, args.output, args.template)
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()