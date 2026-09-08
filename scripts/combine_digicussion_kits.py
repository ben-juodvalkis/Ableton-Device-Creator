#!/usr/bin/env python3
"""
Combine Digicussion Kits — Pair two 16-pad kits into 32-pad drum racks.

Uses a donor 32-pad drum rack (with macro mappings for FX, filter, transpose, etc.)
as the template. Pairs kits within each category sequentially (01+02, 03+04, etc.),
swapping in sample references from the Digicussion source kits.

Top half (pads 0-15): Kit A samples at original notes (77-92)
Bottom half (pads 16-31): Kit B samples with notes shifted -16 (61-76)

Usage:
    export PYTHONPATH=src
    python3 scripts/combine_digicussion_kits.py
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg

# Paths
DONOR_PATH = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Ableton/Drum/Prod/NI Acoustic/"
    "Amplified Funk Aquarius + BluOut.adg"
)
SOURCE_DIR = Path("/Users/Music/Desktop/Digicussion")
OUTPUT_DIR = Path("/Users/Music/Desktop/Digicussion Combined")

# Pack base paths for resolving Live 9 sample references to absolute paths
PACK_BASE_PATHS = {
    "Digicussion 1": "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/Packs/Digicussion 1",
    "Digicussion 2": "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/Packs/Digicussion 2",
}

NOTE_SHIFT = -16  # Shift for bottom half notes


def extract_pad_info(root):
    """Extract sample FileRef and ReceivingNote for each pad from a source kit."""
    pads = []
    for preset in root.iter("DrumBranchPreset"):
        recv_note = preset.find(".//ReceivingNote")
        note_val = int(recv_note.get("Value")) if recv_note is not None else None

        # Get the SampleRef > FileRef
        file_ref = None
        for sr in preset.iter("SampleRef"):
            file_ref = sr.find("FileRef")
            break

        pads.append({"note": note_val, "file_ref": file_ref})
    return pads


def convert_fileref_to_live12(file_ref):
    """Convert a Live 9 FileRef to Live 12 format if needed."""
    # Check if already Live 12 format (RelativePath has a Value attribute, not children)
    rel_path_el = file_ref.find("RelativePath")
    if rel_path_el is not None and rel_path_el.get("Value") is not None:
        return file_ref

    # Extract info from Live 9 format
    name_el = file_ref.find("Name")
    sample_name = name_el.get("Value", "") if name_el is not None else ""

    pack_name_el = file_ref.find("LivePackName")
    pack_name = pack_name_el.get("Value", "") if pack_name_el is not None else ""

    pack_id_el = file_ref.find("LivePackId")
    pack_id = pack_id_el.get("Value", "") if pack_id_el is not None else ""

    type_el = file_ref.find("Type")
    type_val = type_el.get("Value", "2") if type_el is not None else "2"

    # Build relative path from RelativePathElement children
    rel_parts = []
    if rel_path_el is not None:
        for elem in rel_path_el:
            if elem.tag == "RelativePathElement":
                rel_parts.append(elem.get("Dir", ""))

    rel_path_str = "/".join(rel_parts + [sample_name]) if rel_parts else sample_name

    # Absolute path from pack base
    abs_path = ""
    if pack_name in PACK_BASE_PATHS:
        abs_path = PACK_BASE_PATHS[pack_name] + "/" + rel_path_str

    # Build new Live 12 FileRef
    new_ref = ET.Element("FileRef")
    ET.SubElement(new_ref, "RelativePathType").set("Value", "5")
    ET.SubElement(new_ref, "RelativePath").set("Value", rel_path_str)
    ET.SubElement(new_ref, "Path").set("Value", abs_path)
    ET.SubElement(new_ref, "Type").set("Value", type_val)
    ET.SubElement(new_ref, "LivePackName").set("Value", pack_name)
    ET.SubElement(new_ref, "LivePackId").set("Value", pack_id)
    ET.SubElement(new_ref, "OriginalFileSize").set("Value", "0")
    ET.SubElement(new_ref, "OriginalCrc").set("Value", "0")
    ET.SubElement(new_ref, "SourceHint").set("Value", "")

    return new_ref


def replace_pad_sample(preset, new_file_ref, new_note):
    """Replace a pad's FileRef and ReceivingNote in the donor template."""
    # Update ReceivingNote
    recv_note = preset.find(".//ReceivingNote")
    if recv_note is not None:
        recv_note.set("Value", str(new_note))

    # Update FileRef within SampleRef
    for sr in preset.iter("SampleRef"):
        old_ref = sr.find("FileRef")
        if old_ref is not None:
            sr.remove(old_ref)
        sr.append(new_file_ref)
        break


def process_pair(donor_xml_str, kit_a_path, kit_b_path, output_path):
    """Combine two kits into a 32-pad rack using the donor template."""
    # Parse source kits
    kit_a_xml = decode_adg(kit_a_path)
    kit_b_xml = decode_adg(kit_b_path)
    pads_a = extract_pad_info(ET.fromstring(kit_a_xml))
    pads_b = extract_pad_info(ET.fromstring(kit_b_xml))

    # Clone donor template
    donor_root = ET.fromstring(donor_xml_str)
    donor_presets = list(donor_root.iter("DrumBranchPreset"))

    if len(donor_presets) != 32:
        print(f"  WARNING: Donor has {len(donor_presets)} pads, expected 32")

    # Top half (pads 0-15): Kit A at original notes
    for i in range(min(16, len(pads_a), len(donor_presets))):
        pad = pads_a[i]
        if pad["file_ref"] is not None:
            new_ref = convert_fileref_to_live12(pad["file_ref"])
            replace_pad_sample(donor_presets[i], new_ref, pad["note"])

    # Bottom half (pads 16-31): Kit B with notes shifted -16
    for i in range(min(16, len(pads_b))):
        donor_idx = 16 + i
        if donor_idx >= len(donor_presets):
            break
        pad = pads_b[i]
        if pad["file_ref"] is not None:
            new_ref = convert_fileref_to_live12(pad["file_ref"])
            shifted_note = pad["note"] + NOTE_SHIFT
            replace_pad_sample(donor_presets[donor_idx], new_ref, shifted_note)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    xml_string = ET.tostring(donor_root, encoding="unicode", xml_declaration=True)
    encode_adg(xml_string, output_path)


def get_kit_number(path):
    """Extract kit number from filename like 'Burned Kit 03.adg' -> '03'."""
    stem = path.stem
    # Find the last number in the name (before any parenthetical like "(D#)")
    parts = stem.split()
    for part in reversed(parts):
        # Strip parenthetical suffixes
        clean = part.strip("()")
        if clean.isdigit():
            return clean
    return stem


def main():
    if not DONOR_PATH.exists():
        print(f"Error: Donor template not found: {DONOR_PATH}")
        sys.exit(1)

    if not SOURCE_DIR.exists():
        print(f"Error: Source directory not found: {SOURCE_DIR}")
        sys.exit(1)

    # Load donor template XML once
    print(f"Loading donor template: {DONOR_PATH.name}")
    donor_xml = decode_adg(DONOR_PATH)
    if isinstance(donor_xml, bytes):
        donor_xml_str = donor_xml.decode("utf-8")
    else:
        donor_xml_str = donor_xml

    # Get categories
    categories = sorted(
        [d for d in SOURCE_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
    )

    print(f"Output: {OUTPUT_DIR}\n")

    success = 0
    skipped = 0
    errors = 0

    for cat in categories:
        kits = sorted(cat.glob("*.adg"))
        n_pairs = len(kits) // 2
        leftover = len(kits) % 2

        print(f"{cat.name}: {len(kits)} kits -> {n_pairs} pairs")

        for j in range(0, len(kits) - 1, 2):
            kit_a = kits[j]
            kit_b = kits[j + 1]

            num_a = get_kit_number(kit_a)
            num_b = get_kit_number(kit_b)

            # Extract category prefix (e.g., "Burned Kit")
            prefix = kit_a.stem.rsplit(num_a, 1)[0].rstrip()
            output_name = f"{prefix} {num_a} + {num_b}.adg"
            output_path = OUTPUT_DIR / cat.name / output_name

            try:
                process_pair(donor_xml_str, kit_a, kit_b, output_path)
                print(f"  OK: {output_name}")
                success += 1
            except Exception as e:
                print(f"  ERROR: {output_name} — {e}")
                errors += 1

        if leftover:
            print(f"  SKIP: {kits[-1].name} (unpaired)")
            skipped += 1

    print(f"\nDone: {success} combined, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
