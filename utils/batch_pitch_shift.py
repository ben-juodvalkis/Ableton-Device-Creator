#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List
import sys
import os

# Add the python directory to the Python path for imports
sys.path.append(str(Path(__file__).parent.parent))
from utils.decoder import decode_adg
from utils.encoder import encode_adg
from utils.pitch_shifter import shift_drum_rack_pitch

def find_adg_files(folder_path: Path) -> List[Path]:
    """
    Recursively find all .adg files in the given folder and its subfolders
    
    Args:
        folder_path (Path): Root folder to search in
        
    Returns:
        List[Path]: List of paths to .adg files
    """
    adg_files = []
    try:
        for path in folder_path.rglob("*.adg"):
            adg_files.append(path)
    except Exception as e:
        print(f"Error scanning folder: {e}")
    
    return sorted(adg_files)

def process_adg_file(file_path: Path, semitones: int) -> bool:
    """
    Process a single ADG file by shifting its MIDI notes
    
    Args:
        file_path (Path): Path to the ADG file
        semitones (int): Number of semitones to shift
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"\nProcessing: {file_path}")
        
        # Read and decode the ADG file
        xml_content = decode_adg(file_path)
        
        # Shift the pitch
        modified_xml = shift_drum_rack_pitch(xml_content, semitones)
        
        # Save directly back to the original file
        encode_adg(modified_xml, file_path)
        
        print(f"Successfully updated: {file_path}")
        return True
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Recursively process all ADG files in a folder')
    parser.add_argument('folder', type=str, help='Folder to search for ADG files')
    parser.add_argument('--semitones', type=int, default=16,
                       help='Number of semitones to shift (default: 16)')
    
    try:
        args = parser.parse_args()
        folder_path = Path(args.folder)
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # Find all ADG files
        adg_files = find_adg_files(folder_path)
        
        if not adg_files:
            print("No ADG files found!")
            return 1
        
        print(f"Found {len(adg_files)} ADG files to process")
        print(f"Shifting notes by {args.semitones} semitones")
        
        # Process each file
        success_count = 0
        for file_path in adg_files:
            if process_adg_file(file_path, args.semitones):
                success_count += 1
        
        print(f"\nProcessing complete!")
        print(f"Successfully processed {success_count} out of {len(adg_files)} files")
        
        return 0 if success_count == len(adg_files) else 1
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 