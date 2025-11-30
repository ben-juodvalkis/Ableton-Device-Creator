#!/usr/bin/env python3
"""
CLI Demo - Demonstrates CLI functionality without requiring Click installation.

This script shows how the CLI would work if Click were installed.
"""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.drum_racks import DrumRackCreator, DrumRackModifier
from ableton_device_creator.sampler import SamplerCreator, SimplerCreator
from ableton_device_creator.macro_mapping import DrumPadColorMapper
from ableton_device_creator.core import decode_adg, encode_adg


def demo_drum_rack_create():
    """Simulate: adc drum-rack create samples/"""
    print("=" * 70)
    print("DEMO: adc drum-rack create samples/")
    print("=" * 70)

    samples_dir = Path("/Library/Application Support/Native Instruments/Kontakt 5/presets/Effects/Convolution/11 Unsusual Reverbs/IR Samples")
    template = Path(__file__).parent.parent / "templates/input_rack.adg"
    output = Path(__file__).parent.parent / "output/cli_demo_rack.adg"

    if not samples_dir.exists():
        print(f"❌ Samples not found: {samples_dir}")
        return

    print(f"Creating drum rack from: {samples_dir}")
    print(f"Template: {template}")
    print(f"Output: {output}")

    try:
        creator = DrumRackCreator(template=template)
        result = creator.from_folder(
            samples_dir=samples_dir,
            output=output,
            categorize=False,  # Just fill pads sequentially
            recursive=False
        )

        print(f"✓ Created drum rack: {result}")
        print(f"  File size: {result.stat().st_size / 1024:.1f} KB")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")


def demo_drum_rack_color():
    """Simulate: adc drum-rack color output/cli_demo_rack.adg"""
    print("=" * 70)
    print("DEMO: adc drum-rack color output/cli_demo_rack.adg")
    print("=" * 70)

    device = Path(__file__).parent.parent / "output/cli_demo_rack.adg"

    if not device.exists():
        print(f"❌ Device not found: {device}")
        print("   Run demo_drum_rack_create() first")
        return

    print(f"Applying colors to: {device}")

    try:
        colorizer = DrumPadColorMapper(device)
        colorizer.apply_colors().save(device)

        print(f"✓ Applied colors: {device}")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")


def demo_sampler_create():
    """Simulate: adc sampler create samples/ --layout chromatic"""
    print("=" * 70)
    print("DEMO: adc sampler create samples/ --layout chromatic")
    print("=" * 70)

    samples_dir = Path("/Library/Application Support/Native Instruments/Kontakt 5/presets/Effects/Convolution/11 Unsusual Reverbs/IR Samples")
    template = Path(__file__).parent.parent / "templates/sampler-rack.adg"
    output = Path(__file__).parent.parent / "output/cli_demo_sampler.adg"

    if not samples_dir.exists():
        print(f"❌ Samples not found: {samples_dir}")
        return

    print(f"Creating sampler from: {samples_dir}")
    print(f"Layout: chromatic")
    print(f"Max samples: 10")

    try:
        creator = SamplerCreator(template=template)
        result = creator.from_folder(
            samples_dir=samples_dir,
            output=output,
            layout="chromatic",
            samples_per_instrument=10
        )

        print(f"✓ Created sampler: {result}")
        print(f"  File size: {result.stat().st_size / 1024:.1f} KB")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")


def demo_util_info():
    """Simulate: adc util info output/cli_demo_rack.adg"""
    print("=" * 70)
    print("DEMO: adc util info output/cli_demo_rack.adg")
    print("=" * 70)

    file_path = Path(__file__).parent.parent / "output/cli_demo_rack.adg"

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    print(f"File: {file_path}")

    try:
        xml_content = decode_adg(file_path)

        # Basic stats
        print(f"  Compressed size: {file_path.stat().st_size / 1024:.1f} KB")
        print(f"  Uncompressed size: {len(xml_content) / 1024:.1f} KB")
        print(f"  Compression ratio: {file_path.stat().st_size / len(xml_content):.1%}")

        # Detect device type
        if isinstance(xml_content, bytes):
            xml_str = xml_content.decode('utf-8')
        else:
            xml_str = xml_content
        if 'DrumGroupDevice' in xml_str:
            print(f"  Type: Drum Rack")
        elif 'MultiSampler' in xml_str:
            print(f"  Type: Multi-Sampler / Simpler")
        else:
            print(f"  Type: Unknown")

        # Count samples
        sample_count = xml_str.count('<SampleRef>')
        if sample_count > 0:
            print(f"  Sample references: {sample_count}")

        print()

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all CLI demos."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "Ableton Device Creator - CLI Demo" + " " * 20 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print("This demonstrates what the CLI would do if Click were installed.")
    print("To use the actual CLI: pip install click>=8.0.0")
    print()

    # Run demos
    demo_drum_rack_create()
    demo_drum_rack_color()
    demo_sampler_create()
    demo_util_info()

    print("=" * 70)
    print("CLI Demo Complete!")
    print("=" * 70)
    print()
    print("To use the real CLI with Click installed:")
    print("  adc drum-rack create samples/")
    print("  adc sampler create samples/ --layout chromatic")
    print("  adc util info output/MyRack.adg")
    print()
    print("See docs/CLI_GUIDE.md for full documentation")


if __name__ == "__main__":
    main()
