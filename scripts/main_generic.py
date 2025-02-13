#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List, Tuple
from decoder import decode_adg
from encoder import encode_adg
from transformer import transform_xml

def get_all_samples(folder_path: Path) -> List[str]:
    """Get all wav samples from the folder"""
    samples = []
    
    try:
        # Get all .wav files and sort alphabetically
        wav_files = sorted(folder_path.glob('*.wav'))
        samples.extend(str(f) for f in wav_files)
    except Exception as e:
        print(f"Warning: Error scanning directory: {e}")
    
    return samples

def organize_samples(folder_path: Path, batch_index: int) -> Tuple[List[str], str, bool]:
    """
    Organize samples into batches of 32 for the drum rack
    Returns (samples_list, rack_name, has_more_samples)
    """
    # Get folder name for rack naming
    folder_name = folder_path.name
    parent_name = folder_path.parent.name
    
    # Combine parent and folder name if they're different
    if parent_name.lower() not in folder_name.lower():
        rack_prefix = f"{parent_name} {folder_name}"
    else:
        rack_prefix = folder_name
    
    # Get all samples
    all_samples = get_all_samples(folder_path)
    
    # Calculate how many complete racks we can make
    samples_per_rack = 32
    max_complete_racks = len(all_samples) // samples_per_rack
    remaining_samples = len(all_samples) % samples_per_rack
    
    # If we're beyond the number of complete racks and there are no remaining samples, stop
    if batch_index >= max_complete_racks and remaining_samples == 0:
        return [], "", False
    
    # Get the current batch of samples
    start_idx = batch_index * samples_per_rack
    end_idx = start_idx + samples_per_rack
    current_samples = all_samples[start_idx:end_idx]
    
    # Pad with None if we don't have enough samples
    while len(current_samples) < samples_per_rack:
        current_samples.append(None)
    
    # Generate rack name
    rack_name = f"{rack_prefix} {batch_index + 1:02d}"
    
    # Print summary
    print(f"\nBatch {batch_index + 1} sample count: {len([s for s in current_samples if s])}")
    print(f"Total samples available: {len(all_samples)}")
    print(f"Complete racks possible: {max_complete_racks}")
    if remaining_samples:
        print(f"Remaining samples: {remaining_samples}")
    
    # Check if we have more samples for another rack
    has_more = (batch_index + 1) * samples_per_rack < len(all_samples)
    
    return current_samples, rack_name, has_more

def main():
    parser = argparse.ArgumentParser(description='Create drum racks from any sample folder')
    parser.add_argument('input_file', type=str, help='Input template .adg file path')
    parser.add_argument('samples_folder', type=str, help='Path to folder containing samples')
    parser.add_argument('--output-folder', type=str, help='Optional: Output folder for .adg files', default=None)
    
    try:
        args = parser.parse_args()
        input_path = Path(args.input_file)
        samples_path = Path(args.samples_folder)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        if not samples_path.exists():
            raise FileNotFoundError(f"Samples folder not found: {samples_path}")
        
        # If no output folder specified, create one based on the folder name
        if args.output_folder:
            output_folder = Path(args.output_folder)
        else:
            # Use parent and folder name for output folder
            folder_name = samples_path.name
            parent_name = samples_path.parent.name
            if parent_name.lower() not in folder_name.lower():
                output_name = f"{parent_name} {folder_name} Racks"
            else:
                output_name = f"{folder_name} Racks"
            output_folder = input_path.parent / output_name
        
        # Create output folder if it doesn't exist
        output_folder.mkdir(parents=True, exist_ok=True)
        print(f"Creating drum racks in: {output_folder}")
        
        batch_index = 0
        while True:
            try:
                # Get organized samples for this batch
                samples, rack_name, has_more = organize_samples(samples_path, batch_index)
                
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
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 