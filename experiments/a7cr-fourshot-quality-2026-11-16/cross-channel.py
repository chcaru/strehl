"""Q1: do red and blue carry fine detail the output discards, and does a joint
three-channel filter beat green alone?

  python -X utf8 cross-channel.py OUT.json ODD.tif EVEN.tif [--shift-placebo]

ODD/EVEN: odd- and even-frame half-stacks of one capture, linear camera RGB,
colour carried and NOT chroma-smoothed (`STREHL_CARRY_RGB=raw`).

Tiles as compare-colour.py (256 px, top 30 % green high-pass energy, under
1 % near clipping), split into a design set and a validation set on a
checkerboard of the tile grid. Per tile the halves' relative shift is taken
from green and removed from every channel.

Design set, per radial bin (0.01 cycles/px): the 3x3 signal matrix
S = sym Re <A_c conj(B_d)> (what the halves share) and the noise matrix
N = <A_c conj(A_d) + B_c conj(B_d)> / 2 - S.

Validation set, per estimator W (3x3 per bin, x_hat = W y):
  mse_c = < |(W A)_c - B_c|^2 > - N_cc(validation)
the mean squared error of the estimate of channel c's noise-free content,
because B's noise is independent of A's. Reported as an equivalent
signal-to-noise power S_cc / mse_c - 1 (for a scalar Wiener filter this is
S/N exactly, which is the instrument's own check) and integrated over bands.

Estimators:
  raw       W = I
  own       per-channel Wiener (no borrowing)
  borrow    the shipped step: green as is; red, blue = green + Gaussian
            (1 px) of their difference from green
  joint     W = S (S + N)^-1, all three channels
With --shift-placebo red and blue are rolled 8 px against green in both
halves before anything else: the cross-channel terms must vanish and joint
must fall to own.

Fooled by: fixed pattern both halves share reads as signal (it is
independent between channels at a site, so it cannot fake cross-channel
coherence); one near-neutral subject.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp
import evaluate as ev

T = ev.T
BIN = 0.01
NB = 72


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    placebo = '--shift-placebo' in sys.argv
    out, fa, fb = Path(args[0]), args[1], args[2]
    dev = fp.DEV

    def load(f):
        return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)

    A, B = load(fa), load(fb)
    if placebo:
        for im in (A, B):
            im[0] = torch.roll(im[0], (8, 8), (0, 1))
            im[2] = torch.roll(im[2], (-8, 8), (0, 1))
    _, H, W = A.shape
    g = A[1]
    hpe = (g - fp.gauss(g, 2.0)) ** 2
    ty, tx = H // T, W // T
    e = hpe[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
    m = g[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
    fg = m > np.percentile(m, 15)
    sel = (e >= np.percentile(e[fg], 70)) & fg
    sel[:1], sel[-1:], sel[:, :1], sel[:, -1:] = False, False, False, False
    clip = (A.max(0).values > 60000) | (B.max(0).values > 60000)
    clipt = torch.nn.functional.avg_pool2d(clip.float()[None, None], T, T)[0, 0].cpu().numpy() > 0.01
    sel &= ~clipt[:ty, :tx]
    tiles = [(int(x), int(y)) for y, x in np.argwhere(sel)]
    design = [t for t in tiles if (t[0] + t[1]) % 2 == 0]
    valid = [t for t in tiles if (t[0] + t[1]) % 2 == 1]
    print(f'tiles {len(tiles)}: design {len(design)}, validation {len(valid)}')

    win = ev.hann2(T, dev)
    norm = T * T * float((win * win).sum())
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    bins = torch.clamp((fr / BIN).long(), max=NB - 1)
    count = torch.bincount(bins.flatten(), minlength=NB).double()
    centres = (np.arange(NB) + 0.5) * BIN

    def radial(x):
        """[.., T, T] complex or real -> [.., NB] mean over each radial bin."""
        flat = x.reshape(*x.shape[:-2], -1)
        idx = bins.flatten().expand(flat.shape)
        acc = torch.zeros(*x.shape[:-2], NB, dtype=flat.dtype, device=dev)
        acc.scatter_add_(-1, idx, flat)
        return acc / count.clamp(min=1)

    def tile_ffts(x, y):
        a = A[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        b = B[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        a = a - a.mean((1, 2), keepdim=True)
        b = b - b.mean((1, 2), keepdim=True)
        FA, FB = torch.fft.fft2(a * win), torch.fft.fft2(b * win)
        _, _, (sx, sy) = ev.pair_spectra(a[1], b[1], win)
        FB = FB * torch.exp(2j * np.pi * (fx * sx + fy * sy))
        return FA, FB

    def spectra(ts):
        S = torch.zeros(3, 3, NB, dtype=torch.float64, device=dev)
        N = torch.zeros_like(S)
        for x, y in ts:
            FA, FB = tile_ffts(x, y)
            cross = FA[:, None] * FB[None, :].conj()          # [c, d, T, T]
            s = radial(0.5 * (cross + cross.transpose(0, 1).conj()).real) / norm
            auto = 0.5 * (FA[:, None] * FA[None, :].conj() + FB[:, None] * FB[None, :].conj()).real
            S += s
            N += radial(auto) / norm - s
        return S / len(ts), N / len(ts)

    Sd, Nd = spectra(design)
    Sv, Nv = spectra(valid)

    def psd(mat):
        """Nearest positive semi-definite matrix per bin: [3, 3, NB] -> same."""
        m = mat.permute(2, 0, 1)
        w, v = torch.linalg.eigh(0.5 * (m + m.transpose(1, 2)))
        return (v * w.clamp(min=0)[:, None, :]) @ v.transpose(1, 2)

    Sp = psd(Sd)                                     # [NB, 3, 3]
    Nm = Nd.permute(2, 0, 1)
    Ndiag = torch.diag_embed(torch.diagonal(Nm, dim1=1, dim2=2).clamp(min=1e-30))
    eye = torch.eye(3, dtype=torch.float64, device=dev).expand(NB, 3, 3)
    f = torch.tensor(centres, dtype=torch.float64, device=dev)
    gsm = torch.exp(-2 * np.pi ** 2 * 1.0 ** 2 * f * f)        # 1 px Gaussian
    own = torch.diag_embed(torch.diagonal(Sp, dim1=1, dim2=2) / (torch.diagonal(Sp, dim1=1, dim2=2) + torch.diagonal(Ndiag, dim1=1, dim2=2)))
    borrow = torch.zeros(NB, 3, 3, dtype=torch.float64, device=dev)
    borrow[:, 1, 1] = 1
    for c in (0, 2):
        borrow[:, c, c] = gsm
        borrow[:, c, 1] = 1 - gsm
    joint = Sp @ torch.linalg.inv(Sp + Ndiag)
    # What the same design predicts for the full stack (half the noise).
    joint_full = Sp @ torch.linalg.inv(Sp + 0.5 * Ndiag)
    estimators = {'raw': eye, 'own': own, 'borrow': borrow, 'joint': joint}

    mse = {k: torch.zeros(3, NB, dtype=torch.float64, device=dev) for k in estimators}
    for x, y in valid:
        FA, FB = tile_ffts(x, y)
        for k, Wm in estimators.items():
            Wf = Wm[bins]                                        # [T, T, 3, 3]
            for src, ref in ((FA, FB), (FB, FA)):
                est = torch.einsum('yxcd,dyx->cyx', Wf.to(torch.complex128), src)
                mse[k] += 0.5 * radial((est - ref).abs() ** 2) / norm
    Nvd = torch.diagonal(Nv.permute(2, 0, 1), dim1=1, dim2=2).T      # [3, NB]
    Svd = torch.diagonal(Sv.permute(2, 0, 1), dim1=1, dim2=2).T
    for k in mse:
        mse[k] = mse[k] / len(valid) - Nvd

    bands = {'0.10-0.25': (0.10, 0.25), '0.25-0.40': (0.25, 0.40), '0.40-0.50': (0.40, 0.50)}
    wts = count.cpu().numpy()

    def band(v, lo, hi):
        sel = (centres >= lo) & (centres < hi)
        return float((v[sel] * wts[sel]).sum())

    report = {'tiles': len(tiles), 'design': len(design), 'validation': len(valid), 'placebo': placebo,
              'centres': centres.tolist(), 'bands': {}, 'coherence': {}, 'noise_correlation': {}}
    Sn, Nn = Sd.cpu().numpy(), Nd.cpu().numpy()
    print('cross-channel signal coherence S_cd / sqrt(S_cc S_dd) and noise correlation, design set:')
    for (c, d, label) in ((0, 1, 'R-G'), (2, 1, 'B-G'), (0, 2, 'R-B')):
        coh = Sn[c, d] / np.sqrt(np.clip(Sn[c, c] * Sn[d, d], 1e-300, None))
        ncor = Nn[c, d] / np.sqrt(np.clip(Nn[c, c] * Nn[d, d], 1e-300, None))
        report['coherence'][label] = coh.tolist()
        report['noise_correlation'][label] = ncor.tolist()
        print(f'  {label}: signal ' + ' '.join(f'{coh[int(q / BIN)]:.3f}' for q in (0.05, 0.15, 0.25, 0.30, 0.35, 0.40, 0.45))
              + '   noise ' + ' '.join(f'{ncor[int(q / BIN)]:+.3f}' for q in (0.05, 0.15, 0.25, 0.30, 0.35, 0.40, 0.45))
              + '   at 0.05 0.15 0.25 0.30 0.35 0.40 0.45 cycles/px')
    print('per-channel signal-to-noise power S/N by frequency, design set (half-stack):')
    for c in range(3):
        print(f'  {"RGB"[c]}: ' + ' '.join(f'{Sn[c, c][int(q / BIN)] / Nn[c, c][int(q / BIN)]:.2f}' for q in (0.05, 0.15, 0.25, 0.30, 0.35, 0.40, 0.45)))
    Svn = Svd.cpu().numpy()
    print('validation set, equivalent signal-to-noise power S / mse - 1 per band (half-stack noise):')
    for name, (lo, hi) in bands.items():
        row = {}
        for k in estimators:
            mk = mse[k].cpu().numpy()
            row[k] = [band(Svn[c], lo, hi) / max(band(mk[c], lo, hi), 1e-300) - 1 for c in range(3)]
        row['raw_direct'] = [band(Svn[c], lo, hi) / band(Nvd.cpu().numpy()[c], lo, hi) for c in range(3)]
        report['bands'][name] = row
        print(f'  {name}: ' + '   '.join(f'{k} ' + '/'.join(f'{v:.2f}' for v in row[k]) for k in ('raw_direct', 'raw', 'own', 'borrow', 'joint')))
        print(f'      joint over own: ' + ' / '.join(f'{row["joint"][c] / row["own"][c]:.2f}' for c in range(3))
              + '   joint over borrow: ' + ' / '.join(f'{row["joint"][c] / row["borrow"][c]:.2f}' for c in range(3))
              + '   joint over green-own: ' + ' / '.join(f'{row["joint"][c] / row["own"][1]:.2f}' for c in range(3)))
    # Model prediction for the full stack from the design spectra.
    err_own = (torch.diagonal(Sp, dim1=1, dim2=2) * 0.5 * torch.diagonal(Ndiag, dim1=1, dim2=2)
               / (torch.diagonal(Sp, dim1=1, dim2=2) + 0.5 * torch.diagonal(Ndiag, dim1=1, dim2=2))).T.cpu().numpy()
    err_joint = torch.diagonal(Sp - joint_full @ Sp, dim1=1, dim2=2).T.cpu().numpy()
    Spd = torch.diagonal(Sp, dim1=1, dim2=2).T.cpu().numpy()
    print('predicted for the full stack (design spectra, noise halved), equivalent S/N power own -> joint:')
    report['full_stack_prediction'] = {}
    for name, (lo, hi) in bands.items():
        o = [band(Spd[c], lo, hi) / band(err_own[c], lo, hi) - 1 for c in range(3)]
        j = [band(Spd[c], lo, hi) / max(band(err_joint[c], lo, hi), 1e-300) - 1 for c in range(3)]
        report['full_stack_prediction'][name] = {'own': o, 'joint': j}
        print(f'  {name}: ' + ' / '.join(f'{o[c]:.1f} -> {j[c]:.1f} (x{j[c] / o[c]:.2f})' for c in range(3)))
    report['S_design'] = Sn.tolist()
    report['N_design'] = Nn.tolist()
    report['joint_filter'] = joint.cpu().numpy().tolist()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
