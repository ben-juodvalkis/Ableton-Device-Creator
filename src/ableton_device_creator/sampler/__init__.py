"""
Sampler and Simpler device creation tools.

This module provides classes for creating Ableton Live sampler instruments
and Simpler devices from audio samples.
"""

from .creator import SamplerCreator
from .simpler import SimplerCreator
from .thin import ThinReport, plan_thin, thin_multisamples, verify_thin
from .thin_batch import ThinResult, ThinTreeReport, thin_tree

__all__ = [
    "SamplerCreator",
    "SimplerCreator",
    "ThinReport",
    "ThinResult",
    "ThinTreeReport",
    "plan_thin",
    "thin_multisamples",
    "thin_tree",
    "verify_thin",
]
