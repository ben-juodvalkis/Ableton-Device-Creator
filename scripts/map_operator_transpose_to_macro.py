#!/usr/bin/env python3
"""
Map Operator Transpose to Macro — wire each drum pad's Operator "Transpose"
knob to a macro on that pad's own Instrument Rack, for every .adg in a folder.

Mirrors what Ableton Live writes when you multi-select every chain and map
Transpose to the same macro in one bulk action (verified against a real
Live-generated reference file, Kit-GrainBeams — distinct from mapping chains
one at a time, which instead preserves each chain's value and leaves the
macro's default at -1):
  - Inserts a <KeyMidi> block (Channel=16 sentinel, NoteOrController=<macro
    index>) as the first child of each Operator's Globals/Transpose element.
  - Resets the Operator's Transpose knob itself to 0 (unison pitch across
    every pad).
  - Sets that pad's MacroControls.<N>/Manual to the neutral macro position
    (the 0-127 value that reproduces Transpose=0).
  - Sets MacroDefaults.<N> to the pad's *original* Transpose value scaled
    into the macro's 0-127 range, so the pre-mapping pitch is recoverable via
    the macro's right-click "reset to default".

Each pad is its own Instrument Rack (InstrumentGroupDevice) nested inside the
Drum Rack's DrumBranchPreset, with its own independent set of 16 macros — so
macro index 15 (Macro 16) here is local to each pad, not the outer rack.
Layered pads (more than one Operator per pad) get every Operator mapped to
the same macro.

Every mapped pad's own macro is then, in turn, mapped up to a macro on the
top-level Drum Rack (outer DrumGroupDevice) — a macro-of-a-macro chain, also
confirmed against the same reference file. This is the same KeyMidi mechanism
one level up: the pad's MacroControls.<N> element gets its own <KeyMidi>
(Channel=16, NoteOrController=<outer macro index>), and since both macro
scales are already 0-127 no rescaling is needed. The outer macro's own
Default is left at -1 (sentinel for "mapped via a plain map-to-macro action",
as opposed to the bulk-reset default seen at the pad level).

Usage:
    export PYTHONPATH=src
    python3 scripts/map_operator_transpose_to_macro.py
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg

TARGET_DIR = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Ableton/Drum/Prod/Designer Drums"
)
MACRO_INDEX = 8  # Macro 9, confirmed unused on every pad of every kit
OUTER_MACRO_INDEX = 0  # Macro 1 on the top-level Drum Rack, confirmed unused


def format_value(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if text else "0"


def build_key_midi(macro_index: int) -> ET.Element:
    key_midi = ET.Element("KeyMidi")
    fields = [
        ("PersistentKeyString", ""),
        ("IsNote", "false"),
        ("Channel", "16"),
        ("NoteOrController", str(macro_index)),
        ("LowerRangeNote", "-1"),
        ("UpperRangeNote", "-1"),
        ("ControllerMapMode", "0"),
    ]
    for tag, value in fields:
        ET.SubElement(key_midi, tag).set("Value", value)
    return key_midi


def map_pad(dbp: ET.Element, macro_index: int):
    """Maps every Operator's Transpose in this pad to its own macro. Returns
    the macro's new (neutral) value on success, or None if there was nothing
    to map (missing macro slot, or every Operator already mapped)."""
    igd = dbp.find("./DevicePresets/GroupDevicePreset/Device/InstrumentGroupDevice")
    if igd is None:
        return None

    macro_ctrl = igd.find(f"MacroControls.{macro_index}")
    macro_default = igd.find(f"MacroDefaults.{macro_index}")
    if macro_ctrl is None:
        return None

    default_values = []
    neutral_value = None
    for operator in dbp.findall(".//Operator"):
        transpose = operator.find("./Globals/Transpose")
        if transpose is None or transpose.find("KeyMidi") is not None:
            continue

        rng = transpose.find("MidiControllerRange")
        min_v = float(rng.find("Min").get("Value"))
        max_v = float(rng.find("Max").get("Value"))
        manual = transpose.find("Manual")
        current = float(manual.get("Value"))

        default_values.append((current - min_v) / (max_v - min_v) * 127.0)
        neutral_value = (0.0 - min_v) / (max_v - min_v) * 127.0

        transpose.insert(1, build_key_midi(macro_index))
        manual.set("Value", "0")  # unison pitch across every pad

    if not default_values:
        return None

    macro_manual = macro_ctrl.find("Manual")
    macro_manual.set("Value", format_value(neutral_value))
    if macro_default is not None:
        macro_default.set("Value", format_value(sum(default_values) / len(default_values)))

    # Live only ever stores even values here (8, 10, 12...); confirmed against
    # a real manually-mapped reference file. An odd value corrupts the rack's
    # macro-knob grid layout.
    required_visible = macro_index + 1
    if required_visible % 2 != 0:
        required_visible += 1

    num_visible = igd.find("NumVisibleMacroControls")
    if num_visible is not None and int(num_visible.get("Value")) < required_visible:
        num_visible.set("Value", str(required_visible))

    return neutral_value


def link_pad_macro_to_outer(igd: ET.Element, macro_index: int, outer_macro_index: int) -> None:
    macro_ctrl = igd.find(f"MacroControls.{macro_index}")
    if macro_ctrl.find("KeyMidi") is not None:
        return  # already linked
    macro_ctrl.insert(1, build_key_midi(outer_macro_index))


def map_rack(rack_path: Path, macro_index: int, outer_macro_index: int) -> int:
    root = ET.fromstring(decode_adg(rack_path))

    mapped_igds = []
    neutral_value = None
    for dbp in root.findall(".//DrumBranchPreset"):
        igd = dbp.find("./DevicePresets/GroupDevicePreset/Device/InstrumentGroupDevice")
        result = map_pad(dbp, macro_index)
        if result is not None:
            mapped_igds.append(igd)
            neutral_value = result

    if not mapped_igds:
        return 0

    for igd in mapped_igds:
        link_pad_macro_to_outer(igd, macro_index, outer_macro_index)

    dgd = root.find(".//DrumGroupDevice")
    outer_ctrl = dgd.find(f"MacroControls.{outer_macro_index}")
    outer_default = dgd.find(f"MacroDefaults.{outer_macro_index}")
    outer_ctrl.find("Manual").set("Value", format_value(neutral_value))
    if outer_default is not None:
        outer_default.set("Value", "-1")

    # Collapse the outer rack's macro view to show just this one knob,
    # matching the reference file — but only if nothing past it is already
    # in use, so we never hide a macro someone's actually relying on.
    other_macros_used = False
    for i in range(outer_macro_index + 1, 16):
        mc = dgd.find(f"MacroControls.{i}")
        if mc is not None and float(mc.find("Manual").get("Value")) != 0:
            other_macros_used = True
            break

    outer_numvis = dgd.find("NumVisibleMacroControls")
    if outer_numvis is not None and not other_macros_used:
        outer_numvis.set("Value", str(outer_macro_index + 1))

    # The outer Drum Rack shows its chain/pad list by default, not its macro
    # knobs; the pad-level racks already default to showing macros.
    outer_macros_visible = dgd.find("AreMacroControlsVisible")
    if outer_macros_visible is not None:
        outer_macros_visible.set("Value", "true")

    xml_string = ET.tostring(root, encoding="unicode", xml_declaration=True)
    encode_adg(xml_string, rack_path)
    return len(mapped_igds)


def main():
    if not TARGET_DIR.exists():
        print(f"Error: folder not found: {TARGET_DIR}")
        sys.exit(1)

    racks = sorted(TARGET_DIR.glob("*.adg"))
    print(
        f"Mapping Operator Transpose -> pad Macro {MACRO_INDEX + 1} -> "
        f"outer Macro {OUTER_MACRO_INDEX + 1} on {len(racks)} racks\n"
    )

    ok = 0
    skip = 0
    for rack in racks:
        try:
            n = map_rack(rack, MACRO_INDEX, OUTER_MACRO_INDEX)
            if n > 0:
                print(f"  OK: {rack.name} ({n} pads mapped)")
                ok += 1
            else:
                print(f"  SKIP: {rack.name} (no pads updated)")
                skip += 1
        except Exception as e:
            print(f"  ERROR: {rack.name} — {e}")

    print(f"\nDone: {ok} updated, {skip} skipped")


if __name__ == "__main__":
    main()
