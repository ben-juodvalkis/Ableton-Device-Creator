#!/usr/bin/env python3
"""
Create Close/Room combined Damage Drum Racks — the same kits as
create_variety_drum_rack.py, but every pad is a nested Instrument Rack with
TWO Samplers (Close mic and Room a.k.a. "Full" mic) whose chain-selector
zones crossfade between them. The selector is chained up to the Drum Rack's
Macro 7 ("Room"), so one knob sweeps every pad from pure Close (0) to pure
Room (127).

templates/close_room_drum_rack_template.adg is the donor: a 32-pad Drum Rack
hand-built in Ableton (exported 2026-07-17) where each pad holds the nested
two-chain rack with the crossfade zones, macro chaining, and mixer already
configured. Per this project's donor rule, this script only swaps each
Sampler's MultiSampleMap/SampleParts in place — never structure, zones,
macros, or ReceivingNote. The Close chain is identified by its selector zone
(fades out across 0-126), the Room chain by its mirror (fades in across
1-127) — not by chain order.

Kit definitions are imported from create_variety_drum_rack.compose_all_kits()
so the combined set always matches the single-mic sets kit-for-kit,
pad-for-pad. Both mic folders must exist for every instrument or the kit is
aborted without output (same policy as the single-mic build).

Unlike the single-mic donor (empty Samplers on every pad), this donor ships
with real sample content on all 32 pads, so pads beyond a kit's instrument
list are cleared (both chains' SampleParts emptied, name blanked) instead of
being left to sound the donor's Alfaias.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_damage_close_room_racks.py
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, parse_velocity_layers, velocity_bins
from create_variety_drum_rack import PAD_ROOT_NOTE, SAMPLE_LIBRARY_ROOT, color_pad, compose_all_kits

DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "close_room_drum_rack_template.adg"
OUTPUT_DIR = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/"
    "Looping Presets/Instruments/Ableton/Perc/Damage Close-Room"
)

# Which source subfolder feeds each chain; "Full" is what the library calls
# the room mic.
CHAIN_MICS = {"Close": "Close", "Room": "Full"}


def classify_chains(pad: ET.Element) -> dict:
    """Return {"Close": chain, "Room": chain} for one pad's nested rack,
    identified by the crossfading BranchSelectorRange zones the donor was
    built with (Close fades out toward 127, Room fades in from 0)."""
    chains = pad.findall("DevicePresets/GroupDevicePreset/BranchPresets/InstrumentBranchPreset")
    if len(chains) != 2:
        raise ValueError(f"Expected 2 nested chains on pad, found {len(chains)}")

    result = {}
    for chain in chains:
        zone = chain.find("BranchSelectorRange")
        if zone.find("CrossfadeMax").get("Value") == "0":
            result["Close"] = chain
        elif zone.find("CrossfadeMin").get("Value") == "127":
            result["Room"] = chain
    if set(result) != {"Close", "Room"}:
        raise ValueError("Pad's chain selector zones don't match the donor's Close/Room crossfade layout")
    return result


def replace_sample_parts(chain: ET.Element, parts: list) -> None:
    sample_map = chain.find(".//MultiSampleMap")
    if sample_map is None:
        raise ValueError("Chain's Sampler missing MultiSampleMap element")
    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")
    for part in parts:
        new_parts.append(part)
    enable_round_robin(sample_map)


def fill_pad(pad: ET.Element, creator: SamplerCreator, instrument_dir: Path) -> None:
    """Fill one pad's Close and Room Samplers in place from the instrument's
    two mic folders, fixed on PAD_ROOT_NOTE."""
    summaries = []
    for chain_name, chain in classify_chains(pad).items():
        _, layers = parse_velocity_layers(instrument_dir / CHAIN_MICS[chain_name])
        replace_sample_parts(chain, build_sample_parts(creator, layers, PAD_ROOT_NOTE))
        total = sum(len(samples) for samples in layers.values())
        summaries.append(f"{chain_name}: {len(velocity_bins(layers.keys()))} layers/{total} samples")
    print(f"    {'; '.join(summaries)}")


def clear_pad(pad: ET.Element) -> None:
    """Silence a surplus donor pad: empty both chains' SampleParts and blank
    the name. Structure (nested rack, zones, macros) stays untouched."""
    for chain in classify_chains(pad).values():
        replace_sample_parts(chain, [])
    name_elem = pad.find("Name")
    if name_elem is not None:
        name_elem.set("Value", "")


def name_room_macro(rack_root: ET.Element) -> None:
    """The donor's top-level crossfade macro is still at its default name —
    label it to match the nested racks' "Room" macro."""
    dg = rack_root.find(".//DrumGroupDevice")
    display_name = dg.find("MacroDisplayNames.6") if dg is not None else None
    if display_name is not None:
        display_name.set("Value", "Room")


def build_kit(kit_name: str, instruments: list, creator: SamplerCreator) -> bool:
    output_path = OUTPUT_DIR / f"Drum_Rack_{kit_name.replace(' ', '_')}.adg"

    print(f"\n=== {kit_name} ({len(instruments)} pads) ===")

    rack_xml = decode_adg(DRUM_RACK_TEMPLATE)
    rack_root = ET.fromstring(rack_xml)
    name_room_macro(rack_root)

    pads = rack_root.findall(".//BranchPresets/DrumBranchPreset")
    pads.sort(key=lambda p: int(p.find(".//ZoneSettings/ReceivingNote").get("Value")), reverse=True)

    if len(instruments) > len(pads):
        print(f"  Error: {len(instruments)} instruments but only {len(pads)} pads available")
        return False

    missing = []
    for category, name in instruments:
        for mic in CHAIN_MICS.values():
            folder = SAMPLE_LIBRARY_ROOT / category / name / mic
            if not folder.exists():
                print(f"  SKIP (missing folder): {category}/{name}/{mic}")
                missing.append(f"{category}/{name}/{mic}")
    if missing:
        print(f"\n  {len(missing)} mic folders missing — aborting without writing output.")
        return False

    for pad, (category, name) in zip(pads, instruments):
        note = pad.find(".//ZoneSettings/ReceivingNote").get("Value")
        print(f"  Note {note}: {category}/{name}")
        fill_pad(pad, creator, SAMPLE_LIBRARY_ROOT / category / name)
        color_pad(pad, category)
        name_elem = pad.find("Name")
        if name_elem is not None:
            name_elem.set("Value", name)

    for pad in pads[len(instruments):]:
        clear_pad(pad)
    if len(instruments) < len(pads):
        print(f"  Cleared {len(pads) - len(instruments)} surplus donor pads")

    xml_string = ET.tostring(rack_root, encoding="unicode", xml_declaration=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    encode_adg(xml_string, output_path)
    print(f"  Created: {output_path}")
    return True


def main():
    if not DRUM_RACK_TEMPLATE.exists():
        print(f"Error: Drum rack template not found: {DRUM_RACK_TEMPLATE}")
        sys.exit(1)

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)

    all_kits = compose_all_kits()

    results = {}
    for kit_name, instruments in all_kits.items():
        results[kit_name] = build_kit(kit_name, instruments, creator)

    print("\nSummary:")
    for kit_name, ok in results.items():
        print(f"  {'OK' if ok else 'FAILED'}: {kit_name}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
