#!/usr/bin/env python3
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Optional

def shift_drum_rack_pitch(xml_content: str, semitones: int = 16) -> str:
    """
    Shift the MIDI note assignments in a drum rack by the specified number of semitones
    
    Args:
        xml_content (str): Original XML content
        semitones (int): Number of semitones to shift (default: 16)
        
    Returns:
        str: Transformed XML content with shifted MIDI notes
    """
    try:
        # Parse the XML
        root = ET.fromstring(xml_content)
        
        # Find all DrumBranchPreset elements (individual drum pads)
        drum_pads = root.findall(".//DrumBranchPreset")
        
        # Keep track of how many notes we've shifted
        shifted_count = 0
        
        # Process each pad
        for pad in drum_pads:
            # Find the receiving note element
            zone_settings = pad.find(".//ZoneSettings")
            if zone_settings is not None:
                receiving_note = zone_settings.find("ReceivingNote")
                if receiving_note is not None:
                    # Get current note value
                    current_note = int(receiving_note.get("Value"))
                    
                    # Shift the note down by subtracting semitones
                    new_note = current_note - semitones
                    
                    # Update the note value
                    receiving_note.set("Value", str(new_note))
                    shifted_count += 1

        print(f"Shifted {shifted_count} MIDI note(s) down by {semitones} semitones")
        
        # Convert back to string with the XML declaration
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    except Exception as e:
        raise Exception(f"Error shifting drum rack pitch: {e}")

def main():
    parser = argparse.ArgumentParser(description='Shift MIDI note assignments in a drum rack ADG file')
    parser.add_argument('input_file', type=str, help='Input .adg file path')
    parser.add_argument('--output-file', type=str, help='Output .adg file path (optional)')
    parser.add_argument('--semitones', type=int, default=16,
                       help='Number of semitones to shift (default: 16)')
    
    try:
        args = parser.parse_args()
        input_path = Path(args.input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # If no output file specified, create one with '_shifted' suffix
        if not args.output_file:
            output_path = input_path.parent / f"{input_path.stem}_shifted{input_path.suffix}"
        else:
            output_path = Path(args.output_file)
        
        # Read and decode the ADG file
        from decoder import decode_adg
        xml_content = decode_adg(input_path)
        
        # Shift the pitch
        modified_xml = shift_drum_rack_pitch(xml_content, args.semitones)
        
        # Encode and save the modified ADG file
        from encoder import encode_adg
        encode_adg(modified_xml, output_path)
        
        print(f"Successfully created shifted drum rack: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 