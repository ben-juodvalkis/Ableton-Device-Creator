#!/usr/bin/env python3
import gzip
import argparse
from pathlib import Path

def adg_to_xml(adg_path, xml_path):
    """Convert .adg file to .xml"""
    try:
        with gzip.open(adg_path, 'rb') as f_in:
            with open(xml_path, 'wb') as f_out:
                f_out.write(f_in.read())
        print(f"Successfully converted {adg_path} to {xml_path}")
    except Exception as e:
        print(f"Error converting ADG to XML: {e}")

def xml_to_adg(xml_path, adg_path):
    """Convert .xml file to .adg"""
    try:
        with open(xml_path, 'rb') as f_in:
            with gzip.open(adg_path, 'wb', compresslevel=6) as f_out:
                f_out.write(f_in.read())
        print(f"Successfully converted {xml_path} to {adg_path}")
    except Exception as e:
        print(f"Error converting XML to ADG: {e}")

def main():
    parser = argparse.ArgumentParser(description='Convert between Ableton .adg and .xml files')
    parser.add_argument('input_file', type=str, help='Input file path')
    parser.add_argument('output_file', type=str, help='Output file path')
    
    args = parser.parse_args()
    input_path = Path(args.input_file)
    output_path = Path(args.output_file)
    
    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist")
        return
    
    if input_path.suffix.lower() == '.adg':
        adg_to_xml(input_path, output_path)
    elif input_path.suffix.lower() == '.xml':
        xml_to_adg(input_path, output_path)
    else:
        print("Error: Input file must be either .adg or .xml")

if __name__ == "__main__":
    main()