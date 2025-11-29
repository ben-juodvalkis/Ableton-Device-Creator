#!/usr/bin/env python3
"""
Create Multi-Velocity Drum Rack from Auto Sampled Folders

Takes a folder of Auto Sampled multi-velocity samples and creates a drum rack
with MultiSampler devices on each pad, using velocity layers like the template.

Filename format: KitName-Note-VelocityLevel-RandomID.aif
Example: Burnt Crispr-C1-V127-5GYZ.aif

Usage:
    python3 create_multivelocity_drum_rack.py sample_folder output.adg
    python3 create_multivelocity_drum_rack.py "Burnt Crispr" output.adg --template template.adg
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from collections import defaultdict

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg


def note_name_to_midi(note_name: str) -> int:
    """Convert note name (e.g., 'C1', 'A#2') to MIDI note number."""
    # Handle sharp notes
    if '#' in note_name:
        note_part = note_name[:-1]  # e.g., 'A#1' -> 'A#'
        octave = int(note_name[-1])
    else:
        note_part = note_name[:-1]  # e.g., 'C1' -> 'C'
        octave = int(note_name[-1])
    
    # Note mapping (C=0, C#=1, D=2, D#=3, E=4, F=5, F#=6, G=7, G#=8, A=9, A#=10, B=11)
    note_map = {
        'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 
        'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11
    }
    
    if note_part not in note_map:
        raise ValueError(f"Invalid note: {note_part}")
    
    # MIDI note = (octave + 1) * 12 + note_offset
    # This gives us C1=24, C2=36, C3=48, etc.
    return (octave + 1) * 12 + note_map[note_part]


def midi_to_drum_pad(midi_note: int) -> int:
    """Convert MIDI note to drum pad number (1-based, where pad 1 = MIDI 92)."""
    # Standard drum rack: Pad 1 = MIDI 92, Pad 32 = MIDI 61
    # Pad number = 93 - MIDI note
    return 93 - midi_note


def drum_pad_to_midi(pad_number: int) -> int:
    """Convert drum pad number to MIDI note (where pad 1 = MIDI 92)."""
    return 93 - pad_number


def parse_auto_sampled_filename(filename: str) -> Optional[Tuple[str, str, int]]:
    """
    Parse Auto Sampled filename format.
    
    Args:
        filename: Auto Sampled filename (e.g., 'Burnt Crispr-C1-V127-5GYZ.aif')
    
    Returns:
        Tuple of (kit_name, note_name, velocity) or None if invalid
    """
    # Pattern: KitName-Note-VelocityLevel-RandomID.extension
    pattern = r'^(.+?)-([A-G]#?\d+)-V(\d+)-[A-Z0-9]+\.(aif|wav)$'
    match = re.match(pattern, filename)
    
    if match:
        kit_name = match.group(1)
        note_name = match.group(2)
        velocity = int(match.group(3))
        return kit_name, note_name, velocity
    
    return None


def organize_samples_by_note(sample_folder: Path) -> Dict[str, List[Tuple[int, str]]]:
    """
    Organize samples by note name with velocity layers.
    
    Args:
        sample_folder: Path to folder containing Auto Sampled files
    
    Returns:
        Dict mapping note_name -> [(velocity, file_path), ...]
    """
    samples_by_note = defaultdict(list)
    
    print(f"Scanning samples in: {sample_folder}")
    
    # Look for .aif and .wav files
    for ext in ['*.aif', '*.wav']:
        for sample_file in sample_folder.glob(ext):
            parsed = parse_auto_sampled_filename(sample_file.name)
            if parsed:
                kit_name, note_name, velocity = parsed
                samples_by_note[note_name].append((velocity, str(sample_file)))
    
    # Sort velocity layers for each note
    for note_name in samples_by_note:
        samples_by_note[note_name].sort(key=lambda x: x[0])  # Sort by velocity
    
    print(f"Found samples for {len(samples_by_note)} notes:")
    for note_name, velocity_layers in samples_by_note.items():
        velocities = [v for v, _ in velocity_layers]
        print(f"  {note_name}: {len(velocity_layers)} layers (V{min(velocities)}-V{max(velocities)})")
    
    return dict(samples_by_note)


def create_velocity_ranges(velocity_layers: List[Tuple[int, str]]) -> List[Tuple[int, int, str]]:
    """
    Create velocity ranges for MultiSampler from sorted velocity layers.
    
    Args:
        velocity_layers: List of (velocity, file_path) sorted by velocity
    
    Returns:
        List of (vel_min, vel_max, file_path) tuples
    """
    if not velocity_layers:
        return []
    
    ranges = []
    num_layers = len(velocity_layers)
    
    for i, (velocity, file_path) in enumerate(velocity_layers):
        if i == 0:
            # First layer: 1 to midpoint between this and next
            if num_layers == 1:
                vel_min, vel_max = 1, 127
            else:
                next_velocity = velocity_layers[i + 1][0]
                vel_min = 1
                vel_max = (velocity + next_velocity) // 2
        elif i == num_layers - 1:
            # Last layer: from previous midpoint to 127
            prev_velocity = velocity_layers[i - 1][0]
            vel_min = (prev_velocity + velocity) // 2 + 1
            vel_max = 127
        else:
            # Middle layer: from previous midpoint to next midpoint
            prev_velocity = velocity_layers[i - 1][0]
            next_velocity = velocity_layers[i + 1][0]
            vel_min = (prev_velocity + velocity) // 2 + 1
            vel_max = (velocity + next_velocity) // 2
        
        ranges.append((vel_min, vel_max, file_path))
    
    return ranges


def create_multisampler_xml(note_name: str, velocity_ranges: List[Tuple[int, int, str]]) -> str:
    """
    Create MultiSampler device XML with velocity layers.
    
    Args:
        note_name: Note name for this sampler (e.g., 'C1')
        velocity_ranges: List of (vel_min, vel_max, file_path) tuples
    
    Returns:
        Complete MultiSampler device XML string
    """
    # Get the MIDI note for the root key
    root_key = note_name_to_midi(note_name)
    
    # Start building the MultiSampler XML
    multisampler_parts = []
    
    for i, (vel_min, vel_max, file_path) in enumerate(velocity_ranges):
        # Create relative path (adjust as needed for your setup)
        rel_path = "../../" + '/'.join(file_path.split('/')[-3:])
        
        part_xml = f'''			<MultiSamplePart Id="{i}">
				<LomId Value="0" />
				<Name Value="{Path(file_path).stem}" />
				<KeyRange>
					<Min Value="0" />
					<Max Value="127" />
					<CrossfadeMin Value="0" />
					<CrossfadeMax Value="127" />
				</KeyRange>
				<VelocityRange>
					<Min Value="{vel_min}" />
					<Max Value="{vel_max}" />
					<CrossfadeMin Value="{vel_min}" />
					<CrossfadeMax Value="{vel_max}" />
				</VelocityRange>
				<SelectorRange>
					<Min Value="0" />
					<Max Value="127" />
					<CrossfadeMin Value="0" />
					<CrossfadeMax Value="127" />
				</SelectorRange>
				<RootKey Value="{root_key}" />
				<DetailClipKey Value="{root_key}" />
				<TuningInSemitones Value="0" />
				<SampleRef>
					<FileRef>
						<RelativePathType Value="3" />
						<RelativePath Value="{rel_path}" />
						<Path Value="{file_path}" />
						<Type Value="1" />
						<LivePackName Value="" />
						<LivePackId Value="" />
						<OriginalFileSize Value="0" />
						<OriginalCrc Value="0" />
						<SourceHint Value="" />
					</FileRef>
				</SampleRef>
				<SampleStart Value="0" />
				<SampleEnd Value="0" />
				<LoopStart Value="0" />
				<LoopEnd Value="0" />
				<OutMarkerSampleStart Value="0" />
				<OutMarkerSampleEnd Value="0" />
				<StretchMode Value="0" />
				<ScrollPosition Value="0" />
				<SampleVolume Value="1" />
				<Reverse Value="false" />
				<Snap Value="true" />
				<NestedPlayback Value="false" />
				<LinkedSampleEditing Value="false" />
			</MultiSamplePart>'''
        multisampler_parts.append(part_xml)
    
    # Complete MultiSampler XML with all sample parts
    multisampler_xml = f'''		<MultiSampler Id="0">
			<LomId Value="0" />
			<LomIdView Value="0" />
			<IsExpanded Value="true" />
			<On>
				<LomId Value="0" />
				<Manual Value="true" />
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<MidiCCOnOffThresholds>
					<Min Value="64" />
					<Max Value="127" />
				</MidiCCOnOffThresholds>
			</On>
			<ModulationSourceCount Value="0" />
			<ParametersListWrapper LomId="0" />
			<Pointee Id="0" />
			<LastSelectedTimeableIndex Value="0" />
			<LastSelectedClipEnvelopeIndex Value="0" />
			<LastPresetRef>
				<Value>
					<AbletonDefaultPresetRef Id="0">
						<FileRef>
							<RelativePathType Value="7" />
							<RelativePath Value="Devices/Instruments/Sampler" />
							<Path Value="/Applications/Ableton Live 12 Beta.app/Contents/App-Resources/Builtin/Devices/Instruments/Sampler" />
							<Type Value="2" />
							<LivePackName Value="" />
							<LivePackId Value="" />
							<OriginalFileSize Value="0" />
							<OriginalCrc Value="0" />
							<SourceHint Value="" />
						</FileRef>
						<DeviceId Name="MultiSampler" />
					</AbletonDefaultPresetRef>
				</Value>
			</LastPresetRef>
			<LockedScripts />
			<IsFolded Value="false" />
			<ShouldShowPresetName Value="true" />
			<UserName Value="" />
			<Annotation Value="" />
			<SourceContext>
				<Value />
			</SourceContext>
			<MpePitchBendUsesTuning Value="true" />
			<ViewData Value="{{}}" />
			<MultiSampleMap>
				<SampleParts>
{chr(10).join(multisampler_parts)}
				</SampleParts>
			</MultiSampleMap>
			<Player>
				<MultiSamplePartSelection>
					<SelectedIndex Value="0" />
				</MultiSamplePartSelection>
				<SamplePlayingMode>
					<SamplePart Value="0" />
				</SamplePlayingMode>
				<SampleSelector>
					<LomId Value="0" />
					<Manual Value="0" />
					<MidiControllerRange>
						<Min Value="0" />
						<Max Value="127" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</SampleSelector>
				<IsSamplerDevice Value="true" />
				<LoadSampleTimeout Value="100" />
				<LastBrowsedSampleFolder Value="" />
				<SampleVolumeModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</SampleVolumeModulationTarget>
			</Player>
		</MultiSampler>'''
    
    return multisampler_xml


def create_drum_branch_xml(note_name: str, multisampler_xml: str, pad_midi_note: int) -> str:
    """
    Create complete DrumBranchPreset XML with MultiSampler device.
    
    Args:
        note_name: Note name (e.g., 'C1')
        multisampler_xml: Complete MultiSampler device XML
        pad_midi_note: MIDI note for this drum pad (92 for pad 1)
    
    Returns:
        Complete DrumBranchPreset XML string
    """
    sending_note = note_name_to_midi(note_name)  # Note sent to the sampler
    
    branch_xml = f'''	<DrumBranchPreset Id="0">
		<Name Value="{note_name}" />
		<DevicePresets>
			<AbletonDevicePreset Id="0">
				<Device>
{multisampler_xml}
				</Device>
				<OverwriteProtectionNumber Value="3075" />
				<LocalFiltersJson Value="" />
				<PresetRef>
					<AbletonDefaultPresetRef Id="0">
						<FileRef>
							<RelativePathType Value="7" />
							<RelativePath Value="Devices/Instruments/Sampler" />
							<Path Value="/Applications/Ableton Live 12 Beta.app/Contents/App-Resources/Builtin/Devices/Instruments/Sampler" />
							<Type Value="2" />
							<LivePackName Value="" />
							<LivePackId Value="" />
							<OriginalFileSize Value="0" />
							<OriginalCrc Value="0" />
							<SourceHint Value="" />
						</FileRef>
						<DeviceId Name="MultiSampler" />
					</AbletonDefaultPresetRef>
				</PresetRef>
				<BranchDeviceId Value="device:ableton:instr:MultiSampler" />
			</AbletonDevicePreset>
		</DevicePresets>
		<MixerPreset>
			<AudioBranchMixerPreset Id="0">
				<LomId Value="0" />
				<OverwriteProtectionNumber Value="3075" />
				<Volume>
					<LomId Value="0" />
					<Manual Value="0.8541019559" />
					<MidiControllerRange>
						<Min Value="0.0003162277571" />
						<Max Value="1.99526238" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</Volume>
				<Panorama>
					<LomId Value="0" />
					<Manual Value="0" />
					<MidiControllerRange>
						<Min Value="-1" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</Panorama>
				<Sends />
				<SoloSink Value="false" />
				<PanMode Value="0" />
				<SplitStereoPanL>
					<LomId Value="0" />
					<Manual Value="0" />
					<MidiControllerRange>
						<Min Value="-1" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</SplitStereoPanL>
				<SplitStereoPanR>
					<LomId Value="0" />
					<Manual Value="0" />
					<MidiControllerRange>
						<Min Value="-1" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</SplitStereoPanR>
			</AudioBranchMixerPreset>
		</MixerPreset>
		<BranchSelectorRange>
			<Min Value="0" />
			<Max Value="127" />
		</BranchSelectorRange>
		<SessionViewBranchWidth Value="55" />
		<SourceContext>
			<BranchSourceContext Id="0">
				<OriginalFileSize Value="0" />
				<OriginalCrc Value="0" />
				<BranchDeviceId Value="device:ableton:instr:MultiSampler" />
				<LocalFiltersJson Value="" />
				<PresetRef>
					<AbletonDefaultPresetRef Id="0">
						<FileRef>
							<RelativePathType Value="7" />
							<RelativePath Value="Devices/Instruments/Sampler" />
							<Path Value="/Applications/Ableton Live 12 Beta.app/Contents/App-Resources/Builtin/Devices/Instruments/Sampler" />
							<Type Value="2" />
							<LivePackName Value="" />
							<LivePackId Value="" />
							<OriginalFileSize Value="0" />
							<OriginalCrc Value="0" />
							<SourceHint Value="" />
						</FileRef>
						<DeviceId Name="MultiSampler" />
					</AbletonDefaultPresetRef>
				</PresetRef>
				<BranchDeviceId Value="device:ableton:instr:MultiSampler" />
			</BranchSourceContext>
		</SourceContext>
		<ZoneSettings>
			<ReceivingNote Value="{pad_midi_note}" />
			<SendingNote Value="{sending_note}" />
			<ChokeGroup Value="0" />
		</ZoneSettings>
	</DrumBranchPreset>'''
    
    return branch_xml


def create_multivelocity_drum_rack(
    sample_folder: Path,
    output_path: Path,
    template_path: Optional[Path] = None
) -> Path:
    """
    Create a multi-velocity drum rack from Auto Sampled folder.
    
    Args:
        sample_folder: Path to folder containing Auto Sampled files
        output_path: Path for output drum rack
        template_path: Optional template drum rack (uses built-in if not provided)
    
    Returns:
        Path to created drum rack
    
    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If no valid samples found
    """
    # Validate inputs
    if not sample_folder.exists():
        raise FileNotFoundError(f"Sample folder not found: {sample_folder}")
    
    print(f"\n{'='*70}")
    print(f"CREATING MULTI-VELOCITY DRUM RACK")
    print(f"{'='*70}\n")
    
    # Organize samples by note
    samples_by_note = organize_samples_by_note(sample_folder)
    
    if not samples_by_note:
        raise ValueError(f"No valid Auto Sampled files found in {sample_folder}")
    
    # Create drum branches for each note
    drum_branches = []
    total_velocity_layers = 0
    
    print(f"\nCreating drum pads:")
    
    # Sort notes by MIDI note number for consistent pad assignment
    sorted_notes = sorted(samples_by_note.keys(), key=note_name_to_midi)
    
    for i, note_name in enumerate(sorted_notes):
        velocity_layers = samples_by_note[note_name]
        
        # Skip notes with no velocity layers
        if not velocity_layers:
            continue
        
        # Calculate drum pad MIDI note (pad 1 = MIDI 92, pad 2 = MIDI 91, etc.)
        pad_number = i + 1
        pad_midi_note = drum_pad_to_midi(pad_number)
        
        # Create velocity ranges
        velocity_ranges = create_velocity_ranges(velocity_layers)
        total_velocity_layers += len(velocity_ranges)
        
        # Create MultiSampler XML
        multisampler_xml = create_multisampler_xml(note_name, velocity_ranges)
        
        # Create drum branch XML
        branch_xml = create_drum_branch_xml(note_name, multisampler_xml, pad_midi_note)
        drum_branches.append(branch_xml)
        
        # Log creation
        velocities = [f"V{v}" for v, _ in velocity_layers]
        ranges_str = ', '.join([f"V{vmin}-{vmax}" for vmin, vmax, _ in velocity_ranges])
        print(f"  Pad {pad_number:2d} ({note_name}): {len(velocity_layers)} layers ({ranges_str})")
    
    # Create complete drum rack XML
    branches_xml = '\n'.join(drum_branches)
    
    drum_rack_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Ableton MajorVersion="5" MinorVersion="12.0_12300" SchemaChangeCount="1" Creator="Ableton Live 12.3b14" Revision="60e3c7d386cee7e68f51086d1a4b72a3f1c19ca2">
	<GroupDevicePreset>
		<OverwriteProtectionNumber Value="3075" />
		<Device>
			<DrumGroupDevice Id="0">
				<LomId Value="0" />
				<LomIdView Value="0" />
				<IsExpanded Value="true" />
				<BreakoutIsExpanded Value="false" />
				<On>
					<LomId Value="0" />
					<Manual Value="true" />
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<MidiCCOnOffThresholds>
						<Min Value="64" />
						<Max Value="127" />
					</MidiCCOnOffThresholds>
				</On>
				<ModulationSourceCount Value="0" />
				<ParametersListWrapper LomId="0" />
				<Pointee Id="0" />
				<LastSelectedTimeableIndex Value="0" />
				<LastSelectedClipEnvelopeIndex Value="0" />
				<LastPresetRef>
					<Value>
						<AbletonDefaultPresetRef Id="0">
							<FileRef>
								<RelativePathType Value="7" />
								<RelativePath Value="Devices/Instruments/Drum Rack" />
								<Path Value="/Applications/Ableton Live 12 Beta.app/Contents/App-Resources/Builtin/Devices/Instruments/Drum Rack" />
								<Type Value="2" />
								<LivePackName Value="" />
								<LivePackId Value="" />
								<OriginalFileSize Value="0" />
								<OriginalCrc Value="0" />
								<SourceHint Value="" />
							</FileRef>
							<DeviceId Name="DrumGroupDevice" />
						</AbletonDefaultPresetRef>
					</Value>
				</LastPresetRef>
				<LockedScripts />
				<IsFolded Value="false" />
				<ShouldShowPresetName Value="true" />
				<UserName Value="" />
				<Annotation Value="" />
				<SourceContext>
					<Value />
				</SourceContext>
				<MpePitchBendUsesTuning Value="true" />
				<ViewData Value="{{}}" />
				<OverwriteProtectionNumber Value="3075" />
				<Branches />
				<IsBranchesListVisible Value="false" />
				<IsReturnBranchesListVisible Value="false" />
				<IsRangesEditorVisible Value="false" />
				<AreDevicesVisible Value="true" />
				<BranchPresets>
{branches_xml}
				</BranchPresets>
				<ReturnBranchPresets />
			</DrumGroupDevice>
		</Device>
	</GroupDevicePreset>
</Ableton>'''
    
    # Encode to .adg
    print(f"\nWriting drum rack: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encode_adg(drum_rack_xml, output_path)
    
    print(f"\n{'='*70}")
    print(f"✓ CREATION COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {output_path}")
    print(f"Drum pads: {len(drum_branches)}")
    print(f"Total velocity layers: {total_velocity_layers}")
    print(f"Notes covered: {', '.join(sorted_notes)}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Create multi-velocity drum rack from Auto Sampled folder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create drum rack from sample folder
    python3 create_multivelocity_drum_rack.py "/path/to/Burnt Crispr" output.adg
    
    # Use custom template
    python3 create_multivelocity_drum_rack.py sample_folder output.adg --template my_template.adg

Auto Sampled Format:
    Filenames must follow: KitName-Note-VelocityLevel-RandomID.extension
    Example: Burnt Crispr-C1-V127-5GYZ.aif
    
    - Note: C1, C#1, D1, etc.
    - Velocity: V21, V42, V64, V85, V106, V127 (typical levels)
    - Extension: .aif or .wav

Features:
    - Each note gets its own drum pad with MultiSampler device
    - Velocity layers automatically distributed across 1-127 range
    - Supports any number of velocity layers per note
    - Maintains chromatic note order in drum rack
        """
    )
    
    parser.add_argument(
        'sample_folder',
        type=Path,
        help='Path to folder containing Auto Sampled files'
    )
    parser.add_argument(
        'output',
        type=Path,
        help='Output drum rack path (.adg file)'
    )
    parser.add_argument(
        '--template',
        type=Path,
        default=None,
        help='Optional template drum rack (not implemented yet)'
    )
    
    args = parser.parse_args()
    
    try:
        create_multivelocity_drum_rack(
            args.sample_folder,
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