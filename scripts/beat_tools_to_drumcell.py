#!/usr/bin/env python3
"""
Beat Tools -> DrumCell — rehost Beat Tools kit samples in a DrumCell drum rack.

The stock "Beat Tools" kits are Instrument Racks whose pads each hold an
OriginalSimpler. This tool keeps the *samples* but rehosts them in one of the
user's own DrumCell-based 32-pad drum racks (the "Electro Acoustic" family,
e.g. `606 808 EMI Crush.adg`), so the samples play through the DrumCell engine
and inherit the donor rack's macros / mixer / FX return chain.

Design rule (same as the Sampler-based Drum Rack workflow in CLAUDE.md): never
reconstruct rack structure — only swap sample content. The donor's 32-pad note
layout, colors, macros, per-pad DrumCell voice settings and FX are left
untouched; for each pad we replace only the DrumCell's `UserSample` FileRef
(plus the cached DefaultDuration / DefaultSampleRate) and relabel the pad.

Because the donor has 32 pads, two 16-pad kits fill it exactly:
    Top half    (donor pads  0-15, notes 92-77): Kit A
    Bottom half (donor pads 16-31, notes 76-61): Kit B

A kit with fewer/more than 16 pads fills sequentially from the top; any donor
pad past the supplied sample count keeps the donor's own sample (reported).

Usage:
    export PYTHONPATH=src
    python3 scripts/beat_tools_to_drumcell.py
"""

import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg

# --- Config -----------------------------------------------------------------

# The original "606 808 EMI Crush.adg" rack was replaced in the Electro
# Acoustic rebuild (create_electro_acoustic_racks.py); a copy is preserved
# in the repo as the canonical DrumCell donor.
DONOR_PATH = Path(__file__).parent.parent / "templates/electro_acoustic_drumcell_donor.adg"
PROD_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Ableton/Drum/Prod"
)
PACKS_ROOT = Path("/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/Packs")

# Pack folders to convert. Each becomes <folder>/DrumCell Versions/.
SOURCE_FOLDERS = [
    "Build and Drop",
    "Chop and Swing",
    "Drive and Glow",
    "Glitch and Wash",
    "Punch and Tilt",
    "Skitter and Step",
]

PADS_PER_DONOR = 32
OUTPUT_SUBDIR = "DrumCell Versions"


# --- Structure helpers ------------------------------------------------------

def drum_branch_container(root):
    """Return the BranchPresets element of the *outermost* drum rack.

    Uses the first DrumGroupDevice in document order (the main rack); its direct
    BranchPresets children are the pads. Iterating direct children (rather than
    root.iter) avoids descending into a nested rack loaded on a pad, as in the
    Street Kit.
    """
    for gdp in root.iter("GroupDevicePreset"):
        dev = gdp.find("Device")
        if dev is not None and dev.find("DrumGroupDevice") is not None:
            return gdp.find("BranchPresets")
    return None


def repair_file_ref_path(file_ref):
    """Repair a stale absolute <Path> to the installed-pack location.

    These newer packs (Drive and Glow, Skitter and Step, ...) store a stale
    build-server absolute Path (e.g. /Volumes/data/tmp/trunk/...). Live still
    resolves them via RelativePathType=5 + LivePackName + RelativePath, but we
    rewrite the absolute Path to the real installed location so DrumCell has a
    valid path both ways. No-op when the stored Path already exists (Beat Tools).
    """
    path_el = file_ref.find("Path")
    if path_el is not None and path_el.get("Value") and Path(path_el.get("Value")).exists():
        return
    lpn = file_ref.find("LivePackName")
    rel = file_ref.find("RelativePath")
    if lpn is None or rel is None or not lpn.get("Value") or not rel.get("Value"):
        return
    candidate = PACKS_ROOT / lpn.get("Value") / rel.get("Value")
    if candidate.exists() and path_el is not None:
        path_el.set("Value", str(candidate))


# --- Source extraction ------------------------------------------------------

def extract_pads(kit_path: Path):
    """Return a list of {name, note, sample_ref} for a kit's pads.

    Sorted by ReceivingNote **descending** (top pad = highest note first) so the
    sample→note mapping is preserved when the pads are poured onto the donor's
    note-descending grid. Source kits store pads in chain order, NOT note order
    (e.g. a kit's note-92 kick can sit at document index 10), so sorting by note
    is required — filling in document order scrambles which sound lands on which
    note. Pads with no ReceivingNote sort last.
    """
    xml = decode_adg(kit_path)
    if isinstance(xml, bytes):
        xml = xml.decode("utf-8")
    root = ET.fromstring(xml)

    pads = []
    container = drum_branch_container(root)
    for preset in list(container):
        sample_ref = next(preset.iter("SampleRef"), None)
        if sample_ref is None:
            continue  # empty pad (e.g. a synth voice with no sample)
        path_el = sample_ref.find("FileRef/Path")
        stem = Path(path_el.get("Value")).stem if path_el is not None else ""
        note_el = preset.find(".//ZoneSettings/ReceivingNote")
        note = int(note_el.get("Value")) if note_el is not None else -1
        pads.append({"name": stem, "note": note, "sample_ref": sample_ref})

    pads.sort(key=lambda p: p["note"], reverse=True)
    return pads


# --- Donor swap -------------------------------------------------------------

def swap_pad_sample(donor_pad, source_sample_ref, pad_name):
    """Swap one donor DrumCell pad's sample content in place.

    Replaces the DrumCell's UserSample FileRef with the source FileRef and syncs
    the cached DefaultDuration / DefaultSampleRate / LastModDate so DrumCell
    reads the right file length. Rack structure and DrumCell voice params are
    left untouched. Also relabels the pad chain.
    """
    donor_sr = next(donor_pad.iter("SampleRef"), None)
    if donor_sr is None:
        return False

    src_file_ref = source_sample_ref.find("FileRef")
    if src_file_ref is None:
        return False

    # Replace FileRef
    old_ref = donor_sr.find("FileRef")
    if old_ref is not None:
        donor_sr.remove(old_ref)
    # Insert the new FileRef at the front (schema order: FileRef first)
    new_ref = copy.deepcopy(src_file_ref)
    repair_file_ref_path(new_ref)
    donor_sr.insert(0, new_ref)

    # Sync cached sample metadata from the source SampleRef
    for tag in ("LastModDate", "DefaultDuration", "DefaultSampleRate"):
        src_el = source_sample_ref.find(tag)
        dst_el = donor_sr.find(tag)
        if src_el is not None and dst_el is not None:
            dst_el.set("Value", src_el.get("Value"))

    # Relabel the pad chain
    name_el = donor_pad.find("Name")
    if name_el is not None and pad_name:
        name_el.set("Value", pad_name)

    return True


def build_rack(donor_xml_str, samples, output_path):
    """Fill a fresh copy of the donor with `samples` (list of pad dicts).

    Fills donor pads top-down. If there are fewer samples than the donor's 32
    pads, the surplus donor pads are removed entirely so no foreign (606/808)
    samples remain — yielding a clean N-pad rack whose note range matches the
    source kit. Returns (filled, kept_pads).
    """
    donor_root = ET.fromstring(donor_xml_str)
    container = drum_branch_container(donor_root)
    # Fill donor pads high note -> low note so samples (also note-descending)
    # keep their positions and any surplus pads trimmed are the lowest notes.
    donor_pads = sorted(
        container,
        key=lambda p: int(p.find(".//ZoneSettings/ReceivingNote").get("Value")),
        reverse=True,
    )

    n = min(len(samples), len(donor_pads))
    filled = 0
    for i in range(n):
        if swap_pad_sample(donor_pads[i], samples[i]["sample_ref"], samples[i]["name"]):
            filled += 1

    # Remove surplus donor pads (keep only the first n)
    for pad in donor_pads[n:]:
        container.remove(pad)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    xml_string = ET.tostring(donor_root, encoding="unicode", xml_declaration=True)
    encode_adg(xml_string, output_path)
    return filled, n


def combine_kits(donor_xml_str, kit_paths, output_path):
    """Combine one or more kits (in order) into a single donor rack."""
    samples = []
    for kp in kit_paths:
        samples.extend(extract_pads(kp))
    return build_rack(donor_xml_str, samples, output_path)


# --- Planning ---------------------------------------------------------------

def pad_count(kit_path: Path) -> int:
    """Number of pads (direct DrumBranchPresets of the outer drum rack)."""
    xml = decode_adg(kit_path)
    if isinstance(xml, bytes):
        xml = xml.decode("utf-8")
    container = drum_branch_container(ET.fromstring(xml))
    return len(list(container)) if container is not None else 0


def plan_folder(folder_dir: Path):
    """Return (pairs, solos): pair 16-pad kits alphabetically, rest go solo.

    An odd leftover 16-pad kit is converted solo.
    """
    kits = sorted(folder_dir.glob("*.adg"))
    sixteens = [k for k in kits if pad_count(k) == 16]
    others = [k for k in kits if pad_count(k) != 16]

    pairs = []
    i = 0
    while i + 1 < len(sixteens):
        pairs.append((sixteens[i], sixteens[i + 1]))
        i += 2
    solos = others + sixteens[i:]  # trailing unpaired 16-pad kit, if any
    return pairs, sorted(solos)


def write_solo(donor_xml_str, kit, out_dir):
    """Convert one kit solo, splitting into multiple racks if it exceeds 32 pads.

    A kit with more pads than the donor (e.g. Doom Drums, 44) can't fit one
    32-pad rack without dropping samples, so it is split into "<Kit> (1)",
    "<Kit> (2)", ... of up to 32 pads each. Returns a list of (name, filled).
    """
    samples = extract_pads(kit)
    n_chunks = max(1, (len(samples) + PADS_PER_DONOR - 1) // PADS_PER_DONOR)
    results = []
    for c in range(n_chunks):
        chunk = samples[c * PADS_PER_DONOR:(c + 1) * PADS_PER_DONOR]
        name = kit.stem if n_chunks == 1 else f"{kit.stem} ({c + 1})"
        filled, kept = build_rack(donor_xml_str, chunk, out_dir / f"{name}.adg")
        results.append((name, filled))
    return results


# --- Main -------------------------------------------------------------------

def main():
    if not DONOR_PATH.exists():
        sys.exit(f"Donor not found: {DONOR_PATH}")

    donor_xml = decode_adg(DONOR_PATH)
    donor_xml_str = donor_xml.decode("utf-8") if isinstance(donor_xml, bytes) else donor_xml

    folders = sys.argv[1:] if len(sys.argv) > 1 else SOURCE_FOLDERS

    print(f"Donor: {DONOR_PATH.name}\n")
    grand_total = 0

    for folder in folders:
        folder_dir = PROD_ROOT / folder
        if not folder_dir.is_dir():
            print(f"!! Skipping missing folder: {folder}")
            continue
        out_dir = folder_dir / OUTPUT_SUBDIR
        pairs, solos = plan_folder(folder_dir)
        print(f"### {folder}")

        for kit_a, kit_b in pairs:
            a = kit_a.stem.replace(" Kit", "")
            b = kit_b.stem.replace(" Kit", "")
            out = out_dir / f"{a} + {b}.adg"
            filled, kept = combine_kits(donor_xml_str, [kit_a, kit_b], out)
            print(f"  pair  {a + ' + ' + b:<34} {filled} samples / {kept} pads")
            grand_total += 1

        for kit in solos:
            for name, filled in write_solo(donor_xml_str, kit, out_dir):
                tag = "solo " if name == kit.stem else "split"
                print(f"  {tag} {name:<34} {filled} samples")
                grand_total += 1
        print()

    print(f"Done: {grand_total} racks written")


if __name__ == "__main__":
    main()
