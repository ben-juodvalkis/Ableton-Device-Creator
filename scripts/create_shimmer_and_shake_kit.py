#!/usr/bin/env python3
"""
Create the Shimmer and Shake Kit — a few 32-pad Drum Racks collecting every
velocity-mapped note of the Nine Volt Audio "Shimmer and Shake" Kontakt
library as its own pad.

The library is finely VELOCITY-sampled and mapped BY NOTE. Filenames end in
`<Note>-<velocity>.wav`, where the note (C3, E3, F3, ...) is the mapped key and
the trailing number is the recorded MIDI velocity (values run ~1,3,5..127).
The delimiter before the note varies (`bp_C3-001`, `cax_060-C3-001`,
`sb-A1-127`, `off-tam-mod-C3-019`), so NOTE_VEL_RE anchors on the *end*.

Grouping: for each instrument we take the MAIN articulation (name not starting
with `off-`) and make ONE PAD PER NOTE that carries a real velocity map
(>= MIN_SAMPLES_PER_NOTE samples). E.g. Caxixi -> pads `Caxixi C3`, `Caxixi
E3`, `Caxixi F3`, `Caxixi G3`. Within a pad the samples are split into velocity
layers straight from the filename velocity (multisample_utils.velocity_bins on
the distinct values); samples sharing a velocity become round-robin alternates.
All parts sit on PAD_ROOT_NOTE (60), matching every pad's SendingNote in the
donor, so nothing is transposed.

Not included (reported, never dropped silently): the `off-*` articulation,
single-key notes below the velocity-map threshold (the outer chromatic keys),
and files with no `<Note>-<velocity>` tail.

Layout: pads are packed into full 32-pad racks and fill the donor's own pads
lowest-note first (surplus donor pads deleted). We do NOT rewrite
`ReceivingNote` — Live positions pads by the donor's note assignment and
script-editing it just empties the pad, so the kit lands on the donor's note
range (61–92). To start the kit at C1 the donor must be rebuilt in Ableton and
re-exported (see CLAUDE.md).

Usage:
    export PYTHONPATH=src
    python3 scripts/create_shimmer_and_shake_kit.py            # dry run (report only)
    python3 scripts/create_shimmer_and_shake_kit.py --write    # actually build .adg
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, note_name_to_midi, velocity_bins

SAMPLE_LIBRARY_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Nine Volt Audio/Shimmer and Shake Kontakt"
)
ASSETS_DIR = SAMPLE_LIBRARY_ROOT / "Assets"
DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler_drum_rack_template.adg"
OUTPUT_DIR = SAMPLE_LIBRARY_ROOT / "Drum Racks"
KIT_NAME = "Shimmer and Shake"

PAD_ROOT_NOTE = 60          # C3 — matches every pad's fixed SendingNote in the donor
PADS_PER_RACK = 32
MIN_SAMPLES_PER_NOTE = 5    # a note needs at least this many samples to be its own pad

NON_INSTRUMENT_DIRS = {"Wallpaper", "Impulse Responses"}
# note + velocity at the very end of the name, after a '-' or '_' delimiter
NOTE_VEL_RE = re.compile(r"[-_]([A-G]#?-?\d+)-(\d+)\.wav$", re.IGNORECASE)
OFF_RE = re.compile(r"^off[-_]", re.IGNORECASE)


def instrument_name(folder: Path) -> str:
    """'Calabash Maracas Hi Samples' -> 'Calabash Maracas Hi'."""
    return re.sub(r"\s+Samples$", "", folder.name).strip()


def parse_folder(folder: Path) -> Tuple[Dict[str, List[Tuple[Path, int]]], int, int]:
    """Group one instrument's MAIN-articulation samples by note name.

    Returns ({note: [(path, velocity)]}, off_count, unmatched_count). off/off-*
    files and files without a `<Note>-<velocity>` tail are counted (for the
    coverage report), not grouped."""
    by_note: Dict[str, List[Tuple[Path, int]]] = defaultdict(list)
    off = unmatched = 0
    for wav in folder.glob("*.wav"):
        if OFF_RE.match(wav.name):
            off += 1
            continue
        m = NOTE_VEL_RE.search(wav.name)
        if not m:
            unmatched += 1
            continue
        by_note[m.group(1)].append((wav, int(m.group(2))))
    return by_note, off, unmatched


def velocity_layers(samples: List[Tuple[Path, int]]) -> Dict[int, List[Path]]:
    """{velocity: [paths]} straight from the filename velocity — each distinct
    value becomes a layer (velocity_bins turns them into contiguous ranges);
    same-velocity samples become round-robin alternates."""
    layers: Dict[int, List[Path]] = defaultdict(list)
    for path, vel in samples:
        layers[vel].append(path)
    return dict(layers)


def fill_pad(pad_elem: ET.Element, creator: SamplerCreator,
             layers: Dict[int, List[Path]], name: str) -> None:
    """Replace a pad's Sampler SampleParts in place with the velocity-split
    multisample, and enable cyclic round robin (for any same-velocity ties)."""
    sample_map = pad_elem.find(".//MultiSampleMap")
    if sample_map is None:
        raise ValueError("Pad's Sampler missing MultiSampleMap element")
    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")
    for part in build_sample_parts(creator, layers, root_note=PAD_ROOT_NOTE):
        new_parts.append(part)
    enable_round_robin(sample_map)

    name_elem = pad_elem.find("Name")
    if name_elem is not None:
        name_elem.set("Value", name)


def _receiving_note(pad_elem: ET.Element) -> int:
    return int(pad_elem.find(".//ZoneSettings/ReceivingNote").get("Value"))


def build_rack(rack_name: str, pads: List[Tuple[str, Dict[int, List[Path]]]],
               creator: SamplerCreator) -> Path:
    """Build one Drum Rack by filling the donor's own pads, lowest note first
    (pads[0] on the donor's lowest note). Surplus donor pads are deleted.

    IMPORTANT: we do NOT rewrite `ReceivingNote`. Live positions drum pads by
    the donor's own note assignment, and script-editing `ReceivingNote` does
    *not* move the pad in Live's grid — it just detaches the chain and the pad
    shows up empty. So the kit lands on the donor's note range (61–92); to move
    it (e.g. start at C1) the donor must be rebuilt in Ableton and re-exported
    (see CLAUDE.md 'Pad order' / template notes)."""
    rack_root = ET.fromstring(decode_adg(DRUM_RACK_TEMPLATE))
    branch_parent = rack_root.find(".//BranchPresets")
    pad_elems = sorted(branch_parent.findall("DrumBranchPreset"), key=_receiving_note)
    if len(pads) > len(pad_elems):
        raise ValueError(f"{len(pads)} pads but donor rack has only {len(pad_elems)} slots")

    keep = pad_elems[:len(pads)]                      # lowest-note donor pads
    for surplus in pad_elems[len(pads):]:
        branch_parent.remove(surplus)

    for pad_elem, (name, layers) in zip(keep, pads):  # pads[0] -> lowest kept note
        fill_pad(pad_elem, creator, layers, name)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{rack_name}.adg"
    encode_adg(ET.tostring(rack_root, encoding="unicode", xml_declaration=True), output_path)
    return output_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the Shimmer and Shake drum racks.")
    ap.add_argument("--write", action="store_true", help="actually write .adg (default: dry run)")
    args = ap.parse_args()

    if not DRUM_RACK_TEMPLATE.exists():
        sys.exit(f"Error: donor template not found: {DRUM_RACK_TEMPLATE}")
    if not ASSETS_DIR.exists():
        sys.exit(f"Error: Assets folder not found: {ASSETS_DIR}")

    folders = sorted(
        p for p in ASSETS_DIR.iterdir()
        if p.is_dir() and p.name not in NON_INSTRUMENT_DIRS
    )

    # One pad per (instrument, note) that carries a real velocity map, ordered
    # by instrument then note (ascending), packed into full 32-pad racks.
    pads: List[Tuple[str, Dict[int, List[Path]]]] = []
    used = off_total = unmatched_total = thin_notes = thin_samples = 0
    print(f"Scanning: {ASSETS_DIR}\n")
    for folder in folders:
        by_note, off, unmatched = parse_folder(folder)
        off_total += off
        unmatched_total += unmatched
        inst = instrument_name(folder)
        kept = []
        for note in sorted(by_note, key=note_name_to_midi):
            samples = by_note[note]
            if len(samples) < MIN_SAMPLES_PER_NOTE:
                thin_notes += 1
                thin_samples += len(samples)
                continue
            layers = velocity_layers(samples)
            pads.append((f"{inst} {note}", layers))
            used += len(samples)
            kept.append(f"{note}×{len(samples)}")
        print(f"    {inst:<26} pads: {', '.join(kept) if kept else '(none)'}")

    batches = [pads[i:i + PADS_PER_RACK] for i in range(0, len(pads), PADS_PER_RACK)]
    print(f"\nTotal: {len(pads)} pads across {len(batches)} racks, {used} samples used")
    print(f"Excluded: {off_total} off-articulation, {thin_samples} samples on "
          f"{thin_notes} single/thin notes, {unmatched_total} odd-format")

    if not args.write:
        print(f"\nDry run — pass --write to build. Output would go to:\n  {OUTPUT_DIR}")
        return

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)
    print()
    for i, batch in enumerate(batches, 1):
        rack_name = f"{KIT_NAME} {i:02d}"
        path = build_rack(rack_name, batch, creator)
        print(f"Created: {path}  ({len(batch)} pads)")


if __name__ == "__main__":
    main()
