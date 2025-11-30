#!/usr/bin/env python3
"""
Map Ableton drum rack macros with specific parameter values
Takes parameter values from Live API and maps them to macros with proper scaling
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

def map_macros_with_values(xml_content, param_values, num_macros=16):
    """
    Map plugin parameters to macros with specific values

    Args:
        xml_content: The drum rack XML content
        param_values: List of 16 parameter values (0.0-1.0 range)
        num_macros: Number of macros to map (default 16, max supported by Ableton is 8)

    Changes:
    1. Sets MacroControls.N Manual values to param_value * 127
    2. Sets MacroDefaults.0-15 to "-1"
    3. Makes macro controls visible
    4. Maps plugin parameters 101-116 to macros 0-15
    5. Adds MidiControllerRange for each mapped parameter
    """

    # Limit to 16 macros (Ableton's limit for rack device macros)
    num_macros = min(num_macros, 16)

    # Step 1: Set MacroControls Manual values based on parameter values
    for i in range(num_macros):
        if i < len(param_values):
            # Scale from 0-1 to 0-127
            macro_value = param_values[i] * 127.0

            # Find the entire MacroControls.N section and replace its Manual value
            macro_section_pattern = f'<MacroControls\\.{i}>(.*?)</MacroControls\\.{i}>'
            match = re.search(macro_section_pattern, xml_content, flags=re.DOTALL)

            if match:
                old_section = match.group(0)
                # Within this section, replace the Manual value
                new_section = re.sub(
                    r'<Manual Value="[^"]*" />',
                    f'<Manual Value="{macro_value}" />',
                    old_section
                )
                xml_content = xml_content.replace(old_section, new_section)

    # Step 2: Set MacroDefaults to -1 for active macros
    for i in range(num_macros):
        pattern = f'<MacroDefaults.{i} Value="[^"]*" />'
        replacement = f'<MacroDefaults.{i} Value="-1" />'
        xml_content = re.sub(pattern, replacement, xml_content)

    # Step 3: Make macro controls visible
    xml_content = xml_content.replace(
        '<AreMacroControlsVisible Value="false" />',
        '<AreMacroControlsVisible Value="true" />'
    )

    # Step 4: Map plugin parameters to macros
    for i in range(num_macros):
        param_id = 101 + i  # Parameters 101-116

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
    # Add logging to temp folder
    import sys
    import datetime

    log_file = '/Users/Shared/DevWork/GitHub/Looping/temp/mapper_log.txt'

    def log(message):
        with open(log_file, 'a') as f:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {message}\n")
        print(message)

    log("=== Script started ===")
    log(f"Arguments: {sys.argv}")

    parser = argparse.ArgumentParser(
        description='Map drum rack macros with specific parameter values from Live API',
        epilog='Example: python map_macros_with_values.py input.adg output.adg --values 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8'
    )
    parser.add_argument('input_file', type=str, help='Input .adg file')
    parser.add_argument('output_file', type=str, help='Output .adg file')
    parser.add_argument('--values', type=float, nargs='+', required=True,
                        help='16 parameter values (0.0-1.0) from Live API')
    parser.add_argument('--macros', type=int, default=16,
                        help='Number of macros to map (default: 16, max: 16)')
    parser.add_argument('--xml-output', type=str, help='Optional: Save intermediate XML for debugging')

    args = parser.parse_args()
    log(f"Parsed args: input={args.input_file}, output={args.output_file}, values={args.values}")

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    if not input_path.exists():
        msg = f"❌ Error: Input file {input_path} does not exist"
        log(msg)
        return 1

    if input_path.suffix.lower() != '.adg':
        msg = f"❌ Error: Input file must be .adg"
        log(msg)
        return 1

    if len(args.values) < args.macros:
        msg = f"❌ Error: Need at least {args.macros} values, got {len(args.values)}"
        log(msg)
        return 1

    log(f"🔧 Mapping macros for {input_path.name}")
    print(f"🔧 Mapping macros for {input_path.name}")
    print(f"   Mapping first {args.macros} parameters to macros with values:")
    for i in range(min(args.macros, len(args.values))):
        print(f"      Param {101+i} ({args.values[i]:.3f}) → Macro {i+1} ({args.values[i] * 127:.1f})")

    # Extract ADG to XML
    log("Extracting ADG to XML...")
    xml_content = extract_adg_to_xml(input_path)
    log(f"Extracted {len(xml_content)} bytes")

    # Apply macro mappings with values
    log("Applying macro mappings...")
    modified_xml = map_macros_with_values(xml_content, args.values, args.macros)
    log("Mappings applied")

    # Save intermediate XML if requested
    if args.xml_output:
        with open(args.xml_output, 'w') as f:
            f.write(modified_xml)
        print(f"💾 Saved intermediate XML to {args.xml_output}")

    # Compress back to ADG
    log(f"Compressing to {output_path}...")
    compress_xml_to_adg(modified_xml, output_path)
    log(f"✅ Successfully created {output_path}")

    print(f"✅ Successfully created {output_path.name}")
    print(f"   - Parameters 101-{100 + args.macros} mapped to macros 1-{args.macros}")
    print(f"   - Macro values set from Live API parameter values")
    print(f"   - Macro controls visible")

    # Write completion flag for Max to detect
    completion_flag = '/Users/Shared/DevWork/GitHub/Looping/temp/mapper_done.flag'
    with open(completion_flag, 'w') as f:
        f.write(f"DONE: {output_path}\n")
    log(f"Wrote completion flag: {completion_flag}")

    return 0

if __name__ == "__main__":
    exit(main())
