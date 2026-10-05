#!/usr/bin/env python3
"""
Rebuild the Damage Close/Room racks as one-Sampler pads: each Close take
paired with its own Full take, both on one thin velocity slice, crossfaded on
the Sample Selector (Close full at 0 fading out, Full fading in to 127).

## Why the takes can be paired

Damage's Close and Full folders carry different random 4-char codes, so they
were treated as independent passes ("a blend is two performances"). Measured
2026-10-04 across all 732 instruments and 16015 take pairs: each Close take has
one Full take that is the same recording (median best match 0.996, lag-tolerant
correlation over the first 0.5 s), clearly ahead of the next candidate. Pairs
are assigned per velocity layer by maximum total correlation. About 4% are
ambiguous (two candidates within 0.05) - those takes sound alike, so either
partner is close - and are counted, not refused. Full is the close sound plus
ambience (it correlates ~0.99 with Close), which is why the knob crossfades
rather than layering Full on top of Close.

The old racks never paired: each pad was a two-chain rack whose Close and Room
Samplers ran their own round robins, so a mid-knob blend layered two different
hits, and only the Close Sampler followed the pad macros.

## Structure

Donor is Ben's new `Sidebar/Drum/Abbey Road Multi-Mic/50s Autumn.adg`: 32 bare
Sampler pads, RoundRobin off, notes 36-67, all identical apart from samples,
name, note and colour (checked). For every Damage rack, each source pad's name,
colour and note go onto the donor pad at the same note; empty source pads
(cleared surplus) and unused donor pads are dropped. Only `SampleParts`, the
pad `Name` and its colour are spliced - string-level, as everywhere here.

The velocity layout comes from the source pad's own Close chain: its zones'
velocity ranges and the Close takes it kept. So the Lite racks (already thinned
to 8 layers x 3 takes) stay Lite and the xFull racks stay full, with no second
thinning pass - `adc sampler thin` would read the slices as layers. Inside a
layer the takes are ordered quietest first by Close attack energy and given
contiguous slices. A take with no Full partner, or a near-twin of a kept take
(>= 0.999 on both mics), is left out and reported.

Output is staged, mirroring `Instruments/`, for validation in Live before
anything in the library is replaced.

Usage:
    PYTHONPATH=src uv run --no-project --with numpy --with soundfile \\
        python scripts/create_damage_paired_racks.py [--plan] [--only NAME]
"""

import argparse
import itertools
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler.multisample import MultisampleRackCreator, Zone
from create_abbey_road_aux_racks import normalised, pad_spans, set_direct_child, xml_attr
from create_abbey_road_multimic_sampler import (
    ATTACK_S, PAD_ROOT_NOTE, TWIN_THRESHOLD, lagged_corr, load_mono, slices,
)

INSTRUMENTS = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments"
)
DONOR = INSTRUMENTS / "Sidebar/Drum/Abbey Road Multi-Mic/50s Autumn.adg"
SETS = ["Sidebar/Perc/Damage Lite", "xFull/Damage"]
STAGING = Path("/Users/Shared/Music/_staging/Damage paired 2026-10-04")

PAIR_S = 0.5            # window for Close/Full pairing
AMBIGUOUS_MARGIN = 0.05
# Sample Selector: Close full at 0, gone at 127; Full the mirror.
SELECTOR = {"Close": (0, 127, 0, 0), "Full": (0, 127, 127, 127)}
V_RE = re.compile(r"-V(\d+)-(\w{4})\.wav$")


# ------------------------------------------------------------------ analysis

def assign(m: np.ndarray):
    """Rows -> columns maximising total correlation (layers hold <= 6 takes)."""
    rows, cols = m.shape
    best, best_sum = None, -1.0
    if rows <= cols:
        for perm in itertools.permutations(range(cols), rows):
            s = sum(m[i, j] for i, j in enumerate(perm))
            if s > best_sum:
                best, best_sum = list(enumerate(perm)), s
    else:
        for perm in itertools.permutations(range(rows), cols):
            s = sum(m[i, j] for j, i in enumerate(perm))
            if s > best_sum:
                best, best_sum = [(i, j) for j, i in enumerate(perm)], s
    return best


def analyse_instrument(inst_dir: str):
    """Per Close take: Full partner, pairing quality, attack energy, twins.

    Returns {close_path: {"full": path|None, "corr", "ambiguous", "energy",
    "twin_of": close_path|None}}.
    """
    inst = Path(inst_dir)
    takes = {m: defaultdict(dict) for m in ("Close", "Full")}
    for mic in takes:
        for f in (inst / mic).glob("*.wav"):
            m = V_RE.search(f.name)
            if m:
                takes[mic][int(m[1])][m[2]] = f
    out = {}
    for vel, closes in takes["Close"].items():
        fulls = takes["Full"].get(vel, {})
        c_keys, f_keys = sorted(closes), sorted(fulls)
        ca = {k: load_mono(closes[k], PAIR_S) for k in c_keys}
        fa = {k: load_mono(fulls[k], PAIR_S) for k in f_keys}
        partner = {}
        if f_keys:
            m = np.array([[lagged_corr(ca[c], fa[f]) for f in f_keys] for c in c_keys])
            for i, j in assign(m):
                others = np.delete(m[i], j)
                margin = m[i, j] - (others.max() if len(others) else 0.0)
                partner[c_keys[i]] = (f_keys[j], float(m[i, j]), bool(len(others) and margin < AMBIGUOUS_MARGIN))
        twin_of = defaultdict(set)
        for a, b in itertools.combinations([c for c in c_keys if c in partner], 2):
            if (lagged_corr(ca[a], ca[b]) >= TWIN_THRESHOLD
                    and lagged_corr(fa[partner[a][0]], fa[partner[b][0]]) >= TWIN_THRESHOLD):
                twin_of[a].add(str(closes[b]))
                twin_of[b].add(str(closes[a]))
        for c in c_keys:
            full, corr, amb = partner.get(c, (None, 0.0, False))
            out[str(closes[c])] = {
                "full": str(fulls[full]) if full else None,
                "corr": corr,
                "ambiguous": amb,
                "energy": float(np.sqrt(np.mean(load_mono(closes[c], ATTACK_S) ** 2))),
                "twins": twin_of[c],
            }
    return inst_dir, out


def twins(group, info):
    """Close paths in a layer to leave out as near-twins (>= TWIN_THRESHOLD on
    both mics) of a louder kept take."""
    kept, dropped = [], []
    for c in sorted(group, key=lambda c: -info[c]["energy"]):
        if info[c]["twins"] & set(kept):
            dropped.append(c)
        else:
            kept.append(c)
    return dropped


# ---------------------------------------------------------------- rack plan

def source_pads(rack: Path):
    """[(note, name, colour, {(lo, hi): [close paths]})] for each non-empty pad."""
    pads = []
    for p in ET.fromstring(decode_adg(rack)).findall(".//BranchPresets/DrumBranchPreset"):
        layers = defaultdict(list)
        for part in p.findall(".//SampleParts/MultiSamplePart"):
            path = part.find("SampleRef/FileRef/Path").get("Value")
            if "/Close/" not in path:
                continue
            vr = part.find("VelocityRange")
            layers[(int(vr.find("Min").get("Value")), int(vr.find("Max").get("Value")))].append(path)
        if not layers:
            continue
        note = 128 - int(p.find("ZoneSettings/ReceivingNote").get("Value"))
        pads.append((note, p.find("Name").get("Value"),
                     p.find("DocumentColorIndex").get("Value"), dict(layers)))
    return pads


def pad_zones(layers, info, stats):
    zones = []
    expect = 1
    for (lo, hi) in sorted(layers):
        if lo != expect:
            raise ValueError(f"Close layers do not tile: {lo} after {expect - 1}")
        expect = hi + 1
        group = []
        for c in layers[(lo, hi)]:
            if info[c]["full"] is None:
                stats["no_full_partner"] += 1
            else:
                group.append(c)
        drop = set(twins(group, info))
        stats["twins"] += len(drop)
        group = [c for c in group if c not in drop]
        if not group:
            raise ValueError(f"layer {lo}-{hi}: no pairable take")
        group.sort(key=lambda c: (info[c]["energy"], c))
        if len(group) > hi - lo + 1:
            stats["narrow_layer"] += len(group) - (hi - lo + 1)
            group = group[len(group) - (hi - lo + 1):]
        for c, (vmin, vmax) in zip(group, slices(lo, hi, len(group))):
            stats["takes"] += 1
            stats["ambiguous"] += info[c]["ambiguous"]
            for mic, path in (("Close", c), ("Full", info[c]["full"])):
                smin, smax, xmin, xmax = SELECTOR[mic]
                zones.append(Zone(
                    sample=Path(path), root_key=PAD_ROOT_NOTE,
                    key_min=PAD_ROOT_NOTE, key_max=PAD_ROOT_NOTE,
                    vel_min=vmin, vel_max=vmax,
                    selector_min=smin, selector_max=smax,
                    selector_xfade_min=xmin, selector_xfade_max=xmax,
                    name=Path(path).stem,
                ))
    if expect != 128:
        raise ValueError(f"Close layers end at {expect - 1}")
    return zones


# --------------------------------------------------------------------- build

def build_rack(donor, spans, donor_notes, pads, info, creator, stats):
    by_note = {note: (name, colour, zones) for note, name, colour, zones in
               ((n, nm, col, pad_zones(layers, info, stats)) for n, nm, col, layers in pads)}
    missing = set(by_note) - set(donor_notes)
    if missing:
        raise ValueError(f"source notes {sorted(missing)} have no donor pad")
    out, cursor = [], 0
    for (start, end), note in zip(spans, donor_notes):
        if note in by_note:
            name, colour, zones = by_note[note]
            pad = donor[start:end]
            parts = ET.Element("SampleParts")
            for i, z in enumerate(zones):
                parts.append(creator._sample_part(i, z))
            sp = re.search(r"<SampleParts>.*?</SampleParts>", pad, re.S)
            pad = pad[:sp.start()] + ET.tostring(parts, encoding="unicode") + pad[sp.end():]
            pad = set_direct_child(pad, "Name", xml_attr(name))
            pad = set_direct_child(pad, "DocumentColorIndex", colour)
            pad = set_direct_child(pad, "AutoColored", "false")
            out.append(donor[cursor:start] + pad)
        else:
            ws = len(donor[cursor:start]) - len(donor[cursor:start].rstrip())
            out.append(donor[cursor:start - ws])
        cursor = end
    out.append(donor[cursor:])
    return "".join(out), by_note


def verify(result, by_note):
    pads = ET.fromstring(result).findall(".//BranchPresets/DrumBranchPreset")
    assert len(pads) == len(by_note)
    for p in pads:
        note = 128 - int(p.find("ZoneSettings/ReceivingNote").get("Value"))
        name, colour, zones = by_note[note]
        assert p.find("Name").get("Value") == name
        assert p.find("DocumentColorIndex").get("Value") == colour
        assert p.find(".//MultiSampleMap/RoundRobin").get("Value") == "false"
        parts = p.findall(".//SampleParts/MultiSamplePart")
        assert len(parts) == len(zones)
        by_vel = defaultdict(list)
        for part in parts:
            path = part.find("SampleRef/FileRef/Path").get("Value")
            assert Path(path).is_file(), path
            vr = part.find("VelocityRange")
            for v in range(int(vr.find("Min").get("Value")), int(vr.find("Max").get("Value")) + 1):
                by_vel[v].append(path)
        assert set(by_vel) == set(range(1, 128)), name
        for v, paths in by_vel.items():
            mics = sorted("Close" if "/Close/" in x else "Full" for x in paths)
            assert mics == ["Close", "Full"], (name, v, paths)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--plan", action="store_true", help="analyse and report, write nothing")
    ap.add_argument("--only", help="build only racks whose path contains this text")
    ap.add_argument("--out", type=Path, default=STAGING)
    args = ap.parse_args()

    donor = decode_adg(DONOR)
    spans = pad_spans(donor)
    if len({normalised(donor[s:e]) for s, e in spans}) != 1:
        raise SystemExit("donor pads differ beyond samples/name/note/colour - refusing")
    donor_notes = [128 - int(p.find("ZoneSettings/ReceivingNote").get("Value"))
                   for p in ET.fromstring(donor).findall(".//BranchPresets/DrumBranchPreset")]

    racks = [r for s in SETS for r in sorted((INSTRUMENTS / s).rglob("*.adg"))
             if not args.only or args.only in str(r)]
    plans = {r: source_pads(r) for r in racks}
    instruments = sorted({str(Path(c).parent.parent) for pads in plans.values()
                          for _, _, _, layers in pads for cs in layers.values() for c in cs})
    print(f"{len(racks)} racks, {len(instruments)} instruments to analyse")

    info = {}
    with ProcessPoolExecutor(8) as ex:
        for _, res in ex.map(analyse_instrument, instruments, chunksize=2):
            info.update(res)

    creator = MultisampleRackCreator(template=DONOR)
    total = Counter()
    for rack in racks:
        stats = Counter()
        result, by_note = build_rack(donor, spans, donor_notes, plans[rack], info, creator, stats)
        verify(result, by_note)
        total.update(stats)
        rel = rack.relative_to(INSTRUMENTS)
        flags = ", ".join(f"{k} {v}" for k, v in stats.items() if k != "takes" and v)
        print(f"  {rel}: {len(by_note)} pads, {stats['takes']} takes" + (f"  ({flags})" if flags else ""))
        if not args.plan:
            out = args.out / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            encode_adg(result, out)
    print(f"\nTotal: {total['takes']} paired takes; left out {total['no_full_partner']} with no "
          f"Full partner, {total['twins']} twins, {total['narrow_layer']} in layers narrower than "
          f"their takes; {total['ambiguous']} ambiguous pairings kept")
    print("(plan only - nothing written)" if args.plan else f"staged under {args.out}")


if __name__ == "__main__":
    main()
