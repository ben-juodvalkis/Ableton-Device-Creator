#!/usr/bin/env python3
"""
Apply Working Template Method

Uses your complete working omni-mapped.aupreset as template
Only replaces the SynthEngine content with new patches
Preserves all automation structure
"""

import base64
import xml.etree.ElementTree as ET
import re
from pathlib import Path

def extract_synth_engine_from_patch(patch_aupreset_path):
    """Extract just the SynthEngine content from a patch file"""
    try:
        tree = ET.parse(patch_aupreset_path)
        root = tree.getroot()
        dict_elem = root.find('dict')
        
        # Get data0 and decode
        current_key = None
        for child in dict_elem:
            if child.tag == 'key':
                current_key = child.text
            elif child.tag == 'data' and current_key == 'data0':
                data0_content = child.text.strip()
                omnisphere_xml = base64.b64decode(data0_content).decode('utf-8')
                
                # Extract SynthEngine content
                start_idx = omnisphere_xml.find('<SynthEngine')
                end_idx = omnisphere_xml.find('</SynthEngine>')
                
                if start_idx != -1 and end_idx != -1:
                    synth_engine = omnisphere_xml[start_idx:end_idx + len('</SynthEngine>')]
                    return synth_engine
                else:
                    print(f"Could not find SynthEngine in {patch_aupreset_path}")
                    return None
    
    except Exception as e:
        print(f"Error extracting SynthEngine: {e}")
        return None

def create_automation_patch(working_template_path, synth_engine_content, patch_name, output_path):
    """Create new patch using working template + new SynthEngine content"""
    try:
        # Read working template
        tree = ET.parse(working_template_path)
        root = tree.getroot()
        dict_elem = root.find('dict')
        
        # Get template data0 and decode
        current_key = None
        for child in dict_elem:
            if child.tag == 'key':
                current_key = child.text
            elif child.tag == 'data' and current_key == 'data0':
                template_data0 = child.text.strip()
                template_xml = base64.b64decode(template_data0).decode('utf-8')
                
                # Replace SynthEngine content in template
                start_idx = template_xml.find('<SynthEngine')
                end_idx = template_xml.find('</SynthEngine>')
                
                if start_idx != -1 and end_idx != -1:
                    # Replace the SynthEngine section
                    new_xml = (template_xml[:start_idx] + 
                             synth_engine_content + 
                             template_xml[end_idx + len('</SynthEngine>'):])
                    
                    # Update patch name in XML
                    new_xml = re.sub(r'name="[^"]*"', f'name="{patch_name}"', new_xml, count=1)
                    
                    # Encode back to base64
                    new_encoded = base64.b64encode(new_xml.encode('utf-8')).decode('utf-8')
                    
                    # Format with proper line breaks
                    formatted_lines = []
                    for i in range(0, len(new_encoded), 68):
                        line = new_encoded[i:i+68]
                        formatted_lines.append(f"\t{line}")
                    formatted_b64 = "\n".join(formatted_lines)
                    
                    # Update data0 in template
                    child.text = '\n' + formatted_b64 + '\n\t'
                    
                    break
        
        # Update AU preset name
        current_key = None
        for child in dict_elem:
            if child.tag == 'key':
                current_key = child.text
            elif child.tag == 'string' and current_key == 'name':
                child.text = patch_name
                break
        
        # Write to output file preserving original structure
        tree.write(output_path, encoding='utf-8', xml_declaration=True, 
                  default_namespace='', method='xml')
        
        return True
        
    except Exception as e:
        print(f"Error creating automation patch: {e}")
        return False

def test_template_method():
    """Test the template method with reference files"""
    
    print("🧪 Testing Working Template Method")
    print("=" * 50)
    
    # Test creating a new file using working template + unmapped patch content
    working_template = '/Users/Music/Desktop/omni-mapped.aupreset'
    unmapped_patch = '/Users/Music/Desktop/omni-unmapped.aupreset' 
    test_output = '/tmp/template-method-test.aupreset'
    
    print("1. Extracting SynthEngine from unmapped patch...")
    synth_engine = extract_synth_engine_from_patch(unmapped_patch)
    if not synth_engine:
        print("❌ Could not extract SynthEngine")
        return False
    
    print(f"✅ Extracted {len(synth_engine)} chars of SynthEngine content")
    
    print("2. Creating new patch using working template...")
    success = create_automation_patch(working_template, synth_engine, "Template Test", test_output)
    
    if success:
        import os
        test_size = os.path.getsize(test_output)
        template_size = os.path.getsize(working_template)
        
        print(f"✅ Created test patch")
        print(f"   Template size: {template_size:,} bytes")
        print(f"   Test result: {test_size:,} bytes")
        print(f"   Test file: {test_output}")
        print(f"\\n🎯 Test this file in Ableton to verify automation works!")
        return True
    else:
        print("❌ Failed to create test patch")
        return False

if __name__ == "__main__":
    test_template_method()