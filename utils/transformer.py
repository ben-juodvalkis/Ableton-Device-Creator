# transformer.py
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

def transform_xml(xml_content: str, sample_paths: List[str], start_pad: int = 0) -> str:
    """
    Transform the XML content by replacing sample paths in DrumCell devices

    Args:
        xml_content (str): Original XML content
        sample_paths (List[str]): List of sample paths to use (can contain None)
        start_pad (int): Starting pad index (0-31). Samples before this pad are untouched.

    Returns:
        str: Transformed XML content
    """
    try:
        # Parse the XML
        root = ET.fromstring(xml_content)

        # Find all DrumBranchPreset elements (individual drum pads)
        drum_pads = root.findall(".//DrumBranchPreset")

        # Keep track of how many samples we've replaced
        replaced_count = 0

        # Sort drum pads by receiving note DESCENDING - Ableton has highest MIDI at pad 1
        drum_pads.sort(key=lambda pad: int(pad.find(".//ZoneSettings/ReceivingNote").get("Value")), reverse=True)

        # Process each pad with its corresponding sample
        for sample_index, sample_path in enumerate(sample_paths):
            # Calculate the actual pad index (start_pad + sample_index)
            pad_index = start_pad + sample_index

            # Stop if we've run out of pads
            if pad_index >= len(drum_pads):
                break

            # Skip if no sample provided for this position
            if not sample_path:
                continue

            pad = drum_pads[pad_index]

            # Find DrumCell devices within this pad
            drum_cells = pad.findall(".//DrumCell")

            for cell in drum_cells:
                # Find the sample reference for this drum cell
                sample_refs = cell.findall(".//UserSample/Value/SampleRef/FileRef")

                for file_ref in sample_refs:
                    # Update the absolute path
                    path_elem = file_ref.find("Path")
                    if path_elem is not None:
                        path_elem.set('Value', sample_path)

                        # Update the relative path
                        rel_path_elem = file_ref.find("RelativePath")
                        if rel_path_elem is not None:
                            # Split the path and keep the last three components
                            path_parts = sample_path.split('/')
                            new_rel_path = "../../" + '/'.join(path_parts[-3:])
                            rel_path_elem.set('Value', new_rel_path)

                        replaced_count += 1

        if start_pad == 0:
            print(f"Replaced samples in {replaced_count} drum cell(s)")
        else:
            print(f"Replaced samples in {replaced_count} drum cell(s) starting at pad {start_pad + 1}")

        # Convert back to string with the XML declaration
        return ET.tostring(root, encoding='unicode', xml_declaration=True)

    except Exception as e:
        raise Exception(f"Error transforming XML: {e}")

def get_drum_cell_info(xml_content: str) -> list:
    """
    Get information about all drum cells in the rack
    
    Args:
        xml_content (str): XML content to analyze
        
    Returns:
        list: List of dictionaries containing info about each drum cell
    """
    root = ET.fromstring(xml_content)
    cells_info = []
    
    drum_pads = root.findall(".//DrumBranchPreset")
    for pad in drum_pads:
        drum_cells = pad.findall(".//DrumCell")
        for cell in drum_cells:
            cell_info = {}
            
            # Get receiving note (MIDI note) for the pad
            zone_settings = pad.find(".//ZoneSettings")
            if zone_settings is not None:
                receiving_note = zone_settings.find("ReceivingNote")
                if receiving_note is not None:
                    cell_info['midi_note'] = receiving_note.get('Value')
            
            # Get sample path if it exists
            sample_ref = cell.find(".//UserSample/Value/SampleRef/FileRef/Path")
            if sample_ref is not None:
                cell_info['sample_path'] = sample_ref.get('Value')
            
            cells_info.append(cell_info)
    
    return cells_info