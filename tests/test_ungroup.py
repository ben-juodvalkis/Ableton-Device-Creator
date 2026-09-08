"""Tests for dissolving a pad's nested rack (``drum_racks.ungroup`` and ``ungroup_batch``)."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.drum_racks.ungroup import (
    BOOL_THRESHOLDS,
    PARAM_RANGES,
    ungroup_pads,
    verify_ungroup,
)
from ableton_device_creator.drum_racks.ungroup_batch import ungroup_tree, write_report

from test_unmap import (  # the same synthetic presets the unmap tests use
    synthetic_drum_rack,
    synthetic_instrument_rack,
)

# Live 12.4.1's own ungroup of one Session Drums Club pad: an Instrument Rack
# over a Sampler and an EQ Eight, 16 mappings. Only on the machine it was
# measured on; the synthetic tests above cover the same ground everywhere.
GOLDEN_DIR = Path("/Users/Music/Desktop/test Project/New Folder")
GOLDEN_GROUPED = GOLDEN_DIR / "before.adg"
GOLDEN_UNGROUPED = GOLDEN_DIR / "After.adg"

# Differences Live writes on any resave, unrelated to the ungroup itself: the
# round-robin seed is re-rolled, and an off Shaper's slot payload is dropped.
INCIDENTAL = ("RoundRobinRandomSeed", "SimplerShaper")


def pads(xml: str):
    return list(ET.fromstring(xml).iter("DrumBranchPreset"))


def pad_devices(pad: ET.Element):
    """The plain devices sitting directly on the pad, racks excluded."""
    out = []
    presets = pad.find("DevicePresets")
    for p in presets if presets is not None else []:
        if p.tag != "AbletonDevicePreset":
            continue
        d = p.find("Device")
        if d is not None and len(d):
            out.append(d[0].tag)
    return out


# --------------------------------------------------------------------------- #
# The transform
# --------------------------------------------------------------------------- #


def test_lifts_the_chains_devices_into_the_pad():
    xml = synthetic_drum_rack(with_nested=True)
    assert pad_devices(pads(xml)[2]) == []  # the pad holds a GroupDevicePreset, not a device

    out, report = ungroup_pads(xml)

    assert report.is_drum_rack and report.ungrouped == 1
    assert pad_devices(pads(out)[2]) == ["OriginalSimpler"]
    assert ET.fromstring(out).find(".//DrumBranchPreset/DevicePresets/GroupDevicePreset") is None
    assert not verify_ungroup(xml, out, report)


def test_pads_without_a_nested_rack_are_left_alone():
    xml = synthetic_drum_rack(with_nested=True)
    out, report = ungroup_pads(xml)

    plain = [p for p in report.pads if p.skipped]
    assert [p.skipped for p in plain] == ["no nested rack on this pad"] * 2
    for i in (0, 1):
        assert ET.tostring(pads(out)[i]) == ET.tostring(pads(xml)[i])


def test_mappings_that_addressed_the_dissolved_rack_go():
    xml = synthetic_drum_rack(with_nested=True)
    out, report = ungroup_pads(xml)

    plan = next(p for p in report.pads if not p.skipped)
    # The Simpler's TransposeKey rode the nested rack's macro 1; that macro is gone.
    assert plan.key_midi_removed == 1
    # The nested rack's own macro 1 was chained to root macro 16; the chain dies
    # with the wrapper, not with a lifted device.
    assert plan.key_midi_dropped_with_chain == 1
    assert plan.key_midi_kept == 0

    simpler = ET.fromstring(out).find(".//OriginalSimpler")
    assert simpler.find("TransposeKey/KeyMidi") is None
    # The mappings on the other pads' DrumCells are untouched: they address the
    # root rack, which is still there.
    assert (
        len(list(ET.fromstring(out).iter("KeyMidi")))
        == len(list(ET.fromstring(xml).iter("KeyMidi"))) - 2
    )


def test_stored_values_are_never_touched():
    """Nothing a lifted device sounds by moves. The wrapper's own macros do go -
    that is what dissolving it means - so only the devices are compared."""
    xml = synthetic_drum_rack(with_nested=True)
    out, _ = ungroup_pads(xml)

    def manuals(text, tag):
        device = ET.fromstring(text).find(".//%s" % tag)
        return [
            (e.tag, e.find("Manual").get("Value"))
            for e in device.iter()
            if e.find("Manual") is not None
        ]

    assert manuals(out, "OriginalSimpler") == manuals(xml, "OriginalSimpler")
    assert manuals(out, "DrumCell") == manuals(xml, "DrumCell")


def test_a_freed_parameters_range_is_reported_when_it_is_not_measured():
    xml = synthetic_drum_rack(with_nested=True)
    _, report = ungroup_pads(xml)

    # No measured full range for a Simpler's TransposeKey, so it keeps its own.
    assert ("OriginalSimpler", "TransposeKey") not in PARAM_RANGES
    assert report.ranges_left == ["OriginalSimpler TransposeKey"]
    assert report.ranges_reset == 0


def test_a_measured_range_is_reset():
    xml = synthetic_drum_rack(with_nested=True).replace("OriginalSimpler", "MultiSampler")
    xml = xml.replace("<TransposeKey>", "<Pitch>\n<TransposeKey>").replace(
        "</TransposeKey>", "</TransposeKey>\n</Pitch>"
    )
    out, report = ungroup_pads(xml)

    assert report.ranges_reset == 1 and report.ranges_left == []
    rng = ET.fromstring(out).find(".//MultiSampler/Pitch/TransposeKey/MidiControllerRange")
    got = (rng.find("Min").get("Value"), rng.find("Max").get("Value"))
    assert got == PARAM_RANGES[("MultiSampler", "Pitch/TransposeKey")] == ("-48", "48")


def test_an_on_off_parameters_thresholds_go_back_to_the_default():
    xml = synthetic_drum_rack(with_nested=True).replace(
        '<TransposeKey>\n\t\t\t\t\t\t\t\t\t<LomId Value="0" />',
        '<TransposeKey>\n\t\t\t\t\t\t\t\t\t<LomId Value="0" />',
    )
    # Give the Simpler a mapped switch with an inverted threshold pair.
    xml = xml.replace(
        "</OriginalSimpler>",
        "\n".join(
            [
                "<IsOn>",
                '<KeyMidi><PersistentKeyString Value="" /><IsNote Value="false" />'
                '<Channel Value="16" /><NoteOrController Value="1" />'
                '<LowerRangeNote Value="-1" /><UpperRangeNote Value="-1" />'
                '<ControllerMapMode Value="0" /></KeyMidi>',
                '<Manual Value="true" />',
                "<MidiCCOnOffThresholds>",
                '<Min Value="127" /><Max Value="126" />',
                "</MidiCCOnOffThresholds>",
                "</IsOn>",
                "</OriginalSimpler>",
            ]
        ),
    )
    out, report = ungroup_pads(xml)

    simpler = ET.fromstring(out).find(".//OriginalSimpler")
    thresholds = simpler.find("IsOn/MidiCCOnOffThresholds")
    got = (thresholds.find("Min").get("Value"), thresholds.find("Max").get("Value"))
    assert got == BOOL_THRESHOLDS == ("64", "127")
    assert simpler.find("IsOn/Manual").get("Value") == "true"  # the value itself stands
    assert report.ranges_reset == 1


def test_the_racks_own_settings_survive():
    xml = synthetic_drum_rack(with_nested=True)
    out, _ = ungroup_pads(xml)
    before, after = ET.fromstring(xml), ET.fromstring(out)

    for tag in ("MacroControls.3", "MacroDisplayNames.0", "MacroDefaults.0"):
        b = before.find("GroupDevicePreset/Device/DrumGroupDevice/%s" % tag)
        a = after.find("GroupDevicePreset/Device/DrumGroupDevice/%s" % tag)
        assert ET.tostring(b) == ET.tostring(a)


def test_the_result_is_well_formed_and_indented_to_the_pad():
    xml = synthetic_drum_rack(with_nested=True)
    out, _ = ungroup_pads(xml)
    ET.fromstring(out)  # parses

    was = next(
        line for line in xml.split("\n") if "<GroupDevicePreset" in line and "\t\t\t" in line
    )
    now = next(line for line in out.split("\n") if "<AbletonDevicePreset" in line)
    assert len(was) - len(was.lstrip("\t")) == len(now) - len(now.lstrip("\t"))


# --------------------------------------------------------------------------- #
# What it refuses to do
# --------------------------------------------------------------------------- #


def test_an_instrument_rack_preset_is_skipped_whole():
    xml = synthetic_instrument_rack(with_drum_rack=False)
    out, report = ungroup_pads(xml)

    assert out == xml
    assert not report.is_drum_rack and report.ungrouped == 0
    assert "not a Drum Rack" in report.reason


def test_a_second_chain_stops_the_pad():
    xml = synthetic_drum_rack(with_nested=True)
    one = '<InstrumentBranchPreset Id="0">'
    body_start = xml.index(one)
    body_end = xml.index("</InstrumentBranchPreset>", body_start) + len("</InstrumentBranchPreset>")
    xml = xml[:body_end] + "\n" + xml[body_start:body_end] + xml[body_end:]

    out, report = ungroup_pads(xml)

    assert out == xml and report.ungrouped == 0
    assert report.pads[2].skipped == "rack has 2 chains; only a single chain can be lifted"


def test_a_non_unity_chain_mixer_stops_the_pad():
    xml = synthetic_drum_rack(with_nested=True).replace(
        "\t\t\t\t</InstrumentBranchPreset>",
        "\n".join(
            [
                "\t\t\t\t\t<MixerPreset>",
                "\t\t\t\t\t\t<AbletonDevicePreset>",
                "\t\t\t\t\t\t\t<Device>",
                '\t\t\t\t\t\t\t\t<AudioBranchMixerDevice Id="0">',
                "\t\t\t\t\t\t\t\t\t<Volume>",
                '\t\t\t\t\t\t\t\t\t\t<Manual Value="0.5" />',
                "\t\t\t\t\t\t\t\t\t</Volume>",
                "\t\t\t\t\t\t\t\t</AudioBranchMixerDevice>",
                "\t\t\t\t\t\t\t</Device>",
                "\t\t\t\t\t\t</AbletonDevicePreset>",
                "\t\t\t\t\t</MixerPreset>",
                "\t\t\t\t</InstrumentBranchPreset>",
            ]
        ),
    )
    out, report = ungroup_pads(xml)

    assert out == xml and report.ungrouped == 0
    assert report.pads[2].skipped == "chain volume is 0.5, not 1"


def test_a_partial_key_range_stops_the_pad():
    xml = synthetic_drum_rack(with_nested=True).replace(
        "\t\t\t\t</InstrumentBranchPreset>",
        "\n".join(
            [
                "\t\t\t\t\t<ZoneSettings>",
                "\t\t\t\t\t\t<KeyRange>",
                '\t\t\t\t\t\t\t<Min Value="36" />',
                '\t\t\t\t\t\t\t<Max Value="72" />',
                "\t\t\t\t\t\t</KeyRange>",
                "\t\t\t\t\t</ZoneSettings>",
                "\t\t\t\t</InstrumentBranchPreset>",
            ]
        ),
    )
    out, report = ungroup_pads(xml)

    assert out == xml and report.ungrouped == 0
    assert "key range is 36-72" in report.pads[2].skipped


def test_a_nested_drum_rack_is_not_dissolved():
    xml = synthetic_drum_rack(with_nested=True).replace("InstrumentGroupDevice", "DrumGroupDevice")
    out, report = ungroup_pads(xml)

    assert out == xml and report.ungrouped == 0
    assert "cannot be dissolved" in report.pads[2].skipped


def test_verify_catches_a_tampered_result():
    xml = synthetic_drum_rack(with_nested=True)
    out, report = ungroup_pads(xml)
    assert not verify_ungroup(xml, out, report)

    tampered = out.replace('<Manual Value="0" />', '<Manual Value="12" />', 1)
    assert verify_ungroup(xml, tampered, report)


def test_verify_catches_a_dropped_device():
    xml = synthetic_drum_rack(with_nested=True)
    out, report = ungroup_pads(xml)
    start = out.index('<AbletonDevicePreset Id="0">', out.index("OriginalSimpler") - 4000)
    end = out.index("</AbletonDevicePreset>", start) + len("</AbletonDevicePreset>")
    assert verify_ungroup(xml, out[:start] + out[end:], report)


# --------------------------------------------------------------------------- #
# Batch
# --------------------------------------------------------------------------- #


def write_preset(path: Path, xml: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(xml, path)
    return path


def test_tree_dry_run_writes_nothing(tmp_path):
    src = tmp_path / "src"
    write_preset(src / "kit.adg", synthetic_drum_rack(with_nested=True))
    before = (src / "kit.adg").read_bytes()

    report = ungroup_tree(src, dry_run=True)

    assert report.totals["pads_ungrouped"] == 1
    assert (src / "kit.adg").read_bytes() == before


def test_tree_out_dir_is_a_drop_in_replacement(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    write_preset(src / "kit.adg", synthetic_drum_rack(with_nested=True))
    write_preset(src / "sub" / "instrument.adg", synthetic_instrument_rack(with_drum_rack=False))
    (src / "notes.txt").write_text("hello")

    report = ungroup_tree(src, out)

    assert report.totals["pads_ungrouped"] == 1
    assert sorted(p.name for p in out.rglob("*") if p.is_file()) == [
        "instrument.adg",
        "kit.adg",
        "notes.txt",
    ]
    # Untouched files come through byte for byte.
    assert (out / "sub" / "instrument.adg").read_bytes() == (
        src / "sub" / "instrument.adg"
    ).read_bytes()
    assert (out / "notes.txt").read_text() == "hello"
    assert "InstrumentGroupDevice" not in decode_adg(out / "kit.adg")


def test_tree_in_place_rewrites_the_source(tmp_path):
    src = tmp_path / "src"
    write_preset(src / "kit.adg", synthetic_drum_rack(with_nested=True))

    report = ungroup_tree(src, in_place=True)

    assert report.totals["failed"] == 0
    assert "InstrumentGroupDevice" not in decode_adg(src / "kit.adg")
    assert not list(src.rglob("*adc-tmp*"))


def test_a_single_file_is_written_beside_itself(tmp_path):
    kit = write_preset(tmp_path / "British Vintage.adg", synthetic_drum_rack(with_nested=True))

    report = ungroup_tree(kit)

    out = tmp_path / "British Vintage (ungrouped).adg"
    assert out.exists() and report.files[0].output == str(out)
    assert "InstrumentGroupDevice" not in decode_adg(out)
    assert "InstrumentGroupDevice" in decode_adg(kit)  # the original stands


def test_tree_refuses_to_write_over_the_source(tmp_path):
    src = tmp_path / "src"
    write_preset(src / "kit.adg", synthetic_drum_rack(with_nested=True))
    with pytest.raises(ValueError):
        ungroup_tree(src, src)


def test_tree_reports_a_broken_file_and_carries_on(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    (src).mkdir()
    (src / "broken.adg").write_bytes(b"not gzip")
    write_preset(src / "kit.adg", synthetic_drum_rack(with_nested=True))

    report = ungroup_tree(src, out)

    assert report.totals["failed"] == 1 and report.totals["pads_ungrouped"] == 1
    assert (out / "broken.adg").read_bytes() == b"not gzip"  # copied through unchanged


def test_report_json_round_trips(tmp_path):
    src = tmp_path / "src"
    write_preset(src / "kit.adg", synthetic_drum_rack(with_nested=True))
    report = ungroup_tree(src, dry_run=True)

    path = write_report(report, tmp_path / "report.json")
    import json

    data = json.loads(path.read_text())
    assert data["totals"]["pads_ungrouped"] == 1
    assert data["files"][0]["devices_lifted"] == {"OriginalSimpler": 1}


# --------------------------------------------------------------------------- #
# The golden pair
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(
    not (GOLDEN_GROUPED.exists() and GOLDEN_UNGROUPED.exists()),
    reason="golden pair not on this machine",
)
def test_golden_pair_matches_live_ungroup():
    """Live's own ungroup of the pair, line for line bar the incidental resave fields."""
    original = decode_adg(GOLDEN_GROUPED)
    live = decode_adg(GOLDEN_UNGROUPED)
    mine, report = ungroup_pads(original)

    assert not verify_ungroup(original, mine, report)
    assert report.ungrouped == 1
    assert report.pads[0].devices == ["MultiSampler", "Eq8"]
    assert report.key_midi_removed == 15
    assert report.pads[0].key_midi_dropped_with_chain == 1  # the chain mixer's volume
    assert report.ranges_reset == 14

    import difflib

    hunks = [
        line
        for line in difflib.unified_diff(live.split("\n"), mine.split("\n"), n=0)
        if line[:1] in "+-" and line[:3] not in ("+++", "---")
    ]
    assert hunks, "expected the two incidental differences"
    blocks = "\n".join(hunks)
    assert all(field in blocks for field in INCIDENTAL), blocks
    # Nothing else: every changed line belongs to one of those two.
    for line in hunks:
        assert (
            "RoundRobinRandomSeed" in line
            or "<Value" in line
            or "SimplerShaper" in line
            or line.lstrip("+-\t").startswith(
                (
                    "<Type>",
                    "</Type>",
                    "<Amount>",
                    "</Amount>",
                    "<Structure>",
                    "</Structure>",
                    "<LomId",
                    "<Manual",
                    "<AutomationTarget",
                    "</AutomationTarget>",
                    "<LockEnvelope",
                    "<MidiControllerRange>",
                    "</MidiControllerRange>",
                    "<MidiCCOnOffThresholds>",
                    "</MidiCCOnOffThresholds>",
                    "<Min ",
                    "<Max ",
                    "<ModulationTarget",
                    "</ModulationTarget>",
                    "</SimplerShaper>",
                    "</Value>",
                )
            )
        ), line
