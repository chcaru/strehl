"""Measure the shipped merge's per-band selection weights.

THE QUESTION, which is refutable: in a region with no scene structure at a band's
scale, does the weight collapse onto a single frame?

  concentration = max_i(w_i) / sum_i(w_i)

  1/frames  ->  a plain mean; every frame contributed equally.
  1.0       ->  winner-take-all; one frame owns the coefficient.

If flat regions read near 1/frames the proposed mechanism is REFUTED outright. If
they read near 1.0 the merge is picking a winner where there is nothing to pick on,
and the only remaining question is whether that choice is spatially structured
enough to be mottle.

WHY THERE IS A MATCHED ARM. A concentration figure alone charges for the subject:
`orch_mottle_visual.py` is disabled in this repo for exactly that error, having
ranked a leaf highly because its veins sit in the measured band. So every number
here is reported for FLAT and DETAIL sites of the same subject, from the same
render, and it is the CONTRAST between them that carries the claim. A merge that
is behaving separates them; one that is selecting on noise does not.

The winner-coherence null is the empirical label distribution in the same region
(sum p_i^2), not 1/frames. Frames are not used equally -- a stack has a sharpest
frame -- and 1/frames would manufacture apparent structure out of that alone.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile

DUMP = r"C:\dev\strehl-out\V-H2H2\wdump"


def load_dims(prefix):
    with io.open(prefix + "-dims.json", encoding="utf-8") as fh:
        return json.load(fh)


def band(prefix, k, w, h, suffix, dtype):
    path = "%s-b%d-%s" % (prefix, k, suffix)
    a = np.fromfile(path, dtype=dtype)
    if a.size != w * h:
        raise SystemExit("%s: %d values, expected %d*%d=%d"
                         % (path, a.size, w, h, w * h))
    return a.reshape(h, w)


def boxsd(a, r):
    """Local sd over a (2r+1) box, via summed-area tables. Shape-asserted."""
    a = a.astype(np.float64)
    def integ(x):
        s = np.cumsum(np.cumsum(x, axis=0), axis=1)
        return np.pad(s, ((1, 0), (1, 0)))
    h, w = a.shape
    i1, i2 = integ(a), integ(a * a)
    y0 = np.clip(np.arange(h) - r, 0, h); y1 = np.clip(np.arange(h) + r + 1, 0, h)
    x0 = np.clip(np.arange(w) - r, 0, w); x1 = np.clip(np.arange(w) + r + 1, 0, w)
    def win(I):
        return (I[np.ix_(y1, x1)] - I[np.ix_(y0, x1)]
                - I[np.ix_(y1, x0)] + I[np.ix_(y0, x0)])
    n = ((y1 - y0)[:, None] * (x1 - x0)[None, :]).astype(np.float64)
    m1, m2 = win(i1) / n, win(i2) / n
    out = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    assert out.shape == a.shape, "boxsd changed shape %s -> %s" % (a.shape, out.shape)
    return out


def agreement(arg, mask):
    """Fraction of adjacent admitted pairs sharing a winner, and its null."""
    pairs = same = 0
    for d in (0, 1):
        a = arg[:-1, :] if d == 0 else arg[:, :-1]
        b = arg[1:, :] if d == 0 else arg[:, 1:]
        ma = mask[:-1, :] if d == 0 else mask[:, :-1]
        mb = mask[1:, :] if d == 0 else mask[:, 1:]
        ok = ma & mb
        pairs += int(ok.sum())
        same += int((a[ok] == b[ok]).sum())
    lab = arg[mask]
    if lab.size == 0 or pairs == 0:
        return float("nan"), float("nan")
    _, counts = np.unique(lab, return_counts=True)
    p = counts / counts.sum()
    return same / pairs, float((p * p).sum())


def main():
    prefix = os.path.join(DUMP, sys.argv[1] if len(sys.argv) > 1 else "cb")
    img = os.path.join(DUMP, "off.tiff")
    dims = load_dims(prefix)
    nfr = dims["frames"]
    print("subject dump %s   frames=%d" % (os.path.basename(prefix), nfr))
    print("a plain mean reads %.4f; winner-take-all reads 1.0\n" % (1.0 / nfr))

    a = tifffile.imread(img)
    lum = a[..., 1].astype(np.float64) if a.ndim == 3 else a.astype(np.float64)
    print("render %s -> luma %s" % (a.shape, lum.shape))

    # Flat/detail classification on the OUTPUT grid, once, from local sd.
    sd = boxsd(lum, 16)
    lo, hi = np.percentile(sd, [15, 85])
    print("local sd p15=%.1f p85=%.1f  (flat = below p15, detail = above p85)\n"
          % (lo, hi))

    print("%-3s %-11s %-6s %-9s %-9s %-9s %-9s"
          % ("k", "grid", "p", "conc flat", "conc det", "refused f", "refused d"))
    rows = []
    for b in dims["bands"]:
        k, w, h, p = b["k"], b["w"], b["h"], b["exponent"]
        try:
            conc = band(prefix, k, w, h, "conc.f32", np.float32)
            arg = band(prefix, k, w, h, "arg.i32", np.int32)
        except FileNotFoundError:
            continue
        # Map the output-grid classification onto this band's grid.
        ys = (np.arange(h) * (lum.shape[0] / h)).astype(int).clip(0, lum.shape[0] - 1)
        xs = (np.arange(w) * (lum.shape[1] / w)).astype(int).clip(0, lum.shape[1] - 1)
        sdb = sd[np.ix_(ys, xs)]
        flat = sdb <= lo
        det = sdb >= hi
        ok = np.isfinite(conc)
        cf = float(np.median(conc[flat & ok])) if (flat & ok).any() else float("nan")
        cd = float(np.median(conc[det & ok])) if (det & ok).any() else float("nan")
        rf = float((~ok)[flat].mean()) if flat.any() else float("nan")
        rd = float((~ok)[det].mean()) if det.any() else float("nan")
        print("%-3d %-11s %-6.2f %-9.4f %-9.4f %-9.4f %-9.4f"
              % (k, "%dx%d" % (w, h), p, cf, cd, rf, rd))
        rows.append((k, w, h, p, cf, cd, rf, rd, conc, arg, flat, det, ok))

    print("\nWINNER COHERENCE  (obs = adjacent coefficients sharing a winner;")
    print("null = same statistic if labels were shuffled, from the region's own")
    print("label distribution. obs/null near 1.0 = the choice carries no structure.)")
    print("%-3s %-6s %-19s %-19s" % ("k", "p", "FLAT obs/null", "DETAIL obs/null"))
    for (k, w, h, p, cf, cd, rf, rd, conc, arg, flat, det, ok) in rows:
        adm = ok & (arg >= 0)
        of, nf = agreement(arg, flat & adm)
        od, nd = agreement(arg, det & adm)
        print("%-3d %-6.2f %-19s %-19s"
              % (k, p,
                 "%.4f/%.4f=%.2fx" % (of, nf, of / nf) if nf and nf == nf else "n/a",
                 "%.4f/%.4f=%.2fx" % (od, nd, od / nd) if nd and nd == nd else "n/a"))


if __name__ == "__main__":
    main()
