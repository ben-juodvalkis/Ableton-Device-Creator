"""ADG/ADV file decoder - decompresses gzip XML files."""

import gzip
from pathlib import Path
from typing import Union


def decode_adg(file_path: Union[str, Path]) -> str:
    """
    Decode ADG file to XML string.

    ADG and ADV files are gzipped XML files. This function decompresses
    them and returns the XML content as a string.

    Args:
        file_path: Path to .adg or .adv file

    Returns:
        Decompressed XML content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not valid gzip or has wrong extension
        UnicodeDecodeError: If XML content is not valid UTF-8

    Example:
        >>> xml_content = decode_adg("MyDrumRack.adg")
        >>> print(xml_content[:100])
        <?xml version="1.0" encoding="UTF-8"?>
        <Ableton>...
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() not in ['.adg', '.adv']:
        raise ValueError(
            f"Expected .adg or .adv file, got: {file_path.suffix}"
        )

    try:
        with gzip.open(file_path, 'rb') as f:
            xml_bytes = f.read()
    except gzip.BadGzipFile as e:
        raise ValueError(f"Not a valid gzip file: {file_path}") from e

    try:
        return xml_bytes.decode('utf-8')
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(
            e.encoding,
            e.object,
            e.start,
            e.end,
            f"Failed to decode XML content as UTF-8: {e.reason}"
        ) from e


def decode_adv(file_path: Union[str, Path]) -> str:
    """
    Decode ADV file to XML string.

    Alias for decode_adg() - both formats use same encoding.

    Args:
        file_path: Path to .adv file

    Returns:
        Decompressed XML content as string
    """
    return decode_adg(file_path)
