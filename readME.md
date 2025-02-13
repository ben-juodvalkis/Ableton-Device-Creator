# Ableton Device File Processor
## Technical Documentation

## Overview
The Ableton Device File Processor is a Python-based system for creating Ableton Live drum racks (.adg) from Native Instruments Expansion libraries. It offers two main functionalities:
1. Creating full drum racks with organized drum categories
2. Creating percussion-only racks from percussion samples

## Features

### Standard Drum Racks
- Creates organized drum racks from sample libraries
- Maintains consistent pad layout across racks:
  - First 8 pads: Kick drums
  - Next 8 pads: Snares and claps
  - Next 8 pads: Hi-hats and shakers
  - Last 8 pads: Auxiliary percussion
- Names racks based on library name and first kick sample

### Percussion-Only Racks
- Creates 32-pad racks filled with percussion samples
- Organizes samples alphabetically
- Names racks based on library name (e.g., "Anima Ascent Percussion 01")
- Creates multiple racks if library contains more than 32 samples

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd ableton-device-processor
```

2. Ensure Python 3.6+ is installed

## Usage

### Standard Drum Racks

```bash
# Process a single library
python3 scripts/main.py input_rack.adg "/path/to/library/folder"

# Process multiple libraries
python3 scripts/meta_main.py input_rack.adg "/path/to/expansions/folder"
```

### Percussion-Only Racks

```bash
python3 scripts/meta_main_percussion.py input_rack.adg "/path/to/expansions/folder"
```

Arguments:
- `input_rack.adg`: Template drum rack file
- `expansions_folder`: Path to Native Instruments Expansions folder

Output Structure:
```
Output/
├── Amplified Funk Library/
│   ├── Amplified Funk Percussion 01.adg  # 32 percussion samples
│   ├── Amplified Funk Percussion 02.adg  # Next 32 samples
│   └── ...
├── Battery Factory Library/
│   ├── Battery Factory Percussion 01.adg
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
│   ├── decoder.py             # ADG file decoder
│   ├── transformer.py         # XML content transformer
│   └── encoder.py             # ADG file encoder
```

### Process Flow
1. Scan library folders for samples
2. Organize samples based on mode:
   - Standard: Group by drum type (kicks, snares, etc.)
   - Percussion: Alphabetical order
3. Create drum racks with organized samples
4. Save racks in organized output structure

## Sample Organization

### Standard Mode Categories
- **Kicks**: All kick drum samples
- **Snares/Claps**: All snare and clap samples
- **Hi-hats/Shakers**: All hi-hat and shaker samples
- **Auxiliary Percussion**: Any percussion except kicks, snares, claps, hi-hats, shakers, and cymbals

### Percussion Mode
- Uses all samples from the library's Percussion folder
- Organizes alphabetically across 32-pad racks
- Creates multiple racks if more than 32 samples exist

### Sorting
- Standard mode: Samples within each category are sorted by descriptive names
- Percussion mode: All samples sorted alphabetically

## Error Handling
- Validates input files and folders
- Reports missing or invalid libraries
- Continues processing remaining libraries if one fails
- Provides detailed error messages and warnings

## Contributing
To contribute to this project:
1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Submit a pull request

## License
This project is provided under the MIT License.