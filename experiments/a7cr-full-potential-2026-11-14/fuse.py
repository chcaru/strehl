"""Depth map and per-channel matched fusion (brief.md steps 2-4).

  python -X utf8 fuse.py energy WORK_DIR TAG [--no-ca]
  python -X utf8 fuse.py depth  WORK_DIR TAG
  python -X utf8 fuse.py fuse   WORK_DIR TAG ARMS.json

`energy`: every assembled plane is warped to the reference geometry (plane
similarity from align.json, per-channel lateral colour from ca.json unless
--no-ca) and split into bands; the signal amplitude of the three finest bands
of each channel (band power minus the injected noise model's power, signed
square root) is stored on a 1/8 grid: WORK_DIR/energy-TAG.npy
[planes, 3 channels, 3 bands, H/8, W/8] float16.

`depth`: per 1/8 cell, a Gaussian through-focus fit of green's band-1 power
gives the focus plane (fractional), then confidence-weighted smoothing fills
weak cells. Also fitted: each band's focus-curve width, red's and blue's
focus offset from green (axial colour), and each plane's sharpness relative
to the fitted curves (a plane blurred by vibration reads low).

`fuse`: for each channel c and fusion band b (split_fine), with D_c the
channel's depth map and k the plane index, the weight of plane k is the
measured coherent transfer t_b(k - D_c) (coherence.py; zero below `floor`)
times the plane's quality, and the fused band is sum(t Y) / sum(t^2): the
matched filter for the transfer the data actually shows, unbiased for the
in-focus coefficient on average, with variance sigma^2 sum(t^2) / sum(t^2)^2.
Quarter-grid bands take a Gaussian-weighted mean (tau_q planes). Odd and even
planes are accumulated separately (two independent halves); their sum is the
full result. Outside the box that every plane covers the result is
edge-replicated. ARMS.json lists the arms accumulated in one pass: {name, select
(each half takes its own nearest plane, so the full result is the mean of
the two planes bracketing focus: a selector on the same depth map, for
pricing the fusion's light), common_focus (delta_c = 0, arm P1), tau_scale (per band)}.
delta_c is a smooth map (red and blue focus offset from green); own_depth
uses each channel's own depth map instead of green's plus that offset.
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
import fp

H, W = 6336, 9504
S8 = 8
NB_FULL = 3          # bands kept at full resolution
SIG_Q = [1.5, 3.0, 6.0]  # successive total sigmas on the quarter grid


ASM_DIR = os.environ.get('FP_ASM', 'asm')   # 'asm-m1': the one-exposure demosaiced control


def load_asm(work, p):
    a = np.fromfile(work / ASM_DIR / f'p{p:03d}.u16', dtype='<u2').reshape(3, H, W)
    return torch.from_numpy(a.view(np.int16)).to(fp.DEV).float().add_(65536.0).remainder_(65536.0) / 4.0 - 64.0


class Geometry:
    def __init__(self, work, use_ca=True):
        a = json.loads((work / 'align.json').read_text())
        self.planes = sorted(int(p) for p in a['planes'])
        self.align = {int(p): v for p, v in a['planes'].items()}
        self.reference = a['reference']
        ca = json.loads((work / 'ca.json').read_text()) if use_ca else None
        self.ca = [(ca['red']['eps'], ca['red']['dx'], ca['red']['dy']), (0.0, 0.0, 0.0),
                   (ca['blue']['eps'], ca['blue']['dx'], ca['blue']['dy'])] if ca else [(0.0, 0.0, 0.0)] * 3
        # The control's planes are member 1 alone, which sits at its own measured offset from the
        # group mean that the assembled planes (and so the alignment) refer to.
        self.member_shift = {}
        if ASM_DIR != 'asm':
            for line in (work / 'pass0.jsonl').read_text().splitlines():
                r = json.loads(line)
                self.member_shift[r['plane']] = (r['motion'][0][0], r['motion'][0][1])

    def warp(self, x, p, c):
        """Channel c of plane p ([H, W]) resampled to the reference geometry."""
        a = self.align[p]
        eps, dx, dy = self.ca[c]
        mx, my = self.member_shift.get(p, (0.0, 0.0))
        return fp.warp_similarity(x, a['scale'] * (1 + eps), a['theta'], (1 + eps) * a['tx'] + dx - mx, (1 + eps) * a['ty'] + dy - my)

    def valid(self, p, margin=12):
        """Reference-frame box [x0, x1, y0, y1] where plane p has real samples for every channel."""
        a = self.align[p]
        box = [0.0, W - 1.0, 0.0, H - 1.0]
        for eps, dx, dy in self.ca:
            s = a['scale'] * (1 + eps)
            for axis, (n, t) in enumerate(((W, (1 + eps) * a['tx'] + dx), (H, (1 + eps) * a['ty'] + dy))):
                c = (n - 1) / 2
                lo = c + (margin - t - c) / s
                hi = c + (n - 1 - margin - t - c) / s
                box[2 * axis] = max(box[2 * axis], lo)
                box[2 * axis + 1] = min(box[2 * axis + 1], hi)
        return box


def up4(q):
    return F.interpolate(q[None, None], size=(H, W), mode='bicubic', align_corners=False)[0, 0]


def split(x):
    """Exact band split of one channel: three full-resolution bands and
    [b3, b4, b5, base] on the quarter grid; x = b0 + b1 + b2 + up4(sum(q))."""
    l1 = fp.gauss(x, 1.0)
    b0 = x - l1
    l2 = fp.gauss(l1, math.sqrt(3.0))
    b1 = l1 - l2
    dq = F.avg_pool2d(fp.gauss(l2, math.sqrt(12.0))[None, None], 4)[0, 0]
    b2 = l2 - up4(dq)
    q, prev, cur = [], 0.0, dq
    for s in SIG_Q:
        nxt = fp.gauss(cur, math.sqrt(s * s - prev * prev))
        q.append(cur - nxt)
        prev, cur = s, nxt
    q.append(cur)
    return [b0, b1, b2], q, dq


NBF = 4  # full-resolution bands of the fusion split


def split_fine(x):
    """Exact band split used for fusion: four full-resolution bands (Gaussian
    scales 0.5, 1, 2, 4 photosites; the finest octave is split in two because
    its upper half decorrelates across planes faster than its lower half) and
    [three bands, base] on the quarter grid; x = sum(full) + up4(sum(q))."""
    l05 = fp.gauss(x, 0.5)
    l1 = fp.gauss(l05, math.sqrt(0.75))
    l2 = fp.gauss(l1, math.sqrt(3.0))
    dq = F.avg_pool2d(fp.gauss(l2, math.sqrt(12.0))[None, None], 4)[0, 0]
    full = [x - l05, l05 - l1, l1 - l2, l2 - up4(dq)]
    q, prev, cur = [], 0.0, dq
    for sg in SIG_Q:
        nxt = fp.gauss(cur, math.sqrt(sg * sg - prev * prev))
        q.append(cur - nxt)
        prev, cur = sg, nxt
    q.append(cur)
    return full, q, dq


def fine_noise_gain():
    """Power of unit white noise in each fusion band after a typical
    resampling (measured on these operators)."""
    g = torch.Generator(device=fp.DEV).manual_seed(1)
    n = torch.randn(1024, 1024, device=fp.DEV, generator=g)
    n = fp.warp_scale_shift(n, 1.0031, 0.37, -0.41)
    l05 = fp.gauss(n, 0.5)
    l1 = fp.gauss(l05, math.sqrt(0.75))
    l2 = fp.gauss(l1, math.sqrt(3.0))
    l3 = fp.gauss(l2, math.sqrt(12.0))
    return [float(((a - b)[64:-64, 64:-64] ** 2).mean()) for a, b in ((n, l05), (l05, l1), (l1, l2), (l2, l3))]


def table_weight(m, table):
    """Linear interpolation of a transfer table (offsets -J..J) at fractional
    plane offsets m; zero outside the table."""
    J = (table.numel() - 1) // 2
    pos = (m + J).clamp(0, 2 * J)
    i0 = pos.floor().long().clamp(0, 2 * J - 1)
    f = pos - i0
    return torch.where(m.abs() <= J, table[i0] * (1 - f) + table[i0 + 1] * f, torch.zeros_like(m))


def band_noise_gain():
    """Power of unit white noise in each full-resolution band after a typical
    resampling (measured on these operators)."""
    g = torch.Generator(device=fp.DEV).manual_seed(1)
    n = torch.randn(1024, 1024, device=fp.DEV, generator=g)
    n = fp.warp_scale_shift(n, 1.0031, 0.37, -0.41)
    l1 = fp.gauss(n, 1.0)
    l2 = fp.gauss(l1, math.sqrt(3.0))
    l3 = fp.gauss(l2, math.sqrt(12.0))
    return [float(((a - b)[64:-64, 64:-64] ** 2).mean()) for a, b in ((n, l1), (l1, l2), (l2, l3))]


def stage_energy(work, tag, use_ca):
    geo = Geometry(work, use_ca)
    kappa = band_noise_gain()
    print('band noise gain', kappa)
    out = np.lib.format.open_memmap(work / f'energy-{tag}.npy', mode='w+', dtype=np.float16,
                                    shape=(len(geo.planes), 3, NB_FULL, H // S8, W // S8))
    levels = []
    for i, p in enumerate(geo.planes):
        t0 = time.time()
        x = load_asm(work, p)
        lv = []
        for c in range(3):
            w = geo.warp(x[c], p, c)
            bands, q, dq = split(w)
            var = (fp.GAIN_DN_PER_E * up4(dq).clamp(min=0) + fp.READ_NOISE_DN ** 2) * (0.5 if c == 1 else 1.0)
            vq = F.avg_pool2d(var[None, None], S8)[0, 0]
            for b in range(NB_FULL):
                e = F.avg_pool2d((bands[b] ** 2)[None, None], S8)[0, 0] - kappa[b] * vq
                out[i, c, b] = (e.sign() * e.abs().sqrt()).half().cpu().numpy()
            lv.append(float(dq[200:-200, 300:-300].mean()))
            del w, bands, q, dq, var
        levels.append(lv)
        del x
        print(p, round(time.time() - t0, 1), [round(v, 1) for v in lv], flush=True)
    out.flush()
    (work / f'energy-{tag}.json').write_text(json.dumps({'planes': geo.planes, 'kappa': kappa, 'levels': levels}) + '\n')


def gauss_fit(S, half=7):
    """Per-cell Gaussian through-focus fit of power S [n, h, w] (may be
    negative). Returns peak position (fractional index), sigma, peak power,
    and a validity mask."""
    n = S.shape[0]
    k = torch.tensor([0.25, 0.5, 0.25], device=S.device).view(1, 1, 3)
    flat = S.reshape(n, -1).T[:, None, :]
    sm = F.conv1d(F.pad(flat, (1, 1), mode='replicate'), k)
    sm = F.conv1d(F.pad(sm, (1, 1), mode='replicate'), k)[:, 0, :]          # [cells, n]
    peak, kstar = sm.max(1)
    offs = torch.arange(-half, half + 1, device=S.device)
    idx = (kstar[:, None] + offs[None, :]).clamp(0, n - 1)
    inside = ((kstar[:, None] + offs[None, :]) >= 0) & ((kstar[:, None] + offs[None, :]) < n)
    v = torch.gather(sm, 1, idx)
    use = inside & (v > 0.3 * peak[:, None]) & (peak[:, None] > 0)
    # contiguous run around the peak only
    left = torch.cumprod(use[:, :half + 1].flip(1).int(), 1).flip(1).bool()
    right = torch.cumprod(use[:, half:].int(), 1).bool()
    use = torch.cat([left[:, :half], right], 1)
    wgt = (use.double() * (v.double().clamp(min=0) ** 2))
    y = torch.log(v.double().clamp(min=1e-12))
    t = offs.double()[None, :].expand_as(y)
    A = torch.stack([wgt.sum(1), (wgt * t).sum(1), (wgt * t * t).sum(1), (wgt * t ** 3).sum(1), (wgt * t ** 4).sum(1)], 1)
    M = torch.stack([torch.stack([A[:, 0], A[:, 1], A[:, 2]], 1), torch.stack([A[:, 1], A[:, 2], A[:, 3]], 1),
                     torch.stack([A[:, 2], A[:, 3], A[:, 4]], 1)], 1)
    r = torch.stack([(wgt * y).sum(1), (wgt * y * t).sum(1), (wgt * y * t * t).sum(1)], 1)
    M = M + (1e-9 * M.diagonal(dim1=1, dim2=2).mean(1) + 1e-12)[:, None, None] * torch.eye(3, device=S.device, dtype=M.dtype)
    sol = torch.linalg.solve(M, r[..., None])[..., 0]
    a, b, c = sol[:, 0], sol[:, 1], sol[:, 2]
    ok = (c < -1e-4) & (use.sum(1) >= 4)
    k0 = kstar.double() - b / (2 * c.clamp(max=-1e-4))
    sig = torch.sqrt(-1 / (2 * c.clamp(max=-1e-4)))
    amp = torch.exp(a - b * b / (4 * c.clamp(max=-1e-4)))
    ok = ok & ((k0 - kstar).abs() < 2.5) & (sig > 0.7) & (sig < 40)
    shp = S.shape[1:]
    return k0.float().reshape(shp), sig.float().reshape(shp), amp.float().reshape(shp), ok.reshape(shp), peak.reshape(shp)


def smooth_fill(v, w, sigma):
    num = fp.gauss(v * w, sigma)
    den = fp.gauss(w, sigma)
    return num / den.clamp(min=1e-12), den


def stage_depth(work, tag):
    info = json.loads((work / f'energy-{tag}.json').read_text())
    E = np.load(work / f'energy-{tag}.npy', mmap_mode='r')
    n = E.shape[0]

    def power(c, b):
        a = torch.from_numpy(np.ascontiguousarray(E[:, c, b]).astype(np.float32)).to(fp.DEV)
        return a.sign() * a * a

    g1 = power(1, 1)
    k0, sig, amp, ok, peak = gauss_fit(g1)
    # confidence: fitted peak power against the spread of the cell's weakest planes
    floor = g1.kthvalue(max(1, n // 5), 0).values.abs() + 1.0
    conf = (amp / floor).clamp(max=1e4) * ok
    strong = ok & (amp > 25.0 * floor)
    print(f'cells {ok.numel()}, fitted {int(ok.sum())}, strong {int(strong.sum())}')
    w = conf.clamp(max=400.0)
    d1, den = smooth_fill(torch.where(ok, k0, torch.zeros_like(k0)), w, 2.0)
    # reject cells far from their neighbourhood, then refill
    w = w * ((k0 - d1).abs() < 3.0)
    d2, den = smooth_fill(torch.where(ok, k0, torch.zeros_like(k0)), w, 1.5)
    wide, den_w = smooth_fill(torch.where(ok, k0, torch.zeros_like(k0)), w, 12.0)
    trust = (den / (den + 20.0))
    D = trust * d2 + (1 - trust) * wide
    res = {'planes': info['planes'], 'n': n}
    # widths per band and channel offsets, over strong cells
    widths, offsets = {}, {}
    for c in range(3):
        for b in range(NB_FULL):
            kc, sc, ac, okc, _ = gauss_fit(power(c, b))
            m = strong & okc & (ac > 0)
            widths[f'{"RGB"[c]}{b}'] = float(sc[m].median())
            offsets[f'{"RGB"[c]}{b}'] = {'median': float((kc - k0)[m].median()), 'mean': float((kc - k0)[m].mean()),
                                         'iqr': [float(torch.quantile((kc - k0)[m][::7], q)) for q in (0.25, 0.75)], 'cells': int(m.sum())}
            if c != 1 and b == 1:
                dd = (kc - k0)
                yy, xx = torch.meshgrid(torch.arange(D.shape[0], device=fp.DEV), torch.arange(D.shape[1], device=fp.DEV), indexing='ij')
                r2 = (((xx - D.shape[1] / 2) * S8) ** 2 + ((yy - D.shape[0] / 2) * S8) ** 2) / 5711.0 ** 2
                A = torch.stack([torch.ones_like(r2[m]), r2[m]], 1).double()
                sol = torch.linalg.lstsq(A, dd[m].double()[:, None]).solution[:, 0]
                offsets[f'{"RGB"[c]}{b}']['radial'] = [float(sol[0]), float(sol[1])]
    for c, name in ((0, 'red'), (2, 'blue')):
        kc, sc, ac, okc, _ = gauss_fit(power(c, 1))
        m = (strong & okc & ((kc - k0).abs() < 15)).float()
        dmap, dden = smooth_fill(torch.where(m > 0, kc - k0, torch.zeros_like(k0)), m, 24.0)
        np.save(work / f'depth-{tag}-delta-{name}.npy', dmap.cpu().numpy())
        print(name, 'focus offset map: min %.2f median %.2f max %.2f planes' % (float(dmap.min()), float(dmap.median()), float(dmap.max())))
        # The channel's own depth map: its own through-focus fit where it is
        # confident, regularised exactly like green's, falling back to green's
        # map plus the smooth offset elsewhere.
        pc = power(c, 1)
        floor_c = pc.kthvalue(max(1, n // 5), 0).values.abs() + 1.0
        wc = ((ac / floor_c).clamp(max=400.0) * okc) * ((kc - (D + dmap)).abs() < 6.0)
        own, den_c = smooth_fill(torch.where(okc, kc, torch.zeros_like(kc)), wc, 2.0)
        trust_c = den_c / (den_c + 20.0)
        Dc = trust_c * own + (1 - trust_c) * (D + dmap)
        np.save(work / f'depth-{tag}-own-{name}.npy', Dc.cpu().numpy())
        dd = (Dc - D - dmap)
        print(name, 'own depth map minus (green + smooth offset): rms %.2f planes, trusted cells %.0f%%' % (float(dd.pow(2).mean().sqrt()), 100 * float((trust_c > 0.5).float().mean())))
    res['sigma_planes'] = widths
    res['offset_planes'] = offsets
    # plane quality: measured band-1 green power against the cell fits, near focus
    kk = torch.arange(n, device=fp.DEV).view(n, 1, 1)
    ampz = torch.where(strong, amp, torch.zeros_like(amp))
    k0z = torch.where(strong, k0, torch.zeros_like(k0))
    sigz = torch.where(strong, sig, torch.ones_like(sig))
    pred = ampz[None] * torch.exp(-(kk - k0z[None]) ** 2 / (2 * sigz[None] ** 2))
    near = strong[None] & (pred > 0.6 * ampz[None])
    q = ((g1 * pred * near).double().sum((1, 2)) / (pred * pred * near).double().sum((1, 2)).clamp(min=1e-9)).cpu().numpy()
    res['plane_quality'] = q.tolist()
    res['near_cells'] = near.sum((1, 2)).tolist()
    np.save(work / f'depth-{tag}.npy', D.cpu().numpy())
    np.save(work / f'depth-{tag}-raw.npy', torch.stack([k0, sig, amp, ok.float(), conf]).cpu().numpy())
    (work / f'depth-{tag}.json').write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: res[k] for k in ('sigma_planes', 'offset_planes')}, indent=1))
    print('plane quality min/median/max', float(np.min(q)), float(np.median(q)), float(np.max(q)))
    print('lowest planes', [(info['planes'][i], round(float(q[i]), 3)) for i in np.argsort(q)[:12]])
    from PIL import Image
    v = ((D - D.min()) / (D.max() - D.min())).cpu().numpy()
    Image.fromarray((v * 255).astype(np.uint8)).save(work / f'depth-{tag}.png')


def stage_fuse(work, tag, arms):
    """arms: list of {name, weights ('coherent' | 'select'), common_focus,
    own_depth, floor, tau_q}."""
    geo = Geometry(work, use_ca=False)
    dj = json.loads((work / f'depth-{tag}.json').read_text())
    planes = dj['planes']
    n = len(planes)
    NQ = len(SIG_Q) + 1
    D8 = torch.from_numpy(np.load(work / f'depth-{tag}.npy')).to(fp.DEV).clamp(0, n - 1)
    own8 = [torch.from_numpy(np.load(work / f'depth-{tag}-own-red.npy')).to(fp.DEV).clamp(0, n - 1), D8,
            torch.from_numpy(np.load(work / f'depth-{tag}-own-blue.npy')).to(fp.DEV).clamp(0, n - 1)]
    coh = json.loads((work / f'coherence-{tag}.json').read_text())
    # Green's tables serve every channel: red's own table rests on too few sites in the measured crop
    # (its focus lies beyond the offsets the stack's end allows there).
    tables = [[torch.tensor(coh['channels'][1]['bands'][b]['coherent'], device=fp.DEV, dtype=torch.float32) for b in range(NBF)] for c in range(3)]

    def quarter(m):
        return F.interpolate(m[None, None], size=(H // 4, W // 4), mode='bilinear', align_corners=False)[0, 0]

    quality = np.clip(np.array(dj['plane_quality']), 0.0, 1.0)
    gains = np.array(json.loads((work / f'energy-{tag}.json').read_text())['levels'])[:, 1]
    gains = gains / np.median(gains)
    box = [0.0, W - 1.0, 0.0, H - 1.0]
    for p in planes:
        v = geo.valid(p)
        box = [max(box[0], v[0]), min(box[1], v[1]), max(box[2], v[2]), min(box[3], v[3])]
    box = [int(math.ceil(box[0])) + 4, int(math.floor(box[1])) - 4, int(math.ceil(box[2])) + 4, int(math.floor(box[3])) - 4]
    print('common valid box (x0, x1, y0, y1):', box, flush=True)
    state = []
    for arm in arms:
        st = {'arm': arm,
              'num': [[[torch.zeros(H, W, device=fp.DEV) for _ in range(NBF)] for _ in range(3)] for _ in range(2)],
              'numq': [[[torch.zeros(H // 4, W // 4, device=fp.DEV) for _ in range(NQ)] for _ in range(3)] for _ in range(2)],
              'den': [[[torch.zeros(H // 4, W // 4, device=fp.DEV) for _ in range(NBF)] for _ in range(3)] for _ in range(2)],
              'var': [[[torch.zeros(H // 4, W // 4, device=fp.DEV) for _ in range(NBF)] for _ in range(3)] for _ in range(2)],
              'denq': [[[torch.zeros(H // 4, W // 4, device=fp.DEV) for _ in range(NQ)] for _ in range(3)] for _ in range(2)]}
        state.append(st)
        print(arm, flush=True)
    for i, p in enumerate(planes):
        half = i % 2
        t0 = time.time()
        x = load_asm(work, p) / float(gains[i])
        qk = float(quality[i])
        for c in range(3):
            bands, q, _ = split_fine(geo.warp(x[c], p, c))
            for st in state:
                arm = st['arm']
                dq = i - quarter(D8 if arm.get('common_focus') else own8[2 - c] if arm.get('swap_depth') else own8[c])
                df = F.interpolate(dq[None, None], size=(H, W), mode='bilinear', align_corners=False)[0, 0]
                select = arm.get('weights') == 'select'
                for b in range(NBF):
                    if select:
                        hq, hf = ((dq > -1) & (dq <= 1)).float(), ((df > -1) & (df <= 1)).float()
                        tq = hq
                    else:
                        floor = arm.get('floor', 0.3)
                        tq, tf = table_weight(dq, tables[c][b]), table_weight(df, tables[c][b])
                        tq = torch.where(tq >= floor, tq, torch.zeros_like(tq))
                        hq, hf = qk * tq, qk * torch.where(tf >= floor, tf, torch.zeros_like(tf))
                    st['num'][half][c][b] += hf * bands[b]
                    st['den'][half][c][b] += hq * tq
                    st['var'][half][c][b] += hq * hq
                hq = ((dq > -1) & (dq <= 1)).float() if select else qk * torch.exp(-dq * dq / (2 * arm.get('tau_q', 6.0) ** 2))
                for b in range(NQ):
                    st['numq'][half][c][b] += hq * q[b]
                    st['denq'][half][c][b] += hq
                del dq, df
            del bands, q
        del x
        torch.cuda.empty_cache()
        print(p, round(time.time() - t0, 1), flush=True)
    out = work / 'fused'
    out.mkdir(exist_ok=True)
    xi = torch.arange(W, device=fp.DEV).clamp(box[0], box[1])
    yi = torch.arange(H, device=fp.DEV).clamp(box[2], box[3])
    for st in state:
        name_arm = st['arm']['name']
        for name, halves in (('all', (0, 1)), ('odd', (0,)), ('even', (1,))):
            img = torch.zeros(3, H, W, device=fp.DEV)
            for c in range(3):
                qsum = torch.zeros(H // 4, W // 4, device=fp.DEV)
                for b in range(NQ):
                    qsum += sum(st['numq'][h][c][b] for h in halves) / sum(st['denq'][h][c][b] for h in halves).clamp(min=0.05)
                img[c] = up4(qsum)
                for b in range(NBF):
                    d = up4(sum(st['den'][h][c][b] for h in halves)).clamp(min=0.25)
                    img[c] += sum(st['num'][h][c][b] for h in halves) / d
            img = img.index_select(1, yi).index_select(2, xi)   # outside the common box: edge-replicated
            np.save(out / f'{name_arm}-{name}.npy', img.cpu().numpy())
            del img
        # variance of a fused band coefficient relative to one plane's: sum(h^2) / sum(h t)^2
        rel = torch.stack([torch.stack([(st['var'][0][c][b] + st['var'][1][c][b]) / (st['den'][0][c][b] + st['den'][1][c][b]).clamp(min=0.25) ** 2
                                        for b in range(NBF)]) for c in range(3)])
        np.save(out / f'{name_arm}-relvar.npy', rel.half().cpu().numpy())
        (out / f'{name_arm}-box.json').write_text(json.dumps({'box': box}) + '\n')
        print(name_arm, 'median noise variance of a fused band relative to one plane (green):', [round(float(rel[1, b].median()), 3) for b in range(NBF)], flush=True)
        st.clear()


if __name__ == '__main__':
    stage, work, tag = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    with torch.no_grad():
        if stage == 'energy':
            no_ca = '--no-ca' in sys.argv
            if no_ca:
                (work / f'energy-{tag}.noca').write_text('')
            stage_energy(work, tag, not no_ca)
        elif stage == 'depth':
            stage_depth(work, tag)
        elif stage == 'fuse':
            stage_fuse(work, tag, json.loads(Path(sys.argv[4]).read_text()))
