#!/usr/bin/env python3
"""Build the 7 "Mini" category drum racks from the 8Dio Mini .adv presets.

Each pad hosts a full velocity-layered MultiSampler taken from one base
articulation preset (variants excluded: " - " suffixes, "All" combos,
tuned/modwheel duplicates). The donor rack contributes 6 macro mappings
(Attack, Release, Transpose, Osc, Pitch Attack, Pitch Amount), grafted into
every swapped-in sampler with per-pad ranges so default macro positions
reproduce each preset's own envelope. All zone sample refs are rewritten to
the canonical 8Dio core library (md5-verified), removing any dependence on
the duplicated User Library "Samples/Imported/8Dio Mini" tree.

Encoding notes (measured, not documented):
- stored ReceivingNote = 128 - MIDI note (pads pinned to C1/36 upward)
- SendingNote is a plain MIDI note; set to the preset's dominant RootKey
  so the hosted sampler plays at natural pitch
- every element in a Live XML list needs an Id attribute (Live refuses to
  load otherwise: "Not all list members have Ids")
"""
import copy
import gzip
import hashlib
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

MINI = Path("/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/Looping Presets/Instruments/Ableton/Perc/Mini")
CORE = Path("/Users/Shared/Music/Soundbanks/8dio/8Dio_Mini/1_Click_Core_Library")
USERLIB = Path("/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library")
DONOR = Path(__file__).resolve().parent.parent / "output" / "Drum_Rack_Organic_Percussion.adg"
OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "mini-racks"
INSTALL_DIR = MINI.parent / "Mini Racks"

FIRST_NOTE = 36  # C1, bottom-left of the standard pad grid
MAX_PADS = 32

# rack -> ordered object folders (pads fill folder by folder from C1 upward)
RACKS = {
    "Mini Clicks & Mechanisms": [
        "Buttons", "Suitcase Locks", "Screw", "Digicam", "Ultra Click",
        "Pocket Watch", "Stopwatch"],
    "Mini Friction & Scrape": [
        "Zipper", "Shaving", "Nail File", "Marker", "Tape Measure",
        "Fingernail", "Belt"],
    "Mini Paper & Fire": [
        "Zippo", "Matches", "Paper", "Pencil", "Styrofoam", "Bubble Wrap",
        "Breaking Branch"],
    "Mini Water & Liquid": [
        "Water", "Bathtime", "Human Hose", "Shower"],
    "Mini Toys & Objects": [
        "Marbles", "Bowling", "Egg", "Plastic Box", "Plastic Cup",
        "Plastic Egg", "Monkeyballs", "Small Toy", "Clicky Toy", "Snaps",
        "Kizz", "Coins"],
    "Mini Tonal & Resonant": [
        "Music Box", "Wine Drums", "Cups", "Air Hammer", "Shelf Bracket",
        "Frying Pan", "Milk Bottle", "Sand Drums", "Wobbly Bowl"],
    "Mini Oddments": [
        "Random", "Misc", "Radio DJ", "Pixel Kit"],
}

# donor macro wiring grafted per pad (see build history):
# simple params get the donor's KeyMidi; ranges anchored to the preset's own
# envelope so the donor's default macro positions are sound-neutral
GRAFT_PARAMS = [
    ("VolumeAndPan/Envelope/AttackTime", "min=own"),   # macro Attack=0 -> natural
    ("VolumeAndPan/Envelope/ReleaseTime", "max=own"),  # macro Release=127 -> natural
    ("Pitch/TransposeKey", "donor"),                   # [-48,+48], 63.5 = 0 st
]
# these modules are absent (empty slots) in the 8Dio presets, so the donor's
# neutral modules are transplanted whole (their mappings ride inside:
# Osc volume, Pitch Attack, Pitch Amount)
GRAFT_MODULES = ["Player/SubOsc", "Pitch/Envelope"]


# --- preset selection -------------------------------------------------------

def is_variant(stem, allow_mw=False):
    s = stem.lower()
    if " - " in s:
        return True                       # "- singles", "- Harsh", "- Pedal", ...
    if re.search(r"\ball\b", s):
        return True                       # combined "All" presets
    if not allow_mw and ("tuned" in s or "modwheel" in s or re.search(r"\bmw\b", s)):
        return True
    return False


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def base_presets(folder):
    stems = sorted((p.stem for p in (MINI / folder).glob("*.adv")), key=natural_key)
    base = [s for s in stems if not is_variant(s)]
    if not base:  # folders whose only versions are mod-wheel builds
        base = [s for s in stems if not is_variant(s, allow_mw=True)]
    return base


def pad_name(folder, stem):
    name = re.sub(r"\s+01$", "", stem).strip()
    if name.lower().startswith(folder.lower()):
        short = name[len(folder):].strip()
        if len(short) > 2 and not short.isdigit():
            name = short
    return name


# --- canonical sample index -------------------------------------------------

CORE_INDEX = defaultdict(list)
for w in CORE.rglob("*.wav"):
    CORE_INDEX[w.name.lower()].append(w)  # imports lowercased some names


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


def canonical_path(referenced_relpath):
    name = Path(referenced_relpath).name
    candidates = CORE_INDEX.get(name.lower(), [])
    if not candidates:
        raise FileNotFoundError(f"no canonical wav for {name}")
    if len(candidates) == 1:
        return candidates[0]
    want = md5(USERLIB / referenced_relpath)
    for c in candidates:
        if md5(c) == want:
            return c
    raise FileNotFoundError(f"no md5 match for {name}")


# --- sampler transplant -----------------------------------------------------

def load_sampler(adv_path):
    root = ET.fromstring(gzip.open(adv_path, "rb").read())
    ms = root.find("MultiSampler")
    assert ms is not None, f"no MultiSampler in {adv_path}"
    ms.set("Id", "0")  # required on every member of the <Device> list
    parts = ms.findall(".//SampleParts/MultiSamplePart")
    for p in parts:
        fr = p.find("SampleRef/FileRef")
        canon = canonical_path(fr.find("RelativePath").get("Value"))
        fr.find("Path").set("Value", str(canon))
        fr.find("RelativePath").set("Value", canon.name)
        fr.find("RelativePathType").set("Value", "0")
    roots = Counter(int(p.find("RootKey").get("Value")) for p in parts)
    return ms, (roots.most_common(1)[0][0] if roots else 60), len(parts)


def graft_macros(donor_ms, new_ms):
    for path, range_mode in GRAFT_PARAMS:
        src, dst = donor_ms.find(path), new_ms.find(path)
        assert src is not None and dst is not None, f"param missing: {path}"
        km = src.find("KeyMidi")
        assert km is not None and dst.find("KeyMidi") is None
        dst.insert(1, copy.deepcopy(km))  # KeyMidi sits right after LomId
        own = dst.find("Manual").get("Value")
        mcr = copy.deepcopy(src.find("MidiControllerRange"))
        if range_mode == "min=own":
            mcr.find("Min").set("Value", own)
        elif range_mode == "max=own":
            mcr.find("Max").set("Value", own)
        old_mcr = dst.find("MidiControllerRange")
        idx = list(dst).index(old_mcr)
        dst.remove(old_mcr)
        dst.insert(idx, mcr)
    for path in GRAFT_MODULES:
        src, dst = donor_ms.find(path), new_ms.find(path)
        assert src is not None and dst is not None, f"module missing: {path}"
        parent = new_ms.find(path.rsplit("/", 1)[0])
        idx = list(parent).index(dst)
        replacement = copy.deepcopy(src)
        replacement.tail = dst.tail
        parent.remove(dst)
        parent.insert(idx, replacement)


# --- rack build -------------------------------------------------------------

def build_rack(rack_name, folders):
    selection = [(f, stem) for f in folders for stem in base_presets(f)]
    if len(selection) > MAX_PADS:
        counts = Counter(f for f, _ in selection)
        raise SystemExit(f"{rack_name}: {len(selection)} pads > {MAX_PADS}: {dict(counts)}")

    rack = ET.fromstring(gzip.open(DONOR, "rb").read())
    branches = sorted(rack.findall(".//DrumBranchPreset"),
                      key=lambda b: 128 - int(b.find(".//ReceivingNote").get("Value")))
    assert len(branches) == 32

    rows = []
    for i, (folder, stem) in enumerate(selection):
        sampler, rootkey, zones = load_sampler(MINI / folder / f"{stem}.adv")
        branch = branches[i]
        branch.find("Name").set("Value", pad_name(folder, stem))
        branch.find(".//ReceivingNote").set("Value", str(128 - (FIRST_NOTE + i)))
        branch.find(".//SendingNote").set("Value", str(rootkey))
        device = branch.find("DevicePresets/AbletonDevicePreset/Device")
        old = device.find("MultiSampler")
        assert old is not None
        graft_macros(old, sampler)
        sampler.tail = old.tail
        device.remove(old)
        device.insert(0, sampler)
        rows.append((FIRST_NOTE + i, pad_name(folder, stem), zones))

    parent_map = {c: p for p in rack.iter() for c in p}
    for b in branches[len(selection):]:
        parent_map[b].remove(b)

    mn = rack.find(".//MacroDisplayNames.2")
    if mn is not None:
        mn.set("Value", "Transpose")

    out = OUT_DIR / f"{rack_name}.adg"
    xml_out = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        rack, encoding="unicode").encode("utf-8")
    with open(out, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as gz:
            gz.write(xml_out)
    return out, rows


def audit(path, expected_pads):
    """Re-decode and check the failure modes we've actually hit."""
    root = ET.fromstring(gzip.open(path, "rb").read())
    problems = []
    for parent in root.iter():  # list members without Ids
        kids = list(parent)
        tags = [k.tag for k in kids]
        for k in kids:
            if k.get("Id") is None and tags.count(k.tag) > 1:
                problems.append(f"missing Id: {parent.tag}/{k.tag}")
    notes = sorted(128 - int(e.get("Value")) for e in root.iter("ReceivingNote"))
    if len(notes) != expected_pads or len(set(notes)) != len(notes):
        problems.append(f"bad pad notes: {notes}")
    if notes and (notes[0] != FIRST_NOTE or notes[-1] != FIRST_NOTE + expected_pads - 1):
        problems.append(f"pads not contiguous from C1: {notes[0]}-{notes[-1]}")
    for ms in root.findall(".//Device/MultiSampler"):
        if len(ms.findall(".//KeyMidi")) != 6:
            problems.append("sampler without 6 macro mappings")
    zone_refs = root.findall(".//MultiSamplePart/SampleRef/FileRef")
    missing = [fr for fr in zone_refs
               if not Path(fr.find("Path").get("Value")).exists()]
    noncanon = [fr for fr in zone_refs
                if "/8dio/8Dio_Mini/" not in fr.find("Path").get("Value")]
    if missing:
        problems.append(f"{len(missing)} zone samples missing on disk")
    if noncanon:
        problems.append(f"{len(noncanon)} zone refs not canonical")
    return problems, len(zone_refs)


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    total_pads = total_zones = 0
    for rack_name, folders in RACKS.items():
        out, rows = build_rack(rack_name, folders)
        problems, zones = audit(out, len(rows))
        status = "OK" if not problems else "; ".join(problems)
        print(f"{rack_name}: {len(rows)} pads, {zones} zones, "
              f"{out.stat().st_size // 1024} KB [{status}]")
        if problems:
            raise SystemExit(f"audit failed for {rack_name}")
        shutil.copy2(out, INSTALL_DIR / out.name)
        total_pads += len(rows)
        total_zones += zones
    print(f"\ntotal: {len(RACKS)} racks, {total_pads} pads, {total_zones} zones")
    print(f"built in {OUT_DIR}")
    print(f"installed to {INSTALL_DIR}")
