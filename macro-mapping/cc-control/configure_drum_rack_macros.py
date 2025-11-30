#!/usr/bin/env python3
"""
Configure drum rack macros: rename, set visibility, values, and map nested rack macros

This script:
1. Renames top-level macros
2. Sets macro visibility
3. Sets macro values and defaults
4. Maps all Instrument Rack Macro 7s to parent Drum Rack Macro 4

Usage:
    python configure_drum_rack_macros.py input.adg output.adg
    python configure_drum_rack_macros.py input.adg --in-place
"""

import gzip
import re
import argparse
from pathlib import Path
from typing import Dict, Optional


def configure_drum_rack_macros(
    input_path: Path,
    output_path: Path,
    macro_names: Optional[Dict[int, str]] = None,
    macros_visible: bool = True,
    macro_values: Optional[Dict[int, float]] = None,
    macro_defaults: Optional[Dict[int, float]] = None,
    map_instrument_rack_macro: bool = True,
    dry_run: bool = False
):
    """
    Configure drum rack macros comprehensively

    Args:
        input_path: Path to input .adg file
        output_path: Path to output .adg file
        macro_names: Dict of macro index -> new name (e.g., {0: 'FX1', 1: 'FX2'})
        macros_visible: Whether to show macro controls
        macro_values: Dict of macro index -> value (e.g., {3: 64})
        macro_defaults: Dict of macro index -> default value (e.g., {3: -1})
        map_instrument_rack_macro: Map all Instrument Rack Macro 7s to parent Macro 4
        dry_run: If True, show changes without writing
    """

    # Default values
    if macro_names is None:
        macro_names = {0: 'FX1', 1: 'FX2'}
    if macro_values is None:
        macro_values = {3: 64}
    if macro_defaults is None:
        macro_defaults = {3: -1}

    # Read and decode
    print(f"Reading: {input_path}")
    with gzip.open(input_path, 'rb') as f:
        xml_content = f.read().decode('utf-8')

    original_xml = xml_content
    changes_made = []

    # 1. Rename macros
    if macro_names:
        print(f"\n=== RENAMING MACROS ===")
        for idx, new_name in macro_names.items():
            pattern = f'<MacroDisplayNames\\.{idx} Value="([^"]+)" />'
            match = re.search(pattern, xml_content)
            if match:
                old_name = match.group(1)
                replacement = f'<MacroDisplayNames.{idx} Value="{new_name}" />'
                xml_content = re.sub(pattern, replacement, xml_content, count=1)
                print(f"  Macro {idx+1}: '{old_name}' → '{new_name}'")
                changes_made.append(f"Renamed Macro {idx+1}")

    # 2. Set macro visibility
    print(f"\n=== MACRO VISIBILITY ===")
    visibility_pattern = r'<AreMacroControlsVisible Value="([^"]+)" />'
    match = re.search(visibility_pattern, xml_content)
    if match:
        old_visibility = match.group(1)
        new_visibility = 'true' if macros_visible else 'false'
        xml_content = re.sub(
            visibility_pattern,
            f'<AreMacroControlsVisible Value="{new_visibility}" />',
            xml_content,
            count=1
        )
        print(f"  {old_visibility} → {new_visibility}")
        if old_visibility != new_visibility:
            changes_made.append(f"Set macro visibility to {new_visibility}")

    # 3. Set macro values (top-level only - first occurrence)
    if macro_values:
        print(f"\n=== SETTING MACRO VALUES ===")
        for idx, value in macro_values.items():
            # Find the first (top-level) MacroControls.X
            pattern = f'(<MacroControls\\.{idx}>.*?)<Manual Value="([^"]+)" />'
            match = re.search(pattern, xml_content, re.DOTALL)
            if match:
                old_value = match.group(2)
                # Replace only the first occurrence (top-level)
                xml_content = re.sub(
                    pattern,
                    f'\\1<Manual Value="{value}" />',
                    xml_content,
                    count=1,
                    flags=re.DOTALL
                )
                print(f"  MacroControls.{idx}: {old_value} → {value}")
                changes_made.append(f"Set Macro {idx+1} value to {value}")

    # 4. Set macro defaults
    if macro_defaults:
        print(f"\n=== SETTING MACRO DEFAULTS ===")
        for idx, default in macro_defaults.items():
            pattern = f'<MacroDefaults\\.{idx} Value="([^"]+)" />'
            match = re.search(pattern, xml_content)
            if match:
                old_default = match.group(1)
                xml_content = re.sub(
                    pattern,
                    f'<MacroDefaults.{idx} Value="{default}" />',
                    xml_content,
                    count=1
                )
                print(f"  MacroDefaults.{idx}: {old_default} → {default}")
                changes_made.append(f"Set Macro {idx+1} default to {default}")

    # 5. Map Instrument Rack Macro 7 to parent Macro 4
    if map_instrument_rack_macro:
        print(f"\n=== MAPPING INSTRUMENT RACK MACROS ===")

        # Find all InstrumentGroupDevice MacroControls.6 sections that DON'T have KeyMidi
        pattern = r'(<InstrumentGroupDevice Id="0">.*?<MacroControls\.6>\s*<LomId Value="0" />\s*)(<Manual Value="[^"]*" />)'

        # Count potential matches
        matches = list(re.finditer(pattern, xml_content, re.DOTALL))
        instrument_racks_found = len(matches)

        print(f"  Found {instrument_racks_found} InstrumentGroupDevice instances")

        # The KeyMidi block to insert
        keymidi_block = """<KeyMidi>
										<PersistentKeyString Value="" />
										<IsNote Value="false" />
										<Channel Value="16" />
										<NoteOrController Value="3" />
										<LowerRangeNote Value="-1" />
										<UpperRangeNote Value="-1" />
										<ControllerMapMode Value="0" />
									</KeyMidi>
									"""

        def add_keymidi(match):
            """Add KeyMidi block before Manual value"""
            prefix = match.group(1)
            manual = match.group(2)
            return f'{prefix}{keymidi_block}{manual}'

        # Apply the replacement
        xml_content = re.sub(pattern, add_keymidi, xml_content, flags=re.DOTALL)

        # Verify
        keymidi_count = xml_content.count('<NoteOrController Value="3" />')
        print(f"  ✓ Added KeyMidi mappings: {keymidi_count}")
        print(f"  All Instrument Rack Macro 7s now map to parent Drum Rack Macro 4")
        changes_made.append(f"Mapped {keymidi_count} Instrument Rack Macro 7s to parent Macro 4")

    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Changes made: {len(changes_made)}")
    for change in changes_made:
        print(f"  • {change}")

    if dry_run:
        print("\n[DRY RUN] No changes written")
        return

    # Write output
    print(f"\nWriting: {output_path}")
    with gzip.open(output_path, 'wb') as f:
        f.write(xml_content.encode('utf-8'))

    print("✓ Complete!")


def main():
    parser = argparse.ArgumentParser(
        description='Configure drum rack macros: rename, visibility, values, and mappings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Apply default configuration (renames, visibility, values, mappings)
  python configure_drum_rack_macros.py input.adg output.adg

  # Update in-place
  python configure_drum_rack_macros.py input.adg --in-place

  # Dry run to preview changes
  python configure_drum_rack_macros.py input.adg output.adg --dry-run

Default configuration:
  - Rename Macro 1 → 'FX1', Macro 2 → 'FX2'
  - Set macros visible
  - Set Macro 4 value to 64, default to -1
  - Map all Instrument Rack Macro 7s to parent Drum Rack Macro 4
        """
    )

    parser.add_argument('input', type=Path, help='Input .adg file')
    parser.add_argument('output', type=Path, nargs='?', help='Output .adg file (required unless --in-place)')
    parser.add_argument('--in-place', action='store_true', help='Modify the input file directly')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without writing')
    parser.add_argument('--no-rename', action='store_true', help='Skip renaming macros')
    parser.add_argument('--no-mapping', action='store_true', help='Skip adding Instrument Rack mappings')

    args = parser.parse_args()

    # Validate arguments
    if not args.in_place and not args.output:
        parser.error("Either provide an output file or use --in-place")

    if not args.input.exists():
        parser.error(f"Input file not found: {args.input}")

    if not args.input.suffix.lower() == '.adg':
        print(f"⚠️  Warning: Input file doesn't have .adg extension: {args.input}")

    # Determine output path
    output_path = args.input if args.in_place else args.output

    # Configure options
    macro_names = None if args.no_rename else {0: 'FX1', 1: 'FX2'}
    map_macros = not args.no_mapping

    # Run the configuration
    configure_drum_rack_macros(
        args.input,
        output_path,
        macro_names=macro_names,
        macros_visible=True,
        macro_values={3: 64},
        macro_defaults={3: -1},
        map_instrument_rack_macro=map_macros,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    main()
