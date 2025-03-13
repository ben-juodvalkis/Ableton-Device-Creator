#!/usr/bin/env python3
import gzip
import argparse
from pathlib import Path

def process_als_file(input_path, output_path=None):
    """Simply extract and recompress the ALS file without modifications"""
    input_path = Path(input_path)
    if not input_path.exists():
        raise Exception(f"Input file does not exist: {input_path}")

    # Generate output path if not provided
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_test{input_path.suffix}"
    else:
        output_path = Path(output_path)

    try:
        # Read the original file
        print("Reading input file...")
        with gzip.open(input_path, 'rb') as f_in:
            content = f_in.read()
        
        print(f"Read {len(content)} bytes")
        
        # Write to new file
        print("Writing output file...")
        with gzip.open(output_path, 'wb') as f_out:
            f_out.write(content)
            
        print(f"\nFile saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test Ableton Live Set file handling by unzipping and rezipping without modifications')
    parser.add_argument('input_file', type=str, help='Input .als file path')
    parser.add_argument('--output', '-o', type=str, help='Output .als file path (optional, defaults to input_test.als)', default=None)
    
    args = parser.parse_args()
    
    try:
        success = process_als_file(args.input_file, args.output)
        exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main() 