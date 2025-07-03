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

### Test-Driven Development (TDD)
This project follows strict TDD principles. **Always write tests first before implementing any new functionality.**

1. **Red Phase**: Write a failing test that defines the desired behavior
2. **Green Phase**: Write the minimal code to make the test pass
3. **Refactor Phase**: Improve the code while keeping tests green

### Testing Strategy
- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test interactions between components
- **E2E Tests**: Test complete workflows from user perspective

## Testing Commands

### Python Testing (Current Implementation)
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=scripts --cov-report=html

# Run specific test file
python -m pytest tests/test_adg_encoder.py

# Run tests matching pattern
python -m pytest -k "test_drum_rack"

# Run tests in watch mode
python -m pytest-watch
```

### JavaScript/TypeScript Testing (Future Web App)
```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run unit tests only
npm run test:unit

# Run integration tests
npm run test:integration

# Run E2E tests
npm run test:e2e

# Generate coverage report
npm run test:coverage
```

## Requirements
- Python 3.6+
- pytest for Python testing
- pytest-cov for coverage reports
- pytest-watch for continuous testing
- Supported audio formats: .wav, .aiff, .flac, .mp3
- Output devices are placed in `/output/` directory

## TDD Workflow Example

When implementing a new feature:
```bash
# 1. Create test file first
touch tests/test_new_feature.py

# 2. Write failing test
# 3. Run test to confirm it fails
python -m pytest tests/test_new_feature.py

# 4. Implement minimal code to pass
# 5. Run test to confirm it passes
python -m pytest tests/test_new_feature.py

# 6. Refactor if needed
# 7. Run all tests to ensure nothing broke
python -m pytest

# 8. Check coverage
python -m pytest --cov=scripts
```

## Code Review Checklist
- [ ] All new code has corresponding tests
- [ ] Tests are written before implementation (TDD)
- [ ] All tests pass locally
- [ ] Code coverage is maintained or improved
- [ ] Integration tests cover main workflows
- [ ] E2E tests verify user-facing functionality

## Notes
- All paths in generated devices use absolute paths for reliability
- Scripts are designed to handle large sample libraries efficiently
- Error handling allows scripts to continue even if individual samples fail
- **Every bug fix must include a test that reproduces the bug**
- **No code changes without tests**