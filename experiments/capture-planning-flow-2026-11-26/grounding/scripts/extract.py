"""Per-frame summaries of a capture, for the grounding analyses. The capture folder is read only.

For every plane, member 1 of its last complete base group (and of its highlight group, when it
has one) is restored from its `.ARW.straw` archive into scratch, read with rawpy inside the
context, and deleted. Saved per frame, uncompressed:

  g       uint16 (H/2, W/2)   one green site plane, raw DN (the site `strehl focus-step` reads)
  mean8   float32 (3, H/8, W/8)  mean above black per colour over 8 x 8 sensor pixels (R, G, B)
  max8    uint16 (3, H/8, W/8)   largest raw DN per colour over the same blocks
  pin64   uint16 (3, H/64, W/64) samples at the pin per 64 x 64 sensor-pixel tile and colour
  meta    json: plane, focus, tier, iso, shutter code, seconds, file, black, white, largest DN

  python extract.py <capture folder> <out folder> [workers] [--every N]
"""
import concurrent.futures as cf
import json
import pathlib
import subprocess
import sys

import numpy as np
import rawpy

TOOL = pathlib.Path(r'C:\dev\blog\death-of-software\projects\strehl\target\release\strehl-raw-archive.exe')
PIN_MARGIN = 2


def seconds(code):
    n, d = code >> 16, code & 0xffff
    return n / d if d else None


def frames(run):
    """{(plane, tier): record}, the last complete group of each."""
    out = {}
    # Older journals do not record the exposure per group: the run's own, from its manifest.
    props = json.loads((run / 'manifest.json').read_text()).get('initial_status', {}).get('properties', {})
    run_exposure = {'iso': props.get('IsoSensitivity', {}).get('value'), 'shutter': props.get('ShutterSpeed', {}).get('value')}
    for line in open(run / 'events.jsonl', encoding='utf-8'):
        e = json.loads(line)
        if e.get('event') not in ('capture_buffered', 'capture_complete'):
            continue
        d = e['data']
        r = d['response']
        if not r.get('group_complete', True):
            continue
        files = sorted(r['files'], key=lambda f: f.get('member_index', 1))
        tier = d.get('tier') or 'base'
        exposure = d.get('exposure') or run_exposure
        out[(d['ordinal'], tier)] = {
            'plane': d['ordinal'], 'tier': tier, 'focus': files[0].get('focus', d.get('target')),
            'iso': exposure['iso'], 'shutter': exposure['shutter'],
            'seconds': seconds(exposure['shutter']) if exposure['shutter'] else None, 'file': files[0]['name'],
            'files': [f['name'] for f in files], 'group': files[0]['group_id'], 'unix_ms': e['unix_ms']}
    return out


def read_raw(run, name, scratch):
    scratch.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(TOOL), 'restore', str(run / (name + '.straw')), '--output-dir', str(scratch)],
                   check=True, capture_output=True)
    arw = scratch / name
    with rawpy.imread(str(arw)) as raw:
        img = raw.raw_image_visible.copy()
        black = float(np.mean(raw.black_level_per_channel))
        white = float(raw.white_level)
        pattern = raw.raw_pattern.copy()
        colours = raw.color_desc.decode()
    arw.unlink()
    cfa = [[colours[pattern[y, x]] for x in (0, 1)] for y in (0, 1)]
    return img, black, white, cfa


def block(a, n, f):
    h, w = a.shape[0] // n * n, a.shape[1] // n * n
    return f(a[:h, :w].reshape(h // n, n, w // n, n), axis=(1, 3))


def one(args):
    run, out, rec = args
    dst = out / ('%s-%04d.npz' % (rec['tier'], rec['plane']))
    if dst.exists():
        return rec['plane'], rec['tier'], 'kept'
    scratch = out / ('tmp-%s-%d' % (rec['tier'], rec['plane']))
    img, black, white, cfa = read_raw(run, rec['file'], scratch)
    scratch.rmdir()
    sites = {c: [(y, x) for y in (0, 1) for x in (0, 1) if cfa[y][x] == c] for c in 'RGB'}
    gy, gx = sites['G'][0]
    mean8, max8, pin64 = [], [], []
    for c in 'RGB':
        planes = [img[y::2, x::2] for y, x in sites[c]]
        m = sum(block(p.astype(np.float32), 4, np.mean) for p in planes) / len(planes) - black
        mx = np.maximum.reduce([block(p, 4, np.max) for p in planes])
        pn = sum(block((p >= white - PIN_MARGIN).astype(np.uint16), 32, np.sum) for p in planes)
        mean8.append(m.astype(np.float32)); max8.append(mx); pin64.append(pn.astype(np.uint16))
    meta = dict(rec, black=black, white=white, largest=int(img.max()), cfa=cfa, green_site=[gy, gx],
                shape=list(img.shape))
    np.savez(dst, g=img[gy::2, gx::2].copy(), mean8=np.stack(mean8), max8=np.stack(max8),
             pin64=np.stack(pin64), meta=json.dumps(meta))
    return rec['plane'], rec['tier'], 'done'


def main():
    run, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    rest = sys.argv[3:]
    every = int(rest[rest.index('--every') + 1]) if '--every' in rest else 1
    workers = int(rest[0]) if rest and rest[0].isdigit() else 10
    out.mkdir(parents=True, exist_ok=True)
    recs = [r for (p, t), r in sorted(frames(run).items()) if p % every == 0]
    (out / 'index.json').write_text(json.dumps(recs, indent=1))
    done = 0
    with cf.ThreadPoolExecutor(workers) as pool:
        for plane, tier, state in pool.map(one, [(run, out, r) for r in recs]):
            done += 1
            if done % 20 == 0 or done == len(recs):
                print(done, 'of', len(recs), 'last', tier, plane, state, flush=True)


if __name__ == '__main__':
    main()
