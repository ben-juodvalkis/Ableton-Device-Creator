"""
Batch envelope set: walk a tree of presets and set one Sampler envelope
parameter on every Sampler in them.

Writes either to a parallel output tree or in place. Every written file is
re-read and checked against its original (see ``envelope.verify_envelope_set``);
a file that fails any check is not left behind and is listed in the report while
the run continues. In place, each file is written to a temporary sibling and only
then moved over the original, so a failure never leaves a half-written preset.

A preset that already holds the requested value produces no edit and is reported
as ``unchanged``.
"""

import json
import os
import shutil
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from ..core import decode_adg, encode_adg
from .envelope import set_envelope_param, verify_envelope_set

__all__ = ["EnvelopeResult", "EnvelopeTreeReport", "set_envelope_tree", "write_report"]

PROCESSED = "processed"
UNCHANGED = "unchanged"
MACRO_HELD = "macro-held"  # nothing writable: every parameter is driven by a macro
SKIPPED = "skipped"
FAILED = "failed"
DRY_RUN = "dry-run"

PRESET_SUFFIXES = (".adg", ".adv")


@dataclass
class EnvelopeResult:
    """One preset's outcome."""

    path: str
    action: str
    samplers: int = 0
    written: int = 0
    mapped: int = 0
    already_correct: int = 0
    missing: int = 0
    old_values: Dict[str, int] = field(default_factory=dict)
    failures: List[str] = field(default_factory=list)
    output: Optional[str] = None


@dataclass
class EnvelopeTreeReport:
    """Outcome of a whole run."""

    root: str
    out_dir: Optional[str]
    dry_run: bool
    in_place: bool
    envelope: str = "amp"
    param: str = "AttackTime"
    value: str = ""
    files: List[EnvelopeResult] = field(default_factory=list)

    @property
    def totals(self) -> Dict[str, int]:
        actions = Counter(f.action for f in self.files)
        old: Counter = Counter()
        for f in self.files:
            old.update(f.old_values)
        totals = {
            "presets": len(self.files),
            "edited": actions[PROCESSED] + actions[DRY_RUN],
            "already_correct": actions[UNCHANGED],
            "nothing_writable_all_macro_held": actions[MACRO_HELD],
            "no_sampler": actions[SKIPPED],
            "failed": actions[FAILED],
            "samplers": sum(f.samplers for f in self.files),
            "parameters_written": sum(f.written for f in self.files),
            "parameters_macro_held": sum(f.mapped for f in self.files),
            "parameters_already_correct": sum(f.already_correct for f in self.files),
            "parameters_missing": sum(f.missing for f in self.files),
        }
        for value, n in old.most_common(6):
            totals["replaced_value_%s" % value] = n
        return totals

    def to_dict(self) -> Dict[str, object]:
        return {
            "root": self.root,
            "out_dir": self.out_dir,
            "dry_run": self.dry_run,
            "in_place": self.in_place,
            "envelope": self.envelope,
            "param": self.param,
            "value": self.value,
            "totals": self.totals,
            "files": [asdict(f) for f in self.files],
        }


def set_envelope_tree(
    root: Union[str, Path],
    value: float,
    param: str = "AttackTime",
    envelope: str = "amp",
    out_dir: Union[str, Path, None] = None,
    dry_run: bool = False,
    in_place: bool = False,
    overwrite: bool = False,
    progress: Optional[Callable[[EnvelopeResult], None]] = None,
) -> EnvelopeTreeReport:
    """Set ``param`` on the ``envelope`` of every Sampler under ``root``.

    ``root`` may be one preset or a directory. Parameters a macro holds are
    counted and left alone - Live ignores their stored value.
    """
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError("source not found: %s" % root)
    if not in_place and not dry_run and out_dir is None:
        raise ValueError("an output directory is required unless in-place or dry-run is given")
    if in_place and out_dir is not None:
        raise ValueError("in-place and an output directory are mutually exclusive")

    base = root.parent if root.is_file() else root
    out_path = base if (in_place or out_dir is None) else Path(out_dir).resolve()
    if out_dir is not None and not in_place:
        if out_path == base.resolve():
            raise ValueError("output directory must not be the source tree; pass in_place instead")

    report = EnvelopeTreeReport(
        root=str(root),
        out_dir=None if dry_run or in_place else str(out_path),
        dry_run=dry_run,
        in_place=in_place,
        envelope=envelope,
        param=param,
    )

    if root.is_file():
        presets = [root]
    else:
        presets = sorted(
            p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in PRESET_SUFFIXES
        )

    if not dry_run and not in_place and not overwrite:
        existing = [p for p in presets if (out_path / p.relative_to(base)).exists()]
        if existing:
            raise FileExistsError(
                "%d output files already exist under %s (first: %s); pass overwrite to replace them"
                % (len(existing), out_path, existing[0].relative_to(base))
            )

    for path in presets:
        rel = str(path.relative_to(base))
        target = out_path / path.relative_to(base)
        result = _process_file(path, rel, target, value, param, envelope, dry_run, in_place)
        if not report.value and result.action != FAILED:
            report.value = _last_value.get("v", "")
        report.files.append(result)
        if progress is not None:
            progress(result)
    return report


_last_value: Dict[str, str] = {}


def _process_file(
    path: Path,
    rel: str,
    target: Path,
    value: float,
    param: str,
    envelope: str,
    dry_run: bool,
    in_place: bool,
) -> EnvelopeResult:
    try:
        xml = decode_adg(path)
        text, env_report = set_envelope_param(xml, value, param, envelope)
    except Exception as e:  # noqa: BLE001 - a broken file must not stop the run
        return EnvelopeResult(path=rel, action=FAILED, failures=["%s: %s" % (type(e).__name__, e)])

    _last_value["v"] = env_report.value
    result = EnvelopeResult(
        path=rel,
        action=PROCESSED,
        samplers=env_report.samplers,
        written=env_report.written,
        mapped=env_report.mapped,
        already_correct=env_report.already_correct,
        missing=env_report.missing,
        old_values=env_report.old_values,
    )
    if env_report.samplers == 0:
        result.action = SKIPPED
        return result
    if not env_report.changed:
        # Nothing was written: either every parameter already holds the value,
        # or every one of them is macro-held and Live would ignore a write.
        result.action = MACRO_HELD if env_report.already_correct == 0 else UNCHANGED
        return result
    if dry_run:
        result.action = DRY_RUN
        return result

    failures = verify_envelope_set(xml, text, env_report)
    if not failures:
        try:
            written = _write(text, target, in_place)
            if decode_adg(written) != text:
                failures.append("gzip round-trip mismatch")
                if not in_place:
                    written.unlink()
        except Exception as e:  # noqa: BLE001
            failures.append("%s: %s" % (type(e).__name__, e))
    if failures:
        result.failures = failures
        result.action = FAILED
    else:
        result.output = str(target)
    return result


def _write(text: str, target: Path, in_place: bool) -> Path:
    """Write the preset, atomically when replacing a file that is already there."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if not in_place:
        encode_adg(text, target)
        return target
    tmp = target.with_name(target.stem + ".adc-tmp" + target.suffix)
    try:
        encode_adg(text, tmp)
        if decode_adg(tmp) != text:
            raise ValueError("gzip round-trip mismatch before replacing the original")
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink()
    return target


def write_report(report: EnvelopeTreeReport, path: Union[str, Path]) -> Path:
    """Write the run report as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=1), encoding="utf-8")
    return path
