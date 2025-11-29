#!/usr/bin/env python3
"""
Modify Omnisphere arpeggiator phase parameter in aupreset files.
"""
import base64
import xml.etree.ElementTree as ET
import sys
import os
import struct

def modify_arp_phase(input_file, output_file, phase_value=0.0):
    """
    Modify the ArpPhase parameter in an Omnisphere aupreset.

    Args:
        input_file: Path to input .aupreset file
        output_file: Path to output .aupreset file
        phase_value: Float value 0.0-1.0 for arpeggiator phase
    """
    try:
        # Parse the XML
        tree = ET.parse(input_file)
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
            print(f"❌ Error: Could not find data0 element in {input_file}")
            return False

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
            print(f"❌ Error: Could not find ArpPhase parameter in preset data")
            return False

        old_value = match.group(0)
        new_value = f'ArpPhase="{hex_value}"'

        print(f"🔧 Modifying ArpPhase:")
        print(f"   Old: {old_value}")
        print(f"   New: {new_value}")
        print(f"   Phase value: {phase_value}")

        # Replace the value
        modified_data = decoded_data.replace(old_value, new_value, 1)

        # Encode back to base64
        encoded_modified = base64.b64encode(modified_data.encode('utf-8')).decode('utf-8')

        # Update the XML
        data_elem.text = encoded_modified

        # Write to output file
        tree.write(output_file, encoding='utf-8', xml_declaration=True)

        print(f"✅ Successfully wrote modified preset to: {output_file}")
        return True

    except Exception as e:
        print(f"❌ Error processing {input_file}: {e}")
        import traceback
        traceback.print_exc()
        return False


def batch_modify_directory(input_dir, output_dir, phase_value=0.0):
    """
    Modify all .aupreset files in a directory.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")

    aupreset_files = [f for f in os.listdir(input_dir) if f.endswith('.aupreset')]

    if not aupreset_files:
        print(f"❌ No .aupreset files found in {input_dir}")
        return

    print(f"\n🎹 Processing {len(aupreset_files)} Omnisphere presets...")
    print(f"   Input:  {input_dir}")
    print(f"   Output: {output_dir}")
    print(f"   Phase:  {phase_value}\n")

    success_count = 0
    for filename in aupreset_files:
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

        print(f"\n{'='*60}")
        print(f"Processing: {filename}")
        print(f"{'='*60}")

        if modify_arp_phase(input_path, output_path, phase_value):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"✅ Complete! Successfully modified {success_count}/{len(aupreset_files)} presets")
    print(f"{'='*60}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Single file:  python modify_arp_phase.py <input.aupreset> <output.aupreset> [phase_value]")
        print("  Directory:    python modify_arp_phase.py <input_dir> <output_dir> [phase_value]")
        print("\nPhase value: 0.0-1.0 (default: 0.0)")
        print("\nExamples:")
        print("  python modify_arp_phase.py input.aupreset output.aupreset 0.5")
        print('  python modify_arp_phase.py "/Users/Music/Desktop/omni test" "/Users/Music/Desktop/omni test modified" 0.02')
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    phase_value = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0

    # Validate phase value
    if not 0.0 <= phase_value <= 1.0:
        print(f"❌ Error: Phase value must be between 0.0 and 1.0 (got {phase_value})")
        sys.exit(1)

    # Check if input is a directory or file
    if os.path.isdir(input_path):
        batch_modify_directory(input_path, output_path, phase_value)
    elif os.path.isfile(input_path):
        modify_arp_phase(input_path, output_path, phase_value)
    else:
        print(f"❌ Error: Input path not found: {input_path}")
        sys.exit(1)
