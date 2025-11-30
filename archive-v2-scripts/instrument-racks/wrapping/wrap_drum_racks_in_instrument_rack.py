#!/usr/bin/env python3
"""
Wrap Drum Racks in Instrument Rack

Creates an Instrument Rack containing two drum racks as separate chains.
This approach preserves all device complexity and works with any Ableton version.

Usage:
    python3 wrap_drum_racks_in_instrument_rack.py rack1.adg rack2.adg output.adg
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
import re

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def wrap_drum_racks_in_instrument_rack(
    rack_a_path: Path,
    rack_b_path: Path,
    output_path: Path,
    template_path: Optional[Path] = None
) -> Path:
    """
    Wrap two drum racks into an Instrument Rack with two chains.

    Args:
        rack_a_path: Path to first drum rack (.adg)
        rack_b_path: Path to second drum rack (.adg)
        output_path: Path for output Instrument Rack
        template_path: Optional template Instrument Rack (default: auto-detect)

    Returns:
        Path to created Instrument Rack

    Raises:
        FileNotFoundError: If input files don't exist
    """
    # Validate inputs
    if not rack_a_path.exists():
        raise FileNotFoundError(f"Rack A not found: {rack_a_path}")
    if not rack_b_path.exists():
        raise FileNotFoundError(f"Rack B not found: {rack_b_path}")

    # Use default template if not provided
    if template_path is None:
        # Try multiple locations
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / 'scripts/device-creation/templates/instrument_rack_dual_drums_template.adg',
            Path(__file__).parent.parent / 'templates' / 'instrument_rack_dual_drums_template.adg',
            Path('scripts/device-creation/templates/instrument_rack_dual_drums_template.adg'),
        ]
        for p in possible_paths:
            if p.exists():
                template_path = p
                break
        else:
            raise FileNotFoundError(f"Template not found. Tried: {possible_paths[0]}")

    print(f"\n{'='*70}")
    print(f"WRAPPING DRUM RACKS IN INSTRUMENT RACK")
    print(f"{'='*70}\n")

    # Load template
    print(f"Loading template: {template_path.name}")
    template_xml = decode_adg(template_path)

    # Load both drum racks
    print(f"Reading Rack A: {rack_a_path.name}")
    rack_a_xml = decode_adg(rack_a_path)

    print(f"Reading Rack B: {rack_b_path.name}")
    rack_b_xml = decode_adg(rack_b_path)

    # Extract complete chain content from each source
    # This works whether source is a drum rack or already an instrument rack
    rack_a_chain = extract_chain_content(rack_a_xml, rack_a_path.stem)
    rack_b_chain = extract_chain_content(rack_b_xml, rack_b_path.stem)

    print(f"\nExtracted chain content:")
    print(f"  Rack A: {len(rack_a_chain):,} chars")
    print(f"  Rack B: {len(rack_b_chain):,} chars")

    # Replace the two chains in the template
    result_xml = replace_instrument_rack_chains(
        template_xml,
        rack_a_chain,
        rack_b_chain
    )

    # Encode to .adg
    print(f"\nWriting Instrument Rack: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(result_xml, output_path)

    print(f"\n{'='*70}")
    print(f"✓ WRAP COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {output_path}")
    print(f"Size: {output_path.stat().st_size:,} bytes")

    return output_path


def extract_chain_content(source_xml: str, name: str) -> str:
    """
    Extract complete chain content from source file (input-agnostic).

    Simpler approach: Extract the entire GroupDevicePreset content and wrap as a chain.

    Args:
        source_xml: Complete source .adg XML string
        name: Name for the chain

    Returns:
        Complete InstrumentBranchPreset XML section
    """
    # Simply extract EVERYTHING between <GroupDevicePreset> and </GroupDevicePreset>
    # This captures the complete device regardless of nesting
    start = source_xml.find('<GroupDevicePreset')
    if start == -1:
        raise ValueError(f"No GroupDevicePreset found in {name}")

    # Find the matching closing tag using simple string search from the end
    # Since GroupDevicePreset is the outer wrapper, the last </GroupDevicePreset> is the matching one
    end_tag = '</GroupDevicePreset>'
    end = source_xml.rfind(end_tag)

    if end == -1 or end <= start:
        raise ValueError(f"No closing GroupDevicePreset found in {name}")

    # Extract complete preset (including tags)
    complete_preset = source_xml[start:end + len(end_tag)]

    # Now check if this preset contains an InstrumentBranchPreset or just direct device content
    if '<InstrumentBranchPreset' in complete_preset:
        # Extract just the InstrumentBranchPreset from within BranchPresets
        inner_match = re.search(r'<BranchPresets>\s*(.*?)\s*</BranchPresets>', complete_preset, re.DOTALL)
        if inner_match:
            chain_content = inner_match.group(1).strip()
            # Update name
            chain_content = re.sub(
                r'(<UserName Value=")([^"]*)(" />)',
                rf'\1{name}\3',
                chain_content,
                count=1
            )
            return chain_content

    # Otherwise, wrap the entire GroupDevicePreset as a chain
    return create_instrument_branch_preset(complete_preset, name)


def replace_instrument_rack_chains(
    template_xml: str,
    chain_a_content: str,
    chain_b_content: str
) -> str:
    """
    Replace the two chains in an Instrument Rack template.

    Args:
        template_xml: Instrument Rack template XML
        chain_a_content: Complete InstrumentBranchPreset for chain 1
        chain_b_content: Complete InstrumentBranchPreset for chain 2

    Returns:
        Modified Instrument Rack XML
    """
    print(f"\nReplacing chains in template...")

    # Find all InstrumentBranchPreset sections in template
    pattern = r'<InstrumentBranchPreset Id="0">.*?</InstrumentBranchPreset>'
    matches = list(re.finditer(pattern, template_xml, re.DOTALL))

    if len(matches) < 2:
        raise ValueError(f"Template must have at least 2 chains, found {len(matches)}")

    # Replace first chain
    template_xml = template_xml.replace(matches[0].group(0), chain_a_content, 1)
    print(f"  ✓ Chain 1 replaced ({len(chain_a_content):,} chars)")

    # Find again and replace second
    matches = list(re.finditer(pattern, template_xml, re.DOTALL))
    if len(matches) >= 2:
        template_xml = template_xml.replace(matches[1].group(0), chain_b_content, 1)
        print(f"  ✓ Chain 2 replaced ({len(chain_b_content):,} chars)")

    return template_xml


def create_instrument_branch_preset(group_device_preset: str, chain_name: str) -> str:
    """
    Create an InstrumentBranchPreset wrapping a GroupDevicePreset.

    Args:
        group_device_preset: GroupDevicePreset XML section
        chain_name: Name for the chain

    Returns:
        Complete InstrumentBranchPreset XML
    """
    # Extract just the Device content from GroupDevicePreset
    # We need to nest: InstrumentBranchPreset > DevicePresets > GroupDevicePreset

    return f'''<InstrumentBranchPreset Id="0">
\t\t\t\t<Name Value="" />
\t\t\t\t<IsSoloed Value="false" />
\t\t\t\t<DevicePresets>
\t\t\t\t\t{group_device_preset}
\t\t\t\t</DevicePresets>
\t\t\t\t<MixerPreset>
\t\t\t\t\t<AudioBranchMixerPreset Id="0">
\t\t\t\t\t\t<LomId Value="0" />
\t\t\t\t\t\t<OverwriteProtectionNumber Value="3075" />
\t\t\t\t\t\t<Volume>
\t\t\t\t\t\t\t<LomId Value="0" />
\t\t\t\t\t\t\t<Manual Value="0.8541019559" />
\t\t\t\t\t\t\t<MidiControllerRange>
\t\t\t\t\t\t\t\t<Min Value="0.0003162277571" />
\t\t\t\t\t\t\t\t<Max Value="1.99526238" />
\t\t\t\t\t\t\t</MidiControllerRange>
\t\t\t\t\t\t\t<AutomationTarget Id="0">
\t\t\t\t\t\t\t\t<LockEnvelope Value="0" />
\t\t\t\t\t\t\t</AutomationTarget>
\t\t\t\t\t\t\t<ModulationTarget Id="0">
\t\t\t\t\t\t\t\t<LockEnvelope Value="0" />
\t\t\t\t\t\t\t</ModulationTarget>
\t\t\t\t\t\t</Volume>
\t\t\t\t\t\t<Panorama>
\t\t\t\t\t\t\t<LomId Value="0" />
\t\t\t\t\t\t\t<Manual Value="0" />
\t\t\t\t\t\t\t<MidiControllerRange>
\t\t\t\t\t\t\t\t<Min Value="-1" />
\t\t\t\t\t\t\t\t<Max Value="1" />
\t\t\t\t\t\t\t</MidiControllerRange>
\t\t\t\t\t\t\t<AutomationTarget Id="0">
\t\t\t\t\t\t\t\t<LockEnvelope Value="0" />
\t\t\t\t\t\t\t</AutomationTarget>
\t\t\t\t\t\t\t<ModulationTarget Id="0">
\t\t\t\t\t\t\t\t<LockEnvelope Value="0" />
\t\t\t\t\t\t\t</ModulationTarget>
\t\t\t\t\t\t</Panorama>
\t\t\t\t\t\t<Sends />
\t\t\t\t\t\t<SoloSink Value="false" />
\t\t\t\t\t\t<PanMode Value="0" />
\t\t\t\t\t\t<SplitStereoPanL>
\t\t\t\t\t\t\t<LomId Value="0" />
\t\t\t\t\t\t\t<Manual Value="0" />
\t\t\t\t\t\t\t<MidiControllerRange>
\t\t\t\t\t\t\t\t<Min Value="-1" />
\t\t\t\t\t\t\t\t<Max Value="1" />
\t\t\t\t\t\t\t</MidiControllerRange>
\t\t\t\t\t\t\t<AutomationTarget Id="0">
\t\t\t\t\t\t\t\t<LockEnvelope Value="0" />
\t\t\t\t\t\t\t</AutomationTarget>
\t\t\t\t\t\t\t<ModulationTarget Id="0">
\t\t\t\t\t\t\t\t<LockEnvelope Value="0" />
\t\t\t\t\t\t\t</ModulationTarget>
\t\t\t\t\t\t</SplitStereoPanL>
\t\t\t\t\t\t<SplitStereoPanR>
\t\t\t\t\t\t\t<LomId Value="0" />
\t\t\t\t\t\t\t<Manual Value="0" />
\t\t\t\t\t\t\t<MidiControllerRange>
\t\t\t\t\t\t\t\t<Min Value="-1" />
\t\t\t\t\t\t\t\t<Max Value="1" />
\t\t\t\t\t\t\t</MidiControllerRange>
\t\t\t\t\t\t\t<AutomationTarget Id="0">
\t\t\t\t\t\t\t\t<LockEnvelope Value="0" />
\t\t\t\t\t\t\t</AutomationTarget>
\t\t\t\t\t\t\t<ModulationTarget Id="0">
\t\t\t\t\t\t\t\t<LockEnvelope Value="0" />
\t\t\t\t\t\t\t</ModulationTarget>
\t\t\t\t\t\t</SplitStereoPanR>
\t\t\t\t\t</AudioBranchMixerPreset>
\t\t\t\t</MixerPreset>
\t\t\t\t<BranchSelectorRange>
\t\t\t\t\t<Min Value="0" />
\t\t\t\t\t<Max Value="127" />
\t\t\t\t</BranchSelectorRange>
\t\t\t\t<SessionViewBranchWidth Value="55" />
\t\t\t\t<SourceContext>
\t\t\t\t\t<Value />
\t\t\t\t</SourceContext>
\t\t\t</InstrumentBranchPreset>'''


def main():
    parser = argparse.ArgumentParser(
        description='Wrap two drum racks in an Instrument Rack container',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Wrap two drum racks
    python3 wrap_drum_racks_in_instrument_rack.py kit1.adg kit2.adg output.adg

    # Use custom template
    python3 wrap_drum_racks_in_instrument_rack.py kit1.adg kit2.adg output.adg \\
        --template my_template.adg

Benefits over direct merge:
    - Preserves all device complexity
    - Works with any Ableton version
    - No MIDI note conflicts
    - Both kits selectable via chain selector
        """
    )

    parser.add_argument('rack_a', type=Path, help='First drum rack (.adg file)')
    parser.add_argument('rack_b', type=Path, help='Second drum rack (.adg file)')
    parser.add_argument('output', type=Path, help='Output Instrument Rack path')
    parser.add_argument(
        '--template',
        type=Path,
        default=None,
        help='Optional template Instrument Rack'
    )

    args = parser.parse_args()

    try:
        wrap_drum_racks_in_instrument_rack(
            args.rack_a,
            args.rack_b,
            args.output,
            args.template
        )

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
