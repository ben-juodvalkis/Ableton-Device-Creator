"""Tests for macro-mapping removal (``macro_mapping.unmap`` and ``unmap_batch``)."""

import json
import math
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import pytest

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.macro_mapping.unmap import (
    ENUM,
    FADER,
    INT,
    LINEAR,
    LOG,
    POW2,
    POW3,
    POW5,
    bake_plan,
    classify_rack,
    effective_value,
    format_live_float,
    reset_macro_defaults,
    strip_key_midi,
    unmap_drum_rack,
    verify_unmap,
)
from ableton_device_creator.macro_mapping.unmap_batch import unmap_tree, write_report

GOLDEN_MAPPED = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/Looping Presets/"
    "Instruments/Ableton/Drum/Prod/Electro Acoustic/1 Dry Machines/ 606 + 808.adg"
)
GOLDEN_UNMAPPED = Path("/Users/Music/Desktop/test Project/ 606 + 808.adg")
GOLDEN_UNMAPPED_ALT = Path(
    "/Users/Shared/Music/Soundbanks/Ableton/Live Libraries/User Library/Looping Test/"
    "606 + 808 unmapped.adg"
)

# --------------------------------------------------------------------------- #
# Synthetic fixture
# --------------------------------------------------------------------------- #

HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Ableton MajorVersion="5" MinorVersion="12.0_12120" SchemaChangeCount="2" '
    'Creator="Ableton Live 12.1.5" Revision="test">\n'
)

MACRO_VALUES = {3: "63.5", 4: "107.950005", 8: "85", 15: "42"}
MACRO_NAMES = {0: "FX1", 1: "FX2", 4: "Kick"}
MACRO_DEFAULTS = {0: "0", 1: "63.5", 6: "-1", 9: "127"}


def key_midi(macro: int, indent: int, inline: bool = False) -> str:
    """A KeyMidi block for ``macro`` as Live writes it, or the one-line script form."""
    fields = [
        '<PersistentKeyString Value="" />',
        '<IsNote Value="false" />',
        '<Channel Value="16" />',
        '<NoteOrController Value="%d" />' % macro,
        '<LowerRangeNote Value="-1" />',
        '<UpperRangeNote Value="-1" />',
        '<ControllerMapMode Value="0" />',
    ]
    if inline:
        return "\t" * indent + "<KeyMidi>" + "".join(fields) + "</KeyMidi>"
    tab = "\t" * indent
    return "\n".join([tab + "<KeyMidi>"] + [tab + "\t" + f for f in fields] + [tab + "</KeyMidi>"])


def param(tag: str, manual: str, indent: int, macro=None, rng=None, onoff=None, inline=False):
    tab = "\t" * indent
    lines = [tab + "<%s>" % tag, tab + '\t<LomId Value="0" />']
    manual_line = tab + '\t<Manual Value="%s" />' % manual
    if macro is not None and inline:
        lines.append(key_midi(macro, indent + 1, inline=True) + '<Manual Value="%s" />' % manual)
    else:
        if macro is not None:
            lines.append(key_midi(macro, indent + 1))
        lines.append(manual_line)
    if rng is not None:
        lines += [
            tab + "\t<MidiControllerRange>",
            tab + '\t\t<Min Value="%s" />' % rng[0],
            tab + '\t\t<Max Value="%s" />' % rng[1],
            tab + "\t</MidiControllerRange>",
        ]
    if onoff is not None:
        lines += [
            tab + "\t<MidiCCOnOffThresholds>",
            tab + '\t\t<Min Value="%s" />' % onoff[0],
            tab + '\t\t<Max Value="%s" />' % onoff[1],
            tab + "\t</MidiCCOnOffThresholds>",
        ]
    lines += [
        tab + '\t<AutomationTarget Id="0">',
        tab + '\t\t<LockEnvelope Value="0" />',
        tab + "\t</AutomationTarget>",
        tab + "</%s>" % tag,
    ]
    return "\n".join(lines)


def rack_device(tag: str, indent: int, values=None, names=None, defaults=None) -> str:
    values, names, defaults = values or {}, names or {}, defaults or {}
    tab = "\t" * indent
    lines = [tab + '<%s Id="0">' % tag, tab + '\t<LomId Value="0" />']
    for n in range(16):
        lines.append(param("MacroControls.%d" % n, values.get(n, "0"), indent + 1))
    for n in range(16):
        lines.append(
            tab + '\t<MacroDisplayNames.%d Value="%s" />' % (n, names.get(n, "Macro %d" % (n + 1)))
        )
    for n in range(16):
        lines.append(tab + '\t<MacroDefaults.%d Value="%s" />' % (n, defaults.get(n, "63.5")))
    lines.append(tab + "</%s>" % tag)
    return "\n".join(lines)


def drum_cell_pad(pad_id: int, indent: int) -> str:
    tab = "\t" * indent
    cell = "\n".join(
        [
            tab + '\t\t\t<DrumCell Id="0">',
            param("Voice_Transpose", "32", indent + 4, macro=3, rng=("-48", "48")),
            param(
                "Voice_Envelope_Attack",
                "0.00009999999747",
                indent + 4,
                macro=8,
                rng=("0.00009999999747", "20.0000076"),
            ),
            param("Effect_On", "false", indent + 4, macro=0, onoff=("1", "0")),
            tab + "\t\t\t</DrumCell>",
        ]
    )
    mixer = "\n".join(
        [
            tab + '\t\t\t<AudioBranchMixerDevice Id="0">',
            param("Volume", "1", indent + 4, macro=4, rng=("0.0003162277571", "1.99526238")),
            tab + "\t\t\t</AudioBranchMixerDevice>",
        ]
    )
    return "\n".join(
        [
            tab + '<DrumBranchPreset Id="%d">' % pad_id,
            tab + "\t<DevicePresets>",
            tab + '\t\t<AbletonDevicePreset Id="0">',
            tab + "\t\t\t<Device>",
            cell.replace("\t\t\t<DrumCell", "\t\t\t\t<DrumCell").replace(
                "\t\t\t</DrumCell>", "\t\t\t\t</DrumCell>"
            ),
            tab + "\t\t\t</Device>",
            tab + "\t\t</AbletonDevicePreset>",
            tab + "\t</DevicePresets>",
            tab + "\t<MixerPreset>",
            tab + '\t\t<AbletonDevicePreset Id="0">',
            tab + "\t\t\t<Device>",
            mixer.replace("\t\t\t<AudioBranch", "\t\t\t\t<AudioBranch").replace(
                "\t\t\t</AudioBranch", "\t\t\t\t</AudioBranch"
            ),
            tab + "\t\t\t</Device>",
            tab + "\t\t</AbletonDevicePreset>",
            tab + "\t</MixerPreset>",
            tab + "</DrumBranchPreset>",
        ]
    )


def nested_rack_pad(pad_id: int, indent: int) -> str:
    """A pad holding an Instrument Rack: its macro 1 is chained to root macro 16 (one-line
    KeyMidi form), and a Simpler inside it is mapped to the nested rack's own macro 1."""
    tab = "\t" * indent
    inner_device = "\n".join(
        [
            tab + '\t\t\t\t<InstrumentGroupDevice Id="0">',
            tab + '\t\t\t\t\t<LomId Value="0" />',
            param("MacroControls.0", "0", indent + 5, macro=15, rng=("0", "127"), inline=True),
            param("MacroControls.1", "63.5", indent + 5),
            tab + '\t\t\t\t\t<MacroDisplayNames.0 Value="Inner" />',
            tab + '\t\t\t\t\t<MacroDefaults.0 Value="55" />',
            tab + "\t\t\t\t</InstrumentGroupDevice>",
        ]
    )
    simpler = "\n".join(
        [
            tab + '\t\t\t\t\t\t\t\t<OriginalSimpler Id="0">',
            param("TransposeKey", "0", indent + 9, macro=0, rng=("-48", "48")),
            tab + "\t\t\t\t\t\t\t\t</OriginalSimpler>",
        ]
    )
    return "\n".join(
        [
            tab + '<DrumBranchPreset Id="%d">' % pad_id,
            tab + "\t<DevicePresets>",
            tab + '\t\t<GroupDevicePreset Id="0">',
            tab + "\t\t\t<Device>",
            inner_device,
            tab + "\t\t\t</Device>",
            tab + "\t\t\t<BranchPresets>",
            tab + '\t\t\t\t<InstrumentBranchPreset Id="0">',
            tab + "\t\t\t\t\t<DevicePresets>",
            tab + '\t\t\t\t\t\t<AbletonDevicePreset Id="0">',
            tab + "\t\t\t\t\t\t\t<Device>",
            simpler,
            tab + "\t\t\t\t\t\t\t</Device>",
            tab + "\t\t\t\t\t\t</AbletonDevicePreset>",
            tab + "\t\t\t\t\t</DevicePresets>",
            tab + "\t\t\t\t</InstrumentBranchPreset>",
            tab + "\t\t\t</BranchPresets>",
            tab + "\t\t</GroupDevicePreset>",
            tab + "\t</DevicePresets>",
            tab + "</DrumBranchPreset>",
        ]
    )


def synthetic_drum_rack(with_nested: bool = True) -> str:
    pads = [drum_cell_pad(0, 2), drum_cell_pad(1, 2)]
    if with_nested:
        pads.append(nested_rack_pad(2, 2))
    return HEADER + "\n".join(
        [
            "\t<GroupDevicePreset>",
            '\t\t<OverwriteProtectionNumber Value="3073" />',
            "\t\t<Device>",
            rack_device("DrumGroupDevice", 3, MACRO_VALUES, MACRO_NAMES, MACRO_DEFAULTS),
            "\t\t</Device>",
            "\t\t<BranchPresets>",
            "\n".join(pads),
            "\t\t</BranchPresets>",
            "\t</GroupDevicePreset>",
            "</Ableton>",
            "",
        ]
    )


def synthetic_instrument_rack(with_drum_rack: bool) -> str:
    inner = ""
    if with_drum_rack:
        inner = "\n".join(
            [
                '\t\t\t<InstrumentBranchPreset Id="0">',
                "\t\t\t\t<DevicePresets>",
                '\t\t\t\t\t<GroupDevicePreset Id="0">',
                "\t\t\t\t\t\t<Device>",
                rack_device("DrumGroupDevice", 7),
                "\t\t\t\t\t\t</Device>",
                "\t\t\t\t\t\t<BranchPresets />",
                "\t\t\t\t\t</GroupDevicePreset>",
                "\t\t\t\t</DevicePresets>",
                "\t\t\t</InstrumentBranchPreset>",
            ]
        )
    return HEADER + "\n".join(
        [
            "\t<GroupDevicePreset>",
            "\t\t<Device>",
            rack_device("InstrumentGroupDevice", 3),
            "\t\t</Device>",
            "\t\t<BranchPresets>",
            inner,
            "\t\t</BranchPresets>",
            "\t</GroupDevicePreset>",
            "</Ableton>",
            "",
        ]
    )


def manuals(xml: str, tag: str):
    return [el.find("Manual").get("Value") for el in ET.fromstring(xml).iter(tag)]


# --------------------------------------------------------------------------- #
# Pure functions
# --------------------------------------------------------------------------- #


def test_fixture_is_well_formed():
    ET.fromstring(synthetic_drum_rack())
    ET.fromstring(synthetic_instrument_rack(True))


def test_classify_counts_root_and_nested_mappings():
    info = classify_rack(synthetic_drum_rack())
    assert info.root_class == "DrumGroupDevice"
    assert info.is_drum_rack
    assert info.key_midi_count == 10  # 4 per DrumCell pad, chained nested macro, nested Simpler
    assert info.key_midi_root == 9
    assert info.key_midi_nested == 1
    assert info.nested_drum_racks == 0
    assert info.nested_group_devices == {"InstrumentGroupDevice": 1}
    assert info.macro_names[:2] == ["FX1", "FX2"] and len(info.macro_names) == 16
    assert info.macro_values[3] == 63.5 and info.macro_values[8] == 85
    assert not info.has_macro_control_index
    assert info.non_macro_key_midi == 0


def test_classify_instrument_rack_with_and_without_drum_rack():
    assert classify_rack(synthetic_instrument_rack(True)).is_instrument_rack_with_drum_rack
    plain = classify_rack(synthetic_instrument_rack(False))
    assert plain.root_class == "InstrumentGroupDevice"
    assert not plain.is_instrument_rack_with_drum_rack
    assert not plain.is_drum_rack


def test_strip_key_midi_removes_root_owned_only():
    xml = synthetic_drum_rack()
    out, removed = strip_key_midi(xml)
    assert removed == 9
    assert out.count("<KeyMidi") == 1
    # the nested Simpler's mapping survives, the chained nested macro's does not
    assert (
        "<TransposeKey>" in out and ET.fromstring(out).find(".//TransposeKey/KeyMidi") is not None
    )
    assert ET.fromstring(out).find(".//MacroControls.0/KeyMidi") is None
    # nothing but the blocks changed
    assert manuals(out, "Voice_Transpose") == ["32", "32"]
    assert out.count("\n") == xml.count("\n") - 8 * 9  # the one-line block leaves its line


def test_strip_key_midi_include_nested():
    out, removed = strip_key_midi(synthetic_drum_rack(), include_nested=True)
    assert removed == 10
    assert "<KeyMidi" not in out


def test_one_line_block_keeps_its_manual_and_indentation():
    out, _ = strip_key_midi(synthetic_drum_rack())
    line = [l for l in out.split("\n") if "<MacroControls.0>" in l]
    assert len(line) == 2  # root and nested
    inner = out[out.index("<InstrumentGroupDevice") :]
    block = inner[inner.index("<MacroControls.0>") : inner.index("</MacroControls.0>")]
    assert "KeyMidi" not in block
    indent = block[block.index("\n") + 1 : block.index("<LomId")]  # the block's child indentation
    assert indent.strip("\t") == "" and len(indent) == 8
    assert '\n%s<Manual Value="0" />\n' % indent in block


def test_reset_macro_defaults_touches_only_the_root_rack():
    out, changed = reset_macro_defaults(synthetic_drum_rack())
    assert changed == 15  # MacroDefaults.6 was already -1
    root = ET.fromstring(out).find("GroupDevicePreset/Device/DrumGroupDevice")
    assert all(root.find("MacroDefaults.%d" % n).get("Value") == "-1" for n in range(16))
    nested = ET.fromstring(out).find(".//InstrumentGroupDevice/MacroDefaults.0")
    assert nested.get("Value") == "55"
    again, changed_again = reset_macro_defaults(out)
    assert changed_again == 0 and again == out


def test_unmap_bakes_macro_driven_values():
    xml = synthetic_drum_rack()
    out, report = unmap_drum_rack(xml)
    assert report.removed == 9
    assert report.removed_nested == 0
    assert report.baked == 5  # 2 x Transpose, 2 x Attack, chained nested macro
    assert report.kept == 4  # Effect_On (macro 0 -> off) x 2, chain Volume (0 dB) x 2
    assert report.unknown == 0 and report.unknown_params == []
    assert report.macro_defaults_changed == 15
    assert manuals(out, "Voice_Transpose") == ["0", "0"]
    assert manuals(out, "Voice_Envelope_Attack") == ["0.3531291485", "0.3531291485"]
    assert manuals(out, "Effect_On") == ["false", "false"]
    assert manuals(out, "Volume") == ["1", "1"]
    inner = ET.fromstring(out).find(".//InstrumentGroupDevice")
    assert inner.find("MacroControls.0/Manual").get("Value") == "42"
    assert inner.find("MacroControls.0/KeyMidi") is None
    assert inner.find("MacroControls.1/Manual").get("Value") == "63.5"
    assert ET.fromstring(out).find(".//TransposeKey/KeyMidi") is not None
    reasons = Counter(d.reason for d in report.decisions)
    assert reasons == {"baked": 5, "consistent": 4}
    assert verify_unmap(xml, out, report) == []


def test_unmap_is_idempotent():
    out, _ = unmap_drum_rack(synthetic_drum_rack())
    again, report = unmap_drum_rack(out)
    assert again == out
    assert report.removed == 0 and report.baked == 0 and report.macro_defaults_changed == 0


def test_unmap_include_nested_bakes_nested_endpoint():
    xml = synthetic_drum_rack()
    out, report = unmap_drum_rack(xml, include_nested=True)
    assert report.removed == 10 and report.removed_nested == 1
    assert "<KeyMidi" not in out
    assert manuals(out, "TransposeKey") == ["-48"]  # nested macro at 0 -> Min
    assert verify_unmap(xml, out, report, include_nested=True) == []


def test_unmap_without_bake_keeps_stored_values():
    xml = synthetic_drum_rack()
    out, report = unmap_drum_rack(xml, bake=False)
    assert report.removed == 9 and report.baked == 0
    assert manuals(out, "Voice_Transpose") == ["32", "32"]
    assert verify_unmap(xml, out, report) == []


def test_unmap_leaves_everything_else_byte_identical():
    xml = synthetic_drum_rack(with_nested=False)
    out, _ = unmap_drum_rack(xml)
    import re

    expected = re.sub(r"[ \t]*<KeyMidi>.*?</KeyMidi>[ \t]*\n", "", xml, flags=re.S)
    expected = re.sub(r'(<MacroDefaults\.\d+ Value=")[^"]*(" />)', r"\1-1\2", expected)
    expected = expected.replace('<Manual Value="32" />', '<Manual Value="0" />')
    expected = expected.replace(
        '<Manual Value="0.00009999999747" />', '<Manual Value="0.3531291485" />'
    )
    assert out == expected


def test_verify_catches_a_stray_edit():
    xml = synthetic_drum_rack()
    out, report = unmap_drum_rack(xml)
    tampered = out.replace(
        '<MacroDisplayNames.4 Value="Kick" />', '<MacroDisplayNames.4 Value="Snare" />'
    )
    assert any("MacroDisplayNames" in f for f in verify_unmap(xml, tampered, report))
    tampered = out.replace('<Manual Value="63.5" />', '<Manual Value="64" />', 1)
    assert any("unexpected change" in f for f in verify_unmap(xml, tampered, report))


def test_bake_plan_reports_unknown_curves():
    xml = (
        synthetic_drum_rack(with_nested=False)
        .replace("<Voice_Transpose>", "<Voice_Mystery>")
        .replace("</Voice_Transpose>", "</Voice_Mystery>")
    )
    plan = [d for d in bake_plan(xml) if d.param == "Voice_Mystery"]
    assert len(plan) == 2
    assert all(d.reason == "unknown-curve" and d.new_value is None for d in plan)
    out, report = unmap_drum_rack(xml)
    assert report.unknown == 2
    assert report.unknown_params == ["DrumCell/Voice_Mystery@63.5"]
    assert manuals(out, "Voice_Mystery") == ["32", "32"]


@pytest.mark.parametrize(
    "kind, t, lo, hi, expected",
    [
        (LINEAR, 42 / 127, -36.0, 36.0, -12.188976),  # DrumCell Volume (dB)
        (LOG, 85 / 127, 9.999999747e-05, 20.0000076, 0.353129),  # Attack, golden pair
        (LOG, 40 / 127, 0.001000000047, 60.0000343, 0.0319838),  # Decay, library
        (POW2, 0.5, 180.0, 15000.0, 3885.0),  # NoiseFrequency midpoint
        (POW3, 0.5, 0.05999999866, 1.0, 0.1775),  # PunchTime midpoint
        (POW5, 0.5, 1.0, 5000.0, 157.21875),  # RingModFrequency midpoint
        (ENUM, 20 / 127, 0, 5, 1.0),  # ModulationTarget, golden pair
        (INT, 63.5 / 127, -48, 48, 0.0),
        (INT, 80 / 127, -48, 48, 12.0),  # ADR-428 measurement
        (FADER, 107.950005 / 127, 0.0003162277571, 1.99526238, 1.0),  # 0 dB
        (LINEAR, 32 / 127, 0.0, 1.0, 0.251968503),
    ],
)
def test_effective_value(kind, t, lo, hi, expected):
    value = effective_value(kind, t, lo, hi)
    assert value is not None
    assert math.isclose(value, expected, rel_tol=1e-5, abs_tol=1e-9)


def test_effective_value_unknown_regions():
    assert effective_value("nope", 0.5, 0, 1) is None
    assert effective_value(LOG, 0.5, 0, 1) is None
    assert effective_value(FADER, 34 / 127, 0.0003162277571, 1.99526238) is None  # below the knee


@pytest.mark.parametrize(
    "value, text",
    [
        (-12.188976377952756, "-12.1889763"),
        (0.35, "0.349999994"),
        (0.35312905907630920, "0.3531290591"),
        (60.0, "60"),
        (0.0, "0"),
        (107.95000457763672, "107.950005"),  # the float32 Live stores for 0.85 * 127
        (107.95, "107.949997"),  # the nearest float32 to the decimal is one step below
    ],
)
def test_format_live_float(value, text):
    assert format_live_float(value) == text


def test_power_curve_over_a_partial_range_uses_the_full_range():
    # RM Freq mapped over 157.22..1187 Hz (the knob's 50 %..75 %): the macro sweeps the knob
    # linearly, so t = 0.5 lands at the knob's 62.5 %, not halfway in Hz.
    lo, hi = 1 + 4999 * 0.5**5, 1 + 4999 * 0.75**5
    value = effective_value(POW5, 0.5, lo, hi, full=(1.0, 5000.0))
    assert math.isclose(value, 1 + 4999 * 0.625**5, rel_tol=1e-9)
    assert math.isclose(effective_value(POW5, 0.5, 1.0, 5000.0, full=(1.0, 5000.0)), 157.21875)


def test_gzip_round_trip(tmp_path):
    out, _ = unmap_drum_rack(synthetic_drum_rack())
    path = encode_adg(out, tmp_path / "rack.adg")
    assert decode_adg(path) == out


# --------------------------------------------------------------------------- #
# Batch runner and CLI
# --------------------------------------------------------------------------- #


def make_tree(root: Path) -> None:
    encode_adg(synthetic_drum_rack(), root / "Drum" / "Prod" / "Kit A.adg")
    encode_adg(synthetic_drum_rack(with_nested=False), root / "Perc" / " Kit B.adg")
    encode_adg(synthetic_instrument_rack(True), root / "FX" / "Dual.adg")
    encode_adg(synthetic_instrument_rack(False), root / "Inst" / "Plain.adg")
    encode_adg(HEADER + '\t<MultiSampler Id="0" />\n</Ableton>\n', root / "Inst" / "Sampler.adv")
    (root / "notes.txt").write_text("x")


def test_unmap_tree_dry_run_writes_nothing(tmp_path):
    root = tmp_path / "src"
    make_tree(root)
    report = unmap_tree(root, None, dry_run=True)
    totals = report.totals
    assert totals["adg_files"] == 4
    assert totals["drum_racks"] == 2 and totals["processed"] == 2
    assert totals["nested_only"] == 1 and totals["skipped"] == 1
    assert totals["skipped_InstrumentGroupDevice"] == 1
    assert totals["key_midi_in_scope"] == 17
    assert totals["other_adv"] == 1 and totals["other_txt"] == 1
    assert not (tmp_path / "out").exists()
    dry = [f for f in report.files if f.action == "dry-run"]
    assert [f.path for f in dry] == ["Drum/Prod/Kit A.adg", "Perc/ Kit B.adg"]
    assert dry[0].nested_group_devices == {"InstrumentGroupDevice": 1}


def test_unmap_tree_mirrors_and_verifies(tmp_path):
    root, out = tmp_path / "src", tmp_path / "out"
    make_tree(root)
    report = unmap_tree(root, out)
    totals = report.totals
    assert totals["processed"] == 2 and totals["failed"] == 0
    assert totals["key_midi_removed"] == 17
    assert totals["values_baked"] == 9 and totals["values_unknown_curve"] == 0
    assert totals["key_midi_left_nested"] == 1
    written = sorted(p.relative_to(out) for p in out.rglob("*.adg"))
    assert [str(p) for p in written] == ["Drum/Prod/Kit A.adg", "Perc/ Kit B.adg"]
    assert not (out / "FX" / "Dual.adg").exists()
    unmapped = decode_adg(out / "Perc" / " Kit B.adg")
    assert "<KeyMidi" not in unmapped
    assert classify_rack(decode_adg(out / "Drum" / "Prod" / "Kit A.adg")).key_midi_root == 0
    # source untouched
    assert classify_rack(decode_adg(root / "Perc" / " Kit B.adg")).key_midi_root == 8
    path = write_report(report, tmp_path / "r" / "report.json")
    data = json.loads(path.read_text())
    assert data["totals"]["processed"] == 2
    assert {f["path"]: f["action"] for f in data["files"]}["FX/Dual.adg"] == "nested-only"


def test_unmap_tree_refuses_unsafe_output(tmp_path):
    root = tmp_path / "src"
    make_tree(root)
    with pytest.raises(ValueError):
        unmap_tree(root, root)
    with pytest.raises(ValueError):
        unmap_tree(root, root / "inside")
    with pytest.raises(ValueError):
        unmap_tree(root, tmp_path)
    with pytest.raises(ValueError):
        unmap_tree(root, None)


def test_unmap_tree_refuses_to_overwrite_without_flag(tmp_path):
    root, out = tmp_path / "src", tmp_path / "out"
    make_tree(root)
    unmap_tree(root, out)
    with pytest.raises(FileExistsError):
        unmap_tree(root, out)
    report = unmap_tree(root, out, overwrite=True)
    assert report.totals["processed"] == 2


def test_cli_unmap(tmp_path):
    click = pytest.importorskip("click")
    from click.testing import CliRunner

    from ableton_device_creator.cli import main

    root, out = tmp_path / "src", tmp_path / "out"
    make_tree(root)
    runner = CliRunner()
    result = runner.invoke(main, ["drum-rack", "unmap", str(root), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output and "Kit A.adg" in result.output
    assert "processed" in result.output
    assert not out.exists()

    result = runner.invoke(
        main,
        ["drum-rack", "unmap", str(root), "--out", str(out), "--report", str(tmp_path / "r.json")],
    )
    assert result.exit_code == 0, result.output
    assert (out / "Perc" / " Kit B.adg").exists()
    assert json.loads((tmp_path / "r.json").read_text())["totals"]["key_midi_removed"] == 17

    result = runner.invoke(main, ["drum-rack", "unmap", str(root)])
    assert result.exit_code == 2
    del click


# --------------------------------------------------------------------------- #
# Golden pair: the pipeline kit vs Live's own unmap of it
# --------------------------------------------------------------------------- #

COSMETIC_TAGS = {"SourceHint", "ViewData"}
# Elements Live 12.4 adds when it re-saves a 12.1 file (schema migration, not unmapping).
SCHEMA_ADDED_PATHS = {"MidiControllerRange", "Min", "Max", "Voice_PitchToEnvelopeModulation"}


def golden_unmapped_path():
    for p in (GOLDEN_UNMAPPED, GOLDEN_UNMAPPED_ALT):
        if p.exists():
            return p
    return None


@pytest.mark.skipif(
    not GOLDEN_MAPPED.exists() or golden_unmapped_path() is None,
    reason="golden pair not on this machine",
)
def test_golden_pair_matches_live_unmap():
    original = decode_adg(GOLDEN_MAPPED)
    live = decode_adg(golden_unmapped_path())
    out, report = unmap_drum_rack(original)
    assert report.removed == 720 and report.baked == 120 and report.unknown == 0
    assert verify_unmap(original, out, report) == []
    assert out.count("<KeyMidi") == 0

    ours, theirs = ET.fromstring(out), ET.fromstring(live)
    root_ours = ours.find("GroupDevicePreset/Device/DrumGroupDevice")
    root_live = theirs.find("GroupDevicePreset/Device/DrumGroupDevice")
    for n in range(16):
        assert root_ours.find("MacroDefaults.%d" % n).get("Value") == "-1"
        assert root_ours.find("MacroDisplayNames.%d" % n).get("Value") == root_live.find(
            "MacroDisplayNames.%d" % n
        ).get("Value")
        assert root_ours.find("MacroControls.%d/Manual" % n).get("Value") == root_live.find(
            "MacroControls.%d/Manual" % n
        ).get("Value")
    for tag in ("DrumBranchPreset", "DrumCell", "OriginalSimpler", "MultiSampler"):
        assert len(ours.findall(".//" + tag)) == len(theirs.findall(".//" + tag))

    def paths(root):
        counter = Counter()

        def walk(el, prefix):
            p = prefix + "/" + el.tag
            counter[p] += 1
            for ch in el:
                walk(ch, p)

        walk(root, "")
        return counter

    ours_paths, live_paths = paths(ours), paths(theirs)
    only_ours = {p: n for p, n in (ours_paths - live_paths).items()}
    only_live = {p: n for p, n in (live_paths - ours_paths).items()}
    assert only_ours == {}
    assert all(p.split("/")[-1] in COSMETIC_TAGS | SCHEMA_ADDED_PATHS for p in only_live), only_live

    # Every parameter value equals Live's, to float32 precision.
    def values(root):
        seen = Counter()
        out = {}

        def walk(el, prefix):
            p = prefix + "/" + el.tag
            manual = el.find("Manual")
            if manual is not None:
                out[(p, seen[p])] = manual.get("Value")
                seen[p] += 1
            for ch in el:
                walk(ch, p)

        walk(root, "")
        return out

    ours_values, live_values = values(ours), values(theirs)
    assert set(ours_values) == set(live_values)
    mismatches = []
    for key, a in ours_values.items():
        b = live_values[key]
        if a == b:
            continue
        try:
            if math.isclose(float(a), float(b), rel_tol=1e-5, abs_tol=1e-9):
                continue
        except ValueError:
            pass
        mismatches.append((key[0].split("/")[-1], a, b))
    assert mismatches == []
