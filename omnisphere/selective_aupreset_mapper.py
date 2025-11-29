#!/usr/bin/env python3
"""
Selective Omnisphere Aupreset Automation Mapper (v2)

Creates precise, targeted automation mappings similar to manual DAW parameter mapping.
Based on careful analysis of manual mapping patterns - maps only specific parameter instances.
"""

import base64
import xml.etree.ElementTree as ET
import re
import argparse
from pathlib import Path

class SelectiveAupresetMapper:
    """Selectively maps automation parameters to specific Omnisphere parameter instances"""
    
    def __init__(self):
        # Precise automation mapping configuration based on manual analysis
        self.automation_config = {
            # Single instance mappings
            'bypass': [
                {'device': 16, 'id': 6, 'channel': -1, 'instance': 1}  # Map 1st occurrence
            ],
            'attk': [
                {'device': 16, 'id': 0, 'channel': -1, 'instance': 1}  # Map 1st occurrence
            ],
            'rels': [
                {'device': 16, 'id': 1, 'channel': -1, 'instance': 1}  # Map 1st occurrence
            ],
            # Multiple instance mappings for linkvs
            'linkvs': [
                {'device': 16, 'id': 2, 'channel': -1, 'instance': 1},  # Map 1st occurrence
                {'device': 16, 'id': 3, 'channel': -1, 'instance': 2},  # Map 2nd occurrence  
                {'device': 16, 'id': 4, 'channel': -1, 'instance': 3},  # Map 3rd occurrence
                {'device': 16, 'id': 5, 'channel': -1, 'instance': 4}   # Map 4th occurrence
            ]
        }
        
    def extract_preset_data(self, aupreset_path):
        """Extract and decode the preset data from aupreset file"""
        try:
            tree = ET.parse(aupreset_path)
            root = tree.getroot()
            
            # Find data0 element
            dict_elem = root.find('dict')
            if dict_elem is None:
                raise ValueError("No dict element found in aupreset")
                
            data0_found = False
            
            for child in dict_elem:
                if child.tag == 'key' and child.text == 'data0':
                    data0_found = True
                elif data0_found and child.tag == 'data':
                    encoded_data = child.text.strip() if child.text else ""
                    if not encoded_data:
                        raise ValueError("Empty data0 element")
                    decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                    return decoded_data
            
            raise ValueError("No data0 element found in aupreset")
            
        except Exception as e:
            raise Exception(f"Error extracting preset data: {e}")
    
    def inject_selective_mappings(self, preset_xml_data):
        """Inject automation mappings to specific parameter instances only"""
        modified_data = preset_xml_data
        total_mappings = 0
        
        print(f"🎯 Applying selective automation mappings...")
        
        for param_name, mappings in self.automation_config.items():
            print(f"\n🔍 Processing parameter '{param_name}':")
            
            # Find all occurrences of this parameter
            pattern = f'{param_name}="[^"]*"'
            matches = list(re.finditer(pattern, modified_data))
            
            if not matches:
                print(f"  ⚠️  No occurrences found for '{param_name}'")
                continue
                
            print(f"  📊 Found {len(matches)} total occurrences")
            
            # Apply mappings to specific instances
            mappings_applied = 0
            offset = 0  # Track text length changes
            
            for mapping in mappings:
                instance = mapping['instance']
                device = mapping['device'] 
                param_id = mapping['id']
                channel = mapping['channel']
                
                if instance <= len(matches):
                    # Get the match for this instance (1-based indexing)
                    match = matches[instance - 1]
                    
                    # Calculate position with offset from previous injections
                    match_start = match.start() + offset
                    match_end = match.end() + offset
                    
                    # Get the original parameter text
                    original_param = modified_data[match_start:match_end]
                    
                    # Create the automation mapping injection
                    automation_injection = (
                        f' {param_name}MidiLearnDevice0="{device}" '
                        f'{param_name}MidiLearnIDnum0="{param_id}" '
                        f'{param_name}MidiLearnChannel0="{channel}"'
                    )
                    
                    # Insert automation mapping right after the parameter
                    modified_data = (
                        modified_data[:match_end] + 
                        automation_injection + 
                        modified_data[match_end:]
                    )
                    
                    # Update offset for next injection
                    offset += len(automation_injection)
                    mappings_applied += 1
                    total_mappings += 1
                    
                    print(f"  ✅ Instance {instance}: Mapped to Device {device}, ID {param_id}")
                    
                else:
                    print(f"  ⚠️  Instance {instance}: Not found (only {len(matches)} occurrences exist)")
            
            print(f"  📈 Applied {mappings_applied}/{len(mappings)} mappings for '{param_name}'")
        
        print(f"\n🎛️  Total mappings applied: {total_mappings}")
        return modified_data
    
    def save_mapped_preset(self, original_path, modified_xml_data, output_path=None):
        """Save the modified preset data back to an aupreset file"""
        
        # Parse original file to get structure
        tree = ET.parse(original_path)
        root = tree.getroot()
        
        # Find and update the data0 element
        dict_elem = root.find('dict')
        data0_found = False
        
        for child in dict_elem:
            if child.tag == 'key' and child.text == 'data0':
                data0_found = True
            elif data0_found and child.tag == 'data':
                # Encode the modified XML data
                encoded_data = base64.b64encode(modified_xml_data.encode('utf-8')).decode('ascii')
                child.text = encoded_data
                break
        
        # Generate output path if not provided
        if output_path is None:
            original_path_obj = Path(original_path)
            output_path = original_path_obj.parent / f"{original_path_obj.stem} selective mapped{original_path_obj.suffix}"
        
        # Save the modified file
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        print(f"💾 Saved selectively mapped preset: {output_path}")
        
        return output_path
    
    def map_preset(self, input_path, output_path=None):
        """Main method to selectively map automation parameters"""
        
        print(f"🔄 Processing aupreset with selective mapping: {input_path}")
        
        # Extract preset data
        try:
            preset_xml_data = self.extract_preset_data(input_path)
            print(f"📊 Extracted {len(preset_xml_data):,} characters of preset data")
        except Exception as e:
            print(f"❌ Failed to extract preset data: {e}")
            return None
        
        # Check if already mapped
        if "MidiLearnDevice" in preset_xml_data:
            print("⚠️  Preset appears to already have automation mappings")
            print("   Proceeding anyway - may result in duplicate mappings")
        
        # Apply selective automation mappings
        try:
            mapped_xml_data = self.inject_selective_mappings(preset_xml_data)
            
            # Calculate size difference
            size_diff = len(mapped_xml_data) - len(preset_xml_data)
            print(f"📈 Added {size_diff} characters of automation data")
            
        except Exception as e:
            print(f"❌ Failed to inject mappings: {e}")
            return None
        
        # Save mapped preset
        try:
            output_file = self.save_mapped_preset(input_path, mapped_xml_data, output_path)
            return output_file
        except Exception as e:
            print(f"❌ Failed to save mapped preset: {e}")
            return None
    
    def verify_mapping_accuracy(self, original_path, mapped_path):
        """Verify that the mapping matches expected pattern"""
        try:
            mapped_data = self.extract_preset_data(mapped_path)
            
            # Count mappings created
            automation_pattern = r'(\w+)MidiLearnDevice\d+="(\d+)"\s+\1MidiLearnIDnum\d+="(\d+)"'
            mappings = re.findall(automation_pattern, mapped_data)
            
            print(f"\n🔍 VERIFICATION:")
            print(f"  Expected mappings: 7 (1 bypass, 1 attk, 1 rels, 4 linkvs)")
            print(f"  Actual mappings:   {len(mappings)}")
            
            if len(mappings) == 7:
                print("  ✅ Mapping count matches expected pattern!")
                
                # Verify specific mappings
                mapping_dict = {}
                for param, device, idnum in mappings:
                    if param not in mapping_dict:
                        mapping_dict[param] = []
                    mapping_dict[param].append((device, idnum))
                
                print(f"\n  📊 Mapping breakdown:")
                for param, param_mappings in mapping_dict.items():
                    print(f"    {param}: {len(param_mappings)} mapping(s)")
                    for device, idnum in param_mappings:
                        print(f"      → Device {device}, ID {idnum}")
                        
                return True
            else:
                print("  ⚠️  Mapping count doesn't match expected pattern")
                return False
                
        except Exception as e:
            print(f"  ❌ Verification failed: {e}")
            return False

def main():
    """Command line interface for selective mapping"""
    
    parser = argparse.ArgumentParser(
        description="Selectively add host automation mappings to Omnisphere aupreset files"
    )
    parser.add_argument('input', help='Input aupreset file')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('--verify', action='store_true', help='Verify mapping accuracy after creation')
    
    args = parser.parse_args()
    
    print("🎯 Selective Omnisphere Aupreset Automation Mapper v2")
    print("=" * 65)
    print("Based on careful analysis of manual DAW parameter mapping patterns")
    print()
    
    mapper = SelectiveAupresetMapper()
    
    print(f"📄 Processing file: {args.input}")
    result = mapper.map_preset(args.input, args.output)
    
    if result:
        print(f"\n🎉 Selective mapping complete!")
        print(f"   Output: {result}")
        
        if args.verify:
            print(f"\n🔍 Running verification...")
            mapper.verify_mapping_accuracy(args.input, result)
    else:
        print(f"\n❌ Selective mapping failed")

if __name__ == "__main__":
    main()