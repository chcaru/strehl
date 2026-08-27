r"""Registration that survives a defocused source frame.

vr_lib.register (ORB + RANSAC + ECC) recovers a planted similarity to 3.5e-4 in
scale and 0.5 px in shift (vr_commission.py ARM B) but returned 16 matches and
NO fit on foam frame 0, because that frame is grossly defocused and ORB is a
corner detector: the two pictures do not look alike even though they are the
same scene.

This adds a model-initialised path. The geometry is not unknown -- both renders
print their own fit-to-cover ratio, so the master-to-source scale is k_master /
k_source before any drift, and only the inter-frame drift has to be solved. So:

  1. scale the master by the ratio the two logs state,
  2. phase-correlate for the drift (unbounded capture range, unlike ECC),
  3. refine with ECC MOTION_AFFINE, blurred, coarse then fine.

Every arm reports its own ECC correlation and a context NCC, so a fit that did
not work says so instead of quietly returning a plausible matrix.
"""
import os
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402

COVER = re.compile(r"field of view scaled to ([0-9.]+)")


def cover_of_log(text):
    m = COVER.search(text)
    if m:
        return float(m.group(1))
    return 1.0 if "no crop needed" in text else None


def master_cover(subj):
    p = os.path.join(V.SHIP, "%s--%s.log" % (subj, V.ARM))
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return cover_of_log(f.read())


def _prep(a, ds, blur):
    b = cv2.resize(a, None, fx=1.0 / ds, fy=1.0 / ds, interpolation=cv2.INTER_AREA)
    b = cv2.GaussianBlur(b, (0, 0), blur)
    b = (b - b.mean()) / max(float(b.std()), 1e-6)
    return b.astype(np.float32)


def scale_about_centre(s, w, h):
    return np.array([[s, 0.0, (1 - s) * w / 2.0], [0.0, s, (1 - s) * h / 2.0]])


def register_model(mlum, slum, s0, ds_list=(16, 8), blur=1.5):
    """Master->source similarity, initialised from the two renders' cover ratio."""
    h, w = mlum.shape
    A = scale_about_centre(s0, w, h)
    diag = {"init_scale": s0}
    for ds in ds_list:
        m = _prep(mlum, ds, blur)
        s = _prep(slum, ds, blur)
        if ds == ds_list[0]:
            # phase correlation on the model-scaled master: unbounded shift
            Ad = A.copy()
            Ad[:, 2] /= ds
            mw = cv2.warpAffine(m, Ad.astype(np.float32), (s.shape[1], s.shape[0]),
                                flags=cv2.INTER_LINEAR)
            win = cv2.createHanningWindow((s.shape[1], s.shape[0]), cv2.CV_32F)
            (dx, dy), resp = cv2.phaseCorrelate(mw.astype(np.float64) * win,
                                                s.astype(np.float64) * win)
            diag["phase_resp"] = float(resp)
            diag["phase_shift_px"] = (float(dx * ds), float(dy * ds))
            A[0, 2] += dx * ds
            A[1, 2] += dy * ds
        W = A.copy()
        W[:, 2] /= ds
        try:
            cc, W = cv2.findTransformECC(
                m, s, W.astype(np.float32), cv2.MOTION_AFFINE,
                (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), None, 5)
            diag["ecc_ds%d" % ds] = float(cc)
            A = np.array(W, dtype=np.float64)
            A[:, 2] *= ds
        except cv2.error as exc:                               # noqa: BLE001
            diag["ecc_ds%d_error" % ds] = str(exc)[:100]
    diag["scale"] = float(np.sqrt(abs(A[0, 0] * A[1, 1] - A[0, 1] * A[1, 0])))
    diag["ecc"] = diag.get("ecc_ds%d" % ds_list[-1], float("nan"))
    return A, diag


def context_ncc(mlum, slum, A, y, x, win, pad=800, blur=20.0):
    """Same scene? Correlate a padded box with BOTH sides blurred hard enough
    that the master being in focus and the frame not cannot decide it."""
    pad = int(min(pad, y, x, mlum.shape[0] - y - win, mlum.shape[1] - x - win))
    y0, x0, n = y - pad, x - pad, win + 2 * pad
    a = mlum[y0:y0 + n, x0:x0 + n]
    b = V.warp_window(slum[..., None], A, y0, x0, n)
    if b is None:
        return float("nan")
    a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), blur)
    b = b if b.ndim == 2 else b[..., 0]   # cv2 DROPS a singleton channel
    b = cv2.GaussianBlur(b.astype(np.float32), (0, 0), blur)
    a, b = a - a.mean(), b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else float("nan")


def register_best(mlum, slum, s0, y, x, win):
    """ORB first (it is the more accurate when it works), model-ECC as fallback;
    keep whichever verifies better on the context box, and say which."""
    best = (None, {"how": "none"}, -2.0)
    A, d = V.register(mlum, slum)
    if A is not None and d.get("inliers", 0) >= 40:
        n = context_ncc(mlum, slum, A, y, x, win)
        best = (A, dict(d, how="orb"), n if np.isfinite(n) else -2.0)
    A2, d2 = register_model(mlum, slum, s0)
    n2 = context_ncc(mlum, slum, A2, y, x, win)
    n2 = n2 if np.isfinite(n2) else -2.0
    if n2 > best[2]:
        best = (A2, dict(d2, how="model-ecc"), n2)
    A, d, n = best
    d["ncc_context"] = n
    return A, d


if __name__ == "__main__":
    subj = sys.argv[1]
    k = int(sys.argv[2])
    tif = os.path.join(V.OUT, "%s--f%04d.tiff" % (subj, k))
    if not os.path.exists(tif):
        V.render_frame(subj, k, tif)
    import json
    with open(os.path.join(V.OUT, "master_stats.json")) as f:
        ms = json.load(f)[subj]
    y, x = ms["blotch"]["y"], ms["blotch"]["x"]
    km = master_cover(subj)
    ml = V.lum_of(V.read_rgb(V.master_path(subj)))
    sl = V.lum_of(V.read_rgb(tif))
    s0 = km / 0.9974
    print("master cover %.4f  init scale %.4f" % (km, s0))
    A, d = register_best(ml, sl, s0, y, x, V.BWIN)
    print("how=%s  ncc=%.4f  scale=%.4f  ecc=%s" %
          (d["how"], d["ncc_context"], d.get("scale", float("nan")), d.get("ecc")))
    print({kk: v for kk, v in d.items() if kk not in ("how",)})
    print("A=", A)
