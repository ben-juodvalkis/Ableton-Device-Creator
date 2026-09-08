"""Shared helpers for building velocity-layered, round-robin multisamples.

Parses the "<Name>-<Note>-V<velocity>-<RRid>.wav" filename convention used
throughout the autosampler library and turns a folder of samples into
MultiSamplePart XML elements grouped into contiguous velocity bins, with
round robin enabled for same-velocity alternates.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

import xml.etree.ElementTree as ET

FILENAME_RE = re.compile(
    r"^(?P<name>.+)-(?P<note>[A-G]#?-?\d+)-V(?P<velocity>\d+)-(?P<rr>[A-Za-z0-9]+)\.wav$",
    re.IGNORECASE,
)
NOTE_OFFSETS = {
    "C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
    "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11,
}
NOTE_RE = re.compile(r"^([A-G]#?)(-?\d+)$")


def note_name_to_midi(note_name: str) -> int:
    """Convert a note name (e.g. "C#4") to a MIDI note number, matching this
    codebase's convention where C-2 = MIDI note 0 (so C3 = 60)."""
    m = NOTE_RE.match(note_name)
    if not m:
        raise ValueError(f"Unrecognized note name: {note_name}")
    letter, octave = m.group(1), int(m.group(2))
    return (octave + 2) * 12 + NOTE_OFFSETS[letter]


def parse_velocity_layers(folder: Path) -> Tuple[int, Dict[int, List[Path]]]:
    """Group a folder's samples by velocity layer.

    Returns (root_note_midi, {velocity_center: [sample_paths]}).
    Raises if the folder's samples don't share a single root note.
    """
    root_notes = set()
    layers: Dict[int, List[Path]] = {}

    for wav in sorted(folder.glob("*.wav")):
        m = FILENAME_RE.match(wav.name)
        if not m:
            continue
        root_notes.add(m.group("note"))
        layers.setdefault(int(m.group("velocity")), []).append(wav)

    if not layers:
        raise ValueError(f"No samples matching the naming convention in {folder}")
    if len(root_notes) != 1:
        raise ValueError(f"Expected a single root note in {folder}, found: {sorted(root_notes)}")

    return note_name_to_midi(root_notes.pop()), layers


def velocity_bins(centers) -> List[Tuple[int, int, int]]:
    """Compute contiguous [min, max] velocity ranges from layer centers,
    splitting at the midpoint between adjacent centers."""
    centers = sorted(centers)
    bins = []
    for i, center in enumerate(centers):
        vel_min = 1 if i == 0 else (centers[i - 1] + center) // 2 + 1
        vel_max = 127 if i == len(centers) - 1 else (center + centers[i + 1]) // 2
        bins.append((center, vel_min, vel_max))
    return bins


def pitch_zones(notes) -> List[Tuple[int, int, int]]:
    """Contiguous KeyRange zones from sparse recorded notes, split at the
    midpoint between neighbors and stretched to the full 0-127 range at
    the outer edges — same technique as velocity_bins() but on the key
    axis, for chromatic libraries with gaps (not every semitone recorded)."""
    notes = sorted(notes)
    zones = []
    for i, note in enumerate(notes):
        key_min = 0 if i == 0 else (notes[i - 1] + note) // 2 + 1
        key_max = 127 if i == len(notes) - 1 else (note + notes[i + 1]) // 2
        zones.append((note, key_min, key_max))
    return zones


def build_sample_parts(creator, layers: Dict[int, List[Path]], root_note: int, start_index: int = 0, key_min: int = None, key_max: int = None) -> List[ET.Element]:
    """Build MultiSamplePart elements for every sample, split into
    velocity-layer bins with round-robin alternates. key_min/key_max
    default to root_note (exact single-key mapping); pass a wider zone
    (see pitch_zones()) for a sparse chromatic library where one recorded
    note needs to cover its neighbors' gap too.
    start_index lets callers building multiple root notes into one shared
    SampleParts list (e.g. a full chromatic map) keep Ids globally unique
    instead of restarting at 0 for every note."""
    if key_min is None:
        key_min = root_note
    if key_max is None:
        key_max = root_note

    parts = []
    index = start_index
    for center, vel_min, vel_max in velocity_bins(layers.keys()):
        for sample_path in sorted(layers[center], key=lambda p: p.name):
            part = creator._create_sample_part(
                index=index,
                sample_path=sample_path,
                key_min=key_min,
                key_max=key_max,
                root_key=root_note,
            )
            vel_range = part.find("VelocityRange")
            vel_range.find("Min").set("Value", str(vel_min))
            vel_range.find("Max").set("Value", str(vel_max))
            vel_range.find("CrossfadeMin").set("Value", str(vel_min))
            vel_range.find("CrossfadeMax").set("Value", str(vel_max))
            parts.append(part)
            index += 1
    return parts


def enable_round_robin(sample_map: ET.Element) -> None:
    """Enable cyclic round robin on a MultiSampleMap so Ableton alternates
    among samples that share the same key + velocity range."""
    round_robin = sample_map.find("RoundRobin")
    if round_robin is not None:
        round_robin.set("Value", "true")
    round_robin_mode = sample_map.find("RoundRobinMode")
    if round_robin_mode is not None:
        round_robin_mode.set("Value", "0")  # Cyclic
