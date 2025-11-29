#!/usr/bin/env python3
"""
Analyze host automation data differences for Orb radius/angle mappings
"""

import base64
import xml.etree.ElementTree as ET

def extract_host_automation(aupreset_path):
    """Extract host automation data from AU preset"""
    try:
        tree = ET.parse(aupreset_path)
        root = tree.getroot()
        dict_elem = root.find('dict')
        
        current_key = None
        for child in dict_elem:
            if child.tag == 'key':
                current_key = child.text
            elif child.tag == 'data' and current_key == 'data':
                encoded_data = child.text.strip() if child.text else ""
                if encoded_data:
                    return base64.b64decode(encoded_data)
        
        return None
        
    except Exception as e:
        print(f"Error reading {aupreset_path}: {e}")
        return None

def analyze_automation_data(data1, data2):
    """Analyze differences in binary automation data"""
    if not data1 or not data2:
        print("Missing automation data")
        return
    
    print(f"Automation data sizes:")
    print(f"  Orb ON (no mapping):   {len(data1):,} bytes")
    print(f"  Orb ON (with mapping): {len(data2):,} bytes") 
    print(f"  Difference:            {len(data2) - len(data1):,} bytes")
    
    if len(data1) == len(data2):
        # Same size, find byte differences
        differences = []
        for i, (b1, b2) in enumerate(zip(data1, data2)):
            if b1 != b2:
                differences.append((i, b1, b2))
        
        print(f"\nByte differences: {len(differences)}")
        if differences:
            print("First 20 differences:")
            for i, (pos, b1, b2) in enumerate(differences[:20]):
                print(f"  Position {pos}: {b1:02x} → {b2:02x}")
    else:
        # Different sizes, likely additional data
        min_len = min(len(data1), len(data2))
        
        # Check if the beginning is the same
        same_prefix = True
        diff_start = 0
        for i in range(min_len):
            if data1[i] != data2[i]:
                same_prefix = False
                diff_start = i
                break
        
        if same_prefix:
            print(f"First {min_len} bytes are identical")
            if len(data2) > len(data1):
                extra_data = data2[len(data1):]
                print(f"Extra data in mapped version: {len(extra_data)} bytes")
                print(f"Extra data (hex): {extra_data[:50].hex()}")
        else:
            print(f"Data differs starting at position {diff_start}")

def save_automation_data(data, filename):
    """Save automation data for analysis"""
    if data:
        with open(filename, 'wb') as f:
            f.write(data)
        print(f"Saved: {filename}")

def main():
    print("🔍 Analyzing Host Automation Data for Orb Mappings")
    print("=" * 60)
    
    # File paths
    orb_on_file = "/Users/Music/Desktop/omni orb on.aupreset"
    orb_mapped_file = "/Users/Music/Desktop/omni orb mapped.aupreset"
    
    print(f"Extracting host automation data...")
    auto1 = extract_host_automation(orb_on_file)
    auto2 = extract_host_automation(orb_mapped_file)
    
    if not auto1:
        print(f"❌ No automation data in {orb_on_file}")
        return
        
    if not auto2:
        print(f"❌ No automation data in {orb_mapped_file}")
        return
    
    print(f"✅ Extracted automation data from both files")
    
    # Analyze differences
    print(f"\n📊 Automation Data Analysis:")
    analyze_automation_data(auto1, auto2)
    
    # Save for external analysis
    print(f"\n💾 Saving automation data for analysis:")
    save_automation_data(auto1, '/tmp/orb_on_automation.bin')
    save_automation_data(auto2, '/tmp/orb_mapped_automation.bin')
    
    print(f"\nUse hexdump to compare:")
    print(f"  hexdump -C /tmp/orb_on_automation.bin | head -20")
    print(f"  hexdump -C /tmp/orb_mapped_automation.bin | head -20")
    print(f"  diff <(hexdump -C /tmp/orb_on_automation.bin) <(hexdump -C /tmp/orb_mapped_automation.bin)")

if __name__ == "__main__":
    main()