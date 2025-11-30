"""SimplerCreator class for creating individual Simpler devices."""

from pathlib import Path
from typing import List, Optional, Union
import xml.etree.ElementTree as ET
import logging

from ..core import decode_adg, encode_adg

logger = logging.getLogger(__name__)


class SimplerCreator:
    """
    Create Simpler devices from audio samples.

    Creates individual Simpler (.adv) devices for each sample file.
    Simpler is Ableton's simple sampler device for basic sample playback.

    Consolidates functionality from:
    - simpler/main_simpler.py

    Example:
        >>> creator = SimplerCreator(template="templates/simpler-template.adv")
        >>> creator.from_folder("/samples", output_folder="output/simplers/")
    """

    def __init__(self, template: Union[str, Path]):
        """
        Initialize creator with template.

        Args:
            template: Path to template ADV file with Simpler device

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        self.template = Path(template)
        if not self.template.exists():
            raise FileNotFoundError(f"Template not found: {self.template}")

    def from_folder(
        self,
        samples_dir: Union[str, Path],
        output_folder: Optional[Union[str, Path]] = None,
        recursive: bool = False,
    ) -> List[Path]:
        """
        Create individual Simpler devices for each sample in folder.

        Args:
            samples_dir: Folder containing audio samples
            output_folder: Output folder for .adv files (auto-generated if None)
            recursive: Process subdirectories recursively

        Returns:
            List of created .adv file paths

        Example:
            >>> creator.from_folder("/samples/kicks")
            [PosixPath('output/Kick_01.adv'), PosixPath('output/Kick_02.adv')]
        """
        samples_dir = Path(samples_dir)
        logger.info(f"Creating Simpler devices from {samples_dir}")

        # Auto-generate output folder
        if output_folder is None:
            output_folder = Path("output") / f"{samples_dir.name}_simplers"
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        # Get samples
        samples = self._get_samples(samples_dir, recursive=recursive)
        if not samples:
            raise ValueError(f"No valid audio samples found in {samples_dir}")

        logger.info(f"Found {len(samples)} samples - creating Simpler devices")

        # Create a Simpler for each sample
        created_files = []
        for sample_path in samples:
            try:
                output_path = output_folder / f"{sample_path.stem}.adv"
                result = self.from_sample(sample_path, output_path)
                created_files.append(result)
                logger.debug(f"Created {output_path.name}")
            except Exception as e:
                logger.error(f"Failed to create Simpler for {sample_path.name}: {e}")
                continue

        logger.info(f"Created {len(created_files)} Simpler devices in {output_folder}")
        return created_files

    def from_sample(
        self, sample_path: Union[str, Path], output: Union[str, Path]
    ) -> Path:
        """
        Create a Simpler device from a single sample.

        Args:
            sample_path: Path to audio sample file
            output: Output .adv file path

        Returns:
            Path to created .adv file

        Example:
            >>> creator.from_sample("/samples/kick.wav", "output/kick.adv")
            PosixPath('output/kick.adv')
        """
        sample_path = Path(sample_path)
        output = Path(output)

        if not sample_path.exists():
            raise FileNotFoundError(f"Sample not found: {sample_path}")

        output.parent.mkdir(parents=True, exist_ok=True)

        # Load template
        template_xml = decode_adg(self.template)

        # Transform XML to use this sample
        transformed_xml = self._set_sample(template_xml, sample_path)

        # Save
        result = encode_adg(transformed_xml, output)
        logger.debug(f"Created Simpler: {result}")

        return result

    def _get_samples(self, folder: Path, recursive: bool = False) -> List[Path]:
        """Get all valid audio samples from folder."""
        valid_extensions = {'.wav', '.aif', '.aiff', '.flac', '.mp3'}
        samples = []

        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'

        for ext in valid_extensions:
            samples.extend(folder.glob(f'{pattern}{ext}'))
            samples.extend(folder.glob(f'{pattern}{ext.upper()}'))

        # Sort naturally
        samples.sort(key=lambda p: p.name.lower())

        return samples

    def _set_sample(self, xml_content: bytes, sample_path: Path) -> bytes:
        """
        Transform Simpler XML to use the specified sample.

        Args:
            xml_content: Template XML content
            sample_path: Path to sample file

        Returns:
            Transformed XML as bytes
        """
        root = ET.fromstring(xml_content)

        # Find the MultiSampleMap element
        multi_sample_map = root.find(".//MultiSampleMap")
        if multi_sample_map is None:
            raise ValueError("Template missing MultiSampleMap element")

        # Clear existing SampleParts
        sample_parts = multi_sample_map.find("SampleParts")
        if sample_parts is not None:
            sample_parts.clear()
        else:
            sample_parts = ET.SubElement(multi_sample_map, "SampleParts")

        # Create new MultiSamplePart
        multi_sample_part = ET.SubElement(sample_parts, "MultiSamplePart")
        multi_sample_part.set("Id", "0")
        multi_sample_part.set("InitUpdateAreSlicesFromOnsetsEditableAfterRead", "false")
        multi_sample_part.set("HasImportedSlicePoints", "true")
        multi_sample_part.set("NeedsAnalysisData", "true")

        # Add required elements
        lom_id = ET.SubElement(multi_sample_part, "LomId")
        lom_id.set("Value", "0")

        name = ET.SubElement(multi_sample_part, "Name")
        name.set("Value", sample_path.stem)

        selection = ET.SubElement(multi_sample_part, "Selection")
        selection.set("Value", "true")

        is_active = ET.SubElement(multi_sample_part, "IsActive")
        is_active.set("Value", "true")

        solo = ET.SubElement(multi_sample_part, "Solo")
        solo.set("Value", "false")

        # Add key range (full keyboard)
        key_range = ET.SubElement(multi_sample_part, "KeyRange")
        for elem_name, value in [
            ("Min", "0"),
            ("Max", "127"),
            ("CrossfadeMin", "0"),
            ("CrossfadeMax", "127"),
        ]:
            elem = ET.SubElement(key_range, elem_name)
            elem.set("Value", value)

        # Add velocity range (full range)
        velocity_range = ET.SubElement(multi_sample_part, "VelocityRange")
        for elem_name, value in [
            ("Min", "1"),
            ("Max", "127"),
            ("CrossfadeMin", "1"),
            ("CrossfadeMax", "127"),
        ]:
            elem = ET.SubElement(velocity_range, elem_name)
            elem.set("Value", value)

        # Add selector range
        selector_range = ET.SubElement(multi_sample_part, "SelectorRange")
        for elem_name, value in [
            ("Min", "0"),
            ("Max", "127"),
            ("CrossfadeMin", "0"),
            ("CrossfadeMax", "127"),
        ]:
            elem = ET.SubElement(selector_range, elem_name)
            elem.set("Value", value)

        # Root key (middle C = 60)
        root_key = ET.SubElement(multi_sample_part, "RootKey")
        root_key.set("Value", "60")

        # Detune
        detune = ET.SubElement(multi_sample_part, "Detune")
        detune.set("Value", "0")

        # TuneScale
        tune_scale = ET.SubElement(multi_sample_part, "TuneScale")
        tune_scale.set("Value", "100")

        # Panorama (center)
        panorama = ET.SubElement(multi_sample_part, "Panorama")
        panorama.set("Value", "0")

        # Volume (unity)
        volume = ET.SubElement(multi_sample_part, "Volume")
        volume.set("Value", "1")

        # Link
        link = ET.SubElement(multi_sample_part, "Link")
        link.set("Value", "false")

        # Create SampleRef with all required elements
        sample_ref = ET.SubElement(multi_sample_part, "SampleRef")

        # Create FileRef
        file_ref = ET.SubElement(sample_ref, "FileRef")

        # Convert to absolute path
        abs_path = str(sample_path.resolve())

        # Add Path element
        path_elem = ET.SubElement(file_ref, "Path")
        path_elem.set("Value", abs_path)

        # Add RelativePath element
        rel_path_elem = ET.SubElement(file_ref, "RelativePath")
        rel_path = f"Samples/{sample_path.name}"
        rel_path_elem.set("Value", rel_path)

        # Add RelativePathType element (0 = use absolute)
        path_type_elem = ET.SubElement(file_ref, "RelativePathType")
        path_type_elem.set("Value", "0")

        # Add Type element (1 = sample file)
        type_elem = ET.SubElement(file_ref, "Type")
        type_elem.set("Value", "1")

        # Add LivePackName and LivePackId
        live_pack_name = ET.SubElement(file_ref, "LivePackName")
        live_pack_name.set("Value", "")

        live_pack_id = ET.SubElement(file_ref, "LivePackId")
        live_pack_id.set("Value", "")

        # Add OriginalFileSize and OriginalCrc
        original_file_size = ET.SubElement(file_ref, "OriginalFileSize")
        original_file_size.set("Value", "0")

        original_crc = ET.SubElement(file_ref, "OriginalCrc")
        original_crc.set("Value", "0")

        # Add LastModDate
        last_mod_date = ET.SubElement(sample_ref, "LastModDate")
        last_mod_date.set("Value", "0")

        # Add SourceContext
        source_context = ET.SubElement(sample_ref, "SourceContext")

        # Add SampleUsageHint
        sample_usage_hint = ET.SubElement(sample_ref, "SampleUsageHint")
        sample_usage_hint.set("Value", "0")

        # Add DefaultDuration
        default_duration = ET.SubElement(sample_ref, "DefaultDuration")
        default_duration.set("Value", "0")

        # Add DefaultSampleRate
        default_sample_rate = ET.SubElement(sample_ref, "DefaultSampleRate")
        default_sample_rate.set("Value", "48000")

        # Add SamplesToAutoWarp
        samples_to_auto_warp = ET.SubElement(sample_ref, "SamplesToAutoWarp")
        samples_to_auto_warp.set("Value", "1")

        logger.debug(f"Set sample to: {abs_path}")

        # Convert back to bytes with XML declaration
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def get_sample_info(self, adv_file: Union[str, Path]) -> dict:
        """
        Get information about the sample in a Simpler device.

        Args:
            adv_file: Path to .adv file

        Returns:
            Dictionary with sample information

        Example:
            >>> info = creator.get_sample_info("kick.adv")
            >>> print(info['sample_path'])
            /samples/kick.wav
        """
        adv_file = Path(adv_file)
        if not adv_file.exists():
            raise FileNotFoundError(f"ADV file not found: {adv_file}")

        # Decode
        xml_content = decode_adg(adv_file)
        root = ET.fromstring(xml_content)

        info = {}

        # Find the sample reference
        sample_ref = root.find(".//MultiSamplePart//SampleRef/FileRef")
        if sample_ref is not None:
            # Get sample path
            path_elem = sample_ref.find("Path")
            if path_elem is not None:
                info["sample_path"] = path_elem.get("Value")

            # Get relative path
            rel_path_elem = sample_ref.find("RelativePath")
            if rel_path_elem is not None:
                info["relative_path"] = rel_path_elem.get("Value")

            # Get path type
            path_type_elem = sample_ref.find("RelativePathType")
            if path_type_elem is not None:
                info["path_type"] = path_type_elem.get("Value")

        # Get sample rate
        sample_rate = root.find(".//MultiSamplePart//SampleRef/DefaultSampleRate")
        if sample_rate is not None:
            info["sample_rate"] = sample_rate.get("Value")

        # Get duration
        duration = root.find(".//MultiSamplePart//SampleRef/DefaultDuration")
        if duration is not None:
            info["duration"] = duration.get("Value")

        # Get name
        name = root.find(".//MultiSamplePart/Name")
        if name is not None:
            info["name"] = name.get("Value")

        return info
