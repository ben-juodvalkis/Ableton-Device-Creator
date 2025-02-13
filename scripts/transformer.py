# transformer.py
import xml.etree.ElementTree as ET

def transform_xml(xml_content: str, new_sample_path: str = "/Users/Shared/Music/Soundbanks/Native Instruments/Expansions/Amplified Funk Library/Samples/Drums/Clap/Clap BluOut 1.wav") -> str:
    """
    Transform the XML content by replacing the sample path in the DrumCell device
    
    Args:
        xml_content (str): Original XML content
        new_sample_path (str): Full path to the new sample file
        
    Returns:
        str: Transformed XML content
    """
    try:
        # Parse the XML
        root = ET.fromstring(xml_content)
        
        # Find all sample references in drum cells
        for file_ref in root.findall(".//UserSample/Value/SampleRef/FileRef"):
            # Update the absolute path
            path_elem = file_ref.find("Path")
            if path_elem is not None:
                path_elem.set('Value', new_sample_path)
                
            # Update the relative path - extract the filename from the full path
            rel_path_elem = file_ref.find("RelativePath")
            if rel_path_elem is not None:
                # Split the path and keep the last two components (folder/filename)
                path_parts = new_sample_path.split('/')
                new_rel_path = "../../" + '/'.join(path_parts[-3:])
                rel_path_elem.set('Value', new_rel_path)
        
        # Convert back to string with the XML declaration
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    except Exception as e:
        raise Exception(f"Error transforming XML: {e}")