#!/usr/bin/env python3
"""
Modify Omnisphere arpeggiator phase parameter in aupreset files (in-place overwrite).
"""
import base64
import xml.etree.ElementTree as ET
import os
import struct
import tempfile
import shutil

def modify_arp_phase_inplace(file_path, phase_value=0.0):
    """
    Modify the ArpPhase parameter in an Omnisphere aupreset (overwrites original).

    Args:
        file_path: Path to .aupreset file
        phase_value: Float value 0.0-1.0 for arpeggiator phase
    """
    try:
        # Parse the XML
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Find the data0 element
        dict_elem = root.find('dict')
        data0_found = False
        data_elem = None

        for child in dict_elem:
            if child.tag == 'key' and child.text == 'data0':
                data0_found = True
            elif data0_found and child.tag == 'data':
                data_elem = child
                break

        if data_elem is None:
            return False, "Could not find data0 element"

        # Decode the base64 data
        encoded_data = data_elem.text.strip() if data_elem.text else ""
        decoded_data = base64.b64decode(encoded_data).decode('utf-8')

        # Convert phase value to IEEE 754 hex format
        if phase_value == 0.0:
            hex_value = "0"
        else:
            # Pack as float32 and convert to hex
            packed = struct.pack('>f', phase_value)
            hex_value = ''.join(f'{b:02x}' for b in packed)

        # Find and replace ArpPhase value
        import re
        pattern = r'ArpPhase="[^"]*"'
        match = re.search(pattern, decoded_data)

        if not match:
            return False, "Could not find ArpPhase parameter"

        old_value = match.group(0)
        new_value = f'ArpPhase="{hex_value}"'

        # Replace the value
        modified_data = decoded_data.replace(old_value, new_value, 1)

        # Encode back to base64
        encoded_modified = base64.b64encode(modified_data.encode('utf-8')).decode('utf-8')

        # Update the XML
        data_elem.text = encoded_modified

        # Write to temp file first, then move (atomic operation)
        temp_fd, temp_path = tempfile.mkstemp(suffix='.aupreset')
        os.close(temp_fd)

        tree.write(temp_path, encoding='utf-8', xml_declaration=True)
        shutil.move(temp_path, file_path)

        return True, None

    except Exception as e:
        return False, str(e)


def batch_modify_directory_recursive(base_dir, phase_value=0.0):
    """
    Recursively modify all .aupreset files in a directory tree.
    """
    print(f"\n🎹 Scanning for Omnisphere presets in: {base_dir}")
    print(f"   ArpPhase target value: {phase_value}\n")

    # Find all .aupreset files
    aupreset_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.aupreset'):
                aupreset_files.append(os.path.join(root, file))

    total = len(aupreset_files)
    if total == 0:
        print(f"❌ No .aupreset files found in {base_dir}")
        return

    print(f"📊 Found {total:,} preset files to process\n")

    success_count = 0
    error_count = 0

    for idx, file_path in enumerate(aupreset_files, 1):
        # Show progress every 100 files
        if idx % 100 == 0 or idx == 1:
            print(f"[{idx:,}/{total:,}] Processing: {os.path.basename(file_path)}")

        success, error = modify_arp_phase_inplace(file_path, phase_value)

        if success:
            success_count += 1
        else:
            error_count += 1
            print(f"❌ Error in {os.path.basename(file_path)}: {error}")

    print(f"\n{'='*70}")
    print(f"✅ Complete!")
    print(f"   Processed:  {total:,} files")
    print(f"   Successful: {success_count:,} files")
    print(f"   Errors:     {error_count:,} files")
    print(f"{'='*70}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python modify_arp_phase_inplace.py <directory> [phase_value]")
        print("\nPhase value: 0.0-1.0 (default: 0.02)")
        print("\nExample:")
        print('  python modify_arp_phase_inplace.py "/Users/Shared/DevWork/GitHub/Looping/ableton/Presets/Instruments/spectrasonics" 0.02')
        sys.exit(1)

    base_dir = sys.argv[1]
    phase_value = float(sys.argv[2]) if len(sys.argv) > 2 else 0.02

    # Validate phase value
    if not 0.0 <= phase_value <= 1.0:
        print(f"❌ Error: Phase value must be between 0.0 and 1.0 (got {phase_value})")
        sys.exit(1)

    # Check if directory exists
    if not os.path.isdir(base_dir):
        print(f"❌ Error: Directory not found: {base_dir}")
        sys.exit(1)

    # Confirm with user
    print(f"\n⚠️  WARNING: This will OVERWRITE all .aupreset files in:")
    print(f"   {base_dir}")
    print(f"\n   ArpPhase will be set to: {phase_value}")
    response = input("\n   Continue? (yes/no): ")

    if response.lower() != 'yes':
        print("❌ Cancelled by user")
        sys.exit(0)

    batch_modify_directory_recursive(base_dir, phase_value)
