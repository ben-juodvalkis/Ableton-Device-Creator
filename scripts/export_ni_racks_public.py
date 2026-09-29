#!/usr/bin/env python3
"""
Export the NI Expansions drum racks as a shareable Live Project: racks only, no
samples, and nothing from this machine but the sample references themselves.

The recipient opens the project's set, runs File Manager > Manage Project, and
points the missing-file search at their own NI Expansions folder; Live relinks
every rack in the project folder by file name (and size). So the sample
references are left exactly as they are - name and OriginalFileSize are what
the search matches on - and only provenance is cleared:

- every pad chain's <SourceContext> (the "dragged in from" record) points at
  this machine's Samples Organized/Atmospheres/Ambient files - an unrelated
  library - and its BrowserContentPath. Reset to <Value />, the form Live
  itself writes for an empty one (it appears in these same files).
- every <FilePresetRef> (the rack's own PresetRef and LastPresetRef) points
  into the Looping repo. Its RelativePath and Path are blanked, the same shape
  as the empty FileRefs Live writes elsewhere in these files.

Measured 2026-09-29 across all 1656 racks: those are the only path-bearing
fields besides the 52992 sample refs. The verifier re-checks that on every
file rather than trusting the inventory.

Project layout (Live 12 leaves "Ableton Project Info" empty - measured on
every project on this machine):

    Drum Racks for NI Expansions Project/
        Ableton Project Info/
        Drum Racks for NI Expansions.als   <- Live's own factory DefaultLiveSet, copied untouched
        README.txt                         <- disclaimer, required expansions, relink steps
        Drum/Acoustic|Analog|Digital/<Expansion>/<Rack>.adg
        Perc/Acoustic|Analog|Digital/<Expansion>/<Rack>.adg

Edits are string-level on the decoded XML; ElementTree only reads.

Usage:
    python3 scripts/export_ni_racks_public.py              # build into the staging dir
    python3 scripts/export_ni_racks_public.py --out DIR    # build into DIR (must not exist)
    python3 scripts/export_ni_racks_public.py --plan       # count only, write nothing
"""

import argparse
import collections
import gzip
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ableton_device_creator.core import encode_adg  # noqa: E402

SIDEBAR = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Sidebar"
)
# source folder -> folder inside the project. "NI" is dropped from folder
# names: the project says who it is for, it should not look like NI's product.
SOURCES = {
    "Drum/NI Acoustic": "Drum/Acoustic",
    "Drum/NI Analog": "Drum/Analog",
    "Drum/NI Digital": "Drum/Digital",
    "Perc/NI Expansions/Acoustic": "Perc/Acoustic",
    "Perc/NI Expansions/Analog": "Perc/Analog",
    "Perc/NI Expansions/Digital": "Perc/Digital",
}
PROJECT_NAME = "Drum Racks for NI Expansions"
DEFAULT_SET = Path(
    "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/"
    "Builtin/Templates/DefaultLiveSet.als"
)
DEFAULT_OUT = Path("/Users/Shared/Music/_staging") / f"{PROJECT_NAME} Project"
EXPANSIONS_MARKER = "/Native Instruments/Expansions/"

# Anything that would say where this machine keeps things. Sample Paths are
# exempt (they carry the NI expansion layout the relink needs) and are checked
# separately.
LEAK_PATTERNS = ["Samples Organized", "DevWork", "Looping", "userfolder:", "/Users/Music"]


def element_span(text, open_tag, close_tag, start):
    """(start, end) of the element opened at `start`, honouring nesting."""
    depth, i = 0, start
    pat = re.compile(re.escape(open_tag) + r"[\s>]|" + re.escape(close_tag))
    while True:
        m = pat.search(text, i)
        if m is None:
            raise ValueError(f"unbalanced {open_tag} at {start}")
        if m.group().startswith(close_tag):
            depth -= 1
            if depth == 0:
                return start, m.end()
        else:
            depth += 1
        i = m.end()


def clean_xml(xml):
    """Return (cleaned xml, counts)."""
    edits = []
    counts = collections.Counter()

    # <SourceContext> with content -> Live's empty form. Outermost only: a
    # nested one goes with its parent.
    i = 0
    while True:
        s = xml.find("<SourceContext>", i)
        if s < 0:
            break
        start, end = element_span(xml, "<SourceContext", "</SourceContext>", s)
        inner = xml[s + len("<SourceContext>"): end - len("</SourceContext>")]
        if inner.strip() != "<Value />":
            line_start = xml.rfind("\n", 0, s) + 1
            indent = xml[line_start:s]
            empty = f"<SourceContext>\n{indent}\t<Value />\n{indent}</SourceContext>"
            edits.append((start, end, empty))
            counts["source_context"] += 1
        i = end

    # <FilePresetRef>: blank the FileRef's RelativePath and Path.
    for m in re.finditer(r"<FilePresetRef Id=\"\d+\">", xml):
        start, end = element_span(xml, "<FilePresetRef", "</FilePresetRef>", m.start())
        block = xml[start:end]
        new = re.sub(r'(<RelativePath Value=")[^"]*(")', r"\1\2", block)
        new = re.sub(r'(<Path Value=")[^"]*(")', r"\1\2", new)
        if new != block:
            edits.append((start, end, new))
            counts["preset_ref"] += 1

    edits.sort()
    for (a0, a1, _), (b0, _, _) in zip(edits, edits[1:]):
        if b0 < a1:
            raise ValueError("overlapping edits")
    out, pos = [], 0
    for s, e, t in edits:
        out.append(xml[pos:s])
        out.append(t)
        pos = e
    out.append(xml[pos:])
    return "".join(out), counts


def sample_refs(root):
    """[(Path, RelativePath, OriginalFileSize, OriginalCrc)] for every SampleRef, in order."""
    refs = []
    for sr in root.iter("SampleRef"):
        fr = sr.find("FileRef")
        refs.append(tuple(fr.find(t).get("Value") for t in
                          ("Path", "RelativePath", "OriginalFileSize", "OriginalCrc")))
    return refs


def stripped_signature(root):
    """Every element outside SourceContext / FilePresetRef, as (tag, attrs) in order."""
    sig = []

    def walk(e):
        for c in e:
            if c.tag in ("SourceContext", "FilePresetRef"):
                sig.append((c.tag, "<skipped>"))
                continue
            sig.append((c.tag, tuple(sorted(c.attrib.items())), (c.text or "").strip()))
            walk(c)
    walk(root)
    return sig


def verify(original, cleaned):
    """Raise if the cleaned rack differs from the original beyond the intended fields."""
    r0 = ET.fromstring(original)
    r1 = ET.fromstring(cleaned)
    if sample_refs(r0) != sample_refs(r1):
        raise AssertionError("sample references changed")
    if stripped_signature(r0) != stripped_signature(r1):
        raise AssertionError("content outside SourceContext/FilePresetRef changed")
    sample_paths = {p for p, *_ in sample_refs(r1)}
    for path_el in r1.iter("Path"):
        v = path_el.get("Value")
        if v and v not in sample_paths:
            raise AssertionError(f"non-sample path survived: {v}")
    for pat in LEAK_PATTERNS:
        if pat in cleaned:
            raise AssertionError(f"leak pattern survived: {pat}")
    for p in sample_paths:
        if EXPANSIONS_MARKER not in p:
            raise AssertionError(f"sample outside NI Expansions: {p}")


def expansion_of(path):
    return path.split(EXPANSIONS_MARKER, 1)[1].split("/", 1)[0]


def readme(needs, n_racks, n_pads):
    libs = sorted(needs)
    lines = [
        f"{PROJECT_NAME}",
        "=" * len(PROJECT_NAME),
        "",
        f"{n_racks} Ableton Live 12 Drum Racks ({n_pads} pads) built on the sample content",
        "of Native Instruments Maschine Expansions. No audio is included: every pad",
        "references a sample from an expansion you must own and have installed.",
        "",
        "Not affiliated with or endorsed by Native Instruments. Native Instruments,",
        "Maschine and the expansion names are trademarks of their respective owners",
        "and are used here only to say which content these racks need.",
        "",
        "Connecting the racks to your samples",
        "------------------------------------",
        "The racks point at the samples' location on the machine they were built on,",
        "so on yours they will start out missing. Live can find them all at once:",
        "",
        "1. Keep this folder together and open the .als set inside it.",
        "2. File > Manage Files, then Manage Project.",
        "3. Under missing files, choose Locate, set the search folder to the folder",
        "   that holds your NI Expansions (the one containing the '... Library'",
        "   folders), and start the search.",
        "4. When Live has found them, save. The racks in this project folder now",
        "   point at your copies.",
        "",
        "Then drag the Drum and Perc folders into your User Library, or add this",
        "project folder to Places in Live's browser.",
        "",
        f"Expansions used ({len(libs)})",
        "-" * len(f"Expansions used ({len(libs)})"),
        "Racks that draw on an expansion you don't own will have those pads silent.",
        "",
    ]
    width = max(len(l) for l in libs)
    for lib in libs:
        lines.append(f"  {lib.ljust(width)}  used by {needs[lib]} rack(s)")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--plan", action="store_true", help="count and verify only, write nothing")
    args = ap.parse_args()

    if not args.plan and args.out.exists():
        sys.exit(f"{args.out} already exists - remove it or pass another --out")
    if not DEFAULT_SET.exists():
        sys.exit(f"missing Live default set: {DEFAULT_SET}")

    totals = collections.Counter()
    needs = collections.Counter()
    missing_on_disk = set()
    failures = []
    jobs = []
    for src, dst in SOURCES.items():
        for f in sorted((SIDEBAR / src).rglob("*.adg")):
            jobs.append((f, Path(dst) / f.relative_to(SIDEBAR / src)))

    for f, rel in jobs:
        original = gzip.open(f).read().decode("utf-8")
        try:
            cleaned, counts = clean_xml(original)
            verify(original, cleaned)
        except (AssertionError, ValueError, ET.ParseError) as e:
            failures.append((rel, str(e)))
            continue
        refs = sample_refs(ET.fromstring(cleaned))
        totals.update(counts)
        totals["racks"] += 1
        totals["pads"] += len(refs)
        for lib in {expansion_of(p) for p, *_ in refs}:
            needs[lib] += 1
        for p, *_ in refs:
            if not Path(p).exists():
                missing_on_disk.add(p)
        if not args.plan:
            out = args.out / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            encode_adg(cleaned, out)

    print(f"racks {totals['racks']}  pads {totals['pads']}  "
          f"SourceContexts cleared {totals['source_context']}  "
          f"preset refs blanked {totals['preset_ref']}  expansions {len(needs)}")
    if missing_on_disk:
        print(f"WARNING: {len(missing_on_disk)} referenced samples are missing on this machine")
        for p in sorted(missing_on_disk)[:10]:
            print("   ", p)
    if failures:
        print(f"FAILED {len(failures)}:")
        for rel, e in failures[:20]:
            print(f"    {rel}: {e}")
        sys.exit(1)
    if args.plan:
        return

    (args.out / "Ableton Project Info").mkdir()
    shutil.copyfile(DEFAULT_SET, args.out / f"{PROJECT_NAME}.als")
    (args.out / "README.txt").write_text(readme(needs, totals["racks"], totals["pads"]))
    archive = shutil.make_archive(str(args.out), "zip", args.out.parent, args.out.name)
    print(f"wrote {args.out}")
    print(f"zipped {archive}")


if __name__ == "__main__":
    main()
