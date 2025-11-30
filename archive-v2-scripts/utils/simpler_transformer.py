import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

def transform_simpler_xml(xml_content: str, sample_path: str) -> str:
    """
    Transform the XML content by replacing the sample path in a Simpler device
    
    Args:
        xml_content (str): Original XML content
        sample_path (str): New sample path to use
        
    Returns:
        str: Transformed XML content
    """
    try:
        # Parse the XML
        root = ET.fromstring(xml_content)
        
        # Find the MultiSampleMap element
        multi_sample_map = root.find(".//MultiSampleMap")
        if multi_sample_map is None:
            raise ValueError("Could not find MultiSampleMap element")
            
        # Clear existing SampleParts
        sample_parts = multi_sample_map.find("SampleParts")
        if sample_parts is not None:
            sample_parts.clear()
            
        # Create new MultiSamplePart with required attributes
        multi_sample_part = ET.SubElement(sample_parts, "MultiSamplePart")
        multi_sample_part.set('Id', '0')
        multi_sample_part.set('InitUpdateAreSlicesFromOnsetsEditableAfterRead', 'false')
        multi_sample_part.set('HasImportedSlicePoints', 'true')
        multi_sample_part.set('NeedsAnalysisData', 'true')
        
        # Add required MultiSamplePart elements
        lom_id = ET.SubElement(multi_sample_part, "LomId")
        lom_id.set('Value', '0')
        
        name = ET.SubElement(multi_sample_part, "Name")
        name.set('Value', Path(sample_path).stem)
        
        selection = ET.SubElement(multi_sample_part, "Selection")
        selection.set('Value', 'true')
        
        is_active = ET.SubElement(multi_sample_part, "IsActive")
        is_active.set('Value', 'true')
        
        solo = ET.SubElement(multi_sample_part, "Solo")
        solo.set('Value', 'false')
        
        # Add key range
        key_range = ET.SubElement(multi_sample_part, "KeyRange")
        for elem in ['Min', 'Max', 'CrossfadeMin', 'CrossfadeMax']:
            e = ET.SubElement(key_range, elem)
            e.set('Value', '0' if elem in ['Min', 'CrossfadeMin'] else '127')
            
        # Add velocity range
        velocity_range = ET.SubElement(multi_sample_part, "VelocityRange")
        for elem in ['Min', 'Max', 'CrossfadeMin', 'CrossfadeMax']:
            e = ET.SubElement(velocity_range, elem)
            e.set('Value', '1' if elem in ['Min', 'CrossfadeMin'] else '127')
            
        # Add selector range
        selector_range = ET.SubElement(multi_sample_part, "SelectorRange")
        for elem in ['Min', 'Max', 'CrossfadeMin', 'CrossfadeMax']:
            e = ET.SubElement(selector_range, elem)
            e.set('Value', '0' if elem in ['Min', 'CrossfadeMin'] else '127')
            
        # Add other required elements
        root_key = ET.SubElement(multi_sample_part, "RootKey")
        root_key.set('Value', '60')
        
        detune = ET.SubElement(multi_sample_part, "Detune")
        detune.set('Value', '0')
        
        tune_scale = ET.SubElement(multi_sample_part, "TuneScale")
        tune_scale.set('Value', '100')
        
        panorama = ET.SubElement(multi_sample_part, "Panorama")
        panorama.set('Value', '0')
        
        volume = ET.SubElement(multi_sample_part, "Volume")
        volume.set('Value', '1')
        
        link = ET.SubElement(multi_sample_part, "Link")
        link.set('Value', 'false')
        
        # Create SampleRef with all required elements
        sample_ref = ET.SubElement(multi_sample_part, "SampleRef")
        
        # Create FileRef with all required elements
        file_ref = ET.SubElement(sample_ref, "FileRef")
        
        # Convert to absolute path
        abs_path = str(Path(sample_path).resolve())
        
        # Add Path element
        path_elem = ET.SubElement(file_ref, "Path")
        path_elem.set('Value', abs_path)
        
        # Add RelativePath element
        rel_path_elem = ET.SubElement(file_ref, "RelativePath")
        rel_path = "Samples/" + Path(sample_path).name
        rel_path_elem.set('Value', rel_path)
        
        # Add RelativePathType element
        path_type_elem = ET.SubElement(file_ref, "RelativePathType")
        path_type_elem.set('Value', "0")  # Use absolute path
        
        # Add Type element
        type_elem = ET.SubElement(file_ref, "Type")
        type_elem.set('Value', "1")  # Sample file
        
        # Add LivePackName and LivePackId
        live_pack_name = ET.SubElement(file_ref, "LivePackName")
        live_pack_name.set('Value', '')
        
        live_pack_id = ET.SubElement(file_ref, "LivePackId")
        live_pack_id.set('Value', '')
        
        # Add OriginalFileSize and OriginalCrc
        original_file_size = ET.SubElement(file_ref, "OriginalFileSize")
        original_file_size.set('Value', '0')
        
        original_crc = ET.SubElement(file_ref, "OriginalCrc")
        original_crc.set('Value', '0')
        
        # Add LastModDate
        last_mod_date = ET.SubElement(sample_ref, "LastModDate")
        last_mod_date.set('Value', '0')
        
        # Add SourceContext
        source_context = ET.SubElement(sample_ref, "SourceContext")
        
        # Add SampleUsageHint
        sample_usage_hint = ET.SubElement(sample_ref, "SampleUsageHint")
        sample_usage_hint.set('Value', '0')
        
        # Add DefaultDuration and DefaultSampleRate
        default_duration = ET.SubElement(sample_ref, "DefaultDuration")
        default_duration.set('Value', '0')
        
        default_sample_rate = ET.SubElement(sample_ref, "DefaultSampleRate")
        default_sample_rate.set('Value', '48000')
        
        # Add SamplesToAutoWarp
        samples_to_auto_warp = ET.SubElement(sample_ref, "SamplesToAutoWarp")
        samples_to_auto_warp.set('Value', '1')
        
        print(f"Updated sample path to: {abs_path}")
        print(f"Set relative path to: {rel_path}")
        
        # Convert back to string with the XML declaration
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    except Exception as e:
        raise Exception(f"Error transforming Simpler XML: {e}")

def get_simpler_info(xml_content: str) -> dict:
    """
    Get information about the sample in a Simpler device
    
    Args:
        xml_content (str): XML content to analyze
        
    Returns:
        dict: Dictionary containing info about the sample
    """
    root = ET.fromstring(xml_content)
    info = {}
    
    # Find the sample reference
    sample_ref = root.find(".//MultiSamplePart//SampleRef/FileRef")
    if sample_ref is not None:
        # Get sample path
        path_elem = sample_ref.find("Path")
        if path_elem is not None:
            info['sample_path'] = path_elem.get('Value')
            
        # Get relative path
        rel_path_elem = sample_ref.find("RelativePath")
        if rel_path_elem is not None:
            info['relative_path'] = rel_path_elem.get('Value')
            
        # Get path type
        path_type_elem = sample_ref.find("RelativePathType")
        if path_type_elem is not None:
            info['path_type'] = path_type_elem.get('Value')
            
        # Get sample rate
        sample_rate = root.find(".//MultiSamplePart//SampleRef/DefaultSampleRate")
        if sample_rate is not None:
            info['sample_rate'] = sample_rate.get('Value')
            
        # Get duration
        duration = root.find(".//MultiSamplePart//SampleRef/DefaultDuration")
        if duration is not None:
            info['duration'] = duration.get('Value')
    
    return info 