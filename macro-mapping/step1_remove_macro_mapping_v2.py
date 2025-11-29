#!/usr/bin/env python3
"""
Step 1: Remove macro 16 mapping (pure string replacement, exact match to manual step).
"""

import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'utils'))
from decoder import decode_adg
from encoder import encode_adg


def remove_macro_mapping(xml_content: str, macro_idx: int = 15) -> str:
    """
    Remove macro mapping using exact string patterns from manual diff.

    Changes:
    1. MacroControlIndex Value="15" → MacroControlIndex Value="-1"
    2. Remove nested MidiControllerRange, replace with empty
    """

    # Change 1: Find the PluginParameterSettings block with MacroControlIndex="15"
    # and replace the MacroControlIndex and MidiControllerRange

    # Pattern: Match the entire section from MacroControlIndex to the closing MidiControllerRange
    pattern = re.compile(
        r'(<MacroControlIndex Value="15" />\s*)'
        r'(<MidiControllerRange>\s*'
        r'<MidiControllerRange Id="0">\s*'
        r'<Min Value="0" />\s*'
        r'<Max Value="1" />\s*'
        r'</MidiControllerRange>\s*'
        r'</MidiControllerRange>)',
        re.DOTALL
    )

    replacement = '<MacroControlIndex Value="-1" />\n\t\t\t\t\t\t<MidiControllerRange />'

    modified = pattern.sub(replacement, xml_content)

    if modified == xml_content:
        print('⚠ Warning: No macro 15 mapping found to remove')
        return xml_content

    print('✓ Removed MacroControlIndex="15" and replaced MidiControllerRange')

    return modified


def main():
    if len(sys.argv) < 3:
        print('Usage: python3 step1_remove_macro_mapping_v2.py <input.adg> <output.adg>')
        print('')
        print('Example:')
        print('  python3 step1_remove_macro_mapping_v2.py "step 0.adg" "step 1.adg"')
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f'Error: Input not found: {input_path}')
        return 1

    print(f'Removing Macro 16 mapping from: {input_path.name}')
    print('=' * 70)

    # Decode
    xml = decode_adg(input_path)
    print(f'Input size: {len(xml):,} chars')

    # Remove mapping
    modified = remove_macro_mapping(xml)

    # Encode
    encode_adg(modified, output_path)

    print(f'Output size: {len(modified):,} chars')
    print(f'Change: {len(modified) - len(xml):+,} chars')
    print(f'\n✓ Created: {output_path}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
