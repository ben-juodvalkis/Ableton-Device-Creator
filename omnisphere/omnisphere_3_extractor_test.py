#!/usr/bin/env python3
"""
Omnisphere 3 Patch Extractor - TEST VERSION

Fixed version for Omnisphere 3 compatibility with:
- Corrected patch extraction (reads until complete XML)
- Enhanced hierarchy support
- New library definitions

Author: Claude Code Assistant
Date: October 2025
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

# Configuration Constants for TESTING
STEAM_ROOT_DIR = "/Users/Shared/Music/Soundbanks/Spectrasonics/STEAM"
TEMPLATE_FILE_PATH = "/Users/Shared/DevWork/GitHub/Looping/ableton/Presets/Empty Patches/Omnisphere.aupreset"
OUTPUT_DIRECTORY = "/Users/Shared/DevWork/GitHub/Looping/scripts/preset-extraction/spectrasonics/omnisphere/extraction/omnisphere_3_test_output"
METADATA_OUTPUT_FILE = "/Users/Shared/DevWork/GitHub/Looping/scripts/preset-extraction/spectrasonics/omnisphere/extraction/omnisphere_3_metadata_test.json"

# Enhanced Library Info with all Omnisphere 3 libraries
LIBRARY_INFO = {
    # Original Omnisphere Libraries
    "Omnisphere Library.db": {"expected_patches": 5799, "description": "Main Omnisphere Factory Library", "extension": "prt_omn", "product": "Omnisphere"},
    "Hardware Library.db": {"expected_patches": 1587, "description": "Hardware Synthesizers", "extension": "prt_omn", "product": "Omnisphere"},
    "Moog Tribute Library.db": {"expected_patches": 1343, "description": "Moog Synthesizer Tribute", "extension": "prt_omn", "product": "Omnisphere"},
    "Atmosphere Library.db": {"expected_patches": 1027, "description": "Atmospheric Textures", "extension": "prt_omn", "product": "Omnisphere"},
    "Spotlight - EDM.db": {"expected_patches": 813, "description": "Electronic Dance Music", "extension": "prt_omn", "product": "Omnisphere"},
    "A Taste of Omnisphere.db": {"expected_patches": 0, "description": "Demo Patches", "extension": "prt_omn", "product": "Omnisphere"},
    "VIP Library.db": {"expected_patches": 0, "description": "VIP Library", "extension": "prt_omn", "product": "Omnisphere"},
    
    # NEW Omnisphere 3 Libraries (18 additions)
    "Retro Vibes.db": {"expected_patches": 3321, "description": "Retro & Analog Synthesis", "extension": "prt_omn", "product": "Omnisphere"},
    "Electronic Production.db": {"expected_patches": 2625, "description": "Electronic Music Production", "extension": "prt_omn", "product": "Omnisphere"},
    "Analog Vibes.db": {"expected_patches": 2364, "description": "Retro & Analog Synthesis", "extension": "prt_omn", "product": "Omnisphere"},
    "Scoring Electronic.db": {"expected_patches": 2348, "description": "Electronic Music Production", "extension": "prt_omn", "product": "Omnisphere"},
    "Electronic Underground.db": {"expected_patches": 2015, "description": "Electronic Music Production", "extension": "prt_omn", "product": "Omnisphere"},
    "Scoring Organic.db": {"expected_patches": 1889, "description": "Film Scoring & Organic", "extension": "prt_omn", "product": "Omnisphere"},
    "Ambient Dreams.db": {"expected_patches": 1575, "description": "Ambient & Atmospheric", "extension": "prt_omn", "product": "Omnisphere"},
    "SFX Electronic.db": {"expected_patches": 1504, "description": "Electronic Music Production", "extension": "prt_omn", "product": "Omnisphere"},
    "Warm Tones.db": {"expected_patches": 1191, "description": "Ambient & Atmospheric", "extension": "prt_omn", "product": "Omnisphere"},
    "Hard Edges.db": {"expected_patches": 1150, "description": "Hard & Aggressive", "extension": "prt_omn", "product": "Omnisphere"},
    "Live Keyboardist.db": {"expected_patches": 1068, "description": "Instrument Collections", "extension": "prt_omn", "product": "Omnisphere"},
    "Club Land.db": {"expected_patches": 1057, "description": "Electronic Music Production", "extension": "prt_omn", "product": "Omnisphere"},
    "Instruments Collection.db": {"expected_patches": 909, "description": "Instrument Collections", "extension": "prt_omn", "product": "Omnisphere"},
    "Classic Digital.db": {"expected_patches": 849, "description": "Retro & Analog Synthesis", "extension": "prt_omn", "product": "Omnisphere"},
    "Experimental Organic.db": {"expected_patches": 705, "description": "Film Scoring & Organic", "extension": "prt_omn", "product": "Omnisphere"},
    "SFX Organic.db": {"expected_patches": 655, "description": "Film Scoring & Organic", "extension": "prt_omn", "product": "Omnisphere"},
    "Vocal Collection.db": {"expected_patches": 599, "description": "Vocal & Human Sounds", "extension": "prt_omn", "product": "Omnisphere"},
    "Organic Vibes.db": {"expected_patches": 597, "description": "Film Scoring & Organic", "extension": "prt_omn", "product": "Omnisphere"},
    
    # Trilian Libraries
    "Trilian Library.db": {"expected_patches": 1083, "description": "Main Trilian Bass Library", "extension": "prt_trl", "product": "Trilian"},
    "Trilogy Library.db": {"expected_patches": 582, "description": "Legacy Trilogy Library", "extension": "prt_trl", "product": "Trilian"},
    "XTRA - Bass Legends.db": {"expected_patches": 35, "description": "Bass Legends Expansion", "extension": "prt_trl", "product": "Trilian"},
    "Trilian Creative.db": {"expected_patches": 216, "description": "Creative Bass Patches", "extension": "prt_omn", "product": "Trilian"},
    "Trilian VIP.db": {"expected_patches": 0, "description": "VIP Bass Library", "extension": "prt_trl", "product": "Trilian"},
    
    # Keyscape Libraries
    "Keyscape Library.db": {"expected_patches": 466, "description": "Main Keyscape Piano Library", "extension": "prt_key", "product": "Keyscape"},
    "Keyscape Creative.db": {"expected_patches": 1523, "description": "Creative Piano Patches", "extension": "prt_omn", "product": "Keyscape"},
    
    # Sonic Extensions
    "Nylon Sky.db": {"expected_patches": 57, "description": "Nylon Sky Extension", "extension": "prt_omn", "product": "Sonic Extensions"}
}

# AU Preset Constants
AU_MANUFACTURER_ID = 1196381015
AU_SUBTYPE_ID = 1097687666
AU_TYPE_ID = 1635085685
AU_VERSION = 0
AU_RENDER_QUALITY = 127
BASE64_LINE_LENGTH = 68

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_template_from_aupreset() -> Optional[str]:
    """Load template from existing .aupreset file"""
    try:
        template_path = Path(TEMPLATE_FILE_PATH)
        if not template_path.exists():
            logger.error(f"Template file not found: {template_path}")
            return None
        
        logger.info(f"Loading template from: {template_path}")
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
                
                template_xml = base64.b64decode(encoded_data).decode('utf-8')
                logger.info(f"Template loaded successfully ({len(template_xml):,} characters)")
                return template_xml
        
        logger.error("Template data0 section not found")
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
        dir_stack = []  # Full directory path stack
        
        for line in lines:
            line = line.strip()
            
            # Track directory opening
            if '<DIR name="' in line:
                dir_match = re.search(r'<DIR name="([^"]+)"', line)
                if dir_match:
                    dir_name = dir_match.group(1)
                    dir_stack.append(dir_name)
            
            # Track directory closing
            elif '</DIR>' in line and dir_stack:
                dir_stack.pop()
            
            # Extract patch files with full hierarchy
            elif f'{file_extension}"' in line and 'offset=' in line and 'size=' in line:
                name_match = re.search(rf'name="([^"]+\.{file_extension})"', line)
                offset_match = re.search(r'offset="(\d+)"', line)
                size_match = re.search(r'size="(\d+)"', line)
                
                if name_match and offset_match and size_match:
                    patch_name = name_match.group(1).replace(f'.{file_extension}', '')
                    offset = int(offset_match.group(1))
                    size = int(size_match.group(1))
                    
                    # Enhanced hierarchy representation
                    full_path = dir_stack.copy() if dir_stack else []
                    
                    patches.append({
                        'name': patch_name,
                        'full_hierarchy': full_path,
                        'depth': len(full_path),
                        'level1': full_path[0] if len(full_path) >= 1 else '',
                        'level2': full_path[1] if len(full_path) >= 2 else '',
                        'level3': full_path[2] if len(full_path) >= 3 else '',
                        'level4': full_path[3] if len(full_path) >= 4 else '',
                        'path_string': ' → '.join(full_path),
                        'directory': full_path[0] if len(full_path) >= 1 else '',  # Legacy compatibility
                        'subdirectory': full_path[1] if len(full_path) >= 2 else '',  # Legacy compatibility
                        'offset': offset,
                        'size': size,
                        'extension': file_extension
                    })
        
        return patches
    
    except Exception as e:
        logger.error(f"Error parsing library index: {e}")
        return []


def extract_patch_from_library_fixed(library_path, patch_info):
    """FIXED: Find actual patch data start and extract complete patches"""
    try:
        with open(library_path, 'rb') as f:
            # Find the actual start of patch data by locating first <AmberPart>
            content = f.read(3000000)  # Read 3MB to find patch data start
            
            # Find first <AmberPart> tag - this is where patch data actually starts
            first_amber_pos = content.find(b'<AmberPart>')
            if first_amber_pos == -1:
                logger.error(f"Could not find any patch data in {library_path}")
                return None
            
            # Calculate actual patch position
            actual_offset = first_amber_pos + patch_info['offset']
            
            # Read until complete XML structure
            f.seek(actual_offset)
            
            patch_data = b''
            chunk_size = 8192
            max_read = 200000  # Safety limit: 200KB max per patch
            
            while len(patch_data) < max_read:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                patch_data += chunk
                
                # Check if we have complete structure
                if b'</AmberPart>' in patch_data:
                    # Find the actual end position
                    end_pos = patch_data.find(b'</AmberPart>') + len(b'</AmberPart>')
                    complete_patch_data = patch_data[:end_pos]
                    
                    # Decode and return
                    patch_xml = complete_patch_data.decode('utf-8', errors='ignore')
                    logger.debug(f"Extracted complete patch: {len(patch_xml)} chars")
                    return patch_xml
            
            # Fallback: if no </AmberPart> found, use what we have
            patch_xml = patch_data.decode('utf-8', errors='ignore')
            logger.warning(f"No </AmberPart> found, using available data: {len(patch_xml)} chars")
            return patch_xml
            
    except Exception as e:
        logger.error(f"Error extracting patch {patch_info['name']}: {e}")
        return None


def create_preset_with_patch_fixed(template_xml, patch_data, patch_name="Custom Patch"):
    """Create preset using the fixed template system"""
    
    # Update the preset name in the template
    updated_template = template_xml.replace(
        'name="default multi"',
        f'name="{patch_name}"'
    )
    
    # Find all SynthSubEngine sections
    sub_engine_pattern = r'(<SynthSubEngine[^>]*>)(.*?)(</SynthSubEngine>)'
    sub_engines = list(re.finditer(sub_engine_pattern, updated_template, re.DOTALL))
    
    if not sub_engines:
        logger.error("No SynthSubEngine found in template")
        return None
    
    # Find the first SynthSubEngine that has substantial content
    replacement_done = False
    result = updated_template
    
    for i, match in enumerate(sub_engines):
        start_tag, content, end_tag = match.groups()
        
        # Check if this SynthSubEngine has actual content (not empty)
        if len(content.strip()) > 1000 and not replacement_done:
            logger.debug(f"Replacing entire content in SynthSubEngine {i}")
            
            # Extract SynthEngine content from patch data
            start_marker = '<SynthEngine'
            end_marker = '</SynthEngine>'
            
            start_idx = patch_data.find(start_marker)
            end_idx = patch_data.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                # Extract SynthEngine content including tags
                synth_engine_content = patch_data[start_idx:end_idx + len(end_marker)]
                new_content = f'\n{synth_engine_content}\n '
            else:
                logger.error(f"Could not find SynthEngine tags in patch data")
                return None
            
            # Replace this SynthSubEngine in the full template
            new_sub_engine = start_tag + new_content + end_tag
            old_sub_engine = match.group(0)
            
            result = result.replace(old_sub_engine, new_sub_engine, 1)
            replacement_done = True
            break
    
    if not replacement_done:
        logger.error("Could not find suitable SynthSubEngine for replacement")
        return None
    
    return result


def create_clean_aupreset(preset_xml, output_path, preset_name="Custom Patch"):
    """Create .aupreset file with custom host automation mappings"""
    try:
        # Apply custom mappings first
        enhanced_preset_xml = apply_custom_mappings_to_preset(preset_xml)
        
        # Encode the enhanced XML data as Base64 with proper formatting
        encoded_bytes = base64.b64encode(enhanced_preset_xml.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')
        
        # Format the Base64 with proper line breaks
        formatted_lines = []
        for i in range(0, len(encoded_str), BASE64_LINE_LENGTH):
            line = encoded_str[i:i+BASE64_LINE_LENGTH]
            formatted_lines.append(f"\t{line}")
        
        formatted_b64 = "\n".join(formatted_lines)
        
        # Host automation data (from your mapped file)
        host_automation_data = """AAAAAAAAAAAAAAIAAAAAAAAAAAAAAAABAAAAAAAAAAIAAAAAAAAAAwAAAAAAAAAEAAAA
\tAAAAAAUAAAAAAAAABgAAAAAAAAAHAAAAAAAAAAgAAAAAAAAACQAAAAAAAAAKAAAAAAAA
\tAAsAAAAAAAAADAAAAAAAAAANAAAAAAAAAA4AAAAAAAAADwAAAAAAAAAQAAAAAAAAABEA
\tAAAAAAAAEgAAAAAAAAATAAAAAAAAABQAAAAAAAAAFQAAAAAAAAAWAAAAAAAAABcAAAAA
\tAAAAGAAAAAAAAAAZAAAAAAAAABoAAAAAAAAAGwAAAAAAAAAcAAAAAAAAAB0AAAAAAAAA
\tHgAAAAAAAAAfAAAAAAAAACAAAAAAAAAAIQAAAAAAAAAiAAAAAAAAACMAAAAAAAAAJAAA
\tAAAAAAAlAAAAAAAAACYAAAAAAAAAJwAAAAAAAAAoAAAAAAAAACkAAAAAAAAAKgAAAAAA
\tAAArAAAAAAAAACwAAAAAAAAALQAAAAAAAAAuAAAAAAAAAC8AAAAAAAAAMAAAAAAAAAAx
\tAAAAAAAAADIAAAAAAAAAMwAAAAAAAAA0AAAAAAAAADUAAAAAAAAANgAAAAAAAAA3AAAA
\tAAAAADgAAAAAAAAAOQAAAAAAAAA6AAAAAAAAADsAAAAAAAAAPAAAAAAAAAA9AAAAAAAA
\tAD4AAAAAAAAAPwAAAAAAAABAAAAAAAAAAEEAAAAAAAAAQgAAAAAAAABDAAAAAAAAAEQA
\tAAAAAAAARQAAAAAAAABGAAAAAAAAAEcAAAAAAAAASAAAAAAAAABJAAAAAAAAAEoAAAAA
\tAAAASwAAAAAAAABMAAAAAAAAAE0AAAAAAAAATgAAAAAAAABPAAAAAAAAAFAAAAAAAAAA
\tUQAAAAAAAABSAAAAAAAAAFMAAAAAAAAAVAAAAAAAAABVAAAAAAAAAFYAAAAAAAAAVwAA
\tAAAAAABYAAAAAAAAAFkAAAAAAAAAWgAAAAAAAABbAAAAAAAAAFwAAAAAAAAAXQAAAAAA
\tAABeAAAAAAAAAF8AAAAAAAAAYAAAAAAAAABhAAAAAAAAAGIAAAAAAAAAYwAAAAAAAABk
\tAAAAAAAAAGUAAAAAAAAAZgAAAAAAAABnAAAAAAAAAGgAAAAAAAAAaQAAAAAAAABqAAAA
\t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
\tAAAAAAAAf0AAAAAAAAB/gAAAAAAAAH/AAAAAA=="""
        
        # Create the complete AU preset XML structure with custom mappings
        aupreset_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>data</key>
\t<data>
{host_automation_data}
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
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(aupreset_xml)
        
        return True
    except Exception as e:
        logger.error(f"Error creating aupreset {output_path}: {e}")
        return False


def apply_custom_mappings_to_preset(preset_xml):
    """Apply custom host automation mappings and expanded pitch bend to preset XML"""
    
    # Apply expanded pitch bend range (48 semitones = 4 octaves)
    if 'MpeBendRange=' in preset_xml:
        # Replace existing MpeBendRange
        enhanced_xml = re.sub(
            r'MpeBendRange="[^"]*"', 
            'MpeBendRange="48"', 
            preset_xml
        )
        logger.debug("Replaced existing MpeBendRange with 48 semitones")
    else:
        # Add MpeBendRange to MIDIEXPRESSION section
        mpe_pattern = r'(<MIDIEXPRESSION[^>]*?)([ >])'
        match = re.search(mpe_pattern, preset_xml)
        if match:
            # Insert before closing or next attribute
            enhanced_xml = re.sub(
                mpe_pattern,
                r'\1 MpeBendRange="48"\2',
                preset_xml
            )
            logger.debug("Added MpeBendRange=\"48\" to MIDIEXPRESSION section")
        else:
            logger.warning("No MIDIEXPRESSION section found for pitch bend application")
            enhanced_xml = preset_xml
    
    return enhanced_xml


def sanitize_filename(filename):
    """Make filename safe for filesystem"""
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_name = safe_name.strip('. ')
    if len(safe_name) > 100:
        safe_name = safe_name[:100]
    return safe_name


def test_single_library(library_name="Analog Vibes.db"):
    """Test extraction with a single library"""
    
    print(f"🧪 Testing Omnisphere 3 Extraction with {library_name}")
    print("=" * 60)
    
    # Create output directory
    output_dir = Path(OUTPUT_DIRECTORY)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load template
    print("1. Loading template...")
    template_xml = load_template_from_aupreset()
    if not template_xml:
        print("❌ Could not load template")
        return False
    print(f"✅ Template loaded ({len(template_xml):,} characters)")
    
    # Find library
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
    
    # Show hierarchy examples
    print("\n📊 Hierarchy Examples:")
    depth_examples = {}
    for patch in patches:
        depth = patch['depth']
        if depth not in depth_examples and len(depth_examples) < 3:
            depth_examples[depth] = patch
    
    for depth, patch in sorted(depth_examples.items()):
        print(f"  Depth {depth}: {patch['path_string']} → {patch['name'][:40]}...")
    
    # Test extraction with first few patches
    print(f"\n3. Testing extraction (first 5 patches)...")
    lib_output_dir = output_dir / library_name.replace('.db', '')
    lib_output_dir.mkdir(exist_ok=True)
    
    success_count = 0
    for i, patch in enumerate(patches[:5]):
        try:
            print(f"   Testing patch {i+1}: {patch['name'][:50]}...")
            
            # Extract patch
            patch_xml = extract_patch_from_library_fixed(library_path, patch)
            if not patch_xml:
                print(f"   ❌ Failed to extract patch XML")
                continue
            
            # Check if complete
            has_closing = '</SynthEngine>' in patch_xml and '</AmberPart>' in patch_xml
            print(f"   📄 Extracted {len(patch_xml)} chars, complete: {'✅' if has_closing else '❌'}")
            
            if not has_closing:
                print(f"   ⚠️  Patch incomplete, but continuing...")
            
            # Create preset
            complete_preset = create_preset_with_patch_fixed(template_xml, patch_xml, patch['name'])
            if not complete_preset:
                print(f"   ❌ Failed to create preset")
                continue
            
            # Create output path with hierarchy
            safe_name = sanitize_filename(patch['name'])
            if patch['level1']:
                safe_dir = sanitize_filename(patch['level1'])
                category_dir = lib_output_dir / safe_dir
                category_dir.mkdir(exist_ok=True)
                
                if patch['level2']:
                    safe_subdir = sanitize_filename(patch['level2'])
                    subcategory_dir = category_dir / safe_subdir
                    subcategory_dir.mkdir(exist_ok=True)
                    output_path = subcategory_dir / f"{safe_name}.aupreset"
                else:
                    output_path = category_dir / f"{safe_name}.aupreset"
            else:
                output_path = lib_output_dir / f"{safe_name}.aupreset"
            
            # Create clean .aupreset file (no automation yet)
            if create_clean_aupreset(complete_preset, str(output_path), patch['name']):
                file_size = Path(output_path).stat().st_size
                print(f"   ✅ Created: {output_path.name} ({file_size:,} bytes)")
                success_count += 1
            else:
                print(f"   ❌ Failed to write .aupreset file")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n🎉 Test Results:")
    print(f"   Success: {success_count}/5 patches")
    print(f"   Output: {lib_output_dir}")
    
    if success_count > 0:
        print(f"\n✅ Omnisphere 3 extraction is working!")
        print(f"Ready for full library extraction.")
        return True
    else:
        print(f"\n❌ Extraction failed. Check errors above.")
        return False


if __name__ == "__main__":
    # Test with Analog Vibes library
    test_single_library("Analog Vibes.db")