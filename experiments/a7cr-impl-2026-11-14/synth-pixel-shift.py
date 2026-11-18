"""Truth-referenced synthetic four-shot pixel-shift focus stack (plan gate 3).

A real lit A7C II capture (read-only) supplies a full-colour scene at quad
resolution; it is upsampled 2x, reflect-padded to the A7CR buffer and given
two test patches (a neutral slanted edge and a colour zone plate). Each focal
plane blurs the scene by a depth-dependent Gaussian (depth increases left to
right); each plane is sampled into four RGGB mosaics shifted by whole
photosites, with Poisson-Gaussian noise, and written into the strips of real
A7CR four-shot ARWs (their metadata kept), with a capture journal and durable
receipts so that `strehl pixel-shift` and STREHL_PIXEL_SHIFT=remosaic find
the groups exactly as on a real run.

Usage: synth-pixel-shift.py SOURCE_ARW TEMPLATE_DIR OUT_DIR [--planes 5]
TEMPLATE_DIR holds four restored A7CR members frame-00000{1..4}.ARW.
Writes OUT_DIR/run (the group run), OUT_DIR/single (hard links to member 1)
and OUT_DIR/truth.npy (all-in-focus camera RGB over the active area, DN).
"""
import argparse, hashlib, json, os, struct
from pathlib import Path
import numpy as np
import rawpy
from scipy import ndimage

OFFSETS = [(0, 0), (1, 0), (1, 1), (0, 1)]  # member k photosite x+o sees scene x
GAIN, READ, BLACK, WHITE = 0.40, 1.33, 512, 15360


def raw_layout(b):
    def tags_at(at):
        n = struct.unpack_from('<H', b, at)[0]
        t = {}
        for i in range(n):
            tag, typ, cnt, val = struct.unpack_from('<HHII', b, at + 2 + 12 * i)
            t[tag] = (typ, cnt, val)
        return t, struct.unpack_from('<I', b, at + 2 + 12 * n)[0]
    todo, raw = [struct.unpack_from('<I', b, 4)[0]], None
    while todo:
        at = todo.pop()
        if not at or at + 2 > len(b):
            continue
        t, nxt = tags_at(at)
        todo.append(nxt)
        if 330 in t:
            todo.append(t[330][2])
        if t.get(262, (0, 0, 0))[2] == 32803:
            raw = t
    w, h, off = raw[256][2], raw[257][2], raw[273][2]
    ox, oy = struct.unpack_from('<II', b, raw[0xC61F][2])
    cw, ch = struct.unpack_from('<II', b, raw[0xC620][2])
    return w, h, off, ox, oy, cw, ch


def scene_from(source, buf_w, buf_h):
    with rawpy.imread(str(source)) as r:
        raw = r.raw_image_visible.astype(np.float32).copy()
        black = float(np.mean(r.black_level_per_channel))
        pattern = r.raw_pattern.copy()
    assert pattern.tolist() == [[0, 1], [3, 2]], pattern
    raw -= black
    q = np.stack([raw[0::2, 0::2], 0.5 * (raw[0::2, 1::2] + raw[1::2, 0::2]), raw[1::2, 1::2]], -1)
    q = np.clip(q, 0, None)
    up = np.stack([ndimage.zoom(q[..., c], 2, order=1) for c in range(3)], -1)
    ph, pw = max(0, buf_h + 8 - up.shape[0]), max(0, buf_w + 8 - up.shape[1])
    up = np.pad(up, ((0, ph), (0, pw), (0, 0)), mode='reflect')[:buf_h + 8, :buf_w + 8]
    up *= 9000.0 / np.percentile(up[..., 1], 99.5)
    yy, xx = np.mgrid[0:600, 0:600].astype(np.float32)
    # Neutral slanted edge (5 degrees), grey levels identical in all channels.
    edge = np.where((xx - 300) * np.cos(0.087) + (yy - 300) * np.sin(0.087) > 0, 6000.0, 600.0)
    up[2000:2600, 3000:3600, :] = edge[..., None]
    # Colour zone plate: chroma at increasing spatial frequency.
    r2 = ((xx - 300) ** 2 + (yy - 300) ** 2) / 600.0
    zp = 0.5 + 0.5 * np.cos(np.pi * r2 * 0.9)
    up[3500:4100, 5000:5600, 0] = 600 + 5000 * zp
    up[3500:4100, 5000:5600, 1] = 600 + 5000 * (1 - zp)
    up[3500:4100, 5000:5600, 2] = 3000.0
    return up.astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source'); ap.add_argument('templates'); ap.add_argument('out')
    ap.add_argument('--planes', type=int, default=5)
    a = ap.parse_args()
    out = Path(a.out); run = out / 'run'; single = out / 'single'
    run.mkdir(parents=True); single.mkdir()
    templates = [bytearray(Path(a.templates, f'frame-00000{k + 1}.ARW').read_bytes()) for k in range(4)]
    w, h, off, ox, oy, aw, ah = raw_layout(templates[0])
    scene = scene_from(a.source, w, h)  # buffer coordinates + margin of 8
    np.save(out / 'truth.npy', scene[oy:oy + ah, ox:ox + aw])
    xs = (np.arange(w + 8, dtype=np.float32) - ox) / aw
    depth = np.broadcast_to(xs[None, :], scene.shape[:2])
    sigmas = [0.0, 0.75, 1.5, 3.0, 6.0]
    blurred = [scene] + [np.stack([ndimage.gaussian_filter(scene[..., c], s) for c in range(3)], -1)
                         for s in sigmas[1:]]
    rng = np.random.default_rng(20261114)
    by, bx = np.mgrid[0:h, 0:w]
    ay, ax = by - oy, bx - ox  # active coordinates
    colour = np.where((ax % 2 == 0) & (ay % 2 == 0), 0, np.where((ax % 2 == 1) & (ay % 2 == 1), 2, 1))
    events, receipts, n = [], [], 0
    for p in range(a.planes):
        focus = (p + 0.5) / a.planes
        sigma = np.minimum(6.0, 9.0 * np.abs(depth - focus))
        img = np.empty_like(scene)
        idx = np.clip(np.searchsorted(sigmas, sigma) - 1, 0, len(sigmas) - 2)
        lo = np.take(sigmas, idx); hi = np.take(sigmas, idx + 1)
        t = ((sigma - lo) / (hi - lo))[..., None]
        for i in range(len(sigmas) - 1):
            m = idx == i
            img[m] = (1 - t[m]) * blurred[i][m] + t[m] * blurred[i + 1][m]
        files = []
        for k, (dx, dy) in enumerate(OFFSETS):
            # Scene point seen by buffer photosite (bx, by) of member k: (bx - dx, by - dy).
            sy, sx = by - dy + 4, bx - dx + 4
            signal = img[sy, sx, colour]
            e = rng.poisson(np.clip(signal, 0, None) / GAIN) * GAIN + rng.normal(0, READ, signal.shape)
            dn = np.clip(np.round(e + BLACK), 0, WHITE).astype('<u2')
            b = bytearray(templates[k])
            kw, kh, koff, kox, koy, _, _ = raw_layout(b)
            assert (kw, kh, kox, koy) == (w, h, ox, oy), 'members share geometry'
            b[koff:koff + 2 * w * h] = dn.tobytes()
            n += 1
            name = f'frame-{n:06d}.ARW'
            (run / name).write_bytes(b)
            sha = hashlib.sha256(b).hexdigest()
            files.append({'name': name, 'plane': p + 1, 'group_id': f'synthetic-{p + 1}', 'member_index': k + 1,
                          'members': 4, 'sha256': sha, 'bytes': len(b), 'durable': False})
            receipts.append({'logical_name': name, 'sha256': sha, 'durable': True, 'ok': True, 'bytes': len(b)})
            if k == 0:
                os.link(run / name, single / name)
        events.append({'sequence': p + 1, 'event': 'capture_buffered',
                       'data': {'ordinal': p, 'response': {'pixel_shift_shots': 4, 'files': files}}})
        print('plane', p + 1, 'written', flush=True)
    (run / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
    (run / 'transfer-receipts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in receipts))
    (run / 'manifest.json').write_text(json.dumps({'schema': 'strehl-capture-v2', 'synthetic': True,
        'offsets': OFFSETS, 'gain_dn_per_e': GAIN, 'read_dn': READ, 'planes': a.planes}, indent=2) + '\n')


if __name__ == '__main__':
    main()
