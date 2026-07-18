#!/usr/bin/env python3
"""
Build a per-singer Realivox "Special" Sampler (.adv): the Bom / Boom / Bop
sounds, chromatic, each on its own Selector band. Multi-take pitches become
round-robin alternates (Bop especially). Bowfall + Leg/Up/Down takes are
skipped (already flagged 'legato' in the manifest).

Source: realivox_special_pitch_manifest.csv (root note = detected_midi).
Special files are NOT renamed/embedded, so paths are the original names.
Articulation is classified by content (Bom/Boom/Bop) to fold together the
hash-named round-robin takes some singers use (Julie's BadeBom-XXXX).

Run:
    PYTHONPATH=src python3 scripts/create_realivox_special_sampler.py [Singer|all]
"""
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import pitch_zones, enable_round_robin
from create_realivox_vowel_sampler import BASE, OUT_DIR, TEMPLATE, midi_to_name, wav_sr_frames, band

MANIFEST = BASE.parent / "realivox_special_pitch_manifest.csv"
ORDER = ["Bom", "Boom", "Bop"]
MIN_NOTES = 8


def classify(fn):
    s = fn.lower()
    if "boom" in s:
        return "Boom"
    if "bop" in s:
        return "Bop"
    if "bom" in s:      # includes Julie's BadeBom
        return "Bom"
    return None


def collect(singer):
    g = {}  # articulation -> {pitch: [paths]}
    for r in csv.DictReader(open(MANIFEST)):
        if r["singer"] != singer or r["flag"] not in ("ok", "low_conf") or not r["detected_midi"]:
            continue
        art = classify(r["filename"])
        if art is None:
            continue
        p = BASE / f"{singer} Samples" / r["folder"] / r["filename"]
        if not p.exists():
            continue
        g.setdefault(art, {}).setdefault(int(r["detected_midi"]), []).append(p)
    return {a: d for a, d in g.items() if len(d) >= MIN_NOTES}


def build(singer):
    chosen = collect(singer)
    if not chosen:
        print(f"{singer}: no Special sounds"); return
    arts = [a for a in ORDER if a in chosen]

    creator = SamplerCreator(template=TEMPLATE)
    root = ET.fromstring(decode_adg(TEMPLATE))
    smap = root.find(".//MultiSampleMap")
    parts_el = smap.find("SampleParts")
    for c in list(parts_el):
        parts_el.remove(c)

    print(f"\n{singer}  ->  {len(arts)} special sounds")
    index = 0
    rr = 0
    for ai, art in enumerate(arts):
        pitches = chosen[art]
        sel_lo, sel_hi = band(ai, len(arts))
        roots = sorted(pitches)
        zones = {m: (kmin, kmax) for m, kmin, kmax in pitch_zones(roots)}
        for midi in roots:
            kmin, kmax = zones[midi]
            takes = pitches[midi]
            if len(takes) > 1:
                rr += 1
            for p in takes:
                part = creator._create_sample_part(index, p, kmin, kmax, midi)
                sr = part.find("SelectorRange")
                for tag, val in (("Min", sel_lo), ("Max", sel_hi), ("CrossfadeMin", sel_lo), ("CrossfadeMax", sel_hi)):
                    sr.find(tag).set("Value", str(val))
                srate, frames = wav_sr_frames(p)
                ref = part.find("SampleRef")
                ref.find("DefaultSampleRate").set("Value", str(srate))
                ref.find("DefaultDuration").set("Value", str(frames))
                parts_el.append(part)
                index += 1
        print(f"  [{sel_lo:3d}-{sel_hi:3d}] {art:5s}: {len(roots):2d} notes  {midi_to_name(roots[0])}–{midi_to_name(roots[-1])}")

    if rr:
        enable_round_robin(smap)
    sel = root.find(".//SampleSelector/Manual")
    if sel is not None:
        sel.set("Value", "0")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"Realivox {singer} Special.adv"
    encode_adg(ET.tostring(root, encoding="UTF-8", xml_declaration=True), out)
    print(f"  => {out.name}  ({index} parts, {rr} round-robin pitches)")


if __name__ == "__main__":
    who = sys.argv[1] if len(sys.argv) > 1 else "Cheryl"
    singers = ["Cheryl", "Julie", "Patty", "Teresa", "Toni"] if who == "all" else [who]
    for s in singers:
        build(s)
