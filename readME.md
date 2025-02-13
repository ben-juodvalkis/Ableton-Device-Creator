# Ableton Device File Processor
## Technical Documentation

## Overview
The Ableton Device File Processor is a Python-based system for creating Ableton Live drum racks (.adg) from sample libraries. It offers three main functionalities:
1. Creating full drum racks with organized drum categories
2. Creating percussion-only racks from percussion samples
3. Creating drum racks from any folder of samples

## Features

### Standard Drum Racks (NI Expansions)
- Creates organized drum racks from Native Instruments Expansion libraries
- Maintains consistent pad layout across racks:
  - First 8 pads: Kick drums
  - Next 8 pads: Snares and claps
  - Next 8 pads: Hi-hats and shakers
  - Last 8 pads: Auxiliary percussion
- Names racks based on library name and first kick sample

### Percussion-Only Racks (NI Expansions)
- Creates 32-pad racks filled with percussion samples
- Organizes samples alphabetically
- Names racks based on library name (e.g., "Anima Ascent Percussion 01")
- Creates multiple racks if library contains more than 32 samples

### Generic Sample Folder Racks
- Creates 32-pad racks from any folder containing .wav files
- Organizes samples alphabetically
- Names racks based on folder structure (e.g., "Francesca Breath 01")
- Creates multiple racks if folder contains more than 32 samples

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd ableton-device-processor
```

2. Ensure Python 3.6+ is installed

## Usage

### Standard Drum Racks (NI Expansions)

```bash
# Process a single library
python3 scripts/main.py input_rack.adg "/path/to/expansion/library"

# Process multiple libraries
python3 scripts/meta_main.py input_rack.adg "/path/to/expansions/folder"
```

### Percussion-Only Racks (NI Expansions)

```bash
python3 scripts/meta_main_percussion.py input_rack.adg "/path/to/expansions/folder"
```

### Generic Sample Folder Racks

```bash
python3 scripts/main_generic.py input_rack.adg "/path/to/samples/folder"
```

Examples:
```bash
# Process 8dio Francesca breath samples
python3 scripts/main_generic.py input_rack.adg "/Users/Shared/Music/Soundbanks/8dio/8Dio_Francesca/1_Francesca_Core_Library/samples/Breath"

# Process 8dio Barbary breath samples
python3 scripts/main_generic.py input_rack.adg "/Users/Shared/Music/Soundbanks/8dio/8Dio_Barbary/1_Barbary_Core_Library/Samples/Breathe"
```

Arguments:
- `input_rack.adg`: Template drum rack file
- `library/folder`: Path to sample source

Output Structure:
```
For NI Expansions:
Output/
├── Amplified Funk Library/
│   ├── Amplified Funk 01 Kick.adg
│   ├── Amplified Funk Percussion 01.adg
│   └── ...
└── ...

For Generic Folders:
[input_rack location]/
├── Francesca Breath Racks/
│   ├── Francesca Breath 01.adg
│   └── Francesca Breath 02.adg
├── Barbary Breathe Racks/
│   ├── Barbary Breathe 01.adg
│   └── ...
└── ...
```

## System Architecture

### Module Structure
```
ableton-device-processor/
├── scripts/
│   ├── meta_main.py           # Multi-library processor for drum racks
│   ├── meta_main_percussion.py # Multi-library processor for percussion
│   ├── main.py                # Single library processor for drum racks
│   ├── main_percussion.py     # Single library processor for percussion
│   ├── main_generic.py        # Generic folder processor
│   ├── decoder.py             # ADG file decoder
│   ├── transformer.py         # XML content transformer
│   └── encoder.py             # ADG file encoder
```

### Process Flow
1. Scan source location for samples
2. Organize samples based on mode:
   - Standard: Group by drum type (kicks, snares, etc.)
   - Percussion: Alphabetical order from Percussion folder
   - Generic: Alphabetical order from specified folder
3. Create drum racks with organized samples
4. Save racks in organized output structure

## Sample Organization

### Standard Mode Categories (NI Expansions)
- **Kicks**: All kick drum samples
- **Snares/Claps**: All snare and clap samples
- **Hi-hats/Shakers**: All hi-hat and shaker samples (excluding open hi-hats)
- **Auxiliary Percussion**: Any percussion except kicks, snares, claps, hi-hats, shakers, and cymbals

### Percussion Mode (NI Expansions)
- Uses all samples from the library's Percussion folder
- Organizes alphabetically across 32-pad racks

### Generic Mode
- Uses all .wav files from specified folder
- Organizes alphabetically across 32-pad racks
- Creates multiple racks if needed

### Sorting
- Standard mode: Samples within each category are sorted by descriptive names
- Percussion/Generic modes: All samples sorted alphabetically

## Error Handling
- Validates input files and folders
- Reports missing or invalid sources
- Continues processing when possible
- Provides detailed error messages and warnings

## Contributing
To contribute to this project:
1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Submit a pull request

## License
This project is provided under the MIT License.