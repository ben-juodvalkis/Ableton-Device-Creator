# Ableton Device File Processor
## Technical Documentation

## Overview
The Ableton Device File Processor is a Python-based system for manipulating Ableton Live device group (.adg) files. It specializes in creating multiple drum racks from sample libraries, particularly Native Instruments Expansions, while preserving device settings.

## Features
- Creates organized drum racks from sample libraries
- Maintains consistent pad layout across racks:
  - First 8 pads: Auxiliary percussion
  - Next 8 pads: Hi-hats and shakers
  - Next 8 pads: Snares and claps
  - Last 8 pads: Kick drums
- Processes multiple libraries in batch
- Preserves all device settings from template rack

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd ableton-device-processor
```

2. Ensure Python 3.6+ is installed

## Usage

### Processing a Single Library

```bash
python3 scripts/main.py input_rack.adg "/path/to/library/folder"
```

Arguments:
- `input_rack.adg`: Template drum rack file
- `library_folder`: Path to sample library (e.g., "Amplified Funk Library")

Optional:
- `--output-folder`: Custom output location (default: creates named folder next to script)

### Processing Multiple Libraries

```bash
python3 scripts/meta_main.py input_rack.adg "/path/to/expansions/folder"
```

Arguments:
- `input_rack.adg`: Template drum rack file
- `expansions_folder`: Path to folder containing multiple libraries (e.g., Native Instruments Expansions folder)

Output:
- Creates an "Output" folder containing subfolders for each processed library
- Each library folder contains numbered drum racks (e.g., "Amplified Funk 01 Stash.adg")

## System Architecture

### Module Structure
```
ableton-device-processor/
├── scripts/
│   ├── meta_main.py    # Multi-library processor
│   ├── main.py         # Single library processor
│   ├── decoder.py      # ADG file decoder
│   ├── transformer.py  # XML content transformer
│   └── encoder.py      # ADG file encoder
```

### Process Flow
1. Scan library folders for samples
2. Organize samples into categories
3. Create multiple drum racks, each with:
   - 8 auxiliary percussion samples
   - 8 hi-hat/shaker samples
   - 8 snare/clap samples
   - 8 kick samples
4. Save racks in organized output structure

## Sample Organization

### Categories
- **Auxiliary Percussion**: Any percussion except kicks, snares, claps, hi-hats, shakers, and cymbals
- **Hi-hats/Shakers**: Closed hi-hats and shakers (excludes open hi-hats)
- **Snares/Claps**: All snare and clap samples
- **Kicks**: All kick drum samples

### Sorting
- Samples within each category are sorted alphabetically by their descriptive names
- Descriptive names are extracted after the category word (e.g., "Stash" from "Kick Stash 1")

## Output Structure
```
Output/
├── Amplified Funk Library/
│   ├── Amplified Funk 01 Stash.adg
│   ├── Amplified Funk 02 Punch.adg
│   └── ...
├── Battery Factory Library/
│   ├── Battery Factory 01 Deep.adg
│   └── ...
└── ...
```

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