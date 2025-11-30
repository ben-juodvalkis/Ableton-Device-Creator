#!/usr/bin/env python3
"""
Example: Using the macro_mapping module

Demonstrates the new V3 API for macro mapping operations.
"""

from pathlib import Path
from ableton_device_creator.macro_mapping import (
    CCControlMapper,
    DrumPadColorMapper,
    TransposeMapper
)


def example_cc_control():
    """Example: Add CC Control mappings to drum rack."""
    print("\n" + "="*70)
    print("EXAMPLE 1: CC Control Mapping")
    print("="*70)

    # Initialize mapper with drum rack
    mapper = CCControlMapper("templates/drum-racks/Drum Rack Template.adg")

    # Add CC mappings (method chaining)
    mapper.add_cc_mappings({
        3: (119, 15),  # Custom E → CC 119 → Macro 16
        4: (120, 14),  # Custom F → CC 120 → Macro 15
        5: (121, 13),  # Custom G → CC 121 → Macro 14
    }).save("output/drum_rack_with_cc.adg")

    print("✓ Created drum rack with CC control mappings")


def example_color_coding():
    """Example: Apply color coding to drum pads."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Drum Pad Coloring")
    print("="*70)

    # Initialize colorizer
    colorizer = DrumPadColorMapper("output/real_samples_rack.adg")

    # Apply colors (method chaining)
    colorizer.apply_colors().save("output/colored_drum_rack.adg")

    # Get statistics
    stats = colorizer.get_stats()
    print(f"✓ Colored {stats['colored']} pads, skipped {stats['skipped']}")
    print(f"\nColor distribution:")
    for category, count in sorted(stats['by_category'].items()):
        print(f"  {category:15s}: {count:3d} pads")


def example_transpose_mapping():
    """Example: Map transpose to macro."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Transpose-to-Macro Mapping")
    print("="*70)

    # Initialize mapper
    mapper = TransposeMapper("templates/drum-racks/Drum Rack Template.adg")

    # Add transpose mapping to Macro 16
    mapper.add_transpose_mapping(
        macro_index=15,    # Macro 16 (0-indexed)
        macro_value=63.5   # Center position (0 transpose)
    ).save("output/drum_rack_with_transpose.adg")

    # Get statistics
    stats = mapper.get_stats()
    print(f"✓ Found {stats['transpose_params_found']} transpose parameters")
    print(f"✓ Added {stats['mappings_added']} mappings")
    print(f"✓ Updated {stats['macros_updated']} macros")


def example_combined_workflow():
    """Example: Combine multiple operations."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Combined Workflow")
    print("="*70)

    rack_path = "output/real_samples_rack.adg"
    output_path = "output/fully_configured_rack.adg"

    # Step 1: Add CC Control
    print("Step 1: Adding CC control...")
    cc_mapper = CCControlMapper(rack_path)
    cc_mapper.add_cc_mappings({
        0: (102, 0),   # Custom B → CC 102 → Macro 1
        1: (103, 1),   # Custom C → CC 103 → Macro 2
        3: (119, 15),  # Custom E → CC 119 → Macro 16
    })
    temp_path = "output/temp_with_cc.adg"
    cc_mapper.save(temp_path)

    # Step 2: Apply colors
    print("Step 2: Applying colors...")
    colorizer = DrumPadColorMapper(temp_path)
    colorizer.apply_colors()
    temp_path_2 = "output/temp_with_colors.adg"
    colorizer.save(temp_path_2)

    # Step 3: Add transpose mapping
    print("Step 3: Adding transpose mapping...")
    transpose_mapper = TransposeMapper(temp_path_2)
    transpose_mapper.add_transpose_mapping(macro_index=15)
    transpose_mapper.save(output_path)

    # Clean up temp files
    Path(temp_path).unlink(missing_ok=True)
    Path(temp_path_2).unlink(missing_ok=True)

    print(f"\n✓ Created fully configured rack: {output_path}")


if __name__ == '__main__':
    # Create output directory
    Path("output").mkdir(exist_ok=True)

    print("\n" + "="*70)
    print("ABLETON DEVICE CREATOR V3 - MACRO MAPPING EXAMPLES")
    print("="*70)

    # Run examples
    try:
        example_cc_control()
    except FileNotFoundError as e:
        print(f"  ⊘ Skipped: {e}")

    try:
        example_color_coding()
    except FileNotFoundError as e:
        print(f"  ⊘ Skipped: {e}")

    try:
        example_transpose_mapping()
    except FileNotFoundError as e:
        print(f"  ⊘ Skipped: {e}")

    try:
        example_combined_workflow()
    except FileNotFoundError as e:
        print(f"  ⊘ Skipped: {e}")

    print("\n" + "="*70)
    print("EXAMPLES COMPLETE")
    print("="*70 + "\n")
