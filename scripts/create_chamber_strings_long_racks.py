#!/usr/bin/env python3
"""
Create Chamber Strings LONG Racks — one Instrument Rack .adg per sustained
articulation, with the 6 dynamics layers crossfaded on the Sample Selector
(mod-wheel / Dynamics macro) and Close/Far on the two rack chains.

The "Long" (sustained) content is structured differently from the short
articulations (Bartok, Pizz, ... — see create_chamber_strings_racks.py):

    ChamberEnsLong<Artic>_<Mic>_<Note>_<MIDI>_cc<NNN>.wav
    e.g. ChamberEnsLong_Close_A#1_034_cc001.wav

- NO velocity layers, NO round robins.
- 6 continuous *dynamics* layers per note: cc 001 / 026 / 051 / 076 / 102 / 127,
  meant to be crossfaded by a controller (Spitfire's mod-wheel dynamics).
- 24-second sustains, fully chromatic (ranges differ per articulation:
  most C0-C6 / 24-96, Sul Tasto C1-C6 / 36-96, Harmonics C3-C6 / 60-96).

## Mapping

Because there are no round robins, the Sample Selector is free (the conflict
that ruled it out for the short articulations doesn't exist here). Each note's
6 dynamics layers are placed on overlapping Sample-Selector bands with
triangular crossfades, so sweeping the Sample Selector 0->127 morphs pp->ff.
Key = one zone per semitone; Velocity = full 1-127 (dynamics are NOT on
velocity). Close/Far stay on the two rack chains, blended by the donor's
Close/Far macro.

## Donor rule (see CLAUDE.md)

This needs a donor whose two chains ("Close"/"Far") each map a **Dynamics macro
(mod-wheel / CC1) to the MultiSampler's Sample Selector** — that mapping is rack
structure, built in Ableton, never script-patched. Set DONOR to that file. The
script only replaces each chain's sample content (dynamics layers on the
selector bands) and leaves every macro / mapping intact. Until a proper Long
donor exists, you can point DONOR at the short-rack template to validate layout,
but the Sample Selector won't be controllable (it'll sit at the softest layer).

Usage:
    export PYTHONPATH=src
    python3 scripts/create_chamber_strings_long_racks.py            # all
    python3 scripts/create_chamber_strings_long_racks.py Long Long_Tremolo
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import pitch_zones

# --- Configuration ----------------------------------------------------------

REPO = Path(__file__).parent.parent
SAMPLE_LIBRARY_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Spitfire/Chamber Strings"
)
LONG_ROOT = SAMPLE_LIBRARY_ROOT / "Long"
# Donor with a Dynamics->Sample Selector mapping on both Close/Far chains.
DONOR = REPO / "templates" / "chamber_strings_long_rack_template.adg"
OUTPUT_DIR = SAMPLE_LIBRARY_ROOT / "Instrument Racks"

MICS = ("Close", "Far")

LONG_SUFFIX_RE = re.compile(r"_(?P<midi>\d{3})_cc(?P<cc>\d+)\.wav$", re.IGNORECASE)


# --- Dynamics -> Sample Selector bands --------------------------------------

def selector_crossfade_bands(centers):
    """Triangular crossfade bands on the 0-127 selector axis, one per dynamics
    layer. Each layer peaks (full) at its own center and fades to silence at
    the neighbouring centers, so adjacent layers crossfade and a selector sweep
    morphs smoothly pp->ff. Returns {center: (Min, XfMin, XfMax, Max)}."""
    centers = sorted(centers)
    bands = {}
    for i, c in enumerate(centers):
        lo = centers[i - 1] if i > 0 else 0
        hi = centers[i + 1] if i < len(centers) - 1 else 127
        bands[c] = (lo, c, c, hi)
    return bands


def set_selector_band(part: ET.Element, band) -> None:
    lo, xlo, xhi, hi = band
    sel = part.find("SelectorRange")
    sel.find("Min").set("Value", str(lo))
    sel.find("Max").set("Value", str(hi))
    sel.find("CrossfadeMin").set("Value", str(xlo))
    sel.find("CrossfadeMax").set("Value", str(xhi))


# --- Library parsing --------------------------------------------------------

def read_long_folder(folder: Path):
    """Group one mic folder: {midi_note: {cc_center: path}} (one take each)."""
    by_note = defaultdict(dict)
    for wav in sorted(folder.glob("*.wav")):
        m = LONG_SUFFIX_RE.search(wav.name)
        if not m:
            continue
        by_note[int(m.group("midi"))][int(m.group("cc"))] = wav
    return by_note


def discover_articulations():
    """{display_name: {mic: folder}} for articulations with both mics.
    Case-insensitive so Long_Sul_Pont_Close pairs with Long_Sul_pont_Far."""
    found = defaultdict(dict)
    display = {}
    for d in sorted(LONG_ROOT.iterdir()):
        if not d.is_dir():
            continue
        low = d.name.lower()
        for mic in MICS:
            if low.endswith(f"_{mic.lower()}"):
                raw = d.name[: -(len(mic) + 1)]
                key = raw.lower()
                found[key][mic] = d
                if mic == "Close" or key not in display:
                    display[key] = raw  # prefer Close's spelling
    return {display[k]: mics for k, mics in sorted(found.items()) if set(mics) == set(MICS)}


# --- Build ------------------------------------------------------------------

def fill_chain(creator, sample_map: ET.Element, folder: Path) -> int:
    """Replace a chain MultiSampler's SampleParts with one mic's fully chromatic
    content, each note's 6 dynamics layers laid on crossfaded selector bands.
    No round robin (sustained dynamics, one take per note+layer)."""
    old = sample_map.find("SampleParts")
    if old is not None:
        sample_map.remove(old)
    new = ET.SubElement(sample_map, "SampleParts")

    by_note = read_long_folder(folder)
    notes = sorted(by_note)
    zones = {n: (kmin, kmax) for n, kmin, kmax in pitch_zones(notes)}
    centers = sorted({cc for layers in by_note.values() for cc in layers})
    bands = selector_crossfade_bands(centers)

    index = 0
    for note in notes:
        key_min, key_max = zones[note]
        for cc in sorted(by_note[note]):
            part = creator._create_sample_part(
                index=index, sample_path=by_note[note][cc],
                key_min=key_min, key_max=key_max, root_key=note,
            )
            set_selector_band(part, bands[cc])  # velocity stays full 1-127
            new.append(part)
            index += 1
    return index


def build_articulation(artic: str, mic_folders: dict, donor: Path, out_dir: Path) -> Path:
    creator = SamplerCreator(template=donor)
    root = ET.fromstring(decode_adg(donor))

    by_name = {b.find("Name").get("Value"): b for b in root.findall(".//InstrumentBranchPreset")}
    missing = [m for m in MICS if m not in by_name]
    if missing:
        raise ValueError(f"Donor has no chain(s) named {missing}; found {list(by_name)}")

    counts = {}
    for mic in MICS:
        sample_map = by_name[mic].find(".//MultiSampler//MultiSampleMap")
        if sample_map is None:
            raise ValueError(f"Chain {mic!r} has no MultiSampler/MultiSampleMap")
        counts[mic] = fill_chain(creator, sample_map, mic_folders[mic])

    display = artic.replace("_", " ")
    out_path = out_dir / f"Chamber Strings {display}.adg"
    out_dir.mkdir(parents=True, exist_ok=True)
    encode_adg(ET.tostring(root, encoding="unicode", xml_declaration=True), out_path)
    print(f"  Close {counts['Close']} parts, Far {counts['Far']} parts -> {out_path.name}")
    return out_path


def main():
    if not LONG_ROOT.exists():
        sys.exit(f"Error: Long library not found: {LONG_ROOT}")
    if not DONOR.exists():
        sys.exit(f"Error: Long donor not found: {DONOR}\n"
                 f"Build a Close/Far rack whose chains map a Dynamics macro (mod wheel) "
                 f"to the Sample Selector, and save it there (see module docstring).")

    articulations = discover_articulations()
    if not articulations:
        sys.exit(f"Error: no <Artic>_Close/_Far folder pairs under {LONG_ROOT}")

    wanted = [a.replace(" ", "_") for a in sys.argv[1:]]
    if wanted:
        unknown = [w for w in wanted if w not in articulations]
        if unknown:
            sys.exit(f"Error: unknown articulation(s): {unknown}\nAvailable: {list(articulations)}")
        articulations = {a: articulations[a] for a in wanted}

    print(f"Donor: {DONOR.name}")
    print(f"Building {len(articulations)} Long rack(s): {list(articulations)}\n")
    for artic, mic_folders in articulations.items():
        print(artic)
        build_articulation(artic, mic_folders, DONOR, OUTPUT_DIR)


if __name__ == "__main__":
    main()
