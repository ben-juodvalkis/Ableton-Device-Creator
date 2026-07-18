#!/usr/bin/env python3
"""
Build a per-singer Realivox "Syllables" Sampler (.adv): the clean Cons New
consonant syllables (Fa, Kah, Tah, Shee, Moo, Way...) loaded chromatically
into ONE Ableton Sampler, each syllable on its own Selector band so a knob/CC
switches syllable -- the "chromatic playable syllables" counterpart to the
Vowels sampler.

Source: the tagged Cons New WAVs + realivox_pitch_manifest.csv (Ben's
consonant tagging). Each syllable is one-sample-per-semitone (no round
robins in Cons New), root note = detected_midi. Reuses the Vowels builder's
part/zone/metadata helpers.

Only Cons New is used (Cons Old = round-robin/legato mess, End Cons =
word-ending tails -- both deferred).

Run:
    PYTHONPATH=src python3 scripts/create_realivox_syllable_sampler.py [Singer|all]
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
from multisample_utils import pitch_zones
from create_realivox_vowel_sampler import (
    BASE, OUT_DIR, TEMPLATE, midi_to_name, wav_sr_frames, current_path, band,
)

MANIFEST = BASE.parent / "realivox_pitch_manifest.csv"   # the consonant manifest
FOLDER_KW = "Cons New"
MIN_NOTES = 12
SINGER_PFX = ("CK", "JG", "MM", "SD", "TP", "TR", "PM")


def syllable(filename):
    s = re.sub(r"\.wav$", "", filename, flags=re.I)
    s = re.sub(r"\s*[A-G]#?-?\d+$", "", s)   # trailing note (if any)
    s = re.sub(r"_\d+$", "", s).strip()       # _NN take index
    for p in SINGER_PFX:
        if s.startswith(p):
            return s[len(p):].strip()
    return s


def collect(singer):
    groups = {}
    for r in csv.DictReader(open(MANIFEST)):
        if r["singer"] != singer or FOLDER_KW not in r["folder"]:
            continue
        if r["flag"] not in ("ok", "low_conf") or not r["detected_midi"]:
            continue
        syl = syllable(r["filename"])
        midi = int(r["detected_midi"])
        p = current_path(singer, r["folder"], r["filename"], midi)
        if not p.exists():
            continue
        d = groups.setdefault(syl, {})
        if midi not in d or float(r["confidence"]) > d[midi][1]:
            d[midi] = (p, float(r["confidence"]))
    # -> {syllable: sorted [(midi, path)]}, only well-covered ones
    out = {}
    for syl, d in groups.items():
        if len(d) >= MIN_NOTES:
            out[syl] = sorted((m, p) for m, (p, _) in d.items())
    return out


def build(singer):
    chosen = collect(singer)
    if not chosen:
        print(f"{singer}: no syllables found"); return
    syllables = sorted(chosen)

    creator = SamplerCreator(template=TEMPLATE)
    root = ET.fromstring(decode_adg(TEMPLATE))
    parts_el = root.find(".//MultiSampleMap/SampleParts")
    for c in list(parts_el):
        parts_el.remove(c)

    print(f"\n{singer}  ->  {len(syllables)} syllables")
    index = 0
    for si, syl in enumerate(syllables):
        samples = chosen[syl]
        sel_lo, sel_hi = band(si, len(syllables))
        roots = [m for m, _ in samples]
        zones = {m: (kmin, kmax) for m, kmin, kmax in pitch_zones(roots)}
        for midi, path in samples:
            kmin, kmax = zones[midi]
            part = creator._create_sample_part(index, path, kmin, kmax, midi)
            sr = part.find("SelectorRange")
            for tag, val in (("Min", sel_lo), ("Max", sel_hi), ("CrossfadeMin", sel_lo), ("CrossfadeMax", sel_hi)):
                sr.find(tag).set("Value", str(val))
            srate, frames = wav_sr_frames(path)
            ref = part.find("SampleRef")
            ref.find("DefaultSampleRate").set("Value", str(srate))
            ref.find("DefaultDuration").set("Value", str(frames))
            parts_el.append(part)
            index += 1
        print(f"  [{sel_lo:3d}-{sel_hi:3d}] {syl:6s}: {len(samples):2d} notes  {midi_to_name(roots[0])}–{midi_to_name(roots[-1])}")

    sel = root.find(".//SampleSelector/Manual")
    if sel is not None:
        sel.set("Value", "0")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"Realivox {singer} Syllables.adv"
    encode_adg(ET.tostring(root, encoding="UTF-8", xml_declaration=True), out)
    print(f"  => {out.name}  ({index} parts)")


if __name__ == "__main__":
    who = sys.argv[1] if len(sys.argv) > 1 else "Cheryl"
    singers = ["Cheryl", "Julie", "Patty", "Teresa", "Toni"] if who == "all" else [who]
    for s in singers:
        build(s)
