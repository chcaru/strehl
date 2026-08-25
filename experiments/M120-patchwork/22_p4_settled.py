"""M120b step 22 -- P4 settled with a statistic that needs no exotic moment.

Step 21 exonerated ORCH's kurtosis instrument (a plain mean of 299 frames reads
0.04, 0/40 over bar), so the localisation is real. But kurtosis is a shape moment
and hard to reason about. Step 20's pictures suggested a plainer statistic:

    R = lapRMS(shipped gate 4) / lapRMS(plain mean of all 299 frames)

The plain mean is the right reference: constant weights, so it manufactures
nothing, and it averages 299 frames against the gate's ~167, so the two have
comparable noise floors. R > 1 is manufactured fine structure, measured against
an arm that cannot manufacture any. R needs no bar calibration and no plant.

Question: is R predicted by MARGIN (ORCH's mechanism) or by DISTANCE TO THE
SILHOUETTE (halo)?
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
WIN = 96


def lap_rms(a):
    return float(np.sqrt((ndi.laplace(np.asarray(a, np.float64)) ** 2).mean()))


def main():
    rows = json.load(open("m6_localisation.json"))["rows"]
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    K = luma.shape[0]
    for nm, f in (("g4", "armM4-gate4-binlin.tif"), ("g0", "armM-gate0-binlin.tif")):
        a = tifffile.imread(M93 / f)
        assert a.dtype == np.uint16, (f, a.dtype)
    G4 = tifffile.imread(M93 / "armM4-gate4-binlin.tif")[
        BOX[0]:BOX[1], BOX[2]:BOX[3], 1].astype(np.float32)
    G0 = tifffile.imread(M93 / "armM-gate0-binlin.tif")[
        BOX[0]:BOX[1], BOX[2]:BOX[3], 1].astype(np.float32)

    R4, R0 = [], []
    for r in rows:
        s = (slice(r["y"], r["y"] + WIN), slice(r["x"], r["x"] + WIN))
        pm = np.array(luma[:, s[0], s[1]], np.float32).mean(axis=0) * 4.4137
        d = lap_rms(pm)
        R4.append(lap_rms(G4[s]) / d)
        R0.append(lap_rms(G0[s]) / d)
    R4, R0 = np.array(R4), np.array(R0)
    mg = np.array([r["margin"] for r in rows])
    ds = np.array([r["dist"] for r in rows])

    print(f"R = lapRMS(arm) / lapRMS(plain mean of {K}), over {len(rows)} pure-background "
          f"96px windows\n")
    print(f"{'arm':22}{'R median':>11}{'R worst':>10}{'R>1.25':>10}{'R>2':>8}")
    for nm, R in (("gate 0 (neg control)", R0), ("gate 4 (SHIPPED)", R4)):
        print(f"{nm:22}{np.median(R):>11.3f}{R.max():>10.3f}"
              f"{int((R>1.25).sum()):>6}/{len(R)}{int((R>2).sum()):>5}/{len(R)}")

    print(f"\nP4  WHAT PREDICTS A ROUGH WINDOW ON THE SHIPPED ARM?")
    rm, rd = stats.spearmanr(mg, R4), stats.spearmanr(ds, R4)
    print(f"  R4 vs margin                 rho {rm.statistic:+.4f}  p {rm.pvalue:.4g}")
    print(f"  R4 vs distance-to-silhouette rho {rd.statistic:+.4f}  p {rd.pvalue:.4g}")

    def partial(a, b, ctrl):
        ra, rb, rc = (stats.rankdata(v) for v in (a, b, ctrl))
        def res(v, c):
            A = np.vstack([c, np.ones_like(c)]).T
            return v - A @ np.linalg.lstsq(A, v, rcond=None)[0]
        return float(np.corrcoef(res(ra, rc), res(rb, rc))[0, 1])
    pm_ = partial(R4, mg, ds)
    pd_ = partial(R4, ds, mg)
    print(f"  partial R4 vs margin   | distance = {pm_:+.4f}")
    print(f"  partial R4 vs distance | margin   = {pd_:+.4f}")

    rm0, rd0 = stats.spearmanr(mg, R0), stats.spearmanr(ds, R0)
    print(f"\n  same on the gate-0 negative control (where the mosaic IS universal):")
    print(f"  R0 vs margin   rho {rm0.statistic:+.4f} p {rm0.pvalue:.4g}   "
          f"R0 vs distance rho {rd0.statistic:+.4f} p {rd0.pvalue:.4g}")

    med = np.median(ds)
    print(f"\n  split at median distance {med:.1f} px:")
    print(f"{'':18}{'R gate0':>10}{'R gate4':>10}{'gate benefit':>14}")
    for nm, m_ in (("near silhouette", ds <= med), ("far from it", ds > med)):
        print(f"  {nm:16}{R0[m_].mean():>10.3f}{R4[m_].mean():>10.3f}"
              f"{100*(R4[m_].mean()-R0[m_].mean())/R0[m_].mean():>13.1f}%")

    verdict = ("HALO-DRIVEN (distance wins)" if abs(pd_) > abs(pm_) + 0.15 else
               "MECHANISM-DRIVEN (margin wins)" if abs(pm_) > abs(pd_) + 0.15 else
               "UNDECIDED on this evidence")
    print(f"\n  VERDICT ON P4: {verdict}")
    print(f"  CAVEAT: these windows are all pure background, so margin spans only "
          f"{mg.min():.2f}-{mg.max():.2f} gate units (a factor of {mg.max()/mg.min():.1f}).")
    print(f"  The margin test therefore has RESTRICTED RANGE and low power; a null on")
    print(f"  margin here is weaker evidence than the positive on distance.")

    json.dump(dict(R4=R4.tolist(), R0=R0.tolist(),
                   rho_R4_margin=[float(rm.statistic), float(rm.pvalue)],
                   rho_R4_dist=[float(rd.statistic), float(rd.pvalue)],
                   partial_margin=pm_, partial_dist=pd_,
                   margin_range=[float(mg.min()), float(mg.max())],
                   verdict=verdict), open("m8_p4.json", "w"), indent=1)
    print("\nwrote m8_p4.json")


if __name__ == "__main__":
    main()
