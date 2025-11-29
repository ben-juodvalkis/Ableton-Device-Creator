# Ableton Device Creator - Architecture Reference & Quick Guide

## File Map Quick Reference

### Core Foundation (Use these as black boxes)
```
scripts/utils/
├── decoder.py          [19 LOC] Decompress .adg → XML string
├── encoder.py          [16 LOC] Compress XML string → .adg
├── transformer.py      [102 LOC] Update drum rack samples
├── simpler_transformer.py [201 LOC] Create/update Simpler devices
├── __init__.py         Empty module marker
└── (batch/utility scripts - build on above)
```

### Main Entry Points
```
scripts/device/
├── drum_rack/
│   ├── main.py         [215 LOC] NI Expansion → Drum Racks
│   └── main_percussion.py [133 LOC] Percussion-only racks
├── sampler/
│   ├── main_sampler.py [150 LOC] Standard samplers
│   ├── main_drumstyle_sampler.py [177 LOC] Category-based samplers
│   ├── main_percussion_sampler.py [163 LOC] Percussion samplers
│   └── main_phrases_sampler.py [125 LOC] Per-subfolder samplers
├── simpler/
│   └── main_simpler.py [112 LOC] One device per sample
└── generic/
    └── main_generic.py [172 LOC] Any folder structure
```

### Batch Processing
```
scripts/meta/
├── main.py             [94 LOC] Process all NI Expansions
├── main_folders.py     [108 LOC] Process folder hierarchies
└── main_percussion.py  [101 LOC] Batch percussion creation
```

---

## Data Flow Diagrams

### Drum Rack Creation Flow
```
Audio Samples (Folder)
        ↓
[get_all_samples] → [validate] → [sort by name]
        ↓
[organize_drum_samples] → Categorize into groups
        ↓
Batch of 32 samples
        ↓
[decode_adg] → ADG template → XML string
        ↓
[transform_xml] → Update sample paths → Find drum pads
        ↓
Transform XML
        ↓
[encode_adg] → Gzip compress → New .adg file
```

### Sampler Creation Flow
```
Audio Samples (Folder)
        ↓
[get_all_samples] → [validate] → [sort by name]
        ↓
Batch of 32 samples per MIDI key (48-79 = C2-G#4)
        ↓
[decode_adg] → Sampler template → XML string
        ↓
[transform_sampler_xml] → Create MultiSampleParts
        ↓
For each sample:
  Create MultiSamplePart element
  ├─ Id: sequential (0, 1, 2...)
  ├─ KeyRange: [key_min, key_max] (usually same)
  ├─ RootKey: key value
  ├─ SampleRef/FileRef: Path + RelativePath
  └─ (other metadata)
        ↓
[encode_adg] → Gzip compress → New .adg file
```

### Simpler Device Flow
```
Single Audio Sample
        ↓
[validate] → Check file exists and is readable
        ↓
[decode_adv] → Simpler template → XML string
        ↓
[transform_simpler_xml] → Update sample reference
        ↓
Create MultiSamplePart with:
  ├─ KeyRange: 0-127 (full keyboard)
  ├─ VelocityRange: 1-127
  ├─ SelectorRange: 0-127
  ├─ RootKey: 60 (middle C)
  ├─ SampleRef pointing to sample file
  └─ Metadata (name, sample rate, etc.)
        ↓
[encode_adv] → Gzip compress → New .adv file
```

---

## XML Structure Reference

### ADG/ADV File Format
```
.adg / .adv file
    ↓
gzip compressed
    ↓
XML document
    ↓
<?xml version="1.0" encoding="UTF-8"?>
<Ableton MajorVersion="..." MinorVersion="...">
  <LiveDevice>
    <!-- Device specific content -->
  </LiveDevice>
</Ableton>
```

### Drum Rack XML Structure
```
Ableton/LiveDevice/DrumPad/ (32 of these)
├─ DrumBranchPreset
│  ├─ ZoneSettings
│  │  └─ ReceivingNote Value="36"  ← MIDI note (C1=36)
│  ├─ DrumCell
│  │  ├─ PresetRef
│  │  │  └─ SampleRef/FileRef
│  │  │     ├─ Path Value="/path/to/sample.wav"
│  │  │     └─ RelativePath Value="../../last/3/parts.wav"
│  │  └─ ModulationSource (optional)
```

### Sampler XML Structure
```
Ableton/LiveDevice/MultiSampleMap/SampleParts/
├─ MultiSamplePart (Id="0")  ← First sample
│  ├─ KeyRange
│  │  ├─ Min Value="48"      ← MIDI note C2
│  │  ├─ Max Value="48"      ← Single key
│  │  ├─ CrossfadeMin Value="48"
│  │  └─ CrossfadeMax Value="48"
│  ├─ RootKey Value="48"
│  ├─ Name Value="sample_name"
│  ├─ SampleRef/FileRef
│  │  ├─ Path Value="/path/to/sample.wav"
│  │  └─ RelativePath Value="../../last/3/parts.wav"
│  └─ (15+ other attributes)
├─ MultiSamplePart (Id="1")  ← Second sample
│  ├─ KeyRange: 49-49
│  └─ ...
```

### Simpler XML Structure
```
Ableton/LiveDevice/MultiSampleMap/SampleParts/
└─ MultiSamplePart (Id="0")
   ├─ KeyRange: 0-127        ← Full keyboard
   ├─ VelocityRange: 1-127
   ├─ SelectorRange: 0-127
   ├─ RootKey: 60            ← Middle C
   ├─ Name: filename
   ├─ SampleRef/FileRef
   │  ├─ Path: absolute path
   │  └─ RelativePath: relative path
   ├─ DefaultSampleRate: 48000
   ├─ DefaultDuration: 0
   ├─ SamplesToAutoWarp: 1
   └─ (metadata attributes)
```

---

## MIDI Note Mapping Reference

### Keyboard Ranges Used
```
Drum Racks:       C1 to G#3  (36-67, 32 pads)
Samplers:         C2 to G#4  (48-79, 32 keys)
Simpler:          C-2 to G7  (0-127, full keyboard)

MIDI Note Number Guide:
C-2 = 0,    C-1 = 12,   C0 = 24,   C1 = 36,  C2 = 48
C3 = 60 (Middle C),     C4 = 72,   C5 = 84, C6 = 96
```

### Standard Pitch Layout
```
One Octave (12 semitones):
C - C# - D - D# - E - F - F# - G - G# - A - A# - B
0 -  1 - 2 -  3 - 4 - 5 -  6 - 7 -  8 - 9 - 10 - 11
```

---

## Function Call Chains

### Typical Device Creation
```python
# Main script entry point
def main():
    ↓
    # Validate inputs
    input_path.exists()
    folder_path.exists()
    ↓
    # Organize samples
    get_all_samples(folder_path)
    ↓
    # Process each batch
    for batch_index in range(num_batches):
        ↓
        # Decode template
        xml_content = decode_adg(template_path)
        ↓
        # Transform XML
        transformed = transform_xml(xml_content, samples)
        ↓
        # Encode result
        encode_adg(transformed, output_path)
        ↓
        print(f"Created {output_path}")
```

### Sample Organization Helper Functions
```python
get_all_samples()              # → List[str] of absolute paths
  ├─ folder_path.glob('*.wav')
  ├─ is_valid_audio_file()     # Validate WAV files
  └─ sort by descriptive name

get_descriptive_name()          # → str (extracted from filename)
  └─ Split on first space, return second part

get_sample_batch()              # → List[str] (32 samples)
  └─ Pagination: start = batch * 32, end = start + 32

organize_drum_samples()         # → (List[str], str, bool)
  ├─ Categorize by folder
  ├─ Get 8 samples from each category
  ├─ Combine: remaining + hihat + snare + kick
  └─ Return (samples, rack_name, has_more)
```

---

## Import Pattern Problems

### Current Inconsistency
```python
# drum_rack/main.py
from decoder import decode_adg          # ❌ Relative - won't work

# sampler/main_sampler.py
from utils.decoder import decode_adg    # ❌ Semi-relative - fragile

# sampler/main_drumstyle_sampler.py
from scripts.utils.decoder import decode_adg  # ✓ Full path - works but verbose

# Script with sys.path hack
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.decoder import decode_adg    # ✓ Works but fragile
```

### Proposed Solution
```python
# All scripts should use:
from scripts.utils import decode_adg, encode_adg, transform_xml
from scripts.core import organize_drum_samples, get_all_samples
```

---

## Code Duplication Inventory

### High Duplication Functions

#### 1. Sample Organization (appears in 5+ files)
```python
# ~40 LOC duplicated across:
# - drum_rack/main.py
# - drum_rack/main_percussion.py
# - sampler/main_drumstyle_sampler.py
# - sampler/main_percussion_sampler.py
# - device/generic/main_generic.py

def get_descriptive_name(filename: str) -> str:
    parts = filename.split(' ', 1)
    return parts[1].lower() if len(parts) > 1 else filename.lower()

def get_all_samples_from_folders(base_path, folders, exclude_patterns=None):
    # ~10 LOC...
    
def get_sample_batch(samples, batch_index, batch_size=8):
    return samples[batch_index*batch_size : (batch_index+1)*batch_size]
```

**Recommendation**: Extract to `scripts/core/sample_organizer.py`

#### 2. Sampler XML Creation (appears in 4+ files)
```python
# ~50 LOC duplicated across:
# - sampler/main_sampler.py
# - sampler/main_drumstyle_sampler.py
# - sampler/main_percussion_sampler.py
# - sampler/main_phrases_sampler.py

def create_sample_part(index, sample_path, key_min, key_max):
    part = ET.Element("MultiSamplePart")
    part.set("Id", str(index))
    part.set("HasImportedSlicePoints", "false")
    # ... 40+ more LOC ...
    return part
```

**Recommendation**: Extract to `scripts/core/sampler_xml.py`

---

## Configuration Hardcoding Issues

### Batch Sizes (hardcoded as 32)
```python
# Appears in 10+ functions
samples_per_rack = 32  # ← Always hardcoded
max_complete_racks = len(all_samples) // samples_per_rack

# Should be configurable:
CONFIG = {
    'drum_rack_size': 32,
    'sampler_size': 32,
    'simpler_is_single': True
}
```

### MIDI Mappings (hardcoded)
```python
# Drum racks: C1 (36) - assumes first note is 36
# Samplers: C2 (48) - assumes first note is 48
# Simpler: 0-127 - full range

# Should be:
MIDI_CONFIG = {
    'drum_rack': {
        'start_note': 36,  # C1
        'total_pads': 32
    },
    'sampler': {
        'start_note': 48,  # C2
        'total_keys': 32
    },
    'simpler': {
        'start_note': 0,
        'total_keys': 128
    }
}
```

### Excluded Folders (hardcoded)
```python
# Appears in 3+ functions
excluded = {'Kick', 'Snare', 'Clap', 'Hihat', 'Shaker', 'Cymbal'}

# Should be:
SAMPLE_CATEGORIES = {
    'drum': ['Kick', 'Snare', 'Clap', 'Hihat', 'Shaker', 'Cymbal'],
    'percussion': ['Percussion', 'Tom', 'Cowbell', 'Conga']
}
```

### Path Handling (hardcoded assumption)
```python
# Assumes 3-level directory structure
rel_path = "../../" + '/'.join(sample_path.split('/')[-3:])

# Should be computed:
def make_relative_path(absolute_path, relative_to_depth=3):
    parts = absolute_path.split('/')
    return "../" * relative_to_depth + '/'.join(parts[-relative_to_depth:])
```

---

## Error Handling Gaps

### Current Error Handling
```python
try:
    # ... code ...
except Exception as e:
    print(f"Error: {e}")
    # ❌ Silent failure, no logging, no recovery
```

### Required Error Handling
```python
class AbletonDeviceError(Exception):
    """Base exception for Ableton operations"""
    pass

class SampleValidationError(AbletonDeviceError):
    """Raised when sample file is invalid"""
    pass

class XMLParseError(AbletonDeviceError):
    """Raised when XML parsing fails"""
    pass

class FileCompressionError(AbletonDeviceError):
    """Raised when gzip compression fails"""
    pass

# Usage:
try:
    xml = decode_adg(path)
except FileCompressionError as e:
    logger.error(f"Failed to decompress {path}: {e}")
    # Could retry or skip
except Exception as e:
    logger.critical(f"Unexpected error: {e}")
    raise
```

---

## Testing Priorities (TDD Order)

### Tier 1: Core Utilities (MUST HAVE 100% COVERAGE)
```python
# tests/test_encoder.py
def test_encode_adg_writes_gzip_file()
def test_encode_adg_with_invalid_content_raises()
def test_encode_adg_preserves_xml_declaration()

# tests/test_decoder.py
def test_decode_adg_reads_gzip_file()
def test_decode_adg_with_missing_file_raises()
def test_decode_adg_returns_valid_xml_string()

# tests/test_transformer.py
def test_transform_xml_finds_drum_pads()
def test_transform_xml_updates_sample_paths()
def test_transform_xml_maintains_relative_paths()
def test_transform_xml_with_none_samples_skips()

# tests/test_simpler_transformer.py
def test_transform_simpler_xml_creates_multisamplepart()
def test_transform_simpler_xml_sets_all_attributes()
def test_transform_simpler_xml_handles_absolute_paths()
```

### Tier 2: Helper Functions
```python
# tests/test_sample_organizer.py
def test_get_descriptive_name_extracts_part_after_space()
def test_get_all_samples_validates_files()
def test_get_sample_batch_paginates_correctly()
def test_organize_drum_samples_combines_categories()
```

### Tier 3: Integration Tests
```python
# tests/integration/test_drum_rack_creation.py
def test_full_drum_rack_creation_workflow()
def test_drum_rack_creation_with_real_samples()

# tests/integration/test_sampler_creation.py
def test_full_sampler_creation_workflow()
```

---

## Performance Optimization Opportunities

### Currently Inefficient
```python
# Re-imports decoder for each file
for file in files:
    from decoder import decode_adg  # ❌ Reload each time
    xml = decode_adg(file)
```

### Should Be
```python
# Import once, reuse
from scripts.utils import decode_adg

for file in files:
    xml = decode_adg(file)  # ✓ Single import
```

### XML Parsing Optimization
```python
# Current: Parse XML multiple times
xml1 = ET.fromstring(content)
xml2 = ET.fromstring(content)  # ❌ Redundant

# Should: Parse once, reuse
root = ET.fromstring(content)
pads = root.findall(".//DrumBranchPreset")
# Use root for all operations
```

### Batch Processing Opportunities
```python
# Could batch multiple samples into single ADG if needed
# Currently creates one ADG per batch of 32 samples
# Could create one ADG with 64+ samples and handle pagination UI-side
```

---

## Summary Table

| Aspect | Current | Issues | Target |
|--------|---------|--------|--------|
| **Import System** | Inconsistent (3 styles) | Non-reusable, fragile | Unified package imports |
| **Code Duplication** | 40% | Hard to maintain | <10% via extraction |
| **Test Coverage** | 0% | High bug risk | 100% for core, 90% overall |
| **Error Handling** | Generic try/except | Silent failures | Custom exceptions + logging |
| **Configuration** | Hardcoded everywhere | Non-flexible | Config file + env vars |
| **XML Structure** | Inconsistent | Different for each type | Consistent abstraction |
| **Documentation** | Minimal | Hard to understand | Comments + diagrams |
| **CLI Interface** | Raw scripts | Not user-friendly | Proper CLI tool |

---

## Migration Path to Web App

### Phase 1: Prepare Python Code
1. Add tests (100% core coverage)
2. Refactor imports
3. Extract utilities
4. Create configuration system

### Phase 2: Port to TypeScript
1. Create `lib/core/` with same utilities
2. Use pako.js for gzip (instead of Node gzip)
3. Use DOMParser for XML (browser-native)
4. Implement file handling via File API

### Phase 3: Create React Components
1. File upload component
2. Sample organization UI
3. Device preview/configuration
4. Download results

### Phase 4: Full Next.js App
1. Server-side processing (optional)
2. Batch download handling (JSZip)
3. Preset management
4. User accounts

