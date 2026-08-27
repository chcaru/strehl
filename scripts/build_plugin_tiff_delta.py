"""Quantify the difference between two 16-bit RGB TIFF masters.

Written to a file because PowerShell has no heredoc. Reads the two strips with
tifffile if present, else falls back to a minimal baseline-TIFF reader, and
reports the fraction of differing samples plus the magnitude of the difference.
"""

import struct
import sys


def read_tiff_u16(path):
    with open(path, "rb") as fh:
        buf = fh.read()
    if buf[:2] == b"II":
        end = "<"
    elif buf[:2] == b"MM":
        end = ">"
    else:
        raise SystemExit(f"{path}: not a TIFF")
    (magic,) = struct.unpack_from(end + "H", buf, 2)
    if magic != 42:
        raise SystemExit(f"{path}: not a baseline TIFF (magic {magic})")
    (ifd,) = struct.unpack_from(end + "I", buf, 4)
    (n,) = struct.unpack_from(end + "H", buf, ifd)
    tags = {}
    for i in range(n):
        off = ifd + 2 + 12 * i
        tag, typ, cnt = struct.unpack_from(end + "HHI", buf, off)
        size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8}.get(typ, 1) * cnt
        if size <= 4:
            vals_off = off + 8
        else:
            (vals_off,) = struct.unpack_from(end + "I", buf, off + 8)
        fmt = {1: "B", 2: "c", 3: "H", 4: "I"}.get(typ)
        if fmt:
            tags[tag] = struct.unpack_from(end + fmt * cnt, buf, vals_off)
    width = tags[256][0]
    height = tags[257][0]
    bits = tags[258]
    spp = tags[277][0]
    if set(bits) != {16}:
        raise SystemExit(f"{path}: expected 16 bits/sample, got {bits}")
    offsets = tags[273]
    counts = tags[279]
    data = bytearray()
    for o, c in zip(offsets, counts):
        data += buf[o : o + c]
    total = width * height * spp
    arr = struct.unpack(end + "H" * total, bytes(data[: total * 2]))
    return width, height, spp, arr


def main():
    a_path, b_path = sys.argv[1], sys.argv[2]
    wa, ha, sa, a = read_tiff_u16(a_path)
    wb, hb, sb, b = read_tiff_u16(b_path)
    if (wa, ha, sa) != (wb, hb, sb):
        raise SystemExit(f"geometry differs: {wa}x{ha}x{sa} vs {wb}x{hb}x{sb}")
    n = len(a)
    diff = 0
    worst = 0
    total_abs = 0
    for x, y in zip(a, b):
        d = x - y
        if d:
            diff += 1
            d = -d if d < 0 else d
            total_abs += d
            if d > worst:
                worst = d
    print(f"geometry        : {wa} x {ha} x {sa} samples/px, {n} samples")
    print(f"differing       : {diff} samples ({100.0 * diff / n:.4f}%)")
    print(f"worst |delta|   : {worst} DN of 65535")
    print(f"mean |delta|    : {total_abs / n:.4f} DN over all samples")
    if diff:
        print(f"mean |delta|    : {total_abs / diff:.4f} DN over differing samples")


main()
