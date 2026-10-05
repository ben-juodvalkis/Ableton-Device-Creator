#!/usr/bin/env python3
"""
Build a single-Sampler multi-mic instrument from an Abbey Road "Multi-Mic"
render: Close, OH and Room in one Sampler, blended on the Sample Selector, with
the round-robin takes laid out on thin velocity slices instead of Live's round
robin.

Source (rendered by the autosampler repo, one Kontakt multi-out pass per take):

    <Kit> Multi-Mic/<Piece>/<Close|OH|Room>/<Piece> <Artic> <Mic>-<Note>-V<vel>-<CODE>.wav
    <Kit> Multi-Mic/velocity_layers.csv

A take's 4-char CODE is shared by its three mic files: one hit, heard from three
places, sample-aligned. `velocity_layers.csv` holds the velocity range each
recorded layer really plays over in Kontakt - measured by sweeping 1-127, not
read from the Mapping Editor, whose even bins the instrument script reshapes.
`V<vel>` in the filename is the layer's rendered (centre) velocity.

## Why no round robin

Live pools every zone that overlaps on note + velocity + selector into one
round-robin group, so with RoundRobin on, the three mic zones of a take would
alternate instead of layering. Three Samplers in a rack keep RR but drift: a
chain outside the chain-selector range receives no notes and its counter stops.
Here velocity picks the take for all three mics at once, so they cannot diverge.

Each layer's range is split into one slice per take, takes ordered quietest to
loudest by measured attack energy (Close mic, first 100 ms), so velocity also
shades the dynamics inside a layer. A fixed-velocity sequence repeats one take;
put a Velocity device with a little Random in front to vary it.

## Near-duplicate takes

Some takes in a layer are near twins (lag-tolerant correlation >= 0.999 on
every mic - Close alone misleads, see thin_and_order). They are distinct recordings - the .nkx file counts match and an
exact replay scores 1.0000 - but they add no audible variation, so all but one
of each twin group is left out and reported. The source files are untouched.

## Selector curve (Ben, 2026-10-04)

    0-32   OH fades in      Close  0-96,  full 0-64, out 64-96
    32-64  Room fades in    OH     0-127, in 0-32, full 32-96, out 96-127
    64-96  Close fades out  Room   32-127, in 32-64, full 64-127
    96-127 OH fades out

Live stores a fade as the points where a zone reaches full level: up from Min
to CrossfadeMin, down from CrossfadeMax to Max. A zone outside the selector
simply does not sound, and with no RR counter there is nothing to fall behind.
A piece with no Close mic (cymbals, clap, sticks) gets OH and Room only.

Every zone sits on PAD_ROOT_NOTE (C3), the convention of the other drum
Samplers here, so the device drops onto a Drum Rack pad unchanged.

Needs numpy and soundfile, which the core package does not:

    PYTHONPATH=src uv run --with numpy --with soundfile \\
        python scripts/create_abbey_road_multimic_sampler.py --plan
"""

import argparse
import csv
import itertools
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.sampler.multisample import (
    Chain,
    MultisampleRackCreator,
    Zone,
)

REPO = Path(__file__).parent.parent
# Bare Sampler, no zones, RR off, 12.8 s release (one-shots ring out).
DONOR = REPO / "templates" / "oae_evo_sampler_template.adv"

SOURCE_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Native Instruments/Abbey Road Multi Mic"
)
OUTPUT_DIR = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Sidebar/Drum/Abbey Road Multi-Mic"
)

PAD_ROOT_NOTE = 60
# Globals/NumVoices is the index into Live's voice-count menu, not a count:
# factory Sampler presets store 0-11. 14 is what the donor and every curated
# Abbey Road pad already carry, so keep it rather than guess an index.
NUM_VOICES = 14
TWIN_THRESHOLD = 0.999   # Close-mic correlation at or above this = same-sounding take
ATTACK_S = 0.1           # loudness window for ordering takes inside a layer
COMPARE_S = 1.0          # window for twin detection

# mic -> (Min, Max, CrossfadeMin, CrossfadeMax) on the Sample Selector
SELECTOR = {
    "Close": (0, 96, 0, 64),
    "OH": (0, 127, 32, 96),
    "Room": (32, 127, 64, 127),
}
# CompST (80s kits only) is the library's compressed room mic. It takes the end
# of the knob: over 96-127 Room hands over to it as OH fades, so 127 is the
# squashed room alone.
SELECTOR_WITH_COMP = dict(SELECTOR, Room=(32, 127, 64, 96), CompST=(96, 127, 127, 127))
MICS = ["Close", "OH", "Room", "CompST"]

FILE_RE = re.compile(r"^(?P<art>.*) (?P<mic>Close|OH|Room|CompST)-(?P<note>\S+)-V(?P<vel>\d+)-(?P<code>[A-Z0-9]{4})\.wav$")


def selector_for(mic: str, mics) -> tuple:
    """Selector range for `mic` given the mics the piece has. With no Close
    (cymbals, claps, sticks) OH is full from 0 and the curve is otherwise the
    same, so a whole-kit sweep moves every pad toward the room together."""
    table = SELECTOR_WITH_COMP if "CompST" in mics else SELECTOR
    if mic == "OH" and "Close" not in mics:
        return (0, 127, 0, 96)
    return table[mic]


def load_mono(path: Path, seconds: float) -> np.ndarray:
    info = sf.info(str(path))
    frames = min(info.frames, int(info.samplerate * seconds))
    x, _ = sf.read(str(path), frames=frames, always_2d=True)
    return x.mean(axis=1)


def lagged_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Peak normalised cross-correlation: gain- and small-shift-independent."""
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    spec = np.fft.rfft(a, 2 * n) * np.conj(np.fft.rfft(b, 2 * n))
    peak = np.abs(np.fft.irfft(spec)).max()
    denom = np.sqrt((a * a).sum() * (b * b).sum())
    return float(peak / denom) if denom else 0.0


def scan(kit_dir: Path, piece: str, articulation: str):
    """Return {rendered_velocity: {code: {mic: path}}} for one articulation."""
    full = f"{piece} {articulation}"
    takes = defaultdict(lambda: defaultdict(dict))
    for mic_dir in (kit_dir / piece).iterdir():
        if not mic_dir.is_dir():
            continue
        for f in mic_dir.glob("*.wav"):
            m = FILE_RE.match(f.name)
            if m and m["art"] == full:
                takes[int(m["vel"])][m["code"]][m["mic"]] = f
    return takes


def read_layers(kit_dir: Path, piece: str, articulation: str):
    rows = [
        r for r in csv.DictReader(open(kit_dir / "velocity_layers.csv"))
        if r["drum_piece"] == piece and r["articulation"] == articulation
    ]
    if not rows:
        raise SystemExit(f"{piece} / {articulation}: not in velocity_layers.csv")
    return sorted(rows, key=lambda r: int(r["layer"]))


def thin_and_order(codes: dict, ref_mic: str):
    """Drop near-twin takes, then order the survivors quietest first.

    A twin must match on every mic. The Close channel alone is not enough:
    Spring's kick takes score >= 0.999 on Close in 80 of 132 pairs and in none
    on OH (measured 2026-10-04) - the hits differ, the Close processing hides it.

    Returns (kept_codes, dropped [(code, twin_of, weakest-mic corr)]).
    """
    audio = {c: {mic: load_mono(p, COMPARE_S) for mic, p in m.items()}
             for c, m in codes.items()}
    energy = {
        c: float(np.sqrt(np.mean(load_mono(m[ref_mic], ATTACK_S) ** 2)))
        for c, m in codes.items()
    }

    def similarity(a, b):
        return min(lagged_corr(audio[a][mic], audio[b][mic]) for mic in audio[a])

    # Loudest-first keeps the most distinct-sounding take of a twin group
    # deterministic; the order is re-done quietest-first below.
    kept, dropped = [], []
    for code in sorted(codes, key=lambda c: (-energy[c], c)):
        twin = next(
            ((k, r) for k in kept
             if (r := similarity(code, k)) >= TWIN_THRESHOLD),
            None,
        )
        if twin:
            dropped.append((code, twin[0], twin[1]))
        else:
            kept.append(code)
    kept.sort(key=lambda c: (energy[c], c))
    return kept, dropped


def slices(lo: int, hi: int, n: int):
    """Split lo..hi into n contiguous slices, wider ones at the top."""
    width = hi - lo + 1
    out, start = [], lo
    for i in range(n):
        size = width // n + (1 if i >= n - width % n else 0)
        out.append((start, start + size - 1))
        start += size
    return out


def build_zones(kit_dir: Path, piece: str, articulation: str, verbose=True, sample_start=0):
    """`sample_start` skips a fixed lead-in: the Early 60s, Open and Chrome
    presets advance their close mics, so every stem of those kits starts 168
    samples (3.8 ms) before the hit."""
    layers = read_layers(kit_dir, piece, articulation)
    takes = scan(kit_dir, piece, articulation)
    mics = [m for m in MICS if (kit_dir / piece / m).is_dir()]
    ref_mic = "Close" if "Close" in mics else "OH"

    zones, report = [], {"layers": len(layers), "takes": 0, "kept": 0, "dropped": [], "merged": []}
    expect_lo = 1
    for row in layers:
        lo, hi, vel = int(row["vel_lo"]), int(row["vel_hi"]), int(row["rendered_velocity"])
        if lo != expect_lo:
            raise SystemExit(f"layer {row['layer']}: starts at {lo}, expected {expect_lo}")
        expect_lo = hi + 1

        codes = takes.get(vel, {})
        if len(codes) != int(row["takes"]):
            raise SystemExit(f"layer {row['layer']} (V{vel}): {len(codes)} takes on disk, "
                             f"csv says {row['takes']}")
        for code, by_mic in codes.items():
            missing = set(mics) - set(by_mic)
            if missing:
                raise SystemExit(f"take {code} (V{vel}) has no {sorted(missing)} file")

        kept, dropped = thin_and_order(codes, ref_mic)
        report["takes"] += len(codes)
        report["dropped"] += [(row["layer"], *d) for d in dropped]

        # A layer narrower than its take count cannot give every take a slice;
        # keep the loudest-spread subset rather than overlap slices.
        if len(kept) > hi - lo + 1:
            extra = len(kept) - (hi - lo + 1)
            report["merged"].append((row["layer"], extra))
            kept = kept[extra:]
        report["kept"] += len(kept)

        cuts = slices(lo, hi, len(kept))
        if verbose:
            twins = f"  dropped {', '.join(d[0] for d in dropped)}" if dropped else ""
            print(f"  layer {row['layer']:>2}  vel {lo:>3}-{hi:<3} "
                  f"{len(codes)} takes -> {len(kept)}: "
                  + ", ".join(f"{a}-{b}" if a != b else f"{a}" for a, b in cuts) + twins)

        for code, (vmin, vmax) in zip(kept, cuts):
            for mic in mics:
                smin, smax, xmin, xmax = selector_for(mic, mics)
                zones.append(Zone(
                    sample_start=sample_start,
                    sample=codes[code][mic],
                    root_key=PAD_ROOT_NOTE,
                    key_min=PAD_ROOT_NOTE,
                    key_max=PAD_ROOT_NOTE,
                    vel_min=vmin,
                    vel_max=vmax,
                    selector_min=smin,
                    selector_max=smax,
                    selector_xfade_min=xmin,
                    selector_xfade_max=xmax,
                    name=codes[code][mic].stem,
                ))
    if expect_lo != 128:
        raise SystemExit(f"layers end at {expect_lo - 1}, not 127")
    return zones, report, mics


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kit", default="Autumn")
    ap.add_argument("--piece", default="Kick Drum")
    ap.add_argument("--articulation", default="Dampened")
    ap.add_argument("--plan", action="store_true", help="print the layout, write nothing")
    ap.add_argument("--out", type=Path, default=OUTPUT_DIR)
    args = ap.parse_args()

    kit_dir = SOURCE_ROOT / f"{args.kit} Kit Multi-Mic"
    if not kit_dir.is_dir():
        raise SystemExit(f"not found: {kit_dir}")

    name = f"{args.kit} {args.piece} {args.articulation}"
    print(f"{name}  ({kit_dir})")
    zones, report, mics = build_zones(kit_dir, args.piece, args.articulation)

    print(f"\n{report['layers']} layers, {report['takes']} takes, kept {report['kept']}, "
          f"dropped {len(report['dropped'])} near-twins (>= {TWIN_THRESHOLD})")
    for layer, code, twin, r in report["dropped"]:
        print(f"  layer {layer}: {code} ~ {twin}  {r:.4f}")
    for layer, extra in report["merged"]:
        print(f"  layer {layer}: {extra} take(s) left out - layer narrower than its takes")
    print(f"{len(zones)} zones = {report['kept']} takes x {len(mics)} mics ({', '.join(mics)})")

    if args.plan:
        return
    out = args.out / f"{name}.adv"
    MultisampleRackCreator(template=DONOR).build_device(
        Chain(name=name, zones=zones), out, num_voices=NUM_VOICES
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
