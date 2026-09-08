#!/usr/bin/env python3
"""Audit key/velocity coverage of Ableton .adv / .adg devices.

For every device found under a folder, decode the gzipped XML, collect every
active MultiSamplePart (Sampler) or SimplerSlot (Simpler), and report:

  * which MIDI notes (0-127) have no sample at all
  * which notes have a sample but incomplete velocity coverage (1-127)

Usage:
    python3 tools/audit_key_coverage.py <folder> [--json out.json] [--all]
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

AUDIO_EXT = {".adv", ".adg"}
FULL_RANGE = (0, 127)


def decode(path: Path) -> str:
    with gzip.open(path, "rb") as fh:
        return fh.read().decode("utf-8", errors="replace")


def _val(node, tag, default=None):
    el = node.find(tag)
    if el is None:
        return default
    return el.get("Value", default)


def _int(node, tag, default=0):
    v = _val(node, tag, None)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def collect_zones(root) -> list[dict]:
    """Every active sample zone in the device, from any nested sampler."""
    zones = []

    # Sampler / MultiSampler zones
    for part in root.iter("MultiSamplePart"):
        if (_val(part, "IsActive", "true") or "true").lower() == "false":
            continue
        kr = part.find("KeyRange")
        vr = part.find("VelocityRange")
        if kr is None:
            continue
        zones.append(
            {
                "name": _val(part, "Name", "?"),
                "key": (_int(kr, "Min", 0), _int(kr, "Max", 127)),
                "vel": (
                    (_int(vr, "Min", 1), _int(vr, "Max", 127))
                    if vr is not None
                    else (1, 127)
                ),
                "kind": "sampler",
            }
        )

    # Simpler: one sample, plays the whole keyboard unless a zone says otherwise
    for simpler in root.iter("OriginalSimpler"):
        player = simpler.find("Player")
        if player is None:
            continue
        if any(True for _ in player.iter("MultiSamplePart")):
            continue  # already captured above
        sr = player.find("SampleRef")
        if sr is None:
            continue
        zones.append(
            {
                "name": _val(sr.find("FileRef") or ET.Element("x"), "Path", "sample"),
                "key": FULL_RANGE,
                "vel": (1, 127),
                "kind": "simpler",
            }
        )

    return zones


def coverage(zones: list[dict]) -> dict:
    """Per-note coverage: which notes are silent, which are velocity-partial."""
    note_zones: dict[int, list[tuple[int, int]]] = {n: [] for n in range(128)}
    for z in zones:
        lo, hi = z["key"]
        lo = max(0, min(127, lo))
        hi = max(0, min(127, hi))
        for n in range(lo, hi + 1):
            note_zones[n].append(z["vel"])

    silent = []
    partial = []
    for n in range(128):
        vs = note_zones[n]
        if not vs:
            silent.append(n)
            continue
        # merge velocity intervals
        vs = sorted(vs)
        merged = []
        for lo, hi in vs:
            if merged and lo <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        if merged[0][0] > 1 or merged[-1][1] < 127 or len(merged) > 1:
            partial.append((n, [tuple(m) for m in merged]))

    return {"silent": silent, "partial": partial, "zones": len(zones)}


def ranges(nums: list[int]) -> list[tuple[int, int]]:
    out = []
    for n in nums:
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return [tuple(r) for r in out]


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(n: int) -> str:
    """Ableton naming: MIDI 60 = C3."""
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 2}"


def fmt_ranges(rs: list[tuple[int, int]]) -> str:
    parts = []
    for lo, hi in rs:
        if lo == hi:
            parts.append(f"{note_name(lo)}({lo})")
        else:
            parts.append(f"{note_name(lo)}-{note_name(hi)} ({lo}-{hi})")
    return ", ".join(parts)


def audit(folder: Path) -> list[dict]:
    results = []
    files = sorted(p for p in folder.rglob("*") if p.suffix.lower() in AUDIO_EXT)
    for path in files:
        try:
            xml = decode(path)
            root = ET.fromstring(xml)
        except Exception as exc:  # noqa: BLE001
            results.append({"path": str(path), "error": str(exc)})
            continue
        zones = collect_zones(root)
        cov = coverage(zones)
        lows = [z["key"][0] for z in zones] or [None]
        highs = [z["key"][1] for z in zones] or [None]
        results.append(
            {
                "path": str(path),
                "rel": str(path.relative_to(folder)),
                "zones": cov["zones"],
                "key_span": (min(lows), max(highs)) if zones else None,
                "silent": cov["silent"],
                "partial": [(n, m) for n, m in cov["partial"]],
                "device": "sampler" if any(z["kind"] == "sampler" for z in zones) else
                          ("simpler" if zones else "unknown"),
            }
        )
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--json", type=Path, help="write full results as JSON")
    ap.add_argument("--all", action="store_true", help="list fully-covered devices too")
    args = ap.parse_args()

    res = audit(args.folder)
    if args.json:
        args.json.write_text(json.dumps(res, indent=2))

    full, gapped, errored = [], [], []
    for r in res:
        if "error" in r:
            errored.append(r)
        elif r["silent"]:
            gapped.append(r)
        else:
            full.append(r)

    print(f"Scanned {len(res)} devices in {args.folder}")
    print(f"  full 0-127 key coverage : {len(full)}")
    print(f"  has silent notes        : {len(gapped)}")
    print(f"  unreadable              : {len(errored)}")
    print()

    for r in sorted(gapped, key=lambda x: -len(x["silent"])):
        span = r["key_span"]
        print(f"{r['rel']}")
        print(
            f"   {r['zones']} zones, mapped {note_name(span[0])}-{note_name(span[1])}"
            f" ({span[0]}-{span[1]}), {len(r['silent'])} silent notes"
        )
        print(f"   silent: {fmt_ranges(ranges(r['silent']))}")
        print()

    if args.all:
        print("--- fully covered ---")
        for r in full:
            print(f"{r['rel']}  ({r['zones']} zones)")

    for r in errored:
        print(f"ERROR {r['path']}: {r['error']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
