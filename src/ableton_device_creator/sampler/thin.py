"""
Thin a preset's Samplers down to fewer velocity layers and fewer round robins.

Kits autosampled from a big library carry everything the library recorded: the
Damage, Abbey Road and Moonkit racks in this project are 10 velocity layers deep
with up to 6 round-robin takes in each, so one 32-pad rack can reference 1700
separate files and pull 1.5 GB of samples into RAM. Most of that detail is not
audible in a dance class. This module drops zones until each pad is at most
``max_layers`` velocity layers of at most ``max_takes`` takes, and widens the
surviving layers to cover the velocity range the dropped ones used to hold.

The result references a strict *subset* of the original's sample files, so a
thinned rack can only sound like a coarser version of the rack it came from -
nothing is re-derived, re-binned from source, or looked up on disk.

Two rules make this work on every library rather than just the ones this project
generated:

1. **Velocity centres are never inferred.** A layer's recorded centre is not
   stored in the preset, and the obvious reconstructions all fail somewhere:
   Moonkit pads that are missing their softest layer have a first bin stretched
   down to 1, the Damage Kits ladder puts its centres at the bin maxima rather
   than the midpoints, and Soundiron's ``_v1_``..``_v4_`` are layer indices that
   look exactly like velocities. So a kept layer simply absorbs the dropped
   layers adjacent to it - a run of dropped layers is split between the kept
   layers on either side - and the new ranges are unions of ranges that were
   already there. Contiguity is preserved by construction and no boundary is
   invented. (Measured across 7288 pads, 2026-09-11.)

2. **Zones are grouped into lanes by key range and selector range** before
   anything is dropped, and each lane is thinned on its own. The Damage
   Close/Room racks put two mic positions in one device on separate selector
   ranges; thinning them as one pool would strip a mic instead of a dynamic.

A pad is left alone, with a reason, unless its layers are safe to merge: every
zone on one key range, the layers contiguous and covering 1-127, and no zone
using a real velocity crossfade (a crossfade that is not simply its own range -
18 zones in the measured library - would have to be re-derived, so those are
reported rather than guessed at).

All edits are performed on the XML text: dropped zones are cut out, surviving
zones keep their bytes apart from a rewritten ``VelocityRange`` and a renumbered
``Id``. The file is never re-serialised through ElementTree (a re-serialised
Live 12 file parses but will not load). ElementTree is used read-only, to decide
which zones are which and to verify the result.

The functions in this module perform no I/O.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

__all__ = [
    "PadPlan",
    "ThinReport",
    "plan_thin",
    "thin_multisamples",
    "verify_thin",
    "DEFAULT_MAX_LAYERS",
    "DEFAULT_MAX_TAKES",
]

DEFAULT_MAX_LAYERS = 8
DEFAULT_MAX_TAKES = 3


@dataclass
class LanePlan:
    """One key/selector lane of one Sampler."""

    key_range: Tuple[int, int]
    selector_range: Tuple[int, int]
    layers_before: int
    layers_after: int
    takes_before: List[int] = field(default_factory=list)
    takes_after: List[int] = field(default_factory=list)
    zones_before: int = 0
    zones_after: int = 0
    skipped: bool = False
    reason: str = ""


@dataclass
class PadPlan:
    """One Sampler's outcome."""

    index: int
    name: str = ""
    lanes: List[LanePlan] = field(default_factory=list)
    zones_before: int = 0
    zones_after: int = 0
    skipped: bool = False
    reason: str = ""

    @property
    def changed(self) -> bool:
        return not self.skipped and self.zones_after != self.zones_before


@dataclass
class ThinReport:
    """What a whole preset's thinning did."""

    max_layers: int = DEFAULT_MAX_LAYERS
    max_takes: int = DEFAULT_MAX_TAKES
    pads: List[PadPlan] = field(default_factory=list)
    dropped_paths: List[str] = field(default_factory=list)
    kept_paths: List[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return any(p.changed for p in self.pads)

    @property
    def zones_before(self) -> int:
        return sum(p.zones_before for p in self.pads)

    @property
    def zones_after(self) -> int:
        return sum(p.zones_after for p in self.pads)

    @property
    def skipped_reasons(self) -> Dict[str, int]:
        reasons: Dict[str, int] = {}
        for pad in self.pads:
            if pad.skipped and pad.reason:
                reasons[pad.reason] = reasons.get(pad.reason, 0) + 1
            for lane in pad.lanes:
                if lane.skipped and lane.reason:
                    reasons[lane.reason] = reasons.get(lane.reason, 0) + 1
        return reasons


def _element_spans(text: str, tag: str, lo: int = 0, hi: Optional[int] = None) -> List[Tuple[int, int]]:
    """``(start, end)`` of every outermost ``<tag ...>...</tag>`` between lo and hi.

    Depth-counted, so a tag nested inside itself yields one span for the outer
    element. Self-closing tags at depth 0 are returned as their own span.
    """
    hi = len(text) if hi is None else hi
    opener = re.compile(r"<%s(?=[\s/>])" % re.escape(tag))
    closer = "</%s>" % tag
    spans: List[Tuple[int, int]] = []
    i, depth, start = lo, 0, 0
    while i < hi:
        m = opener.search(text, i, hi)
        c = text.find(closer, i, hi)
        if c > hi - len(closer):
            c = -1
        if m is None and c == -1:
            break
        if m is not None and (c == -1 or m.start() < c):
            j = text.index(">", m.end())
            self_closing = text[j - 1] == "/"
            if self_closing:
                if depth == 0:
                    spans.append((m.start(), j + 1))
            else:
                if depth == 0:
                    start = m.start()
                depth += 1
            i = j + 1
        else:
            depth -= 1
            if depth == 0:
                spans.append((start, c + len(closer)))
            i = c + len(closer)
    return spans


def _pick(count: int, keep: int) -> List[int]:
    """``keep`` indices spread evenly over ``range(count)``, endpoints included."""
    if keep >= count:
        return list(range(count))
    if keep <= 1:
        return [0]
    step = (count - 1) / (keep - 1)
    picked = sorted({int(round(i * step)) for i in range(keep)})
    # Rounding can collide on short ladders; fill back up from the unused indices.
    if len(picked) < keep:
        for i in range(count):
            if len(picked) == keep:
                break
            if i not in picked:
                picked.append(i)
        picked.sort()
    return picked


def _absorb(bins: List[Tuple[int, int]], kept: List[int]) -> List[Tuple[int, int]]:
    """New range for each kept layer: its own bin plus the dropped bins nearest it.

    A run of dropped layers between two kept ones is split down the middle, so
    the kept layers stay contiguous and still span whatever the originals
    spanned. No boundary is invented - every new edge is an edge one of the
    original bins already had.
    """
    new: List[Tuple[int, int]] = []
    for position, layer in enumerate(kept):
        first = 0 if position == 0 else (kept[position - 1] + layer) // 2 + 1
        last = len(bins) - 1 if position == len(kept) - 1 else (layer + kept[position + 1]) // 2
        new.append((bins[first][0], bins[last][1]))
    return new


def _zone_facts(part_xml: str) -> Optional[dict]:
    """Key/velocity/selector ranges and sample path of one MultiSamplePart."""
    try:
        el = ET.fromstring(part_xml)
    except ET.ParseError:
        return None

    def rng(tag):
        node = el.find(tag)
        if node is None:
            return None
        try:
            return tuple(
                int(node.find(f).get("Value"))
                for f in ("Min", "Max", "CrossfadeMin", "CrossfadeMax")
            )
        except (AttributeError, TypeError, ValueError):
            return None

    key, vel, sel = rng("KeyRange"), rng("VelocityRange"), rng("SelectorRange")
    if key is None or vel is None:
        return None
    path = el.find(".//FileRef/Path")
    name = el.find("Name")
    return {
        "key": key[:2],
        "vel": vel,
        "sel": sel[:2] if sel else (0, 127),
        "path": path.get("Value") if path is not None else None,
        "name": name.get("Value") if name is not None else "",
    }


_VEL_BLOCK = re.compile(
    r"(<VelocityRange>\s*<Min Value=\")(-?\d+)(\"\s*/>\s*<Max Value=\")(-?\d+)"
    r"(\"\s*/>\s*<CrossfadeMin Value=\")(-?\d+)(\"\s*/>\s*<CrossfadeMax Value=\")(-?\d+)(\"\s*/>\s*</VelocityRange>)"
)
_PART_ID = re.compile(r'(<MultiSamplePart Id=")(\d+)(")')


def _rewrite_zone(part_xml: str, new_id: int, vel: Optional[Tuple[int, int]]) -> str:
    """Renumber a zone and, when asked, move its velocity range."""
    out = _PART_ID.sub(lambda m: m.group(1) + str(new_id) + m.group(3), part_xml, count=1)
    if vel is not None:
        lo, hi = vel

        def sub(m):
            return (
                m.group(1) + str(lo) + m.group(3) + str(hi)
                + m.group(5) + str(lo) + m.group(7) + str(hi) + m.group(9)
            )

        out, n = _VEL_BLOCK.subn(sub, out, count=1)
        if n != 1:
            raise ValueError("could not rewrite the velocity range of a zone")
    return out


def plan_thin(
    xml: str,
    max_layers: int = DEFAULT_MAX_LAYERS,
    max_takes: int = DEFAULT_MAX_TAKES,
) -> Tuple[ThinReport, List[Tuple[int, int, str]]]:
    """Classify every Sampler and return the report plus the text edits to apply.

    Edits are ``(start, end, replacement)`` over ``xml``, non-overlapping and in
    ascending order - one per ``SampleParts`` block that changes.
    """
    if max_layers < 1 or max_takes < 1:
        raise ValueError("max_layers and max_takes must be at least 1")

    report = ThinReport(max_layers=max_layers, max_takes=max_takes)
    edits: List[Tuple[int, int, str]] = []

    for pad_index, (lo, hi) in enumerate(_element_spans(xml, "SampleParts")):
        pad = PadPlan(index=pad_index)
        report.pads.append(pad)

        zone_spans = _element_spans(xml, "MultiSamplePart", lo, hi)
        pad.zones_before = pad.zones_after = len(zone_spans)
        if not zone_spans:
            pad.skipped, pad.reason = True, "no zones"
            continue

        zones = []
        for start, end in zone_spans:
            facts = _zone_facts(xml[start:end])
            if facts is None:
                pad.skipped, pad.reason = True, "unreadable zone"
                break
            facts["span"] = (start, end)
            zones.append(facts)
        if pad.skipped:
            continue

        pad.name = zones[0]["name"]

        # Lanes: one velocity ladder per key range and selector range, thinned
        # independently. A drum pad is a single lane; a chromatic instrument has
        # one per recorded note, and a Close/Room pad one per mic.
        lanes: Dict[Tuple, List[dict]] = {}
        for z in zones:
            lanes.setdefault((z["key"], z["sel"]), []).append(z)

        keep_spans: List[Tuple[Tuple[int, int], Optional[Tuple[int, int]]]] = []
        for (key, sel), lane_zones in lanes.items():
            lane = LanePlan(
                key_range=key, selector_range=sel, layers_before=0, layers_after=0,
                zones_before=len(lane_zones),
            )
            pad.lanes.append(lane)

            layers: Dict[Tuple[int, int], List[dict]] = {}
            crossfaded = False
            for z in lane_zones:
                lo_v, hi_v, cf_lo, cf_hi = z["vel"]
                if (cf_lo, cf_hi) != (lo_v, hi_v):
                    crossfaded = True
                layers.setdefault((lo_v, hi_v), []).append(z)
            bins = sorted(layers)
            lane.layers_before = lane.layers_after = len(bins)
            lane.takes_before = sorted({len(layers[b]) for b in bins})
            lane.takes_after = lane.takes_before

            if crossfaded:
                lane.skipped, lane.reason = True, "velocity crossfade in use"
            elif bins[0][0] != 1 or bins[-1][1] != 127 or any(
                bins[i][1] + 1 != bins[i + 1][0] for i in range(len(bins) - 1)
            ):
                lane.skipped, lane.reason = True, "velocity layers are not contiguous over 1-127"
            if lane.skipped:
                lane.zones_after = lane.zones_before
                keep_spans.extend((z["span"], None) for z in lane_zones)
                continue

            kept_layers = _pick(len(bins), max_layers)
            new_ranges = _absorb(bins, kept_layers)
            lane.layers_after = len(kept_layers)

            after_takes = set()
            for position, layer_index in enumerate(kept_layers):
                takes = layers[bins[layer_index]]
                kept_takes = _pick(len(takes), max_takes)
                after_takes.add(len(kept_takes))
                for t in kept_takes:
                    keep_spans.append((takes[t]["span"], new_ranges[position]))
                for t, take in enumerate(takes):
                    if t not in kept_takes and take["path"]:
                        report.dropped_paths.append(take["path"])
                lane.zones_after += len(kept_takes)
            for layer_index, b in enumerate(bins):
                if layer_index not in kept_layers:
                    for take in layers[b]:
                        if take["path"]:
                            report.dropped_paths.append(take["path"])
            lane.takes_after = sorted(after_takes)

        pad.zones_after = sum(l.zones_after for l in pad.lanes)
        if pad.zones_after == pad.zones_before:
            continue

        keep_spans.sort(key=lambda s: s[0][0])
        pieces = []
        for new_id, ((start, end), vel) in enumerate(keep_spans):
            pieces.append(_rewrite_zone(xml[start:end], new_id, vel))
            facts = _zone_facts(xml[start:end])
            if facts and facts["path"]:
                report.kept_paths.append(facts["path"])

        # Rebuild the SampleParts body, keeping the separators Live wrote between
        # zones so an indented file stays indented and a one-line file stays flat.
        first_start = zone_spans[0][0]
        last_end = zone_spans[-1][1]
        separator = xml[zone_spans[0][1]:zone_spans[1][0]] if len(zone_spans) > 1 else ""
        body = separator.join(pieces)
        edits.append((first_start, last_end, body))

    edits.sort()
    return report, edits


def apply_edits(xml: str, edits: List[Tuple[int, int, str]]) -> str:
    """Splice non-overlapping ``(start, end, replacement)`` edits into the text."""
    out = []
    cursor = 0
    for start, end, replacement in edits:
        if start < cursor:
            raise ValueError("overlapping edits")
        out.append(xml[cursor:start])
        out.append(replacement)
        cursor = end
    out.append(xml[cursor:])
    return "".join(out)


def thin_multisamples(
    xml: str,
    max_layers: int = DEFAULT_MAX_LAYERS,
    max_takes: int = DEFAULT_MAX_TAKES,
) -> Tuple[str, ThinReport]:
    """Thin every Sampler in a preset to at most ``max_layers`` x ``max_takes``.

    Returns the new XML and a report. Everything outside the ``SampleParts``
    blocks - macros, mappings, chain colours, mixer, device parameters - is
    untouched, byte for byte.
    """
    report, edits = plan_thin(xml, max_layers, max_takes)
    return apply_edits(xml, edits), report


def verify_thin(original: str, result: str, report: ThinReport) -> List[str]:
    """Check a thinned preset against the original. Returns failure descriptions.

    Everything the edit was not supposed to touch must be byte-identical, every
    surviving zone must be a zone the original had, and every pad must still
    cover velocity 1-127 with no gap and no overlap.
    """
    failures: List[str] = []
    try:
        ET.fromstring(result)
    except ET.ParseError as e:
        return ["result is not well-formed XML: %s" % e]

    # 1. Nothing outside the zone lists moved.
    def blanked(text: str) -> str:
        spans = _element_spans(text, "SampleParts")
        out, cursor = [], 0
        for lo, hi in spans:
            out.append(text[cursor:lo])
            out.append("<SampleParts/>")
            cursor = hi
        out.append(text[cursor:])
        return "".join(out)

    if blanked(original) != blanked(result):
        failures.append("text outside the zone lists changed")

    before_pads = _element_spans(original, "SampleParts")
    after_pads = _element_spans(result, "SampleParts")
    if len(before_pads) != len(after_pads):
        failures.append(
            "pad count changed: %d -> %d" % (len(before_pads), len(after_pads))
        )
        return failures

    total_after = 0
    for index, ((b_lo, b_hi), (a_lo, a_hi)) in enumerate(zip(before_pads, after_pads)):
        before = [
            _zone_facts(original[s:e]) for s, e in _element_spans(original, "MultiSamplePart", b_lo, b_hi)
        ]
        after = [
            _zone_facts(result[s:e]) for s, e in _element_spans(result, "MultiSamplePart", a_lo, a_hi)
        ]
        if any(z is None for z in after):
            failures.append("pad %d: unreadable zone in the result" % index)
            continue
        total_after += len(after)

        before_paths = {z["path"] for z in before if z}
        for z in after:
            if z["path"] and z["path"] not in before_paths:
                failures.append("pad %d: zone %s was not in the original" % (index, z["path"]))
                break

        plan = report.pads[index] if index < len(report.pads) else None
        if plan is not None and len(after) != plan.zones_after:
            failures.append(
                "pad %d: %d zones, report says %d" % (index, len(after), plan.zones_after)
            )

        # Velocity cover, per lane, only where this module actually re-binned.
        if plan is not None and not plan.skipped:
            lanes: Dict[Tuple, List[Tuple[int, int]]] = {}
            for z in after:
                lanes.setdefault((z["key"], z["sel"]), []).append(z["vel"][:2])
            for lane_key, ranges in lanes.items():
                lane_plan = next(
                    (l for l in plan.lanes if (l.key_range, l.selector_range) == lane_key), None
                )
                if lane_plan is None or lane_plan.skipped:
                    continue
                bins = sorted(set(ranges))
                if len(bins) > report.max_layers:
                    failures.append(
                        "pad %d lane %s: %d layers exceeds the %d asked for"
                        % (index, lane_key, len(bins), report.max_layers)
                    )
                if bins[0][0] != 1 or bins[-1][1] != 127:
                    failures.append("pad %d lane %s: velocity no longer covers 1-127" % (index, lane_key))
                for i in range(len(bins) - 1):
                    if bins[i][1] + 1 != bins[i + 1][0]:
                        failures.append(
                            "pad %d lane %s: gap or overlap between %s and %s"
                            % (index, lane_key, bins[i], bins[i + 1])
                        )
                        break
                counts = {}
                for r in ranges:
                    counts[r] = counts.get(r, 0) + 1
                if counts and max(counts.values()) > report.max_takes:
                    failures.append(
                        "pad %d lane %s: %d takes exceeds the %d asked for"
                        % (index, lane_key, max(counts.values()), report.max_takes)
                    )

    if total_after != report.zones_after:
        failures.append(
            "result has %d zones, report says %d" % (total_after, report.zones_after)
        )
    return failures
