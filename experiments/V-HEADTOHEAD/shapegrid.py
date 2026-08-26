"""Expanded run: a systematic ROI grid over the whole in-focus subject, so the
confidence intervals are set by the data and not by 18 hand-picked squares.
Also sweeps the positive control's sigma to state the instrument's DETECTION
THRESHOLD -- 'no difference' is only meaningful next to 'we could have seen X'."""
import numpy as np, arms, spec, shapecmp, json, sys

def grid_rois(P, T=256, thresh=0.012):
    """Every unclipped-in-both cell whose prior high-pass sd exceeds thresh
    (i.e. real subject detail, not paper)."""
    from scipy import ndimage
    S_scale = arms.h2h.SCALE
    out = []
    g = P.g
    for y in range(240, g.shape[0]-T-240, T//2):
        for x in range(240, g.shape[1]-T-240, T//2):
            if P.clip[y:y+T, x:x+T].any(): continue
            t = g[y:y+T, x:x+T]
            hp = t - ndimage.uniform_filter(t, 9)
            if hp.std() < thresh: continue
            cx, cy = arms.h2h.prior_to_strehl(x+T/2.0, y+T/2.0)
            Ts = int(round(T*S_scale))
            if cx-Ts/2 < 4 or cy-Ts/2 < 4: continue
            if cx+Ts/2 > 7032-4 or cy+Ts/2 > 4688-4: continue
            out.append((y, x))
    return out

if __name__ == "__main__":
    T = 256
    P = arms.prior_arm()
    R = grid_rois(P, T)
    print("grid ROIs on subject detail:", len(R))
    res = {}
    res["null"] = shapecmp.shape_ratio(P, arms.clone_arm(P), R, "NULL CONTROL (grid)", "prior", "clone", T)
    for sg in (0.2, 0.3, 0.5):
        res[f"pos{sg}"] = shapecmp.shape_ratio(P, arms.blur_arm(P, sg), R,
            f"POSITIVE CONTROL sigma={sg} px -- detection threshold", "prior", f"b{sg}", T)
    RS = arms.rescale_arm(P, arms.h2h.SCALE)
    res["scale"] = shapecmp.shape_ratio(P, RS, R, "SCALE-CONFOUND CONTROL (grid)", "prior", "rescaled", T)
    del RS
    S = arms.strehl_arm()
    res["real"] = shapecmp.shape_ratio(P, S, R, "REAL (grid): prior vs strehl -- SHARPNESS, grade removed", "prior", "strehl", T)
    print("\n===== corrected for strehl's own 3.5% rescale cost =====")
    print(f"{'band':<12}{'raw':>9}{'confound':>11}{'corrected':>12}{'  CI(raw)':>20}")
    for k in res["real"]:
        r = res["real"][k]; c = res["scale"][k][2]
        print(f"{k:<12}{r[2]:>9.3f}{c:>11.3f}{r[2]/c:>12.3f}   [{r[3]:.3f}, {r[4]:.3f}]")
    json.dump(res, open("shape_grid.json", "w"), indent=1)
