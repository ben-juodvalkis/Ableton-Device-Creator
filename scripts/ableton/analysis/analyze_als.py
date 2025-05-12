import os
import csv
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
import sys
import logging
from datetime import datetime
import re

# Set up improved logging with error handling
try:
    # Set up initial handlers list with stdout always included
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # We'll determine where to write the log file after we know the target directory
    # For now, configure logging with just console output
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
except Exception as e:
    # Fallback to basic console-only logging if even that fails
    print(f"Could not set up basic logging: {str(e)}")
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )
    logging.warning("Using default logging configuration.")

def find_master_resample_clips(tree):
    """Find all audio clip filenames in tracks named 'Master Resample'."""
    clip_filenames = []
    
    # Search for tracks
    for track in tree.findall(".//AudioTrack"):
        # Check if track name is "Master Resample"
        name = track.find(".//Name/EffectiveName")
        if name is not None and name.get("Value") == "Master Resample":
            logging.debug("Found Master Resample track")
            
            # Search for clips in arrangement view
            for clip in track.findall(".//AudioClip"):
                file_ref = clip.find(".//SampleRef/FileRef")
                if file_ref is not None:
                    path = file_ref.find("Path")
                    if path is not None:
                        # Extract just the filename from the full path
                        filename = os.path.basename(path.get("Value"))
                        clip_filenames.append(filename)
                        logging.debug(f"Found clip: {filename}")
    
    return clip_filenames

def decode_time_signature(value):
    """
    Decode Ableton's numeric time signature value.
    The value appears to be encoded where:
    - 201 = 4/4
    - 202 = 5/4
    - 203 = 6/4
    etc.
    """
    try:
        value = int(value)
        if value >= 201:
            numerator = value - 197  # 201 - 197 = 4 (for 4/4)
            denominator = 4  # Appears to always be 4 in the examples seen
            return f"{numerator}/{denominator}"
    except (ValueError, TypeError):
        pass
    return f"Unknown ({value})"

def sanitize_filename(filename):
    """Remove or replace invalid characters in filename."""
    # Replace invalid characters with underscores
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, '_', filename)

def generate_new_filename(original_name, created_date, tempo, time_signature):
    """Generate new filename with metadata."""
    # Remove .als extension
    base_name = os.path.splitext(original_name)[0]
    
    # Get parent folder's first word
    dir_path = os.path.dirname(original_name)
    parent_folder = os.path.basename(dir_path)
    first_word = parent_folder.split()[0] if parent_folder else ""
    
    # Format creation date
    date_str = datetime.strptime(created_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    
    # Format tempo and time signature
    tempo_str = f"{int(float(tempo))}bpm" if tempo else "unknown-bpm"
    time_sig_str = time_signature.replace('/', '-') if time_signature else "unknown-time"
    
    # Construct new filename
    # Format: ParentWord_OriginalName_YYYY-MM-DD_120bpm_4-4.als
    components = []
    if first_word:
        components.append(first_word)
    components.append(base_name)
    components.append(date_str)
    components.append(tempo_str)
    components.append(time_sig_str)
    
    new_name = "_".join(components) + ".als"
    return sanitize_filename(new_name)

def is_already_renamed(filename):
    """Check if the file appears to have been previously renamed by this script."""
    # Check for our naming pattern: something_YYYY-MM-DD_XXXbpm_X-X.als
    pattern = r'.*_\d{4}-\d{2}-\d{2}_\d+bpm_\d+-\d+\.als$'
    return bool(re.match(pattern, filename))

def extract_project_info(als_path):
    """Extract information from an Ableton Live project file."""
    logging.info(f"Attempting to process file: {als_path}")
    try:
        # Get file system stats
        file_stats = os.stat(als_path)
        
        project_info = {
            'filename': os.path.basename(als_path),
            'time_signature': None,
            'tempo': None,
            'path': als_path,
            'file_size_mb': round(file_stats.st_size / (1024 * 1024), 2),
            'file_created': datetime.fromtimestamp(file_stats.st_birthtime).strftime('%Y-%m-%d %H:%M:%S'),
            'file_modified': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'file_last_accessed': datetime.fromtimestamp(file_stats.st_atime).strftime('%Y-%m-%d %H:%M:%S'),
            'master_resample_clips': []  # New field for Master Resample clip paths
        }
        
        # Read the .als file as gzip
        logging.debug(f"Opening file as gzip: {als_path}")
        with gzip.open(als_path, 'rb') as f:
            xml_content = f.read()
            logging.debug("Successfully read gzipped content")
            
            logging.debug("Parsing XML content")
            tree = ET.fromstring(xml_content)
            
            # Log the root element and its immediate children for debugging
            logging.debug(f"Root element: {tree.tag}")
            for child in tree:
                logging.debug(f"Child element: {child.tag}")
            
            # Find Master Resample clips
            master_resample_clips = find_master_resample_clips(tree)
            project_info['master_resample_clips'] = master_resample_clips
            logging.debug(f"Found {len(master_resample_clips)} Master Resample clips")
            
            # Try all possible time signature locations in order of priority
            time_sig_locations = [
                # First check automation (this is the actual time signature)
                {
                    'path': './/AutomationEnvelopes/Envelopes/AutomationEnvelope[@Id="0"]/Automation/Events/EnumEvent',
                    'source': 'automation',
                    'value_type': 'encoded'
                },
                # Then check project settings
                {
                    'path': './/TimeSignature/Manual/Value',
                    'source': 'project_settings',
                    'value_type': 'encoded'
                },
                # Then check RemoteableTimeSignature structure
                {
                    'path': './/TimeSignature/TimeSignatures/RemoteableTimeSignature',
                    'source': 'RemoteableTimeSignature',
                    'value_type': 'direct'
                }
            ]
            
            for location in time_sig_locations:
                time_sig = tree.find(location['path'])
                if time_sig is not None:
                    logging.debug(f"Found time signature at {location['source']}")
                    
                    if location['value_type'] == 'direct':
                        numerator = time_sig.find('Numerator')
                        denominator = time_sig.find('Denominator')
                        if numerator is not None and denominator is not None:
                            num_val = numerator.get('Value')
                            den_val = denominator.get('Value')
                            if num_val and den_val:
                                time_sig_value = f"{num_val}/{den_val}"
                                # Validate the time signature
                                if num_val != "1" and den_val != "1":  # Skip likely invalid values
                                    logging.debug(f"Found valid time signature: {time_sig_value} (from {location['source']})")
                                    project_info['time_signature'] = time_sig_value
                                    break
                    else:  # encoded value
                        time_sig_value = time_sig.get('Value')
                        if time_sig_value is None:
                            time_sig_value = time_sig.text
                        if time_sig_value:
                            decoded = decode_time_signature(time_sig_value)
                            if not decoded.startswith("Unknown"):  # Skip unknown values
                                logging.debug(f"Found valid time signature: {decoded} (from {location['source']})")
                                project_info['time_signature'] = decoded
                                break
            
            logging.debug("Extracting tempo")
            tempo = tree.find('.//Mixer/Tempo/Manual')
            if tempo is not None:
                project_info['tempo'] = tempo.get('Value')
                logging.debug(f"Found tempo: {project_info['tempo']}")
        
        # Generate new filename
        new_filename = generate_new_filename(
            project_info['filename'],
            project_info['file_created'],
            project_info['tempo'],
            project_info['time_signature']
        )
        
        # Check if file has already been renamed
        if is_already_renamed(project_info['filename']):
            logging.info(f"File appears to be already renamed: {als_path}")
            project_info['new_filename'] = project_info['filename']
            project_info['new_path'] = project_info['path']
        else:
            # Rename the file
            dir_path = os.path.dirname(als_path)
            new_path = os.path.join(dir_path, new_filename)
            
            if als_path != new_path:
                try:
                    os.rename(als_path, new_path)
                    project_info['new_filename'] = new_filename
                    project_info['new_path'] = new_path
                    logging.info(f"Renamed file to: {new_filename}")
                except Exception as e:
                    logging.error(f"Error renaming file {als_path}: {str(e)}")
                    project_info['new_filename'] = project_info['filename']
                    project_info['new_path'] = project_info['path']
            else:
                project_info['new_filename'] = project_info['filename']
                project_info['new_path'] = project_info['path']
        
        logging.info(f"Successfully processed file: {als_path}")
        return project_info
    
    except Exception as e:
        logging.error(f"Error processing {als_path}: {str(e)}", exc_info=True)
        return None

def analyze_projects(root_dir):
    """Recursively analyze all .als files in the directory."""
    # Set up log file in the target directory
    log_file = os.path.join(root_dir, "ableton_analysis.log")
    try:
        # Add a file handler for the target directory
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(file_handler)
        print(f"Logging to: {log_file}")
    except (PermissionError, OSError) as e:
        logging.warning(f"Could not write log file to target directory: {str(e)}")
        logging.warning("Continuing with console logging only")
    
    logging.info(f"Starting analysis of directory: {root_dir}")
    logging.info(f"Directory exists: {os.path.exists(root_dir)}")
    logging.info(f"Directory is readable: {os.access(root_dir, os.R_OK)}")
    
    all_projects = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip 'Backup' folders
        if 'Backup' in dirnames:
            dirnames.remove('Backup')
            logging.debug(f"Skipping Backup folder in: {dirpath}")
        
        logging.debug(f"Scanning directory: {dirpath}")
        logging.debug(f"Found files: {filenames}")
        
        for filename in filenames:
            if filename.endswith('.als'):
                full_path = os.path.join(dirpath, filename)
                logging.info(f"Processing Ableton project: {full_path}")
                project_info = extract_project_info(full_path)
                if project_info:
                    all_projects.append(project_info)
                    logging.debug(f"Added project info for: {filename}")
    
    logging.info(f"Total projects found: {len(all_projects)}")
    
    if all_projects:
        output_csv = os.path.join(root_dir, 'ableton_projects_analysis.csv')
        logging.info(f"Writing results to: {output_csv}")
        
        try:
            fieldnames = all_projects[0].keys()
            with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_projects)
            logging.info("Successfully wrote CSV file")
        except Exception as e:
            logging.error(f"Error writing CSV: {str(e)}", exc_info=True)
    else:
        logging.warning("No project files were successfully analyzed.")

if __name__ == "__main__":
    logging.info("Script started")
    logging.info(f"Arguments received: {sys.argv}")
    
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
        logging.info(f"Processing folder: {folder_path}")
        analyze_projects(folder_path)
    else:
        logging.error("No folder path provided")
        print("Please provide a folder path as an argument.")
    
    logging.info("Script completed")