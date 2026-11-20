"""S7 check (no engine): the quantised copy's journal and receipts carry each file's own
SHA-256 and size, every bound file is present, and outside the CFA strip a copy is
byte-identical to its original.

  python s7-check.py OUT_DIR [RUN]
"""
import hashlib
import json
import pathlib
import sys

import numpy as np

import common as c
import quant

out = pathlib.Path(sys.argv[1])
run = sys.argv[2] if len(sys.argv) > 2 else c.SCARAB
bound = {}
planes = set()
for line in open(out / 'events.jsonl', encoding='utf-8'):
    e = json.loads(line)
    files = (e.get('data', {}).get('response') or {}).get('files') if isinstance(e.get('data'), dict) else None
    for f in files or []:
        bound[f['name']] = (f['sha256'], f['bytes'], f['plane'], f['member_index'])
        planes.add(f['plane'])
rc = {}
for line in open(out / 'transfer-receipts.jsonl', encoding='utf-8'):
    r = json.loads(line)
    if r['logical_name'].startswith('frame-'):
        rc[r['logical_name']] = r['sha256']
present = sorted(p.name for p in out.glob('frame-*.ARW'))
print('bound files %d in %d planes; receipts for %d; present %d' % (len(bound), len(planes), len(rc), len(present)))
assert set(present) == set(bound) == set(rc)
for name in present:
    data = (out / name).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    assert sha == bound[name][0] == rc[name] and len(data) == bound[name][1], name
print('every file matches its journal and receipt SHA-256 and size')
code, rec, width = quant.tables(1.0)
for frame in (1, 50):
    a = np.fromfile(c.restore(run, frame), dtype=np.uint8)
    b = np.fromfile(out / ('frame-%06d.ARW' % frame), dtype=np.uint8)
    lay = c.layout(bytes(a[:1 << 20]))
    lo, hi = lay['offset'], lay['offset'] + lay['bytes']
    same = np.array_equal(a[:lo], b[:lo]) and np.array_equal(a[hi:], b[hi:])
    sa = a[lo:hi].view('<u2')
    sb = b[lo:hi].view('<u2')
    d = sb.astype(np.int32) - sa
    exact = np.array_equal(sb, rec[code[sa]])
    print('frame %d: bytes outside the strip identical %s; strip is the k = 1 table of the original %s; error min %d max %d mean %+.4f DN rms %.3f DN; clipped samples kept %s'
          % (frame, same, exact, d.min(), d.max(), d.mean(), float(np.sqrt((d.astype(np.float64) ** 2).mean())), bool(((sa == 16383) == (sb == 16383)).all())))
    c.drop(run, frame)
