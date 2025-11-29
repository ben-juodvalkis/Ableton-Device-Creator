#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List
import wave
import os
import sys

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg
from utils.simpler_transformer import transform_simpler_xml, get_simpler_info

def is_valid_audio_file(file_path: str) -> bool:
    """Check if file is a valid audio file"""
    try:
        if file_path.lower().endswith('.wav'):
            with wave.open(file_path, 'rb') as wave_file:
                return True
        elif file_path.lower().endswith(('.aif', '.aiff')):
            # For AIF/AIFF files, just check if they exist
            return os.path.exists(file_path)
        return False
    except Exception:
        return False

def get_all_samples(samples_path: Path) -> List[str]:
    """Get all valid audio samples from the folder"""
    samples = []
    
    try:
        # Get all audio files and sort alphabetically
        audio_files = []
        for ext in ['.wav', '.aif', '.aiff']:
            audio_files.extend(samples_path.glob(f'*{ext}'))
            audio_files.extend(samples_path.glob(f'*{ext.upper()}'))
        
        # Sort files alphabetically
        audio_files.sort()
        
        # Filter valid audio files
        samples = [str(f) for f in audio_files if is_valid_audio_file(str(f))]
        
    except Exception as e:
        print(f"Warning: Error scanning samples directory: {e}")
    
    return samples

def main():
    parser = argparse.ArgumentParser(description='Create Simpler devices from sample folder')
    parser.add_argument('input_file', type=str, help='Input template .adv file path')
    parser.add_argument('samples_folder', type=str, help='Path to folder containing samples')
    parser.add_argument('--output-folder', type=str, help='Optional: Output folder for .adv files')
    
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
            output_folder = input_path.parent / f"{samples_path.name} Simplers"
            
        output_folder.mkdir(parents=True, exist_ok=True)
        print(f"Creating Simpler devices in: {output_folder}")
        
        # Get all samples
        samples = get_all_samples(samples_path)
        if not samples:
            print("No valid samples found!")
            return
            
        print(f"Found {len(samples)} samples")
        
        # Process each sample
        for i, sample_path in enumerate(samples):
            try:
                # Create output path for this Simpler - use safe filename
                sample_name = Path(sample_path).stem
                safe_name = "".join(c for c in sample_name if c.isalnum() or c in " -_")
                output_path = output_folder / f"{safe_name}.adv"
                
                # Decode the ADV file to XML
                xml_content = decode_adg(input_path)
                
                # Transform the XML with the new sample path
                transformed_xml = transform_simpler_xml(xml_content, sample_path)
                
                # Encode back to ADV
                encode_adg(transformed_xml, output_path)
                
                print(f"Successfully created {output_path}")
                
            except Exception as e:
                print(f"Error processing sample {sample_path}: {e}")
                continue
        
        print(f"\nCreated {len(samples)} Simpler devices in {output_folder}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 