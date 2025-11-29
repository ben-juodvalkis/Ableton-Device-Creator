#!/usr/bin/env python3
"""
Omnisphere Orb Enable + Scene Automation Mappings

Enables the Orb effect and adds scene automation mappings (scnMix, scnSel)
to Omnisphere aupreset files for enhanced performance control.
"""

import base64
import xml.etree.ElementTree as ET
import re
import argparse
from pathlib import Path
import logging
from datetime import datetime

class OrbAndSceneMapper:
    """Enables Orb and adds scene automation mappings to aupreset files"""

    def __init__(self):
        # Automation mappings to add
        self.automation_config = {
            'scnMix': [
                {'device': 16, 'id': 12, 'channel': -1, 'instance': 1}
            ],
            'scnSel': [
                {'device': 16, 'id': 11, 'channel': -1, 'instance': 1}
            ]
        }
        self.setup_logging()

    def setup_logging(self):
        """Setup logging to both console and desktop log file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"orb_scene_mappings_{timestamp}.log"
        self.log_file_path = Path.home() / "Desktop" / log_filename

        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            handlers=[
                logging.FileHandler(self.log_file_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def log(self, message):
        """Log message to both console and file"""
        self.logger.info(message)

    def extract_preset_data(self, aupreset_path):
        """Extract and decode the preset data from aupreset file"""
        try:
            tree = ET.parse(aupreset_path)
            root = tree.getroot()

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
                    decoded_data = base64.b64decode(encoded_data).decode('utf-8', errors='ignore')
                    return decoded_data

            raise ValueError("No data0 element found in aupreset")

        except Exception as e:
            raise Exception(f"Error extracting preset data: {e}")

    def enable_orb(self, preset_xml_data):
        """Enable the Orb effect by setting orbSt to 3f800000 (1.0)"""
        self.log(f"\n🌀 Enabling Orb effect...")

        # Pattern to find orbSt parameter
        pattern = r'orbSt="[^"]*"'
        matches = re.findall(pattern, preset_xml_data)

        if not matches:
            self.log(f"  ⚠️  orbSt parameter not found")
            return preset_xml_data, False

        self.log(f"  📊 Found {len(matches)} orbSt occurrence(s)")

        # Check if already enabled
        if 'orbSt="3f800000"' in preset_xml_data:
            self.log(f"  ℹ️  Orb already enabled")
            return preset_xml_data, False

        # Replace orbSt value with 3f800000 (1.0 = enabled)
        modified_data = re.sub(pattern, 'orbSt="3f800000"', preset_xml_data)
        self.log(f"  ✅ Orb enabled (orbSt set to 3f800000)")

        return modified_data, True

    def inject_mappings(self, preset_xml_data):
        """Inject scene automation mappings into the preset XML data"""
        modified_data = preset_xml_data
        total_mappings = 0

        self.log(f"\n🎛️  Adding scene automation mappings...")

        for param_name, mappings in self.automation_config.items():
            self.log(f"\n🔍 Processing parameter '{param_name}':")

            # Find all occurrences of this parameter
            pattern = f'{param_name}="[^"]*"'
            matches = list(re.finditer(pattern, modified_data))

            if not matches:
                self.log(f"  ⚠️  No occurrences found for '{param_name}'")
                continue

            self.log(f"  📊 Found {len(matches)} total occurrences")

            # Apply mappings to specific instances only
            mappings_applied = 0
            offset = 0  # Track text length changes

            for mapping in mappings:
                instance = mapping['instance']
                device = mapping['device']
                param_id = mapping['id']
                channel = mapping['channel']

                if instance <= len(matches):
                    # Get the match for this instance (1-based indexing)
                    match = matches[instance - 1]

                    # Calculate position with offset from previous injections
                    match_start = match.start() + offset
                    match_end = match.end() + offset

                    # Check if mapping already exists
                    check_start = max(0, match_end)
                    check_end = min(len(modified_data), match_end + 200)
                    check_region = modified_data[check_start:check_end]

                    if f'{param_name}MidiLearnDevice' in check_region:
                        self.log(f"  ℹ️  Instance {instance}: Mapping already exists, skipping")
                        continue

                    # Create the automation mapping injection
                    automation_injection = (
                        f' {param_name}MidiLearnDevice0="{device}" '
                        f'{param_name}MidiLearnIDnum0="{param_id}" '
                        f'{param_name}MidiLearnChannel0="{channel}"'
                    )

                    # Insert automation mapping right after the parameter
                    modified_data = (
                        modified_data[:match_end] +
                        automation_injection +
                        modified_data[match_end:]
                    )

                    # Update offset for next injection
                    offset += len(automation_injection)
                    mappings_applied += 1
                    total_mappings += 1

                    self.log(f"  ✅ Instance {instance}: Mapped to Device {device}, ID {param_id}")

                else:
                    self.log(f"  ⚠️  Instance {instance}: Not found (only {len(matches)} occurrences exist)")

            self.log(f"  📈 Applied {mappings_applied}/{len(mappings)} mappings for '{param_name}'")

        self.log(f"\n🎛️  Total scene automation mappings applied: {total_mappings}")
        return modified_data, total_mappings

    def save_modified_preset(self, original_path, modified_xml_data, replace_original=False):
        """Save the modified preset data back to an aupreset file"""

        tree = ET.parse(original_path)
        root = tree.getroot()

        # Find and update the data0 element
        dict_elem = root.find('dict')
        data0_found = False

        for child in dict_elem:
            if child.tag == 'key' and child.text == 'data0':
                data0_found = True
            elif data0_found and child.tag == 'data':
                encoded_data = base64.b64encode(modified_xml_data.encode('utf-8')).decode('ascii')
                child.text = encoded_data
                break

        if replace_original:
            output_path = original_path
        else:
            original_path_obj = Path(original_path)
            output_path = original_path_obj.parent / f"{original_path_obj.stem} orb+scene{original_path_obj.suffix}"

        tree.write(output_path, encoding='utf-8', xml_declaration=True)

        if replace_original:
            self.log(f"💾 Updated original: {output_path}")
        else:
            self.log(f"💾 Saved modified preset: {output_path}")

        return output_path

    def process_preset(self, input_path, replace_original=False):
        """Main method to enable orb and add scene automation mappings"""

        self.log(f"🔄 Processing: {input_path}")

        try:
            preset_xml_data = self.extract_preset_data(input_path)
            self.log(f"📊 Extracted {len(preset_xml_data):,} characters")
        except Exception as e:
            self.log(f"❌ Failed to extract: {e}")
            return None

        try:
            # Enable orb
            modified_data, orb_changed = self.enable_orb(preset_xml_data)

            # Add scene automation mappings
            modified_data, mappings_added = self.inject_mappings(modified_data)

            if not orb_changed and mappings_added == 0:
                self.log(f"⚠️  No changes made (orb already enabled, mappings may already exist)")
                return None

            size_diff = len(modified_data) - len(preset_xml_data)
            self.log(f"📈 Added {size_diff} characters total")

        except Exception as e:
            self.log(f"❌ Failed to process: {e}")
            return None

        try:
            output_file = self.save_modified_preset(input_path, modified_data, replace_original)
            return output_file
        except Exception as e:
            self.log(f"❌ Failed to save: {e}")
            return None

    def batch_process_presets(self, input_dir, pattern="*.aupreset", replace_originals=False):
        """Batch process multiple aupreset files"""

        input_path = Path(input_dir)
        if not input_path.exists():
            self.log(f"❌ Input directory not found: {input_dir}")
            return []

        aupreset_files = list(input_path.rglob(pattern))
        self.log(f"🔍 Found {len(aupreset_files)} aupreset files")
        self.log(f"🌀 Enabling Orb + adding scnMix, scnSel automation")
        self.log(f"📂 Input directory: {input_path}")
        if replace_originals:
            self.log(f"🔄 Mode: Replacing original files")
        self.log(f"📄 Log file: {self.log_file_path}")

        if not aupreset_files:
            self.log("   No files found")
            return []

        processed_files = []
        skipped_files = []
        failed_files = []

        for i, aupreset_file in enumerate(aupreset_files, 1):
            self.log(f"\n{'='*80}")
            self.log(f"📄 File {i}/{len(aupreset_files)}")
            self.log(f"📁 {aupreset_file.relative_to(input_path)}")

            try:
                result = self.process_preset(aupreset_file, replace_originals)

                if result:
                    processed_files.append(result)
                    self.log(f"✅ SUCCESS")
                else:
                    skipped_files.append(aupreset_file)
                    self.log(f"⚠️  SKIPPED (no changes needed)")

            except Exception as e:
                failed_files.append({'file': aupreset_file, 'error': str(e)})
                self.log(f"❌ ERROR: {e}")

        self.log(f"\n{'='*80}")
        self.log(f"🎯 BATCH COMPLETE")
        self.log(f"{'='*80}")
        self.log(f"📊 Total files: {len(aupreset_files)}")
        self.log(f"✅ Processed: {len(processed_files)}")
        self.log(f"⚠️  Skipped: {len(skipped_files)}")
        self.log(f"❌ Failed: {len(failed_files)}")
        self.log(f"📄 Log: {self.log_file_path}")

        return processed_files

def main():
    parser = argparse.ArgumentParser(
        description="Enable Orb and add scene automation mappings (scnMix, scnSel) to Omnisphere aupreset files"
    )
    parser.add_argument('input', help='Input aupreset file or directory')
    parser.add_argument('--batch', action='store_true', help='Process directory recursively')
    parser.add_argument('--pattern', default='*.aupreset', help='File pattern for batch')
    parser.add_argument('--replace', action='store_true',
                        help='Replace original files (backup recommended)')

    args = parser.parse_args()

    print("🌀 Omnisphere Orb + Scene Automation Mapper")
    print("=" * 60)
    print("🎯 Enabling: Orb effect")
    print("🎯 Adding: scnMix, scnSel automation")
    if args.replace:
        print("🔄 Mode: Replacing originals (backup recommended!)")
    print()

    mapper = OrbAndSceneMapper()

    if args.batch:
        results = mapper.batch_process_presets(args.input, args.pattern, args.replace)

        if results:
            print(f"\n🎉 Processed {len(results)} files")
        else:
            print(f"\n⚠️  No files processed")
    else:
        result = mapper.process_preset(args.input, args.replace)

        if result:
            print(f"\n🎉 Complete!")
            print(f"   Output: {result}")
        else:
            print(f"\n⚠️  No changes made")

if __name__ == "__main__":
    main()