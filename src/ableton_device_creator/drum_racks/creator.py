"""DrumRackCreator class for creating drum racks from samples."""

from pathlib import Path
from typing import Dict, List, Optional, Union
import xml.etree.ElementTree as ET

from ..core import decode_adg, encode_adg
from .sample_utils import (
    categorize_samples,
    categorize_by_folder,
    validate_samples,
    sort_samples_natural,
)


# MIDI note mapping for drum pads (C1-G3, 32 pads)
DRUM_PAD_NOTES = list(range(36, 68))


class DrumRackCreator:
    """
    Create drum racks from sample folders.

    This class consolidates functionality from multiple legacy scripts:
    - main_simple_folder.py
    - main.py
    - main_percussion.py
    - create_multivelocity_drum_rack_v2.py

    Example:
        >>> creator = DrumRackCreator(template="templates/drum-rack.adg")
        >>> rack = creator.from_folder("/samples", output="MyRack.adg")
        PosixPath('output/MyRack.adg')
    """

    def __init__(self, template: Union[str, Path]):
        """
        Initialize creator with template ADG file.

        Args:
            template: Path to template drum rack ADG file

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
        categorize: bool = False,
        recursive: bool = True,
        max_samples: int = 32,
    ) -> Path:
        """
        Create drum rack from folder of samples.

        Simple mode: Fills pads sequentially with all found samples.

        Args:
            samples_dir: Folder containing samples
            output: Output path (auto-generated if None)
            categorize: Attempt to categorize samples by type
            recursive: Search subdirectories
            max_samples: Maximum number of samples to use (default 32)

        Returns:
            Path to created drum rack

        Example:
            >>> creator.from_folder("/samples/kicks")
            PosixPath('output/kicks.adg')
        """
        samples_dir = Path(samples_dir)

        if not samples_dir.exists():
            raise FileNotFoundError(f"Folder not found: {samples_dir}")

        # Auto-generate output path
        if output is None:
            output = Path("output") / f"{samples_dir.name}.adg"
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Load template
        xml_content = decode_adg(self.template)

        # Get samples
        if categorize:
            categorized = categorize_samples(samples_dir, recursive=recursive)
            samples = self._flatten_categories(categorized)
        else:
            samples = self._get_all_samples(samples_dir, recursive)

        samples = validate_samples(samples)
        samples = sort_samples_natural(samples)

        # Limit to max_samples
        samples = samples[:max_samples]

        if not samples:
            raise ValueError(f"No audio samples found in {samples_dir}")

        print(f"Found {len(samples)} samples, creating drum rack...")

        # Transform XML with samples
        sample_paths = [str(s.absolute()) for s in samples]
        modified_xml = self._transform_drum_rack(xml_content, sample_paths)

        # Save
        result = encode_adg(modified_xml, output)
        print(f"✓ Created drum rack: {result}")

        return result

    def from_categorized_folders(
        self,
        samples_dir: Union[str, Path],
        output: Optional[Union[str, Path]] = None,
        layout: str = "standard",
    ) -> Path:
        """
        Create drum rack from folder with categorized subfolders.

        Expects structure like:
        - samples/Kick/*.wav
        - samples/Snare/*.wav
        - samples/Hat/*.wav

        Args:
            samples_dir: Directory with categorized subfolders
            output: Output path
            layout: Note layout ("standard", "808", "percussion")

        Returns:
            Path to created drum rack

        Example:
            >>> creator.from_categorized_folders("/library/drums")
            PosixPath('output/drums.adg')
        """
        samples_dir = Path(samples_dir)

        if not samples_dir.exists():
            raise FileNotFoundError(f"Folder not found: {samples_dir}")

        # Auto-generate output path
        if output is None:
            output = Path("output") / f"{samples_dir.name}_categorized.adg"
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Categorize by folder structure
        categorized = categorize_by_folder(samples_dir)

        # Get note layout
        note_map = self._get_note_layout(layout)

        # Load template
        xml_content = decode_adg(self.template)

        # Build sample list with specific note positions
        sample_list = [None] * 32  # Initialize with None

        print(f"Organizing samples by category:")
        for category, samples in categorized.items():
            if category == 'uncategorized' or not samples:
                continue

            samples = validate_samples(samples)
            samples = sort_samples_natural(samples)

            if category in note_map:
                start_note = note_map[category]
                # Calculate pad index (note 36 = pad 0)
                pad_index = start_note - 36

                # Fill up to 4 samples for this category
                for i, sample in enumerate(samples[:4]):
                    if pad_index + i < 32:
                        sample_list[pad_index + i] = str(sample.absolute())
                        print(f"  {category}: {sample.name} → Pad {pad_index + i + 1} (Note {start_note + i})")

        # Remove trailing Nones
        while sample_list and sample_list[-1] is None:
            sample_list.pop()

        if not any(sample_list):
            raise ValueError(f"No valid categorized samples found in {samples_dir}")

        # Transform XML
        modified_xml = self._transform_drum_rack(xml_content, sample_list)

        # Save
        result = encode_adg(modified_xml, output)
        print(f"✓ Created categorized drum rack: {result}")

        return result

    def _get_all_samples(self, folder: Path, recursive: bool) -> List[Path]:
        """Get all audio samples from folder."""
        from .sample_utils import SUPPORTED_AUDIO_FORMATS

        pattern = '**/*' if recursive else '*'
        samples = []

        for ext in SUPPORTED_AUDIO_FORMATS:
            samples.extend(folder.glob(f"{pattern}{ext}"))
            samples.extend(folder.glob(f"{pattern}{ext.upper()}"))

        return samples

    def _flatten_categories(self, categorized: Dict[str, List[Path]]) -> List[Path]:
        """Flatten categorized samples to single list, prioritizing common categories."""
        priority_order = ['kick', 'snare', 'hat', 'clap', 'tom', 'cymbal', 'perc', 'shaker']

        flat = []

        # Add priority categories first
        for cat in priority_order:
            if cat in categorized:
                flat.extend(categorized[cat])

        # Add remaining categories
        for cat, samples in categorized.items():
            if cat not in priority_order and cat != 'uncategorized':
                flat.extend(samples)

        # Add uncategorized last
        if 'uncategorized' in categorized:
            flat.extend(categorized['uncategorized'])

        return flat

    def _get_note_layout(self, layout: str) -> Dict[str, int]:
        """Get MIDI note layout for categories."""
        layouts = {
            'standard': {
                'kick': 36,      # C1
                'snare': 40,     # E1
                'clap': 39,      # D#1
                'hat': 42,       # F#1
                'open_hat': 46,  # A#1
                'tom': 48,       # C2
                'cymbal': 49,    # C#2
                'perc': 56,      # G#2
                'shaker': 60,    # C3
            },
            '808': {
                'kick': 36,      # C1
                'snare': 38,     # D1
                'clap': 39,      # D#1
                'hat': 42,       # F#1
                'open_hat': 46,  # A#1
                'tom': 45,       # A1
                'cymbal': 51,    # D#2
                'perc': 60,      # C3
            },
            'percussion': {
                'perc': 36,
                'shaker': 44,
                'tom': 48,
                'cymbal': 52,
            }
        }
        return layouts.get(layout, layouts['standard'])

    def _transform_drum_rack(self, xml_content: str, sample_paths: List[str]) -> str:
        """
        Transform drum rack XML by replacing sample paths.

        Args:
            xml_content: Original XML from template
            sample_paths: List of sample paths (can contain None for empty pads)

        Returns:
            Modified XML string
        """
        try:
            root = ET.fromstring(xml_content)

            # Find all DrumBranchPreset elements (individual drum pads)
            drum_pads = root.findall(".//DrumBranchPreset")

            # Sort by MIDI note DESCENDING (Ableton has highest note at pad 0)
            drum_pads.sort(
                key=lambda pad: int(pad.find(".//ZoneSettings/ReceivingNote").get("Value")),
                reverse=True
            )

            replaced_count = 0

            # Process each sample
            for sample_index, sample_path in enumerate(sample_paths):
                if sample_index >= len(drum_pads):
                    break

                if not sample_path:
                    continue

                pad = drum_pads[sample_index]

                # Find DrumCell devices within this pad
                drum_cells = pad.findall(".//DrumCell")

                for cell in drum_cells:
                    # Find sample reference
                    sample_refs = cell.findall(".//UserSample/Value/SampleRef/FileRef")

                    for file_ref in sample_refs:
                        # Update absolute path
                        path_elem = file_ref.find("Path")
                        if path_elem is not None:
                            path_elem.set('Value', sample_path)

                            # Update relative path
                            rel_path_elem = file_ref.find("RelativePath")
                            if rel_path_elem is not None:
                                # Keep last 3 path components
                                path_parts = sample_path.split('/')
                                new_rel_path = "../../" + '/'.join(path_parts[-3:])
                                rel_path_elem.set('Value', new_rel_path)

                            replaced_count += 1

            print(f"  Replaced {replaced_count} sample reference(s)")

            # Convert back to string
            return ET.tostring(root, encoding='unicode', xml_declaration=True)

        except Exception as e:
            raise Exception(f"Error transforming drum rack XML: {e}") from e
