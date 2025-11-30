# Scripts Directory

This directory contains various Python scripts for working with Ableton Live projects and devices.

## Directory Structure

```
scripts/
├── ableton/              # Scripts for working with Ableton Live files
│   ├── analysis/        # Project analysis tools
│   │   └── analyze_als.py  # Analyzes .als files and generates reports
│   └── conversion/      # File conversion tools
│       └── adg_converter.py  # Converts between ADG formats
│
├── device/              # Device creation and modification scripts
│   ├── sampler/        # Sampler device scripts
│   │   └── main_sampler.py
│   ├── drum_rack/      # Drum Rack device scripts
│   │   ├── main.py     # Core drum rack creation script
│   │   └── main_percussion.py
│   └── generic/        # Generic device scripts
│       └── main_generic.py
│
├── meta/               # Meta-information and configuration scripts
│   ├── main.py        # Meta-script for processing multiple libraries
│   ├── main_folders.py
│   └── main_percussion.py
│
└── utils/              # Shared utility scripts
    ├── encoder.py      # Compresses XML to gzipped ADG format
    ├── decoder.py      # Extracts XML from gzipped ADG files
    ├── transformer.py  # XML transformation utilities
    ├── set_macro.py    # Macro manipulation utilities
    └── scroll_position.py  # Modifies drum rack pad scroll position
```

## Core Utilities

### ADG File Handling

Ableton Device Group (ADG) files are gzipped XML files. We provide two core utilities to work with them:

- **decoder.py**: Extracts the XML content from ADG files

  ```python
  from decoder import decode_adg
  xml_content = decode_adg(Path("device.adg"))  # Returns XML string
  ```

- **encoder.py**: Creates ADG files from XML content
  ```python
  from encoder import encode_adg
  encode_adg(xml_content, Path("output.adg"))  # Saves gzipped ADG file
  ```

### Drum Rack Utilities

- **scroll_position.py**: Modifies which pads are visible in a drum rack

  ```bash
  # Show pads 1-8 (scroll position 0)
  python3 utils/scroll_position.py input_rack.adg --scroll 0

  # Show pads 9-16 (scroll position 8)
  python3 utils/scroll_position.py input_rack.adg --scroll 8 --output custom_name.adg
  ```

### Sampler Device Scripts

- **main_sampler.py**: Creates a Sampler device from all samples in a folder (maps all samples across the key range).
- **main_drumstyle_sampler.py**: Creates a Sampler device with 32 samples per batch, grouped as 8 Kick, 8 Snare/Clap, 8 Hihat/Shaker, 8 Percussion/Other, mapped to consecutive notes (default: C3–G#4). Naming uses the library and first kick descriptor.
- **main_percussion_sampler.py**: Creates percussion-only Sampler devices, each with 32 percussion/other samples per batch, mapped to C3–G#4. Naming uses the library and first sample descriptor.
- **main_phrases_sampler.py**: For phrase/loop libraries, iterates through each subfolder and creates Sampler devices (batches of 32 samples) for each, named after the subfolder (with batch number if needed).

#### Usage Examples

```bash
# Drum-style sampler (4x8 groups)
python3 scripts/device/sampler/main_drumstyle_sampler.py Donor\ Sampler\ Rack.adg /path/to/library --output-folder /path/to/output

# Percussion-only sampler
python3 scripts/device/sampler/main_percussion_sampler.py Donor\ Sampler\ Rack.adg /path/to/library --output-folder /path/to/output

# Phrases/loops: one device per subfolder
python3 scripts/device/sampler/main_phrases_sampler.py Donor\ Sampler\ Rack.adg /path/to/parent_folder --output-folder /path/to/output
```

- All scripts support batch processing over multiple libraries with a shell loop.
- Output files are named for the library/subfolder and (if needed) batch number or descriptor.

## Usage Examples

```bash
# Analyze Ableton projects
python3 ableton/analysis/analyze_als.py /path/to/projects

# Create a sampler device
python3 device/sampler/main_sampler.py /path/to/samples

# Create a drum rack
python3 device/drum_rack/main.py /path/to/samples

# Process multiple libraries
python3 meta/main.py /path/to/template.adg /path/to/expansions

# Modify drum rack view
python3 utils/scroll_position.py input_rack.adg --scroll 16
```

## Dependencies

All scripts require Python 3.x and the following packages:

- xml.etree.ElementTree (built-in)
- pathlib (built-in)
- typing (built-in)
- wave (built-in)
- gzip (built-in)

## Notes

- The `utils/` directory contains shared functionality used by other scripts
- Device scripts in `device/` use the utilities from `utils/` for common operations
- Analysis scripts in `ableton/analysis/` work directly with Ableton Live project files
- Meta scripts in `meta/` handle configuration and setup tasks
- The core drum rack creation script is in `device/drum_rack/main.py`
- The meta script in `meta/main.py` processes multiple libraries using the core script

## Working with ADG Files

ADG files are Ableton Device Group files that store device presets. They are gzipped XML files, which means:

1. They cannot be edited directly as text
2. They must be decoded before modification
3. They must be encoded after modification

The typical workflow for modifying an ADG file is:

1. Use `decoder.py` to extract the XML content
2. Modify the XML content using Python's XML tools
3. Use `encoder.py` to save the modified content as a new ADG file

Example:

```python
from pathlib import Path
from decoder import decode_adg
from encoder import encode_adg

# Extract XML
xml_content = decode_adg(Path("input.adg"))

# Modify XML content
# ... your modifications here ...

# Save as new ADG
encode_adg(modified_xml, Path("output.adg"))
```
