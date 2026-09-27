"""DrumRackCreator fills pads from a folder and deletes the ones it leaves empty."""

import math
import struct
import wave
import xml.etree.ElementTree as ET

from ableton_device_creator.core import decode_adg
from ableton_device_creator.drum_racks import DrumRackCreator


def _write_wav(path):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 20))) for i in range(441)))


def test_unfilled_pads_are_deleted(tmp_path):
    samples = tmp_path / "samples"
    samples.mkdir()
    for name in ("kick_01", "snare_01", "hat_01"):
        _write_wav(samples / f"{name}.wav")

    template_root = ET.fromstring(decode_adg(DrumRackCreator().template))
    template_notes = {
        int(n.get("Value")) for n in template_root.iter("ReceivingNote")
    }

    rack = DrumRackCreator().from_folder(samples, output=tmp_path / "Kit.adg")
    root = ET.fromstring(decode_adg(rack))
    pads = root.findall(".//DrumBranchPreset")

    assert len(pads) == 3
    paths = {p.get("Value") for p in root.iter("Path") if p.get("Value", "").endswith(".wav")}
    assert paths == {str((samples / f"{n}.wav").absolute()) for n in ("kick_01", "snare_01", "hat_01")}
    # Surviving pads keep notes the template already had - nothing is renumbered.
    notes = {int(p.find(".//ZoneSettings/ReceivingNote").get("Value")) for p in pads}
    assert notes <= template_notes
