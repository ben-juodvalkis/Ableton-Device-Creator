#!/usr/bin/env python3
"""
Create Chamber Strings Racks — one Instrument Rack .adg per articulation with
Close and Far as two simultaneously-playing chains, blended by the "Close/Far"
macro (no single-Sampler Sample-Selector trick).

Why a rack instead of the one-Sampler + Sample-Selector approach
(create_chamber_strings_samplers.py): Ableton round-robin alternates among all
sample zones that overlap for a note+velocity — one pool. Putting both mics in
one Sampler forced them to share that pool, so each note played only one mic's
take. A rack gives each mic its own Sampler (its own independent round-robin
pool); both chains sound at once and the Chain Selector crossfades between them,
so the "Close/Far" macro is a real simultaneous blend.

## Donor rule (see CLAUDE.md)

templates/chamber_strings_rack_template.adg is a hand-built 2-chain Instrument
Rack (from an Olafur Arnalds Evolutions "Evo" preset). Chain "Close" is dominant
at Chain Selector 0, chain "Far" at 127, the "Close/Far" macro drives the
selector, and every macro / envelope / Evo character is already configured. We
NEVER reconstruct that structure — we only replace each chain's MultiSampler
sample content and flip on its round-robin. If the rack itself needs to change
(different macros, envelopes, a plainer non-Evo character for the short
articulations), rebuild it in Ableton Live and copy it over the template.

## Source grid

Same Spitfire library as the sampler workflow: per-articulation "<Artic>_Close"
/ "<Artic>_Far" folders, filenames
    ChamberEns_<Artic>_<Mic>_<Note>_<MIDI>_v<vel>_rr<rr>.wav
fully chromatic MIDI 36-96, 3 velocity layers (v032/v072/v112), 2-8 round
robins. The explicit 3-digit MIDI number is the root key. Each chain is filled
across the FULL selector range (mic separation is done by the chains, not the
selector).

Usage:
    export PYTHONPATH=src
    python3 scripts/create_chamber_strings_racks.py            # all articulations
    python3 scripts/create_chamber_strings_racks.py Bartok     # just one (test)
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
from multisample_utils import build_sample_parts, enable_round_robin, pitch_zones

# --- Configuration ----------------------------------------------------------

REPO = Path(__file__).parent.parent
SAMPLE_LIBRARY_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Spitfire/Chamber Strings"
)
TEMPLATE_PATH = REPO / "templates" / "chamber_strings_rack_template.adg"
OUTPUT_DIR = SAMPLE_LIBRARY_ROOT / "Instrument Racks"

# Chain <Name> in the donor -> mic folder suffix. The donor's chains are named
# "Close" / "Far"; we match by name (not index) so chain order can't matter.
MICS = ("Close", "Far")

SUFFIX_RE = re.compile(r"_(?P<midi>\d{3})_v(?P<vel>\d+)_rr(?P<rr>\d+)\.wav$", re.IGNORECASE)


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
    """{articulation: {mic: folder}} for articulations having both mics."""
    found = defaultdict(dict)
    for d in sorted(SAMPLE_LIBRARY_ROOT.iterdir()):
        if not d.is_dir():
            continue
        for mic in MICS:
            if d.name.endswith(f"_{mic}"):
                found[d.name[: -(len(mic) + 1)]][mic] = d
    return {a: mics for a, mics in sorted(found.items()) if set(mics) == set(MICS)}


# --- Build ------------------------------------------------------------------

def fill_chain(creator, sample_map: ET.Element, folder: Path, index_start: int = 0) -> int:
    """Replace a chain MultiSampler's SampleParts with one mic folder's fully
    chromatic, velocity-binned, round-robin content. Returns the part count."""
    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")

    by_note = read_folder(folder)
    notes = sorted(by_note)
    zones = {n: (kmin, kmax) for n, kmin, kmax in pitch_zones(notes)}

    index = index_start
    for note in notes:
        key_min, key_max = zones[note]
        parts = build_sample_parts(
            creator, by_note[note], root_note=note,
            start_index=index, key_min=key_min, key_max=key_max,
        )
        for part in parts:
            new_parts.append(part)
        index += len(parts)

    enable_round_robin(sample_map)
    return index - index_start


def build_articulation(artic: str, mic_folders: dict) -> Path:
    creator = SamplerCreator(template=TEMPLATE_PATH)
    root = ET.fromstring(decode_adg(TEMPLATE_PATH))

    branches = root.findall(".//InstrumentBranchPreset")
    by_name = {b.find("Name").get("Value"): b for b in branches}
    missing = [m for m in MICS if m not in by_name]
    if missing:
        raise ValueError(f"Donor rack has no chain(s) named {missing}; found {list(by_name)}")

    counts = {}
    for mic in MICS:
        branch = by_name[mic]
        sample_map = branch.find(".//MultiSampler//MultiSampleMap")
        if sample_map is None:
            raise ValueError(f"Chain {mic!r} has no MultiSampler/MultiSampleMap")
        # Independent Id space per chain (matches how the donor stores each chain).
        counts[mic] = fill_chain(creator, sample_map, mic_folders[mic])

    display = artic.replace("_", " ")
    out_path = OUTPUT_DIR / f"Chamber Strings {display}.adg"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    encode_adg(ET.tostring(root, encoding="unicode", xml_declaration=True), out_path)

    print(f"  Close {counts['Close']} parts, Far {counts['Far']} parts -> {out_path.name}")
    return out_path


def main():
    if not TEMPLATE_PATH.exists():
        sys.exit(f"Error: donor template not found: {TEMPLATE_PATH}")
    if not SAMPLE_LIBRARY_ROOT.exists():
        sys.exit(f"Error: sample library not found: {SAMPLE_LIBRARY_ROOT}")

    articulations = discover_articulations()
    if not articulations:
        sys.exit(f"Error: no <Artic>_Close/_Far folder pairs under {SAMPLE_LIBRARY_ROOT}")

    wanted = [a.replace(" ", "_") for a in sys.argv[1:]]
    if wanted:
        unknown = [w for w in wanted if w not in articulations]
        if unknown:
            sys.exit(f"Error: unknown articulation(s): {unknown}\nAvailable: {list(articulations)}")
        articulations = {a: articulations[a] for a in wanted}

    print(f"Donor: {TEMPLATE_PATH.name}  (chains Close + Far, blended by the Close/Far macro)")
    print(f"Building {len(articulations)} rack(s): {list(articulations)}\n")
    for artic, mic_folders in articulations.items():
        print(artic)
        build_articulation(artic, mic_folders)


if __name__ == "__main__":
    main()
