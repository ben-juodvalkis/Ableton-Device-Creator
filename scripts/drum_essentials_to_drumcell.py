#!/usr/bin/env python3
"""Build DrumCell drum racks from the factory *Drum Essentials* pack.

Same donor-swap workflow as ``beat_tools_to_drumcell.py`` (which supplies the
shared conversion functions), but the source library lives in Ableton's factory
Packs area and is organised into category subfolders. Output goes to the
Desktop, mirroring the category layout, so nothing is written into the factory
pack itself.

Per category: 16-pad kits are paired alphabetically into full 32-pad racks
(donor pads 0-15 = kit A, 16-31 = kit B); other sizes convert solo, and kits
larger than the 32-pad donor (the two 64-pad Hybrid kits) are split across
"(1)/(2)" racks by ``write_solo``.

The **Synthesized** category is intentionally excluded: every pad there is an
Operator synth voice with no sample to rehost into a DrumCell.

Run:  PYTHONPATH=src python3 scripts/drum_essentials_to_drumcell.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from beat_tools_to_drumcell import (  # noqa: E402
    DONOR_PATH,
    decode_adg,
    plan_folder,
    combine_kits,
    write_solo,
)

SOURCE_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/Packs/"
    "Drum Essentials/Drums"
)
OUTPUT_ROOT = Path("/Users/Music/Desktop/Drum Essentials DrumCell")

# Synthesized omitted on purpose — Operator-based pads, no samples.
CATEGORIES = ["Acoustic", "Drum Machines", "Hybrid"]


def main():
    if not DONOR_PATH.exists():
        sys.exit(f"Donor not found: {DONOR_PATH}")

    donor_xml = decode_adg(DONOR_PATH)
    donor_xml_str = donor_xml.decode("utf-8") if isinstance(donor_xml, bytes) else donor_xml

    print(f"Donor:  {DONOR_PATH.name}")
    print(f"Output: {OUTPUT_ROOT}\n")
    grand_total = 0

    for cat in CATEGORIES:
        src = SOURCE_ROOT / cat
        if not src.is_dir():
            print(f"!! Skipping missing category: {cat}")
            continue
        out_dir = OUTPUT_ROOT / cat
        pairs, solos = plan_folder(src)
        print(f"### {cat}")

        for kit_a, kit_b in pairs:
            a = kit_a.stem.replace(" Kit", "")
            b = kit_b.stem.replace(" Kit", "")
            out = out_dir / f"{a} + {b}.adg"
            filled, kept = combine_kits(donor_xml_str, [kit_a, kit_b], out)
            print(f"  pair  {a + ' + ' + b:<38} {filled} samples / {kept} pads")
            grand_total += 1

        for kit in solos:
            for name, filled in write_solo(donor_xml_str, kit, out_dir):
                tag = "solo " if name == kit.stem else "split"
                print(f"  {tag} {name:<38} {filled} samples")
                grand_total += 1
        print()

    print(f"Done: {grand_total} racks written to {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
