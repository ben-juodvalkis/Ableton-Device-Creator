# CLI Guide - Ableton Device Creator

Command-line interface for creating and modifying Ableton Live devices.

## Installation

### Install with CLI support:
```bash
pip install ableton-device-creator[cli]
```

### Or install Click separately:
```bash
pip install click>=8.0.0
```

## Quick Start

```bash
# Show all commands
adc --help

# Create drum rack from samples
adc drum-rack create samples/

# Create chromatic sampler
adc sampler create samples/ --layout chromatic

# Apply colors to drum rack
adc drum-rack color MyRack.adg
```

---

## Commands Reference

### `adc drum-rack create`

Create a drum rack from audio samples.

**Usage:**
```bash
adc drum-rack create SAMPLES_DIR [OPTIONS]
```

**Options:**
- `-o, --output PATH` - Output ADG file path (default: `output/<folder_name>.adg`)
- `-t, --template PATH` - Template ADG file (default: `templates/input_rack.adg`)
- `--layout [standard|808|percussion]` - MIDI note layout (default: `standard`)
- `--categorize / --no-categorize` - Auto-categorize samples (default: enabled)
- `--recursive / --no-recursive` - Search subdirectories (default: enabled)

**Examples:**
```bash
# Create from folder with auto-categorization
adc drum-rack create samples/kicks/

# Create with custom output
adc drum-rack create samples/ -o MyCustomRack.adg

# Create with 808 layout
adc drum-rack create samples/ --layout 808

# Non-recursive, no categorization
adc drum-rack create samples/ --no-recursive --no-categorize
```

**Layouts:**
- `standard` - Kicks at C1, snares at D1, hats at F#1, etc.
- `808` - Classic TR-808 layout
- `percussion` - Optimized for percussion samples

---

### `adc drum-rack color`

Apply color coding to drum rack pads based on sample type.

**Usage:**
```bash
adc drum-rack color DEVICE [OPTIONS]
```

**Options:**
- `-o, --output PATH` - Output file (default: overwrite input)

**Examples:**
```bash
# Color pads (overwrites file)
adc drum-rack color MyRack.adg

# Color pads (save to new file)
adc drum-rack color MyRack.adg -o ColoredRack.adg
```

**Color scheme:**
- Kicks: Orange
- Snares: Red
- Hats: Yellow
- Claps: Pink
- Toms: Purple
- Cymbals: Blue
- Percussion: Green

---

### `adc drum-rack remap`

Remap MIDI notes for drum rack pads (shift octaves/keys).

**Usage:**
```bash
adc drum-rack remap DEVICE --shift SEMITONES [OPTIONS]
```

**Options:**
- `-s, --shift INTEGER` - Semitones to shift (required)
- `-o, --output PATH` - Output file (default: overwrite input)
- `--scroll-shift INTEGER` - View scroll adjustment (default: auto)

**Examples:**
```bash
# Shift up one octave
adc drum-rack remap MyRack.adg --shift 12

# Shift down one octave
adc drum-rack remap MyRack.adg --shift -12

# Shift with custom scroll
adc drum-rack remap MyRack.adg --shift 12 --scroll-shift 3
```

---

### `adc sampler create`

Create a Multi-Sampler instrument from audio samples.

**Usage:**
```bash
adc sampler create SAMPLES_DIR [OPTIONS]
```

**Options:**
- `-o, --output PATH` - Output ADG file (default: `output/<folder>_sampler.adg`)
- `-t, --template PATH` - Template ADG file (default: `templates/sampler-rack.adg`)
- `--layout [chromatic|drum|percussion]` - Key mapping (default: `chromatic`)
- `--max-samples INTEGER` - Max samples per instrument (default: 32)

**Examples:**
```bash
# Create chromatic sampler (C-2 upward)
adc sampler create samples/ --layout chromatic

# Create drum-style sampler
adc sampler create samples/ --layout drum

# Limit to 16 samples
adc sampler create samples/ --max-samples 16
```

**Layouts:**
- `chromatic` - Maps samples chromatically from C-2 (note 0) upward
- `drum` - 8 kicks, 8 snares, 8 hats, 8 perc (notes 0-31)
- `percussion` - Maps samples chromatically from C1 (note 36) upward

---

### `adc simpler create`

Create individual Simpler devices from audio samples.

**Usage:**
```bash
adc simpler create SAMPLES_DIR [OPTIONS]
```

**Options:**
- `-o, --output-folder PATH` - Output folder (default: `output/<folder>_simplers`)
- `-t, --template PATH` - Template ADV file (default: `templates/simpler-template.adv`)
- `--recursive / --no-recursive` - Search subdirectories (default: no)

**Examples:**
```bash
# Create Simpler for each sample
adc simpler create samples/

# Custom output folder
adc simpler create samples/ -o my_simplers/

# Process subdirectories
adc simpler create samples/ --recursive
```

---

### `adc util decode`

Decode ADG/ADV file to XML for inspection or editing.

**Usage:**
```bash
adc util decode FILE [OPTIONS]
```

**Options:**
- `-o, --output PATH` - Output XML file (default: `<input>.xml`)

**Examples:**
```bash
# Decode to XML
adc util decode MyRack.adg

# Specify output file
adc util decode MyRack.adg -o rack.xml
```

---

### `adc util encode`

Encode XML file to ADG/ADV format.

**Usage:**
```bash
adc util encode FILE --output OUTPUT
```

**Options:**
- `-o, --output PATH` - Output ADG/ADV file (required)

**Examples:**
```bash
# Encode XML to ADG
adc util encode MyRack.xml -o MyRack.adg

# Encode to ADV
adc util encode MySimpler.xml -o MySimpler.adv
```

---

### `adc util info`

Show information about ADG/ADV file.

**Usage:**
```bash
adc util info FILE
```

**Examples:**
```bash
# Show device info
adc util info MyRack.adg
```

**Output:**
- File size (compressed and uncompressed)
- Compression ratio
- Device type (Drum Rack, Sampler, etc.)
- Sample count

---

## Workflows

### Workflow 1: Complete Drum Rack Setup

```bash
# 1. Create drum rack from samples
adc drum-rack create samples/drums/ -o MyKit.adg

# 2. Apply color coding
adc drum-rack color MyKit.adg

# 3. Remap to higher octave (optional)
adc drum-rack remap MyKit.adg --shift 12 -o MyKit_High.adg
```

### Workflow 2: Sampler Library Creation

```bash
# Create chromatic samplers for different categories
adc sampler create samples/kicks/ --layout chromatic -o Kicks.adg
adc sampler create samples/snares/ --layout chromatic -o Snares.adg
adc sampler create samples/hats/ --layout chromatic -o Hats.adg
```

### Workflow 3: Simpler Library

```bash
# Create individual Simpler devices
adc simpler create samples/oneshots/ -o oneshots_simplers/

# Process entire library recursively
adc simpler create "Native Instruments/Library/" --recursive
```

### Workflow 4: Inspect and Modify

```bash
# 1. Decode to XML
adc util decode MyRack.adg -o MyRack.xml

# 2. Edit MyRack.xml in your favorite editor
vim MyRack.xml

# 3. Re-encode to ADG
adc util encode MyRack.xml -o MyRack_Modified.adg

# 4. Check the result
adc util info MyRack_Modified.adg
```

---

## Tips & Best Practices

### 1. **Template Management**

Keep your templates organized:
```
templates/
├── input_rack.adg          # Default drum rack template
├── sampler-rack.adg        # Default sampler template
├── simpler-template.adv    # Default Simpler template
└── custom/
    ├── 808_template.adg
    └── percussion_template.adg
```

### 2. **Batch Processing**

Process multiple folders:
```bash
#!/bin/bash
for folder in samples/*/; do
    name=$(basename "$folder")
    adc drum-rack create "$folder" -o "output/${name}.adg"
    adc drum-rack color "output/${name}.adg"
done
```

### 3. **Sample Organization**

Organize samples for best categorization:
```
samples/
├── kicks/
│   ├── Kick_01.wav
│   └── Kick_02.wav
├── snares/
│   ├── Snare_01.wav
│   └── Snare_02.wav
└── hats/
    ├── HH_Closed_01.wav
    └── HH_Open_01.wav
```

### 4. **Output Organization**

Use consistent naming:
```bash
adc drum-rack create samples/808/ -o "output/drum-racks/808_Kit.adg"
adc sampler create samples/bass/ -o "output/samplers/Bass_Chromatic.adg"
adc simpler create samples/fx/ -o "output/simplers/fx/"
```

---

## Troubleshooting

### Click Not Installed
```
Error: Click is not installed. Install with: pip install ableton-device-creator[cli]
```
**Solution:** Install Click: `pip install click>=8.0.0`

### Template Not Found
```
Error: Template not found: templates/input_rack.adg
```
**Solution:** Specify template path: `--template /path/to/template.adg`

### No Samples Found
```
Error: No valid audio samples found in /path/to/folder
```
**Solution:**
- Check folder contains .wav, .aif, .aiff, .flac, or .mp3 files
- Use `--recursive` if samples are in subdirectories

### Permission Denied
```
Error: Failed to write file: Permission denied
```
**Solution:**
- Check write permissions for output directory
- Specify different output location: `-o /path/with/permissions/`

---

## Advanced Usage

### Custom Python Scripts with CLI

You can also use the CLI programmatically:

```python
from ableton_device_creator.cli import main
import sys

# Simulate command-line arguments
sys.argv = ['adc', 'drum-rack', 'create', 'samples/', '-o', 'output.adg']
main()
```

### Environment Variables

Set default paths:
```bash
export ADC_TEMPLATES="/path/to/templates"
export ADC_OUTPUT="/path/to/output"
```

---

## See Also

- [API Documentation](api/README.md)
- [Examples](../examples/)
- [V3 Implementation Plan](current-plan/V3_IMPLEMENTATION_PLAN.md)
