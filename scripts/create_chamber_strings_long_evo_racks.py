#!/usr/bin/env python3
"""
Create Chamber Strings LONG dynamics racks — one Instrument Rack per sustained
articulation holding all six dynamic layers as chains, crossfaded by the user's
Evo Grid Selector Max device.

Donor: the hand-built "Long CS.adg" in the Looping Presets tree. Per the repo's
donor rule the structure is never reconstructed — this script replaces only each
chain's Sampler zone content and the two name fields, and leaves the Max
devices, macros, mixer, chain zones and everything else byte-identical.

## What the donor is

An Instrument Rack of 6 InstrumentBranchPresets. Each chain is one dynamic
layer: a MultiSampler holding that layer's Close/Far combined zone map (from
`Sampler Instruments/Long Close-Far/`, built by
create_chamber_strings_long_samplers.py) followed by an instance of
`Evo-Grid-Selector.amxd` from the User Library.

Every chain's BranchSelectorRange is 0-0, so the chain selector does nothing —
the Max device does the crossfading, driven by the "Crossfade X" / "Crossfade Y"
macros. The rack carries NO KeyMidi mappings at all, which is the Looping
convention: the Looping surface drives parameters by macro *name*, and a
macro-held parameter is disabled in Live.

Chain N's Max device is carried across to chain N untouched, with one deliberate
exception: `Wrap` is forced off everywhere. The donor was saved with it on in
chains 1/3/5 and off in 2/4/6, which was not intended. `--fix-donor` corrects the
donor in place too, backing it up first.

## Why string-level edits

The donor is a Live-saved file carrying a large embedded Max payload.
Re-serialising a Live 12 file through ElementTree produces something that parses
but will not load (see the unmap module in CLAUDE.md), so the replacement splices
text: the six `<SampleParts>` spans and the seven `<UserName>` values, nothing
else. ElementTree is used only to read and to verify the result.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_chamber_strings_long_evo_racks.py --plan
    python3 scripts/create_chamber_strings_long_evo_racks.py
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg

USER_LIBRARY = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library"
)
RACK_DIR = (USER_LIBRARY / "Looping Presets/Instruments/Ableton/Inst/String"
            / "Long/Chamber Strings")
DONOR = RACK_DIR / "Long CS.adg"
BACKUP_DIR = Path("/Users/Shared/Music/_backups/Chamber Strings Long racks")
ADV_DIR = Path(
    "/Users/Shared/Music/Soundbanks/Ben Multisamples/Spitfire/Chamber Strings"
    "/Sampler Instruments/Long Close-Far"
)

# rack file name -> the label used by the combined .adv file names.
# "Long CS" is the donor itself; it is rebuilt only under --verify-donor.
RACKS = {
    "Long": "",
    "Long CS": "Con Sordino",
    "Long Flautando": "Flautando",
    "Long Harmonics": "Harmonics",
    "Long Sul Pont": "Sul Pont",
    "Long Sul Tasto": "Sul Tasto",
    "Long Tremolo": "Tremolo",
}
DYN_COUNT = 6
WRAP_PARAM = "Wrap"


def adv_name(label: str, dyn: int) -> str:
    return " ".join(p for p in ("CS", "Long", label, f"dyn{dyn}") if p)


def sample_parts_text(adv: Path) -> str:
    """The <SampleParts>...</SampleParts> block of a single-Sampler .adv."""
    xml = decode_adg(adv)
    start = xml.index("<SampleParts>")
    end = xml.index("</SampleParts>", start) + len("</SampleParts>")
    return xml[start:end]


def set_wrap_off(xml: str):
    """Force the Evo Grid Selector's `Wrap` enum off in every chain.

    The donor was saved with Wrap on in chains 1/3/5 and off in 2/4/6, which was
    not intended — it should be off everywhere. Each `MxDEnumParameter` block is
    matched by name and carries exactly one `Manual`, so the edit is anchored
    inside that block and cannot reach any other parameter.
    """
    out, cursor, changed = [], 0, 0
    for m in re.finditer(r"<MxDEnumParameter[ >]", xml):
        end = xml.index("</MxDEnumParameter>", m.start())
        block = xml[m.start():end]
        name = re.search(r'<Name Value="([^"]*)" />', block)
        manuals = re.findall(r'<Manual Value="([^"]*)" />', block)
        if name is None or name.group(1) != WRAP_PARAM or len(manuals) != 1:
            continue
        if manuals[0] == "0":
            continue
        fixed, n = re.subn(r'(<Manual Value=")[^"]*(" />)', r"\g<1>0\g<2>", block, count=1)
        if n != 1:
            raise SystemExit("could not rewrite a Wrap parameter block")
        out.append(xml[cursor:m.start()])
        out.append(fixed)
        cursor = end
        changed += 1
    out.append(xml[cursor:])
    return "".join(out), changed


def donor_spans(xml: str):
    """(rack_username_span, [(sampler_username_span, sample_parts_span)] * 6).

    Spans are (start, end) over the value text or the whole element, taken in
    document order so a chain's name always precedes its own zone map.
    """
    names = [(m.start(1), m.end(1), m.group(1))
             for m in re.finditer(r'<UserName Value="([^"]*)" />', xml)
             if m.group(1)]
    parts = [(m.start(), xml.index("</SampleParts>", m.start()) + len("</SampleParts>"))
             for m in re.finditer(r"<SampleParts>", xml)]

    if len(names) != DYN_COUNT + 1:
        raise SystemExit(f"donor has {len(names)} named UserName elements, expected 7")
    if len(parts) != DYN_COUNT:
        raise SystemExit(f"donor has {len(parts)} SampleParts blocks, expected 6")

    rack_name = (names[0][0], names[0][1])
    chains = []
    for i in range(DYN_COUNT):
        nstart, nend, _ = names[i + 1]
        pstart, pend = parts[i]
        if not nstart < pstart:
            raise SystemExit(f"chain {i}: name at {nstart} does not precede zones at {pstart}")
        chains.append(((nstart, nend), (pstart, pend)))
    return rack_name, chains


def build(rack_name: str, label: str, donor_xml: str, spans) -> str:
    rack_span, chain_spans = spans
    pieces, cursor = [], 0

    pieces.append(donor_xml[cursor:rack_span[0]])
    pieces.append(rack_name)
    cursor = rack_span[1]

    for dyn in range(1, DYN_COUNT + 1):
        (nstart, nend), (pstart, pend) = chain_spans[dyn - 1]
        adv = ADV_DIR / f"{adv_name(label, dyn)}.adv"
        if not adv.exists():
            raise SystemExit(f"missing source patch: {adv}")
        pieces.append(donor_xml[cursor:nstart])
        pieces.append(adv.stem)
        pieces.append(donor_xml[nend:pstart])
        pieces.append(sample_parts_text(adv))
        cursor = pend

    pieces.append(donor_xml[cursor:])
    return "".join(pieces)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="report without writing")
    ap.add_argument("--verify-donor", action="store_true",
                    help="also rebuild Long CS, to check the splice reproduces the donor")
    ap.add_argument("--scratch", default=".",
                    help="where --verify-donor writes its rebuilt copy")
    ap.add_argument("--fix-donor", action="store_true",
                    help="also turn Wrap off in the donor itself, backing it up first")
    args = ap.parse_args()

    if not DONOR.exists():
        raise SystemExit(f"Donor not found: {DONOR}")
    donor_xml = decode_adg(DONOR)
    spans = donor_spans(donor_xml)
    print(f"Donor: {DONOR.name}  ({len(donor_xml):,} chars, "
          f"{DONOR.stat().st_size:,} bytes packed)")
    print(f"  rack name span {spans[0]}, {len(spans[1])} chains")

    if args.fix_donor:
        fixed, n = set_wrap_off(donor_xml)
        if n:
            backup = BACKUP_DIR / f"Long CS (Wrap alternating, pre-fix).adg"
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DONOR, backup)
            if not args.plan:
                encode_adg(fixed, DONOR)
                print(f"  donor: Wrap turned off in {n} chains "
                      f"(backup: {backup})")
            donor_xml = fixed
            spans = donor_spans(donor_xml)  # offsets move if the edit ever changes length
        else:
            print("  donor: Wrap already off in every chain")

    targets = dict(RACKS)
    if not args.verify_donor:
        targets.pop("Long CS")

    for rack_name, label in targets.items():
        advs = [ADV_DIR / f"{adv_name(label, d)}.adv" for d in range(1, DYN_COUNT + 1)]
        missing = [a.name for a in advs if not a.exists()]
        if missing:
            raise SystemExit(f"{rack_name}: missing {missing}")

        out_xml = build(rack_name, label, donor_xml, spans)
        out_xml, wrapped = set_wrap_off(out_xml)
        zones = out_xml.count("<MultiSamplePart ")
        if args.plan:
            print(f"  {rack_name + '.adg':<26} <- {advs[0].stem} .. {advs[-1].stem}"
                  f"   {zones} zones, Wrap turned off in {wrapped} chains")
            continue

        out = RACK_DIR / f"{rack_name}.adg"
        if args.verify_donor and rack_name == "Long CS":
            out = Path(args.scratch) / "Long CS (rebuilt).adg"
        encode_adg(out_xml, out)
        print(f"  {out.name:<26} {zones} zones, {out.stat().st_size:,} bytes, "
              f"Wrap off in all 6 ({wrapped} corrected)")


if __name__ == "__main__":
    main()
