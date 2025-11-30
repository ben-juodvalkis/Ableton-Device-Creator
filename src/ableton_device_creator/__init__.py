"""
Ableton Device Creator - Professional toolkit for Ableton Live device creation.

This package provides tools for creating, modifying, and managing Ableton Live
devices (.adg) and presets (.adv) programmatically.

Basic Usage:
    >>> from ableton_device_creator.core import decode_adg, encode_adg
    >>> from ableton_device_creator.drum_racks import DrumRackCreator
    >>> from ableton_device_creator.macro_mapping import CCControlMapper
    >>>
    >>> # Create drum rack
    >>> creator = DrumRackCreator("template.adg")
    >>> creator.from_folder("samples/", output="MyRack.adg")
    >>>
    >>> # Add CC control
    >>> mapper = CCControlMapper("MyRack.adg")
    >>> mapper.add_cc_mappings({3: (119, 15)}).save("Mapped.adg")
"""

__version__ = "3.0.0-alpha.1"
__author__ = "Ben Juodvalkis"
__license__ = "MIT"

# Core utilities
from .core import decode_adg, encode_adv, encode_adg

# Drum rack creation
from .drum_racks import DrumRackCreator

# Macro mapping
from .macro_mapping import CCControlMapper, DrumPadColorMapper, TransposeMapper, DRUM_COLORS

__all__ = [
    "__version__",
    # Core
    "decode_adg",
    "decode_adv",
    "encode_adg",
    "encode_adv",
    # Drum Racks
    "DrumRackCreator",
    # Macro Mapping
    "CCControlMapper",
    "DrumPadColorMapper",
    "TransposeMapper",
    "DRUM_COLORS",
]
