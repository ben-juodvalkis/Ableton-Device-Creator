"""
Turn a Drum Rack's Auto-Select on or off, string-level.

One field on the rack's *root* device, and nothing else:

    <IsAutoSelectEnabled Value="true" />

That is Live's Auto-Select toggle in the rack's chain list: with it on, playing a
pad selects that pad in the rack view, so the device panel follows whatever is
being played. It is a view preference - no parameter, no mapping and no sample
reference is involved, so a rack sounds exactly the same either way.

Measured on a Live 12.4.1 before/after pair (``Kit-Carbon``, 2026-09-11): the
toggle rewrites that one field on the root device and nothing else. Live's
resave of the same file also rewrote the preset's own ``RelativePath``/``Path``
provenance and ``UserName`` - incidental to the file having been copied out of
the User Library, not to the toggle, so neither is reproduced here.

Scope is the root device only, which is what Live itself does: the nested
devices inside the measured kit's pads kept their own Auto-Select state when the
outer kit's was switched on. A preset whose root is an Instrument Rack is left
alone entirely.

**``IsAutoSelectEnabled`` is not only a rack field, so it cannot be found by
searching for the tag.** A Sampler carries one of its own, under
``MultiSampler/ViewSettings`` - the Sampler's zone view follows what is played,
the same idea one level down. A Latin perc kit whose 32 pads each hold a bare
Sampler has 33 of them in the file, and ``Perc/Latin/Conga A`` has exactly that
(measured 2026-09-11). The two are indistinguishable by tag:

    DrumGroupDevice/IsAutoSelectEnabled                    <- the rack's own
    .../AbletonDevicePreset/Device/MultiSampler/ViewSettings/IsAutoSelectEnabled

The target is therefore resolved structurally with ElementTree - the direct
child of the preset's root group device - and then located in the text by
document-order index, which is exact because ``Element.iter()`` and a
left-to-right scan of the text visit elements in the same order. This is the
same resolution the Sampler envelope module uses for the four ``AttackTime``
fields, and for the same reason.

A root Drum Rack that carries no ``IsAutoSelectEnabled`` at all is reported
rather than repaired - where the field would belong in an older schema is a
guess, and a guess is not worth making for a view preference.

Edits are made on the XML text with anchored regular expressions. The file is
never re-serialised through ElementTree (re-serialised Live 12 files parse but
do not load); ElementTree is used read-only, to locate and to verify.

The functions in this module perform no I/O.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..macro_mapping.unmap import GROUP_DEVICE_TAGS

__all__ = [
    "AutoSelectReport",
    "root_auto_select_index",
    "set_auto_select",
    "verify_auto_select",
]

_AUTO_SELECT = re.compile(r"<IsAutoSelectEnabled Value=\"(\w+)\"\s*/>")
_FIELD = "IsAutoSelectEnabled"


def root_auto_select_index(xml: str) -> Tuple[Optional[str], Optional[int], List[Tuple[int, int]]]:
    """Locate the root group device's own ``IsAutoSelectEnabled``.

    Returns ``(root device tag, index, spans)`` where ``index`` counts
    ``IsAutoSelectEnabled`` elements in document order - so ``spans[index]`` is
    the field's text span - and ``spans`` holds every occurrence in the text.
    The tag is ``None`` when the preset has no group device at its root, and the
    index is ``None`` when that device carries no such field of its own.

    Raises ``ValueError`` when the parsed elements cannot be aligned with the
    text, which would make any index meaningless.
    """
    spans = [m.span() for m in _AUTO_SELECT.finditer(xml)]
    tree = ET.fromstring(xml)
    elements = [el for el in tree.iter() if el.tag == _FIELD]
    if len(elements) != len(spans):
        raise ValueError(
            "cannot align <%s> elements with the text: %d parsed, %d in the text"
            % (_FIELD, len(elements), len(spans))
        )

    device = next((el for el in tree.iter() if el.tag in GROUP_DEVICE_TAGS), None)
    if device is None:
        return None, None, spans
    own = next((child for child in device if child.tag == _FIELD), None)
    if own is None:
        return device.tag, None, spans
    return device.tag, elements.index(own), spans


@dataclass
class AutoSelectReport:
    """What ``set_auto_select`` did to one preset."""

    root_class: str = ""
    wanted: bool = True
    was_enabled: Optional[bool] = None
    index: Optional[int] = None  # which IsAutoSelectEnabled, in document order
    total_fields: int = 0  # how many the file holds in all (racks and Samplers)
    changed: bool = False
    reason: str = ""  # why nothing was done, when nothing was done

    @property
    def is_drum_rack(self) -> bool:
        return self.root_class == "DrumGroupDevice"


def set_auto_select(xml: str, enabled: bool = True) -> Tuple[str, AutoSelectReport]:
    """Set Auto-Select on a preset's root Drum Rack.

    Returns the edited XML and a report. A preset that is not a root Drum Rack,
    or one already in the requested state, comes back unchanged with
    ``report.changed`` false and ``report.reason`` saying why.
    """
    root_class, index, spans = root_auto_select_index(xml)
    if root_class is None:
        return xml, AutoSelectReport(wanted=enabled, reason="no group device at the root")
    report = AutoSelectReport(
        root_class=root_class, wanted=enabled, index=index, total_fields=len(spans)
    )
    if root_class != "DrumGroupDevice":
        report.reason = "root device is %s, not a Drum Rack" % root_class
        return xml, report
    if index is None:
        report.reason = "root device has no IsAutoSelectEnabled field"
        return xml, report

    start, end = spans[index]
    report.was_enabled = _AUTO_SELECT.match(xml, start).group(1) == "true"
    if report.was_enabled == enabled:
        report.reason = "already %s" % ("on" if enabled else "off")
        return xml, report

    replacement = '<IsAutoSelectEnabled Value="%s" />' % ("true" if enabled else "false")
    report.changed = True
    return xml[:start] + replacement + xml[end:], report


def verify_auto_select(original: str, result: str, report: AutoSelectReport) -> List[str]:
    """Check ``result`` against ``original``. Returns a list of failures, empty when clean.

    Confirms the result still parses, that every byte outside the
    ``IsAutoSelectEnabled`` fields is unchanged, that exactly one of those fields
    moved, that it is the root Drum Rack's own, and that it now holds the
    requested value. Every other one in the file - each pad Sampler's zone-view
    setting among them - must come back identical.
    """
    failures: List[str] = []
    if not report.changed:
        if result != original:
            failures.append("no change was reported but the text differs")
        return failures

    try:
        root_class, index, spans = root_auto_select_index(result)
    except (ET.ParseError, ValueError) as e:
        return ["result could not be read back: %s" % e]
    if root_class is None:
        return ["result has no group device at its root"]
    if root_class != report.root_class:
        failures.append("root device changed: %s -> %s" % (report.root_class, root_class))
    if index != report.index:
        failures.append("root Auto-Select moved: index %s -> %s" % (report.index, index))
    if len(spans) != report.total_fields:
        failures.append(
            "file holds %d IsAutoSelectEnabled fields, was %d" % (len(spans), report.total_fields)
        )

    # Everything that is not one of these fields must be byte-identical, and the
    # values must differ at exactly the one index that was targeted.
    strip = lambda text: _AUTO_SELECT.sub("", text)  # noqa: E731
    if strip(original) != strip(result):
        failures.append("something other than an Auto-Select field changed")

    o_values, r_values = _AUTO_SELECT.findall(original), _AUTO_SELECT.findall(result)
    if len(o_values) != len(r_values):
        failures.append("the number of Auto-Select fields changed")
        return failures
    moved = [i for i, (o, r) in enumerate(zip(o_values, r_values)) if o != r]
    if moved != [report.index]:
        failures.append(
            "Auto-Select changed at %s, expected only the root device at %s"
            % (moved, report.index)
        )
        return failures
    want = "true" if report.wanted else "false"
    if r_values[report.index] != want:
        failures.append("root Auto-Select is %s, expected %s" % (r_values[report.index], want))
    return failures
