#!/usr/bin/env python3
"""
Create Soundiron Bronze Bin Drum Rack — one combined 32-pad Drum Rack whose
pads are the library's 13 metal-percussion articulations, each a full
velocity-layered, round-robin Sampler.

templates/sampler_drum_rack_template.adg is a hand-built 32-pad Drum Rack with
a real Sampler already loaded on every pad (macros, colors, choke groups, etc.
authored in Ableton). Every pad's SendingNote is fixed at 60 (C3), so every
embedded Sampler is built on one fixed root note. This script only swaps each
pad's MultiSampleMap/SampleParts in place — nothing structural about the rack
is reconstructed or copied, so there's nothing to fall out of sync with the
donor. (See the "Sampler-Based Drum Rack Workflow" notes in CLAUDE.md.)

Layout: the 7 "bronze bin" articulations fill the lower pads (natural folder
order), the 6 "chrome can" articulations the higher pads (alphabetical). Bronze
pads are colored orange, chrome pads blue. The remaining 19 donor pads are left
untouched.

Two Soundiron quirks this handles that the Damage workflow's
multisample_utils.parse_velocity_layers() does not:

1. Filenames carry no note and use two different schemes, so we parse velocity
   and round-robin positionally and fix every pad on PAD_ROOT_NOTE (60):
       bronze bin:  bronze_<art>_<n>_<VEL>_<RR>.wav   (e.g. bronze_mlt_1_3_07)
       chrome can:  bb_cc_<art>_<name>_v<VEL>_r<RR>.wav (e.g. bb_cc_mlt_side_v10_r01)

2. The VEL numbers are sequential layer indices (1..N, soft->loud), NOT MIDI
   velocities. Passing 1,2,3,... straight into velocity_bins() would cram every
   layer down near velocity 1-N and make all normal playing trigger only the
   loudest layer. Instead each folder's N layers are remapped onto centers
   spread evenly across 1-127 (the same spread Heavyocity's autosampler bakes
   into its V1/V15/.../V127 filenames), so the whole velocity range is covered.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_bronze_bin_drum_rack.py
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, velocity_bins

SAMPLE_LIBRARY_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Soundiron/Soundiron Bronze Bin"
)
SAMPLES_ROOT = SAMPLE_LIBRARY_ROOT / "Samples"
DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler_drum_rack_template.adg"
OUTPUT_DIR = SAMPLE_LIBRARY_ROOT / "Drum Racks"
OUTPUT_PATH = OUTPUT_DIR / "Soundiron_Bronze_Bin.adg"

PAD_ROOT_NOTE = 60  # C3 — matches every pad's fixed SendingNote

# Ableton DocumentColorIndex — bronze pads orange, chrome pads blue (indices
# reused from this project's validated palette; see CATEGORY_COLORS elsewhere).
BRONZE_COLOR = 60  # orange
CHROME_COLOR = 45  # blue

# Two Soundiron filename schemes, VEL = layer index, RR = round-robin take.
BRONZE_RE = re.compile(r"^bronze_[a-z]+_\d+_(?P<vel>\d+)_(?P<rr>\d+)\.wav$", re.IGNORECASE)
CHROME_RE = re.compile(r"^bb_cc_.+_v(?P<vel>\d+)_r(?P<rr>\d+)\.wav$", re.IGNORECASE)


def clean_name(folder_name: str) -> str:
    """Strip a leading order digit and title-case: '1 mallet rim' -> 'Mallet Rim'."""
    return re.sub(r"^\d+\s*", "", folder_name).title()


def parse_soundiron_layers(folder: Path) -> dict:
    """Group a folder's samples by their raw layer index (1..N, soft->loud),
    accepting either Soundiron naming scheme. Returns {raw_index: [paths]}."""
    raw: dict[int, list[Path]] = {}
    for wav in sorted(folder.glob("*.wav")):
        m = BRONZE_RE.match(wav.name) or CHROME_RE.match(wav.name)
        if not m:
            continue
        raw.setdefault(int(m.group("vel")), []).append(wav)
    if not raw:
        raise ValueError(f"No Soundiron-named samples found in {folder}")
    return raw


def remap_to_velocity_centers(raw_layers: dict) -> dict:
    """Map sequential layer indices onto velocity centers spread evenly across
    1-127, so velocity_bins() covers the whole range instead of clustering near
    the raw indices. N=1 collapses to a single full-range layer. For N up to the
    ~15 layers this library uses, the spread centers are always distinct."""
    order = sorted(raw_layers)  # ascending raw index = soft -> loud
    n = len(order)
    remapped: dict[int, list[Path]] = {}
    for i, raw_idx in enumerate(order):
        center = 64 if n == 1 else round(1 + (127 - 1) * i / (n - 1))
        remapped[center] = raw_layers[raw_idx]
    return remapped


def fill_pad(pad: ET.Element, creator: SamplerCreator, folder: Path) -> None:
    """Replace one pad's Sampler SampleParts in place with a folder's
    velocity-layered, round-robin samples, fixed on PAD_ROOT_NOTE."""
    layers = remap_to_velocity_centers(parse_soundiron_layers(folder))

    sample_map = pad.find(".//MultiSampleMap")
    if sample_map is None:
        raise ValueError("Pad's Sampler missing MultiSampleMap element")

    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")
    for part in build_sample_parts(creator, layers, PAD_ROOT_NOTE):
        new_parts.append(part)

    enable_round_robin(sample_map)

    total = sum(len(v) for v in layers.values())
    summary = ", ".join(
        f"v{vmin}-{vmax}:{len(layers[center])}rr" for center, vmin, vmax in velocity_bins(layers.keys())
    )
    print(f"    {len(layers)} velocity layers, {total} samples ({summary})")


def color_pad(pad: ET.Element, color: int) -> None:
    """Set a pad's color (element already exists on every donor pad)."""
    color_elem = pad.find("DocumentColorIndex")
    if color_elem is not None:
        color_elem.set("Value", str(color))
    auto_colored = pad.find("AutoColored")
    if auto_colored is not None:
        auto_colored.set("Value", "false")


def discover_instruments() -> list:
    """Ordered (folder, pad_name, color) for all 13 articulations: bronze bin
    (natural folder order) on the low pads, then chrome can (alphabetical)."""
    instruments = []
    for group, subdir, color in [
        ("Bronze", "bronze bin", BRONZE_COLOR),
        ("Chrome", "chrome can", CHROME_COLOR),
    ]:
        group_root = SAMPLES_ROOT / subdir
        for folder in sorted(p for p in group_root.iterdir() if p.is_dir()):
            instruments.append((folder, f"{group} {clean_name(folder.name)}", color))
    return instruments


def build_combined_rack(instruments: list, creator: SamplerCreator, output_path: Path) -> None:
    rack_root = ET.fromstring(decode_adg(DRUM_RACK_TEMPLATE))

    pads = rack_root.findall(".//BranchPresets/DrumBranchPreset")
    # ascending ReceivingNote so bronze lands on the low pads, chrome on the high
    pads.sort(key=lambda p: int(p.find(".//ZoneSettings/ReceivingNote").get("Value")))

    if len(instruments) > len(pads):
        raise ValueError(f"{len(instruments)} instruments but only {len(pads)} pads available")

    for pad, (folder, pad_name, color) in zip(pads, instruments):
        note = pad.find(".//ZoneSettings/ReceivingNote").get("Value")
        print(f"  Note {note}: {pad_name}  <- {folder.relative_to(SAMPLE_LIBRARY_ROOT)}")
        fill_pad(pad, creator, folder)
        color_pad(pad, color)
        name_elem = pad.find("Name")
        if name_elem is not None:
            name_elem.set("Value", pad_name)

    # Drop the leftover donor pads (each still holds an empty Sampler) so the
    # rack contains only the filled pads. Safe to remove outright: the donor's
    # DrumGroupDevice/Branches and its Chains/DrumPads list wrappers are all
    # empty (Live rebuilds them on load from BranchPresets), and no macro is
    # mapped to any pad, so removing a pad leaves no dangling reference. Kept
    # pads keep their original Ids/ReceivingNotes — neither needs to be contiguous.
    leftover = pads[len(instruments):]
    parent_map = {c: p for p in rack_root.iter() for c in p}
    for pad in leftover:
        parent_map[pad].remove(pad)

    xml_string = ET.tostring(rack_root, encoding="unicode", xml_declaration=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(xml_string, output_path)
    print(f"\nCreated: {output_path} ({len(instruments)} pads, {len(leftover)} empty donor pads removed)")


def main():
    if not DRUM_RACK_TEMPLATE.exists():
        print(f"Error: Drum rack template not found: {DRUM_RACK_TEMPLATE}")
        sys.exit(1)
    if not SAMPLES_ROOT.exists():
        print(f"Error: Samples folder not found: {SAMPLES_ROOT}")
        sys.exit(1)

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)

    instruments = discover_instruments()
    print(f"Found {len(instruments)} articulations under {SAMPLES_ROOT}\n")

    build_combined_rack(instruments, creator, OUTPUT_PATH)


if __name__ == "__main__":
    main()
