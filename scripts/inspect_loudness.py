#!/usr/bin/env python3
"""
Inspect Loudness — measure peak/RMS level of each instrument's V127 (loudest
velocity layer) samples across the library, grouped by source category.

Uses `sox <file> -n stats` (stdlib has no audio decoding for 24-bit/float
WAV) to read Pk lev dB and RMS lev dB. One representative V127 file per
instrument (first alphabetically) is measured for speed.

Usage:
    python3 scripts/inspect_loudness.py
"""

import re
import statistics
import subprocess
import sys
from pathlib import Path

SAMPLE_LIBRARY_ROOT = Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Heavyocity/Damage")
EXCLUDED_CATEGORIES = {"Transitions", "Drum Racks"}
V127_RE = re.compile(r"-V127-", re.IGNORECASE)

SOX_STAT_RE = {
    "peak_db": re.compile(r"Pk lev dB\s+(-?\d+\.\d+)"),
    "rms_db": re.compile(r"RMS lev dB\s+(-?\d+\.\d+)"),
}


def measure(path: Path) -> dict:
    result = subprocess.run(
        ["sox", str(path), "-n", "stats"],
        capture_output=True, text=True,
    )
    output = result.stderr  # sox writes stats to stderr
    values = {}
    for key, pattern in SOX_STAT_RE.items():
        m = pattern.search(output)
        values[key] = float(m.group(1)) if m else None
    return values


def find_v127(close_dir: Path) -> Path:
    candidates = sorted(f for f in close_dir.glob("*.wav") if V127_RE.search(f.name))
    return candidates[0] if candidates else None


def main():
    print(f"Scanning: {SAMPLE_LIBRARY_ROOT}\n")

    by_category = {}
    per_instrument = []

    for category_dir in sorted(p for p in SAMPLE_LIBRARY_ROOT.iterdir() if p.is_dir()):
        if category_dir.name in EXCLUDED_CATEGORIES:
            continue
        for instrument_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            close = instrument_dir / "Close"
            if not close.is_dir():
                continue
            sample = find_v127(close)
            if sample is None:
                continue

            stats = measure(sample)
            if stats["peak_db"] is None:
                continue

            entry = {
                "category": category_dir.name,
                "instrument": instrument_dir.name,
                "peak_db": stats["peak_db"],
                "rms_db": stats["rms_db"],
            }
            per_instrument.append(entry)
            by_category.setdefault(category_dir.name, []).append(entry)

    print(f"Measured {len(per_instrument)} instruments\n")

    print(f"{'Category':20} {'n':>4} {'peak_db avg':>12} {'peak_db min':>12} {'peak_db max':>12} {'rms_db avg':>11}")
    for category, entries in sorted(by_category.items(), key=lambda kv: statistics.mean(e["peak_db"] for e in kv[1]), reverse=True):
        peaks = [e["peak_db"] for e in entries]
        rms = [e["rms_db"] for e in entries if e["rms_db"] is not None]
        print(f"{category:20} {len(entries):>4} {statistics.mean(peaks):>12.2f} {min(peaks):>12.2f} {max(peaks):>12.2f} {statistics.mean(rms):>11.2f}")

    print("\nLoudest 15 instruments by peak dB:")
    for e in sorted(per_instrument, key=lambda e: e["peak_db"], reverse=True)[:15]:
        print(f"  {e['peak_db']:>7.2f} dB peak / {e['rms_db']:>7.2f} dB RMS  {e['category']}/{e['instrument']}")

    print("\nQuietest 15 instruments by peak dB:")
    for e in sorted(per_instrument, key=lambda e: e["peak_db"])[:15]:
        print(f"  {e['peak_db']:>7.2f} dB peak / {e['rms_db']:>7.2f} dB RMS  {e['category']}/{e['instrument']}")


if __name__ == "__main__":
    main()
