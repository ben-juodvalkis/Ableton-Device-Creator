#!/usr/bin/env python3
"""
Convert Ableton Simpler (.adv) to DrumCell (.adv)

Replicates Ableton's built-in "Convert Simpler to Drum Rack" functionality
by mapping OriginalSimpler XML structure to DrumCell XML structure.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.decoder import decode_adg
from utils.encoder import encode_adg


def create_drumcell_template():
    """Create a basic DrumCell XML structure with default values"""
    template = """<?xml version="1.0" encoding="UTF-8"?>
<Ableton MajorVersion="5" MinorVersion="12.0_12300" SchemaChangeCount="1" Creator="Ableton Live 12.3b12" Revision="a51ffacdd96935f4e75c565b931d9d81c161dfb8">
	<DrumCell>
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
			<Value />
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
		<ViewData Value="{}" />
		<OverwriteProtectionNumber Value="3075" />
		<UserSample>
			<Value>
				<SampleRef Id="0">
					<FileRef>
						<RelativePathType Value="5" />
						<RelativePath Value="" />
						<Path Value="" />
						<Type Value="2" />
						<LivePackName Value="" />
						<LivePackId Value="" />
						<OriginalFileSize Value="0" />
						<OriginalCrc Value="0" />
						<SourceHint Value="" />
					</FileRef>
					<LastModDate Value="0" />
					<SourceContext />
					<SampleUsageHint Value="0" />
					<DefaultDuration Value="0" />
					<DefaultSampleRate Value="44100" />
					<SamplesToAutoWarp Value="1" />
				</SampleRef>
			</Value>
		</UserSample>
		<Voice_Gain Value="1" />
		<Voice_Transpose>
			<LomId Value="0" />
			<Manual Value="0" />
			<MidiControllerRange>
				<Min Value="-48" />
				<Max Value="48" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_Transpose>
		<Voice_Detune>
			<LomId Value="0" />
			<Manual Value="0" />
			<MidiControllerRange>
				<Min Value="-0.5" />
				<Max Value="0.5" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_Detune>
		<Voice_VelocityToVolume>
			<LomId Value="0" />
			<Manual Value="0.349999994" />
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_VelocityToVolume>
		<Voice_ModulationSource>
			<LomId Value="0" />
			<Manual Value="0" />
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
		</Voice_ModulationSource>
		<Voice_ModulationTarget>
			<LomId Value="0" />
			<Manual Value="0" />
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="5" />
			</MidiControllerRange>
		</Voice_ModulationTarget>
		<Voice_ModulationAmount>
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
		</Voice_ModulationAmount>
		<Voice_Filter_On>
			<LomId Value="0" />
			<Manual Value="true" />
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<MidiCCOnOffThresholds>
				<Min Value="64" />
				<Max Value="127" />
			</MidiCCOnOffThresholds>
		</Voice_Filter_On>
		<Voice_Filter_Frequency>
			<LomId Value="0" />
			<Manual Value="21999.9902" />
			<MidiControllerRange>
				<Min Value="29.9999981" />
				<Max Value="21999.9902" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_Filter_Frequency>
		<Voice_Filter_Resonance>
			<LomId Value="0" />
			<Manual Value="0" />
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="0.8999999762" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_Filter_Resonance>
		<Voice_Filter_Type>
			<LomId Value="0" />
			<Manual Value="1" />
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="3" />
			</MidiControllerRange>
		</Voice_Filter_Type>
		<Voice_Filter_PeakGain>
			<LomId Value="0" />
			<Manual Value="1" />
			<MidiControllerRange>
				<Min Value="0.2511886358" />
				<Max Value="3.98107195" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_Filter_PeakGain>
		<Voice_Envelope_Attack>
			<LomId Value="0" />
			<Manual Value="0.00009999999747" />
			<MidiControllerRange>
				<Min Value="0.00009999999747" />
				<Max Value="20.0000076" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_Envelope_Attack>
		<Voice_Envelope_Hold>
			<LomId Value="0" />
			<Manual Value="0.3000001013" />
			<MidiControllerRange>
				<Min Value="0.001000000047" />
				<Max Value="60.0000343" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_Envelope_Hold>
		<Voice_Envelope_Decay>
			<LomId Value="0" />
			<Manual Value="1" />
			<MidiControllerRange>
				<Min Value="0.001000000047" />
				<Max Value="60.0000343" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_Envelope_Decay>
		<Voice_Envelope_Mode>
			<LomId Value="0" />
			<Manual Value="0" />
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
		</Voice_Envelope_Mode>
		<Voice_PlaybackStart>
			<LomId Value="0" />
			<Manual Value="0" />
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_PlaybackStart>
		<Voice_PlaybackLength>
			<LomId Value="0" />
			<Manual Value="0.999951601" />
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Voice_PlaybackLength>
		<Voice_PitchToEnvelopeModulation Value="false" />
		<Volume>
			<LomId Value="0" />
			<Manual Value="0" />
			<MidiControllerRange>
				<Min Value="-36" />
				<Max Value="36" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Volume>
		<Pan>
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
		</Pan>
		<Effect_On>
			<LomId Value="0" />
			<Manual Value="true" />
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<MidiCCOnOffThresholds>
				<Min Value="64" />
				<Max Value="127" />
			</MidiCCOnOffThresholds>
		</Effect_On>
		<Effect_Type>
			<LomId Value="0" />
			<Manual Value="0" />
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="8" />
			</MidiControllerRange>
		</Effect_Type>
		<Effect_PitchEnvelopeAmount>
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
		</Effect_PitchEnvelopeAmount>
		<Effect_PitchEnvelopeDecay>
			<LomId Value="0" />
			<Manual Value="0.2999999821" />
			<MidiControllerRange>
				<Min Value="0.004999999888" />
				<Max Value="2" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_PitchEnvelopeDecay>
		<Effect_SubOscAmount>
			<LomId Value="0" />
			<Manual Value="0" />
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_SubOscAmount>
		<Effect_SubOscFrequency>
			<LomId Value="0" />
			<Manual Value="59.9999924" />
			<MidiControllerRange>
				<Min Value="29.9999962" />
				<Max Value="119.999985" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_SubOscFrequency>
		<Effect_NoiseAmount>
			<LomId Value="0" />
			<Manual Value="0" />
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_NoiseAmount>
		<Effect_NoiseFrequency>
			<LomId Value="0" />
			<Manual Value="10000.001" />
			<MidiControllerRange>
				<Min Value="180" />
				<Max Value="15000" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_NoiseFrequency>
		<Effect_LoopOffset>
			<LomId Value="0" />
			<Manual Value="0.01999999769" />
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_LoopOffset>
		<Effect_LoopLength>
			<LomId Value="0" />
			<Manual Value="0.3000000119" />
			<MidiControllerRange>
				<Min Value="0.009999999776" />
				<Max Value="0.5" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_LoopLength>
		<Effect_StretchFactor>
			<LomId Value="0" />
			<Manual Value="1" />
			<MidiControllerRange>
				<Min Value="1" />
				<Max Value="20" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_StretchFactor>
		<Effect_StretchGrainSize>
			<LomId Value="0" />
			<Manual Value="0.09999999404" />
			<MidiControllerRange>
				<Min Value="0.004999999888" />
				<Max Value="0.3000000119" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_StretchGrainSize>
		<Effect_PunchAmount>
			<LomId Value="0" />
			<Manual Value="0" />
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_PunchAmount>
		<Effect_PunchTime>
			<LomId Value="0" />
			<Manual Value="0.1201599985" />
			<MidiControllerRange>
				<Min Value="0.05999999866" />
				<Max Value="1" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_PunchTime>
		<Effect_EightBitResamplingRate>
			<LomId Value="0" />
			<Manual Value="14080" />
			<MidiControllerRange>
				<Min Value="999.999878" />
				<Max Value="30000.002" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_EightBitResamplingRate>
		<Effect_EightBitFilterDecay>
			<LomId Value="0" />
			<Manual Value="5.00000095" />
			<MidiControllerRange>
				<Min Value="0.009999999776" />
				<Max Value="5.00000095" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_EightBitFilterDecay>
		<Effect_FmAmount>
			<LomId Value="0" />
			<Manual Value="0" />
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_FmAmount>
		<Effect_FmFrequency>
			<LomId Value="0" />
			<Manual Value="999.999878" />
			<MidiControllerRange>
				<Min Value="9.99999905" />
				<Max Value="4500.00146" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_FmFrequency>
		<Effect_RingModAmount>
			<LomId Value="0" />
			<Manual Value="0" />
			<MidiControllerRange>
				<Min Value="0" />
				<Max Value="1" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_RingModAmount>
		<Effect_RingModFrequency>
			<LomId Value="0" />
			<Manual Value="999.999817" />
			<MidiControllerRange>
				<Min Value="1" />
				<Max Value="5000" />
			</MidiControllerRange>
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<ModulationTarget Id="0">
				<LockEnvelope Value="0" />
			</ModulationTarget>
		</Effect_RingModFrequency>
		<NotePitchBend Value="true" />
	</DrumCell>
</Ableton>"""
    return ET.fromstring(template)


def copy_element_attributes(source, target):
    """Copy all attributes from source element to target element"""
    for key, value in source.attrib.items():
        target.set(key, value)


def copy_sample_reference(simpler_root, drumcell_root):
    """Copy sample reference from Simpler to DrumCell"""
    # Find first MultiSamplePart (or the selected one)
    sample_parts = simpler_root.findall('.//MultiSamplePart')
    if not sample_parts:
        print("Warning: No MultiSamplePart found in Simpler")
        return

    # Use the first one (or find the one with Selection="true")
    simpler_part = sample_parts[0]
    for part in sample_parts:
        if part.find('Selection') is not None and part.find('Selection').get('Value') == 'true':
            simpler_part = part
            break

    # Extract sample reference info
    simpler_ref = simpler_part.find('SampleRef')
    if simpler_ref is None:
        print("Warning: No SampleRef found in MultiSamplePart")
        return

    # Find DrumCell sample reference
    drumcell_ref = drumcell_root.find('.//UserSample/Value/SampleRef')
    if drumcell_ref is None:
        print("Error: Could not find DrumCell SampleRef")
        return

    # Copy FileRef
    simpler_file_ref = simpler_ref.find('FileRef')
    drumcell_file_ref = drumcell_ref.find('FileRef')
    if simpler_file_ref is not None and drumcell_file_ref is not None:
        # Check if sample exists - can be in Path OR RelativePath/Name format
        path_elem = simpler_file_ref.find('Path')
        name_elem = simpler_file_ref.find('Name')
        has_relative_elem = simpler_file_ref.find('HasRelativePath')

        # Check for absolute path
        has_absolute_path = path_elem is not None and path_elem.get('Value', '')

        # Check for relative path (RelativePath elements + Name)
        has_relative_path = (has_relative_elem is not None and
                            has_relative_elem.get('Value') == 'true' and
                            name_elem is not None and
                            name_elem.get('Value', '') != '')

        if not has_absolute_path and not has_relative_path:
            print("⚠️  Empty pad (no sample path) - skipping")
            return False

        for child in simpler_file_ref:
            drumcell_child = drumcell_file_ref.find(child.tag)
            if drumcell_child is not None:
                copy_element_attributes(child, drumcell_child)

    # Copy other SampleRef attributes
    for tag in ['LastModDate', 'SampleUsageHint', 'DefaultDuration', 'DefaultSampleRate']:
        simpler_elem = simpler_ref.find(tag)
        drumcell_elem = drumcell_ref.find(tag)
        if simpler_elem is not None and drumcell_elem is not None:
            copy_element_attributes(simpler_elem, drumcell_elem)

    # Print sample name (from Path or Name element)
    sample_name = "unknown"
    if path_elem is not None and path_elem.get('Value', ''):
        from pathlib import Path
        sample_name = Path(path_elem.get('Value')).name
    elif name_elem is not None:
        sample_name = name_elem.get('Value', 'unknown')

    print(f"✓ Copied sample: {sample_name}")
    return True


def map_parameter(simpler_root, drumcell_root, simpler_path, drumcell_path, scale_fn=None):
    """Map a parameter from Simpler to DrumCell with optional scaling"""
    simpler_elem = simpler_root.find(simpler_path)
    drumcell_elem = drumcell_root.find(drumcell_path)

    if simpler_elem is not None and drumcell_elem is not None:
        # Try both 'Manual' and 'Value' attributes (Simpler uses 'Value')
        value = simpler_elem.get('Manual') or simpler_elem.get('Value')
        if value is not None:
            if scale_fn:
                value = str(scale_fn(float(value)))
            # DrumCell stores values in the 'Value' attribute of the <Manual> element
            drumcell_elem.set('Value', str(value))
            return True
    return False


def map_basic_parameters(simpler_root, drumcell_root):
    """Map basic parameters from Simpler to DrumCell"""
    mappings = [
        # (simpler_path, drumcell_path, scale_function)
        ('.//Pitch/TransposeKey/Manual', './/Voice_Transpose/Manual', None),
        ('.//Pitch/TransposeFine/Manual', './/Voice_Detune/Manual', lambda x: x / 100.0),  # Cents to semitones
        ('.//VolumeAndPan/Volume/Manual', './/Volume/Manual', None),
        ('.//VolumeAndPan/Panorama/Manual', './/Pan/Manual', None),
        ('.//VolumeAndPan/VolumeVelScale/Manual', './/Voice_VelocityToVolume/Manual', None),
        ('.//LoopModulators/SampleStart/Manual', './/Voice_PlaybackStart/Manual', None),
        ('.//LoopModulators/SampleLength/Manual', './/Voice_PlaybackLength/Manual', None),
    ]

    print("\n📋 Mapping basic parameters:")
    for simpler_path, drumcell_path, scale_fn in mappings:
        if map_parameter(simpler_root, drumcell_root, simpler_path, drumcell_path, scale_fn):
            param_name = drumcell_path.split('/')[-2]
            print(f"  ✓ {param_name}")


def map_envelope(simpler_root, drumcell_root):
    """Map Simpler's complex envelope to DrumCell's simple AHDM envelope"""
    print("\n🎚️  Mapping envelope:")

    # Simpler uses milliseconds in VolumeAndPan/Envelope
    # DrumCell uses seconds in Voice_Envelope_*

    # Attack: Convert from ms to seconds
    attack_elem = simpler_root.find('.//VolumeAndPan/Envelope/AttackTime/Manual')
    if attack_elem is not None:
        attack_ms = float(attack_elem.get('Value'))
        attack_sec = attack_ms / 1000.0
        # Clamp to DrumCell's range (0.0001 - 20 seconds)
        attack_sec = max(0.0001, min(20.0, attack_sec))
        drumcell_root.find('.//Voice_Envelope_Attack/Manual').set('Value', str(attack_sec))
        print(f"  ✓ Attack: {attack_ms}ms → {attack_sec}s")

    # Decay: Ableton's logic depends on PlaybackMode
    # PlaybackMode 1 = One-Shot: Uses a default decay of 1 second
    # PlaybackMode 0 = Classic: Uses the ADSR envelope
    playback_mode_elem = simpler_root.find('.//Globals/PlaybackMode')
    playback_mode = 0
    if playback_mode_elem is not None:
        playback_mode = int(playback_mode_elem.get('Value'))

    if playback_mode == 1:
        # One-Shot mode: Ableton uses default decay of 1 second
        decay_sec = 1.0
        drumcell_root.find('.//Voice_Envelope_Decay/Manual').set('Value', str(decay_sec))
        print(f"  ✓ Decay: {decay_sec}s (One-Shot mode default)")
    else:
        # Classic mode: Use Simpler's Decay or Release time
        sustain_elem = simpler_root.find('.//VolumeAndPan/Envelope/SustainLevel/Manual')
        release_elem = simpler_root.find('.//VolumeAndPan/Envelope/ReleaseTime/Manual')
        decay_elem = simpler_root.find('.//VolumeAndPan/Envelope/DecayTime/Manual')

        sustain_level = 1.0
        if sustain_elem is not None:
            sustain_level = float(sustain_elem.get('Value'))

        # If sustain is at max, use release time as decay
        if release_elem is not None and sustain_level >= 0.99:
            release_ms = float(release_elem.get('Value'))
            decay_sec = release_ms / 1000.0
            # Clamp to DrumCell's range (0.001 - 60 seconds)
            decay_sec = max(0.001, min(60.0, decay_sec))
            drumcell_root.find('.//Voice_Envelope_Decay/Manual').set('Value', str(decay_sec))
            print(f"  ✓ Decay: {release_ms}ms (from Release) → {decay_sec}s")
        elif decay_elem is not None:
            decay_ms = float(decay_elem.get('Value'))
            decay_sec = decay_ms / 1000.0
            # Clamp to DrumCell's range (0.001 - 60 seconds)
            decay_sec = max(0.001, min(60.0, decay_sec))
            drumcell_root.find('.//Voice_Envelope_Decay/Manual').set('Value', str(decay_sec))
            print(f"  ✓ Decay: {decay_ms}ms → {decay_sec}s")

    # Hold: Use Ableton's exact value
    hold_sec = 0.3000001013  # Matches Ableton's default
    drumcell_root.find('.//Voice_Envelope_Hold/Manual').set('Value', str(hold_sec))
    print(f"  ✓ Hold: {hold_sec}s")

    # Mode: 0 = Trigger, 1 = Gate
    # Ableton uses Trigger (0) mode - the sound decays naturally
    mode = 0
    drumcell_root.find('.//Voice_Envelope_Mode/Manual').set('Value', str(mode))
    mode_name = "Trigger"
    print(f"  ✓ Mode: {mode_name}")


def map_filter(simpler_root, drumcell_root):
    """Map filter settings if Simpler's filter is enabled"""
    # Note: Simpler's filter is in a Slot, which can contain various filter devices
    # DrumCell has a simple built-in filter
    # Ableton keeps filter on by default even if Simpler's filter is off

    filter_on = simpler_root.find('.//Filter/IsOn/Manual')
    if filter_on is not None and filter_on.get('Value') == 'true':
        print("\n🔊 Filter: ON (with DrumCell defaults)")
        # DrumCell filter is already on in the template
    else:
        print("\n🔊 Filter: ON (DrumCell default, fully open)")
        # Keep filter on, it's fully open by default (frequency at max)


def simpler_to_drumcell(simpler_xml):
    """Convert Simpler XML to DrumCell XML. Returns None if conversion should be skipped."""
    print("\n" + "="*60)
    print("🔄 Converting Simpler → DrumCell")
    print("="*60)

    simpler_root = ET.fromstring(simpler_xml)
    drumcell_root = create_drumcell_template()

    # Perform mappings
    sample_copied = copy_sample_reference(simpler_root, drumcell_root)

    # If sample copy failed (empty pad), skip this conversion
    if sample_copied is False:
        return None

    map_basic_parameters(simpler_root, drumcell_root)
    map_envelope(simpler_root, drumcell_root)
    map_filter(simpler_root, drumcell_root)

    print("\n" + "="*60)
    print("✅ Conversion complete")
    print("="*60 + "\n")

    return ET.tostring(drumcell_root, encoding='unicode', xml_declaration=True)


def main():
    if len(sys.argv) != 3:
        print("Usage: simpler_to_drumcell.py <input_simpler.adv> <output_drumcell.adv>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Decode Simpler
    print(f"📖 Reading: {input_path.name}")
    simpler_xml = decode_adg(input_path)

    # Convert
    drumcell_xml = simpler_to_drumcell(simpler_xml)

    # Encode DrumCell
    print(f"💾 Writing: {output_path.name}")
    encode_adg(drumcell_xml, output_path)

    print(f"\n✨ Success! Created: {output_path}")


if __name__ == '__main__':
    main()
