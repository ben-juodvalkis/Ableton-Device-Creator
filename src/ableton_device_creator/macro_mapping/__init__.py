"""
Macro mapping utilities for Ableton Live devices.

This module provides tools for coloring drum pads and configuring transpose mappings.
"""

from .color_mapper import DrumPadColorMapper, DRUM_COLORS
from .transpose import TransposeMapper
from .unmap import (
    BakeDecision,
    RackInfo,
    UnmapReport,
    classify_rack,
    reset_macro_defaults,
    strip_key_midi,
    unmap_drum_rack,
    verify_unmap,
)
from .unmap_batch import FileResult, TreeReport, unmap_tree, write_report

__all__ = [
    "DrumPadColorMapper",
    "TransposeMapper",
    "DRUM_COLORS",
    # Unmap
    "BakeDecision",
    "RackInfo",
    "UnmapReport",
    "classify_rack",
    "reset_macro_defaults",
    "strip_key_midi",
    "unmap_drum_rack",
    "verify_unmap",
    "FileResult",
    "TreeReport",
    "unmap_tree",
    "write_report",
]
