#!/usr/bin/env python3
import gzip
import argparse
from pathlib import Path

def convert_to_xml(device_path, xml_path):
    """Convert .adg or .adv file to .xml"""
    try:
        with gzip.open(device_path, 'rb') as f_in:
            with open(xml_path, 'wb') as f_out:
                f_out.write(f_in.read())
        print(f"Successfully converted {device_path} to {xml_path}")
    except Exception as e:
        print(f"Error converting to XML: {e}")

def convert_to_device(xml_path, device_path):
    """Convert .xml file to .adg or .adv"""
    try:
        with open(xml_path, 'rb') as f_in:
            with gzip.open(device_path, 'wb', compresslevel=6) as f_out:
                f_out.write(f_in.read())
        print(f"Successfully converted {xml_path} to {device_path}")
    except Exception as e:
        print(f"Error converting from XML: {e}")

def main():
    parser = argparse.ArgumentParser(description='Convert between Ableton device files (.adg/.adv) and .xml files')
    parser.add_argument('input_file', type=str, help='Input file path')
    parser.add_argument('output_file', type=str, help='Output file path')
    
    args = parser.parse_args()
    input_path = Path(args.input_file)
    output_path = Path(args.output_file)
    
    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist")
        return
    
    if input_path.suffix.lower() in ['.adg', '.adv']:
        convert_to_xml(input_path, output_path)
    elif input_path.suffix.lower() == '.xml':
        convert_to_device(input_path, output_path)
    else:
        print("Error: Input file must be either .adg, .adv, or .xml")

if __name__ == "__main__":
    main()