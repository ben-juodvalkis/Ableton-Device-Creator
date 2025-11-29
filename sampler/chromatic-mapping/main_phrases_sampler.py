#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List, Tuple
import sys
import xml.etree.ElementTree as ET

# Add the python directory to the Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg

def get_descriptive_name(filename: str) -> str:
    parts = filename.split(' ', 1)
    if len(parts) > 1:
        return parts[1].lower()
    return filename.lower()

def get_all_samples(folder_path: Path) -> List[str]:
    samples = []
    try:
        wav_files = sorted(folder_path.glob('*.wav'))
        samples = [str(f) for f in wav_files]
        samples.sort(key=lambda x: get_descriptive_name(Path(x).stem))
    except Exception as e:
        print(f"Warning: Error scanning directory {folder_path}: {e}")
    return samples

def get_sample_batch(samples: List[str], batch_index: int, batch_size: int = 32) -> List[str]:
    start_idx = batch_index * batch_size
    end_idx = start_idx + batch_size
    return samples[start_idx:end_idx]

def transform_sampler_xml(xml_content: str, samples: List[str]) -> str:
    try:
        root = ET.fromstring(xml_content)
        sample_map = root.find(".//MultiSampleMap")
        if sample_map is None:
            raise ValueError("Could not find MultiSampleMap element")
        sample_parts = sample_map.find("SampleParts")
        if sample_parts is not None:
            sample_map.remove(sample_parts)
        new_parts = ET.SubElement(sample_map, "SampleParts")
        # Map to MIDI notes 48-79 (C3-G#4)
        for i, sample_path in enumerate(samples):
            if not sample_path:
                continue
            key = 48 + i
            part = create_sample_part(i, sample_path, key, key)
            new_parts.append(part)
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    except Exception as e:
        raise Exception(f"Error transforming sampler XML: {e}")

def create_sample_part(index: int, sample_path: str, key_min: int, key_max: int) -> ET.Element:
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
    rel_path = "../../" + '/'.join(sample_path.split('/')[-3:])
    ET.SubElement(file_ref, "RelativePath").set("Value", rel_path)
    return part

def main():
    parser = argparse.ArgumentParser(description='Create Sampler devices for each subfolder (Phrases) in a parent folder')
    parser.add_argument('input_file', type=str, help='Input template .adg file path')
    parser.add_argument('parent_folder', type=str, help='Path to parent folder containing subfolders of samples')
    parser.add_argument('--output-folder', type=str, help='Optional: Output folder for .adg files', default=None)
    try:
        args = parser.parse_args()
        input_path = Path(args.input_file)
        parent_path = Path(args.parent_folder)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        if not parent_path.exists():
            raise FileNotFoundError(f"Parent folder not found: {parent_path}")
        if args.output_folder:
            output_root = Path(args.output_folder)
        else:
            output_root = input_path.parent / f"Phrases Samplers"
        output_root.mkdir(parents=True, exist_ok=True)
        for subfolder in sorted([f for f in parent_path.iterdir() if f.is_dir()]):
            samples = get_all_samples(subfolder)
            if not samples:
                print(f"No samples found in {subfolder}, skipping.")
                continue
            print(f"Processing {subfolder.name} ({len(samples)} samples)")
            batch_index = 0
            while True:
                batch_samples = get_sample_batch(samples, batch_index)
                if not any(batch_samples):
                    break
                # Pad to 32
                while len(batch_samples) < 32:
                    batch_samples.append(None)
                # Name: subfolder + batch number if needed
                if len(samples) > 32:
                    rack_name = f"{subfolder.name} {batch_index+1:02d}"
                else:
                    rack_name = subfolder.name
                safe_name = "".join(c for c in rack_name if c.isalnum() or c in " -_")
                output_path = output_root / f"{safe_name}.adg"
                xml_content = decode_adg(input_path)
                transformed_xml = transform_sampler_xml(xml_content, batch_samples)
                encode_adg(transformed_xml, output_path)
                print(f"Successfully created {output_path}")
                if len(samples) <= 32 or (batch_index+1)*32 >= len(samples):
                    break
                batch_index += 1
        print(f"\nCreated Sampler devices for all subfolders in {parent_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 