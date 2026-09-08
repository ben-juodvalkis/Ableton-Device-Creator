#!/usr/bin/env python3
"""Make Ableton Sampler presets playable across the whole keyboard.

Two independent repairs, applied to every .adv/.adg under a folder:

  1. FILL  - close dead keys that sit inside a device's own mapped span.
             Each gap is split at its midpoint: the block below extends up,
             the block above extends down. Nothing that already sounds moves.

  2. STRETCH - extend the lowest zones down to MIDI 0 and the highest zones
             up to MIDI 127, so no key on the keyboard is silent.

Devices whose layout maps only white keys are treated as deliberate
one-sample-per-white-key maps: they are stretched, but their black keys are
left alone unless --fill-black is passed.

Edits are applied as targeted text surgery on the raw XML so that every byte
outside the touched <KeyRange> blocks is preserved exactly.

Usage:
    python3 tools/fix_key_coverage.py <src> <dst> [--fill-black] [--dry-run]
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from ableton_device_creator.core import encode_adg  # noqa: E402

EXTS = {".adv", ".adg"}
BLACK = {1, 3, 6, 8, 10}
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

PART_SPLIT = re.compile(r"(?=<MultiSamplePart\b)")
KEYRANGE_RE = re.compile(
    r"(<KeyRange>\s*"
    r"<Min Value=\")(-?\d+)(\" />\s*"
    r"<Max Value=\")(-?\d+)(\" />\s*"
    r"<CrossfadeMin Value=\")(-?\d+)(\" />\s*"
    r"<CrossfadeMax Value=\")(-?\d+)(\" />\s*"
    r"</KeyRange>)"
)
ISACTIVE_RE = re.compile(r"<IsActive Value=\"(true|false)\" />")


def note_name(n: int) -> str:
    """Ableton naming: MIDI 60 = C3."""
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 2}"


def ranges(nums):
    out = []
    for n in sorted(nums):
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return [tuple(r) for r in out]


def fmt(rs):
    return ", ".join(
        note_name(a) if a == b else f"{note_name(a)}-{note_name(b)}" for a, b in rs
    )


class Part:
    """One MultiSamplePart, located in the raw XML text."""

    __slots__ = ("text", "m", "lo", "hi", "xlo", "xhi", "active", "new_lo", "new_hi")

    def __init__(self, text: str):
        self.text = text
        end = text.find("</MultiSamplePart>")
        self.m = KEYRANGE_RE.search(text, 0, end if end != -1 else len(text))
        if self.m:
            self.lo = int(self.m.group(2))
            self.hi = int(self.m.group(4))
            self.xlo = int(self.m.group(6))
            self.xhi = int(self.m.group(8))
        else:
            self.lo = self.hi = self.xlo = self.xhi = None
        am = ISACTIVE_RE.search(text, 0, end if end != -1 else len(text))
        self.active = (am.group(1) == "true") if am else True
        self.new_lo = self.lo
        self.new_hi = self.hi

    def render(self) -> str:
        if not self.m or (self.new_lo == self.lo and self.new_hi == self.hi):
            return self.text
        g = self.m.groups()
        # Crossfade bounds ride along with the edge they sit on, so extending a
        # zone never introduces a fade-in across the newly covered keys.
        xlo = self.new_lo if self.xlo == self.lo else max(self.new_lo, self.xlo)
        xhi = self.new_hi if self.xhi == self.hi else min(self.new_hi, self.xhi)
        block = (
            f"{g[0]}{self.new_lo}{g[2]}{self.new_hi}{g[4]}{xlo}{g[6]}{xhi}{g[8]}"
        )
        return self.text[: self.m.start()] + block + self.text[self.m.end() :]


def process(xml: str, fill_black: bool) -> tuple[str, dict]:
    head, *chunks = PART_SPLIT.split(xml)
    parts = [Part(c) for c in chunks]
    zoned = [p for p in parts if p.m and p.active]
    report = {"filled": [], "stretched_low": None, "stretched_high": None,
              "whitekey": False, "zones": len(zoned)}
    if not zoned:
        return xml, report

    covered = set()
    for p in zoned:
        covered.update(range(max(0, p.lo), min(127, p.hi) + 1))
    gmin, gmax = min(p.lo for p in zoned), max(p.hi for p in zoned)

    whitekey = all(n % 12 not in BLACK for n in covered)
    report["whitekey"] = whitekey

    # --- 1. fill interior holes ------------------------------------------
    if not (whitekey and not fill_black):
        holes = [n for n in range(gmin, gmax + 1) if n not in covered]
        for lo, hi in ranges(holes):
            mid = lo + (hi - lo) // 2
            below = [p for p in zoned if p.new_hi == lo - 1]
            above = [p for p in zoned if p.new_lo == hi + 1]
            if below and above:
                for p in below:
                    p.new_hi = mid
                for p in above:
                    p.new_lo = mid + 1
            elif below:
                for p in below:
                    p.new_hi = hi
            elif above:
                for p in above:
                    p.new_lo = lo
            else:
                continue
            report["filled"].append((lo, hi))

    # --- 2. stretch the outermost zones to the keyboard edges -------------
    if gmin > 0:
        for p in zoned:
            if p.lo == gmin:
                p.new_lo = 0
        report["stretched_low"] = gmin
    if gmax < 127:
        for p in zoned:
            if p.hi == gmax:
                p.new_hi = 127
        report["stretched_high"] = gmax

    return head + "".join(p.render() for p in parts), report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--fill-black", action="store_true",
                    help="also fill black keys in white-key-only layouts")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    files = sorted(p for p in args.src.rglob("*") if p.suffix.lower() in EXTS)
    reports = []
    changed = unchanged = 0

    for path in files:
        rel = path.relative_to(args.src)
        xml = gzip.open(path, "rb").read().decode("utf-8")
        new_xml, rep = process(xml, args.fill_black)
        rep["rel"] = str(rel)
        reports.append(rep)

        if new_xml == xml:
            unchanged += 1
        else:
            changed += 1
        if not args.dry_run:
            out = args.dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            if new_xml == xml:
                shutil.copy2(path, out)
            else:
                encode_adg(new_xml, out)

    if args.json:
        args.json.write_text(json.dumps(reports, indent=2))

    filled = [r for r in reports if r["filled"]]
    print(f"{len(files)} devices | {changed} modified, {unchanged} already fine")
    print(f"  holes filled in : {len(filled)} devices")
    print(f"  stretched low   : {sum(1 for r in reports if r['stretched_low'] is not None)}")
    print(f"  stretched high  : {sum(1 for r in reports if r['stretched_high'] is not None)}")
    print(f"  white-key maps  : {sum(1 for r in reports if r['whitekey'])}"
          f" ({'black keys filled' if args.fill_black else 'black keys left alone'})")
    if filled:
        print("\n--- interior holes closed ---")
        for r in sorted(filled, key=lambda x: -sum(h - l + 1 for l, h in x["filled"])):
            n = sum(h - l + 1 for l, h in r["filled"])
            print(f"{n:>3} keys  {r['rel']}")
            print(f"          {fmt(r['filled'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
