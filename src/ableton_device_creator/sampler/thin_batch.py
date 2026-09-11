"""
Batch thin: walk a tree of ``.adg``/``.adv`` presets and thin every Sampler in
them down to fewer velocity layers and fewer round robins.

Writes either to a parallel output tree or in place. Every written file is
re-read and checked against its original (see ``thin.verify_thin``); a file that
fails any check is not left behind and is listed in the report while the run
continues. In place, each file is written to a temporary sibling and only then
moved over the original, so a failure never leaves a half-written preset in the
library.

A preset whose Samplers are already within the requested limits is reported as
``unchanged`` and, to an output tree, copied over byte for byte - so the output
tree can replace the source tree whole.
"""

import json
import os
import shutil
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Union

from ..core import decode_adg, encode_adg
from .thin import (
    DEFAULT_MAX_LAYERS,
    DEFAULT_MAX_TAKES,
    thin_multisamples,
    verify_thin,
)

__all__ = ["ThinResult", "ThinTreeReport", "thin_tree", "write_report"]

PROCESSED = "processed"
UNCHANGED = "unchanged"
SKIPPED = "skipped"
FAILED = "failed"
DRY_RUN = "dry-run"

PRESET_SUFFIXES = (".adg", ".adv")


@dataclass
class ThinResult:
    """One preset's outcome."""

    path: str
    action: str
    pads: int = 0
    zones_before: int = 0
    zones_after: int = 0
    samples_before: int = 0
    samples_after: int = 0
    bytes_before: int = 0
    bytes_after: int = 0
    reasons: Dict[str, int] = field(default_factory=dict)
    failures: List[str] = field(default_factory=list)
    output: Optional[str] = None
    copied: bool = False


@dataclass
class ThinTreeReport:
    """Outcome of a whole run."""

    root: str
    out_dir: Optional[str]
    dry_run: bool
    in_place: bool
    max_layers: int = DEFAULT_MAX_LAYERS
    max_takes: int = DEFAULT_MAX_TAKES
    copy_unchanged: bool = True
    files: List[ThinResult] = field(default_factory=list)
    copied_other: int = 0

    @property
    def totals(self) -> Dict[str, int]:
        actions = Counter(f.action for f in self.files)
        reasons: Counter = Counter()
        for f in self.files:
            reasons.update(f.reasons)
        totals = {
            "presets": len(self.files),
            "thinned": actions[PROCESSED] + actions[DRY_RUN],
            "already_within_limits": actions[UNCHANGED],
            "skipped": actions[SKIPPED],
            "failed": actions[FAILED],
            "zones_before": sum(f.zones_before for f in self.files),
            "zones_after": sum(f.zones_after for f in self.files),
            "sample_bytes_before": sum(f.bytes_before for f in self.files),
            "sample_bytes_after": sum(f.bytes_after for f in self.files),
            "copied_unchanged": sum(1 for f in self.files if f.copied),
            "copied_other": self.copied_other,
        }
        for reason, n in sorted(reasons.items()):
            totals["left_alone_%s" % reason.replace(" ", "_")[:48]] = n
        return totals

    def to_dict(self) -> Dict[str, object]:
        return {
            "root": self.root,
            "out_dir": self.out_dir,
            "dry_run": self.dry_run,
            "in_place": self.in_place,
            "max_layers": self.max_layers,
            "max_takes": self.max_takes,
            "totals": self.totals,
            "files": [asdict(f) for f in self.files],
        }


def _check_out_dir(root: Path, out_dir: Optional[Path], dry_run: bool, in_place: bool) -> Path:
    if in_place:
        if out_dir is not None:
            raise ValueError("in-place and an output directory are mutually exclusive")
        return root
    if dry_run and out_dir is None:
        return root
    if out_dir is None:
        raise ValueError("an output directory is required unless in-place or dry-run is given")
    root_r, out_r = root.resolve(), out_dir.resolve()
    if out_r == root_r:
        raise ValueError("output directory must not be the source tree; pass in_place instead")
    if root_r in out_r.parents:
        raise ValueError("output directory must not be inside the source tree")
    if out_r in root_r.parents:
        raise ValueError("the source tree must not be inside the output directory")
    return out_r


def thin_tree(
    root: Union[str, Path],
    out_dir: Union[str, Path, None] = None,
    max_layers: int = DEFAULT_MAX_LAYERS,
    max_takes: int = DEFAULT_MAX_TAKES,
    dry_run: bool = False,
    in_place: bool = False,
    overwrite: bool = False,
    copy_unchanged: bool = True,
    progress: Optional[Callable[[ThinResult], None]] = None,
) -> ThinTreeReport:
    """Thin every Sampler under ``root`` to at most ``max_layers`` x ``max_takes``.

    ``root`` may be one preset or a directory. ``dry_run`` classifies and reports
    without writing. ``in_place`` rewrites the source files; otherwise every
    preset is written at its relative path under ``out_dir`` and, with
    ``copy_unchanged``, everything not edited is copied there byte for byte.
    Existing output files stop the run unless ``overwrite`` is set.
    """
    root = Path(root)
    single_file = root.is_file()
    if not root.exists():
        raise FileNotFoundError("source not found: %s" % root)

    base = root.parent if single_file else root
    out_path = _check_out_dir(
        base, Path(out_dir) if out_dir is not None else None, dry_run, in_place
    )
    report = ThinTreeReport(
        root=str(root),
        out_dir=None if dry_run or in_place else str(out_path),
        dry_run=dry_run,
        in_place=in_place,
        max_layers=max_layers,
        max_takes=max_takes,
        copy_unchanged=copy_unchanged and not in_place,
    )

    if single_file:
        presets, other_files = [root], []
    else:
        files = sorted(p for p in root.rglob("*") if p.is_file())
        presets = [p for p in files if p.suffix.lower() in PRESET_SUFFIXES]
        other_files = [p for p in files if p.suffix.lower() not in PRESET_SUFFIXES]

    if not dry_run and not in_place and not overwrite:
        candidates = presets + (other_files if copy_unchanged else [])
        existing = [p for p in candidates if (out_path / p.relative_to(base)).exists()]
        if existing:
            raise FileExistsError(
                "%d output files already exist under %s (first: %s); pass overwrite to replace them"
                % (len(existing), out_path, existing[0].relative_to(base))
            )

    sizes: Dict[str, int] = {}
    for path in presets:
        rel = str(path.relative_to(base))
        target = out_path / path.relative_to(base)
        result = _process_file(path, rel, target, max_layers, max_takes, dry_run, in_place, sizes)
        if report.copy_unchanged and not dry_run and result.output is None:
            _copy_unchanged(path, target)
            result.copied = True
        report.files.append(result)
        if progress is not None:
            progress(result)

    if report.copy_unchanged and not dry_run:
        for path in other_files:
            _copy_unchanged(path, out_path / path.relative_to(base))
        report.copied_other = len(other_files)
    return report


def _copy_unchanged(source: Path, target: Path) -> None:
    """Copy a file byte for byte, keeping its timestamps (Looping fingerprints files)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _sample_bytes(paths: Set[str], sizes: Dict[str, int]) -> int:
    total = 0
    for p in paths:
        if p not in sizes:
            try:
                sizes[p] = os.path.getsize(p)
            except OSError:
                sizes[p] = 0
        total += sizes[p]
    return total


def _process_file(
    path: Path,
    rel: str,
    target: Path,
    max_layers: int,
    max_takes: int,
    dry_run: bool,
    in_place: bool,
    sizes: Dict[str, int],
) -> ThinResult:
    try:
        xml = decode_adg(path)
        text, thin_report = thin_multisamples(xml, max_layers, max_takes)
    except Exception as e:  # noqa: BLE001 - a broken file must not stop the run
        return ThinResult(path=rel, action=FAILED, failures=["%s: %s" % (type(e).__name__, e)])

    kept = set(thin_report.kept_paths)
    dropped = set(thin_report.dropped_paths) - kept
    result = ThinResult(
        path=rel,
        action=PROCESSED,
        pads=len(thin_report.pads),
        zones_before=thin_report.zones_before,
        zones_after=thin_report.zones_after,
        samples_before=len(kept | dropped),
        samples_after=len(kept),
        reasons=thin_report.skipped_reasons,
    )
    if not thin_report.pads:
        result.action = SKIPPED
        return result
    if not thin_report.changed:
        result.action = UNCHANGED
        return result

    result.bytes_before = _sample_bytes(kept | dropped, sizes)
    result.bytes_after = _sample_bytes(kept, sizes)
    if dry_run:
        result.action = DRY_RUN
        return result

    failures = verify_thin(xml, text, thin_report)
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


def write_report(report: ThinTreeReport, path: Union[str, Path]) -> Path:
    """Write the run report as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=1), encoding="utf-8")
    return path
