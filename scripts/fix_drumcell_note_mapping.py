#!/usr/bin/env python3
"""Repair the note mapping of already-placed DrumCell racks, in place.

Background: the first conversion runs filled donor pads in the source kit's
*document/chain order* instead of by ReceivingNote, which scrambled which sound
landed on which note (the kit's note-92 kick could end up on some other pad).
extract_pads() now sorts by ReceivingNote, so a fresh conversion is correct.

This script regenerates every DrumCell rack that already sits at the MAIN level
of each pack folder, overwriting it with a correctly-mapped version, then removes
the leftover "DrumCell Versions" subfolders. Each rack's source kit(s) are found
in the factory pack by parsing the rack's own filename ("A + B" -> kits A,B;
"Name (2)" -> chunk 2 of an oversized kit), so the exact current set/pairing is
preserved — only the pad-to-note mapping changes.

Run:  PYTHONPATH=src python3 scripts/fix_drumcell_note_mapping.py [--dry-run]
"""

import sys
import os
import glob
import re
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from beat_tools_to_drumcell import (  # noqa: E402
    DONOR_PATH, decode_adg, extract_pads, build_rack, PADS_PER_DONOR,
)

PROD = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Ableton/Drum/Prod"
)
PK = Path("/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/Packs")

# pack folder (under PROD) -> factory source-kit directory
FOLDERS = {
    "Beat Tools": PK / "Beat Tools/Drums",
    "Build and Drop": PK / "Build and Drop/Drums",
    "Chop and Swing": PK / "Chop and Swing/Drums",
    "Drive and Glow": PK / "Drive and Glow/Drums",
    "Glitch and Wash": PK / "Glitch and Wash/Drums",
    "Punch and Tilt": PK / "Punch and Tilt/Drums",
    "Skitter and Step": PK / "Skitter and Step/Drums",
    "Mood Reel": PK / "Mood Reel/Drum Racks",
}

_norm = lambda s: s.replace(" ", "").lower()


def build_lut(facdir):
    """Three lookups from factory kits: full stem, ' Kit'-stripped, normalized."""
    fac = glob.glob(str(facdir / "*.adg"))
    full = {Path(p).stem: p for p in fac}
    strip = {Path(p).stem.replace(" Kit", ""): p for p in fac}
    nm = {_norm(Path(p).stem.replace(" Kit", "")): p for p in fac}
    return full, strip, nm


def resolve(base, lut):
    full, strip, nm = lut
    if base in full:
        return full[base]
    if base in strip:
        return strip[base]
    if _norm(base) in nm:
        return nm[_norm(base)]
    return None


def main():
    dry = "--dry-run" in sys.argv
    if not DONOR_PATH.exists():
        sys.exit(f"Donor not found (was it moved?): {DONOR_PATH}")
    donor = decode_adg(DONOR_PATH)
    donor = donor.decode("utf-8") if isinstance(donor, bytes) else donor

    total, fixed, unresolved = 0, 0, []
    for folder, facdir in FOLDERS.items():
        outdir = PROD / folder
        if not outdir.is_dir():
            print(f"!! missing folder {folder}")
            continue
        if not facdir.is_dir():
            print(f"!! missing factory dir for {folder}: {facdir}")
            continue
        lut = build_lut(facdir)
        outs = sorted(glob.glob(str(outdir / "*.adg")))
        print(f"### {folder}  ({len(outs)} racks)")
        for o in outs:
            total += 1
            stem = Path(o).stem
            m = re.match(r"^(.*) \((\d+)\)$", stem)
            base = m.group(1) if m else stem
            chunk = int(m.group(2)) - 1 if m else 0

            srcs = None
            if " + " in base and not m:
                rs = [resolve(p, lut) for p in base.split(" + ")]
                if all(rs):
                    srcs = rs
            if srcs is None:
                r = resolve(base, lut)
                srcs = [r] if r else None
            if srcs is None:
                unresolved.append(f"{folder}/{stem}")
                print(f"  !! UNRESOLVED {stem}")
                continue

            samples = []
            for s in srcs:
                samples += extract_pads(Path(s))
            if m or len(samples) > PADS_PER_DONOR:
                samples = samples[chunk * PADS_PER_DONOR:(chunk + 1) * PADS_PER_DONOR]

            if not dry:
                build_rack(donor, samples, Path(o))
            fixed += 1

        sub = outdir / "DrumCell Versions"
        if sub.is_dir():
            print(f"  {'would remove' if dry else 'removing'} subfolder: {sub.name}/")
            if not dry:
                shutil.rmtree(sub)
        print()

    print(f"{'DRY-RUN — ' if dry else ''}fixed {fixed}/{total} racks, "
          f"{len(unresolved)} unresolved")
    if unresolved:
        print("Unresolved:", unresolved)


if __name__ == "__main__":
    main()
