#!/usr/bin/env python3
"""
Omnisphere Pitch Bend Range Modifier

Batch modifies pitch bend range (pbup/pbdn) in aupreset files.
Converts hex-encoded floats to new semitone values.
"""

import base64
import xml.etree.ElementTree as ET
import re
import argparse
from pathlib import Path
import struct
import logging
from datetime import datetime

class PitchBendModifier:
    """Modifies pitch bend range in aupreset files"""

    def __init__(self, new_semitones=0.24):
        self.new_semitones = new_semitones
        self.setup_logging()

    def setup_logging(self):
        """Setup logging to both console and desktop log file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"pitchbend_modifier_{timestamp}.log"
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

    def float_to_hex(self, value):
        """Convert float to big-endian hex string"""
        return struct.pack('>f', value).hex()

    def hex_to_float(self, hex_str):
        """Convert hex string to float"""
        return struct.unpack('>f', bytes.fromhex(hex_str))[0]

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

    def modify_pitch_bend(self, preset_xml_data):
        """Modify pitch bend values in the preset XML data"""
        modified_data = preset_xml_data
        new_hex = self.float_to_hex(self.new_semitones)

        # Pattern to find pbup and pbdn values
        pbup_pattern = r'pbup="([0-9a-f]{8})"'
        pbdn_pattern = r'pbdn="([0-9a-f]{8})"'

        # Find existing values
        pbup_matches = re.findall(pbup_pattern, modified_data)
        pbdn_matches = re.findall(pbdn_pattern, modified_data)

        if not pbup_matches and not pbdn_matches:
            self.log("  ⚠️  No pitch bend parameters found")
            return None

        # Show original values
        if pbup_matches:
            original_pbup = self.hex_to_float(pbup_matches[0])
            self.log(f"  📊 Original pbup: {original_pbup:.6f} semitones ({pbup_matches[0]})")

        if pbdn_matches:
            original_pbdn = self.hex_to_float(pbdn_matches[0])
            self.log(f"  📊 Original pbdn: {original_pbdn:.6f} semitones ({pbdn_matches[0]})")

        # Replace with new values
        modifications = 0
        if pbup_matches:
            modified_data = re.sub(pbup_pattern, f'pbup="{new_hex}"', modified_data)
            modifications += len(pbup_matches)
            self.log(f"  ✅ Modified {len(pbup_matches)} pbup value(s) to {self.new_semitones} semitones ({new_hex})")

        if pbdn_matches:
            modified_data = re.sub(pbdn_pattern, f'pbdn="{new_hex}"', modified_data)
            modifications += len(pbdn_matches)
            self.log(f"  ✅ Modified {len(pbdn_matches)} pbdn value(s) to {self.new_semitones} semitones ({new_hex})")

        if modifications == 0:
            return None

        return modified_data

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
            output_path = original_path_obj.parent / f"{original_path_obj.stem} pb{self.new_semitones:.2f}{original_path_obj.suffix}"

        tree.write(output_path, encoding='utf-8', xml_declaration=True)

        if replace_original:
            self.log(f"💾 Updated original: {output_path}")
        else:
            self.log(f"💾 Saved modified preset: {output_path}")

        return output_path

    def modify_preset(self, input_path, replace_original=False):
        """Main method to modify pitch bend in a preset"""

        self.log(f"🔄 Processing: {input_path}")

        try:
            preset_xml_data = self.extract_preset_data(input_path)
            self.log(f"📊 Extracted {len(preset_xml_data):,} characters")
        except Exception as e:
            self.log(f"❌ Failed to extract: {e}")
            return None

        try:
            modified_xml_data = self.modify_pitch_bend(preset_xml_data)

            if modified_xml_data is None:
                self.log(f"⚠️  No modifications made")
                return None

        except Exception as e:
            self.log(f"❌ Failed to modify: {e}")
            return None

        try:
            output_file = self.save_modified_preset(input_path, modified_xml_data, replace_original)
            return output_file
        except Exception as e:
            self.log(f"❌ Failed to save: {e}")
            return None

    def batch_modify_presets(self, input_dir, pattern="*.aupreset", replace_originals=False):
        """Batch process multiple aupreset files"""

        input_path = Path(input_dir)
        if not input_path.exists():
            self.log(f"❌ Input directory not found: {input_dir}")
            return []

        aupreset_files = list(input_path.rglob(pattern))
        self.log(f"🔍 Found {len(aupreset_files)} aupreset files")
        self.log(f"🎯 Target pitch bend: {self.new_semitones} semitones")
        self.log(f"📂 Input directory: {input_path}")
        if replace_originals:
            self.log(f"🔄 Mode: Replacing original files")
        self.log(f"📄 Log file: {self.log_file_path}")

        if not aupreset_files:
            self.log("   No files found")
            return []

        processed_files = []
        failed_files = []

        for i, aupreset_file in enumerate(aupreset_files, 1):
            self.log(f"\n{'='*80}")
            self.log(f"📄 File {i}/{len(aupreset_files)}")
            self.log(f"📁 {aupreset_file.relative_to(input_path)}")

            try:
                result = self.modify_preset(aupreset_file, replace_originals)

                if result:
                    processed_files.append(result)
                    self.log(f"✅ SUCCESS")
                else:
                    failed_files.append({'file': aupreset_file, 'error': 'No modifications'})
                    self.log(f"⚠️  SKIPPED")

            except Exception as e:
                failed_files.append({'file': aupreset_file, 'error': str(e)})
                self.log(f"❌ ERROR: {e}")

        self.log(f"\n{'='*80}")
        self.log(f"🎯 BATCH COMPLETE")
        self.log(f"{'='*80}")
        self.log(f"📊 Total files: {len(aupreset_files)}")
        self.log(f"✅ Processed: {len(processed_files)}")
        self.log(f"⚠️  Skipped: {len([f for f in failed_files if f['error'] == 'No modifications'])}")
        self.log(f"❌ Failed: {len([f for f in failed_files if f['error'] != 'No modifications'])}")
        self.log(f"📄 Log: {self.log_file_path}")

        return processed_files

def main():
    parser = argparse.ArgumentParser(
        description="Modify pitch bend range in Omnisphere aupreset files"
    )
    parser.add_argument('input', help='Input aupreset file or directory')
    parser.add_argument('-s', '--semitones', type=float, default=0.24,
                        help='New pitch bend range in semitones (default: 0.24)')
    parser.add_argument('--batch', action='store_true', help='Process directory recursively')
    parser.add_argument('--pattern', default='*.aupreset', help='File pattern for batch')
    parser.add_argument('--replace', action='store_true',
                        help='Replace original files (backup recommended)')

    args = parser.parse_args()

    print("🎛️  Omnisphere Pitch Bend Range Modifier")
    print("=" * 60)
    print(f"🎯 Target: {args.semitones} semitones")
    if args.replace:
        print("🔄 Mode: Replacing originals (backup recommended!)")
    print()

    modifier = PitchBendModifier(args.semitones)

    if args.batch:
        results = modifier.batch_modify_presets(args.input, args.pattern, args.replace)

        if results:
            print(f"\n🎉 Processed {len(results)} files")
        else:
            print(f"\n❌ No files processed")
    else:
        result = modifier.modify_preset(args.input, args.replace)

        if result:
            print(f"\n🎉 Complete!")
            print(f"   Output: {result}")
        else:
            print(f"\n❌ Failed")

if __name__ == "__main__":
    main()