#!/usr/bin/env python3
"""
Add parameter visibility to Ableton drum rack (.adg) files
Makes all 128 Komplete Kontrol parameters (101-228) visible in the device UI
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

def add_parameter_visibility(xml_content, num_params=128, start_lom_id=76445):
    """
    Add PluginParameterSettings to make parameters visible in Ableton

    Adds parameter settings for parameters 101-228 (128 params) if they don't exist.
    Does NOT map them to macros - just makes them visible.
    """

    # Check if ParameterSettings already exists with content
    existing_param_match = re.search(r'<ParameterSettings>(.*?)</ParameterSettings>', xml_content, re.DOTALL)
    if existing_param_match:
        existing_content = existing_param_match.group(1)
        existing_count = existing_content.count('<PluginParameterSettings Id=')

        if existing_count >= num_params:
            print(f"   ⚠️  Already has {existing_count} parameters (>= {num_params}), skipping...")
            return xml_content
        else:
            print(f"   📝 Extending from {existing_count} to {num_params} parameters...")
            # Continue to replace with full parameter set

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

    # Replace ParameterSettings (empty or existing) with the full version
    new_param_section = f'<ParameterSettings>\n{full_param_settings}\n\t\t\t\t\t</ParameterSettings>'

    # Try replacing empty version first
    if '<ParameterSettings />' in xml_content:
        xml_content = xml_content.replace('<ParameterSettings />', new_param_section)
    else:
        # Replace existing ParameterSettings section
        xml_content = re.sub(
            r'<ParameterSettings>.*?</ParameterSettings>',
            new_param_section,
            xml_content,
            flags=re.DOTALL
        )

    return xml_content

def main():
    parser = argparse.ArgumentParser(
        description='Add parameter visibility to Ableton drum rack (.adg) files',
        epilog='Example: python add_parameter_visibility.py input.adg output.adg'
    )
    parser.add_argument('input_file', type=str, help='Input .adg file')
    parser.add_argument('output_file', type=str, help='Output .adg file')
    parser.add_argument('--params', type=int, default=128, help='Number of parameters to make visible (default: 128)')
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

    print(f"🔧 Adding parameter visibility to {input_path.name}")
    print(f"   Making parameters 101-{100 + args.params} visible...")

    # Extract ADG to XML
    xml_content = extract_adg_to_xml(input_path)

    # Add parameter visibility
    modified_xml = add_parameter_visibility(xml_content, args.params)

    # Save intermediate XML if requested
    if args.xml_output:
        with open(args.xml_output, 'w') as f:
            f.write(modified_xml)
        print(f"💾 Saved intermediate XML to {args.xml_output}")

    # Compress back to ADG
    compress_xml_to_adg(modified_xml, output_path)

    print(f"✅ Successfully created {output_path.name}")
    print(f"   - Plugin parameters 101-{100 + args.params} are now visible")
    print(f"   - Parameters are NOT yet mapped to macros")

if __name__ == "__main__":
    main()
