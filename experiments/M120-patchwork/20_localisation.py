"""M120b step 20 -- P4 (localisation) and P3-sharpened (is the residual halo?).

ORCH: on the shipped render the defect is in ~3 of 12 background windows, not all
of them. What distinguishes a window that patchworks from one that does not?

  mechanism predicts  -> the flattest-response windows, i.e. LOW MARGIN
  halo predicts       -> the windows near the subject silhouette, i.e. LOW DISTANCE

These are separable, and they are separable on this grid because margin, n_eff,
the background mask and the shipped gate-4 render are all co-registered here
(M87 box pixel (y,x) == shipped-grid pixel (1178+y, 278+x), NCC 1.0000, M120 s.3).

Measured on the real Rust `armM4-gate4-binlin.tif` -- the SHIPPED arm -- with
gate 0 alongside for the "which windows does the gate fix" question.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage as ndi, stats
from pathlib import Path

C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
M93 = Path(r"C:\dev\strehl-out\M93-out")
OUT = Path(r"C:\dev\strehl-out\M120")
BOX = (1178, 1922, 278, 1422)
WIN, STRIDE = 96, 48


def contrast(a):
    a = np.asarray(a, np.float32)
    bp = ndi.gaussian_filter(a, 2.0) - ndi.gaussian_filter(a, 8.0)
    return float(np.sqrt((bp * bp).mean()) / a.mean())


def lap_kurt(a):
    """ORCH's instrument: excess kurtosis of the Laplacian."""
    l = ndi.laplace(np.asarray(a, np.float64))
    return float(stats.kurtosis(l.ravel(), fisher=True, bias=False))


def main():
    bg = np.load(OUT / "m1_bg_mask.npy")
    margin = np.load(OUT / "m1_margin.npy")
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    K, H, W = luma.shape

    g4 = tifffile.imread(M93 / "armM4-gate4-binlin.tif")
    g0 = tifffile.imread(M93 / "armM-gate0-binlin.tif")
    assert g4.dtype == np.uint16 and g0.dtype == np.uint16
    G4 = g4[BOX[0]:BOX[1], BOX[2]:BOX[3], 1].astype(np.float32)
    G0 = g0[BOX[0]:BOX[1], BOX[2]:BOX[3], 1].astype(np.float32)
    print(f"shipped gate-4 render over the M87 box: {G4.shape}, "
          f"min {G4.min():.0f} max {G4.max():.0f}")

    # distance from every pixel to the nearest NON-background pixel (the silhouette)
    dist = ndi.distance_transform_edt(bg)

    rows = []
    for y in range(0, H - WIN, STRIDE):
        for x in range(0, W - WIN, STRIDE):
            s = (slice(y, y + WIN), slice(x, x + WIN))
            fill = float(bg[s].mean())
            if fill < 0.98:
                continue
            cube = np.array(luma[:, y:y + WIN, x:x + WIN], np.float32)
            den = max(contrast(cube[k]) for k in range(K))
            rows.append(dict(
                y=int(y), x=int(x),
                q4=contrast(G4[s]) / den, q0=contrast(G0[s]) / den,
                k4=lap_kurt(G4[s]), k0=lap_kurt(G0[s]),
                k_single=lap_kurt(cube[K // 2]),
                margin=float(np.median(margin[s])),
                dist=float(np.median(dist[s])),
                level=float(G4[s].mean()),
            ))
    print(f"{len(rows)} pure-background windows of {WIN}px (>=98% background fill)")

    q4 = np.array([r["q4"] for r in rows])
    k4 = np.array([r["k4"] for r in rows])
    k0 = np.array([r["k0"] for r in rows])
    ks = np.array([r["k_single"] for r in rows])
    mg = np.array([r["margin"] for r in rows])
    ds = np.array([r["dist"] for r in rows])

    print(f"\nORCH's instrument on these windows (Laplacian excess kurtosis):")
    print(f"  single input frame : median {np.median(ks):7.2f}  worst {ks.max():7.2f}  "
          f"over bar(10) {int((ks>10).sum())}/{len(ks)}")
    print(f"  gate 0             : median {np.median(k0):7.2f}  worst {k0.max():7.2f}  "
          f"over bar(10) {int((k0>10).sum())}/{len(k0)}")
    print(f"  gate 4 (SHIPPED)   : median {np.median(k4):7.2f}  worst {k4.max():7.2f}  "
          f"over bar(10) {int((k4>10).sum())}/{len(k4)}")
    print(f"  -> replicates ORCH's shape: localised on the shipped arm, "
          f"{100*(k4>10).mean():.0f}% of windows")

    print(f"\nP4  WHAT PREDICTS A PATCHWORKED WINDOW?  (n={len(rows)})")
    print(f"{'severity':>12}{'vs margin':>26}{'vs dist-to-silhouette':>28}")
    out = {}
    for nm, sev in (("Q (gate 4)", q4), ("kurtosis (gate 4)", k4), ("kurtosis (gate 0)", k0)):
        rm = stats.spearmanr(mg, sev)
        rd = stats.spearmanr(ds, sev)
        out[nm] = dict(vs_margin=[float(rm.statistic), float(rm.pvalue)],
                       vs_dist=[float(rd.statistic), float(rd.pvalue)])
        print(f"{nm:>12}   rho {rm.statistic:+.4f} (p={rm.pvalue:8.2e})   "
              f"rho {rd.statistic:+.4f} (p={rd.pvalue:8.2e})")

    # partial: does distance still predict once margin is controlled, and vice versa?
    def partial(a, b, ctrl):
        ra = stats.rankdata(a); rb = stats.rankdata(b); rc = stats.rankdata(ctrl)
        def res(v, c):
            A = np.vstack([c, np.ones_like(c)]).T
            return v - A @ np.linalg.lstsq(A, v, rcond=None)[0]
        return float(np.corrcoef(res(ra, rc), res(rb, rc))[0, 1])
    print(f"\n  partial (Spearman, controlling for the other):")
    print(f"    Q vs margin | distance   = {partial(q4, mg, ds):+.4f}")
    print(f"    Q vs distance | margin   = {partial(q4, ds, mg):+.4f}")
    print(f"    kurt vs margin | distance= {partial(k4, mg, ds):+.4f}")
    print(f"    kurt vs distance | margin= {partial(k4, ds, mg):+.4f}")
    out["partial"] = dict(q_margin_given_dist=partial(q4, mg, ds),
                          q_dist_given_margin=partial(q4, ds, mg),
                          k_margin_given_dist=partial(k4, mg, ds),
                          k_dist_given_margin=partial(k4, ds, mg))

    # the worst windows, named
    print(f"\n  the 6 worst windows by gate-4 kurtosis:")
    print(f"    {'y':>5}{'x':>6}{'kurt4':>9}{'kurt0':>9}{'Q4':>8}{'margin':>9}{'dist':>8}")
    for r in sorted(rows, key=lambda r: -r["k4"])[:6]:
        print(f"    {r['y']:>5}{r['x']:>6}{r['k4']:>9.2f}{r['k0']:>9.2f}"
              f"{r['q4']:>8.2f}{r['margin']:>9.2f}{r['dist']:>8.1f}")
    print(f"  the 6 quietest:")
    for r in sorted(rows, key=lambda r: r["k4"])[:6]:
        print(f"    {r['y']:>5}{r['x']:>6}{r['k4']:>9.2f}{r['k0']:>9.2f}"
              f"{r['q4']:>8.2f}{r['margin']:>9.2f}{r['dist']:>8.1f}")

    # P3-sharpened: split by distance, does the gate's benefit differ?
    med = np.median(ds)
    near, far = ds <= med, ds > med
    print(f"\nP3-sharpened  DOES THE GATE HELP LESS NEAR THE SILHOUETTE?")
    print(f"  (split at median distance {med:.1f} px)")
    print(f"{'':14}{'Q gate0':>10}{'Q gate4':>10}{'reduction':>12}{'kurt4>10':>11}")
    for nm, m_ in (("near silhouette", near), ("far from it", far)):
        q0s, q4s = np.array([r['q0'] for r in rows])[m_], q4[m_]
        print(f"  {nm:12}{q0s.mean():>10.3f}{q4s.mean():>10.3f}"
              f"{100*(q4s.mean()-q0s.mean())/q0s.mean():>11.1f}%"
              f"{int((k4[m_]>10).sum()):>7}/{int(m_.sum())}")
        out[nm] = dict(q0=float(q0s.mean()), q4=float(q4s.mean()),
                       viol=int((k4[m_] > 10).sum()), n=int(m_.sum()))

    json.dump({"n_windows": len(rows), "win": WIN, "corr": out, "rows": rows},
              open("m6_localisation.json", "w"), indent=1)
    print("\nwrote m6_localisation.json")


if __name__ == "__main__":
    main()
