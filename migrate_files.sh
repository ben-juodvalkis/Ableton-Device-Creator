#!/bin/bash

# Migration script for Ableton Device Creator V2.0
# Source: /Users/Shared/DevWork/GitHub/Looping/scripts/device-creation/python
# Destination: /Users/Shared/DevWork/GitHub/Ableton Device Creator

SOURCE_BASE="/Users/Shared/DevWork/GitHub/Looping/scripts/device-creation/python"
DEST_BASE="/Users/Shared/DevWork/GitHub/Ableton Device Creator"

echo "Starting file migration..."

# Function to copy and report
copy_file() {
    local src="$1"
    local dest="$2"
    if [ -f "$src" ]; then
        cp "$src" "$dest"
        echo "✓ Copied: $(basename "$src")"
    else
        echo "✗ Missing: $src"
    fi
}

# Drum Rack Creation Scripts
echo ""
echo "=== Migrating Drum Rack Creation Scripts ==="
copy_file "$SOURCE_BASE/drum_rack/main.py" "$DEST_BASE/drum-racks/creation/main.py"
copy_file "$SOURCE_BASE/drum_rack/main_percussion.py" "$DEST_BASE/drum-racks/creation/main_percussion.py"
copy_file "$SOURCE_BASE/drum_rack/main_simple_folder.py" "$DEST_BASE/drum-racks/creation/main_simple_folder.py"
copy_file "$SOURCE_BASE/drum_rack/main_by_note_name.py" "$DEST_BASE/drum-racks/creation/main_by_note_name.py"
copy_file "$SOURCE_BASE/drum_rack/create_dual_folder_drum_rack.py" "$DEST_BASE/drum-racks/creation/create_dual_folder_drum_rack.py"
copy_file "$SOURCE_BASE/drum_rack/create_dual_folder_drum_rack_v2.py" "$DEST_BASE/drum-racks/creation/create_dual_folder_drum_rack_v2.py"
copy_file "$SOURCE_BASE/drum_rack/create_triple_folder_electro_acoustic_rack.py" "$DEST_BASE/drum-racks/creation/create_triple_folder_electro_acoustic_rack.py"
copy_file "$SOURCE_BASE/drum_rack/create_multivelocity_drum_rack.py" "$DEST_BASE/drum-racks/creation/create_multivelocity_drum_rack.py"
copy_file "$SOURCE_BASE/drum_rack/create_multivelocity_drum_rack_v2.py" "$DEST_BASE/drum-racks/creation/create_multivelocity_drum_rack_v2.py"
copy_file "$SOURCE_BASE/drum_rack/create_from_template.py" "$DEST_BASE/drum-racks/creation/create_from_template.py"

# Drum Rack Batch Processing
echo ""
echo "=== Migrating Drum Rack Batch Scripts ==="
copy_file "$SOURCE_BASE/drum_rack/batch_battery_kits.py" "$DEST_BASE/drum-racks/batch/batch_battery_kits.py"
copy_file "$SOURCE_BASE/drum_rack/batch_battery_kits_organized.py" "$DEST_BASE/drum-racks/batch/batch_battery_kits_organized.py"
copy_file "$SOURCE_BASE/drum_rack/batch_process_all_expansions.py" "$DEST_BASE/drum-racks/batch/batch_process_all_expansions.py"
copy_file "$SOURCE_BASE/drum_rack/batch_process_dual_racks.py" "$DEST_BASE/drum-racks/batch/batch_process_dual_racks.py"
copy_file "$SOURCE_BASE/drum_rack/batch_remap_drum_racks.py" "$DEST_BASE/drum-racks/batch/batch_remap_drum_racks.py"
copy_file "$SOURCE_BASE/drum_rack/batch_trim_to_16.py" "$DEST_BASE/drum-racks/batch/batch_trim_to_16.py"
copy_file "$SOURCE_BASE/drum_rack/batch_wrap_pairs.py" "$DEST_BASE/drum-racks/batch/batch_wrap_pairs.py"
copy_file "$SOURCE_BASE/drum_rack/batch_shift_second_chain.py" "$DEST_BASE/drum-racks/batch/batch_shift_second_chain.py"

# Drum Rack Modification
echo ""
echo "=== Migrating Drum Rack Modification Scripts ==="
copy_file "$SOURCE_BASE/drum_rack/remap_drum_rack_notes.py" "$DEST_BASE/drum-racks/modification/remap_drum_rack_notes.py"
copy_file "$SOURCE_BASE/drum_rack/trim_drum_racks_to_16.py" "$DEST_BASE/drum-racks/modification/trim_drum_racks_to_16.py"
copy_file "$SOURCE_BASE/drum_rack/replace_foreign_samples.py" "$DEST_BASE/drum-racks/modification/replace_foreign_samples.py"
copy_file "$SOURCE_BASE/drum_rack/merge_drum_racks.py" "$DEST_BASE/drum-racks/modification/merge_drum_racks.py"
copy_file "$SOURCE_BASE/drum_rack/expand_instrument_racks.py" "$DEST_BASE/drum-racks/modification/expand_instrument_racks.py"
copy_file "$SOURCE_BASE/drum_rack/shift_second_chain_midi.py" "$DEST_BASE/drum-racks/modification/shift_second_chain_midi.py"
copy_file "$SOURCE_BASE/drum_rack/disable_auto_color.py" "$DEST_BASE/drum-racks/modification/disable_auto_color.py"

# Macro Mapping - CC Control
echo ""
echo "=== Migrating Macro Mapping CC Control Scripts ==="
copy_file "$SOURCE_BASE/add_cc_control_to_drum_rack.py" "$DEST_BASE/macro-mapping/cc-control/add_cc_control_to_drum_rack.py"
copy_file "$SOURCE_BASE/add_cc_control_to_drum_rack_v2.py" "$DEST_BASE/macro-mapping/cc-control/add_cc_control_to_drum_rack_v2.py"
copy_file "$SOURCE_BASE/add_cc_control_string_based.py" "$DEST_BASE/macro-mapping/cc-control/add_cc_control_string_based.py"
copy_file "$SOURCE_BASE/drum_rack/apply_cc_mappings_preserve_values.py" "$DEST_BASE/macro-mapping/cc-control/apply_cc_mappings_preserve_values.py"
copy_file "$SOURCE_BASE/drum_rack/apply_drumcell_cc_mappings.py" "$DEST_BASE/macro-mapping/cc-control/apply_drumcell_cc_mappings.py"
copy_file "$SOURCE_BASE/drum_rack/apply_drumcell_cc_mappings_with_macros.py" "$DEST_BASE/macro-mapping/cc-control/apply_drumcell_cc_mappings_with_macros.py"
copy_file "$SOURCE_BASE/drum_rack/batch_apply_cc_mappings.py" "$DEST_BASE/macro-mapping/cc-control/batch_apply_cc_mappings.py"
copy_file "$SOURCE_BASE/drum_rack/generate_cc_preset_map.py" "$DEST_BASE/macro-mapping/cc-control/generate_cc_preset_map.py"
copy_file "$SOURCE_BASE/configure_drum_rack_macros.py" "$DEST_BASE/macro-mapping/cc-control/configure_drum_rack_macros.py"
copy_file "$SOURCE_BASE/rename_drum_rack_macros.py" "$DEST_BASE/macro-mapping/cc-control/rename_drum_rack_macros.py"

# Macro Mapping - Transpose
echo ""
echo "=== Migrating Macro Mapping Transpose Scripts ==="
copy_file "$SOURCE_BASE/drum_rack/batch_add_transpose_mapping.py" "$DEST_BASE/macro-mapping/transpose/batch_add_transpose_mapping.py"
copy_file "$SOURCE_BASE/drum_rack/update_transpose_range.py" "$DEST_BASE/macro-mapping/transpose/update_transpose_range.py"

# Macro Mapping - Color Coding
echo ""
echo "=== Migrating Macro Mapping Color Scripts ==="
copy_file "$SOURCE_BASE/drum_rack/apply_color_coding.py" "$DEST_BASE/macro-mapping/color-coding/apply_color_coding.py"
copy_file "$SOURCE_BASE/drum_rack/apply_drum_rack_colors.py" "$DEST_BASE/macro-mapping/color-coding/apply_drum_rack_colors.py"
copy_file "$SOURCE_BASE/drum_rack/batch_apply_colors.py" "$DEST_BASE/macro-mapping/color-coding/batch_apply_colors.py"

# Macro Mapping - General
echo ""
echo "=== Migrating General Macro Mapping Scripts ==="
copy_file "$SOURCE_BASE/step1_remove_macro_mapping.py" "$DEST_BASE/macro-mapping/step1_remove_macro_mapping.py"
copy_file "$SOURCE_BASE/step1_remove_macro_mapping_v2.py" "$DEST_BASE/macro-mapping/step1_remove_macro_mapping_v2.py"
copy_file "$SOURCE_BASE/step2_add_cc_control.py" "$DEST_BASE/macro-mapping/step2_add_cc_control.py"
copy_file "$SOURCE_BASE/step3_add_macro_mapping.py" "$DEST_BASE/macro-mapping/step3_add_macro_mapping.py"
copy_file "$SOURCE_BASE/step4_set_macro_value.py" "$DEST_BASE/macro-mapping/step4_set_macro_value.py"
copy_file "$SOURCE_BASE/drum_rack/batch_set_macro_value.py" "$DEST_BASE/macro-mapping/batch_set_macro_value.py"
copy_file "$SOURCE_BASE/rename_macro_16_custom_e.py" "$DEST_BASE/macro-mapping/rename_macro_16_custom_e.py"
copy_file "$SOURCE_BASE/drum_rack/apply_template_mappings.py" "$DEST_BASE/macro-mapping/apply_template_mappings.py"

# Instrument Rack Wrapping
echo ""
echo "=== Migrating Instrument Rack Wrapping Scripts ==="
copy_file "$SOURCE_BASE/drum_rack/wrap_device_in_rack.py" "$DEST_BASE/instrument-racks/wrapping/wrap_device_in_rack.py"
copy_file "$SOURCE_BASE/drum_rack/wrap_device_in_rack_template.py" "$DEST_BASE/instrument-racks/wrapping/wrap_device_in_rack_template.py"
copy_file "$SOURCE_BASE/drum_rack/wrap_two_devices_in_rack.py" "$DEST_BASE/instrument-racks/wrapping/wrap_two_devices_in_rack.py"
copy_file "$SOURCE_BASE/drum_rack/wrap_drum_racks_in_instrument_rack.py" "$DEST_BASE/instrument-racks/wrapping/wrap_drum_racks_in_instrument_rack.py"

# Instrument Rack Multi-Device
echo ""
echo "=== Migrating Multi-Device Instrument Rack Scripts ==="
copy_file "$SOURCE_BASE/batch_aupreset_wrapper.py" "$DEST_BASE/instrument-racks/multi-device/batch_aupreset_wrapper.py"
copy_file "$SOURCE_BASE/round_robin_creator.py" "$DEST_BASE/instrument-racks/multi-device/round_robin_creator.py"
copy_file "$SOURCE_BASE/batch_round_robin_8dio.py" "$DEST_BASE/instrument-racks/multi-device/batch_round_robin_8dio.py"

# Conversion Tools
echo ""
echo "=== Migrating Conversion Scripts ==="
copy_file "$SOURCE_BASE/conversion/simpler_to_drumcell.py" "$DEST_BASE/conversion/simpler-to-drumcell/simpler_to_drumcell.py"
copy_file "$SOURCE_BASE/conversion/drum_rack_simpler_to_drumcell.py" "$DEST_BASE/conversion/simpler-to-drumcell/drum_rack_simpler_to_drumcell.py"
copy_file "$SOURCE_BASE/conversion/batch_convert_drum_racks.py" "$DEST_BASE/conversion/simpler-to-drumcell/batch_convert_drum_racks.py"
copy_file "$SOURCE_BASE/device/conversion/adg_converter.py" "$DEST_BASE/conversion/adg-converter/adg_converter.py"
copy_file "$SOURCE_BASE/device/conversion/apply_macro_mappings.py" "$DEST_BASE/conversion/adg-converter/apply_macro_mappings.py"
copy_file "$SOURCE_BASE/device/conversion/map_macros_with_values.py" "$DEST_BASE/conversion/adg-converter/map_macros_with_values.py"
copy_file "$SOURCE_BASE/device/conversion/set_macro_values.py" "$DEST_BASE/conversion/adg-converter/set_macro_values.py"
copy_file "$SOURCE_BASE/device/conversion/add_parameter_visibility.py" "$DEST_BASE/conversion/adg-converter/add_parameter_visibility.py"
copy_file "$SOURCE_BASE/device/conversion/scan_adg_files.py" "$DEST_BASE/conversion/adg-converter/scan_adg_files.py"

# Sampler Scripts
echo ""
echo "=== Migrating Sampler Scripts ==="
copy_file "$SOURCE_BASE/device/sampler/main_sampler.py" "$DEST_BASE/sampler/chromatic-mapping/main_sampler.py"
copy_file "$SOURCE_BASE/device/sampler/main_drumstyle_sampler.py" "$DEST_BASE/sampler/chromatic-mapping/main_drumstyle_sampler.py"
copy_file "$SOURCE_BASE/device/sampler/main_percussion_sampler.py" "$DEST_BASE/sampler/chromatic-mapping/main_percussion_sampler.py"
copy_file "$SOURCE_BASE/device/sampler/main_phrases_sampler.py" "$DEST_BASE/sampler/chromatic-mapping/main_phrases_sampler.py"
copy_file "$SOURCE_BASE/device/sampler/auto_sampled_drum_racks.py" "$DEST_BASE/sampler/chromatic-mapping/auto_sampled_drum_racks.py"

# Simpler Scripts
echo ""
echo "=== Migrating Simpler Scripts ==="
copy_file "$SOURCE_BASE/device/simpler/main_simpler.py" "$DEST_BASE/simpler/main_simpler.py"

# Core Utilities
echo ""
echo "=== Migrating Core Utilities ==="
copy_file "$SOURCE_BASE/device/utils/decoder.py" "$DEST_BASE/utils/decoder.py"
copy_file "$SOURCE_BASE/device/utils/encoder.py" "$DEST_BASE/utils/encoder.py"
copy_file "$SOURCE_BASE/device/utils/transformer.py" "$DEST_BASE/utils/transformer.py"
copy_file "$SOURCE_BASE/device/utils/simpler_transformer.py" "$DEST_BASE/utils/simpler_transformer.py"
copy_file "$SOURCE_BASE/device/utils/pitch_shifter.py" "$DEST_BASE/utils/pitch_shifter.py"
copy_file "$SOURCE_BASE/device/utils/scroll_position.py" "$DEST_BASE/utils/scroll_position.py"
copy_file "$SOURCE_BASE/device/utils/set_macro.py" "$DEST_BASE/utils/set_macro.py"
copy_file "$SOURCE_BASE/device/utils/batch_pitch_shift.py" "$DEST_BASE/utils/batch_pitch_shift.py"
copy_file "$SOURCE_BASE/device/utils/batch_scroll_position.py" "$DEST_BASE/utils/batch_scroll_position.py"
copy_file "$SOURCE_BASE/device/utils/__init__.py" "$DEST_BASE/utils/__init__.py"

# Meta Scripts
echo ""
echo "=== Migrating Meta Batch Processors ==="
copy_file "$SOURCE_BASE/meta/main.py" "$DEST_BASE/drum-racks/batch/meta_main.py"
copy_file "$SOURCE_BASE/meta/main_folders.py" "$DEST_BASE/drum-racks/batch/meta_main_folders.py"
copy_file "$SOURCE_BASE/meta/main_percussion.py" "$DEST_BASE/drum-racks/batch/meta_main_percussion.py"

echo ""
echo "Migration complete!"
echo "Files copied to: $DEST_BASE"
