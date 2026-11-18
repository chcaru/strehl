"""R3 and R4: what the frames around a point's focus hold, from a run of
single-group renders (series-frames.ps1: raw carry, no restoration, profile
lateral colour only; every frame already gathered onto the output grid by
the product's alignment).

  python -X utf8 series-focus.py OUT_PREFIX SERIES_DIR FIRST LAST [--tile 256] [--stride 128] [--half 8]

Tiles. Per frame, tile energy of green minus its 2 px Gaussian. A tile's
focus plane is the parabola-refined peak of that energy over frames. Kept:
peak at least `half` frames from both ends of the series, peak energy at
least 4x the smallest over the series (a clear focus peak), level above the
15th percentile, no clipping. k0 = the nearest frame to the peak; the tile's
window is k0 - half .. k0 + half.

Registration (R3). Each window frame's displacement against frame k0 is the
weighted least-squares phase ramp of the green cross-spectrum over 0.03-0.30
cycles/px (channel-shift.py's estimator). Reported by lag: rms over tiles;
the rms left after a similarity (shift, scale, rotation) fitted over the
tiles that share the same frame pair; and how far a planted shift is
recovered (control).

Pair products. With every window frame registered to k0 (or not: the
unregistered arm), P[k, l] = sum over a radial band of Re(F_k conj F_l) for
each channel. Noise is independent between frames, so off-diagonal entries
are noise-free: P[k, l] = sum H_k H_l S. The neighbour product
q[k + 1/2] = P[k, k + 1] traces the through-focus transfer squared.

R4a  each channel's focus (centroid of q above half its peak) against
     green's, and what red and blue hold at green's focus against their own
     peak, by band.
R4b  frames' worth of signal-to-noise on offer: sum q / max q by band
     (the matched-filter bound in units of the best frame, for equal noise
     per frame; the window truncates it at 2 half + 1); the best frame's own
     signal-to-noise (peak q over the diagonal's excess over its
     neighbour-product estimate).
R4c  what a matched-weight average of the window keeps of the registered
     signal when the frames are not registered to each other
     (sum_{k != l} w_k w_l P_unregistered / the same registered).
R4d  coherence of red (blue) with green in the fine band: both at green's
     focus frame, and each at its own focus frame, after a radial
     displacement model fitted over tiles in that band; placebo: tiles'
     displacements rolled.

Fooled by: tiles spanning several depths (broad q; reported widths are upper
bounds); registration error far from focus (the window stops at +-half);
weak red or blue texture (few tiles carry the colour statistics).
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp

BANDS = [(0.03, 0.06), (0.06, 0.10), (0.10, 0.16), (0.16, 0.24), (0.24, 0.32), (0.32, 0.42), (0.42, 0.50)]


def arg(name, default=None):
    for i, tok in enumerate(sys.argv):
        if tok == name:
            return sys.argv[i + 1]
        if tok.startswith(name + '='):
            return tok.split('=', 1)[1]
    return default


def main():
    prefix, sdir, first, last = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    T, S, half = int(arg('--tile', '256')), int(arg('--stride', '128')), int(arg('--half', '8'))
    dev = fp.DEV
    ks = list(range(first, last + 1))
    nk = len(ks)

    def load(k):
        return torch.from_numpy(tifffile.imread(sdir / f'one-{k}.tif').astype(np.float32)).to(dev).permute(2, 0, 1)

    # pass 1: focus plane per tile
    E, L, C = [], [], []
    for k in ks:
        img = load(k)
        g = img[1]
        hp = (g - fp.gauss(g, 2.0)) ** 2
        E.append(F.avg_pool2d(hp[None, None], T, S)[0, 0])
        L.append(F.avg_pool2d(g[None, None], T, S)[0, 0])
        C.append(F.avg_pool2d((img.max(0).values > 60000).float()[None, None], T, S)[0, 0])
        H, W = g.shape
        del img
    E, L, C = torch.stack(E), torch.stack(L), torch.stack(C)
    ny, nx = E.shape[1:]
    pk = E.argmax(0)
    i0 = pk.clamp(1, nk - 2)
    em, e0, ep = E.gather(0, (i0 - 1)[None])[0], E.gather(0, i0[None])[0], E.gather(0, (i0 + 1)[None])[0]
    d = em - 2 * e0 + ep
    kf = i0.float() + torch.where(d.abs() > 1e-12, 0.5 * (em - ep) / d, torch.zeros_like(d)).clamp(-1, 1)
    lvl = L.mean(0)
    ok = (pk >= half) & (pk <= nk - 1 - half) & (E.max(0).values >= 4 * E.min(0).values) & (lvl > torch.quantile(lvl.flatten(), 0.15)) & (C.max(0).values < 0.002)
    ok[0], ok[-1], ok[:, 0], ok[:, -1] = False, False, False, False
    sel = torch.nonzero(ok).cpu().numpy()
    n = len(sel)
    k0 = pk[ok].cpu().numpy()                    # index into ks
    kfp = kf[ok].cpu().numpy()
    print(f'{n} tiles of {ny * nx} with a focus peak between frames {ks[half]} and {ks[nk - 1 - half]}; peak frame histogram: '
          + ' '.join(f'{ks[i]}:{int((k0 == i).sum())}' for i in range(half, nk - half)), flush=True)
    # pass 2: tile stacks around each tile's own k0
    nw = 2 * half + 1
    stack = torch.zeros(n, nw, 3, T, T, device='cpu', dtype=torch.float32)
    for ki, k in enumerate(ks):
        img = load(k)
        for i, (ty, tx) in enumerate(sel):
            j = ki - (k0[i] - half)
            if 0 <= j < nw:
                stack[i, j] = img[:, ty * S:ty * S + T, tx * S:tx * S + T].cpu()
        del img
    cx, cy = (W - 1) / 2, (H - 1) / 2
    pos = np.array([[tx * S + T / 2 - cx, ty * S + T / 2 - cy] for ty, tx in sel])
    win = torch.hann_window(T, periodic=True, device=dev, dtype=torch.float32)
    win = win[:, None] * win[None, :]
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float32)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float32)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    fitm = ((fr >= 0.03) & (fr <= 0.30)).float()
    masks = torch.stack([((fr >= lo) & (fr < hi)).float() for lo, hi in BANDS])
    nb = len(BANDS)

    def shift_of(X, fit):
        r = torch.fft.ifft2(X * fit / (X.abs() + 1e-12 * X.abs().mean())).real
        idx = int(r.argmax())
        py, px = idx // T, idx % T
        s = torch.tensor([float(px - T if px > T / 2 else px), float(py - T if py > T / 2 else py)], device=dev)
        for _ in range(5):
            Y = X * torch.exp(2j * np.pi * (fx * s[0] + fy * s[1]))
            wgt = Y.abs() * fit
            ph = torch.angle(Y)
            a = torch.stack([(wgt * fx * fx).sum(), (wgt * fx * fy).sum(), (wgt * fy * fy).sum()])
            b = torch.stack([(wgt * fx * ph).sum(), (wgt * fy * ph).sum()])
            det = a[0] * a[2] - a[1] * a[1]
            s = s + torch.stack([-(a[2] * b[0] - a[1] * b[1]) / det, -(a[0] * b[1] - a[1] * b[0]) / det]) / (2 * np.pi)
        return s

    shifts = np.zeros((n, nw, 2), np.float32)
    Preg = np.zeros((n, 3, nb, nw, nw), np.float64)
    Pun = np.zeros((n, 3, nb, nw, nw), np.float64)
    fine = (fr >= 0.24) & (fr <= 0.42)
    finef = fine.float()
    # R4d accumulators: cross-spectra tiles (fine band only, kept as complex fields per tile)
    Xsame = {c: [] for c in (0, 2)}
    Xown = {c: [] for c in (0, 2)}
    Psame = {c: [] for c in (0, 2)}
    Pown = {c: [] for c in (0, 2)}
    own_frame = {c: [] for c in (0, 2)}
    planted = []
    norm = T * T * float((win * win).sum())
    for i in range(n):
        x = stack[i].to(dev)
        x = x - x.mean((-2, -1), keepdim=True)
        Fw = torch.fft.fft2(x * win)                          # [nw, 3, T, T]
        ramps = []
        for j in range(nw):
            if j == half:
                s = torch.zeros(2, device=dev)
            else:
                s = shift_of(Fw[j, 1] * Fw[half, 1].conj(), fitm)
            shifts[i, j] = s.cpu().numpy()
            ramps.append(torch.exp(2j * np.pi * (fx * s[0] + fy * s[1])))
        if i < 40:                                            # control: a planted shift of (0.30, -0.20) px on frame k0 + 1
            Fp = Fw[half + 1, 1] * torch.exp(-2j * np.pi * (fx * 0.30 + fy * -0.20))
            sp = shift_of(Fp * Fw[half, 1].conj(), fitm).cpu().numpy()
            planted.append(sp - shifts[i, half + 1])
        Fr = Fw * torch.stack(ramps)[:, None]
        for c in range(3):
            for b in range(nb):
                m = masks[b].flatten() > 0
                A = Fr[:, c].reshape(nw, -1)[:, m]
                Preg[i, c, b] = (A @ A.conj().T).real.double().cpu().numpy() / norm
                A = Fw[:, c].reshape(nw, -1)[:, m]
                Pun[i, c, b] = (A @ A.conj().T).real.double().cpu().numpy() / norm
        # R4d: red and blue against green, fine band
        for c in (0, 2):
            q = np.array([Preg[i, c, 4:6, j, j + 1].sum() for j in range(nw - 1)])
            jo = int(np.clip(np.argmax(q[2:-2]) + 2, 1, nw - 2))   # own-focus frame index (lower of the pair)
            own_frame[c].append(jo - half)
            Xsame[c].append((Fr[half, c] * Fr[half, 1].conj() * finef).cpu())
            Xown[c].append((Fr[jo, c] * Fr[half + (1 if jo == half else 0), 1].conj() * finef).cpu())
            g_sig = float(np.sqrt(max(Preg[i, 1, 4:6, half - 1, half].sum() * Preg[i, 1, 4:6, half, half + 1].sum(), 0)))
            c_same = float(np.sqrt(max(Preg[i, c, 4:6, half - 1, half].sum() * Preg[i, c, 4:6, half, half + 1].sum(), 0)))
            c_own = float(np.sqrt(max(Preg[i, c, 4:6, jo - 1, jo].sum() * Preg[i, c, 4:6, jo, jo + 1].sum(), 0)))
            Psame[c].append((c_same, g_sig))
            Pown[c].append((c_own, g_sig))
        del x, Fw, Fr
        if i % 50 == 0:
            print(f'tile {i} / {n}', flush=True)
    report = {'series': [first, last], 'tiles': int(n), 'tile': T, 'stride': S, 'half': half, 'bands': BANDS}
    planted = np.array(planted)
    report['planted_shift_error_px'] = {'mean': planted.mean(0).tolist(), 'target': [0.30, -0.20], 'sd': planted.std(0).tolist()}
    print(f'control: planted (0.30, -0.20) px recovered as ({planted[:, 0].mean():+.3f}, {planted[:, 1].mean():+.3f}), sd ({planted[:, 0].std():.3f}, {planted[:, 1].std():.3f})')

    # ---- R3: registration between gathered frames ----
    lags = {}
    for lag in range(-half, half + 1):
        if lag == 0:
            continue
        j = half + lag
        s = shifts[:, j]
        raw = float(np.sqrt((s ** 2).sum(1).mean()))
        left2, cnt, scales, rots = 0.0, 0, [], []
        for k in np.unique(k0):
            m = k0 == k
            if m.sum() < 15:
                continue
            A = np.zeros((2 * m.sum(), 4))
            A[0::2, 0] = 1
            A[1::2, 1] = 1
            A[0::2, 2], A[1::2, 2] = pos[m, 0], pos[m, 1]
            A[0::2, 3], A[1::2, 3] = -pos[m, 1], pos[m, 0]
            sol, *_ = np.linalg.lstsq(A, s[m].reshape(-1), rcond=None)
            res = (s[m].reshape(-1) - A @ sol).reshape(-1, 2)
            left2 += float((res ** 2).sum())
            cnt += int(m.sum())
            scales.append(sol[2] * 1e6)
            rots.append(sol[3] * 1e6)
        lags[lag] = {'rms_px': raw, 'rms_after_similarity_px': float(np.sqrt(left2 / max(cnt, 1))) if cnt else None, 'tiles_in_fits': cnt,
                     'scale_ppm_sd': float(np.std(scales)) if scales else None, 'scale_ppm_mean': float(np.mean(scales)) if scales else None,
                     'rotation_urad_sd': float(np.std(rots)) if rots else None}
    report['registration'] = lags
    print('R3 displacement against the focus frame, rms px by lag (raw / after a per-pair similarity):')
    print('   ' + '  '.join(f'{lag:+d}: {v["rms_px"]:.3f}/{v["rms_after_similarity_px"]:.3f}' if v['rms_after_similarity_px'] is not None else f'{lag:+d}: {v["rms_px"]:.3f}' for lag, v in lags.items()))
    print('   fitted per-pair scale, ppm mean (sd): ' + '  '.join(f'{lag:+d}: {v["scale_ppm_mean"]:+.0f} ({v["scale_ppm_sd"]:.0f})' for lag, v in lags.items() if v['scale_ppm_mean'] is not None))

    # ---- R4a / R4b / R4c ----
    def q_of(P):
        return np.stack([P[..., j, j + 1] for j in range(nw - 1)], -1)   # [..., nw - 1] at k0 - half + j + 1/2

    q = q_of(Preg)                                   # [n, 3, nb, nw - 1]
    xs = np.arange(nw - 1) - half + 0.5
    r4 = {'bands': {}}
    for b, (lo, hi) in enumerate(BANDS):
        row = {}
        qq = q[:, :, b]                               # [n, 3, nw - 1]
        qm = np.median(qq / np.maximum(qq[:, 1:2].max(-1, keepdims=True), 1e-30), 0)       # per channel, normalised to green's peak
        # focus centroids above half of own peak, per tile
        cen = np.zeros((n, 3))
        for c in range(3):
            v = np.clip(qq[:, c], 0, None)
            wgt = np.where(v >= 0.5 * v.max(-1, keepdims=True), v, 0)
            cen[:, c] = (wgt * xs).sum(-1) / np.maximum(wgt.sum(-1), 1e-30)
        avail = np.clip(qq, 0, None).sum(-1) / np.maximum(qq.max(-1), 1e-30)               # [n, 3]
        # value at green's focus pair against own peak: the pairs straddling k0 are j = half - 1 and half
        at_green = 0.5 * (qq[:, :, half - 1] + qq[:, :, half]) / np.maximum(qq.max(-1), 1e-30)
        diag = np.stack([Preg[:, :, b, j, j] for j in range(1, nw - 1)], -1)
        sig_d = np.sqrt(np.clip(qq[:, :, :-1] * qq[:, :, 1:], 0, None))
        noise = np.median(diag - sig_d, -1)                                                 # [n, 3]
        snr1 = qq.max(-1) / np.maximum(noise, 1e-30)
        # matched weights from green's q, registered against unregistered
        keep = np.zeros((n, 3))
        for c in range(3):
            h = np.sqrt(np.clip(0.5 * (np.pad(qq[:, c], ((0, 0), (1, 0)))[:, :nw] + np.pad(qq[:, c], ((0, 0), (0, 1)))[:, :nw]), 0, None))
            Wm = h[:, :, None] * h[:, None, :]
            off = 1 - np.eye(nw)
            keep[:, c] = (Wm * Pun[:, c, b] * off).sum((1, 2)) / np.maximum((Wm * Preg[:, c, b] * off).sum((1, 2)), 1e-30)
        for c, name in enumerate('RGB'):
            row[name] = {'focus_offset_from_green_frames_median': float(np.median(cen[:, c] - cen[:, 1])),
                         'focus_offset_iqr': [float(v) for v in np.percentile(cen[:, c] - cen[:, 1], [25, 75])],
                         'at_green_focus_over_own_peak_median': float(np.median(at_green[:, c])),
                         'frames_on_offer_median': float(np.median(avail[:, c])),
                         'best_frame_snr_median': float(np.median(snr1[:, c])),
                         'unregistered_keeps_median': float(np.median(keep[:, c])),
                         'q_median_profile': qm[c].tolist()}
        r4['bands'][f'{lo}-{hi}'] = row
        print(f'band {lo:.2f}-{hi:.2f}: ' + ';  '.join(
            f'{name}: focus {row[name]["focus_offset_from_green_frames_median"]:+.2f} fr, at green focus {row[name]["at_green_focus_over_own_peak_median"]:.3f} of own peak, '
            f'{row[name]["frames_on_offer_median"]:.1f} frames on offer, best-frame S/N {row[name]["best_frame_snr_median"]:.1f}, unregistered keeps {row[name]["unregistered_keeps_median"]:.3f}'
            for name in 'RGB'))
    report['through_focus'] = r4

    # ---- R4d: fine-band coherence with green ----
    r4d = {}

    def radial_fit(Sx):
        A = np.zeros((2 * n, 3))
        A[0::2, 0] = 1
        A[1::2, 1] = 1
        A[0::2, 2], A[1::2, 2] = pos[:, 0], pos[:, 1]
        sol, *_ = np.linalg.lstsq(A, Sx.reshape(-1), rcond=None)
        return sol, (A @ sol).reshape(-1, 2)

    for c, name in ((0, 'R'), (2, 'B')):
        rows = {}
        for label, Xs, Ps in (('at green focus', Xsame[c], Psame[c]), ('at own focus', Xown[c], Pown[c])):
            Sx = np.array([shift_of(X.to(dev), finef).cpu().numpy() for X in Xs])
            sol, model = radial_fit(Sx)
            den = sum(np.sqrt(p[0] * p[1]) for p in Ps) * norm

            def coh(sh):
                acc = 0.0
                for X, s in zip(Xs, sh):
                    X = X.to(dev)
                    acc += float((X * torch.exp(2j * np.pi * (fx * float(s[0]) + fy * float(s[1])))).real.sum())
                return acc / max(den, 1e-30)

            rows[label] = {'fit_t': [float(sol[0]), float(sol[1])], 'fit_eps_ppm': float(sol[2] * 1e6),
                           'rms_px': float(np.sqrt((Sx ** 2).sum(1).mean())), 'rms_after_model_px': float(np.sqrt(((Sx - model) ** 2).sum(1).mean())),
                           'coherence_none': coh(np.zeros_like(Sx)), 'coherence_model': coh(model), 'coherence_own': coh(Sx),
                           'coherence_placebo': coh(np.roll(Sx, 7, 0)),
                           'channel_over_green_signal': float(np.median([p[0] / max(p[1], 1e-30) for p in Ps]))}
            v = rows[label]
            print(f'{name} against green, fine band, {label}: displacement fit t=({v["fit_t"][0]:+.3f}, {v["fit_t"][1]:+.3f}) eps={v["fit_eps_ppm"]:+.0f} ppm, '
                  f'rms {v["rms_px"]:.3f} -> {v["rms_after_model_px"]:.3f}; coherence none {v["coherence_none"]:.3f}, model {v["coherence_model"]:.3f}, '
                  f'own {v["coherence_own"]:.3f}, placebo {v["coherence_placebo"]:.3f}; channel/green fine signal amplitude {np.sqrt(v["channel_over_green_signal"]):.3f}')
        rows['own_focus_frame_offset_median'] = float(np.median(own_frame[c]))
        r4d[name] = rows
    report['fine_coherence'] = r4d
    Path(prefix + '.json').write_text(json.dumps(report, indent=1) + '\n')
    np.savez_compressed(prefix + '.npz', Preg=Preg.astype(np.float32), Pun=Pun.astype(np.float32), shifts=shifts, pos=pos, k0=np.array([ks[i] for i in k0]), kf=kfp,
                        sel=sel, bands=np.array(BANDS))


if __name__ == '__main__':
    with torch.no_grad():
        main()
