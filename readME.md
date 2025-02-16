# Ableton Device File Processor
## Technical Documentation

## Overview
The Ableton Device File Processor is a Python-based system for creating and modifying Ableton Live drum racks (.adg) and sampler instruments. It provides several specialized scripts for different use cases.

## Features

### 1. Native Instruments Expansion Processing
- **Standard Drum Racks** (`drum_rack/main.py`, `drum_rack/meta_main.py`)
  - Creates organized drum racks with consistent pad layout
  - Groups samples by type (kicks, snares, hi-hats, etc.)
  - Processes single or multiple expansions

- **Percussion-Only Racks** (`drum_rack/main_percussion.py`, `drum_rack/meta_main_percussion.py`)
  - Creates 32-pad racks from percussion samples only
  - Organizes samples alphabetically
  - Names racks based on expansion name

### 2. Generic Sample Processing
- **Single Folder Processing** (`drum_rack/main_generic.py`)
  - Creates 32-pad racks from any folder containing audio files
  - Organizes samples alphabetically
  - Names racks based on folder structure

- **Recursive Folder Processing** (`drum_rack/meta_main_folders.py`)
  - Processes entire folder hierarchies
  - Maintains folder structure in output
  - Creates drum racks for each folder containing samples

### 3. Sampler Instrument Creation
- **Multi-Sample Instruments** (`sampler/main_sampler.py`)
  - Creates sampler instruments with samples mapped chromatically
  - Starts mapping from C2 (MIDI note 48)
  - Supports WAV, AIF, and AIFF files
  - Creates multiple instruments when more than 32 samples
  - Fills partial instruments with samples from previous rack
  - Maintains consistent 32-sample layouts
  - Preserves folder structure in output

### 4. Macro Control Processing
- **Batch Macro Setting** (`drum_rack/set_macro.py`)
  - Sets macro values across multiple drum racks
  - Processes files recursively in folders
  - Updates both default and manual macro values
  - Supports all 127 macro controls

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd ableton-device-processor
```

2. Ensure Python 3.6+ is installed

## Usage Examples

### 1. Native Instruments Expansions

```bash
# Process single expansion
python3 scripts/drum_rack/main.py input_rack.adg "/path/to/expansion/library"

# Process all expansions
python3 scripts/drum_rack/meta_main.py input_rack.adg "/path/to/expansions/folder"
```

### 2. Generic Sample Processing

```bash
# Process single sample folder
python3 scripts/drum_rack/main_generic.py input_rack.adg "/path/to/samples/folder"

# Process folder hierarchy
python3 scripts/drum_rack/meta_main_folders.py input_rack.adg "/path/to/base/folder"
```

### 3. Sampler Instrument Creation

```bash
# Create sampler instruments from folder
python3 scripts/sampler/main_sampler.py sampler-rack.adg "/path/to/samples/folder"

# Example with specific output folder
python3 scripts/sampler/main_sampler.py sampler-rack.adg "/Samples/Pianos" --output-folder "/Output/Pianos"
```

### 4. Macro Control Setting

```bash
# Set macro value in all racks in a folder
python3 scripts/drum_rack/set_macro.py "/path/to/racks/folder" [macro_number] [value]
```

## Output Structure

### For Sampler Instruments
```
output-sampler/
├── Category/
│   ├── Subcategory/
│   │   ├── Subcategory 01.adg  # First 32 samples
│   │   ├── Subcategory 02.adg  # Next 32 samples
│   │   └── Subcategory 03.adg  # Remaining samples (filled to 32)
│   └── ...
└── ...
```

### For Drum Racks
```
Output/
├── Category/
│   ├── Subcategory/
│   │   ├── Subcategory 01.adg
│   │   └── Subcategory 02.adg
│   └── ...
└── ...
```

## Script Details

### Main Scripts
- **main.py**: Single expansion processor
- **main_percussion.py**: Single expansion percussion processor
- **main_generic.py**: Single folder processor
- **main_sampler.py**: Sampler instrument creator
- **meta_main.py**: Multi-expansion processor
- **meta_main_percussion.py**: Multi-expansion percussion processor
- **meta_main_folders.py**: Recursive folder processor
- **set_macro.py**: Macro value processor

### Support Scripts
- **utils/decoder.py**: ADG file decoder
- **utils/encoder.py**: ADG file encoder
- **drum_rack/transformer.py**: Drum rack XML transformer
- **sampler/transformer.py**: Sampler XML transformer

## Features by Script

### main_sampler.py
- Creates sampler instruments from audio folders
- Maps samples chromatically from C2
- Supports WAV, AIF, and AIFF files
- Creates multiple instruments for >32 samples
- Fills partial instruments with previous samples
- Maintains folder structure in output
- Reports processing status and sample counts
- Validates audio files before processing

## Error Handling
- Validates input files and folders
- Checks for valid audio files
- Reports invalid or corrupted files
- Maintains processing on errors
- Provides detailed error messages

## Contributing
To contribute to this project:
1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Submit a pull request

## License
This project is provided under the MIT License.