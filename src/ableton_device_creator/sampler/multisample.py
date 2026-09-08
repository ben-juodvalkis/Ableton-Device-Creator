"""Build true multisampled Sampler instruments and multi-chain Instrument Racks.

Where `SamplerCreator` maps one sample per key (chromatic / drum / percussion
layouts), this module builds *zone maps*: each sample keeps its own root key and
spans a key range, with optional velocity layers and selector ranges. That is
what a real multisampled acoustic instrument needs.

The rack layout mirrors what Live writes for a `.adg` group preset:

    Ableton / GroupDevicePreset / BranchPresets / InstrumentBranchPreset *
        Name
        DevicePresets / AbletonDevicePreset / Device / MultiSampler
        MixerPreset
        BranchSelectorRange      <- chain-selector zone
        ZoneSettings             <- chain key/velocity zone
        DocumentColorIndex

Chains are produced by deep-copying the template's single branch, so every
device parameter the template carries (envelopes, filter, voice count) is
inherited unchanged.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Union
import copy
import wave
import xml.etree.ElementTree as ET

from ..core import decode_adg, encode_adg

__all__ = ["Zone", "Chain", "MultisampleRackCreator", "build_key_zones"]

XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


@dataclass
class Zone:
    """One MultiSamplePart: a sample with its root key and playable ranges."""

    sample: Path
    root_key: int
    key_min: int
    key_max: int
    vel_min: int = 1
    vel_max: int = 127
    selector_min: int = 0
    selector_max: int = 127
    volume: float = 1.0
    detune: int = 0
    name: Optional[str] = None

    def label(self) -> str:
        return self.name or Path(self.sample).stem


@dataclass
class Chain:
    """One rack chain holding a Sampler with its own zone map."""

    name: str
    zones: List[Zone] = field(default_factory=list)
    selector_min: int = 0
    selector_max: int = 127
    key_min: int = 0
    key_max: int = 127
    vel_min: int = 1
    vel_max: int = 127
    color_index: Optional[int] = None


def build_key_zones(
    roots: Sequence[int], low_limit: Optional[int] = None, high_limit: Optional[int] = None
):
    """Split a sorted list of root keys into contiguous key ranges.

    Boundaries fall at the midpoint between neighbouring roots. Returns a dict
    of root -> (key_min, key_max).
    """
    roots = sorted(set(roots))
    if not roots:
        return {}
    ranges = {}
    for i, root in enumerate(roots):
        if i == 0:
            kmin = low_limit if low_limit is not None else root
        else:
            kmin = (roots[i - 1] + root) // 2 + 1
        if i == len(roots) - 1:
            kmax = high_limit if high_limit is not None else root
        else:
            kmax = (root + roots[i + 1]) // 2
        ranges[root] = (min(kmin, root), max(kmax, root))
    return ranges


def _wav_frames(path: Path):
    """Return (frames, sample_rate) for a WAV, or (0, 44100) if unreadable."""
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes(), w.getframerate()
    except Exception:
        return 0, 44100


def _sub(parent, tag, value=None):
    e = ET.SubElement(parent, tag)
    if value is not None:
        e.set("Value", str(value))
    return e


def _range(parent, tag, vmin, vmax, xmin=None, xmax=None):
    e = ET.SubElement(parent, tag)
    _sub(e, "Min", vmin)
    _sub(e, "Max", vmax)
    _sub(e, "CrossfadeMin", vmin if xmin is None else xmin)
    _sub(e, "CrossfadeMax", vmax if xmax is None else xmax)
    return e


class MultisampleRackCreator:
    """Create an Instrument Rack of multisampled Samplers from zone maps."""

    def __init__(self, template: Union[str, Path]):
        self.template = Path(template)
        if not self.template.exists():
            raise FileNotFoundError(f"Template not found: {self.template}")

    # ---------------------------------------------------------------- public

    def build(
        self,
        chains: Sequence[Chain],
        output: Union[str, Path],
        rack_name: Optional[str] = None,
        num_voices: int = 32,
    ) -> Path:
        """Write an .adg Instrument Rack with one Sampler chain per `Chain`."""
        if not chains:
            raise ValueError("At least one chain is required")

        root = ET.fromstring(decode_adg(self.template))
        group = root.find(".//InstrumentGroupDevice")
        if group is None:
            raise ValueError(f"{self.template}: no InstrumentGroupDevice found")

        branch_presets = root.find(".//GroupDevicePreset/BranchPresets")
        if branch_presets is None:
            raise ValueError(f"{self.template}: no BranchPresets found")
        prototypes = list(branch_presets)
        if not prototypes:
            raise ValueError(f"{self.template}: template has no chain to copy")
        prototype = prototypes[0]

        for child in prototypes:
            branch_presets.remove(child)

        for index, chain in enumerate(chains):
            branch = copy.deepcopy(prototype)
            branch.set("Id", str(index))
            self._fill_branch(branch, chain, num_voices)
            branch_presets.append(branch)

        if rack_name:
            user_name = group.find("UserName")
            if user_name is not None:
                user_name.set("Value", rack_name)

        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        xml = XML_DECLARATION + ET.tostring(root, encoding="unicode")
        encode_adg(xml, output)
        return output

    def build_device(
        self,
        chain: Chain,
        output: Union[str, Path],
        num_voices: int = 32,
    ) -> Path:
        """Write a standalone Sampler `.adv` preset for a single zone map.

        A `.adv` is simply the device element directly under `<Ableton>`, so the
        Sampler is lifted out of the rack template and rewrapped.
        """
        root = ET.fromstring(decode_adg(self.template))
        branch = root.find(".//GroupDevicePreset/BranchPresets/InstrumentBranchPreset")
        if branch is None:
            raise ValueError(f"{self.template}: template has no chain to copy")
        branch = copy.deepcopy(branch)
        self._fill_branch(branch, chain, num_voices)

        sampler = branch.find(".//Device/MultiSampler")
        preset = ET.Element("Ableton", root.attrib)
        preset.append(sampler)

        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        encode_adg(XML_DECLARATION + ET.tostring(preset, encoding="unicode"), output)
        return output

    # --------------------------------------------------------------- private

    def _fill_branch(self, branch, chain: Chain, num_voices: int):
        name = branch.find("Name")
        if name is not None:
            name.set("Value", chain.name)

        sampler = branch.find(".//Device/MultiSampler")
        if sampler is None:
            raise ValueError("Template chain does not contain a MultiSampler")

        user_name = sampler.find("UserName")
        if user_name is not None:
            user_name.set("Value", chain.name)

        voices = sampler.find(".//NumVoices")
        if voices is not None:
            voices.set("Value", str(num_voices))

        sample_parts = sampler.find(".//MultiSampleMap/SampleParts")
        if sample_parts is None:
            raise ValueError("Template Sampler has no MultiSampleMap/SampleParts")
        for child in list(sample_parts):
            sample_parts.remove(child)
        for i, zone in enumerate(chain.zones):
            sample_parts.append(self._sample_part(i, zone))

        selector = branch.find("BranchSelectorRange")
        if selector is not None:
            selector.find("Min").set("Value", str(chain.selector_min))
            selector.find("Max").set("Value", str(chain.selector_max))
            selector.find("CrossfadeMin").set("Value", str(chain.selector_min))
            selector.find("CrossfadeMax").set("Value", str(chain.selector_max))

        zone_settings = branch.find("ZoneSettings")
        if zone_settings is not None:
            kr = zone_settings.find("KeyRange")
            kr.find("Min").set("Value", str(chain.key_min))
            kr.find("Max").set("Value", str(chain.key_max))
            kr.find("CrossfadeMin").set("Value", str(chain.key_min))
            kr.find("CrossfadeMax").set("Value", str(chain.key_max))
            vr = zone_settings.find("VelocityRange")
            vr.find("Min").set("Value", str(chain.vel_min))
            vr.find("Max").set("Value", str(chain.vel_max))
            vr.find("CrossfadeMin").set("Value", str(chain.vel_min))
            vr.find("CrossfadeMax").set("Value", str(chain.vel_max))

        if chain.color_index is not None:
            color = branch.find("DocumentColorIndex")
            if color is not None:
                color.set("Value", str(chain.color_index))
            auto = branch.find("AutoColored")
            if auto is not None:
                auto.set("Value", "false")

    def _sample_part(self, index: int, zone: Zone) -> ET.Element:
        sample = Path(zone.sample)
        frames, rate = _wav_frames(sample)

        part = ET.Element("MultiSamplePart")
        part.set("Id", str(index))
        part.set("HasImportedSlicePoints", "false")
        _sub(part, "LomId", index)
        _sub(part, "Name", zone.label())
        _sub(part, "Selection", "true")
        _sub(part, "IsActive", "true")
        _sub(part, "Solo", "false")
        _range(part, "KeyRange", zone.key_min, zone.key_max)
        _range(part, "VelocityRange", zone.vel_min, zone.vel_max)
        _range(part, "SelectorRange", zone.selector_min, zone.selector_max)
        _sub(part, "RootKey", zone.root_key)
        _sub(part, "Detune", zone.detune)
        _sub(part, "TuneScale", 100)
        _sub(part, "Panorama", 0)
        _sub(part, "Volume", zone.volume)
        _sub(part, "Link", "false")

        sample_ref = ET.SubElement(part, "SampleRef")
        file_ref = ET.SubElement(sample_ref, "FileRef")
        _sub(file_ref, "Path", str(sample.resolve()))
        _sub(file_ref, "RelativePath", f"Samples/{sample.name}")
        _sub(file_ref, "RelativePathType", 0)
        _sub(file_ref, "Type", 1)
        _sub(file_ref, "LivePackName", "")
        _sub(file_ref, "LivePackId", "")
        _sub(file_ref, "OriginalFileSize", sample.stat().st_size if sample.exists() else 0)
        _sub(file_ref, "OriginalCrc", 0)
        _sub(sample_ref, "LastModDate", 0)
        ET.SubElement(sample_ref, "SourceContext")
        _sub(sample_ref, "SampleUsageHint", 0)
        _sub(sample_ref, "DefaultDuration", frames)
        _sub(sample_ref, "DefaultSampleRate", rate)
        return part
