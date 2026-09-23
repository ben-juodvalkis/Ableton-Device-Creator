#!/usr/bin/env python3
"""Rehost a Simpler-per-pad Drum Rack on DrumCells, keeping the rack itself.

The source kit's rack, pads, notes, names, choke groups and pad mixers are kept
byte for byte. Only each pad's device block changes: its OriginalSimpler
`AbletonDevicePreset` is replaced with the donor's DrumCell block, into which
the Simpler's own `SampleRef` is spliced whole (so Core Library references keep
resolving the way Live resolved them before).

Simpler settings that carry over per pad, because they set the kit's sound:
- `VolumeAndPan/Volume` -> DrumCell `Volume` (both dB)
- `VolumeAndPan/VolumeVelScale` -> DrumCell `Voice_VelocityToVolume` (both 0-1)
- a trimmed `SampleEnd` -> DrumCell `Voice_PlaybackLength` (fraction of the file)
Everything else is the donor's DrumCell voice, unchanged. A pad whose Simpler
does something a DrumCell block cannot simply inherit (transpose, a moved
sample start, reverse, more than one zone, a macro mapping) is refused, not guessed.

Why not fill the donor rack instead: the donor's pads sit on other notes, and
rewriting ReceivingNote empties pads in Live (see CLAUDE.md), so the source
kit's own rack is the only way to keep its note layout.

Edits are string-level; ElementTree only reads.

Usage:
    python3 scripts/simpler_kit_to_drumcell.py KIT.adg [--donor RACK.adg] [--out OUT.adg]
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ableton_device_creator.core import decode_adg, encode_adg  # noqa: E402

DEFAULT_DONOR = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Ableton/Drum/Electro Acoustic/1 Dry Machines/"
    " 606 + 808.adg"
)

PRESET_OPEN = re.compile(r"<AbletonDevicePreset\b[^>]*>")
PRESET_CLOSE = "</AbletonDevicePreset>"


def text(xml):
    return xml.decode("utf-8") if isinstance(xml, bytes) else xml


def preset_spans(xml, device_tag):
    """(start, end) of every AbletonDevicePreset whose device is `device_tag`.

    AbletonDevicePresets never nest inside one another, so the next close tag
    after an open tag is its own.
    """
    spans = []
    for m in PRESET_OPEN.finditer(xml):
        end = xml.index(PRESET_CLOSE, m.end()) + len(PRESET_CLOSE)
        head = xml[m.end():m.end() + 400]
        if re.search(r"<Device>\s*<%s\b" % device_tag, head):
            spans.append((m.start(), end))
    return spans


def line_indent(xml, pos):
    return xml[xml.rfind("\n", 0, pos) + 1:pos]


def reindent(block, old, new):
    return "\n".join(
        new + line[len(old):] if line.startswith(old) else line
        for line in block.split("\n")
    )


def manual(dev, path):
    e = dev.find(path + "/Manual")
    return None if e is None else e.get("Value")


def set_manual(block, param, value):
    pat = re.compile(r"(<%s>\s*<LomId[^>]*/>\s*<Manual Value=\")[^\"]*(\")" % param)
    out, n = pat.subn(lambda m: m.group(1) + value + m.group(2), block, count=1)
    if n != 1:
        raise ValueError(f"donor DrumCell has no {param}")
    return out


def check_simpler(dev):
    """Return a reason this Simpler cannot become a plain DrumCell, or None."""
    parts = dev.findall("Player/MultiSampleMap/SampleParts/MultiSamplePart")
    if len(parts) != 1:
        return f"{len(parts)} zones"
    if dev.find(".//KeyMidi") is not None:
        return "macro-mapped"
    for path, want in [("Pitch/TransposeKey", "0"), ("Pitch/TransposeFine", "0"),
                       ("Player/Reverse", "false"), ("Globals/PlaybackMode", None)]:
        if want is None:
            continue
        if manual(dev, path) != want:
            return f"{path} = {manual(dev, path)}"
    if int(parts[0].find("SampleStart").get("Value")) != 0:
        return "sample start moved"
    return None


def playback_length(dev):
    """Simpler's sample end as DrumCell's Length (fraction of the file), or None if untrimmed."""
    part = dev.find("Player/MultiSampleMap/SampleParts/MultiSamplePart")
    end = int(part.find("SampleEnd").get("Value"))
    dur = int(part.find("SampleRef/DefaultDuration").get("Value"))
    return None if end >= dur - 1 else (end + 1) / dur


def convert(src_xml, donor_xml):
    donor_spans = preset_spans(donor_xml, "DrumCell")
    if not donor_spans:
        raise ValueError("donor has no DrumCell")
    ds, de = donor_spans[0]
    donor_block = donor_xml[ds:de]
    donor_indent = line_indent(donor_xml, ds)

    root = ET.fromstring(src_xml)
    simplers = [d for d in root.iter("OriginalSimpler")]
    spans = preset_spans(src_xml, "OriginalSimpler")
    if len(spans) != len(simplers):
        raise ValueError(f"{len(spans)} Simpler presets in text, {len(simplers)} parsed")

    report = []
    out, last = [], 0
    for (s, e), dev in zip(spans, simplers):
        reason = check_simpler(dev)
        if reason:
            raise ValueError(f"pad refused: {reason}")
        simpler_text = src_xml[s:e]
        ref = re.search(r"<SampleRef\b[^>]*>(.*?)</SampleRef>", simpler_text, re.S)
        ind = line_indent(src_xml, s)
        block = reindent(donor_block, donor_indent, ind)
        # splice the Simpler's sample reference into the DrumCell's UserSample
        sr_ind = line_indent(simpler_text, ref.start())
        u = re.search(r"(<UserSample>\s*<Value>\s*)(<SampleRef\b[^>]*>)(.*?)(</SampleRef>)", block, re.S)
        tgt_ind = line_indent(block, u.start(2))
        inner = reindent(ref.group(1), sr_ind, tgt_ind)
        block = block[:u.start(3)] + inner + block[u.end(3):]
        vol = manual(dev, "VolumeAndPan/Volume")
        vel = manual(dev, "VolumeAndPan/VolumeVelScale")
        block = set_manual(block, "Volume", vol)
        block = set_manual(block, "Voice_VelocityToVolume", vel)
        length = playback_length(dev)
        if length is not None:
            block = set_manual(block, "Voice_PlaybackLength", f"{length:.10g}")
        out.append(src_xml[last:s])
        out.append(block)
        last = e
        path = dev.find(".//SampleRef/FileRef/Path").get("Value")
        report.append((path.rsplit("/", 1)[-1], vol, vel, length))
    out.append(src_xml[last:])
    return "".join(out), report


def pads(xml):
    top = ET.fromstring(xml)[0]
    return [
        (p.find("ZoneSettings/ReceivingNote").get("Value"),
         p.find("Name").get("Value") if p.find("Name") is not None else "",
         [d.tag for d in p.findall("DevicePresets/*/Device/*")])
        for p in top.findall("BranchPresets/DrumBranchPreset")
    ]


def verify(src_xml, result):
    before, after = pads(src_xml), pads(result)
    assert len(before) == len(after), "pad count changed"
    for (n0, name0, _), (n1, name1, devs) in zip(before, after):
        assert (n0, name0) == (n1, name1), f"pad {n0} changed"
        assert devs == ["DrumCell"], f"pad {n1} holds {devs}"
    s0 = [r.find(".//SampleRef/FileRef/Path").get("Value")
          for r in ET.fromstring(src_xml).iter("OriginalSimpler")]
    s1 = [r.find(".//UserSample//SampleRef/FileRef/Path").get("Value")
          for r in ET.fromstring(result).iter("DrumCell")]
    assert s0 == s1, "sample order changed"
    # everything outside the device blocks is byte-identical
    strip = lambda x, tag: re.sub(
        r"<AbletonDevicePreset\b[^>]*>\s*<OverwriteProtectionNumber[^>]*/>\s*<Device>\s*<%s\b.*?</AbletonDevicePreset>" % tag,
        "<DEV/>", x, flags=re.S)
    assert strip(src_xml, "OriginalSimpler") == strip(result, "DrumCell"), "text outside pads' devices changed"
    return before


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kit", type=Path)
    ap.add_argument("--donor", type=Path, default=DEFAULT_DONOR)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    out = a.out or a.kit.with_name(f"{a.kit.stem} (DrumCell).adg")
    src, donor = text(decode_adg(a.kit)), text(decode_adg(a.donor))
    result, report = convert(src, donor)
    layout = verify(src, result)
    encode_adg(result, out)
    assert text(decode_adg(out)) == result
    for (note, name, _), (sample, vol, vel, length) in zip(layout, report):
        trim = f"  length {length*100:.1f}%" if length is not None else ""
        print(f"  note {note:>3}  {name or '-':<6} {sample:<30} vol {float(vol):6.1f} dB  vel>vol {float(vel)*100:3.0f}%{trim}")
    print(f"{len(report)} pads -> {out}")


if __name__ == "__main__":
    main()
