#!/usr/bin/env python3
"""
Sampler Creation Examples

This script demonstrates how to create Multi-Sampler instruments and Simpler devices
using the ableton_device_creator library.
"""

from pathlib import Path
import sys

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.sampler import SamplerCreator, SimplerCreator


def example_chromatic_sampler():
    """Create a chromatic sampler instrument."""
    print("=" * 60)
    print("Example 1: Creating Chromatic Sampler")
    print("=" * 60)

    # Use Native Instruments library samples (adjust path as needed)
    samples_dir = Path.home() / "Music/Native Instruments/Sierra Grove/Samples/Kicks"
    template = Path(__file__).parent.parent / "templates/sampler-rack.adg"

    if not samples_dir.exists():
        print(f"Samples directory not found: {samples_dir}")
        print("Using test samples instead...")
        samples_dir = Path(__file__).parent.parent / "test_samples"

    if not template.exists():
        print(f"Template not found: {template}")
        return

    # Create sampler
    creator = SamplerCreator(template=template)

    output = Path(__file__).parent.parent / "output/chromatic_kicks.adg"
    result = creator.from_folder(
        samples_dir=samples_dir,
        output=output,
        layout="chromatic",
        samples_per_instrument=32,
    )

    print(f"✓ Created chromatic sampler: {result}")
    print(f"  Maps up to 32 samples chromatically from C-2 upward")
    print()


def example_drum_sampler():
    """Create a drum-style sampler (8 kicks, 8 snares, etc.)."""
    print("=" * 60)
    print("Example 2: Creating Drum-Style Sampler")
    print("=" * 60)

    samples_dir = Path.home() / "Music/Native Instruments/Sierra Grove/Samples/Kicks"
    template = Path(__file__).parent.parent / "templates/sampler-rack.adg"

    if not samples_dir.exists():
        print(f"Samples directory not found: {samples_dir}")
        return

    if not template.exists():
        print(f"Template not found: {template}")
        return

    # Create drum-style sampler
    creator = SamplerCreator(template=template)

    output = Path(__file__).parent.parent / "output/drum_kicks.adg"
    result = creator.from_folder(
        samples_dir=samples_dir, output=output, layout="drum", samples_per_instrument=32
    )

    print(f"✓ Created drum-style sampler: {result}")
    print(f"  Layout:")
    print(f"    - Kicks: C-2 to G-2 (notes 0-7)")
    print(f"    - Snares: G#-2 to D#-1 (notes 8-15)")
    print(f"    - Hats: E-1 to B-1 (notes 16-23)")
    print(f"    - Perc: C0 to G0 (notes 24-31)")
    print()


def example_percussion_sampler():
    """Create a percussion sampler (starts at C1)."""
    print("=" * 60)
    print("Example 3: Creating Percussion Sampler")
    print("=" * 60)

    samples_dir = Path.home() / "Music/Native Instruments/Sierra Grove/Samples/Perc"
    template = Path(__file__).parent.parent / "templates/sampler-rack.adg"

    if not samples_dir.exists():
        print(f"Samples directory not found: {samples_dir}")
        return

    if not template.exists():
        print(f"Template not found: {template}")
        return

    # Create percussion sampler
    creator = SamplerCreator(template=template)

    output = Path(__file__).parent.parent / "output/percussion.adg"
    result = creator.from_folder(
        samples_dir=samples_dir, output=output, layout="percussion"
    )

    print(f"✓ Created percussion sampler: {result}")
    print(f"  Maps samples chromatically starting from C1 (note 36)")
    print()


def example_simpler_batch():
    """Create individual Simpler devices for each sample."""
    print("=" * 60)
    print("Example 4: Creating Simpler Devices (Batch)")
    print("=" * 60)

    samples_dir = Path.home() / "Music/Native Instruments/Sierra Grove/Samples/Kicks"
    template = Path(__file__).parent.parent / "templates/simpler-template.adv"

    if not samples_dir.exists():
        print(f"Samples directory not found: {samples_dir}")
        return

    if not template.exists():
        print(f"Template not found: {template}")
        return

    # Create Simpler devices
    creator = SimplerCreator(template=template)

    output_folder = Path(__file__).parent.parent / "output/kick_simplers"
    created = creator.from_folder(samples_dir=samples_dir, output_folder=output_folder)

    print(f"✓ Created {len(created)} Simpler devices in: {output_folder}")
    print(f"  First few:")
    for adv_file in created[:5]:
        print(f"    - {adv_file.name}")
    if len(created) > 5:
        print(f"    ... and {len(created) - 5} more")
    print()


def example_simpler_single():
    """Create a single Simpler device."""
    print("=" * 60)
    print("Example 5: Creating Single Simpler Device")
    print("=" * 60)

    # Find a sample
    samples_dir = Path.home() / "Music/Native Instruments/Sierra Grove/Samples/Kicks"
    template = Path(__file__).parent.parent / "templates/simpler-template.adv"

    if not samples_dir.exists():
        print(f"Samples directory not found: {samples_dir}")
        return

    if not template.exists():
        print(f"Template not found: {template}")
        return

    # Get first sample
    samples = list(samples_dir.glob("*.wav"))
    if not samples:
        print("No samples found!")
        return

    sample = samples[0]

    # Create Simpler
    creator = SimplerCreator(template=template)

    output = Path(__file__).parent.parent / f"output/{sample.stem}.adv"
    result = creator.from_sample(sample_path=sample, output=output)

    print(f"✓ Created Simpler: {result}")
    print(f"  Sample: {sample.name}")

    # Get info about the created device
    info = creator.get_sample_info(result)
    print(f"  Info:")
    print(f"    - Name: {info.get('name', 'N/A')}")
    print(f"    - Path: {info.get('sample_path', 'N/A')}")
    print(f"    - Sample Rate: {info.get('sample_rate', 'N/A')} Hz")
    print()


def example_sampler_from_list():
    """Create sampler from explicit list of samples."""
    print("=" * 60)
    print("Example 6: Creating Sampler from Sample List")
    print("=" * 60)

    samples_dir = Path.home() / "Music/Native Instruments/Sierra Grove/Samples/Kicks"
    template = Path(__file__).parent.parent / "templates/sampler-rack.adg"

    if not samples_dir.exists():
        print(f"Samples directory not found: {samples_dir}")
        return

    if not template.exists():
        print(f"Template not found: {template}")
        return

    # Get specific samples
    all_samples = sorted(samples_dir.glob("*.wav"))[:10]  # First 10

    if not all_samples:
        print("No samples found!")
        return

    # Create sampler from list
    creator = SamplerCreator(template=template)

    output = Path(__file__).parent.parent / "output/selected_kicks.adg"
    result = creator.from_samples_list(
        samples=all_samples, output=output, layout="chromatic"
    )

    print(f"✓ Created sampler from {len(all_samples)} selected samples: {result}")
    print(f"  Samples:")
    for i, sample in enumerate(all_samples[:5]):
        print(f"    - Note {i}: {sample.name}")
    if len(all_samples) > 5:
        print(f"    ... and {len(all_samples) - 5} more")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Ableton Device Creator - Sampler Examples")
    print("=" * 60 + "\n")

    try:
        # Multi-Sampler examples
        example_chromatic_sampler()
        example_drum_sampler()
        example_percussion_sampler()
        example_sampler_from_list()

        # Simpler examples
        example_simpler_batch()
        example_simpler_single()

        print("=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        print()
        print("Check the output/ directory for created devices.")
        print("Open them in Ableton Live to test!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
