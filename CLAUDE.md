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

### Ad-Hoc Scripts (`scripts/`)

One-off/donor-based workflows that sit on top of the core package rather than
extending its public API — batch-processing specific sample libraries,
donor-template cloning, one-time XML surgery. See **Sampler-Based Drum Rack
Workflow** below for the active one. Not covered by the package's normal
`__init__.py` exports; run directly with `PYTHONPATH=src python3 scripts/<name>.py`.

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
- `decode_adg(file_path) -> str` - Decompress ADG/ADV to XML
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

**Auto-Select (`auto_select.py`, `auto_select_batch.py`):**
- `set_auto_select(xml, enabled=True) -> (xml, AutoSelectReport)` - flip the root
  Drum Rack's `IsAutoSelectEnabled`
- `root_auto_select_index(xml)` - `(root device tag, document-order index, spans)`
- `verify_auto_select(original, result, report)` - result parses, every byte
  outside the `IsAutoSelectEnabled` fields is identical, and exactly one field
  moved: the root device's own, to the requested value
- `set_auto_select_tree(root, enabled=True, ...)` - batch runner behind
  `adc drum-rack auto-select` (`--on/--off`); in place it writes a
  `.adc-tmp.adg` sibling and `os.replace`s it

Live's Auto-Select toggle in the rack's chain list: with it on, playing a pad
selects that pad in the rack view. It is a view preference - no parameter, no
mapping, no sample reference - so a rack sounds the same either way. Measured
against Live 12.4.1's own toggle on `Kit-Carbon` (2026-09-11): that one field on
the root device is the whole gesture, reproduced byte for byte. Live's resave
also rewrote the preset's own `RelativePath`/`Path` provenance and `UserName`,
incidental to the file having been copied out of the User Library; neither is
reproduced.

**`IsAutoSelectEnabled` is not only a rack field, so it cannot be found by
searching for the tag.** A Sampler carries one of its own under
`MultiSampler/ViewSettings` - the same idea one level down, for its zone view.
Which sibling owns the others depends on how the pads are built, and both shapes
are in the library: `Kit-Carbon`'s 17 fields are the rack plus 16 nested
Instrument Racks, while `Perc/Latin/Conga A`'s 33 are the rack plus 32 bare pad
Samplers. The target is resolved structurally with ElementTree (direct child of
the root group device) and then located in the text by document-order index -
the same resolution `sampler/envelope.py` uses for the four `AttackTime` fields,
for the same reason. A first-match-in-the-root-span search was tried first and
the verifier caught it on the 19 Latin racks before anything was written.

Scope is the root device only, which is what Live does - nested racks and pad
Samplers keep their own state. Instrument Rack presets are skipped whole. A root
Drum Rack with no such field is reported, not repaired: where it would belong in
an older schema is a guess, and not one worth making for a view preference.

**Ungrouping pad racks (`ungroup.py`, `ungroup_batch.py`):**
- `ungroup_pads(xml) -> (xml, UngroupReport)` - Live's own "Ungroup" on every
  pad at once: the pad's `GroupDevicePreset` wrapper is replaced by its single
  chain's `AbletonDevicePreset` blocks, in order
- `plan_ungroup(xml)` - the classification plus the `(start, end, text)` edits
- `verify_ungroup(original, result, report)` - pads, notes, mixer and every
  lifted device compared element by element against the original
- `ungroup_tree(root, out_dir=None, in_place=False, ...)` - batch runner behind
  `adc drum-rack ungroup`; `root` may be one `.adg` or a directory. In place it
  writes a `.adc-tmp.adg` sibling and `os.replace`s it; with no `--out` a single
  file is written beside itself as `NAME (ungrouped).adg`

Measured against Live 12.4.1's own ungroup of a Session Drums Club pad
(2026-09-08). Three things happen and nothing else:
- the wrapper goes and its chain's devices move up into the pad chain;
- every `KeyMidi` that addressed the dissolved rack's macros goes, because
  those macros no longer exist. A mapping inside a rack nested *deeper* keeps
  addressing its own rack and stays;
- each freed parameter's mapping range is restored - `MidiCCOnOffThresholds`
  to 64/127 (universal: all 1111 unmapped booleans in the measured file carry
  it, everything else was mapped), `MidiControllerRange` to `PARAM_RANGES`.

**Stored values are never touched, and there is nothing to bake.** Unlike
`unmap` on a script-generated kit, a preset Live saved already holds the
macro-driven value in each mapped parameter's `Manual`; the golden pair
confirms Live rewrites no `Manual` when it ungroups. Restoring the range is
cosmetic - it is inert once the `KeyMidi` is gone - so a parameter whose full
range is not in `PARAM_RANGES` keeps its stored range and is reported rather
than guessed at. Reproduces Live's output byte for byte apart from two fields
incidental to any resave: `RoundRobinRandomSeed` (re-rolled) and an off
Shaper's slot payload (dropped).

A pad is left alone, with a reason, unless its wrapper adds nothing of its own:
one chain, no return chains, full key and velocity range, centred pan, unmuted,
nothing soloed. Two parallel chains spliced into one series chain would change
the sound, so multi-chain racks (the Close/Room donor, for one) are refused, as
are nested Drum Racks.

**Chain level is the one deliberate departure from Live.** Live discards the
chain fader; `ungroup` folds its gain into the pad's own fader instead, which is
exact - two faders in series multiply, and `AudioBranchMixerDevice/Volume` is the
same linear gain on both (range 0.0003162277571..1.99526238, i.e. -70..+6 dB,
identical across all 1863 unmapped instances measured in the library). The pad is
refused only when the fold cannot be done: no pad fader, a macro-mapped pad fader
(Live ignores a mapped parameter's stored value, so the write would do nothing),
or a product outside that range. `--no-fold-chain-volume` reproduces Live.

The chain mixer's own *mappings* still die with the chain and are counted
separately (`key_midi_dropped_with_chain`): the level survives, but the macro
that rode it is gone.

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

**Envelope parameters (`envelope.py`, `envelope_batch.py`):**
- `set_envelope_param(xml, value, param="AttackTime", envelope="amp")` - set one
  envelope parameter on every Sampler in a preset
- `verify_envelope_set(original, result, report)` - result parses, only the
  targeted parameters moved, and every one now holds the requested value
- `set_envelope_tree(root, value, ...)` - batch runner behind `adc sampler set-env`

**A Sampler has four envelopes and they all expose the same parameter names**, so
"amp attack" cannot be found by searching for `AttackTime` - a 32-pad rack has
128 of them (measured 2026-09-11):

```
MultiSampler/VolumeAndPan/Envelope/AttackTime       <- the amp envelope
MultiSampler/.../SimplerFilter/Envelope/AttackTime
MultiSampler/VolumeAndPan/Envelope/Slot/Value/SimplerPitchEnvelope/AttackTime
MultiSampler/.../SimplerSubOsc/Envelope/AttackTime
```

Note the third - **the pitch envelope is nested inside the amp envelope**, so
even "the AttackTime inside VolumeAndPan/Envelope" is ambiguous by text. Targets
are resolved structurally with ElementTree (direct child of direct child) and
then located in the text by document-order index, which is exact because
`Element.iter()` and a left-to-right text scan visit elements in the same order.

**A macro-mapped parameter is never written.** Live ignores the stored `Manual`
of a parameter a macro holds, so the write would be inert; those are counted and
reported instead - the same reasoning as `ungroup` refusing to fold a level into
a macro-mapped fader. A preset where *every* parameter is macro-held is reported
as `nothing_writable_all_macro_held`, never as "already correct" - the
distinction matters, since the latter would claim the value is set when it is
not. Values are written in Live's float32 style (`0.1` stores as `0.1000000015`),
so a preset already holding the value is left byte-identical.

**Thinning (`thin.py`, `thin_batch.py`):**
- `thin_multisamples(xml, max_layers, max_takes) -> (xml, ThinReport)` - drop
  zones until every pad is at most N velocity layers of at most M round-robin
  takes, widening the survivors to cover what the dropped layers held
- `plan_thin(xml, ...)` - the classification plus the `(start, end, text)` edits
- `verify_thin(original, result, report)` - result parses, text outside the zone
  lists is byte-identical, every surviving zone was in the original, and every
  lane still tiles velocity 1-127 with no gap or overlap
- `thin_tree(root, out_dir=None, in_place=False, ...)` - batch runner behind
  `adc sampler thin`; `root` may be one preset or a directory

Autosampled kits carry everything the source library recorded - the Damage and
Abbey Road racks are 10 velocity layers deep with up to 6 takes each, so one
32-pad rack references ~1700 separate files and pulls 1.5 GB into RAM. The
result references a strict *subset* of the original's sample files, so a thinned
rack can only sound like a coarser version of what it came from.

**Velocity centres are never inferred, and must not be** (measured across 7288
pads, 2026-09-11). A layer's recorded centre is not stored in the preset and
every reconstruction fails somewhere: Moonkit pads missing their softest layer
have a first bin stretched down to 1, the Damage Kits ladder puts centres at bin
*maxima* rather than midpoints, and Soundiron's `_v1_`..`_v4_` are layer indices
that read exactly like velocities. Instead a kept layer absorbs the dropped
layers adjacent to it - a run is split between the kept layers on either side -
so every new boundary is one an original bin already had, and contiguity holds
by construction.

Zones are grouped into **lanes by key range and selector range** and each lane
is thinned on its own: the Damage Close/Room racks put two mics in one device on
separate selector ranges, and thinning them as one pool would strip a mic
instead of a dynamic. A chromatic instrument is simply one lane per recorded
note. A lane is left alone, and counted, when its layers do not tile 1-127 or
when a zone uses a real velocity crossfade (18 zones in the library) - those
would have to be re-derived rather than merged.

**Why thin the presets rather than rebuild them from source.** The generator
scripts and their libraries all still resolve, but the racks in the User Library
have been curated well past what the scripts emit: `AR 50s Autumn Kit
Brushes.adg` was renamed `50s Autumn Brushes.adg`, `Drum_Rack_Combo_08.adg`
became `Perc/Damage/Combo/Combo 08.adg`, and every rack has since been
unmapped, macro-hidden and chain-coloured. Filenames and folder curation are
recorded nowhere in the repo, so a rebuild cannot reproduce them. Editing the
presets preserves all of it byte for byte.

### `macro_mapping/` - Macro Controls

**Purpose:** Add macro mappings and modify device parameters
**Classes:**
- `DrumPadColorMapper` - Auto-color drum pads by type
- `TransposeMapper` - Add transpose control to samplers

**Unmapping (`unmap.py`, `unmap_batch.py`):**
- `classify_rack(xml) -> RackInfo` - root class, KeyMidi counts (root-owned vs nested), nested racks, macro names
- `unmap_drum_rack(xml) -> (xml, UnmapReport)` - strip root-owned `KeyMidi`, bake macro-driven values into `Manual`, reset root `MacroDefaults` to -1
- `strip_key_midi`, `reset_macro_defaults`, `bake_plan` - the individual steps
- `verify_unmap(original, result, report)` - element-by-element check of the result against the original
- `unmap_tree(root, out_dir, ...)` - batch runner behind `adc drum-rack unmap`; never writes into `root`, copies every untouched file into `out_dir` so the output tree can replace `root` whole

Rules baked into the module, all measured on the library (2026-09-07):
- Edits are string-level (anchored regexes on the decoded XML). Never re-serialise a Live 12 file through ElementTree for writing: it parses but will not load. ElementTree is read-only here.
- A `KeyMidi` addresses the macros of the innermost rack around it. Mappings inside a nested rack's chains belong to that rack and stay (Live's unmap on the outer rack behaves the same way); mappings chaining a root macro to a nested rack's macro are root-owned and go.
- Live ignores the stored `Manual` of a mapped parameter and, on unmap, writes the macro-driven value in. Generated kits have stale stored values (attack 0.1 ms where the macro produces 353 ms, transpose 32 where it produces 0), so a plain strip would change the sound. `CURVES` holds the per-parameter interpolation (linear, log, t², t³, t⁵, stepped, switch, fader) with the evidence for each; a parameter with no verified curve keeps its stored value and is reported.
- `KeyMidi` blocks come in two textual forms: Live's multi-line block, and a one-line block written by older scripts with the `<Manual>` on the same line. Both are handled.
- Why the mappings are removed rather than re-pointed: the Looping surface (ADR-428) owns every whole-kit gesture as a virtual macro that fans out to each pad's parameters by name; a macro-held parameter is disabled in Live, so the kits must carry no mappings.

**Hiding macros (`hide_macros.py`, `hide_macros_batch.py`):**
- `hide_macros(xml) -> (xml, HideReport)` - on the root Drum Rack only: `AreMacroControlsVisible` to false, `MacroDisplayNames.N` back to `Macro N+1`
- `root_device_span(xml)` - `(tag, start, end)` over the text, `end` being the first *nested* group device, so edits cannot reach into the pads
- `verify_hide(original, result, report)` - result parses, text outside the root span is byte-identical, inside it only those two fields moved, macro values survive
- `hide_macros_tree(root, out_dir=None, in_place=False, ...)` - batch runner behind `adc drum-rack hide-macros`; in place it writes a `.adc-tmp.adg` sibling and `os.replace`s it, so a failure never leaves a half-written preset

The cosmetic counterpart to unmapping, measured on a Live 12.4.15 before/after pair (2026-09-08):
- Those two fields are the whole gesture. Live's resave of the same file also rewrote `MacroDefaults` (from -1 to the current macro values), `RoundRobinRandomSeed`, sample `RelativePath`s, `Upper/LowerDisplayString` and a Simpler range - all incidental to the resave and to the file having moved, none of it reproduced.
- `NumVisibleMacroControls` does *not* change: it is how many knobs the panel would show, not whether the panel is shown.
- Scope is the root device only. Nested racks inside the pads keep their names and panel state, and Instrument Rack presets are skipped whole - the Looping surface drives kits, so only kits need a bare front panel.

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
- `adc drum-rack create|color|remap|unmap|hide-macros|ungroup|auto-select`
- `adc sampler create|thin`
- `adc simpler create`
- `adc util decode|encode|info`

## Sampler-Based Drum Rack Workflow

**Purpose:** build 32-pad Drum Racks where every pad is a full Multi-Sampler
(not a DrumCell/Simpler), loaded with a velocity-layered, round-robin
multisample — for autosampled libraries like Heavyocity Damage that export
one folder per instrument.

**Source filename convention:** `<InstrumentName>-<Note>-V<velocity>-<RRid>.wav`
(e.g. `Alfaias-C#4-V29-BRWQ.wav`), inside a per-instrument folder with
`Close`/`Full` mic-position subfolders. All samples in one folder share a
single recorded root note; velocities cluster into ~10 layer centers with
several round-robin takes each.

**Key files:**
- `scripts/multisample_utils.py` — shared parsing: `parse_velocity_layers()`
  reads a folder into `{velocity_center: [samples]}`, `velocity_bins()` turns
  layer centers into contiguous non-overlapping velocity ranges (split at
  midpoints between centers), `build_sample_parts()` builds the
  `MultiSamplePart` XML elements (fixed on one root note), `enable_round_robin()`
  flips the `MultiSampleMap`'s native `RoundRobin`/`RoundRobinMode` flags
  (Cyclic) so Ableton auto-alternates same-key/same-velocity samples.
- `scripts/create_alfaias_multisample.py` — standalone example: one instrument
  folder → one single-key Sampler `.adg` (built on `templates/sampler-rack.adg`).
- `scripts/create_variety_drum_rack.py` — the main tool: builds full 32-pad
  kits. `KITS` is a dict of kit name → list of `(category, instrument)` pairs;
  edit it to add/change curated kits. `discover_catalog()` +
  `build_random_kits()` generate additional seeded-random kits sampled from
  the whole library (edit `NUM_RANDOM_KITS`/`RANDOM_KIT_SIZE`/`RANDOM_SEED_BASE`
  at the top of the file). `SAMPLE_LIBRARY_ROOT` and `OUTPUT_DIR` are also set
  at the top — **update `SAMPLE_LIBRARY_ROOT` if the source library moves**
  (it has moved once already).

**Critical design rule — never reconstruct rack structure, only swap sample
content:** `templates/sampler_drum_rack_template.adg` is a full 32-pad Drum
Rack built and exported by hand in Ableton Live, with a real Multi-Sampler
already loaded on every pad and macros/colors/choke groups/mixer already
configured as desired. Every pad's `SendingNote` is fixed at 60 (C3)
regardless of which note triggers the pad (`ReceivingNote`, unique per pad),
so every embedded Sampler's `MultiSamplePart`s are built on a single fixed
root note (60) — see `PAD_ROOT_NOTE` in the script. The scripts only ever
touch each pad's `MultiSampleMap/SampleParts` in place; they never clone
devices or copy individual rack-level properties (macros, names, colors,
`NumVisibleMacroControls`, etc.) from one file into another. That approach
was tried first and kept missing fields (macro names live in sibling
`MacroDisplayNames.N`/`MacroColor.N`/`MacroDefaults.N` arrays under
`DrumGroupDevice`, not nested inside `MacroControls.N` — easy to miss).
**If the donor rack itself needs to change** (different macro mapping, pad
count, note layout, envelope settings), rebuild it in Ableton Live, export
it, and copy the new file over `templates/sampler_drum_rack_template.adg` —
don't try to patch it from a script.

**Pad note range is fixed by the donor — do NOT remap `ReceivingNote` from a
script.** Rewriting `ZoneSettings/ReceivingNote` does *not* reposition a Drum
Rack pad in Live's grid; it detaches the chain and the pad loads **empty**.
(Learned the hard way: a Shimmer & Shake build remapped every pad to 36+ to
force a C1 start, and in Live every pad went blank — the fix was to stop
touching `ReceivingNote`.) So scripts must fill the donor's existing pads at
their native notes and leave `ReceivingNote` alone. The donor's 32 pads sit at
`ReceivingNote` 61–92 (all `SendingNote` 60), so kits currently start at C#3
and leave the low pads (36–60) empty below the kit — cosmetic, and the racks
work. `build_rack()` in `create_shimmer_and_shake_kit.py` (and the other kit
scripts) fills the donor's lowest pads first and deletes surplus pads, never
changing a note. **To actually move the kit (e.g. start at C1 with nothing
empty below), rebuild the donor in Ableton Live** with pads on the notes you
want and re-export it over `templates/sampler_drum_rack_template.adg` — per the
template rule above, note layout is a donor change, never a script patch.

**Output:** kits are written to `SAMPLE_LIBRARY_ROOT / "Drum Racks"` (outside
the repo, alongside the source library), not the repo's `output/` directory.
The user has since moved the generated sets into the Ableton User Library
(`.../User Library/Looping Presets/Instruments/Ableton/Perc/Damage Close` and
`.../Damage Room` — note "Full" mic renamed "Room"); safe because sample
references are absolute paths into the unmoved source library.

### Close/Room Combined variant (2026-07)

`scripts/create_damage_close_room_racks.py` builds the same kits (imported via
`compose_all_kits()` from `create_variety_drum_rack.py` — kit definitions stay
single-source) but every pad is a nested Instrument Rack with TWO Samplers:
Close mic and Room ("Full") mic, crossfaded by the chain selector (selector 0 =
pure Close, 127 = pure Room; the Close chain's selector zone fades out across
0-126, Room's fades in across 1-127). The selector chains up to the Drum
Rack's Macro 7 "Room", so one knob mixes every pad at once. Donor:
`templates/close_room_drum_rack_template.adg`, hand-built by the user
(2026-07-17), 32 pads at ReceivingNote 61-92, SendingNote 60. Chains are
identified by their `BranchSelectorRange` crossfade values, never by order.
Unlike the single-mic donor this one ships with real samples on all pads, so
kits under 32 instruments get surplus pads cleared (SampleParts emptied, name
blanked) — never left sounding the donor's Alfaias. Both mic folders share
identical velocity centers library-wide (verified across all 732 instruments),
so the two chains always switch layers at the same velocities; the takes
themselves are independent autosampling passes (different RR ids), so a blend
is two performances, not two mics of one hit. Output: one combined set in
`.../User Library/Looping Presets/Instruments/Ableton/Perc/Damage Close-Room`.

## Round-Robin Drum Racks (no velocity/note metadata)

**Purpose:** build round-robin Drum Racks from "found sound" one-shot libraries
whose filenames carry **no note and no velocity** — only numbered round-robin
takes (e.g. Soundiron Rust 1). This is the sibling of the Sampler-Based Drum
Rack Workflow above: same donor template and same "only swap each pad's
`MultiSampleMap/SampleParts` in place" rule, but there are no velocity layers
to build — each articulation becomes one pad whose takes are round-robin
alternates over the full 1-127 velocity range, fixed on `PAD_ROOT_NOTE` (60).

**Key file:** `scripts/create_rust_round_robin_racks.py`. `articulation_key()`
reduces a filename stem to its articulation by stripping the trailing take
suffix — an optional `_L`/`_R` channel marker (only Soundiron's Dumpster
`Dmst_*` files use it; their `_L`/`_R` files are full stereo takes, kept as
extra round robins, not split) followed by a `_<number>` take index. Samples
sharing the result become one pad. Every articulation across the library is
laid out in object order (objects alphabetical, articulations alphabetical
within each) and packed into sequential full 32-pad racks
(`Rust Round Robin NN.adg`), so each object's hits stay adjacent and no pads are
wasted except at the tail of the last rack; `build_rack` prints each rack's
object composition. Single-take pads are kept (valid one-shots) and their count
reported per rack — nothing dropped silently. Each run calls `clean_previous()`
to delete prior `Rust *.adg` output first, so re-runs leave a clean set.
`SAMPLE_LIBRARY_ROOT` is set at the top of the file; **update it if the source
library moves.**

On top of the donor's defaults, `apply_sampler_params()` sets a small
hand-tuned mapping (`SAMPLER_PARAMS`) on every pad's Sampler — lowpass cutoff
~3.34 kHz with velocity→cutoff, and velocity→volume — so harder hits open up
and get louder. These were dialed in by hand in Ableton on an example rack and
transcribed as verbatim values; edit `SAMPLER_PARAMS` to retune. The shared
donor template is left untouched, so the Damage workflow is unaffected.

**Output:** same as above — `SAMPLE_LIBRARY_ROOT / "Drum Racks"`, outside the repo.

## SonicCouture Electro-Acoustic DrumCell Racks

**Purpose:** category-pure 32-pad DrumCell racks from the SonicCouture
Electro-Acoustic one-shot export (181 kit folders of 12 single-velocity
samples each, under `/Users/Shared/Music/Soundbanks/Ben Multisamples/
Soniccouture/Electro Acoustic/{Dry, Electro Acoustic, Hybrid, Distorted}`).

**Key file:** `scripts/create_electro_acoustic_racks.py` (`--plan` to preview).
Kits parse to (machine, treatment) with export-typo normalization; each rack
pairs two same-treatment kits ("EMI Crush - 606 + 808"), odd leftovers pool
per category. Kit A fills notes 92..81, kit B 76..65 (same type→note offsets
everywhere, so B-half clips transpose to A-halves by exactly 16); spare donor
pads are deleted. Output subfolders mirror SonicCouture's snapshot numbering
(`1 Dry Machines` … `4 Overdrive`) under the User Library
`.../Drum/Prod/Electro Acoustic/`.

**Donor:** `templates/electro_acoustic_drumcell_donor.adg` (copy of the old
"606 808 EMI Crush" rack; same only-swap-sample-content rule as the other
donor workflows). `beat_tools_to_drumcell.py` uses the same donor.

**Known source glitches** (skipped with warnings, don't "fix" in the script):
`Korg 55B PA Mic` folder is empty; `Korg 55B FatFace` 09-12 are zero-frame
4KB shells; `Drumulator Dry` was never exported; ~37 filenames have mangled
random-code suffixes (leading `<idx>-<Type>-V127-` fields are still valid).
Re-exporting those from Kontakt would allow a rebuild to pick them up.

**Pad placement:** `build_rack()` places each sample by its **slot number**
(slot N → note 93−N in the top bank), not by its position in the scanned list.
The two are identical for the four original categories — no kit there has a
slot gap — but Boroughs drops middle slots, where positional fill would slide
every later sound up a semitone onto the wrong pad. Keep it slot-indexed.

## SonicCouture Boroughs DrumCell Racks

**Purpose:** one rack per borough from the fifth snapshot category (100 kit
folders under `.../Soniccouture/Electro Acoustic/Boroughs`, exported
2026-07-18, WAV rather than AIFF). Unlike the (machine × treatment) grids of
the other four categories, each borough is a self-contained named kit, so
there is nothing to pair on — one borough, one rack, named for its snapshot.

**Key file:** `scripts/create_boroughs_racks.py` (`--plan` to preview); reuses
the donor, `scan_kit()` and `build_rack()` from `create_electro_acoustic_racks`.
Each kit fills the top bank only — 01-Kick at note 92 through 12-Cowbell at 81
— and every unused pad is deleted. Placement is by slot, so the note→drum-type
map is identical across all 100 racks and a clip written for one borough
triggers the same types in any other. Output: `5 Boroughs` alongside the other
numbered subfolders.

**Known source glitches** (pads left empty, reported not filled): 40 of the
100 boroughs are missing a middle slot — 35 lack `08-Tom-Alt`, 3 lack
`07-HiHat-Open`, and `Hexagon Projection` / `In Another Space` lack both
`06-Tom-Hi` and `08-Tom-Alt`. Re-exporting those from Kontakt and re-running
would fill the holes. The other never-exported category is `Focus Tuned`.

## Chamber Strings Long Sampler Patches

**Purpose:** flat single-Sampler `.adv` building blocks for the Spitfire
Chamber Strings sustained articulations — no racks, no macros, no chains, to be
assembled into a master rack by hand.

**Key file:** `scripts/create_chamber_strings_long_samplers.py`
(`--test` writes two verification patches, `--flat` / `--combined` one set).
Reuses `read_long_folder` and `discover_articulations` from
`create_chamber_strings_long_racks.py` (the rack approach, set aside) and
`MultisampleRackCreator` / `Zone` from `sampler/multisample.py`. Donor is
`templates/oae_evo_sampler_template.adv`, a bare Sampler with no zones.

**Two sets, both written outside the repo** under
`.../Chamber Strings/Sampler Instruments/`:
- `Long/` — 84 patches, one articulation x mic x dynamic layer, 5556 zones,
  every source file mapped exactly once.
- `Long Close-Far/` — 42 patches, both mics in one Sampler crossfaded on the
  Sample Selector, 5334 zones.

Ranges are fully chromatic, so every key zone is one key wide on its own root
with no stretching. Velocity is full 1-127 everywhere; the dynamics are
separate patches, never on velocity. Layer order dyn1..dyn6 =
cc001/026/051/076/102/127, confirmed by measured RMS rising monotonically
across all six on four different articulations (2026-09-09).

**Both mics in one Sampler works only because this library has no round
robins.** The Close zones span the whole selector range and are full at 0,
fading to silence at 127; the Far zones mirror them; both overlap on every
note, so Live layers them and the selector mixes. With `RoundRobin` on, Live
pools every overlapping zone and alternates instead — one mic per note, no
blend. That is what ruled the selector out for the short articulations. Here
there is one take per note per layer per mic, so the flag stays `false`.
Confirmed in Live 12 (2026-09-09): the sweep blends smoothly, it does not
switch.

**Close and Far are not two mics of one take.** Measured coherence between them
is 0.04-0.12 in every band and note onsets differ by up to half a second
(Flautando A#3: Close 151 ms, Far 644 ms). They are independent renders, so a
mid-selector blend doubles two performances rather than moving a mic — the same
situation as the Damage Close-Room racks. Usable, but not mic positioning, and
the middle of the sweep dips about 3 dB with Far already 5-6 dB under Close.

**Live does not read a WAV's `smpl` chunk when it loads a preset** — only when
a sample is dragged into the UI. These are 24 s sustains that must loop, so
each zone's sustain loop is written into the XML from the file's own chunk
(`Zone(loop="auto")`, typically frames 176400 -> 1058399). Without it every
patch stops dead at 24 s.

**Known source defect — `Long_Harmonics_Far` is the Close render.** Notes 60-70
are byte-identical files; the rest are waveform-identical (coherence 1.000, max
difference one 24-bit LSB). The flat set still writes those 6 patches since that
is what is on disk, but they duplicate their Close counterparts; the combined
set builds Harmonics from Close alone rather than layering one recording
against itself. Re-exporting that mic from Kontakt and re-running fixes both.

### Dynamics racks (`create_chamber_strings_long_evo_racks.py`)

One Instrument Rack per articulation, holding all six dynamic layers as chains
crossfaded by the user's `Evo-Grid-Selector.amxd`. Written to
`.../User Library/Looping Presets/Instruments/Ableton/Inst/String/Long/Chamber Strings/`.

**Donor is `Long CS.adg`, hand-built by the user** (2026-09-09) from the six
combined Close/Far patches. Chain N is dynamic layer N: a Sampler plus one Evo
Grid Selector instance. Every `BranchSelectorRange` is 0-0 — the chain selector
does nothing, the Max device does the crossfading from the "Crossfade X" /
"Crossfade Y" macros. The rack carries **no `KeyMidi` mappings at all**, the
Looping convention: the surface drives parameters by macro *name*, and a
macro-held parameter is disabled in Live.

Chain N's Max device is carried across to chain N untouched, with one deliberate
exception: **`Wrap` is forced off in every chain.** The donor was first saved
with it on in chains 1/3/5 and off in 2/4/6, which was not intended.
`--fix-donor` corrects the donor in place as well, backing it up to
`/Users/Shared/Music/_backups/Chamber Strings Long racks/` first — that edit
changes exactly three characters in the file and nothing else.

**Edits are string-level**, splicing only the six `<SampleParts>` spans and the
seven `<UserName>` values. The donor is a Live-saved file with a large embedded
Max payload, and re-serialising one through ElementTree yields a file that
parses but will not load. `--verify-donor` rebuilds `Long CS` itself and checks
the result: everything outside the zone maps comes back byte-identical, and the
only zone-level difference is `Volume` written as `1.0` where Live writes `1`
(plus the slicing/warp defaults Live adds on resave, which generated patches
have never carried).

## Lite Rack Sets (2026-09-11)

211 lightweight racks built with `adc sampler thin`, one per full rack. Same
filenames, so a Lite rack is a drop-in swap. **59.8 GB less sample RAM**, zero
verification failures.

**Where they live.** The full sets were moved to
`.../Looping Presets/Instruments/xFull/` (`Abbey Road`, `A Moonkits`, `Damage`,
`Metal`, `Shaker`, `Ethnic`, `Mini Racks` - 211 racks, out of the browse path),
and the Lite sets sit in the normal tree under
`.../Instruments/Ableton/Drum/` and `.../Ableton/Perc/` as `<Library> Lite`.
The table below names each set by its original library.

**Amp attack set to 0.2 ms across all 422 racks** (2026-09-11) with
`adc sampler set-env --value 0.2 --in-place`: 10280 parameters written, 5140 in
each tree. A further 4300 are macro-held and were left alone - concentrated in
the Damage Close/Room racks (exactly half of their Samplers) and Soundiron
Shaker, where 14 presets have no writable amp attack at all. Backup of all 422
racks beforehand in `/Users/Shared/Music/_backups/Lite and Full racks before
amp attack 2026-09-11/`.

| set | racks | zones | sample RAM | layers x takes |
|---|---|---|---|---|
| `Perc/Damage Lite` | 68 | 114084 -> 63286 | 102.2 -> 61.3 GB | 8 x 3 |
| `Drum/Abbey Road Lite` | 19 | 29888 -> 13640 | 24.2 -> 10.8 GB | 8 x 3 |
| `Drum/A Moonkits Lite` | 80 | 49942 -> 33127 | 17.1 -> 11.5 GB | 8 x 3 |
| `Perc/Metal Lite` | 18 | 3521 -> 2158 | 2.2 -> 1.2 GB | 8 x 6 |
| `Perc/Shaker Lite` | 17 | 8358 -> 3256 | 1.0 -> 0.3 GB | 8 x 6 |
| `Perc/Ethnic Lite` | 2 | 2106 -> 1224 | 0.9 -> 0.5 GB | 8 x 6 |
| `Perc/Mini Racks Lite` | 7 | 9428 -> 7513 | 0.2 -> 0.1 GB | 8 x 6 |

**The take count is per-library and matters.** Damage, Abbey Road and Moonkits
record 2-6 takes per layer, so 3 is a mild trim. The Soundiron libraries
(Shaker, Metal, Ethnic, Mini Racks) record **10-47** takes per layer with few or
no velocity layers - round robin *is* their realism, and 3 takes machine-guns on
a roll. Those were built at 6.

**Racks deliberately left out.** `Drum/Ableton`, `Inst/Guitar`, `Key/Mallets`
and most of `Perc/Latin` reference one big *combined* sample file per
instrument, with many zones pointing into regions of it (Ableton's own Pack
format). Thinning those cuts zones but frees essentially no RAM - `Drum/Ableton`
is 25182 zones for 0.34 GB - so it is all risk and no reward. Check
`unique sample files ~= zone count` before adding a library to the list.

## Auto-Select on across the Ableton tree (2026-09-11)

`adc drum-rack auto-select --in-place` over
`.../Looping Presets/Instruments/Ableton`: 2788 root Drum Racks now have
Auto-Select on, so playing a pad selects it in the rack view. Only **38 needed
it** - 2750 were already on, and the 38 were a coherent set: Ableton's own
`Drum/Packs/Designer Drums` (16), `Perc/Latin` (19) and three `Perc/Shaker Lite`
racks. 406 Instrument Rack presets skipped, zero verification failures. The
11896 nested `IsAutoSelectEnabled` fields in those files - nested racks and pad
Samplers - were left at `false`. Backup of the 38 in
`/Users/Shared/Music/_backups/Ableton kits before auto-select 2026-09-11/`.

## Drum-Rack Chain Colors

**Purpose:** colour a Drum Rack's pad chains by drum type, so a kit reads at a
glance — kicks one colour, snares another, hats split open/closed.

**Key file:** `scripts/color_drum_rack_chains.py` (`--plan` to preview,
`--apply` to write, `--only-uncoded` to restrict to racks that carry no colour
information yet). `classify_sample()` maps a pad's sample path to a drum type by
filename keywords; `COLORS` maps type → Live palette index.

**Two fields per pad chain, both direct children of `DrumBranchPreset`:**
- `DocumentColorIndex` — the colour.
- `AutoColored` — **must be `false` or Live ignores the stored index entirely**
  and picks its own colour. This is the whole reason a rack can look uniformly
  coloured no matter what the file says: writing `DocumentColorIndex` alone
  changes nothing visible. Live clears the flag itself when you assign a chain
  colour by hand. (Measured 2026-09-08: the 25 Acoustic/Ableton kits that looked
  mono-coloured were exactly the 426 pads with `AutoColored=true`; every other
  kit in the folder already had it `false`.)

Nested `InstrumentBranchPreset` / `AudioEffectBranchPreset` chains inside a pad
are left alone — only the drum pad's own chain is touched. Edits are
string-level on the decoded XML, addressing the n-th textual occurrence of each
tag and checking its old value before replacing (ElementTree decides *which*
elements, never writes — a re-serialised Live 12 file parses but will not load).

**Colour scheme** — the indices Ableton's own NI Acoustic kits use, taken as the
dominant choice per drum type across all 515 racks under `Drum/Prod/NI Acoustic`:
kick 54, snare/rim/clap 4, tom 19, closed hat 29, open hat 30, cymbal 69,
shaker 26, percussion 13, tonal/other 0.

## Templates

**Location:** `templates/`

**Required templates:**
- `input_rack.adg` - Drum rack template (32 pads, no samples, DrumCell per pad)
- `sampler-rack.adg` - Multi-Sampler template (no samples)
- `simpler-template.adv` - Simpler template (no sample)
- `sampler_drum_rack_template.adg` - Donor for the Sampler-based Drum Rack
  workflow above (32 pads, each with an empty Multi-Sampler already loaded
  and configured). Hand-built in Ableton Live, not generated — see above.
- `close_room_drum_rack_template.adg` - Donor for the Close/Room combined
  Damage workflow (32 pads, each a nested 2-chain Instrument Rack with
  Close/Room Samplers crossfaded by chain selector). Hand-built in Ableton
  Live — see above.

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
