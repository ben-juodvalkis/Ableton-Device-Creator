"""
Set a Sampler envelope parameter across every Sampler in a preset, string-level.

A Sampler holds four envelopes that all expose the same parameter names, so
"amp attack" cannot be found by searching for ``AttackTime`` - a 32-pad rack has
128 of them. Measured on the library (2026-09-11), one Sampler's four live at::

    MultiSampler/VolumeAndPan/Envelope/AttackTime      <- the amp envelope
    MultiSampler/.../SimplerFilter/Envelope/AttackTime
    MultiSampler/VolumeAndPan/Envelope/Slot/Value/SimplerPitchEnvelope/AttackTime
    MultiSampler/.../SimplerSubOsc/Envelope/AttackTime

Note the third: the pitch envelope is nested *inside* the amp envelope, so even
"the AttackTime inside VolumeAndPan/Envelope" is ambiguous by text. Targets are
therefore resolved structurally with ElementTree - direct child of direct child -
and then located in the text by document-order index, which is exact because
``Element.iter()`` and a left-to-right scan of the text visit elements in the
same order.

**A macro-mapped parameter is not changed by this.** Live ignores the stored
``Manual`` of a parameter a macro holds, so writing one would be inert; those are
counted and reported rather than written, the same way ``ungroup`` refuses to
fold a level into a macro-mapped fader. In the measured library 4300 of 14580
amp-attack parameters are mapped, nearly all of them in the Damage Close/Room
racks and Soundiron Shake.

Values are written in Live's own float32 style, so a value that is already
correct produces no edit at all and the file is left byte-identical.

The functions in this module perform no I/O.
"""

import re
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

__all__ = [
    "ENVELOPES",
    "EnvelopeReport",
    "format_value",
    "set_envelope_param",
    "verify_envelope_set",
]

#: Envelope name -> the chain of direct-child tags from ``MultiSampler`` down to
#: the envelope element that owns the parameters.
ENVELOPES: Dict[str, Tuple[str, ...]] = {
    "amp": ("VolumeAndPan", "Envelope"),
}

_MANUAL = re.compile(r"<Manual(\s[^>]*?)?/?>")
_VALUE_ATTR = re.compile(r'(\sValue=")([^"]*)(")')


def format_value(value: float) -> str:
    """Format a number the way Live stores a float parameter.

    Live's values are float32 printed to ten significant digits - 0.1 is stored
    as ``0.1000000015``. Round-tripping through float32 reproduces that exactly.
    """
    as_f32 = struct.unpack("<f", struct.pack("<f", float(value)))[0]
    text = "%.10g" % as_f32
    return text


@dataclass
class EnvelopeReport:
    """What a set across one preset did."""

    envelope: str = "amp"
    param: str = "AttackTime"
    value: str = ""
    samplers: int = 0
    written: int = 0
    already_correct: int = 0
    mapped: int = 0  # macro-held: Live ignores the stored value, so left alone
    missing: int = 0  # Sampler has no such parameter
    old_values: Dict[str, int] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return self.written > 0


def _descend(element: Optional[ET.Element], tags: Tuple[str, ...]) -> Optional[ET.Element]:
    """Follow a chain of *direct child* tags."""
    for tag in tags:
        if element is None:
            return None
        element = element.find(tag)
    return element


def _manual_spans(xml: str) -> List[Tuple[int, int]]:
    """Text span of every ``<Manual ...>`` open tag, in document order."""
    return [m.span() for m in _MANUAL.finditer(xml)]


def set_envelope_param(
    xml: str,
    value: float,
    param: str = "AttackTime",
    envelope: str = "amp",
) -> Tuple[str, EnvelopeReport]:
    """Set one envelope parameter on every Sampler in a preset.

    Returns the new XML and a report. Parameters a macro holds are counted in
    ``report.mapped`` and left alone - Live would ignore the stored value.
    """
    if envelope not in ENVELOPES:
        raise ValueError(
            "unknown envelope %r; known: %s" % (envelope, ", ".join(sorted(ENVELOPES)))
        )
    text_value = format_value(value)
    report = EnvelopeReport(envelope=envelope, param=param, value=text_value)

    root = ET.fromstring(xml)
    manual_elements = [el for el in root.iter() if el.tag == "Manual"]
    spans = _manual_spans(xml)
    if len(manual_elements) != len(spans):
        raise ValueError(
            "cannot align <Manual> elements with the text: %d parsed, %d in the text"
            % (len(manual_elements), len(spans))
        )
    index_of = {id(el): i for i, el in enumerate(manual_elements)}

    targets: List[int] = []
    for sampler in root.iter("MultiSampler"):
        report.samplers += 1
        owner = _descend(sampler, ENVELOPES[envelope])
        parameter = owner.find(param) if owner is not None else None
        if parameter is None:
            report.missing += 1
            continue
        manual = parameter.find("Manual")
        if manual is None:
            report.missing += 1
            continue
        if parameter.find(".//KeyMidi") is not None:
            report.mapped += 1
            continue
        old = manual.get("Value")
        report.old_values[old] = report.old_values.get(old, 0) + 1
        if old == text_value:
            report.already_correct += 1
            continue
        targets.append(index_of[id(manual)])

    if not targets:
        return xml, report

    out: List[str] = []
    cursor = 0
    for i in sorted(targets):
        start, end = spans[i]
        tag = xml[start:end]
        new_tag, n = _VALUE_ATTR.subn(
            lambda m: m.group(1) + text_value + m.group(3), tag, count=1
        )
        if n != 1:
            raise ValueError("a <Manual> tag had no Value attribute to set")
        out.append(xml[cursor:start])
        out.append(new_tag)
        cursor = end
        report.written += 1
    out.append(xml[cursor:])
    return "".join(out), report


def verify_envelope_set(original: str, result: str, report: EnvelopeReport) -> List[str]:
    """Check the result. Returns failure descriptions.

    The result must parse, must differ from the original *only* in the targeted
    parameters, and every targeted parameter must now hold the requested value.
    """
    failures: List[str] = []
    try:
        before = ET.fromstring(original)
        after = ET.fromstring(result)
    except ET.ParseError as e:
        return ["result is not well-formed XML: %s" % e]

    b_manual = [el for el in before.iter() if el.tag == "Manual"]
    a_manual = [el for el in after.iter() if el.tag == "Manual"]
    if len(b_manual) != len(a_manual):
        return ["<Manual> count changed: %d -> %d" % (len(b_manual), len(a_manual))]

    owner_chain = ENVELOPES[report.envelope]
    targeted = set()
    for sampler in after.iter("MultiSampler"):
        owner = _descend(sampler, owner_chain)
        parameter = owner.find(report.param) if owner is not None else None
        if parameter is None:
            continue
        manual = parameter.find("Manual")
        if manual is None or parameter.find(".//KeyMidi") is not None:
            continue
        targeted.add(id(manual))
        if manual.get("Value") != report.value:
            failures.append(
                "a %s %s still reads %s, not %s"
                % (report.envelope, report.param, manual.get("Value"), report.value)
            )
            break

    changed = 0
    for b, a in zip(b_manual, a_manual):
        if b.get("Value") != a.get("Value"):
            changed += 1
            if id(a) not in targeted:
                failures.append(
                    "a <Manual> outside the target set changed: %s -> %s"
                    % (b.get("Value"), a.get("Value"))
                )
                break
    if changed != report.written:
        failures.append("%d values changed, report says %d" % (changed, report.written))

    # Nothing but <Manual> tags may have moved.
    if _MANUAL.sub("<Manual/>", original) != _MANUAL.sub("<Manual/>", result):
        failures.append("text outside the <Manual> tags changed")
    return failures
