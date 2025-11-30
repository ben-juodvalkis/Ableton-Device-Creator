#!/usr/bin/env python3
"""
Replace Foreign Samples in Vox Phrases Drum Racks

Finds drum racks that contain samples from non-8dio sources and replaces
them with similar samples from the same 8dio folder as the majority samples.

For example, if a rack has 31 samples from:
    /Users/Shared/Music/Soundbanks/8dio/8Dio_Francesca/.../Soft/
And 1 sample from:
    /Users/Shared/Music/Soundbanks/Native Instruments/.../Kick/Kick 3onIt 1.wav

This script will replace the NI kick with a suitable sample from the 8dio Soft folder.

Usage:
    python3 replace_foreign_samples.py <vox_phrases_dir> [--dry-run] [--output-dir DIR]

Examples:
    # Dry run (show what would change)
    python3 replace_foreign_samples.py "/path/to/Vox Phrases" --dry-run

    # Replace in place
    python3 replace_foreign_samples.py "/path/to/Vox Phrases"

    # Save to new directory
    python3 replace_foreign_samples.py "/path/to/Vox Phrases" --output-dir "/path/to/output"
"""

import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict, Counter
import random
import shutil

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.decoder import decode_adg
from utils.encoder import encode_adg


def categorize_sample_path(path: str) -> tuple[str, str]:
    """
    Categorize a sample path by source and return (source, subfolder).

    Returns:
        tuple: (source_name, subfolder_path)

    Examples:
        '/Users/.../8dio/8Dio_Francesca/.../Soft/sample.wav' -> ('8dio', '8Dio_Francesca/.../Soft')
        '/Users/.../Native Instruments/.../Kick.wav' -> ('Native Instruments', 'Expansions/.../Kick')
    """
    if not path:
        return ('empty', '')

    if '/8dio/' in path:
        # Extract subfolder within 8dio
        parts = path.split('/8dio/')
        if len(parts) > 1:
            # Get the folder structure after /8dio/
            subfolder = str(Path(parts[1]).parent)
            return ('8dio', subfolder)

    if '/Native Instruments/' in path:
        parts = path.split('/Native Instruments/')
        if len(parts) > 1:
            subfolder = str(Path(parts[1]).parent)
            return ('Native Instruments', subfolder)

    if '/Soundbanks/' in path:
        parts = path.split('/Soundbanks/')
        if len(parts) > 1:
            source = parts[1].split('/')[0]
            subfolder = str(Path(parts[1]).parent)
            return (source, subfolder)

    return ('other', str(Path(path).parent))


def get_primary_8dio_folder(sample_paths: list[str]) -> str:
    """
    Find the most common 8dio folder from a list of sample paths.

    Returns:
        The full path to the primary 8dio sample folder
    """
    folders = []

    for path in sample_paths:
        source, subfolder = categorize_sample_path(path)
        if source == '8dio':
            # Reconstruct full path to folder
            if '/8dio/' in path:
                folder_path = str(Path(path).parent)
                folders.append(folder_path)

    if not folders:
        return None

    # Return most common folder
    folder_counter = Counter(folders)
    return folder_counter.most_common(1)[0][0]


def find_replacement_sample(primary_folder: Path, foreign_path: str, used_samples: set) -> str:
    """
    Find a replacement sample from the primary folder.

    Strategy:
    - For kicks: look for samples with 'kick', 'bd', 'bass' in name (prefer lower pitch)
    - For claps/snares: look for samples with 'clap', 'snap', 'snare' in name
    - For hihats: look for samples with 'hat', 'hh', 'cymbal' in name
    - Otherwise: pick a random sample from the folder
    - Always picks unique samples (tracks used_samples to avoid duplicates)

    Args:
        primary_folder: Path to the 8dio folder to search
        foreign_path: Path to the foreign sample (for context)
        used_samples: Set of already-used sample paths to avoid duplicates

    Returns:
        Full path to replacement sample
    """
    if not primary_folder.exists():
        return None

    # Get all wav files in the folder
    wav_files = list(primary_folder.glob('*.wav')) + list(primary_folder.glob('*.aif'))

    if not wav_files:
        return None

    # Filter out already-used samples
    available_files = [f for f in wav_files if str(f) not in used_samples]

    if not available_files:
        # If all samples used, reset and use all again
        available_files = wav_files

    # Determine sample type from foreign path
    foreign_name = Path(foreign_path).stem.lower()

    # Define search patterns for different sample types
    if 'kick' in foreign_name or 'bd' in foreign_name or '3onit' in foreign_name:
        # Look for kick-like samples (lower pitched vocals)
        patterns = ['oo', 'oh', 'ah', 'uh', 'mm', 'hm', 'low', 'deep', 'bass']
    elif 'clap' in foreign_name or 'snap' in foreign_name:
        # Look for percussive/sharp vocals
        patterns = ['t', 'k', 'ch', 'sh', 'p', 'snap', 'pop', 'click']
    elif 'hat' in foreign_name or 'hh' in foreign_name or 'cymbal' in foreign_name:
        # Look for breathy/sibilant vocals
        patterns = ['s', 'sh', 'ch', 'f', 'h', 'breath', 'air', 'whisp']
    elif 'bell' in foreign_name or 'perc' in foreign_name:
        # Look for tonal/melodic vocals
        patterns = ['a', 'e', 'i', 'o', 'u', 'ah', 'eh', 'oh', 'sustain', 'tone']
    else:
        # Default: any sample
        patterns = []

    # Try to find matching samples
    if patterns:
        candidates = []
        for wav in available_files:
            name = wav.stem.lower()
            for pattern in patterns:
                if pattern in name:
                    candidates.append(wav)
                    break

        if candidates:
            # Sort and pick first available candidate
            candidates.sort(key=lambda x: x.stem)
            return str(candidates[0])

    # Fallback: return first available sample alphabetically
    available_files.sort(key=lambda x: x.stem)
    return str(available_files[0])


def replace_foreign_samples_in_rack(rack_xml: str, verbose: bool = False) -> tuple[str, dict]:
    """
    Replace foreign (non-8dio) samples with 8dio alternatives.

    Args:
        rack_xml: XML content of drum rack
        verbose: Print detailed info

    Returns:
        tuple: (modified_xml, stats_dict)
    """
    root = ET.fromstring(rack_xml)

    # Collect all sample paths
    all_paths = []
    file_ref_elements = []

    for file_ref in root.findall('.//SampleRef/FileRef'):
        path_elem = file_ref.find('Path')
        if path_elem is not None:
            path = path_elem.get('Value', '')
            if path:
                all_paths.append(path)
                file_ref_elements.append((file_ref, path))

    # Find primary 8dio folder
    primary_folder_path = get_primary_8dio_folder(all_paths)

    if not primary_folder_path:
        return (ET.tostring(root, encoding='unicode', xml_declaration=True), {
            'replaced': 0,
            'failed': 0,
            'reason': 'No 8dio samples found'
        })

    primary_folder = Path(primary_folder_path)

    # Track used samples to ensure uniqueness
    used_samples = set()

    # Replace foreign samples
    stats = {
        'replaced': 0,
        'failed': 0,
        'replacements': []
    }

    for file_ref, original_path in file_ref_elements:
        source, _ = categorize_sample_path(original_path)

        if source != '8dio':
            # This is a foreign sample - replace it
            replacement = find_replacement_sample(primary_folder, original_path, used_samples)

            if replacement:
                # Mark this sample as used
                used_samples.add(replacement)

                # Update Path element
                path_elem = file_ref.find('Path')
                if path_elem is not None:
                    path_elem.set('Value', replacement)

                # Update RelativePath element
                rel_path_elem = file_ref.find('RelativePath')
                if rel_path_elem is not None:
                    # Create relative path (../../last_3_components)
                    path_parts = replacement.split('/')
                    new_rel_path = '../../' + '/'.join(path_parts[-3:])
                    rel_path_elem.set('Value', new_rel_path)

                stats['replaced'] += 1
                stats['replacements'].append({
                    'original': original_path,
                    'replacement': replacement
                })

                if verbose:
                    print(f"    REPLACED:")
                    print(f"      From: {Path(original_path).name}")
                    print(f"      To:   {Path(replacement).name}")
            else:
                stats['failed'] += 1
                if verbose:
                    print(f"    FAILED to find replacement for: {Path(original_path).name}")

    return (ET.tostring(root, encoding='unicode', xml_declaration=True), stats)


def process_directory(vox_phrases_dir: Path, dry_run: bool = False, output_dir: Path = None, verbose: bool = True):
    """
    Process all ADG files in the Vox Phrases directory.

    Args:
        vox_phrases_dir: Path to Vox Phrases directory
        dry_run: If True, don't write files (just report)
        output_dir: Optional output directory (if None, modifies in place)
        verbose: Print detailed info
    """
    total_files = 0
    modified_files = 0
    total_replaced = 0
    total_failed = 0

    print("=" * 80)
    print("🔄 Replace Foreign Samples in Vox Phrases Drum Racks")
    print("=" * 80)
    print(f"Input:  {vox_phrases_dir}")
    if dry_run:
        print("Mode:   DRY RUN (no files will be modified)")
    elif output_dir:
        print(f"Output: {output_dir}")
    else:
        print("Mode:   IN PLACE (will modify original files)")
    print()

    for adg_file in sorted(vox_phrases_dir.rglob('*.adg')):
        total_files += 1

        # Decode
        rack_xml = decode_adg(adg_file)

        # Replace foreign samples
        modified_xml, stats = replace_foreign_samples_in_rack(rack_xml, verbose=verbose)

        if stats['replaced'] > 0:
            modified_files += 1
            total_replaced += stats['replaced']
            total_failed += stats['failed']

            rel_path = adg_file.relative_to(vox_phrases_dir)
            print(f"✓ {rel_path}")
            print(f"  Replaced: {stats['replaced']} samples")
            if stats['failed'] > 0:
                print(f"  Failed:   {stats['failed']} samples")

            if verbose and stats['replacements']:
                for repl in stats['replacements'][:3]:  # Show first 3
                    print(f"    {Path(repl['original']).name}")
                    print(f"      → {Path(repl['replacement']).name}")
                if len(stats['replacements']) > 3:
                    print(f"    ... and {len(stats['replacements']) - 3} more")
            print()

            # Write modified file
            if not dry_run:
                if output_dir:
                    # Create same subfolder structure in output dir
                    output_file = output_dir / rel_path
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                else:
                    # Overwrite original
                    output_file = adg_file

                encode_adg(modified_xml, output_file)

    # Summary
    print()
    print("=" * 80)
    print("✅ SUMMARY")
    print("=" * 80)
    print(f"Total files:     {total_files}")
    print(f"Modified files:  {modified_files}")
    print(f"Samples replaced: {total_replaced}")
    if total_failed > 0:
        print(f"Failed:          {total_failed}")

    if dry_run:
        print("\n⚠️  DRY RUN - No files were actually modified")
        print("   Run without --dry-run to apply changes")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Replace foreign samples in Vox Phrases drum racks with 8dio alternatives',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'vox_phrases_dir',
        type=str,
        help='Path to Vox Phrases directory'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would change without modifying files'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory (if not specified, modifies files in place)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce output verbosity'
    )

    args = parser.parse_args()

    vox_phrases_dir = Path(args.vox_phrases_dir)

    if not vox_phrases_dir.exists():
        print(f"Error: Directory not found: {vox_phrases_dir}")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None

    process_directory(
        vox_phrases_dir,
        dry_run=args.dry_run,
        output_dir=output_dir,
        verbose=not args.quiet
    )

    return 0


if __name__ == '__main__':
    sys.exit(main())
