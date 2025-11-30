"""SamplerCreator class for creating Multi-Sampler instruments."""

from pathlib import Path
from typing import Dict, List, Optional, Union
import xml.etree.ElementTree as ET
import logging

from ..core import decode_adg, encode_adg

logger = logging.getLogger(__name__)

# Chromatic MIDI note mapping (C-2 to G8, 32 samples per instrument)
CHROMATIC_START = 0  # C-2 in MIDI
CHROMATIC_NOTES_PER_INSTRUMENT = 32


class SamplerCreator:
    """
    Create Multi-Sampler instruments from audio samples.

    This class consolidates functionality from:
    - main_sampler.py (chromatic mapping)
    - main_drumstyle_sampler.py (drum-style layout)
    - main_phrases_sampler.py (phrase/loop mapping)
    - main_percussion_sampler.py (percussion layout)

    Example:
        >>> creator = SamplerCreator(template="templates/sampler-rack.adg")
        >>> sampler = creator.from_folder("/samples", output="MySampler.adg")
    """

    def __init__(self, template: Union[str, Path]):
        """
        Initialize creator with template.

        Args:
            template: Path to template ADG/ADV file with Multi-Sampler

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        self.template = Path(template)
        if not self.template.exists():
            raise FileNotFoundError(f"Template not found: {self.template}")

    def from_folder(
        self,
        samples_dir: Union[str, Path],
        output: Optional[Union[str, Path]] = None,
        layout: str = "chromatic",
        samples_per_instrument: int = 32,
    ) -> Path:
        """
        Create sampler instrument from folder of samples.

        Args:
            samples_dir: Folder containing audio samples
            output: Output path (auto-generated if None)
            layout: Key mapping layout ("chromatic", "drum", "percussion")
            samples_per_instrument: Max samples per instrument (default 32)

        Returns:
            Path to created sampler instrument

        Example:
            >>> creator.from_folder("/samples/kicks", layout="chromatic")
            PosixPath('output/kicks_sampler.adg')
        """
        samples_dir = Path(samples_dir)
        logger.info(f"Creating sampler from {samples_dir}")

        # Auto-generate output path
        if output is None:
            output = Path("output") / f"{samples_dir.name}_sampler.adg"
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Get samples
        samples = self._get_samples(samples_dir)
        if not samples:
            raise ValueError(f"No valid audio samples found in {samples_dir}")

        logger.info(f"Found {len(samples)} valid samples")

        # Limit to samples_per_instrument
        samples = samples[:samples_per_instrument]

        # Load template
        template_xml = decode_adg(self.template)

        # Transform based on layout
        if layout == "chromatic":
            transformed_xml = self._create_chromatic_mapping(template_xml, samples)
        elif layout == "drum":
            transformed_xml = self._create_drum_mapping(template_xml, samples)
        elif layout == "percussion":
            transformed_xml = self._create_percussion_mapping(template_xml, samples)
        else:
            raise ValueError(f"Unknown layout: {layout}")

        # Save
        result = encode_adg(transformed_xml, output)
        logger.info(f"Created sampler: {result}")

        return result

    def from_samples_list(
        self,
        samples: List[Union[str, Path]],
        output: Union[str, Path],
        layout: str = "chromatic",
    ) -> Path:
        """
        Create sampler from explicit list of samples.

        Args:
            samples: List of sample file paths
            output: Output path
            layout: Key mapping layout

        Returns:
            Path to created sampler
        """
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Convert to Path objects and validate
        sample_paths = [Path(s) for s in samples]
        valid_samples = [s for s in sample_paths if s.exists()]

        if not valid_samples:
            raise ValueError("No valid samples provided")

        logger.info(f"Creating sampler from {len(valid_samples)} samples")

        # Load template
        template_xml = decode_adg(self.template)

        # Transform based on layout
        if layout == "chromatic":
            transformed_xml = self._create_chromatic_mapping(template_xml, valid_samples)
        elif layout == "drum":
            transformed_xml = self._create_drum_mapping(template_xml, valid_samples)
        elif layout == "percussion":
            transformed_xml = self._create_percussion_mapping(template_xml, valid_samples)
        else:
            raise ValueError(f"Unknown layout: {layout}")

        # Save
        return encode_adg(transformed_xml, output)

    def _get_samples(self, folder: Path) -> List[Path]:
        """Get all valid audio samples from folder."""
        valid_extensions = {'.wav', '.aif', '.aiff', '.flac', '.mp3'}
        samples = []

        for ext in valid_extensions:
            samples.extend(folder.glob(f'*{ext}'))
            samples.extend(folder.glob(f'*{ext.upper()}'))

        # Sort naturally
        samples.sort(key=lambda p: p.name.lower())

        return samples

    def _create_chromatic_mapping(
        self, xml_content: bytes, samples: List[Path]
    ) -> bytes:
        """
        Create chromatic key mapping (samples mapped chromatically).

        Maps samples to consecutive MIDI notes starting from C-2 (note 0).
        Each sample spans 1 semitone.

        Args:
            xml_content: Template XML
            samples: List of sample paths

        Returns:
            Transformed XML as bytes
        """
        root = ET.fromstring(xml_content)

        # Find MultiSampleMap element
        sample_map = root.find(".//MultiSampleMap")
        if sample_map is None:
            raise ValueError("Template missing MultiSampleMap element")

        # Clear existing sample parts
        sample_parts = sample_map.find("SampleParts")
        if sample_parts is not None:
            sample_map.remove(sample_parts)

        # Create new SampleParts
        new_parts = ET.SubElement(sample_map, "SampleParts")

        # Add each sample chromatically
        for i, sample_path in enumerate(samples):
            midi_note = CHROMATIC_START + i
            if midi_note > 127:
                logger.warning(f"Skipping {sample_path.name} - exceeds MIDI range")
                break

            # Create sample part
            part = self._create_sample_part(
                index=i,
                sample_path=sample_path,
                key_min=midi_note,
                key_max=midi_note,
                root_key=midi_note,
            )
            new_parts.append(part)
            logger.debug(f"Mapped {sample_path.name} to note {midi_note}")

        return ET.tostring(root, encoding='utf-8', xml_declaration=True)

    def _create_drum_mapping(self, xml_content: bytes, samples: List[Path]) -> bytes:
        """
        Create drum-style mapping (8 kicks, 8 snares, 8 hats, 8 perc).

        Layout:
        - Kicks: C-2 to G-2 (notes 0-7)
        - Snares: G#-2 to D#-1 (notes 8-15)
        - Hats: E-1 to B-1 (notes 16-23)
        - Percussion: C0 to G0 (notes 24-31)

        Args:
            xml_content: Template XML
            samples: List of sample paths (max 32)

        Returns:
            Transformed XML as bytes
        """
        root = ET.fromstring(xml_content)

        # Find MultiSampleMap element
        sample_map = root.find(".//MultiSampleMap")
        if sample_map is None:
            raise ValueError("Template missing MultiSampleMap element")

        # Clear existing sample parts
        sample_parts = sample_map.find("SampleParts")
        if sample_parts is not None:
            sample_map.remove(sample_parts)

        # Create new SampleParts
        new_parts = ET.SubElement(sample_map, "SampleParts")

        # Map samples in groups of 8
        group_size = 8
        for i, sample_path in enumerate(samples[:32]):
            midi_note = i  # 0-31
            part = self._create_sample_part(
                index=i,
                sample_path=sample_path,
                key_min=midi_note,
                key_max=midi_note,
                root_key=midi_note,
            )
            new_parts.append(part)
            logger.debug(f"Mapped {sample_path.name} to note {midi_note}")

        return ET.tostring(root, encoding='utf-8', xml_declaration=True)

    def _create_percussion_mapping(
        self, xml_content: bytes, samples: List[Path]
    ) -> bytes:
        """
        Create percussion mapping (similar to chromatic but starting at C1).

        Maps samples chromatically starting from MIDI note 36 (C1).

        Args:
            xml_content: Template XML
            samples: List of sample paths

        Returns:
            Transformed XML as bytes
        """
        root = ET.fromstring(xml_content)

        # Find MultiSampleMap element
        sample_map = root.find(".//MultiSampleMap")
        if sample_map is None:
            raise ValueError("Template missing MultiSampleMap element")

        # Clear existing sample parts
        sample_parts = sample_map.find("SampleParts")
        if sample_parts is not None:
            sample_map.remove(sample_parts)

        # Create new SampleParts
        new_parts = ET.SubElement(sample_map, "SampleParts")

        # Add each sample starting from C1 (note 36)
        start_note = 36  # C1
        for i, sample_path in enumerate(samples):
            midi_note = start_note + i
            if midi_note > 127:
                logger.warning(f"Skipping {sample_path.name} - exceeds MIDI range")
                break

            part = self._create_sample_part(
                index=i,
                sample_path=sample_path,
                key_min=midi_note,
                key_max=midi_note,
                root_key=midi_note,
            )
            new_parts.append(part)
            logger.debug(f"Mapped {sample_path.name} to note {midi_note}")

        return ET.tostring(root, encoding='utf-8', xml_declaration=True)

    def _create_sample_part(
        self,
        index: int,
        sample_path: Path,
        key_min: int,
        key_max: int,
        root_key: int,
    ) -> ET.Element:
        """
        Create a MultiSamplePart element for the given sample.

        Args:
            index: Sample part ID
            sample_path: Path to sample file
            key_min: Minimum MIDI note
            key_max: Maximum MIDI note
            root_key: Root/center MIDI note

        Returns:
            MultiSamplePart XML element
        """
        part = ET.Element("MultiSamplePart")
        part.set("Id", str(index))
        part.set("HasImportedSlicePoints", "false")

        # LomId
        lom_id = ET.SubElement(part, "LomId")
        lom_id.set("Value", str(index))

        # Name
        name = ET.SubElement(part, "Name")
        name.set("Value", sample_path.stem)

        # Selection
        selection = ET.SubElement(part, "Selection")
        selection.set("Value", "true")

        # IsActive
        is_active = ET.SubElement(part, "IsActive")
        is_active.set("Value", "true")

        # Solo
        solo = ET.SubElement(part, "Solo")
        solo.set("Value", "false")

        # Key range
        key_range = ET.SubElement(part, "KeyRange")
        key_min_elem = ET.SubElement(key_range, "Min")
        key_min_elem.set("Value", str(key_min))
        key_max_elem = ET.SubElement(key_range, "Max")
        key_max_elem.set("Value", str(key_max))
        # Crossfade (no crossfade for one-note zones)
        crossfade_min = ET.SubElement(key_range, "CrossfadeMin")
        crossfade_min.set("Value", str(key_min))
        crossfade_max = ET.SubElement(key_range, "CrossfadeMax")
        crossfade_max.set("Value", str(key_max))

        # Velocity range
        velocity_range = ET.SubElement(part, "VelocityRange")
        vel_min = ET.SubElement(velocity_range, "Min")
        vel_min.set("Value", "1")
        vel_max = ET.SubElement(velocity_range, "Max")
        vel_max.set("Value", "127")
        vel_crossfade_min = ET.SubElement(velocity_range, "CrossfadeMin")
        vel_crossfade_min.set("Value", "1")
        vel_crossfade_max = ET.SubElement(velocity_range, "CrossfadeMax")
        vel_crossfade_max.set("Value", "127")

        # Selector range
        selector_range = ET.SubElement(part, "SelectorRange")
        sel_min = ET.SubElement(selector_range, "Min")
        sel_min.set("Value", "0")
        sel_max = ET.SubElement(selector_range, "Max")
        sel_max.set("Value", "127")
        sel_crossfade_min = ET.SubElement(selector_range, "CrossfadeMin")
        sel_crossfade_min.set("Value", "0")
        sel_crossfade_max = ET.SubElement(selector_range, "CrossfadeMax")
        sel_crossfade_max.set("Value", "127")

        # Root key
        root_key_elem = ET.SubElement(part, "RootKey")
        root_key_elem.set("Value", str(root_key))

        # Detune
        detune = ET.SubElement(part, "Detune")
        detune.set("Value", "0")

        # TuneScale
        tune_scale = ET.SubElement(part, "TuneScale")
        tune_scale.set("Value", "100")

        # Panorama
        panorama = ET.SubElement(part, "Panorama")
        panorama.set("Value", "0")

        # Volume
        volume = ET.SubElement(part, "Volume")
        volume.set("Value", "1")

        # Link
        link = ET.SubElement(part, "Link")
        link.set("Value", "false")

        # SampleRef
        sample_ref = ET.SubElement(part, "SampleRef")

        # FileRef
        file_ref = ET.SubElement(sample_ref, "FileRef")

        # Path (absolute)
        abs_path = str(sample_path.resolve())
        path_elem = ET.SubElement(file_ref, "Path")
        path_elem.set("Value", abs_path)

        # RelativePath
        rel_path_elem = ET.SubElement(file_ref, "RelativePath")
        rel_path_elem.set("Value", f"Samples/{sample_path.name}")

        # RelativePathType (0 = use absolute)
        path_type = ET.SubElement(file_ref, "RelativePathType")
        path_type.set("Value", "0")

        # Type (1 = sample file)
        file_type = ET.SubElement(file_ref, "Type")
        file_type.set("Value", "1")

        # LivePackName
        live_pack_name = ET.SubElement(file_ref, "LivePackName")
        live_pack_name.set("Value", "")

        # LivePackId
        live_pack_id = ET.SubElement(file_ref, "LivePackId")
        live_pack_id.set("Value", "")

        # OriginalFileSize
        original_size = ET.SubElement(file_ref, "OriginalFileSize")
        original_size.set("Value", "0")

        # OriginalCrc
        original_crc = ET.SubElement(file_ref, "OriginalCrc")
        original_crc.set("Value", "0")

        # LastModDate
        last_mod = ET.SubElement(sample_ref, "LastModDate")
        last_mod.set("Value", "0")

        # SourceContext
        source_context = ET.SubElement(sample_ref, "SourceContext")

        # SampleUsageHint
        usage_hint = ET.SubElement(sample_ref, "SampleUsageHint")
        usage_hint.set("Value", "0")

        # DefaultDuration
        default_duration = ET.SubElement(sample_ref, "DefaultDuration")
        default_duration.set("Value", "0")

        # DefaultSampleRate
        default_sample_rate = ET.SubElement(sample_ref, "DefaultSampleRate")
        default_sample_rate.set("Value", "48000")

        return part
