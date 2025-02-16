#!/usr/bin/env python3
import argparse
from pathlib import Path
import subprocess
import sys
import os

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def find_sample_folders(base_path: Path) -> list[Path]:
    """Find all folders containing audio samples"""
    sample_folders = []
    
    try:
        # Check if current folder has audio files
        has_samples = any(
            f.suffix.lower() in ('.wav', '.aif', '.aiff') 
            for f in base_path.iterdir() 
            if f.is_file()
        )
        if has_samples:
            sample_folders.append(base_path)
        
        # Recursively check subfolders
        for folder in base_path.iterdir():
            if folder.is_dir():
                sample_folders.extend(find_sample_folders(folder))
                
    except Exception as e:
        print(f"Error scanning directory {base_path}: {e}")
    
    return sample_folders

def count_audio_files(folder_path: Path) -> int:
    """Count audio files in a folder"""
    count = 0
    try:
        for ext in ('*.wav', '*.aif', '*.aiff'):
            count += len(list(folder_path.glob(ext)))
    except Exception:
        pass
    return count

def process_folder(cmd: list[str]) -> None:
    """Process a single folder using main_sampler.py"""
    folder_path = Path(cmd[2])
    print(f"\n{'='*80}")
    print(f"Processing folder: {folder_path}")
    print(f"{'='*80}\n")
    
    try:
        # Run main_sampler.py for this folder
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
    parser = argparse.ArgumentParser(description='Process multiple folders into sampler instruments')
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
        
        # Find all folders containing samples
        sample_folders = find_sample_folders(base_path)
        
        if not sample_folders:
            print("No folders with audio files found!")
            return
        
        # Sort folders for consistent processing order
        sample_folders.sort()
        
        print(f"Found {len(sample_folders)} folders with samples:")
        for folder in sample_folders:
            sample_count = count_audio_files(folder)
            print(f"- {folder.relative_to(base_path)} ({sample_count} audio files)")
        print()
        
        # Process each folder
        for folder in sample_folders:
            # Create command
            cmd = [
                sys.executable,
                str(Path(__file__).parent / 'main_sampler.py'),
                str(input_path),
                str(folder)
            ]
            process_folder(cmd)
        
        print(f"\nCompleted processing {len(sample_folders)} folders!")
        print(f"All sampler instruments can be found in: output-sampler/")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 