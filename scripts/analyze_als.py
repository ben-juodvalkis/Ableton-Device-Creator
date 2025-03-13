"""
# Ableton Project Analyzer

This script analyzes Ableton Live project files (.als) and generates a CSV report containing
project metadata and musical information. It also renames the files to include creation date,
tempo, and time signature.

## Features
- Recursively scans directories for .als files
- Extracts musical information (tempo, time signature)
- Includes file metadata (creation date, size, etc.)
- Renames files with format: original_name [YYYY-MM-DD][BPM][TIME_SIG].als
- Outputs results to a CSV file in the input directory
- Detailed logging to Desktop for troubleshooting

## Installation

1. Save this script to:
   `/Users/Shared/DevWork/GitHub/Maestro-Modern/scripts/analyze_als.py`

2. Make the script executable:
   ```bash
   chmod +x /Users/Shared/DevWork/GitHub/Maestro-Modern/scripts/analyze_als.py
   ```

3. Set up the macOS Quick Action:
   a. Open Automator
   b. Create New > Quick Action
   c. Configure workflow settings:
      - Workflow receives: folders
      - in: Finder
   d. Add "Run Shell Script" action
   e. Configure shell script:
      - Shell: /bin/bash
      - Pass input: as arguments
      - Script content:
        ```bash
        /usr/bin/python3 /Users/Shared/DevWork/GitHub/Maestro-Modern/scripts/analyze_als.py "$1"
        ```
   f. Save as "Analyze Ableton Projects"

## Usage

1. Right-click any folder containing Ableton projects
2. Select Quick Actions > Analyze Ableton Projects
3. Find the generated CSV file in the selected folder
4. Check ~/Desktop/ableton_analysis.log for detailed logs

## Output Format

The CSV includes the following columns:
- filename: Name of the .als file
- path: Full path to the file
- file_size_mb: Size of the file in MB
- file_created: Creation timestamp
- file_modified: Last modified timestamp
- file_last_accessed: Last accessed timestamp
- time_signature: Musical time signature (e.g., "4/4")
- tempo: Project tempo in BPM

## Troubleshooting

If the script isn't working:
1. Check the log file at ~/Desktop/ableton_analysis.log
2. Verify Python 3 is installed
3. Ensure the script has execution permissions
4. Check folder permissions
"""

import os
import csv
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
import sys
import logging
from datetime import datetime
import re

# Set up logging
log_dir = os.path.expanduser("~/Desktop")
log_file = os.path.join(log_dir, "ableton_analysis.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

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
        }
        
        # Read the .als file as gzip
        logging.debug(f"Opening file as gzip: {als_path}")
        with gzip.open(als_path, 'rb') as f:
            xml_content = f.read()
            logging.debug("Successfully read gzipped content")
            
            logging.debug("Parsing XML content")
            tree = ET.fromstring(xml_content)
            
            # Extract time signature from the automation events
            logging.debug("Extracting time signature")
            time_sig = tree.find('.//AutomationEnvelopes/Envelopes/AutomationEnvelope[@Id="0"]/Automation/Events/EnumEvent')
            if time_sig is not None:
                time_sig_value = time_sig.get('Value')
                project_info['time_signature'] = decode_time_signature(time_sig_value)
                logging.debug(f"Found time signature value: {time_sig_value} -> {project_info['time_signature']}")
            
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