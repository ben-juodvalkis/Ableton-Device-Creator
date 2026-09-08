"""
Batch unmap: walk a tree of ``.adg`` files and write unmapped copies to a parallel tree.

The source tree is never written to. Every written file is re-read and checked
against its original (see ``unmap.verify_unmap``); a file that fails any check
is not left behind and is listed in the report while the run continues.
"""

import json
import shutil
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from ..core import decode_adg, encode_adg
from .unmap import RackInfo, classify_rack, unmap_drum_rack, verify_unmap

__all__ = ["FileResult", "TreeReport", "unmap_tree", "write_report"]

PROCESSED = "processed"
NESTED_ONLY = "nested-only"
SKIPPED = "skipped"
FAILED = "failed"
DRY_RUN = "dry-run"


@dataclass
class FileResult:
    """One ``.adg`` file's outcome."""

    path: str
    action: str
    root_class: str = ""
    key_midi_total: int = 0
    key_midi_root: int = 0
    key_midi_nested: int = 0
    nested_drum_racks: int = 0
    nested_group_devices: Dict[str, int] = field(default_factory=dict)
    macro_names: List[str] = field(default_factory=list)
    macro_values: List[float] = field(default_factory=list)
    has_macro_control_index: bool = False
    non_macro_key_midi: int = 0
    removed: int = 0
    baked: int = 0
    kept: int = 0
    unknown: int = 0
    unknown_params: List[str] = field(default_factory=list)
    macro_defaults_changed: int = 0
    failures: List[str] = field(default_factory=list)
    output: Optional[str] = None
    copied: bool = False  # the original was copied unchanged into the output tree


@dataclass
class TreeReport:
    """Outcome of a whole run."""

    root: str
    out_dir: Optional[str]
    dry_run: bool
    include_nested: bool
    bake: bool
    copy_unchanged: bool = True
    files: List[FileResult] = field(default_factory=list)
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
            "nested_only": actions[NESTED_ONLY],
            "skipped": actions[SKIPPED],
            "failed": actions[FAILED],
            "key_midi_in_scope": sum(
                f.key_midi_root + (f.key_midi_nested if self.include_nested else 0)
                for f in self.files
                if f.root_class == "DrumGroupDevice"
            ),
            "key_midi_removed": sum(f.removed for f in self.files),
            "key_midi_left_nested": (
                sum(f.key_midi_nested for f in self.files if f.action in (PROCESSED, DRY_RUN))
                if not self.include_nested
                else 0
            ),
            "values_baked": sum(f.baked for f in self.files),
            "values_kept": sum(f.kept for f in self.files),
            "values_unknown_curve": sum(f.unknown for f in self.files),
            "files_with_unknown_curve": sum(1 for f in self.files if f.unknown),
            "files_with_macro_control_index": sum(
                1 for f in self.files if f.has_macro_control_index
            ),
            "files_with_non_macro_key_midi": sum(1 for f in self.files if f.non_macro_key_midi),
            "files_with_nested_racks": sum(
                1
                for f in self.files
                if f.root_class == "DrumGroupDevice" and f.nested_group_devices
            ),
            "copied_unchanged_adg": sum(1 for f in self.files if f.copied),
            "copied_unchanged_other": self.copied_other,
        }
        for cls, n in sorted(skipped_by_class.items()):
            totals["skipped_%s" % (cls or "unknown")] = n
        for ext, n in sorted(self.other_files.items()):
            totals["other_%s" % ext.lstrip(".")] = n
        return totals

    def to_dict(self) -> Dict[str, object]:
        return {
            "root": self.root,
            "out_dir": self.out_dir,
            "dry_run": self.dry_run,
            "include_nested": self.include_nested,
            "bake": self.bake,
            "copy_unchanged": self.copy_unchanged,
            "totals": self.totals,
            "files": [asdict(f) for f in self.files],
        }


def _info_result(rel: str, info: RackInfo, action: str) -> FileResult:
    return FileResult(
        path=rel,
        action=action,
        root_class=info.root_class,
        key_midi_total=info.key_midi_count,
        key_midi_root=info.key_midi_root,
        key_midi_nested=info.key_midi_nested,
        nested_drum_racks=info.nested_drum_racks,
        nested_group_devices=dict(info.nested_group_devices),
        macro_names=list(info.macro_names),
        macro_values=list(info.macro_values),
        has_macro_control_index=info.has_macro_control_index,
        non_macro_key_midi=info.non_macro_key_midi,
    )


def _check_out_dir(root: Path, out_dir: Optional[Path], dry_run: bool) -> Path:
    if dry_run and out_dir is None:
        return root
    if out_dir is None:
        raise ValueError("an output directory is required unless --dry-run is given")
    root_r, out_r = root.resolve(), out_dir.resolve()
    if out_r == root_r:
        raise ValueError("output directory must not be the source tree")
    if root_r in out_r.parents:
        raise ValueError("output directory must not be inside the source tree")
    if out_r in root_r.parents:
        raise ValueError("the source tree must not be inside the output directory")
    return out_r


def unmap_tree(
    root: Union[str, Path],
    out_dir: Union[str, Path, None],
    dry_run: bool = False,
    include_nested: bool = False,
    bake: bool = True,
    overwrite: bool = False,
    copy_unchanged: bool = True,
    progress: Optional[Callable[[FileResult], None]] = None,
) -> TreeReport:
    """Unmap every root Drum Rack under ``root`` into the same relative path under ``out_dir``.

    ``dry_run`` classifies and reports without writing. ``include_nested`` also
    removes mappings owned by racks nested inside the pads. ``bake`` writes the
    macro-driven value into each unmapped parameter (Live's behaviour). Existing
    output files stop the run unless ``overwrite`` is set. With ``copy_unchanged``
    every file that is not unmapped (other racks, ``.adv`` presets, a rack that
    failed verification) is copied into ``out_dir`` byte for byte, so the output
    tree is a drop-in replacement for ``root``. ``progress`` is called with each
    ``.adg`` file's result as it completes.
    """
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError("source tree not found: %s" % root)
    out_path = _check_out_dir(root, Path(out_dir) if out_dir is not None else None, dry_run)
    report = TreeReport(
        root=str(root),
        out_dir=None if dry_run else str(out_path),
        dry_run=dry_run,
        include_nested=include_nested,
        bake=bake,
        copy_unchanged=copy_unchanged,
    )

    files = sorted(p for p in root.rglob("*") if p.is_file())
    adg_files = [p for p in files if p.suffix.lower() == ".adg"]
    other_files = [p for p in files if p.suffix.lower() != ".adg"]
    report.other_files = dict(Counter(p.suffix.lower() or "(none)" for p in other_files))

    if not dry_run and not overwrite:
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
        result = _process_file(path, rel, target, dry_run, include_nested, bake)
        if not dry_run and copy_unchanged and result.output is None:
            _copy_unchanged(path, target)
            result.copied = True
        report.files.append(result)
        if progress is not None:
            progress(result)

    if not dry_run and copy_unchanged:
        for path in other_files:
            _copy_unchanged(path, out_path / path.relative_to(root))
        report.copied_other = len(other_files)
    return report


def _copy_unchanged(source: Path, target: Path) -> None:
    """Copy a file byte for byte, keeping its timestamps (Looping fingerprints files)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _process_file(
    path: Path, rel: str, target: Path, dry_run: bool, include_nested: bool, bake: bool
) -> FileResult:
    try:
        xml = decode_adg(path)
        info = classify_rack(xml)
    except Exception as e:  # noqa: BLE001 - a broken file must not stop the run
        return FileResult(path=rel, action=FAILED, failures=["%s: %s" % (type(e).__name__, e)])

    if info.is_drum_rack:
        if dry_run:
            return _info_result(rel, info, DRY_RUN)
        return _unmap_file(xml, rel, info, target, include_nested, bake)
    if info.is_instrument_rack_with_drum_rack:
        return _info_result(rel, info, NESTED_ONLY)
    return _info_result(rel, info, SKIPPED)


def _unmap_file(
    xml: str, rel: str, info: RackInfo, target: Path, include_nested: bool, bake: bool
) -> FileResult:
    result = _info_result(rel, info, PROCESSED)
    try:
        text, unmap_report = unmap_drum_rack(xml, include_nested=include_nested, bake=bake)
        result.removed = unmap_report.removed
        result.baked = unmap_report.baked
        result.kept = unmap_report.kept
        result.unknown = unmap_report.unknown
        result.unknown_params = unmap_report.unknown_params
        result.macro_defaults_changed = unmap_report.macro_defaults_changed
        failures = verify_unmap(xml, text, unmap_report, include_nested=include_nested)
        if not failures:
            encode_adg(text, target)
            if decode_adg(target) != text:
                failures.append("gzip round-trip mismatch")
        if failures:
            result.failures = failures
            result.action = FAILED
            if target.exists():
                target.unlink()
        else:
            result.output = str(target)
    except Exception as e:  # noqa: BLE001
        result.failures = ["%s: %s" % (type(e).__name__, e)]
        result.action = FAILED
        if target.exists():
            target.unlink()
    return result


def write_report(report: TreeReport, path: Union[str, Path]) -> Path:
    """Write the run report as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=1), encoding="utf-8")
    return path
