"""Partition the blend arm's gradient-energy change by region.

blendlook.py measured -19.1% gradient energy on flower-bud's top-decile edges
and that number cannot be read as detail loss, because it is confounded by
construction. Section 11.4 MEASURED that the control's band edge carries 1853 DN
of gradient against <=243 DN in any source frame: the control contains a
manufactured seam with 7.6x more edge energy than the data has. Removing a
manufactured edge MUST reduce gradient energy. A metric that scores that as
softening is scoring the cure as the disease.

So partition. The collar around the silhouette is where the artifact lived. The
deep interior, eroded well clear of it, is where real photographed detail lives.
If the blend is softer in the deep interior too, that is real loss and my lane
still has something to argue about. If it is flat or sharper there, the whole
-19.1% is artifact removal.

Absolute DN throughout, per tonight's rule: an additive bias is invisible in both
an error and a ratio.
"""
import json
import pathlib
import numpy as np
import tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\pics")
B = pathlib.Path(r"C:\dev\strehl-out\BUILD-BLEND")
ERODE = 60      # px clear of the silhouette before "deep interior" starts
COLLAR = 40     # px outward from the silhouette: where the artifact lived


def luma(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} is {a.dtype}"
    return (a.astype(np.float32).mean(axis=2) if a.ndim == 3
            else a.astype(np.float32))


def subject(l):
    """Otsu on a downsample, then the largest filled component."""
    s = l[::4, ::4]
    hist, edges = np.histogram(s, 512)
    p = hist / hist.sum()
    om = np.cumsum(p)
    mu = np.cumsum(p * ((edges[:-1] + edges[1:]) / 2))
    with np.errstate(invalid="ignore", divide="ignore"):
        var = (mu[-1] * om - mu) ** 2 / (om * (1 - om))
    thr = float((edges[:-1] + edges[1:])[np.nanargmax(var)] / 2)
    m = ndimage.binary_fill_holes(l < thr)      # subject is darker than sweep
    lab, n = ndimage.label(m)
    if n > 1:
        sz = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (1 + int(np.argmax(sz)))
    return ndimage.binary_fill_holes(m), thr


def grad(l):
    gx = ndimage.sobel(l, axis=1) * 0.125
    gy = ndimage.sobel(l, axis=0) * 0.125
    return np.hypot(gx, gy)


def run(name, ctrl, blend):
    lc, lb = luma(ctrl), luma(blend)
    assert lc.shape == lb.shape
    gain = float(np.median(lb) / np.median(lc))
    m, thr = subject(lc)

    pad = np.zeros((m.shape[0] + 2, m.shape[1] + 2), bool)
    pad[1:-1, 1:-1] = m
    dout = ndimage.distance_transform_edt(~pad)[1:-1, 1:-1]
    din = ndimage.distance_transform_edt(pad)[1:-1, 1:-1]

    deep = din > ERODE
    collar = (~m) & (dout > 0) & (dout <= COLLAR)
    far = dout > 400

    gc, gb = grad(lc), grad(lb / gain)
    print(f"\n{'=' * 74}\n{name}")
    print(f"  subject {m.mean() * 100:.1f}% of frame (Otsu thr {thr:.0f} DN), "
          f"gain {gain:.4f}")
    print(f"  {'region':<34}{'n px':>10}{'ctrl DN/px':>13}"
          f"{'blend DN/px':>13}{'delta DN':>11}{'ratio':>9}")
    rows = {}
    for tag, reg, top in (
            (f"deep interior (eroded {ERODE} px)", deep, True),
            (f"collar 0-{COLLAR} px outside", collar, False),
            ("far backdrop (>400 px)", far, False)):
        if reg.sum() < 1000:
            print(f"  {tag:<34}{'(empty)':>10}")
            continue
        sel = reg & (gc > np.percentile(gc[reg], 90)) if top else reg
        a, b = float(gc[sel].mean()), float(gb[sel].mean())
        rows[tag] = {"n": int(sel.sum()), "ctrl": a, "blend": b,
                     "delta": b - a, "ratio": b / a}
        print(f"  {tag:<34}{sel.sum():>10}{a:>13.1f}{b:>13.1f}"
              f"{b - a:>+11.1f}{b / a:>9.4f}")

    print(f"\n  absolute levels (median DN), the quantity a ratio cannot show:")
    for tag, reg in (("deep interior", deep), ("collar", collar),
                     ("far backdrop", far)):
        if reg.sum() < 1000:
            continue
        a, b = float(np.median(lc[reg])), float(np.median(lb[reg]))
        print(f"    {tag:<20}ctrl {a:>9.0f} DN   blend {b:>9.0f} DN"
              f"   {b - a:>+8.0f} DN = {100 * (b - a) / a:+6.2f}%")

    di = rows.get(f"deep interior (eroded {ERODE} px)")
    if di:
        print(f"\n  VERDICT")
        print(f"    deep-interior detail: {di['delta']:+.1f} DN/px "
              f"= {100 * (di['ratio'] - 1):+.1f}%")
        if di["ratio"] >= 0.98:
            print("    -> no measurable detail loss where the real photograph is.")
        else:
            print("    -> REAL SOFTENING inside the subject. A residual for my lane.")
    return {"name": name, "gain": gain, "rows": rows}


def main():
    jobs = [("flower-bud-alone-cpl", "flower-bud-alone-cpl-ctrl.tif",
             "flower-bud-alone-cpl-blend.tif"),
            ("lavendar-cpl", "lavendar-cpl-ctrl.tif", "lavendar-cpl-blend.tif"),
            ("couch-fibers-cpl (do no harm)", "couch-fibers-cpl-ctrl.tif",
             "couch-fibers-cpl-blend.tif")]
    res = [run(n, B / "bm" / c, B / "bm" / b) for n, c, b in jobs]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT.parent / "residual.json").write_text(json.dumps(res, indent=1))

    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
    for a_, r in zip(ax, res):
        tags = list(r["rows"])
        vals = [100 * (r["rows"][t]["ratio"] - 1) for t in tags]
        a_.bar(range(len(tags)), vals,
               color=["seagreen" if v >= -2 else "crimson" for v in vals])
        a_.axhline(0, color="k", lw=.8)
        a_.set_xticks(range(len(tags)))
        a_.set_xticklabels([t.split("(")[0].strip() for t in tags],
                           rotation=20, ha="right", fontsize=8)
        a_.set_ylabel("gradient energy, blend vs ctrl (%)")
        a_.set_title(r["name"], fontsize=10)
        a_.grid(alpha=.3, axis="y")
    fig.suptitle("Where the blend arm changes edge energy: artifact collar vs "
                 "real detail", fontsize=13)
    plt.tight_layout()
    p = OUT / "BLEND-residual.png"
    plt.savefig(p, dpi=80)
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
