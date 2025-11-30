#!/usr/bin/env python3
"""
Apply macro mappings to Ableton drum rack (.adg) files
Maps the first 8 plugin parameters (101-108) to macros 1-8
"""

import gzip
import argparse
import re
from pathlib import Path

def extract_adg_to_xml(adg_path):
    """Extract .adg file to XML string"""
    with gzip.open(adg_path, 'rb') as f:
        return f.read().decode('utf-8')

def compress_xml_to_adg(xml_content, adg_path):
    """Compress XML string to .adg file"""
    with gzip.open(adg_path, 'wb', compresslevel=6) as f:
        f.write(xml_content.encode('utf-8'))

def add_parameter_visibility(xml_content, num_params=8, start_lom_id=76445):
    """
    Add PluginParameterSettings to make parameters visible in Ableton

    Adds parameter settings for parameters 101-108 if they don't exist
    """

    # Check if ParameterSettings already exists with content
    if '<PluginParameterSettings Id="0">' in xml_content:
        return xml_content  # Parameters already visible

    # Generate the parameter settings
    param_settings = []
    for i in range(num_params):
        param_id = 101 + i
        lom_id = start_lom_id + i
        index = i * 2

        param_xml = f'''			<PluginParameterSettings Id="{i}">
				<Index Value="{index}" />
				<VisualIndex Value="{i}" />
				<ParameterId Value="{param_id}" />
				<Type Value="PluginFloatParameter" />
				<MacroControlIndex Value="-1" />
				<MidiControllerRange />
				<LomId Value="{lom_id}" />
			</PluginParameterSettings>'''
        param_settings.append(param_xml)

    # Join all parameter settings
    full_param_settings = '\n'.join(param_settings)

    # Replace empty ParameterSettings with the full version
    xml_content = xml_content.replace(
        '<ParameterSettings />',
        f'<ParameterSettings>\n{full_param_settings}\n\t\t\t\t\t</ParameterSettings>'
    )

    return xml_content

def apply_macro_mappings(xml_content, num_macros=8):
    """
    Apply macro mappings to the first N plugin parameters (101-108)

    Changes:
    1. Ensures parameters are visible (adds ParameterSettings if needed)
    2. Sets MacroDefaults.0-7 to "-1"
    3. Makes macro controls visible
    4. Maps plugin parameters 101-108 to macros 0-7
    5. Adds MidiControllerRange for each mapped parameter
    """

    # Step 0: Ensure parameters are visible
    xml_content = add_parameter_visibility(xml_content, num_macros)

    # Step 1: Change MacroDefaults for first 8 macros from "0" to "-1"
    for i in range(num_macros):
        pattern = f'<MacroDefaults.{i} Value="0" />'
        replacement = f'<MacroDefaults.{i} Value="-1" />'
        xml_content = xml_content.replace(pattern, replacement)

    # Step 2: Make macro controls visible
    xml_content = xml_content.replace(
        '<AreMacroControlsVisible Value="false" />',
        '<AreMacroControlsVisible Value="true" />'
    )

    # Step 3: Map plugin parameters to macros
    # Pattern to find: MacroControlIndex with value -1, followed by empty MidiControllerRange
    for i in range(num_macros):
        param_id = 101 + i  # Parameters 101-108

        # Find the PluginParameterSettings block for this parameter
        param_pattern = (
            f'(<ParameterId Value="{param_id}" />\\s*'
            f'<Type Value="PluginFloatParameter" />\\s*)'
            f'<MacroControlIndex Value="-1" />\\s*'
            f'<MidiControllerRange />'
        )

        param_replacement = (
            f'\\1'
            f'<MacroControlIndex Value="{i}" />\n'
            f'\t\t\t\t\t\t<MidiControllerRange>\n'
            f'\t\t\t\t\t\t\t<MidiControllerRange Id="0">\n'
            f'\t\t\t\t\t\t\t\t<Min Value="0" />\n'
            f'\t\t\t\t\t\t\t\t<Max Value="1" />\n'
            f'\t\t\t\t\t\t\t</MidiControllerRange>\n'
            f'\t\t\t\t\t\t</MidiControllerRange>'
        )

        xml_content = re.sub(param_pattern, param_replacement, xml_content, flags=re.DOTALL)

    return xml_content

def main():
    parser = argparse.ArgumentParser(
        description='Apply macro mappings to Ableton drum rack (.adg) files',
        epilog='Example: python apply_macro_mappings.py input.adg output.adg'
    )
    parser.add_argument('input_file', type=str, help='Input .adg file')
    parser.add_argument('output_file', type=str, help='Output .adg file')
    parser.add_argument('--macros', type=int, default=8, help='Number of macros to map (default: 8)')
    parser.add_argument('--xml-output', type=str, help='Optional: Save intermediate XML for debugging')

    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    if not input_path.exists():
        print(f"❌ Error: Input file {input_path} does not exist")
        return

    if input_path.suffix.lower() != '.adg':
        print(f"❌ Error: Input file must be .adg")
        return

    print(f"🔧 Applying macro mappings to {input_path.name}")
    print(f"   Mapping first {args.macros} parameters to macros...")

    # Extract ADG to XML
    xml_content = extract_adg_to_xml(input_path)

    # Apply macro mappings
    modified_xml = apply_macro_mappings(xml_content, args.macros)

    # Save intermediate XML if requested
    if args.xml_output:
        with open(args.xml_output, 'w') as f:
            f.write(modified_xml)
        print(f"💾 Saved intermediate XML to {args.xml_output}")

    # Compress back to ADG
    compress_xml_to_adg(modified_xml, output_path)

    print(f"✅ Successfully created {output_path.name}")
    print(f"   - Plugin parameters 101-{100 + args.macros} made visible")
    print(f"   - Parameters mapped to macros 1-{args.macros}")
    print(f"   - Macro controls visibility enabled")

if __name__ == "__main__":
    main()
