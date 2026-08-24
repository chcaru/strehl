"""M113 K3 - why the end-to-end gain is smaller than published, and what the
ringing looks like where it would actually be seen.

K2 measured +0.0830 dex end-to-end where M95 published +0.1343 (synthetic) and
+0.1160 (real warps). Three candidate explanations, all testable on files
already on disk:

  T1 TILE SELECTION. M95 scored 40 tiles chosen as SHARPEST BY GRADIENT. I scored
     every tile on a geometric lattice. If the gain is concentrated in detailed
     tiles, the two disagree for a reason that is a CHOICE, not a defect -- and
     the honest number depends on which question is asked.
  T2 THE ELECTION MOVES. The gather feeds the focus field, so changing the kernel
     changes which frames the gate admits. Then the arms differ in NOISE as well
     as in kernel, and the flat-ROI reading is about n_eff, not sharpness.
  T3 THE GATHER IS ON HALF-RESOLUTION CFA PLANES. The metric band is in OUTPUT
     px; the kernel acts in PLANE px, which are 2x coarser after --demosaic.

And the ringing question, asked where it is visible rather than on average:
  E1 the sharpest 0.1% of edges only
  E2 UNDERSHOOT separately from overshoot -- a dark rim beside a bright hair is
     the artefact the owner would see, and an average over both signs hides it.
"""
import json
import os
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "experiments", "M95-resample", "src"))
sys.path.insert(0, os.path.join(ROOT, "experiments", "ORCH-drift-check"))
import x2_pairs as X  # noqa: E402
import kernel_crops as KC  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
R = r"C:\dev\strehl-out\M113\render"
ARMS = {"nearest": "lin-nn.tif", "catmull-rom": "lin-cr.tif", "lanczos3": "lin-l3.tif"}
TILE = 256


def luma(p):
    a = tifffile.imread(p).astype(np.float32)
    return 0.25 * a[..., 0] + 0.50 * a[..., 1] + 0.25 * a[..., 2]


def main():
    imgs = {k: luma(os.path.join(R, f)) for k, f in ARMS.items()}
    h, w = imgs["nearest"].shape
    res = {}

    # ---------------------------------------------------- T1 tile selection
    print("T1  the gain against tile detail")
    tiles = [(y, x) for y in range(h // 4, 3 * h // 4 - TILE, TILE)
             for x in range(w // 4, 3 * w // 4 - TILE, TILE)]
    # detail scored on the NEAREST arm, which is neither treatment nor control
    det = []
    for y, x in tiles:
        t = imgs["nearest"][y:y + TILE, x:x + TILE]
        det.append(float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var()))
    det = np.array(det)
    d = np.array([X.band_ratio(imgs["lanczos3"][y:y + TILE, x:x + TILE], 1.0)
                  - X.band_ratio(imgs["catmull-rom"][y:y + TILE, x:x + TILE], 1.0)
                  for y, x in tiles])
    order = np.argsort(det)[::-1]
    print(f"    {'tile set':34s} {'n':>4s} {'mean gain':>10s} {'sem':>8s}")
    sets = {}
    for lab, idx in (("all geometric tiles", np.arange(len(tiles))),
                     ("sharpest 40 by gradient", order[:40]),
                     ("sharpest 20", order[:20]),
                     ("sharpest 10", order[:10]),
                     ("flattest 40", order[-40:])):
        v = d[idx]
        sets[lab] = dict(n=int(v.size), mean=float(v.mean()),
                         sem=float(v.std(ddof=1) / np.sqrt(v.size)))
        print(f"    {lab:34s} {v.size:4d} {v.mean():+10.4f} {v.std(ddof=1)/np.sqrt(v.size):8.4f}")
    rho = float(np.corrcoef(np.log10(det + 1e-9), d)[0, 1])
    print(f"    corr(log10 tile gradient variance, per-tile gain) = {rho:+.4f}")
    res["T1"] = dict(sets=sets, corr_detail_gain=rho)

    # ------------------------------------------------------ T2 does noise move
    print("\nT2  does the kernel move the ELECTION? (flat-ROI noise is the tell)")
    best, flat = 1e18, None
    for yy in range(h // 8, 7 * h // 8 - TILE, TILE):
        for xx in range(w // 8, 7 * w // 8 - TILE, TILE):
            t = imgs["nearest"][yy:yy + TILE, xx:xx + TILE]
            v = float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var())
            if v < best:
                best, flat = v, (yy, xx)
    yy, xx = flat
    print(f"    flattest tile ({xx},{yy}), gradient var {best:.4g}")
    print(f"    {'arm':12s} {'mean DN':>10s} {'sd DN':>9s} {'hipass sd DN':>13s}")
    t2 = {}
    for k in ARMS:
        t = imgs[k][yy:yy + TILE, xx:xx + TILE].astype(np.float64)
        hp = t - np.fft.ifft2(np.fft.fft2(t) * (
            np.sqrt(np.fft.fftfreq(TILE)[:, None] ** 2 + np.fft.fftfreq(TILE)[None, :] ** 2) < 0.10)).real
        t2[k] = dict(mean=float(t.mean()), sd=float(t.std()), hp_sd=float(hp.std()))
        print(f"    {k:12s} {t.mean():10.1f} {t.std():9.3f} {hp.std():13.4f}")
    r = t2["lanczos3"]["hp_sd"] / t2["catmull-rom"]["hp_sd"]
    print(f"    lanczos3 / catmull-rom high-pass sd on a FLAT ROI = {r:.4f}x")
    print("    >1 means lanczos3 passes more noise (expected for a wider passband).")
    print("    <1 means something other than the kernel moved -- the election.")
    res["T2"] = dict(flat_xy=[int(xx), int(yy)], arms=t2, hp_ratio=float(r))

    # ---------------------------------------- T3 the same band in PLANE px
    print("\nT3  the metric band expressed in the coordinates the KERNEL acts in")
    print(f"    output grid {w}x{h}; the gather runs on CFA planes at {w//2}x{h//2}")
    print(f"    metric band {X.BAND[0]}-{X.BAND[1]} cyc/output-px  ==  "
          f"{2*X.BAND[0]:.2f}-{2*X.BAND[1]:.2f} cyc/plane-px, i.e. ABOVE plane Nyquist (0.5).")
    print("    So the band the headline is quoted in is not a band the gather can")
    print("    directly carry; what reaches it there is demosaic reconstruction.")
    # re-measure on a 2x2-binned output = the plane grid
    binned = {k: imgs[k][: (h // 2) * 2, : (w // 2) * 2].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
              for k in ARMS}
    bt = [(y, x) for y in range((h // 2) // 4, 3 * (h // 2) // 4 - TILE, TILE)
          for x in range((w // 2) // 4, 3 * (w // 2) // 4 - TILE, TILE)]
    db = np.array([X.band_ratio(binned["lanczos3"][y:y + TILE, x:x + TILE], 1.0)
                   - X.band_ratio(binned["catmull-rom"][y:y + TILE, x:x + TILE], 1.0) for y, x in bt])
    dbn = np.array([X.band_ratio(binned["nearest"][y:y + TILE, x:x + TILE], 1.0)
                    - X.band_ratio(binned["catmull-rom"][y:y + TILE, x:x + TILE], 1.0) for y, x in bt])
    print(f"    ON THE PLANE GRID (2x2 binned), n={db.size}:")
    print(f"      catmull-rom -> lanczos3 : {db.mean():+.4f} dex  sem {db.std(ddof=1)/np.sqrt(db.size):.4f}")
    print(f"      catmull-rom -> nearest  : {dbn.mean():+.4f} dex")
    res["T3"] = dict(n=int(db.size), gain=float(db.mean()),
                     sem=float(db.std(ddof=1) / np.sqrt(db.size)), nearest=float(dbn.mean()))

    # ------------------------------------------- E1/E2 ringing where it shows
    print("\nE1/E2  ringing at the SHARPEST edges, over- and under-shoot separated")
    ref = imgs["nearest"]
    e = {}
    for name, x, y, rw, rh in KC.REGIONS:
        sub = ref[y:y + rh, x:x + rw].astype(np.float64)
        lo, hi = sub.copy(), sub.copy()
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                s = np.roll(np.roll(sub, dy, axis=0), dx, axis=1)
                lo, hi = np.minimum(lo, s), np.maximum(hi, s)
        rng = np.maximum(hi - lo, 1e-6)
        g = np.hypot(np.gradient(sub, axis=0), np.gradient(sub, axis=1))
        inner = (slice(3, -3), slice(3, -3))
        thr = np.percentile(g[inner], 99.9)
        mask = g[inner] >= thr
        print(f"\n    ROI '{name}'  sharpest 0.1% edges = {mask.sum()} px, "
              f"gradient >= {thr:.0f} DN/px, median local range {np.median(rng):.0f} DN")
        print(f"      {'arm':12s} {'OVER mean DN':>13s} {'OVER p99 DN':>12s} "
              f"{'UNDER mean DN':>14s} {'UNDER p99 DN':>13s} {'UNDER %rng p99':>15s}")
        row = {}
        for k in ("catmull-rom", "lanczos3"):
            a = imgs[k][y:y + rh, x:x + rw].astype(np.float64)
            ov = np.maximum(a - hi, 0.0)[inner][mask]
            un = np.maximum(lo - a, 0.0)[inner][mask]
            rr = rng[inner][mask]
            row[k] = dict(over_mean=float(ov.mean()), over_p99=float(np.percentile(ov, 99)),
                          under_mean=float(un.mean()), under_p99=float(np.percentile(un, 99)),
                          under_p99_frac=float(np.percentile(un / rr, 99)))
            q = row[k]
            print(f"      {k:12s} {q['over_mean']:13.2f} {q['over_p99']:12.1f} "
                  f"{q['under_mean']:14.2f} {q['under_p99']:13.1f} {q['under_p99_frac']:15.4f}")
        print(f"      lanczos3/catmull-rom  over {row['lanczos3']['over_mean']/max(row['catmull-rom']['over_mean'],1e-9):.3f}x"
              f"   under {row['lanczos3']['under_mean']/max(row['catmull-rom']['under_mean'],1e-9):.3f}x")
        e[name] = dict(rows=row, n_edge_px=int(mask.sum()), grad_thr=float(thr))
    res["E"] = e

    json.dump(res, open(os.path.join(OUT, "k3_diagnose.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k3_diagnose.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
