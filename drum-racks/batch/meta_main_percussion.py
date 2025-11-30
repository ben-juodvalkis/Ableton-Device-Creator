#!/usr/bin/env python3
import argparse
from pathlib import Path
import subprocess
import sys
from typing import List

def find_library_folders(expansions_path: Path) -> List[Path]:
    """Find all library folders in the expansions directory that have percussion samples"""
    libraries = []
    try:
        for folder in expansions_path.iterdir():
            perc_path = folder / 'Samples' / 'Drums' / 'Percussion'
            if folder.is_dir() and perc_path.exists() and any(perc_path.glob('*.wav')):
                libraries.append(folder)
    except Exception as e:
        print(f"Error scanning expansions directory: {e}")
    
    return sorted(libraries)

def get_percussion_count(library_path: Path) -> int:
    """Get the number of percussion samples in a library"""
    perc_path = library_path / 'Samples' / 'Drums' / 'Percussion'
    return len(list(perc_path.glob('*.wav')))

def process_library(cmd: List[str]) -> None:
    """Process a single library using main.py"""
    library_name = Path(cmd[3]).name  # Library path is now 4th argument
    print(f"\n{'='*80}")
    print(f"Processing library: {library_name}")
    print(f"{'='*80}\n")
    
    try:
        # Run main.py for this library
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr, file=sys.stderr)
            
        if result.returncode != 0:
            print(f"Warning: Processing {library_name} failed with code {result.returncode}")
            
    except Exception as e:
        print(f"Error processing {library_name}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Create percussion-only drum racks from expansion libraries')
    parser.add_argument('input_file', type=str, help='Input template .adg file path')
    parser.add_argument('expansions_folder', type=str, 
                       help='Path to Native Instruments Expansions folder')
    
    try:
        args = parser.parse_args()
        input_path = Path(args.input_file)
        expansions_path = Path(args.expansions_folder)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        if not expansions_path.exists():
            raise FileNotFoundError(f"Expansions folder not found: {expansions_path}")
        
        # Create Output directory in script location
        output_dir = Path('Output')
        output_dir.mkdir(exist_ok=True)
        
        # Find all library folders with percussion samples
        libraries = find_library_folders(expansions_path)
        
        if not libraries:
            print("No libraries with percussion samples found!")
            return
        
        print(f"Found {len(libraries)} libraries with percussion samples:")
        for lib in libraries:
            perc_count = get_percussion_count(lib)
            print(f"- {lib.name} ({perc_count} percussion samples)")
        print()
        
        # Process each library
        for library in libraries:
            # Create command with output folder and percussion-only flag
            cmd = [
                sys.executable,
                'scripts/device-creation/python/device/drum_rack/main_percussion.py',
                str(input_path),
                str(library),
                '--output-folder',
                str(output_dir / library.name)
            ]
            process_library(cmd)
        
        print(f"\nCompleted processing {len(libraries)} libraries!")
        print(f"All percussion racks can be found in: {output_dir.absolute()}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 