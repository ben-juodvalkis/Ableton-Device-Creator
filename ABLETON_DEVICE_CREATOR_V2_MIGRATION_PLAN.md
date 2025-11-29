# Ableton Device Creator V2.0 - Migration Plan

**Date**: 2025-11-28
**Source Repo**: `/Users/Shared/DevWork/GitHub/Looping/scripts`
**Target Repo**: `/Users/Shared/DevWork/GitHub/Ableton Device Creator`
**GitHub**: https://github.com/ben-juodvalkis/Ableton-Device-Creator

---

## Executive Summary

This plan migrates sophisticated device creation, preset extraction, and analysis tools from the Looping project to a standalone public repository. The old Ableton Device Creator repo will be completely refreshed with modern, production-ready tooling.

**Migration Type**: Major V2.0 reboot (not incremental update)

---

## Phase 1: Archive Old Code & Prepare Clean Slate

### 1.1 Archive V1 Code

```bash
cd "/Users/Shared/DevWork/GitHub/Ableton Device Creator"

# Create archive branch for V1 history
git checkout main
git checkout -b archive-v1-2025-11-28

# Move old code to archive
mkdir -p archive-v1
git mv scripts archive-v1/
git mv docs archive-v1/ 2>/dev/null || true
git commit -m "Archive V1 scripts before V2 migration

- Moving all V1 code to archive-v1/
- Preserves git history for reference
- Preparing for V2.0 complete rewrite"

# Return to main and create clean V2 structure
git checkout main
git merge archive-v1-2025-11-28
```

### 1.2 Clean Root Directory

```bash
# Remove temporary files (keep .git, .gitignore, README.md)
rm -f *.adg *.xml *.als "3_2025-03-10_148bpm_Unknown (1)" 2>/dev/null || true
rm -f Donor*.* Looper*.xml temp*.xml 2>/dev/null || true
rm -rf "Ableton Project Info" "Maschine Imports" "Phrases Samplers" "Simpler Examples" 2>/dev/null || true
rm -rf "Output" "output-sampler" "input_rack_variations" src node_modules 2>/dev/null || true
rm -f package*.json *.code-workspace 2>/dev/null || true

git add -A
git commit -m "Clean root directory for V2 structure"
```

---

## Phase 2: Create V2 Directory Structure

### 2.1 New Directory Layout

```bash
# Create main directories
mkdir -p {drum-racks,instrument-racks,macro-mapping,conversion,sampler,simpler,analysis}
mkdir -p {omnisphere,kontakt,native-instruments}
mkdir -p {templates/drum-racks,templates/instrument-racks,templates/omnisphere}
mkdir -p {utils,docs,examples}

# Create subdirectories
mkdir -p drum-racks/{batch,creation,modification}
mkdir -p macro-mapping/{cc-control,transpose,color-coding}
mkdir -p omnisphere/{extraction,restructuring,analysis}
mkdir -p kontakt/decoding
mkdir -p native-instruments/{nksn-extraction,osc-server}
mkdir -p examples/{drum-racks,preset-extraction,advanced}
```

### 2.2 Directory Structure Overview

```
Ableton-Device-Creator/
├── README.md                           # New comprehensive documentation
├── LICENSE                             # MIT License
├── .gitignore                          # Updated for Python/Node
│
├── drum-racks/                         # Drum rack creation & manipulation
│   ├── batch/                          # Batch processing scripts
│   ├── creation/                       # Device creation from samples
│   └── modification/                   # Existing device modification
│
├── instrument-racks/                   # Instrument rack creation
│   ├── wrapping/                       # Wrap devices in racks
│   └── multi-device/                   # Dual/triple device racks
│
├── macro-mapping/                      # Macro control automation
│   ├── cc-control/                     # CC Control mapping
│   ├── transpose/                      # Transpose mapping
│   └── color-coding/                   # Pad color automation
│
├── conversion/                         # Device conversion utilities
│   ├── simpler-to-drumcell/
│   └── adg-converter/
│
├── sampler/                            # Sampler device creation
│   └── chromatic-mapping/
│
├── simpler/                            # Simpler device creation
│
├── omnisphere/                         # Omnisphere preset tools
│   ├── extraction/                     # Extract .aupreset from .prt_omn
│   ├── restructuring/                  # Reorganize preset libraries
│   └── analysis/                       # Analyze preset structure
│
├── kontakt/                            # Kontakt tools
│   └── decoding/                       # NKI file decoder
│
├── native-instruments/                 # NI Expansion tools
│   ├── nksn-extraction/               # NKSN format tools
│   └── osc-server/                    # OSC server for preset browsing
│
├── analysis/                           # Device analysis tools
│   ├── compare/                        # Compare devices
│   └── extract/                        # Extract device data
│
├── utils/                              # Shared utilities
│   ├── decoder.py                      # ADG/ADV decoder
│   ├── encoder.py                      # ADG/ADV encoder
│   ├── transformer.py                  # XML transformation
│   └── __init__.py
│
├── templates/                          # Device templates
│   ├── drum-racks/
│   ├── instrument-racks/
│   └── omnisphere/
│
├── docs/                               # Documentation
│   ├── DRUM_RACKS.md
│   ├── PRESET_EXTRACTION.md
│   ├── MACRO_MAPPING.md
│   ├── ADVANCED_USAGE.md
│   └── CONTRIBUTING.md
│
└── examples/                           # Usage examples
    ├── drum-racks/
    ├── preset-extraction/
    └── advanced/
```

---

## Phase 3: File Migration Mapping

### 3.1 DO NOT MIGRATE (Stay in Looping Repo)

These scripts are part of the Looping project build/runtime:

```
❌ generate-instruments-json.ts          # Looping build process
❌ generate-max-device-config.ts         # Looping build process
❌ setup-ipad.js                         # Looping runtime tool
❌ osc-debug.js                          # Looping dev tool
❌ totalmix-*.js                         # Looping audio interface tools
❌ detect-interfaces.js                  # Looping network tool
❌ create-status-page.js                 # Looping UI tool
❌ copy-track-types.js                   # Looping config tool
❌ constants.py, copy-constants.js       # Looping config management
```

### 3.2 MIGRATE - Drum Rack Tools

**Source**: `Looping/scripts/device-creation/python/drum_rack/*`
**Destination**: `Ableton-Device-Creator/drum-racks/`

```bash
# Creation scripts -> drum-racks/creation/
cp "device-creation/python/device/drum_rack/main.py" "drum-racks/creation/"
cp "device-creation/python/device/drum_rack/main_percussion.py" "drum-racks/creation/"
cp "device-creation/python/device/drum_rack/main_simple_folder.py" "drum-racks/creation/"
cp "device-creation/python/device/drum_rack/main_by_note_name.py" "drum-racks/creation/"
cp "device-creation/python/drum_rack/create_dual_folder_drum_rack.py" "drum-racks/creation/"
cp "device-creation/python/drum_rack/create_dual_folder_drum_rack_v2.py" "drum-racks/creation/"
cp "device-creation/python/drum_rack/create_triple_folder_electro_acoustic_rack.py" "drum-racks/creation/"
cp "device-creation/python/drum_rack/create_multivelocity_drum_rack.py" "drum-racks/creation/"
cp "device-creation/python/drum_rack/create_multivelocity_drum_rack_v2.py" "drum-racks/creation/"
cp "device-creation/python/drum_rack/create_from_template.py" "drum-racks/creation/"

# Batch processing -> drum-racks/batch/
cp "device-creation/python/device/drum_rack/batch_battery_kits.py" "drum-racks/batch/"
cp "device-creation/python/device/drum_rack/batch_battery_kits_organized.py" "drum-racks/batch/"
cp "device-creation/python/device/drum_rack/batch_process_all_expansions.py" "drum-racks/batch/"
cp "device-creation/python/drum_rack/batch_process_dual_racks.py" "drum-racks/batch/"
cp "device-creation/python/drum_rack/batch_remap_drum_racks.py" "drum-racks/batch/"
cp "device-creation/python/drum_rack/batch_trim_to_16.py" "drum-racks/batch/"
cp "device-creation/python/drum_rack/batch_wrap_pairs.py" "drum-racks/batch/"
cp "device-creation/python/drum_rack/batch_shift_second_chain.py" "drum-racks/batch/"
cp "device-creation/bash_electro_acoustic_racks.py" "drum-racks/batch/"
cp "device-creation/bash_electro_acoustic_unique_racks.py" "drum-racks/batch/"

# Modification scripts -> drum-racks/modification/
cp "device-creation/python/drum_rack/remap_drum_rack_notes.py" "drum-racks/modification/"
cp "device-creation/python/drum_rack/trim_drum_racks_to_16.py" "drum-racks/modification/"
cp "device-creation/python/drum_rack/replace_foreign_samples.py" "drum-racks/modification/"
cp "device-creation/python/drum_rack/merge_drum_racks.py" "drum-racks/modification/"
cp "device-creation/python/drum_rack/expand_instrument_racks.py" "drum-racks/modification/"
cp "device-creation/python/drum_rack/shift_second_chain_midi.py" "drum-racks/modification/"
cp "device-creation/python/drum_rack/disable_auto_color.py" "drum-racks/modification/"
```

### 3.3 MIGRATE - Macro Mapping Tools

```bash
# CC Control -> macro-mapping/cc-control/
cp "device-creation/python/add_cc_control_to_drum_rack.py" "macro-mapping/cc-control/"
cp "device-creation/python/add_cc_control_to_drum_rack_v2.py" "macro-mapping/cc-control/"
cp "device-creation/python/add_cc_control_string_based.py" "macro-mapping/cc-control/"
cp "device-creation/python/drum_rack/apply_cc_mappings_preserve_values.py" "macro-mapping/cc-control/"
cp "device-creation/python/drum_rack/apply_drumcell_cc_mappings.py" "macro-mapping/cc-control/"
cp "device-creation/python/drum_rack/apply_drumcell_cc_mappings_with_macros.py" "macro-mapping/cc-control/"
cp "device-creation/python/drum_rack/batch_apply_cc_mappings.py" "macro-mapping/cc-control/"
cp "device-creation/python/drum_rack/generate_cc_preset_map.py" "macro-mapping/cc-control/"
cp "device-creation/python/configure_drum_rack_macros.py" "macro-mapping/cc-control/"
cp "device-creation/python/rename_drum_rack_macros.py" "macro-mapping/cc-control/"

# Transpose mapping -> macro-mapping/transpose/
cp "device-creation/python/drum_rack/batch_add_transpose_mapping.py" "macro-mapping/transpose/"
cp "device-creation/python/update_transpose_range.py" "macro-mapping/transpose/"

# Color coding -> macro-mapping/color-coding/
cp "device-creation/python/drum_rack/apply_color_coding.py" "macro-mapping/color-coding/"
cp "device-creation/python/drum_rack/apply_drum_rack_colors.py" "macro-mapping/color-coding/"
cp "device-creation/python/drum_rack/batch_apply_colors.py" "macro-mapping/color-coding/"

# General macro tools -> macro-mapping/
cp "device-creation/python/step1_remove_macro_mapping.py" "macro-mapping/"
cp "device-creation/python/step1_remove_macro_mapping_v2.py" "macro-mapping/"
cp "device-creation/python/step2_add_cc_control.py" "macro-mapping/"
cp "device-creation/python/step3_add_macro_mapping.py" "macro-mapping/"
cp "device-creation/python/step4_set_macro_value.py" "macro-mapping/"
cp "device-creation/python/drum_rack/batch_set_macro_value.py" "macro-mapping/"
cp "device-creation/python/rename_macro_16_custom_e.py" "macro-mapping/"
cp "device-creation/python/drum_rack/apply_template_mappings.py" "macro-mapping/"
```

### 3.4 MIGRATE - Instrument Rack Tools

```bash
# Wrapping tools -> instrument-racks/wrapping/
cp "device-creation/python/drum_rack/wrap_device_in_rack.py" "instrument-racks/wrapping/"
cp "device-creation/python/drum_rack/wrap_device_in_rack_template.py" "instrument-racks/wrapping/"
cp "device-creation/python/drum_rack/wrap_two_devices_in_rack.py" "instrument-racks/wrapping/"
cp "device-creation/python/drum_rack/wrap_drum_racks_in_instrument_rack.py" "instrument-racks/wrapping/"

# Multi-device racks -> instrument-racks/multi-device/
cp "device-creation/python/batch_aupreset_wrapper.py" "instrument-racks/multi-device/"
cp "device-creation/python/round_robin_creator.py" "instrument-racks/multi-device/"
cp "device-creation/python/batch_round_robin_8dio.py" "instrument-racks/multi-device/"
```

### 3.5 MIGRATE - Conversion Tools

```bash
# Device conversion -> conversion/
cp "device-creation/python/conversion/simpler_to_drumcell.py" "conversion/simpler-to-drumcell/"
cp "device-creation/python/conversion/drum_rack_simpler_to_drumcell.py" "conversion/simpler-to-drumcell/"
cp "device-creation/python/conversion/batch_convert_drum_racks.py" "conversion/simpler-to-drumcell/"

cp "device-creation/python/device/conversion/adg_converter.py" "conversion/adg-converter/"
cp "device-creation/python/device/conversion/apply_macro_mappings.py" "conversion/adg-converter/"
cp "device-creation/python/device/conversion/map_macros_with_values.py" "conversion/adg-converter/"
cp "device-creation/python/device/conversion/set_macro_values.py" "conversion/adg-converter/"
cp "device-creation/python/device/conversion/add_parameter_visibility.py" "conversion/adg-converter/"
cp "device-creation/python/device/conversion/scan_adg_files.py" "conversion/adg-converter/"
```

### 3.6 MIGRATE - Sampler & Simpler Tools

```bash
# Sampler -> sampler/chromatic-mapping/
cp "device-creation/python/device/sampler/main_sampler.py" "sampler/chromatic-mapping/"
cp "device-creation/python/device/sampler/main_drumstyle_sampler.py" "sampler/chromatic-mapping/"
cp "device-creation/python/device/sampler/main_percussion_sampler.py" "sampler/chromatic-mapping/"
cp "device-creation/python/device/sampler/main_phrases_sampler.py" "sampler/chromatic-mapping/"
cp "device-creation/python/device/sampler/auto_sampled_drum_racks.py" "sampler/chromatic-mapping/"

# Simpler -> simpler/
cp "device-creation/python/device/simpler/main_simpler.py" "simpler/"
```

### 3.7 MIGRATE - Omnisphere Tools

```bash
# Extraction -> omnisphere/extraction/
cp "preset-extraction/spectrasonics/omnisphere/extraction/omnisphere_3_full_extractor.py" "omnisphere/extraction/"
cp "preset-extraction/spectrasonics/omnisphere/extraction/omnisphere_3_pure_extractor.py" "omnisphere/extraction/"
cp "preset-extraction/spectrasonics/omnisphere/extraction/omnisphere_mass_extractor_final.py" "omnisphere/extraction/"
cp "preset-extraction/spectrasonics/omnisphere/extraction/apply_working_template.py" "omnisphere/extraction/"
cp "preset-extraction/spectrasonics/omnisphere/extraction/apply_working_template_batch.py" "omnisphere/extraction/"
cp "preset-extraction/spectrasonics/omnisphere/tools/batch_pitchbend_modifier.py" "omnisphere/extraction/"
cp "preset-extraction/spectrasonics/omnisphere/tools/modify_arp_phase.py" "omnisphere/extraction/"
cp "preset-extraction/spectrasonics/omnisphere/tools/modify_arp_phase_inplace.py" "omnisphere/extraction/"

# Restructuring -> omnisphere/restructuring/
cp "restructure-omnisphere.ts" "omnisphere/restructuring/"
cp "consolidation-engine.ts" "omnisphere/restructuring/"
cp "validate-consolidation-rules.ts" "omnisphere/restructuring/"
cp "config/omnisphere-consolidation-rules.js" "omnisphere/restructuring/"

# Analysis -> omnisphere/analysis/
cp "audit-omnisphere-presets.ts" "omnisphere/analysis/"
cp "analyze-omnisphere-structure.ts" "omnisphere/analysis/"
cp "build-hierarchical-index.ts" "omnisphere/analysis/"
cp "preset-extraction/spectrasonics/omnisphere/compare_orb_automation.py" "omnisphere/analysis/"
cp "preset-extraction/spectrasonics/omnisphere/compare_orb_settings.py" "omnisphere/analysis/"
cp "preset-extraction/spectrasonics/omnisphere/analyze_host_automation.py" "omnisphere/analysis/"
```

### 3.8 MIGRATE - Kontakt Tools

```bash
# Decoding -> kontakt/decoding/
cp "kontakt-nki-decoder.py" "kontakt/decoding/"
cp "nki_analyzer.py" "kontakt/decoding/"
cp "nki_complete_mapper.py" "kontakt/decoding/"
cp "nki_mapping_extractor.py" "kontakt/decoding/"
cp "nki_simple_analyzer.py" "kontakt/decoding/"
cp "unpack_kga.py" "kontakt/decoding/"
cp "unpack_kpk.py" "kontakt/decoding/"
```

### 3.9 MIGRATE - Native Instruments Tools

```bash
# NKSN extraction -> native-instruments/nksn-extraction/
cp -r "preset-extraction/native-instruments/tools/" "native-instruments/nksn-extraction/tools/"
cp -r "preset-extraction/native-instruments/utilities/" "native-instruments/nksn-extraction/utilities/"
cp -r "preset-extraction/native-instruments/archive/" "native-instruments/nksn-extraction/archive/"

# OSC Server -> native-instruments/osc-server/
cp -r "preset-extraction/native-instruments/osc-server/" "native-instruments/osc-server/"
cp -r "preset-extraction/native-instruments/max-msp/" "native-instruments/max-msp/"
```

### 3.10 MIGRATE - Analysis Tools

```bash
# Analysis -> analysis/
cp "analyze_drum_racks.py" "analysis/compare/"
cp "analyze_drum_racks_detailed.py" "analysis/compare/"
cp "device-creation/python/drum_rack/compare_drum_racks.py" "analysis/compare/"
cp "device-creation/python/drum_rack/deep_compare_xml.py" "analysis/compare/"
cp "compare_aupresets.py" "analysis/compare/"

cp "extract_vst_state.py" "analysis/extract/"
cp "find_cc_mappings.py" "analysis/extract/"
cp "decode_plugin_state.py" "analysis/extract/"
```

### 3.11 MIGRATE - Utilities

```bash
# Core utilities -> utils/
cp "device-creation/python/utils/decoder.py" "utils/"
cp "device-creation/python/utils/encoder.py" "utils/"
cp "device-creation/python/utils/transformer.py" "utils/"
cp "device-creation/python/utils/simpler_transformer.py" "utils/"
cp "device-creation/python/utils/pitch_shifter.py" "utils/"
cp "device-creation/python/utils/scroll_position.py" "utils/"
cp "device-creation/python/utils/set_macro.py" "utils/"
cp "device-creation/python/utils/batch_pitch_shift.py" "utils/"
cp "device-creation/python/utils/batch_scroll_position.py" "utils/"
cp "device-creation/python/utils/__init__.py" "utils/"
```

### 3.12 MIGRATE - Templates

```bash
# Templates -> templates/
cp -r "device-creation/templates/Drum Racks/" "templates/drum-racks/"
cp "device-creation/templates/input_rack.adg" "templates/drum-racks/"
cp "device-creation/templates/input_rack_no_release.adg" "templates/drum-racks/"
cp "device-creation/templates/instrument_rack_dual_drums_template.adg" "templates/instrument-racks/"
cp "device-creation/templates/Mini Template.adg" "templates/instrument-racks/"
cp "device-creation/templates/sampler-rack.adg" "templates/"
cp "device-creation/templates/simpler-template.adv" "templates/"
cp -r "device-creation/templates/Omnisphere/" "templates/omnisphere/"
```

### 3.13 MIGRATE - Meta Scripts (Batch Processors)

```bash
# Meta processors -> drum-racks/batch/
cp "device-creation/python/meta/main.py" "drum-racks/batch/meta_main.py"
cp "device-creation/python/meta/main_folders.py" "drum-racks/batch/meta_main_folders.py"
cp "device-creation/python/meta/main_percussion.py" "drum-racks/batch/meta_main_percussion.py"
```

---

## Phase 4: Post-Migration Cleanup

### 4.1 Update Import Paths

After migration, all Python scripts need updated imports. Create a migration script:

```python
# fix_imports.py
import os
import re
from pathlib import Path

def update_imports(file_path):
    """Update import statements to match new structure"""
    with open(file_path, 'r') as f:
        content = f.read()

    # Update common import patterns
    replacements = {
        r'from device-creation\.python\.utils': 'from utils',
        r'from \.\.utils': 'from utils',
        r'from utils\.utils': 'from utils',
        r'import sys\s+sys\.path\.insert.*': '',  # Remove old path hacks
    }

    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)

    with open(file_path, 'w') as f:
        f.write(content)

# Run on all Python files
for py_file in Path('.').rglob('*.py'):
    if 'archive-v1' not in str(py_file):
        update_imports(py_file)
```

### 4.2 Create Package Structure

```bash
# Add __init__.py to make directories Python packages
find . -type d -not -path "*/archive-v1/*" -not -path "*/.git/*" -exec touch {}/__init__.py \;
```

### 4.3 Create Requirements File

```bash
cat > requirements.txt << 'EOF'
# Core dependencies
lxml>=4.9.0
# Add other dependencies as discovered during testing
EOF
```

### 4.4 Update .gitignore

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Output directories
output/
output-*/
Output/
test-output/

# Temporary files
temp*.xml
temp*.adg
temp*.adv
*.tmp

# Node (if any JS utilities)
node_modules/
package-lock.json
EOF
```

---

## Phase 5: Documentation Creation

### 5.1 Main README.md

Create comprehensive `README.md` (see Section 6 for full content)

### 5.2 Category-Specific Documentation

```bash
# Create documentation files
touch docs/DRUM_RACKS.md
touch docs/PRESET_EXTRACTION.md
touch docs/MACRO_MAPPING.md
touch docs/ADVANCED_USAGE.md
touch docs/CONTRIBUTING.md
touch docs/CHANGELOG.md
```

See Section 7 for documentation outlines.

### 5.3 Example Files

```bash
# Create example usage files
touch examples/drum-racks/01_create_from_samples.sh
touch examples/drum-racks/02_batch_process_expansions.sh
touch examples/drum-racks/03_apply_cc_control.sh
touch examples/preset-extraction/01_extract_omnisphere.sh
touch examples/preset-extraction/02_decode_kontakt.sh
touch examples/advanced/01_dual_device_rack.sh
```

---

## Phase 6: Main README.md Content

```markdown
# Ableton Device Creator V2.0

Professional toolkit for creating, modifying, and extracting Ableton Live devices and presets.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Overview

Comprehensive suite of tools for:
- **Drum Rack Creation**: Generate drum racks from sample libraries with intelligent categorization
- **Macro Automation**: Batch apply CC control, transpose, and color coding
- **Preset Extraction**: Extract Omnisphere, Kontakt, and Native Instruments presets
- **Device Conversion**: Convert between Simpler/Drumcell and other formats
- **Advanced Racks**: Create multi-device instrument racks with complex routing

## Features

### 🥁 Drum Rack Tools
- Create organized drum racks from any sample folder
- Intelligent sample categorization (kicks, snares, hats, etc.)
- Multi-velocity layer support
- Batch processing for entire libraries
- Custom pad layouts and mappings

### 🎹 Instrument Rack Tools
- Wrap multiple devices in instrument racks
- Dual/triple device rack creation
- Round-robin sample rotation
- Custom macro routing

### 🎛️ Macro Mapping
- Automated CC Control integration
- Batch transpose mapping
- Smart color coding by sample type
- Preserve existing mappings while adding new ones

### 🎼 Preset Extraction
- **Omnisphere**: Extract .aupreset files from .prt_omn
- **Kontakt**: Decode .nki files and extract mappings
- **Native Instruments**: NKSN format extraction and conversion

### 🔧 Device Conversion
- Simpler → Drumcell conversion
- ADG format conversion with macro preservation
- Batch conversion with path updates

## Quick Start

### Installation

```bash
git clone https://github.com/ben-juodvalkis/Ableton-Device-Creator.git
cd Ableton-Device-Creator
pip install -r requirements.txt
```

### Basic Usage

**Create drum rack from samples:**
```bash
python3 drum-racks/creation/main.py \
  templates/drum-racks/input_rack.adg \
  "/path/to/samples"
```

**Batch process sample library:**
```bash
python3 drum-racks/batch/meta_main_folders.py \
  templates/drum-racks/input_rack.adg \
  "/path/to/sample/library"
```

**Extract Omnisphere presets:**
```bash
python3 omnisphere/extraction/omnisphere_3_full_extractor.py \
  "/path/to/omnisphere/library"
```

**Add CC Control to drum racks:**
```bash
python3 macro-mapping/cc-control/batch_apply_cc_mappings.py \
  "/path/to/drum/racks"
```

## Documentation

- **[Drum Racks Guide](docs/DRUM_RACKS.md)** - Complete drum rack creation and modification
- **[Preset Extraction](docs/PRESET_EXTRACTION.md)** - Omnisphere, Kontakt, NI tools
- **[Macro Mapping](docs/MACRO_MAPPING.md)** - CC control and automation
- **[Advanced Usage](docs/ADVANCED_USAGE.md)** - Multi-device racks and conversions

## Project Structure

```
├── drum-racks/              # Drum rack creation & batch processing
├── instrument-racks/        # Multi-device instrument racks
├── macro-mapping/           # CC control, transpose, color coding
├── conversion/              # Device format conversion
├── sampler/                 # Chromatic sampler creation
├── simpler/                 # Simpler device generation
├── omnisphere/              # Omnisphere extraction & restructuring
├── kontakt/                 # Kontakt NKI decoding
├── native-instruments/      # NI expansion tools
├── analysis/                # Device comparison & extraction
├── utils/                   # Shared utilities (decoder, encoder, transformer)
├── templates/               # Device templates (.adg, .adv)
├── docs/                    # Detailed documentation
└── examples/                # Usage examples
```

## Requirements

- **Python 3.8+**
- **Ableton Live 11+** (for testing generated devices)
- **lxml** (for XML processing)

## Use Cases

### Music Producers
- Organize sample libraries into browsable drum racks
- Create custom instrument racks from multiple devices
- Batch process entire expansion libraries

### Sound Designers
- Extract and reorganize preset libraries
- Create multi-layered instruments
- Automate repetitive device configuration

### Live Performers
- Build performance-ready racks with CC control
- Create color-coded drum layouts
- Generate consistent device naming and organization

## Examples

See [examples/](examples/) directory for detailed usage examples:
- Basic drum rack creation
- Batch processing workflows
- Preset extraction pipelines
- Advanced multi-device racks

## Contributing

Contributions welcome! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

Built for the Ableton Live community. Special thanks to all contributors and users who've provided feedback.

## Support

- **Issues**: [GitHub Issues](https://github.com/ben-juodvalkis/Ableton-Device-Creator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ben-juodvalkis/Ableton-Device-Creator/discussions)

---

**Version**: 2.0.0
**Last Updated**: 2025-11-28
```

---

## Phase 7: Documentation Outlines

### 7.1 docs/DRUM_RACKS.md Outline

```markdown
# Drum Rack Creation & Modification

## Table of Contents
1. Basic Drum Rack Creation
2. Batch Processing
3. Multi-Velocity Layers
4. Dual/Triple Device Racks
5. Modification Tools
6. Troubleshooting

## 1. Basic Drum Rack Creation

### Single Folder Processing
- main.py - Standard NI expansion layout
- main_simple_folder.py - Generic folder processing
- main_by_note_name.py - Note-based naming

### Template Selection
- input_rack.adg - Standard template with release
- input_rack_no_release.adg - No release tail
- Mini Template.adg - Minimal footprint

## 2. Batch Processing

### Meta Scripts
- meta_main.py - Process multiple expansions
- meta_main_folders.py - Recursive folder processing
- batch_process_all_expansions.py - Complete library processing

## 3. Multi-Velocity Layers
[Detailed guide...]

## 4. Dual/Triple Device Racks
[Detailed guide...]

## 5. Modification Tools
- Remap notes
- Trim to 16 pads
- Replace foreign samples
- Merge drum racks
- Color coding

## 6. Troubleshooting
[Common issues and solutions...]
```

### 7.2 docs/PRESET_EXTRACTION.md Outline

```markdown
# Preset Extraction Tools

## Omnisphere
### Extraction
- Full extraction pipeline
- Batch processing
- Template-based extraction

### Restructuring
- Reorganize preset libraries
- Consolidation rules
- Hierarchical indexing

### Analysis
- Preset structure analysis
- Automation comparison
- Coverage auditing

## Kontakt
### NKI Decoding
- Basic decoder usage
- Mapping extraction
- Complete analysis

### Package Extraction
- KGA unpacking
- KPK unpacking

## Native Instruments
### NKSN Extraction
- Reveal NKSN data
- Batch conversion
- Database exploration

### OSC Integration
- OSC server setup
- Max/MSP integration
- Preset browsing
```

### 7.3 docs/MACRO_MAPPING.md Outline

```markdown
# Macro Mapping & Automation

## CC Control Integration
- Add CC Control to drum racks
- Batch processing
- Preserve existing mappings
- DrumCell-specific mappings

## Transpose Mapping
- Batch add transpose mapping
- Update transpose ranges

## Color Coding
- Automatic color assignment by sample type
- Batch apply colors
- Custom color schemes

## Advanced Macro Operations
- Remove mappings
- Rename macros
- Set macro values
- Template-based mapping
```

### 7.4 docs/ADVANCED_USAGE.md Outline

```markdown
# Advanced Usage

## Multi-Device Instrument Racks
- Wrap devices in racks
- Dual/triple device racks
- Round-robin sample rotation
- AUPreset wrapper

## Device Conversion
- Simpler to DrumCell
- ADG converter
- Macro mapping preservation

## Custom Workflows
- Pipeline processing
- Template customization
- Integration with DAW workflows

## Scripting & Automation
- Python API usage
- Custom transformations
- Batch processing strategies
```

### 7.5 docs/CONTRIBUTING.md Outline

```markdown
# Contributing to Ableton Device Creator

## Code of Conduct
[Standard CoC]

## How to Contribute
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

## Code Style
- Python: PEP 8
- TypeScript: Prettier defaults
- Descriptive variable names
- Comments for complex logic

## Testing
- Test with real Ableton devices
- Include sample test files
- Document expected behavior

## Documentation
- Update relevant docs
- Add examples for new features
- Include command-line help

## Pull Request Process
[PR guidelines]
```

---

## Phase 8: Testing & Validation

### 8.1 Test Each Category

After migration, test representative scripts from each category:

```bash
# Test drum rack creation
python3 drum-racks/creation/main_simple_folder.py \
  templates/drum-racks/input_rack.adg \
  "test-samples/"

# Test macro mapping
python3 macro-mapping/cc-control/add_cc_control_to_drum_rack_v2.py \
  "test-rack.adg"

# Test Omnisphere extraction
python3 omnisphere/extraction/omnisphere_3_pure_extractor.py \
  "test-preset.prt_omn"

# Test utilities
python3 -c "from utils.decoder import decode_adg; print('Import successful')"
```

### 8.2 Validation Checklist

```markdown
- [ ] All Python scripts have correct imports
- [ ] Templates load correctly
- [ ] Drum rack creation works
- [ ] Macro mapping functions
- [ ] Omnisphere extraction works
- [ ] Kontakt decoder functions
- [ ] Utils are importable
- [ ] No broken file references
- [ ] Documentation links work
- [ ] Examples run successfully
```

---

## Phase 9: Git Operations & Release

### 9.1 Commit Migration

```bash
# Add all new files
git add .

# Commit with detailed message
git commit -m "V2.0 Migration: Complete toolkit restructure

Major changes:
- Migrated 100+ production-ready scripts from Looping project
- Organized into logical categories (drum-racks, preset-extraction, etc.)
- Added comprehensive documentation
- Created templates directory with working .adg/.adv files
- Updated all import paths
- Added examples for common workflows

New structure:
- drum-racks/: Creation, batch processing, modification
- macro-mapping/: CC control, transpose, color coding
- omnisphere/: Extraction, restructuring, analysis
- kontakt/: NKI decoding and analysis
- native-instruments/: NKSN extraction, OSC server
- instrument-racks/: Multi-device racks
- conversion/: Format conversion tools
- utils/: Shared decoder/encoder/transformer

Breaking changes from V1:
- Complete directory restructure
- Python 3.8+ required
- New import paths
- V1 code archived in archive-v1/ branch

Migration from V1: Not recommended - V2 is complete rewrite"

# Tag release
git tag -a v2.0.0 -m "Version 2.0.0 - Complete rewrite with production tools"

# Push to GitHub
git push origin main
git push origin v2.0.0
git push origin archive-v1-2025-11-28
```

### 9.2 GitHub Release Notes

Create release on GitHub with these notes:

```markdown
# Ableton Device Creator V2.0.0

## Major Rewrite

Complete overhaul with production-ready tools migrated from live performance system.

## New Features

### Drum Rack Tools
- 15+ creation scripts for various sample layouts
- Batch processing for entire libraries
- Multi-velocity layer support
- Dual/triple device rack creation

### Macro Mapping
- Automated CC Control integration
- Batch transpose mapping
- Smart color coding
- Preserve existing mappings

### Preset Extraction
- Omnisphere: Full .aupreset extraction from .prt_omn
- Kontakt: NKI decoder with mapping extraction
- Native Instruments: NKSN format tools

### Advanced Features
- Multi-device instrument racks
- Device format conversion
- Simpler → DrumCell conversion
- Round-robin sample rotation

## Breaking Changes

⚠️ **Complete rewrite - not compatible with V1**

- New directory structure
- Updated import paths
- Python 3.8+ required
- Different CLI arguments

V1 users: V1 code preserved in `archive-v1` branch

## Installation

```bash
git clone https://github.com/ben-juodvalkis/Ableton-Device-Creator.git
cd Ableton-Device-Creator
pip install -r requirements.txt
```

## Documentation

- [Drum Racks Guide](docs/DRUM_RACKS.md)
- [Preset Extraction](docs/PRESET_EXTRACTION.md)
- [Macro Mapping](docs/MACRO_MAPPING.md)
- [Advanced Usage](docs/ADVANCED_USAGE.md)

## What's Next

- Video tutorials
- More examples
- Community templates
- CI/CD testing

## Acknowledgments

Built from 2+ years of production use in professional live looping system.
```

---

## Phase 10: Post-Release Tasks

### 10.1 Update Looping Repo

After successful migration, clean up Looping repo:

```bash
cd "/Users/Shared/DevWork/GitHub/Looping"

# Update CLAUDE.md to reference new repo
# Add note about device creation scripts moving

# Optional: Add git submodule for device creator if needed
git submodule add https://github.com/ben-juodvalkis/Ableton-Device-Creator scripts/device-creation
```

### 10.2 Create Cross-Links

Update both repos to reference each other:

**Looping README.md:**
```markdown
## Related Projects

Device creation and preset extraction tools have been moved to:
[Ableton Device Creator](https://github.com/ben-juodvalkis/Ableton-Device-Creator)
```

**Device Creator README.md:**
```markdown
## Related Projects

These tools were developed for and used in:
[Live Looping System](https://github.com/ben-juodvalkis/Looping) - Professional iPad-controlled live performance system
```

---

## Execution Checklist

When executing in Ableton Device Creator repo, follow this order:

```markdown
Phase 1: Archive & Clean
- [ ] Create archive-v1 branch
- [ ] Move old code to archive-v1/
- [ ] Clean root directory
- [ ] Commit archive

Phase 2: Structure
- [ ] Create directory structure
- [ ] Verify all directories created

Phase 3: Migration
- [ ] Copy drum-rack files
- [ ] Copy macro-mapping files
- [ ] Copy instrument-rack files
- [ ] Copy conversion files
- [ ] Copy sampler/simpler files
- [ ] Copy omnisphere files
- [ ] Copy kontakt files
- [ ] Copy NI files
- [ ] Copy analysis files
- [ ] Copy utils files
- [ ] Copy templates
- [ ] Verify all files copied

Phase 4: Cleanup
- [ ] Run import fix script
- [ ] Add __init__.py files
- [ ] Create requirements.txt
- [ ] Update .gitignore
- [ ] Test imports

Phase 5: Documentation
- [ ] Write main README.md
- [ ] Write docs/DRUM_RACKS.md
- [ ] Write docs/PRESET_EXTRACTION.md
- [ ] Write docs/MACRO_MAPPING.md
- [ ] Write docs/ADVANCED_USAGE.md
- [ ] Write docs/CONTRIBUTING.md
- [ ] Create examples

Phase 6: Testing
- [ ] Test drum rack creation
- [ ] Test macro mapping
- [ ] Test preset extraction
- [ ] Test utils imports
- [ ] Run validation checklist

Phase 7: Release
- [ ] Commit all changes
- [ ] Tag v2.0.0
- [ ] Push to GitHub
- [ ] Create GitHub release
- [ ] Update description

Phase 8: Post-Release
- [ ] Update Looping repo
- [ ] Add cross-links
- [ ] Announce on social media (if desired)
```

---

## File Migration Reference Sheet

Quick reference for what goes where:

| Source Category | Destination | File Count |
|----------------|-------------|------------|
| drum_rack/*.py | drum-racks/ | ~60 files |
| CC control scripts | macro-mapping/cc-control/ | ~10 files |
| Transpose scripts | macro-mapping/transpose/ | ~3 files |
| Color scripts | macro-mapping/color-coding/ | ~3 files |
| Instrument rack wrapping | instrument-racks/wrapping/ | ~4 files |
| Multi-device racks | instrument-racks/multi-device/ | ~3 files |
| Conversion scripts | conversion/ | ~9 files |
| Sampler creation | sampler/chromatic-mapping/ | ~5 files |
| Simpler creation | simpler/ | ~1 file |
| Omnisphere extraction | omnisphere/extraction/ | ~8 files |
| Omnisphere restructuring | omnisphere/restructuring/ | ~4 files |
| Omnisphere analysis | omnisphere/analysis/ | ~6 files |
| Kontakt decoding | kontakt/decoding/ | ~7 files |
| NI NKSN tools | native-instruments/nksn-extraction/ | ~15 files |
| NI OSC server | native-instruments/osc-server/ | ~8 files |
| Analysis tools | analysis/ | ~8 files |
| Core utils | utils/ | ~10 files |
| Templates | templates/ | ~10 files |

**Total**: ~170+ files migrated

---

## Notes & Warnings

### Important Considerations

1. **Test Before Deleting**: Don't delete anything from Looping repo until V2 is tested and working
2. **Path Updates**: Many scripts have hardcoded paths - will need manual review
3. **Dependencies**: Some scripts may have undocumented dependencies
4. **Templates**: Verify all template .adg/.adv files load in Ableton
5. **Archive Access**: Keep archive-v1 branch accessible for reference

### Known Issues to Address

1. Some scripts use `sys.path.insert()` hacks - remove these
2. Inconsistent error handling - standardize
3. Mix of Python 2/3 string handling - audit for Python 3.8+
4. Some scripts have no CLI help - add argparse
5. Template paths are absolute in some files - make relative

### Future Improvements

1. Add pytest test suite
2. Create GitHub Actions for validation
3. Build Docker container for consistent environment
4. Create video tutorials
5. Add more example workflows
6. Create web-based documentation
7. Build GUI wrapper for common operations

---

## Success Criteria

The migration is successful when:

✅ All 170+ files copied to new structure
✅ Import statements updated and working
✅ Representative test from each category passes
✅ Documentation covers all major features
✅ README.md is comprehensive and clear
✅ Templates load correctly in Ableton
✅ GitHub release is published
✅ V1 code is safely archived
✅ Cross-links between repos are updated

---

## Timeline Estimate

- **Phase 1-2** (Archive & Structure): 30 minutes
- **Phase 3** (Migration): 1-2 hours
- **Phase 4** (Cleanup): 1 hour
- **Phase 5** (Documentation): 2-3 hours
- **Phase 6** (Testing): 1-2 hours
- **Phase 7** (Release): 30 minutes
- **Phase 8** (Post-release): 30 minutes

**Total**: ~8-10 hours of focused work

---

## Contact for Issues

When executing this plan, if you encounter:
- **Import errors**: Check utils/__init__.py and relative imports
- **Missing files**: Verify source path in Looping repo
- **Template errors**: Check .adg/.adv files aren't corrupted
- **Git conflicts**: Use `git status` and resolve before proceeding

---

**End of Migration Plan**

This document should be saved and referenced during the migration process. Execute phases sequentially and check off items as completed.
