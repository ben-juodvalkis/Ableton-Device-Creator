"""Decoder for Native Instruments NCW (Compressed Wave) files.

Handles the plain, unencrypted NCW variant (magic 0x01A89ED6 / 0x00000131).
The layout below was derived by measuring the actual files, not from a spec:

  Header (120 bytes)
    0x00  u32   magic 0x01A89ED6 (little-endian 0xD69EA801)
    0x04  u32   magic 0x00000131
    0x08  u16   channels
    0x0A  u16   bits per sample
    0x0C  u32   sample rate
    0x10  u32   samples per channel
    0x14  u32   block-table offset (always 120)
    0x18  u32   block-data offset
    0x1C  u32   block-data size
    rest        uninitialized padding from NI's writer -- ignore it

  Block table: u32 offsets into the block data, one per block plus a final
  end-offset sentinel. Blocks cycle channel-major (block i -> channel
  i % channels).

  Block: 16-byte header (u32 magic 0x3E9A0C16, i32 base, i16 bits,
  u16 flags, u32 reserved) followed by 512 slots of `bits`-wide signed
  integers packed LSB-first. `base` IS the block's first sample; slots 0..510
  are deltas accumulated onto it, and slot 511 is always zero padding.
  Treating `base` as a pre-roll anchor instead (i.e. accumulating all 512
  slots) puts an audible discontinuity at every 512-sample boundary.

Pure stdlib.

    from ncw import read_ncw, ncw_to_wav
"""

import struct
import wave
from pathlib import Path

MAGIC = (0xD69EA801, 0x00000131)
BLOCK_MAGIC = 0x3E9A0C16
HEADER_SIZE = 120
BLOCK_SAMPLES = 512


class NcwError(Exception):
    pass


def _unpack_block(payload, bits, base):
    """Decode one block: `base` is sample 0, then 511 accumulated deltas."""
    if bits == 0:
        return [base] * BLOCK_SAMPLES
    packed = int.from_bytes(payload, "little")
    mask = (1 << bits) - 1
    sign = 1 << (bits - 1)
    out = [base]
    acc = base
    for i in range(BLOCK_SAMPLES - 1):
        v = (packed >> (i * bits)) & mask
        if v & sign:
            v -= 1 << bits
        acc += v
        out.append(acc)
    return out


def read_ncw(path):
    """Return (channels, info) where channels is a list of per-channel int lists."""
    data = Path(path).read_bytes()
    if len(data) < HEADER_SIZE:
        raise NcwError(f"{path}: too short to be an NCW file")
    m0, m1 = struct.unpack_from("<II", data, 0)
    if (m0, m1) != MAGIC:
        raise NcwError(
            f"{path}: not a plain NCW file (magic {m0:#010x} {m1:#010x}); "
            "encrypted or unknown variant"
        )
    channels, bit_depth = struct.unpack_from("<HH", data, 8)
    sample_rate, num_samples, table_off, blocks_off, blocks_size = struct.unpack_from(
        "<5I", data, 12
    )
    if channels < 1:
        raise NcwError(f"{path}: bad channel count {channels}")
    if bit_depth not in (8, 16, 24, 32):
        raise NcwError(f"{path}: unsupported bit depth {bit_depth}")

    n_entries = (blocks_off - table_off) // 4
    offsets = struct.unpack_from("<%dI" % n_entries, data, table_off)

    chans = [[] for _ in range(channels)]
    for i in range(n_entries - 1):
        if offsets[i] >= blocks_size:
            break
        off = blocks_off + offsets[i]
        magic, base, bits, flags, _reserved = struct.unpack_from("<IihHI", data, off)
        if magic != BLOCK_MAGIC:
            raise NcwError(f"{path}: bad block magic at block {i} ({magic:#010x})")
        if bits < 0:
            raise NcwError(
                f"{path}: block {i} uses the unhandled absolute mode (bits={bits}); "
                "decoder needs extending before this file can be trusted"
            )
        payload = data[off + 16:blocks_off + offsets[i + 1]]
        chans[i % channels].extend(_unpack_block(payload, bits, base))

    for c in range(channels):
        if len(chans[c]) < num_samples:
            raise NcwError(
                f"{path}: decoded {len(chans[c])} of {num_samples} samples on "
                f"channel {c}"
            )
        del chans[c][num_samples:]

    info = dict(
        channels=channels,
        bit_depth=bit_depth,
        sample_rate=sample_rate,
        num_samples=num_samples,
        duration=num_samples / sample_rate if sample_rate else 0.0,
    )
    return chans, info


def ncw_to_wav(src, dst):
    """Decode an NCW file to a 16-bit PCM WAV. Returns the info dict."""
    chans, info = read_ncw(src)
    shift = info["bit_depth"] - 16
    frames = bytearray()
    for i in range(len(chans[0])):
        for c in chans:
            v = c[i] >> shift if shift > 0 else c[i]
            if v < -32768:
                v = -32768
            elif v > 32767:
                v = 32767
            frames += struct.pack("<h", v)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(info["channels"])
        w.setsampwidth(2)
        w.setframerate(info["sample_rate"])
        w.writeframes(bytes(frames))
    return info


if __name__ == "__main__":
    import sys

    for arg in sys.argv[1:]:
        src = Path(arg)
        print(src.name, ncw_to_wav(src, src.with_suffix(".wav")))
