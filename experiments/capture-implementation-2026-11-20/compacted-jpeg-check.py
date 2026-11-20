"""After compaction, does every embedded-JPEG pointer in the main IFD chain still lead to a
decodable JPEG, and which is the largest?   compacted-jpeg-check.py <restored ARW> <original ARW>"""
import io
import struct
import sys

from PIL import Image


def jpegs(b):
    out = []
    ifd = struct.unpack_from('<I', b, 4)[0]
    k = 0
    while ifd and k < 8:
        n = struct.unpack_from('<H', b, ifd)[0]
        tags = {}
        for i in range(n):
            tag, ty, cnt, val = struct.unpack_from('<HHII', b, ifd + 2 + 12 * i)
            if ty == 3:
                val &= 0xffff
            tags[tag] = val
        if 0x0201 in tags and 0x0202 in tags:
            off, ln = tags[0x0201], tags[0x0202]
            try:
                im = Image.open(io.BytesIO(b[off:off + ln]))
                im.load()
                size = im.size
            except Exception as e:  # noqa: BLE001
                size = 'NOT DECODABLE: %s' % e
            out.append((k, off, ln, tags.get(0x0100), tags.get(0x0101), size))
        ifd = struct.unpack_from('<I', b, ifd + 2 + 12 * n)[0]
        k += 1
    return out


for label, path in (('restored', sys.argv[1]), ('original', sys.argv[2])):
    b = open(path, 'rb').read()
    print(label, len(b), 'bytes')
    for k, off, ln, w, h, size in jpegs(b):
        print('   IFD%d JPEG at %d, %d bytes, tags %sx%s, decodes to %s' % (k, off, ln, w, h, size))
