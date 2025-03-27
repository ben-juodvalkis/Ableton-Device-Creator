# Input Rack Documentation

## Overview
The input rack is a Drum Rack device that serves as the main interface for triggering samples. It contains 32 pads, each mapped to specific MIDI notes.

## Pitch Mapping

### Original Mapping (Before Shift)
- Pads 1-32: MIDI notes 64-95
- Each pad was triggered by a note 64 semitones higher than its position

### New Mapping (After Shift)
- Pads 1-32: MIDI notes 48-79
- Each pad is now triggered by a note 48 semitones higher than its position
- All notes have been shifted down by 16 semitones

### Example
- Pad 1: MIDI note 48 (was 64)
- Pad 2: MIDI note 49 (was 65)
- Pad 3: MIDI note 50 (was 66)
...and so on

## Usage
1. Load the input rack into Ableton Live
2. Connect your MIDI controller or keyboard
3. Play notes 48-79 to trigger the corresponding pads
4. Each pad will play its assigned sample at the new pitch

## Notes
- The pitch shift was applied to maintain compatibility with lower MIDI note ranges
- All samples maintain their original pitch, only the trigger notes have been shifted
- The rack can be used with any MIDI controller that can output notes in the 48-79 range 