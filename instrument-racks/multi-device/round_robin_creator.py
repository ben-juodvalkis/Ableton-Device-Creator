#!/usr/bin/env python3
"""
Round Robin Sampler Creator
Creates new Ableton devices from Mini Template.adg with custom sample folders.
Adapts the number of sample zones based on available samples.
"""
import argparse
from pathlib import Path
from typing import List
import wave
import sys
import xml.etree.ElementTree as ET

# Add utils to path
sys.path.append(str(Path(__file__).parent))
from utils.decoder import decode_adg
from utils.encoder import encode_adg

def is_valid_audio_file(file_path: Path) -> bool:
    """Check if file is a valid audio file"""
    try:
        if file_path.suffix.lower() in ['.wav', '.aif', '.aiff']:
            if file_path.suffix.lower() == '.wav':
                with wave.open(str(file_path), 'rb') as wave_file:
                    return True
            return True  # Assume AIF/AIFF are valid
        return False
    except Exception:
        return False

def get_samples_from_folder(folder_path: Path) -> List[str]:
    """Get all valid audio samples from folder, sorted by name"""
    samples = []
    skipped = []
    
    # Supported audio formats
    audio_extensions = ['.wav', '.aif', '.aiff']
    
    for ext in audio_extensions:
        for file_path in sorted(folder_path.glob(f'*{ext}')):
            if is_valid_audio_file(file_path):
                samples.append(str(file_path.absolute()))
            else:
                skipped.append(file_path.name)
        
        # Also check uppercase
        for file_path in sorted(folder_path.glob(f'*{ext.upper()}')):
            if is_valid_audio_file(file_path):
                samples.append(str(file_path.absolute()))
            else:
                skipped.append(file_path.name)
    
    if skipped:
        print(f"Warning: Skipped {len(skipped)} invalid files: {', '.join(skipped[:5])}")
        if len(skipped) > 5:
            print(f"  ... and {len(skipped) - 5} more")
    
    return samples

def create_round_robin_xml(xml_content: str, sample_paths: List[str], folder_name: str) -> str:
    """
    Transform XML by replacing sample paths and adjusting sample count.
    Adapts the MultiSampleMap to match the number of available samples.
    """
    try:
        root = ET.fromstring(xml_content)
        
        # Find the MultiSampleMap
        sample_map = root.find(".//MultiSampleMap")
        if sample_map is None:
            raise ValueError("Could not find MultiSampleMap in template")
        
        # Remove existing sample parts
        existing_parts = sample_map.find("SampleParts")
        if existing_parts is not None:
            sample_map.remove(existing_parts)
        
        # Create new SampleParts element
        new_parts = ET.SubElement(sample_map, "SampleParts")
        
        print(f"Creating round robin with {len(sample_paths)} samples...")
        
        # Add each sample as a MultiSamplePart
        for i, sample_path in enumerate(sample_paths):
            part = create_sample_part(i, sample_path, folder_name)
            new_parts.append(part)
        
        # Update device name if there's a name field
        name_elements = root.findall(".//Name")
        for name_elem in name_elements:
            current_name = name_elem.get("Value", "")
            if current_name == "Mini Template":
                name_elem.set("Value", f"{folder_name} Round Robin")
        
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
        
    except Exception as e:
        raise Exception(f"Error transforming XML: {e}")

def create_sample_part(index: int, sample_path: str, folder_name: str) -> ET.Element:
    """Create a MultiSamplePart element for round robin sampling"""
    
    # Extract sample name from path
    sample_name = Path(sample_path).stem
    
    part = ET.Element("MultiSamplePart")
    part.set("Id", str(index))
    part.set("InitUpdateAreSlicesFromOnsetsEditableAfterRead", "false")
    part.set("HasImportedSlicePoints", "false")
    part.set("NeedsAnalysisData", "false")
    
    # Basic properties
    ET.SubElement(part, "LomId").set("Value", "0")
    ET.SubElement(part, "Name").set("Value", sample_name)
    ET.SubElement(part, "Selection").set("Value", "false")
    ET.SubElement(part, "IsActive").set("Value", "true")
    ET.SubElement(part, "Solo").set("Value", "false")
    
    # Key range - all samples cover full range for round robin
    key_range = ET.SubElement(part, "KeyRange")
    ET.SubElement(key_range, "Min").set("Value", "0")
    ET.SubElement(key_range, "Max").set("Value", "127")
    
    # Velocity range - full velocity
    vel_range = ET.SubElement(part, "VelocityRange")
    ET.SubElement(vel_range, "Min").set("Value", "1")
    ET.SubElement(vel_range, "Max").set("Value", "127")
    
    # Sample reference
    sample_ref = ET.SubElement(part, "SampleRef")
    file_ref = ET.SubElement(sample_ref, "FileRef")
    
    # File paths
    ET.SubElement(file_ref, "Path").set("Value", sample_path)
    
    # Create relative path (Ableton style)
    path_parts = sample_path.replace('\\', '/').split('/')
    if len(path_parts) >= 3:
        rel_path = "../../" + '/'.join(path_parts[-3:])
    else:
        rel_path = "../../" + '/'.join(path_parts)
    ET.SubElement(file_ref, "RelativePath").set("Value", rel_path)
    
    # Sample properties (matching template structure)
    ET.SubElement(part, "SampleStart").set("Value", "0")
    ET.SubElement(part, "SampleEnd").set("Value", "0")
    ET.SubElement(part, "LoopStart").set("Value", "0")
    ET.SubElement(part, "LoopEnd").set("Value", "0")
    ET.SubElement(part, "LoopOn").set("Value", "false")
    ET.SubElement(part, "LoopFade").set("Value", "0")
    ET.SubElement(part, "Reverse").set("Value", "false")
    ET.SubElement(part, "Gain").set("Value", "1")
    ET.SubElement(part, "Transpose").set("Value", "0")
    ET.SubElement(part, "Detune").set("Value", "0")
    ET.SubElement(part, "TuneMode").set("Value", "0")
    
    # Zone settings
    zone_settings = ET.SubElement(part, "ZoneSettings")
    ET.SubElement(zone_settings, "CrossfadeRange").set("Value", "0")
    
    # Slice settings (empty for round robin)
    ET.SubElement(part, "BeatSlicePoints")
    ET.SubElement(part, "RegionSlicePoints")
    ET.SubElement(part, "UseDynamicBeatSlices").set("Value", "true")
    ET.SubElement(part, "UseDynamicRegionSlices").set("Value", "true")
    ET.SubElement(part, "AreSlicesFromOnsetsEditable").set("Value", "false")
    
    return part

def main():
    parser = argparse.ArgumentParser(
        description='Create round robin sampler devices from Mini Template.adg',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create single device from sample folder (uses repo template)
  python3 round_robin_creator.py "/path/to/samples"
  
  # Use custom template
  python3 round_robin_creator.py "/path/to/samples" --template "/path/to/Mini Template.adg"
  
  # Specify custom output location
  python3 round_robin_creator.py "/path/to/samples" --output "/path/to/output.adg"
  
  # Process with custom device name
  python3 round_robin_creator.py "/path/to/samples" --name "My Custom Kit"
        '''
    )
    
    parser.add_argument('samples_folder', type=str, help='Path to folder containing audio samples')
    parser.add_argument('--template', '-t', type=str, help='Path to Mini Template.adg file (default: uses repo template)')
    parser.add_argument('--output', '-o', type=str, help='Output path for new .adg file')
    parser.add_argument('--name', '-n', type=str, help='Custom name for the device')
    
    try:
        args = parser.parse_args()
        
        # Use repo template by default
        if args.template:
            template_path = Path(args.template)
        else:
            # Use template from repo
            script_dir = Path(__file__).parent
            template_path = script_dir.parent / "templates" / "Mini Template.adg"
        
        samples_path = Path(args.samples_folder)
        
        # Validate inputs
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        if not samples_path.exists() or not samples_path.is_dir():
            raise FileNotFoundError(f"Samples folder not found: {samples_path}")
        
        # Get folder name for device naming
        folder_name = args.name or samples_path.name
        safe_folder_name = "".join(c for c in folder_name if c.isalnum() or c in " -_")
        
        # Setup output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = samples_path.parent / f"{safe_folder_name} Round Robin.adg"
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Template: {template_path.name}")
        print(f"Samples folder: {samples_path}")
        print(f"Output: {output_path}")
        print()
        
        # Get samples from folder
        samples = get_samples_from_folder(samples_path)
        if not samples:
            print("Error: No valid audio samples found in folder!")
            return 1
        
        print(f"Found {len(samples)} valid samples")
        
        # Process the template
        print("Processing template...")
        xml_content = decode_adg(template_path)
        transformed_xml = create_round_robin_xml(xml_content, samples, safe_folder_name)
        encode_adg(transformed_xml, output_path)
        
        print(f"\n✓ Successfully created: {output_path}")
        print(f"  Round robin with {len(samples)} samples")
        print(f"  Device name: {safe_folder_name} Round Robin")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())