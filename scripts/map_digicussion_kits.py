#!/usr/bin/env python3
"""
Map Digicussion Kits — Generate transpose-mapped versions of all Digicussion kits.

Takes the "Burned Kit 01 mapped.adg" (which has Macro 1 mapped to transpose on
all 16 Simplers) as a template, and for each source kit in the Digicussion folder,
swaps in the sample references and note assignments while keeping the macro mapping.

Usage:
    export PYTHONPATH=src
    python3 scripts/map_digicussion_kits.py
"""

import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg

# Paths
TEMPLATE_PATH = Path("/Users/Music/Desktop/Burned Kit 01 mapped.adg")
SOURCE_DIR = Path("/Users/Music/Desktop/Digicussion")
OUTPUT_DIR = Path("/Users/Music/Desktop/Digicussion Mapped")

# Pack base paths for resolving Live 9 sample references to absolute paths
PACK_BASE_PATHS = {
    "Digicussion 1": "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/Packs/Digicussion 1",
    "Digicussion 2": "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/Packs/Digicussion 2",
}


def extract_pad_info(root):
    """Extract sample FileRef and ReceivingNote for each pad from a source kit."""
    pads = []
    for preset in root.iter("DrumBranchPreset"):
        recv_note = preset.find(".//ReceivingNote")
        note_val = recv_note.get("Value") if recv_note is not None else None

        # Get the SampleRef > FileRef
        file_ref = None
        for sr in preset.iter("SampleRef"):
            file_ref = sr.find("FileRef")
            break

        pads.append({"note": note_val, "file_ref": file_ref})
    return pads


def convert_fileref_to_live12(file_ref):
    """Convert a Live 9 FileRef to Live 12 format if needed.

    Live 9 format has: HasRelativePath, RelativePath (with RelativePathElement children),
                       Name, Data, RefersToFolder, SearchHint
    Live 12 format has: RelativePathType, RelativePath (string value), Path (absolute),
                        Type, LivePackName, LivePackId, OriginalFileSize, OriginalCrc, SourceHint
    """
    # Check if already Live 12 format (RelativePath has a Value attribute, not children)
    rel_path_el = file_ref.find("RelativePath")
    if rel_path_el is not None and rel_path_el.get("Value") is not None:
        # Already Live 12 format
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

    # Relative path = dirs + filename
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


def apply_samples_to_template(template_root, source_pads):
    """Replace sample references and note assignments in the template with source pad data."""
    template_presets = list(template_root.iter("DrumBranchPreset"))

    if len(template_presets) != len(source_pads):
        print(f"  WARNING: Template has {len(template_presets)} pads, source has {len(source_pads)}")

    for i, (preset, pad_info) in enumerate(zip(template_presets, source_pads)):
        # Update ReceivingNote
        if pad_info["note"] is not None:
            recv_note = preset.find(".//ReceivingNote")
            if recv_note is not None:
                recv_note.set("Value", pad_info["note"])

        # Update FileRef within SampleRef
        if pad_info["file_ref"] is not None:
            new_ref = convert_fileref_to_live12(pad_info["file_ref"])

            for sr in preset.iter("SampleRef"):
                old_ref = sr.find("FileRef")
                if old_ref is not None:
                    sr.remove(old_ref)
                sr.append(new_ref)
                break


def process_kit(template_xml_str, source_path, output_path):
    """Process a single source kit: clone template, swap samples, save."""
    # Parse source
    source_xml = decode_adg(source_path)
    source_root = ET.fromstring(source_xml)
    source_pads = extract_pad_info(source_root)

    # Clone template
    template_root = ET.fromstring(template_xml_str)

    # Apply source samples to template
    apply_samples_to_template(template_root, source_pads)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    xml_string = ET.tostring(template_root, encoding="unicode", xml_declaration=True)
    encode_adg(xml_string, output_path)


def main():
    if not TEMPLATE_PATH.exists():
        print(f"Error: Template not found: {TEMPLATE_PATH}")
        sys.exit(1)

    if not SOURCE_DIR.exists():
        print(f"Error: Source directory not found: {SOURCE_DIR}")
        sys.exit(1)

    # Load template XML once
    print(f"Loading template: {TEMPLATE_PATH}")
    template_xml = decode_adg(TEMPLATE_PATH)
    if isinstance(template_xml, bytes):
        template_xml_str = template_xml.decode("utf-8")
    else:
        template_xml_str = template_xml

    # Find all source kits
    source_kits = sorted(SOURCE_DIR.rglob("*.adg"))
    print(f"Found {len(source_kits)} source kits")
    print(f"Output: {OUTPUT_DIR}\n")

    success = 0
    errors = 0

    for kit_path in source_kits:
        rel_path = kit_path.relative_to(SOURCE_DIR)
        output_path = OUTPUT_DIR / rel_path

        try:
            process_kit(template_xml_str, kit_path, output_path)
            print(f"  OK: {rel_path}")
            success += 1
        except Exception as e:
            print(f"  ERROR: {rel_path} — {e}")
            errors += 1

    print(f"\nDone: {success} mapped, {errors} errors")


if __name__ == "__main__":
    main()
