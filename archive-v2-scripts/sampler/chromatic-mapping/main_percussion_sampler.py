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

def get_all_samples_from_folders(base_path: Path, folders: List[str], exclude_patterns: List[str] = None) -> List[str]:
    samples = []
    for folder in folders:
        folder_path = base_path / folder
        if not folder_path.exists():
            continue
        wav_files = [f for f in folder_path.glob('*.wav')]
        if exclude_patterns:
            for pattern in exclude_patterns:
                wav_files = [f for f in wav_files if pattern not in f.name]
        samples.extend(str(f) for f in wav_files)
    samples.sort(key=lambda x: get_descriptive_name(Path(x).stem))
    return samples

def get_sample_batch(samples: List[str], batch_index: int, batch_size: int = 32) -> List[str]:
    start_idx = batch_index * batch_size
    end_idx = start_idx + batch_size
    return samples[start_idx:end_idx]

def get_library_name(donor_path: Path) -> str:
    try:
        library_name = donor_path.name
        library_name = library_name.replace(" Library", "").replace(" Collection", "").strip()
        return library_name
    except Exception:
        return "Percussion"

def organize_percussion_samples(donor_path: Path, batch_index: int) -> Tuple[List[str], str, bool]:
    drums_path = donor_path / 'Samples' / 'Drums'
    library_name = get_library_name(donor_path)
    excluded_folders = {'Kick', 'Snare', 'Clap', 'Hihat', 'Shaker', 'Cymbal'}
    percussion_folders = []
    try:
        for folder in drums_path.iterdir():
            if folder.is_dir() and folder.name not in excluded_folders:
                percussion_folders.append(folder.name)
    except Exception as e:
        print(f"Warning: Error scanning drums directory: {e}")
    if not percussion_folders:
        percussion_folders = ['Percussion', 'Tom']
    percussion_samples = get_all_samples_from_folders(drums_path, percussion_folders)
    max_complete_sets = len(percussion_samples) // 32
    if batch_index >= max_complete_sets:
        return [], "", False
    batch_samples = get_sample_batch(percussion_samples, batch_index)
    while len(batch_samples) < 32:
        batch_samples.append(None)
    # Descriptor from first sample
    descriptor = ""
    if batch_samples and batch_samples[0]:
        first = Path(batch_samples[0]).stem
        parts = first.split(' ', 1)
        if len(parts) > 1:
            descriptor = parts[1]
    if descriptor:
        rack_name = f"{library_name} {descriptor}"
    else:
        rack_name = library_name
    has_more = batch_index + 1 < max_complete_sets
    return batch_samples[:32], rack_name, has_more

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
    parser = argparse.ArgumentParser(description='Create percussion-only sampler racks from sample library')
    parser.add_argument('input_file', type=str, help='Input template .adg file path')
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
        if args.output_folder:
            output_folder = Path(args.output_folder)
        else:
            library_name = get_library_name(donor_path)
            output_folder = input_path.parent / f"{library_name} Perc Samplers"
        output_folder.mkdir(parents=True, exist_ok=True)
        print(f"Creating percussion-only samplers in: {output_folder}")
        batch_index = 0
        while True:
            try:
                samples, rack_name, has_more = organize_percussion_samples(donor_path, batch_index)
                if not samples:
                    break
                safe_name = "".join(c for c in rack_name if c.isalnum() or c in " -_")
                output_path = output_folder / f"{safe_name}.adg"
                xml_content = decode_adg(input_path)
                transformed_xml = transform_sampler_xml(xml_content, samples)
                encode_adg(transformed_xml, output_path)
                print(f"Successfully created {output_path}")
                if not has_more:
                    break
                batch_index += 1
            except Exception as e:
                print(f"Error processing batch {batch_index + 1}: {e}")
                break
        print(f"\nCreated {batch_index + 1} percussion-only samplers in {output_folder}")
    except Exception as e:
        print(f"Error processing arguments: {e}")

if __name__ == "__main__":
    main() 