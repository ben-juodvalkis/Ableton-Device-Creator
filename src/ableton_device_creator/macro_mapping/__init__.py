"""
Macro mapping utilities for Ableton Live devices.

This module provides tools for mapping parameters to macros, adding CC control,
coloring drum pads, and configuring transpose mappings.
"""

from .cc_controller import CCControlMapper
from .color_mapper import DrumPadColorMapper, DRUM_COLORS
from .transpose import TransposeMapper

__all__ = [
    "CCControlMapper",
    "DrumPadColorMapper",
    "TransposeMapper",
    "DRUM_COLORS",
]
