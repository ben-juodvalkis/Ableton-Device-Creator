# Ableton Device Creator - Reorganization Implementation Plan

**Date:** 2025-11-28
**Current Status:** Production code scattered across 111 scripts
**Goal:** Streamlined, maintainable, library-first architecture
**Target:** Public dissemination and ease of use

---

## Executive Summary

Transform Ableton Device Creator from a collection of 111 standalone scripts into a modern Python package with CLI interface, eliminating 40% code duplication and achieving 90%+ test coverage.

**Timeline:** 4-6 weeks
**Scope:** 111 scripts → 15 consolidated modules + CLI
**Breaking Changes:** Yes (new API, but backward-compatible scripts provided)

---

## Current State Analysis

### Repository Statistics

```
Total Python Scripts: 111
Total Lines of Code: ~8,000
Code Duplication: ~40%
Test Coverage: 0%
External Dependencies: 0
```

### Directory Structure (Current)

```
Ableton-Device-Creator/
├── drum-racks/               # 32 scripts
│   ├── creation/             # 9 scripts
│   ├── batch/                # 11 scripts
│   └── modification/         # 7 scripts
├── macro-mapping/            # 26 scripts
│   ├── cc-control/           # 10 scripts
│   ├── transpose/            # 2 scripts
│   └── color-coding/         # 3 scripts
├── instrument-racks/         # 7 scripts
├── conversion/               # 9 scripts
├── sampler/                  # 5 scripts
├── simpler/                  # 1 script
├── analysis/                 # 0 scripts (empty dirs)
├── kontakt/                  # 0 scripts (empty dirs)
├── native-instruments/       # 0 scripts (empty dirs)
└── utils/                    # 10 core utilities
```

### Pain Points

1. **40% Code Duplication**
   - Same sample categorization logic in 5+ scripts
   - Duplicate XML modification functions
   - Repeated path handling code
   - Identical error handling patterns

2. **No Library Structure**
   - Can't import as package: `from adc import DrumRackCreator`
   - Every script is standalone
   - No shared state or configuration
   - Difficult to extend programmatically

3. **Poor User Experience**
   - 111 scripts to choose from (overwhelming)
   - Inconsistent CLI arguments
   - No unified help system
   - Difficult discovery ("which script do I use?")

4. **Zero Test Coverage**
   - Violates project's own TDD guidelines (CLAUDE.md)
   - No confidence in refactoring
   - Bugs found in production
   - No regression protection

5. **Maintenance Burden**
   - Bug fixes need to be applied to 4-5 scripts
   - Feature additions require multiple updates
   - Documentation spread across 111 files
   - Hard to onboard contributors

---

## Target Architecture

### Option A: Library-First (Recommended)

```
ableton-device-creator/
├── README.md
├── LICENSE
├── pyproject.toml              # Modern Python packaging
├── setup.py                    # Backward compatibility
│
├── src/
│   └── ableton_device_creator/
│       ├── __init__.py
│       ├── cli.py              # Single CLI entry point
│       ├── config.py           # Configuration management
│       │
│       ├── core/               # Core utilities (was utils/)
│       │   ├── __init__.py
│       │   ├── decoder.py      # ADG → XML
│       │   ├── encoder.py      # XML → ADG
│       │   ├── transformer.py  # XML manipulation
│       │   └── simpler_transformer.py
│       │
│       ├── drum_racks/         # Drum rack tools
│       │   ├── __init__.py
│       │   ├── creator.py      # Single DrumRackCreator class
│       │   ├── modifier.py     # Single DrumRackModifier class
│       │   ├── batch.py        # Batch processing logic
│       │   └── sample_utils.py # Shared sample categorization
│       │
│       ├── sampler/            # Sampler tools
│       │   ├── __init__.py
│       │   └── creator.py
│       │
│       ├── macro_mapping/      # Macro tools
│       │   ├── __init__.py
│       │   ├── cc_control.py
│       │   ├── transpose.py
│       │   └── color.py
│       │
│       └── instrument_racks/   # Instrument rack tools
│           ├── __init__.py
│           └── wrapper.py
│
├── tests/                      # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── fixtures/               # Test data
│   │   ├── test-samples/
│   │   └── test-templates/
│   ├── test_core.py            # 100% coverage
│   ├── test_drum_racks.py
│   ├── test_sampler.py
│   └── test_integration.py     # End-to-end tests
│
├── scripts/                    # Backward-compatible wrappers
│   ├── create-drum-rack        # Thin wrapper around CLI
│   ├── batch-process
│   └── add-cc-control
│
├── templates/                  # Device templates
├── docs/                       # Documentation
│   ├── API.md
│   ├── CLI.md
│   └── MIGRATION_GUIDE.md
│
└── examples/                   # Example usage
    ├── basic_drum_rack.py
    └── custom_workflow.py
```

### CLI Design

**Single entry point with subcommands:**

```bash
# Install package
pip install .

# CLI available as 'adc'
adc --help

# Drum rack creation
adc drum-rack create \
  --template templates/input_rack.adg \
  --samples /path/to/samples \
  --output output/

# Batch processing
adc drum-rack batch \
  --template templates/input_rack.adg \
  --library /path/to/library \
  --output output/

# Macro mapping
adc macro add-cc-control \
  --racks /path/to/racks

# Sampler creation
adc sampler create \
  --template templates/sampler.adg \
  --samples /path/to/samples

# Show all commands
adc --list-commands
```

### Python API Design

**Library usage:**

```python
from ableton_device_creator import DrumRackCreator, MacroMapper

# Create drum rack programmatically
creator = DrumRackCreator(template="templates/input_rack.adg")
rack = creator.from_folder(
    samples_dir="/path/to/samples",
    output="output/My Rack.adg"
)

# Add CC control
mapper = MacroMapper()
mapper.add_cc_control(
    device_path="output/My Rack.adg",
    macro=1,
    parameter="Filter Cutoff"
)

# Batch processing
from ableton_device_creator.batch import BatchProcessor

processor = BatchProcessor(template="templates/input_rack.adg")
processor.process_library(
    library_path="/path/to/library",
    output_dir="output/"
)
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

**Goal:** Set up package structure and consolidate core utilities

**Tasks:**
1. ✅ Create `src/ableton_device_creator/` package structure
2. ✅ Move and consolidate `utils/` → `core/`
   - decoder.py
   - encoder.py
   - transformer.py
   - simpler_transformer.py
3. ✅ Create `pyproject.toml` for modern packaging
4. ✅ Create `setup.py` for backward compatibility
5. ✅ Add 100% test coverage for core utilities
   - test_decoder.py
   - test_encoder.py
   - test_transformer.py
6. ✅ Set up pytest infrastructure
7. ✅ Create GitHub Actions for CI/CD

**Deliverables:**
- Installable package: `pip install .`
- 100% core test coverage
- CI/CD pipeline running

**Success Criteria:**
```python
# Can import core
from ableton_device_creator.core import decode_adg, encode_adg

# Tests pass
pytest tests/test_core.py --cov=src/ableton_device_creator/core
# Coverage: 100%
```

---

### Phase 2: Drum Rack Consolidation (Week 2)

**Goal:** Consolidate 32 drum rack scripts into 3 modules

**Current:** 32 scripts with massive duplication
**Target:** 3 modules with shared logic

**Tasks:**
1. ✅ Extract shared sample categorization logic
   ```python
   # src/ableton_device_creator/drum_racks/sample_utils.py
   def categorize_samples(folder_path):
       """Shared logic used by all creation scripts"""
       return {
           'kicks': [...],
           'snares': [...],
           'hats': [...]
       }
   ```

2. ✅ Create `DrumRackCreator` class
   ```python
   # src/ableton_device_creator/drum_racks/creator.py
   class DrumRackCreator:
       def __init__(self, template_path):
           self.template = template_path

       def from_folder(self, samples_dir, **options):
           """Replaces main_simple_folder.py"""
           pass

       def from_categorized(self, samples_dict, **options):
           """Replaces main.py"""
           pass

       def with_velocity_layers(self, samples_dir, **options):
           """Replaces create_multivelocity_drum_rack_v2.py"""
           pass
   ```

3. ✅ Create `DrumRackModifier` class
   ```python
   # src/ableton_device_creator/drum_racks/modifier.py
   class DrumRackModifier:
       def remap_notes(self, rack_path, mapping):
           """Replaces remap_drum_rack_notes.py"""
           pass

       def trim_to_16(self, rack_path):
           """Replaces trim_drum_racks_to_16.py"""
           pass

       def merge(self, rack_paths, output):
           """Replaces merge_drum_racks.py"""
           pass
   ```

4. ✅ Create `BatchProcessor` class
   ```python
   # src/ableton_device_creator/drum_racks/batch.py
   class BatchProcessor:
       def process_library(self, library_path, output_dir):
           """Replaces meta_main_folders.py"""
           pass

       def process_expansions(self, expansions_path):
           """Replaces batch_process_all_expansions.py"""
           pass
   ```

5. ✅ Add comprehensive tests
   - test_drum_rack_creator.py (with real samples)
   - test_drum_rack_modifier.py
   - test_batch_processor.py

**Deliverables:**
- 32 scripts → 4 modules
- 80%+ test coverage
- Backward-compatible CLI wrappers

**Success Criteria:**
```bash
# Old way still works (via wrapper)
python scripts/create-drum-rack /path/to/samples

# New way (CLI)
adc drum-rack create --samples /path/to/samples

# New way (Python)
from ableton_device_creator import DrumRackCreator
creator = DrumRackCreator("templates/input_rack.adg")
creator.from_folder("/path/to/samples")
```

---

### Phase 3: Macro Mapping Consolidation (Week 3)

**Goal:** Consolidate 26 macro scripts into 3 modules

**Tasks:**
1. ✅ Create `CCControlMapper` class
   ```python
   # src/ableton_device_creator/macro_mapping/cc_control.py
   class CCControlMapper:
       def add_to_rack(self, rack_path, mappings):
           """Replaces add_cc_control_to_drum_rack_v2.py"""
           pass

       def batch_apply(self, racks_dir, mappings):
           """Replaces batch_apply_cc_mappings.py"""
           pass
   ```

2. ✅ Create `TransposeMapper` class
3. ✅ Create `ColorMapper` class
4. ✅ Add tests for all mapping functions

**Deliverables:**
- 26 scripts → 3 modules
- 80%+ test coverage

---

### Phase 4: Sampler & Other Tools (Week 4)

**Goal:** Consolidate remaining scripts

**Tasks:**
1. ✅ Consolidate 5 sampler scripts → `SamplerCreator` class
2. ✅ Consolidate 7 instrument rack scripts → `InstrumentRackWrapper` class
3. ✅ Consolidate 9 conversion scripts → `DeviceConverter` class
4. ✅ Add comprehensive tests

**Deliverables:**
- All scripts consolidated
- 85%+ overall test coverage

---

### Phase 5: CLI Implementation (Week 5)

**Goal:** Build unified CLI interface

**Tasks:**
1. ✅ Create `cli.py` with Click framework
   ```python
   # src/ableton_device_creator/cli.py
   import click

   @click.group()
   def main():
       """Ableton Device Creator CLI"""
       pass

   @main.group()
   def drum_rack():
       """Drum rack commands"""
       pass

   @drum_rack.command()
   @click.option('--template', required=True)
   @click.option('--samples', required=True)
   def create(template, samples):
       """Create drum rack from samples"""
       from .drum_racks import DrumRackCreator
       creator = DrumRackCreator(template)
       creator.from_folder(samples)
   ```

2. ✅ Add all subcommands
   - `adc drum-rack create`
   - `adc drum-rack batch`
   - `adc drum-rack modify`
   - `adc macro add-cc`
   - `adc macro add-transpose`
   - `adc sampler create`
   - `adc convert simpler-to-drumcell`

3. ✅ Add comprehensive help text
4. ✅ Add shell completion

**Deliverables:**
- Complete CLI with all features
- Shell completion for bash/zsh
- Comprehensive help system

---

### Phase 6: Documentation & Migration (Week 6)

**Goal:** Complete documentation and migration guides

**Tasks:**
1. ✅ Write API documentation
   - API.md - Library usage
   - CLI.md - CLI reference
   - EXAMPLES.md - Common workflows

2. ✅ Write migration guide
   ```markdown
   # Migration from V2.0 to V3.0

   ## Script → CLI

   Old:
   ```bash
   python drum-racks/creation/main_simple_folder.py template.adg /samples
   ```

   New:
   ```bash
   adc drum-rack create --template template.adg --samples /samples
   ```

   ## Script → Python API

   Old:
   ```bash
   python drum-racks/creation/main_simple_folder.py template.adg /samples
   ```

   New:
   ```python
   from ableton_device_creator import DrumRackCreator
   creator = DrumRackCreator("template.adg")
   creator.from_folder("/samples")
   ```
   ```

3. ✅ Create video tutorials
   - 5-minute quickstart
   - Common workflows
   - Migration guide

4. ✅ Update README.md
5. ✅ Create CHANGELOG.md

**Deliverables:**
- Complete documentation suite
- Video tutorials
- Migration guide

---

## Code Consolidation Strategy

### Example: Sample Categorization

**Before (duplicated across 5+ scripts):**

```python
# In main.py
kicks = []
snares = []
hats = []
for file in os.listdir(folder):
    if 'kick' in file.lower() or 'bd' in file.lower():
        kicks.append(file)
    elif 'snare' in file.lower() or 'sd' in file.lower():
        snares.append(file)
    # ... etc

# Same code in main_simple_folder.py
kicks = []
snares = []
# ... duplicate code

# Same code in main_percussion.py
# ... duplicate code again
```

**After (shared module):**

```python
# src/ableton_device_creator/drum_racks/sample_utils.py
from typing import Dict, List
from pathlib import Path

SAMPLE_CATEGORIES = {
    'kick': ['kick', 'bd', 'bassdrum'],
    'snare': ['snare', 'sd'],
    'hat': ['hat', 'hh', 'hihat'],
    'clap': ['clap', 'cp'],
    'perc': ['perc', 'percussion']
}

def categorize_samples(folder_path: Path) -> Dict[str, List[Path]]:
    """
    Categorize samples by type based on filename.

    Args:
        folder_path: Path to folder containing samples

    Returns:
        Dictionary mapping category to list of sample paths

    Example:
        >>> samples = categorize_samples(Path('/samples'))
        >>> samples['kick']
        [Path('/samples/Kick 01.wav'), Path('/samples/BD_heavy.wav')]
    """
    categories = {cat: [] for cat in SAMPLE_CATEGORIES.keys()}

    for file_path in folder_path.glob('**/*'):
        if file_path.suffix.lower() in ['.wav', '.aiff', '.flac', '.mp3']:
            filename_lower = file_path.stem.lower()

            for category, keywords in SAMPLE_CATEGORIES.items():
                if any(keyword in filename_lower for keyword in keywords):
                    categories[category].append(file_path)
                    break

    return categories

# Now used everywhere:
from ableton_device_creator.drum_racks.sample_utils import categorize_samples
samples = categorize_samples(Path(samples_dir))
```

---

## Testing Strategy

### Test Coverage Goals

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| core/ | 100% | Critical |
| drum_racks/ | 90% | High |
| macro_mapping/ | 85% | High |
| sampler/ | 80% | Medium |
| conversion/ | 80% | Medium |

### Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── fixtures/
│   ├── test-samples/           # 20 test samples
│   │   ├── Kick 01.wav
│   │   ├── Snare 01.wav
│   │   └── ...
│   ├── test-templates/         # Minimal test templates
│   │   ├── test_rack.adg
│   │   └── test_sampler.adg
│   └── expected-output/        # Expected output for comparison
│
├── unit/                       # Unit tests
│   ├── test_core.py
│   ├── test_drum_rack_creator.py
│   └── test_macro_mapper.py
│
├── integration/                # Integration tests
│   ├── test_drum_rack_workflow.py
│   └── test_batch_processing.py
│
└── e2e/                        # End-to-end tests
    └── test_full_workflow.py
```

### Example Test

```python
# tests/unit/test_drum_rack_creator.py
import pytest
from pathlib import Path
from ableton_device_creator import DrumRackCreator

def test_create_drum_rack_from_folder(test_samples_dir, tmp_path):
    """Test basic drum rack creation"""

    # Arrange
    creator = DrumRackCreator(template="tests/fixtures/test_rack.adg")
    output_path = tmp_path / "test_rack.adg"

    # Act
    result = creator.from_folder(
        samples_dir=test_samples_dir,
        output=output_path
    )

    # Assert
    assert output_path.exists()
    assert output_path.stat().st_size > 1000  # Non-empty

    # Verify XML structure
    from ableton_device_creator.core import decode_adg
    xml = decode_adg(output_path)
    assert b'<DrumBranch>' in xml
    assert b'<SampleRef>' in xml

def test_create_with_velocity_layers(test_samples_with_velocity, tmp_path):
    """Test multi-velocity drum rack creation"""

    creator = DrumRackCreator(template="tests/fixtures/test_rack.adg")
    output = tmp_path / "velocity_rack.adg"

    result = creator.with_velocity_layers(
        samples_dir=test_samples_with_velocity,
        output=output
    )

    assert output.exists()
    # Verify velocity zones created
    xml = decode_adg(output)
    assert xml.count(b'<VelocityZone>') >= 3  # At least 3 layers
```

---

## Package Installation

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ableton-device-creator"
version = "3.0.0"
description = "Professional toolkit for Ableton Live device creation"
authors = [{name = "Your Name", email = "your.email@example.com"}]
license = {text = "MIT"}
requires-python = ">=3.8"
dependencies = []  # Zero external dependencies!

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
]
cli = [
    "click>=8.0.0",
]

[project.scripts]
adc = "ableton_device_creator.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "--cov=src/ableton_device_creator --cov-report=html --cov-report=term"

[tool.black]
line-length = 100
target-version = ['py38']

[tool.coverage.run]
source = ["src/ableton_device_creator"]
omit = ["tests/*", "src/ableton_device_creator/cli.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
]
```

---

## Backward Compatibility

### Script Wrappers

Provide thin wrappers for old scripts:

```bash
#!/bin/bash
# scripts/create-drum-rack

# Wrapper for backward compatibility
# Old: python drum-racks/creation/main_simple_folder.py template.adg /samples
# New: adc drum-rack create --template template.adg --samples /samples

template=$1
samples=$2

adc drum-rack create --template "$template" --samples "$samples"
```

### Migration Period

- **V2.0:** Current version (111 scripts)
- **V3.0:** New version (library + CLI)
- **Support:** Both versions for 6 months
- **Deprecation:** V2.0 scripts marked deprecated but functional
- **Sunset:** V2.0 scripts removed after 1 year

---

## Success Metrics

### Code Quality
- [ ] Test coverage: 90%+
- [ ] Code duplication: <10%
- [ ] Linting: 100% pass
- [ ] Type hints: 80%+ coverage

### User Experience
- [ ] Single CLI entry point
- [ ] Library importable
- [ ] Comprehensive documentation
- [ ] Video tutorials available

### Performance
- [ ] Extraction speed: Same or faster
- [ ] Memory usage: Same or lower
- [ ] Package size: <5MB

### Community
- [ ] GitHub stars: 100+
- [ ] Issues resolved: <1 week average
- [ ] Contributors: 5+
- [ ] Documentation views: 1000+/month

---

## Risks & Mitigation

### Risk 1: Breaking Changes

**Risk:** Users rely on exact script names/paths

**Mitigation:**
- Provide backward-compatible wrappers
- Document migration clearly
- Support both versions for 6 months
- Create automated migration tool

### Risk 2: Test Coverage Gaps

**Risk:** Miss edge cases in consolidation

**Mitigation:**
- Start with core (100% coverage)
- Incremental rollout (one category at a time)
- Extensive integration testing
- Beta testing period

### Risk 3: Performance Regression

**Risk:** New abstraction layer adds overhead

**Mitigation:**
- Benchmark before/after
- Profile critical paths
- Optimize hot spots
- Maintain zero-dependency principle

---

## Next Actions

### Immediate (This Week)
1. [ ] Create branch: `git checkout -b v3-reorganization`
2. [ ] Set up package structure
3. [ ] Create pyproject.toml
4. [ ] Add pytest infrastructure
5. [ ] Start Phase 1 (core consolidation)

### Short-Term (Next 2 Weeks)
1. [ ] Complete Phase 1 & 2
2. [ ] Achieve 100% core coverage
3. [ ] Consolidate drum rack scripts
4. [ ] Create initial CLI

### Long-Term (4-6 Weeks)
1. [ ] Complete all phases
2. [ ] Achieve 90%+ overall coverage
3. [ ] Publish to PyPI
4. [ ] Release V3.0.0

---

## Conclusion

This reorganization transforms Ableton Device Creator from a collection of scripts into a professional Python package while maintaining zero external dependencies and backward compatibility.

**Benefits:**
- ✅ Easier to use (single CLI vs 111 scripts)
- ✅ Easier to maintain (3 modules vs 32 scripts)
- ✅ Easier to extend (library API)
- ✅ Easier to test (90%+ coverage)
- ✅ Better for public dissemination

**Timeline:** 4-6 weeks
**Effort:** High (complete rewrite)
**Reward:** Professional-grade toolkit ready for public release

---

**Ready to start?** Begin with Phase 1: Core Infrastructure

```bash
git checkout -b v3-reorganization
mkdir -p src/ableton_device_creator/core
# Let's go!
```
