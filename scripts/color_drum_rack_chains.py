#!/usr/bin/env python3
"""Colour a Drum Rack's pad chains by drum type.

Mirrors the colour scheme Ableton's own NI Acoustic kits use (measured across
all 515 racks under ``Drum/Prod/NI Acoustic`` on 2026-09-08): every pad chain
gets the colour of the sound sitting on it, so a kit reads at a glance -- kicks
one colour, snares another, hats split open/closed, and so on.

Two fields per pad chain, both owned *directly* by a ``DrumBranchPreset``:

* ``DocumentColorIndex`` -- the colour itself.
* ``AutoColored`` -- must be ``false`` or Live picks its own colour and ignores
  the stored index entirely.  This is what makes a rack look uniformly coloured
  no matter what is written in the file, and it is why the racks this script
  targets looked mono-coloured in the first place.  Live clears the same flag
  when you assign a chain colour by hand.

Nested ``InstrumentBranchPreset`` / ``AudioEffectBranchPreset`` chains inside a
pad keep their own colours, and nothing else in the file moves.

Usage::

    PYTHONPATH=src python3 scripts/color_drum_rack_chains.py <dir-or-file> --plan
    PYTHONPATH=src python3 scripts/color_drum_rack_chains.py <dir-or-file> --apply
    PYTHONPATH=src python3 scripts/color_drum_rack_chains.py <dir> --apply --only-mono

``--only-mono`` restricts the run to racks whose pads currently all share one
colour, i.e. the ones that carry no information yet.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg  # noqa: E402


# --------------------------------------------------------------------------
# Colour scheme
# --------------------------------------------------------------------------
# Live palette indices, taken from the dominant choice per drum type across the
# NI Acoustic library (see module docstring).  Counts from that survey:
#   kick 2205/2270 -> 54   snare 1978 + clap 1105 -> 4   tom 559 -> 19
#   closed hat 2677 -> 29  open hat 1092 -> 30   cymbal 575 -> 69
#   shaker 711 -> 26       perc 1357 -> 13       tonal/other 875 -> 0
COLORS = {
    "kick": 54,
    "snare": 4,
    "tom": 19,
    "hihat_closed": 29,
    "hihat_open": 30,
    "cymbal": 69,
    "shaker": 26,
    "perc": 13,
    "other": 0,
}

# Ordered: the first pattern that matches wins.  A few narrow guards come first
# so they beat the broader rule that would otherwise swallow them.
RULES: list[tuple[str, str]] = [
    # "Cowbell" must not be taken by the cymbal rule's \bbell\b
    ("perc", r"\bcow ?bell\b"),
    ("kick", r"\bkick\b|\bbd\b|bass ?drum|\bbeater\b|drum case"),
    ("snare", r"\bsnare\b|\brim\b|rimshot|side ?stick|\bclap\b|\bsnap\b|"
              r"\b(centre|center|edge) (un)?damped\b"),
    ("tom", r"\btom\b|floor ?tom|rack ?tom|\broto\b"),
    ("hihat", r"\bhi ?hat\b|\bhh\b|\bhat\b|\bpedal (shut|open)\b|"
              r"\bfully closed\b|\bopen (quarter|half|three ?quarters)\b|"
              r"\b(closed|open)( edge)?$|\bclosed\b"),
    ("cymbal", r"\bcrash\b|\bride\b|\bchina\b|\bsplash\b|\bcymbal\b|\bgong\b|\bbell\b"),
    ("shaker", r"\bshaker\b|\bmaraca|\bcabasa\b"),
    ("perc", r"\btamb|\bconga\b|\bbongo\b|\bclave\b|\bwood\b|\bblock\b|\bguiro\b|"
             r"\btriangle\b|\bclapstick\b|percussion|\bperc\b|\bcuica\b|\bagogo\b|"
             r"\bdjembe\b|\bcajon\b|\btimbale|\bsurdo\b|\bhand ?drum\b"),
    ("other", r"\bbass\b|\bpiano\b|\bkeys\b|\bwurli\b|\bchord\b|\bpluck\b|\bsynth\b|"
              r"\bvox\b|\bvocal\b|\bsilent\b|\butility\b"),
]

# A hat is open only when the name says so.  Everything else -- closed, tight,
# loose, pedal, foot chick, or a bare "Hihat" -- reads as closed.  "Fully
# Closed" is excluded so its "closed" is not overridden by a stray "open".
_OPEN_HAT = re.compile(r"\bopen\b")
_FULLY_CLOSED = re.compile(r"\bfully closed\b")

_COMPILED = [(kind, re.compile(pat)) for kind, pat in RULES]

_AUDIO_EXT = (".wav", ".aif", ".aiff", ".flac", ".mp3")


def _normalize(path: str) -> str:
    """Lower-case a sample path and flatten its separators for matching."""
    stem = path.rsplit(".", 1)[0]
    flat = stem.lower().replace("_", " ").replace("-", " ").replace("/", " / ")
    return re.sub(r"\s+", " ", flat)


def classify_sample(path: str) -> str | None:
    """Return the drum type for a sample path, or None if nothing matches."""
    text = _normalize(path)
    for kind, pattern in _COMPILED:
        if pattern.search(text):
            if kind != "hihat":
                return kind
            if _OPEN_HAT.search(text) and not _FULLY_CLOSED.search(text):
                return "hihat_open"
            return "hihat_closed"
    return None


# --------------------------------------------------------------------------
# Reading a rack
# --------------------------------------------------------------------------
def _pad_label(branch: ET.Element) -> str:
    """Best identifying string for a pad: its sample, else its preset name."""
    presets = []
    for ref in branch.iter("FileRef"):
        rel = ref.find("RelativePath")
        abs_ = ref.find("Path")
        value = (rel.get("Value") if rel is not None else "") or \
                (abs_.get("Value") if abs_ is not None else "")
        if not value:
            continue
        low = value.lower()
        if low.endswith(_AUDIO_EXT):
            return value
        if low.endswith((".adv", ".adg")):
            presets.append(value.rsplit("/", 1)[-1])
    if presets:
        return presets[0]
    name = branch.find("Name")
    return name.get("Value") if name is not None else ""


@dataclass
class PadPlan:
    """One pad's before/after colour and why."""
    occurrence: int          # index into the file's DocumentColorIndex sequence
    note: int | None
    old: int
    new: int
    kind: str | None
    label: str
    auto_occurrence: int | None = None   # index into the AutoColored sequence
    auto_old: str | None = None          # "true"/"false", None if absent

    @property
    def needs_color(self) -> bool:
        return self.new != self.old

    @property
    def needs_auto_off(self) -> bool:
        return self.auto_occurrence is not None and self.auto_old == "true"

    @property
    def changed(self) -> bool:
        return self.needs_color or self.needs_auto_off


@dataclass
class RackPlan:
    """Everything decided for one rack, before any bytes are written."""
    pads: list[PadPlan] = field(default_factory=list)
    unclassified: list[PadPlan] = field(default_factory=list)

    @property
    def is_uncoded(self) -> bool:
        """True when the rack's pad colours carry no information yet.

        Either every pad is on ``AutoColored`` (Live picks the colour, so the
        stored indices are ignored) or they all share one colour.
        """
        return all(p.auto_old == "true" for p in self.pads) or \
            len({p.old for p in self.pads}) <= 1

    @property
    def changes(self) -> list[PadPlan]:
        return [p for p in self.pads if p.changed]


def plan_rack(xml: str) -> RackPlan:
    """Decide each pad chain's new colour.  Reads only -- writes nothing."""
    root = ET.fromstring(xml)
    # Document order of every element of each kind, so a pad's element can be
    # addressed by its position in the file's text as well as in the tree.
    order = {id(e): i for i, e in enumerate(root.iter("DocumentColorIndex"))}
    auto_order = {id(e): i for i, e in enumerate(root.iter("AutoColored"))}

    plan = RackPlan()
    for branch in root.iter("DrumBranchPreset"):
        color_el = branch.find("DocumentColorIndex")   # direct child only
        if color_el is None:
            continue
        auto_el = branch.find("AutoColored")
        note_el = branch.find(".//ZoneSettings/ReceivingNote")
        label = _pad_label(branch)
        kind = classify_sample(label)
        old = int(color_el.get("Value"))
        pad = PadPlan(
            occurrence=order[id(color_el)],
            note=int(note_el.get("Value")) if note_el is not None else None,
            old=old,
            new=COLORS.get(kind, old),
            kind=kind,
            label=label,
            auto_occurrence=auto_order[id(auto_el)] if auto_el is not None else None,
            auto_old=auto_el.get("Value") if auto_el is not None else None,
        )
        plan.pads.append(pad)
        if kind is None:
            plan.unclassified.append(pad)
    return plan


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------
_COLOR_RE = re.compile(r'<DocumentColorIndex Value="(-?\d+)" />')
_AUTO_RE = re.compile(r'<AutoColored Value="(\w+)" />')


def _rewrite(xml: str, pattern: re.Pattern, tag: str,
             wanted: dict[int, tuple[str, str]]) -> str:
    """Replace the n-th occurrences of ``pattern`` named in ``wanted``.

    ``wanted`` maps occurrence index -> (expected old value, new value); the
    expected value is checked so a shifted index fails loudly instead of
    silently editing the wrong element.
    """
    if not wanted:
        return xml
    out, cursor = [], 0
    for i, match in enumerate(pattern.finditer(xml)):
        entry = wanted.get(i)
        if entry is None:
            continue
        old, new = entry
        if match.group(1) != old:
            raise RuntimeError(f"{tag} #{i}: expected {old!r}, found {match.group(1)!r}")
        out.append(xml[cursor:match.start()])
        out.append(f'<{tag} Value="{new}" />')
        cursor = match.end()
    out.append(xml[cursor:])
    return "".join(out)


def apply_plan(xml: str, plan: RackPlan) -> str:
    """Rewrite the planned pad colours in the raw text.

    String-level on purpose: a Live 12 file re-serialised through ElementTree
    parses but will not load, so the tree is used for decisions only.
    """
    root = ET.fromstring(xml)
    if len(_COLOR_RE.findall(xml)) != len(list(root.iter("DocumentColorIndex"))) or \
       len(_AUTO_RE.findall(xml)) != len(list(root.iter("AutoColored"))):
        raise RuntimeError("text/tree element counts disagree")

    result = _rewrite(
        xml, _COLOR_RE, "DocumentColorIndex",
        {p.occurrence: (str(p.old), str(p.new)) for p in plan.pads if p.needs_color},
    )
    return _rewrite(
        result, _AUTO_RE, "AutoColored",
        {p.auto_occurrence: ("true", "false") for p in plan.pads if p.needs_auto_off},
    )


def verify(original: str, result: str, plan: RackPlan) -> None:
    """Confirm the result differs from the original in exactly the planned way."""
    ET.fromstring(result)   # must still parse

    for pattern, tag, wanted in (
        (_COLOR_RE, "DocumentColorIndex",
         {p.occurrence: str(p.new) for p in plan.pads if p.needs_color}),
        (_AUTO_RE, "AutoColored",
         {p.auto_occurrence: "false" for p in plan.pads if p.needs_auto_off}),
    ):
        before, after = pattern.findall(original), pattern.findall(result)
        if len(before) != len(after):
            raise RuntimeError(f"{tag} element count changed")
        expected = list(before)
        for index, value in wanted.items():
            expected[index] = value
        if after != expected:
            raise RuntimeError(f"{tag} values are not the planned ones")

    # Every byte outside those two fields' values must be untouched.
    def blank(text: str) -> str:
        text = _COLOR_RE.sub("<DocumentColorIndex />", text)
        return _AUTO_RE.sub("<AutoColored />", text)

    if blank(original) != blank(result):
        raise RuntimeError("text outside the colour fields changed")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def iter_racks(target: Path):
    if target.is_file():
        yield target
    else:
        yield from sorted(target.rglob("*.adg"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", type=Path, help="a .adg file or a directory of them")
    ap.add_argument("--apply", action="store_true", help="write the changes")
    ap.add_argument("--plan", action="store_true", help="preview only (default)")
    ap.add_argument("--only-uncoded", "--only-mono", action="store_true",
                    dest="only_uncoded",
                    help="only racks that carry no pad-colour information yet "
                         "(auto-coloured pads, or all one colour)")
    ap.add_argument("--verbose", action="store_true", help="list every pad")
    args = ap.parse_args(argv)

    if not args.target.exists():
        ap.error(f"not found: {args.target}")

    touched = skipped = pads_changed = 0
    unclassified: list[tuple[str, PadPlan]] = []

    for path in iter_racks(args.target):
        xml = decode_adg(path)
        plan = plan_rack(xml)
        if not plan.pads:
            continue
        if args.only_uncoded and not plan.is_uncoded:
            skipped += 1
            continue

        unclassified += [(path.name, p) for p in plan.unclassified]
        changes = plan.changes
        if not changes:
            skipped += 1
            continue

        kinds = {}
        for pad in plan.pads:
            kinds.setdefault(pad.kind or "?", 0)
            kinds[pad.kind or "?"] += 1
        summary = ", ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
        auto_off = sum(1 for p in plan.pads if p.needs_auto_off)
        note = f", auto-colour off on {auto_off}" if auto_off else ""
        print(f"{path.name}: {len(changes)}/{len(plan.pads)} pads{note} -> {summary}")
        if args.verbose:
            for pad in plan.pads:
                arrow = (f"{pad.old:>3} -> {pad.new:<3}" if pad.needs_color
                         else f"{pad.old:>3}  (keep)")
                flag = "  auto->off" if pad.needs_auto_off else ""
                print(f"    note {str(pad.note):>3}  {arrow}{flag}  {pad.kind}"
                      f"  {pad.label.rsplit('/', 1)[-1]}")

        touched += 1
        pads_changed += len(changes)

        if args.apply:
            result = apply_plan(xml, plan)
            verify(xml, result, plan)
            tmp = path.with_suffix(".adc-tmp.adg")
            encode_adg(result, tmp)
            tmp.replace(path)

    print()
    print(f"{'wrote' if args.apply else 'would change'}: {touched} racks, "
          f"{pads_changed} pad chains  (unchanged/skipped: {skipped})")
    if unclassified:
        print(f"\nUNCLASSIFIED pads kept their existing colour ({len(unclassified)}):")
        for name, pad in unclassified:
            print(f"    {name}  note {pad.note}  {pad.label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
