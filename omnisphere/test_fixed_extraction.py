#!/usr/bin/env python3
"""Test the fixed extraction for all three products"""

import sys
sys.path.append('.')
from omnisphere_3_full_extractor import *

def test_all_products():
    print("🧪 Testing Fixed Extraction for All Products")
    print("=" * 50)
    
    # Load template
    template_xml = load_template_from_aupreset()
    if not template_xml:
        print("❌ Could not load template")
        return
    
    test_cases = [
        {
            'product': 'Omnisphere',
            'library': '/Users/Shared/Music/Soundbanks/Spectrasonics/STEAM/Omnisphere/Settings Library/Patches/Factory/Club Land.db',
            'extension': 'prt_omn'
        },
        {
            'product': 'Keyscape', 
            'library': '/Users/Shared/Music/Soundbanks/Spectrasonics/STEAM/Keyscape/Settings Library/Patches/Factory/Keyscape Library.db',
            'extension': 'prt_key'
        },
        {
            'product': 'Trilian',
            'library': '/Users/Shared/Music/Soundbanks/Spectrasonics/STEAM/Trilian/Settings Library/Patches/Factory/Trilian Library.db', 
            'extension': 'prt_trl'
        }
    ]
    
    for test in test_cases:
        product = test['product']
        library_path = test['library']
        extension = test['extension']
        
        print(f"\n🔄 Testing {product}...")
        
        if not Path(library_path).exists():
            print(f"   ❌ Library not found: {library_path}")
            continue
            
        # Parse patches
        patches = parse_library_index_enhanced(library_path, extension)
        if not patches:
            print(f"   ❌ Could not parse library")
            continue
            
        print(f"   📊 Found {len(patches)} patches")
        
        # Test first patch
        if patches:
            patch = patches[0]
            original_name = patch['name']
            clean_name = clean_patch_name(original_name)
            
            print(f"   🎵 Testing: \"{original_name}\"")
            print(f"   🧹 Cleaned: \"{clean_name}\"")
            
            # Try extraction
            patch_xml = extract_patch_from_library_fixed(library_path, patch, product)
            if patch_xml:
                print(f"   ✅ Extracted {len(patch_xml)} chars")
                
                # Try creating preset
                complete_preset = create_preset_with_patch_fixed(template_xml, patch_xml, clean_name, product)
                if complete_preset:
                    print(f"   ✅ Created preset ({len(complete_preset):,} chars)")
                else:
                    print(f"   ❌ Failed to create preset")
            else:
                print(f"   ❌ Failed to extract patch")

if __name__ == "__main__":
    test_all_products()