# main.py
import argparse
from pathlib import Path
from typing import List, Dict
import re
import sys

# Add the python directory to the Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg
from utils.transformer import transform_xml

def get_descriptive_name(filename: str) -> str:
    """Extract descriptive part of filename after category word"""
    # Split on first space to separate category from description
    parts = filename.split(' ', 1)
    if len(parts) > 1:
        return parts[1].lower()  # Return description part in lowercase
    return filename.lower()

def get_all_samples_from_folders(base_path: Path, folders: List[str], exclude_patterns: List[str] = None) -> List[str]:
    """Get all samples from given folders"""
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
    
    return samples

def get_sample_batch(samples: List[str], batch_index: int, batch_size: int = 8) -> List[str]:
    """Get a batch of samples starting from batch_index * batch_size"""
    start_idx = batch_index * batch_size
    end_idx = start_idx + batch_size
    return samples[start_idx:end_idx]

def get_library_name(donor_path: Path) -> str:
    """Extract the library name from the donor path"""
    # For path like "/Users/Shared/Music/Soundbanks/Native Instruments/Expansions/Amplified Funk Library"
    # Return "Amplified Funk"
    try:
        # Get the parent folder name (e.g. "Amplified Funk Library")
        library_name = donor_path.name
        # Remove common suffixes
        library_name = library_name.replace(" Library", "").replace(" Collection", "").strip()
        return library_name
    except Exception:
        return "Drum Rack"  # Fallback name

def organize_drum_samples(donor_path: Path, batch_index: int) -> tuple[List[str], str, bool]:
    """
    Organize samples into 4 groups of 8 for the drum rack
    Returns (samples_list, rack_name, has_more_samples)
    """
    drums_path = donor_path / 'Samples' / 'Drums'
    
    # Get library name
    library_name = get_library_name(donor_path)
    
    # Get all samples for each category
    excluded_folders = {'Kick', 'Snare', 'Clap', 'Hihat', 'Shaker', 'Cymbal'}
    remaining_folders = []
    
    try:
        for folder in drums_path.iterdir():
            if folder.is_dir() and folder.name not in excluded_folders:
                remaining_folders.append(folder.name)
    except Exception as e:
        print(f"Warning: Error scanning drums directory: {e}")
    
    if not remaining_folders:
        remaining_folders = ['Percussion', 'Tom']
    
    # Get all samples for each category
    remaining_all = get_all_samples_from_folders(drums_path, remaining_folders)
    hihat_shaker_all = get_all_samples_from_folders(drums_path, ['Hihat', 'Shaker'], ['OpenHH'])
    snare_clap_all = get_all_samples_from_folders(drums_path, ['Snare', 'Clap'])
    kick_all = get_all_samples_from_folders(drums_path, ['Kick'])
    
    # Calculate how many complete sets we can make
    min_samples = min(
        len(remaining_all),
        len(hihat_shaker_all),
        len(snare_clap_all),
        len(kick_all)
    )
    max_complete_sets = min_samples // 8
    
    # If we're beyond the number of complete sets, stop
    if batch_index >= max_complete_sets:
        return [], "", False
    
    # Get the current batch for each category
    remaining_samples = get_sample_batch(remaining_all, batch_index)
    hihat_shaker_samples = get_sample_batch(hihat_shaker_all, batch_index)
    snare_clap_samples = get_sample_batch(snare_clap_all, batch_index)
    kick_samples = get_sample_batch(kick_all, batch_index)
    
    # Get the descriptive name from the first kick sample (if available)
    kick_descriptor = ""
    if kick_samples:
        first_kick = Path(kick_samples[0]).stem
        parts = first_kick.split(' ', 1)
        if len(parts) > 1:
            kick_descriptor = parts[1]
    
    # Combine all samples in order
    all_samples = remaining_samples + hihat_shaker_samples + snare_clap_samples + kick_samples
    
    # Print summary of what we found
    print(f"\nBatch {batch_index + 1} sample distribution:")
    print(f"Remaining percussion: {len(remaining_samples)}")
    print(f"Hihats/Shakers: {len(hihat_shaker_samples)}")
    print(f"Snares/Claps: {len(snare_clap_samples)}")
    print(f"Kicks: {len(kick_samples)}")
    
    # Print total samples available in each category
    print(f"\nTotal samples available:")
    print(f"Remaining percussion: {len(remaining_all)}")
    print(f"Hihats/Shakers: {len(hihat_shaker_all)}")
    print(f"Snares/Claps: {len(snare_clap_all)}")
    print(f"Kicks: {len(kick_all)}")
    print(f"Complete sets possible: {max_complete_sets}")
    
    # Ensure we have exactly 32 samples (pad with None if necessary)
    while len(all_samples) < 32:
        all_samples.append(None)
    
    # Check if we have more complete sets available
    has_more = batch_index + 1 < max_complete_sets
    
    # Generate rack name
    rack_name = f"{library_name} {batch_index + 1:02d}"
    if kick_descriptor:
        rack_name += f" {kick_descriptor}"
    
    return all_samples[:32], rack_name, has_more

def main():
    parser = argparse.ArgumentParser(description='Process Ableton device group files')
    parser.add_argument('input_file', type=str, help='Input .adg file path')
    parser.add_argument('donor_folder', type=str, help='Path to donor samples folder')
    parser.add_argument('--output-folder', type=str, help='Optional: Output folder for .adg files', default=None)
    
    try:
        args = parser.parse_args()
        input_path = Path(args.input_file)
        donor_path = Path(args.donor_folder)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        if not donor_path.exists():
            raise FileNotFoundError(f"Donor folder not found: {donor_path}")
        
        # If no output folder specified, create one based on the library name
        if args.output_folder:
            output_folder = Path(args.output_folder)
        else:
            library_name = get_library_name(donor_path)
            # Create output folder next to the input file
            output_folder = input_path.parent / f"{library_name} Drum Racks"
        
        # Create output folder if it doesn't exist
        output_folder.mkdir(parents=True, exist_ok=True)
        print(f"Creating drum racks in: {output_folder}")
        
        batch_index = 0
        while True:
            try:
                # Get organized samples for this batch
                samples, rack_name, has_more = organize_drum_samples(donor_path, batch_index)
                
                if not samples:
                    break
                    
                # Create output path for this rack - use safe filename
                safe_name = "".join(c for c in rack_name if c.isalnum() or c in " -_")
                output_path = output_folder / f"{safe_name}.adg"
                
                # Decode the ADG file to XML
                xml_content = decode_adg(input_path)
                
                # Transform the XML with our organized samples
                transformed_xml = transform_xml(xml_content, samples)
                
                # Encode back to ADG
                encode_adg(transformed_xml, output_path)
                
                print(f"Successfully created {output_path}")
                
                if not has_more:
                    break
                    
                batch_index += 1
                
            except Exception as e:
                print(f"Error processing batch {batch_index + 1}: {e}")
                break
        
        print(f"\nCreated {batch_index + 1} drum racks in {output_folder}")
    except Exception as e:
        print(f"Error processing arguments: {e}")

if __name__ == "__main__":
    main()