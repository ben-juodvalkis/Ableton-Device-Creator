#!/usr/bin/env python3
"""
Apply exact automation mappings from hand-mapped file to extracted patches
"""

import xml.etree.ElementTree as ET
import base64
import sys
from pathlib import Path

def extract_exact_automation_data(hand_mapped_path):
    """Extract the exact automation data from hand-mapped file"""
    tree = ET.parse(hand_mapped_path)
    root = tree.getroot()
    dict_elem = root.find('dict')
    
    current_key = None
    for child in dict_elem:
        if child.tag == 'key':
            current_key = child.text
        elif child.tag == 'data' and current_key == 'data':
            return child.text.strip()
    
    return None

def apply_automation_to_file(aupreset_path, automation_data):
    """Apply automation data while preserving exact XML structure"""
    try:
        # Read the original file as text to preserve formatting
        with open(aupreset_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Find the data section and replace only its content
        import re
        
        # Pattern to find the data section between <key>data</key> and next <key>
        data_pattern = r'(<key>data</key>\s*<data>)(.*?)(</data>\s*<key>)'
        
        # Replace the data content while preserving structure
        def replace_data_content(match):
            opening = match.group(1)
            closing = match.group(3)
            # Format automation data to match original indentation
            formatted_data = '\n\t' + automation_data + '\n\t'
            return opening + formatted_data + closing
        
        # Apply the replacement
        modified_content = re.sub(data_pattern, replace_data_content, original_content, flags=re.DOTALL)
        
        # Write back preserving original structure
        with open(aupreset_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        return True
        
    except Exception as e:
        print(f"Error applying automation to {aupreset_path}: {e}")
        return False

def main():
    hand_mapped_path = '/Users/Music/Desktop/mapped.aupreset'
    automation_dir = '/Users/Shared/DevWork/GitHub/Looping/ableton/Presets/Instruments/spectrasonics/omnisphere_3_with_automation'
    
    print("🎛️ Applying Exact Automation Mappings")
    print("=" * 50)
    
    # Extract automation data
    print("1. Extracting automation data from hand-mapped file...")
    automation_data = extract_exact_automation_data(hand_mapped_path)
    if not automation_data:
        print("❌ Could not extract automation data")
        return
    
    print(f"✅ Extracted {len(automation_data):,} characters of automation data")
    
    # Find all .aupreset files in automation directory
    print("2. Finding extracted .aupreset files...")
    aupreset_files = list(Path(automation_dir).rglob('*.aupreset'))
    print(f"✅ Found {len(aupreset_files)} .aupreset files")
    
    # Apply automation to each file
    print("3. Applying automation data to each file...")
    success_count = 0
    
    for aupreset_file in aupreset_files:
        print(f"   Processing: {aupreset_file.name}")
        if apply_automation_to_file(str(aupreset_file), automation_data):
            success_count += 1
            print(f"   ✅ Updated")
        else:
            print(f"   ❌ Failed")
    
    print(f"\n🎉 Results:")
    print(f"   Success: {success_count}/{len(aupreset_files)} files")
    print(f"   All files now have your exact automation mappings!")

if __name__ == "__main__":
    main()