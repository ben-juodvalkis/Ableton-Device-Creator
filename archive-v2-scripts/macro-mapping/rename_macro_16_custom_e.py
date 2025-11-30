#!/usr/bin/env python3
"""
Rename macro 16 to 'Custom E' in Ableton .adg files

Usage:
    python rename_macro_16_custom_e.py <file_or_directory>

Examples:
    python rename_macro_16_custom_e.py /path/to/file.adg
    python rename_macro_16_custom_e.py /path/to/directory/
"""
import re
import sys
from pathlib import Path

# Add parent directory to path to import utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.decoder import decode_adg
from utils.encoder import encode_adg


def rename_macro_in_xml(xml_content: str, macro_idx: int, new_name: str) -> str:
    """
    Rename a macro in XML content, regardless of its current name

    Args:
        xml_content: XML string content from .adg file
        macro_idx: Macro index (0-15)
        new_name: New name for the macro

    Returns:
        Modified XML content
    """
    # Use regex to match any current value for this macro
    pattern = rf'(<MacroDisplayNames\.{macro_idx} Value=")[^"]*(" />)'
    replacement = rf'\g<1>{new_name}\g<2>'

    modified_xml, count = re.subn(pattern, replacement, xml_content)

    if count > 0:
        print(f"    Found and renamed {count} MacroDisplayNames.{macro_idx} tag(s)")

    return modified_xml


def process_file(adg_path: Path, macro_idx: int, new_name: str, backup: bool = True) -> bool:
    """
    Process a single .adg file to rename a macro

    Args:
        adg_path: Path to .adg file
        macro_idx: Macro index (0-15)
        new_name: New name for the macro
        backup: Whether to create .bak backup file

    Returns:
        True if successful
    """
    try:
        print(f"\nProcessing: {adg_path.name}")

        # Decode ADG to XML
        xml_content = decode_adg(adg_path)

        # Backup original if requested
        if backup:
            backup_path = adg_path.with_suffix('.adg.bak')
            with open(backup_path, 'wb') as f:
                import gzip
                with gzip.open(adg_path, 'rb') as orig:
                    f.write(orig.read())
            print(f"  Backup created: {backup_path.name}")

        # Rename macro
        modified_xml = rename_macro_in_xml(xml_content, macro_idx, new_name)

        # Encode back to ADG
        encode_adg(modified_xml, adg_path)

        print(f"  Macro {macro_idx + 1} renamed to '{new_name}'")
        return True

    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    target_path = Path(sys.argv[1])

    # Configuration: Macro 16 = index 15
    macro_idx = 15
    new_name = "Custom E"

    if not target_path.exists():
        print(f"Error: Path not found: {target_path}")
        return 1

    # Collect .adg files
    if target_path.is_file():
        if target_path.suffix.lower() != '.adg':
            print(f"Error: Not an .adg file: {target_path}")
            return 1
        adg_files = [target_path]
    else:
        adg_files = sorted(target_path.glob("**/*.adg"))

    if not adg_files:
        print(f"No .adg files found")
        return 1

    print(f"Found {len(adg_files)} .adg file(s)")
    print(f"Renaming Macro {macro_idx + 1} to '{new_name}'")

    # Process files
    successful = 0
    failed = 0

    for adg_file in adg_files:
        if process_file(adg_file, macro_idx, new_name, backup=True):
            successful += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Complete: {successful} successful, {failed} failed")
    if successful > 0:
        print(f"Backup files created with .bak extension")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
