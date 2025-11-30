# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Ableton Device Creator V3.0** is a modern Python library for creating and modifying Ableton Live devices (drum racks, sampler instruments, and Simpler devices) from audio sample libraries.

**Status:** Production-ready, actively maintained
**Version:** 3.0.0 (November 2025)
**Python:** 3.8+
**Dependencies:** Zero (core), Click 8.0+ (CLI optional)

## Architecture

### V3.0 Structure (Current)

```
src/ableton_device_creator/     # Modern Python package
├── core/                        # ADG encoder/decoder
│   ├── decoder.py
│   ├── encoder.py
│   └── __init__.py
├── drum_racks/                  # Drum rack creation
│   ├── creator.py
│   ├── modifier.py
│   ├── sample_utils.py
│   └── __init__.py
├── sampler/                     # Sampler creation
│   ├── creator.py
│   ├── simpler.py
│   └── __init__.py
├── macro_mapping/               # Color, transpose
│   ├── color_mapper.py
│   ├── transpose.py
│   └── __init__.py
├── cli.py                       # Command-line interface
└── __init__.py                  # Package exports
```

### Legacy Code

- `archive-v2-scripts/` - V2 reference scripts (111 scripts, read-only)
- `archive-v1/` - V1 code (preserved, not functional)

## Key Technical Information

### ADG/ADV File Format

- ADG (Ableton Device Group) and ADV (Ableton Device) files are **gzipped XML files**
- Core workflow: Decompress → Modify XML → Recompress
- Compression format: gzip with mtime=0, no filename header

### V3.0 API Usage

#### Python API

```python
from ableton_device_creator.drum_racks import DrumRackCreator
from ableton_device_creator.sampler import SamplerCreator, SimplerCreator
from ableton_device_creator.macro_mapping import DrumPadColorMapper

# Create drum rack
creator = DrumRackCreator(template="templates/input_rack.adg")
rack = creator.from_folder("samples/", output="MyKit.adg")

# Apply colors
colorizer = DrumPadColorMapper("MyKit.adg")
colorizer.apply_colors().save("MyKit_Colored.adg")

# Create chromatic sampler
sampler = SamplerCreator(template="templates/sampler-rack.adg")
sampler.from_folder("samples/", layout="chromatic")
```

#### CLI Usage (requires Click)

```bash
# Create drum rack
adc drum-rack create samples/ -o MyKit.adg

# Apply colors
adc drum-rack color MyKit.adg

# Create sampler
adc sampler create samples/ --layout chromatic

# Show device info
adc util info MyKit.adg
```

## Common Development Tasks

### Running Examples

```bash
# Set PYTHONPATH
export PYTHONPATH=src

# Run examples
python3 examples/drum_rack_example.py
python3 examples/sampler_example.py
python3 examples/cli_demo.py
```

### Testing (Manual)

```bash
# Create test device
python3 examples/test_sampler_simple.py

# Open in Ableton Live and verify:
# - Device loads without errors
# - Samples trigger correctly
# - MIDI mappings are correct
```

### Modifying Core Utilities

**Location:** `src/ableton_device_creator/core/`

**Important:** encoder/decoder must maintain exact Ableton gzip format:
- No timestamp (mtime=0)
- No filename in header
- UTF-8 encoding

**Test after changes:**
```python
from ableton_device_creator.core import decode_adg, encode_adg

# Roundtrip test
xml = decode_adg("templates/input_rack.adg")
encode_adg(xml, "test_output.adg")
xml2 = decode_adg("test_output.adg")
assert xml == xml2  # Must match exactly
```

### Adding New Features

**Follow V3.0 patterns:**
1. Create class in appropriate module (drum_racks, sampler, etc.)
2. Add to module's `__init__.py`
3. Export from main `__init__.py` if public API
4. Add example in `examples/`
5. Add CLI command if appropriate
6. Update README.md and docs/

**Example:**
```python
# src/ableton_device_creator/drum_racks/new_feature.py
class NewFeature:
    def __init__(self, template):
        self.template = Path(template)

    def create(self, input_path, output):
        # Implementation
        pass

# src/ableton_device_creator/drum_racks/__init__.py
from .new_feature import NewFeature
__all__ = [..., "NewFeature"]

# src/ableton_device_creator/__init__.py
from .drum_racks import NewFeature
__all__ = [..., "NewFeature"]
```

## Important Script Behaviors

### Drum Rack Scripts
- Creates 32-pad drum racks (C1 to G3, MIDI notes 36-67)
- Auto-categorizes samples by type (kick, snare, hat, clap, tom, cymbal, perc)
- Multiple layouts: standard, 808, percussion
- Supports velocity layers

### Sampler Scripts
- **Chromatic layout:** Maps 32 samples from C-2 upward (MIDI notes 0-31)
- **Drum layout:** 8 kicks, 8 snares, 8 hats, 8 perc (notes 0-31)
- **Percussion layout:** Maps from C1 upward (note 36+)
- Creates separate instruments for each 32-sample batch

### Simpler Scripts
- Creates one .adv device per sample
- Each Simpler spans full keyboard (notes 0-127)
- Maintains folder structure in batch mode
- Simplest device type for basic sample playback

### Sample Categorization

Detects sample types by filename keywords:
- **Kicks:** "kick", "bd", "bassdrum", "kck"
- **Snares:** "snare", "sd", "snr"
- **Hats:** "hat", "hh", "hihat", "hi-hat"
- **Claps:** "clap", "cp", "handclap"
- **Toms:** "tom", "tm"
- **Cymbals:** "cymbal", "cym", "crash", "ride"
- **Perc:** "perc", "percussion", "shaker", "conga", "bongo"

## Development Principles

### Testing Philosophy

This project prioritizes **production-proven code over extensive test coverage**.

**Current Validation Approach:**
- **Primary testing:** Manual verification in Ableton Live (open the generated device)
- **Production use:** 2+ years of real-world usage in live performance systems
- **Immediate feedback:** Invalid ADG files fail to load (obvious, instant feedback)
- **Stability:** ADG/ADV file format is stable and well-understood

**Why not strict TDD:**
- Generated devices must be tested in Ableton anyway (automated tests can't verify sound/UI)
- File operations are simple and stable (gzip compression, XML manipulation)
- Low risk: bugs are immediately obvious when device won't load
- Production use is the best validation

### Code Quality Principles

**What Matters Most:**
1. **Does it work in Ableton?** - The ultimate test
2. **Is it production-proven?** - Real-world usage over synthetic tests
3. **Is the code readable?** - Clear logic over clever tricks
4. **Zero dependencies** - Keep core simple and portable (CLI can use Click)

**Code Review Checklist:**
- [ ] Tested manually in Ableton Live
- [ ] Error handling for common cases (missing files, invalid paths)
- [ ] Code is readable with clear docstrings
- [ ] No new core dependencies (stdlib only)
- [ ] CLI dependencies are optional (pyproject.toml [cli])
- [ ] Documentation updated
- [ ] Type hints added

## Module Descriptions

### `core/` - ADG/ADV Encoding

**Purpose:** Low-level file format handling
**Dependencies:** stdlib only (gzip, pathlib, xml.etree.ElementTree)
**API:**
- `decode_adg(file_path) -> bytes` - Decompress ADG/ADV to XML
- `encode_adg(xml_content, output_path) -> Path` - Compress XML to ADG/ADV
- Both accept str or bytes for backward compatibility

### `drum_racks/` - Drum Rack Creation

**Purpose:** Create and modify drum racks
**Classes:**
- `DrumRackCreator` - Create drum racks from samples
  - `from_folder()` - Simple sequential fill
  - `from_categorized_folders()` - Organize by sample type
- `DrumRackModifier` - Modify existing racks
  - `remap_notes()` - Shift MIDI note mappings
  - `get_note_mappings()` - Read current mappings

**Utilities:**
- `categorize_samples()` - Auto-detect sample types
- `categorize_by_folder()` - Categorize by folder structure
- `detect_velocity_layers()` - Find multi-velocity samples
- `sort_samples_natural()` - Natural number sorting

### `sampler/` - Sampler Creation

**Purpose:** Create Multi-Sampler instruments and Simpler devices
**Classes:**
- `SamplerCreator` - Multi-Sampler with key layouts
  - Layouts: chromatic, drum, percussion
  - Max 32 samples per instrument
- `SimplerCreator` - Individual Simpler devices
  - Batch mode (one .adv per sample)
  - Single mode
  - `get_sample_info()` - Extract metadata

### `macro_mapping/` - Macro Controls

**Purpose:** Add macro mappings and modify device parameters
**Classes:**
- `DrumPadColorMapper` - Auto-color drum pads by type
- `TransposeMapper` - Add transpose control to samplers

**Color Scheme:**
- Kicks: Orange (index 60)
- Snares: Red (index 59)
- Hats: Yellow (index 62)
- Claps: Pink (index 58)
- Toms: Purple (index 49)
- Cymbals: Blue (index 45)
- Perc: Green (index 16)

### `cli.py` - Command-Line Interface

**Purpose:** Terminal interface for all features
**Dependencies:** `click>=8.0.0` (optional)
**Commands:**
- `adc drum-rack create|color|remap`
- `adc sampler create`
- `adc simpler create`
- `adc util decode|encode|info`

## Templates

**Location:** `templates/`

**Required templates:**
- `input_rack.adg` - Drum rack template (32 pads, no samples)
- `sampler-rack.adg` - Multi-Sampler template (no samples)
- `simpler-template.adv` - Simpler template (no sample)

**Creating templates:**
1. Create empty device in Ableton Live
2. Configure desired settings (envelopes, filters, etc.)
3. Save as preset
4. Remove sample references if needed
5. Test with toolkit

## Output

**Default location:** `output/`
**File naming:** Auto-generated based on input folder name
**Paths in devices:** Absolute paths for reliability

## Supported Audio Formats

- .wav (primary)
- .aif, .aiff (AIFF)
- .flac (lossless)
- .mp3 (lossy)

## Common Issues & Solutions

### "Template not found"
- Ensure template path is correct
- Default templates in `templates/` directory
- Use absolute paths or relative to CWD

### "No samples found"
- Check folder contains supported audio files
- Use `--recursive` flag for nested folders
- Verify file permissions

### "Device won't load in Ableton"
- File likely corrupted during encoding
- Check roundtrip: decode → encode → decode
- Ensure XML is well-formed
- Test with minimal template

### "Click not installed" (CLI only)
- Install: `pip install click>=8.0.0`
- Or use Python API directly

## Documentation

- **[README.md](README.md)** - Main documentation
- **[docs/CLI_GUIDE.md](docs/CLI_GUIDE.md)** - CLI reference
- **[docs/api/](docs/api/)** - API documentation
- **[examples/](examples/)** - Usage examples
- **[docs/current-plan/V3_IMPLEMENTATION_PLAN.md](docs/current-plan/V3_IMPLEMENTATION_PLAN.md)** - Development history

## Version History

- **V3.0.0** (Nov 2025) - Modern Python package, CLI, production-ready
- **V2.0.0** (Nov 2024) - 111 production scripts
- **V1.0.0** - Original proof-of-concept

## Notes

- All paths in generated devices use absolute paths for reliability
- Scripts are designed to handle large sample libraries efficiently
- Error handling allows operations to continue if individual samples fail
- Manual testing in Ableton Live is the primary validation method
- CLI is optional (requires Click), Python API always works
