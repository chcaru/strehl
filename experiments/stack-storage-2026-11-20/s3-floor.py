"""S3: the noise floor of a lossless coder, from six repeats of each shift position.

Run stack-1794687317465-11226: six four-shot groups at ONE focus position, so frames
s, s+4, ..., s+20 (s = 1..4) are six exposures of the same scene on the same photosites.

Per shift position: per-pixel temporal mean and unbiased variance (after removing each
frame's lamp level, a per-frame scale on the signal above black), variance against the
product's model for this body (0.4040 DN/e-, 1.334 DN read, black 512), and the ORACLE code
length: a coder that knew every pixel's true mean would still pay the entropy of the noise,
0.5 log2(2 pi e sigma^2) bits (integer bins; exact discrete entropy below sigma 2).

Also the leave-one-out empirical cross-check (code frame k with the mean of the other five;
its excess over the oracle is 0.5 log2(6/5) = 0.132 bits by construction), and how big the
fixed pattern a spatial coder cannot see (PRNU 0.30/0.35/0.40 % R/G/B, MEASURED
2026-11-16) is against that noise.
"""
import math
import sys

import numpy as np

import common as c

c.below_normal()
RUN = sys.argv[1] if len(sys.argv) > 1 else c.REPEAT_A
BLACK = 512.0
GAIN = 0.4040
READ = 1.334
CROP = (32, 20, 9504, 6336)
KAPPA = {'R': 0.0030, 'G1': 0.0035, 'G2': 0.0035, 'B': 0.0040}
EDGES = np.array([-50, 25, 50, 100, 200, 400, 800, 1600, 3200, 6400, 16000], dtype=np.float64)


def model_var(s):
    return GAIN * np.maximum(s, 0.0) + READ * READ


def entropy_bits(var):
    """Entropy in bits of an integer-binned Gaussian of variance `var` (DN^2)."""
    var = np.asarray(var, dtype=np.float64)
    h = 0.5 * np.log2(2 * math.pi * math.e * (var + 1.0 / 12.0))  # Sheppard-corrected; within 1e-3 above sigma 1
    return h


def cfa_names(cfa):
    """Which 2x2 site is which colour, from levels: greens are the two brightest-correlated diagonal sites."""
    m = [[float(cfa[y::2, x::2][::8, ::8].mean()) for x in (0, 1)] for y in (0, 1)]
    return m


x0, y0, cw, ch = CROP
frames = {s: [s + 4 * g for g in range(6)] for s in (1, 2, 3, 4)}
print('run', RUN, 'black', BLACK, 'gain', GAIN, 'DN/e-', 'read', READ, 'DN')
total_rows = []
for s, fs in frames.items():
    stack = np.empty((6, ch, cw), dtype=np.float32)
    for i, f in enumerate(fs):
        stack[i] = c.cfa_of(RUN, f)[y0:y0 + ch, x0:x0 + cw]
    sig = stack - BLACK
    level = sig.reshape(6, -1)[:, ::97].mean(axis=1)
    scale = level / level.mean()
    print('== shift position %d: frames %s  lamp level per frame (relative) %s' % (s, fs, np.round(scale, 5)))
    sig /= scale[:, None, None].astype(np.float32)
    mean = sig.mean(axis=0)
    var = sig.var(axis=0, ddof=1)
    # frame-to-frame scene motion check: correlation of consecutive differences
    d1 = (sig[1] - sig[0])[::4, ::4]
    d2 = (sig[3] - sig[2])[::4, ::4]
    print('   correlation of (f2-f1) with (f4-f3), should be ~0 with no scene motion: %.4f' % np.corrcoef(d1.ravel(), d2.ravel())[0, 1])
    sat = (stack.max(axis=0) >= 16383)
    print('   saturated pixels (any repeat at 16383): %.4f %%' % (100 * sat.mean()))
    sites = cfa_names(stack[0])
    print('   2x2 site means (DN): %s' % np.round(np.array(sites), 1))
    names = {(0, 0): 'R', (0, 1): 'G1', (1, 0): 'G2', (1, 1): 'B'}
    grand_oracle_model = 0.0
    grand_oracle_meas = 0.0
    grand_loo = 0.0
    grand_fp = 0.0
    for (dy, dx), name in names.items():
        m = mean[dy::2, dx::2].ravel().astype(np.float64)
        v = var[dy::2, dx::2].ravel().astype(np.float64)
        ok = ~sat[dy::2, dx::2].ravel()
        idx = np.clip(np.digitize(m, EDGES) - 1, 0, len(EDGES) - 2)
        print('   %-2s site (%d,%d): level bin (DN above black) | %% of pixels | mean level | measured var | model var | ratio | sigma DN | oracle bits (measured) | fixed pattern sd DN | bits a spatial coder loses to it' % (name, dy, dx))
        meas_curve = np.zeros(len(EDGES) - 1)
        for b in range(len(EDGES) - 1):
            sel = (idx == b) & ok
            if sel.sum() < 2000:
                meas_curve[b] = np.nan
                continue
            lv = m[sel].mean()
            mv = v[sel].mean()
            mod = model_var(m[sel]).mean()
            meas_curve[b] = mv / mod
            fp = KAPPA[name] * max(lv, 0.0)
            lost = 0.5 * math.log2(1 + fp * fp / mv)
            print('      [%6d, %6d) %6.2f %% %9.1f %10.2f %10.2f  %.3f  %7.2f  %6.3f   %6.2f  %.4f'
                  % (EDGES[b], EDGES[b + 1], 100 * sel.mean(), lv, mv, mod, mv / mod, math.sqrt(mv), float(entropy_bits(mv)), fp, lost))
        ratio = np.where(np.isnan(meas_curve), 1.0, meas_curve)[idx]
        mvar = model_var(m)
        o_model = entropy_bits(mvar)[ok].mean()
        o_meas = entropy_bits(mvar * ratio)[ok].mean()
        fp_bits = (0.5 * np.log2(1 + (KAPPA[name] * np.maximum(m, 0)) ** 2 / (mvar * ratio)))[ok].mean()
        # leave-one-out empirical: frame k coded with the mean of the other five, Gaussian at the measured variance * 6/5
        loo = 0.0
        for k in range(6):
            xk = sig[k][dy::2, dx::2].ravel().astype(np.float64)
            others = (m * 6 - xk) / 5
            pv = mvar * ratio * 1.2 + 1.0 / 12.0
            loo += (0.5 * np.log2(2 * math.pi * pv) + (xk - others) ** 2 / (2 * pv) / math.log(2))[ok].mean()
        loo /= 6
        print('      oracle floor: %.3f bits/px (model sigma), %.3f (measured sigma); leave-one-out empirical %.3f (expected oracle + 0.132 = %.3f); fixed pattern adds %.4f bits for a spatial coder'
              % (o_model, o_meas, loo, o_meas + 0.132, fp_bits))
        grand_oracle_model += o_model / 4
        grand_oracle_meas += o_meas / 4
        grand_loo += loo / 4
        grand_fp += fp_bits / 4
    print('   ALL SITES shift %d: oracle %.3f bits/px (model), %.3f (measured), LOO %.3f, fixed-pattern cost %.4f' % (s, grand_oracle_model, grand_oracle_meas, grand_loo, grand_fp))
    total_rows.append((grand_oracle_model, grand_oracle_meas, grand_loo, grand_fp))
    del stack, sig, mean, var
t = np.array(total_rows).mean(axis=0)
print('RUN MEAN (active area): oracle floor %.3f bits/px by the model, %.3f by measured variance; LOO check %.3f; a spatial coder cannot go below floor + %.4f (fixed pattern)' % tuple(t))
