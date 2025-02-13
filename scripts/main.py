# main.py
import argparse
from pathlib import Path
from decoder import decode_adg
from encoder import encode_adg
from transformer import transform_xml

def main():
    parser = argparse.ArgumentParser(description='Process Ableton device group files')
    parser.add_argument('input_file', type=str, help='Input .adg file path')
    parser.add_argument('output_file', type=str, help='Output .adg file path')
    
    args = parser.parse_args()
    input_path = Path(args.input_file)
    output_path = Path(args.output_file)
    
    try:
        # Step 1: Decode the ADG file to XML
        xml_content = decode_adg(input_path)
        
        # Step 2: Transform the XML
        transformed_xml = transform_xml(xml_content)
        
        # Step 3: Encode back to ADG
        encode_adg(transformed_xml, output_path)
        
        print(f"Successfully processed {input_path} to {output_path}")
        
    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    main()