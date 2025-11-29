# encoder.py
import gzip
from pathlib import Path

def encode_adg(xml_content: str, output_path: Path) -> None:
    """
    Encode XML content to an Ableton .adg file

    Matches Ableton's gzip format:
    - No timestamp (mtime=0)
    - No filename in header (filename='')
    - Deflate compression

    Args:
        xml_content (str): XML content to encode
        output_path (Path): Path where the .adg file should be saved
    """
    try:
        # Use GzipFile with explicit parameters to match Ableton's format
        # filename='' prevents FNAME flag from being set
        with open(output_path, 'wb') as f_out:
            with gzip.GzipFile(filename='', fileobj=f_out, mode='wb', mtime=0) as gz:
                gz.write(xml_content.encode('utf-8'))
    except Exception as e:
        raise Exception(f"Error encoding ADG file: {e}")