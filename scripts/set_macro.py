#!/usr/bin/env python3
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from decoder import decode_adg
from encoder import encode_adg

def set_macro_value(xml_content: str, macro_number: int, value: int) -> str:
    """Set macro value in the XML content"""
    try:
        root = ET.fromstring(xml_content)
        
        # Set MacroDefaults value
        macro_default = root.find(f".//MacroDefaults.{macro_number - 1}")
        if macro_default is not None:
            macro_default.set('Value', str(float(value)))
            print(f"Set MacroDefaults.{macro_number - 1} to {value}")
        
        # Set Manual value in MacroControls
        macro_control = root.find(f".//MacroControls.{macro_number - 1}/Manual")
        if macro_control is not None:
            macro_control.set('Value', str(float(value)))
            print(f"Set MacroControls.{macro_number - 1} Manual to {value}")
            
        if macro_default is None and macro_control is None:
            raise ValueError(f"No macro controls found for Macro {macro_number}")
        
        # Convert back to string with the XML declaration
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
        
    except Exception as e:
        raise Exception(f"Error setting macro value: {e}")

def process_adg_file(file_path: Path, macro_number: int, value: int) -> None:
    """Process a single ADG file"""
    try:
        # Decode ADG to XML
        xml_content = decode_adg(file_path)
        
        # Set macro value
        modified_xml = set_macro_value(xml_content, macro_number, value)
        
        # Encode back to ADG
        encode_adg(modified_xml, file_path)
        
        print(f"Successfully processed: {file_path}")
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def find_and_process_adg_files(folder_path: Path, macro_number: int, value: int) -> None:
    """Recursively find and process all ADG files in folder"""
    try:
        # Find all .adg files in folder and subfolders
        adg_files = list(folder_path.rglob('*.adg'))
        
        if not adg_files:
            print(f"No ADG files found in {folder_path}")
            return
        
        print(f"Found {len(adg_files)} ADG files to process:")
        for file in adg_files:
            print(f"- {file.relative_to(folder_path)}")
        print()
        
        # Process each file
        processed = 0
        for file in adg_files:
            try:
                process_adg_file(file, macro_number, value)
                processed += 1
            except Exception as e:
                print(f"Failed to process {file}: {e}")
        
        print(f"\nCompleted processing {processed} of {len(adg_files)} files")
        
    except Exception as e:
        print(f"Error scanning folder: {e}")

def main():
    parser = argparse.ArgumentParser(description='Set macro value in Ableton drum racks')
    parser.add_argument('folder', type=str, help='Folder containing .adg files')
    parser.add_argument('macro', type=int, help='Macro number (1-127)')
    parser.add_argument('value', type=int, help='Value to set (0-127)')
    
    try:
        args = parser.parse_args()
        folder_path = Path(args.folder)
        
        # Validate arguments
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        if not 1 <= args.macro <= 127:
            raise ValueError("Macro number must be between 1 and 127")
            
        if not 0 <= args.value <= 127:
            raise ValueError("Macro value must be between 0 and 127")
        
        # Process files
        find_and_process_adg_files(folder_path, args.macro, args.value)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 