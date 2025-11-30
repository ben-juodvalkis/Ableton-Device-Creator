"""ADG/ADV file encoder - compresses XML to gzip format."""

import gzip
from pathlib import Path
from typing import Union


def encode_adg(xml_content: str, output_path: Union[str, Path]) -> Path:
    """
    Encode XML string to ADG file.

    Matches Ableton's gzip format:
    - No timestamp (mtime=0)
    - No filename in header (filename='')
    - Deflate compression
    - UTF-8 encoding

    Args:
        xml_content: XML content as string
        output_path: Where to save .adg file

    Returns:
        Path to created file

    Raises:
        ValueError: If XML content doesn't start with <?xml
        OSError: If cannot write file

    Example:
        >>> xml = '<?xml version="1.0"?><Ableton>...</Ableton>'
        >>> encode_adg(xml, "MyRack.adg")
        PosixPath('MyRack.adg')
    """
    output_path = Path(output_path)

    # Basic validation that content looks like XML
    if not xml_content.strip().startswith('<?xml'):
        raise ValueError(
            "Content must be valid XML starting with <?xml declaration"
        )

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Match Ableton's gzip format exactly
        with open(output_path, 'wb') as f_out:
            with gzip.GzipFile(
                filename='',      # No filename in header
                fileobj=f_out,
                mode='wb',
                mtime=0           # No timestamp
            ) as gz:
                gz.write(xml_content.encode('utf-8'))
    except OSError as e:
        raise OSError(f"Failed to write file {output_path}: {e}") from e

    return output_path


def encode_adv(xml_content: str, output_path: Union[str, Path]) -> Path:
    """
    Encode XML string to ADV file.

    Alias for encode_adg() - both formats use same encoding.

    Args:
        xml_content: XML content as string
        output_path: Where to save .adv file

    Returns:
        Path to created file
    """
    return encode_adg(xml_content, output_path)
