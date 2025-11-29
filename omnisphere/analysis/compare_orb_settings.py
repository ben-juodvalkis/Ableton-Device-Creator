#!/usr/bin/env python3
"""
Compare Omnisphere presets with Orb OFF vs Orb ON
to identify the hex values that control the Orb setting
"""

import base64
import xml.etree.ElementTree as ET
import re

def extract_preset_xml(aupreset_path):
    """Extract and decode XML from .aupreset file"""
    try:
        tree = ET.parse(aupreset_path)
        root = tree.getroot()
        dict_elem = root.find('dict')
        data0_found = False
        
        for child in dict_elem:
            if child.tag == 'key' and child.text == 'data0':
                data0_found = True
            elif data0_found and child.tag == 'data':
                encoded_data = child.text.strip() if child.text else ""
                if encoded_data:
                    decoded_xml = base64.b64decode(encoded_data).decode('utf-8')
                    return decoded_xml
                else:
                    print(f"Warning: Empty data in {aupreset_path}")
                    return None
        
        print(f"Error: No data0 found in {aupreset_path}")
        return None
        
    except Exception as e:
        print(f"Error reading {aupreset_path}: {e}")
        return None

def find_hex_differences(xml1, xml2, context_chars=50):
    """Find hex pattern differences between two XML strings"""
    differences = []
    
    # Find all hex patterns (e.g., attr="3d23d70a")
    hex_pattern = r'(\w+)="([0-9a-fA-F]{8})"'
    
    matches1 = {match.group(1): match.group(2) for match in re.finditer(hex_pattern, xml1)}
    matches2 = {match.group(1): match.group(2) for match in re.finditer(hex_pattern, xml2)}
    
    # Find differing attributes
    all_attrs = set(matches1.keys()) | set(matches2.keys())
    
    for attr in sorted(all_attrs):
        val1 = matches1.get(attr, 'MISSING')
        val2 = matches2.get(attr, 'MISSING')
        
        if val1 != val2:
            differences.append({
                'attribute': attr,
                'orb_off_value': val1,
                'orb_on_value': val2
            })
    
    return differences

def compare_orb_presets():
    """Compare Orb OFF vs Orb ON presets"""
    
    # File paths
    orb_off_preset = "/Users/Music/Desktop/omni original.aupreset"
    orb_on_preset = "/Users/Music/Desktop/omni orb on.aupreset"
    
    print("🔍 Comparing Omnisphere Orb Settings")
    print("=" * 60)
    print(f"Orb OFF: {orb_off_preset}")
    print(f"Orb ON:  {orb_on_preset}")
    print()
    
    # Extract XML from both files
    print("Extracting XML content...")
    orb_off_xml = extract_preset_xml(orb_off_preset)
    orb_on_xml = extract_preset_xml(orb_on_preset)
    
    if not orb_off_xml:
        print(f"❌ Could not extract XML from Orb OFF preset")
        return
    
    if not orb_on_xml:
        print(f"❌ Could not extract XML from Orb ON preset")
        return
    
    print(f"✅ Both files extracted successfully")
    
    # Basic comparison
    print(f"\n📏 Size Comparison:")
    print(f"  Orb OFF XML:  {len(orb_off_xml):,} characters")
    print(f"  Orb ON XML:   {len(orb_on_xml):,} characters")
    print(f"  Difference:   {len(orb_on_xml) - len(orb_off_xml):,} characters")
    
    # Check if identical
    if orb_off_xml == orb_on_xml:
        print(f"\n❌ XML Content is IDENTICAL - no Orb differences found!")
        return
    else:
        print(f"\n✅ XML Content DIFFERS - analyzing differences...")
    
    # Find hex differences
    print(f"\n🔍 Analyzing Hex Pattern Differences:")
    differences = find_hex_differences(orb_off_xml, orb_on_xml)
    
    if not differences:
        print("  No hex pattern differences found")
    else:
        print(f"  Found {len(differences)} hex differences:")
        for diff in differences:
            print(f"    {diff['attribute']}:")
            print(f"      Orb OFF: {diff['orb_off_value']}")
            print(f"      Orb ON:  {diff['orb_on_value']}")
    
    # Look for Orb-specific patterns
    print(f"\n🎛️ Searching for Orb-related Patterns:")
    
    orb_keywords = ['orb', 'Orb', 'ORB', 'modwheel', 'ModWheel', 'wheel', 'Wheel']
    
    for keyword in orb_keywords:
        orb_off_count = orb_off_xml.count(keyword)
        orb_on_count = orb_on_xml.count(keyword)
        
        if orb_off_count != orb_on_count:
            print(f"  '{keyword}': OFF={orb_off_count}, ON={orb_on_count} (DIFF!)")
        elif orb_off_count > 0:
            print(f"  '{keyword}': {orb_off_count} occurrences (same in both)")
    
    # Extract pitch bend values for reference
    print(f"\n🎯 Pitch Bend Reference (for comparison):")
    pb_pattern = r'(pbup|pbdn)="([0-9a-fA-F]{8})"'
    
    pb_off_matches = re.findall(pb_pattern, orb_off_xml)
    pb_on_matches = re.findall(pb_pattern, orb_on_xml)
    
    for param, value in pb_off_matches:
        print(f"  Orb OFF {param}: {value}")
    
    for param, value in pb_on_matches:
        print(f"  Orb ON {param}:  {value}")
    
    # Save XML files for manual inspection
    with open('/tmp/orb_off.xml', 'w') as f:
        f.write(orb_off_xml)
    with open('/tmp/orb_on.xml', 'w') as f:
        f.write(orb_on_xml)
    
    print(f"\n💾 Saved XML files for manual comparison:")
    print(f"  Orb OFF: /tmp/orb_off.xml")
    print(f"  Orb ON:  /tmp/orb_on.xml")
    print(f"\n  Use: diff /tmp/orb_off.xml /tmp/orb_on.xml | head -50")
    
    # Generate regex patterns for automation script
    if differences:
        print(f"\n🤖 Suggested Automation Script Patterns:")
        for diff in differences:
            if diff['orb_off_value'] != 'MISSING' and diff['orb_on_value'] != 'MISSING':
                print(f"  enhanced_engine = re.sub(r'{diff['attribute']}=\"{diff['orb_off_value']}\"', '{diff['attribute']}=\"{diff['orb_on_value']}\"', enhanced_engine)")

if __name__ == "__main__":
    compare_orb_presets()