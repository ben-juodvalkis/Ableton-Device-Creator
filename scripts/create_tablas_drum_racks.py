#!/usr/bin/env python3
"""
Create Soundiron Tablas Drum Racks — two 32-pad Drum Racks whose pads are the
library's individual one-shot *strokes*, each a velocity-layered, round-robin
Sampler:

    Soundiron_Tabla         <- tabla/a, tabla/b, tabla/c, tabla/d   (~20 pads)
    Soundiron_Bayan_Combo   <- bayan + combo                        (~24 pads)

Built on templates/sampler_drum_rack_template.adg exactly like the Bronze Bin
script: every pad already holds a real Sampler with SendingNote fixed at 60, so
we only swap each pad's MultiSampleMap/SampleParts and never reconstruct rack
structure. Empty leftover donor pads are deleted so each rack holds only real
pads (see the Bronze Bin script / CLAUDE.md for why that removal is safe).

Unlike Bronze Bin (one folder = one pad), a tabla folder holds MANY strokes, so
the pad unit here is one *stroke*. Filenames encode <stroke>_<velocity>_<RR>
(the trailing token is always round-robin 1-10; the middle is the velocity
layer). As with Bronze Bin the velocity numbers are sequential layer indices,
so each stroke's layers are remapped evenly across 1-127.

This library has no manual and the Kontakt .nki group names aren't recoverable,
so strokes get generic numbered names (e.g. "Tabla A 3", "Bayan C 2"). Rename
in Ableton if you know the real bols.

Messiness handled (per the survey of the folders):
  - macOS "(1)" duplicate files are skipped.
  - tabla/a double-sampled strokes 2 & 3 with full velocity layers (3-number
    names) on top of the flat 1-velocity set (2-number names); for any stroke
    the velocity-layered take wins, otherwise the flat take is one layer.
  - inconsistent prefixes are matched per scheme (tabla_d / tablas_d,
    single / singles, combo_single_a / tab_combo_A).
  - the malformed bayan_single_a 2-number files (literal "x", 28-47 takes) have
    no scheme here, so they're dropped; counts are printed.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_tablas_drum_racks.py
"""

import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, velocity_bins

SAMPLE_LIBRARY_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Soundiron/Soundiron_Tablas"
)
DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler_drum_rack_template.adg"
OUTPUT_DIR = SAMPLE_LIBRARY_ROOT / "Drum Racks"

PAD_ROOT_NOTE = 60  # C3 — matches every pad's fixed SendingNote
DUPE_RE = re.compile(r"\(\d+\)")  # macOS "name (1).wav" duplicate downloads

# A "scheme" is one logical articulation group: (subfolder, filename regex whose
# groups are (stroke, velocity, rr) for arity 3 or (stroke, rr) for arity 2,
# arity, pad-name prefix, Ableton color index). Schemes that share a prefix are
# merged by stroke (velocity-layered take wins) — that's how tabla/a's two takes
# collapse to one pad per stroke.
Scheme = lambda folder, rx, arity, prefix, color: (folder, re.compile(rx), arity, prefix, color)

RACKS = OrderedDict([
    ("Soundiron_Tabla", [
        Scheme("tabla/a", r"tablas_single_a_(\d+)_(\d+)_(\d+)\.wav$", 3, "Tabla A", 60),
        Scheme("tabla/a", r"tablas_single_a_(\d+)_(\d+)\.wav$",       2, "Tabla A", 60),
        Scheme("tabla/b", r"tablas_singles_b_(\d+)_(\d+)_(\d+)\.wav$", 3, "Tabla B", 62),
        Scheme("tabla/c", r"tablas_single_c_(\d+)_(\d+)_(\d+)\.wav$",  3, "Tabla C", 45),
        Scheme("tabla/d", r"tablas?_d_(\d+)_(\d+)_(\d+)\.wav$",        3, "Tabla D", 49),
    ]),
    ("Soundiron_Bayan_Combo", [
        Scheme("bayan", r"bayan_single_a_(\d+)_(\d+)_(\d+)\.wav$", 3, "Bayan A", 16),
        # strokes 3 & 9 were captured single-velocity with many round-robins
        # (2-number names, like tabla/a); recover them. The literal-"x" junk
        # files don't match either regex, so they stay dropped.
        Scheme("bayan", r"bayan_single_a_(\d+)_(\d+)\.wav$",       2, "Bayan A", 16),
        Scheme("bayan", r"bayan_single_b_(\d+)_(\d+)_(\d+)\.wav$", 3, "Bayan B", 26),
        Scheme("bayan", r"bayan_c_(\d+)_(\d+)_(\d+)\.wav$",        3, "Bayan C", 43),
        Scheme("combo", r"combo_single_a_(\d+)_(\d+)_(\d+)\.wav$", 3, "Combo A", 58),
        Scheme("combo", r"tab_combo_A(\d+)_(\d+)_(\d+)\.wav$",     3, "Combo B", 9),
    ]),
])


def remap_to_velocity_centers(raw_layers: dict) -> dict:
    """Map sequential layer indices (1..N, soft->loud) onto velocity centers
    spread evenly across 1-127, so velocity_bins() covers the whole range
    instead of clustering near the raw indices. N=1 -> one full-range layer."""
    order = sorted(raw_layers)
    n = len(order)
    remapped: dict = {}
    for i, raw_idx in enumerate(order):
        center = 64 if n == 1 else round(1 + (127 - 1) * i / (n - 1))
        remapped[center] = raw_layers[raw_idx]
    return remapped


def build_pad_specs(schemes: list) -> tuple:
    """Turn a rack's schemes into an ordered list of pad specs:
    (pad_name, color, {velocity_index: [sample_paths]}).
    Returns (specs, dupes_skipped, unmatched_by_folder)."""
    # prefix -> {stroke -> {"multi": {vel: [paths]}, "single": [paths]}}
    by_prefix: "OrderedDict[str, dict]" = OrderedDict()
    prefix_color: dict = {}
    dupes = 0
    matched_names: dict = defaultdict(set)   # folder -> set of matched filenames
    folder_files: dict = {}                  # folder -> all non-dupe wavs

    for folder, rx, arity, prefix, color in schemes:
        by_prefix.setdefault(prefix, {})
        prefix_color[prefix] = color
        fdir = SAMPLE_LIBRARY_ROOT / folder
        if folder not in folder_files:
            folder_files[folder] = [w for w in sorted(fdir.glob("*.wav")) if not DUPE_RE.search(w.name)]
            dupes += sum(1 for w in fdir.glob("*.wav") if DUPE_RE.search(w.name))
        for wav in folder_files[folder]:
            m = rx.match(wav.name)
            if not m:
                continue
            matched_names[folder].add(wav.name)
            stroke = int(m.group(1))
            entry = by_prefix[prefix].setdefault(stroke, {"multi": defaultdict(list), "single": []})
            if arity == 3:
                entry["multi"][int(m.group(2))].append(wav)
            else:
                entry["single"].append(wav)

    specs = []
    for prefix, strokes in by_prefix.items():
        for stroke in sorted(strokes):
            entry = strokes[stroke]
            layers = dict(entry["multi"]) if entry["multi"] else {1: entry["single"]}
            specs.append((f"{prefix} {stroke}", prefix_color[prefix], layers))

    unmatched = {
        folder: [w.name for w in files if w.name not in matched_names[folder]]
        for folder, files in folder_files.items()
    }
    return specs, dupes, unmatched


def fill_pad(pad: ET.Element, creator: SamplerCreator, layers: dict) -> str:
    """Swap a pad's Sampler SampleParts for a stroke's velocity-layered,
    round-robin samples, fixed on PAD_ROOT_NOTE. Returns a one-line summary."""
    centers = remap_to_velocity_centers(layers)

    sample_map = pad.find(".//MultiSampleMap")
    if sample_map is None:
        raise ValueError("Pad's Sampler missing MultiSampleMap element")
    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")
    for part in build_sample_parts(creator, centers, PAD_ROOT_NOTE):
        new_parts.append(part)
    enable_round_robin(sample_map)

    total = sum(len(v) for v in centers.values())
    return f"{len(centers)} vel layers, {total} samples"


def color_pad(pad: ET.Element, color: int) -> None:
    color_elem = pad.find("DocumentColorIndex")
    if color_elem is not None:
        color_elem.set("Value", str(color))
    auto_colored = pad.find("AutoColored")
    if auto_colored is not None:
        auto_colored.set("Value", "false")


def build_rack(rack_name: str, schemes: list, creator: SamplerCreator, output_path: Path) -> bool:
    print(f"\n=== {rack_name} ===")
    specs, dupes, unmatched = build_pad_specs(schemes)

    rack_root = ET.fromstring(decode_adg(DRUM_RACK_TEMPLATE))
    branch_parent = rack_root.find(".//BranchPresets")
    rn = lambda p: int(p.find(".//ZoneSettings/ReceivingNote").get("Value"))
    pad_elems = sorted(branch_parent.findall("DrumBranchPreset"), key=rn)

    if len(specs) > len(pad_elems):
        print(f"  Error: {len(specs)} strokes but only {len(pad_elems)} pads available")
        return False

    # Keep the lowest-note branches we need; delete the surplus so no empty pads
    # are left behind (safe — see module docstring / Bronze Bin).
    keep = pad_elems[:len(specs)]
    removed = len(pad_elems) - len(specs)
    for surplus in pad_elems[len(specs):]:
        branch_parent.remove(surplus)

    # Fill highest kept note first: Live lays a Drum Rack out highest-note-first
    # (top-to-bottom), so item #1 lands on the TOP pad and the rack reads in
    # order downward. Filling lowest-first would flip it upside down.
    total_samples = 0
    for pad, (pad_name, color, layers) in zip(sorted(keep, key=rn, reverse=True), specs):
        note = pad.find(".//ZoneSettings/ReceivingNote").get("Value")
        summary = fill_pad(pad, creator, layers)
        color_pad(pad, color)
        name_elem = pad.find("Name")
        if name_elem is not None:
            name_elem.set("Value", pad_name)
        total_samples += sum(len(v) for v in layers.values())
        print(f"  Note {note}: {pad_name:10}  ({summary})")

    xml_string = ET.tostring(rack_root, encoding="unicode", xml_declaration=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(xml_string, output_path)

    dropped = sum(len(v) for v in unmatched.values())
    print(f"  --- {len(specs)} pads, {total_samples} samples | skipped {dupes} dupes, "
          f"{dropped} unmatched files, removed {removed} empty pads")
    for folder, names in unmatched.items():
        if names:
            print(f"      unmatched in {folder}: {len(names)} (e.g. {names[0]})")
    print(f"  Created: {output_path}")
    return True


def main():
    if not DRUM_RACK_TEMPLATE.exists():
        print(f"Error: Drum rack template not found: {DRUM_RACK_TEMPLATE}")
        sys.exit(1)
    if not SAMPLE_LIBRARY_ROOT.exists():
        print(f"Error: Sample library not found: {SAMPLE_LIBRARY_ROOT}")
        sys.exit(1)

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)
    results = {
        name: build_rack(name, schemes, creator, OUTPUT_DIR / f"{name}.adg")
        for name, schemes in RACKS.items()
    }

    print("\nSummary:")
    for name, ok in results.items():
        print(f"  {'OK' if ok else 'FAILED'}: {name}")
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
