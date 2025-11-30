"""
Ableton Device Creator - Professional toolkit for Ableton Live device creation.

This package provides tools for creating, modifying, and managing Ableton Live
devices (.adg) and presets (.adv) programmatically.

Basic Usage:
    >>> from ableton_device_creator.core import decode_adg, encode_adg
    >>> xml = decode_adg("MyRack.adg")
    >>> # Modify XML...
    >>> encode_adg(xml, "Modified.adg")
"""

__version__ = "3.0.0-alpha.1"
__author__ = "Ben Juodvalkis"
__license__ = "MIT"

# Core utilities
from .core import decode_adg, encode_adg

__all__ = [
    "__version__",
    "decode_adg",
    "encode_adg",
]
