# Ableton Device File Processor
## Technical Documentation

## Overview
The Ableton Device File Processor is a Python-based system for manipulating Ableton Live device group (.adg) files. It specializes in modifying Drum Rack presets, particularly for updating sample paths across multiple drum pads while preserving all other settings.

## System Architecture

### Module Structure
```
ableton-device-processor/
├── scripts/
│   ├── main.py           # Main script orchestrating the process
│   ├── decoder.py        # ADG file decoder
│   ├── transformer.py    # XML content transformer
│   └── encoder.py        # ADG file encoder
```

### Process Flow
1. Decode: ADG → XML
2. Transform: Modify XML content (sample paths)
3. Encode: XML → ADG

## Module Documentation

### decoder.py
The decoder module handles the extraction and decompression of ADG files.

#### Functions
```python
decode_adg(adg_path: Path) -> str
```
- **Purpose**: Decodes a gzipped ADG file into XML content
- **Parameters**:
  - `adg_path`: Path object pointing to the input ADG file
- **Returns**: String containing the decoded XML content
- **Raises**: Exception if decoding fails
- **Example**:
```python
from pathlib import Path
from decoder import decode_adg

xml_content = decode_adg(Path("my_device.adg"))
```

### transformer.py
The transformer module handles XML modifications, specifically focusing on updating sample paths in Drum Rack devices.

#### Functions

```python
transform_xml(xml_content: str, new_sample_path: str = "/path/to/default/sample.wav") -> str
```
- **Purpose**: Transforms XML content by replacing sample paths in all DrumCell devices
- **Parameters**:
  - `xml_content`: String containing the XML to transform
  - `new_sample_path`: Path to the new sample file (optional, has default)
- **Returns**: String containing the transformed XML
- **Behavior**: 
  - Processes all drum pads in the rack
  - Updates both absolute and relative sample paths
  - Preserves all other device settings
  - Reports number of samples replaced
- **Example**:
```python
from transformer import transform_xml

transformed_xml = transform_xml(xml_content, "/path/to/new/sample.wav")
```

```python
get_drum_cell_info(xml_content: str) -> list
```
- **Purpose**: Analyzes and reports information about all drum cells in the rack
- **Parameters**:
  - `xml_content`: String containing the XML to analyze
- **Returns**: List of dictionaries containing info about each drum cell
- **Information Retrieved**:
  - MIDI note assignments
  - Current sample paths
- **Example**:
```python
from transformer import get_drum_cell_info

cells_info = get_drum_cell_info(xml_content)
for cell in cells_info:
    print(f"MIDI Note: {cell['midi_note']}, Sample: {cell['sample_path']}")
```

### encoder.py
The encoder module handles compression and creation of ADG files.

#### Functions
```python
encode_adg(xml_content: str, output_path: Path) -> None
```
- **Purpose**: Encodes XML content into a gzipped ADG file
- **Parameters**:
  - `xml_content`: String containing the XML to encode
  - `output_path`: Path object for the output ADG file
- **Example**:
```python
from pathlib import Path
from encoder import encode_adg

encode_adg(transformed_xml, Path("output_device.adg"))
```

## Usage

### Basic Usage
```bash
python3 scripts/main.py input_file.adg output_file.adg
```

### Command Line Arguments
- `input_file`: Path to the input ADG file
- `output_file`: Path where the processed ADG file should be saved

### Example Workflow
```bash
# Process a drum rack, replacing all samples with the default sample
python3 scripts/main.py my_drum_rack.adg modified_drum_rack.adg
```

## Common Use Cases

### 1. Replacing All Samples in a Drum Rack
```python
# In transformer.py
def transform_xml(xml_content: str) -> str:
    root = ET.fromstring(xml_content)
    for file_ref in root.findall(".//UserSample/Value/SampleRef/FileRef"):
        path_elem = file_ref.find("Path")
        if path_elem is not None:
            path_elem.set('Value', "/path/to/new/sample.wav")
    return ET.tostring(root, encoding='unicode', xml_declaration=True)
```

### 2. Analyzing Drum Rack Structure
```python
# Get information about all drum cells
cells_info = get_drum_cell_info(xml_content)
for cell in cells_info:
    print(f"Found drum cell: MIDI Note {cell['midi_note']}")
```

## Error Handling

### Common Issues and Solutions

1. **File Access Issues**
   - Verify file permissions
   - Check file paths are correct
   - Ensure the ADG file is not currently in use by Ableton Live

2. **XML Parsing Errors**
   - Verify ADG file is valid
   - Check for XML structure integrity
   - Ensure proper encoding (UTF-8)

3. **Sample Path Issues**
   - Verify new sample paths exist
   - Check for proper path formatting
   - Ensure consistent path separators

### Debug Tips
- Use `get_drum_cell_info()` to inspect drum rack structure
- Check console output for number of replaced samples
- Verify file paths are correctly formatted for your OS

## Best Practices

### Working with Sample Paths
- Use absolute paths when possible
- Maintain consistent path separator style
- Verify sample files exist before processing
- Consider using sample path validation

### File Handling
- Always use Path objects for file paths
- Handle file operations with try/except blocks
- Verify input files before processing
- Create backups before modification

## Contributing
To contribute to this project:
1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Submit a pull request

## License
This project is provided under the MIT License.