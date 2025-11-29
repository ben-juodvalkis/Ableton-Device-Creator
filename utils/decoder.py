# decoder.py
import gzip
from pathlib import Path

def decode_adg(adg_path: Path) -> str:
    """
    Decode an Ableton .adg file to XML string
    
    Args:
        adg_path (Path): Path to the .adg file
        
    Returns:
        str: Decoded XML content
    """
    try:
        with gzip.open(adg_path, 'rb') as f:
            xml_content = f.read().decode('utf-8')
        return xml_content
    except Exception as e:
        raise Exception(f"Error decoding ADG file: {e}")


def encode_adg(xml_content: str, output_path: Path) -> None:
    """
    Encode XML content to an Ableton .adg file
    
    Args:
        xml_content (str): XML content to encode
        output_path (Path): Path where to save the .adg file
    """
    try:
        with gzip.open(output_path, 'wb') as f:
            f.write(xml_content.encode('utf-8'))
    except Exception as e:
        raise Exception(f"Error encoding ADG file: {e}")