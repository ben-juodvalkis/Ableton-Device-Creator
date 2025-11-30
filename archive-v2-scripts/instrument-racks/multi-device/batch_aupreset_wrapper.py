#!/usr/bin/env python3
"""
Batch processing script to wrap multiple Komplete Kontrol aupreset files in drum racks
"""

import sys
import os
import binascii
import xml.etree.ElementTree as ET
from pathlib import Path
import re

# Add utils directory to path
sys.path.append(str(Path(__file__).parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg

def read_aupreset_file(aupreset_path):
    """Read and return the aupreset file content"""
    with open(aupreset_path, 'r', encoding='utf-8') as f:
        return f.read()

def hex_encode_aupreset(aupreset_content):
    """Convert aupreset content to hex string for embedding"""
    # Convert string to bytes, then to hex
    aupreset_bytes = aupreset_content.encode('utf-8')
    hex_string = binascii.hexlify(aupreset_bytes).decode('ascii')
    
    # Format as groups of 64 characters with tabs and newlines (Ableton format)
    formatted_hex = []
    for i in range(0, len(hex_string), 64):
        chunk = hex_string[i:i+64]
        formatted_hex.append('\t\t\t' + chunk.upper())
    
    return '\n'.join(formatted_hex) + '\n\t\t\t'

def extract_preset_info_from_aupreset(aupreset_content):
    """Extract name and manufacturer from aupreset content"""
    try:
        # Look for the name string
        name_match = re.search(r'<key>name</key>\s*<string>([^<]+)</string>', aupreset_content)
        name = name_match.group(1) if name_match else "Komplete Kontrol"
        
        # Look for manufacturer
        manufacturer_match = re.search(r'<key>manufacturer</key>\s*<integer>([^<]+)</integer>', aupreset_content)
        manufacturer = manufacturer_match.group(1) if manufacturer_match else "760105261"
        
        return name, manufacturer
    except Exception as e:
        print(f"Warning: Could not extract preset info: {e}")
        return "Komplete Kontrol", "760105261"

def create_aupreset_xml(hex_buffer, preset_name="Komplete Kontrol", manufacturer="760105261"):
    """Create the AuPreset XML structure (based on working KK drum rack)"""
    au_preset_xml = f'''<AuPreset Id="0">
						<OverwriteProtectionNumber Value="3075" />
						<MpeEnabled Value="2" />
						<MpeSettings>
							<ZoneType Value="0" />
							<FirstNoteChannel Value="1" />
							<LastNoteChannel Value="15" />
						</MpeSettings>
						<ParameterSettings />
						<IsOn Value="true" />
						<PowerMacroControlIndex Value="-1" />
						<PowerMacroMappingRange>
							<Min Value="64" />
							<Max Value="127" />
						</PowerMacroMappingRange>
						<IsFolded Value="false" />
						<StoredAllParameters Value="true" />
						<DeviceLomId Value="0" />
						<DeviceViewLomId Value="0" />
						<IsOnLomId Value="0" />
						<ParametersListWrapperLomId Value="0" />
						<Buffer>
{hex_buffer}
						</Buffer>
						<PresetRef>
							<FilePresetRef Id="0">
								<FileRef>
									<RelativePathType Value="1" />
									<RelativePath Value="../../Library/Caches/Ableton/Presets/AudioUnits/Native Instruments/Komplete Kontrol/Default.aupreset" />
									<Path Value="/Users/Music/Library/Caches/Ableton/Presets/AudioUnits/Native Instruments/Komplete Kontrol/Default.aupreset" />
									<Type Value="2" />
									<LivePackName Value="" />
									<LivePackId Value="" />
									<OriginalFileSize Value="0" />
									<OriginalCrc Value="0" />
									<SourceHint Value="" />
								</FileRef>
							</FilePresetRef>
						</PresetRef>
						<Name Value="{preset_name}" />
						<Manufacturer Value="{manufacturer}" />
						<SubType Value="1315523403" />
						<Type Value="1635085685" />
						<Version Value="0" />
						<UniqueId Value="1315523403" />
					</AuPreset>'''
    
    return au_preset_xml

def inject_aupreset_into_drum_rack(empty_rack_path, aupreset_path, output_path):
    """Main function to inject aupreset into drum rack"""
    
    # Decode the empty drum rack
    drum_rack_xml = decode_adg(empty_rack_path)
    
    # Read the aupreset content
    aupreset_content = read_aupreset_file(aupreset_path)
    
    # Extract preset info
    preset_name, manufacturer = extract_preset_info_from_aupreset(aupreset_content)
    
    # Convert aupreset to hex
    hex_buffer = hex_encode_aupreset(aupreset_content)
    
    # Create the AuPreset XML
    aupreset_xml = create_aupreset_xml(hex_buffer, preset_name, manufacturer)
    
    # Find the DevicePresets section within the DrumBranchPreset
    # Find the DevicePresets section (which should be empty: <DevicePresets />)
    device_presets_pattern = r'<DevicePresets\s*/>'
    device_presets_match = re.search(device_presets_pattern, drum_rack_xml)
    
    if not device_presets_match:
        # Try to find non-empty DevicePresets
        device_presets_pattern_alt = r'(<DevicePresets>)(.*?)(</DevicePresets>)'
        device_presets_match = re.search(device_presets_pattern_alt, drum_rack_xml, re.DOTALL)
        
        if device_presets_match:
            # Replace the content with our AuPreset
            replacement = f'{device_presets_match.group(1)}\n\t\t\t\t\t{aupreset_xml}\n\t\t\t\t{device_presets_match.group(3)}'
            modified_xml = drum_rack_xml.replace(device_presets_match.group(0), replacement)
        else:
            raise Exception("Could not find DevicePresets section in drum rack")
    else:
        # Replace the self-closing tag with opening/closing tags containing our AuPreset
        replacement = f'<DevicePresets>\n\t\t\t\t\t{aupreset_xml}\n\t\t\t\t</DevicePresets>'
        modified_xml = drum_rack_xml.replace(device_presets_match.group(0), replacement)
    
    # Encode back to ADG
    encode_adg(modified_xml, output_path)
    
    return output_path

def get_clean_filename(aupreset_path):
    """Get a clean filename for the output drum rack"""
    filename = Path(aupreset_path).stem
    # Remove BPM info and clean up
    clean_name = re.sub(r'\s*\(\d+\s*bpm\)', '', filename, flags=re.IGNORECASE)
    # Replace any remaining problematic characters
    clean_name = re.sub(r'[^\w\s-]', '', clean_name)
    return clean_name.strip()

def batch_process_directory(aupreset_directory, empty_rack_path, output_directory=None, 
                           in_place=False, overwrite=False, backup_originals=False):
    """Process all aupreset files in a directory"""
    
    aupreset_dir = Path(aupreset_directory)
    empty_rack = Path(empty_rack_path)
    
    if not aupreset_dir.exists():
        raise FileNotFoundError(f"Aupreset directory not found: {aupreset_dir}")
    if not empty_rack.exists():
        raise FileNotFoundError(f"Empty drum rack template not found: {empty_rack}")
    
    # Set up output directory
    if in_place:
        output_dir = aupreset_dir
        print(f"Converting in-place: {output_dir}")
    elif output_directory:
        output_dir = Path(output_directory)
        output_dir.mkdir(exist_ok=True)
        print(f"Output directory: {output_dir}")
    else:
        output_dir = aupreset_dir.parent / f"{aupreset_dir.name} - Drum Racks"
        output_dir.mkdir(exist_ok=True)
        print(f"Output directory: {output_dir}")
    
    # Set up backup directory if needed
    backup_dir = None
    if backup_originals and in_place:
        backup_dir = aupreset_dir / ".aupreset-backup"
        backup_dir.mkdir(exist_ok=True)
        print(f"Backup directory: {backup_dir}")
    
    # Find all aupreset files
    aupreset_files = list(aupreset_dir.glob("*.aupreset"))
    
    if not aupreset_files:
        print("No .aupreset files found in directory")
        return
    
    print(f"Found {len(aupreset_files)} aupreset files to process")
    
    # Process each file
    results = []
    errors = []
    skipped = []
    backed_up = []
    
    for i, aupreset_file in enumerate(aupreset_files, 1):
        try:
            # Create output filename
            clean_name = get_clean_filename(aupreset_file)
            output_file = output_dir / f"{clean_name}.adg"
            
            # Check if output file already exists
            if output_file.exists() and not overwrite:
                skip_msg = f"[{i:2d}/{len(aupreset_files)}] Skipping: {aupreset_file.name} (drum rack already exists)"
                print(f"⏭️  {skip_msg}")
                skipped.append(aupreset_file.name)
                continue
            
            print(f"[{i:2d}/{len(aupreset_files)}] Processing: {aupreset_file.name}")
            print(f"           → {output_file.name}")
            
            # Backup original if requested
            if backup_originals and backup_dir:
                backup_path = backup_dir / aupreset_file.name
                aupreset_file.rename(backup_path)
                backed_up.append(aupreset_file.name)
                print(f"           📁 Backed up to: {backup_path.name}")
                # Update reference to use backup path for processing
                source_file = backup_path
            else:
                source_file = aupreset_file
            
            # Process the file
            result_path = inject_aupreset_into_drum_rack(empty_rack, source_file, output_file)
            results.append(result_path)
            
        except Exception as e:
            error_msg = f"Error processing {aupreset_file.name}: {e}"
            print(f"❌ {error_msg}")
            errors.append(error_msg)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Successfully processed: {len(results)} files")
    if skipped:
        print(f"⏭️  Skipped (already exist): {len(skipped)} files")
        if len(skipped) <= 5:
            for skip in skipped:
                print(f"   • {skip}")
        else:
            print(f"   • {skipped[0]} (and {len(skipped)-1} more...)")
    if backed_up:
        print(f"📁 Backed up originals: {len(backed_up)} files")
    if errors:
        print(f"❌ Errors: {len(errors)} files")
        for error in errors:
            print(f"   • {error}")
    
    if in_place:
        print(f"\nConverted in directory: {output_dir}")
        if backup_dir and backed_up:
            print(f"Original aupresets backed up to: {backup_dir}")
    else:
        print(f"\nOutput directory: {output_dir}")
    
    return results, errors, skipped, backed_up

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch process Komplete Kontrol aupreset files into drum racks')
    parser.add_argument('aupreset_directory', help='Directory containing .aupreset files')
    parser.add_argument('--empty-rack', default='/Users/Music/Desktop/kK drum rack/empty drum rack.adg',
                       help='Path to empty drum rack template')
    parser.add_argument('--output-dir', help='Output directory for generated drum racks')
    parser.add_argument('--in-place', action='store_true',
                       help='Create drum racks in same directory as aupresets')
    parser.add_argument('--overwrite', action='store_true',
                       help='Overwrite existing drum racks')
    parser.add_argument('--backup-originals', action='store_true',
                       help='Move original aupresets to backup folder (only with --in-place)')
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.backup_originals and not args.in_place:
        print("❌ Error: --backup-originals can only be used with --in-place")
        return False
    
    try:
        results, errors, skipped, backed_up = batch_process_directory(
            args.aupreset_directory,
            args.empty_rack,
            args.output_dir,
            args.in_place,
            args.overwrite,
            args.backup_originals
        )
        
        if results:
            print(f"\n🎉 Generated {len(results)} drum racks!")
            if args.in_place:
                print("Ready to use alongside original aupresets!")
            else:
                print("Ready to load in Ableton Live!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()