"""
Sampler and Simpler device creation tools.

This module provides classes for creating Ableton Live sampler instruments
and Simpler devices from audio samples.
"""

from .creator import SamplerCreator
from .simpler import SimplerCreator
from .envelope import EnvelopeReport, set_envelope_param, verify_envelope_set
from .envelope_batch import EnvelopeResult, EnvelopeTreeReport, set_envelope_tree
from .thin import ThinReport, plan_thin, thin_multisamples, verify_thin
from .thin_batch import ThinResult, ThinTreeReport, thin_tree

__all__ = [
    "EnvelopeReport",
    "EnvelopeResult",
    "EnvelopeTreeReport",
    "SamplerCreator",
    "SimplerCreator",
    "ThinReport",
    "ThinResult",
    "ThinTreeReport",
    "plan_thin",
    "set_envelope_param",
    "set_envelope_tree",
    "thin_multisamples",
    "thin_tree",
    "verify_envelope_set",
    "verify_thin",
]
