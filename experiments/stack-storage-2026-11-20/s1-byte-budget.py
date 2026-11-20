"""S1: where the bytes of one A7CR uncompressed ARW and of its archive go.

  python s1-byte-budget.py [run frame]...

Walks the TIFF IFDs, accounts the CFA strip, every embedded JPEG (found by tag and by a
marker scan of everything outside the strip) and the rest, and compares with the archive's
size as stored (format 1) and as `strehl-raw-archive pack` writes it today (format 2).
"""
import io
import os
import subprocess
import sys

import numpy as np
from PIL import Image

import common as c

c.below_normal()
pairs = [(c.SCARAB, 1), (c.SCARAB, 400), (c.REPEAT_A, 1)]
if len(sys.argv) > 2:
    pairs = [(sys.argv[i], int(sys.argv[i + 1])) for i in range(1, len(sys.argv) - 1, 2)]


def jpeg_end(b, at):
    """End (exclusive) of the JPEG starting at `at`, by walking its markers."""
    i = at + 2
    n = len(b)
    while i + 4 <= n:
        if b[i] != 0xFF:
            return None
        m = b[i + 1]
        if m == 0xD9:
            return i + 2
        if m in (0x01,) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        seg = (b[i + 2] << 8) | b[i + 3]
        if m == 0xDA:
            j = i + 2 + seg
            while True:
                j = b.find(b'\xff', j)
                if j < 0 or j + 1 >= n:
                    return None
                if b[j + 1] == 0x00 or 0xD0 <= b[j + 1] <= 0xD7:
                    j += 2
                    continue
                break
            i = j
            continue
        i += 2 + seg
    return None


for run, frame in pairs:
    arw = c.restore(run, frame)
    b = bytes(np.memmap(arw, dtype=np.uint8, mode='r'))
    lay = c.layout(b)
    total = len(b)
    strip = (lay['offset'], lay['offset'] + lay['bytes'])
    print('== %s frame %d: ARW %d bytes' % (run, frame, total))
    print('   CFA strip: IFD %s, %d x %d, %d bits/sample container, offset %d, %d bytes (%.2f %% of file)'
          % (lay['ifd'], lay['width'], lay['height'], lay['bits'], lay['offset'], lay['bytes'], 100 * lay['bytes'] / total))
    for name, at, entries in c.walk(b):
        t = c.tags(entries)
        dims = (t.get(0x0100, [0, 0, 0, None])[3], t.get(0x0101, [0, 0, 0, None])[3])
        extra = ''
        if 0x0201 in t and 0x0202 in t:
            extra = ' JPEG by tag at %d, %d bytes' % (t[0x0201][3][0], t[0x0202][3][0])
        crop = {k: t[k][3] for k in (0xc61f, 0xc620, 0x74c7, 0x74c8) if k in t}
        print('   %-12s at %-9d %2d entries dims %s%s %s' % (name, at, len(entries), dims, extra, crop or ''))
    outside = [(0, strip[0]), (strip[1], total)]
    jpeg_bytes = 0
    for lo, hi in outside:
        at = lo
        while True:
            at = b.find(b'\xff\xd8\xff', at, hi)
            if at < 0:
                break
            end = jpeg_end(b, at)
            if end is None or end > hi:
                at += 3
                continue
            try:
                im = Image.open(io.BytesIO(b[at:end]))
                size = im.size
                sub = im.info.get('progression'), im.mode
            except Exception as e:  # noqa: BLE001
                size, sub = ('undecodable', str(e)[:40]), None
            print('   JPEG at %-9d %9d bytes  %s %s' % (at, end - at, size, sub))
            jpeg_bytes += end - at
            at = end
    rest = total - lay['bytes'] - jpeg_bytes
    zeros = sum(b[lo:hi].count(0) for lo, hi in outside)
    print('   embedded JPEGs %d bytes (%.2f %%); other metadata and padding %d bytes (of the non-strip bytes, %d are zero)'
          % (jpeg_bytes, 100 * jpeg_bytes / total, rest, zeros))
    stored = os.path.getsize(c.archive(run, frame))
    magic = open(c.archive(run, frame), 'rb').read(8).decode()
    out2 = c.SCRATCH / ('s1-%s-%06d.ARW.straw' % (run, frame))
    if out2.exists():
        out2.unlink()
    r = subprocess.run([str(c.EXE), 'pack', str(arw), str(out2)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    f2 = os.path.getsize(out2)
    magic2 = open(out2, 'rb').read(8).decode()
    out2.unlink()
    px = lay['width'] * lay['height']
    other = total - lay['bytes']
    print('   archive on disk (%s): %d bytes; packed today (%s): %d bytes' % (magic, stored, magic2, f2))
    for label, size in (('on disk', stored), ('format 2', f2)):
        print('   %-9s if non-strip bytes stored raw: CFA <= %.3f bits/px; if they cost nothing: %.3f bits/px (whole file)'
              % (label, 8 * (size - other) / px, 8 * size / px))
