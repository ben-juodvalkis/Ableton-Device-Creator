#!/usr/bin/env python3
"""
Set Macro Value — Set a single macro's value on every .adg in a folder.

Updates MacroControls.<N>/Manual to the given value on the top-level rack.
Leaves MacroDefaults alone (so saved value is what loads).

Usage:
    export PYTHONPATH=src
    python3 scripts/set_macro_value.py
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg

TARGET_DIR = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Ableton/FX/Voices Rack"
)
# (macro_index, macro_value) — macro_index is 0-based (Macro 10 = 9, Macro 11 = 10)
MACRO_SETTINGS = [
    (9, 50.0),   # Macro 10 -> 50
    (10, 16.0),  # Macro 11 -> 16
]


def set_macros(rack_path: Path, settings: list) -> int:
    xml_bytes = decode_adg(rack_path)
    root = ET.fromstring(xml_bytes)

    updated = 0
    for macro_index, macro_value in settings:
        ctrl = root.find(f".//MacroControls.{macro_index}")
        if ctrl is None:
            continue
        manual = ctrl.find("Manual")
        if manual is None:
            continue
        manual.set("Value", str(macro_value))
        updated += 1

    if updated == 0:
        return 0

    xml_string = ET.tostring(root, encoding="unicode", xml_declaration=True)
    encode_adg(xml_string, rack_path)
    return updated


def main():
    if not TARGET_DIR.exists():
        print(f"Error: folder not found: {TARGET_DIR}")
        sys.exit(1)

    racks = sorted(TARGET_DIR.rglob("*.adg"))
    desc = ", ".join(f"Macro {i+1}={v}" for i, v in MACRO_SETTINGS)
    print(f"Setting {desc} on {len(racks)} racks\n")

    ok = 0
    skip = 0
    for r in racks:
        try:
            n = set_macros(r, MACRO_SETTINGS)
            if n > 0:
                print(f"  OK: {r.name} ({n} macros)")
                ok += 1
            else:
                print(f"  SKIP: {r.name} (no macros found)")
                skip += 1
        except Exception as e:
            print(f"  ERROR: {r.name} — {e}")

    print(f"\nDone: {ok} updated, {skip} skipped")


if __name__ == "__main__":
    main()
