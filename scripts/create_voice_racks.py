#!/usr/bin/env python3
"""
Create Voice Racks — Batch voice samples into 32-pad drum racks with macros.

Uses the "Amplified Funk 01.adg" donor template (32 pads, 16 macros with FX/Filter/Cutoff
mappings, 1056 KeyMidi elements). For each source folder, loads audio files, batches
them into groups of 32, and generates a rack per batch. Wraps samples to fill any
remaining pads in the last rack.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_voice_racks.py
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg

# Paths
DONOR_PATH = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Ableton/Drum/Perc/NI Acoustic/Amplified Funk 01.adg"
)
VOICES_ROOT = Path("/Users/Shared/Music/Samples Organized/Voices")
OUTPUT_DIR = Path("/Users/Music/Desktop/Voices Racks")

# Source folders to process
SOURCE_FOLDERS = [
    VOICES_ROOT / "Children",
    VOICES_ROOT / "Conet",
    # Each subfolder of Downloads (added at runtime)
    VOICES_ROOT / "From CDs" / "Lalo Lalo",
]

DOWNLOADS_DIR = VOICES_ROOT / "Downloads"

AUDIO_EXTS = {".wav", ".aif", ".aiff", ".flac", ".mp3"}
PADS_PER_RACK = 32


def collect_audio_files(folder: Path) -> list:
    """Collect audio files in a folder (non-recursive), sorted alphabetically."""
    files = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS
    ]
    return sorted(files, key=lambda f: f.name.lower())


def build_fileref(sample_path: Path, rack_dir: Path) -> ET.Element:
    """Build a Live 12 FileRef element for an absolute sample path.

    Uses RelativePathType=1 (relative to .adg location) matching the donor format.
    Ableton uses the absolute Path as primary, RelativePath as fallback.
    """
    try:
        rel_path = os.path.relpath(sample_path, rack_dir)
    except ValueError:
        rel_path = str(sample_path)

    fr = ET.Element("FileRef")
    ET.SubElement(fr, "RelativePathType").set("Value", "1")
    ET.SubElement(fr, "RelativePath").set("Value", rel_path)
    ET.SubElement(fr, "Path").set("Value", str(sample_path))
    ET.SubElement(fr, "Type").set("Value", "2")
    ET.SubElement(fr, "LivePackName").set("Value", "")
    ET.SubElement(fr, "LivePackId").set("Value", "")
    ET.SubElement(fr, "OriginalFileSize").set("Value", "0")
    ET.SubElement(fr, "OriginalCrc").set("Value", "0")
    ET.SubElement(fr, "SourceHint").set("Value", "")
    return fr


def replace_pad_sample(preset: ET.Element, new_file_ref: ET.Element) -> None:
    """Replace a pad's FileRef in the donor template, keep the donor's note."""
    for sr in preset.iter("SampleRef"):
        old_ref = sr.find("FileRef")
        if old_ref is not None:
            sr.remove(old_ref)
        sr.append(new_file_ref)
        break


def create_rack(donor_xml_str: str, samples: list, output_path: Path) -> None:
    """Clone donor template and swap in the given samples (up to 32)."""
    donor_root = ET.fromstring(donor_xml_str)
    donor_presets = list(donor_root.iter("DrumBranchPreset"))

    # Wrap samples to fill 32 pads
    if len(samples) == 0:
        return
    filled = [samples[i % len(samples)] for i in range(PADS_PER_RACK)]

    for i in range(min(PADS_PER_RACK, len(donor_presets))):
        new_ref = build_fileref(filled[i], output_path.parent)
        replace_pad_sample(donor_presets[i], new_ref)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    xml_string = ET.tostring(donor_root, encoding="unicode", xml_declaration=True)
    encode_adg(xml_string, output_path)


def process_folder(donor_xml_str: str, folder: Path, output_dir: Path, rack_base_name: str) -> int:
    """Process a single source folder, creating one or more racks."""
    samples = collect_audio_files(folder)
    if not samples:
        print(f"  SKIP: {folder.name} (no audio files)")
        return 0

    # Batch into groups of 32
    batches = [samples[i:i + PADS_PER_RACK] for i in range(0, len(samples), PADS_PER_RACK)]
    created = 0

    for batch_idx, batch in enumerate(batches):
        if len(batches) == 1:
            rack_name = f"{rack_base_name}.adg"
        else:
            rack_name = f"{rack_base_name} {batch_idx + 1:02d}.adg"
        output_path = output_dir / rack_name

        create_rack(donor_xml_str, batch, output_path)
        note = f"({len(batch)} samples" + (" + wrap" if len(batch) < PADS_PER_RACK else "") + ")"
        print(f"  OK: {rack_name} {note}")
        created += 1

    return created


def main():
    if not DONOR_PATH.exists():
        print(f"Error: Donor template not found: {DONOR_PATH}")
        sys.exit(1)

    # Load donor template once
    print(f"Loading donor template: {DONOR_PATH.name}")
    donor_xml = decode_adg(DONOR_PATH)
    donor_xml_str = donor_xml.decode("utf-8") if isinstance(donor_xml, bytes) else donor_xml

    # Build full source list: explicit folders + each subfolder of Downloads
    sources = list(SOURCE_FOLDERS[:2])  # Children, Conet
    if DOWNLOADS_DIR.exists():
        for sub in sorted(DOWNLOADS_DIR.iterdir()):
            if sub.is_dir():
                sources.append(sub)
    sources.append(SOURCE_FOLDERS[-1])  # Lalo Lalo

    print(f"Processing {len(sources)} source folders")
    print(f"Output: {OUTPUT_DIR}\n")

    total_racks = 0
    for folder in sources:
        if not folder.exists():
            print(f"MISSING: {folder}")
            continue

        # Determine rack base name and output subdir
        rel = folder.relative_to(VOICES_ROOT)
        parts = rel.parts
        if parts[0] == "Downloads":
            # Downloads/<sub> -> "<sub>"
            base_name = parts[1]
            out_subdir = OUTPUT_DIR / "Downloads"
        elif parts[0] == "From CDs":
            # From CDs/Lalo Lalo -> "Lalo Lalo"
            base_name = parts[-1]
            out_subdir = OUTPUT_DIR / "From CDs"
        else:
            # Children, Conet -> "Children"
            base_name = parts[0]
            out_subdir = OUTPUT_DIR

        print(f"{folder.relative_to(VOICES_ROOT)}:")
        total_racks += process_folder(donor_xml_str, folder, out_subdir, base_name)

    print(f"\nDone: {total_racks} racks created in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
