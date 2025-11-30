# Ableton Device Creator V2.0

> **Professional toolkit for creating, modifying, and managing Ableton Live devices**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Overview

Comprehensive suite of production-tested Python scripts for automating Ableton Live device creation and modification. Born from 2+ years of use in professional live performance systems.

### What Can You Do?

- **Create drum racks** from sample libraries with intelligent categorization
- **Automate macro mapping** for CC control, transpose, and color coding
- **Build multi-device racks** with complex routing and layering
- **Convert between formats** (Simpler ↔ DrumCell, ADG manipulation)
- **Batch process** entire sample libraries in minutes

## Related Projects

**Omnisphere preset extraction tools** have been moved to a dedicated repository:
👉 [Omnisphere-Tools](https://github.com/YOUR-USERNAME/Omnisphere-Tools) - Extract and analyze Spectrasonics Omnisphere presets

This repository focuses exclusively on **documented Ableton Live file formats** (ADG/ADV).

## Quick Start

### Installation

```bash
git clone https://github.com/ben-juodvalkis/Ableton-Device-Creator.git
cd "Ableton-Device-Creator"

# No dependencies required! Uses Python standard library only
python3 --version  # Ensure Python 3.8+
```

### Basic Usage

**Create a drum rack from samples:**

```bash
python3 drum-racks/creation/main_simple_folder.py \
  templates/input_rack.adg \
  "/path/to/your/samples"
```

**Batch process entire sample library:**

```bash
python3 drum-racks/batch/meta_main_folders.py \
  templates/input_rack.adg \
  "/path/to/Native Instruments/Expansions"
```

**Add CC Control to existing drum racks:**

```bash
python3 macro-mapping/cc-control/batch_apply_cc_mappings.py \
  "/path/to/your/drum/racks"
```

## Features

### 🥁 Drum Rack Tools (37 scripts)

**Creation** ([drum-racks/creation/](drum-racks/creation/))
- Standard NI expansion layout processing
- Percussion-only rack creation
- Multi-velocity layer support
- Dual/triple device racks (electro + acoustic)
- Template-based creation
- Note-name based organization

**Batch Processing** ([drum-racks/batch/](drum-racks/batch/))
- Process entire expansion libraries
- Recursive folder processing
- Battery kit organization
- Bulk remapping and trimming

**Modification** ([drum-racks/modification/](drum-racks/modification/))
- Remap MIDI notes
- Trim to 16 pads
- Replace sample paths
- Merge multiple racks
- Disable auto-coloring

### 🎛️ Macro Mapping Tools (18 scripts)

**CC Control** ([macro-mapping/cc-control/](macro-mapping/cc-control/))
- Automated CC Control device integration
- DrumCell-specific mappings
- Preserve existing values while adding new mappings
- Batch processing entire libraries
- Custom preset map generation

**Transpose** ([macro-mapping/transpose/](macro-mapping/transpose/))
- Batch add transpose controls
- Custom range configuration

**Color Coding** ([macro-mapping/color-coding/](macro-mapping/color-coding/))
- Automatic color assignment by sample type
- Batch apply across libraries
- Custom color schemes

### 🎹 Instrument Rack Tools (7 scripts)

**Wrapping** ([instrument-racks/wrapping/](instrument-racks/wrapping/))
- Wrap single devices in racks
- Template-based wrapping
- Dual/triple device rack creation

**Multi-Device** ([instrument-racks/multi-device/](instrument-racks/multi-device/))
- AUPreset wrapper for plugin automation
- Round-robin sample rotation
- Complex layering configurations

### 🔄 Conversion Tools (9 scripts)

**Simpler → DrumCell** ([conversion/simpler-to-drumcell/](conversion/simpler-to-drumcell/))
- Convert Simpler devices to DrumCell
- Batch drum rack conversion
- Preserve sample mappings

**ADG Converter** ([conversion/adg-converter/](conversion/adg-converter/))
- Format conversion with macro preservation
- Apply macro mappings programmatically
- Set macro values in bulk
- Parameter visibility control

### 🎵 Sampler & Simpler (6 scripts)

**Sampler** ([sampler/chromatic-mapping/](sampler/chromatic-mapping/))
- Chromatic sample mapping (32 samples per octave)
- Drum-style sampler layout
- Percussion-only samplers
- Phrase/loop organization

**Simpler** ([simpler/](simpler/))
- Create individual Simpler devices per sample
- Maintains folder structure

### 🛠️ Core Utilities

**[utils/](utils/)** - Shared components used by all scripts
- `decoder.py` - Decompress ADG/ADV files to XML
- `encoder.py` - Compress XML back to ADG/ADV
- `transformer.py` - XML manipulation for drum racks
- `simpler_transformer.py` - Simpler-specific transformations
- `pitch_shifter.py` - Transpose sample regions
- `scroll_position.py` - Update macro scroll positions
- `set_macro.py` - Set macro values programmatically

## Project Structure

```
Ableton-Device-Creator/
├── drum-racks/              # 37 drum rack scripts
│   ├── creation/            # Create from sample folders
│   ├── batch/               # Process entire libraries
│   └── modification/        # Modify existing racks
│
├── macro-mapping/           # 18 macro automation scripts
│   ├── cc-control/          # CC Control integration
│   ├── transpose/           # Transpose mapping
│   └── color-coding/        # Automatic pad coloring
│
├── instrument-racks/        # 7 multi-device rack scripts
│   ├── wrapping/            # Wrap devices in racks
│   └── multi-device/        # Complex rack creation
│
├── conversion/              # 9 format conversion scripts
│   ├── simpler-to-drumcell/ # Simpler → DrumCell
│   └── adg-converter/       # ADG manipulation
│
├── sampler/                 # 5 sampler creation scripts
│   └── chromatic-mapping/   # Chromatic layout variants
│
├── simpler/                 # 1 simpler creation script
│
├── utils/                   # 10 core utilities
│   ├── decoder.py           # ADG → XML
│   ├── encoder.py           # XML → ADG
│   └── transformer.py       # XML manipulation
│
├── templates/               # Device templates (.adg, .adv)
│   ├── drum-racks/          # Drum rack templates
│   ├── input_rack.adg       # Standard template
│   └── simpler-template.adv # Simpler template
│
├── archive-v1/              # V1 code (preserved)
│
└── docs/                    # Documentation (planned)
    ├── DRUM_RACKS.md
    ├── MACRO_MAPPING.md
    └── ADVANCED_USAGE.md
```

## Common Workflows

### Workflow 1: Organize Sample Library into Drum Racks

```bash
# Process entire Native Instruments expansion library
python3 drum-racks/batch/meta_main_folders.py \
  templates/input_rack.adg \
  "/Library/Application Support/Native Instruments/Expansions"

# Output: Organized drum racks in output/ directory
```

### Workflow 2: Add CC Control to All Your Drum Racks

```bash
# Batch add CC Control to existing racks
python3 macro-mapping/cc-control/batch_apply_cc_mappings.py \
  "/Users/You/Music/Ableton/User Library/Presets/Instruments/Drum Rack"

# Racks now have CC Control mapped to Macro 1
```

### Workflow 3: Create Multi-Velocity Drum Rack

```bash
# Create rack with velocity layers
python3 drum-racks/creation/create_multivelocity_drum_rack_v2.py \
  templates/input_rack.adg \
  "/path/to/velocity-layered/samples"

# Automatically detects velocity markers in filenames
```

### Workflow 4: Convert Simpler Rack to DrumCell

```bash
# Convert existing drum rack from Simpler to DrumCell
python3 conversion/simpler-to-drumcell/drum_rack_simpler_to_drumcell.py \
  "My Drum Rack.adg"

# Output: DrumCell-based version with all samples preserved
```

## Requirements

- **Python 3.8+** (no external dependencies!)
- **Ableton Live 11+** (for testing generated devices)
- All scripts use Python standard library only

## Use Cases

### Music Producers
- Organize massive sample libraries into browsable racks
- Create consistent naming and folder structures
- Batch process expansion packs

### Sound Designers
- Automate repetitive device configuration
- Create multi-layered instruments quickly
- Build template libraries

### Live Performers
- Build performance-ready racks with CC control
- Create color-coded drum layouts for visual cueing
- Standardize device configurations across sets

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Project overview and command reference
- **[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)** - Development roadmap
- **[ARCHITECTURE_REFERENCE.md](ARCHITECTURE_REFERENCE.md)** - Technical architecture
- **[CODEBASE_OVERVIEW.md](CODEBASE_OVERVIEW.md)** - Detailed code analysis

## How It Works

### ADG/ADV File Format

Ableton Device files (.adg) and Device Presets (.adv) are **gzipped XML files**. This toolkit:

1. **Decompresses** the .adg/.adv file to XML
2. **Modifies** the XML structure (add samples, change mappings, etc.)
3. **Recompresses** back to .adg/.adv format

Example:

```python
from utils.decoder import decode_adg
from utils.encoder import encode_adg

# Decompress ADG to XML
decode_adg("MyDrumRack.adg")  # Creates MyDrumRack.xml

# Modify XML as needed...

# Recompress to ADG
encode_adg("MyDrumRack.xml")  # Creates MyDrumRack.adg
```

## Version History

### V2.0.0 (2025-11-28)

**Complete rewrite** with production-ready tools from live performance system.

**New:**
- 82 Python scripts migrated from Looping project
- Organized into 10 logical categories
- Comprehensive template library
- Zero external dependencies

**Breaking Changes:**
- Completely new directory structure
- Different import paths
- Not compatible with V1

V1 code preserved in `archive-v1/` branch for reference.

## Contributing

Contributions welcome! This project follows **strict Test-Driven Development (TDD)**:

1. Write tests first (Red phase)
2. Implement minimal code (Green phase)
3. Refactor (Refactor phase)

See [CLAUDE.md](CLAUDE.md) for TDD workflow and testing commands.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Built for the Ableton Live community with 2+ years of production use in professional live looping systems.

Special thanks to:
- Native Instruments for expansions that inspired many batch scripts
- The Ableton community for feedback and use cases

## Support

- **Issues**: [GitHub Issues](https://github.com/ben-juodvalkis/Ableton-Device-Creator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ben-juodvalkis/Ableton-Device-Creator/discussions)

---

**Built with Claude Code** | [Documentation](CLAUDE.md) | [Architecture](ARCHITECTURE_REFERENCE.md)
