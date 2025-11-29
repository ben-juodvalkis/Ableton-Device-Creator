#!/usr/bin/env python3
"""
Pure Omnisphere 3 Extractor - No automation mappings
Clean extraction only - automation applied separately
"""

import base64
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Configuration
STEAM_ROOT_DIR = "/Users/Shared/Music/Soundbanks/Spectrasonics/STEAM"
TEMPLATE_FILE_PATH = "/Users/Shared/DevWork/GitHub/Looping/ableton/Presets/Empty Patches/Omnisphere.aupreset"
OUTPUT_DIRECTORY = "/Users/Shared/DevWork/GitHub/Looping/scripts/preset-extraction/spectrasonics/omnisphere/extraction/omnisphere_3_clean_output"

# Constants
AU_MANUFACTURER_ID = 1196381015
AU_SUBTYPE_ID = 1097687666  
AU_TYPE_ID = 1635085685
AU_VERSION = 0
AU_RENDER_QUALITY = 127
BASE64_LINE_LENGTH = 68

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_template_from_aupreset():
    """Load template from existing .aupreset file"""
    try:
        tree = ET.parse(TEMPLATE_FILE_PATH)
        root = tree.getroot()
        dict_elem = root.find('dict')
        
        data0_found = False
        for child in dict_elem:
            if child.tag == 'key' and child.text == 'data0':
                data0_found = True
            elif data0_found and child.tag == 'data':
                encoded_data = child.text.strip()
                template_xml = base64.b64decode(encoded_data).decode('utf-8')
                logger.info(f"Template loaded successfully ({len(template_xml):,} characters)")
                return template_xml
        
        return None
    except Exception as e:
        logger.error(f"Error loading template: {e}")
        return None


def parse_library_index_enhanced(library_path, file_extension="prt_omn"):
    """Enhanced parser with full hierarchy support"""
    patches = []
    
    try:
        with open(library_path, 'rb') as f:
            content = f.read(500000).decode('utf-8', errors='ignore')
        
        lines = content.split('\n')
        dir_stack = []
        
        for line in lines:
            line = line.strip()
            
            if '<DIR name="' in line:
                dir_match = re.search(r'<DIR name="([^"]+)"', line)
                if dir_match:
                    dir_name = dir_match.group(1)
                    dir_stack.append(dir_name)
            
            elif '</DIR>' in line and dir_stack:
                dir_stack.pop()
            
            elif f'{file_extension}"' in line and 'offset=' in line and 'size=' in line:
                name_match = re.search(rf'name="([^"]+\.{file_extension})"', line)
                offset_match = re.search(r'offset="(\d+)"', line)
                size_match = re.search(r'size="(\d+)"', line)
                
                if name_match and offset_match and size_match:
                    patch_name = name_match.group(1).replace(f'.{file_extension}', '')
                    offset = int(offset_match.group(1))
                    size = int(size_match.group(1))
                    
                    full_path = dir_stack.copy() if dir_stack else []
                    
                    patches.append({
                        'name': patch_name,
                        'full_hierarchy': full_path,
                        'depth': len(full_path),
                        'level1': full_path[0] if len(full_path) >= 1 else '',
                        'level2': full_path[1] if len(full_path) >= 2 else '',
                        'level3': full_path[2] if len(full_path) >= 3 else '',
                        'path_string': ' → '.join(full_path),
                        'directory': full_path[0] if len(full_path) >= 1 else '',
                        'subdirectory': full_path[1] if len(full_path) >= 2 else '',
                        'offset': offset,
                        'size': size,
                        'extension': file_extension
                    })
        
        return patches
    except Exception as e:
        logger.error(f"Error parsing library index: {e}")
        return []


def extract_patch_from_library_fixed(library_path, patch_info):
    """Extract complete patch including closing tags"""
    try:
        with open(library_path, 'rb') as f:
            content = f.read(3000000)  # Read 3MB to find patch data start
            
            first_amber_pos = content.find(b'<AmberPart>')
            if first_amber_pos == -1:
                logger.error(f"Could not find any patch data in {library_path}")
                return None
            
            actual_offset = first_amber_pos + patch_info['offset']
            f.seek(actual_offset)
            
            patch_data = b''
            chunk_size = 8192
            max_read = 200000
            
            while len(patch_data) < max_read:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                patch_data += chunk
                
                if b'</AmberPart>' in patch_data:
                    end_pos = patch_data.find(b'</AmberPart>') + len(b'</AmberPart>')
                    complete_patch_data = patch_data[:end_pos]
                    patch_xml = complete_patch_data.decode('utf-8', errors='ignore')
                    return patch_xml
            
            patch_xml = patch_data.decode('utf-8', errors='ignore')
            logger.warning(f"No </AmberPart> found, using available data: {len(patch_xml)} chars")
            return patch_xml
            
    except Exception as e:
        logger.error(f"Error extracting patch {patch_info['name']}: {e}")
        return None


def create_preset_with_patch_fixed(template_xml, patch_data, patch_name="Custom Patch"):
    """Create preset using the template system"""
    
    updated_template = template_xml.replace('name="default multi"', f'name="{patch_name}"')
    
    sub_engine_pattern = r'(<SynthSubEngine[^>]*>)(.*?)(</SynthSubEngine>)'
    sub_engines = list(re.finditer(sub_engine_pattern, updated_template, re.DOTALL))
    
    if not sub_engines:
        logger.error("No SynthSubEngine found in template")
        return None
    
    replacement_done = False
    result = updated_template
    
    for i, match in enumerate(sub_engines):
        start_tag, content, end_tag = match.groups()
        
        if len(content.strip()) > 1000 and not replacement_done:
            start_marker = '<SynthEngine'
            end_marker = '</SynthEngine>'
            
            start_idx = patch_data.find(start_marker)
            end_idx = patch_data.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                synth_engine_content = patch_data[start_idx:end_idx + len(end_marker)]
                new_content = f'\n{synth_engine_content}\n '
            else:
                logger.error(f"Could not find SynthEngine tags in patch data")
                return None
            
            new_sub_engine = start_tag + new_content + end_tag
            old_sub_engine = match.group(0)
            
            result = result.replace(old_sub_engine, new_sub_engine, 1)
            replacement_done = True
            break
    
    return result if replacement_done else None


def create_clean_aupreset(preset_xml, output_path, preset_name="Custom Patch"):
    """Create clean .aupreset file without automation"""
    try:
        encoded_bytes = base64.b64encode(preset_xml.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')
        
        formatted_lines = []
        for i in range(0, len(encoded_str), BASE64_LINE_LENGTH):
            line = encoded_str[i:i+BASE64_LINE_LENGTH]
            formatted_lines.append(f"\t{line}")
        
        formatted_b64 = "\n".join(formatted_lines)
        
        # Clean AU preset structure (matching original format)
        aupreset_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>data</key>
\t<data>
\t</data>
\t<key>data0</key>
\t<data>
{formatted_b64}
\t</data>
\t<key>manufacturer</key>
\t<integer>{AU_MANUFACTURER_ID}</integer>
\t<key>name</key>
\t<string>{preset_name}</string>
\t<key>render-quality</key>
\t<integer>{AU_RENDER_QUALITY}</integer>
\t<key>subtype</key>
\t<integer>{AU_SUBTYPE_ID}</integer>
\t<key>type</key>
\t<integer>{AU_TYPE_ID}</integer>
\t<key>version</key>
\t<integer>{AU_VERSION}</integer>
</dict>
</plist>'''
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(aupreset_xml)
        
        return True
    except Exception as e:
        logger.error(f"Error creating aupreset {output_path}: {e}")
        return False


def sanitize_filename(filename):
    """Make filename safe for filesystem"""
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_name = safe_name.strip('. ')
    if len(safe_name) > 100:
        safe_name = safe_name[:100]
    return safe_name


def test_clean_extraction(library_name="Analog Vibes.db"):
    """Test clean extraction without automation"""
    
    print(f"🎹 Testing CLEAN Omnisphere 3 Extraction with {library_name}")
    print("=" * 60)
    
    output_dir = Path(OUTPUT_DIRECTORY)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("1. Loading template...")
    template_xml = load_template_from_aupreset()
    if not template_xml:
        print("❌ Could not load template")
        return False
    print(f"✅ Template loaded ({len(template_xml):,} characters)")
    
    library_path = f"/Users/Shared/Music/Soundbanks/Spectrasonics/STEAM/Omnisphere/Settings Library/Patches/Factory/{library_name}"
    if not Path(library_path).exists():
        print(f"❌ Library not found: {library_path}")
        return False
    
    print(f"2. Parsing {library_name}...")
    patches = parse_library_index_enhanced(library_path, "prt_omn")
    if not patches:
        print("❌ Could not parse library")
        return False
    
    print(f"✅ Found {len(patches)} patches")
    
    print("\n3. Testing clean extraction (first 3 patches)...")
    lib_output_dir = output_dir / library_name.replace('.db', '')
    lib_output_dir.mkdir(exist_ok=True)
    
    success_count = 0
    for i, patch in enumerate(patches[:3]):
        try:
            print(f"   Testing patch {i+1}: {patch['name'][:50]}...")
            
            patch_xml = extract_patch_from_library_fixed(library_path, patch)
            if not patch_xml:
                print(f"   ❌ Failed to extract patch XML")
                continue
            
            has_closing = '</SynthEngine>' in patch_xml and '</AmberPart>' in patch_xml
            print(f"   📄 Extracted {len(patch_xml)} chars, complete: {'✅' if has_closing else '❌'}")
            
            complete_preset = create_preset_with_patch_fixed(template_xml, patch_xml, patch['name'])
            if not complete_preset:
                print(f"   ❌ Failed to create preset")
                continue
            
            safe_name = sanitize_filename(patch['name'])
            output_path = lib_output_dir / f"{safe_name}.aupreset"
            
            if create_clean_aupreset(complete_preset, str(output_path), patch['name']):
                file_size = Path(output_path).stat().st_size
                print(f"   ✅ Created: {output_path.name} ({file_size:,} bytes)")
                success_count += 1
            else:
                print(f"   ❌ Failed to write .aupreset file")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n🎉 Clean Extraction Results:")
    print(f"   Success: {success_count}/3 patches")
    print(f"   Output: {lib_output_dir}")
    
    if success_count > 0:
        print(f"\n✅ Clean extraction working!")
        print(f"Now test these files in Ableton before applying automation.")
        return True
    else:
        print(f"\n❌ Clean extraction failed.")
        return False


if __name__ == "__main__":
    test_clean_extraction("Analog Vibes.db")