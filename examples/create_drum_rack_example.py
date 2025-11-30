#!/usr/bin/env python3
"""
Example: Creating Drum Racks with Ableton Device Creator V3

This example demonstrates the new library-first API for creating drum racks.
"""

from pathlib import Path
from ableton_device_creator.drum_racks import DrumRackCreator

def example_1_simple_folder():
    """
    Example 1: Create drum rack from a folder of samples.
    Fills pads sequentially with all found samples.
    """
    print("Example 1: Simple folder processing")
    print("=" * 60)

    creator = DrumRackCreator(
        template="templates/drum-racks/Drum Rack Template.adg"
    )

    output = creator.from_folder(
        samples_dir="test_samples",
        output="output/simple_rack.adg",
        categorize=True,  # Sort by category (kicks first, then snares, etc.)
        recursive=True,
        max_samples=32
    )

    print(f"✓ Created: {output}\n")


def example_2_categorized_folders():
    """
    Example 2: Create drum rack from categorized folder structure.

    Expected structure:
    - my_samples/Kick/*.wav
    - my_samples/Snare/*.wav
    - my_samples/Hat/*.wav
    """
    print("Example 2: Categorized folder structure")
    print("=" * 60)

    # First, create test folder structure
    test_dir = Path("test_samples_categorized")
    test_dir.mkdir(exist_ok=True)

    # Create category subfolders
    for category in ['Kick', 'Snare', 'Hat', 'Clap']:
        cat_dir = test_dir / category
        cat_dir.mkdir(exist_ok=True)
        # Create dummy samples
        for i in range(1, 4):
            (cat_dir / f"{category}_{i:02d}.wav").touch()

    creator = DrumRackCreator(
        template="templates/drum-racks/Drum Rack Template.adg"
    )

    output = creator.from_categorized_folders(
        samples_dir=test_dir,
        output="output/categorized_rack.adg",
        layout="standard"  # or "808" or "percussion"
    )

    print(f"✓ Created: {output}\n")


def example_3_sample_categorization():
    """
    Example 3: Use sample_utils for categorization analysis.
    """
    print("Example 3: Sample categorization utilities")
    print("=" * 60)

    from ableton_device_creator.drum_racks import categorize_samples

    samples = categorize_samples(Path("test_samples"))

    print("\nCategorization results:")
    for category, files in samples.items():
        if files:
            print(f"  {category}: {len(files)} samples")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Ableton Device Creator V3 - Examples")
    print("=" * 60 + "\n")

    # Run examples
    example_1_simple_folder()
    example_2_categorized_folders()
    example_3_sample_categorization()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print("\nNext step: Open the generated .adg files in Ableton Live")
    print("to verify they load correctly.\n")
