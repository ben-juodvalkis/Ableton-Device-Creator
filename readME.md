# Ableton Device File Processor
## Technical Documentation

## Overview
The Ableton Device File Processor is a Python-based system for creating and modifying Ableton Live drum racks (.adg). It provides several specialized scripts for different use cases.

## Features

### 1. Native Instruments Expansion Processing
- **Standard Drum Racks** (`main.py`, `meta_main.py`)
  - Creates organized drum racks with consistent pad layout
  - Groups samples by type (kicks, snares, hi-hats, etc.)
  - Processes single or multiple expansions

- **Percussion-Only Racks** (`main_percussion.py`, `meta_main_percussion.py`)
  - Creates 32-pad racks from percussion samples only
  - Organizes samples alphabetically
  - Names racks based on expansion name

### 2. Generic Sample Processing
- **Single Folder Processing** (`main_generic.py`)
  - Creates 32-pad racks from any folder containing .wav files
  - Organizes samples alphabetically
  - Names racks based on folder structure

- **Recursive Folder Processing** (`meta_main_folders.py`)
  - Processes entire folder hierarchies
  - Maintains folder structure in output
  - Creates drum racks for each folder containing samples

### 3. Macro Control Processing
- **Batch Macro Setting** (`set_macro.py`)
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
python3 scripts/main.py input_rack.adg "/path/to/expansion/library"

# Process all expansions
python3 scripts/meta_main.py input_rack.adg "/path/to/expansions/folder"

# Process percussion from all expansions
python3 scripts/meta_main_percussion.py input_rack.adg "/path/to/expansions/folder"
```

### 2. Generic Sample Processing

```bash
# Process single sample folder
python3 scripts/main_generic.py input_rack.adg "/path/to/samples/folder"

# Process folder hierarchy
python3 scripts/meta_main_folders.py input_rack.adg "/path/to/base/folder"
```

### 3. Macro Control Setting

```bash
# Set macro value in all racks in a folder
python3 scripts/set_macro.py "/path/to/racks/folder" [macro_number] [value]

# Examples:
python3 scripts/set_macro.py "/Music/Drum Racks" 10 63
python3 scripts/set_macro.py "/Music/FX Racks" 1 127
```

### Example Use Cases

#### Processing Vocal Libraries
```bash
# Process breath samples from 8dio libraries
python3 scripts/main_generic.py input_rack.adg "/Users/Shared/Music/Soundbanks/8dio/8Dio_Francesca/1_Francesca_Core_Library/samples/Breath"
```

#### Processing Sound Effects
```bash
# Process entire sound effects library
python3 scripts/meta_main_folders.py input_rack.adg "/Users/Shared/Music/Samples Organized/Atmospheres"
```

#### Updating Macro Controls
```bash
# Set reverb macro in all atmosphere racks
python3 scripts/set_macro.py "/Music/FX/Atmosphere" 10 63
```

## Output Structure

### For NI Expansions
```
Output/
├── Amplified Funk Library/
│   ├── Amplified Funk 01 Kick.adg
│   ├── Amplified Funk Percussion 01.adg
│   └── ...
└── ...
```

### For Generic Processing
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
- **main.py**: Single expansion processor (organized by drum type)
- **main_percussion.py**: Single expansion percussion processor
- **main_generic.py**: Single folder processor
- **meta_main.py**: Multi-expansion processor
- **meta_main_percussion.py**: Multi-expansion percussion processor
- **meta_main_folders.py**: Recursive folder processor
- **set_macro.py**: Macro value processor

### Support Scripts
- **decoder.py**: ADG file decoder
- **encoder.py**: ADG file encoder
- **transformer.py**: XML content transformer

## Features by Script

### set_macro.py
- Sets macro values in multiple drum racks
- Processes files recursively
- Updates both default and manual values
- Supports macros 1-127
- Validates value range (0-127)
- Reports processing status

### main_generic.py
- Processes any folder containing .wav files
- Validates audio files before processing
- Creates 32-pad racks
- Names racks based on folder structure
- Supports partial racks for remaining samples

### meta_main_folders.py
- Recursively scans folder hierarchies
- Maintains folder structure in output
- Reports sample counts per folder
- Processes all folders containing .wav files
- Creates organized output structure

### main.py / meta_main.py
- Organizes samples by drum type
- Creates consistent pad layouts
- Names racks based on first kick sample
- Supports batch processing of expansions

### main_percussion.py / meta_main_percussion.py
- Focuses on percussion samples
- Creates alphabetically organized racks
- Names racks with expansion name
- Supports multiple racks per expansion

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