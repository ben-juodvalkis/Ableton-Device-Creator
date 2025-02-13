# Ableton Device File Processor
## Technical Documentation

## Overview
The Ableton Device File Processor is a Python-based system for manipulating Ableton Live device group (.adg) files. It provides a modular framework for decoding, transforming, and re-encoding ADG files, allowing for programmatic modifications to Ableton Live devices.

## System Architecture

### Module Structure
```
ableton-device-processor/
├── main.py           # Main script orchestrating the process
├── decoder.py        # ADG file decoder
├── transformer.py    # XML content transformer
└── encoder.py        # ADG file encoder
```

### Process Flow
1. Decode: ADG → XML
2. Transform: Modify XML content
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
The transformer module handles XML content modifications.

#### Functions
```python
transform_xml(xml_content: str) -> str
```
- **Purpose**: Transforms XML content according to specified rules
- **Parameters**:
  - `xml_content`: String containing the XML to transform
- **Returns**: String containing the transformed XML
- **Raises**: Exception if transformation fails
- **Example**:
```python
from transformer import transform_xml

transformed_xml = transform_xml(xml_content)
```

#### Adding Custom Transformations
To add custom transformations, modify the `transform_xml` function:

```python
def transform_xml(xml_content: str) -> str:
    root = ET.fromstring(xml_content)
    
    # Example: Change sample path
    for sample_ref in root.findall(".//SampleRef/FileRef/Path"):
        sample_ref.set('Value', '/new/path/to/sample.wav')
    
    return ET.tostring(root, encoding='unicode', xml_declaration=True)
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
- **Raises**: Exception if encoding fails
- **Example**:
```python
from pathlib import Path
from encoder import encode_adg

encode_adg(transformed_xml, Path("output_device.adg"))
```

### main.py
The main script orchestrates the entire process.

#### Usage
```bash
python main.py input_file.adg output_file.adg
```

#### Command Line Arguments
- `input_file`: Path to the input ADG file
- `output_file`: Path where the processed ADG file should be saved

#### Example
```bash
python main.py "empty_drum_rack.adg" "modified_drum_rack.adg"
```

## Error Handling
All modules include error handling with specific error messages:
- File not found errors
- XML parsing errors
- Encoding/decoding errors
- Transformation errors

## Best Practices

### Working with XML Content
- Always validate XML structure before transforming
- Use XML namespaces correctly
- Preserve XML declaration and encoding
- Maintain proper indentation

### File Handling
- Use Path objects for file paths
- Close file handles properly
- Handle encoding/decoding exceptions
- Verify file existence before processing

## Common Use Cases

### 1. Modifying Sample Paths
```python
def transform_xml(xml_content: str) -> str:
    root = ET.fromstring(xml_content)
    for path in root.findall(".//FileRef/Path"):
        current_path = path.get('Value')
        new_path = current_path.replace('/old/path', '/new/path')
        path.set('Value', new_path)
    return ET.tostring(root, encoding='unicode', xml_declaration=True)
```

### 2. Changing Device Parameters
```python
def transform_xml(xml_content: str) -> str:
    root = ET.fromstring(xml_content)
    for param in root.findall(".//Manual"):
        if param.get('Value'):
            param.set('Value', "0.5")  # Set new value
    return ET.tostring(root, encoding='unicode', xml_declaration=True)
```

## Troubleshooting

### Common Issues and Solutions

1. **Invalid ADG File**
   - Verify file is a valid Ableton device group file
   - Check file permissions
   - Ensure file isn't corrupted

2. **XML Parsing Errors**
   - Verify XML structure is valid
   - Check for proper XML declaration
   - Ensure correct encoding (UTF-8)

3. **Transformation Errors**
   - Verify XPath queries
   - Check XML namespace usage
   - Validate element/attribute modifications

### Debug Tips
- Use print statements to inspect XML content
- Validate XML structure after transformations
- Check file encodings

## Contributing
To contribute to this project:
1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Submit a pull request

## License
This project is provided under the MIT License.