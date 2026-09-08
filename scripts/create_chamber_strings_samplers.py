#!/usr/bin/env python3
"""
Create Chamber Strings Samplers — one full-keyboard Multi-Sampler .adv per
articulation, with Close/Far mic positions separated on the Sample Selector
(no rack required).

Source library: Spitfire Chamber Strings (Chamber Ensemble), autosampled to a
fully-chromatic grid. Filename convention:

    ChamberEns_<Artic>_<Mic>_<Note>_<MIDI>_v<vel>_rr<rr>.wav
    e.g. ChamberEns_Bartok_Close_A#2_046_v032_rr1.wav

Each articulation is recorded at two mic positions (Close + Far) in sibling
folders "<Artic>_Close" / "<Artic>_Far". Within a folder every semitone from
MIDI 36 (C1) to 96 (C6) is sampled at 3 velocity layers (v032 / v072 / v112)
with several round-robin takes each (2-8 depending on articulation).

The explicit 3-digit MIDI number in each filename is used as the root key
(sidesteps every note-name/octave convention question).

## How the three zone axes are used

- Key       : one zone per recorded semitone (pitch_zones stretches the lowest
              note down to 0 and the highest up to 127 so out-of-range notes
              still sound, transposed from the nearest edge sample).
- Velocity  : the 3 layer centers become contiguous non-overlapping bins
              (velocity_bins), split at the midpoints between centers.
- Selector  : Close samples occupy the low half of the Sample Selector, Far
              the high half. The Sampler's "Sample Selector" parameter
              (automatable / MIDI-mappable) then chooses the mic.

## Why a chooser, not a simultaneous blend

Ableton round-robin alternates among ALL sample zones that overlap for a given
note+velocity — it sees one pool. If both mics were always active they'd share
one RR pool, so each note would play only ONE mic's take (not both layered).
Keeping the mics on separate selector halves keeps each mic's round-robin pool
clean; the Sample Selector sweeps Close -> Far. A genuine simultaneous both-mic
blend with independent round-robins needs two Sampler chains in a Rack, which
this workflow deliberately avoids. Set SELECTOR_CROSSFADE > 0 for a morph band
around the split if you want the sweep to fade rather than hard-switch (RR
pools both mics only inside that band).

Usage:
    export PYTHONPATH=src
    python3 scripts/create_chamber_strings_samplers.py            # all articulations
    python3 scripts/create_chamber_strings_samplers.py Bartok     # just one (test)
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))  # multisample_utils lives beside this file

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, pitch_zones, velocity_bins

# --- Configuration ----------------------------------------------------------

REPO = Path(__file__).parent.parent
SAMPLE_LIBRARY_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Spitfire/Chamber Strings"
)
TEMPLATE_PATH = REPO / "templates" / "oae_evo_sampler_template.adv"
OUTPUT_DIR = SAMPLE_LIBRARY_ROOT / "Sampler Instruments"

MICS = ("Close", "Far")

# Sample Selector (0-127) layout for the two mic positions.
SELECTOR_SPLIT = 64      # Close lives below this, Far at/above it.
SELECTOR_CROSSFADE = 0   # half-width of the morph band around the split;
                         # 0 = hard switch (RR stays clean everywhere).
DEFAULT_SELECTOR = 0     # value the Sample Selector is parked at on load
                         # (0 = Close). Automate / MIDI-map it to change mic.

# Parse the trailing "_<MIDI>_v<vel>_rr<rr>.wav" — mic + articulation come from
# the folder, so only the note number, velocity layer and take are read here.
SUFFIX_RE = re.compile(r"_(?P<midi>\d{3})_v(?P<vel>\d+)_rr(?P<rr>\d+)\.wav$", re.IGNORECASE)


# --- Selector zones ---------------------------------------------------------

def selector_bounds(mic: str):
    """Return (min, max, xfade_min, xfade_max) on the 0-127 selector axis for a
    mic position, honouring SELECTOR_SPLIT / SELECTOR_CROSSFADE."""
    b = SELECTOR_CROSSFADE
    if mic == "Close":
        return (0, min(127, SELECTOR_SPLIT - 1 + b), 0, max(0, SELECTOR_SPLIT - 1 - b))
    return (max(0, SELECTOR_SPLIT - b), 127, min(127, SELECTOR_SPLIT + b), 127)


def set_selector(part: ET.Element, mic: str) -> None:
    lo, hi, xlo, xhi = selector_bounds(mic)
    sel = part.find("SelectorRange")
    sel.find("Min").set("Value", str(lo))
    sel.find("Max").set("Value", str(hi))
    sel.find("CrossfadeMin").set("Value", str(xlo))
    sel.find("CrossfadeMax").set("Value", str(xhi))


# --- Library parsing --------------------------------------------------------

def read_folder(folder: Path):
    """Group one mic folder's samples: {midi_note: {vel_center: [paths]}}."""
    by_note = defaultdict(lambda: defaultdict(list))
    for wav in sorted(folder.glob("*.wav")):
        m = SUFFIX_RE.search(wav.name)
        if not m:
            continue
        by_note[int(m.group("midi"))][int(m.group("vel"))].append(wav)
    return by_note


def discover_articulations():
    """Find articulations that have BOTH a _Close and a _Far folder.
    Returns {articulation: {mic: folder}} in sorted order."""
    found = defaultdict(dict)
    for d in sorted(SAMPLE_LIBRARY_ROOT.iterdir()):
        if not d.is_dir():
            continue
        for mic in MICS:
            if d.name.endswith(f"_{mic}"):
                found[d.name[: -(len(mic) + 1)]][mic] = d
    return {a: mics for a, mics in sorted(found.items()) if set(mics) == set(MICS)}


# --- Build ------------------------------------------------------------------

def build_articulation(artic: str, mic_folders: dict) -> Path:
    creator = SamplerCreator(template=TEMPLATE_PATH)
    root = ET.fromstring(decode_adg(TEMPLATE_PATH))

    sample_map = root.find(".//MultiSampleMap")
    if sample_map is None:
        raise ValueError("Template missing MultiSampleMap element")
    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")

    per_mic = {mic: read_folder(folder) for mic, folder in mic_folders.items()}

    # Key zones from the union of notes across both mics (a few files differ).
    all_notes = sorted({n for notes in per_mic.values() for n in notes})
    zones = {note: (kmin, kmax) for note, kmin, kmax in pitch_zones(all_notes)}

    index = 0
    counts = {mic: 0 for mic in MICS}
    for note in all_notes:
        key_min, key_max = zones[note]
        for mic in MICS:
            layers = per_mic[mic].get(note)
            if not layers:
                continue
            parts = build_sample_parts(
                creator, layers, root_note=note,
                start_index=index, key_min=key_min, key_max=key_max,
            )
            for part in parts:
                set_selector(part, mic)
                new_parts.append(part)
            index += len(parts)
            counts[mic] += len(parts)

    enable_round_robin(sample_map)

    # Park the Sample Selector at the chosen default (mappable/automatable).
    manual = root.find(".//SampleSelector/Manual")
    if manual is not None:
        manual.set("Value", str(DEFAULT_SELECTOR))

    display = artic.replace("_", " ")
    out_path = OUTPUT_DIR / f"Chamber Strings {display}.adv"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    encode_adg(ET.tostring(root, encoding="unicode", xml_declaration=True), out_path)

    print(f"  notes {all_notes[0]}-{all_notes[-1]} ({len(all_notes)}), "
          f"Close {counts['Close']} parts, Far {counts['Far']} parts, "
          f"{index} total -> {out_path.name}")
    return out_path


def main():
    if not TEMPLATE_PATH.exists():
        sys.exit(f"Error: template not found: {TEMPLATE_PATH}")
    if not SAMPLE_LIBRARY_ROOT.exists():
        sys.exit(f"Error: sample library not found: {SAMPLE_LIBRARY_ROOT}")

    articulations = discover_articulations()
    if not articulations:
        sys.exit(f"Error: no <Artic>_Close/_Far folder pairs under {SAMPLE_LIBRARY_ROOT}")

    wanted = [a.replace(" ", "_") for a in sys.argv[1:]]
    if wanted:
        missing = [w for w in wanted if w not in articulations]
        if missing:
            sys.exit(f"Error: unknown articulation(s): {missing}\n"
                     f"Available: {list(articulations)}")
        articulations = {a: articulations[a] for a in wanted}

    print(f"Selector: Close {selector_bounds('Close')}  Far {selector_bounds('Far')}  "
          f"default={DEFAULT_SELECTOR}")
    print(f"Building {len(articulations)} articulation(s): {list(articulations)}\n")
    for artic, mic_folders in articulations.items():
        print(artic)
        build_articulation(artic, mic_folders)


if __name__ == "__main__":
    main()
