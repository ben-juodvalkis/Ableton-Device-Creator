#!/usr/bin/env python3
"""
Omnisphere Aupreset Automation Mapper

Takes an unmapped aupreset file and adds host parameter automation mappings
to create a performance-ready version with consistent parameter exposure.
"""

import base64
import xml.etree.ElementTree as ET
import re
import argparse
from pathlib import Path

class AupresetAutomationMapper:
    """Maps host automation parameters to Omnisphere aupreset files"""
    
    def __init__(self):
        # Default automation mapping configuration
        self.automation_mappings = {
            'attk': {'device': 16, 'id': 0, 'channel': -1},
            'rels': {'device': 16, 'id': 1, 'channel': -1}, 
            'linkvs': {'device': 16, 'id': 2, 'channel': -1},
            'bypass': {'device': 16, 'id': 6, 'channel': -1}
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
                    return decoded_data, child  # Return both data and XML element
            
            raise ValueError("No data0 element found in aupreset")
            
        except Exception as e:
            raise Exception(f"Error extracting preset data: {e}")
    
    def inject_automation_mappings(self, preset_xml_data):
        """Inject automation mappings into the preset XML data"""
        modified_data = preset_xml_data
        
        print(f"🎛️  Injecting {len(self.automation_mappings)} automation mappings...")
        
        for param_name, mapping in self.automation_mappings.items():
            device = mapping['device']
            param_id = mapping['id']
            channel = mapping['channel']
            
            # Pattern to find the parameter and inject automation attributes
            pattern = f'({param_name}="[^"]*")'
            
            # Replacement adds the automation mapping attributes
            replacement = (
                f'\\1 {param_name}MidiLearnDevice0="{device}" '
                f'{param_name}MidiLearnIDnum0="{param_id}" '
                f'{param_name}MidiLearnChannel0="{channel}"'
            )
            
            # Count occurrences before replacement
            matches = re.findall(pattern, modified_data)
            if matches:
                modified_data = re.sub(pattern, replacement, modified_data)
                print(f"  ✅ {param_name}: {len(matches)} occurrences mapped to Device {device}, ID {param_id}")
            else:
                print(f"  ⚠️  {param_name}: No occurrences found")
        
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
            output_path = original_path_obj.parent / f"{original_path_obj.stem} mapped{original_path_obj.suffix}"
        
        # Save the modified file
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        print(f"💾 Saved mapped preset: {output_path}")
        
        return output_path
    
    def map_preset(self, input_path, output_path=None):
        """Main method to map automation parameters in an aupreset file"""
        
        print(f"🔄 Processing aupreset: {input_path}")
        
        # Extract preset data
        try:
            preset_xml_data, data_element = self.extract_preset_data(input_path)
            print(f"📊 Extracted {len(preset_xml_data):,} characters of preset data")
        except Exception as e:
            print(f"❌ Failed to extract preset data: {e}")
            return None
        
        # Check if already mapped
        if "MidiLearnDevice" in preset_xml_data:
            print("⚠️  Preset appears to already have automation mappings")
            print("   Proceeding anyway - may result in duplicate mappings")
        
        # Inject automation mappings
        try:
            mapped_xml_data = self.inject_automation_mappings(preset_xml_data)
            
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
    
    def batch_map_presets(self, input_dir, output_dir=None, pattern="*.aupreset"):
        """Batch process multiple aupreset files"""
        
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"❌ Input directory not found: {input_dir}")
            return []
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = input_path
        
        # Find aupreset files
        aupreset_files = list(input_path.glob(pattern))
        print(f"🔍 Found {len(aupreset_files)} aupreset files to process")
        
        if not aupreset_files:
            print("   No aupreset files found matching pattern")
            return []
        
        # Process each file
        processed_files = []
        for aupreset_file in aupreset_files:
            print(f"\n{'='*60}")
            
            output_file = output_path / f"{aupreset_file.stem} mapped{aupreset_file.suffix}"
            result = self.map_preset(aupreset_file, output_file)
            
            if result:
                processed_files.append(result)
        
        print(f"\n✅ Successfully processed {len(processed_files)} / {len(aupreset_files)} files")
        return processed_files

def main():
    """Command line interface"""
    
    parser = argparse.ArgumentParser(
        description="Add host automation mappings to Omnisphere aupreset files"
    )
    parser.add_argument('input', help='Input aupreset file or directory')
    parser.add_argument('-o', '--output', help='Output file or directory')
    parser.add_argument('--batch', action='store_true', help='Process all aupreset files in input directory')
    parser.add_argument('--pattern', default='*.aupreset', help='File pattern for batch processing')
    
    args = parser.parse_args()
    
    print("🎛️  Omnisphere Aupreset Automation Mapper")
    print("=" * 60)
    
    mapper = AupresetAutomationMapper()
    
    if args.batch:
        print(f"📂 Batch processing directory: {args.input}")
        results = mapper.batch_map_presets(args.input, args.output, args.pattern)
        
        if results:
            print(f"\n🎉 Batch processing complete!")
            print(f"   Processed {len(results)} files successfully")
        else:
            print(f"\n❌ Batch processing failed")
    else:
        print(f"📄 Processing single file: {args.input}")
        result = mapper.map_preset(args.input, args.output)
        
        if result:
            print(f"\n🎉 Mapping complete!")
            print(f"   Output: {result}")
        else:
            print(f"\n❌ Mapping failed")

if __name__ == "__main__":
    main()