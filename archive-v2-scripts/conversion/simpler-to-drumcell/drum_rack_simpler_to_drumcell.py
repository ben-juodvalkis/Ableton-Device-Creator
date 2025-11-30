#!/usr/bin/env python3
"""
Convert all Simplers in a Drum Rack to DrumCells

Takes an Ableton Drum Rack (.adg) file and converts all OriginalSimpler
devices to DrumCell devices, replicating Ableton's built-in conversion.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.decoder import decode_adg
from utils.encoder import encode_adg

# Import the single simpler converter
from conversion.simpler_to_drumcell import simpler_to_drumcell, create_drumcell_template


def find_and_convert_simplers(rack_root):
    """Find all OriginalSimpler devices in the rack and convert them to DrumCell"""

    # Find all DrumBranchPreset elements (individual pads)
    branch_presets = rack_root.findall('.//DrumBranchPreset')

    print(f"\n📊 Found {len(branch_presets)} pads in drum rack")

    converted_count = 0
    skipped_count = 0

    for idx, branch_preset in enumerate(branch_presets):
        # Find the device container
        device_elem = branch_preset.find('.//Device')

        if device_elem is None:
            skipped_count += 1
            continue

        # Check if it contains an OriginalSimpler
        simpler = device_elem.find('OriginalSimpler')

        if simpler is not None:
            # Check if this is a multi-sample Simpler (should NOT be converted)
            sample_parts = simpler.findall('.//MultiSamplePart')

            if len(sample_parts) > 1:
                # Multi-sample Simpler with multiple zones/velocity layers
                print(f"  ⏭️  Pad {idx + 1}: Skipping multi-sample Simpler ({len(sample_parts)} zones)")
                skipped_count += 1
                continue

            # Get sample name for logging
            sample_ref = simpler.find('.//MultiSamplePart/SampleRef/FileRef/Path')
            sample_path = sample_ref.get('Value') if sample_ref is not None else 'Unknown'
            sample_name = Path(sample_path).name if sample_path != 'Unknown' else 'Empty'

            print(f"  🔄 Pad {idx + 1}: Converting Simpler → {sample_name}")

            # Convert the Simpler to DrumCell XML string
            simpler_xml_str = ET.tostring(simpler, encoding='unicode')

            # Wrap in Ableton root for conversion
            wrapped_simpler = f"""<?xml version="1.0" encoding="UTF-8"?>
<Ableton MajorVersion="5" MinorVersion="12.0_12300" SchemaChangeCount="1" Creator="Ableton Live 12.3b12" Revision="a51ffacdd96935f4e75c565b931d9d81c161dfb8">
{simpler_xml_str}
</Ableton>"""

            # Convert using existing converter
            drumcell_xml_str = simpler_to_drumcell(wrapped_simpler)

            # Check if conversion was skipped (empty pad)
            if drumcell_xml_str is None:
                print(f"    ⏭️  Skipped empty pad")
                skipped_count += 1
                continue

            # Parse the converted DrumCell
            drumcell_root = ET.fromstring(drumcell_xml_str)
            drumcell = drumcell_root.find('DrumCell')

            if drumcell is not None:
                # IMPORTANT: Add Id="0" attribute to DrumCell (required by Ableton)
                # Get the Id from the original Simpler if it exists
                simpler_id = simpler.get('Id', '0')
                drumcell.set('Id', simpler_id)

                # Remove the old Simpler
                device_elem.remove(simpler)

                # Add the new DrumCell
                device_elem.append(drumcell)

                # IMPORTANT: Update PresetRef DeviceId from "OriginalSimpler" to "DrumCell"
                # Find the parent AbletonDevicePreset
                for parent in branch_preset.iter():
                    if device_elem in parent:
                        preset_ref = parent.find('PresetRef')
                        if preset_ref is not None:
                            device_id = preset_ref.find('.//DeviceId')
                            if device_id is not None and device_id.get('Name') == 'OriginalSimpler':
                                device_id.set('Name', 'DrumCell')
                        break

                converted_count += 1
            else:
                print(f"    ⚠️  Failed to convert pad {idx + 1}")
        else:
            # Check if it's already a DrumCell or empty
            drumcell = device_elem.find('DrumCell')
            if drumcell is not None:
                print(f"  ⏭️  Pad {idx + 1}: Already DrumCell, skipping")
            skipped_count += 1

    return converted_count, skipped_count


def main():
    if len(sys.argv) != 3:
        print("Usage: drum_rack_simpler_to_drumcell.py <input_rack.adg> <output_rack.adg>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    print("="*80)
    print("🥁 DRUM RACK: Convert All Simplers → DrumCells")
    print("="*80)

    # Decode drum rack
    print(f"\n📖 Reading: {input_path.name}")
    rack_xml = decode_adg(input_path)
    rack_root = ET.fromstring(rack_xml)

    # Convert all simplers
    converted, skipped = find_and_convert_simplers(rack_root)

    # Encode result
    print(f"\n💾 Writing: {output_path.name}")
    result_xml = ET.tostring(rack_root, encoding='unicode', xml_declaration=True)
    encode_adg(result_xml, output_path)

    # Summary
    print("\n" + "="*80)
    print("✅ CONVERSION COMPLETE")
    print("="*80)
    print(f"  Converted: {converted} Simplers → DrumCells")
    print(f"  Skipped:   {skipped} pads (empty or already DrumCell)")
    print(f"\n✨ Success! Created: {output_path}")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
