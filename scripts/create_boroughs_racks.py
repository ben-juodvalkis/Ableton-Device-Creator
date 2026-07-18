#!/usr/bin/env python3
"""
SonicCouture Electro-Acoustic "Boroughs" -> one DrumCell rack per borough.

Boroughs is the fifth SonicCouture snapshot category, exported 2026-07-18 after
the other four were built by create_electro_acoustic_racks.py. It differs in
shape: the other categories are (machine x treatment) grids whose kits are only
meaningful in pairs ("EMI Crush - 606 + 808"), whereas each of the 100 boroughs
is a self-contained named kit. So there is nothing to pair on here -- one
borough, one rack, named exactly for its snapshot.

Source: <root>/Boroughs/<Borough>/, each holding single-velocity one-shots
numbered 01-Kick .. 12-Cowbell (same filename convention as the other
categories, WAV rather than AIFF).

Rack layout (donor: templates/electro_acoustic_drumcell_donor.adg, 32 DrumCell
pads at notes 61-92): the kit fills the top bank at fixed slot->note offsets --
01-Kick at 92 through 12-Cowbell at 81 -- and every unused pad is deleted.
Because placement is by slot number, the mapping is identical across all 100
racks, so a clip written for one borough triggers the same drum types in any
other. Kits missing a slot leave that one pad absent rather than shifting.

Export gaps are reported, never silently filled: 40 of the 100 boroughs are
missing a middle slot (37 lack 08-Tom-Alt, 3 lack 07-HiHat-Open, and Hexagon
Projection / In Another Space also lack 06-Tom-Hi). Re-exporting those from
Kontakt and re-running would fill the holes.

Usage:
    python3 scripts/create_boroughs_racks.py          # build
    python3 scripts/create_boroughs_racks.py --plan   # print plan only
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from create_electro_acoustic_racks import (
    DONOR_PATH,
    OUTPUT_ROOT,
    SAMPLE_LIBRARY_ROOT,
    SAMPLES_PER_KIT,
    build_rack,
    decode_adg,
    scan_kit,
)

# --- Config -----------------------------------------------------------------

SOURCE_DIR = SAMPLE_LIBRARY_ROOT / "Boroughs"
OUTPUT_DIR = OUTPUT_ROOT / "5 Boroughs"

# Slot -> drum type, for the missing-slot report. Matches the export's own
# numbering (note the inconsistent "Hihat"/"HiHat" casing, which is theirs).
SLOT_NAMES = {
    1: "Kick", 2: "Rim", 3: "Snare", 4: "HiHat",
    5: "Tom-Lo", 6: "Tom-Hi", 7: "HiHat-Open", 8: "Tom-Alt",
    9: "Hihat-Mid", 10: "Ride", 11: "Clap", 12: "Cowbell",
}

# scan_kit flags every short kit; the grouped slot report below says it better.
COUNT_WARNING = re.compile(r": \d+ samples \(expected \d+\)$")


# --- Source scanning --------------------------------------------------------

def scan_boroughs(warnings: list):
    """Return one kit dict per borough folder, alphabetically."""
    kits = []
    for folder in sorted(SOURCE_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not folder.is_dir():
            continue
        samples = scan_kit(folder, warnings)
        if not samples:
            warnings.append(f"EMPTY folder skipped: {folder.name}")
            continue
        kits.append({
            "folder": folder.name,
            "short": folder.name,   # pad labels read "Croydon Kick"
            "samples": samples,
        })
    return kits


def missing_slots(kit):
    """Slot numbers absent from a kit, e.g. [8] for a kit with no Tom-Alt."""
    present = {s["idx"] for s in kit["samples"]}
    return [n for n in range(1, SAMPLES_PER_KIT + 1) if n not in present]


def report_gaps(kits):
    """Print boroughs with missing slots, grouped by which slots they lack."""
    by_gap = {}
    for kit in kits:
        gap = tuple(missing_slots(kit))
        if gap:
            by_gap.setdefault(gap, []).append(kit["folder"])
    if not by_gap:
        return
    total = sum(len(v) for v in by_gap.values())
    print(f"Incomplete kits ({total} of {len(kits)}) -- pads left empty, re-export to fill:")
    for gap in sorted(by_gap, key=lambda g: (-len(by_gap[g]), g)):
        names = sorted(by_gap[gap], key=str.lower)
        label = ", ".join(f"{n:02d}-{SLOT_NAMES[n]}" for n in gap)
        shown = ", ".join(names[:6]) + (f", +{len(names) - 6} more" if len(names) > 6 else "")
        print(f"  missing {label}  ({len(names)}): {shown}")
    print()


# --- Main -------------------------------------------------------------------

def main():
    plan_only = "--plan" in sys.argv

    if not DONOR_PATH.exists():
        sys.exit(f"Donor not found: {DONOR_PATH}")
    if not SOURCE_DIR.is_dir():
        sys.exit(f"Source not found: {SOURCE_DIR}")

    donor_xml = decode_adg(DONOR_PATH)
    donor_xml = donor_xml.decode("utf-8") if isinstance(donor_xml, bytes) else donor_xml

    warnings = []
    kits = scan_boroughs(warnings)
    print(f"### 5 Boroughs  ({len(kits)} boroughs -> {len(kits)} racks)\n")

    if not plan_only:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for old in sorted(OUTPUT_DIR.glob("*.adg")):
            old.unlink()

    for kit in kits:
        name = kit["folder"]
        if plan_only:
            print(f"  {name:<28} {len(kit['samples'])} pads")
        else:
            filled = build_rack(donor_xml, kit, None, OUTPUT_DIR / f"{name}.adg")
            print(f"  {name:<28} {filled} pads")
    print()

    report_gaps(kits)

    other = [w for w in warnings if not COUNT_WARNING.search(w)]
    if other:
        print("Warnings:")
        for w in other:
            print(f"  !! {w}")
        print()

    if plan_only:
        print(f"Plan: {len(kits)} racks (nothing written)")
    else:
        print(f"Done: {len(kits)} racks written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
