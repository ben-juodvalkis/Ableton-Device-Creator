#!/usr/bin/env python3
"""
Verify batch processing output by checking for automation mappings in processed files
"""

import base64
import xml.etree.ElementTree as ET
import re
from pathlib import Path

def extract_preset_data(filename):
    """Extract and decode data from AU preset file"""
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
        
        # Find data0 element
        dict_elem = root.find('dict')
        data0_found = False
        
        for child in dict_elem:
            if child.tag == 'key' and child.text == 'data0':
                data0_found = True
            elif data0_found and child.tag == 'data':
                encoded_data = child.text.strip() if child.text else ""
                decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                return decoded_data
        
        return None
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return None

def analyze_mappings(preset_data):
    """Analyze automation mappings in preset data"""
    if not preset_data:
        return {}
    
    results = {
        'total_mappings': 0,
        'mappings': [],
        'has_linkvs': False,
        'envelope_contexts': []
    }
    
    # Find automation mappings
    automation_pattern = r'(\w+)MidiLearnDevice(\d+)="(\d+)"\s+\1MidiLearnIDnum\2="(\d+)"(?:\s+\1MidiLearnChannel\2="([^"]+)")?'
    mappings = re.findall(automation_pattern, preset_data)
    
    results['total_mappings'] = len(mappings)
    results['mappings'] = mappings
    
    # Check for linkvs mappings
    if any('linkvs' in mapping[0] for mapping in mappings):
        results['has_linkvs'] = True
    
    # Check envelope contexts
    for match in re.finditer(r'(attk|rels)MidiLearnDevice0', preset_data):
        start = max(0, match.start() - 200)
        end = min(len(preset_data), match.end() + 100)
        context = preset_data[start:end]
        
        if 'AENVPARAMS' in context.upper():
            results['envelope_contexts'].append(f"{match.group(1)}: AMP envelope ✅")
        elif 'FENVPARAMS' in context.upper():
            results['envelope_contexts'].append(f"{match.group(1)}: FILTER envelope ❌")
        else:
            results['envelope_contexts'].append(f"{match.group(1)}: Unknown context ❓")
    
    return results

def main():
    print("🔍 BATCH OUTPUT VERIFICATION")
    print("=" * 50)
    
    # Find some "safe mapped" files to verify
    base_dir = Path("/Users/Music/Desktop")
    mapped_files = list(base_dir.rglob("*safe mapped*.aupreset"))
    
    if not mapped_files:
        print("❌ No 'safe mapped' files found in /Users/Music/Desktop")
        print("Looking for any mapped aupreset files...")
        mapped_files = list(base_dir.rglob("*mapped*.aupreset"))
    
    if not mapped_files:
        print("❌ No mapped files found at all")
        return
    
    print(f"📁 Found {len(mapped_files)} mapped files to verify")
    
    # Analyze first few files
    for i, file_path in enumerate(mapped_files[:5]):
        print(f"\n{'='*60}")
        print(f"📄 Analyzing file {i+1}: {file_path.name}")
        print(f"   Full path: {file_path}")
        
        preset_data = extract_preset_data(file_path)
        results = analyze_mappings(preset_data)
        
        print(f"   📊 Total automation mappings: {results['total_mappings']}")
        
        if results['total_mappings'] == 0:
            print("   ❌ NO AUTOMATION MAPPINGS FOUND!")
            print("   This suggests the batch processing failed for this file")
        elif results['total_mappings'] == 7:
            print("   ✅ Expected 7 mappings found")
        else:
            print(f"   ⚠️  Unexpected mapping count: {results['total_mappings']}")
        
        if results['mappings']:
            print("   🎛️  Automation mappings:")
            for param, slot, device, idnum, channel in results['mappings']:
                print(f"      {param}[{slot}] → Device: {device}, ID: {idnum}")
        
        if results['has_linkvs']:
            print("   🔗 Has linkvs layer linking")
        
        if results['envelope_contexts']:
            print("   📈 Envelope contexts:")
            for context in results['envelope_contexts']:
                print(f"      {context}")
    
    print(f"\n🏁 Verification complete")

if __name__ == "__main__":
    main()