"""S6b: what the embedded JPEGs of an A7CR ARW are worth: dropped, or recompressed
losslessly (byte-exact restoration) with JPEG XL's JPEG transcoding or Brunsli
(libjxl BSD-3-Clause; Brunsli MIT), through imagecodecs as black boxes.
"""
import struct
import time

import imagecodecs
import numpy as np

import common as c

c.below_normal()
FRAMES = [(c.SCARAB, 1), (c.SCARAB, 401), (c.REPEAT_A, 1)]
for run, frame in FRAMES:
    b = bytes(np.memmap(c.restore(run, frame), dtype=np.uint8, mode='r'))
    lay = c.layout(b)
    total = 0
    saved = {'jxl': 0, 'brunsli': 0}
    print('== %s frame %d' % (run, frame))
    for name, at, entries in c.walk(b):
        t = c.tags(entries)
        if 0x0201 not in t or 0x0202 not in t:
            continue
        off, size = t[0x0201][3][0], t[0x0202][3][0]
        j = b[off:off + size]
        total += size
        row = ['%s JPEG %d bytes' % (name, size)]
        for label, enc, dec in (('jxl', imagecodecs.jpegxl_encode_jpeg, imagecodecs.jpegxl_decode_jpeg),
                                ('brunsli', imagecodecs.brunsli_encode, imagecodecs.brunsli_decode)):
            try:
                t0 = time.perf_counter()
                e = enc(j)
                t1 = time.perf_counter()
                d = dec(e)
                t2 = time.perf_counter()
                exact = bytes(d) == j
                saved[label] += size - len(e)
                row.append('%s %d bytes (%.1f %% smaller, byte-exact %s, encode %.2f s, decode %.2f s)' % (label, len(e), 100 * (1 - len(e) / size), exact, t1 - t0, t2 - t1))
            except Exception as ex:  # noqa: BLE001
                row.append('%s failed: %s' % (label, str(ex)[:60]))
        print('   ' + ' | '.join(row))
    print('   all embedded JPEGs %d bytes = %.2f MB; lossless recompression saves %.2f MB (JXL) / %.2f MB (Brunsli); dropping them saves %.2f MB'
          % (total, total / 1e6, saved['jxl'] / 1e6, saved['brunsli'] / 1e6, total / 1e6))
