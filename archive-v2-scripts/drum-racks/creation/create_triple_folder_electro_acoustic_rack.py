#!/usr/bin/env python3
"""
Create Electro Acoustic Drum Rack from Three Folders

Combines three 12-sample folders into a single 32-pad drum rack with specific mapping:
- Folder A: Pads 1-12 (mapped by drum type: Kick, Rim, Snare, Clap, Tom Lo, Tom Hi, HiHat, HiHat-Open, Ride, HiHat-Mid, Rim, Tom-Alt)
- Folder B: Pads 17-28 (same mapping as A)
- Folder C: Remaining pads

Sample filename format expected: "Name-##-Type-V127-CODE.aif"
(e.g., "606 Dry-01-Kick-V127-S5CV.aif")

Usage:
    python3 create_triple_folder_electro_acoustic_rack.py folderA folderB folderC output.adg
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from collections import defaultdict

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def drum_pad_to_midi(pad_number: int) -> int:
    """Convert drum pad number to MIDI note (where pad 1 = MIDI 92)."""
    return 93 - pad_number


def parse_electro_acoustic_filename(filename: str) -> Optional[Tuple[str, int, str]]:
    """Parse Electro Acoustic filename format: Name-##-Type-V127-CODE.aif"""
    pattern = r'^(.+?)-(\d+)-(.+?)-V\d+-[A-Z0-9]+\.(aif|wav)$'
    match = re.match(pattern, filename)
    
    if match:
        kit_name = match.group(1)
        sample_number = int(match.group(2))
        sample_type = match.group(3)
        return kit_name, sample_number, sample_type
    
    return None


def organize_electro_acoustic_samples(sample_folder: Path, folder_name: str) -> Dict[str, str]:
    """Organize Electro Acoustic samples by type."""
    samples_by_type = {}
    
    print(f"Scanning samples in {folder_name}: {sample_folder}")
    
    for ext in ['*.aif', '*.wav']:
        for sample_file in sample_folder.glob(ext):
            parsed = parse_electro_acoustic_filename(sample_file.name)
            if parsed:
                kit_name, sample_number, sample_type = parsed
                samples_by_type[sample_type] = str(sample_file)
    
    print(f"  Found {len(samples_by_type)} sample types:")
    for sample_type in sorted(samples_by_type.keys()):
        print(f"    {sample_type}")
    
    return samples_by_type


def get_drum_type_mapping() -> Dict[int, str]:
    """Define the drum type mapping for pads 1-12 and 17-28."""
    return {
        1: "Kick",
        2: "Rim", 
        3: "Snare",
        4: "Clap",
        5: "Tom-Lo",
        6: "Tom-Hi", 
        7: "HiHat",
        8: "HiHat-Open",
        9: "Ride",
        10: "HiHat-Mid",
        11: "Rim",  # Second Rim
        12: "Tom-Alt"
    }


def create_simple_drumcell(
    template_drumcell: ET.Element,
    sample_path: str,
    sample_name: str
) -> ET.Element:
    """Create a simple single-sample DrumCell."""
    # Deep copy the template
    new_drumcell = ET.fromstring(ET.tostring(template_drumcell))
    
    # Find the SampleRef in the DrumCell
    sample_ref = new_drumcell.find('.//SampleRef')
    if sample_ref is not None:
        file_ref = sample_ref.find('FileRef')
        if file_ref is not None:
            # Create relative path
            rel_path = "../../" + '/'.join(sample_path.split('/')[-3:])
            
            # Update the file reference
            path_elem = file_ref.find('Path')
            if path_elem is not None:
                path_elem.set('Value', sample_path)
            
            rel_path_elem = file_ref.find('RelativePath')
            if rel_path_elem is not None:
                rel_path_elem.set('Value', rel_path)
    
    return new_drumcell


def create_triple_folder_electro_acoustic_rack(
    folderA: Path,
    folderB: Path,
    folderC: Path,
    output_path: Path,
    template_path: Optional[Path] = None
) -> Path:
    """Create a triple-folder Electro Acoustic drum rack with 32 pads."""
    
    # Use default template if not provided
    if template_path is None:
        template_path = Path(__file__).parent.parent.parent / 'templates/Drum Racks/Acoustic/Amplified Funk 3onIt + 7dee.adg'
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    for folder in [folderA, folderB, folderC]:
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")
    
    print(f"\n{'='*70}")
    print(f"CREATING TRIPLE-FOLDER ELECTRO ACOUSTIC DRUM RACK (32 Pads)")
    print(f"{'='*70}\n")
    print(f"Template: {template_path.name}")
    print(f"Folder A (Pads 1-12): {folderA.name}")
    print(f"Folder B (Pads 17-28): {folderB.name}")
    print(f"Folder C (Remaining pads): {folderC.name}")
    
    # Load template
    template_xml = decode_adg(template_path)
    template_root = ET.fromstring(template_xml)
    
    # Extract template DrumCell and DrumBranchPreset
    template_drumcell = template_root.find('.//DrumCell')
    if template_drumcell is None:
        raise ValueError("Template missing DrumCell device")
    
    template_branch = template_root.find('.//DrumBranchPreset')
    if template_branch is None:
        raise ValueError("Template missing DrumBranchPreset structure")
    
    # Organize samples from all three folders
    samples_folderA = organize_electro_acoustic_samples(folderA, "Folder A")
    samples_folderB = organize_electro_acoustic_samples(folderB, "Folder B") 
    samples_folderC = organize_electro_acoustic_samples(folderC, "Folder C")
    
    if not any([samples_folderA, samples_folderB, samples_folderC]):
        raise ValueError(f"No valid Electro Acoustic files found in any folder")
    
    # Find the BranchPresets container in template
    branch_presets_container = template_root.find('.//BranchPresets')
    if branch_presets_container is None:
        raise ValueError("Template missing BranchPresets structure")
    
    # Don't clear - the template has 32 pre-configured branches with correct MIDI notes
    # We'll update them in place instead
    
    # Get drum type mapping
    drum_mapping = get_drum_type_mapping()
    
    total_pads = 0
    
    print(f"\nCreating drum pads:")
    
    # Process Folder A (Pads 1-12)
    for pad_number in range(1, 13):
        drum_type = drum_mapping[pad_number]
        branch_index = pad_number - 1  # 0-based index
        
        if drum_type in samples_folderA:
            sample_path = samples_folderA[drum_type]
            
            # Get the existing branch from template
            existing_branch = branch_presets_container[branch_index]
            
            # Update branch name
            existing_branch.find('Name').set('Value', f"A-{drum_type}")
            
            # Create DrumCell with single sample
            updated_drumcell = create_simple_drumcell(
                template_drumcell, sample_path, f"A-{drum_type}"
            )
            
            # Replace the DrumCell in the existing branch
            device_container = existing_branch.find('.//Device')
            old_drumcell = device_container.find('DrumCell')
            if old_drumcell is not None:
                device_container.remove(old_drumcell)
            device_container.append(updated_drumcell)
            
            # Log creation
            print(f"  Pad {pad_number:2d} (A-{drum_type}): {Path(sample_path).name}")
            total_pads += 1
        else:
            print(f"  Pad {pad_number:2d} (A-{drum_type}): MISSING")
    
    # Process Folder B (Pads 17-28)
    for i, pad_number in enumerate(range(17, 29)):
        drum_type = drum_mapping[i + 1]  # Map to drum types 1-12
        branch_index = pad_number - 1  # 0-based index (16-27)
        
        if drum_type in samples_folderB:
            sample_path = samples_folderB[drum_type]
            
            # Get the existing branch from template
            existing_branch = branch_presets_container[branch_index]
            
            # Update branch name
            existing_branch.find('Name').set('Value', f"B-{drum_type}")
            
            # Create DrumCell with single sample
            updated_drumcell = create_simple_drumcell(
                template_drumcell, sample_path, f"B-{drum_type}"
            )
            
            # Replace the DrumCell in the existing branch
            device_container = existing_branch.find('.//Device')
            old_drumcell = device_container.find('DrumCell')
            if old_drumcell is not None:
                device_container.remove(old_drumcell)
            device_container.append(updated_drumcell)
            
            # Log creation
            print(f"  Pad {pad_number:2d} (B-{drum_type}): {Path(sample_path).name}")
            total_pads += 1
        else:
            print(f"  Pad {pad_number:2d} (B-{drum_type}): MISSING")
    
    # Process Folder C (Remaining pads 13-16, 29-32)
    remaining_pads = list(range(13, 17)) + list(range(29, 33))
    
    # Prioritize the most important drum sounds for extra pads
    priority_drums = ["Kick", "Rim", "Snare", "Clap", "Tom-Lo", "Tom-Hi", "HiHat", "Ride"]
    
    # Get prioritized samples from Folder C
    prioritized_c_samples = []
    for drum_type in priority_drums:
        if drum_type in samples_folderC:
            prioritized_c_samples.append((drum_type, samples_folderC[drum_type]))
        elif drum_type == "HiHat" and "HiHat-Open" in samples_folderC:
            # Fallback to HiHat-Open if HiHat not found
            prioritized_c_samples.append(("HiHat-Open", samples_folderC["HiHat-Open"]))
    
    # Fill remaining slots with other available samples
    used_types = {item[0] for item in prioritized_c_samples}
    for sample_type, sample_path in samples_folderC.items():
        if sample_type not in used_types and len(prioritized_c_samples) < len(remaining_pads):
            prioritized_c_samples.append((sample_type, sample_path))
    
    for i, pad_number in enumerate(remaining_pads):
        branch_index = pad_number - 1  # 0-based index
        
        if i < len(prioritized_c_samples):
            sample_type, sample_path = prioritized_c_samples[i]
            
            # Get the existing branch from template
            existing_branch = branch_presets_container[branch_index]
            
            # Update branch name
            existing_branch.find('Name').set('Value', f"C-{sample_type}")
            
            # Create DrumCell with single sample
            updated_drumcell = create_simple_drumcell(
                template_drumcell, sample_path, f"C-{sample_type}"
            )
            
            # Replace the DrumCell in the existing branch
            device_container = existing_branch.find('.//Device')
            old_drumcell = device_container.find('DrumCell')
            if old_drumcell is not None:
                device_container.remove(old_drumcell)
            device_container.append(updated_drumcell)
            
            # Log creation
            print(f"  Pad {pad_number:2d} (C-{sample_type}): {Path(sample_path).name}")
            total_pads += 1
        else:
            print(f"  Pad {pad_number:2d}: EMPTY (no more C samples)")
    
    # Convert back to XML string
    result_xml = ET.tostring(template_root, encoding='unicode', xml_declaration=True)
    
    # Encode to .adg
    print(f"\nWriting triple-folder drum rack: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(result_xml, output_path)
    
    print(f"\n{'='*70}")
    print(f"✓ TRIPLE-FOLDER CREATION COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {output_path}")
    print(f"Total drum pads: {total_pads}")
    print(f"Folder A samples: {len(samples_folderA)}")
    print(f"Folder B samples: {len(samples_folderB)}")
    print(f"Folder C samples: {len(samples_folderC)}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Create triple-folder Electro Acoustic drum rack with 32 pads')
    
    parser.add_argument('folderA', type=Path, help='Path to first sample folder (pads 1-12)')
    parser.add_argument('folderB', type=Path, help='Path to second sample folder (pads 17-28)')
    parser.add_argument('folderC', type=Path, help='Path to third sample folder (remaining pads)')
    parser.add_argument('output', type=Path, help='Output drum rack path (.adg file)')
    parser.add_argument('--template', type=Path, default=None, help='Optional template drum rack')
    
    args = parser.parse_args()
    
    try:
        create_triple_folder_electro_acoustic_rack(args.folderA, args.folderB, args.folderC, args.output, args.template)
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()