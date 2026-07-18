#!/usr/bin/env python3
"""
Create Rust Round-Robin Drum Racks — full 32-pad Drum Racks built from the
Soundiron Rust 1 "found sound" library, where every pad is a full Multi-Sampler
loaded with the round-robin takes of a single articulation.

Unlike the autosampled Damage library (see create_variety_drum_rack.py), Rust
samples carry NO note or velocity information in their filenames — they are
unpitched one-shots recorded in numbered round-robin takes, e.g.

    crowbar_1_01.wav ... crowbar_1_09.wav   -> pad "crowbar_1"  (9 RR takes)
    galvpipe_2_c_01.wav ... _10.wav         -> pad "galvpipe_2_c" (10 RR takes)
    Dmst_heavy_01_01_L.wav / _01_R.wav ...  -> pad "Dmst_heavy_01"

so there are no velocity layers to build — each articulation becomes one pad
whose samples are round-robin alternates over the full 1-127 velocity range,
fixed on the pad's root note (60, matching every pad's SendingNote in the
donor template). Ableton's native cyclic round robin then alternates the takes.

Grouping (see articulation_key): the round-robin take index is the trailing
"_<number>" on the stem, optionally preceded by an "_L"/"_R" channel marker
(only the Dumpster "Dmst_*" files use that, and their _L/_R pairs are full
stereo takes, so they're kept as extra round robins rather than split apart).
Stripping that suffix yields the articulation; everything sharing it is one pad.

Packing: every articulation across the whole library is laid out in object order
(objects alphabetical, articulations alphabetical within each) and flowed into
sequential full 32-pad racks ("Rust Round Robin NN.adg"), so each object's hits
stay adjacent and no pads are wasted except at the tail of the last rack. Pads
with a single take are kept (a valid one-shot, just nothing to alternate) and
their count reported so nothing is dropped silently.

Structural rule (see CLAUDE.md): templates/sampler_drum_rack_template.adg is a
hand-built 32-pad Drum Rack with a configured Multi-Sampler already on every
pad. This script only swaps each pad's MultiSampleMap/SampleParts in place and
sets the pad Name — it never reconstructs macros, colors, choke groups, or the
rack structure, so there is nothing to fall out of sync with the donor.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_rust_round_robin_racks.py
"""

import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import enable_round_robin

SAMPLE_LIBRARY_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Soundiron/Soundiron Rust 1 v2.0"
)
SAMPLES_DIR = SAMPLE_LIBRARY_ROOT / "Samples"
DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler_drum_rack_template.adg"
OUTPUT_DIR = SAMPLE_LIBRARY_ROOT / "Drum Racks"

PAD_ROOT_NOTE = 60   # C3 — matches every pad's fixed SendingNote in the donor
PADS_PER_RACK = 32

# Per-pad Sampler tuning applied to every pad on top of the donor template,
# matching the hand-tuned "EXAMPLE" rack: bring the (already-on, lowpass)
# filter cutoff down and make both cutoff and volume velocity-sensitive, so
# harder hits open up and get louder. Values are verbatim from the example;
# paths are relative to each pad's MultiSampler device. Resonance/type/on-state
# are intentionally left at the donor's defaults.
SAMPLER_PARAMS = {
    "Filter/Slot/Value/SimplerFilter/Freq/Manual": "3340.1438",        # cutoff ~3.34 kHz
    "Filter/Slot/Value/SimplerFilter/ModByVelocity/Manual": "0.3671875",  # velocity -> cutoff
    "Filter/Slot/Value/SimplerFilter/Slope/Manual": "false",           # 12 dB/oct
    "VolumeAndPan/VolumeVelScale/Manual": "0.349999994",               # velocity -> volume
}

# An articulation (one pad): the object it came from, a display name, and its
# round-robin takes.
Articulation = Tuple[str, str, List[Path]]

_CHANNEL_RE = re.compile(r"_[LR]$")   # Dumpster Dmst_* stereo-take marker
_TAKE_RE = re.compile(r"_\d+$")        # round-robin take index


def articulation_key(stem: str) -> str:
    """Reduce a sample filename stem to its articulation, dropping the
    round-robin take suffix: an optional "_L"/"_R" channel marker followed by
    a "_<number>" take index. Everything sharing the result is one pad."""
    key = _TAKE_RE.sub("", _CHANNEL_RE.sub("", stem))
    return key or stem  # never collapse to empty (e.g. a bare "01.wav")


def object_name(folder: Path) -> str:
    """Human-readable object name from a sample folder: drop the trailing
    ' Samples' and turn underscores into spaces (Coins, Crowbar strike,
    Metal Racks, Dumpster 01, galvanized nipples, ...)."""
    name = re.sub(r"\s+Samples$", "", folder.name)
    return name.replace("_", " ").strip()


# Shorter labels for the wordier objects, used only in rack filenames.
SHORT_NAMES = {
    "Crowbar strike": "Crowbar",
    "Dolphin Point Bridge": "Dolphin",
    "Dumpster 01": "Dumpster",
    "STL City Museum 01": "STL Museum",
    "Saw bowed room": "Saw",
    "Stairwell railing": "Stairwell",
    "Tower step bang": "Tower",
    "UMSL Observatory": "UMSL",
    "Willow Bridge": "Willow",
    "black diamond airshaft": "Black Diamond",
    "bottles&chairs 01": "Bottles & Chairs",
    "galvanized nipples": "Galvanized",
}


def rack_display_name(index: int, entries: List[Articulation]) -> str:
    """Name a packed rack after the objects it holds: dominant object first,
    minor ones (a single pad, or past the fourth) summarized as '+N more'.
    Keeps the 2-digit index so racks still sort in play order and stay unique
    when one object spans several racks (e.g. the five Dumpster racks)."""
    counts: Dict[str, int] = defaultdict(int)
    for obj, _, _ in entries:
        counts[obj] += 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    shown = [(obj, n) for obj, n in ordered if n >= 2][:4] or ordered[:1]
    label = " + ".join(SHORT_NAMES.get(obj, obj) for obj, _ in shown)
    omitted = len(ordered) - len(shown)
    if omitted:
        label += f" +{omitted} more"
    return f"Rust {index:02d} - {label}"


def gather_articulations(samples_dir: Path) -> List[Articulation]:
    """Walk every object folder and return one (object, articulation, takes)
    entry per pad, in object order (objects alphabetical, articulations
    alphabetical within each object). glob is non-recursive, so each folder's
    sibling Wallpaper/ image subfolder is ignored."""
    entries: List[Articulation] = []
    for folder in sorted(p for p in samples_dir.iterdir() if p.is_dir()):
        groups: Dict[str, List[Path]] = defaultdict(list)
        for wav in folder.glob("*.wav"):
            groups[articulation_key(wav.stem)].append(wav)
        obj = object_name(folder)
        for key in sorted(groups):
            entries.append((obj, key, sorted(groups[key], key=lambda p: p.name)))
    return entries


def fill_pad(pad: ET.Element, creator: SamplerCreator, samples: List[Path], name: str) -> None:
    """Replace one pad's Sampler SampleParts in place with the round-robin
    takes of a single articulation, all fixed on PAD_ROOT_NOTE across the full
    velocity range, and enable cyclic round robin. Only the pad's sample
    content and Name are touched."""
    sample_map = pad.find(".//MultiSampleMap")
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

    name_elem = pad.find("Name")
    if name_elem is not None:
        name_elem.set("Value", name)


def apply_sampler_params(pad: ET.Element) -> None:
    """Set the hand-tuned SAMPLER_PARAMS on one pad's MultiSampler in place."""
    device = pad.find(".//MultiSampler")
    if device is None:
        raise ValueError("Pad missing MultiSampler device")
    for rel_path, value in SAMPLER_PARAMS.items():
        elem = device.find(rel_path)
        if elem is None:
            raise ValueError(f"Sampler param path not found on pad: {rel_path}")
        elem.set("Value", value)


def build_rack(rack_name: str, entries: List[Articulation], creator: SamplerCreator) -> Path:
    """Build one Drum Rack from up to PADS_PER_RACK articulations, filling pads
    in ascending ReceivingNote order (so entries land low to high). Leftover
    pads keep the donor's empty Sampler. The Sampler tuning is applied to every
    pad so the rack stays uniform even if a sample is dropped on a spare pad."""
    rack_root = ET.fromstring(decode_adg(DRUM_RACK_TEMPLATE))
    pads = rack_root.findall(".//BranchPresets/DrumBranchPreset")
    pads.sort(key=lambda p: int(p.find(".//ZoneSettings/ReceivingNote").get("Value")))

    for pad in pads:
        apply_sampler_params(pad)

    singletons = 0
    total_takes = 0
    composition: Dict[str, int] = defaultdict(int)  # object -> pad count, insertion-ordered
    for pad, (obj, key, samples) in zip(pads, entries):
        fill_pad(pad, creator, samples, key)
        singletons += len(samples) == 1
        total_takes += len(samples)
        composition[obj] += 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{rack_name}.adg"
    xml_string = ET.tostring(rack_root, encoding="unicode", xml_declaration=True)
    encode_adg(xml_string, output_path)

    comp = ", ".join(f"{obj} ({n})" for obj, n in composition.items())
    note = "" if singletons == 0 else f", {singletons} single-take"
    print(f"  {output_path.name}: {len(entries)} pads, {total_takes} takes{note}")
    print(f"      {comp}")
    return output_path


def clean_previous(output_dir: Path) -> None:
    """Remove Rust racks written by earlier runs (both the old one-per-object
    'Rust - *.adg' layout and prior 'Rust Round Robin *.adg' packs) so a re-run
    leaves a clean set."""
    if not output_dir.exists():
        return
    stale = sorted(p for p in output_dir.glob("Rust *.adg"))
    for p in stale:
        p.unlink()
    if stale:
        print(f"Removed {len(stale)} previously generated rack(s).")


def main():
    if not DRUM_RACK_TEMPLATE.exists():
        print(f"Error: Drum rack template not found: {DRUM_RACK_TEMPLATE}")
        sys.exit(1)
    if not SAMPLES_DIR.exists():
        print(f"Error: Samples directory not found: {SAMPLES_DIR}")
        sys.exit(1)

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)

    print(f"Scanning: {SAMPLES_DIR}")
    entries = gather_articulations(SAMPLES_DIR)
    total_takes = sum(len(s) for _, _, s in entries)
    num_racks = (len(entries) + PADS_PER_RACK - 1) // PADS_PER_RACK
    print(f"  {len(entries)} articulations / {total_takes} samples -> {num_racks} full racks\n")

    clean_previous(OUTPUT_DIR)

    for i in range(num_racks):
        batch = entries[i * PADS_PER_RACK:(i + 1) * PADS_PER_RACK]
        build_rack(rack_display_name(i + 1, batch), batch, creator)

    print(f"\nDone: {num_racks} racks covering {total_takes} samples -> {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
