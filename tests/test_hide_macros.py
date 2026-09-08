"""Tests for hiding the macro panel (``macro_mapping.hide_macros`` and ``hide_macros_batch``)."""

import re
import xml.etree.ElementTree as ET

import pytest

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.macro_mapping.hide_macros import (
    default_macro_name,
    hide_macros,
    root_device_span,
    verify_hide,
)
from ableton_device_creator.macro_mapping.hide_macros_batch import hide_macros_tree, write_report

from test_unmap import (  # the same synthetic presets the unmap tests use
    MACRO_NAMES,
    MACRO_VALUES,
    synthetic_drum_rack,
    synthetic_instrument_rack,
)

NAME_RE = re.compile(r'<MacroDisplayNames\.(\d+) Value="([^"]*)"\s*/>')
VIS_RE = re.compile(r'<AreMacroControlsVisible Value="(\w+)"\s*/>')


def with_visible_panel(xml: str, value: str = "true") -> str:
    """Add the panel flag the way Live writes it, right after the root's macro names."""
    marker = '<MacroDisplayNames.15 Value="Macro 16" />'
    at = xml.index(marker) + len(marker)
    return xml[:at] + '\n\t\t\t<AreMacroControlsVisible Value="%s" />' % value + xml[at:]


def root_names(xml: str):
    _, start, end = root_device_span(xml)
    return [v for _, v in NAME_RE.findall(xml[start:end])]


# --------------------------------------------------------------------------- #
# Pure functions
# --------------------------------------------------------------------------- #


def test_root_device_span_stops_at_the_first_nested_rack():
    xml = synthetic_drum_rack(with_nested=True)
    tag, start, end = root_device_span(xml)
    assert tag == "DrumGroupDevice"
    assert xml[start:].startswith('<DrumGroupDevice Id="0">')
    assert "InstrumentGroupDevice" not in xml[start:end]
    assert "InstrumentGroupDevice" in xml[end:]


def test_hides_panel_and_resets_root_names():
    xml = with_visible_panel(synthetic_drum_rack())
    out, report = hide_macros(xml)

    assert report.root_class == "DrumGroupDevice"
    assert report.changed and report.hidden and report.was_visible is True
    assert dict(report.renamed) == MACRO_NAMES
    assert root_names(out) == [default_macro_name(n) for n in range(16)]
    assert VIS_RE.findall(out) == ["false"]
    assert verify_hide(xml, out, report) == []
    ET.fromstring(out)


def test_leaves_a_nested_racks_own_names_and_panel_alone():
    xml = with_visible_panel(synthetic_drum_rack(with_nested=True))
    xml = xml.replace(
        '<MacroDisplayNames.0 Value="Inner" />',
        '<MacroDisplayNames.0 Value="Inner" />\n<AreMacroControlsVisible Value="true" />',
    )
    out, report = hide_macros(xml)

    assert report.changed
    assert 'Value="Inner"' in out  # the nested Instrument Rack keeps its name
    assert VIS_RE.findall(out) == ["false", "true"]  # and its open panel
    assert verify_hide(xml, out, report) == []


def test_macro_values_and_defaults_survive():
    xml = with_visible_panel(synthetic_drum_rack())
    out, _ = hide_macros(xml)
    tree = ET.fromstring(out)
    root = tree.find("./GroupDevicePreset/Device/DrumGroupDevice")
    for index, value in MACRO_VALUES.items():
        assert root.find("MacroControls.%d/Manual" % index).get("Value") == value
    assert root.find("MacroDefaults.1").get("Value") == "63.5"
    assert root.find("MacroDefaults.6").get("Value") == "-1"


def test_mappings_and_pads_survive():
    xml = with_visible_panel(synthetic_drum_rack())
    out, _ = hide_macros(xml)
    assert out.count("<KeyMidi>") == xml.count("<KeyMidi>")
    assert out.count("<DrumBranchPreset ") == xml.count("<DrumBranchPreset ")
    assert out.count("<DrumCell ") == xml.count("<DrumCell ")


@pytest.mark.parametrize("with_drum_rack", [False, True])
def test_instrument_rack_is_untouched(with_drum_rack):
    xml = with_visible_panel(synthetic_instrument_rack(with_drum_rack))
    xml = xml.replace('<MacroDisplayNames.0 Value="Macro 1" />', '<MacroDisplayNames.0 Value="X" />')
    out, report = hide_macros(xml)

    assert out == xml
    assert not report.changed
    assert report.root_class == "InstrumentGroupDevice"
    assert "not a Drum Rack" in report.reason
    assert verify_hide(xml, out, report) == []


def test_already_hidden_with_default_names_is_a_no_op():
    xml = with_visible_panel(synthetic_drum_rack(), value="false")
    for index, name in MACRO_NAMES.items():
        xml = xml.replace(
            '<MacroDisplayNames.%d Value="%s" />' % (index, name),
            '<MacroDisplayNames.%d Value="%s" />' % (index, default_macro_name(index)),
        )
    out, report = hide_macros(xml)

    assert out == xml and not report.changed
    assert report.reason == "already hidden with default names"


def test_a_rack_with_no_panel_flag_is_renamed_only():
    xml = synthetic_drum_rack()  # the fixture carries no AreMacroControlsVisible
    out, report = hide_macros(xml)

    assert report.changed and not report.hidden and report.was_visible is None
    assert root_names(out) == [default_macro_name(n) for n in range(16)]
    assert verify_hide(xml, out, report) == []


def test_verify_catches_a_tampered_result():
    xml = with_visible_panel(synthetic_drum_rack())
    out, report = hide_macros(xml)
    tampered = out.replace('<MacroControls.3>', '<MacroControls.3 >', 1)
    assert verify_hide(xml, tampered, report) != []


# --------------------------------------------------------------------------- #
# Batch runner
# --------------------------------------------------------------------------- #


def build_tree(root):
    (root / "Kits").mkdir(parents=True)
    encode_adg(with_visible_panel(synthetic_drum_rack()), root / "Kits" / "kit.adg")
    encode_adg(with_visible_panel(synthetic_instrument_rack(True)), root / "Kits" / "inst.adg")
    (root / "Kits" / "notes.txt").write_text("not a preset", encoding="utf-8")
    return root


def test_tree_dry_run_writes_nothing(tmp_path):
    root = build_tree(tmp_path / "src")
    before = (root / "Kits" / "kit.adg").read_bytes()

    report = hide_macros_tree(root, dry_run=True)

    assert report.totals["drum_racks"] == 1
    assert report.totals["processed"] == 1
    assert report.totals["skipped_InstrumentGroupDevice"] == 1
    assert report.totals["failed"] == 0
    assert (root / "Kits" / "kit.adg").read_bytes() == before


def test_tree_in_place_edits_only_the_drum_rack(tmp_path):
    root = build_tree(tmp_path / "src")
    inst_before = (root / "Kits" / "inst.adg").read_bytes()

    report = hide_macros_tree(root, in_place=True)

    assert report.totals["processed"] == 1 and report.totals["failed"] == 0
    assert report.totals["panels_hidden"] == 1
    assert report.totals["names_reset"] == len(MACRO_NAMES)
    kit = decode_adg(root / "Kits" / "kit.adg")
    assert VIS_RE.findall(kit)[0] == "false"
    assert root_names(kit) == [default_macro_name(n) for n in range(16)]
    assert (root / "Kits" / "inst.adg").read_bytes() == inst_before
    assert list(root.rglob("*adc-tmp*")) == []


def test_tree_out_dir_is_a_drop_in_replacement(tmp_path):
    root = build_tree(tmp_path / "src")
    out = tmp_path / "out"

    report = hide_macros_tree(root, out)

    assert report.totals["copied_unchanged_adg"] == 1  # the Instrument Rack
    assert report.totals["copied_unchanged_other"] == 1  # notes.txt
    assert sorted(p.relative_to(out) for p in out.rglob("*") if p.is_file()) == sorted(
        p.relative_to(root) for p in root.rglob("*") if p.is_file()
    )
    assert VIS_RE.findall(decode_adg(out / "Kits" / "kit.adg"))[0] == "false"
    assert (out / "Kits" / "inst.adg").read_bytes() == (root / "Kits" / "inst.adg").read_bytes()
    assert decode_adg(root / "Kits" / "kit.adg") == with_visible_panel(synthetic_drum_rack())


def test_tree_refuses_to_write_over_the_source(tmp_path):
    root = build_tree(tmp_path / "src")
    with pytest.raises(ValueError, match="must not be the source tree"):
        hide_macros_tree(root, root)
    with pytest.raises(ValueError, match="mutually exclusive"):
        hide_macros_tree(root, tmp_path / "out", in_place=True)


def test_tree_refuses_to_overwrite_existing_output(tmp_path):
    root = build_tree(tmp_path / "src")
    out = tmp_path / "out"
    hide_macros_tree(root, out)
    with pytest.raises(FileExistsError):
        hide_macros_tree(root, out)
    hide_macros_tree(root, out, overwrite=True)  # allowed when asked for


def test_tree_reports_a_broken_file_and_carries_on(tmp_path):
    root = build_tree(tmp_path / "src")
    (root / "Kits" / "broken.adg").write_bytes(b"not gzip at all")

    report = hide_macros_tree(root, in_place=True)

    assert report.totals["failed"] == 1
    assert report.totals["processed"] == 1
    assert (root / "Kits" / "broken.adg").read_bytes() == b"not gzip at all"


def test_report_json_round_trips(tmp_path):
    import json

    root = build_tree(tmp_path / "src")
    report = hide_macros_tree(root, dry_run=True)
    path = write_report(report, tmp_path / "report.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["dry_run"] is True
    assert data["totals"]["drum_racks"] == 1
    assert len(data["files"]) == 2
