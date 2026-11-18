"""R4 at the scale of a point: through-focus transfer per pixel, grouped by
the full merge's own depth label.

  python -X utf8 point-focus.py OUT.json SERIES_DIR FIRST LAST WEIGHT_DUMP_PREFIX [--half 8]

series-focus.py measures tiles, and a tile of scales spans several focus
planes (frames on opposite sides of a tile's focus are sharp in different
places), so its widths are upper bounds. Here every pixel is its own sample.

Depth label: the winning frame of the full default render's election at
plane band 1 (`STREHL_PYRAMID_WEIGHT_DUMP`, `-b1-arg.i32`, decoded to the
0-based frame index, replicated to the output grid). It comes from a different band than
those scored below, so a scored coefficient's own noise did not choose it.
Kept where band 2's winner (replicated) is within 2 frames of it (a
consistent depth) and the label is at least `half` frames inside the
series.

Bands of each frame's channel c (output pixels):
  fine    c - G(c, 1)         about 0.20 cycles/px and up
  mid     G(c, 1) - G(c, 2)   about 0.08-0.25
  coarse  G(c, 2) - G(c, 4)   about 0.04-0.12
and for green also `top`, c - G(c, 0.6): the last octave below Nyquist.

For every labelled pixel with label L, the products c_{L+i} c_{L+j} of its
band coefficient in frames L+i and L+j (i, j in -half..half), averaged over
all labelled pixels: P[i, j]. Noise is independent between frames, so
off-diagonal entries are noise-free. Reported per band and channel:

  profile   q[i + 1/2] = P[i, i + 1] / max: transfer squared through focus
  focus     centroid of q above half its peak, against the label
  on offer  sum q / max q: frames' worth of signal-to-noise a matched
            filter with ideal (possibly signed) weights could use, for
            equal noise per frame; truncated at the window
  coherence the same for positive matched weights (what a weighted average
            centred on the label delivers) and for positive weights centred
            on the band's own focus; and the signed rank-1 and rank-2
            completions of P (if frames far apart still share content)
  windows   signal amplitude kept and signal-to-noise (in best frames) of
            uniform windows of 3, 5, 7, 11, 17 frames centred on the label,
            and centred on the band's own focus

Control: labels rolled by 400 px (pixels no longer at their own focus): the
profile must flatten and widths must rise.

Fooled by: label error (broadens q and lowers the peak: widths here are
still upper bounds, tighter than the tiles'); coefficients with no signal
dilute nothing (products average to zero) but pixels of every texture
strength are pooled with their signal power as weight.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp


def arg(name, default=None):
    for i, tok in enumerate(sys.argv):
        if tok == name:
            return sys.argv[i + 1]
        if tok.startswith(name + '='):
            return tok.split('=', 1)[1]
    return default


def bands_of(x, top):
    g1, g2, g4 = fp.gauss(x, 1.0), fp.gauss(x, 2.0), fp.gauss(x, 4.0)
    out = [x - g1, g1 - g2, g2 - g4]
    if top:
        out.append(x - fp.gauss(x, 0.6))
    return out


def complete(Pm, rank, iters=300):
    off = 1 - np.eye(len(Pm))
    M = Pm.copy()
    for _ in range(iters):
        w, v = np.linalg.eigh(M)
        w, v = w[::-1][:rank], v[:, ::-1][:, :rank]
        L = (v * np.clip(w, 0, None)) @ v.T
        M = Pm * off + np.diag(np.diag(L))
    return np.clip(np.linalg.eigvalsh(M)[::-1][:rank], 0, None).sum()


def analyse(P, half, label):
    nw = 2 * half + 1
    off = 1 - np.eye(nw)
    q = np.array([P[j, j + 1] for j in range(nw - 1)])
    xs = np.arange(nw - 1) - half + 0.5
    qmax = q.max()
    v = np.clip(q, 0, None)
    w = np.where(v >= 0.5 * qmax, v, 0)
    cen = float((w * xs).sum() / w.sum())
    h = np.sqrt(np.clip(0.5 * (np.r_[q[0], q] + np.r_[q, q[-1]]), 0, None))     # per-frame amplitude, from neighbour products
    hmax2 = float((h ** 2).max())

    def arm(wts):
        s2 = (np.outer(wts, wts) * P * off).sum() / (wts.sum() ** 2 - (wts ** 2).sum())
        return float(np.sqrt(max(s2 / hmax2, 0))), float(s2 / hmax2 / ((wts ** 2).sum() / wts.sum() ** 2))

    idx = np.arange(nw) - half
    c0 = int(round(cen))
    res = {'profile': (q / qmax).tolist(), 'focus_offset_frames': cen,
           'at_label_over_peak': float(0.5 * (q[half - 1] + q[half]) / qmax),
           'on_offer_magnitude': float(v.sum() / qmax * nw / (nw - 1)),
           'rank1_signed': float(complete(P, 1) / hmax2), 'rank2': float(complete(P, 2) / hmax2),
           'matched_positive': arm(h)[1], 'windows': {}}
    for width in (1, 3, 5, 7, 11, 17):
        r = width // 2
        a_lab = arm((np.abs(idx) <= r).astype(float)) if width > 1 else (float(np.sqrt(max(0.5 * (q[half - 1] + q[half]) / hmax2, 0))), float(0.5 * (q[half - 1] + q[half]) / hmax2))
        own = (np.abs(idx - c0) <= r).astype(float)
        a_own = arm(own) if width > 1 and own.sum() == width else None
        res['windows'][str(width)] = {'label_centred': a_lab, 'own_focus_centred': a_own}
    print(f'  {label}: focus {cen:+.2f} fr from the label; at the label {res["at_label_over_peak"]:.3f} of peak power; on offer {res["on_offer_magnitude"]:.1f} '
          f'(signed rank-1 {res["rank1_signed"]:.1f}, rank-2 {res["rank2"]:.1f}, positive matched {res["matched_positive"]:.1f})')
    print('      profile ' + ' '.join(f'{x:.2f}' for x in res['profile']))
    print('      uniform windows centred on the label, amplitude kept / S-N in best frames: '
          + '  '.join(f'{k}: {v["label_centred"][0]:.2f}/{v["label_centred"][1]:.1f}' for k, v in res['windows'].items()))
    print('      the same centred on this band\'s own focus: '
          + '  '.join(f'{k}: {v["own_focus_centred"][0]:.2f}/{v["own_focus_centred"][1]:.1f}' for k, v in res['windows'].items() if v['own_focus_centred']))
    return res


def main():
    out, sdir, first, last, prefix = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    half = int(arg('--half', '8'))
    dev = fp.DEV
    dims = json.loads(Path(prefix + '-dims.json').read_text())
    b1, b2 = dims['bands'][1], dims['bands'][2]
    a1 = torch.from_numpy(np.fromfile(f'{prefix}-b1-arg.i32', dtype='<i4').reshape(b1['h'], b1['w']).astype(np.int64)).to(dev)
    a2 = torch.from_numpy(np.fromfile(f'{prefix}-b2-arg.i32', dtype='<i4').reshape(b2['h'], b2['w']).astype(np.int64)).to(dev)
    # The dump numbers frames in the order the accumulators absorbed them, not
    # in file order. With the restoration's half-stacks on (the default for
    # pixel-shift stacks) every second folded frame goes to a second
    # accumulator that is absorbed last, so for N frames: label a < ceil(N / 2)
    # is frame 2 a, otherwise frame 2 (a - ceil(N / 2)) + 1. Checked against
    # series-focus.py's tile focus planes before use (see results).
    nfr = dims['frames']
    first_half = (nfr + 1) // 2

    def decode(a):
        return torch.where(a < 0, a, torch.where(a < first_half, 2 * a, 2 * (a - first_half) + 1))

    a1, a2 = decode(a1), decode(a2)
    ks = list(range(first, last + 1))
    H, W = tifffile.memmap(sdir / f'one-{ks[0]}.tif').shape[:2]
    lab = a1.repeat_interleave(4, 0).repeat_interleave(4, 1)[:H, :W]
    lab2 = a2.repeat_interleave(8, 0).repeat_interleave(8, 1)[:H, :W]
    ok = (lab >= first + half) & (lab <= last - half) & ((lab - lab2).abs() <= 2)
    ok[:64], ok[-64:], ok[:, :64], ok[:, -64:] = False, False, False, False
    print(f'{int(ok.sum())} labelled pixels ({100 * float(ok.float().mean()):.1f} % of the frame), labels {first + half}..{last - half}', flush=True)
    names = [('G', 1, ['fine', 'mid', 'coarse', 'top']), ('R', 0, ['fine', 'mid', 'coarse']), ('B', 2, ['fine', 'mid', 'coarse'])]
    nw = 2 * half + 1
    report = {'series': [first, last], 'half': half, 'labelled_pixels': int(ok.sum()), 'arms': {}}
    for arm_name, roll in (('labels', 0), ('placebo: labels rolled 400 px', 400)):
        lab_use = torch.roll(lab, (roll, roll), (0, 1)) if roll else lab
        ok_use = torch.roll(ok, (roll, roll), (0, 1)) if roll else ok
        idx = torch.nonzero(ok_use.flatten())[:, 0]
        if len(idx) > 6_000_000:
            idx = idx[torch.randperm(len(idx), device=dev)[:6_000_000]]
        labs = lab_use.flatten()[idx]
        store = {}
        for ch, c, bnames in names:
            # coefficients of the selected pixels, every frame of the series: [frames, bands, pixels] float16
            store[ch] = torch.zeros(len(ks), len(bnames), len(idx), device=dev, dtype=torch.float16)
        for ki, k in enumerate(ks):
            img = torch.from_numpy(tifffile.imread(sdir / f'one-{k}.tif').astype(np.float32)).to(dev).permute(2, 0, 1)
            for ch, c, bnames in names:
                for bi, band in enumerate(bands_of(img[c], len(bnames) == 4)):
                    store[ch][ki, bi] = band.flatten()[idx].to(torch.float16)
            del img
        res = {}
        print(arm_name)
        for ch, c, bnames in names:
            for bi, bname in enumerate(bnames):
                P = np.zeros((nw, nw))
                rel = (labs - first)                                  # frame index of each pixel's label
                coef = torch.stack([store[ch][:, bi].gather(0, (rel + j)[None])[0].float() for j in range(-half, half + 1)])   # [nw, pixels]
                P = (coef.double() @ coef.double().T / coef.shape[1]).cpu().numpy()
                res[f'{ch} {bname}'] = analyse(P, half, f'{ch} {bname:6s}')
                res[f'{ch} {bname}']['P'] = P.tolist()
        report['arms'][arm_name] = res
        del store
    out.write_text(json.dumps(report) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
