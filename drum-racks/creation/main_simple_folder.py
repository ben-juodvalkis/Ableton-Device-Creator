#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import List, Tuple

# Add the parent directory to the Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg
from utils.transformer import transform_xml

def get_all_samples(folder_path: Path) -> List[str]:
    """Get all audio samples from the folder"""
    samples = []

    try:
        # Get all audio files and sort alphabetically
        audio_extensions = ['.wav', '.aif', '.aiff', '.mp3', '.flac']
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(folder_path.glob(f'*{ext}'))

        # Sort and convert to strings
        samples.extend(str(f) for f in sorted(audio_files))
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

    # Get all samples
    all_samples = get_all_samples(folder_path)

    # Calculate how many complete racks we can make
    samples_per_rack = 32
    max_complete_racks = len(all_samples) // samples_per_rack

    # If we're beyond the number of complete racks, check for remaining samples
    if batch_index >= max_complete_racks:
        remaining_samples = len(all_samples) % samples_per_rack
        if remaining_samples == 0 or batch_index > max_complete_racks:
            return [], "", False

    # Get the current batch of samples
    start_idx = batch_index * samples_per_rack
    end_idx = start_idx + samples_per_rack
    current_samples = all_samples[start_idx:end_idx]

    # Pad with None if we don't have enough samples
    while len(current_samples) < samples_per_rack:
        current_samples.append(None)

    # Generate rack name
    if max_complete_racks > 1 or (len(all_samples) % samples_per_rack > 0 and batch_index < max_complete_racks):
        rack_name = f"{folder_name} {batch_index + 1:02d}"
    else:
        rack_name = folder_name

    # Print summary
    print(f"\nBatch {batch_index + 1} sample count: {len([s for s in current_samples if s])}")
    print(f"Total samples available: {len(all_samples)}")
    print(f"Complete racks possible: {max_complete_racks}")
    if len(all_samples) % samples_per_rack:
        print(f"Remaining samples: {len(all_samples) % samples_per_rack}")

    # Check if we have more samples for another rack
    has_more = (batch_index + 1) * samples_per_rack < len(all_samples)

    return current_samples, rack_name, has_more

def main():
    parser = argparse.ArgumentParser(description='Create Ableton drum racks from a simple folder of samples')
    parser.add_argument('input_file', type=str, help='Input .adg template file path')
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
            folder_name = samples_path.name
            output_folder = input_path.parent / f"{folder_name} Racks"

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

        print(f"\nCreated {batch_index + 1} drum rack(s) in {output_folder}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
