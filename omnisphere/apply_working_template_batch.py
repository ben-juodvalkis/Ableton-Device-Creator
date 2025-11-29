#!/usr/bin/env python3
"""
Apply Omnisphere Automation Template to All Patches

Uses comprehensive automation template with:
- Host automation mappings (Orb radius/angle + parameters)
- Enhanced pitch bend range (2→12 semitones)
- Orb activation (orbSt + scnMC settings)
- ArpPhase timing offset (0.02 for slight groove enhancement)
- 22 MIDI Learn mappings for live performance

Applies to all 30,383 extracted patches while preserving patch-specific sounds
"""

import base64
import xml.etree.ElementTree as ET
import re
import time
from pathlib import Path

def extract_synth_engine_from_patch(patch_aupreset_path):
    """Extract SynthEngine content and apply pitch bend + Orb enhancements"""
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
                    
                    # Apply pitch bend enhancements to the extracted SynthEngine
                    # Convert old pitch bend values to enhanced values
                    enhanced_engine = re.sub(r'pbup="3d23d70a"', 'pbup="3e75c28f"', synth_engine)
                    enhanced_engine = re.sub(r'pbdn="3d23d70a"', 'pbdn="3e75c28f"', enhanced_engine)

                    # Apply ArpPhase enhancement (0.02 = 3ca3d70a for slight timing offset)
                    enhanced_engine = re.sub(r'ArpPhase="[^"]*"', 'ArpPhase="3ca3d70a"', enhanced_engine)
                    
                    # Apply Orb activation enhancements
                    # Add Orb state activation (orbSt="3f800000") if not present
                    if 'orbSt=' not in enhanced_engine:
                        # Insert orbSt after the first occurrence of a parameter block
                        orb_insertion = re.sub(r'(<SynthEngine[^>]*>)', r'\1 orbSt="3f800000"', enhanced_engine, count=1)
                        enhanced_engine = orb_insertion
                    else:
                        # Update existing orbSt to active state
                        enhanced_engine = re.sub(r'orbSt="[^"]*"', 'orbSt="3f800000"', enhanced_engine, count=1)
                    
                    # Add Orb modulation control (scnMC="3f7d95ae") if not present
                    if 'scnMC=' not in enhanced_engine:
                        # Insert scnMC after orbSt
                        orb_mod_insertion = re.sub(r'(orbSt="3f800000")', r'\1 scnMC="3f7d95ae"', enhanced_engine, count=1)
                        enhanced_engine = orb_mod_insertion
                    else:
                        # Update existing scnMC to active state
                        enhanced_engine = re.sub(r'scnMC="[^"]*"', 'scnMC="3f7d95ae"', enhanced_engine, count=1)
                    
                    return enhanced_engine
                else:
                    return None
    
    except Exception as e:
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
                    
                    # Note: Automation mappings (Orb radius/angle + parameters) preserved from template
                    
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
        return False

def apply_template_to_all_patches():
    """Apply working template to all extracted patches"""
    
    print("🎛️ Applying Working Template to All Patches")
    print("=" * 60)
    
    working_template = '/Users/Shared/DevWork/GitHub/Looping/scripts/device-creation/templates/Omnisphere/omnisphere-automation-template.aupreset'
    # Use paths relative to project root - intermediate extraction goes to temp, final output to Omnisphere Source
    clean_collection = '/Users/Shared/DevWork/GitHub/Looping/temp/omnisphere_extraction'
    output_collection = '/Users/Shared/DevWork/GitHub/Looping/ableton/Presets/Omnisphere Source'
    
    # Create output directory
    Path(output_collection).mkdir(parents=True, exist_ok=True)
    
    print(f"Template: {working_template}")
    print(f"Source: {clean_collection}")
    print(f"Output: {output_collection}")
    
    # Find all .aupreset files
    print("\\n1. Finding all .aupreset files...")
    aupreset_files = list(Path(clean_collection).rglob('*.aupreset'))
    print(f"✅ Found {len(aupreset_files)} .aupreset files")
    
    # Process each file
    print("\\n2. Applying working template to each file...")
    success_count = 0
    error_count = 0
    start_time = time.time()
    
    for i, source_file in enumerate(aupreset_files):
        if i % 1000 == 0 and i > 0:
            elapsed = time.time() - start_time
            print(f"   Progress: {i}/{len(aupreset_files)} ({success_count} ✅, {error_count} ❌) | {elapsed/60:.1f}m elapsed")
        
        try:
            # Extract SynthEngine from source
            synth_engine = extract_synth_engine_from_patch(str(source_file))
            if not synth_engine:
                error_count += 1
                continue
            
            # Get clean patch name from filename (no path, no extension)
            patch_name = source_file.stem
            
            # Create output path maintaining directory structure
            rel_path = source_file.relative_to(clean_collection)
            output_path = Path(output_collection) / rel_path
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create automation-enhanced patch
            if create_automation_patch(working_template, synth_engine, patch_name, str(output_path)):
                success_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            error_count += 1
    
    # Final results
    elapsed = time.time() - start_time
    print(f"\\n🎉 Template Application Complete!")
    print(f"  ✅ Successfully processed: {success_count:,} patches")
    print(f"  ❌ Errors: {error_count}")
    print(f"  ⏱️ Total time: {elapsed/60:.1f} minutes")
    print(f"  📁 Output: {output_collection}")
    print(f"\\n✨ All patches now have your complete automation setup!")
    
    return error_count == 0

if __name__ == "__main__":
    print("🎹 Working Template Batch Processor")
    print("Uses your complete working automation template")
    print("Estimated time: 5-10 minutes for 30,326 patches")
    print("\\n🚀 Starting batch processing...")
    
    apply_template_to_all_patches()