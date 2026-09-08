#!/usr/bin/env python3
"""
Clone the hand-built "Realivox Cheryl Syllables" Instrument Rack (.adg) and,
for every other Realivox Sampler patch (.adv), produce a copy of that rack
with ONLY the sample content swapped -- preserving all of the rack's macros
(Formant, Syllable/Selector, Random Syllable, Time Attack/Release, Start,
Osc), mappings and the tuned embedded Sampler.

Swap surgery (per the repo rule "never reconstruct the rack, only swap
samples"): replace the embedded MultiSampler's <SampleParts> with the
target's, copy the target's RoundRobin on/mode (Voiced Syllables need it),
and retitle the UserName fields. Nothing else in the rack is touched.

For the vowel patches the "Syllable" macro is relabelled "Vowel".

Run:
    PYTHONPATH=src python3 scripts/wrap_realivox_in_rack.py
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from ableton_device_creator.core import decode_adg, encode_adg

DONOR = Path("/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
             "Looping Presets/Instruments/Ableton/Inst/Vocal/The Ladies/"
             "Realivox Cheryl Syllables.adg")
DONOR_NAME = "Realivox Cheryl Syllables"
ADV_DIR = Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Realivox/Ableton Instruments")
OUT_DIR = DONOR.parent
SINGERS = ["Cheryl", "Julie", "Patty", "Teresa", "Toni"]
TYPES = ["Vowels", "Syllables", "Voiced Syllables", "Special"]
# selector-macro relabels (macro 6 / macro 7) for non-syllable patch kinds
MACRO_LABELS = {"Vowels": ("Vowel", "Random Vowel"), "Special": ("Sound", "Random Sound")}


def as_bytes(x):
    return x if isinstance(x, bytes) else x.encode()


def wrap(adv_path, name, kind):
    donor = ET.fromstring(DONOR_BYTES)
    src = ET.fromstring(as_bytes(decode_adg(str(adv_path))))

    src_map = src.find(".//MultiSampleMap")
    src_parts = src_map.find("SampleParts")
    d_map = donor.find(".//MultiSampleMap")
    d_parts = d_map.find("SampleParts")

    # 1. swap sample parts
    for c in list(d_parts):
        d_parts.remove(c)
    n = 0
    for part in list(src_parts):
        d_parts.append(part)
        n += 1
    # 2. carry round-robin on/off + mode from the source patch
    for field in ("RoundRobin", "RoundRobinMode"):
        s, d = src_map.find(field), d_map.find(field)
        if s is not None and d is not None:
            d.set("Value", s.get("Value"))
    # 3. retitle
    for un in donor.iter("UserName"):
        if un.get("Value") == DONOR_NAME:
            un.set("Value", name)
    # 4. relabel the selector macro for non-syllable kinds
    if kind in MACRO_LABELS:
        m6, m7 = MACRO_LABELS[kind]
        for el in donor.iter():
            if el.tag == "MacroDisplayNames.6" and el.get("Value") == "Syllable":
                el.set("Value", m6)
            elif el.tag == "MacroDisplayNames.7" and el.get("Value") == "Random Syllable":
                el.set("Value", m7)

    out = OUT_DIR / f"{name}.adg"
    encode_adg(ET.tostring(donor, encoding="UTF-8", xml_declaration=True), str(out))
    rr = d_map.find("RoundRobin").get("Value")
    print(f"  {name:34s} {n:4d} parts  RR={rr}")


if __name__ == "__main__":
    DONOR_BYTES = as_bytes(decode_adg(str(DONOR)))
    print(f"Donor: {DONOR.name}\nOut:   {OUT_DIR}\n")
    for singer in SINGERS:
        for kind in TYPES:
            name = f"Realivox {singer} {kind}"
            if name == DONOR_NAME:
                print(f"  {name:34s} (donor — skipped)")
                continue
            adv = ADV_DIR / f"{name}.adv"
            if not adv.exists():
                print(f"  {name:34s} !! missing {adv.name}")
                continue
            wrap(adv, name, kind)
