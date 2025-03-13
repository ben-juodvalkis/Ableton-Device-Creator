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
    ├── encoder.py      # ADG encoding utilities
    ├── decoder.py      # ADG decoding utilities
    ├── transformer.py  # XML transformation utilities
    └── set_macro.py    # Macro manipulation utilities
```

## Usage

Each script can be run independently. For example:

```bash
# Analyze Ableton projects
python3 ableton/analysis/analyze_als.py /path/to/projects

# Create a sampler device
python3 device/sampler/main_sampler.py /path/to/samples

# Create a drum rack
python3 device/drum_rack/main.py /path/to/samples

# Process multiple libraries
python3 meta/main.py /path/to/template.adg /path/to/expansions
```

## Dependencies

All scripts require Python 3.x and the following packages:
- xml.etree.ElementTree (built-in)
- pathlib (built-in)
- typing (built-in)
- wave (built-in)

## Notes

- The `utils/` directory contains shared functionality used by other scripts
- Device scripts in `device/` use the utilities from `utils/` for common operations
- Analysis scripts in `ableton/analysis/` work directly with Ableton Live project files
- Meta scripts in `meta/` handle configuration and setup tasks
- The core drum rack creation script is in `device/drum_rack/main.py`
- The meta script in `meta/main.py` processes multiple libraries using the core script 