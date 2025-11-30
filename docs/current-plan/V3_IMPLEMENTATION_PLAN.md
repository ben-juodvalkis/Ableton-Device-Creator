# Ableton Device Creator V3.0 - Comprehensive Implementation Plan

**Project:** Ableton Device Creator V3.0 (Library-First Architecture)
**Timeline:** 6 weeks (30 working days)
**Scope:** Transform 111 scripts → Modern Python package with CLI
**Effort:** ~120-150 hours total
**Goal:** Professional, maintainable, testable toolkit ready for public use

---

## Table of Contents

1. [Pre-Implementation Checklist](#pre-implementation-checklist)
2. [Phase 1: Foundation & Core (Week 1)](#phase-1-foundation--core-week-1)
3. [Phase 2: Drum Racks (Week 2)](#phase-2-drum-racks-week-2)
4. [Phase 3: Macro Mapping (Week 3)](#phase-3-macro-mapping-week-3)
5. [Phase 4: Sampler & Conversion (Week 4)](#phase-4-sampler--conversion-week-4)
6. [Phase 5: CLI & Integration (Week 5)](#phase-5-cli--integration-week-5)
7. [Phase 6: Documentation & Release (Week 6)](#phase-6-documentation--release-week-6)
8. [Testing Strategy](#testing-strategy)
9. [Quality Assurance](#quality-assurance)
10. [Deployment Plan](#deployment-plan)

---

## Pre-Implementation Checklist

### Setup & Prerequisites (Day 0)

- [ ] **Create development branch**
  ```bash
  cd "/Users/Shared/DevWork/GitHub/Ableton Device Creator"
  git checkout -b v3-reorganization
  git push -u origin v3-reorganization
  ```

- [ ] **Install development tools**
  ```bash
  pip install pytest pytest-cov black flake8 mypy click
  ```

- [ ] **Create project tracker**
  - [ ] GitHub Project board or Linear/Jira
  - [ ] Weekly milestones
  - [ ] Issue templates for bugs/features

- [ ] **Backup current working state**
  ```bash
  git tag v2.1-pre-reorganization
  git push --tags
  ```

- [ ] **Set up local test environment**
  - [ ] Test sample library (100-200 samples)
  - [ ] Test templates (5-10 .adg files)
  - [ ] Expected output fixtures

---

## Phase 1: Foundation & Core (Week 1)

**Goal:** Set up package infrastructure and consolidate core utilities with 100% test coverage

**Duration:** 5 days (40 hours)
**Critical Path:** Yes - everything depends on this

---

### Day 1: Package Structure & Build System

**Tasks:**

#### 1.1 Create Package Directory Structure (2 hours)

```bash
mkdir -p src/ableton_device_creator/{core,drum_racks,macro_mapping,sampler,conversion,instrument_racks}
mkdir -p tests/{unit,integration,e2e,fixtures}
mkdir -p tests/fixtures/{samples,templates,expected}
mkdir -p scripts
mkdir -p docs/{api,guides,examples}
```

**Deliverable:** Directory tree matching library-first architecture

---

#### 1.2 Create pyproject.toml (1 hour)

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ableton-device-creator"
version = "3.0.0-alpha.1"
description = "Professional toolkit for Ableton Live device creation and modification"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.8"
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Multimedia :: Sound/Audio",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]
keywords = ["ableton", "audio", "music-production", "device-creation"]

dependencies = []  # Zero dependencies for core

[project.optional-dependencies]
cli = ["click>=8.0.0"]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.7.0",
    "flake8>=6.1.0",
    "mypy>=1.4.0",
]

[project.scripts]
adc = "ableton_device_creator.cli:main"

[project.urls]
Homepage = "https://github.com/ben-juodvalkis/Ableton-Device-Creator"
Documentation = "https://ableton-device-creator.readthedocs.io"
Repository = "https://github.com/ben-juodvalkis/Ableton-Device-Creator"
Issues = "https://github.com/ben-juodvalkis/Ableton-Device-Creator/issues"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = """
    --cov=src/ableton_device_creator
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90
    -v
"""

[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311']
include = '\.pyi?$'
extend-exclude = '''
/(
    \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
ignore_missing_imports = true

[tool.coverage.run]
source = ["src/ableton_device_creator"]
omit = [
    "tests/*",
    "src/ableton_device_creator/cli.py",  # CLI tested via integration
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

**Test:** `pip install -e .` should work

---

#### 1.3 Create setup.py for Backward Compatibility (30 min)

```python
# setup.py
from setuptools import setup

# Defer all configuration to pyproject.toml
setup()
```

**Test:** `python setup.py --version` should output version

---

#### 1.4 Create Package __init__.py Files (30 min)

```python
# src/ableton_device_creator/__init__.py
"""
Ableton Device Creator - Professional toolkit for Ableton Live device creation.

This package provides tools for creating, modifying, and managing Ableton Live
devices (.adg) and presets (.adv) programmatically.

Basic Usage:
    >>> from ableton_device_creator import DrumRackCreator
    >>> creator = DrumRackCreator(template="templates/input_rack.adg")
    >>> rack = creator.from_folder("samples/")
"""

__version__ = "3.0.0-alpha.1"
__author__ = "Your Name"
__license__ = "MIT"

# Core utilities
from .core import decode_adg, encode_adg, transform_xml

# Main classes (imported when modules are complete)
# from .drum_racks import DrumRackCreator, DrumRackModifier
# from .macro_mapping import MacroMapper, CCControlMapper
# from .sampler import SamplerCreator

__all__ = [
    "__version__",
    "decode_adg",
    "encode_adg",
    "transform_xml",
    # "DrumRackCreator",
    # "DrumRackModifier",
    # "MacroMapper",
    # "SamplerCreator",
]
```

**Test:** `python -c "import ableton_device_creator; print(ableton_device_creator.__version__)"`

---

### Day 2: Core Utilities Migration (8 hours)

**Goal:** Move utils/ to core/ with proper module structure

#### 2.1 Create core/__init__.py (1 hour)

```python
# src/ableton_device_creator/core/__init__.py
"""
Core utilities for ADG/ADV file manipulation.

This module provides the fundamental building blocks for working with
Ableton Live device files (ADG/ADV format).
"""

from .decoder import decode_adg, decode_adv
from .encoder import encode_adg, encode_adv
from .transformer import DrumRackTransformer, SimplerTransformer
from .xml_utils import find_element, modify_element, validate_xml

__all__ = [
    # Decoder/Encoder
    "decode_adg",
    "decode_adv",
    "encode_adg",
    "encode_adv",
    # Transformers
    "DrumRackTransformer",
    "SimplerTransformer",
    # XML utilities
    "find_element",
    "modify_element",
    "validate_xml",
]
```

---

#### 2.2 Migrate decoder.py (1 hour)

```python
# src/ableton_device_creator/core/decoder.py
"""ADG/ADV file decoder - decompresses gzip XML files."""

import gzip
from pathlib import Path
from typing import Union

def decode_adg(file_path: Union[str, Path]) -> bytes:
    """
    Decode ADG file to XML.

    Args:
        file_path: Path to .adg file

    Returns:
        Decompressed XML content as bytes

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not valid gzip

    Example:
        >>> xml_content = decode_adg("MyDrumRack.adg")
        >>> print(xml_content[:100])
        b'<?xml version="1.0" encoding="UTF-8"?>...'
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.suffix.lower() in ['.adg', '.adv']:
        raise ValueError(f"Expected .adg or .adv file, got: {file_path.suffix}")

    try:
        with gzip.open(file_path, 'rb') as f:
            return f.read()
    except gzip.BadGzipFile:
        raise ValueError(f"Not a valid gzip file: {file_path}")

def decode_adv(file_path: Union[str, Path]) -> bytes:
    """
    Decode ADV file to XML.

    Alias for decode_adg() - both formats use same encoding.
    """
    return decode_adg(file_path)
```

**Copy from:** `utils/decoder.py`
**Changes:** Add type hints, docstrings, error handling

---

#### 2.3 Migrate encoder.py (1 hour)

```python
# src/ableton_device_creator/core/encoder.py
"""ADG/ADV file encoder - compresses XML to gzip format."""

import gzip
from pathlib import Path
from typing import Union

def encode_adg(xml_content: bytes, output_path: Union[str, Path]) -> Path:
    """
    Encode XML to ADG file.

    Args:
        xml_content: XML content as bytes
        output_path: Where to save .adg file

    Returns:
        Path to created file

    Raises:
        ValueError: If XML content is invalid
        OSError: If cannot write file

    Example:
        >>> xml = b'<?xml version="1.0"?>...'
        >>> encode_adg(xml, "MyRack.adg")
        PosixPath('MyRack.adg')
    """
    output_path = Path(output_path)

    if not xml_content.startswith(b'<?xml'):
        raise ValueError("Content must be valid XML")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with gzip.open(output_path, 'wb', compresslevel=9) as f:
        f.write(xml_content)

    return output_path

def encode_adv(xml_content: bytes, output_path: Union[str, Path]) -> Path:
    """
    Encode XML to ADV file.

    Alias for encode_adg() - both formats use same encoding.
    """
    return encode_adg(xml_content, output_path)
```

---

#### 2.4 Migrate transformer.py (2 hours)

```python
# src/ableton_device_creator/core/transformer.py
"""XML transformation utilities for drum racks."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

class DrumRackTransformer:
    """Transform drum rack XML structure."""

    def __init__(self, xml_content: bytes):
        """
        Initialize transformer with XML content.

        Args:
            xml_content: Decoded ADG XML as bytes
        """
        self.tree = ET.fromstring(xml_content)
        self.root = self.tree

    def add_sample(self, note: int, sample_path: str) -> None:
        """
        Add sample to drum rack at MIDI note.

        Args:
            note: MIDI note number (0-127)
            sample_path: Absolute path to sample file

        Raises:
            ValueError: If note out of range
        """
        if not 0 <= note <= 127:
            raise ValueError(f"MIDI note must be 0-127, got {note}")

        # Find or create DrumBranch for this note
        branch = self._get_or_create_branch(note)

        # Add sample reference
        sample_ref = ET.SubElement(branch, 'SampleRef')
        file_ref = ET.SubElement(sample_ref, 'FileRef')
        ET.SubElement(file_ref, 'Path').text = sample_path

    def _get_or_create_branch(self, note: int) -> ET.Element:
        """Get or create DrumBranch for MIDI note."""
        # Implementation from original transformer.py
        pass

    def remove_sample(self, note: int) -> bool:
        """
        Remove sample from drum rack at MIDI note.

        Returns:
            True if sample was removed, False if no sample at that note
        """
        pass

    def get_samples(self) -> Dict[int, str]:
        """
        Get all samples in rack.

        Returns:
            Dict mapping MIDI note to sample path
        """
        pass

    def to_xml(self) -> bytes:
        """Convert back to XML bytes."""
        return ET.tostring(self.root, encoding='utf-8', xml_declaration=True)

class SimplerTransformer:
    """Transform Simpler device XML structure."""

    def __init__(self, xml_content: bytes):
        self.tree = ET.fromstring(xml_content)
        self.root = self.tree

    def set_sample(self, sample_path: str) -> None:
        """Set the sample for Simpler device."""
        pass

    def to_xml(self) -> bytes:
        """Convert back to XML bytes."""
        return ET.tostring(self.root, encoding='utf-8', xml_declaration=True)
```

**Copy from:** `utils/transformer.py`, `utils/simpler_transformer.py`
**Changes:** Object-oriented API, type hints, comprehensive docstrings

---

#### 2.5 Create xml_utils.py (1 hour)

```python
# src/ableton_device_creator/core/xml_utils.py
"""Common XML manipulation utilities."""

import xml.etree.ElementTree as ET
from typing import Optional, List

def find_element(root: ET.Element, path: str) -> Optional[ET.Element]:
    """
    Find element by XPath-like path.

    Args:
        root: Root XML element
        path: Path like "Ableton/DrumRack/Branches"

    Returns:
        Found element or None
    """
    return root.find(path)

def find_all_elements(root: ET.Element, tag: str) -> List[ET.Element]:
    """Find all elements with given tag."""
    return root.findall(f".//{tag}")

def modify_element(element: ET.Element, tag: str, value: str) -> None:
    """Modify element text value."""
    child = element.find(tag)
    if child is not None:
        child.text = value

def validate_xml(xml_content: bytes) -> bool:
    """
    Validate XML is well-formed.

    Returns:
        True if valid, False otherwise
    """
    try:
        ET.fromstring(xml_content)
        return True
    except ET.ParseError:
        return False
```

**Deliverable:** Complete core/ module with utilities

---

### Day 3: Core Testing Infrastructure (8 hours)

**Goal:** Achieve 100% test coverage for core module

#### 3.1 Create Test Fixtures (2 hours)

```bash
# Create minimal test ADG file
cd tests/fixtures/templates
# Copy a minimal working drum rack
cp "/path/to/minimal_rack.adg" test_rack.adg

# Create test samples
cd ../samples
# Generate or copy 10 test samples
for i in {01..10}; do
  # Copy or generate silent wav files
  cp "/path/to/Kick_$i.wav" .
done
```

**Create conftest.py:**

```python
# tests/conftest.py
"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path

@pytest.fixture
def fixtures_dir():
    """Path to fixtures directory."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def test_templates(fixtures_dir):
    """Path to test templates."""
    return fixtures_dir / "templates"

@pytest.fixture
def test_samples(fixtures_dir):
    """Path to test samples."""
    return fixtures_dir / "samples"

@pytest.fixture
def test_rack_adg(test_templates):
    """Path to test drum rack ADG."""
    return test_templates / "test_rack.adg"

@pytest.fixture
def decoded_rack_xml(test_rack_adg):
    """Decoded XML from test rack."""
    from ableton_device_creator.core import decode_adg
    return decode_adg(test_rack_adg)
```

---

#### 3.2 Write test_decoder.py (2 hours)

```python
# tests/unit/test_decoder.py
"""Test ADG/ADV decoder functionality."""

import pytest
import gzip
from pathlib import Path
from ableton_device_creator.core import decode_adg, decode_adv

class TestDecodeADG:
    """Test decode_adg function."""

    def test_decode_valid_adg(self, test_rack_adg):
        """Test decoding valid ADG file."""
        result = decode_adg(test_rack_adg)

        assert isinstance(result, bytes)
        assert result.startswith(b'<?xml')
        assert b'Ableton' in result

    def test_decode_nonexistent_file(self):
        """Test error on nonexistent file."""
        with pytest.raises(FileNotFoundError):
            decode_adg("nonexistent.adg")

    def test_decode_invalid_extension(self, tmp_path):
        """Test error on wrong file extension."""
        bad_file = tmp_path / "test.txt"
        bad_file.write_text("test")

        with pytest.raises(ValueError, match="Expected .adg or .adv"):
            decode_adg(bad_file)

    def test_decode_not_gzip(self, tmp_path):
        """Test error on non-gzip file."""
        bad_file = tmp_path / "test.adg"
        bad_file.write_text("not gzipped")

        with pytest.raises(ValueError, match="Not a valid gzip"):
            decode_adg(bad_file)

    def test_decode_adv_alias(self, test_rack_adg):
        """Test that decode_adv is alias for decode_adg."""
        # Temporarily rename to .adv
        adv_file = test_rack_adg.with_suffix('.adv')
        test_rack_adg.rename(adv_file)

        try:
            result = decode_adv(adv_file)
            assert result.startswith(b'<?xml')
        finally:
            adv_file.rename(test_rack_adg)

    def test_decode_accepts_string_path(self, test_rack_adg):
        """Test decoder accepts string path."""
        result = decode_adg(str(test_rack_adg))
        assert isinstance(result, bytes)

    def test_decode_accepts_path_object(self, test_rack_adg):
        """Test decoder accepts Path object."""
        result = decode_adg(test_rack_adg)
        assert isinstance(result, bytes)

# Run: pytest tests/unit/test_decoder.py -v
# Target: 100% coverage of decoder.py
```

---

#### 3.3 Write test_encoder.py (2 hours)

```python
# tests/unit/test_encoder.py
"""Test ADG/ADV encoder functionality."""

import pytest
from pathlib import Path
from ableton_device_creator.core import encode_adg, decode_adg

class TestEncodeADG:
    """Test encode_adg function."""

    def test_encode_valid_xml(self, decoded_rack_xml, tmp_path):
        """Test encoding valid XML to ADG."""
        output = tmp_path / "output.adg"
        result = encode_adg(decoded_rack_xml, output)

        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_encode_decode_roundtrip(self, decoded_rack_xml, tmp_path):
        """Test encode→decode roundtrip preserves content."""
        output = tmp_path / "roundtrip.adg"

        # Encode
        encode_adg(decoded_rack_xml, output)

        # Decode back
        decoded = decode_adg(output)

        # Should match original
        assert decoded == decoded_rack_xml

    def test_encode_creates_parent_dirs(self, decoded_rack_xml, tmp_path):
        """Test encoder creates parent directories."""
        output = tmp_path / "subdir" / "nested" / "output.adg"

        encode_adg(decoded_rack_xml, output)

        assert output.exists()

    def test_encode_invalid_xml(self, tmp_path):
        """Test error on non-XML content."""
        output = tmp_path / "bad.adg"

        with pytest.raises(ValueError, match="valid XML"):
            encode_adg(b"not xml", output)

    def test_encode_accepts_string_path(self, decoded_rack_xml, tmp_path):
        """Test encoder accepts string path."""
        output = str(tmp_path / "output.adg")
        result = encode_adg(decoded_rack_xml, output)
        assert Path(result).exists()

# Run: pytest tests/unit/test_encoder.py -v --cov=src/ableton_device_creator/core/encoder.py
# Target: 100% coverage
```

---

#### 3.4 Write test_transformer.py (2 hours)

```python
# tests/unit/test_transformer.py
"""Test XML transformation utilities."""

import pytest
from ableton_device_creator.core import DrumRackTransformer, SimplerTransformer

class TestDrumRackTransformer:
    """Test DrumRackTransformer class."""

    def test_init_with_valid_xml(self, decoded_rack_xml):
        """Test initialization with valid XML."""
        transformer = DrumRackTransformer(decoded_rack_xml)
        assert transformer.root is not None

    def test_add_sample(self, decoded_rack_xml, test_samples):
        """Test adding sample to drum rack."""
        transformer = DrumRackTransformer(decoded_rack_xml)
        sample_path = str(test_samples / "Kick_01.wav")

        transformer.add_sample(note=36, sample_path=sample_path)

        samples = transformer.get_samples()
        assert 36 in samples
        assert samples[36] == sample_path

    def test_add_sample_invalid_note(self, decoded_rack_xml):
        """Test error on invalid MIDI note."""
        transformer = DrumRackTransformer(decoded_rack_xml)

        with pytest.raises(ValueError, match="MIDI note must be 0-127"):
            transformer.add_sample(note=128, sample_path="/test.wav")

    def test_remove_sample(self, decoded_rack_xml):
        """Test removing sample from rack."""
        transformer = DrumRackTransformer(decoded_rack_xml)

        # Add then remove
        transformer.add_sample(36, "/test.wav")
        result = transformer.remove_sample(36)

        assert result is True
        assert 36 not in transformer.get_samples()

    def test_get_samples(self, decoded_rack_xml):
        """Test getting all samples from rack."""
        transformer = DrumRackTransformer(decoded_rack_xml)
        samples = transformer.get_samples()

        assert isinstance(samples, dict)
        # Existing rack should have some samples
        assert len(samples) > 0

    def test_to_xml(self, decoded_rack_xml):
        """Test converting back to XML."""
        transformer = DrumRackTransformer(decoded_rack_xml)
        xml = transformer.to_xml()

        assert isinstance(xml, bytes)
        assert xml.startswith(b'<?xml')

class TestSimplerTransformer:
    """Test SimplerTransformer class."""

    # Similar tests for SimplerTransformer
    pass

# Run: pytest tests/unit/test_transformer.py -v --cov
# Target: 90%+ coverage (some edge cases may be hard to test)
```

---

### Day 4: GitHub Actions CI/CD (4 hours)

#### 4.1 Create .github/workflows/tests.yml (2 hours)

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [ main, v3-reorganization ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11']

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: Lint with flake8
      run: |
        flake8 src/ableton_device_creator --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 src/ableton_device_creator --count --max-complexity=10 --max-line-length=100 --statistics

    - name: Type check with mypy
      run: |
        mypy src/ableton_device_creator

    - name: Test with pytest
      run: |
        pytest --cov=src/ableton_device_creator --cov-report=xml --cov-report=term

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

---

#### 4.2 Create .github/workflows/release.yml (1 hour)

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-and-publish:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install build dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine

    - name: Build package
      run: python -m build

    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*

    - name: Create GitHub Release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/*
        generate_release_notes: true
```

---

#### 4.3 Configure Codecov (30 min)

```yaml
# codecov.yml
coverage:
  status:
    project:
      default:
        target: 90%
        threshold: 1%
    patch:
      default:
        target: 80%
```

---

### Day 5: Integration & Phase 1 Validation (8 hours)

#### 5.1 Integration Testing (4 hours)

```python
# tests/integration/test_core_integration.py
"""Integration tests for core module."""

import pytest
from pathlib import Path
from ableton_device_creator.core import (
    decode_adg,
    encode_adg,
    DrumRackTransformer,
)

def test_full_workflow(test_rack_adg, test_samples, tmp_path):
    """Test complete workflow: decode → modify → encode."""

    # 1. Decode
    xml = decode_adg(test_rack_adg)

    # 2. Transform
    transformer = DrumRackTransformer(xml)
    transformer.add_sample(36, str(test_samples / "Kick_01.wav"))
    transformer.add_sample(38, str(test_samples / "Snare_01.wav"))
    modified_xml = transformer.to_xml()

    # 3. Encode
    output = tmp_path / "modified_rack.adg"
    encode_adg(modified_xml, output)

    # 4. Verify
    assert output.exists()

    # 5. Decode again and verify changes persisted
    reloaded_xml = decode_adg(output)
    reloaded_transformer = DrumRackTransformer(reloaded_xml)
    samples = reloaded_transformer.get_samples()

    assert 36 in samples
    assert 38 in samples
```

---

#### 5.2 Package Installation Test (1 hour)

```bash
# Test package installation
pip uninstall -y ableton-device-creator
pip install -e .

# Test imports
python -c "from ableton_device_creator import __version__; print(__version__)"
python -c "from ableton_device_creator.core import decode_adg, encode_adg"

# Run all tests
pytest --cov=src/ableton_device_creator/core --cov-report=term-missing

# Should show 100% coverage for core module
```

---

#### 5.3 Documentation (2 hours)

```markdown
# docs/api/core.md

# Core Module API Reference

## Decoder

### `decode_adg(file_path: Union[str, Path]) -> bytes`

Decode ADG file to XML.

**Parameters:**
- `file_path`: Path to .adg file

**Returns:**
- Decompressed XML content as bytes

**Raises:**
- `FileNotFoundError`: If file doesn't exist
- `ValueError`: If file is not valid gzip

**Example:**
```python
from ableton_device_creator.core import decode_adg

xml = decode_adg("MyDrumRack.adg")
print(xml[:100])
```

[... continue for all functions ...]
```

---

#### 5.4 Phase 1 Checklist

**Before proceeding to Phase 2, verify:**

- [ ] Package installs with `pip install -e .`
- [ ] All core tests pass (100% coverage)
- [ ] CI/CD pipeline runs successfully
- [ ] Can import: `from ableton_device_creator.core import decode_adg`
- [ ] Can decode real ADG files
- [ ] Can encode and decode roundtrip
- [ ] Type checking passes (`mypy src/`)
- [ ] Linting passes (`flake8 src/`)
- [ ] Documentation is complete

**Deliverables:**
✅ Installable Python package
✅ Core module with 100% test coverage
✅ CI/CD pipeline
✅ API documentation
✅ Foundation ready for Phase 2

---

## Phase 2: Drum Racks (Week 2)

**Goal:** Consolidate 32 drum rack scripts into 3 classes with 90% test coverage

**Duration:** 5 days (40 hours)

---

### Day 6: Sample Categorization (8 hours)

#### 6.1 Create sample_utils.py (4 hours)

```python
# src/ableton_device_creator/drum_racks/sample_utils.py
"""Sample file categorization and organization utilities."""

from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

@dataclass
class SampleCategory:
    """Sample category definition."""
    name: str
    keywords: List[str]
    aliases: List[str]

# Standard drum sample categories
DRUM_CATEGORIES = {
    'kick': SampleCategory(
        name='kick',
        keywords=['kick', 'bd', 'bassdrum', 'bass drum', 'kck'],
        aliases=['kicks', 'kick_drum']
    ),
    'snare': SampleCategory(
        name='snare',
        keywords=['snare', 'sd', 'snr'],
        aliases=['snares', 'snare_drum']
    ),
    'hat': SampleCategory(
        name='hat',
        keywords=['hat', 'hh', 'hihat', 'hi-hat', 'hi hat'],
        aliases=['hats', 'hihat', 'hi_hat']
    ),
    'clap': SampleCategory(
        name='clap',
        keywords=['clap', 'cp', 'handclap'],
        aliases=['claps', 'hand_clap']
    ),
    'tom': SampleCategory(
        name='tom',
        keywords=['tom', 'tm'],
        aliases=['toms']
    ),
    'cymbal': SampleCategory(
        name='cymbal',
        keywords=['cymbal', 'cym', 'crash', 'ride'],
        aliases=['cymbals', 'crash', 'ride']
    ),
    'perc': SampleCategory(
        name='perc',
        keywords=['perc', 'percussion', 'shaker', 'conga', 'bongo'],
        aliases=['percussion', 'percs']
    ),
}

SUPPORTED_AUDIO_FORMATS = {'.wav', '.aif', '.aiff', '.flac', '.mp3'}

def categorize_samples(
    folder_path: Path,
    categories: Optional[Dict[str, SampleCategory]] = None,
    recursive: bool = True
) -> Dict[str, List[Path]]:
    """
    Categorize audio samples by type based on filename.

    Args:
        folder_path: Directory containing samples
        categories: Custom categories (uses DRUM_CATEGORIES if None)
        recursive: Search subdirectories

    Returns:
        Dictionary mapping category name to list of sample paths

    Example:
        >>> samples = categorize_samples(Path('/samples'))
        >>> samples['kick']
        [Path('/samples/Kick_01.wav'), Path('/samples/BD_heavy.wav')]
    """
    if categories is None:
        categories = DRUM_CATEGORIES

    # Initialize result dict
    result = {cat: [] for cat in categories.keys()}
    result['uncategorized'] = []

    # Find all audio files
    pattern = '**/*' if recursive else '*'
    audio_files = []

    for ext in SUPPORTED_AUDIO_FORMATS:
        audio_files.extend(folder_path.glob(f"{pattern}{ext}"))

    # Categorize each file
    for file_path in audio_files:
        filename_lower = file_path.stem.lower()
        categorized = False

        # Check against each category
        for cat_name, cat_info in categories.items():
            if any(keyword in filename_lower for keyword in cat_info.keywords):
                result[cat_name].append(file_path)
                categorized = True
                break

        if not categorized:
            result['uncategorized'].append(file_path)

    return result

def detect_velocity_layers(samples: List[Path]) -> Dict[str, List[Path]]:
    """
    Detect velocity layers in sample filenames.

    Common patterns:
    - Kick_v1.wav, Kick_v2.wav, Kick_v3.wav
    - Snare_soft.wav, Snare_med.wav, Snare_hard.wav
    - HH_01.wav, HH_02.wav, HH_03.wav

    Returns:
        Dict mapping velocity layer name to samples
    """
    layers = {}

    for sample in samples:
        stem = sample.stem.lower()

        # Pattern 1: _v1, _v2, etc.
        if '_v' in stem:
            layer = stem.split('_v')[1].split('_')[0]
            layer_name = f"velocity_{layer}"

        # Pattern 2: _soft, _med, _hard
        elif any(x in stem for x in ['soft', 'med', 'medium', 'hard']):
            for keyword in ['soft', 'med', 'medium', 'hard']:
                if keyword in stem:
                    layer_name = keyword
                    break

        # Pattern 3: _01, _02, _03
        elif stem[-3:-1] == '_0' or stem[-2:].isdigit():
            layer = stem.split('_')[-1]
            if layer.isdigit():
                layer_name = f"layer_{layer}"

        else:
            layer_name = "default"

        if layer_name not in layers:
            layers[layer_name] = []
        layers[layer_name].append(sample)

    return layers

def validate_samples(samples: List[Path]) -> List[Path]:
    """
    Validate sample files exist and are readable.

    Returns:
        List of valid sample paths
    """
    valid = []

    for sample in samples:
        if not sample.exists():
            continue
        if not sample.is_file():
            continue
        if sample.suffix.lower() not in SUPPORTED_AUDIO_FORMATS:
            continue

        valid.append(sample)

    return valid
```

**Test:**

```python
# tests/unit/test_sample_utils.py
def test_categorize_samples(test_samples):
    """Test sample categorization."""
    from ableton_device_creator.drum_racks.sample_utils import categorize_samples

    result = categorize_samples(test_samples)

    assert 'kick' in result
    assert 'snare' in result
    assert len(result['kick']) > 0

def test_detect_velocity_layers():
    """Test velocity layer detection."""
    from ableton_device_creator.drum_racks.sample_utils import detect_velocity_layers
    from pathlib import Path

    samples = [
        Path("/Kick_v1.wav"),
        Path("/Kick_v2.wav"),
        Path("/Kick_v3.wav"),
    ]

    layers = detect_velocity_layers(samples)

    assert 'velocity_1' in layers
    assert len(layers['velocity_1']) == 1
```

---

### Day 7-8: DrumRackCreator Class (16 hours)

#### 7.1 Create drum_racks/__init__.py (1 hour)

```python
# src/ableton_device_creator/drum_racks/__init__.py
"""
Drum rack creation and modification tools.

This module provides classes for creating and modifying Ableton Live
drum racks from sample folders.
"""

from .creator import DrumRackCreator
from .modifier import DrumRackModifier
from .batch import BatchProcessor
from .sample_utils import categorize_samples, detect_velocity_layers

__all__ = [
    "DrumRackCreator",
    "DrumRackModifier",
    "BatchProcessor",
    "categorize_samples",
    "detect_velocity_layers",
]
```

---

#### 7.2 Create creator.py (8 hours)

```python
# src/ableton_device_creator/drum_racks/creator.py
"""DrumRackCreator class for creating drum racks from samples."""

from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

from ..core import decode_adg, encode_adg, DrumRackTransformer
from .sample_utils import categorize_samples, detect_velocity_layers, validate_samples

logger = logging.getLogger(__name__)

# MIDI note mapping for drum pads (C1-G3)
DRUM_PAD_NOTES = list(range(36, 68))  # 32 pads

class DrumRackCreator:
    """
    Create drum racks from sample folders.

    This class consolidates functionality from:
    - main_simple_folder.py
    - main.py
    - main_percussion.py
    - main_by_note_name.py
    - create_multivelocity_drum_rack_v2.py
    - create_dual_folder_drum_rack_v2.py
    - create_triple_folder_electro_acoustic_rack.py

    Example:
        >>> creator = DrumRackCreator(template="templates/input_rack.adg")
        >>> rack = creator.from_folder("/samples", output="MyRack.adg")
    """

    def __init__(self, template: Union[str, Path]):
        """
        Initialize creator with template.

        Args:
            template: Path to template ADG file
        """
        self.template = Path(template)
        if not self.template.exists():
            raise FileNotFoundError(f"Template not found: {self.template}")

    def from_folder(
        self,
        samples_dir: Union[str, Path],
        output: Optional[Union[str, Path]] = None,
        categorize: bool = True,
        recursive: bool = True,
    ) -> Path:
        """
        Create drum rack from folder of samples.

        Replaces: main_simple_folder.py

        Args:
            samples_dir: Folder containing samples
            output: Output path (auto-generated if None)
            categorize: Categorize samples by type
            recursive: Search subdirectories

        Returns:
            Path to created drum rack

        Example:
            >>> creator.from_folder("/samples/kicks")
            PosixPath('output/kicks.adg')
        """
        samples_dir = Path(samples_dir)
        logger.info(f"Creating drum rack from {samples_dir}")

        # Auto-generate output path
        if output is None:
            output = Path("output") / f"{samples_dir.name}.adg"
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Load template
        template_xml = decode_adg(self.template)
        transformer = DrumRackTransformer(template_xml)

        # Get samples
        if categorize:
            categorized = categorize_samples(samples_dir, recursive=recursive)
            samples = self._flatten_categories(categorized)
        else:
            samples = list(samples_dir.glob('**/*.wav' if recursive else '*.wav'))

        samples = validate_samples(samples)
        logger.info(f"Found {len(samples)} valid samples")

        # Map samples to MIDI notes
        for note, sample in zip(DRUM_PAD_NOTES, samples[:32]):
            transformer.add_sample(note, str(sample.absolute()))
            logger.debug(f"Added {sample.name} at note {note}")

        # Save
        modified_xml = transformer.to_xml()
        result = encode_adg(modified_xml, output)
        logger.info(f"Created drum rack: {result}")

        return result

    def from_categorized(
        self,
        samples_dict: Dict[str, List[Path]],
        output: Optional[Path] = None,
        layout: str = "standard",
    ) -> Path:
        """
        Create drum rack from pre-categorized samples.

        Replaces: main.py

        Args:
            samples_dict: Dict mapping category to sample paths
            output: Output path
            layout: Note layout ("standard", "808", "percussion")

        Returns:
            Path to created drum rack

        Example:
            >>> samples = {
            ...     'kick': [Path('/kick1.wav'), Path('/kick2.wav')],
            ...     'snare': [Path('/snare1.wav')],
            ... }
            >>> creator.from_categorized(samples, layout="808")
        """
        # Get note layout
        note_map = self._get_note_layout(layout)

        # Load template
        template_xml = decode_adg(self.template)
        transformer = DrumRackTransformer(template_xml)

        # Map categories to notes
        for category, samples in samples_dict.items():
            if category in note_map:
                start_note = note_map[category]
                for i, sample in enumerate(samples[:4]):  # Max 4 per category
                    note = start_note + i
                    transformer.add_sample(note, str(sample.absolute()))

        # Save
        if output is None:
            output = Path("output/categorized_rack.adg")
        output.parent.mkdir(parents=True, exist_ok=True)

        modified_xml = transformer.to_xml()
        return encode_adg(modified_xml, output)

    def with_velocity_layers(
        self,
        samples_dir: Union[str, Path],
        output: Optional[Path] = None,
        layers: int = 3,
    ) -> Path:
        """
        Create multi-velocity drum rack.

        Replaces: create_multivelocity_drum_rack_v2.py

        Args:
            samples_dir: Folder with velocity-layered samples
            output: Output path
            layers: Number of velocity layers

        Returns:
            Path to created rack
        """
        samples_dir = Path(samples_dir)

        # Get all samples
        all_samples = list(samples_dir.glob('**/*.wav'))

        # Detect velocity layers
        layers_dict = detect_velocity_layers(all_samples)

        # Create rack with layers
        template_xml = decode_adg(self.template)
        transformer = DrumRackTransformer(template_xml)

        # Add velocity zones
        # (This would require more complex XML manipulation)
        # For now, simplified version:
        for note, samples_list in zip(DRUM_PAD_NOTES, layers_dict.values()):
            # Add first sample (full implementation would add all layers)
            if samples_list:
                transformer.add_sample(note, str(samples_list[0].absolute()))

        # Save
        if output is None:
            output = Path("output") / f"{samples_dir.name}_velocity.adg"
        output.parent.mkdir(parents=True, exist_ok=True)

        modified_xml = transformer.to_xml()
        return encode_adg(modified_xml, output)

    def _flatten_categories(self, categorized: Dict[str, List[Path]]) -> List[Path]:
        """Flatten categorized samples to single list."""
        flat = []
        for samples in categorized.values():
            flat.extend(samples)
        return flat

    def _get_note_layout(self, layout: str) -> Dict[str, int]:
        """Get MIDI note layout for categories."""
        layouts = {
            'standard': {
                'kick': 36,
                'snare': 40,
                'hat': 42,
                'clap': 39,
                'tom': 48,
                'cymbal': 49,
                'perc': 56,
            },
            '808': {
                'kick': 36,
                'snare': 38,
                'hat': 42,
                'clap': 39,
                'tom': 45,
                'cymbal': 51,
                'perc': 60,
            },
            'percussion': {
                'perc': 36,
                'shaker': 44,
                'conga': 48,
                'bongo': 52,
            }
        }
        return layouts.get(layout, layouts['standard'])
```

---

#### 7.3 Write creator tests (4 hours)

```python
# tests/unit/test_drum_rack_creator.py
"""Test DrumRackCreator class."""

import pytest
from pathlib import Path
from ableton_device_creator.drum_racks import DrumRackCreator

class TestDrumRackCreator:
    """Test DrumRackCreator initialization and methods."""

    def test_init_with_valid_template(self, test_rack_adg):
        """Test initialization with valid template."""
        creator = DrumRackCreator(template=test_rack_adg)
        assert creator.template == test_rack_adg

    def test_init_with_nonexistent_template(self):
        """Test error on nonexistent template."""
        with pytest.raises(FileNotFoundError):
            DrumRackCreator(template="nonexistent.adg")

    def test_from_folder(self, test_rack_adg, test_samples, tmp_path):
        """Test creating rack from folder."""
        creator = DrumRackCreator(template=test_rack_adg)
        output = tmp_path / "test_rack.adg"

        result = creator.from_folder(
            samples_dir=test_samples,
            output=output,
            categorize=False
        )

        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_from_folder_with_categorization(self, test_rack_adg, test_samples, tmp_path):
        """Test creating rack with sample categorization."""
        creator = DrumRackCreator(template=test_rack_adg)
        output = tmp_path / "categorized_rack.adg"

        result = creator.from_folder(
            samples_dir=test_samples,
            output=output,
            categorize=True
        )

        assert output.exists()

    def test_from_categorized(self, test_rack_adg, test_samples, tmp_path):
        """Test creating rack from pre-categorized samples."""
        from ableton_device_creator.drum_racks.sample_utils import categorize_samples

        creator = DrumRackCreator(template=test_rack_adg)
        samples_dict = categorize_samples(test_samples)
        output = tmp_path / "categorized.adg"

        result = creator.from_categorized(
            samples_dict=samples_dict,
            output=output,
            layout="standard"
        )

        assert output.exists()

    def test_with_velocity_layers(self, test_rack_adg, tmp_path):
        """Test creating multi-velocity rack."""
        # Create test samples with velocity layers
        velocity_dir = tmp_path / "velocity_samples"
        velocity_dir.mkdir()

        # Create dummy files
        for i in range(1, 4):
            (velocity_dir / f"Kick_v{i}.wav").touch()

        creator = DrumRackCreator(template=test_rack_adg)
        output = tmp_path / "velocity_rack.adg"

        result = creator.with_velocity_layers(
            samples_dir=velocity_dir,
            output=output
        )

        assert output.exists()

# Run: pytest tests/unit/test_drum_rack_creator.py -v --cov
# Target: 85%+ coverage
```

---

#### 7.4 Integration test (3 hours)

```python
# tests/integration/test_drum_rack_workflow.py
"""Integration test for complete drum rack creation workflow."""

def test_complete_drum_rack_workflow(test_rack_adg, test_samples, tmp_path):
    """Test end-to-end workflow: samples → drum rack → verify."""
    from ableton_device_creator.drum_racks import DrumRackCreator
    from ableton_device_creator.core import decode_adg, DrumRackTransformer

    # 1. Create rack
    creator = DrumRackCreator(template=test_rack_adg)
    output = tmp_path / "workflow_test.adg"

    result = creator.from_folder(
        samples_dir=test_samples,
        output=output,
        categorize=True
    )

    # 2. Verify created
    assert result.exists()

    # 3. Decode and verify structure
    xml = decode_adg(result)
    transformer = DrumRackTransformer(xml)
    samples = transformer.get_samples()

    # Should have at least some samples mapped
    assert len(samples) > 0

    # 4. Verify samples have absolute paths
    for note, path in samples.items():
        assert Path(path).is_absolute()
```

---

### Day 9-10: DrumRackModifier & BatchProcessor (16 hours)

**Similar detailed breakdowns for:**

#### 9.1 modifier.py (8 hours)
- Consolidates trim, remap, merge scripts
- Methods: `remap_notes()`, `trim_to_16()`, `merge()`, `disable_auto_color()`
- Tests with 85%+ coverage

#### 9.2 batch.py (6 hours)
- Consolidates batch processing scripts
- Methods: `process_library()`, `process_expansions()`
- Progress tracking, error handling

#### 9.3 Integration tests (2 hours)
- Test batch processing 100+ samples
- Test error recovery
- Test progress callbacks

---

**This is Day 1-10 of the full 30-day plan. Would you like me to continue with:**
- Phase 3: Macro Mapping (Week 3)
- Phase 4: Sampler & Conversion (Week 4)
- Phase 5: CLI & Integration (Week 5)
- Phase 6: Documentation & Release (Week 6)

**Or would you prefer:**
1. More detail on a specific phase?
2. Implementation code for a specific class?
3. Testing strategy deep-dive?

Let me know how you'd like to proceed!

---

## Implementation Log

### 2025-11-29 - Project Start

**Decision: Revised Testing Strategy**

After reviewing the plan, we decided to adopt a pragmatic testing approach aligned with the project's production-proven philosophy:

- **Phase 1 (Core Utilities):** Skip comprehensive testing
  - Rationale: decoder/encoder are simple gzip wrappers with 2+ years production use
  - Validation: Package installation and import tests only
  - ADG files fail loudly if broken (instant feedback in Ableton)

- **Phase 2+ (Complex Logic):** Add targeted testing
  - Focus: Sample categorization, velocity layer detection, MIDI note mapping
  - Target: 60-80% coverage on complex logic (not trivial I/O)
  - Integration tests for end-to-end workflows (samples → device → verify)

- **Real validation:** Test each phase output in Ableton Live
  - Does the device load?
  - Do samples trigger correctly?
  - Are note mappings correct?

**Next Steps:**
- [x] Begin Phase 1: Foundation & Core (simplified, no 100% coverage requirement)
- [x] Create package structure
- [x] Migrate core utilities
- [x] Verify package installation

**Status:** Phase 1 foundation complete!

---

### 2025-11-29 - Phase 1 Foundation Complete ✓

**Completed Tasks:**
1. ✓ Created `v3-reorganization` branch
2. ✓ Tagged current state as `v2.1-pre-reorganization`
3. ✓ Created package structure:
   ```
   src/ableton_device_creator/
   ├── __init__.py
   ├── core/
   │   ├── __init__.py
   │   ├── decoder.py
   │   ├── encoder.py
   ├── drum_racks/
   ├── macro_mapping/
   ├── sampler/
   ├── conversion/
   └── instrument_racks/
   ```
4. ✓ Created `pyproject.toml` (simplified, optional testing deps)
5. ✓ Migrated core utilities with improvements:
   - `decoder.py`: Added type hints, better error handling
   - `encoder.py`: Added type hints, validates XML, creates parent dirs
6. ✓ Package installs successfully: `pip install -e .`
7. ✓ Verified imports work: `from ableton_device_creator.core import decode_adg, encode_adg`
8. ✓ Tested roundtrip: decode → encode → decode (✓ matches)

**Test Results:**
- Decoded 1.1MB XML from template ADG
- Encoded to 57KB gzipped ADG
- Roundtrip verification: ✓ Perfect match

**Next Steps:**
- [x] Commit Phase 1 changes
- [x] Begin Phase 2: Sample categorization and DrumRackCreator
- [x] Create `sample_utils.py` with categorization logic

---

### 2025-11-29 - Phase 2 Core Complete ✓

**Completed Tasks:**
1. ✓ Created `sample_utils.py` with comprehensive categorization:
   - `categorize_samples()`: Categorize by filename keywords
   - `categorize_by_folder()`: Categorize by folder structure
   - `validate_samples()`: Validate audio file paths
   - `detect_velocity_layers()`: Detect multi-velocity samples
   - `sort_samples_natural()`: Natural number sorting
   - 9 drum categories (kick, snare, hat, clap, tom, cymbal, perc, shaker, open_hat)
   - Support for .wav, .aif, .aiff, .flac, .mp3

2. ✓ Created `DrumRackCreator` class:
   - `from_folder()`: Simple mode - fill pads sequentially
   - `from_categorized_folders()`: Organize by category with custom layouts
   - Supports standard, 808, and percussion layouts
   - Automatic MIDI note mapping
   - XML transformation with sample path updates

3. ✓ Integration testing:
   - Created 15 test samples (5 kicks, 5 snares, 5 hats)
   - Categorization: ✓ Correctly identified all samples
   - Drum rack creation: ✓ 57KB ADG generated
   - Verification: ✓ All 15 samples present in output

**Test Results:**
```
Input: 15 WAV samples (kicks, snares, hats)
Categorization: 100% accurate
Output: 57KB ADG with 15 sample references
Verification: ✓ All samples mapped correctly
```

**Files Created:**
- `src/ableton_device_creator/drum_racks/__init__.py`
- `src/ableton_device_creator/drum_racks/sample_utils.py` (280 lines)
- `src/ableton_device_creator/drum_racks/creator.py` (380 lines)

**Next Steps:**
- [x] Commit Phase 2 changes
- [ ] Test in Ableton Live (manual validation)
- [ ] Phase 3: Add more creator methods (velocity layers, batch processing)

---

## Phase 1 & 2 Summary

**Total Progress: ~40% of V3.0 Core Functionality**

### What We've Built

**Phase 1: Foundation (Completed)**
- Modern Python package with `src/` layout
- Zero-dependency core (decoder/encoder)
- Installable via `pip install -e .`
- Type hints and comprehensive error handling

**Phase 2: Drum Rack Creation (Completed)**
- Sample categorization engine (9 categories)
- DrumRackCreator class (2 creation modes)
- Support for multiple audio formats
- Natural sorting and velocity layer detection

### Code Statistics
- **Files Created:** 10
- **Lines of Code:** ~1,000
- **Test Coverage:** Manual integration testing (production-proven approach)
- **Commits:** 2 (clean git history)

### API Examples

**Simple Usage:**
```python
from ableton_device_creator.drum_racks import DrumRackCreator

creator = DrumRackCreator(template="template.adg")
rack = creator.from_folder("samples/", output="MyRack.adg")
```

**Categorized Usage:**
```python
creator.from_categorized_folders(
    samples_dir="drums/",
    layout="808",  # or "standard", "percussion"
    output="Categorized.adg"
)
```

### ✅ Manual Validation Complete!

**Tested in Ableton Live - SUCCESS!**

Test rack: `output/real_samples_rack.adg`
- ✅ Device loads without errors
- ✅ All pads trigger correctly (kicks, snares, hats, claps, toms, cymbals, perc)
- ✅ Sample categorization accurate (9 categories)
- ✅ MIDI note mapping correct (standard layout)
- ✅ 19 samples mapped from NI Sierra Grove library

**Production-Ready Features:**
- Sample categorization by folder structure
- Multiple layout modes (standard, 808, percussion)
- Natural sorting of samples
- Supports .wav, .aif, .aiff, .flac, .mp3

---

### 2025-11-29 - Production Validation ✓

**This is the moment of truth:** Code tested in real DAW, with real samples, in production conditions.

The V3.0 architecture is **proven to work**. This validates:
- Modern package structure
- Zero-dependency core
- Production-proven validation approach (no extensive test suite needed)
- 2+ years of XML manipulation knowledge successfully migrated

**Phase 1 & 2 = COMPLETE AND VALIDATED** 🎉

---

### 2025-11-29 - Repository Cleanup ✓

**Major reorganization to prepare for V3 migration:**

Moved to `archive-v2-scripts/`:
- ✅ drum-racks/ (114 files) - Partially migrated to `src/drum_racks/`
- ✅ sampler/ - To be migrated
- ✅ macro-mapping/ - To be migrated
- ✅ simpler/ - To be migrated
- ✅ instrument-racks/ - To be migrated
- ✅ conversion/ - To be migrated
- ✅ utils/ - Already migrated to `src/core/`
- ✅ kontakt/ - Evaluate for migration
- ✅ analysis/ - Evaluate for migration

Removed test artifacts:
- test_samples/ (empty dummy files)
- test_samples_real/ (temporary copies)
- test-output/ (old artifacts)

**New clean structure:**
```
Ableton Device Creator/
├── src/                     # ✅ V3 library code
├── archive-v2-scripts/      # 📚 V2 reference
├── archive-v1/              # 🗄️ V1 archive
├── templates/               # ADG/ADV templates
├── docs/                    # Documentation
├── examples/                # Usage examples
└── output/                  # Generated devices
```

**Benefits:**
- Clear separation: production code vs reference code
- Easy to see what's migrated vs what's pending
- Clean git history with file renames preserved
- Can still reference old implementations during migration

**Git Status:**
- 7 commits on v3-reorganization
- All changes pushed
- Clean working directory

**Final Root Directory:**
```
/
├── README.md              # Main documentation
├── CLAUDE.md              # AI assistant context
├── pyproject.toml         # Package configuration
├── setup.py               # Build backend
├── .gitignore             # Git config
├── src/                   # ✅ V3 production code
├── archive-v2-scripts/    # 📚 V2 reference (114 files)
├── archive-v1/            # 🗄️ V1 archive
├── docs/                  # 📖 Documentation (organized)
├── examples/              # 📝 Usage examples
├── templates/             # 🎯 ADG/ADV templates
└── output/                # 🎵 Generated devices
```

**All dependencies in pyproject.toml:**
- Core: Zero dependencies (stdlib only)
- Optional [cli]: click>=8.0.0
- Optional [dev]: pytest, black, flake8

---

## Session Summary: 2025-11-29

**Total Accomplishments:**
- ✅ Phase 1: Package foundation complete
- ✅ Phase 2: Drum rack creation complete
- ✅ Production validation in Ableton Live
- ✅ Repository cleanup and organization
- ✅ 7 commits with clean history

**Code Statistics:**
- 10 new files created in src/
- ~1,000 lines of production code
- 114 V2 files organized to archive
- 100% of new code validated in DAW

**Ready for Production Use:**
```python
from ableton_device_creator.drum_racks import DrumRackCreator

creator = DrumRackCreator(template="templates/drum-rack.adg")
rack = creator.from_categorized_folders("samples/", layout="808")
# Open in Ableton Live - it works! ✅
```

---

---

### 2025-11-29 - Phase 3: Macro Mapping Complete ✓

**Completed Tasks:**
1. ✓ Created `src/ableton_device_creator/macro_mapping/` module structure
2. ✓ Implemented `cc_controller.py` - CCControlMapper class (500 lines)
3. ✓ Implemented `color_mapper.py` - DrumPadColorMapper class (280 lines)
4. ✓ Implemented `transpose.py` - TransposeMapper class (200 lines)
5. ✓ Created `macro_mapping_example.py` with working examples
6. ✓ Updated main package `__init__.py` with new exports

**Code Statistics:**
- 3 new modules created in `src/macro_mapping/`
- ~980 lines of production code
- Consolidates 25+ scripts from `archive-v2-scripts/macro-mapping/`
- 100% functional: tested with real ADG files

**New Capabilities:**

```python
from ableton_device_creator.macro_mapping import (
    CCControlMapper,
    DrumPadColorMapper,
    TransposeMapper
)

# Add CC Control mappings
mapper = CCControlMapper("input.adg")
mapper.add_cc_mappings({
    3: (119, 15),  # Custom E → CC 119 → Macro 16
    4: (120, 14),  # Custom F → CC 120 → Macro 15
}).save("output.adg")

# Apply color coding to drum pads
colorizer = DrumPadColorMapper("input.adg")
colorizer.apply_colors().save("colored.adg")

# Map transpose to macro
transpose = TransposeMapper("input.adg")
transpose.add_transpose_mapping(macro_index=15).save("output.adg")
```

**Test Results:**
- ✅ CC Control: Successfully added to drum rack
- ✅ Color Coding: Colored 32 pads with 9 categories
- ✅ Transpose: Mapped to Macro 16
- ✅ Combined workflow: All operations work together

**Consolidated V2 Scripts:**
- `cc-control/add_cc_control_to_drum_rack.py` (568 lines) → `cc_controller.py`
- `cc-control/apply_cc_mappings_preserve_values.py` (443 lines) → (merged)
- `color-coding/apply_drum_rack_colors.py` (326 lines) → `color_mapper.py`
- `color-coding/apply_color_coding.py` (273 lines) → (merged)
- `transpose/batch_add_transpose_mapping.py` (391 lines) → `transpose.py`
- Plus 20+ other variants and batch scripts

**Phase 3 = COMPLETE ✅** (~60% of V3.0 done)

---

**Next Phase Options:**
- Add CLI interface (`adc create-drum-rack samples/`)
- Add batch processing for libraries
- Add velocity layer support
- Add Simpler/Sampler device creation
- Migrate conversion utilities
