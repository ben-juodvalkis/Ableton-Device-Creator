#!/usr/bin/env python3
"""
Put a drum rack's hi-hat pads in one choke group, so closing the hat cuts off an
open one ringing. Ben's reference is `~/Desktop/choke group.adg` (his Vintage
Ivory multi-mic rack): Hi-Hat Closed, Hi-Hat Pedal and Hi-Hat Open in group 1,
everything else - including the "Extra: Hi-hat - Brush ..." pad - left at 0.

Pads are chosen by name, per library (RULES). Only each matching pad's own
<ZoneSettings><ChokeGroup> is rewritten, string-level; every other pad goes back
to 0, so re-running is idempotent. The result is re-read and compared with the
original with every ChokeGroup blanked: anything else changed fails the rack.
Originals are copied to --backup first (default under
/Users/Shared/Music/_backups/).

    python3 scripts/set_choke_groups.py --rule abbey-road --dir ".../Sidebar/Drum/Abbey Road Multi-Mic" [--dry-run]
    python3 scripts/set_choke_groups.py --rule moonkits --dir ".../Sidebar/Drum/A Moonkits Lite"
"""

import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg

# rule -> pad-name regex for the hats that choke each other
RULES = {
    # curated Abbey Road racks (incl. multi-mic + Lite): role prefix on the pad name
    "abbey-road": r"^Hi-Hat (Closed|Pedal|Open):",
    # A Moonkits: Hat_closed / Hat_Medium / Hat_Open / Hat_Wide_Open (n)
    "moonkits": r"^Hat_(closed|Medium|Open|Wide_Open) \(\d+\)$",
}
PAD_RE = re.compile(r'<DrumBranchPreset Id="\d+">.*?</DrumBranchPreset>', re.S)
CHOKE_RE = re.compile(r'(<ZoneSettings>.*?<ChokeGroup Value=")(\d+)(" />)', re.S)
NAME_RE = re.compile(r'<DrumBranchPreset Id="\d+">\s*<Name Value="([^"]*)"')


def unescape(s: str) -> str:
    return s.replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def apply_chokes(xml: str, rule: str, group: int = 1):
    """Return (new xml, [names of choked pads]). Non-matching pads get 0."""
    pattern = re.compile(RULES[rule], re.I)
    choked, pieces, cursor = [], [], 0
    for m in PAD_RE.finditer(xml):
        pad = m.group(0)
        name = unescape(NAME_RE.match(pad).group(1))
        zs = list(CHOKE_RE.finditer(pad))
        if len(zs) != 1:
            raise ValueError(f"pad {name!r}: {len(zs)} ZoneSettings ChokeGroup fields, expected 1")
        value = group if pattern.search(name) else 0
        if value:
            choked.append(name)
        z = zs[0]
        pad = pad[:z.start(2)] + str(value) + pad[z.end(2):]
        pieces.append(xml[cursor:m.start()] + pad)
        cursor = m.end()
    pieces.append(xml[cursor:])
    return "".join(pieces), choked


def blank(xml: str) -> str:
    return re.sub(r'<ChokeGroup Value="\d+" />', "", xml)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, type=Path, help="folder of .adg drum racks (searched recursively)")
    ap.add_argument("--rule", required=True, choices=RULES)
    ap.add_argument("--group", type=int, default=1)
    ap.add_argument("--expect", type=int, default=None, help="fail a rack unless exactly this many pads choke")
    ap.add_argument("--backup", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    racks = sorted(args.dir.rglob("*.adg"))
    if not racks:
        raise SystemExit(f"no .adg under {args.dir}")
    backup = args.backup or Path("/Users/Shared/Music/_backups") / (
        f"{args.dir.name} before choke groups {datetime.date.today()}")
    failures, changed = [], 0
    for rack in racks:
        xml = decode_adg(rack)
        new, choked = apply_chokes(xml, args.rule, args.group)
        rel = rack.relative_to(args.dir)
        if args.expect is not None and len(choked) != args.expect:
            failures.append(f"{rel}: {len(choked)} hat pads matched, expected {args.expect}: {choked}")
            continue
        if blank(new) != blank(xml):
            failures.append(f"{rel}: changed outside ChokeGroup")
            continue
        print(f"{rel}: {len(choked)} pads -> group {args.group}: {', '.join(choked)}")
        if args.dry_run or new == xml:
            continue
        dest = backup / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(rack, dest)
        encode_adg(new, rack)
        check = decode_adg(rack)
        if check != new:
            failures.append(f"{rel}: re-read differs from what was written")
        changed += 1
    print(f"\n{len(racks)} racks, {changed} written" + (" (dry run)" if args.dry_run else f", originals in {backup}"))
    if failures:
        print("FAILURES:\n  " + "\n  ".join(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
