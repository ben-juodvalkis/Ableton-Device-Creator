"""Sample file categorization and organization utilities."""

from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class SampleCategory:
    """Sample category definition."""
    name: str
    keywords: List[str]
    aliases: List[str]


# Standard drum sample categories
DRUM_CATEGORIES = {
    'kick': SampleCategory(
        name='kick',
        keywords=['kick', 'bd', 'bassdrum', 'bass drum', 'kck', 'bass_drum'],
        aliases=['kicks', 'kick_drum']
    ),
    'snare': SampleCategory(
        name='snare',
        keywords=['snare', 'sd', 'snr', 'snare_drum'],
        aliases=['snares']
    ),
    'hat': SampleCategory(
        name='hat',
        keywords=['hat', 'hh', 'hihat', 'hi-hat', 'hi hat', 'hi_hat', 'closedhat', 'closedhh'],
        aliases=['hats', 'hihat']
    ),
    'clap': SampleCategory(
        name='clap',
        keywords=['clap', 'cp', 'handclap', 'hand_clap'],
        aliases=['claps']
    ),
    'tom': SampleCategory(
        name='tom',
        keywords=['tom', 'tm', 'lowtom', 'midtom', 'hightom', 'low_tom', 'mid_tom', 'high_tom'],
        aliases=['toms']
    ),
    'cymbal': SampleCategory(
        name='cymbal',
        keywords=['cymbal', 'cym', 'crash', 'ride', 'splash'],
        aliases=['cymbals']
    ),
    'perc': SampleCategory(
        name='perc',
        keywords=['perc', 'percussion', 'shaker', 'conga', 'bongo', 'cowbell', 'tambourine', 'wood'],
        aliases=['percussion', 'percs']
    ),
    'shaker': SampleCategory(
        name='shaker',
        keywords=['shaker', 'shake', 'maracas'],
        aliases=['shakers']
    ),
    'open_hat': SampleCategory(
        name='open_hat',
        keywords=['openhh', 'open_hh', 'openhat', 'open_hat', 'open hat', 'oh'],
        aliases=['open_hats']
    ),
}

SUPPORTED_AUDIO_FORMATS = {'.wav', '.aif', '.aiff', '.flac', '.mp3'}


def categorize_samples(
    folder_path: Path,
    categories: Optional[Dict[str, SampleCategory]] = None,
    recursive: bool = True
) -> Dict[str, List[Path]]:
    """
    Categorize audio samples by type based on filename.

    Args:
        folder_path: Directory containing samples
        categories: Custom categories (uses DRUM_CATEGORIES if None)
        recursive: Search subdirectories

    Returns:
        Dictionary mapping category name to list of sample paths

    Example:
        >>> samples = categorize_samples(Path('/samples'))
        >>> samples['kick']
        [Path('/samples/Kick_01.wav'), Path('/samples/BD_heavy.wav')]
    """
    if categories is None:
        categories = DRUM_CATEGORIES

    folder_path = Path(folder_path)

    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    if not folder_path.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")

    # Initialize result dict
    result = {cat: [] for cat in categories.keys()}
    result['uncategorized'] = []

    # Find all audio files
    pattern = '**/*' if recursive else '*'
    audio_files = []

    for ext in SUPPORTED_AUDIO_FORMATS:
        audio_files.extend(folder_path.glob(f"{pattern}{ext}"))
        # Also try uppercase extensions
        audio_files.extend(folder_path.glob(f"{pattern}{ext.upper()}"))

    # Categorize each file
    for file_path in audio_files:
        filename_lower = file_path.stem.lower()
        categorized = False

        # Check against each category
        for cat_name, cat_info in categories.items():
            if any(keyword in filename_lower for keyword in cat_info.keywords):
                result[cat_name].append(file_path)
                categorized = True
                break

        if not categorized:
            result['uncategorized'].append(file_path)

    return result


def categorize_by_folder(
    folder_path: Path,
    categories: Optional[Dict[str, SampleCategory]] = None
) -> Dict[str, List[Path]]:
    """
    Categorize samples by their parent folder name.

    Useful for libraries organized like:
    - /Samples/Drums/Kick/*.wav
    - /Samples/Drums/Snare/*.wav

    Args:
        folder_path: Directory containing categorized subfolders
        categories: Custom categories (uses DRUM_CATEGORIES if None)

    Returns:
        Dictionary mapping category name to list of sample paths
    """
    if categories is None:
        categories = DRUM_CATEGORIES

    folder_path = Path(folder_path)
    result = {cat: [] for cat in categories.keys()}
    result['uncategorized'] = []

    # Look for subfolders that match category names
    for subfolder in folder_path.iterdir():
        if not subfolder.is_dir():
            continue

        folder_name_lower = subfolder.name.lower()
        categorized = False

        # Check if folder name matches any category
        for cat_name, cat_info in categories.items():
            # Check both keywords and aliases
            all_terms = cat_info.keywords + cat_info.aliases + [cat_name]
            if any(term in folder_name_lower for term in all_terms):
                # Get all audio files from this folder
                for ext in SUPPORTED_AUDIO_FORMATS:
                    result[cat_name].extend(subfolder.glob(f"*{ext}"))
                    result[cat_name].extend(subfolder.glob(f"*{ext.upper()}"))
                categorized = True
                break

        if not categorized:
            # Add to uncategorized
            for ext in SUPPORTED_AUDIO_FORMATS:
                result['uncategorized'].extend(subfolder.glob(f"*{ext}"))

    return result


def validate_samples(samples: List[Path]) -> List[Path]:
    """
    Validate sample files exist and are readable.

    Args:
        samples: List of sample file paths

    Returns:
        List of valid sample paths
    """
    valid = []

    for sample in samples:
        if not sample.exists():
            continue
        if not sample.is_file():
            continue
        if sample.suffix.lower() not in SUPPORTED_AUDIO_FORMATS:
            continue

        valid.append(sample)

    return valid


def detect_velocity_layers(samples: List[Path]) -> Dict[str, List[Path]]:
    """
    Detect velocity layers in sample filenames.

    Common patterns:
    - Kick_v1.wav, Kick_v2.wav, Kick_v3.wav
    - Snare_soft.wav, Snare_med.wav, Snare_hard.wav
    - HH_01.wav, HH_02.wav, HH_03.wav

    Args:
        samples: List of sample file paths

    Returns:
        Dict mapping velocity layer name to samples
    """
    layers: Dict[str, List[Path]] = {}

    for sample in samples:
        stem = sample.stem.lower()
        layer_name = "default"

        # Pattern 1: _v1, _v2, etc.
        if '_v' in stem:
            parts = stem.split('_v')
            if len(parts) > 1:
                layer = parts[1].split('_')[0]
                if layer.isdigit():
                    layer_name = f"velocity_{layer}"

        # Pattern 2: _soft, _med, _hard
        elif any(x in stem for x in ['soft', 'med', 'medium', 'hard', 'loud']):
            for keyword in ['soft', 'med', 'medium', 'hard', 'loud']:
                if keyword in stem:
                    layer_name = keyword
                    break

        # Pattern 3: _01, _02, _03 at the end
        elif stem[-3:].startswith('_') and stem[-2:].isdigit():
            layer = stem[-2:]
            layer_name = f"layer_{layer}"

        if layer_name not in layers:
            layers[layer_name] = []
        layers[layer_name].append(sample)

    return layers


def sort_samples_natural(samples: List[Path]) -> List[Path]:
    """
    Sort samples using natural sorting (handles numbers correctly).

    Example:
        kick_1.wav, kick_2.wav, kick_10.wav
        (not kick_1.wav, kick_10.wav, kick_2.wav)

    Args:
        samples: List of sample paths

    Returns:
        Sorted list of sample paths
    """
    import re

    def natural_key(path: Path) -> List:
        """Convert filename to list of strings and numbers for sorting."""
        parts = re.split(r'(\d+)', path.stem.lower())
        return [int(part) if part.isdigit() else part for part in parts]

    return sorted(samples, key=natural_key)
