"""
Ableton Device Creator - Professional toolkit for Ableton Live device creation.

This package provides tools for creating, modifying, and managing Ableton Live
devices (.adg) and presets (.adv) programmatically.

Basic Usage:
    >>> from ableton_device_creator.core import decode_adg, encode_adg
    >>> from ableton_device_creator.drum_racks import DrumRackCreator, DrumRackModifier
    >>> from ableton_device_creator.macro_mapping import DrumPadColorMapper
    >>>
    >>> # Create drum rack
    >>> creator = DrumRackCreator("template.adg")
    >>> creator.from_folder("samples/", output="MyRack.adg")
    >>>
    >>> # Color the pads
    >>> colorizer = DrumPadColorMapper("MyRack.adg")
    >>> colorizer.apply_colors().save("Colored.adg")
    >>>
    >>> # Remap MIDI notes
    >>> modifier = DrumRackModifier("MyRack.adg")
    >>> modifier.remap_notes(shift=12).save("Remapped.adg")
"""

__version__ = "3.0.0-alpha.1"
__author__ = "Ben Juodvalkis"
__license__ = "MIT"

# Core utilities
from .core import decode_adg, encode_adv, encode_adg

# Drum rack creation
from .drum_racks import DrumRackCreator, DrumRackModifier

# Macro mapping
from .macro_mapping import DrumPadColorMapper, TransposeMapper, DRUM_COLORS

__all__ = [
    "__version__",
    # Core
    "decode_adg",
    "decode_adv",
    "encode_adg",
    "encode_adv",
    # Drum Racks
    "DrumRackCreator",
    "DrumRackModifier",
    # Macro Mapping
    "DrumPadColorMapper",
    "TransposeMapper",
    "DRUM_COLORS",
]
