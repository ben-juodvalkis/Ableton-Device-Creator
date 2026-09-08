#!/usr/bin/env python3
"""
SonicCouture Electro-Acoustic -> category-organized DrumCell drum racks.

Rebuilds the "Electro Acoustic" rack family with category-pure racks that say
exactly what they contain, replacing the old V2 triple-folder set whose names
rarely matched their contents (e.g. "606 808 EMI Crush" actually held
606 Neve + 808 Dry + 606 EMI Crush, plus stray acoustic template samples).

Source: 181 kit folders under SAMPLE_LIBRARY_ROOT, one per SonicCouture
snapshot, each holding exactly 12 single-velocity one-shots numbered
01-Kick .. 12-Cowbell. Categories mirror SonicCouture's snapshot folders:
Dry, Electro Acoustic, Hybrid, Distorted (= "Overdrive" snapshots).

Plan ("same treatment, two machines" pairing, chosen 2026-07):
- Kits parse to (machine, treatment); typos in the export are normalized
  ("MR10 alve" -> Valve, "CR80000" -> CR8000, "Bentley"/"Rhythm Ace" merged).
- Within each category, kits group by treatment; machines pair alphabetically
  ("EMI Crush - 606 + 808"). Odd leftovers pool per category and pair by
  (machine, treatment) so e.g. the one-off 808 room treatments pair together
  ("808 - Shake the Room + Slammed Room"). Hybrids pair alphabetically.
- Output subfolders mirror SonicCouture's numbering:
  1 Dry Machines / 2 Electro Acoustic / 3 Hybrid / 4 Overdrive.

Rack layout (donor: templates/electro_acoustic_drumcell_donor.adg, a copy of
the old "606 808 EMI Crush.adg" — 32 DrumCell pads at notes 61-92):
- Kit A fills the top bank, notes 92..81 (sample 01-Kick at 92, .. 12-Cowbell
  at 81); kit B fills notes 76..65 at the same offsets, so any B-half clip
  moves to any A-half by transposing exactly 16 semitones.
- The 4 spare pads per half (80-77 / 64-61) are deleted, so nothing foreign
  is ever left on a pad. Design rule per CLAUDE.md: only swap sample content,
  never reconstruct rack structure.

After a fully successful build the old top-level *.adg racks are deleted
(the donor is preserved in templates/). Re-runs clean the four subfolders
first. Every skipped/odd source folder is reported — no silent drops.

Usage:
    python3 scripts/create_electro_acoustic_racks.py          # build
    python3 scripts/create_electro_acoustic_racks.py --plan   # print plan only
"""

import os
import struct
import sys
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg

# --- Config -----------------------------------------------------------------

SAMPLE_LIBRARY_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Soniccouture/Electro Acoustic"
)
OUTPUT_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Ableton/Drum/Prod/Electro Acoustic"
)
DONOR_PATH = Path(__file__).parent.parent / "templates/electro_acoustic_drumcell_donor.adg"

CATEGORY_DIRS = {  # source folder -> output subfolder
    "Dry": "1 Dry Machines",
    "Electro Acoustic": "2 Electro Acoustic",
    "Hybrid": "3 Hybrid",
    "Distorted": "4 Overdrive",
}

SAMPLES_PER_KIT = 12
TOP_HALF_START = 0    # donor pads note-descending: index 0 = note 92
BOTTOM_HALF_START = 16  # index 16 = note 76

# Known machines, longest-name-first so multiword names match before prefixes.
MACHINES = [
    "Korg 55B", "Rhythm Ace", "Drumulator", "DrumTraks", "LinnDrum",
    "Bentley", "CR80000", "CR8000", "CR78", "SDS8000", "SDS800",
    "DR 110", "DR110", "DR55", "DMX", "MR10", "606", "808", "909",
]
MACHINE_ALIASES = {
    "Bentley": "Rhythm Ace",   # same hardware, two spellings in the export
    "CR80000": "CR8000",
    "SDS8000": "SDS800",
    "DR 110": "DR110",
}
TREATMENT_ALIASES = {  # export typos -> canonical treatment names
    "Bass Ap": "Bass Amp",
    "Bass Neve": "Neve",
    "alve": "Valve",
    "Semii Acoustic": "Semi Acoustic",
    "Fatface": "FatFace",
    "Dry Room": "Dirty Room",   # snapshot list has "CR8000 Dirty Room"
    "PA Mic": "PA Mics",
}
AUDIO_EXTS = {".aif", ".aiff", ".wav"}


# --- Audio metadata ---------------------------------------------------------

def _ext80_to_float(b: bytes) -> float:
    """Decode the 80-bit extended float used for AIFF sample rates."""
    exp = struct.unpack(">H", b[:2])[0]
    mant = struct.unpack(">Q", b[2:10])[0]
    sign = -1.0 if exp & 0x8000 else 1.0
    exp &= 0x7FFF
    if exp == 0 and mant == 0:
        return 0.0
    return sign * mant * 2.0 ** (exp - 16383 - 63)


def audio_info(path: Path):
    """Return (frames, sample_rate) for an AIFF/WAV file (stdlib only;
    the aifc module was removed in Python 3.13)."""
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as w:
            return w.getnframes(), w.getframerate()
    with open(path, "rb") as f:
        hdr = f.read(12)
        if hdr[:4] != b"FORM" or hdr[8:12] not in (b"AIFF", b"AIFC"):
            raise ValueError(f"Not an AIFF file: {path}")
        while True:
            ch = f.read(8)
            if len(ch) < 8:
                break
            cid, size = ch[:4], int.from_bytes(ch[4:8], "big")
            if cid == b"COMM":
                data = f.read(size)
                frames = int.from_bytes(data[2:6], "big")
                rate = int(round(_ext80_to_float(data[8:18])))
                return frames, rate
            f.seek(size + (size & 1), 1)
    raise ValueError(f"No COMM chunk in {path}")


# --- Source scanning --------------------------------------------------------

def parse_folder_name(name: str):
    """Split a kit folder name into (machine, treatment), normalizing typos.

    Returns (None, name) when no known machine prefix matches (Hybrid kits).
    """
    if name.startswith("808PA"):  # "808PA Mics" — missing space in the export
        return "808", "PA Mics"
    for m in MACHINES:
        if name == m or name.startswith(m + " "):
            treatment = name[len(m):].strip()
            machine = MACHINE_ALIASES.get(m, m)
            treatment = TREATMENT_ALIASES.get(treatment, treatment)
            return machine, treatment
    return None, name


def scan_kit(folder: Path, warnings: list):
    """Read a kit folder into an index-sorted sample list.

    Filenames look like "<Kit>-01-Kick-V127-XXXX.aif"; ~37 files across the
    library have glitched random-code suffixes, so only the leading
    "<idx>-<Type>-V<vel>-" fields are trusted.
    """
    import re

    samples = []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in AUDIO_EXTS:
            continue
        m = re.match(r"^.+?-(\d{2})-([A-Za-z-]+?)-V\d+-", f.name)
        if not m:
            warnings.append(f"unparsed filename, skipped: {folder.name}/{f.name}")
            continue
        frames, _ = audio_info(f)
        if frames == 0:  # Korg 55B FatFace 09-12 exported as 4KB empty shells
            warnings.append(f"zero-length audio, skipped: {folder.name}/{f.name}")
            continue
        samples.append({"idx": int(m.group(1)), "type": m.group(2), "path": f})
    samples.sort(key=lambda s: s["idx"])

    if len(samples) != SAMPLES_PER_KIT:
        warnings.append(f"{folder.name}: {len(samples)} samples (expected {SAMPLES_PER_KIT})")
    idxs = [s["idx"] for s in samples]
    if len(set(idxs)) != len(idxs):
        warnings.append(f"{folder.name}: duplicate sample indices {idxs}")
    return samples


def scan_library(warnings: list):
    """Return {category: [kit dicts]} for every non-empty source folder."""
    kits_by_cat = {}
    for cat in CATEGORY_DIRS:
        kits = []
        for folder in sorted((SAMPLE_LIBRARY_ROOT / cat).iterdir()):
            if not folder.is_dir():
                continue
            samples = scan_kit(folder, warnings)
            if not samples:
                warnings.append(f"EMPTY folder skipped: {cat}/{folder.name}")
                continue
            machine, treatment = parse_folder_name(folder.name)
            if cat == "Hybrid":
                machine, treatment = None, None
            kits.append({
                "folder": folder.name,
                "category": cat,
                "machine": machine,
                "treatment": treatment if cat != "Dry" else "Dry",
                # short label used in rack names and pad names
                "short": machine if machine else _strip_kit(folder.name),
                "samples": samples,
            })
        kits_by_cat[cat] = kits
    return kits_by_cat


def _strip_kit(name: str) -> str:
    return name[:-4] if name.endswith(" Kit") else name


# --- Pairing plan -----------------------------------------------------------

def kit_label(kit) -> str:
    """Full descriptive label, e.g. '808 EMI Snareverb' or 'Ack-Ack'."""
    if kit["machine"]:
        return f"{kit['machine']} {kit['treatment']}".strip()
    return _strip_kit(kit["folder"])


def rack_name(a, b) -> str:
    """Name a rack from its one or two kits."""
    if b is None:
        if a["machine"]:
            return f"{a['machine']} - {a['treatment']}"
        return f"Hybrid - {kit_label(a)}"
    if a["machine"] is None:  # hybrid pair
        return f"Hybrid - {kit_label(a)} + {kit_label(b)}"
    if a["treatment"] == b["treatment"]:
        return f"{a['treatment']} - {a['machine']} + {b['machine']}"
    if a["machine"] == b["machine"]:
        return f"{a['machine']} - {a['treatment']} + {b['treatment']}"
    return f"{kit_label(a)} + {kit_label(b)}"


def plan_category(kits, cat):
    """Pair kits into racks. Returns a list of (kitA, kitB|None)."""
    racks = []
    if cat == "Hybrid":
        ordered = sorted(kits, key=lambda k: kit_label(k).lower())
        for i in range(0, len(ordered) - 1, 2):
            racks.append((ordered[i], ordered[i + 1]))
        if len(ordered) % 2:
            racks.append((ordered[-1], None))
        return racks

    # Group by treatment; pair machines alphabetically within each group.
    groups = {}
    for k in kits:
        groups.setdefault(k["treatment"], []).append(k)
    pool = []
    for treatment in sorted(groups):
        members = sorted(groups[treatment], key=lambda k: k["machine"])
        if len(members) < 2:
            pool.extend(members)
            continue
        for i in range(0, len(members) - 1, 2):
            racks.append((members[i], members[i + 1]))
        if len(members) % 2:
            pool.append(members[-1])

    # Leftovers pair by (machine, treatment) so same-machine one-offs meet.
    pool.sort(key=lambda k: (k["machine"], k["treatment"]))
    for i in range(0, len(pool) - 1, 2):
        racks.append((pool[i], pool[i + 1]))
    if len(pool) % 2:
        racks.append((pool[-1], None))
    return racks


# --- Rack building ----------------------------------------------------------

def donor_pads_note_desc(root):
    """The donor drum rack's pad presets, highest ReceivingNote first."""
    for gdp in root.iter("GroupDevicePreset"):
        dev = gdp.find("Device")
        if dev is not None and dev.find("DrumGroupDevice") is not None:
            container = gdp.find("BranchPresets")
            pads = sorted(
                container,
                key=lambda p: int(p.find(".//ZoneSettings/ReceivingNote").get("Value")),
                reverse=True,
            )
            return container, pads
    raise ValueError("Donor has no DrumGroupDevice")


def fill_pad(pad, sample, label, rack_dir: Path):
    """Point one donor DrumCell pad at a new sample file, in place."""
    sr = next(pad.iter("SampleRef"))
    file_ref = sr.find("FileRef")
    path = sample["path"]

    file_ref.find("Path").set("Value", str(path))
    rel = os.path.relpath(path, rack_dir)
    file_ref.find("RelativePath").set("Value", rel)
    size_el = file_ref.find("OriginalFileSize")
    if size_el is not None:
        size_el.set("Value", str(path.stat().st_size))

    frames, rate = audio_info(path)
    for tag, value in (
        ("LastModDate", str(int(path.stat().st_mtime))),
        ("DefaultDuration", str(frames)),
        ("DefaultSampleRate", str(rate)),
    ):
        el = sr.find(tag)
        if el is not None:
            el.set("Value", value)

    pad.find("Name").set("Value", label)


def build_rack(donor_xml: str, kit_a, kit_b, out_path: Path):
    """Fill a fresh donor copy: kit A at notes 92.., kit B at 76.., trim rest."""
    root = ET.fromstring(donor_xml)
    container, pads = donor_pads_note_desc(root)

    keep = set()
    for kit, start in ((kit_a, TOP_HALF_START), (kit_b, BOTTOM_HALF_START)):
        if kit is None:
            continue
        for sample in kit["samples"]:
            # Place by slot number, not list position: a kit missing a middle
            # slot (Boroughs drops 08-Tom-Alt in 37 of 100 kits) must leave that
            # pad empty rather than sliding every later sound up a semitone.
            slot = sample["idx"] - 1
            if not 0 <= slot < 16:
                continue
            pad = pads[start + slot]
            label = f"{kit['short']} {sample['type'].replace('-', ' ')}"
            fill_pad(pad, sample, label, out_path.parent)
            keep.add(id(pad))

    for pad in pads:
        if id(pad) not in keep:
            container.remove(pad)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    xml_string = ET.tostring(root, encoding="unicode", xml_declaration=True)
    encode_adg(xml_string, out_path)
    return len(keep)


# --- Main -------------------------------------------------------------------

def main():
    plan_only = "--plan" in sys.argv

    if not DONOR_PATH.exists():
        sys.exit(f"Donor not found: {DONOR_PATH}")
    donor_xml = decode_adg(DONOR_PATH)
    donor_xml = donor_xml.decode("utf-8") if isinstance(donor_xml, bytes) else donor_xml

    warnings = []
    kits_by_cat = scan_library(warnings)

    total = 0
    for cat in ("Dry", "Electro Acoustic", "Hybrid", "Distorted"):
        out_dir = OUTPUT_ROOT / CATEGORY_DIRS[cat]
        racks = plan_category(kits_by_cat[cat], cat)
        print(f"### {CATEGORY_DIRS[cat]}  ({len(kits_by_cat[cat])} kits -> {len(racks)} racks)")

        if not plan_only:
            for old in sorted(out_dir.glob("*.adg")):
                old.unlink()

        for a, b in racks:
            name = rack_name(a, b)
            desc = kit_label(a) + (f"  +  {kit_label(b)}" if b else "  (solo)")
            if plan_only:
                print(f"  {name:<46} {desc}")
            else:
                filled = build_rack(donor_xml, a, b, out_dir / f"{name}.adg")
                print(f"  {name:<46} {filled} pads   [{desc}]")
            total += 1
        print()

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  !! {w}")
        print()

    if plan_only:
        print(f"Plan: {total} racks (nothing written)")
        return

    old_racks = sorted(OUTPUT_ROOT.glob("*.adg"))
    for old in old_racks:
        old.unlink()
    print(f"Done: {total} racks written; {len(old_racks)} old top-level racks deleted")


if __name__ == "__main__":
    main()
