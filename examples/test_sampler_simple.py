#!/usr/bin/env python3
"""
Simple Sampler Test - Creates devices from any available samples
"""

from pathlib import Path
import sys

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.sampler import SamplerCreator, SimplerCreator


def find_sample_folder():
    """Find a folder with audio samples."""
    # Try common locations
    locations = [
        Path.home() / "Music/Native Instruments",
        Path("/Library/Application Support/Native Instruments"),
        Path.home() / "Documents/Ableton/User Library/Samples",
        Path.home() / "Music",
    ]

    for base in locations:
        if not base.exists():
            continue

        # Find first folder with WAV files
        for folder in base.rglob("*"):
            if folder.is_dir():
                wav_files = list(folder.glob("*.wav"))[:10]
                if len(wav_files) >= 5:
                    return folder, wav_files

    return None, []


def main():
    print("Testing Sampler Creation")
    print("=" * 60)

    # Find samples
    sample_folder, samples = find_sample_folder()

    if not samples:
        print("❌ No sample folders found with at least 5 WAV files")
        print("\nPlease ensure you have audio samples in one of these locations:")
        print("  - ~/Music/Native Instruments/")
        print("  - ~/Documents/Ableton/User Library/Samples/")
        print("  - ~/Music/")
        return

    print(f"✓ Found samples in: {sample_folder}")
    print(f"  Sample count: {len(samples)}")
    print(f"  First sample: {samples[0].name}")
    print()

    # Test 1: Create chromatic sampler
    print("Test 1: Creating Chromatic Sampler")
    print("-" * 60)

    template = Path(__file__).parent.parent / "templates/sampler-rack.adg"
    if not template.exists():
        print(f"❌ Template not found: {template}")
        return

    creator = SamplerCreator(template=template)
    output = Path(__file__).parent.parent / "output/test_chromatic_sampler.adg"

    try:
        result = creator.from_samples_list(
            samples=samples[:10], output=output, layout="chromatic"
        )
        print(f"✓ Created: {result}")
        print(f"  Mapped {min(10, len(samples))} samples chromatically")
        print(f"  File size: {result.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return

    print()

    # Test 2: Create Simpler devices
    print("Test 2: Creating Simpler Devices")
    print("-" * 60)

    template_simpler = Path(__file__).parent.parent / "templates/simpler-template.adv"
    if not template_simpler.exists():
        print(f"❌ Template not found: {template_simpler}")
        return

    creator_simpler = SimplerCreator(template=template_simpler)
    output_folder = Path(__file__).parent.parent / "output/test_simplers"

    try:
        # Create from first 3 samples
        created = []
        for i, sample in enumerate(samples[:3]):
            output_adv = output_folder / f"{sample.stem}.adv"
            result = creator_simpler.from_sample(sample, output_adv)
            created.append(result)

        print(f"✓ Created {len(created)} Simpler devices:")
        for adv_file in created:
            print(f"    - {adv_file.name} ({adv_file.stat().st_size / 1024:.1f} KB)")

        # Test get_sample_info
        info = creator_simpler.get_sample_info(created[0])
        print(f"\n  Info for {created[0].name}:")
        print(f"    - Name: {info.get('name', 'N/A')}")
        print(f"    - Sample Rate: {info.get('sample_rate', 'N/A')} Hz")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("=" * 60)
    print("✓ All tests completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Open output/test_chromatic_sampler.adg in Ableton Live")
    print("2. Open output/test_simplers/*.adv in Ableton Live")
    print("3. Test triggering samples with MIDI keyboard")


if __name__ == "__main__":
    main()
