#!/usr/bin/env python3
"""
Batch Round Robin Creator for 8Dio Mini Library
Processes all instrument sample folders and creates round robin devices.
Names devices based on parent instrument folder.
"""
import argparse
from pathlib import Path
import sys
from typing import List
import subprocess

# Add utils to path
sys.path.append(str(Path(__file__).parent))
from round_robin_creator import get_samples_from_folder, create_round_robin_xml
from utils.decoder import decode_adg
from utils.encoder import encode_adg

def find_sample_folders(library_path: Path) -> List[Path]:
    """Find all 'Samples' directories in the 8Dio library"""
    sample_folders = []
    for samples_dir in library_path.rglob("Samples"):
        if samples_dir.is_dir():
            sample_folders.append(samples_dir)
    return sorted(sample_folders)

def get_instrument_name(samples_path: Path) -> str:
    """Extract instrument name from parent directory"""
    # samples_path is like: .../instrument_name/Samples
    # or: .../instrument_name/subcategory/Samples
    parent = samples_path.parent
    
    # Handle nested structure like "air_hammer/bang/Samples"
    if parent.name in ['bang', 'brush', 'hit', 'tap', 'strike', 'soft', 'hard']:
        # Use grandparent + parent for more descriptive names
        grandparent = parent.parent
        return f"{grandparent.name}_{parent.name}"
    else:
        return parent.name

def sanitize_filename(name: str) -> str:
    """Clean up name for use as filename"""
    # Replace common separators with spaces
    name = name.replace('_', ' ').replace('-', ' ')
    # Title case
    name = ' '.join(word.capitalize() for word in name.split())
    # Remove any invalid characters
    return "".join(c for c in name if c.isalnum() or c in ' -_')

def process_library(template_path: Path, library_path: Path, output_dir: Path) -> None:
    """Process entire 8Dio Mini library"""
    
    sample_folders = find_sample_folders(library_path)
    
    if not sample_folders:
        print(f"No 'Samples' directories found in {library_path}")
        return
    
    print(f"Found {len(sample_folders)} sample directories to process")
    print(f"Output directory: {output_dir}")
    print()
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load template once
    print("Loading template...")
    template_xml = decode_adg(template_path)
    
    processed = 0
    skipped = 0
    
    for samples_path in sample_folders:
        try:
            instrument_name = get_instrument_name(samples_path)
            clean_name = sanitize_filename(instrument_name)
            
            print(f"Processing: {clean_name} ({samples_path.parent.name})")
            
            # Get samples from folder
            samples = get_samples_from_folder(samples_path)
            
            if not samples:
                print(f"  ⚠️  No valid samples found, skipping")
                skipped += 1
                continue
            
            if len(samples) < 2:
                print(f"  ⚠️  Only {len(samples)} sample(s) found, skipping (need at least 2 for round robin)")
                skipped += 1
                continue
            
            print(f"  📁 Found {len(samples)} samples")
            
            # Create output path
            output_path = output_dir / f"{clean_name} Round Robin.adg"
            
            # Skip if already exists
            if output_path.exists():
                print(f"  ⏭️  Already exists, skipping")
                skipped += 1
                continue
            
            # Transform XML with new samples
            transformed_xml = create_round_robin_xml(template_xml, samples, clean_name)
            
            # Save the device
            encode_adg(transformed_xml, output_path)
            
            print(f"  ✅ Created: {output_path.name}")
            processed += 1
            
        except Exception as e:
            print(f"  ❌ Error processing {samples_path}: {e}")
            skipped += 1
    
    print()
    print("="*60)
    print(f"Batch processing complete!")
    print(f"✅ Successfully processed: {processed} instruments")
    print(f"⚠️  Skipped: {skipped} instruments")
    print(f"📁 Output directory: {output_dir}")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(
        description='Batch create round robin devices from 8Dio Mini library',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Process entire 8Dio Mini library (uses repo template by default)
  python3 batch_round_robin_8dio.py "/path/to/8Dio_Mini/1_Click_Core_Library"
  
  # Use custom template
  python3 batch_round_robin_8dio.py "/path/to/8Dio_Mini/1_Click_Core_Library" --template "/path/to/Mini Template.adg"
  
  # Specify custom output directory
  python3 batch_round_robin_8dio.py "/path/to/8Dio_Mini/1_Click_Core_Library" --output "/path/to/output"
        '''
    )
    
    parser.add_argument('library_path', type=str, help='Path to 8Dio Mini 1_Click_Core_Library folder')
    parser.add_argument('--template', '-t', type=str, help='Path to Mini Template.adg file (default: uses repo template)')
    parser.add_argument('--output', '-o', type=str, help='Output directory for .adg files (default: Desktop/8Dio_Mini_Round_Robin)')
    parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing files')
    
    try:
        args = parser.parse_args()
        
        # Use repo template by default
        if args.template:
            template_path = Path(args.template)
        else:
            # Use template from repo
            script_dir = Path(__file__).parent
            template_path = script_dir.parent / "templates" / "Mini Template.adg"
        
        library_path = Path(args.library_path)
        
        # Validate inputs
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        if not library_path.exists() or not library_path.is_dir():
            raise FileNotFoundError(f"Library folder not found: {library_path}")
        
        # Setup output directory
        if args.output:
            output_dir = Path(args.output)
        else:
            output_dir = Path.home() / "Desktop" / "8Dio_Mini_Round_Robin"
        
        print(f"8Dio Mini Round Robin Batch Creator")
        print("="*50)
        print(f"Template: {template_path}")
        print(f"Library: {library_path}")
        print(f"Output: {output_dir}")
        print()
        
        # Process the library
        process_library(template_path, library_path, output_dir)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())