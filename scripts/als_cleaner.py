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
    """Generate output path with _cleaned suffix"""
    input_path = Path(input_path)
    return input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"

def has_arrangement_clips(track_elem):
    """Check if a track has clips in the arrangement view"""
    # Check for ArrangementClips element
    arrangement_clips = track_elem.find('.//ArrangementClips')
    if arrangement_clips is not None:
        # Check if there are any Events in ArrangerAutomation
        sample = track_elem.find('.//Sample/ArrangerAutomation/Events')
        if sample is not None and len(sample) > 0:
            print(f"Found arrangement events in track")
            return True

        # Check for any non-empty clip elements
        for child in arrangement_clips.iter():
            if child.tag in ['AudioClip', 'MidiClip']:
                print(f"Found {child.tag} in ArrangementClips")
                return True

    # Check the MainSequencer for clips
    main_sequencer = track_elem.find('.//MainSequencer/Sample/ArrangerAutomation/Events')
    if main_sequencer is not None and len(main_sequencer) > 0:
        print(f"Found events in MainSequencer")
        return True

    print(f"No arrangement clips found in track")
    return False

def clean_live_set(xml_content):
    """Remove MIDI tracks and empty audio tracks from top level only, preserving all group contents"""
    try:
        # Parse XML while preserving formatting
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        root = ET.fromstring(xml_content.decode('utf-8'), parser=parser)
        
        # Find the Tracks element
        tracks_elem = root.find('.//Tracks')
        if tracks_elem is None:
            raise Exception("No tracks found in the Live Set")

        # Track statistics for reporting
        stats = {
            'total_tracks': 0,
            'removed_midi': 0,
            'removed_empty_audio': 0,
            'preserved_groups': 0,
            'kept_tracks': 0
        }
        
        # Process only top-level tracks
        tracks_to_remove = []
        
        for track in tracks_elem.findall('./'):
            stats['total_tracks'] += 1
            track_name = track.find('.//Name/EffectiveName')
            track_id = track.get('Id', 'unknown')
            name_str = track_name.get('Value', 'unnamed') if track_name is not None else 'unnamed'
            print(f"\nChecking track {track_id} ({name_str})")
            
            if track.tag == 'GroupTrack':
                print(f"Track {track_id} is GroupTrack - preserving with all contents")
                stats['preserved_groups'] += 1
                stats['kept_tracks'] += 1
            elif track.tag == 'ReturnTrack':
                print(f"Track {track_id} is ReturnTrack - keeping")
                stats['kept_tracks'] += 1
            elif track.tag == 'MidiTrack':
                print(f"Track {track_id} is a MIDI track - will remove")
                stats['removed_midi'] += 1
                tracks_to_remove.append(track)
            elif track.tag == 'AudioTrack':
                if has_arrangement_clips(track):
                    print(f"Track {track_id} has arrangement clips - keeping")
                    stats['kept_tracks'] += 1
                else:
                    print(f"Track {track_id} has no arrangement clips - will remove")
                    stats['removed_empty_audio'] += 1
                    tracks_to_remove.append(track)
        
        # Remove tracks marked for removal
        for track in tracks_to_remove:
            tracks_elem.remove(track)
        
        # Update track count
        tracks_elem.set('Value', str(len(tracks_elem.findall('./'))))
        
        if stats['kept_tracks'] == 0:
            raise Exception("Cannot remove all tracks - at least one track must remain")

        # Convert back to bytes while preserving formatting
        xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        return xml_str, stats

    except Exception as e:
        raise Exception(f"Error cleaning Live Set: {e}")

def process_als_file(input_path, output_path=None):
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
        cleaned_xml, stats = clean_live_set(xml_content)
        
        # Save result
        save_als_from_xml(cleaned_xml, output_path)
        
        # Print statistics
        print("\nProcessing complete!")
        print(f"Total tracks processed: {stats['total_tracks']}")
        print(f"MIDI tracks removed: {stats['removed_midi']}")
        print(f"Empty audio tracks removed: {stats['removed_empty_audio']}")
        print(f"Group tracks preserved (with contents): {stats['preserved_groups']}")
        print(f"Tracks kept: {stats['kept_tracks']}")
        print(f"\nCleaned file saved to: {output_path}")
        
    except Exception as e:
        print(f"\nError: {e}")
        return False

    return True

def main():
    parser = argparse.ArgumentParser(description='Clean up Ableton Live Set by removing MIDI tracks and audio tracks without arrangement clips')
    parser.add_argument('input_file', type=str, help='Input .als file path')
    parser.add_argument('--output', '-o', type=str, help='Output .als file path (optional, defaults to input_cleaned.als)', default=None)
    
    args = parser.parse_args()
    
    try:
        success = process_als_file(args.input_file, args.output)
        exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main() 