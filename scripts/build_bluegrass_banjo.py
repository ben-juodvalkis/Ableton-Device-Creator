#!/usr/bin/env python3
"""Build Ableton Sampler instruments from the Bluegrass Banjo (NCW) library.

Two steps:

1. Decode the NI `.ncw` samples to WAV (tools/ncw.py).
2. Map them into one Sampler `.adv` per articulation.

Filename note names use NI's convention where C3 = middle C = MIDI 60, verified
by measuring the decoded audio (G1 -> 98.4 Hz, C2 -> 130.5 Hz, D3 -> 294.0 Hz),
so MIDI = note + 12 relative to scientific pitch.

Articulations in the library:
    brt mp / med mp   two pick tones at the same dynamic, 2 takes each
    mute f / mute mf  muted stabs, two dynamics
    sld               whole-step slides
    strm f / strm mf  chord strums, already mapped high (MIDI 86-96)
    fngr nse          finger noise one-shots

Velocity layering is a hard split with no crossfade on purpose: the layers are
separate takes, so crossfading them would double the pick attack into a flam.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from ableton_device_creator.sampler.multisample import (  # noqa: E402
    Chain,
    MultisampleRackCreator,
    Zone,
    build_key_zones,
)
from ncw import ncw_to_wav  # noqa: E402

NCW_DIR = Path("/Users/Shared/Music/Soundbanks/Apple/Bluegrass Banjo Samples")
WAV_DIR = Path("/Users/Shared/Music/Soundbanks/Apple/Bluegrass Banjo WAV")
OUT_DIR = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library"
    "/Presets/Instruments/Sampler/Bluegrass Banjo"
)
TEMPLATE = REPO / "templates" / "sampler-rack.adg"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Playable span for the pitched articulations. Roots run MIDI 43-84; the outer
# zones stretch a little further so the bottom and top of the range still speak.
KEY_LOW, KEY_HIGH = 36, 85
# Where the two tone/dynamic layers meet.
VEL_SPLIT = 64

ARTIC_DIRS = {
    "brt mp": "01 Picked Bright",
    "med mp": "02 Picked Medium",
    "mute f": "03 Muted F",
    "mute mf": "04 Muted MF",
    "sld": "05 Slides",
    "strm f": "06 Strum F",
    "strm mf": "07 Strum MF",
    "fngr nse": "08 Finger Noise",
}

NOTE_RE = re.compile(r"^IL Banjo-BG (brt mp|med mp|mute f|mute mf) ([A-G]#?)(-?\d)([a-z]\d?)$")
SLIDE_RE = re.compile(r"^IL Banjo-BG sld ([A-G]#?)(-?\d)-([A-G]#?)(-?\d)([a-z])$")
STRUM_RE = re.compile(r"^IL Banjo-BG strm (f|mf) ([A-G]#?)(-?\d) (\d+)$")
NOISE_RE = re.compile(r"^IL Banjo-BG fngr nse (up|dn) (\d+)$")


def midi_of(name: str, octave: str) -> int:
    """NI naming (C3 = 60) -> MIDI note number."""
    return NOTE_NAMES.index(name) + 12 * (int(octave) + 2)


def note_label(midi: int) -> str:
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def decode_library() -> int:
    """Decode every .ncw into WAV_DIR, grouped by articulation. Returns count."""
    count = 0
    for src in sorted(NCW_DIR.glob("*.ncw")):
        subdir = next(
            (d for key, d in ARTIC_DIRS.items() if f" {key} " in src.name), "99 Other"
        )
        dst = WAV_DIR / subdir / (src.stem + ".wav")
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            ncw_to_wav(src, dst)
        count += 1
    return count


def scan():
    """Group decoded WAVs: {articulation: {root_midi: [(take, path), ...]}}."""
    table = defaultdict(lambda: defaultdict(list))
    noises = []
    for wav in sorted(WAV_DIR.rglob("*.wav")):
        stem = wav.stem
        m = NOTE_RE.match(stem)
        if m:
            artic, name, octave, take = m.groups()
            table[artic][midi_of(name, octave)].append((take, wav))
            continue
        m = SLIDE_RE.match(stem)
        if m:
            name, octave, _, _, take = m.groups()
            table["sld"][midi_of(name, octave)].append((take, wav))
            continue
        m = STRUM_RE.match(stem)
        if m:
            dyn, name, octave, take = m.groups()
            table["strm " + dyn][midi_of(name, octave)].append((take, wav))
            continue
        m = NOISE_RE.match(stem)
        if m:
            noises.append((m.group(1), int(m.group(2)), wav))
    for artic in table:
        for root in table[artic]:
            table[artic][root].sort()
    noises.sort(key=lambda t: (t[0], t[1]))
    return table, noises


def split_velocity(lo: int, hi: int, n: int):
    """Split a velocity span into n adjacent, non-overlapping bands."""
    if n <= 1:
        return [(lo, hi)]
    width = (hi - lo + 1) / n
    bands = []
    for i in range(n):
        band_lo = lo if i == 0 else lo + round(i * width)
        band_hi = hi if i == n - 1 else lo + round((i + 1) * width) - 1
        bands.append((band_lo, band_hi))
    return bands


def nearest_root(root: int, available):
    return min(available, key=lambda r: (abs(r - root), r))


def layered_zones(layers, key_low=KEY_LOW, key_high=KEY_HIGH, vel_lo=1, vel_hi=127):
    """Build zones for an instrument whose velocity layers are separate takes.

    `layers` is an ordered list of (label, {root: [(take, path)]}) from softest
    to hardest. Each layer owns a fixed slice of the `vel_lo`..`vel_hi` span so
    the tone boundary sits at the same velocity on every key; takes inside a
    layer subdivide that slice further.
    """
    roots = sorted({r for _, table in layers for r in table})
    key_ranges = build_key_zones(roots, key_low, key_high)
    spans = split_velocity(vel_lo, vel_hi, len(layers))

    zones = []
    for (label, table), (vel_lo, vel_hi) in zip(layers, spans):
        have = sorted(table)
        for root in roots:
            source_root = root if root in table else nearest_root(root, have)
            takes = table[source_root]
            kmin, kmax = key_ranges[root]
            for (take_lo, take_hi), (take, path) in zip(
                split_velocity(vel_lo, vel_hi, len(takes)), takes
            ):
                zones.append(
                    Zone(
                        sample=path,
                        root_key=source_root,
                        key_min=kmin,
                        key_max=kmax,
                        vel_min=take_lo,
                        vel_max=take_hi,
                        name=f"{note_label(root)} {label} {take}",
                    )
                )
    return zones


def main():
    print(f"Decoding {NCW_DIR.name} ...")
    n = decode_library()
    print(f"  {n} NCW files -> {WAV_DIR}")

    table, noises = scan()
    creator = MultisampleRackCreator(TEMPLATE)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    built = []

    # 1. Picked -- medium tone on the lower half of velocity, bright on the upper.
    picked = layered_zones(
        [("med", table["med mp"]), ("brt", table["brt mp"])]
    )
    built.append(
        (
            creator.build_device(
                Chain(name="Bluegrass Banjo Picked", zones=picked),
                OUT_DIR / "Bluegrass Banjo Picked.adv",
            ),
            picked,
        )
    )

    # 2. Muted stabs -- mf below the split, f above.
    muted = layered_zones([("mf", table["mute mf"]), ("f", table["mute f"])])
    built.append(
        (
            creator.build_device(
                Chain(name="Bluegrass Banjo Muted", zones=muted),
                OUT_DIR / "Bluegrass Banjo Muted.adv",
            ),
            muted,
        )
    )

    # 3. Slides -- one take each, whole-step gestures, full velocity range.
    slides = layered_zones([("sld", table["sld"])])
    built.append(
        (
            creator.build_device(
                Chain(name="Bluegrass Banjo Slides", zones=slides),
                OUT_DIR / "Bluegrass Banjo Slides.adv",
            ),
            slides,
        )
    )

    # 4. Chord strums -- the library already maps these to MIDI 86-96; the gaps
    #    between them fill by transposing a neighbour, which yields the missing
    #    chromatic chords.
    strums = layered_zones(
        [("mf", table["strm mf"]), ("f", table["strm f"])], key_low=85, key_high=100
    )
    built.append(
        (
            creator.build_device(
                Chain(name="Bluegrass Banjo Strums", zones=strums),
                OUT_DIR / "Bluegrass Banjo Strums.adv",
            ),
            strums,
        )
    )

    # 5. Finger noise -- unpitched one-shots, one per key from C6 up, untransposed.
    noise_zones = [
        Zone(
            sample=path,
            root_key=96 + i,
            key_min=96 + i,
            key_max=96 + i,
            name=f"fngr nse {direction} {num}",
        )
        for i, (direction, num, path) in enumerate(noises)
    ]
    built.append(
        (
            creator.build_device(
                Chain(name="Bluegrass Banjo Finger Noise", zones=noise_zones),
                OUT_DIR / "Bluegrass Banjo Finger Noise.adv",
            ),
            noise_zones,
        )
    )

    # 6. Composite -- one instrument where velocity chooses the articulation:
    #    muted stabs at the bottom, picked in the middle, slides at the top.
    #    Each band subdivides among its own layers and takes.
    composite = (
        layered_zones(
            [("mf", table["mute mf"]), ("f", table["mute f"])],
            vel_lo=1,
            vel_hi=59,
        )
        + layered_zones(
            [("med", table["med mp"]), ("brt", table["brt mp"])],
            vel_lo=60,
            vel_hi=119,
        )
        + layered_zones([("sld", table["sld"])], vel_lo=120, vel_hi=127)
    )
    built.append(
        (
            creator.build_device(
                Chain(name="Bluegrass Banjo Composite", zones=composite),
                OUT_DIR / "Bluegrass Banjo Composite.adv",
            ),
            composite,
        )
    )

    print(f"\nWrote {len(built)} Sampler presets to:\n  {OUT_DIR}")
    for path, zones in built:
        keys = sorted({z.key_min for z in zones} | {z.key_max for z in zones})
        print(
            f"  {path.name:38s} {len(zones):3d} zones  "
            f"keys {note_label(keys[0])}-{note_label(keys[-1])}"
        )


if __name__ == "__main__":
    main()
