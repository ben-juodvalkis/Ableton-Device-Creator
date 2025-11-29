#!/usr/bin/env python3
"""
Omnisphere 3 Full Library Extractor

Extracts specified Omnisphere 3, Keyscape, and Trilian libraries
Clean extraction only - automation applied separately

Target Libraries:
- 18 New Omnisphere 3 libraries  
- Keyscape libraries
- Trilian libraries
"""

import base64
import logging
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

# Configuration
STEAM_ROOT_DIR = "/Users/Shared/Music/Soundbanks/Spectrasonics/STEAM"
TEMPLATE_FILE_PATH = "/Users/Shared/DevWork/GitHub/Looping/ableton/Presets/Empty Patches/Omnisphere.aupreset"
# Intermediate extraction directory (cleaned up after automation applied)
OUTPUT_DIRECTORY = "/Users/Shared/DevWork/GitHub/Looping/temp/omnisphere_extraction"

# Target Libraries (as specified by user)
TARGET_LIBRARIES = {
    # New Omnisphere 3 Libraries  
    "Omnisphere": [
        "Analog Vibes.db",
        "Classic Digital.db", 
        "Retro Vibes.db",
        "Electronic Production.db",
        "Electronic Underground.db",
        "Hard Edges.db",
        "Club Land.db",
        "Ambient Dreams.db", 
        "Organic Vibes.db",
        "Warm Tones.db",
        "Scoring Organic.db",
        "Scoring Electronic.db",
        "Experimental Organic.db",
        "Instruments Collection.db",
        "Live Keyboardist.db",
        "Vocal Collection.db",
        "SFX Electronic.db",
        "SFX Organic.db",
        "Nylon Sky.db"  # Sonic Extension - acoustic guitars
    ],
    
    # Keyscape Libraries
    "Keyscape": [
        "Keyscape Library.db",
        "Keyscape Creative.db" 
    ],
    
    # Trilian Libraries  
    "Trilian": [
        "Trilian Library.db",
        "Trilogy Library.db",
        "XTRA - Bass Legends.db",
        "Trilian Creative.db"
    ]
}

# File extensions by product
EXTENSIONS = {
    "Omnisphere": "prt_omn",
    "Keyscape": "prt_key", 
    "Trilian": "prt_trl"
}

# Some Keyscape Creative uses .prt_omn
SPECIAL_EXTENSIONS = {
    "Keyscape Creative.db": "prt_omn",
    "Trilian Creative.db": "prt_omn"
}

# Special path handling for Sonic Extensions
SPECIAL_PATHS = {
    "Nylon Sky.db": "Sonic Extensions/Nylon Sky/Settings Library/Patches/Factory"
}

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


def extract_patch_from_library_fixed(library_path, patch_info, product="Omnisphere", library_name=""):
    """Extract complete patch - Omnisphere uses AmberPart containers, Keyscape/Trilian use direct offsets"""
    try:
        with open(library_path, 'rb') as f:
            
            if product == "Omnisphere" and library_name not in ["Nylon Sky.db"]:
                # Omnisphere 3 method: Find AmberPart container and read complete XML
                content = f.read(3000000)
                first_amber_pos = content.find(b'<AmberPart>')
                if first_amber_pos == -1:
                    logger.error(f"Could not find AmberPart data in {library_path}")
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
                        return complete_patch_data.decode('utf-8', errors='ignore')
                
                return patch_data.decode('utf-8', errors='ignore')
                
            else:
                # Keyscape/Trilian/Nylon Sky method: Use original offset method (like old script)
                content = f.read(1000000)
                text_content = content.decode('utf-8', errors='ignore')
                filesystem_end_pos = text_content.find('</FileSystem>')
                
                if filesystem_end_pos == -1:
                    logger.error(f"Could not find FileSystem end in {library_path}")
                    return None
                
                data_start = filesystem_end_pos + len('</FileSystem>') + 1
                actual_offset = data_start + patch_info['offset']
                f.seek(actual_offset)
                
                patch_data = f.read(patch_info['size'])
                return patch_data.decode('utf-8', errors='ignore')
            
    except Exception as e:
        logger.error(f"Error extracting patch {patch_info['name']}: {e}")
        return None


def create_preset_with_patch_fixed(template_xml, patch_data, patch_name="Custom Patch", product="Omnisphere"):
    """Create preset using the template system - supports all Spectrasonics products"""
    
    updated_template = template_xml.replace('name="default multi"', f'name="{patch_name}"')
    
    sub_engine_pattern = r'(<SynthSubEngine[^>]*>)(.*?)(</SynthSubEngine>)'
    sub_engines = list(re.finditer(sub_engine_pattern, updated_template, re.DOTALL))
    
    if not sub_engines:
        logger.error("No SynthSubEngine found in template")
        return None
    
    # All products use SynthEngine in the final aupreset (confirmed from working files)
    engine_start = '<SynthEngine'
    engine_end = '</SynthEngine>'
    
    replacement_done = False
    result = updated_template
    
    for i, match in enumerate(sub_engines):
        start_tag, content, end_tag = match.groups()
        
        if len(content.strip()) > 1000 and not replacement_done:
            start_idx = patch_data.find(engine_start)
            end_idx = patch_data.find(engine_end)
            
            if start_idx != -1 and end_idx != -1:
                engine_content = patch_data[start_idx:end_idx + len(engine_end)]
                new_content = f'\n{engine_content}\n '
            else:
                logger.error(f"Could not find {engine_start} tags in patch data")
                return None
            
            new_sub_engine = start_tag + new_content + end_tag
            old_sub_engine = match.group(0)
            
            result = result.replace(old_sub_engine, new_sub_engine, 1)
            replacement_done = True
            break
    
    return result if replacement_done else None


def create_clean_aupreset(preset_xml, output_path, preset_name="Custom Patch"):
    """Create clean .aupreset file"""
    try:
        encoded_bytes = base64.b64encode(preset_xml.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')
        
        formatted_lines = []
        for i in range(0, len(encoded_str), BASE64_LINE_LENGTH):
            line = encoded_str[i:i+BASE64_LINE_LENGTH]
            formatted_lines.append(f"\t{line}")
        
        formatted_b64 = "\n".join(formatted_lines)
        
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


def clean_patch_name(patch_name):
    """Remove library prefixes from patch names"""
    # Remove library prefixes like "CLUB │", "AV │", "UN │", etc.
    # Using working pattern from testing
    clean_name = re.sub(r'^[A-Z]{1,4}\s*[│|]\s*', '', patch_name)
    return clean_name.strip()

def sanitize_filename(filename):
    """Make filename safe for filesystem"""
    # First remove prefixes
    clean_name = clean_patch_name(filename)
    
    # Standard filesystem safety
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', clean_name)
    safe_name = safe_name.strip('. ')
    if len(safe_name) > 100:
        safe_name = safe_name[:100]
    return safe_name


def extract_full_libraries():
    """Extract all specified libraries"""
    
    print("🚀 Starting Full Omnisphere 3 Library Extraction")
    print("=" * 60)
    
    # Create main output directory
    output_dir = Path(OUTPUT_DIRECTORY)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load template once
    print("Loading template...")
    template_xml = load_template_from_aupreset()
    if not template_xml:
        print("❌ Could not load template")
        return False
    print(f"✅ Template loaded ({len(template_xml):,} characters)")
    
    # Process each product
    total_extracted = 0
    total_errors = 0
    start_time = time.time()
    
    for product, libraries in TARGET_LIBRARIES.items():
        print(f"\n📚 Processing {product} Libraries")
        print(f"   Targeting {len(libraries)} libraries")
        
        product_dir = output_dir / product
        product_dir.mkdir(exist_ok=True)
        
        for library_name in libraries:
            print(f"\n🔄 Processing: {library_name}")
            
            # Build library path - check for special paths first
            if library_name in SPECIAL_PATHS:
                factory_path = SPECIAL_PATHS[library_name]
                library_path = Path(STEAM_ROOT_DIR) / factory_path / library_name
            else:
                factory_path = f"{product}/Settings Library/Patches/Factory"
                library_path = Path(STEAM_ROOT_DIR) / factory_path / library_name
            
            if not library_path.exists():
                print(f"   ❌ Library not found: {library_path}")
                continue
            
            # Get correct file extension
            extension = SPECIAL_EXTENSIONS.get(library_name, EXTENSIONS[product])
            
            # Parse library
            patches = parse_library_index_enhanced(str(library_path), extension)
            if not patches:
                print(f"   ❌ Could not parse library")
                continue
            
            print(f"   📊 Found {len(patches)} patches")
            
            # Create library output directory
            safe_lib_name = sanitize_filename(library_name.replace('.db', ''))
            lib_output_dir = product_dir / safe_lib_name
            lib_output_dir.mkdir(exist_ok=True)
            
            # Extract patches
            lib_success = 0
            lib_errors = 0
            
            for j, patch in enumerate(patches):
                if j % 100 == 0 and j > 0:
                    elapsed = time.time() - start_time
                    print(f"      Progress: {j}/{len(patches)} ({lib_success} ✅, {lib_errors} ❌) | {elapsed/60:.1f}m elapsed")
                
                try:
                    # Extract patch with product-specific handling
                    patch_xml = extract_patch_from_library_fixed(str(library_path), patch, product, library_name)
                    if not patch_xml:
                        lib_errors += 1
                        continue
                    
                    # Create preset with cleaned name
                    clean_name = clean_patch_name(patch['name'])
                    complete_preset = create_preset_with_patch_fixed(template_xml, patch_xml, clean_name, product)
                    if not complete_preset:
                        lib_errors += 1
                        continue
                    
                    # Create output path with clean filename
                    safe_name = sanitize_filename(patch['name'])  # This now removes prefixes
                    
                    if patch['level1']:
                        safe_dir1 = sanitize_filename(patch['level1'])
                        level1_dir = lib_output_dir / safe_dir1
                        level1_dir.mkdir(parents=True, exist_ok=True)
                        
                        if patch['level2']:
                            safe_dir2 = sanitize_filename(patch['level2'])
                            level2_dir = level1_dir / safe_dir2
                            level2_dir.mkdir(parents=True, exist_ok=True)
                            
                            if patch['level3']:
                                safe_dir3 = sanitize_filename(patch['level3'])
                                level3_dir = level2_dir / safe_dir3
                                level3_dir.mkdir(parents=True, exist_ok=True)
                                output_path = level3_dir / f"{safe_name}.aupreset"
                            else:
                                output_path = level2_dir / f"{safe_name}.aupreset"
                        else:
                            output_path = level1_dir / f"{safe_name}.aupreset"
                    else:
                        output_path = lib_output_dir / f"{safe_name}.aupreset"
                    
                    # Create .aupreset file with cleaned name (already applied in complete_preset creation above)
                    if create_clean_aupreset(complete_preset, str(output_path), clean_name):
                        lib_success += 1
                    else:
                        lib_errors += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing {patch['name']}: {e}")
                    lib_errors += 1
            
            # Library summary
            elapsed = time.time() - start_time
            print(f"   ✅ {safe_lib_name}: {lib_success}/{len(patches)} successful ({lib_errors} errors) | {elapsed/60:.1f}m")
            total_extracted += lib_success
            total_errors += lib_errors
    
    # Final summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"🎉 Full Extraction Complete!")
    print(f"  ✅ Successfully extracted: {total_extracted:,} patches")
    print(f"  ❌ Errors: {total_errors}")
    print(f"  ⏱️ Total time: {elapsed/60:.1f} minutes")
    print(f"  📁 Output directory: {output_dir}")
    print(f"\n🔄 Next steps:")
    print(f"  1. Test a few extracted files in Ableton")
    print(f"  2. Apply automation mappings with separate script")
    print(f"  3. Run generate-instruments-json.ts to update browser")
    
    return total_errors == 0


if __name__ == "__main__":
    print("🎹 Omnisphere 3 Full Library Extractor")
    print("Target: 18 Omnisphere + Keyscape + Trilian libraries") 
    print("Estimated time: 2-3 hours")
    print("Estimated output: ~25,000 patches, ~12GB")
    print("\n🚀 Starting extraction...")
    
    extract_full_libraries()