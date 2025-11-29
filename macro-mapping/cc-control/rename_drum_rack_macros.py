#!/usr/bin/env python3
"""
Rename macros in Ableton drum rack .adg files
"""
import re
import sys
from pathlib import Path

# Add parent directory to path to import utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.decoder import decode_adg
from utils.encoder import encode_adg


def rename_macros_in_xml(xml_content: str, macro_names: dict) -> str:
    """
    Rename drum rack macros in XML content

    Args:
        xml_content: XML string content from .adg file
        macro_names: Dict mapping macro index (0-15) to new name

    Returns:
        Modified XML content
    """
    modified_xml = xml_content

    # Drum rack macros use MacroDisplayNames.X tags
    # Pattern: <MacroDisplayNames.0 Value="Macro 1" />

    for macro_idx, new_name in macro_names.items():
        # Match the MacroDisplayNames tag for this specific macro
        old_pattern = f'<MacroDisplayNames.{macro_idx} Value="Macro {macro_idx + 1}" />'
        new_pattern = f'<MacroDisplayNames.{macro_idx} Value="{new_name}" />'

        modified_xml = modified_xml.replace(old_pattern, new_pattern)

    return modified_xml


def process_drum_rack(adg_path: Path, macro_names: dict, backup: bool = True) -> bool:
    """
    Process a single drum rack file to rename macros

    Args:
        adg_path: Path to .adg file
        macro_names: Dict mapping macro index to new name
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
            print(f"  ✓ Backup created: {backup_path.name}")

        # Rename macros
        modified_xml = rename_macros_in_xml(xml_content, macro_names)

        # Encode back to ADG
        encode_adg(modified_xml, adg_path)

        print(f"  ✓ Macros renamed successfully")
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    # Define macro renames (0-indexed to match MacroDisplayNames.X)
    macro_names = {
        0: "Saturation",  # MacroDisplayNames.0 (Macro 1)
        1: "Crush",       # MacroDisplayNames.1 (Macro 2)
        2: "MixUp",       # MacroDisplayNames.2 (Macro 3)
        3: "Reverb",      # MacroDisplayNames.3 (Macro 4)
        4: "Delay",       # MacroDisplayNames.4 (Macro 5)
        5: "40",          # MacroDisplayNames.5 (Macro 6)
    }

    # Target directory
    drums_dir = Path("/Users/Shared/DevWork/GitHub/Looping/ableton/Presets/audio-units/native-instruments/Komplete Kontrol Organized/Drums/40s Very Own - Drums Library")

    if not drums_dir.exists():
        print(f"Error: Directory not found: {drums_dir}")
        return 1

    # Get all .adg files
    adg_files = sorted(drums_dir.glob("*.adg"))

    if not adg_files:
        print(f"No .adg files found in {drums_dir}")
        return 1

    print(f"Found {len(adg_files)} drum rack files")
    print("\nMacro renaming plan:")
    for idx, name in macro_names.items():
        print(f"  Macro {idx + 1} → {name}")

    # Process each file
    successful = 0
    failed = 0

    for adg_file in adg_files:
        if process_drum_rack(adg_file, macro_names, backup=True):
            successful += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Processing complete:")
    print(f"  ✓ Successful: {successful}")
    if failed > 0:
        print(f"  ✗ Failed: {failed}")
    print(f"\nBackup files created with .bak extension")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
