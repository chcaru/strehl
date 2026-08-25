"""M120d step 24 -- T1 re-run with the correct validation reference, plus the
unifying test that step 23's refusal exposed.

WHY 23's T1 REFUSED: it compared gate-4 n_eff over the whole background mask
(57.9) against a reference (166.8) that step 19 measured over the REGISTERED
ROI. Re-checked: on the registered ROI the cached field gates to 166.8 exactly.
The field and the gating were right; my reference was the wrong region. The
refusal was correct behaviour and the diagnosis is benign.

WHAT IT EXPOSED, which is worth more than the original test: admission breadth
is wildly non-uniform across the background -- ROI median 193 frames, whole
background median 27. The shipped merge is therefore NOT "an average of 167
frames" everywhere; in much of the background it is close to a single-winner
election, which is exactly the regime that manufactures structure.

=====================================================================
PRE-REGISTERED, WRITTEN BEFORE THE RUN
=====================================================================

T1 (as in step 23, ROI-validated): background luma vs effective elected index.
  CONFIRM |rho| > 0.3 at gate 0 with null |rho| < 0.1;  REFUTE if |rho| < 0.1.

T3 (new, and it unifies P4 with ORCH's photometric result): if the defect is
owned by the single-winner election, then manufactured structure should be
worst where ADMISSION IS NARROWEST. Regress the step-22 ratio
R = lapRMS(gate4)/lapRMS(plain mean 299) on mean n_eff over the same 40 windows.
  CONFIRM : rho(R, n_eff) < -0.3, p < 0.05.
  REFUTE  : |rho| < 0.15, or rho positive.
  If T3 confirms, then n_eff also mediates the distance effect found in step 25
  (near silhouette -> real structure -> fewer ties -> narrow admission), and I
  will report the partial correlations to test that mediation explicitly.

VALIDATION GATE: n_eff on the REGISTERED ROI must be 166.8 +/- 5%.
"""
import json
import numpy as np
from scipy import ndimage as ndi, stats
from pathlib import Path

C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
UNIT = np.sqrt(2.0) * 0.015214
WIN = 96


def main():
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    field = np.load(C / "bee3-leg-field.npy", mmap_mode="r")
    K, H, W = luma.shape
    bg = np.load(OUT / "m1_bg_mask.npy")
    fmax = np.load(OUT / "m9_fmax.npy")
    den4 = np.load(OUT / "m9_den_gate4.npy")

    roi = np.zeros((H, W), bool)
    roi[476:604, 442:570] = True
    n_roi = float(den4[roi].mean())
    ok = abs(n_roi - 166.8) / 166.8 < 0.05
    print(f"VALIDATION GATE: gate-4 n_eff on registered ROI = {n_roi:.1f} "
          f"(reference 166.8) -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    print(f"  admission is NON-UNIFORM: background n_eff median "
          f"{np.median(den4[bg]):.0f}, ROI median {np.median(den4[roi]):.0f}, "
          f"p1-p99 {np.percentile(den4[bg],1):.0f}-{np.percentile(den4[bg],99):.0f}\n")

    # ---------- T1 ----------
    print("=" * 72)
    print("T1  DOES BACKGROUND LUMA TRACK THE ELECTED FRAME?  (gate stated per row)")
    print("=" * 72)
    out_t1 = {}
    for gate in (0.0, 4.0):
        thr = fmax - gate * UNIT
        num = np.zeros((H, W), np.float64)
        den = np.zeros((H, W), np.float64)
        lsum = np.zeros((H, W), np.float64)
        for k in range(K):
            adm = np.asarray(field[k], np.float32) >= thr
            num += adm * k
            den += adm
            lsum += adm * np.asarray(luma[k], np.float32)
        eff = num / np.maximum(den, 1)
        merged = lsum / np.maximum(den, 1)
        x, y = eff[bg], merged[bg]
        rho = stats.spearmanr(x, y)
        yn = np.roll(np.roll(merged, 331, 0), 557, 1)[bg]
        rn = stats.spearmanr(x, yn)
        sl, ic, rv, _, _ = stats.linregress(x, y)
        lo, hi = np.percentile(x, [1, 99])
        swing = abs(sl) * (hi - lo)
        print(f"\n  GATE {gate:.0f}   n_eff(bg) {den[bg].mean():6.1f}   "
              f"effective-index sd {eff[bg].std():5.1f}")
        print(f"    luma vs effective index : rho {rho.statistic:+.4f}  p {rho.pvalue:.3g}"
              f"   slope {sl:+.3f} DN/frame")
        print(f"    NULL (merged shifted)   : rho {rn.statistic:+.4f}  p {rn.pvalue:.3g}")
        print(f"    implied level swing across elected-index range = {swing:.1f} DN "
              f"= {100*swing/np.median(y):.2f}% of median background luma")
        out_t1[str(gate)] = dict(rho=float(rho.statistic), rho_null=float(rn.statistic),
                                 slope=float(sl), swing=float(swing),
                                 swing_pct=float(100 * swing / np.median(y)),
                                 n_eff=float(den[bg].mean()))
        if gate == 4.0:
            np.save(OUT / "m9_eff_index_gate4.npy", eff.astype(np.float32))
    r0 = out_t1["0.0"]
    v1 = ("CHAIN CONFIRMED" if abs(r0["rho"]) > 0.3 and abs(r0["rho_null"]) < 0.1
          else "CHAIN BROKEN" if abs(r0["rho"]) < 0.1 else "EQUIVOCAL")
    print(f"\n  PRE-REGISTERED VERDICT (T1): {v1}")
    print(f"  ORCH measured drift of 3.2-8.4% p-p over 23 frames; the election here "
          f"spans\n  {out_t1['0.0']['swing_pct']:.2f}% at gate 0 and "
          f"{out_t1['4.0']['swing_pct']:.2f}% at gate 4 across the elected-index range.")

    # ---------- T3 ----------
    print("\n" + "=" * 72)
    print("T3  IS MANUFACTURED STRUCTURE WORST WHERE ADMISSION IS NARROWEST?")
    print("=" * 72)
    rows = json.load(open("m6_localisation.json"))["rows"]
    R4 = np.array(json.load(open("m8_p4.json"))["R4"])
    ne = np.array([den4[r["y"]:r["y"] + WIN, r["x"]:r["x"] + WIN].mean() for r in rows])
    ds = np.array([r["dist"] for r in rows])
    mg = np.array([r["margin"] for r in rows])
    rn_ = stats.spearmanr(ne, R4)
    print(f"  R4 vs n_eff                  rho {rn_.statistic:+.4f}  p {rn_.pvalue:.3g}"
          f"   (n={len(R4)})")
    print(f"  n_eff range over windows     {ne.min():.0f} - {ne.max():.0f} frames "
          f"(median {np.median(ne):.0f})")
    rnd = stats.spearmanr(ne, ds)
    print(f"  n_eff vs distance-to-silhouette rho {rnd.statistic:+.4f} p {rnd.pvalue:.3g}"
          f"  <- tests the mediation story")

    def partial(a, b, ctrl):
        ra, rb, rc = (stats.rankdata(v) for v in (a, b, ctrl))
        def res(v, c):
            A = np.vstack([c, np.ones_like(c)]).T
            return v - A @ np.linalg.lstsq(A, v, rcond=None)[0]
        return float(np.corrcoef(res(ra, rc), res(rb, rc))[0, 1])
    p_ne = partial(R4, ne, ds)
    p_ds = partial(R4, ds, ne)
    print(f"  partial R4 vs n_eff    | distance = {p_ne:+.4f}")
    print(f"  partial R4 vs distance | n_eff    = {p_ds:+.4f}")
    v3 = ("CONFIRMED" if rn_.statistic < -0.3 and rn_.pvalue < 0.05
          else "REFUTED" if (abs(rn_.statistic) < 0.15 or rn_.statistic > 0) else "EQUIVOCAL")
    print(f"\n  PRE-REGISTERED VERDICT (T3): {v3}")
    if v3 == "CONFIRMED":
        med = np.median(ne)
        print(f"  split at median n_eff {med:.0f}: narrow-admission windows R = "
              f"{R4[ne<=med].mean():.3f}, broad-admission windows R = {R4[ne>med].mean():.3f}")

    json.dump(dict(t1=out_t1, t1_verdict=v1,
                   t3=dict(rho=float(rn_.statistic), p=float(rn_.pvalue),
                           rho_ne_dist=float(rnd.statistic), partial_ne=p_ne,
                           partial_dist=p_ds, verdict=v3,
                           n_eff=ne.tolist())),
              open("m10_link.json", "w"), indent=1)
    print("\nwrote m10_link.json")


if __name__ == "__main__":
    main()
