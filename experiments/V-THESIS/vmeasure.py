"""V-THESIS: independent re-derivation of the estimation-vs-selection headline.

Shares NO code with experiments/BUILD-THESIS. Different statistic (spectral
blur-match, scene-referred), different site selection (an exhaustive
non-overlapping grid, not a top-N by |laplacian|), different noise estimator
(Immerkaer, not Donoho), different registration (anchor displacement field, not
ECC), and an EXACT Gaussian plant rather than scipy's truncated one.

SITE SELECTION.  Every non-overlapping 512 px tile of the merge frame is a
candidate. A tile is kept only if BOTH arms carry band signal above 3x their
own noise floor and the arms' content actually corresponds (NCC >= 0.55).
Nothing is ranked; nothing is chosen for being detailed. That removes the
"which arm nominated the ground" question entirely rather than answering it
with a second rule.

WHAT IS REPORTED PER SUBJECT
  VA_shipped   equivalent Gaussian blur, merge px, + = the merge resolves finer
  VA_taxed     same, with the argmax arm charged the merge's coverage rescale
  tax          what that rescale costs on its own
  VA_null      the same instrument on a PLANTED noise difference, no blur
"""
import json, pathlib, sys
import numpy as np, cv2, tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from vstat import va_blur_px, sigma_immerkaer, radial_power   # noqa: E402
from vplant import despeckle                                   # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-THESIS")
SUBJECTS = ["bee-3-cpl","bee-1-cpl","leaf-2-cpl","flowers-cpl","tweezers-cpl","flat-on-ruler-cpl"]
TILE = 512
MARGIN = 64
DS = 4
NCC_MIN = 0.55
SNR_MIN = 3.0
RNG = np.random.default_rng(20260826)


def green(p):
    return tifffile.imread(str(p))[:, :, 1].astype(np.float64)


def band_snr(t):
    """Mean noise-corrected band power divided by the flat noise level."""
    T = min(t.shape)
    s = sigma_immerkaer(t)
    w = np.outer(np.hanning(t.shape[0]), np.hanning(t.shape[1]))
    floor = s**2 * float((w*w).sum())
    kcap = int(0.80*(T//2))
    k, P, N = radial_power(t, None, kcap)
    lo, hi = max(2, int(np.ceil(T/24.0))), min(kcap, int(np.floor(T/4.0)))
    sel = slice(lo, hi+1)
    return float(np.nanmean(P[sel] - floor) / max(floor, 1e-30)), s


def tax(t, s):
    """The merge's coverage rescale, charged to a tile: crop to s, upsample back."""
    h, w = t.shape
    ch, cw = int(round(h*s)), int(round(w*s))
    y0, x0 = (h-ch)//2, (w-cw)//2
    return cv2.resize(t[y0:y0+ch, x0:x0+cw].astype(np.float32), (w, h),
                      interpolation=cv2.INTER_CUBIC).astype(np.float64)


def main():
    reg = {r["subject"]: r for r in json.loads((OUT/"register.json").read_text(encoding="utf8"))}
    OUT.mkdir(parents=True, exist_ok=True)
    allrows = []
    summary = []
    for subj in SUBJECTS:
        gm, ga = green(R/subj/"merge.tif"), green(R/subj/"argmax.tif")
        rr = reg[subj]
        s, tx, ty = rr["fitted_scale"], rr["tx"], rr["ty"]
        Ta = int(round(TILE*s))
        H, W = gm.shape
        mds = cv2.resize(gm.astype(np.float32), None, fx=1.0/DS, fy=1.0/DS, interpolation=cv2.INTER_AREA)
        ads = cv2.resize(ga.astype(np.float32), None, fx=1.0/DS, fy=1.0/DS, interpolation=cv2.INTER_AREA)
        mds = mds - cv2.blur(mds,(25,25)); ads = ads - cv2.blur(ads,(25,25))
        rows = []
        for y in range(MARGIN, H-TILE-MARGIN+1, TILE):
            for x in range(MARGIN, W-TILE-MARGIN+1, TILE):
                tm = gm[y:y+TILE, x:x+TILE]
                # predict, then refine by NCC at DS
                px, py = s*(x+TILE/2)+tx, s*(y+TILE/2)+ty
                n2 = int(round(TILE*s/DS))
                tpl = cv2.resize(mds[y//DS:y//DS+TILE//DS, x//DS:x//DS+TILE//DS], (n2,n2),
                                 interpolation=cv2.INTER_AREA)
                SR = 24
                ry0 = int(np.clip(py/DS-n2/2-SR, 0, ads.shape[0]-n2-2*SR))
                rx0 = int(np.clip(px/DS-n2/2-SR, 0, ads.shape[1]-n2-2*SR))
                regn = ads[ry0:ry0+n2+2*SR, rx0:rx0+n2+2*SR]
                if regn.shape[0] < n2 or regn.shape[1] < n2: continue
                res = cv2.matchTemplate(regn, tpl, cv2.TM_CCOEFF_NORMED)
                _, sc, _, loc = cv2.minMaxLoc(res)
                ax = int(round((rx0+loc[0])*DS)); ay = int(round((ry0+loc[1])*DS))
                if ax < 0 or ay < 0 or ax+Ta > W or ay+Ta > H: continue
                ta = ga[ay:ay+Ta, ax:ax+Ta]
                snr_m, sig_m = band_snr(tm)
                snr_a, sig_a = band_snr(ta)
                ok = (sc >= NCC_MIN) and (snr_m >= SNR_MIN) and (snr_a >= SNR_MIN)
                if not ok:
                    rows.append(dict(x=x,y=y,ax=ax,ay=ay,ncc=float(sc),snr_m=snr_m,snr_a=snr_a,kept=False))
                    continue
                v_ship = va_blur_px(tm, ta)
                tmd,_ = despeckle(tm, sig_m); tad,_ = despeckle(ta, sig_a)
                v_ds = va_blur_px(tmd, tad)
                ta_tax = tax(ta, s)
                v_tax = va_blur_px(tm, ta_tax)
                v_taxcost = va_blur_px(ta, ta_tax)
                rows.append(dict(x=x,y=y,ax=ax,ay=ay,ncc=float(sc),snr_m=snr_m,snr_a=snr_a,kept=True,
                                 sigma_m=sig_m, sigma_a=sig_a,
                                 va_shipped=v_ship, va_despeckled=v_ds,
                                 va_taxed=v_tax, tax_px=v_taxcost))
        kept = [r for r in rows if r["kept"]]
        def col(k): return np.array([r[k] for r in kept], float)
        # noise null: merge tile + noise to the measured sigma ratio, no blur
        nulls = []
        for r in kept[:8]:
            tm = gm[r["y"]:r["y"]+TILE, r["x"]:r["x"]+TILE]
            add = float(np.sqrt(max(r["sigma_a"]**2 - r["sigma_m"]**2, 0.0)))
            if add <= 0: continue
            nulls.append(va_blur_px(tm, tm + RNG.normal(0.0, add, tm.shape)))
        sig_ratio = float(np.median(col("sigma_a")/col("sigma_m"))) if kept else float("nan")
        rec = dict(subject=subj, scale=s, Tm=TILE, Ta=Ta,
                   n_candidate=len(rows), n_kept=len(kept),
                   median_ncc=float(np.median(col("ncc"))) if kept else None,
                   sigma_ratio=sig_ratio,
                   va_shipped_median=float(np.median(col("va_shipped"))) if kept else None,
                   va_shipped_iqr=[float(np.percentile(col("va_shipped"),25)),
                                   float(np.percentile(col("va_shipped"),75))] if kept else None,
                   va_despeckled_median=float(np.median(col("va_despeckled"))) if kept else None,
                   va_taxed_median=float(np.median(col("va_taxed"))) if kept else None,
                   tax_px_median=float(np.median(col("tax_px"))) if kept else None,
                   va_null_median=float(np.median(nulls)) if nulls else None,
                   n_null=len(nulls), tiles=rows)
        summary.append(rec); allrows.append(rec)
        print(f"\n=== {subj}   scale {s:.4f}  Tm={TILE} Ta={Ta}  "
              f"tiles {len(kept)}/{len(rows)} kept  medNCC {rec['median_ncc']}")
        if kept:
            v = col("va_shipped")
            print(f"    sigma argmax/merge      {sig_ratio:.3f}")
            print(f"    VA shipped   median {np.median(v):+.3f} px   IQR [{np.percentile(v,25):+.3f},{np.percentile(v,75):+.3f}]   "
                  f"n>0 {int((v>0).sum())}/{len(v)}")
            print(f"    VA despeckled median {np.median(col('va_despeckled')):+.3f} px")
            print(f"    VA argmax-taxed median {np.median(col('va_taxed')):+.3f} px   "
                  f"(the tax alone costs {np.median(col('tax_px')):+.3f} px)")
            print(f"    VA NOISE NULL median  {rec['va_null_median']:+.3f} px  (n={len(nulls)})")
    (OUT/"vmeasure.json").write_text(json.dumps(summary, indent=1), encoding="utf8")
    print(f"\nwrote {OUT/'vmeasure.json'}")


if __name__ == "__main__":
    main()
