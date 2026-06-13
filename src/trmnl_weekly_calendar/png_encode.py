from __future__ import annotations

import struct
import zlib
from typing import Literal

from PIL import Image


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def quantize_grayscale_4bit(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda p: round(p / 17) * 17)


def png_chunk(kind: Literal[b"IHDR", b"IDAT", b"IEND"], data: bytes = b"") -> bytes:
    crc = zlib.crc32(kind)
    crc = zlib.crc32(data, crc)
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc & 0xFFFFFFFF)


def encode_png_grayscale_4bit(image: Image.Image) -> bytes:
    samples = image.convert("L").point(lambda p: round(p / 17))
    width, height = samples.size
    sample_data = samples.tobytes()
    packed_rows = bytearray()

    for y in range(height):
        row = sample_data[y * width : (y + 1) * width]
        packed_rows.append(0)  # PNG filter type: none.
        for x in range(0, width, 2):
            high = row[x] & 0x0F
            low = row[x + 1] & 0x0F if x + 1 < width else 0
            packed_rows.append((high << 4) | low)

    ihdr = struct.pack(
        ">IIBBBBB",
        width,
        height,
        4,  # bit depth
        0,  # color type: grayscale
        0,  # compression method
        0,  # filter method
        0,  # interlace method
    )
    compressed = zlib.compress(bytes(packed_rows), level=9)
    return PNG_SIGNATURE + png_chunk(b"IHDR", ihdr) + png_chunk(b"IDAT", compressed) + png_chunk(b"IEND")
