#!/usr/bin/env python3
"""
Build a per-singer Realivox "Vowels" Sampler (.adv): all pure vowels loaded
chromatically into ONE Ableton Sampler, each vowel on its own Selector band
so a single knob/CC (Sampler's built-in Sample Selector) switches vowel.

Data source: the tagged vowel WAVs + realivox_vowel_pitch_manifest.csv under
the Ben Multisamples copy (produced by analyze_/embed_realivox_vowel_pitch).
Each file's root note = manifest detected_midi (the true MIDI number, which
is also what got embedded in the WAV smpl chunk).

- Legato/diphthong/unpitched rows are ignored (only flag ok/low_conf pure
  vowels are used). Per canonical vowel we pick the single articulation with
  the most samples, dedupe to one sample per pitch, and build contiguous key
  zones with pitch_zones(). Each vowel gets an equal slice of the 0-127
  Selector axis.
- Sample paths are absolute (renamed files with the note appended), so the
  .adv resolves regardless of where it's saved.

Run:
    PYTHONPATH=src python3 scripts/create_realivox_vowel_sampler.py [Singer|all]
"""
import csv
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from multisample_utils import pitch_zones

BEN = Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Realivox")
BASE = BEN / "RealivoxLadies_Extracted"
MANIFEST = BEN / "realivox_vowel_pitch_manifest.csv"
OUT_DIR = BEN / "Ableton Instruments"
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "oae_evo_sampler_template.adv"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
midi_to_name = lambda m: f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"

# canonical vowel order (defines Selector band order); library articulation -> canonical
VOWEL_ORDER = ["Ah", "Eh", "Ee", "Oh", "Oo", "Uh", "Mm"]
# a vowel needs at least this many chromatic samples to be worth mapping;
# below it the source is too sparse (mostly legato) and would stretch badly
MIN_NOTES = 8
DIPHTHONG_MARKERS = ("wah", "wee", "yah", "yoh", "you", "yeah", "hey", "eyo", "eyu")


def canonical_vowel(art):
    a = "".join(c for c in art.lower() if c.isalpha())
    a = a.lstrip()  # noop but explicit
    for pfx in ("mm", "pm", "ck", "jg", "sd", "tp", "tr", "patty", "cheryl", "julie", "teresa", "toni"):
        if a.startswith(pfx):
            a = a[len(pfx):]
            break
    if any(t in a for t in DIPHTHONG_MARKERS):
        return None
    if a.startswith("ahh") or a == "ah":
        return "Ah"
    if a.startswith("aae"):
        return "Eh"
    if a.startswith("eee") or a == "ee":
        return "Ee"
    if a.startswith("ohh") or a == "oh":
        return "Oh"
    if a.startswith("ooo") or a == "oo":
        return "Oo"
    if a.startswith("uh"):
        return "Uh"
    if a.startswith("hmm") or a.startswith("mmm") or a == "mm":
        return "Mm"
    return None


def wav_sr_frames(path):
    """(sample_rate, frame_count) from a RIFF/WAVE header, any bit depth."""
    with open(path, "rb") as f:
        if f.read(12)[:4] != b"RIFF":
            return 44100, 0
        sr = ch = bits = 0
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            cid, sz = hdr[:4], struct.unpack("<I", hdr[4:8])[0]
            if cid == b"fmt ":
                fmt = f.read(sz)
                ch = struct.unpack("<H", fmt[2:4])[0]
                sr = struct.unpack("<I", fmt[4:8])[0]
                bits = struct.unpack("<H", fmt[14:16])[0]
            elif cid == b"data":
                frames = sz // max(1, ch * (bits // 8))
                return sr, frames
            else:
                f.seek(sz + (sz & 1), 1)
    return sr or 44100, 0


def current_path(singer, folder, filename, midi):
    """Reconstruct the post-embed path (note appended by embed_realivox_pitch)."""
    note = midi_to_name(midi)
    stem = filename[:-4] if filename.lower().endswith(".wav") else filename
    name = filename if stem.endswith(f" {note}") else f"{stem} {note}.wav"
    return BASE / f"{singer} Samples" / folder / name


def collect(singer):
    """Return {canonical_vowel: [(path, root_midi), ...]} for one singer."""
    # group rows by (vowel, articulation)
    groups = {}
    for r in csv.DictReader(open(MANIFEST)):
        if r["singer"] != singer or r["flag"] not in ("ok", "low_conf"):
            continue
        if not r["detected_midi"]:
            continue
        v = canonical_vowel(r["articulation"])
        if v is None:
            continue
        groups.setdefault((v, r["articulation"]), []).append(r)

    chosen = {}
    for v in VOWEL_ORDER:
        cands = {art: rows for (vv, art), rows in groups.items() if vv == v}
        if not cands:
            continue
        art = max(cands, key=lambda a: len(cands[a]))  # articulation with most samples
        by_root = {}
        for r in cands[art]:
            midi = int(r["detected_midi"])
            p = current_path(singer, r["folder"], r["filename"], midi)
            if not p.exists():
                print(f"    !! missing {p.name}")
                continue
            # dedupe: one sample per root pitch (keep highest confidence)
            if midi not in by_root or float(r["confidence"]) > by_root[midi][1]:
                by_root[midi] = (p, float(r["confidence"]))
        if by_root:
            chosen[v] = (art, sorted((m, p) for m, (p, _) in by_root.items()))
    return chosen


def band(i, n):
    lo = round(i * 128 / n)
    hi = round((i + 1) * 128 / n) - 1
    return lo, max(lo, hi)


def build(singer):
    chosen = collect(singer)
    if not chosen:
        print(f"{singer}: no vowels found"); return
    for v in VOWEL_ORDER:
        if v in chosen and len(chosen[v][1]) < MIN_NOTES:
            print(f"  (skip {v}: only {len(chosen[v][1])} sample(s) — too sparse)")
    vowels = [v for v in VOWEL_ORDER if v in chosen and len(chosen[v][1]) >= MIN_NOTES]

    creator = SamplerCreator(template=TEMPLATE)
    root = ET.fromstring(decode_adg(TEMPLATE))
    parts_el = root.find(".//MultiSampleMap/SampleParts")
    for c in list(parts_el):
        parts_el.remove(c)

    print(f"\n{singer}  ->  {len(vowels)} vowels")
    index = 0
    for vi, v in enumerate(vowels):
        art, samples = chosen[v]
        sel_lo, sel_hi = band(vi, len(vowels))
        roots = [m for m, _ in samples]
        zones = {m: (kmin, kmax) for m, kmin, kmax in pitch_zones(roots)}
        for midi, path in samples:
            kmin, kmax = zones[midi]
            part = creator._create_sample_part(index, path, kmin, kmax, midi)
            # per-vowel Selector band (hard switch: crossfade = band edges)
            sr = part.find("SelectorRange")
            for tag, val in (("Min", sel_lo), ("Max", sel_hi), ("CrossfadeMin", sel_lo), ("CrossfadeMax", sel_hi)):
                sr.find(tag).set("Value", str(val))
            # correct sample metadata so Live doesn't need to rescan
            srate, frames = wav_sr_frames(path)
            ref = part.find("SampleRef")
            ref.find("DefaultSampleRate").set("Value", str(srate))
            ref.find("DefaultDuration").set("Value", str(frames))
            parts_el.append(part)
            index += 1
        print(f"  [{sel_lo:3d}-{sel_hi:3d}] {v:3s}  ({art}): {len(samples):2d} notes  {midi_to_name(roots[0])}–{midi_to_name(roots[-1])}")

    # start the Selector on the first vowel
    sel = root.find(".//SampleSelector/Manual")
    if sel is not None:
        sel.set("Value", "0")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"Realivox {singer} Vowels.adv"
    encode_adg(ET.tostring(root, encoding="UTF-8", xml_declaration=True), out)
    print(f"  => {out}  ({index} parts)")


if __name__ == "__main__":
    who = sys.argv[1] if len(sys.argv) > 1 else "Cheryl"
    singers = ["Cheryl", "Julie", "Patty", "Teresa", "Toni"] if who == "all" else [who]
    for s in singers:
        build(s)
