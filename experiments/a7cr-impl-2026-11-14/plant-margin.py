"""Copy plain ARWs, overwriting every sample outside the declared crop with a
planted value. A stack of the copies must be byte-identical to the originals'.
Usage: plant-margin.py SRC_DIR DST_DIR VALUE"""
import struct, sys
from pathlib import Path
import numpy as np

src, dst, value = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
dst.mkdir(parents=True, exist_ok=True)
for f in sorted(src.glob('*.ARW')):
    b = bytearray(f.read_bytes())
    def ifd_tags(at):
        n = struct.unpack_from('<H', b, at)[0]
        return {struct.unpack_from('<H', b, at + 2 + 12 * i)[0]: struct.unpack_from('<HII', b, at + 4 + 12 * i)
                for i in range(n)}, struct.unpack_from('<I', b, at + 2 + 12 * n)[0]
    raw = None
    todo = [struct.unpack_from('<I', b, 4)[0]]
    while todo:
        at = todo.pop()
        if not at or at + 2 > len(b): continue
        tags, nxt = ifd_tags(at)
        todo.append(nxt)
        if 330 in tags: todo.append(tags[330][2])
        if tags.get(262, (0, 0, 0))[2] == 32803: raw = tags
    w, h, off = raw[256][2], raw[257][2], raw[273][2]
    ox, oy = struct.unpack_from('<II', b, raw[0xC61F][2])
    cw, ch = struct.unpack_from('<II', b, raw[0xC620][2])
    img = np.frombuffer(b, dtype='<u2', count=w * h, offset=off).reshape(h, w).copy()
    mask = np.ones((h, w), bool); mask[oy:oy + ch, ox:ox + cw] = False
    img[mask] = value
    b[off:off + 2 * w * h] = img.astype('<u2').tobytes()
    (dst / f.name).write_bytes(bytes(b))
    print(f.name, (w, h), (ox, oy, cw, ch), int(mask.sum()), 'planted')
