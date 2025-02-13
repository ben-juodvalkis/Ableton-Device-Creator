# main.py
import argparse
from pathlib import Path
from typing import List, Dict
import re
from decoder import decode_adg
from encoder import encode_adg
from transformer import transform_xml

def get_descriptive_name(filename: str) -> str:
    """Extract descriptive part of filename after category word"""
    # Split on first space to separate category from description
    parts = filename.split(' ', 1)
    if len(parts) > 1:
        return parts[1].lower()  # Return description part in lowercase
    return filename.lower()

def get_samples_from_folders(base_path: Path, folders: List[str], count: int, exclude_patterns: List[str] = None) -> List[str]:
    """Get specified number of samples from given folders"""
    samples = []
    for folder in folders:
        folder_path = base_path / folder
        if not folder_path.exists():
            continue
            
        # Get all .wav files
        wav_files = [f for f in folder_path.glob('*.wav')]
        
        # Filter out excluded patterns if any
        if exclude_patterns:
            for pattern in exclude_patterns:
                wav_files = [f for f in wav_files if pattern not in f.name]
                
        # Add to samples list with full paths
        samples.extend(str(f) for f in wav_files)
    
    # Sort by descriptive name
    samples.sort(key=lambda x: get_descriptive_name(Path(x).stem))
    
    # Return requested number of samples
    return samples[:count]

def organize_drum_samples(donor_path: Path) -> List[str]:
    """Organize samples into 4 groups of 8 for the drum rack"""
    drums_path = donor_path / 'Samples' / 'Drums'
    
    # Get remaining percussion samples (first 8 pads)
    excluded_folders = {'Kick', 'Snare', 'Clap', 'Hihat', 'Shaker', 'Cymbal'}
    remaining_folders = []
    
    try:
        for folder in drums_path.iterdir():
            if folder.is_dir() and folder.name not in excluded_folders:
                remaining_folders.append(folder.name)
    except Exception as e:
        print(f"Warning: Error scanning drums directory: {e}")
    
    if not remaining_folders:
        remaining_folders = ['Percussion', 'Tom']  # Fallback to default folders
        
    print(f"Using folders for first set: {', '.join(remaining_folders)}")
    remaining_samples = get_samples_from_folders(drums_path, remaining_folders, 8)
    
    # Get hihat and shaker samples (next 8 pads)
    hihat_shaker_samples = get_samples_from_folders(
        drums_path, 
        ['Hihat', 'Shaker'], 
        8,
        exclude_patterns=['OpenHH']
    )
    
    # Get snare and clap samples (next 8 pads)
    snare_clap_samples = get_samples_from_folders(drums_path, ['Snare', 'Clap'], 8)
    
    # Get kick samples (last 8 pads)
    kick_samples = get_samples_from_folders(drums_path, ['Kick'], 8)
    
    # Combine all samples in order
    all_samples = remaining_samples + hihat_shaker_samples + snare_clap_samples + kick_samples
    
    # Print summary of what we found
    print(f"\nSample distribution:")
    print(f"Remaining percussion: {len(remaining_samples)}")
    print(f"Hihats/Shakers: {len(hihat_shaker_samples)}")
    print(f"Snares/Claps: {len(snare_clap_samples)}")
    print(f"Kicks: {len(kick_samples)}")
    
    # Ensure we have exactly 32 samples (pad with None if necessary)
    while len(all_samples) < 32:
        all_samples.append(None)
    
    return all_samples[:32]

def main():
    parser = argparse.ArgumentParser(description='Process Ableton device group files')
    parser.add_argument('input_file', type=str, help='Input .adg file path')
    parser.add_argument('output_file', type=str, help='Output .adg file path')
    parser.add_argument('donor_folder', type=str, help='Path to donor samples folder')
    
    args = parser.parse_args()
    input_path = Path(args.input_file)
    output_path = Path(args.output_file)
    donor_path = Path(args.donor_folder)
    
    try:
        # Get organized samples
        samples = organize_drum_samples(donor_path)
        
        # Step 1: Decode the ADG file to XML
        xml_content = decode_adg(input_path)
        
        # Step 2: Transform the XML with our organized samples
        transformed_xml = transform_xml(xml_content, samples)
        
        # Step 3: Encode back to ADG
        encode_adg(transformed_xml, output_path)
        
        print(f"Successfully processed {input_path} to {output_path}")
        print(f"Replaced samples with selections from {donor_path}")
        
    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    main()