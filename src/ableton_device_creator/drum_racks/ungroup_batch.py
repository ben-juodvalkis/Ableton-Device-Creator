"""
Batch ungroup: walk a tree of ``.adg`` files and dissolve every Drum Rack pad's
nested rack into the pad chain.

Writes either to a parallel output tree or in place. Every written file is
re-read and checked against its original (see ``ungroup.verify_ungroup``); a
file that fails any check is not left behind and is listed in the report while
the run continues. In place, each file is written to a temporary sibling and
only then moved over the original, so a failure never leaves a half-written
preset in the library.
"""

import json
import os
import shutil
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from ..core import decode_adg, encode_adg
from .ungroup import ungroup_pads, verify_ungroup

__all__ = ["UngroupResult", "UngroupTreeReport", "ungroup_tree", "write_report"]

PROCESSED = "processed"
UNCHANGED = "unchanged"
SKIPPED = "skipped"
FAILED = "failed"
DRY_RUN = "dry-run"


@dataclass
class UngroupResult:
    """One ``.adg`` file's outcome."""

    path: str
    action: str
    root_class: str = ""
    pads: int = 0
    ungrouped: int = 0
    pads_skipped: int = 0
    devices_lifted: Dict[str, int] = field(default_factory=dict)
    key_midi_removed: int = 0
    key_midi_dropped_with_chain: int = 0
    key_midi_kept: int = 0
    ranges_reset: int = 0
    ranges_left: List[str] = field(default_factory=list)
    skip_reasons: Dict[str, int] = field(default_factory=dict)
    reason: str = ""
    failures: List[str] = field(default_factory=list)
    output: Optional[str] = None
    copied: bool = False  # the original was copied unchanged into the output tree


@dataclass
class UngroupTreeReport:
    """Outcome of a whole run."""

    root: str
    out_dir: Optional[str]
    dry_run: bool
    in_place: bool
    copy_unchanged: bool = True
    files: List[UngroupResult] = field(default_factory=list)
    other_files: Dict[str, int] = field(default_factory=dict)
    copied_other: int = 0

    @property
    def totals(self) -> Dict[str, int]:
        actions = Counter(f.action for f in self.files)
        totals = {
            "adg_files": len(self.files),
            "drum_racks": sum(1 for f in self.files if f.root_class == "DrumGroupDevice"),
            "processed": actions[PROCESSED] + actions[DRY_RUN],
            "nothing_to_ungroup": actions[UNCHANGED],
            "skipped": actions[SKIPPED],
            "failed": actions[FAILED],
            "pads": sum(f.pads for f in self.files),
            "pads_ungrouped": sum(f.ungrouped for f in self.files),
            "pads_skipped": sum(f.pads_skipped for f in self.files),
            "mappings_removed": sum(f.key_midi_removed for f in self.files),
            "mappings_dropped_with_chain": sum(f.key_midi_dropped_with_chain for f in self.files),
            "mappings_kept": sum(f.key_midi_kept for f in self.files),
            "ranges_reset": sum(f.ranges_reset for f in self.files),
            "copied_unchanged_adg": sum(1 for f in self.files if f.copied),
            "copied_unchanged_other": self.copied_other,
        }
        lifted: Counter = Counter()
        for f in self.files:
            lifted.update(f.devices_lifted)
        for dev, n in sorted(lifted.items()):
            totals["lifted_%s" % dev] = n
        reasons: Counter = Counter()
        for f in self.files:
            reasons.update(f.skip_reasons)
        for reason, n in sorted(reasons.items()):
            totals["pad_skipped_%s" % reason] = n
        for ext, n in sorted(self.other_files.items()):
            totals["other_%s" % ext.lstrip(".")] = n
        return totals

    @property
    def ranges_left(self) -> List[str]:
        return sorted({r for f in self.files for r in f.ranges_left})

    def to_dict(self) -> Dict[str, object]:
        return {
            "root": self.root,
            "out_dir": self.out_dir,
            "dry_run": self.dry_run,
            "in_place": self.in_place,
            "copy_unchanged": self.copy_unchanged,
            "totals": self.totals,
            "ranges_left_stored": self.ranges_left,
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


def ungroup_tree(
    root: Union[str, Path],
    out_dir: Union[str, Path, None] = None,
    dry_run: bool = False,
    in_place: bool = False,
    overwrite: bool = False,
    copy_unchanged: bool = True,
    progress: Optional[Callable[[UngroupResult], None]] = None,
) -> UngroupTreeReport:
    """Dissolve every pad's nested rack in every Drum Rack under ``root``.

    ``root`` may be a single ``.adg`` file or a directory to walk. ``dry_run``
    classifies and reports without writing. ``in_place`` rewrites the source
    files; otherwise every rack is written at its relative path under
    ``out_dir`` and, with ``copy_unchanged``, every file that is not edited
    (Instrument Racks, ``.adv`` presets, a rack that failed verification) is
    copied there byte for byte so the output tree can replace ``root`` whole.
    Existing output files stop the run unless ``overwrite`` is set. ``progress``
    is called with each ``.adg`` file's result as it completes.
    """
    root = Path(root)
    if root.is_file():
        return _single_file(root, out_dir, dry_run, in_place, overwrite, progress)
    if not root.is_dir():
        raise FileNotFoundError("source tree not found: %s" % root)
    out_path = _check_out_dir(
        root, Path(out_dir) if out_dir is not None else None, dry_run, in_place
    )
    report = UngroupTreeReport(
        root=str(root),
        out_dir=None if dry_run or in_place else str(out_path),
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
        result = _process_file(path, rel, target, dry_run, in_place)
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


def _single_file(
    path: Path,
    out_dir: Union[str, Path, None],
    dry_run: bool,
    in_place: bool,
    overwrite: bool,
    progress: Optional[Callable[[UngroupResult], None]],
) -> UngroupTreeReport:
    """One ``.adg`` in, one out. ``out_dir`` may be a directory or a target file."""
    if path.suffix.lower() != ".adg":
        raise ValueError("not an .adg preset: %s" % path)
    if in_place:
        target = path
    elif out_dir is None:
        if dry_run:
            target = path
        else:
            target = path.with_name("%s (ungrouped).adg" % path.stem)
    else:
        out = Path(out_dir)
        target = out if out.suffix.lower() == ".adg" else out / path.name
    if not dry_run and not in_place and target.exists() and not overwrite:
        raise FileExistsError("%s already exists; pass overwrite to replace it" % target)

    report = UngroupTreeReport(
        root=str(path),
        out_dir=None if dry_run or in_place else str(target),
        dry_run=dry_run,
        in_place=in_place,
        copy_unchanged=False,
    )
    result = _process_file(path, path.name, target, dry_run, in_place)
    report.files.append(result)
    if progress is not None:
        progress(result)
    return report


def _copy_unchanged(source: Path, target: Path) -> None:
    """Copy a file byte for byte, keeping its timestamps (Looping fingerprints files)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _process_file(
    path: Path, rel: str, target: Path, dry_run: bool, in_place: bool
) -> UngroupResult:
    try:
        xml = decode_adg(path)
        text, report = ungroup_pads(xml)
    except Exception as e:  # noqa: BLE001 - a broken file must not stop the run
        return UngroupResult(path=rel, action=FAILED, failures=["%s: %s" % (type(e).__name__, e)])

    result = UngroupResult(
        path=rel,
        action=PROCESSED,
        root_class=report.root_class,
        pads=len(report.pads),
        ungrouped=report.ungrouped,
        pads_skipped=report.skipped,
        devices_lifted=dict(Counter(d for p in report.pads for d in p.devices)),
        key_midi_removed=report.key_midi_removed,
        key_midi_dropped_with_chain=sum(p.key_midi_dropped_with_chain for p in report.pads),
        key_midi_kept=sum(p.key_midi_kept for p in report.pads),
        ranges_reset=report.ranges_reset,
        ranges_left=report.ranges_left,
        skip_reasons=dict(Counter(p.skipped for p in report.pads if p.skipped)),
        reason=report.reason,
    )
    if not report.is_drum_rack:
        result.action = SKIPPED
        return result
    if not report.changed:
        result.action = UNCHANGED
        return result
    if dry_run:
        result.action = DRY_RUN
        return result

    failures = verify_ungroup(xml, text, report)
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


def write_report(report: UngroupTreeReport, path: Union[str, Path]) -> Path:
    """Write the run report as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=1), encoding="utf-8")
    return path
