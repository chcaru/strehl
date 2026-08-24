"""M102 S4 -- realism, MEASURED against the real bee-3-cpl stack.

Every comparison here is deliberately a RATIO or a normalised width, never an
absolute scene-dependent quantity, because the synthetic scene is not the real
scene and a bar on an absolute quantity would fail for reasons unrelated to
the hypothesis. That constraint is discipline 609, which I earned in M92 by
writing exactly such a bar.

Both stacks go through the SAME operator implemented once in this file. A
second implementation would confound "the simulator is unfaithful" with
"the two measurements differ".

Usage:
  python src/s4_realism.py
"""
import glob
import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "M92-null-averaging", "src"))

import m102lib as M            # noqa: E402
import s13_sensor_guard as G   # noqa: E402
from s3_roundtrip import read_gray_tif  # noqa: E402

REAL = os.path.join(M.ROOT, "bee-3-cpl")
REAL_STRIDE = 8          # every 8th frame: 299 -> 38, enough for a width
ROI = 384                # square ROI side, in CFA px, on the real frame


def focus_field(g):
    """Local high-frequency energy in a 17x17 window.

    17 matches the shipped merge's own regularisation window, so the width
    this returns is comparable to the scale the pipeline elects on.
    """
    lap = ndimage.convolve(g.astype(np.float64),
                           np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]],
                                    float), mode="nearest")
    return ndimage.uniform_filter(lap * lap, 17)


def noise_in_flat(g, mask=None, win=9):
    """Robust noise estimate: MAD of the residual after a local median,
    evaluated ON THE MASK ONLY.

    The mask argument is not cosmetic. The first revision of this function
    was called with the off-mask pixels filled by a constant, and the MAD was
    then taken over the whole frame: more than half the pixels had exactly
    zero residual, so the median absolute deviation was exactly 0.0 and every
    synthetic frame reported a noise ratio of 0.000. The bug was visible only
    because the same function returned 0.9946 on the real stack, where no
    such filling happens.
    """
    med = ndimage.median_filter(g.astype(np.float64), win)
    r = (g - med)
    if mask is not None:
        r = r[mask]
    r = np.asarray(r).ravel()
    return float(np.median(np.abs(r - np.median(r))) * 1.4826)


def predicted_sigma(mean_dn, g_dn_e, rn_e, black=M.BLACK):
    s = max(float(mean_dn) - black, 0.0)
    return float(np.sqrt(g_dn_e * s + (rn_e * g_dn_e) ** 2))


def tf_width(cube, mask):
    """Median half-width, in frames, of the normalised through-focus curve.

    Per pixel: normalise the response to [0,1] over frames, then count frames
    at or above 0.5. A count, not a fitted sigma -- a fit would impose a
    shape, and the shape is one of the things under test.
    """
    F = cube.shape[0]
    v = cube[:, mask]
    lo = v.min(axis=0)
    hi = v.max(axis=0)
    ok = (hi - lo) > 1e-12
    n = ((v[:, ok] - lo[ok]) / (hi[ok] - lo[ok]) >= 0.5).sum(axis=0)
    return float(np.median(n)), int(ok.sum()), F


def disconnected(cube, mask, sigma_frac=0.10):
    """Fraction of pixels whose competitive set is disconnected in frame
    index, and the mean gap. M96 MEASURED 25.247% / 29.12 frames on the real
    stack (fact 1263); this reproduces the STATISTIC, on both stacks, with
    one implementation."""
    v = cube[:, mask]
    hi = v.max(axis=0)
    lo = v.min(axis=0)
    ok = (hi - lo) > 1e-12
    v, hi, lo = v[:, ok], hi[ok], lo[ok]
    comp = v >= (hi - sigma_frac * (hi - lo))
    idx = np.arange(v.shape[0])[:, None]
    first = np.where(comp, idx, 10 ** 6).min(axis=0)
    last = np.where(comp, idx, -1).max(axis=0)
    span = last - first + 1
    cnt = comp.sum(axis=0)
    dis = span > cnt
    gap = (span - cnt)[dis]
    return (float(dis.mean()), float(gap.mean()) if gap.size else 0.0,
            int(ok.sum()))


def synth_cube(d):
    files = sorted(glob.glob(os.path.join(d, "DSC*.ARW")))
    cfa = [read_gray_tif(f).astype(np.float64) for f in files]
    # G1 site of the RGGB quad: one green plane, no demosaic, no
    # interpolation. Requirement 4 is that the stack is CFA; measuring on an
    # interpolated plane would measure the interpolator.
    return np.stack([c[0::2, 1::2] for c in cfa]), np.stack(cfa)


def real_cube():
    import rawpy
    files = sorted(glob.glob(os.path.join(REAL, "*.ARW")))
    sel = files[::REAL_STRIDE]
    planes, means = [], []
    for f in sel:
        with rawpy.imread(f) as r:
            a = r.raw_image_visible.astype(np.float64)
        h, w = a.shape
        y0, x0 = (h - ROI) // 2, (w - ROI) // 2
        sub = a[y0:y0 + ROI, x0:x0 + ROI]
        planes.append(sub[0::2, 1::2])
        means.append(float(sub.mean()))
    return np.stack(planes), np.array(means), len(files), len(sel)


def real_dense(n=64, roi=256):
    """Densely-sampled real window, stride 1, for a through-focus WIDTH.

    The strided cube cannot measure this: at stride 8 the half-width quantum
    is 8 real frames, and the first revision of this arm reported a real
    half-width of exactly 1 sample -- i.e. the measurement was pinned at its
    own resolution limit and the synth/real ratio built on it was
    uninterpretable.
    """
    import rawpy
    files = sorted(glob.glob(os.path.join(REAL, "*.ARW")))
    a0 = max(0, len(files) // 2 - n // 2)
    sel = files[a0:a0 + n]
    planes = []
    for f in sel:
        with rawpy.imread(f) as r:
            a = r.raw_image_visible.astype(np.float64)
        h, w = a.shape
        y0, x0 = (h - roi) // 2, (w - roi) // 2
        planes.append(a[y0:y0 + roi, x0:x0 + roi][0::2, 1::2])
    return np.stack(planes), len(files)


def main():
    out = {}
    iso, gdn, rn = G.sensor_for("bee-3-cpl")
    out["sensor"] = {"stack": "bee-3-cpl", "iso": iso, "gain_dn_per_e": gdn,
                     "read_noise_e": rn, "source": "sensor_for() / EXIF"}

    d = os.path.join(M.WORK, "nb_base")
    z = np.load(os.path.join(d, "truth.npz"))
    gcube, cfacube = synth_cube(d)
    smooth = z["mask_smooth"][0::2, 1::2]
    tex = z["mask_textured"][0::2, 1::2]

    # ---- N1: measured / predicted noise, per frame, synthetic.
    rows = []
    for k in range(gcube.shape[0]):
        g = gcube[k]
        m = float(np.median(g[smooth]))
        meas = noise_in_flat(g, mask=smooth)
        pred = predicted_sigma(m, gdn, rn)
        rows.append({"frame": k, "mean_dn": m, "measured": meas,
                     "predicted": pred, "ratio": meas / pred})
    r = np.array([x["ratio"] for x in rows])
    out["N1_synth"] = {"n": len(rows), "ratio_median": float(np.median(r)),
                       "ratio_min": float(r.min()),
                       "ratio_max": float(r.max()),
                       "bar_0.90_1.10": bool(0.90 <= np.median(r) <= 1.10),
                       "per_frame": rows[:4]}

    # ---- N2 / N3 on the synthetic stack.
    scube = np.stack([focus_field(gcube[k]) for k in range(gcube.shape[0])])
    w_s, n_s, F_s = tf_width(scube, tex)
    d_s, gap_s, _ = disconnected(scube, tex)
    out["N2_synth"] = {"halfwidth_frames": w_s, "n_px": n_s, "frames": F_s,
                       "halfwidth_frac_of_stack": w_s / F_s}
    out["N3_synth"] = {"disconnected_frac": d_s, "mean_gap_frames": gap_s}

    # ---- The real stack, same operator.
    try:
        rcube, rmeans, n_all, n_sel = real_cube()
        rtex = np.ones(rcube.shape[1:], bool)
        rfoc = np.stack([focus_field(rcube[k]) for k in range(rcube.shape[0])])
        w_r, n_r, F_r = tf_width(rfoc, rtex)
        d_r, gap_r, _ = disconnected(rfoc, rtex)
        nr = []
        for k in range(rcube.shape[0]):
            meas = noise_in_flat(rcube[k])
            pred = predicted_sigma(float(np.median(rcube[k])), gdn, rn)
            nr.append(meas / pred)
        out["real"] = {
            "frames_total": n_all, "frames_used": n_sel,
            "stride": REAL_STRIDE, "roi_cfa_px": ROI,
            "N1_ratio_median": float(np.median(nr)),
            "N2_halfwidth_frames": w_r,
            "N2_halfwidth_frac_of_stack": w_r / F_r,
            "N3_disconnected_frac": d_r, "N3_mean_gap_frames": gap_r,
        }
        # Widths are compared as a FRACTION of the stack, because the two
        # stacks have different frame counts and different rail steps; the
        # raw frame count would compare my chosen rail to the owner's.
        dcube, n_all2 = real_dense()
        dfoc = np.stack([focus_field(dcube[k])
                         for k in range(dcube.shape[0])])
        w_d, n_d, F_d = tf_width(dfoc, np.ones(dcube.shape[1:], bool))
        out["real"]["N2_dense_halfwidth_frames"] = w_d
        out["real"]["N2_dense_window_frames"] = F_d
        out["real"]["N2_dense_halfwidth_frac_of_stack"] = w_d / n_all2
        ratio = (w_s / F_s) / (w_d / n_all2)
        out["N2_bar"] = {
            "basis": "dense stride-1 real window, frac of full stack",
            "synth_frac": w_s / F_s, "real_frac": w_d / n_all2,
            "width_frac_ratio_synth_over_real": float(ratio),
            "bar_factor_2": bool(0.5 <= ratio <= 2.0),
            "strided_ratio_superseded": float((w_s / F_s) / (w_r / F_r))}
    except Exception as e:            # noqa: BLE001
        out["real"] = {"error": f"{type(e).__name__}: {e}"}

    out["N3_bar"] = {"synth_frac": d_s,
                     "bar_nonzero_and_lt_0.60": bool(0.0 < d_s < 0.60),
                     "m96_real_reference_fact_1263": M.DISCONNECTED_FRAC}
    os.makedirs(M.OUT, exist_ok=True)
    with open(os.path.join(M.OUT, "s4_realism.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "N1_synth"},
                     indent=2))
    print("N1_synth:", json.dumps({k: v for k, v in out["N1_synth"].items()
                                   if k != "per_frame"}, indent=2))


if __name__ == "__main__":
    main()
