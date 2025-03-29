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
        
        # Find the MultiSamplePart element
        sample_part = root.find(".//MultiSamplePart")
        if sample_part is None:
            raise ValueError("Could not find MultiSamplePart element")
            
        # Find the sample reference
        sample_ref = sample_part.find(".//SampleRef/FileRef")
        if sample_ref is None:
            raise ValueError("Could not find SampleRef/FileRef element")
            
        # Convert to absolute path
        abs_path = str(Path(sample_path).resolve())
        
        # Update the absolute path
        path_elem = sample_ref.find("Path")
        if path_elem is not None:
            path_elem.set('Value', abs_path)
            
        # Update the relative path
        rel_path_elem = sample_ref.find("RelativePath")
        if rel_path_elem is not None:
            # For now, just use the filename as the relative path
            # This ensures Ableton can find it via absolute path
            rel_path = "Samples/" + Path(sample_path).name
            rel_path_elem.set('Value', rel_path)
            
        # Update RelativePathType to use absolute path (Value="0")
        path_type_elem = sample_ref.find("RelativePathType")
        if path_type_elem is not None:
            path_type_elem.set('Value', "0")
            
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