"""
Fold a Drum Rack's macro panel away and drop its custom macro names, string-level.

Two fields on the rack's *root* device, and nothing else:

1. ``<AreMacroControlsVisible Value="false" />`` - the macro panel is hidden;
2. ``<MacroDisplayNames.N Value="Macro N+1" />`` - the custom names go back to
   Live's defaults.

Measured on a Live 12.4.15 before/after pair (``Acuff Kit``, 2026-09-08): those
two fields are the whole gesture. Live's resave also rewrote ``MacroDefaults``,
``RoundRobinRandomSeed``, sample ``RelativePath``s and a Simpler range - all
incidental to the resave and to the file having moved, not to hiding macros, so
none of it is reproduced here.

Scope. Only presets whose *root* device is a Drum Rack are touched, and only
that root device's own two fields: a rack nested inside a pad keeps its names
and its panel state, and an Instrument Rack preset is left alone entirely.
Macro values, macro positions, ``NumVisibleMacroControls`` and mappings are all
untouched - this is a cosmetic edit.

Edits are made on the XML text with anchored regular expressions. The file is
never re-serialised through ElementTree (re-serialised Live 12 files parse but
do not load); ElementTree is used read-only, to classify and to verify.

The functions in this module perform no I/O.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .unmap import GROUP_DEVICE_TAGS

__all__ = [
    "HideReport",
    "default_macro_name",
    "root_device_span",
    "hide_macros",
    "verify_hide",
]

MACRO_COUNT = 16

_GROUP_DEVICE_OPEN = re.compile(
    r"<(%s)\s+Id=\"[-\d]+\">" % "|".join(sorted(GROUP_DEVICE_TAGS))
)
_MACRO_NAME = re.compile(r"<MacroDisplayNames\.(\d+) Value=\"([^\"]*)\"\s*/>")
_MACRO_VISIBLE = re.compile(r"<AreMacroControlsVisible Value=\"(\w+)\"\s*/>")


def default_macro_name(index: int) -> str:
    """Live's untouched name for macro ``index`` (0-based): ``Macro 1`` .. ``Macro 16``."""
    return "Macro %d" % (index + 1)


@dataclass
class HideReport:
    """What ``hide_macros`` did to one preset."""

    root_class: str = ""
    renamed: List[Tuple[int, str]] = field(default_factory=list)  # (macro index, old name)
    hidden: bool = False  # the panel was visible and is now hidden
    was_visible: Optional[bool] = None
    changed: bool = False
    reason: str = ""  # why nothing was done, when nothing was done

    @property
    def is_drum_rack(self) -> bool:
        return self.root_class == "DrumGroupDevice"


def root_device_span(xml: str) -> Optional[Tuple[str, int, int]]:
    """Locate the root group device: ``(tag, start, end)`` over the XML text.

    ``end`` is the start of the first *nested* group device, so the span holds
    the root device's own fields and none of its chains'. Returns ``None`` when
    the preset has no group device at its root (a plain ``.adv``, say).
    """
    first = _GROUP_DEVICE_OPEN.search(xml)
    if first is None:
        return None
    nxt = _GROUP_DEVICE_OPEN.search(xml, first.end())
    return first.group(1), first.start(), nxt.start() if nxt else len(xml)


def hide_macros(xml: str) -> Tuple[str, HideReport]:
    """Hide the macro panel and reset the macro names of a root Drum Rack.

    Returns the edited XML and a report. A preset that is not a root Drum Rack
    comes back unchanged, with ``report.changed`` false and ``report.reason``
    saying why.
    """
    span = root_device_span(xml)
    if span is None:
        return xml, HideReport(reason="no group device at the root")
    root_class, start, end = span
    report = HideReport(root_class=root_class)
    if root_class != "DrumGroupDevice":
        report.reason = "root device is %s, not a Drum Rack" % root_class
        return xml, report

    head, body, tail = xml[:start], xml[start:end], xml[end:]

    def rename(m: re.Match) -> str:
        index, old = int(m.group(1)), m.group(2)
        want = default_macro_name(index)
        if old == want:
            return m.group(0)
        report.renamed.append((index, old))
        return '<MacroDisplayNames.%d Value="%s" />' % (index, want)

    body = _MACRO_NAME.sub(rename, body)

    visible = _MACRO_VISIBLE.search(body)
    if visible is not None:
        report.was_visible = visible.group(1) == "true"
        if report.was_visible:
            body = (
                body[: visible.start()]
                + '<AreMacroControlsVisible Value="false" />'
                + body[visible.end() :]
            )
            report.hidden = True

    report.changed = bool(report.renamed) or report.hidden
    if not report.changed:
        report.reason = "already hidden with default names"
    return head + body + tail, report


def verify_hide(original: str, result: str, report: HideReport) -> List[str]:
    """Check ``result`` against ``original``. Returns a list of failures, empty when clean.

    Confirms the result still parses, that the root device is the same Drum Rack
    now carrying default names and a hidden panel, that nothing outside the root
    device's span moved, and that inside the span the only text that changed is
    the two fields this module owns.
    """
    failures: List[str] = []
    if not report.changed:
        if result != original:
            failures.append("no change was reported but the text differs")
        return failures

    try:
        tree = ET.fromstring(result)
    except ET.ParseError as e:
        return ["result is not well-formed XML: %s" % e]

    span = root_device_span(result)
    if span is None:
        return ["result has no group device at its root"]
    root_class, start, end = span
    if root_class != report.root_class:
        failures.append("root device changed: %s -> %s" % (report.root_class, root_class))

    original_span = root_device_span(original)
    if original_span is None or original_span[1] != start:
        failures.append("the root device no longer starts where it did")
        return failures
    _, o_start, o_end = original_span

    if original[:o_start] != result[:start]:
        failures.append("text before the root device changed")
    if original[o_end:] != result[end:]:
        failures.append("text after the root device changed")

    o_body, r_body = original[o_start:o_end], result[start:end]
    strip = lambda text: _MACRO_VISIBLE.sub("", _MACRO_NAME.sub("", text))  # noqa: E731
    if strip(o_body) != strip(r_body):
        failures.append("something other than the macro names and panel state changed")

    names = _MACRO_NAME.findall(r_body)
    if len(names) != MACRO_COUNT:
        failures.append("root device has %d macro names, expected %d" % (len(names), MACRO_COUNT))
    bad = [v for i, v in names if v != default_macro_name(int(i))]
    if bad:
        failures.append("macro names left non-default: %s" % ", ".join(bad))

    # A rack with no AreMacroControlsVisible at all (older schema) is renamed only.
    visible = _MACRO_VISIBLE.findall(r_body)
    if visible and visible[0] != "false":
        failures.append("root macro panel is not hidden: %s" % visible[0])

    # The root's own macro values must survive: this edit is cosmetic.
    o_vals = re.findall(r"<MacroControls\.\d+>.*?</MacroControls\.\d+>", o_body, re.S)
    r_vals = re.findall(r"<MacroControls\.\d+>.*?</MacroControls\.\d+>", r_body, re.S)
    if o_vals != r_vals:
        failures.append("root macro controls changed")

    del tree  # parsed only to prove the result is well-formed
    return failures
