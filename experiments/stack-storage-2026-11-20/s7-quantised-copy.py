"""S7: a quantised copy of the first planes of a capture, for rendering against the original.

  python s7-quantised-copy.py K PLANES OUT_DIR [RUN]

Writes frame-000001.ARW ... (4 x PLANES files) to OUT_DIR: each is the restored original with
ONLY its CFA strip changed (every sample replaced by its quant.py reconstruction at step
K sigma; all metadata, previews and padding byte-identical), plus the run's manifest.json,
result.json and a journal and receipts cut down to those files with their SHA-256 replaced
by the modified files' own (the engine binds files by the journal's hashes). The capture
folder is only read.
"""
import hashlib
import json
import pathlib
import shutil
import sys

import numpy as np

import common as c
import quant

c.below_normal()
k = float(sys.argv[1])
planes = int(sys.argv[2])
out = pathlib.Path(sys.argv[3])
run = sys.argv[4] if len(sys.argv) > 4 else c.SCARAB
src = c.CAPTURES / run
out.mkdir(parents=True, exist_ok=True)
code, rec, width = quant.tables(k)
lut = rec[code]
shas = {}
err2 = 0.0
count = 0
for frame in range(1, 4 * planes + 1):
    name = 'frame-%06d.ARW' % frame
    dst = out / name
    arw = c.restore(run, frame)
    b = np.fromfile(arw, dtype=np.uint8)
    old = hashlib.sha256(b.tobytes()).hexdigest()
    lay = c.layout(bytes(b[:1 << 20]))
    strip = b[lay['offset']:lay['offset'] + lay['bytes']].view('<u2')
    q = lut[strip]
    d = q.astype(np.int32) - strip
    err2 += float((d.astype(np.float64) ** 2).sum())
    count += d.size
    strip[:] = q
    data = b.tobytes()
    shas[name] = (old, hashlib.sha256(data).hexdigest(), len(data))
    with open(dst, 'wb') as f:
        f.write(data)
    c.drop(run, frame)
    if frame % 8 == 0:
        print('wrote', frame, 'of', 4 * planes, flush=True)
print('rms change %.3f DN over %d samples' % ((err2 / count) ** 0.5, count))
for fixed in ('manifest.json', 'result.json'):
    if (src / fixed).exists():
        shutil.copyfile(src / fixed, out / fixed)
keep = set(shas)
lines = []
for line in open(src / 'events.jsonl', encoding='utf-8'):
    if not line.strip():
        continue
    e = json.loads(line)
    if e.get('event') in ('capture_buffered', 'capture_complete', 'capture_intent', 'focus_intent', 'focus_complete'):
        ordinal = e['data'].get('ordinal')
        if ordinal is not None and ordinal >= planes:
            continue
    files = (e.get('data', {}).get('response') or {}).get('files') if isinstance(e.get('data'), dict) else None
    if files:
        assert all(f['name'] in keep for f in files), e['data'].get('ordinal')
        for f in files:
            old, new, size = shas[f['name']]
            assert f['sha256'] == old and f['bytes'] == size, f['name']
            f['sha256'] = new
    lines.append(json.dumps(e, separators=(',', ':')))
(out / 'events.jsonl').write_bytes(('\n'.join(lines) + '\n').encode())
lines = []
for line in open(src / 'transfer-receipts.jsonl', encoding='utf-8'):
    if not line.strip():
        continue
    r = json.loads(line)
    n = r.get('logical_name', '')
    if n.startswith('frame-'):
        if n not in keep:
            continue
        old, new, size = shas[n]
        assert r['sha256'] == old, n
        r['sha256'] = new
        r['path'] = str(out / n)
        r['storage_encoding'] = 'identity'
        r['storage_bytes'] = size
    lines.append(json.dumps(r, separators=(',', ':')))
(out / 'transfer-receipts.jsonl').write_bytes(('\n'.join(lines) + '\n').encode())
(out / 'README.txt').write_bytes((
    'Quantised copy (quant.py, k = %g) of planes 1..%d of %s, written by s7-quantised-copy.py.\n'
    'Only the CFA strips differ from the originals; events.jsonl and transfer-receipts.jsonl are cut to these\n'
    'files and carry the modified files\' SHA-256. Scratch: delete when done.\n' % (k, planes, run)).encode())
print('done:', out)
