"""Why did the weevil's one-aperture cutoff fit run to its ceiling? (plan Q1, shd-q-restore)

Reads the per-tile spectra the engine dumps (STREHL_OPTICAL_RESTORE_DUMP, `tile_records`) and
refits the cutoff with strehl_core::optical_restore::fit_cutoff_joint ported below, on chosen
tiles and with chosen corrections. The port is checked first: on the tiles the render used it
must return the render's own joint fit.

Arms (plan section 3):
  noise    the reference's measured noise spectrum subtracted from its signal before the fit
           (the reference signal is a cross-spectrum, so it holds no temporal noise in
           expectation; this arm tests whether something noise-like is in it anyway);
  floor    the reference signal minus its own level in the top bins (0.60-0.70 cycles/px):
           a white component common to the two frames;
  unpinned tiles whose reference crops or merged planes hold near-pinned samples left out,
           at several thresholds;
  halves   the fit on the halves' signal instead of the reference (what a high signal-to-noise
           spectrum of the same tiles gives; the blend transfer is not divided out).

  python fit-cause.py <spectra.json> [more spectra.json ...] > fit-cause.txt
"""
import json
import sys

import numpy as np

W = np.array([0.600, 0.535, 0.465])
CEILING = 0.88


def mtf_diffraction(s):
    s = np.clip(s, 0.0, 1.0)
    return (2 / np.pi) * (np.arccos(s) - s * np.sqrt(1 - s * s))


ALPHA = 0.1 * np.arange(41)[:, None]


def fit_joint(c, signals):
    """fit_cutoff_joint, the alpha loop vectorised (the same arithmetic per point)."""
    fit = (c > 0.20) & (c < 0.49)
    x = c[fit]
    cubes = [np.cbrt(np.maximum(s[fit], 0.0)) for s in signals]
    slope = x[None, :] ** -ALPHA
    best = (np.inf, 0.0)
    for a in range(126):
        fg = 0.40 + 0.004 * a
        total = 0.0
        for ch, cube in enumerate(cubes):
            fc = fg * W[1] / W[ch]
            base = (mtf_diffraction(x / fc) * np.sinc(x)) ** 2
            power = max((cube ** 2).sum(), 1e-300)
            m = np.cbrt(slope * base[None, :])
            mm = np.maximum((m * m).sum(axis=1), 1e-30)
            k = (m * cube[None, :]).sum(axis=1) / mm
            total += (((cube[None, :] - k[:, None] * m) ** 2).sum(axis=1) / power).min()
        if total < best[0]:
            best = (total, fg)
    return best[1], best[0]


def mean(tiles, ch, key):
    return np.mean([t['channels'][ch][key] for t in tiles], axis=0)


for path in sys.argv[1:]:
    d = json.load(open(path))
    c = np.array(d['centres'])
    tiles = d['tile_records']
    used = [t for t in tiles if not t['hot']]
    print('==', path)
    print('tiles with references %d, used by the render %d (render says %d)' % (len(tiles), len(used), d['tiles']))
    # Port check: the radial means of the used tiles are the render's spectra.
    for ch in range(3):
        got = mean(used, ch, 'ref_signal')
        want = np.array(d['channels'][ch]['ref_signal'])
        print('  channel %d: port spectra vs render max rel diff %.2e' % (ch, np.max(np.abs(got - want)) / np.max(np.abs(want))))

    def report(name, sel, transform=lambda s, n, ch: s, key='ref_signal'):
        if len(sel) < 8:
            print('  %-44s %3d tiles: too few' % (name, len(sel)))
            return
        sig = [transform(mean(sel, ch, key), mean(sel, ch, key.replace('signal', 'noise')), ch) for ch in range(3)]
        g, r = fit_joint(c, sig)
        print('  %-44s %3d tiles: green %.3f%s  residual %.4f' % (name, len(sel), g, '  CEILING' if g >= CEILING else '', r))

    report('as rendered (port check)', used)
    # Signal-to-noise of the reference by band, green.
    s, n = mean(used, 1, 'ref_signal'), mean(used, 1, 'ref_noise')
    so, no = mean(used, 1, 'out_signal'), mean(used, 1, 'out_noise')
    for lo, hi in [(0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.49), (0.5, 0.6), (0.6, 0.7)]:
        b = (c >= lo) & (c < hi)
        print('  green %.2f-%.2f: reference signal %.3e noise %.3e (S/N %.2f); halves signal %.3e noise %.3e (S/N %.1f)'
              % (lo, hi, s[b].mean(), n[b].mean(), s[b].mean() / max(n[b].mean(), 1e-30),
                 so[b].mean(), no[b].mean(), so[b].mean() / max(no[b].mean(), 1e-30)))
    report('noise: signal - measured noise', used, lambda s, n, ch: s - n)
    report('noise: signal - 0.5 x measured noise', used, lambda s, n, ch: s - 0.5 * n)
    top = (c >= 0.60) & (c < 0.70)
    report('floor: signal - its 0.60-0.70 level', used, lambda s, n, ch: s - s[top].mean())
    report('halves: the halves\' signal', used, key='out_signal')
    for f in [0.95, 0.8, 0.5, 0.3, 0.2]:
        report('unpinned: reference peak <= %.2f' % f, [t for t in used if max(max(p) for p in t['ref_peak']) <= f])
        report('unpinned: merged peak <= %.2f' % f, [t for t in used if max(t['merged_peak']) <= f])
    report('unpinned: no reference sample > 0.5', [t for t in used if t['ref_over_half'] == 0])
    # Distribution of tile peaks.
    peaks = np.array([max(max(p) for p in t['ref_peak']) for t in used])
    print('  reference peaks over the range: quartiles %s' % np.round(np.percentile(peaks, [0, 25, 50, 75, 100]), 3))
    # Per tile: which tiles fit with a roll-off on their own?
    own = []
    for t in used:
        g, _ = fit_joint(c, [np.array(t['channels'][ch]['ref_signal']) for ch in range(3)])
        own.append(g)
    own = np.array(own)
    print('  per-tile fits: %d of %d at the ceiling; quartiles %s' % ((own >= CEILING).sum(), len(own), np.round(np.percentile(own, [0, 25, 50, 75, 100]), 3)))
    keep = [t for t, g in zip(used, own) if g < CEILING]
    report('tiles whose own fit has a roll-off', keep)
