# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ableton Device Creator is a Python-based toolkit for creating and modifying Ableton Live devices (drum racks, sampler instruments, and Simpler devices) from audio sample libraries.

## Key Technical Information

### ADG/ADV File Format
- ADG (Ableton Device Group) and ADV (Ableton Device) files are **gzipped XML files**
- Core workflow: Decompress → Modify XML → Recompress
- Key utilities in `scripts/utils/`:
  - `adg_encoder.py` - Encode XML to ADG
  - `adg_decoder.py` - Decode ADG to XML
  - `adg_xml_modifier.py` - XML transformation utilities

### Example ADG Modification Workflow
```python
# 1. Decode ADG to XML
python scripts/utils/adg_decoder.py "path/to/device.adg"

# 2. Modify the XML file as needed

# 3. Re-encode to ADG
python scripts/utils/adg_encoder.py "path/to/device.xml"
```

## Common Commands

### Drum Rack Creation
```bash
# Standard drum rack (32 pads)
python scripts/device/create_drum_rack.py /path/to/sample_library

# Drum racks organized by subfolder type
python scripts/device/create_drum_rack_from_folder.py /path/to/library "Drum Rack Name"

# Percussion-only drum rack
python scripts/device/create_drum_rack_perc_only.py /path/to/percussion_samples
```

### Sampler Instrument Creation
```bash
# Standard sampler (32 samples mapped chromatically)
python scripts/device/create_sampler_instrument.py /path/to/samples

# Drum-style sampler (8 kicks, 8 snares, etc.)
python scripts/device/create_sampler_instrument_drum_layout.py /path/to/drum_samples

# Phrase/loop sampler
python scripts/device/create_sampler_phrases.py /path/to/phrases_or_loops
```

### Simpler Device Creation
```bash
# Create individual Simpler devices for each sample
python scripts/device/create_simpler_device.py /path/to/samples
```

### Utility Commands
```bash
# Generate macro controls XML
python scripts/utils/adg_macro_xml_gen.py

# Update scroll position in ADG
python scripts/utils/update_macro_scroll_position.py /path/to/device.adg
```

## Important Script Behaviors

### Drum Rack Scripts
- Creates 32-pad drum racks (C1 to G3)
- Organizes samples by type when using folder-based scripts
- Handles kicks, snares, hi-hats, claps, and other percussion types
- Creates separate racks when more than 32 samples of one type

### Sampler Scripts  
- Maps 32 samples chromatically starting from C-2
- Creates new sampler devices for each 32-sample batch
- Drum layout variant: 8 kicks (C-2 to G-2), 8 snares (G#-2 to D#-1), etc.
- Phrase variant: Handles loops and musical phrases

### Simpler Scripts
- Creates one device per sample
- Maintains folder structure in output
- Simplest device type for basic sample playback

### Batch Processing
- Scripts in `scripts/meta/` process entire directories recursively
- Maintain original folder structures in output
- Handle Native Instruments expansion packs

## Key Directories
- `/scripts/device/` - Main device creation scripts
- `/scripts/utils/` - ADG encoding/decoding utilities  
- `/scripts/meta/` - Batch processing scripts
- `/scripts/max/` - Max/MSP JavaScript integration
- `/src/` - TypeScript/Node.js components

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

### Future Testing (V3.0+)

When transitioning to library-first architecture, targeted testing will be added:

**Test priorities:**
1. **Core utilities** - encoder/decoder roundtrip tests
2. **Sample categorization** - ensure kicks/snares/hats are detected correctly
3. **Integration tests** - can we create a working drum rack end-to-end?

**Target coverage:** 60-80% (focus on complex logic, not simple file I/O)

**Testing tools (optional):**
```bash
# Install testing dependencies (optional)
pip install pytest pytest-cov

# Run basic integration tests
python -m pytest tests/

# Generate coverage report
python -m pytest --cov=src --cov-report=html
```

## Requirements
- Python 3.8+
- Supported audio formats: .wav, .aiff, .flac, .mp3
- Output devices are placed in `/output/` directory
- **Testing dependencies (optional):** pytest, pytest-cov

## Code Quality Principles

### What Matters Most
1. **Does it work in Ableton?** - The ultimate test
2. **Is it production-proven?** - Real-world usage over synthetic tests
3. **Is the code readable?** - Clear logic over clever tricks
4. **Zero dependencies** - Keep it simple and portable

### Code Review Checklist
- [ ] Script tested manually in Ableton Live
- [ ] Error handling for common failure cases (missing files, invalid paths)
- [ ] Code is readable and well-commented
- [ ] No external dependencies added
- [ ] Documentation updated if behavior changes

## Notes
- All paths in generated devices use absolute paths for reliability
- Scripts are designed to handle large sample libraries efficiently
- Error handling allows scripts to continue even if individual samples fail
- Manual testing in Ableton Live is the primary validation method