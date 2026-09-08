#!/usr/bin/env python3
"""
Create the Hands Make Sounds Kit — one Drum Rack of Multi-Samplers from the
99Sounds "Hands Make Sounds" free library (hand claps + finger snaps).

Like the Soundiron Rust workflow (create_rust_round_robin_racks.py), these
samples carry NO velocity or note information — the shipped Claps.sfz/Snaps.sfz
map every take flat across lovel=0..hivel=127, one sample per key, purely to
browse them. So there are no velocity layers to build: each recorded "space"
becomes one pad whose numbered takes are round-robin alternates over the full
1-127 velocity range, fixed on PAD_ROOT_NOTE (60).

Filename convention: "<type>-<space>-<NN>.wav" (e.g. clap-bathroom-07.wav,
snap-far-12.wav). The take index is the trailing "-<NN>"; stripping it yields
the pad group. The library's natural grouping is by acoustic space:

    Claps: bathroom, corridor, hall, room, toilet
    Snaps: close, far                                 -> 7 pads total

Layout follows this project's Drum Rack convention (see CLAUDE.md): pads are
assigned highest-note-first so the list reads top-to-bottom in Live (groups in
alphabetical order — Clap Bathroom at the top, Snap Far at the bottom), and
donor pads we don't fill are deleted so none are left empty. Only each pad's
MultiSampleMap/SampleParts and Name are touched; the donor's macros, colors,
choke groups and mixer are left as built.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_hands_make_sounds_kit.py            # dry run (report only)
    python3 scripts/create_hands_make_sounds_kit.py --write    # actually build .adg
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import enable_round_robin

SAMPLE_LIBRARY_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/99Sounds/[99Sounds] Hands Make Sounds"
)
DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler_drum_rack_template.adg"
OUTPUT_DIR = SAMPLE_LIBRARY_ROOT / "Drum Racks"
KIT_NAME = "Hands Make Sounds"

PAD_ROOT_NOTE = 60   # C3 — matches every pad's fixed SendingNote in the donor
PADS_PER_RACK = 32

_TAKE_RE = re.compile(r"-\d+$")   # trailing "-NN" round-robin take index


def group_key(stem: str) -> str:
    """'clap-bathroom-07' -> 'clap-bathroom'. Everything sharing the result is
    one pad (round-robin takes of one recorded space)."""
    return _TAKE_RE.sub("", stem)


def pad_name(key: str) -> str:
    """'clap-bathroom' -> 'Clap Bathroom'."""
    return key.replace("-", " ").title()


def collect_pads(root: Path) -> List[tuple]:
    """Scan the library into (pad_name, [round-robin sample paths]) pairs,
    ordered by group key so the rack reads Clap Bathroom -> Snap Far."""
    groups: Dict[str, List[Path]] = defaultdict(list)
    for wav in root.rglob("*.wav"):
        groups[group_key(wav.stem)].append(wav)
    return [
        (pad_name(key), sorted(groups[key], key=lambda p: p.name))
        for key in sorted(groups)
    ]


def _receiving_note(pad_elem: ET.Element) -> int:
    return int(pad_elem.find(".//ZoneSettings/ReceivingNote").get("Value"))


def fill_pad(pad_elem: ET.Element, creator: SamplerCreator, samples: List[Path], name: str) -> None:
    """Replace a pad's Sampler SampleParts in place with round-robin takes over
    the full velocity range, fixed on PAD_ROOT_NOTE, and enable cyclic round
    robin. Only the pad's sample content and Name are touched."""
    sample_map = pad_elem.find(".//MultiSampleMap")
    if sample_map is None:
        raise ValueError("Pad's Sampler missing MultiSampleMap element")
    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")
    for index, sample_path in enumerate(samples):
        new_parts.append(
            creator._create_sample_part(
                index=index,
                sample_path=sample_path,
                key_min=PAD_ROOT_NOTE,
                key_max=PAD_ROOT_NOTE,
                root_key=PAD_ROOT_NOTE,
            )
        )
    enable_round_robin(sample_map)

    name_elem = pad_elem.find("Name")
    if name_elem is not None:
        name_elem.set("Value", name)


def build_rack(rack_name: str, pads: List[tuple], creator: SamplerCreator) -> Path:
    """Build one Drum Rack from `pads`. Surplus donor pads are deleted (none
    left empty), and pads are assigned highest-note-first so the list reads
    top-to-bottom in Live (see CLAUDE.md 'Pad order')."""
    rack_root = ET.fromstring(decode_adg(DRUM_RACK_TEMPLATE))
    branch_parent = rack_root.find(".//BranchPresets")
    pad_elems = sorted(branch_parent.findall("DrumBranchPreset"), key=_receiving_note)
    if len(pads) > len(pad_elems):
        raise ValueError(f"{len(pads)} pads but donor rack has only {len(pad_elems)} slots")

    keep = pad_elems[:len(pads)]
    for surplus in pad_elems[len(pads):]:
        branch_parent.remove(surplus)

    for pad_elem, (name, samples) in zip(sorted(keep, key=_receiving_note, reverse=True), pads):
        fill_pad(pad_elem, creator, samples, name)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{rack_name}.adg"
    encode_adg(ET.tostring(rack_root, encoding="unicode", xml_declaration=True), output_path)
    return output_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the Hands Make Sounds drum rack.")
    ap.add_argument("--write", action="store_true", help="actually write .adg (default: dry run)")
    args = ap.parse_args()

    if not DRUM_RACK_TEMPLATE.exists():
        sys.exit(f"Error: donor template not found: {DRUM_RACK_TEMPLATE}")
    if not SAMPLE_LIBRARY_ROOT.exists():
        sys.exit(f"Error: sample library not found: {SAMPLE_LIBRARY_ROOT}")

    pads = collect_pads(SAMPLE_LIBRARY_ROOT)
    print(f"Scanning: {SAMPLE_LIBRARY_ROOT}\n")
    for name, samples in pads:
        print(f"    • {name:<20} {len(samples):>3} round-robin takes")
    print(f"\nTotal: {len(pads)} pads, {sum(len(s) for _, s in pads)} samples")

    if len(pads) > PADS_PER_RACK:
        sys.exit(f"Error: {len(pads)} pads exceeds one {PADS_PER_RACK}-pad rack")

    if not args.write:
        print(f"\nDry run — pass --write to build. Output would go to:\n  {OUTPUT_DIR}")
        return

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)
    path = build_rack(KIT_NAME, pads, creator)
    print(f"\nCreated: {path}  ({len(pads)} pads)")


if __name__ == "__main__":
    main()
