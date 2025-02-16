import gzip
from pathlib import Path

def encode_adg(xml_content: str, output_path: Path) -> None:
    """
    Encode XML content to an Ableton .adg file
    
    Args:
        xml_content (str): XML content to encode
        output_path (Path): Path where the .adg file should be saved
    """
    try:
        with gzip.open(output_path, 'wb') as f:
            f.write(xml_content.encode('utf-8'))
    except Exception as e:
        raise Exception(f"Error encoding ADG file: {e}") 