#!/usr/bin/env python3
"""
Nylon Sky Only Extractor

Quick extraction script for just Nylon Sky patches
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
OUTPUT_DIRECTORY = "/Users/Shared/DevWork/GitHub/Looping/ableton/Presets/Instruments/spectrasonics/omnisphere_3_complete"

# Only extract Nylon Sky
TARGET_LIBRARIES = {
    "Omnisphere": ["Nylon Sky.db"]
}

# File extensions by product
EXTENSIONS = {
    "Omnisphere": "prt_omn"
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
                template_data = child.text.strip()
                logger.info(f"Template loaded successfully ({len(template_data):,} characters)")
                return template_data
    except Exception as e:
        logger.error(f"Failed to load template: {e}")
        sys.exit(1)


def clean_patch_name(name: str) -> str:
    """Remove library prefixes from patch names"""
    # Remove patterns like "CLUB │", "AV │", "NYC │", etc.
    cleaned = re.sub(r'^[A-Z]{1,4}\s*[│|]\s*', '', name)
    return cleaned.strip()


def parse_nylon_sky_db(db_path: str, extension: str) -> List[Dict]:
    """Parse Nylon Sky database using traditional offset method"""
    patches = []
    
    try:
        with open(db_path, 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()
            
        # Extract only the FileSystem section (first 131 lines)
        filesystem_lines = []
        for line in lines:
            filesystem_lines.append(line)
            if '</FileSystem>' in line:
                break
                
        filesystem_content = ''.join(filesystem_lines)
        
        # Parse XML structure to find files
        root = ET.fromstring(filesystem_content)
        
        # Find all FILE elements within DIR elements
        current_dir = None
        for elem in root.iter():
            if elem.tag == 'DIR':
                current_dir = elem.get('name', 'Unknown')
            elif elem.tag == 'FILE':
                file_name = elem.get('name', 'Unknown')
                offset = int(elem.get('offset', '0'))
                size = int(elem.get('size', '0'))
                
                # Extract patch name from filename (remove .prt_omn extension)
                patch_name = file_name.replace('.prt_omn', '')
                clean_name = clean_patch_name(patch_name)
                
                # Create hierarchy based on directory
                hierarchy = [current_dir] if current_dir else []
                
                patches.append({
                    'name': clean_name,
                    'original_name': patch_name,
                    'hierarchy': hierarchy,
                    'offset': offset,
                    'size': size,
                    'extension': extension
                })
                
    except Exception as e:
        logger.error(f"Error reading database {db_path}: {e}")
        return []
    
    return patches


def extract_patch_data(db_path: str, offset: int, size: int) -> str:
    """Extract individual patch data from database"""
    try:
        with open(db_path, 'rb') as file:
            file.seek(offset)
            patch_data = file.read(size)
            return patch_data.decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Error extracting patch data: {e}")
        return ""


def create_aupreset_with_data(patch_data: str, name: str, output_path: str):
    """Create .aupreset file with patch data"""
    
    # Create AU plugin structure
    root = ET.Element('plist', version='1.0')
    dict_elem = ET.SubElement(root, 'dict')
    
    # Add AU plugin info
    ET.SubElement(dict_elem, 'key').text = 'manufacturer'
    ET.SubElement(dict_elem, 'integer').text = str(AU_MANUFACTURER_ID)
    
    ET.SubElement(dict_elem, 'key').text = 'subtype'
    ET.SubElement(dict_elem, 'integer').text = str(AU_SUBTYPE_ID)
    
    ET.SubElement(dict_elem, 'key').text = 'type'
    ET.SubElement(dict_elem, 'integer').text = str(AU_TYPE_ID)
    
    ET.SubElement(dict_elem, 'key').text = 'version'
    ET.SubElement(dict_elem, 'integer').text = str(AU_VERSION)
    
    # Add patch data
    ET.SubElement(dict_elem, 'key').text = 'data0'
    data_elem = ET.SubElement(dict_elem, 'data')
    
    # Encode and format the data
    encoded_data = base64.b64encode(patch_data.encode('utf-8')).decode('ascii')
    formatted_data = '\n'.join(
        encoded_data[i:i+BASE64_LINE_LENGTH] 
        for i in range(0, len(encoded_data), BASE64_LINE_LENGTH)
    )
    data_elem.text = f'\n{formatted_data}\n'
    
    # Write file
    tree = ET.ElementTree(root)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)


def main():
    """Main extraction function"""
    template_data = load_template_from_aupreset()
    
    if not template_data:
        logger.error("Could not load template data")
        return
    
    output_dir = Path(OUTPUT_DIRECTORY)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    total_patches = 0
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
            extension = EXTENSIONS[product]
            
            # Parse library
            patches = parse_nylon_sky_db(str(library_path), extension)
            if not patches:
                print(f"   ❌ Could not parse library")
                continue
            
            print(f"   📊 Found {len(patches)} patches")
            
            # Create library directory
            clean_library_name = library_name.replace('.db', '')
            library_dir = product_dir / clean_library_name
            
            # Process patches
            for patch in patches:
                # Extract patch data from database
                patch_data = extract_patch_data(str(library_path), patch['offset'], patch['size'])
                if not patch_data:
                    continue
                
                # Build path from hierarchy
                if patch['hierarchy']:
                    folder_path = library_dir / Path(*patch['hierarchy'])
                else:
                    folder_path = library_dir
                
                folder_path.mkdir(parents=True, exist_ok=True)
                
                # Create file
                safe_name = re.sub(r'[<>:"/\\|?*]', '', patch['name'])
                file_path = folder_path / f"{safe_name}.aupreset"
                
                create_aupreset_with_data(patch_data, patch['name'], str(file_path))
                total_patches += 1
            
            print(f"   ✅ Extracted {len(patches)} patches")
    
    elapsed_time = time.time() - start_time
    print(f"\n🎉 Extraction Complete!")
    print(f"   Total patches: {total_patches:,}")
    print(f"   Time elapsed: {elapsed_time:.1f} seconds")


if __name__ == "__main__":
    main()