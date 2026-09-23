#!/usr/bin/env python3
"""
Combine the 100 one-per-borough racks in "5 Boroughs" into 50 two-kit racks,
laid out like the rest of Electro Acoustic ("Croydon + Crunk my Sub").

Built from the *library* racks, not from source: since create_boroughs_racks.py
wrote them, every Electro Acoustic rack has been through the Prod macro batch
edit, `unmap` and `hide-macros`, so a fresh donor build would undo all three.
Instead:

- Donor = one of the library's own "2 Electro Acoustic" pair racks. All 37 are
  byte-identical apart from each pad's <SampleRef> block and pad <Name>
  (measured 2026-09-23), and their top-bank pads (92..81) are identical to the
  Boroughs racks' pads on the same terms. So the donor already carries both
  halves exactly as the pipeline left them.
- Each output pad is the donor's pad at that note with only its <SampleRef>
  block and <Name> swapped for the borough pad's: kit A's slot at note n goes to
  n, kit B's slot at n goes to n-16 (76..65), the same offsets as every other
  pair rack. A slot a borough never exported leaves that pad out, as before.
- Boroughs pair alphabetically, as the Hybrid racks do; 100 is even, so there
  is no solo rack.

Edits are string-level on the decoded XML (ElementTree only reads), and each
result is verified before it is written: text outside <BranchPresets> is
byte-identical to the donor, every pad matches its donor pad once SampleRef and
Name are set aside, and every SampleRef is its source pad's, verbatim.

Usage:
    python3 scripts/pair_boroughs_racks.py --out DIR          # build into DIR
    python3 scripts/pair_boroughs_racks.py --plan             # print plan only
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg

EA_ROOT = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Ableton/Drum/Electro Acoustic"
)
BOROUGHS_DIR = EA_ROOT / "5 Boroughs"
DONOR_PATH = EA_ROOT / "2 Electro Acoustic" / "EMI Crush - 606 + 808.adg"

BANK_OFFSET = 16  # kit B sits 16 semitones below kit A

BRANCH_PRESETS = re.compile(r"(<BranchPresets>)(.*?)(\n\t*</BranchPresets>)", re.S)
PAD = re.compile(r"\n\t*<DrumBranchPreset Id=\"\d+\">.*?</DrumBranchPreset>", re.S)
SAMPLE_REF = re.compile(r"<SampleRef Id=\"\d+\">.*?</SampleRef>", re.S)
PAD_NAME = re.compile(r"(<DrumBranchPreset Id=\"\d+\">\s*<Name Value=\")([^\"]*)(\")")
RECEIVING_NOTE = re.compile(r"<ReceivingNote Value=\"(\d+)\"")


def read_text(path: Path) -> str:
    xml = decode_adg(path)
    return xml.decode("utf-8") if isinstance(xml, bytes) else xml


def split_pads(text: str):
    """(span of the BranchPresets body, {note: pad text}, [notes in text order])."""
    m = BRANCH_PRESETS.search(text)
    if m is None:
        raise ValueError("no <BranchPresets>")
    if BRANCH_PRESETS.search(text, m.end()):
        raise ValueError("more than one <BranchPresets>; not a flat DrumCell rack")
    body = m.group(2)
    pads, order = {}, []
    for pm in PAD.finditer(body):
        pad = pm.group(0)
        notes = RECEIVING_NOTE.findall(pad)
        if len(notes) != 1 or len(SAMPLE_REF.findall(pad)) != 1:
            raise ValueError("pad is not one DrumCell with one sample")
        note = int(notes[0])
        pads[note] = pad
        order.append(note)
    if "".join(pads[n] for n in order) != body:
        raise ValueError("BranchPresets holds something other than pads")
    return m.span(2), pads, order


def skeleton(pad: str) -> str:
    """A pad with its sample and name set aside, for structural comparison."""
    return PAD_NAME.sub(r"\1\3", SAMPLE_REF.sub("<SampleRef/>", pad))


def transplant(donor_pad: str, source_pad: str) -> str:
    """The donor pad carrying the source pad's sample and name."""
    sample = SAMPLE_REF.search(source_pad).group(0)
    name = PAD_NAME.search(source_pad).group(2)
    out = SAMPLE_REF.sub(lambda _: sample, donor_pad, count=1)
    return PAD_NAME.sub(lambda m: m.group(1) + name + m.group(3), out, count=1)


def build_pair(donor: str, a: str, b: str) -> str:
    span, donor_pads, order = split_pads(donor)
    _, a_pads, _ = split_pads(a)
    _, b_pads, _ = split_pads(b)

    for label, pads in (("A", a_pads), ("B", b_pads)):
        for note, pad in pads.items():
            if skeleton(pad) != skeleton(donor_pads[note]):
                raise ValueError(f"kit {label} pad {note} differs from the donor beyond sample/name")

    sources = {n: a_pads[n] for n in a_pads}
    sources.update({n - BANK_OFFSET: p for n, p in b_pads.items()})
    missing = set(sources) - set(donor_pads)
    if missing:
        raise ValueError(f"no donor pad at notes {sorted(missing)}")

    body = "".join(transplant(donor_pads[n], sources[n]) for n in order if n in sources)
    return donor[:span[0]] + body + donor[span[1]:]


def verify_pair(donor: str, a: str, b: str, result: str) -> int:
    """Check the result against its inputs; returns the pad count."""
    ET.fromstring(result)
    d_span, d_pads, _ = split_pads(donor)
    r_span, r_pads, _ = split_pads(result)
    _, a_pads, _ = split_pads(a)
    _, b_pads, _ = split_pads(b)

    assert donor[:d_span[0]] == result[:r_span[0]], "text before pads changed"
    assert donor[d_span[1]:] == result[r_span[1]:], "text after pads changed"

    expected = {n: p for n, p in a_pads.items()}
    expected.update({n - BANK_OFFSET: p for n, p in b_pads.items()})
    assert set(r_pads) == set(expected), "pad notes differ from the two kits"
    for note, pad in r_pads.items():
        src = expected[note]
        assert skeleton(pad) == skeleton(d_pads[note]), f"pad {note} structure moved"
        assert SAMPLE_REF.search(pad).group(0) == SAMPLE_REF.search(src).group(0), \
            f"pad {note} sample is not its source's"
        assert PAD_NAME.search(pad).group(2) == PAD_NAME.search(src).group(2), \
            f"pad {note} name is not its source's"
    return len(r_pads)


def plan():
    racks = sorted(BOROUGHS_DIR.glob("*.adg"), key=lambda p: p.stem.lower())
    if len(racks) % 2:
        raise SystemExit(f"{len(racks)} borough racks; expected an even number")
    return [(racks[i], racks[i + 1]) for i in range(0, len(racks), 2)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, help="directory to write the paired racks into")
    ap.add_argument("--plan", action="store_true", help="print the pairing only")
    args = ap.parse_args()
    if not args.plan and not args.out:
        ap.error("--out or --plan is required")

    pairs = plan()
    donor = read_text(DONOR_PATH)
    print(f"{len(pairs) * 2} boroughs -> {len(pairs)} racks  (donor: {DONOR_PATH.name})\n")

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
    total = 0
    for pa, pb in pairs:
        name = f"{pa.stem} + {pb.stem}"
        a, b = read_text(pa), read_text(pb)
        result = build_pair(donor, a, b)
        pads = verify_pair(donor, a, b, result)
        total += pads
        if args.out:
            encode_adg(result, args.out / f"{name}.adg")
        print(f"  {name:<44} {pads} pads")
    print(f"\n{len(pairs)} racks, {total} pads, all verified"
          + ("" if args.out else " (nothing written)"))


if __name__ == "__main__":
    main()
