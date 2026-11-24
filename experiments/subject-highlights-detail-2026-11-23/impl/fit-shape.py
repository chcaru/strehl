"""Where in frequency does the weevil's reference spectrum part from the diffraction model?
(plan Q1, shd-q-restore; follows fit-cause.py, whose fit port it imports)

For each dump: the joint fit over narrower bands (0.20 up to 0.40, 0.44, 0.49), and the green
reference signal per bin over 0.20-0.50 against the model with the lanternfly's cutoff.

  python fit-shape.py <spectra.json> [...]
"""
import importlib.util
import json
import pathlib
import sys

import numpy as np

spec = importlib.util.spec_from_file_location('fc', pathlib.Path(__file__).with_name('fit-cause.py'))
fc = importlib.util.module_from_spec(spec)
sys.argv, argv = sys.argv[:1], sys.argv[1:]
spec.loader.exec_module(fc)


def fit_band(c, signals, hi):
    keep = c < hi
    # fit_joint fits 0.20-0.49 of whatever it is given: hand it only bins below `hi`.
    cc = np.where(keep, c, 10.0)
    return fc.fit_joint(cc, signals)


for path in argv:
    d = json.load(open(path))
    c = np.array(d['centres'])
    used = [t for t in d['tile_records'] if not t['hot']]
    sig = [fc.mean(used, ch, 'ref_signal') for ch in range(3)]
    print('==', path)
    for hi in [0.40, 0.44, 0.49]:
        g, r = fit_band(c, sig, hi)
        print('  fit over 0.20-%.2f: green %.3f%s residual %.4f' % (hi, g, '  CEILING' if g >= fc.CEILING else '', r))
    # Green: local log-slope of the reference signal, against the model's at fc 0.776, alpha 0.
    s = sig[1]
    model = (fc.mtf_diffraction(c / 0.776) * np.sinc(c)) ** 2
    rows = []
    for lo in np.arange(0.20, 0.50, 0.03):
        b = (c >= lo) & (c < lo + 0.03)
        b2 = (c >= lo + 0.03) & (c < lo + 0.06)
        if b2.sum() == 0 or lo + 0.06 > 0.52:
            continue
        ds = np.log(s[b2].mean() / s[b].mean()) / np.log(c[b2].mean() / c[b].mean())
        dm = np.log(model[b2].mean() / model[b].mean()) / np.log(c[b2].mean() / c[b].mean())
        rows.append('%.2f %+.2f/%+.2f' % (lo + 0.03, ds, dm))
    print('  green log-slope of the reference signal / of MTF^2 sinc^2 at fc 0.776 (alpha 0), by 0.03 bins:')
    print('   ', '  '.join(rows))
