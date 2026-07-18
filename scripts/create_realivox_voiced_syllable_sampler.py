#!/usr/bin/env python3
"""
Build a per-singer Realivox "Voiced Syllables" Sampler (.adv) from Cons Old:
the Bah/Bee/Boh/Boo/Buh/Dah/Dee/Doh/Doo/Duh + Ha/Hey/Ho/Laa/Shoo/Who/Yeah
syllables, chromatic, each syllable on its own Selector band. Multi-take
pitches (mainly Bah) become round-robin alternates.

Cons Old is messy: hash-named round-robin takes (Bah_01-05QZ), 'Leg' legato
variants, Lala runs, F-master retakes (FBah/FHa/FShoo...), 'fix' one-offs.
base_syllable() normalizes all of that to the base syllable; is_legato()
drops the moving takes. Only syllables with >= MIN_NOTES distinct pitches
are kept.

Run:
    PYTHONPATH=src python3 scripts/create_realivox_voiced_syllable_sampler.py [Singer|all]
"""
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import pitch_zones, enable_round_robin
from create_realivox_syllable_sampler import (
    OUT_DIR, TEMPLATE, MANIFEST, MIN_NOTES,
    midi_to_name, wav_sr_frames, current_path, band,
)

FOLDER_KW = "Cons Old"


def is_legato(fn):
    return bool(re.search(r"leg|up\d|down\d|\bup\b|\bdown\b|\bdn\b|dn\d|lala|partial|fall|\bmel\b", fn, re.I))


def base_syllable(fn):
    s = re.sub(r"\.wav$", "", fn, flags=re.I)
    s = re.sub(r"\s*\(\d+\)$", "", s)                   # trailing "(1)" dup marker
    s = re.sub(r"-[A-Za-z0-9]{2,5}$", "", s)            # hash suffix -05QZ
    s = re.sub(r"(?i)\s*(mstr|master)\w*", " ", s)      # master/mstr clusters
    s = re.sub(r"(?i)(fix|new|old)", "", s)             # patch markers
    s = re.sub(r"\s*[A-G]#?-?\d+\s*$", "", s)           # trailing note
    s = s.strip()
    while re.search(r"[ _]?\d+$", s) and not s[-1].isalpha():  # strip take/pitch indices: " 1", "_01", glued "65"
        s = re.sub(r"[ _]?\d+$", "", s).strip()
    s = re.sub(r"^(CKFN|CKF|CK|Ck)\s*", "", s)
    s = re.sub(r"^F(?=[A-Z])", "", s)                   # F modifier (FBah->Bah, keep Fa)
    return re.sub(r"\s+", " ", s).strip()


def collect(singer):
    g = {}  # syllable -> {pitch: [(path, conf)]}
    for r in csv.DictReader(open(MANIFEST)):
        if r["singer"] != singer or FOLDER_KW not in r["folder"]:
            continue
        if r["flag"] not in ("ok", "low_conf") or not r["detected_midi"]:
            continue
        if is_legato(r["filename"]):
            continue
        syl = base_syllable(r["filename"])
        if not syl:
            continue
        midi = int(r["detected_midi"])
        p = current_path(singer, r["folder"], r["filename"], midi)
        if not p.exists():
            continue
        g.setdefault(syl, {}).setdefault(midi, []).append((p, float(r["confidence"])))
    return {syl: d for syl, d in g.items() if len(d) >= MIN_NOTES}


def build(singer):
    chosen = collect(singer)
    if not chosen:
        print(f"{singer}: no voiced syllables"); return
    syllables = sorted(chosen)

    creator = SamplerCreator(template=TEMPLATE)
    root = ET.fromstring(decode_adg(TEMPLATE))
    smap = root.find(".//MultiSampleMap")
    parts_el = smap.find("SampleParts")
    for c in list(parts_el):
        parts_el.remove(c)

    print(f"\n{singer}  ->  {len(syllables)} voiced syllables")
    index = 0
    rr_pitches = 0
    for si, syl in enumerate(syllables):
        pitches = chosen[syl]
        sel_lo, sel_hi = band(si, len(syllables))
        roots = sorted(pitches)
        zones = {m: (kmin, kmax) for m, kmin, kmax in pitch_zones(roots)}
        for midi in roots:
            kmin, kmax = zones[midi]
            takes = pitches[midi]
            if len(takes) > 1:
                rr_pitches += 1
            for p, _ in takes:
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
        print(f"  [{sel_lo:3d}-{sel_hi:3d}] {syl:6s}: {len(roots):2d} notes  {midi_to_name(roots[0])}–{midi_to_name(roots[-1])}")

    enable_round_robin(smap)  # alternate same-key/same-selector multi-takes
    sel = root.find(".//SampleSelector/Manual")
    if sel is not None:
        sel.set("Value", "0")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"Realivox {singer} Voiced Syllables.adv"
    encode_adg(ET.tostring(root, encoding="UTF-8", xml_declaration=True), out)
    print(f"  => {out.name}  ({index} parts, {rr_pitches} round-robin pitches)")


if __name__ == "__main__":
    who = sys.argv[1] if len(sys.argv) > 1 else "Cheryl"
    singers = ["Cheryl", "Julie", "Patty", "Teresa", "Toni"] if who == "all" else [who]
    for s in singers:
        build(s)
