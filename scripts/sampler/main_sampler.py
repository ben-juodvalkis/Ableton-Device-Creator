#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List, Tuple
import xml.etree.ElementTree as ET
import sys
import os

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.decoder import decode_adg
from utils.encoder import encode_adg

import wave

def is_valid_audio_file(file_path: str) -> bool:
    """Check if file is a valid audio file"""
    try:
        # Check for WAV files
        if file_path.lower().endswith('.wav'):
            with wave.open(file_path, 'rb') as wave_file:
                return True
        # Check for AIFF/AIF files
        elif file_path.lower().endswith(('.aif', '.aiff')):
            # For AIFF we'll just check if file exists since Python's built-in
            # libraries don't have great AIFF support
            return Path(file_path).exists()
        return False
    except Exception:
        return False

def get_all_samples(folder_path: Path) -> List[str]:
    """Get all valid audio samples from the folder"""
    samples = []
    skipped = []
    
    try:
        # Get all WAV and AIFF files
        audio_files = []
        audio_files.extend(folder_path.glob('*.wav'))
        audio_files.extend(folder_path.glob('*.aif'))
        audio_files.extend(folder_path.glob('*.aiff'))
        
        # Sort and validate
        for file_path in sorted(audio_files):
            if is_valid_audio_file(str(file_path)):
                samples.append(str(file_path))
            else:
                skipped.append(file_path.name)
        
        if skipped:
            print(f"Warning: Skipped {len(skipped)} invalid files:")
            for file in skipped[:5]:  # Show first 5 skipped files
                print(f"- {file}")
            if len(skipped) > 5:
                print(f"... and {len(skipped) - 5} more")
            
    except Exception as e:
        print(f"Warning: Error scanning directory: {e}")
    
    return samples

def get_sample_batch(samples: List[str], batch_index: int, batch_size: int = 32, previous_samples: List[str] = None) -> List[str]:
    """Get a batch of samples starting from batch_index * batch_size"""
    start_idx = batch_index * batch_size
    end_idx = start_idx + batch_size
    current_batch = samples[start_idx:end_idx]
    
    # If we have less than batch_size samples and previous samples exist,
    # fill remaining slots with samples from previous batch
    if len(current_batch) < batch_size and previous_samples:
        remaining = batch_size - len(current_batch)
        current_batch.extend(previous_samples[:remaining])
    
    return current_batch

def transform_sampler_xml(xml_content: str, samples: List[str]) -> str:
    """Transform the XML content by setting up sample zones"""
    try:
        root = ET.fromstring(xml_content)
        
        # Find the MultiSampleMap element
        sample_map = root.find(".//MultiSampleMap")
        if sample_map is None:
            raise ValueError("Could not find MultiSampleMap element")
            
        # Clear existing sample parts
        sample_parts = sample_map.find("SampleParts")
        if sample_parts is not None:
            sample_map.remove(sample_parts)
            
        # Create new SampleParts element
        new_parts = ET.SubElement(sample_map, "SampleParts")
        
        # Starting at C2 (MIDI note 48)
        base_note = 48
        
        # Add each sample as a zone
        for i, sample_path in enumerate(samples):
            if not sample_path:
                continue
                
            # Create sample part element
            part = create_sample_part(i, sample_path, base_note + i)
            new_parts.append(part)
            
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
        
    except Exception as e:
        raise Exception(f"Error transforming sampler XML: {e}")

def create_sample_part(index: int, sample_path: str, note: int) -> ET.Element:
    """Create a sample part element for the given sample"""
    part = ET.Element("MultiSamplePart")
    part.set("Id", str(index))
    part.set("HasImportedSlicePoints", "false")
    
    # Set key range to single note with matching crossfade values
    key_range = ET.SubElement(part, "KeyRange")
    ET.SubElement(key_range, "Min").set("Value", str(note))
    ET.SubElement(key_range, "Max").set("Value", str(note))
    ET.SubElement(key_range, "CrossfadeMin").set("Value", str(note))
    ET.SubElement(key_range, "CrossfadeMax").set("Value", str(note))
    
    # Set velocity range
    vel_range = ET.SubElement(part, "VelocityRange")
    ET.SubElement(vel_range, "Min").set("Value", "1")
    ET.SubElement(vel_range, "Max").set("Value", "127")
    ET.SubElement(vel_range, "CrossfadeMin").set("Value", "1")
    ET.SubElement(vel_range, "CrossfadeMax").set("Value", "127")
    
    # Set selector range
    selector_range = ET.SubElement(part, "SelectorRange")
    ET.SubElement(selector_range, "Min").set("Value", "0")
    ET.SubElement(selector_range, "Max").set("Value", "127")
    ET.SubElement(selector_range, "CrossfadeMin").set("Value", "0")
    ET.SubElement(selector_range, "CrossfadeMax").set("Value", "127")
    
    # Set root key to match zone
    ET.SubElement(part, "RootKey").set("Value", str(note))
    
    # Set sample reference
    sample_ref = ET.SubElement(part, "SampleRef")
    file_ref = ET.SubElement(sample_ref, "FileRef")
    
    # Set paths
    ET.SubElement(file_ref, "Path").set("Value", sample_path)
    rel_path = "../../" + '/'.join(sample_path.split('/')[-3:])
    ET.SubElement(file_ref, "RelativePath").set("Value", rel_path)
    
    return part

def main():
    parser = argparse.ArgumentParser(description='Create sampler racks from sample folder')
    parser.add_argument('input_file', type=str, help='Input template .adg file path')
    parser.add_argument('samples_folder', type=str, help='Path to folder containing samples')
    parser.add_argument('--output-folder', type=str, help='Optional: Output folder for .adg files')
    
    try:
        args = parser.parse_args()
        input_path = Path(args.input_file)
        samples_path = Path(args.samples_folder)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        if not samples_path.exists():
            raise FileNotFoundError(f"Samples folder not found: {samples_path}")
            
        # Create output-sampler directory in script location
        output_base = Path('output-sampler')
        output_base.mkdir(exist_ok=True)
        
        # Create subfolder structure matching input path
        rel_path = samples_path.relative_to('/Users/Shared/Music/Samples Organized')
        output_folder = output_base / rel_path
        output_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"Creating sampler racks in: {output_folder}")
        
        # Get all samples
        all_samples = get_all_samples(samples_path)
        if not all_samples:
            print("No valid samples found!")
            return
            
        # Calculate how many complete sets we can make
        samples_per_rack = 32
        num_complete_sets = len(all_samples) // samples_per_rack
        remaining_samples = len(all_samples) % samples_per_rack
        
        print(f"Found {len(all_samples)} samples")
        print(f"Will create {num_complete_sets} full racks", end="")
        if remaining_samples:
            print(f" plus 1 partial rack with {remaining_samples} samples")
        else:
            print()
        
        # Process each batch
        batch_index = 0
        previous_samples = None
        while batch_index * samples_per_rack < len(all_samples):
            # Get current batch of samples
            current_samples = get_sample_batch(
                all_samples, 
                batch_index, 
                samples_per_rack,
                previous_samples
            )
            
            # Create output path
            safe_name = "".join(c for c in samples_path.name if c.isalnum() or c in " -_")
            if num_complete_sets > 0:
                output_path = output_folder / f"{safe_name} {batch_index + 1:02d}.adg"
            else:
                output_path = output_folder / f"{safe_name}.adg"
            
            # Process the rack
            xml_content = decode_adg(input_path)
            transformed_xml = transform_sampler_xml(xml_content, current_samples)
            encode_adg(transformed_xml, output_path)
            
            print(f"Successfully created {output_path}")
            
            # Store current samples for next iteration
            previous_samples = current_samples
            batch_index += 1
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 