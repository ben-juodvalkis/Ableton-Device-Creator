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