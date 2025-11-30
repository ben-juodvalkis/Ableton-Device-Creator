# API Documentation

Complete Python API reference for Ableton Device Creator V3.0

## Core Modules

### [Core](core.md)
Low-level ADG/ADV file manipulation.

- `decode_adg()` - Decompress ADG/ADV to XML
- `encode_adg()` - Compress XML to ADG/ADV
- `decode_adv()` - Alias for decode_adg
- `encode_adv()` - Alias for encode_adg

### [Drum Racks](drum_racks.md)
Drum rack creation and modification.

- `DrumRackCreator` - Create drum racks from samples
- `DrumRackModifier` - Modify existing drum racks
- `categorize_samples()` - Auto-categorize samples by type
- `detect_velocity_layers()` - Detect multi-velocity samples

### [Sampler](sampler.md)
Multi-Sampler and Simpler device creation.

- `SamplerCreator` - Create Multi-Sampler instruments
- `SimplerCreator` - Create Simpler devices

### [Macro Mapping](macro_mapping.md)
Macro mapping and device modification.

- `DrumPadColorMapper` - Apply color coding to drum pads
- `TransposeMapper` - Add transpose controls
- `DRUM_COLORS` - Color scheme constants

## Quick Reference

### Import Paths

```python
# Core utilities
from ableton_device_creator.core import decode_adg, encode_adg

# Drum racks
from ableton_device_creator.drum_racks import DrumRackCreator, DrumRackModifier

# Sampler
from ableton_device_creator.sampler import SamplerCreator, SimplerCreator

# Macro mapping
from ableton_device_creator.macro_mapping import DrumPadColorMapper, TransposeMapper
```

### Common Patterns

#### Create and Modify Device

```python
from ableton_device_creator.drum_racks import DrumRackCreator
from ableton_device_creator.macro_mapping import DrumPadColorMapper

# Create
creator = DrumRackCreator("templates/input_rack.adg")
rack = creator.from_folder("samples/", output="MyKit.adg")

# Color
colorizer = DrumPadColorMapper("MyKit.adg")
colorizer.apply_colors().save("MyKit_Colored.adg")
```

#### Decode and Encode

```python
from ableton_device_creator.core import decode_adg, encode_adg

# Decode to XML
xml = decode_adg("MyRack.adg")

# Modify XML...

# Encode back
encode_adg(modified_xml, "MyRack_Modified.adg")
```

## See Also

- [CLI Guide](../CLI_GUIDE.md) - Command-line interface
- [Examples](../../examples/) - Usage examples
- [Main README](../../README.md) - Project overview
