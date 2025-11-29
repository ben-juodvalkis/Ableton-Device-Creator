#!/usr/bin/env python3
import argparse
from pathlib import Path
import subprocess
import sys
from typing import List

def find_sample_folders(base_path: Path) -> List[Path]:
    """Find all folders containing wav files"""
    sample_folders = []
    
    try:
        # Check if current folder has wav files
        if any(base_path.glob('*.wav')):
            sample_folders.append(base_path)
        
        # Recursively check subfolders
        for folder in base_path.iterdir():
            if folder.is_dir():
                sample_folders.extend(find_sample_folders(folder))
                
    except Exception as e:
        print(f"Error scanning directory {base_path}: {e}")
    
    return sample_folders

def process_folder(cmd: List[str]) -> None:
    """Process a single folder using main_generic.py"""
    folder_path = Path(cmd[2])
    print(f"\n{'='*80}")
    print(f"Processing folder: {folder_path}")
    print(f"{'='*80}\n")
    
    try:
        # Run main_generic.py for this folder
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr, file=sys.stderr)
            
        if result.returncode != 0:
            print(f"Warning: Processing {folder_path} failed with code {result.returncode}")
            
    except Exception as e:
        print(f"Error processing {folder_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Process multiple folders into drum racks')
    parser.add_argument('input_file', type=str, help='Input template .adg file path')
    parser.add_argument('base_folder', type=str, help='Path to base folder containing samples')
    
    try:
        args = parser.parse_args()
        input_path = Path(args.input_file)
        base_path = Path(args.base_folder)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        if not base_path.exists():
            raise FileNotFoundError(f"Base folder not found: {base_path}")
        
        # Create Output directory in script location
        output_dir = Path('Output')
        output_dir.mkdir(exist_ok=True)
        
        # Find all folders containing samples
        sample_folders = find_sample_folders(base_path)
        
        if not sample_folders:
            print("No folders with wav files found!")
            return
        
        # Sort folders for consistent processing order
        sample_folders.sort()
        
        print(f"Found {len(sample_folders)} folders with samples:")
        for folder in sample_folders:
            wav_count = len(list(folder.glob('*.wav')))
            print(f"- {folder.relative_to(base_path)} ({wav_count} wav files)")
        print()
        
        # Process each folder
        for folder in sample_folders:
            # Create relative path structure in output directory
            relative_path = folder.relative_to(base_path)
            output_folder = output_dir / relative_path
            
            # Create command
            cmd = [
                sys.executable,
                'scripts/device-creation/python/device/generic/main_generic.py',
                str(input_path),
                str(folder),
                '--output-folder',
                str(output_folder)
            ]
            process_folder(cmd)
        
        print(f"\nCompleted processing {len(sample_folders)} folders!")
        print(f"All drum racks can be found in: {output_dir.absolute()}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 