# Ableton Device Creator - Comprehensive Codebase Overview

## Executive Summary

Ableton Device Creator is a Python-based toolkit for creating and modifying Ableton Live devices (drum racks, sampler instruments, and Simpler devices) from audio sample libraries. The project is transitioning toward a Next.js web application while maintaining the core Python infrastructure. Total Python codebase: ~2,724 lines across 22 scripts.

---

## Current Architecture

### Overall Workflow
1. **Input**: ADG/ADV files (gzipped XML) + Sample audio library
2. **Processing**: Decode → Transform XML → Encode
3. **Output**: New ADG/ADV files with organized samples

### Technology Stack
- **Backend**: Python 3.6+ (current implementation)
- **Frontend**: TypeScript/Next.js (planned migration)
- **File Format**: ADG/ADV (gzipped XML)
- **Dependencies**:
  - Python standard library (gzip, xml.etree.ElementTree, argparse, pathlib)
  - Node.js: fast-xml-parser (for future TypeScript implementation)
  - No external Python dependencies (standalone)

---

## Directory Structure

```
/scripts
├── device/                  # Device creation main scripts
│   ├── drum_rack/          # Drum rack creation (3 variants)
│   ├── sampler/            # Sampler instrument creation (4 variants)
│   ├── simpler/            # Simpler device creation (1 variant)
│   ├── generic/            # Generic folder processing
│   └── conversion/          # Format conversion utilities
├── utils/                   # Core utilities (encode/decode/transform)
├── meta/                    # Batch/recursive processing scripts
├── ableton/
│   └── analysis/           # Ableton Live set analysis
└── max/                    # Max/MSP JavaScript integration

/src
├── lib/
│   ├── services/
│   │   ├── AbletonParser/  # TypeScript parsing service
│   │   └── AbletonModifier/ # TypeScript modification service
│   └── utils/              # File utilities

/docs                        # Documentation
/output                      # Device output directory
/Simpler Examples           # Example Simpler devices
```

---

## Core Components

### 1. ENCODER/DECODER (Gzip compression layer)

**Files**: `scripts/utils/encoder.py` (16 LOC), `scripts/utils/decoder.py` (19 LOC)

```python
# encoder.py: Gzip XML → .adg file
def encode_adg(xml_content: str, output_path: Path) -> None

# decoder.py: .adg file → XML string
def decode_adg(adg_path: Path) -> str
```

**Purpose**: Handle gzip compression/decompression for ADG/ADV files
**Key Insight**: ADG files are simply gzip-compressed XML - very simple implementation

---

### 2. TRANSFORMER (XML modification layer)

**File**: `scripts/utils/transformer.py` (102 LOC)

**Core Functions**:
- `transform_xml(xml_content, sample_paths)` - Updates DrumCell sample references
- `get_drum_cell_info(xml_content)` - Analyzes drum rack structure

**Architecture**:
- Uses ElementTree for XML parsing
- Finds all `DrumBranchPreset` elements (32 individual pads)
- Sorts pads by MIDI note (ReceivingNote)
- Updates both absolute and relative file paths
- Returns XML string with declaration

**Key Pattern**:
```python
# Path element structure:
FileRef/
  ├─ Path (absolute path)
  └─ RelativePath ("../../" + last 3 components)
```

---

### 3. SIMPLER TRANSFORMER

**File**: `scripts/utils/simpler_transformer.py` (201 LOC)

**Core Functions**:
- `transform_simpler_xml(xml_content, sample_path)` - Creates single-sample Simpler device
- `get_simpler_info(xml_content)` - Extracts sample metadata

**Architecture**:
- Creates/updates `MultiSampleMap/MultiSamplePart` structure
- Sets 15+ XML attributes for proper Simpler functionality:
  - `KeyRange` (0-127)
  - `VelocityRange` (1-127)
  - `SelectorRange` (0-127)
  - `RootKey` (60 = middle C)
  - Metadata (Name, LomId, Selection, IsActive, Solo)

**Key Differences from Drum Rack**:
- Single sample per device
- Covers full keyboard range (0-127)
- Includes sample analysis metadata (DefaultSampleRate, DefaultDuration)
- Uses absolute paths for reliability

---

## Device Creation Scripts

### A. Drum Rack Scripts (3 variants)

#### 1. `scripts/device/drum_rack/main.py` (215 LOC)
**Purpose**: Create organized drum racks from Native Instruments expansion libraries

**Workflow**:
1. Parse library structure: `Samples/Drums/{Kick,Snare,Clap,Hihat,Shaker,Percussion,Tom}`
2. Get 8 samples from each category
3. Combine into groups of 32 (4 categories × 8 samples)
4. Create multiple racks if enough samples
5. Name: `{Library} {Batch} {Descriptor}`

**Key Functions**:
- `organize_drum_samples()` - Organizes by category, returns batch
- `get_all_samples_from_folders()` - Gets samples with filtering
- `get_sample_batch()` - Pagination logic
- `get_library_name()` - Extracts clean name from path

**Sample Organization**:
```
Batch layout (32 pads):
[8 remaining] + [8 hihat/shaker] + [8 snare/clap] + [8 kick]
```

#### 2. `scripts/device/drum_rack/main_percussion.py` (133 LOC)
**Purpose**: Create percussion-only drum racks

**Workflow**:
1. Extract percussion samples only
2. Create sequential batches of 32
3. Name: `{Library} Percussion {Batch}`

**Key Difference**: No category-based organization, just sorted samples

#### 3. `scripts/device/generic/main_generic.py` (172 LOC)
**Purpose**: Process ANY folder structure (not just Expansion libraries)

**Workflow**:
1. Get all WAV files from folder
2. Sort alphabetically
3. Validate audio files (try opening with wave module)
4. Create batches of 32
5. Name: `{Parent} {Folder} {Batch}`

**Key Feature**: Works with arbitrary folder hierarchies

---

### B. Sampler Scripts (4 variants)

#### 1. `scripts/device/sampler/main_sampler.py` (150 LOC)
**Purpose**: Create sampler instruments from sample folder

**Key Difference from Drum Racks**:
- MIDI notes instead of drum pads
- Each sample = one key
- Maps: C2 (MIDI 48) → 48+N (Nth sample)
- Creates multiple samplers for >32 samples

**XML Structure**:
```xml
MultiSampleMap/
  ├─ SampleParts/
  │   ├─ MultiSamplePart (Id="0", key=48)
  │   ├─ MultiSamplePart (Id="1", key=49)
  │   └─ ...
```

#### 2. `scripts/device/sampler/main_drumstyle_sampler.py` (177 LOC)
**Purpose**: Create drum-style samplers from library structure

**Key Difference**:
- Organizes by drum categories (like drum_rack/main.py)
- Uses different MIDI key range
- Combines categories into 32-key layout

#### 3. `scripts/device/sampler/main_percussion_sampler.py` (163 LOC)
**Purpose**: Percussion-only sampler creation

#### 4. `scripts/device/sampler/main_phrases_sampler.py` (125 LOC)
**Purpose**: Create sampler for each subfolder (phrase/loop organization)

**Unique Pattern**:
- Iterates subfolders of parent folder
- One sampler per subfolder
- Output: `{Parent}/{Subfolder} [01-N].adg`

---

### C. Simpler Script

#### `scripts/device/simpler/main_simpler.py` (112 LOC)
**Purpose**: Create individual Simpler device per sample

**Key Points**:
- One device per audio file (unlike samplers/drum racks)
- Output: `{Folder}/{Filename}.adv`
- Supports: WAV, AIF, AIFF
- Maintains folder structure in output
- Uses absolute paths for reliability

---

## Utility Scripts

### Sample Organization Utilities

**`scripts/utils/set_macro.py`** (106 LOC)
- Updates macro control values in ADG files
- Finds: `MacroDefaults.{N-1}` and `MacroControls.{N-1}/Manual`
- Batch processes folders recursively
- Range validation: Macro 1-127, Value 0-127

**`scripts/utils/scroll_position.py`** (69 LOC)
- Modifies `PadScrollPosition` element
- Useful for hiding pads not in use
- Range: 0-31 (represents which pads are visible)

**`scripts/utils/pitch_shifter.py`** (92 LOC)
- Shifts MIDI note assignments in drum racks
- Changes `ReceivingNote` values in `DrumBranchPreset`
- Default: shifts down 16 semitones

**`scripts/utils/batch_*.py`**
- `batch_pitch_shift.py` (101 LOC) - Batch pitch shifting
- `batch_scroll_position.py` (104 LOC) - Batch scroll position updates
- Recursive folder processing patterns

---

## Batch/Meta Processing Scripts

### `scripts/meta/main.py` (94 LOC)
**Purpose**: Process multiple Native Instruments expansions
- Finds all library folders in expansions directory
- Spawns `scripts/device/drum_rack/main.py` for each
- Output: `Output/{Library Name}/`

### `scripts/meta/main_folders.py` (108 LOC)
**Purpose**: Process folder hierarchies recursively
- Finds all folders containing WAV files
- Maintains folder structure in output
- Spawns `scripts/device/generic/main_generic.py` for each

### `scripts/meta/main_percussion.py` (101 LOC)
**Purpose**: Batch percussion-only rack creation
- Finds libraries with percussion samples
- Reports percussion sample counts
- Spawns `scripts/device/drum_rack/main_percussion.py` for each

---

## TypeScript/Next.js Architecture (Planned)

### Current TypeScript Implementation

**`src/lib/services/AbletonParser/index.ts`** (109 LOC)
- Parses Ableton Live sets (.als files, not devices)
- Analyzes track structure (Audio/MIDI/Return/Master/Group)
- Detects clips in arrangement and session view
- Error codes: `NO_TRACKS`, `PARSE_ERROR`

**`src/lib/services/AbletonModifier/index.ts`** (73 LOC)
- Removes unwanted tracks from sets
- Filters: MIDI tracks, audio tracks without arrangement clips
- Uses XMLBuilder for output formatting

**`src/lib/services/AbletonParser/types.ts`** (24 LOC)
```typescript
interface AbletonTrack {
  id: string;
  name: string;
  type: 'audio' | 'midi' | 'return' | 'master' | 'group';
  hasArrangementClips: boolean;
  shouldRemove: boolean;
}

interface AbletonSetAnalysis {
  totalTracks: number;
  tracksToKeep: AbletonTrack[];
  tracksToRemove: AbletonTrack[];
}
```

**`src/lib/utils/fileUtils.ts`** (48 LOC)
- `backupFile()` - Create timestamped backup
- `processAbletonFile()` - Generic file processing wrapper

**`src/lib/services/AbletonParser/store.ts`** (31 LOC)
- Svelte store for analysis state
- Methods: `setAnalysis()`, `setLoading()`, `setError()`

---

## Ableton Live Set Analysis

**`scripts/ableton/analysis/analyze_als.py`** (318 LOC)
**Purpose**: Analyze and rename Ableton Live sets based on metadata

**Key Features**:
- Extracts audio clips from "Master Resample" track
- Parses tempo, time signature, creation date
- Generates organized filenames
- CSV export functionality

**Unique Logic**:
- Time signature decoding: `value - 197 = numerator` (201 = 4/4)
- Metadata extraction from `AudioClip/SampleRef/FileRef`
- Filename sanitization for Windows compatibility

---

## Key Architectural Patterns

### 1. Import Path Issues
**Problem**: Inconsistent import statements across scripts
- Some use relative imports: `from decoder import decode_adg`
- Some use package imports: `from scripts.utils.decoder import decode_adg`
- Some use sys.path manipulation: `sys.path.append(str(Path(__file__).parent.parent.parent))`

**Impact**: Scripts not easily importable, difficult to create unified library

### 2. Code Duplication
High duplication across similar scripts:

| Function | Appears In | Times |
|----------|-----------|-------|
| `get_descriptive_name()` | 4+ scripts | 5 |
| `get_all_samples_from_folders()` | 3+ scripts | 4 |
| `get_sample_batch()` | 4+ scripts | 5 |
| `transform_sampler_xml()` | 4+ scripts | 4 |
| `create_sample_part()` | 4+ scripts | 4 |

### 3. Hardcoded Values
- Batch size: 32 (samples per device) - hardcoded in many places
- MIDI note ranges: C2 (48) for samplers, C1 (36) for drums
- Excluded folders: `{'Kick', 'Snare', 'Clap', 'Hihat', 'Shaker', 'Cymbal'}`
- Relative path prefix: `"../../"` (assumes 3-level hierarchy)

### 4. XML Attribute Inconsistencies
Different scripts create different XML structures:
- Drum racks: Only `Id` and `HasImportedSlicePoints`
- Samplers: Add `Name`, `KeyRange`, `RootKey`
- Simplers: Full 15+ attributes including ranges and metadata

### 5. Naming Conventions
- Variable naming: Snake case throughout
- Function naming: Verb_object pattern (`organize_drum_samples`, `get_library_name`)
- Class naming: Not used - all scripts are functional

---

## Testing Infrastructure

**Current State**: NO TESTS FOUND
- No `tests/` directory
- No `conftest.py` or pytest configuration
- No test fixtures
- No CI/CD pipeline configured

**CLAUDE.md Requirements**: Strict TDD methodology
- Tests must be written first
- Minimum 90% code coverage
- 100% coverage for core utilities
- Every bug fix must include reproducing test

---

## Technical Debt & Pain Points

### Critical Issues

1. **No test coverage**
   - Impact: Unable to refactor safely
   - Required by project guidelines
   - High risk for bugs in production

2. **Import path chaos**
   - `scripts/device/drum_rack/main.py` uses `from decoder import...`
   - `scripts/device/sampler/main_sampler.py` uses `from utils.decoder import...`
   - `scripts/device/sampler/main_drumstyle_sampler.py` uses `from scripts.utils.decoder import...`
   - Makes code non-reusable

3. **Massive code duplication**
   - ~40% duplication across sampler/drum rack variants
   - Makes maintenance nightmare
   - Bug fixes must be applied in multiple places

4. **No error handling**
   - Generic `try/except` with single error message
   - No validation of sample files before processing
   - No rollback mechanism on failure

5. **Hardcoded MIDI mappings**
   - Drum racks: C1-G#3 (36-67, assumes 32 pads)
   - Samplers: C2-... (48-79)
   - Simpler: Full range (0-127)
   - No configuration for custom layouts

### Medium Issues

6. **Path handling inconsistencies**
   - Mix of Path objects and strings
   - Relative path generation hardcoded: `"../../" + '/'.join(path_parts[-3:])`
   - Assumes 3-level directory structure

7. **File validation gaps**
   - Only validates WAV files (not AIF/AIFF properly)
   - No sample rate validation
   - No bit depth validation

8. **Performance concerns**
   - XML parsing via ElementTree (adequate but not optimized)
   - No batch processing optimization
   - Re-reads decoder.py for each file

9. **Documentation gaps**
   - No inline comments explaining XML structure
   - No diagram of MIDI note mappings
   - No sample library structure requirements

10. **Inconsistent naming**
    - `organize_drum_samples()` vs `organize_sampler_samples()`
    - `transform_xml()` vs `transform_sampler_xml()`
    - No consistent module structure

---

## Dependency Graph

```
Core Layer (Foundation)
├── encoder.py (16 LOC) - Write .adg files
└── decoder.py (19 LOC) - Read .adg files

Transform Layer (Logic)
├── transformer.py (102 LOC) - Drum rack XML ops
├── simpler_transformer.py (201 LOC) - Simpler device XML ops
├── set_macro.py (106 LOC) - Macro control updates
├── scroll_position.py (69 LOC) - Scroll position updates
└── pitch_shifter.py (92 LOC) - MIDI note shifts

Device Creation Layer (Main Scripts)
├── drum_rack/main.py (215 LOC) - Expansion processing
├── drum_rack/main_percussion.py (133 LOC) - Percussion-only racks
├── generic/main_generic.py (172 LOC) - Generic folders
├── sampler/main_sampler.py (150 LOC) - Standard samplers
├── sampler/main_drumstyle_sampler.py (177 LOC) - Category samplers
├── sampler/main_percussion_sampler.py (163 LOC) - Percussion samplers
├── sampler/main_phrases_sampler.py (125 LOC) - Phrase/loop samplers
└── simpler/main_simpler.py (112 LOC) - Individual Simplers

Batch Processing Layer (Meta)
├── meta/main.py (94 LOC) - Process expansions
├── meta/main_folders.py (108 LOC) - Process folder hierarchies
└── meta/main_percussion.py (101 LOC) - Batch percussion racks

TypeScript Layer (Future Web App)
├── AbletonParser (109 LOC) - Parse Ableton sets
├── AbletonModifier (73 LOC) - Modify Ableton sets
└── fileUtils.ts (48 LOC) - File operations
```

---

## Code Statistics

| Metric | Value |
|--------|-------|
| Total Python LOC | 2,724 |
| Total TypeScript LOC | 230 |
| Python Files | 22 |
| TypeScript Files | 5 |
| Test Files | 0 |
| Test Coverage | 0% |
| Code Duplication | ~40% |
| Classes Defined | 0 |
| Functions Defined | 80+ |

---

## Recommended Refactoring Priorities

### Phase 1: Immediate (Prevent Bugs)
1. **Create test suite** for core utilities (100% coverage)
   - Estimated: 200 LOC of tests
   - Covers: encoder, decoder, transformer, simpler_transformer

2. **Consolidate import structure**
   - Create `scripts/__init__.py`
   - Standardize to `from scripts.utils import decode_adg`
   - Move utility modules to package structure

3. **Extract common functions**
   - Create `scripts/core/sample_organizer.py`
   - Move: `get_descriptive_name()`, `get_all_samples_from_folders()`, `get_sample_batch()`
   - Reduces duplication by ~200 LOC

### Phase 2: Medium (Improve Maintainability)
4. **Create configuration system**
   - MIDI note mappings as config
   - Batch sizes configurable
   - Excluded folders as config
   - Path prefix strategy configurable

5. **Error handling framework**
   - Custom exceptions for different failure modes
   - Validation before processing
   - Detailed error reporting

6. **Abstract device creation**
   - Base `DeviceCreator` class
   - Subclasses: `DrumRackCreator`, `SamplerCreator`, `SimplerCreator`
   - Reduces main scripts to ~50 LOC each

### Phase 3: Long-term (Modernization)
7. **Web application**
   - Port core utilities to TypeScript/Next.js
   - Browser-based processing
   - File download batching

8. **CLI tool**
   - Create proper Python package
   - Install via pip
   - Proper version management

---

## Summary

The Ableton Device Creator is a functional but unmaintainable codebase. Its strengths:
- Simple, focused functionality
- No external dependencies (Python)
- Clear ADG file format understanding
- Multiple specialized scripts for different use cases

Its weaknesses:
- No tests (violates project guidelines)
- Extreme code duplication (40%)
- Inconsistent import/module structure
- Hardcoded configuration values
- No error handling strategy
- Impossible to use as a library

The project desperately needs:
1. Test coverage (blocking requirement)
2. Module/import restructuring
3. Code consolidation
4. Configuration abstraction
5. Error handling framework

Once these are addressed, it will be maintainable and ready for web application porting.

