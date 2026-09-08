#!/usr/bin/env python3
"""
Build per-singer Realivox "Breaths" Drum Racks by cloning the 8dio "African
Breath 01" DrumCell rack and swapping each pad's sample for a Realivox breath.
Reuses beat_tools_to_drumcell.build_rack (clone donor, swap pad FileRef +
metadata, drop surplus pads) — rack layout/macros/DrumCell voice params kept.

Breaths live in one shared folder, tagged by singer initials:
    CK=Cheryl  JG=Julie  PM=Patty  TP=Toni  TR=Teresa
They're unpitched, so one breath per pad (donor has 32 pads; Cheryl's 33 fill
32, the rest make smaller racks).

Run:
    PYTHONPATH=src python3 scripts/create_realivox_breath_racks.py
"""
import copy
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_device_creator.core import decode_adg
from beat_tools_to_drumcell import build_rack
from create_realivox_vowel_sampler import wav_sr_frames

DONOR = Path("/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
             "Looping Presets/Instruments/Ableton/Inst/Vocal/8dio Racks/African/"
             "African Breath 01.adg")
# finished racks live alongside the wrapped samplers in the User Library
OUT_DIR = Path("/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
               "Looping Presets/Instruments/Ableton/Inst/Vocal/The Ladies")
BREATHS = Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Realivox/"
               "RealivoxLadies_Extracted/Breaths Samples")
SINGERS = {"CK": "Cheryl", "JG": "Julie", "PM": "Patty", "TP": "Toni", "TR": "Teresa"}


def donor_xml_and_template():
    x = decode_adg(str(DONOR))
    if isinstance(x, bytes):
        x = x.decode("utf-8")
    template = copy.deepcopy(next(ET.fromstring(x).iter("SampleRef")))
    return x, template


def make_sample_ref(template, wav):
    """A SampleRef pointing at `wav`, cloned from a donor pad's SampleRef so
    the FileRef structure is exactly what DrumCell expects."""
    sr = copy.deepcopy(template)
    fr = sr.find("FileRef")
    fr.find("Path").set("Value", str(wav.resolve()))
    for tag, val in (("RelativePath", f"Samples/{wav.name}"), ("RelativePathType", "0"),
                     ("LivePackName", ""), ("LivePackId", "")):
        el = fr.find(tag)
        if el is not None:
            el.set("Value", val)
    srate, frames = wav_sr_frames(wav)
    for tag, val in (("DefaultDuration", frames), ("DefaultSampleRate", srate), ("LastModDate", "0")):
        el = sr.find(tag)
        if el is not None:
            el.set("Value", str(val))
    return sr


PAD_COUNT = 32


def main():
    donor_x, template = donor_xml_and_template()
    # all breaths in singer order, each tagged with its singer
    all_breaths = []
    for prefix, singer in SINGERS.items():
        for w in sorted(BREATHS.glob(f"{prefix} *.wav")):
            all_breaths.append((w, singer))
    n_racks = (len(all_breaths) + PAD_COUNT - 1) // PAD_COUNT
    print(f"Donor: {DONOR.name}\nOut:   {OUT_DIR}")
    print(f"{len(all_breaths)} breaths -> {n_racks} rack(s) of up to {PAD_COUNT} pads\n")

    for i in range(0, len(all_breaths), PAD_COUNT):
        chunk = all_breaths[i:i + PAD_COUNT]
        rack_no = i // PAD_COUNT + 1
        samples = [{"name": w.stem, "sample_ref": make_sample_ref(template, w)} for w, _ in chunk]
        out = OUT_DIR / f"Realivox Breaths {rack_no}.adg"
        filled, n = build_rack(donor_x, samples, out)
        comp = ", ".join(f"{s}×{c}" for s, c in Counter(s for _, s in chunk).items())
        print(f"  Rack {rack_no}: {filled} pads  [{comp}]  => {out.name}")


if __name__ == "__main__":
    main()
