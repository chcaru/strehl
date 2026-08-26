"""Is the deep-interior softening real, or is it my estimator?

residual.py reported -23.1% / -10.2% / -2.7% gradient energy in the deep subject
interior and concluded REAL SOFTENING. That conclusion is not safe, because the
pixels were selected as the top decile of the CONTROL's own gradient. Selecting
on one arm's extremes and then comparing arms is regression to the mean: any
change whatsoever, including a pure denoise, lowers the other arm's value in that
set. It is the same shape of error as the +0.845 sigma upper-envelope bias that
impeached a headline number on this project tonight.

The decisive control is to run the selection both ways round. If selecting on the
control says the blend is softer, AND selecting on the blend says the control is
softer, the difference is an artifact of selection and there is nothing there.
If the sign survives both, the softening is real.

Also reported: a symmetric selection, no selection at all, and a level-normalised
form, because the deep interior changes brightness between arms and gradient in DN
scales with level.
"""
import json
import pathlib
import numpy as np
import tifffile
from scipy import ndimage

B = pathlib.Path(r"C:\dev\strehl-out\BUILD-BLEND")
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
ERODE = 60


def luma(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} is {a.dtype}"
    return (a.astype(np.float32).mean(axis=2) if a.ndim == 3
            else a.astype(np.float32))


def subject(l):
    s = l[::4, ::4]
    hist, edges = np.histogram(s, 512)
    p = hist / hist.sum()
    om, mu = np.cumsum(p), np.cumsum(p * ((edges[:-1] + edges[1:]) / 2))
    with np.errstate(invalid="ignore", divide="ignore"):
        var = (mu[-1] * om - mu) ** 2 / (om * (1 - om))
    thr = float((edges[:-1] + edges[1:])[np.nanargmax(var)] / 2)
    m = ndimage.binary_fill_holes(l < thr)
    lab, n = ndimage.label(m)
    if n > 1:
        sz = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (1 + int(np.argmax(sz)))
    return ndimage.binary_fill_holes(m)


def grad(l):
    return np.hypot(ndimage.sobel(l, axis=1) * 0.125,
                    ndimage.sobel(l, axis=0) * 0.125)


def run(name, ctrl, blend):
    lc, lb = luma(ctrl), luma(blend)
    gain = float(np.median(lb) / np.median(lc))
    lb = lb / gain
    m = subject(lc)
    pad = np.zeros((m.shape[0] + 2, m.shape[1] + 2), bool)
    pad[1:-1, 1:-1] = m
    deep = ndimage.distance_transform_edt(pad)[1:-1, 1:-1] > ERODE
    gc, gb = grad(lc), grad(lb)

    print(f"\n{'=' * 78}\n{name}   deep interior = {deep.sum()} px, "
          f"gain-matched at {gain:.4f}")
    lvc, lvb = float(np.median(lc[deep])), float(np.median(lb[deep]))
    print(f"  median level  ctrl {lvc:.0f} DN   blend {lvb:.0f} DN  "
          f"({100 * (lvb - lvc) / lvc:+.2f}% after gain match)")
    print(f"\n  {'selection':<40}{'ctrl':>11}{'blend':>11}{'delta DN':>11}{'%':>9}")
    rows = {}
    sels = [
        ("top decile of CTRL gradient  (biased ->ctrl)", gc > np.percentile(gc[deep], 90)),
        ("top decile of BLEND gradient (biased ->blend)", gb > np.percentile(gb[deep], 90)),
        ("top decile of the MEAN gradient (symmetric)",
         (gc + gb) / 2 > np.percentile(((gc + gb) / 2)[deep], 90)),
        ("every deep-interior pixel (no selection)", np.ones_like(deep)),
    ]
    for tag, s in sels:
        sel = deep & s
        a, b = float(gc[sel].mean()), float(gb[sel].mean())
        rows[tag] = {"n": int(sel.sum()), "ctrl": a, "blend": b, "pct": 100 * (b / a - 1)}
        print(f"  {tag:<40}{a:>11.1f}{b:>11.1f}{b - a:>+11.1f}"
              f"{100 * (b / a - 1):>+9.2f}")

    fwd = rows["top decile of CTRL gradient  (biased ->ctrl)"]["pct"]
    rev = rows["top decile of BLEND gradient (biased ->blend)"]["pct"]
    sym = rows["top decile of the MEAN gradient (symmetric)"]["pct"]
    allp = rows["every deep-interior pixel (no selection)"]["pct"]
    print(f"\n  BIAS CHECK")
    print(f"    forward selection {fwd:+.2f}%   reverse selection {rev:+.2f}%")
    if fwd < 0 and rev > 0:
        print(f"    -> SIGN FLIPS. The forward number was regression to the mean.")
    else:
        print(f"    -> sign SURVIVES reversal; a real difference is present.")
    print(f"    unbiased estimates: symmetric {sym:+.2f}%, unselected {allp:+.2f}%")
    print(f"    -> deep-interior detail is "
          f"{'preserved' if sym > -2 else 'SOFTER'} by the honest estimators.")
    return {"name": name, "gain": gain, "fwd": fwd, "rev": rev,
            "sym": sym, "all": allp, "rows": rows}


def main():
    jobs = [("flower-bud-alone-cpl", "flower-bud-alone-cpl-ctrl.tif",
             "flower-bud-alone-cpl-blend.tif"),
            ("lavendar-cpl", "lavendar-cpl-ctrl.tif", "lavendar-cpl-blend.tif"),
            ("couch-fibers-cpl (do no harm)", "couch-fibers-cpl-ctrl.tif",
             "couch-fibers-cpl-blend.tif")]
    res = [run(n, B / "bm" / c, B / "bm" / b) for n, c, b in jobs]
    (OUT / "biascheck.json").write_text(json.dumps(res, indent=1))
    print(f"\nwrote {OUT / 'biascheck.json'}")


if __name__ == "__main__":
    main()
