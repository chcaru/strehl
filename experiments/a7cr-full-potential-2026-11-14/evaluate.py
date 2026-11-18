"""Bars N1 and R1 (brief.md): independent-realisation spectra of each arm.

  python -X utf8 evaluate.py WORK_DIR S0_DIR OUT_DIR ARM [ARM ...]

Pairs of independent realisations: S0 = the shipped stack of the single-shot
run and of the four-shot run as member1 (two captures); each prototype arm =
its odd-plane and even-plane halves (WORK_DIR/fused/ARM-odd.npy, -even.npy).
Arms named `file:LABEL:A.npy:B.npy` are read directly ([3, H, W] float32, in
the prototype's geometry and units).

Tiles: 256 px, where at least 70 % of the depth stage's cells are strongly
in focus, away from the border, with no clipped sample in S0. The prototype
tile and the S0 tile cover the same subject area (S0 is located by a fitted
similarity; it is about 1 % magnified by the shipped cover fit).

Per tile and channel, Hann-windowed FFTs A and B; their relative shift is
taken from the phase-correlation peak and removed as a phase ramp, so
registration error does not leak into either figure. Then
  signal(f) = Re(A conj(B))          (noise cancels; common content stays)
  noise(f)  = (|A|^2 + |B|^2) / 2 - signal(f)
normalised so that a sum over frequency bins is a variance per pixel. For a
prototype arm the full result is the mean of its halves, so its noise is the
halves' noise / 2. Prototype channels are scaled to S0 units by the ratio of
tile means.

R1: sqrt(sum signal) over 0.25-0.40 cycles/px, arm / S0.
N1: sqrt(sum noise x |1 - box5|^2) over all bins, arm / S0 (the high-pass
    of value minus its 5x5 box mean, evaluated in the Fourier domain).
Fooled by: content common to both realisations that is not scene (fixed
pattern, deterministic ringing, demosaic aliasing at a fixed CFA phase) counts
as signal; anything that differs counts as noise.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
import fp

H, W = 6336, 9504
T = 256


def lowres(img, f=8):
    return F.avg_pool2d(img[None, None], f)[0, 0]


def warp_sim(img, p):
    h, w = img.shape
    cx, cy = (w - 1) / 2, (h - 1) / 2
    yy, xx = torch.meshgrid(torch.arange(h, device=img.device, dtype=torch.float32),
                            torch.arange(w, device=img.device, dtype=torch.float32), indexing='ij')
    X = cx + p[0] * (xx - cx) + p[1]
    Y = cy + p[0] * (yy - cy) + p[2]
    grid = torch.stack([2 * (X + 0.5) / w - 1, 2 * (Y + 0.5) / h - 1], -1)[None]
    return F.grid_sample(img[None, None], grid, mode='bicubic', padding_mode='border', align_corners=False)[0, 0]


def register(a, b, scale0=1.0, rounds=6, tile=48):
    """(s, tx, ty) with b(c + s (x - c) + t) ~ a(x); images at any common
    resolution, band-passed here. Scale-and-shift parametric Lucas-Kanade."""
    def bp(x):
        x = x / x.mean()
        return fp.gauss(x, 1.5) - fp.gauss(x, 5.0)
    a, b = bp(a), bp(b)
    h, w = a.shape
    cx, cy = (w - 1) / 2, (h - 1) / 2
    yy, xx = torch.meshgrid(torch.arange(h, device=a.device, dtype=torch.float64) - cy,
                            torch.arange(w, device=a.device, dtype=torch.float64) - cx, indexing='ij')
    p = [scale0, 0.0, 0.0]
    for _ in range(rounds):
        wb = warp_sim(b, p)
        g = 0.5 * (a + wb)
        gx = F.pad((g[:, 2:] - g[:, :-2]) / 2, (1, 1)).double()
        gy = F.pad((g[2:, :] - g[:-2, :]) / 2, (0, 0, 1, 1)).double()
        dt = (wb - a).double()
        m = torch.ones_like(dt)
        m[:tile] = 0; m[-tile:] = 0; m[:, :tile] = 0; m[:, -tile:] = 0
        J = [gx * xx + gy * yy, gx, gy]
        A = torch.stack([torch.stack([(J[i] * J[j] * m).sum() for j in range(3)]) for i in range(3)])
        r = -torch.stack([(J[i] * dt * m).sum() for i in range(3)])
        d = torch.linalg.solve(A, r)
        p = [p[0] + float(d[0]), p[1] + float(d[1]), p[2] + float(d[2])]
    return p


def hann2(n, dev):
    w = torch.hann_window(n, periodic=True, device=dev, dtype=torch.float64)
    return w[:, None] * w[None, :]


def pair_spectra(a, b, win):
    """Normalised 2-D signal and noise spectra of one tile pair [T, T]."""
    a = a.double() - a.double().mean()
    b = b.double() - b.double().mean()
    FA, FB = torch.fft.fft2(a * win), torch.fft.fft2(b * win)
    X = FA * FB.conj()
    # relative shift from the phase-correlation peak, sub-pixel by parabola
    r = torch.fft.ifft2(X / (X.abs() + 1e-9 * X.abs().mean())).real
    idx = int(r.argmax())
    py, px = idx // T, idx % T
    def sub(vm, v0, vp):
        d = vm - 2 * v0 + vp
        return 0.0 if abs(float(d)) < 1e-12 else float(0.5 * (vm - vp) / d)
    sy = py + sub(r[(py - 1) % T, px], r[py, px], r[(py + 1) % T, px])
    sx = px + sub(r[py, (px - 1) % T], r[py, px], r[py, (px + 1) % T])
    sy = sy - T if sy > T / 2 else sy
    sx = sx - T if sx > T / 2 else sx
    fy = torch.fft.fftfreq(T, device=a.device, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=a.device, dtype=torch.float64)[None, :]
    X = X * torch.exp(2j * np.pi * (fx * sx + fy * sy))
    norm = T * T * float((win * win).sum())
    sig = X.real / norm
    noise = (FA.abs() ** 2 + FB.abs() ** 2) / (2 * norm) - sig
    return sig, noise, (sx, sy)


def main():
    work, s0dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    arms = sys.argv[4:]
    out.mkdir(parents=True, exist_ok=True)
    dev = fp.DEV
    tag = json.loads((work / 'eval-config.json').read_text())['depth_tag'] if (work / 'eval-config.json').exists() else 'ca'
    raw = np.load(work / f'depth-{tag}-raw.npy')
    sj = json.loads((work / f'depth-{tag}.json').read_text())
    amp, ok, conf = raw[2], raw[3] > 0, raw[4]
    strong = torch.from_numpy((ok & (conf > 25.0)).astype(np.float32)).to(dev)
    frac = F.avg_pool2d(strong[None, None], T // 8)[0, 0].cpu().numpy()   # per 256-px tile
    s0 = {k: torch.from_numpy(tifffile.imread(s0dir / f'{k}.tif').astype(np.float32)).to(dev).permute(2, 0, 1) for k in ('single', 'member1')}
    ref_arm = arms[0]

    def load_arm(arm):
        if arm.startswith('file:'):
            _, label, fa, fb = arm.split(':', 3)
            return label, torch.from_numpy(np.load(fa)).to(dev), torch.from_numpy(np.load(fb)).to(dev)
        return arm, torch.from_numpy(np.load(work / 'fused' / f'{arm}-odd.npy')).to(dev), torch.from_numpy(np.load(work / 'fused' / f'{arm}-even.npy')).to(dev)

    label0, a0, b0 = load_arm(ref_arm)
    pg = lowres(0.5 * (a0[1] + b0[1]))
    p_single = register(pg, lowres(s0['single'][1]), scale0=1.0104)
    p_m1 = register(pg, lowres(s0['member1'][1]), scale0=1.0104)
    print('S0 single located: scale %.5f shift (%.2f, %.2f) px' % (p_single[0], 8 * p_single[1], 8 * p_single[2]))
    print('S0 member1 located: scale %.5f shift (%.2f, %.2f) px' % (p_m1[0], 8 * p_m1[1], 8 * p_m1[2]))

    def s0_origin(p, x0, y0):
        cx, cy = (W - 1) / 2, (H - 1) / 2
        ux, uy = x0 + T / 2 - 0.5, y0 + T / 2 - 0.5
        sx = cx + p[0] * (ux - cx) + 8 * p[1]
        sy = cy + p[0] * (uy - cy) + 8 * p[2]
        return int(round(sx - T / 2 + 0.5)), int(round(sy - T / 2 + 0.5))

    tiles = []
    for tyi in range(2, frac.shape[0] - 2):
        for txi in range(2, frac.shape[1] - 2):
            if frac[tyi, txi] < 0.5:
                continue
            x0, y0 = txi * T, tyi * T
            o1, o2 = s0_origin(p_single, x0, y0), s0_origin(p_m1, x0, y0)
            if min(o1 + o2) < 0 or max(o1[0], o2[0]) + T > W or max(o1[1], o2[1]) + T > H:
                continue
            if float(s0['single'][:, o1[1]:o1[1] + T, o1[0]:o1[0] + T].max()) >= 60000 or float(s0['member1'][:, o2[1]:o2[1] + T, o2[0]:o2[0] + T].max()) >= 60000:
                continue
            tiles.append((x0, y0, o1, o2))
    print('tiles', len(tiles))
    (out / 'tiles.json').write_text(json.dumps(tiles) + '\n')
    win = hann2(T, dev)
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    nb = 50
    bins = torch.clamp((fr / 0.5 * nb).long(), max=nb * 2)

    def d5(f):
        return torch.where(f.abs() < 1e-9, torch.ones_like(f), torch.sin(5 * np.pi * f) / (5 * torch.sin(np.pi * f)))
    hp = (1 - d5(fx) * d5(fy)) ** 2
    band = ((fr >= 0.25) & (fr <= 0.40)).double()
    band_lo = ((fr >= 0.10) & (fr < 0.25)).double()

    def radial(x):
        return [float(x[bins == i].mean()) for i in range(nb)]

    def run(pairs):
        """pairs: per tile, (A [3,T,T], B [3,T,T]). Returns per-channel sums."""
        res = []
        for c in range(3):
            S = torch.zeros(T, T, dtype=torch.float64, device=dev)
            N = torch.zeros(T, T, dtype=torch.float64, device=dev)
            shifts = []
            for a, b in pairs:
                s, nz, sh = pair_spectra(a[c], b[c], win)
                S += s; N += nz
                shifts.append(sh)
            S /= len(pairs); N /= len(pairs)
            sh = np.array(shifts)
            res.append({'signal_band': float((S * band).sum()), 'signal_band_lo': float((S * band_lo).sum()),
                        'noise_hp': float((N * hp).sum()), 'noise_total': float(N.sum()),
                        'signal_radial': radial(S), 'noise_radial': radial(N),
                        'shift_rms_px': float(np.sqrt((sh ** 2).mean()))})
        return res

    report = {'tiles': len(tiles), 'tile_px': T, 'arms': {}, 's0_single_similarity': p_single, 's0_member1_similarity': p_m1}
    s0_pairs = [(s0['single'][:, o1[1]:o1[1] + T, o1[0]:o1[0] + T], s0['member1'][:, o2[1]:o2[1] + T, o2[0]:o2[0] + T]) for _, _, o1, o2 in tiles]
    rs0 = run(s0_pairs)
    report['arms']['S0'] = rs0
    s0_means = torch.stack([torch.stack([a.mean((1, 2)) for a, _ in s0_pairs]).median(0).values])[0]
    for arm in arms:
        label, a, b = (label0, a0, b0) if arm == ref_arm else load_arm(arm)
        pm = torch.stack([(0.5 * (a + b))[:, y0:y0 + T, x0:x0 + T].mean((1, 2)) for x0, y0, _, _ in tiles]).median(0).values
        gain = (s0_means / pm)
        pairs = [(a[:, y0:y0 + T, x0:x0 + T] * gain[:, None, None], b[:, y0:y0 + T, x0:x0 + T] * gain[:, None, None]) for x0, y0, _, _ in tiles]
        r = run(pairs)
        for c in range(3):
            r[c]['noise_hp_full'] = r[c]['noise_hp'] / 2
            r[c]['R1_amplitude_ratio'] = float(np.sqrt(max(r[c]['signal_band'], 0) / rs0[c]['signal_band']))
            r[c]['R_lo_amplitude_ratio'] = float(np.sqrt(max(r[c]['signal_band_lo'], 0) / rs0[c]['signal_band_lo']))
            r[c]['N1_noise_ratio'] = float(np.sqrt(max(r[c]['noise_hp_full'], 0) / rs0[c]['noise_hp']))
        report['arms'][label] = r
        report.setdefault('gain_to_s0', {})[label] = gain.tolist()
        print(f'{label:16s} ' + '  '.join(f'{"RGB"[c]}: R1 {r[c]["R1_amplitude_ratio"]:.3f} lo {r[c]["R_lo_amplitude_ratio"]:.3f} N1 {r[c]["N1_noise_ratio"]:.3f}' for c in range(3)), flush=True)
        if arm != ref_arm:
            del a, b
    print('S0 half-pair shift rms px', [round(rs0[c]['shift_rms_px'], 3) for c in range(3)])
    (out / 'evaluate.json').write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
