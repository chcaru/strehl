"""Level-invariant sharpness: the do-no-harm number that survives.

interiorlook.py showed the four largest gradient decreases inside flower-bud's
subject. In all four the control holds the artifact - hard-edged flat pale
plateaus cutting across plant material - and the blend holds plant. In two of
them the level collapses from 20710 DN to 1417 DN and from 17009 DN to 3952 DN,
because a spurious bright wash is being removed.

Gradient magnitude in DN scales with level. A region 14.6x darker cannot carry
the same absolute edge energy no matter how sharp it is, so mean |grad| in DN was
measuring brightness, not sharpness, and the -16% is an artefact of that.

The level-invariant form is local Weber contrast: |grad| divided by the local mean
level. It answers "how much contrast does the structure carry relative to its own
illumination", which is the question do-no-harm is actually asking.

Reported alongside absolute DN levels, per tonight's rule.
"""
import json
import pathlib
import numpy as np
import tifffile
from scipy import ndimage

B = pathlib.Path(r"C:\dev\strehl-out\BUILD-BLEND\bm")
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
ERODE = 60
FLOOR = 200.0     # DN; keeps the ratio finite in true black


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
    sz = ndimage.sum(m, lab, range(1, n + 1))
    return ndimage.binary_fill_holes(lab == (1 + int(np.argmax(sz))))


def contrast(l):
    g = np.hypot(ndimage.sobel(l, axis=1) * 0.125,
                 ndimage.sobel(l, axis=0) * 0.125)
    return g / np.maximum(ndimage.uniform_filter(l, 33), FLOOR)


def run(name, ctrl, blend):
    lc, lb = luma(ctrl), luma(blend)
    lb = lb / (float(np.median(lb)) / float(np.median(lc)))
    m = subject(lc)
    pad = np.zeros((m.shape[0] + 2, m.shape[1] + 2), bool)
    pad[1:-1, 1:-1] = m
    deep = ndimage.distance_transform_edt(pad)[1:-1, 1:-1] > ERODE
    cc, cb = contrast(lc), contrast(lb)

    print(f"\n{'=' * 76}\n{name}   deep interior {deep.sum()} px")
    print(f"  median level   ctrl {np.median(lc[deep]):8.0f} DN"
          f"   blend {np.median(lb[deep]):8.0f} DN")
    print(f"\n  local Weber contrast |grad| / local mean level (level-invariant)")
    print(f"  {'selection':<38}{'ctrl':>11}{'blend':>11}{'%':>9}")
    out = {}
    sym = (cc + cb) / 2
    for tag, sel in (("top decile of the MEAN (symmetric)",
                      deep & (sym > np.percentile(sym[deep], 90))),
                     ("every deep-interior pixel", deep),
                     ("top decile of CTRL  (biased ->ctrl)",
                      deep & (cc > np.percentile(cc[deep], 90))),
                     ("top decile of BLEND (biased ->blend)",
                      deep & (cb > np.percentile(cb[deep], 90)))):
        a, b = float(cc[sel].mean()), float(cb[sel].mean())
        out[tag] = {"ctrl": a, "blend": b, "pct": 100 * (b / a - 1)}
        print(f"  {tag:<38}{a:>11.5f}{b:>11.5f}{100 * (b / a - 1):>+9.2f}")

    s = out["top decile of the MEAN (symmetric)"]["pct"]
    u = out["every deep-interior pixel"]["pct"]
    f = out["top decile of CTRL  (biased ->ctrl)"]["pct"]
    r = out["top decile of BLEND (biased ->blend)"]["pct"]
    print(f"\n  bias control: forward {f:+.2f}%  reverse {r:+.2f}%  -> "
          f"{'sign flips, selection artefact' if f * r < 0 else 'sign survives'}")
    print(f"  VERDICT  unbiased: symmetric {s:+.2f}%, unselected {u:+.2f}%")
    print(f"    -> subject detail is "
          f"{'PRESERVED or improved' if min(s, u) > -3 else 'SOFTER'} "
          f"by the level-invariant measure")
    return {"name": name, "rows": out, "sym": s, "all": u}


def main():
    jobs = [("flower-bud-alone-cpl", "flower-bud-alone-cpl-ctrl.tif",
             "flower-bud-alone-cpl-blend.tif"),
            ("lavendar-cpl", "lavendar-cpl-ctrl.tif", "lavendar-cpl-blend.tif"),
            ("couch-fibers-cpl (do no harm)", "couch-fibers-cpl-ctrl.tif",
             "couch-fibers-cpl-blend.tif")]
    res = [run(n, B / c, B / b) for n, c, b in jobs]
    (OUT / "weber.json").write_text(json.dumps(res, indent=1))
    print(f"\nwrote {OUT / 'weber.json'}")


if __name__ == "__main__":
    main()
