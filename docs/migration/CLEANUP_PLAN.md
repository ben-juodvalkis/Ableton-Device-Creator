# V2 to V3 Cleanup Plan

## Moving to Archive

The following directories contain V2 scripts that will be migrated to `src/` over time:

### Being Archived:
- `drum-racks/` → Already migrated to `src/ableton_device_creator/drum_racks/`
- `sampler/` → Will migrate to `src/ableton_device_creator/sampler/`
- `macro-mapping/` → Will migrate to `src/ableton_device_creator/macro_mapping/`
- `simpler/` → Will migrate to `src/ableton_device_creator/sampler/`
- `instrument-racks/` → Will migrate to `src/ableton_device_creator/instrument_racks/`
- `conversion/` → Will migrate to `src/ableton_device_creator/conversion/`
- `kontakt/` → Will evaluate for migration
- `utils/` → Already migrated to `src/ableton_device_creator/core/`
- `analysis/` → Will evaluate for migration

### Keeping:
- `src/` - NEW V3 code (library-first architecture)
- `templates/` - ADG/ADV template files
- `docs/` - Documentation
- `examples/` - Usage examples
- `output/` - Generated device files
- `archive-v1/` - V1 code archive
- `archive-v2-scripts/` - V2 code for migration reference

### Removing:
- `test_samples/` - Empty dummy files
- `test_samples_real/` - Temporary test files
- `test-output/` - Old test output

## Migration Status

- ✅ Core utilities (decoder/encoder)
- ✅ Drum rack creation (basic)
- ⏳ Drum rack modification
- ⏳ Sampler creation
- ⏳ Simpler creation
- ⏳ Macro mapping
- ⏳ Instrument racks
- ⏳ Batch processing
