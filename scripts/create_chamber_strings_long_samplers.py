#!/usr/bin/env python3
"""
Create Chamber Strings LONG Sampler patches — flat, single-Sampler `.adv`
files, one per articulation x mic x dynamic layer. No racks, no macros, no
chains; these are building blocks to be assembled into a master rack by hand.

Source: .../Spitfire/Chamber Strings/Long/<Artic>_<Mic>/
    ChamberEnsLong<Artic>_<Mic>_<Note>_<MIDI>_cc<NNN>.wav
    e.g. ChamberEnsLong_Close_A#1_034_cc001.wav

The three-digit field is the MIDI root key and `cc` is the dynamic layer.
Six layers per note — cc001/026/051/076/102/127 — named dyn1..dyn6 in that
order; measured RMS rises monotonically across them (2026-09-09), so the
ordering is the recorded dynamic ordering.

Ranges are fully chromatic: every semitone is sampled, so every key zone is
exactly one key wide with root key = that note and no stretching anywhere.
Most articulations span MIDI 24-96, Sul Tasto 36-96, Harmonics 60-96.
Velocity is full 1-127 on every zone — the dynamics are separate patches,
never on velocity.

## Two sets

`--flat` writes one mic per patch (84 files) with the Sample Selector unused.

`--combined` writes both mics into one Sampler (42 files), crossfaded on the
Sample Selector: the Close zones are full at selector 0 and fade to silence at
127, the Far zones mirror them. Both mics' zones overlap for every note, so
Live layers them and the selector mixes. This works *only* because the library
has no round robins — one take per note per layer per mic. With round robin on,
Live would treat the two overlapping zones as alternates and play one mic at a
time instead of blending. Verified against a Live-saved Close/Far preset.

Close and Far are NOT two mics of one take: measured coherence between them is
0.04-0.12 in every band and note onsets differ by up to half a second, so a
mid-selector blend doubles two independent performances rather than moving a
mic. It is a usable sound, but it is not mic positioning.

## Looping

Every source file is a 24 s sustain carrying a WAV `smpl` chunk with one
forward loop (typically frames 176400 -> 1058399, i.e. 4.0 s -> 24.0 s). Live
reads `smpl` only when a sample is dragged into the UI, never when it loads a
preset, so each zone's sustain loop is written into the XML explicitly, read
from the file's own chunk (`loop="auto"`).

## Known source defect

`Long_Harmonics_Far` is not the Far mic: it is the Close render. Notes 60-70
are byte-identical files and the rest are waveform-identical (coherence 1.000,
max difference one 24-bit LSB). Measured 2026-09-09. The flat set still writes
the Harmonics Far patches, since that is what is on disk, but they duplicate
their Close counterparts. The combined set builds Harmonics from Close alone
rather than doubling one render against itself. Re-exporting that mic from
Kontakt and re-running would fix both.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_chamber_strings_long_samplers.py --test
    python3 scripts/create_chamber_strings_long_samplers.py            # all 126
    python3 scripts/create_chamber_strings_long_samplers.py --flat
    python3 scripts/create_chamber_strings_long_samplers.py --combined
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ableton_device_creator.sampler.multisample import (
    Chain,
    MultisampleRackCreator,
    Zone,
)
from create_chamber_strings_long_racks import (
    LONG_ROOT,
    MICS,
    SAMPLE_LIBRARY_ROOT,
    discover_articulations,
    read_long_folder,
)

REPO = Path(__file__).parent.parent
DONOR = REPO / "templates" / "oae_evo_sampler_template.adv"
FLAT_DIR = SAMPLE_LIBRARY_ROOT / "Sampler Instruments" / "Long"
COMBINED_DIR = SAMPLE_LIBRARY_ROOT / "Sampler Instruments" / "Long Close-Far"

# The six dynamic layers, softest first. Printed by --table.
DYN_CC = [1, 26, 51, 76, 102, 127]

# Folder token -> the name that reads well on a rack chain. "CS" is Spitfire's
# abbreviation for con sordino; the short articulations folder spells it out.
ARTIC_LABELS = {
    "Long": "",
    "Long_CS": "Con Sordino",
    "Long_Flautando": "Flautando",
    "Long_Harmonics": "Harmonics",
    "Long_Sul_Pont": "Sul Pont",
    "Long_Sul_Tasto": "Sul Tasto",
    "Long_Tremolo": "Tremolo",
}

# Harmonics' Far folder holds the Close render (see module docstring), so a
# combined Harmonics patch would layer one recording against itself.
CLOSE_ONLY_COMBINED = {"Long_Harmonics"}

MAX_VOICES = 32


def label_for(artic: str) -> str:
    if artic not in ARTIC_LABELS:
        raise SystemExit(f"Unknown articulation folder {artic!r} — add it to ARTIC_LABELS")
    return ARTIC_LABELS[artic]


def patch_name(artic: str, dyn_index: int, mic: str = None) -> str:
    parts = ["CS", "Long", label_for(artic)]
    if mic:
        parts.append(mic)
    parts.append(f"dyn{dyn_index}")
    return " ".join(p for p in parts if p)


def zones_for(folder: Path, cc: int, xfade: str = None):
    """One zone per recorded note at one dynamic layer.

    Every semitone is recorded, so each zone is one key wide on its own root.
    `xfade` selects the selector fade: None leaves the zone full across the
    whole selector range, "close" makes it full at 0 and silent at 127, "far"
    the mirror.
    """
    fade = {None: (None, None), "close": (0, 0), "far": (127, 127)}[xfade]
    by_note = read_long_folder(folder)
    zones = []
    for note in sorted(by_note):
        sample = by_note[note].get(cc)
        if sample is None:
            print(f"    ! note {note} has no cc{cc:03d} layer — skipped")
            continue
        zones.append(
            Zone(
                sample=sample,
                root_key=note,
                key_min=note,
                key_max=note,
                vel_min=1,
                vel_max=127,
                selector_min=0,
                selector_max=127,
                selector_xfade_min=fade[0],
                selector_xfade_max=fade[1],
                loop="auto",
                name=sample.stem,
            )
        )
    return zones


def write_patch(creator, name: str, zones, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.adv"
    creator.build_device(Chain(name=name, zones=zones), path, num_voices=MAX_VOICES)
    looped = sum(1 for z in zones if z.loop)
    print(f"    {path.name}: {len(zones)} zones "
          f"({zones[0].root_key}-{zones[-1].root_key}), {looped} looped")
    return path


def build(articulations, flat: bool, combined: bool):
    """Write the requested sets. Returns per-set (patches, zones) totals."""
    creator = MultisampleRackCreator(template=DONOR)
    flat_patches = flat_zones = combined_patches = combined_zones = 0

    for artic, mics in articulations.items():
        print(f"\n=== {artic} ===")
        for dyn_index, cc in enumerate(DYN_CC, start=1):
            if flat:
                for mic in MICS:
                    zones = zones_for(mics[mic], cc)
                    write_patch(creator, patch_name(artic, dyn_index, mic), zones, FLAT_DIR)
                    flat_patches += 1
                    flat_zones += len(zones)
            if combined:
                if artic in CLOSE_ONLY_COMBINED:
                    zones = zones_for(mics["Close"], cc)
                    note = " (Close only — Far folder duplicates Close)"
                else:
                    zones = (zones_for(mics["Close"], cc, "close")
                             + zones_for(mics["Far"], cc, "far"))
                    note = ""
                print(f"  combined dyn{dyn_index}{note}")
                write_patch(creator, patch_name(artic, dyn_index), zones, COMBINED_DIR)
                combined_patches += 1
                combined_zones += len(zones)

    return (flat_patches, flat_zones), (combined_patches, combined_zones)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flat", action="store_true", help="only the 84 single-mic patches")
    ap.add_argument("--combined", action="store_true", help="only the 42 Close/Far patches")
    ap.add_argument("--test", action="store_true",
                    help="two verification patches only: flat Harmonics Close dyn1 "
                         "and combined Flautando dyn5")
    args = ap.parse_args()

    if not DONOR.exists():
        raise SystemExit(f"Donor template not found: {DONOR}")
    if not LONG_ROOT.exists():
        raise SystemExit(f"Sample library not found: {LONG_ROOT}")

    print("Dynamic layer mapping (softest first):")
    for i, cc in enumerate(DYN_CC, start=1):
        print(f"  dyn{i}  <-  cc{cc:03d}")

    articulations = discover_articulations()
    print(f"\nArticulations with both mics: {len(articulations)}")

    if args.test:
        creator = MultisampleRackCreator(template=DONOR)
        print("\n=== TEST 1: flat, Long_Harmonics Close dyn1 (cc001) ===")
        write_patch(creator, patch_name("Long_Harmonics", 1, "Close"),
                    zones_for(articulations["Long_Harmonics"]["Close"], 1), FLAT_DIR)
        print("\n=== TEST 2: combined, Long_Flautando dyn5 (cc102) ===")
        zones = (zones_for(articulations["Long_Flautando"]["Close"], 102, "close")
                 + zones_for(articulations["Long_Flautando"]["Far"], 102, "far"))
        write_patch(creator, patch_name("Long_Flautando", 5), zones, COMBINED_DIR)
        return

    flat = args.flat or not args.combined
    combined = args.combined or not args.flat
    (flat_patches, flat_zones), (comb_patches, comb_zones) = build(
        articulations, flat, combined
    )

    on_disk = sum(len(list(f.glob("*.wav"))) for mics in articulations.values()
                  for f in mics.values())
    print(f"\n{'=' * 60}\nSource .wav files on disk: {on_disk}")

    if flat:
        print(f"Flat set:     {flat_patches} patches, {flat_zones} zones")
        assert flat_patches == 84, f"expected 84 flat patches, wrote {flat_patches}"
        assert flat_zones == on_disk == 5556, (
            f"accounting failed: {flat_zones} zones vs {on_disk} files, expected 5556"
        )
        print("  OK — every one of the 5556 source files is mapped exactly once.")

    if combined:
        # Every mic of every articulation except Harmonics, whose Far folder
        # duplicates its Close render and so contributes nothing to a blend.
        harmonics_far = sum(
            len(list(mics["Far"].glob("*.wav")))
            for artic, mics in articulations.items() if artic in CLOSE_ONLY_COMBINED
        )
        expected = on_disk - harmonics_far
        print(f"Combined set: {comb_patches} patches, {comb_zones} zones")
        assert comb_patches == 42, f"expected 42 combined patches, wrote {comb_patches}"
        assert comb_zones == expected, (
            f"accounting failed: {comb_zones} zones, expected {expected} "
            f"({on_disk} files less {harmonics_far} duplicate Harmonics Far)"
        )
        print(f"  OK — {expected} zones = 5556 files less the {harmonics_far} "
              "duplicate Harmonics Far files.")


if __name__ == "__main__":
    main()
