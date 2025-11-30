#!/usr/bin/env python3
"""
Simple test script to set drum rack macro values
"""

import gzip
import re
from pathlib import Path

def extract_adg_to_xml(adg_path):
    """Extract .adg file to XML string"""
    with gzip.open(adg_path, 'rb') as f:
        return f.read().decode('utf-8')

def compress_xml_to_adg(xml_content, adg_path):
    """Compress XML string to .adg file"""
    with gzip.open(adg_path, 'wb', compresslevel=6) as f:
        f.write(xml_content.encode('utf-8'))

def set_macro_values(xml_content, macro_values):
    """
    Set macro Manual values

    Args:
        xml_content: The drum rack XML
        macro_values: List of 16 values (0-127 range)
    """

    for i, value in enumerate(macro_values):
        # Find the MacroControls.N section and replace the Manual value
        # Simple approach: find the line and replace it directly

        # Pattern to match: <Manual Value="anything" /> within a MacroControls.N block
        # We'll find the MacroControls.N block and replace its Manual value line

        # First, find the entire MacroControls.N section
        macro_section_pattern = f'<MacroControls\\.{i}>(.*?)</MacroControls\\.{i}>'
        match = re.search(macro_section_pattern, xml_content, flags=re.DOTALL)

        if match:
            old_section = match.group(0)
            # Within this section, replace the Manual value
            new_section = re.sub(
                r'<Manual Value="[^"]*" />',
                f'<Manual Value="{value}" />',
                old_section
            )
            xml_content = xml_content.replace(old_section, new_section)
            print(f"  ✓ Set Macro {i+1} to {value}")
        else:
            print(f"  ✗ Could not find MacroControls.{i}")

    return xml_content

# Test
input_file = '/Users/Shared/DevWork/GitHub/Looping/temp/drum orig.adg'
output_file = '/Users/Shared/DevWork/GitHub/Looping/temp/drum_test_macros.adg'

print("Testing macro value setting...")
print(f"Input: {input_file}")
print(f"Output: {output_file}\n")

# Test values (scaled 0-127): macros 7,8,9,13 should be non-zero
test_values = [0, 0, 0, 0, 0, 0, 63.5, 63.5, 127, 0, 0, 0, 127, 0, 0, 0]

xml = extract_adg_to_xml(input_file)
modified = set_macro_values(xml, test_values)
compress_xml_to_adg(modified, output_file)

print(f"\n✅ Created {output_file}")
print("Load in Ableton and check if macros 7, 8, 9, 13 are set correctly")
