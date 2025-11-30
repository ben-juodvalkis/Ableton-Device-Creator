#!/usr/bin/env python3
"""
Step 3: Add macro mapping from CC Control Custom E to Macro 16.

Injects a KeyMidi element into CustomFloatValues.3 to map:
- Custom E (CC Control parameter slot 3)
- To Macro 16 (NoteOrController = 15, 0-indexed)
- Via MIDI Channel 16
"""

import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'utils'))
from decoder import decode_adg
from encoder import encode_adg


def add_macro_mapping(xml_content: str, slot: int = 3, macro_idx: int = 15) -> str:
    """
    Add KeyMidi mapping from CC Control parameter to drum rack macro.

    Args:
        xml_content: Decoded .adg XML
        slot: CC Control CustomFloatValues slot (0-11)
        macro_idx: Drum rack macro index (0-15)

    Returns:
        Modified XML
    """

    # Check if already has KeyMidi in this slot
    if re.search(rf'<CustomFloatValues\.{slot}>.*?<KeyMidi>', xml_content, re.DOTALL):
        print(f'⚠ CustomFloatValues.{slot} already has KeyMidi mapping, skipping')
        return xml_content

    # Build the KeyMidi block
    key_midi_block = f'''<KeyMidi>
										<PersistentKeyString Value="" />
										<IsNote Value="false" />
										<Channel Value="16" />
										<NoteOrController Value="{macro_idx}" />
										<LowerRangeNote Value="-1" />
										<UpperRangeNote Value="-1" />
										<ControllerMapMode Value="0" />
									</KeyMidi>
									'''

    # Pattern: Find CustomFloatValues.{slot} and inject KeyMidi after LomId
    pattern = rf'(<CustomFloatValues\.{slot}>\s+<LomId Value="0" />)'
    replacement = rf'\1\n\t\t\t\t\t\t\t\t\t{key_midi_block}'

    modified = re.sub(pattern, replacement, xml_content, count=1)

    if modified == xml_content:
        print(f'⚠ Warning: Could not find CustomFloatValues.{slot} to inject KeyMidi')
        return xml_content

    custom_letter = 'BCDEFGHIJKLM'[slot] if slot < 12 else '?'
    print(f'✓ Added KeyMidi: Custom {custom_letter} (slot {slot}) → Macro {macro_idx + 1}')

    return modified


def main():
    if len(sys.argv) < 3:
        print('Usage: python3 step3_add_macro_mapping.py <input.adg> <output.adg>')
        print('')
        print('Example:')
        print('  python3 step3_add_macro_mapping.py "step 2.adg" "step 3.adg"')
        print('')
        print('Maps CC Control Custom E (slot 3) to Macro 16 (index 15)')
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f'Error: Input not found: {input_path}')
        return 1

    print(f'Adding macro mapping to: {input_path.name}')
    print('=' * 70)

    # Decode
    xml = decode_adg(input_path)
    print(f'Input size: {len(xml):,} chars')

    # Add KeyMidi mapping (Custom E → Macro 16)
    modified = add_macro_mapping(xml, slot=3, macro_idx=15)

    # Encode
    encode_adg(modified, output_path)

    print(f'Output size: {len(modified):,} chars')
    print(f'Change: {len(modified) - len(xml):+,} chars')
    print(f'\n✓ Created: {output_path}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
