#!/usr/bin/env python3
"""
Compare Omnisphere presets with Orb ON vs Orb ON + Automation Mappings
to identify the automation mapping data for Orb radius and angle
"""

import base64
import xml.etree.ElementTree as ET
import re

def extract_preset_data(aupreset_path):
    """Extract both host automation data and Omnisphere XML data"""
    try:
        tree = ET.parse(aupreset_path)
        root = tree.getroot()
        dict_elem = root.find('dict')
        
        preset_data = {
            'host_automation': None,
            'omnisphere_xml': None
        }
        
        current_key = None
        for child in dict_elem:
            if child.tag == 'key':
                current_key = child.text
            elif child.tag == 'data':
                if current_key == 'data':
                    # Host automation data
                    encoded_data = child.text.strip() if child.text else ""
                    if encoded_data:
                        preset_data['host_automation'] = base64.b64decode(encoded_data)
                elif current_key == 'data0':
                    # Omnisphere XML data
                    encoded_data = child.text.strip() if child.text else ""
                    if encoded_data:
                        preset_data['omnisphere_xml'] = base64.b64decode(encoded_data).decode('utf-8')
        
        return preset_data
        
    except Exception as e:
        print(f"Error reading {aupreset_path}: {e}")
        return None

def find_automation_differences(data1, data2):
    """Find differences in host automation data"""
    if not data1['host_automation'] or not data2['host_automation']:
        return "Missing automation data"
    
    auto1 = data1['host_automation']
    auto2 = data2['host_automation']
    
    print(f"  Host automation sizes:")
    print(f"    Orb ON (no mapping):  {len(auto1):,} bytes")
    print(f"    Orb ON (with mapping): {len(auto2):,} bytes")
    print(f"    Difference:           {len(auto2) - len(auto1):,} bytes")
    
    return len(auto2) - len(auto1)

def find_midi_learn_differences(xml1, xml2):
    """Find MIDI Learn mapping differences in Omnisphere XML"""
    if not xml1 or not xml2:
        return []
    
    # Find MIDI Learn patterns
    ml_pattern = r'(\w+)MidiLearnDevice(\d+)="(\d+)"\s+\1MidiLearnIDnum\2="(\d+)"(?:\s+\1MidiLearnChannel\2="([^"]+)")?'
    
    ml1_matches = re.findall(ml_pattern, xml1)
    ml2_matches = re.findall(ml_pattern, xml2)
    
    print(f"  MIDI Learn mappings:")
    print(f"    Orb ON (no mapping):   {len(ml1_matches)} mappings")
    print(f"    Orb ON (with mapping): {len(ml2_matches)} mappings")
    
    # Convert to sets for comparison
    ml1_set = set(ml1_matches)
    ml2_set = set(ml2_matches)
    
    new_mappings = ml2_set - ml1_set
    removed_mappings = ml1_set - ml2_set
    
    return {
        'new_mappings': list(new_mappings),
        'removed_mappings': list(removed_mappings),
        'total_ml1': len(ml1_matches),
        'total_ml2': len(ml2_matches)
    }

def find_orb_related_changes(xml1, xml2):
    """Find Orb-specific parameter changes"""
    orb_keywords = ['orb', 'Orb', 'radius', 'angle', 'Radius', 'Angle']
    
    changes = {}
    for keyword in orb_keywords:
        count1 = xml1.count(keyword) if xml1 else 0
        count2 = xml2.count(keyword) if xml2 else 0
        
        if count1 != count2:
            changes[keyword] = {'before': count1, 'after': count2}
    
    return changes

def compare_orb_automation():
    """Compare Orb ON vs Orb ON + Automation"""
    
    # File paths
    orb_on_file = "/Users/Music/Desktop/omni orb on.aupreset"
    orb_mapped_file = "/Users/Music/Desktop/omni orb mapped.aupreset"
    
    print("🔍 Comparing Orb Automation Mappings")
    print("=" * 70)
    print(f"Orb ON (no mapping):   {orb_on_file}")
    print(f"Orb ON (with mapping): {orb_mapped_file}")
    print()
    
    # Extract data from both files
    print("Extracting preset data...")
    orb_on_data = extract_preset_data(orb_on_file)
    orb_mapped_data = extract_preset_data(orb_mapped_file)
    
    if not orb_on_data:
        print(f"❌ Could not extract data from Orb ON file")
        return
    
    if not orb_mapped_data:
        print(f"❌ Could not extract data from Orb Mapped file")
        return
    
    print(f"✅ Both files extracted successfully")
    
    # Compare host automation data
    print(f"\n📊 Host Automation Data Comparison:")
    auto_diff = find_automation_differences(orb_on_data, orb_mapped_data)
    
    # Compare MIDI Learn mappings
    print(f"\n🎛️ MIDI Learn Mapping Comparison:")
    ml_diff = find_midi_learn_differences(orb_on_data['omnisphere_xml'], orb_mapped_data['omnisphere_xml'])
    
    if ml_diff['new_mappings']:
        print(f"\n✨ NEW Automation Mappings (added for Orb):")
        for param, slot, device, idnum, channel in ml_diff['new_mappings']:
            print(f"    {param}[{slot}] → Device: {device}, ID: {idnum}")
            if channel:
                print(f"                     Channel: {channel}")
    
    if ml_diff['removed_mappings']:
        print(f"\n❌ REMOVED Mappings:")
        for param, slot, device, idnum, channel in ml_diff['removed_mappings']:
            print(f"    {param}[{slot}] → Device: {device}, ID: {idnum}")
    
    # Look for Orb-related parameter changes
    print(f"\n🎯 Orb-Related Parameter Changes:")
    orb_changes = find_orb_related_changes(orb_on_data['omnisphere_xml'], orb_mapped_data['omnisphere_xml'])
    
    if orb_changes:
        for keyword, change in orb_changes.items():
            print(f"    '{keyword}': {change['before']} → {change['after']}")
    else:
        print("    No Orb-related keyword changes found")
    
    # Save XML files for detailed comparison
    with open('/tmp/orb_on_only.xml', 'w') as f:
        f.write(orb_on_data['omnisphere_xml'] or "")
    with open('/tmp/orb_mapped.xml', 'w') as f:
        f.write(orb_mapped_data['omnisphere_xml'] or "")
    
    print(f"\n💾 Saved XML files for detailed comparison:")
    print(f"  Orb ON only: /tmp/orb_on_only.xml")
    print(f"  Orb Mapped:  /tmp/orb_mapped.xml")
    print(f"\n  Use: diff /tmp/orb_on_only.xml /tmp/orb_mapped.xml | head -20")
    
    # Generate automation template code if new mappings found
    if ml_diff['new_mappings']:
        print(f"\n🤖 Suggested Template Enhancement:")
        print(f"Add these MIDI Learn mappings to your working template:")
        
        for param, slot, device, idnum, channel in ml_diff['new_mappings']:
            print(f"  {param}MidiLearnDevice{slot}=\"{device}\" {param}MidiLearnIDnum{slot}=\"{idnum}\"", end="")
            if channel:
                print(f" {param}MidiLearnChannel{slot}=\"{channel}\"")
            else:
                print()

if __name__ == "__main__":
    compare_orb_automation()