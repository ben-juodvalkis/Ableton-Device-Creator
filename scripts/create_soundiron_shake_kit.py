#!/usr/bin/env python3
"""
Create the Soundiron Shake Kit — one 32-pad Drum Rack whose pads are full
Multi-Samplers, each loaded with the velocity-layered, round-robin multisample
of a single percussion articulation from the Soundiron "Shake" library.

Unlike the sibling Rust library (see create_rust_round_robin_racks.py), whose
filenames carry no dynamics, Shake's one-shots encode a real velocity axis, so
each pad here is a *velocity-layered* Sampler rather than a flat round-robin.

Filename grammar (verified against the audio — the number-before-the-take axis
rises monotonically in RMS, so it is genuinely soft->loud):

    <instrument>_<artic>_<letter>_<dyn>_<take>.wav      e.g. gourd_single_a_3_07
        letter  a..e   = round-robin variation group (no loudness trend)
        dyn     1..N    = velocity/dynamic layer  (Hoof reaches 11 -> 2 digits)
        take    01..10  = round-robin take within the layer

Variants folded into the same rule:
    - keyword-less bell hits         sleigh_bells_4_a_1_07   (artic word omitted)
    - two-axis shakes                pumpkin_shake_2_1_05    (dyn = 2nd number)
    - named-level drains             rain_1_drain_soft_03    (soft/mid/hard -> vel)
    - single-layer gestures          hoof_shaker_shake_fx_a_02, ..._spin_fx_08

Excluded (phrase material, per request — one-shots only): loop, lp, groove,
grooves, beat, and every "_r" reverse variant.

Within a pad: the dynamic values are spread evenly across MIDI velocity 1-127
(split at the midpoints, via multisample_utils.velocity_bins), every sample
sharing a dynamic — across all letters and takes — becomes a round-robin
alternate, and Ableton's native cyclic RoundRobin flag alternates them. Every
part is fixed on PAD_ROOT_NOTE (60), matching every pad's SendingNote in the
donor template, exactly like the Rust workflow.

Structural rule (see CLAUDE.md): templates/sampler_drum_rack_template.adg is a
hand-built 32-pad Drum Rack with a configured Multi-Sampler already on every
pad. This script only swaps each pad's MultiSampleMap/SampleParts in place and
sets the pad Name — it never reconstructs macros, colors, choke groups, or the
rack structure.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_soundiron_shake_kit.py            # dry run (report only)
    python3 scripts/create_soundiron_shake_kit.py --write    # actually build .adg
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, velocity_bins

SAMPLE_LIBRARY_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Soundiron/Soundiron_Shake"
)
DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler_drum_rack_template.adg"
OUTPUT_DIR = SAMPLE_LIBRARY_ROOT / "Drum Racks"
KIT_NAME = "Soundiron Shake"

PAD_ROOT_NOTE = 60   # C3 — matches every pad's fixed SendingNote in the donor
PADS_PER_RACK = 32

PHRASE_WORDS = {"loop", "lp", "groove", "grooves", "beat"}
ARTIC_WORDS = {"single", "strike", "shake", "drain", "spin"} | PHRASE_WORDS
DRAIN_LEVEL = {"soft": 1, "mid": 2, "hard": 3}


def clean_stem(name: str) -> str:
    """Filename -> stem with the ' (1)' Finder-duplicate marker removed."""
    return re.sub(r"\s*\(\d+\)", "", name).removesuffix(".wav")


def parse_sample(stem: str) -> Optional[Tuple[str, Optional[int]]]:
    """Classify one filename stem.

    Returns (articulation_label, dynamic) for a one-shot, where dynamic is an
    int velocity-layer key or None for an un-layered gesture; returns None for
    phrase material (loops/grooves/beats/reverse) or anything unparseable.
    """
    toks = stem.split("_")
    if not toks:
        return None
    if toks[-1] == "r":            # "_r" reverse marker -> phrase, skip
        return None
    if not toks[-1].isdigit():     # every one-shot ends in a numeric take index
        return None
    body = toks[:-1]               # drop the take index

    idx = next((i for i, t in enumerate(body) if t in ARTIC_WORDS), None)
    if idx is None:
        # keyword-less bell hit: <...>_<letter>_<dyn>  (sleigh_bells_4/5)
        if len(body) >= 2 and re.fullmatch(r"[a-z]", body[-2]) and body[-1].isdigit():
            return ("hit", int(body[-1]))
        return None

    artic = body[idx]
    post = body[idx + 1:]
    if artic in PHRASE_WORDS:
        return None
    if artic == "spin" or "fx" in post:                    # single-layer gesture
        words = [w for w in post if not w.isdigit() and len(w) > 1]
        return (" ".join([artic, *words]), None)
    if artic == "drain":                                   # named soft/mid/hard levels
        lvl = next((DRAIN_LEVEL[w] for w in post if w in DRAIN_LEVEL), None)
        return ("drain", lvl)
    nums = [w for w in post if w.isdigit()]                # dyn = number before the take
    return (artic, int(nums[-1]) if nums else None)


def instrument_name(folder: Path) -> str:
    """'Wicker_Bell_Baskets Samples' -> 'Wicker Bell Baskets'."""
    name = re.sub(r"\s+[Ss]amples$", "", folder.name)
    return name.replace("_", " ").strip()


def parse_folder(folder: Path) -> Dict[str, Dict[int, List[Path]]]:
    """{articulation_label: {dynamic: [round-robin sample paths]}} for one
    instrument folder. A None dynamic is stored under key 0 (single layer)."""
    pads: Dict[str, Dict[int, List[Path]]] = defaultdict(lambda: defaultdict(list))
    for wav in sorted(folder.glob("*.wav")):
        if re.search(r"\(\d+\)", wav.name):    # Finder duplicate — skip
            continue
        parsed = parse_sample(clean_stem(wav.name))
        if parsed is None:
            continue
        label, dyn = parsed
        pads[label][dyn if dyn is not None else 0].append(wav)
    return pads


def spread_centers(dyn_values) -> Dict[int, int]:
    """Map sorted distinct dynamic values to evenly spaced velocity centers in
    1-127, so velocity_bins() then carves contiguous, gap-free layers."""
    ds = sorted(dyn_values)
    n = len(ds)
    return {d: max(1, round((i + 0.5) / n * 127)) for i, d in enumerate(ds)}


class Pad:
    """One resolved pad: display name + {dynamic: [samples]} layers."""

    def __init__(self, name: str, layers: Dict[int, List[Path]]):
        self.name = name
        self.layers = layers

    @property
    def sample_count(self) -> int:
        return sum(len(v) for v in self.layers.values())


def resolve_pads(folder: Path) -> List[Pad]:
    """Turn a folder into its ordered list of Pads. The articulation with the
    most samples is the instrument's 'main' hit and takes the bare instrument
    name; the rest are suffixed (e.g. 'Gourd', 'Gourd strike')."""
    parsed = parse_folder(folder)
    if not parsed:
        return []
    inst = instrument_name(folder)
    main = max(parsed, key=lambda k: sum(len(v) for v in parsed[k].values()))
    pads = []
    for label in sorted(parsed, key=lambda k: (k != main, k)):   # main first, then alpha
        name = inst if label == main else f"{inst} {label}"
        pads.append(Pad(name, dict(parsed[label])))
    return pads


def fill_pad(pad_elem: ET.Element, creator: SamplerCreator, pad: Pad) -> None:
    """Replace one pad's Sampler SampleParts in place with `pad`'s
    velocity-layered round-robin multisample, and enable cyclic round robin."""
    centers = spread_centers(pad.layers.keys())
    layers_by_center = {centers[d]: samples for d, samples in pad.layers.items()}

    sample_map = pad_elem.find(".//MultiSampleMap")
    if sample_map is None:
        raise ValueError("Pad's Sampler missing MultiSampleMap element")
    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")
    for part in build_sample_parts(creator, layers_by_center, root_note=PAD_ROOT_NOTE):
        new_parts.append(part)
    enable_round_robin(sample_map)

    name_elem = pad_elem.find("Name")
    if name_elem is not None:
        name_elem.set("Value", pad.name)


def _receiving_note(pad_elem: ET.Element) -> int:
    return int(pad_elem.find(".//ZoneSettings/ReceivingNote").get("Value"))


def build_rack(rack_name: str, pads: List[Pad], creator: SamplerCreator) -> Path:
    """Build one Drum Rack from `pads`.

    Any donor pads we don't fill are deleted, so the rack contains exactly the
    pads we have — no empty pads left behind. Pads are assigned highest-note
    first, because Live lays a Drum Rack out with the highest note at the top:
    the first instrument in the list lands on the top pad and it reads
    top-to-bottom."""
    rack_root = ET.fromstring(decode_adg(DRUM_RACK_TEMPLATE))
    branch_parent = rack_root.find(".//BranchPresets")
    pad_elems = sorted(branch_parent.findall("DrumBranchPreset"), key=_receiving_note)
    if len(pads) > len(pad_elems):
        raise ValueError(f"{len(pads)} pads but donor rack has only {len(pad_elems)} slots")

    # Keep the lowest-note branches we need; delete the surplus so none stay empty.
    keep = pad_elems[:len(pads)]
    for surplus in pad_elems[len(pads):]:
        branch_parent.remove(surplus)

    # First pad -> highest kept note (top of the rack in Live), then descending.
    for pad_elem, pad in zip(sorted(keep, key=_receiving_note, reverse=True), pads):
        fill_pad(pad_elem, creator, pad)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{rack_name}.adg"
    encode_adg(ET.tostring(rack_root, encoding="unicode", xml_declaration=True), output_path)
    return output_path


def format_layers(pad: Pad) -> str:
    """Human-readable velocity-layer summary for the dry-run report."""
    centers = spread_centers(pad.layers.keys())
    bins = velocity_bins(centers.values())
    center_to_takes = {centers[d]: len(pad.layers[d]) for d in pad.layers}
    parts = [f"v{lo}-{hi}:{center_to_takes[c]}rr" for c, lo, hi in bins]
    if len(pad.layers) == 1 and 0 in pad.layers:
        return f"1 layer, {pad.sample_count} rr (full velocity)"
    return f"{len(pad.layers)} vel layers [{', '.join(parts)}]"


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the Soundiron Shake sampler drum rack.")
    ap.add_argument("--write", action="store_true", help="actually write .adg (default: dry run)")
    args = ap.parse_args()

    if not DRUM_RACK_TEMPLATE.exists():
        sys.exit(f"Error: donor template not found: {DRUM_RACK_TEMPLATE}")
    if not SAMPLE_LIBRARY_ROOT.exists():
        sys.exit(f"Error: sample library not found: {SAMPLE_LIBRARY_ROOT}")

    folders = sorted(p for p in SAMPLE_LIBRARY_ROOT.iterdir() if p.is_dir())
    all_pads: List[Pad] = []
    print(f"Scanning: {SAMPLE_LIBRARY_ROOT}\n")
    for folder in folders:
        pads = resolve_pads(folder)
        if not pads:
            continue
        print(f"{instrument_name(folder)}")
        for pad in pads:
            print(f"    • {pad.name:<32} {pad.sample_count:>3} samples   {format_layers(pad)}")
        all_pads.extend(pads)

    print(f"\nTotal: {len(all_pads)} pads, {sum(p.sample_count for p in all_pads)} samples")

    batches = [all_pads[i:i + PADS_PER_RACK] for i in range(0, len(all_pads), PADS_PER_RACK)]
    if len(all_pads) > PADS_PER_RACK:
        print(f"(> {PADS_PER_RACK} pads — will split into {len(batches)} racks)")

    if not args.write:
        print("\nDry run — pass --write to build. Output would go to:")
        print(f"  {OUTPUT_DIR}")
        return

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)
    print()
    for i, batch in enumerate(batches, 1):
        rack_name = KIT_NAME if len(batches) == 1 else f"{KIT_NAME} {i:02d}"
        path = build_rack(rack_name, batch, creator)
        print(f"Created: {path}  ({len(batch)} pads)")


if __name__ == "__main__":
    main()
