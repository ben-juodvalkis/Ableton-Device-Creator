#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import sys
import xml.etree.ElementTree as ET
import re

# Add the python directory to the Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg

def note_name_to_midi(note_name: str) -> int:
    """Convert note name (e.g., 'C1', 'A#2') to MIDI note number."""
    # Handle sharp notes
    if '#' in note_name:
        note_part = note_name[:-2]  # e.g., 'A#'
        octave = int(note_name[-1])
    else:
        note_part = note_name[:-1]  # e.g., 'C'
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
    """Extract note name from Auto Sampled filename format: KitName-Note-V127-ID.aif"""
    # Pattern: anything-NOTE-V127-ID.aif where NOTE is like C1, A#2, etc.
    pattern = r'^[^-]+-([A-G]#?\d+)-V127-[A-Z0-9]+\.(aif|wav)$'
    match = re.match(pattern, filename)
    if match:
        return match.group(1)  # Return the note part
    return None

def get_samples_by_note(kit_folder: Path) -> Dict[str, str]:
    """Get all samples from a kit folder, organized by note name."""
    samples_by_note = {}
    
    # Look for .aif and .wav files
    for ext in ['*.aif', '*.wav']:
        for sample_file in kit_folder.glob(ext):
            note_name = parse_sample_filename(sample_file.name)
            if note_name:
                samples_by_note[note_name] = str(sample_file)
    
    return samples_by_note

def create_drum_rack_samples(samples_by_note: Dict[str, str]) -> List[Optional[str]]:
    """Create ordered list of exactly 32 samples for drum rack pads C1 to G3."""
    samples = [None] * 32  # Exactly 32 pads in drum rack
    
    # Generate all note names from C1 to G3 (32 chromatic notes)
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    pad_index = 0
    for octave in range(1, 4):  # Octaves 1, 2, 3
        for note in notes:
            if pad_index >= 32:  # Stop at 32 pads
                break
                
            note_name = f"{note}{octave}"
            if note_name in samples_by_note:
                samples[pad_index] = samples_by_note[note_name]
            
            pad_index += 1
            
            # Special case: G3 is the 32nd pad (last one)
            if note_name == "G3":
                break
        
        if pad_index >= 32:
            break
    
    return samples

def transform_drum_rack_xml(xml_content: str, samples: List[Optional[str]]) -> str:
    """Transform the drum rack XML by only updating file references, preserving everything else."""
    try:
        root = ET.fromstring(xml_content)
        
        # Find all FileRef elements that are inside SampleRef elements (these are the actual sample references)
        sample_file_refs = root.findall(".//SampleRef/FileRef")
        
        print(f"Found {len(sample_file_refs)} sample FileRef elements to update")
        
        # Update only the sample file references
        sample_index = 0
        for file_ref in sample_file_refs:
            if sample_index < len(samples):
                sample_path = samples[sample_index]
                if sample_path:
                    path_elem = file_ref.find("Path")
                    rel_path_elem = file_ref.find("RelativePath")
                    
                    if path_elem is not None:
                        # Update the absolute path
                        path_elem.set("Value", sample_path)
                        print(f"  Updated sample {sample_index}: {Path(sample_path).name}")
                    
                    if rel_path_elem is not None:
                        # Update the relative path  
                        rel_path = "../../" + '/'.join(sample_path.split('/')[-3:])
                        rel_path_elem.set("Value", rel_path)
                    
                sample_index += 1
        
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    except Exception as e:
        raise Exception(f"Error transforming drum rack XML: {e}")

def create_drum_branch(sample_path: str, midi_note: int) -> ET.Element:
    """Create a drum branch XML element for a drum rack."""
    branch = ET.Element("DrumBranch")
    
    # Set the MIDI note (key)
    branch.set("Key", str(midi_note))
    
    # Name (using filename without extension)
    name = ET.SubElement(branch, "Name")
    name.set("Value", Path(sample_path).stem)
    
    # IsActive
    is_active = ET.SubElement(branch, "IsActive")
    is_active.set("Value", "true")
    
    # Create a simple Simpler device to hold the sample
    device_chain = ET.SubElement(branch, "DeviceChain")
    
    # Device chain properties
    ET.SubElement(device_chain, "LomId").set("Value", "0")
    ET.SubElement(device_chain, "LomIdView").set("Value", "0")
    ET.SubElement(device_chain, "IsExpanded").set("Value", "true")
    
    # Create devices list with Simpler
    devices = ET.SubElement(device_chain, "Devices")
    simpler = ET.SubElement(devices, "Simpler")
    simpler.set("Id", "0")
    
    # Simpler properties
    ET.SubElement(simpler, "LomId").set("Value", "0")
    ET.SubElement(simpler, "LomIdView").set("Value", "0")
    ET.SubElement(simpler, "IsExpanded").set("Value", "true")
    
    # On/Off
    on_elem = ET.SubElement(simpler, "On")
    ET.SubElement(on_elem, "LomId").set("Value", "0")
    ET.SubElement(on_elem, "Manual").set("Value", "true")
    
    # Sample reference
    sample_ref = ET.SubElement(simpler, "SampleRef")
    file_ref = ET.SubElement(sample_ref, "FileRef")
    ET.SubElement(file_ref, "Path").set("Value", sample_path)
    
    # Create relative path
    rel_path = "../../" + '/'.join(sample_path.split('/')[-3:])
    ET.SubElement(file_ref, "RelativePath").set("Value", rel_path)
    
    return branch

def create_sample_part(index: int, sample_path: str, key_min: int, key_max: int) -> ET.Element:
    """Create a sample part XML element."""
    part = ET.Element("MultiSamplePart")
    part.set("Id", str(index))
    part.set("HasImportedSlicePoints", "false")
    
    # Name
    name = ET.SubElement(part, "Name")
    name.set("Value", Path(sample_path).stem)
    
    # Key range
    key_range = ET.SubElement(part, "KeyRange")
    ET.SubElement(key_range, "Min").set("Value", str(key_min))
    ET.SubElement(key_range, "Max").set("Value", str(key_max))
    ET.SubElement(key_range, "CrossfadeMin").set("Value", str(key_min))
    ET.SubElement(key_range, "CrossfadeMax").set("Value", str(key_max))
    
    # RootKey
    ET.SubElement(part, "RootKey").set("Value", str(key_min))
    
    # Set sample reference
    sample_ref = ET.SubElement(part, "SampleRef")
    file_ref = ET.SubElement(sample_ref, "FileRef")
    ET.SubElement(file_ref, "Path").set("Value", sample_path)
    
    # Create relative path (adjust as needed for your setup)
    rel_path = "../../" + '/'.join(sample_path.split('/')[-3:])
    ET.SubElement(file_ref, "RelativePath").set("Value", rel_path)
    
    return part

def main():
    parser = argparse.ArgumentParser(description='Create drum racks from Auto Sampled kit folders')
    parser.add_argument('template_file', type=str, help='Input template .adg file path')
    parser.add_argument('auto_sampled_folder', type=str, help='Path to Auto Sampled folder')
    parser.add_argument('--output-folder', type=str, help='Optional: Output folder for .adg files', default=None)
    parser.add_argument('--exclude', type=str, nargs='*', default=['Abbey Road Vintage Dixieland'], 
                       help='Folders to exclude from processing')
    
    try:
        args = parser.parse_args()
        template_path = Path(args.template_file)
        auto_sampled_path = Path(args.auto_sampled_folder)
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        if not auto_sampled_path.exists():
            raise FileNotFoundError(f"Auto Sampled folder not found: {auto_sampled_path}")
        
        # Set up output folder
        if args.output_folder:
            output_folder = Path(args.output_folder)
        else:
            output_folder = auto_sampled_path.parent / "Auto Sampled Drum Racks"
        
        output_folder.mkdir(parents=True, exist_ok=True)
        print(f"Creating drum racks in: {output_folder}")
        
        # Process each kit folder
        processed = 0
        failed = 0
        
        for kit_folder in auto_sampled_path.iterdir():
            if not kit_folder.is_dir():
                continue
            
            # Skip excluded folders
            if kit_folder.name in args.exclude:
                print(f"Skipping excluded folder: {kit_folder.name}")
                continue
            
            try:
                print(f"Processing kit: {kit_folder.name}")
                
                # Get samples organized by note
                samples_by_note = get_samples_by_note(kit_folder)
                if not samples_by_note:
                    print(f"  No valid samples found in {kit_folder.name}")
                    failed += 1
                    continue
                
                # Create ordered sample list for 32 drum pads (C1-G3)
                ordered_samples = create_drum_rack_samples(samples_by_note)
                sample_count = sum(1 for s in ordered_samples if s is not None)
                print(f"  Found {sample_count} samples for 32 drum pads (C1-G3)")
                
                if sample_count == 0:
                    print(f"  No samples in C1-G3 range for {kit_folder.name}")
                    failed += 1
                    continue
                
                # Create output file
                safe_name = "".join(c for c in kit_folder.name if c.isalnum() or c in " -_")
                output_path = output_folder / f"{safe_name}.adg"
                
                # Transform template
                xml_content = decode_adg(template_path)
                transformed_xml = transform_drum_rack_xml(xml_content, ordered_samples)
                encode_adg(transformed_xml, output_path)
                
                print(f"  ✓ Created: {output_path}")
                processed += 1
                
            except Exception as e:
                print(f"  ✗ Error processing {kit_folder.name}: {e}")
                failed += 1
        
        print(f"\nProcessing complete:")
        print(f"  Processed: {processed} kits")
        print(f"  Failed: {failed} kits")
        print(f"  Output folder: {output_folder}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())