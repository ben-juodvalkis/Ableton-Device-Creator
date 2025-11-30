# Ableton Device Creator V3.0

> **Professional Python toolkit for creating and modifying Ableton Live devices**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Overview

Modern Python library for programmatically creating and modifying Ableton Live devices (.adg) and presets (.adv). Born from 2+ years of production use in professional live performance systems.

### What's New in V3.0?

✨ **Modern Python Package** - Installable with pip, proper module structure
🎯 **Simple API** - High-level classes replace 100+ scripts
⚡ **CLI Tool** - Command-line interface for quick workflows
📚 **Zero Dependencies** - Core uses only Python stdlib
🎨 **Production-Ready** - Tested with real samples and DAW

---

## Quick Start

### Installation

```bash
# Install the package
pip install ableton-device-creator

# Or install from source
git clone https://github.com/ben-juodvalkis/Ableton-Device-Creator.git
cd "Ableton-Device-Creator"
pip install -e .

# Optional: Install CLI support
pip install ableton-device-creator[cli]
```

### Basic Usage (Python API)

```python
from ableton_device_creator.drum_racks import DrumRackCreator
from ableton_device_creator.sampler import SamplerCreator

# Create drum rack from samples
creator = DrumRackCreator(template="templates/input_rack.adg")
rack = creator.from_folder("samples/drums/", output="MyKit.adg")

# Create chromatic sampler
sampler = SamplerCreator(template="templates/sampler-rack.adg")
instrument = sampler.from_folder("samples/", layout="chromatic")
```

### Basic Usage (CLI)

```bash
# Create drum rack
adc drum-rack create samples/drums/

# Apply color coding
adc drum-rack color MyKit.adg

# Create chromatic sampler
adc sampler create samples/ --layout chromatic

# Show device info
adc util info MyKit.adg
```

---

## Features

### 🥁 Drum Rack Creation

```python
from ableton_device_creator.drum_racks import DrumRackCreator, DrumRackModifier

# Create from folder with auto-categorization
creator = DrumRackCreator("templates/input_rack.adg")
rack = creator.from_categorized_folders(
    "samples/drums/",
    layout="808",  # or "standard", "percussion"
    output="808_Kit.adg"
)

# Remap MIDI notes
modifier = DrumRackModifier("MyKit.adg")
modifier.remap_notes(shift=12).save("MyKit_High.adg")
```

**Features:**
- Auto-categorize samples (kicks, snares, hats, etc.)
- Multiple layouts (standard, 808, percussion)
- MIDI note remapping
- Batch processing

### 🎨 Macro Mapping

```python
from ableton_device_creator.macro_mapping import DrumPadColorMapper, TransposeMapper

# Apply color coding
colorizer = DrumPadColorMapper("MyKit.adg")
colorizer.apply_colors().save("MyKit_Colored.adg")

# Add transpose control
transpose = TransposeMapper("MySampler.adg")
transpose.add_transpose_mapping(macro_index=15).save("MySampler_Transpose.adg")
```

**Features:**
- Auto color pads by sample type
- Add transpose controls to samplers
- Preserve existing mappings

### 🎹 Sampler & Simpler

```python
from ableton_device_creator.sampler import SamplerCreator, SimplerCreator

# Create chromatic sampler (maps samples to consecutive notes)
sampler = SamplerCreator("templates/sampler-rack.adg")
sampler.from_folder("samples/", layout="chromatic")

# Create Simpler devices (one per sample)
simpler = SimplerCreator("templates/simpler-template.adv")
simpler.from_folder("samples/", output_folder="simplers/")
```

**Layouts:**
- **Chromatic** - Maps samples from C-2 upward
- **Drum** - 8 kicks, 8 snares, 8 hats, 8 perc
- **Percussion** - Maps from C1 upward

### 🛠️ Core Utilities

```python
from ableton_device_creator.core import decode_adg, encode_adg

# Decode ADG to XML for inspection
xml = decode_adg("MyRack.adg")
print(xml[:100])

# Modify XML and re-encode
encode_adg(modified_xml, "MyRack_Modified.adg")
```

---

## CLI Reference

Full CLI documentation: [docs/CLI_GUIDE.md](docs/CLI_GUIDE.md)

### Drum Rack Commands

```bash
# Create drum rack
adc drum-rack create samples/ -o MyKit.adg --layout 808

# Apply colors
adc drum-rack color MyKit.adg

# Remap notes (shift up 1 octave)
adc drum-rack remap MyKit.adg --shift 12
```

### Sampler Commands

```bash
# Create chromatic sampler
adc sampler create samples/ --layout chromatic

# Create drum-style sampler
adc sampler create samples/ --layout drum --max-samples 32
```

### Simpler Commands

```bash
# Create Simpler devices (one per sample)
adc simpler create samples/ -o simplers/

# Process recursively
adc simpler create samples/ --recursive
```

### Utility Commands

```bash
# Decode to XML
adc util decode MyRack.adg -o MyRack.xml

# Encode from XML
adc util encode MyRack.xml -o MyRack.adg

# Show device info
adc util info MyRack.adg
```

---

## Project Structure

```
Ableton-Device-Creator/
├── src/ableton_device_creator/    # Python package
│   ├── core/                       # ADG encoder/decoder
│   ├── drum_racks/                 # Drum rack creation
│   ├── sampler/                    # Sampler creation
│   ├── macro_mapping/              # Color, transpose
│   └── cli.py                      # Command-line interface
│
├── examples/                       # Usage examples
│   ├── drum_rack_example.py
│   ├── sampler_example.py
│   └── macro_mapping_example.py
│
├── templates/                      # Device templates
│   ├── input_rack.adg              # Drum rack template
│   ├── sampler-rack.adg            # Sampler template
│   └── simpler-template.adv        # Simpler template
│
├── docs/                           # Documentation
│   ├── CLI_GUIDE.md                # CLI reference
│   └── current-plan/               # Development docs
│
└── archive-v2-scripts/             # V2 reference code
```

---

## Common Workflows

### Workflow 1: Complete Drum Kit Setup

```bash
# 1. Create drum rack
adc drum-rack create samples/drums/ -o MyKit.adg

# 2. Apply color coding
adc drum-rack color MyKit.adg

# 3. Remap to higher octave (optional)
adc drum-rack remap MyKit.adg --shift 12 -o MyKit_High.adg
```

### Workflow 2: Sampler Library

```python
from ableton_device_creator.sampler import SamplerCreator

creator = SamplerCreator("templates/sampler-rack.adg")

# Create samplers for different categories
creator.from_folder("samples/kicks/", output="Kicks_Chromatic.adg")
creator.from_folder("samples/snares/", output="Snares_Chromatic.adg")
creator.from_folder("samples/hats/", output="Hats_Chromatic.adg")
```

### Workflow 3: Batch Processing

```python
from pathlib import Path
from ableton_device_creator.drum_racks import DrumRackCreator

creator = DrumRackCreator("templates/input_rack.adg")

# Process all subfolders
for folder in Path("samples").iterdir():
    if folder.is_dir():
        creator.from_folder(folder, output=f"output/{folder.name}.adg")
```

---

## API Documentation

### DrumRackCreator

```python
from ableton_device_creator.drum_racks import DrumRackCreator

creator = DrumRackCreator(template="templates/input_rack.adg")

# Simple mode - fill pads sequentially
rack = creator.from_folder(
    samples_dir="samples/",
    output="MyRack.adg",
    categorize=False
)

# Categorized mode - organize by sample type
rack = creator.from_categorized_folders(
    samples_dir="samples/",
    layout="808",  # or "standard", "percussion"
    output="Categorized.adg"
)
```

### SamplerCreator

```python
from ableton_device_creator.sampler import SamplerCreator

creator = SamplerCreator(template="templates/sampler-rack.adg")

# Chromatic layout (C-2 upward)
sampler = creator.from_folder(
    samples_dir="samples/",
    layout="chromatic",
    samples_per_instrument=32
)

# Drum layout (8 kicks, 8 snares, etc.)
sampler = creator.from_folder(
    samples_dir="samples/",
    layout="drum"
)
```

### SimplerCreator

```python
from ableton_device_creator.sampler import SimplerCreator

creator = SimplerCreator(template="templates/simpler-template.adv")

# Batch create (one .adv per sample)
devices = creator.from_folder(
    samples_dir="samples/",
    output_folder="simplers/"
)

# Single device
device = creator.from_sample(
    sample_path="kick.wav",
    output="kick.adv"
)
```

---

## Requirements

- **Python 3.8+**
- **Core:** Zero dependencies (stdlib only)
- **CLI:** `click>=8.0.0` (optional, install with `pip install ableton-device-creator[cli]`)
- **Ableton Live 11+** (for testing generated devices)

---

## How It Works

### ADG/ADV File Format

Ableton device files (.adg) and presets (.adv) are **gzipped XML files**:

```
MyRack.adg (55 KB gzipped)
    ↓ decode
MyRack.xml (1.1 MB uncompressed)
    ↓ modify
MyRack_Modified.xml
    ↓ encode
MyRack_Modified.adg (56 KB gzipped)
```

This toolkit:
1. Decompresses .adg/.adv to XML
2. Modifies the XML structure
3. Recompresses to .adg/.adv

---

## Version History

### V3.0.0 (2025-11-29)

**Complete rewrite as modern Python package**

**New:**
- ✅ Installable Python package with pip
- ✅ Clean API with high-level classes
- ✅ CLI tool with 11 commands
- ✅ Comprehensive documentation
- ✅ Production-tested with real samples
- ✅ Type hints throughout
- ✅ Zero core dependencies

**Migrated:**
- 111 V2 scripts → 15 Python classes
- Ad-hoc scripts → Organized modules
- Manual workflows → CLI commands

**Breaking Changes:**
- New import paths (`from ableton_device_creator.drum_racks import ...`)
- Different API (class-based instead of scripts)
- V2 scripts preserved in `archive-v2-scripts/`

### V2.0.0 (2025-11-28)

Production-ready scripts from live performance system (111 scripts).

### V1.0.0

Original proof-of-concept (preserved in `archive-v1/`).

---

## Development

### Running Examples

```bash
# Set PYTHONPATH
export PYTHONPATH=src

# Run examples
python3 examples/drum_rack_example.py
python3 examples/sampler_example.py
python3 examples/cli_demo.py
```

### Testing Philosophy

This project prioritizes **production-proven code** over extensive test coverage:

- **Primary validation:** Manual testing in Ableton Live
- **Production use:** 2+ years in professional live performance
- **Immediate feedback:** Invalid ADG files fail to load in DAW
- **Focus:** Real-world usage over synthetic tests

---

## Documentation

- **[CLI Guide](docs/CLI_GUIDE.md)** - Complete CLI reference
- **[CLAUDE.md](CLAUDE.md)** - Project context for AI assistants
- **[Examples](examples/)** - Python API examples
- **[V3 Implementation Plan](docs/current-plan/V3_IMPLEMENTATION_PLAN.md)** - Development roadmap

---

## Contributing

Contributions welcome! Please:

1. Test in Ableton Live (the ultimate validation)
2. Add examples for new features
3. Update documentation
4. Keep zero-dependency policy for core

---

## License

MIT License - see LICENSE file for details.

---

## Acknowledgments

Built for the Ableton Live community with 2+ years of production use.

**Special thanks:**
- Native Instruments for sample libraries that inspired this toolkit
- Ableton community for feedback and use cases
- Claude AI for V3.0 refactoring assistance

---

## Support

- **Issues:** [GitHub Issues](https://github.com/ben-juodvalkis/Ableton-Device-Creator/issues)
- **Discussions:** [GitHub Discussions](https://github.com/ben-juodvalkis/Ableton-Device-Creator/discussions)
- **Documentation:** [docs/](docs/)

---

**V3.0 - Built with Python & Claude Code**
