#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List, Tuple
import wave
import os
import sys
import xml.etree.ElementTree as ET
from utils.decoder import decode_adg
from utils.encoder import encode_adg

def is_valid_audio_file(file_path: str) -> bool:
    """Check if file is a valid audio file"""
    try:
        if file_path.lower().endswith('.wav'):
            with wave.open(file_path, 'rb') as wave_file:
                return True
        return False
    except Exception:
        return False

def get_all_samples(folder_path: Path) -> List[str]:
    """Get all valid audio samples from the folder"""
    samples = []
    skipped = []
    
    try:
        wav_files = sorted(folder_path.glob('*.wav'))
        for file_path in wav_files:
            if is_valid_audio_file(str(file_path)):
                samples.append(str(file_path))
            else:
                skipped.append(file_path.name)
        
        if skipped:
            print(f"Warning: Skipped {len(skipped)} invalid files")
            
    except Exception as e:
        print(f"Warning: Error scanning directory: {e}")
    
    return samples

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
        
        # Add each sample as a zone
        for i, sample_path in enumerate(samples):
            if not sample_path:
                continue
                
            # Calculate key range for this zone
            key_min = (127 // len(samples)) * i
            key_max = (127 // len(samples)) * (i + 1) - 1
            if i == len(samples) - 1:
                key_max = 127  # Ensure last zone reaches top
                
            # Create sample part element
            part = create_sample_part(i, sample_path, key_min, key_max)
            new_parts.append(part)
            
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
        
    except Exception as e:
        raise Exception(f"Error transforming sampler XML: {e}")

def create_sample_part(index: int, sample_path: str, key_min: int, key_max: int) -> ET.Element:
    """Create a sample part element for the given sample"""
    part = ET.Element("MultiSamplePart")
    part.set("Id", str(index))
    part.set("HasImportedSlicePoints", "false")
    
    # Set key range
    key_range = ET.SubElement(part, "KeyRange")
    ET.SubElement(key_range, "Min").set("Value", str(key_min))
    ET.SubElement(key_range, "Max").set("Value", str(key_max))
    
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
            
        # Setup output folder
        if args.output_folder:
            output_folder = Path(args.output_folder)
        else:
            output_folder = input_path.parent / f"{samples_path.name} Samplers"
            
        output_folder.mkdir(parents=True, exist_ok=True)
        print(f"Creating sampler racks in: {output_folder}")
        
        # Get all samples
        samples = get_all_samples(samples_path)
        if not samples:
            print("No valid samples found!")
            return
            
        print(f"Found {len(samples)} samples")
        
        # Create output path
        safe_name = "".join(c for c in samples_path.name if c.isalnum() or c in " -_")
        output_path = output_folder / f"{safe_name} Sampler.adg"
        
        # Process the rack
        xml_content = decode_adg(input_path)
        transformed_xml = transform_sampler_xml(xml_content, samples)
        encode_adg(transformed_xml, output_path)
        
        print(f"Successfully created {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 