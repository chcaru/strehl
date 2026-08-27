"""Does the winner's share dilute as the frame count rises?

ORCH's hypothesis, labelled by him as inference from the arithmetic and not
measurement: SoftPower normalises w_i / sum_j w_j, so the winner's share depends
on how many frames sit near-tied with it, that count grows with N, and the
reconstruction therefore drifts toward an average as the stack deepens. If true,
one mechanism explains both the mid-scale mottle (flat regions, effective count
collapses to ~1 chosen by noise) and the softness lane's measured 0.114 -- 63
frames softer than 32 at matched focus range.

WHY THIS DOES NOT USE THE CONCENTRATION STATISTIC.  max(w)/sum(w) has null value
1/N under a plain mean. It falls as N rises for a merge that behaves identically
at both frame counts, for one that behaves randomly, and for one that behaves as
ORCH describes. Reporting that it fell would confirm the hypothesis by
construction -- the arithmetic of the statistic, not a property of the merge.

The scale-free form is the participation ratio

    n_eff = sum(w)^2 / sum(w^2)

which reads N for a plain mean and 1.0 for winner-take-all at EVERY N, so a
value at 63 frames is directly comparable with a value at 32.

  ORCH's story alive:  n_eff in DETAIL rises with N -- near-ties multiply.
  ORCH's story dead:   n_eff in detail is flat in N -- the winner keeps its
                       share however many others are present, and the 0.114
                       has another explanation.

The two are separated by reporting BOTH n_eff and n_eff/N. If n_eff is constant
there is no dilution; if n_eff/N is constant the dilution is total; a real answer
is very likely between them, so both bracketing readings are printed rather than
one and a verdict.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\V-H2H2\nscale\out"


def boxsd(a, r):
    """Local sd in a (2r+1) box. Asserts its own output shape.

    ORCH's orch_eye_check.py carried a running-sum box blur that silently
    returned an array one row and one column short and only broke when two
    blurs of different radius were differenced. The assert is that defect's
    fix, kept here because this helper is the same shape of code.
    """
    a = a.astype(np.float64)

    def integ(x):
        return np.pad(np.cumsum(np.cumsum(x, axis=0), axis=1), ((1, 0), (1, 0)))

    h, w = a.shape
    i1, i2 = integ(a), integ(a * a)
    y0 = np.clip(np.arange(h) - r, 0, h)
    y1 = np.clip(np.arange(h) + r + 1, 0, h)
    x0 = np.clip(np.arange(w) - r, 0, w)
    x1 = np.clip(np.arange(w) + r + 1, 0, w)

    def win(I):
        return (I[np.ix_(y1, x1)] - I[np.ix_(y0, x1)]
                - I[np.ix_(y1, x0)] + I[np.ix_(y0, x0)])

    n = ((y1 - y0)[:, None] * (x1 - x0)[None, :]).astype(np.float64)
    m1, m2 = win(i1) / n, win(i2) / n
    out = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    assert out.shape == a.shape, "boxsd changed shape: %s vs %s" % (out.shape, a.shape)
    return out


def dims(arm):
    with io.open(os.path.join(OUT, "%s-dims.json" % arm), encoding="utf-8") as fh:
        return json.load(fh)


def band(arm, k, suffix, dtype):
    p = os.path.join(OUT, "%s-b%d-%s" % (arm, k, suffix))
    return np.fromfile(p, dtype=dtype) if os.path.exists(p) else None


def masks(arm, w, h, ref=None, lo_p=15, hi_p=85):
    """Flat/detail masks on a render, resampled to a band grid.

    `ref` names the arm whose render defines the regions. Classifying each arm
    on its OWN render is a confound when the arms are being compared: if one arm
    is sharper, its detail percentile selects different pixels, and a difference
    in where you looked is reported as a difference in what you found. The
    default here is therefore a SHARED reference -- the same pixels on both arms
    -- and the caller can pass ref=arm to get the per-arm classification and
    check that the choice does not carry the result.
    """
    src = ref if ref is not None else arm
    img = tifffile.imread(os.path.join(OUT, "%s.tiff" % src))
    lum = img[..., 1].astype(np.float64)
    sd = boxsd(lum, 16)
    lo, hi = np.percentile(sd, lo_p), np.percentile(sd, hi_p)
    oh, ow = lum.shape
    ys = (np.arange(h) * (oh / h)).astype(int).clip(0, oh - 1)
    xs = (np.arange(w) * (ow / w)).astype(int).clip(0, ow - 1)
    s = sd[np.ix_(ys, xs)]
    return (s <= lo), (s >= hi), (oh, ow)


def main():
    argv = [a for a in sys.argv[1:] if a != "--own-masks"]
    own = "--own-masks" in sys.argv
    arms = argv or ["n63", "n32"]
    ref = None if own else arms[0]
    D = {a: dims(a) for a in arms}
    print("region classification: %s"
          % ("each arm on its own render" if own
             else "SHARED, both arms scored on %s's render" % ref))
    for a in arms:
        print("%-5s frames=%d" % (a, D[a]["frames"]))

    shapes = {}
    print()
    print("PARTICIPATION RATIO  n_eff = sum(w)^2 / sum(w^2)")
    print("  a plain mean reads N; winner-take-all reads 1.0, at every N")
    print()
    hdr = "%-3s %-6s" % ("k", "p")
    for a in arms:
        hdr += " | %-9s %-9s %-9s" % ("%s flat" % a, "%s det" % a, "%s n/N" % a)
    print(hdr + " | detail ratio")

    nb = min(len(D[a]["bands"]) for a in arms)
    rows = []
    for k in range(nb):
        cells, det_means = [], {}
        p = D[arms[0]]["bands"][k]["exponent"]
        for a in arms:
            b = D[a]["bands"][k]
            n = band(a, k, "neff.f32", np.float32)
            if n is None:
                cells.append(" | %-9s %-9s %-9s" % ("-", "-", "-"))
                continue
            n = n.reshape(b["h"], b["w"])
            fm, dm, shp = masks(a, b["w"], b["h"], ref=ref)
            shapes[a] = shp
            good = np.isfinite(n)
            f = float(np.mean(n[fm & good])) if np.any(fm & good) else float("nan")
            d = float(np.mean(n[dm & good])) if np.any(dm & good) else float("nan")
            det_means[a] = d
            cells.append(" | %-9.3f %-9.3f %-9.4f" % (f, d, d / D[a]["frames"]))
        ratio = ""
        if len(arms) == 2 and all(x in det_means for x in arms):
            hi, lo = det_means[arms[0]], det_means[arms[1]]
            if lo == lo and lo != 0:
                ratio = "%.3fx" % (hi / lo)
        print("%-3d %-6.2f%s | %s" % (k, p, "".join(cells), ratio))
        rows.append((k, p, det_means))

    print()
    for a in arms:
        if a in shapes:
            print("%-5s render %dx%d" % (a, shapes[a][1], shapes[a][0]))
    if len(set(shapes.values())) > 1:
        print("WARNING: the arms rendered at DIFFERENT sizes. The alignment crop")
        print("  differs, so the two grids are not the same pixels and every")
        print("  cross-arm cell above is suspect. Do not report these numbers.")

    if len(arms) == 2:
        n_hi = D[arms[0]]["frames"]
        n_lo = D[arms[1]]["frames"]
        print()
        print("If n_eff were PROPORTIONAL to N the detail ratio would read %.3fx"
              % (n_hi / n_lo))
        print("If the winner kept its share regardless of depth it would read 1.000x")


if __name__ == "__main__":
    main()
