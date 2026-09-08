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
from .hide_macros import (
    HideReport,
    default_macro_name,
    hide_macros,
    root_device_span,
    verify_hide,
)
from .hide_macros_batch import HideResult, HideTreeReport, hide_macros_tree

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
    # Hide macros
    "HideReport",
    "HideResult",
    "HideTreeReport",
    "default_macro_name",
    "hide_macros",
    "hide_macros_tree",
    "root_device_span",
    "verify_hide",
]
