"""Independent registration of the two arms, and a test of BUILD-THESIS's claim
that 'a single global affine cannot register these two arms'.

Method is deliberately different from theirs (they used cv2.findTransformECC on
a 4x-downsampled, high-passed pair). Here: a grid of small anchor patches
matched by normalised cross-correlation, then a robust least-squares fit of a
similarity and of a full affine to the resulting displacement field, with the
RESIDUALS reported. A displacement field is falsifiable in a way a single ECC
score is not: if no global model fits, the residuals say so and say where.
"""
import json, pathlib, sys
import numpy as np, cv2, tifffile

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
SUBJECTS = ["bee-3-cpl","bee-1-cpl","leaf-2-cpl","flowers-cpl","tweezers-cpl","flat-on-ruler-cpl"]
DS = 4
PATCH = 40          # ds px  -> 160 full-res px
SEARCH = 56         # ds px  -> 224 full-res px


def green(p):
    return tifffile.imread(str(p))[:, :, 1].astype(np.float32)


def logged_scale(subject):
    for line in (R/subject/"merge.err").read_text(encoding="utf8", errors="replace").splitlines():
        if "field of view scaled to" in line:
            return float(line.split("field of view scaled to")[1].split()[0])
    return None


def anchors(gm, ga, s_hint):
    m = cv2.resize(gm, None, fx=1.0/DS, fy=1.0/DS, interpolation=cv2.INTER_AREA)
    a = cv2.resize(ga, None, fx=1.0/DS, fy=1.0/DS, interpolation=cv2.INTER_AREA)
    m = m - cv2.blur(m, (31,31)); a = a - cv2.blur(a, (31,31))
    H, W = m.shape
    pts = []
    step = 60
    for y in range(SEARCH+PATCH, H-SEARCH-PATCH, step):
        for x in range(SEARCH+PATCH, W-SEARCH-PATCH, step):
            tpl = m[y:y+PATCH, x:x+PATCH]
            if tpl.std() < 1e-6: continue
            # resample template to the argmax arm's sampling density
            n2 = max(8, int(round(PATCH*s_hint)))
            tpl2 = cv2.resize(tpl, (n2,n2), interpolation=cv2.INTER_AREA)
            cy, cx = y+PATCH/2.0, x+PATCH/2.0
            py, px = cy*s_hint, cx*s_hint          # rough predicted centre
            ry0 = int(np.clip(py-n2/2-SEARCH, 0, H-n2-2*SEARCH))
            rx0 = int(np.clip(px-n2/2-SEARCH, 0, W-n2-2*SEARCH))
            reg = a[ry0:ry0+n2+2*SEARCH, rx0:rx0+n2+2*SEARCH]
            if reg.shape[0] < n2 or reg.shape[1] < n2: continue
            r = cv2.matchTemplate(reg, tpl2, cv2.TM_CCOEFF_NORMED)
            _, sc, _, loc = cv2.minMaxLoc(r)
            if sc < 0.45: continue
            ax = (rx0+loc[0]+n2/2.0)*DS
            ay = (ry0+loc[1]+n2/2.0)*DS
            pts.append((cx*DS, cy*DS, ax, ay, float(sc), tpl.std()))
    return np.array(pts, dtype=np.float64)


def fit_similarity(P):
    """argmax = s*merge + t (no rotation). Returns s, tx, ty."""
    mx, my, ax, ay = P[:,0], P[:,1], P[:,2], P[:,3]
    A = np.zeros((2*len(P), 3)); b = np.zeros(2*len(P))
    A[0::2,0] = mx; A[0::2,1] = 1.0; b[0::2] = ax
    A[1::2,0] = my; A[1::2,2] = 1.0; b[1::2] = ay
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    return sol


def fit_affine(P):
    mx, my, ax, ay = P[:,0], P[:,1], P[:,2], P[:,3]
    M = np.column_stack([mx, my, np.ones_like(mx)])
    cx, *_ = np.linalg.lstsq(M, ax, rcond=None)
    cy, *_ = np.linalg.lstsq(M, ay, rcond=None)
    return np.vstack([cx, cy])


def resid(P, model, kind):
    mx, my = P[:,0], P[:,1]
    if kind == "sim":
        s, tx, ty = model
        px, py = s*mx+tx, s*my+ty
    else:
        px = model[0,0]*mx + model[0,1]*my + model[0,2]
        py = model[1,0]*mx + model[1,1]*my + model[1,2]
    return np.hypot(px-P[:,2], py-P[:,3])


def main():
    out = []
    for s in SUBJECTS:
        gm, ga = green(R/s/"merge.tif"), green(R/s/"argmax.tif")
        sl = logged_scale(s)
        P = anchors(gm, ga, sl)
        if len(P) < 12:
            print(f"{s}: only {len(P)} anchors"); continue
        keep = np.ones(len(P), bool)
        for _ in range(4):
            sim = fit_similarity(P[keep])
            r = resid(P, sim, "sim")
            med = np.median(r[keep]); mad = np.median(np.abs(r[keep]-med))+1e-9
            keep = r < med + 4*1.4826*mad
        sim = fit_similarity(P[keep])
        aff = fit_affine(P[keep])
        rs, ra = resid(P[keep], sim, "sim"), resid(P[keep], aff, "aff")
        rot = np.degrees(np.arctan2(aff[1,0], aff[0,0]))
        print(f"\n=== {s}")
        print(f"   anchors {len(P)} matched, {keep.sum()} inliers, median NCC {np.median(P[keep][:,4]):.3f}")
        print(f"   logged FOV scale        {sl:.4f}")
        print(f"   fitted similarity scale {sim[0]:.5f}   t=({sim[1]:+.1f},{sim[2]:+.1f}) px")
        print(f"   similarity residual     median {np.median(rs):.2f} px   p90 {np.percentile(rs,90):.2f}   max {rs.max():.2f}")
        print(f"   full affine residual    median {np.median(ra):.2f} px   p90 {np.percentile(ra,90):.2f}   max {ra.max():.2f}")
        print(f"   affine implied rotation {rot:+.4f} deg   ax={aff[0,0]:.5f} ay={aff[1,1]:.5f}")
        out.append(dict(subject=s, logged_scale=sl, fitted_scale=float(sim[0]),
                        tx=float(sim[1]), ty=float(sim[2]),
                        n_anchor=int(len(P)), n_inlier=int(keep.sum()),
                        sim_resid_median=float(np.median(rs)), sim_resid_p90=float(np.percentile(rs,90)),
                        sim_resid_max=float(rs.max()),
                        aff_resid_median=float(np.median(ra)), aff_resid_p90=float(np.percentile(ra,90)),
                        affine=aff.tolist()))
    p = pathlib.Path(r"C:\dev\strehl-out\V-THESIS"); p.mkdir(parents=True, exist_ok=True)
    (p/"register.json").write_text(json.dumps(out, indent=1), encoding="utf8")
    print(f"\nwrote {p/'register.json'}")


if __name__ == "__main__":
    main()
