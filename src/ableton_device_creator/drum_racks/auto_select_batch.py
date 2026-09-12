"""
Batch auto-select: walk a tree of ``.adg`` files and switch every root Drum
Rack's Auto-Select on (or off).

Writes either to a parallel output tree or in place. Every written file is
re-read and checked against its original (see ``auto_select.verify_auto_select``);
a file that fails any check is not left behind and is listed in the report while
the run continues. In place, each file is written to a temporary sibling and only
then moved over the original, so a failure never leaves a half-written preset in
the library.
"""

import json
import os
import shutil
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from ..core import decode_adg, encode_adg
from .auto_select import set_auto_select, verify_auto_select

__all__ = [
    "AutoSelectResult",
    "AutoSelectTreeReport",
    "set_auto_select_tree",
    "write_report",
]

PROCESSED = "processed"
UNCHANGED = "unchanged"
SKIPPED = "skipped"
FAILED = "failed"
DRY_RUN = "dry-run"


@dataclass
class AutoSelectResult:
    """One ``.adg`` file's outcome."""

    path: str
    action: str
    root_class: str = ""
    was_enabled: Optional[bool] = None
    reason: str = ""
    failures: List[str] = field(default_factory=list)
    output: Optional[str] = None
    copied: bool = False  # the original was copied unchanged into the output tree


@dataclass
class AutoSelectTreeReport:
    """Outcome of a whole run."""

    root: str
    out_dir: Optional[str]
    enabled: bool
    dry_run: bool
    in_place: bool
    copy_unchanged: bool = True
    files: List[AutoSelectResult] = field(default_factory=list)
    other_files: Dict[str, int] = field(default_factory=dict)
    copied_other: int = 0

    @property
    def totals(self) -> Dict[str, int]:
        actions = Counter(f.action for f in self.files)
        skipped_by_class = Counter(f.root_class for f in self.files if f.action == SKIPPED)
        totals = {
            "adg_files": len(self.files),
            "drum_racks": sum(1 for f in self.files if f.root_class == "DrumGroupDevice"),
            "processed": actions[PROCESSED] + actions[DRY_RUN],
            "already_set": actions[UNCHANGED],
            "skipped": actions[SKIPPED],
            "failed": actions[FAILED],
            "copied_unchanged_adg": sum(1 for f in self.files if f.copied),
            "copied_unchanged_other": self.copied_other,
        }
        for cls, n in sorted(skipped_by_class.items()):
            totals["skipped_%s" % (cls or "unknown")] = n
        no_field = sum(
            1 for f in self.files if f.reason == "root device has no IsAutoSelectEnabled field"
        )
        if no_field:
            totals["skipped_no_field"] = no_field
        for ext, n in sorted(self.other_files.items()):
            totals["other_%s" % ext.lstrip(".")] = n
        return totals

    def to_dict(self) -> Dict[str, object]:
        return {
            "root": self.root,
            "out_dir": self.out_dir,
            "enabled": self.enabled,
            "dry_run": self.dry_run,
            "in_place": self.in_place,
            "copy_unchanged": self.copy_unchanged,
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


def set_auto_select_tree(
    root: Union[str, Path],
    enabled: bool = True,
    out_dir: Union[str, Path, None] = None,
    dry_run: bool = False,
    in_place: bool = False,
    overwrite: bool = False,
    copy_unchanged: bool = True,
    progress: Optional[Callable[[AutoSelectResult], None]] = None,
) -> AutoSelectTreeReport:
    """Set Auto-Select on every root Drum Rack under ``root``.

    ``dry_run`` classifies and reports without writing. ``in_place`` rewrites the
    source files; otherwise every edited rack is written at its relative path
    under ``out_dir`` and, with ``copy_unchanged``, every file that is not edited
    (Instrument Racks, ``.adv`` presets, racks already in the requested state) is
    copied there byte for byte so the output tree can replace ``root`` whole.
    Existing output files stop the run unless ``overwrite`` is set. ``progress``
    is called with each ``.adg`` file's result as it completes.
    """
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError("source tree not found: %s" % root)
    out_path = _check_out_dir(
        root, Path(out_dir) if out_dir is not None else None, dry_run, in_place
    )
    report = AutoSelectTreeReport(
        root=str(root),
        out_dir=None if dry_run or in_place else str(out_path),
        enabled=enabled,
        dry_run=dry_run,
        in_place=in_place,
        copy_unchanged=copy_unchanged and not in_place,
    )

    files = sorted(p for p in root.rglob("*") if p.is_file())
    adg_files = [p for p in files if p.suffix.lower() == ".adg"]
    other_files = [p for p in files if p.suffix.lower() != ".adg"]
    report.other_files = dict(Counter(p.suffix.lower() or "(none)" for p in other_files))

    if not dry_run and not in_place and not overwrite:
        candidates = files if copy_unchanged else adg_files
        existing = [p for p in candidates if (out_path / p.relative_to(root)).exists()]
        if existing:
            raise FileExistsError(
                "%d output files already exist under %s (first: %s); pass overwrite to replace them"
                % (len(existing), out_path, existing[0].relative_to(root))
            )

    for path in adg_files:
        rel = str(path.relative_to(root))
        target = out_path / path.relative_to(root)
        result = _process_file(path, rel, target, enabled, dry_run, in_place)
        if report.copy_unchanged and not dry_run and result.output is None:
            _copy_unchanged(path, target)
            result.copied = True
        report.files.append(result)
        if progress is not None:
            progress(result)

    if report.copy_unchanged and not dry_run:
        for path in other_files:
            _copy_unchanged(path, out_path / path.relative_to(root))
        report.copied_other = len(other_files)
    return report


def _copy_unchanged(source: Path, target: Path) -> None:
    """Copy a file byte for byte, keeping its timestamps (Looping fingerprints files)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _process_file(
    path: Path, rel: str, target: Path, enabled: bool, dry_run: bool, in_place: bool
) -> AutoSelectResult:
    try:
        xml = decode_adg(path)
        text, auto_report = set_auto_select(xml, enabled)
    except Exception as e:  # noqa: BLE001 - a broken file must not stop the run
        return AutoSelectResult(
            path=rel, action=FAILED, failures=["%s: %s" % (type(e).__name__, e)]
        )

    result = AutoSelectResult(
        path=rel,
        action=PROCESSED,
        root_class=auto_report.root_class,
        was_enabled=auto_report.was_enabled,
        reason=auto_report.reason,
    )
    if not auto_report.is_drum_rack:
        result.action = SKIPPED
        return result
    if not auto_report.changed:
        # A Drum Rack with no field at all is skipped, not "already set".
        result.action = SKIPPED if auto_report.was_enabled is None else UNCHANGED
        return result
    if dry_run:
        result.action = DRY_RUN
        return result

    failures = verify_auto_select(xml, text, auto_report)
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
    # Keep the .adg suffix: encode_adg refuses anything else.
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


def write_report(report: AutoSelectTreeReport, path: Union[str, Path]) -> Path:
    """Write the run report as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=1), encoding="utf-8")
    return path
