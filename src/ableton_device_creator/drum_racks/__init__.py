"""
Drum rack creation and modification tools.

This module provides classes for creating and modifying Ableton Live
drum racks from sample folders.
"""

from .creator import DrumRackCreator
from .modifier import DrumRackModifier
from .auto_select import AutoSelectReport, set_auto_select, verify_auto_select
from .auto_select_batch import (
    AutoSelectResult,
    AutoSelectTreeReport,
    set_auto_select_tree,
)
from .ungroup import PadPlan, UngroupReport, ungroup_pads, verify_ungroup
from .ungroup_batch import UngroupResult, UngroupTreeReport, ungroup_tree
from .sample_utils import (
    categorize_samples,
    categorize_by_folder,
    validate_samples,
    sort_samples_natural,
    SUPPORTED_AUDIO_FORMATS,
    DRUM_CATEGORIES,
)

__all__ = [
    "DrumRackCreator",
    "DrumRackModifier",
    "set_auto_select",
    "verify_auto_select",
    "AutoSelectReport",
    "set_auto_select_tree",
    "AutoSelectResult",
    "AutoSelectTreeReport",
    "ungroup_pads",
    "verify_ungroup",
    "PadPlan",
    "UngroupReport",
    "ungroup_tree",
    "UngroupResult",
    "UngroupTreeReport",
    "categorize_samples",
    "categorize_by_folder",
    "validate_samples",
    "sort_samples_natural",
    "SUPPORTED_AUDIO_FORMATS",
    "DRUM_CATEGORIES",
]
