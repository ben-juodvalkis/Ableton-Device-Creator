#!/usr/bin/env python3
import gzip
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

def extract_als_to_xml(als_path):
    """Extract the gzipped XML content from an ALS file"""
    try:
        with gzip.open(als_path, 'rb') as f_in:
            return f_in.read()
    except Exception as e:
        raise Exception(f"Error extracting ALS file: {e}")

def save_als_from_xml(xml_content, als_path):
    """Save XML content back to a gzipped ALS file"""
    try:
        with gzip.open(als_path, 'wb') as f_out:
            if isinstance(xml_content, str):
                xml_content = xml_content.encode('utf-8')
            f_out.write(xml_content)
    except Exception as e:
        raise Exception(f"Error saving ALS file: {e}")

def get_output_path(input_path):
    """Generate output path with _no_bus suffix"""
    input_path = Path(input_path)
    return input_path.parent / f"{input_path.stem}_no_bus{input_path.suffix}"

def find_group_track_by_name(tracks_elem, group_name):
    """Find a group track by its name"""
    for track in tracks_elem.findall('./'):
        if track.tag == 'GroupTrack':
            track_name = track.find('.//Name/EffectiveName')
            if track_name is not None:
                name = track_name.get('Value', '')
                if name == group_name:
                    return track
    return None

def remove_group_track(xml_content, group_name):
    """Remove a specific group track and its contents"""
    try:
        # Parse XML while preserving formatting
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        root = ET.fromstring(xml_content.decode('utf-8'), parser=parser)
        
        # Find the Tracks element
        tracks_elem = root.find('.//Tracks')
        if tracks_elem is None:
            raise Exception("No tracks found in the Live Set")

        # Find and remove the Bus group track
        bus_track = find_group_track_by_name(tracks_elem, group_name)
        if bus_track is None:
            raise Exception(f"Group track '{group_name}' not found")
        
        # Get track info for reporting
        track_id = bus_track.get('Id', 'unknown')
        print(f"\nRemoving group track {track_id} ({group_name}) and all its contents")
        
        # Remove the group track
        tracks_elem.remove(bus_track)
        
        # Update track count
        tracks_elem.set('Value', str(len(tracks_elem.findall('./'))))

        # Convert back to bytes while preserving formatting
        xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        return xml_str

    except Exception as e:
        raise Exception(f"Error removing group track: {e}")

def process_als_file(input_path, output_path=None, group_name="Bus"):
    """Process an Ableton Live Set file"""
    input_path = Path(input_path)
    if not input_path.exists():
        raise Exception(f"Input file does not exist: {input_path}")

    # Generate output path if not provided
    if output_path is None:
        output_path = get_output_path(input_path)
    else:
        output_path = Path(output_path)

    try:
        # Extract and process
        xml_content = extract_als_to_xml(input_path)
        cleaned_xml = remove_group_track(xml_content, group_name)
        
        # Save result
        save_als_from_xml(cleaned_xml, output_path)
        
        print(f"\nProcessing complete!")
        print(f"Group track '{group_name}' and its contents have been removed")
        print(f"\nCleaned file saved to: {output_path}")
        
    except Exception as e:
        print(f"\nError: {e}")
        return False

    return True

def main():
    parser = argparse.ArgumentParser(description='Remove a specific group track and its contents from an Ableton Live Set')
    parser.add_argument('input_file', type=str, help='Input .als file path')
    parser.add_argument('--group', '-g', type=str, help='Name of the group track to remove (default: Bus)', default='Bus')
    parser.add_argument('--output', '-o', type=str, help='Output .als file path (optional, defaults to input_no_bus.als)', default=None)
    
    args = parser.parse_args()
    
    try:
        success = process_als_file(args.input_file, args.output, args.group)
        exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main() 