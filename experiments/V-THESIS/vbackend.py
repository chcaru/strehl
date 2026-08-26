"""Is the detail null BACKEND-INVARIANT?

BUILD-THESIS's six headline subjects all ran `pyramid (default)` -- verified
from the run banners, not the argv. But it also rendered three subjects with
`--merge estimator` explicitly, and those renders survive. So the question the
product actually needs can be answered without re-rendering anything:

    does --merge pyramid tie argmax on detail the same way --merge estimator does?

Three arms, one pinned binary (sha256 4c0c6022...ff7840):
    P  renders/<subj>/merge.tif          pyramid, the shipping default
    E  renders/EST-<subj>/merge.tif      estimator, explicitly requested
    A  renders/<subj>/argmax.tif         the selector

P and E come from runs with IDENTICAL frame count, reference frame and field-of-
view scale (read from both banners), so they sit on the same grid and need no
registration at all. Only A is on a different grid, and it is matched with the
same NCC machinery my headline used.

Sites, gates and statistic are exactly vmeasure.py's, so these numbers are
directly comparable with the ones already in docs/research/V-THESIS.md.
Positive means the FIRST-named arm resolves finer, in its own pixels.
"""
import json, pathlib, sys
import numpy as np, tifffile, cv2

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vstat import va_blur_px, sigma_immerkaer                      # noqa: E402
from vmeasure import green, band_snr, TILE, MARGIN, DS, NCC_MIN, SNR_MIN  # noqa: E402
from vplant import gauss_exact                                     # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-THESIS")
SUBJ = ["bee-3-cpl", "leaf-2-cpl", "flat-on-ruler-cpl"]
RNG = np.random.default_rng(20260826)
reg = {r["subject"]: r for r in json.loads((OUT/"register.json").read_text(encoding="utf8"))}

# ---- commission the same-grid configuration before trusting any P-vs-E number
print("COMMISSIONING the same-grid (P vs E) configuration on a real pyramid tile")
t = green(R/"bee-3-cpl"/"merge.tif")[1400:1912, 800:1312]
for s in (0.0, 0.20, 0.50, 1.00):
    planted = gauss_exact(t, s) if s > 0 else t
    print(f"   plant blur {s:4.2f} px into arm B -> reads {va_blur_px(t, planted):+.3f} px")
sig = sigma_immerkaer(t)
print(f"   plant NOISE only (sigma {sig:.1f} DN, no blur) -> reads "
      f"{va_blur_px(t, t + RNG.normal(0, sig, t.shape)):+.3f} px")
print()

print(f"{'subject':<19}{'n':>4}{'P vs A':>9}{'E vs A':>9}{'P vs E':>9}   verdict")
print("-" * 74)
out = {}
for subj in SUBJ:
    P, E, A = (green(R/subj/"merge.tif"), green(R/f"EST-{subj}"/"merge.tif"),
               green(R/subj/"argmax.tif"))
    assert P.shape == E.shape, f"{subj}: P and E differ in shape"
    rr = reg[subj]; s, tx, ty = rr["fitted_scale"], rr["tx"], rr["ty"]
    Ta = int(round(TILE*s)); H, W = P.shape
    mds = cv2.resize(P.astype(np.float32), None, fx=1.0/DS, fy=1.0/DS, interpolation=cv2.INTER_AREA)
    ads = cv2.resize(A.astype(np.float32), None, fx=1.0/DS, fy=1.0/DS, interpolation=cv2.INTER_AREA)
    mds = mds - cv2.blur(mds, (25, 25)); ads = ads - cv2.blur(ads, (25, 25))
    pa, ea, pe = [], [], []
    for y in range(MARGIN, H-TILE-MARGIN+1, TILE):
        for x in range(MARGIN, W-TILE-MARGIN+1, TILE):
            tp = P[y:y+TILE, x:x+TILE]; te = E[y:y+TILE, x:x+TILE]
            px, py = s*(x+TILE/2)+tx, s*(y+TILE/2)+ty
            n2 = int(round(TILE*s/DS)); SR = 24
            tpl = cv2.resize(mds[y//DS:y//DS+TILE//DS, x//DS:x//DS+TILE//DS], (n2, n2),
                             interpolation=cv2.INTER_AREA)
            ry0 = int(np.clip(py/DS-n2/2-SR, 0, ads.shape[0]-n2-2*SR))
            rx0 = int(np.clip(px/DS-n2/2-SR, 0, ads.shape[1]-n2-2*SR))
            regn = ads[ry0:ry0+n2+2*SR, rx0:rx0+n2+2*SR]
            if regn.shape[0] < n2 or regn.shape[1] < n2: continue
            _, sc, _, loc = cv2.minMaxLoc(cv2.matchTemplate(regn, tpl, cv2.TM_CCOEFF_NORMED))
            ax = int(round((rx0+loc[0])*DS)); ay = int(round((ry0+loc[1])*DS))
            if ax < 0 or ay < 0 or ax+Ta > W or ay+Ta > H: continue
            ta = A[ay:ay+Ta, ax:ax+Ta]
            if sc < NCC_MIN: continue
            if band_snr(tp)[0] < SNR_MIN or band_snr(ta)[0] < SNR_MIN: continue
            pa.append(va_blur_px(tp, ta)); ea.append(va_blur_px(te, ta))
            pe.append(va_blur_px(tp, te))
    n = len(pa)
    mpa, mea, mpe = np.median(pa), np.median(ea), np.median(pe)
    same = "same tie" if abs(mpa-mea) < 0.15 else "BACKENDS DIFFER"
    out[subj] = dict(n=n, P_vs_A=float(mpa), E_vs_A=float(mea), P_vs_E=float(mpe),
                     P_vs_A_all=[float(v) for v in pa], E_vs_A_all=[float(v) for v in ea],
                     P_vs_E_all=[float(v) for v in pe])
    print(f"{subj:<19}{n:>4}{mpa:>+9.3f}{mea:>+9.3f}{mpe:>+9.3f}   {same}")
print("-" * 74)
print("P vs A = pyramid vs argmax   E vs A = estimator vs argmax   P vs E = pyramid vs estimator")
print("positive = first arm resolves finer, in merge pixels")
(OUT/"backend.json").write_text(json.dumps(out, indent=1), encoding="utf8")
