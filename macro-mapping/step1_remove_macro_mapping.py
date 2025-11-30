#!/usr/bin/env python3
"""
Step 1: Remove macro mapping from a specific parameter in an Ableton .adg file.

This script:
1. Finds a PluginParameterSettings with MacroControlIndex = specific macro
2. Sets MacroControlIndex to -1 (unmapped)
3. Changes MidiControllerRange to empty
4. Sets MacroDefaults for that macro to -1

Pure string-based replacement to preserve formatting.
"""

import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'utils'))
from decoder import decode_adg
from encoder import encode_adg


def remove_macro_mapping(xml_content: str, macro_idx: int, param_id: int = None) -> str:
    """
    Remove macro mapping using string replacement.

    Args:
        xml_content: Decoded .adg XML
        macro_idx: Macro index to unmap (0-15)
        param_id: Optional specific parameter ID to unmap (if None, finds any mapping)

    Returns:
        Modified XML
    """

    # Step 1: Change MacroDefaults.{macro_idx} from whatever value to -1
    pattern = rf'(<MacroDefaults\.{macro_idx} Value=")([^"]+)(")'
    xml_content = re.sub(pattern, rf'\g<1>-1\3', xml_content)
    print(f'✓ Set MacroDefaults.{macro_idx} to -1')

    # Step 2: Find PluginParameterSettings with MacroControlIndex = macro_idx
    # and change it to -1, also simplify MidiControllerRange

    if param_id:
        # Target specific parameter ID
        pattern = (
            rf'(<PluginParameterSettings Id="0">[\s\S]*?'
            rf'<ParameterId Value="{param_id}" />[\s\S]*?)'
            rf'<MacroControlIndex Value="{macro_idx}" />'
            rf'([\s\S]*?</PluginParameterSettings>)'
        )
    else:
        # Find any parameter with this macro mapping
        pattern = (
            rf'(<PluginParameterSettings Id="0">[\s\S]*?)'
            rf'<MacroControlIndex Value="{macro_idx}" />'
            rf'([\s\S]*?</PluginParameterSettings>)'
        )

    # First, find the match
    match = re.search(pattern, xml_content)
    if not match:
        print(f'⚠ Warning: No parameter found mapped to Macro {macro_idx + 1}')
        return xml_content

    # Get the full PluginParameterSettings block
    param_block = match.group(0)

    # Extract parameter ID for logging
    param_id_match = re.search(r'<ParameterId Value="(\d+)" />', param_block)
    if param_id_match:
        found_param_id = param_id_match.group(1)
        print(f'✓ Found Parameter ID {found_param_id} mapped to Macro {macro_idx + 1}')

    # Replace MacroControlIndex
    param_block_modified = re.sub(
        rf'<MacroControlIndex Value="{macro_idx}" />',
        '<MacroControlIndex Value="-1" />',
        param_block
    )

    # Replace the MidiControllerRange section (which has nested structure)
    # Original: <MidiControllerRange><MidiControllerRange Id="0">...</></MidiControllerRange>
    # New: <MidiControllerRange />
    param_block_modified = re.sub(
        r'<MidiControllerRange>\s*<MidiControllerRange Id="0">.*?</MidiControllerRange>\s*</MidiControllerRange>',
        '<MidiControllerRange />',
        param_block_modified,
        flags=re.DOTALL
    )

    # Replace in the full XML
    xml_content = xml_content.replace(param_block, param_block_modified)
    print(f'✓ Unmapped Parameter ID {found_param_id} from Macro {macro_idx + 1}')

    return xml_content


def main():
    if len(sys.argv) < 4:
        print('Usage: python3 step1_remove_macro_mapping.py <input.adg> <output.adg> <macro_index>')
        print('  macro_index: 0-15 (0 = Macro 1, 15 = Macro 16)')
        print('')
        print('Example: python3 step1_remove_macro_mapping.py input.adg output.adg 15')
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    macro_idx = int(sys.argv[3])

    if not input_path.exists():
        print(f'Error: Input file not found: {input_path}')
        return 1

    if macro_idx < 0 or macro_idx > 15:
        print(f'Error: Macro index must be 0-15, got {macro_idx}')
        return 1

    print(f'Removing Macro {macro_idx + 1} mapping from {input_path.name}')
    print('=' * 70)

    # Decode
    xml = decode_adg(input_path)
    print(f'Decoded: {len(xml):,} chars')

    # Remove mapping
    modified = remove_macro_mapping(xml, macro_idx)

    # Encode
    encode_adg(modified, output_path)
    print(f'\n✓ Created: {output_path}')
    print(f'Size: {len(modified):,} chars (change: {len(modified) - len(xml):+,})')

    return 0


if __name__ == '__main__':
    sys.exit(main())
