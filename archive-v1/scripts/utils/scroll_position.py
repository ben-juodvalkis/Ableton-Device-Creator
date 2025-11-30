#!/usr/bin/env python3
import argparse
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add the current directory to sys.path to import sibling modules
sys.path.append(os.path.dirname(__file__))
from decoder import decode_adg
from encoder import encode_adg

def transform_scroll_position(xml_content: str, scroll_position: int) -> str:
    """
    Transform the XML content by modifying the pad scroll position
    
    Args:
        xml_content (str): Original XML content
        scroll_position (int): New scroll position value
        
    Returns:
        str: Transformed XML content
    """
    try:
        # Parse the XML
        root = ET.fromstring(xml_content)
        
        # Find and modify the PadScrollPosition
        pad_scroll_pos = root.find(".//PadScrollPosition")
        if pad_scroll_pos is not None:
            pad_scroll_pos.set('Value', str(scroll_position))
            print(f"Set scroll position to {scroll_position}")
        else:
            print("Warning: Could not find PadScrollPosition element")
        
        # Convert back to string with the XML declaration
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    except Exception as e:
        raise Exception(f"Error transforming XML: {e}")

def modify_scroll_position(input_file, output_file, scroll_position):
    # Decode the ADG file
    xml_content = decode_adg(Path(input_file))
    
    # Transform the content
    transformed_xml = transform_scroll_position(xml_content, scroll_position)
    
    # Encode and save the output file
    encode_adg(transformed_xml, Path(output_file))
    
    print(f"Created {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Modify pad scroll position in an ADG file')
    parser.add_argument('input_file', help='Input ADG file')
    parser.add_argument('--scroll', type=int, default=0, help='Scroll position (0-31)')
    parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    if not args.output:
        # Create output filename based on scroll position
        base_name = os.path.splitext(os.path.basename(args.input_file))[0]
        args.output = f"{base_name}_scroll_{args.scroll}.adg"
    
    modify_scroll_position(args.input_file, args.output, args.scroll)

if __name__ == '__main__':
    main() 