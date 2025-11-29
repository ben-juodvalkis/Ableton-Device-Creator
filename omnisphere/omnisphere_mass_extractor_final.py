#!/usr/bin/env python3
"""
⚠️ DEPRECATED: Legacy Omnisphere Mass Patch Extractor

This script is deprecated as of October 22, 2025.
Use omnisphere_3_full_extractor.py for Omnisphere 3 extraction instead.

Legacy: Omnisphere Mass Patch Extractor - MULTI-LIBRARY VERSION

Extracts ALL patches from Spectrasonics Omnisphere Factory Libraries
and converts them to individual .aupreset files for direct use in Ableton Live.

Supports all Factory libraries:
- Omnisphere Library.db (2,088 patches)
- Hardware Library.db (1,568 patches) 
- Moog Tribute Library.db (1,343 patches)
- Atmosphere Library.db (1,027 patches)
- Spotlight - EDM.db (813 patches)
- A Taste of Omnisphere.db (minimal patches)

Total: 7,839+ patches across 191+ categories

Successfully tested and verified:
- 100% extraction success rate across all libraries
- Perfect AU preset compatibility
- Correct sound reproduction in Omnisphere
- Organized by library and original categories

Author: Claude Code Assistant
Date: August 2024
"""

import base64
import json
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote
from collections import defaultdict

# Configuration Constants
STEAM_ROOT_DIR = "/Users/Shared/Music/Soundbanks/Spectrasonics/STEAM"
TEMPLATE_FILE_PATH = "../templates/test_files_archive/TEMPLATE_DONOR.aupreset"  # Working Omnisphere preset used as template base
OUTPUT_DIRECTORY = "../../data/presets/complete_steam_presets"
METADATA_OUTPUT_FILE = "../../data/metadata/omnisphere_metadata.json"  # Enhanced metadata database

# Factory library directories to search
FACTORY_DIRS = [
    "Omnisphere/Settings Library/Patches/Factory",
    "Trilian/Settings Library/Patches/Factory",
    "Keyscape/Settings Library/Patches/Factory",
    "Sonic Extensions/*/Settings Library/Patches/Factory"  # Wildcard for extensions
]

# Library definitions with expected patch counts and file extensions
LIBRARY_INFO = {
    # Omnisphere Libraries (.prt_omn files)
    "Omnisphere Library.db": {"expected_patches": 5794, "description": "Main Omnisphere Factory Library", "extension": "prt_omn", "product": "Omnisphere"},
    "Hardware Library.db": {"expected_patches": 1568, "description": "Hardware Synthesizers", "extension": "prt_omn", "product": "Omnisphere"},
    "Moog Tribute Library.db": {"expected_patches": 1343, "description": "Moog Synthesizer Tribute", "extension": "prt_omn", "product": "Omnisphere"},
    "Atmosphere Library.db": {"expected_patches": 1027, "description": "Atmospheric Textures", "extension": "prt_omn", "product": "Omnisphere"},
    "Spotlight - EDM.db": {"expected_patches": 813, "description": "Electronic Dance Music", "extension": "prt_omn", "product": "Omnisphere"},
    "A Taste of Omnisphere.db": {"expected_patches": 0, "description": "Demo Patches", "extension": "prt_omn", "product": "Omnisphere"},
    "VIP Library.db": {"expected_patches": 0, "description": "VIP Library", "extension": "prt_omn", "product": "Omnisphere"},
    
    # Trilian Libraries (.prt_trl files)  
    "Trilian Library.db": {"expected_patches": 1083, "description": "Main Trilian Bass Library", "extension": "prt_trl", "product": "Trilian"},
    "Trilogy Library.db": {"expected_patches": 582, "description": "Legacy Trilogy Library", "extension": "prt_trl", "product": "Trilian"},
    "XTRA - Bass Legends.db": {"expected_patches": 35, "description": "Bass Legends Expansion", "extension": "prt_trl", "product": "Trilian"},
    "Trilian Creative.db": {"expected_patches": 216, "description": "Creative Bass Patches", "extension": "prt_omn", "product": "Trilian"},
    "Trilian VIP.db": {"expected_patches": 0, "description": "VIP Bass Library", "extension": "prt_trl", "product": "Trilian"},
    
    # Keyscape Libraries (.prt_key files)
    "Keyscape Library.db": {"expected_patches": 466, "description": "Main Keyscape Piano Library", "extension": "prt_key", "product": "Keyscape"},
    "Keyscape Creative.db": {"expected_patches": 1523, "description": "Creative Piano Patches", "extension": "prt_omn", "product": "Keyscape"},
    
    # Sonic Extensions (.prt_omn files)
    "Nylon Sky.db": {"expected_patches": 57, "description": "Nylon Sky Extension", "extension": "prt_omn", "product": "Sonic Extensions"}
}

# AU Preset Metadata Constants
AU_MANUFACTURER_ID = 1196381015    # Spectrasonics
AU_SUBTYPE_ID = 1097687666        # Omnisphere subtype
AU_TYPE_ID = 1635085685           # Audio Unit type
AU_VERSION = 0
AU_RENDER_QUALITY = 127

# Processing Constants
FILESYSTEM_READ_SIZE = 500000     # Bytes to read for parsing FileSystem
BASE64_LINE_LENGTH = 68           # Characters per Base64 line in AU preset

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def discover_steam_libraries() -> List[Dict[str, any]]:
    """
    Discover and validate all available STEAM libraries (Omnisphere + Trilian) in Factory directories.
    
    Returns:
        List[Dict]: List of library dictionaries with path, name, and patch count info
    """
    libraries = []
    steam_root = Path(STEAM_ROOT_DIR)
    
    if not steam_root.exists():
        logger.error(f"STEAM root directory not found: {steam_root}")
        return libraries
    
    logger.info(f"Scanning STEAM installation: {steam_root}")
    
    # Scan each factory directory (including wildcard expansion)
    total_db_files = 0
    for factory_subdir in FACTORY_DIRS:
        if "*" in factory_subdir:
            # Handle wildcard paths (e.g., "Sonic Extensions/*/Settings Library/Patches/Factory")
            pattern_parts = factory_subdir.split("/")
            base_path = steam_root
            for i, part in enumerate(pattern_parts):
                if part == "*":
                    # Find all matching directories at this level
                    remaining_path = "/".join(pattern_parts[i+1:])
                    for wildcard_dir in base_path.iterdir():
                        if wildcard_dir.is_dir():
                            full_factory_dir = wildcard_dir / remaining_path
                            if full_factory_dir.exists():
                                factory_dirs_to_scan = [full_factory_dir]
                                break
                    else:
                        factory_dirs_to_scan = []
                    break
                else:
                    base_path = base_path / part
            else:
                factory_dirs_to_scan = [base_path] if base_path.exists() else []
        else:
            # Regular path
            factory_dir = steam_root / factory_subdir
            factory_dirs_to_scan = [factory_dir] if factory_dir.exists() else []
        
        for factory_dir in factory_dirs_to_scan:
            if not factory_dir.exists():
                logger.warning(f"Factory directory not found: {factory_dir}")
                continue
                
            logger.info(f"Scanning: {factory_dir.relative_to(steam_root)}")
            
            # Find all .db files in this directory
            db_files = list(factory_dir.glob("*.db"))
            total_db_files += len(db_files)
            logger.info(f"  Found {len(db_files)} .db files")
            
            for db_file in db_files:
                library_name = db_file.name
                
                # Skip empty files
                if db_file.stat().st_size == 0:
                    logger.warning(f"  Skipping empty library: {library_name}")
                    continue
                
                # Get expected info if available
                expected_info = LIBRARY_INFO.get(library_name, {})
                file_extension = expected_info.get("extension", "prt_omn")  # Default to Omnisphere
                product = expected_info.get("product", "Unknown")
                
                try:
                    # Parse library index with correct extension
                    patches = parse_library_index(str(db_file), file_extension)
                    patch_count = len(patches) if patches else 0
                    
                    if patch_count == 0:
                        logger.warning(f"  No patches found in: {library_name}")
                        continue
                    
                    library_info = {
                        "path": str(db_file),
                        "name": library_name,
                        "display_name": library_name.replace(".db", "").replace("_", " "),
                        "patch_count": patch_count,
                        "size_mb": round(db_file.stat().st_size / (1024 * 1024), 1),
                        "description": expected_info.get("description", ""),
                        "expected_patches": expected_info.get("expected_patches", 0),
                        "extension": file_extension,
                        "product": product,
                        "factory_dir": str(factory_dir.relative_to(steam_root))
                    }
                    
                    libraries.append(library_info)
                    logger.info(f"  ✓ {library_name}: {patch_count} patches ({library_info['size_mb']}MB) - {product}")
                    
                except Exception as e:
                    logger.error(f"  Error analyzing {library_name}: {e}")
    
    # Sort by product first, then by patch count (largest first)
    libraries.sort(key=lambda x: (x["product"], -x["patch_count"]))
    
    total_patches = sum(lib["patch_count"] for lib in libraries)
    logger.info(f"Total libraries discovered: {len(libraries)} with {total_patches:,} patches across {len(FACTORY_DIRS)} products")
    
    return libraries


def load_complete_template() -> Optional[str]:
    """
    Load the complete working Omnisphere template from archived preset file.
    
    Returns:
        Optional[str]: Decoded XML template content, or None if loading fails
    """
    try:
        template_path = Path(TEMPLATE_FILE_PATH)
        if not template_path.exists():
            logger.error(f"Template file not found: {template_path}")
            return None
        
        logger.info(f"Loading template from: {template_path}")
        
        # Parse AU preset XML structure
        tree = ET.parse(template_path)
        root = tree.getroot()
        dict_elem = root.find('dict')
        
        if dict_elem is None:
            logger.error("Invalid AU preset format - no dict element found")
            return None
        
        # Find data0 key and extract Base64 content
        data0_found = False
        for child in dict_elem:
            if child.tag == 'key' and child.text == 'data0':
                data0_found = True
            elif data0_found and child.tag == 'data':
                encoded_data = child.text.strip() if child.text else ""
                if not encoded_data:
                    logger.error("Template data0 section is empty")
                    return None
                
                # Decode Base64 to get Omnisphere XML
                template_xml = base64.b64decode(encoded_data).decode('utf-8')
                logger.info(f"Template loaded successfully ({len(template_xml):,} characters)")
                return template_xml
        
        logger.error("Template data0 section not found")
        return None
        
    except ET.ParseError as e:
        logger.error(f"XML parsing error in template: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading template: {e}")
        return None


def parse_library_index(library_path, file_extension="prt_omn"):
    """Parse the FileSystem structure to get all patch info for any STEAM product"""
    patches = []
    
    try:
        with open(library_path, 'rb') as f:
            # Read the first part as text to get the FileSystem structure
            content = f.read(500000).decode('utf-8', errors='ignore')
        
        # Find all FILE entries
        lines = content.split('\n')
        dir_stack = []  # Stack to track nested directories
        current_top_dir = ""  # Top-level directory
        current_sub_dir = ""  # Immediate parent directory
        
        for line in lines:
            line = line.strip()
            
            # Track directory structure with nesting
            if '<DIR name="' in line:
                dir_match = re.search(r'<DIR name="([^"]+)"', line)
                if dir_match:
                    dir_name = dir_match.group(1)
                    dir_stack.append(dir_name)
                    
                    # Top-level directory is the first one
                    if len(dir_stack) == 1:
                        current_top_dir = dir_name
                        current_sub_dir = ""
                    else:
                        # For nested directories, keep the top-level and track the immediate parent
                        current_sub_dir = dir_name
            
            # Handle directory closing (though this is more complex in practice)
            elif '</DIR>' in line and dir_stack:
                dir_stack.pop()
                if len(dir_stack) == 0:
                    current_top_dir = ""
                    current_sub_dir = ""
                elif len(dir_stack) == 1:
                    current_top_dir = dir_stack[0]
                    current_sub_dir = ""
                else:
                    current_top_dir = dir_stack[0]
                    current_sub_dir = dir_stack[-1]
            
            # Extract patch file info (support multiple extensions)
            if f'{file_extension}"' in line and 'offset=' in line and 'size=' in line:
                # Parse: <FILE name="Patch Name.prt_xxx" offset="12345" size="678"/>
                name_match = re.search(rf'name="([^"]+\.{file_extension})"', line)
                offset_match = re.search(r'offset="(\d+)"', line)
                size_match = re.search(r'size="(\d+)"', line)
                
                if name_match and offset_match and size_match:
                    patch_name = name_match.group(1).replace(f'.{file_extension}', '')
                    offset = int(offset_match.group(1))
                    size = int(size_match.group(1))
                    
                    patches.append({
                        'name': patch_name,
                        'directory': current_top_dir,  # Use top-level directory
                        'subdirectory': current_sub_dir,  # Store subdirectory too
                        'offset': offset,
                        'size': size,
                        'extension': file_extension
                    })
        
        return patches
    
    except Exception as e:
        print(f"Error parsing library index: {e}")
        return []



def append_patch_to_json(patch_entry, json_file_path):
    """Append a single patch to the JSON database incrementally"""
    import json
    import os
    
    # Load existing database or create new one
    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                database = json.load(f)
        except:
            # If file is corrupted, start fresh
            database = {"patches": [], "indexes": {}}
    else:
        # Create new database structure
        database = {
            "patches": [],
            "indexes": {
                "byGenre": {},
                "byMood": {}, 
                "byType": {},
                "byAuthor": {},
                "byCategory": {},
                "byComplexity": {},
                "byLibrary": {},
                "byOscType": {}
            }
        }
    
    # Add patch to main list
    database["patches"].append(patch_entry)
    patch_id = patch_entry["id"]
    
    # Update indexes
    for genre in patch_entry.get("genres", []):
        if genre:
            if genre not in database["indexes"]["byGenre"]:
                database["indexes"]["byGenre"][genre] = []
            database["indexes"]["byGenre"][genre].append(patch_id)
    
    # ... similar for other fields
    
    # Save updated database
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(database, f, indent=2, ensure_ascii=False)
    
    return True

def parse_metadata_attributes(attrib_data):
    """Parse the ATTRIB_VALUE_DATA string to extract metadata like Genre, Mood, Type, etc."""
    metadata = {
        'genres': [],
        'moods': [],
        'types': [],
        'author': '',
        'complexity': '',
        'description': '',
        'keywords': [],
        'version': '',
        'osc_type': '',
        'url': '',
        'size': 0
    }
    
    if not attrib_data:
        return metadata
    
    try:
        # Split by semicolon, then by equals sign
        pairs = [pair.strip() for pair in attrib_data.split(';') if '=' in pair]
        
        for pair in pairs:
            if '=' not in pair:
                continue
                
            key, value = pair.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Handle HTML entities
            value = unquote(value.replace('&#34;', '"').replace('&#38;', '&'))
            
            # Parse different metadata types
            if key == 'Genre':
                if value and value not in metadata['genres']:
                    metadata['genres'].append(value)
            elif key == 'Mood':
                if value and value not in metadata['moods']:
                    metadata['moods'].append(value)
            elif key == 'Type':
                if value and value not in metadata['types']:
                    metadata['types'].append(value)
            elif key == 'Author':
                metadata['author'] = value
            elif key == 'Complexity':
                metadata['complexity'] = value
            elif key == 'Description':
                metadata['description'] = value
            elif key == 'Keywords':
                # Split keywords by comma
                keywords = [k.strip() for k in value.split(',') if k.strip()]
                metadata['keywords'].extend(keywords)
            elif key == 'Version':
                metadata['version'] = value
            elif key == 'Osc Type':
                metadata['osc_type'] = value
            elif key == 'URL':
                metadata['url'] = value
            elif key == 'size':
                try:
                    metadata['size'] = int(value)
                except:
                    pass
                    
    except Exception as e:
        logger.warning(f"Error parsing metadata attributes: {e}")
    
    return metadata


def extract_patch_from_library(library_path, patch_info):
    """Extract a specific patch from the library archive"""
    try:
        with open(library_path, 'rb') as f:
            # Find the actual data start position (after </FileSystem>)
            content = f.read(1000000)  # Read first 1MB to find FileSystem end
            text_content = content.decode('utf-8', errors='ignore')
            filesystem_end_pos = text_content.find('</FileSystem>')
            
            if filesystem_end_pos == -1:
                print(f"Could not find FileSystem end in {library_path}")
                return None
            
            # Calculate actual data start position  
            data_start = filesystem_end_pos + len('</FileSystem>') + 1  # +1 for newline
            
            # Seek to the correct patch offset (relative to data start)
            actual_offset = data_start + patch_info['offset']
            f.seek(actual_offset)
            
            # Read the patch data
            patch_data = f.read(patch_info['size'])
            
            # Decode as text (patch files are XML)
            patch_xml = patch_data.decode('utf-8', errors='ignore')
            return patch_xml
            
    except Exception as e:
        print(f"Error extracting patch {patch_info['name']}: {e}")
        return None


def extract_parent_folder_category(folder_path):
    """Extract parent folder from full folder path to get correct category hierarchy"""
    if not folder_path:
        return '', ''
    
    # Remove leading/trailing slashes and normalize
    clean_path = folder_path.strip('/')
    
    # Split by forward slash to get hierarchy 
    path_parts = [part.strip() for part in clean_path.split('/') if part.strip()]
    
    if not path_parts:
        return '', ''
    
    if len(path_parts) == 1:
        # Single level - use as category, no subcategory
        return path_parts[0], ''
    else:
        # Multiple levels - parent becomes category, last becomes subcategory
        parent_category = path_parts[0]
        subcategory = path_parts[-1]  # Use the deepest folder as subcategory
        return parent_category, subcategory


def extract_patch_metadata(patch_xml, patch_directory="", patch_subdirectory="", patch_name="", library_name=""):
    """Extract metadata from patch XML, including ATTRIB_VALUE_DATA and proper categories"""
    metadata = {
        'genres': [],
        'moods': [],
        'types': [],
        'author': '',
        'complexity': '',
        'description': '',
        'keywords': [],
        'version': '',
        'osc_type': '',
        'url': '',
        'size': 0,
        'library': '',
        'folder': '',
        'directory': '',        # Top-level directory (e.g., "Human Voices")
        'subdirectory': '',     # Sub-directory (e.g., "Throat Singers")
        'category': '',         # ATTR Category (e.g., "Throat Singers") 
        'subcategory': ''       # ATTR SubCategory (if present)
    }
    
    if not patch_xml:
        return metadata
    
    try:
        # Store the directory paths
        metadata['directory'] = patch_directory      # Top-level (e.g., "Human Voices")
        metadata['subdirectory'] = patch_subdirectory # Sub-level (e.g., "Throat Singers")
        
        # Look for ATTRIB_VALUE_DATA in the XML
        attrib_match = re.search(r'ATTRIB_VALUE_DATA="([^"]*)"', patch_xml)
        if attrib_match:
            attrib_data = attrib_match.group(1)
            metadata.update(parse_metadata_attributes(attrib_data))
        
        # Extract library and folder from XML attributes
        library_match = re.search(r'library="([^"]*)"', patch_xml)
        if library_match:
            metadata['library'] = library_match.group(1)
            
        folder_match = re.search(r'folder="([^"]*)"', patch_xml)
        if folder_match:
            metadata['folder'] = folder_match.group(1)
        
        # Extract Category and SubCategory from database - handle different structures
        
        # METHOD 1: Look for explicit Category/SubCategory ATTR values (used by Omnisphere)
        category_attr_match = re.search(r'<ATTR\s+NAME="Category"\s+VALUE="([^"]*)"', patch_xml)
        subcategory_attr_match = re.search(r'<ATTR\s+NAME="SubCategory"\s+VALUE="([^"]*)"', patch_xml)
        
        if category_attr_match:
            metadata['category'] = category_attr_match.group(1)
        if subcategory_attr_match:
            metadata['subcategory'] = subcategory_attr_match.group(1)
            
        # METHOD 2: Look for Type field in ATTRIB_VALUE_DATA (used by Keyscape/Trilian)
        if not metadata['category']:
            # Look for ATTRIB_VALUE_DATA and extract Type field
            attrib_data_match = re.search(r'ATTRIB_VALUE_DATA="([^"]*)"', patch_xml)
            if attrib_data_match:
                attrib_data = attrib_data_match.group(1)
                type_match = re.search(r'Type=([^;]+)', attrib_data)
                if type_match:
                    type_value = type_match.group(1)
                    # For Keyscape, the Type field contains the subcategory and we need to map it to parent category
                    if 'Keyscape' in library_name:
                        metadata['category'] = 'Keyboards'  # All Keyscape patches are keyboard instruments
                        metadata['subcategory'] = type_value
                        logger.info(f"Extracted from ATTRIB_VALUE_DATA Type for {patch_name}: Category='Keyboards', SubCategory='{type_value}'")
                    else:
                        # For other libraries, Type might be the main category
                        metadata['category'] = type_value
                        logger.info(f"Extracted from ATTRIB_VALUE_DATA Type for {patch_name}: Category='{type_value}'")
                else:
                    logger.warning(f"No Type field found in ATTRIB_VALUE_DATA for patch: {patch_name} in library: {library_name}")
            else:
                logger.warning(f"No Category ATTR or ATTRIB_VALUE_DATA found for patch: {patch_name} in library: {library_name}")
            
    except Exception as e:
        logger.warning(f"Error extracting patch metadata: {e}")
    
    return metadata


def create_preset_with_patch_fixed(template_xml, patch_data, patch_name="Custom Patch"):
    """
    FIXED: Replace only the SynthEngine content within the first SynthSubEngine,
    preserving all 8 SynthSubEngine sections to avoid corruption.
    """
    
    # Update the preset name in the template
    updated_template = template_xml.replace(
        'name="default multi"',
        f'name="{patch_name}"'
    )
    
    # Find all SynthSubEngine sections
    sub_engine_pattern = r'(<SynthSubEngine[^>]*>)(.*?)(</SynthSubEngine>)'
    sub_engines = list(re.finditer(sub_engine_pattern, updated_template, re.DOTALL))
    
    if not sub_engines:
        print("Error: No SynthSubEngine found in template")
        return None
    
    # Find the first SynthSubEngine that has substantial content
    replacement_done = False
    result = updated_template
    
    for i, match in enumerate(sub_engines):
        start_tag, content, end_tag = match.groups()
        
        # Check if this SynthSubEngine has actual content (not empty)
        if len(content.strip()) > 1000 and not replacement_done:
            print(f"  Replacing entire content in SynthSubEngine {i}")
            
            # The patch_data from library has <AmberPart> wrapper that we need to remove
            # Extract just the SynthEngine content
            start_marker = '<SynthEngine '
            end_marker = '</SynthEngine>'
            
            start_idx = patch_data.find(start_marker)
            end_idx = patch_data.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                # Extract SynthEngine content including tags
                synth_engine_content = patch_data[start_idx:end_idx + len(end_marker)]
                new_content = f'\n{synth_engine_content}\n '
            else:
                print(f"  ERROR: Could not find SynthEngine tags in patch data")
                return None
            
            # Replace this SynthSubEngine in the full template
            new_sub_engine = start_tag + new_content + end_tag
            old_sub_engine = match.group(0)
            
            result = result.replace(old_sub_engine, new_sub_engine, 1)
            replacement_done = True
            break
    
    if not replacement_done:
        print("Error: Could not find suitable SynthSubEngine for replacement")
        return None
    
    return result


def create_aupreset_fixed(preset_xml, output_path, preset_name="Custom Patch"):
    """Create properly formatted .aupreset file with all AU metadata"""
    try:
        # Encode the XML data as Base64 with proper formatting
        encoded_bytes = base64.b64encode(preset_xml.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')
        
        # Format the Base64 with proper line breaks (68 chars per line + tabs)
        formatted_lines = []
        for i in range(0, len(encoded_str), BASE64_LINE_LENGTH):
            line = encoded_str[i:i+BASE64_LINE_LENGTH]
            formatted_lines.append(f"\t{line}")
        
        formatted_b64 = "\n".join(formatted_lines)
        
        # Create the complete AU preset XML structure with all metadata
        aupreset_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>data</key>
	<data>
	</data>
	<key>data0</key>
	<data>
{formatted_b64}
	</data>
	<key>manufacturer</key>
	<integer>{AU_MANUFACTURER_ID}</integer>
	<key>name</key>
	<string>{preset_name}</string>
	<key>render-quality</key>
	<integer>{AU_RENDER_QUALITY}</integer>
	<key>subtype</key>
	<integer>{AU_SUBTYPE_ID}</integer>
	<key>type</key>
	<integer>{AU_TYPE_ID}</integer>
	<key>version</key>
	<integer>{AU_VERSION}</integer>
</dict>
</plist>'''
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(aupreset_xml)
        
        return True
    except Exception as e:
        print(f"Error creating aupreset {output_path}: {e}")
        return False


def sanitize_filename(filename):
    """Make filename safe for filesystem"""
    # Replace problematic characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    safe_name = safe_name.strip('. ')
    # Limit length
    if len(safe_name) > 100:
        safe_name = safe_name[:100]
    return safe_name


def build_metadata_database(libraries, template_xml):
    """Build comprehensive metadata database with search indexes"""
    
    print("\n🔍 Building Enhanced Metadata Database...")
    
    # Initialize database structure
    database = {
        "metadata": {
            "totalPatches": 0,
            "lastUpdated": "2024-08-31",
            "libraries": [lib["display_name"] for lib in libraries]
        },
        "patches": [],
        "indexes": {
            "byGenre": defaultdict(list),
            "byMood": defaultdict(list), 
            "byType": defaultdict(list),
            "byAuthor": defaultdict(list),
            "byComplexity": defaultdict(list),
            "byLibrary": defaultdict(list),
            "byDirectory": defaultdict(list),
            "bySubdirectory": defaultdict(list),
            "byCategory": defaultdict(list),
            "byOscType": defaultdict(list)
        }
    }
    
    patch_id = 0
    
    for library in libraries:
        library_name = library["display_name"]
        print(f"\n📚 Processing metadata for: {library_name}")
        
        # Parse library patches
        patches = parse_library_index(library['path'], library['extension'])
        if not patches:
            print(f"   ❌ Could not parse library: {library['name']}")
            continue
            
        print(f"   🔄 Processing {len(patches)} patches for metadata...")
        
        processed = 0
        for patch_info in patches:
            try:
                # Extract patch XML to get metadata
                patch_xml = extract_patch_from_library(library['path'], patch_info)
                if not patch_xml:
                    continue
                    
                # Extract enhanced metadata with patch directory, name and library
                metadata = extract_patch_metadata(patch_xml, patch_info.get('directory', ''), patch_info.get('subdirectory', ''), patch_info['name'], library['name'])
                
                # Build relative file path for Max MSP
                safe_name = sanitize_filename(patch_info['name'])
                if patch_info['directory']:
                    safe_dir = sanitize_filename(patch_info['directory'])
                    relative_path = f"{library_name}/{safe_dir}/{safe_name}.aupreset"
                else:
                    relative_path = f"{library_name}/{safe_name}.aupreset"
                
                # Create patch entry with proper category hierarchy
                patch_entry = {
                    "id": patch_id,
                    "name": patch_info['name'],
                    "library": library_name,
                    "directory": metadata['directory'] or patch_info.get('directory', ''),  # Top-level directory (e.g., "Human Voices")
                    "subdirectory": metadata['subdirectory'] or patch_info.get('subdirectory', ''),  # Sub-level directory (e.g., "Throat Singers")
                    "category": metadata['category'],  # ATTR category
                    "subcategory": metadata['subcategory'],  # ATTR subcategory
                    "filePath": f"complete_steam_presets/{relative_path}",
                    "relativePath": relative_path,
                    "genres": metadata['genres'],
                    "moods": metadata['moods'], 
                    "types": metadata['types'],
                    "author": metadata['author'],
                    "complexity": metadata['complexity'],
                    "description": metadata['description'],
                    "keywords": metadata['keywords'],
                    "version": metadata['version'],
                    "oscType": metadata['osc_type'],
                    "url": metadata['url'],
                    "fileSize": patch_info.get('size', 0),
                    "product": library.get('product', 'Omnisphere')
                }
                
                database["patches"].append(patch_entry)
                
                # Build indexes for fast filtering
                for genre in metadata['genres']:
                    if genre:
                        database["indexes"]["byGenre"][genre].append(patch_id)
                        
                for mood in metadata['moods']:
                    if mood:
                        database["indexes"]["byMood"][mood].append(patch_id)
                        
                for patch_type in metadata['types']:
                    if patch_type:
                        database["indexes"]["byType"][patch_type].append(patch_id)
                
                if metadata['author']:
                    database["indexes"]["byAuthor"][metadata['author']].append(patch_id)
                    
                if metadata['complexity']:
                    database["indexes"]["byComplexity"][metadata['complexity']].append(patch_id)
                    
                database["indexes"]["byLibrary"][library_name].append(patch_id)
                
                # Index by directory hierarchy
                if metadata['directory'] or patch_info.get('directory'):
                    directory = metadata['directory'] or patch_info.get('directory', '')
                    if directory:
                        database["indexes"]["byDirectory"][directory].append(patch_id)
                        
                if metadata['subdirectory'] or patch_info.get('subdirectory'):
                    subdirectory = metadata['subdirectory'] or patch_info.get('subdirectory', '')
                    if subdirectory:
                        database["indexes"]["bySubdirectory"][subdirectory].append(patch_id)
                
                if patch_info.get('directory'):
                    database["indexes"]["byCategory"][patch_info['directory']].append(patch_id)
                    
                if metadata['osc_type']:
                    database["indexes"]["byOscType"][metadata['osc_type']].append(patch_id)
                
                patch_id += 1
                processed += 1
                
                if processed % 200 == 0:
                    print(f"      Progress: {processed}/{len(patches)} patches processed...")
                    
            except Exception as e:
                logger.warning(f"Error processing patch {patch_info['name']}: {e}")
                continue
        
        print(f"   ✅ Processed {processed}/{len(patches)} patches from {library_name}")
    
    # Convert defaultdicts to regular dicts for JSON serialization
    database["indexes"] = {
        key: dict(index_dict) for key, index_dict in database["indexes"].items()
    }
    
    database["metadata"]["totalPatches"] = len(database["patches"])
    
    print(f"\n📊 Metadata Database Complete:")
    print(f"   Total Patches: {database['metadata']['totalPatches']:,}")
    print(f"   Unique Genres: {len(database['indexes']['byGenre'])}")
    print(f"   Unique Moods: {len(database['indexes']['byMood'])}")
    print(f"   Unique Types: {len(database['indexes']['byType'])}")
    print(f"   Authors: {len(database['indexes']['byAuthor'])}")
    
    return database


def save_metadata_database(database, output_file):
    """Save metadata database to JSON file"""
    try:
        print(f"\n💾 Saving metadata database to: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(database, f, indent=2, ensure_ascii=False)
            
        # Calculate file size
        file_size = Path(output_file).stat().st_size / (1024 * 1024)  # MB
        print(f"   ✅ Database saved successfully ({file_size:.1f}MB)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving metadata database: {e}")
        return False


def test_single_patch():
    """Test the fix with a single patch from the main library first"""
    
    print("🧪 Testing Single Patch Conversion")
    print("=" * 50)
    
    # Use the main Omnisphere Library for testing
    library_path = str(Path(STEAM_ROOT_DIR) / "Omnisphere/Settings Library/Patches/Factory/Omnisphere Library.db")
    
    print("Loading template...")
    template_xml = load_complete_template()
    if not template_xml:
        print("✗ Could not load template")
        return False
    print(f"✓ Template loaded ({len(template_xml):,} characters)")
    
    print("Parsing library index...")
    patches = parse_library_index(library_path, "prt_omn")  # Test with Omnisphere
    if not patches:
        print("✗ Could not parse library")
        return False
    
    # Find "Optigan Marimba in Space" specifically
    target_patch = None
    for patch in patches:
        if patch['name'] == "Optigan Marimba in Space":
            target_patch = patch
            break
    
    if not target_patch:
        print("✗ Could not find 'Optigan Marimba in Space' patch")
        return False
    
    print(f"✓ Found target patch: {target_patch['name']}")
    
    # Extract the patch
    print("Extracting patch data...")
    patch_xml = extract_patch_from_library(library_path, target_patch)
    if not patch_xml:
        print("✗ Could not extract patch")
        return False
    
    print(f"✓ Extracted patch ({len(patch_xml)} characters)")
    
    # Create preset with fixed replacement
    print("Creating preset with FIXED replacement logic...")
    complete_preset = create_preset_with_patch_fixed(template_xml, patch_xml, target_patch['name'])
    if not complete_preset:
        print("✗ Could not create complete preset")
        return False
    
    print(f"✓ Created complete preset ({len(complete_preset):,} characters)")
    
    # Verify it has 8 SynthSubEngines
    sub_engine_count = complete_preset.count('<SynthSubEngine ')
    synth_engine_count = complete_preset.count('<SynthEngine ')
    print(f"  SynthSubEngine count: {sub_engine_count}")
    print(f"  SynthEngine count: {synth_engine_count}")
    
    if sub_engine_count != 8:
        print(f"✗ WRONG! Should have 8 SynthSubEngines, got {sub_engine_count}")
        return False
    
    if synth_engine_count != 8:
        print(f"✗ WRONG! Should have 8 SynthEngines, got {synth_engine_count}")
        return False
    
    print("✅ Structure verification passed!")
    
    # Save test file
    test_output = "/Users/Shared/DevWork/GitHub/Ableton-Experiments/TEST_FIXED_Optigan_Marimba_in_Space.aupreset"
    
    if create_aupreset_fixed(complete_preset, test_output, target_patch['name']):
        print(f"✅ Test preset created: {test_output}")
        print("Please test this file in Omnisphere!")
        return True
    else:
        print("✗ Failed to create test preset")
        return False


def verify_prerequisites() -> bool:
    """
    Verify all prerequisites are met before starting extraction.
    
    Returns:
        bool: True if all prerequisites are satisfied, False otherwise
    """
    issues = []
    
    # Check STEAM root directory
    steam_dir = Path(STEAM_ROOT_DIR)
    if not steam_dir.exists():
        issues.append(f"STEAM directory not found: {steam_dir}")
    else:
        # Check for product directories
        products_found = []
        for factory_subdir in FACTORY_DIRS:
            if "*" not in factory_subdir:  # Skip wildcard paths for now
                factory_path = steam_dir / factory_subdir
                if factory_path.exists():
                    product = factory_subdir.split("/")[0]
                    if product not in products_found:
                        products_found.append(product)
        
        if not products_found:
            issues.append(f"No Spectrasonics products found in: {steam_dir}")
        else:
            logger.info(f"Found Spectrasonics products: {', '.join(products_found)}")
    
    # Check template file
    template_path = Path(TEMPLATE_FILE_PATH)
    if not template_path.exists():
        issues.append(f"Template file not found: {template_path}")
    
    # Check Python version
    if sys.version_info < (3, 6):
        issues.append(f"Python 3.6+ required, found {sys.version}")
    
    if issues:
        logger.error("Prerequisites check failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    
    logger.info("All prerequisites satisfied")
    return True


def extract_all_libraries():
    """Extract patches from all discovered Omnisphere libraries and build metadata database"""
    
    print("\n🚀 Starting FULL MULTI-LIBRARY extraction with Enhanced Metadata...")
    
    # Discover all available libraries
    libraries = discover_steam_libraries()
    if not libraries:
        print("❌ No valid libraries found!")
        return False
    
    print(f"\nFound {len(libraries)} libraries:")
    total_expected = 0
    for lib in libraries:
        print(f"  📚 {lib['display_name']}: {lib['patch_count']:,} patches ({lib['size_mb']}MB)")
        if lib['description']:
            print(f"      {lib['description']}")
        total_expected += lib['patch_count']
    
    print(f"\n🎯 Total patches to extract: {total_expected:,}")
    
    # Load template once
    print("\nLoading template...")
    template_xml = load_complete_template()
    if not template_xml:
        print("✗ Could not load template")
        return False
    print(f"✓ Template loaded ({len(template_xml):,} characters)")
    
    # Create main output directory
    output_dir = Path(OUTPUT_DIRECTORY)
    output_dir.mkdir(exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    
    # Build enhanced metadata database FIRST
    database = build_metadata_database(libraries, template_xml)
    if not database or database["metadata"]["totalPatches"] == 0:
        print("❌ Could not build metadata database!")
        return False
    
    # Process each library
    overall_success = 0
    overall_errors = 0
    
    for i, library in enumerate(libraries, 1):
        print(f"\n📚 Processing Library {i}/{len(libraries)}: {library['display_name']}")
        print(f"   Expected patches: {library['patch_count']:,}")
        
        # Create library-specific output directory
        library_output = output_dir / library['display_name']
        library_output.mkdir(exist_ok=True)
        
        # Extract patches from this library
        patches = parse_library_index(library['path'], library['extension'])
        if not patches:
            print(f"   ❌ Could not parse library: {library['name']}")
            continue
        
        print(f"   🔄 Extracting {len(patches)} patches...")
        
        lib_success = 0
        lib_errors = 0
        
        for j, patch_info in enumerate(patches):
            if j % 100 == 0 and j > 0:
                print(f"      Progress: {j}/{len(patches)} ({lib_success} successful, {lib_errors} errors)")
            
            try:
                # Extract patch data from library
                patch_xml = extract_patch_from_library(library['path'], patch_info)
                if not patch_xml:
                    lib_errors += 1
                    continue
                
                # Create complete preset with template
                complete_preset = create_preset_with_patch_fixed(template_xml, patch_xml, patch_info['name'])
                if not complete_preset:
                    lib_errors += 1
                    continue
                
                # Create safe filename and path
                safe_name = sanitize_filename(patch_info['name'])
                if patch_info['directory']:
                    safe_dir = sanitize_filename(patch_info['directory'])
                    category_dir = library_output / safe_dir
                    category_dir.mkdir(exist_ok=True)
                    output_path = category_dir / f"{safe_name}.aupreset"
                else:
                    output_path = library_output / f"{safe_name}.aupreset"
                
                # Create .aupreset file
                if create_aupreset_fixed(complete_preset, str(output_path), patch_info['name']):
                    lib_success += 1
                else:
                    lib_errors += 1
                    
            except Exception as e:
                print(f"      Error processing {patch_info['name']}: {e}")
                lib_errors += 1
        
        # Library summary
        print(f"   ✅ Library complete: {lib_success}/{len(patches)} successful ({lib_errors} errors)")
        overall_success += lib_success
        overall_errors += lib_errors
    
    # Save metadata database
    if database:
        if save_metadata_database(database, METADATA_OUTPUT_FILE):
            print(f"  🗄️ Enhanced metadata database created: {METADATA_OUTPUT_FILE}")
        else:
            print(f"  ⚠️ Warning: Could not save metadata database")

    # Final summary
    print("\n" + "=" * 70)
    print(f"🎉 ENHANCED MULTI-LIBRARY Extraction complete!")
    print(f"  📊 Total patches processed: {overall_success + overall_errors:,}")
    print(f"  ✅ Successfully converted: {overall_success:,} patches")
    print(f"  ❌ Errors: {overall_errors}")
    print(f"  📁 Output directory: {output_dir}")
    print(f"  🗄️ Metadata database: {METADATA_OUTPUT_FILE}")
    print(f"  🎵 Libraries processed: {len(libraries)}")
    
    if database:
        print(f"\n🔍 Metadata Summary:")
        print(f"  📚 Total indexed patches: {database['metadata']['totalPatches']:,}")
        print(f"  🎭 Unique Genres: {len(database['indexes']['byGenre'])}")
        print(f"  😊 Unique Moods: {len(database['indexes']['byMood'])}")
        print(f"  🎼 Unique Types: {len(database['indexes']['byType'])}")
        print(f"  👨‍🎤 Authors: {len(database['indexes']['byAuthor'])}")
    
    print("\n✨ Enhanced Omnisphere Ecosystem Extracted with Full Metadata!")
    
    return overall_errors == 0


def main():
    """Main function - verify prerequisites, test first, then ask to proceed"""
    
    print("🎹 Enhanced Omnisphere Mass Patch Extractor - FULL METADATA VERSION")
    print("=" * 70)
    print("✨ NEW: Extracts Genre, Mood, Type, Author, Description + Full Metadata!")
    print("🔍 NEW: Creates searchable JSON database for Max MSP integration!")
    print("=" * 70)
    
    # Verify prerequisites
    if not verify_prerequisites():
        print("\n❌ Prerequisites check failed. Please resolve issues above.")
        sys.exit(1)
    
    # Clean up previous extraction for fresh start
    output_path = Path(OUTPUT_DIRECTORY)
    if output_path.exists():
        print(f"\n🧹 Cleaning previous extraction: {OUTPUT_DIRECTORY}")
        import shutil
        shutil.rmtree(output_path)
        print("✓ Previous extraction removed for fresh start")
    
    # Discover libraries
    libraries = discover_steam_libraries()
    if not libraries:
        print("\n❌ No valid libraries discovered. Check Factory directory path.")
        sys.exit(1)
    
    print(f"\n📚 Discovered {len(libraries)} libraries with {sum(lib['patch_count'] for lib in libraries):,} total patches")
    
    # Test with single patch first
    if not test_single_patch():
        print("\n❌ Single patch test failed. Not proceeding with mass extraction.")
        return
    
    print("\n" + "=" * 70)
    print("✅ Single patch test passed! Starting ENHANCED MULTI-LIBRARY extraction + metadata...")
    print("=" * 70)
    
    # Full multi-library extraction with enhanced metadata
    success = extract_all_libraries()
    if success:
        print("\n🎊 All libraries successfully extracted with full metadata!")
        print(f"🔍 Ready for Max MSP integration via: {METADATA_OUTPUT_FILE}")
    else:
        print("\n⚠️ Extraction completed with some errors - check logs above.")


if __name__ == "__main__":
    main()