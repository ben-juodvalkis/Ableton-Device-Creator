#!/usr/bin/env python3
"""
Step 4: Set Macro 16 value to 63 (center position).
"""

import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'utils'))
from decoder import decode_adg
from encoder import encode_adg


def set_macro_value(xml_content: str, macro_idx: int = 15, value: int = 63) -> str:
    """
    Set the Manual value for a specific macro.

    Args:
        xml_content: Decoded .adg XML
        macro_idx: Macro index (0-15)
        value: Value to set (0-127)

    Returns:
        Modified XML
    """

    # Pattern: Find MacroControls.{macro_idx} and change its Manual value
    pattern = rf'(<MacroControls\.{macro_idx}>[\s\S]*?<Manual Value=")([^"]+)(")'

    # Check current value
    current = re.search(pattern, xml_content)
    if current:
        current_val = current.group(2)
        print(f'Current Macro {macro_idx + 1} value: {current_val}')
    else:
        print(f'⚠ Warning: Could not find MacroControls.{macro_idx}')
        return xml_content

    # Replace with new value
    modified = re.sub(pattern, rf'\g<1>{value}\3', xml_content, count=1)

    if modified == xml_content:
        print(f'⚠ No change made')
        return xml_content

    print(f'✓ Set Macro {macro_idx + 1} value: {current_val} → {value}')

    return modified


def main():
    if len(sys.argv) < 3:
        print('Usage: python3 step4_set_macro_value.py <input.adg> <output.adg> [value]')
        print('')
        print('Example:')
        print('  python3 step4_set_macro_value.py "step 3.adg" "step 4.adg" 63')
        print('')
        print('Default value: 63 (center position for 0-127 range)')
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    value = int(sys.argv[3]) if len(sys.argv) > 3 else 63

    if not input_path.exists():
        print(f'Error: Input not found: {input_path}')
        return 1

    if value < 0 or value > 127:
        print(f'Error: Value must be 0-127, got {value}')
        return 1

    print(f'Setting Macro 16 value to {value} in: {input_path.name}')
    print('=' * 70)

    # Decode
    xml = decode_adg(input_path)
    print(f'Input size: {len(xml):,} chars')

    # Set macro value
    modified = set_macro_value(xml, macro_idx=15, value=value)

    # Encode
    encode_adg(modified, output_path)

    print(f'Output size: {len(modified):,} chars')
    print(f'Change: {len(modified) - len(xml):+,} chars')
    print(f'\n✓ Created: {output_path}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
