#!/usr/bin/env python3
"""
Create Abbey Road Pad Kits — a second, 32-pad-focused generation mode for
the Abbey Road Drummer library, for a 32-pad hardware controller.

Unlike create_abbey_road_kit.py (one pad per CSV articulation, however many
that is per kit — 58 to 94), this uses a FIXED 32-role template: the same
conceptual layout on every kit, mapped to notes 36-67 (the same 32-note
range this project's other 32-pad racks use):

- Notes 36-51 (16 pads) follow General MIDI drum-map positions where Abbey
  Road has a real equivalent (Kick=36, Side Stick=37, Snare=38, Hand
  Clap=39, Closed HH=42, Pedal HH=44, Open HH=46, Crash 1=49, Ride=51),
  with the GM tom slots (41/43/45/47/48/50) filled by cycling through
  whatever toms the kit actually has.
- Notes 52-67 (16 pads) are "wildcard" extras — the distinctive stuff
  worth having on hand (Woodblock, Stick Hit, a second Clap, Cowbell,
  Tambourine, Triangle, Bongo, extra cymbals/toms/snare/kick flavors).

Which specific CSV articulation fills a role is chosen per kit via a
keyword fallback chain, since exact wording varies ("Dampened" vs "Damp"
vs "Rubber Beater" for the same "closed kick" concept). Every one of the
32 pads is guaranteed to be filled for every kit — if a role's preferred
piece doesn't exist in a kit, a final pass fills the gap from whatever
unused material remains, so no pad stays empty even though which exact
sound lands on a "wildcard" pad can vary kit to kit.

Drum rolls are hard-excluded (ROLL_RE) everywhere — preferences, tom
cycling, and the final guaranteed-fill pass alike.

Reuses to_receiving_note_value(), find_articulation_samples(), and
piece_color() from create_abbey_road_kit.py — see that file's docstring
for why ReceivingNote needs the 128-n inversion.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_abbey_road_pad_kit.py
"""

import copy
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin
from create_abbey_road_kit import (
    LIBRARY_ROOT, MAPPING_CSV, DRUM_RACK_TEMPLATE, PAD_ROOT_NOTE,
    discover_kits, era_short_name, find_articulation_samples, piece_color, to_receiving_note_value,
)

OUTPUT_DIR = LIBRARY_ROOT / "Drum Racks" / "32-Pad"
FIRST_NOTE = 36  # C1 — same 32-note range (36-67) as this project's other 32-pad racks

ROLL_RE = re.compile(r"\broll\b", re.IGNORECASE)
TOM_RE = re.compile(r"^tom\s*\d+", re.IGNORECASE)

# Notes 36-51: General MIDI-ish. TOM means "next tom in the round-robin
# cycle" (see pick_tom_cycle) rather than a fixed preference chain.
PRIMARY_ROLES = [
    ("Kick",           r"^kick(?!\s*shell)",  [r"dampened", r"^damp$", r"rubber beater"]),
    ("Side Stick",     r"snare",              [r"sidestick"]),
    ("Snare",          r"snare",              [r"alternating"]),
    ("Hand Clap",      r"clap",               [r"^solo$"]),
    ("Snare (alt)",    r"snare",              [r"wires off"]),
    ("TOM",            None,                  []),
    ("Hi-Hat Closed",  r"hi.?hat",            [r"closed tip right.left alternating", r"closed tight tip right.left alternating", r"closed shank right.left alternating"]),
    ("TOM",            None,                  []),
    ("Hi-Hat Pedal",   r"hi.?hat",            [r"closed pedal"]),
    ("TOM",            None,                  []),
    ("Hi-Hat Open",    r"hi.?hat",            [r"^open full$", r"open half"]),
    ("TOM",            None,                  []),
    ("TOM",            None,                  []),
    ("Crash 1",        r"^cymbal\s*1\b",      [r"^tip$", r"^edge$", r"^bell$"]),
    ("TOM",            None,                  []),
    ("Ride",           r"^cymbal\s*3\b",      [r"^tip$", r"^edge$", r"^bell$"]),
]
assert len(PRIMARY_ROLES) == 16

# Notes 52-67: wildcard extras, ordered by priority (distinctive/fun stuff
# first). Any role that finds nothing leaves its slot for the guaranteed
# final-fill pass, so ordering here just controls what's LIKELY to land
# where, not a strict guarantee.
WILDCARD_ROLES = [
    ("Stick Hit",       r"stick",              []),
    ("Woodblock",       r"woodblock",          [r"^mid$"]),
    ("Clap (alt)",      r"clap",               [r"^multi$"]),
    ("Cowbell",         r"cowbell",            [r"high open"]),
    ("Tambourine",      r"tambourine",         [r"^shake$"]),
    ("Triangle",        r"triangle",           [r"^open$"]),
    ("Bongo",           r"bongo",              []),
    ("Kick Shell",      r"kick shell",         []),
    ("Kick (open)",     r"^kick(?!\s*shell)",  [r"^open$", r"felt beater", r"half open"]),
    ("Kick (extra)",    r"^kick(?!\s*shell)",  [r"mirror", r"half open"]),
    ("Snare Rimshot",   r"snare",              [r"^rimshot$"]),
    ("Snare Rim Only",  r"snare",              [r"rim only"]),
    ("Snare Flam",      r"snare",              [r"flam"]),
    ("Crash 2",         r"^cymbal\s*2\b",      [r"^tip$", r"^edge$"]),
    ("China/Splash",    r"^cymbal\s*[45]\b",   [r"^tip$", r"^edge$"]),
    ("Ride Bell",       r"^cymbal\s*3\b",      [r"^bell$", r"^edge$"]),
]
assert len(WILDCARD_ROLES) == 16


def load_kit_rows(kit_name: str, kit_folder: Path) -> list:
    """Only rows with real, existing sample files — a CSV row is not proof
    samples exist (e.g. Cymbal Choke articulations are documented but
    never actually recorded in this library). Filtering here means every
    downstream candidate is guaranteed playable, so nothing picked by
    pick_articulation/build_tom_cycle/fill_gap can silently fail later."""
    rows = []
    with open(MAPPING_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["kit_name"] != kit_name or ROLL_RE.search(row["articulation"]):
                continue
            drum_piece, articulation = row["drum_piece"], row["articulation"]
            folder = kit_folder / drum_piece
            prefix = f"{drum_piece} {articulation.replace('/', '-')}"
            if find_articulation_samples(folder, prefix):
                rows.append((drum_piece, articulation))
    return rows


def pick_articulation(rows, piece_pattern, preferences, used):
    piece_re = re.compile(piece_pattern, re.IGNORECASE)
    candidates = [(p, a) for p, a in rows if piece_re.search(p) and (p, a) not in used]
    if not candidates:
        return None

    for pref in preferences:
        pref_re = re.compile(pref, re.IGNORECASE)
        for p, a in candidates:
            if pref_re.search(a):
                return p, a

    return sorted(candidates)[0]


def build_tom_cycle(rows: list) -> list:
    """Round-robin ordering across distinct tom pieces before repeating any
    one piece — so 4 tom slots on a 2-tom kit alternate Tom1/Tom2/Tom1/Tom2
    with different articulations rather than exhausting Tom1 first."""
    pieces = sorted(set(p for p, a in rows if TOM_RE.search(p)))
    if not pieces:
        return []

    def art_rank(a):
        if re.search(r"alternating", a, re.IGNORECASE):
            return 0
        if re.search(r"center right hand", a, re.IGNORECASE):
            return 1
        if re.search(r"rimshot", a, re.IGNORECASE):
            return 2
        return 3

    per_piece = {piece: sorted({a for p, a in rows if p == piece}, key=art_rank) for piece in pieces}
    max_len = max(len(v) for v in per_piece.values())

    cycle = []
    for rank in range(max_len):
        for piece in pieces:
            if rank < len(per_piece[piece]):
                cycle.append((piece, per_piece[piece][rank]))
    return cycle


def pick_from_cycle(cycle: list, used: set):
    for candidate in cycle:
        if candidate not in used:
            return candidate
    return None


def build_fallback_cycle(rows: list) -> list:
    """Round-robin across all distinct pieces before repeating any one
    piece — plain alphabetical fallback keeps re-picking whichever piece
    sorts first (e.g. "Cymbal 1") for every gap on a kit missing several
    wildcard pieces, which is both repetitive and a worse substitute than
    spreading gaps across different pieces."""
    pieces = sorted(set(p for p, a in rows))
    per_piece = {piece: sorted({a for p, a in rows if p == piece}) for piece in pieces}
    max_len = max(len(v) for v in per_piece.values())
    cycle = []
    for rank in range(max_len):
        for piece in pieces:
            if rank < len(per_piece[piece]):
                cycle.append((piece, per_piece[piece][rank]))
    return cycle


def resolve_roles(rows: list) -> list:
    """Returns a list of 32 (role_label, drum_piece, articulation) or
    (role_label, None, None) — the latter should not happen given the
    guaranteed final-fill pass, but is handled gracefully if it does.
    A role_label of "Extra" means the guaranteed-fill pass substituted
    unrelated material for a piece this kit doesn't have — the original
    role name (e.g. "Cowbell") is deliberately NOT kept in that case, since
    labeling a Crash Cymbal edge hit "Cowbell" would be actively misleading."""
    used = set()
    tom_cycle = build_tom_cycle(rows)
    fallback_cycle = build_fallback_cycle(rows)
    assignments = [None] * 32

    for idx, (role_label, piece_pattern, preferences) in enumerate(PRIMARY_ROLES + WILDCARD_ROLES):
        if role_label == "TOM":
            choice = pick_from_cycle(tom_cycle, used)
        else:
            choice = pick_articulation(rows, piece_pattern, preferences, used)

        if choice is not None:
            used.add(choice)
            assignments[idx] = (role_label, choice[0], choice[1])
        else:
            assignments[idx] = (role_label, None, None)

    # Guaranteed fill: no pad stays empty if the kit has any material left.
    # Relabeled "Extra" since the substitute has nothing to do with the
    # original role.
    for idx, entry in enumerate(assignments):
        if entry[1] is None:
            choice = pick_from_cycle(fallback_cycle, used)
            if choice is not None:
                used.add(choice)
                assignments[idx] = ("Extra", choice[0], choice[1])

    return assignments


def build_kit(kit_name: str, kit_folder: Path, donor_pad: ET.Element, creator: SamplerCreator) -> bool:
    output_path = OUTPUT_DIR / f"AR {era_short_name(kit_folder)} {kit_name} 32Pad.adg"
    print(f"\n=== {kit_name} ===")

    rows = load_kit_rows(kit_name, kit_folder)
    if not rows:
        print("  No usable samples for this kit — skipping.")
        return False

    assignments = resolve_roles(rows)

    rack_xml = decode_adg(DRUM_RACK_TEMPLATE)
    rack_root = ET.fromstring(rack_xml)
    branch_presets = rack_root.find(".//BranchPresets")
    for old_pad in list(branch_presets):
        branch_presets.remove(old_pad)

    built = 0
    for idx, (role_label, drum_piece, articulation) in enumerate(assignments):
        note = FIRST_NOTE + idx

        if drum_piece is None:
            print(f"  Note {note:3} ({role_label}): no material available — pad left empty")
            continue

        folder = kit_folder / drum_piece
        prefix = f"{drum_piece} {articulation.replace('/', '-')}"
        layers = find_articulation_samples(folder, prefix)
        if not layers:
            print(f"  Note {note:3} ({role_label}): {drum_piece}/{articulation} has no sample files — pad left empty")
            continue

        pad = copy.deepcopy(donor_pad)
        pad.set("Id", str(idx))

        recv = pad.find(".//ZoneSettings/ReceivingNote")
        recv.set("Value", str(to_receiving_note_value(note)))

        sample_map = pad.find(".//MultiSampleMap")
        old_parts = sample_map.find("SampleParts")
        if old_parts is not None:
            sample_map.remove(old_parts)
        new_parts = ET.SubElement(sample_map, "SampleParts")
        for part in build_sample_parts(creator, layers, PAD_ROOT_NOTE):
            new_parts.append(part)
        enable_round_robin(sample_map)

        color = piece_color(drum_piece)
        if color is not None:
            color_elem = pad.find("DocumentColorIndex")
            if color_elem is not None:
                color_elem.set("Value", str(color))
            auto_colored = pad.find("AutoColored")
            if auto_colored is not None:
                auto_colored.set("Value", "false")

        name_elem = pad.find("Name")
        if name_elem is not None:
            name_elem.set("Value", f"{role_label}: {drum_piece} - {articulation}")

        branch_presets.append(pad)
        built += 1
        print(f"  Note {note:3} ({role_label}): {drum_piece} / {articulation}")

    if built == 0:
        print("  No pads built — skipping output.")
        return False

    xml_string = ET.tostring(rack_root, encoding="unicode", xml_declaration=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    encode_adg(xml_string, output_path)
    print(f"  Created: {output_path} ({built}/32 pads)")
    return True


def main():
    if not DRUM_RACK_TEMPLATE.exists():
        print(f"Error: Drum rack template not found: {DRUM_RACK_TEMPLATE}")
        sys.exit(1)

    kits = discover_kits(LIBRARY_ROOT)
    print(f"Discovered {len(kits)} kit folders")

    donor_xml = decode_adg(DRUM_RACK_TEMPLATE)
    donor_root = ET.fromstring(donor_xml)
    donor_pad = copy.deepcopy(donor_root.find(".//BranchPresets/DrumBranchPreset"))
    if donor_pad is None:
        raise ValueError("Donor template missing a DrumBranchPreset to clone")

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)

    results = {}
    for kit_name, kit_folder in kits.items():
        results[kit_name] = build_kit(kit_name, kit_folder, donor_pad, creator)

    print("\nSummary:")
    for kit_name, ok in results.items():
        print(f"  {'OK' if ok else 'FAILED'}: {kit_name}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
