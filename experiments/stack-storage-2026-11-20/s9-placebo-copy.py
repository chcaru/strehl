"""S9: the causal placebo for the calibrated tier's render test.

  python s9-placebo-copy.py K PLANES OUT_DIR [RUN]

Like s7-quantised-copy.py, but each CFA sample is NOT quantised: it gets an independent random
integer drawn uniformly from the same range the k-sigma quantiser's error has at that level
(-(w - 1) / 2 .. +(w - 1) / 2 for the bin width w of quant.py), so the perturbation has the
quantiser's size at every level and none of its dependence on the sample's own value.
A render from this copy shows what any perturbation of that size does to the merge; the
calibrated copy's render should differ from the lossless render by no more than this one does.
16383 (clipped) stays exact, as in the quantiser. Seeded per frame; the capture is only read.
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
half = ((width[code] - 1) // 2).astype(np.int32)  # per raw value
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
    rng = np.random.default_rng(20261120 + frame)
    h = half[strip]
    u = np.floor(rng.random(strip.shape) * (2 * h + 1)).astype(np.int32) - h
    q = np.clip(strip.astype(np.int32) + u, 0, quant.WHITE - 1)
    q[strip == quant.WHITE] = quant.WHITE
    d = q - strip
    err2 += float((d.astype(np.float64) ** 2).sum())
    count += d.size
    strip[:] = q.astype(np.uint16)
    data = b.tobytes()
    shas[name] = (old, hashlib.sha256(data).hexdigest(), len(data))
    with open(dst, 'wb') as f:
        f.write(data)
    c.drop(run, frame)
    if frame % 16 == 0:
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
print('done:', out)
