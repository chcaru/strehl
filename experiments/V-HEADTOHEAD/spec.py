"""Band-limited contrast variance at MATCHED SCENE FREQUENCIES.  The sharpness
instrument.

METHOD.  For an ROI specified in PRIOR raster coordinates, each arm reads the
integer pixel box covering the SAME SCENE AREA in its own grid -- 384 px for the
prior arm, 397 px for strehl, because strehl's raster carries 3.5063% more pixels
per scene unit (MEASURED by geom.py, not assumed).  Neither arm is resampled.

Each box is divided by its own mean and DC-removed, so the statistic is in
CONTRAST^2 units and every gain, exposure and white-point difference cancels.
strehl's tone rendering is inverted first so this is LINEAR light: without that,
strehl's 0.55 display S-curve alone would inflate every band.

Power is integrated over ANNULI DEFINED IN SCENE FREQUENCY (cycles per prior
pixel).  An annulus [f1,f2] cyc/prior-px is read at [f1/s, f2/s] cyc/arm-px.  By
Parseval the annulus sum of |F|^2/N^2 is the variance carried by that band, an
absolute quantity that does not depend on how densely the arm samples the scene.

FOOLING DIRECTIONS (rule 18).  Band variance rises when a merge PRESERVES detail
and equally when it MANUFACTURES it (sharpening, ringing) or when it is NOISIER.
It is therefore admissible as evidence of *collapse* and inadmissible on its own
as evidence of *quality*.  It is read here against three things: a flat ROI
(rule 9), the noise band, and the pictures.

WHAT WOULD MAKE IT FAIL (rule 20).  A flat, detail-free ROI must not show a
detail advantage for anybody: run below.  Two identical arms must return 1.000:
run below.  A 0.8 px Gaussian must be detected with the right sign and roughly
the right magnitude: run below.  The 3.5% rescale on its own must not produce
the effect: run below.
"""
import numpy as np, arms, json, sys

BANDS = [(0.02, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
         (0.30, 0.40), (0.40, 0.48)]

def band_variance(arm, y, x, T):
    """T is the box size in PRIOR pixels; the arm reads round(T*scale)."""
    cx, cy = arm.px(x + T / 2.0, y + T / 2.0)
    Ts = int(round(T * arm.scale))
    x0 = int(round(cx - Ts / 2.0)); y0 = int(round(cy - Ts / 2.0))
    if x0 < 0 or y0 < 0 or y0 + Ts > arm.g.shape[0] or x0 + Ts > arm.g.shape[1]:
        return None, None, None
    box = arm.g[y0:y0 + Ts, x0:x0 + Ts].astype(np.float64)
    clip = arm.clip[y0:y0 + Ts, x0:x0 + Ts].mean()
    m = box.mean()
    if m <= 1e-6: return None, None, None
    c = box / m - 1.0
    w = np.hanning(Ts)[:, None] * np.hanning(Ts)[None, :]
    c = c * w
    F = np.fft.fft2(c)
    P = (np.abs(F) ** 2) / (Ts * Ts) ** 2
    P /= (w ** 2).mean()                       # window energy correction
    fy = np.fft.fftfreq(Ts)[:, None]; fx = np.fft.fftfreq(Ts)[None, :]
    r = np.hypot(fy, fx) * arm.scale           # -> cycles per PRIOR pixel
    out = {}
    for a, b in BANDS:
        out[(a, b)] = float(P[(r >= a) & (r < b)].sum())
    return out, clip, m

def compare(A, B, rois, T, label, na, nb, quiet=False):
    acc = {k: [] for k in BANDS}
    used = 0
    for (y, x) in rois:
        va, ca, _ = band_variance(A, y, x, T)
        vb, cb, _ = band_variance(B, y, x, T)
        if va is None or vb is None: continue
        if ca > 0.0 or cb > 0.0: continue
        used += 1
        for k in BANDS:
            acc[k].append((va[k], vb[k]))
    if used == 0:
        print(f"{label}: NO USABLE ROIs"); return None
    print(f"\n===== {label}   ({used} ROIs of {T}x{T} prior px) =====")
    print(f"{'band cyc/px':<14}{na:>13}{nb:>13}{'B/A':>9}{'  95% CI of ratio':>22}")
    res = {}
    rng = np.random.default_rng(5)
    for k in BANDS:
        v = np.array(acc[k]); a = v[:, 0]; b = v[:, 1]
        ra = float(b.sum() / a.sum())
        idx = rng.integers(0, len(a), (4000, len(a)))
        bs = b[idx].sum(1) / a[idx].sum(1)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        print(f"{k[0]:.2f}-{k[1]:.2f}      {a.mean():>13.3e}{b.mean():>13.3e}{ra:>9.3f}   [{lo:.3f}, {hi:.3f}]")
        res[f"{k[0]:.2f}-{k[1]:.2f}"] = [float(a.mean()), float(b.mean()), ra, float(lo), float(hi)]
    return res

DETAIL_ROIS = [(3272,4616),(1544,4424),(3080,4616),(1352,3272),(1352,4424),(1544,4232),
               (1736,4232),(1736,4424),(3464,4616),(1352,4616),(1160,3272),(3080,4424),
               (2504,3800),(2888,3416),(2120,2648),(2696,2264),(3656,3032),(1928,3608),
               (2312,4040),(2696,4808),(3848,3416),(1160,2504),(2888,1880),(3272,2264)]
FLAT_ROIS   = [(968,584),(1160,584),(968,392),(1160,392),(1736,392),(1736,584),
               (968,776),(1160,776),(1928,584),(1928,392),(1352,584),(776,584)]

if __name__ == "__main__":
    T = 384
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    P = arms.prior_arm()
    out = {}
    if which in ("all", "null"):
        out["null_detail"] = compare(P, arms.clone_arm(P), DETAIL_ROIS, T,
            "NULL CONTROL (detail ROIs): prior vs prior, identical bytes", "prior", "clone")
    if which in ("all", "pos"):
        out["pos_detail"] = compare(P, arms.blur_arm(P, 0.8), DETAIL_ROIS, T,
            "POSITIVE CONTROL: prior vs prior blurred sigma=0.8 px", "prior", "blur0.8")
    if which in ("all", "scale"):
        out["scale_detail"] = compare(P, arms.rescale_arm(P, arms.h2h.SCALE), DETAIL_ROIS, T,
            "SCALE-CONFOUND CONTROL: prior vs prior crop 1/1.035 + cubic upsample", "prior", "rescaled")
        out["scale_flat"] = compare(P, arms.rescale_arm(P, arms.h2h.SCALE), FLAT_ROIS, T,
            "SCALE-CONFOUND CONTROL on FLAT ROIs", "prior", "rescaled")
    if which in ("all", "real"):
        S = arms.strehl_arm()
        out["real_detail"] = compare(P, S, DETAIL_ROIS, T,
            "REAL, DETAIL ROIs: prior (focus-stack fork) vs strehl SHIP-V2", "prior", "strehl")
        out["real_flat"] = compare(P, S, FLAT_ROIS, T,
            "REAL, FLAT ROIs (rule 9 control + noise): prior vs strehl", "prior", "strehl")
    json.dump(out, open(f"spec_results_{which}.json", "w"), indent=1)
