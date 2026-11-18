"""Restoration (brief.md step 5): one linear filter per channel that takes
the in-focus system OTF to a ringing-free target, capped by measured noise.

  python -X utf8 restore.py WORK_DIR EVAL_DIR ARM OUT_ARM [--ref-arm SEL]
         [--sigma-t 0.5] [--noise-match R] [--cutoff-scale 1.0] [--max-gain 8]

Everything the filter needs is measured on this stack, on evaluate.py's tiles
(EVAL_DIR/tiles.json), from independent halves (odd and even planes):

* signal(f) and noise(f) of ARM: cross- and auto-spectra as in evaluate.py.
* fusion transfer M(f), with --ref-arm: sqrt(signal_ARM / signal_REF), REF
  being the selector on the same depth map (its halves are single planes,
  so it carries the in-focus image without the fusion's blend). Blending
  neighbouring planes costs fine-detail amplitude (defocus and highlight
  walk); M is that cost, measured, so restoration can undo it on average.
* cutoff per channel, from REF's (else ARM's) signal spectrum: the model
  A f^-alpha [MTF_diff(f / fc) sinc(f)]^2 is fitted to the cube root of the
  signal over 0.20-0.49 cycles/px (grid over fc and alpha). Near the cutoff
  MTF^2 falls as (1 - f / fc)^3, so signal^(1/3) is linear in f and its
  zero crossing is a second, model-free estimate, reported beside it.
  No lens data is used. Channels' cutoffs must order as 1 / wavelength; that
  is the check that this is diffraction.
* OTF model H: circular-aperture diffraction at fc, times the photosite
  aperture sinc(fx) sinc(fy), times M. Nothing else: unmodelled blur is left
  in, which errs toward under-restoring.
* target T: Gaussian of --sigma-t photosites (a positive PSF: no ringing of
  its own).
* gain G = (T / H) S / (S + lambda N), S the fitted signal spectrum of ARM,
  N the full result's noise (halves' noise / 2), capped at --max-gain.
  lambda = 1 is the Wiener filter. With --noise-match R, lambda is solved so
  that the filtered result's high-pass noise (value minus 5x5 box mean) is R
  times the shipped stack's (EVAL_DIR/evaluate.json): "as noisy as shipped
  times R, as sharp as that allows".

--root applies the same filter to sqrt(value + 25 DN) and squares the
result. A linear filter with any gain above one has negative side lobes, and
next to a highlight fifty times brighter than its surroundings even a 1-2 %
lobe drives the surroundings below zero (measured: -259 DN beside a 10 000 DN
glint on a 200 DN ground). The square root compresses that ratio to about
seven, so the lobe stays a shallow dip, and it roughly equalises the photon
noise across levels. The cost is that the result is no longer a linear
filtering of the scene: low-contrast texture gets the designed response,
strong highlights get less of it on their dark side and more at their peak.

Photosites near a clipped sample keep their unrestored value (--no-protect
disables): a clipped highlight is not the linear image of the scene.

Writes WORK_DIR/fused/OUT_ARM-{all,odd,even}.npy (the same filter applied to
each, so the halves stay independent realisations) and
EVAL_DIR/restore-OUT_ARM.json. --cutoff-scale is the wrong-aperture placebo.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
import fp
import evaluate as ev

H, W, T = ev.H, ev.W, ev.T
ROOT_OFFSET = 25.0   # DN added before the square root of --root
PITCH_MM = 0.00376
WAVELENGTH_UM = [0.600, 0.535, 0.465]   # nominal channel centroids (not measured)


def arg(name, default, cast=float):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def mtf_diff(s):
    s = s.clamp(0, 1)
    return (2 / math.pi) * (torch.acos(s) - s * torch.sqrt(1 - s * s))


def mtf_diff_np(s):
    s = np.clip(s, 0, 1)
    return (2 / math.pi) * (np.arccos(s) - s * np.sqrt(1 - s * s))


def main():
    work, evd, arm, out_arm = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    sigma_t, match = arg('--sigma-t', 0.5), arg('--noise-match', 0.0)
    cscale, gmax = arg('--cutoff-scale', 1.0), arg('--max-gain', 8.0)
    ref_arm = arg('--ref-arm', None, str)
    dev = fp.DEV
    tiles = json.loads((evd / 'tiles.json').read_text())
    evj = json.loads((evd / 'evaluate.json').read_text())
    win = ev.hann2(T, dev)
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    nb = 72
    edges = torch.linspace(0, 0.72, nb + 1, device=dev, dtype=torch.float64)
    centres = (0.5 * (edges[1:] + edges[:-1])).cpu().numpy()
    bins = torch.bucketize(fr, edges) - 1
    cnt = np.array([int((bins == i).sum()) for i in range(nb)])

    def spectra(name):
        a = torch.from_numpy(np.load(work / 'fused' / f'{name}-odd.npy')).to(dev)
        b = torch.from_numpy(np.load(work / 'fused' / f'{name}-even.npy')).to(dev)
        out = []
        for c in range(3):
            S = torch.zeros(T, T, dtype=torch.float64, device=dev)
            N = torch.zeros(T, T, dtype=torch.float64, device=dev)
            for x0, y0, _, _ in tiles:
                s, nz, _ = ev.pair_spectra(a[c, y0:y0 + T, x0:x0 + T], b[c, y0:y0 + T, x0:x0 + T], win)
                S += s
                N += nz
            S /= len(tiles)
            N /= len(tiles)
            out.append((np.array([float(S[bins == i].mean()) if cnt[i] else 0.0 for i in range(nb)]),
                        np.array([float(N[bins == i].mean()) if cnt[i] else 0.0 for i in range(nb)])))
        del a, b
        return out

    sp = spectra(arm)
    sp_ref = spectra(ref_arm) if ref_arm else None
    report = {'arm': arm, 'ref_arm': ref_arm, 'sigma_t': sigma_t, 'noise_match': match, 'cutoff_scale': cscale, 'channels': []}
    params = []
    for c in range(3):
        Sr, Nh = sp[c]
        Nr = Nh / 2                                   # full result
        Sc = sp_ref[c][0] if sp_ref else Sr           # spectrum the cutoff is read from
        # Three-parameter fit in the cube-root domain (it handles the bins
        # where the model is zero): cbrt(S) = a [f^-alpha (MTF sinc)^2]^(1/3)
        # over 0.20-0.49 cycles/px (below the axis Nyquist, so nothing folded).
        fit = (centres > 0.20) & (centres < 0.49)
        cube = np.cbrt(np.maximum(Sc, 0))
        best = None
        for fc in np.arange(0.40, 0.9001, 0.004):
            base = (mtf_diff_np(centres[fit] / fc) * np.sinc(centres[fit])) ** 2
            for al in np.arange(0.4, 3.2001, 0.05):
                m = np.cbrt(centres[fit] ** (-al) * base)
                a_ = float((cube[fit] * m).sum() / max((m * m).sum(), 1e-30))
                res = float(np.sqrt(((cube[fit] - a_ * m) ** 2).mean()))
                if best is None or res < best[0]:
                    best = (res, fc, al)
        fc = float(best[1])
        lin = (centres > 0.75 * fc) & (centres < min(0.97 * fc, 0.49)) & (Sc > 0)
        fc_cube = float('nan')
        if lin.sum() >= 4:
            k = np.polyfit(centres[lin], cube[lin], 1)
            fc_cube = float(-k[1] / k[0])
        fcm = fc * cscale
        # fusion transfer: smooth radial profile of sqrt(S_arm / S_ref)
        M = np.ones(nb)
        if sp_ref:
            ok = (Sr > 0) & (Sc > 0) & (centres > 0.02) & (centres < 0.47)
            ratio = np.sqrt(Sr[ok] / Sc[ok])
            k = np.polyfit(centres[ok], ratio, 3, w=np.sqrt(cnt[ok]))
            M = np.clip(np.polyval(k, np.minimum(centres, 0.47)), 0.3, 1.15)
            M[centres < 0.02] = np.polyval(k, 0.02)
        # the arm's own signal spectrum model, for the Wiener factor
        Hr = mtf_diff_np(centres / fcm) * np.sinc(centres) * M
        good = (centres > 0.03) & (centres < 0.47) & (Sr > 0) & (Hr > 1e-3)
        A2 = np.polyfit(np.log(centres[good]), np.log(Sr[good] / Hr[good] ** 2), 1)
        ch = {'cutoff_cyc_px': float(fc), 'cutoff_cube_root_cyc_px': fc_cube, 'cutoff_cyc_mm': float(fc / PITCH_MM),
              'n_eff_at_nominal_wavelength': float(1 / (WAVELENGTH_UM[c] * 1e-3 * fc / PITCH_MM)), 'model_fit_rms_log': best[0],
              'object_slope': float(-A2[0]), 'fusion_transfer': {'freq': [0.1, 0.2, 0.3, 0.4], 'M': [float(np.interp(v, centres, M)) for v in (0.1, 0.2, 0.3, 0.4)]}}
        report['channels'].append(ch)
        params.append((fcm, float(-A2[0]), float(A2[1]), Nr, M))
        print(f'{"RGB"[c]}: cutoff {fc:.3f} cyc/px (cube-root estimate {fc_cube:.3f}) = {fc / PITCH_MM:.0f} cyc/mm -> N_eff {ch["n_eff_at_nominal_wavelength"]:.1f} at {WAVELENGTH_UM[c]} um; '
              f'fusion transfer at 0.2/0.3/0.4: ' + '/'.join(f'{v:.2f}' for v in ch['fusion_transfer']['M'][1:]), flush=True)

    PAD = 64
    Hp, Wp = H + 2 * PAD, W + 2 * PAD
    FY = torch.fft.fftfreq(Hp, device=dev, dtype=torch.float32)[:, None]
    FX = torch.fft.rfftfreq(Wp, device=dev, dtype=torch.float32)[None, :]
    FR = torch.sqrt(FX * FX + FY * FY)

    def d5(f):
        return torch.where(f.abs() < 1e-7, torch.ones_like(f), torch.sin(5 * math.pi * f) / (5 * torch.sin(math.pi * f)))
    HP = (1 - d5(FX) * d5(FY)) ** 2
    weight = torch.where((FX > 0) & (FX < 0.5), 2.0, 1.0)   # rfft half-plane counted twice

    def radial(v):
        return torch.from_numpy(np.interp(FR.cpu().numpy().ravel(), centres, v).astype(np.float32)).to(dev).reshape(FR.shape)

    gains = evj.get('gain_to_s0', {}).get(arm)
    filters = []
    for c in range(3):
        fcm, alpha, logA, Nr, M = params[c]
        Hf = mtf_diff(FR / fcm) * torch.sinc(FX) * torch.sinc(FY) * radial(M)
        Sf = math.exp(logA) * FR.clamp(min=1e-3) ** (-alpha) * Hf * Hf
        Nf = radial(np.maximum(Nr, 1e-12))
        Tf = torch.exp(-2 * math.pi ** 2 * sigma_t ** 2 * FR * FR)

        def gain(lam):
            g = (Tf / Hf.clamp(min=1e-4)) * Sf / (Sf + lam * Nf)
            g = torch.where(Hf > 1e-4, g, torch.zeros_like(g)).clamp(max=gmax)
            g[0, 0] = 1.0
            return g

        def hp_noise(g):   # predicted high-pass noise variance per pixel of the filtered full result
            return float((g * g * Nf * HP * weight).sum() / weight.sum())
        lam = 1.0
        base = float((Nf * HP * weight).sum() / weight.sum())
        ch = report['channels'][c]
        if match > 0 and gains is not None:
            target = match ** 2 * evj['arms']['S0'][c]['noise_hp'] / gains[c] ** 2
            lo, hi = 1e-6, 1e6
            for _ in range(70):
                mid = math.sqrt(lo * hi)
                if hp_noise(gain(mid)) > target:
                    lo = mid
                else:
                    hi = mid
            lam = math.sqrt(lo * hi)
            ch['noise_match_reached'] = bool(hp_noise(gain(lam)) > 0.98 * target)
        g = gain(lam)
        ch['lambda'] = lam
        ch['predicted_hp_noise_gain'] = math.sqrt(hp_noise(g) / base)
        prof = [0.1, 0.2, 0.3, 0.4, 0.45]
        ix = [int(round(v * Wp)) for v in prof]
        ch['profile'] = {'freq': prof, 'gain': [float(g[0, i]) for i in ix], 'system_mtf': [float(Hf[0, i]) for i in ix],
                         'restored_mtf': [float(g[0, i] * Hf[0, i]) for i in ix], 'target': [float(Tf[0, i]) for i in ix]}
        print(f'{"RGB"[c]}: lambda {lam:.3g}; high-pass noise x{ch["predicted_hp_noise_gain"]:.2f}; MTF system -> restored (target) at '
              + '  '.join(f'{v}: {float(Hf[0, i]):.2f} -> {float(g[0, i] * Hf[0, i]):.2f} ({float(Tf[0, i]):.2f})' for v, i in zip(prof[1:], ix[1:])), flush=True)
        filters.append(g)
    out = work / 'fused'
    root = '--root' in sys.argv
    report['root_domain'] = root
    # Highlight protection: a clipped highlight is not the linear image of the
    # scene (its top is cut off), so any gain above one rings around it. Near
    # clipped photosites the unrestored value is kept, with a smooth hand-over.
    protect = None
    if '--no-protect' not in sys.argv:
        full = torch.from_numpy(np.load(out / f'{arm}-all.npy')).to(dev)
        clipped = (full.max(0).values > 0.80 * (15360.0 - 512.0)).float()
        if ref_arm:   # the selector keeps single-plane levels, which the blend can pull below the threshold
            sel_full = torch.from_numpy(np.load(out / f'{ref_arm}-all.npy')).to(dev)
            clipped = torch.maximum(clipped, (sel_full.max(0).values > 0.80 * (15360.0 - 512.0)).float())
            del sel_full
        near = (F.max_pool2d(clipped[None, None], 21, 1, 10)[0, 0] > 0).float()
        protect = 1.0 - fp.gauss(near, 4.0).clamp(0, 1)
        report['protected_fraction'] = float(1 - protect.mean())
        print('highlight protection covers %.2f%% of the frame' % (100 * report['protected_fraction']))
        del full, clipped, near
    for name in ('all', 'odd', 'even'):
        x = torch.from_numpy(np.load(out / f'{arm}-{name}.npy')).to(dev)
        y = torch.empty_like(x)
        for c in range(3):
            xp = F.pad(x[c][None, None], (PAD, PAD, PAD, PAD), mode='reflect')[0, 0]
            if root:
                xp = torch.sqrt(xp.clamp(min=0) + ROOT_OFFSET)
            y[c] = torch.fft.irfft2(torch.fft.rfft2(xp) * filters[c], s=(Hp, Wp))[PAD:-PAD, PAD:-PAD]
            if root:
                y[c] = y[c].clamp(min=0) ** 2 - ROOT_OFFSET
            if protect is not None:
                y[c] = x[c] + protect * (y[c] - x[c])
            del xp
        np.save(out / f'{out_arm}-{name}.npy', y.cpu().numpy())
        del x, y
    # Control C1: the same filters applied to other images (the shipped
    # stacks), linear, unprotected, written as float TIFFs: SRC DST pairs.
    if '--apply-to-tiff' in sys.argv:
        import tifffile
        rest = sys.argv[sys.argv.index('--apply-to-tiff') + 1:]
        for src, dst in zip(rest[0::2], rest[1::2]):
            x = torch.from_numpy(tifffile.imread(src).astype(np.float32)).to(dev).permute(2, 0, 1)
            y = torch.empty_like(x)
            for c in range(3):
                xp = F.pad(x[c][None, None], (PAD, PAD, PAD, PAD), mode='reflect')[0, 0]
                y[c] = torch.fft.irfft2(torch.fft.rfft2(xp) * filters[c], s=(Hp, Wp))[PAD:-PAD, PAD:-PAD]
                del xp
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            tifffile.imwrite(dst, y.permute(1, 2, 0).cpu().numpy(), photometric='rgb')
            print('filtered', src, '->', dst)
            del x, y
    (evd / f'restore-{out_arm}.json').write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
