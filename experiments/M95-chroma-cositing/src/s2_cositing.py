"""S2 — the real measurement, with the robust estimator and the coherence gate.

Supersedes `s1_cositing.py`, whose fit residual was 1.0736 px -- larger than
the effect it was measuring. That run is kept as the record of the failure. Two
things were wrong with it and both are fixed here:

1. It used the naive phase fit, which wraps once the displacement exceeds about
   2 px inside the fit band. C7 shows that failure directly: a planted 4.00 px
   was read as -0.21 px, confidently.
2. It selected ROIs on detail alone. In a single frame from a focus stack most
   of the field is defocused, and a defocused region is bright and full of
   high-frequency NOISE, which passes a detail threshold. Registering red
   against blue there measures nothing. C9's coherence gate is the fix.

Both image pairs are measured:
  - frame 183 alone, where only a band of the field is in focus;
  - the gate-0 merge of all 299 frames, where the whole field is in focus.
The merged pair is the one that matters for the product, because it is what a
user actually looks at.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m95c as C  # noqa: E402

S = 256
COH_MIN = 0.5

PAIRS = {
    "frame-183": ("armF-f183.tif", "armF-f183-demo.tif"),
    "merged-gate0": ("armM-gate0-binlin.tif", "armM-gate0-demo.tif"),
}


def field_rois(h, w, s, nx, ny, margin=64):
    ys = np.linspace(margin, h - s - margin, ny).astype(int)
    xs = np.linspace(margin, w - s - margin, nx).astype(int)
    return [(int(y), int(x)) for y in ys for x in xs]


def chans(img, y, x, scale):
    yy, xx, ss = y * scale, x * scale, S * scale
    t = img[yy : yy + ss, xx : xx + ss, :].astype(np.float64)
    return t[:, :, 0], t[:, :, 1], t[:, :, 2]


def fit_const_plus_radial(rows, ky, kx, cy, cx):
    """Split d(x,y) = c + k * r_hat into constant and radial parts.

    One weighted least squares over both components together, because `k` is
    shared between them and `c` is not.
    """
    A, rhs = [], []
    for r in rows:
        ry, rx = r["y"] + S / 2 - cy, r["x"] + S / 2 - cx
        n = np.hypot(ry, rx)
        uy, ux = (ry / n, rx / n) if n > 0 else (0.0, 0.0)
        A.append([1.0, 0.0, uy])
        rhs.append(r[ky])
        A.append([0.0, 1.0, ux])
        rhs.append(r[kx])
    A, rhs = np.array(A), np.array(rhs)
    sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    resid = rhs - A @ sol
    return {
        "c_dy": float(sol[0]),
        "c_dx": float(sol[1]),
        "c_mag": float(np.hypot(sol[0], sol[1])),
        "k_radial": float(sol[2]),
        "resid_rms": float(np.sqrt(np.mean(resid**2))),
        "n_roi": len(rows),
    }


def run_pair(name, binf, demof):
    print("\n" + "=" * 72)
    print("PAIR: %s" % name)
    ib = C.load_tif(os.path.join(C.OUT, binf))
    idm = C.load_tif(os.path.join(C.OUT, demof))
    h, w = ib.shape[0], ib.shape[1]
    cy, cx = h / 2.0, w / 2.0
    assert idm.shape[0] == 2 * h and idm.shape[1] == 2 * w

    rois = field_rois(h, w, S, nx=7, ny=5)
    rows_b, rows_d, diag = [], [], []
    for y, x in rois:
        rb, gb, bb = chans(ib, y, x, 1)
        rd, gd, bd = chans(idm, y, x, 2)
        coh_b = C.coherence(rb, bb)
        coh_d = C.coherence(rd, bd)
        keep = min(coh_b, coh_d) >= COH_MIN
        diag.append({"y": y, "x": x, "coh_bin": coh_b, "coh_demo": coh_d, "kept": bool(keep)})
        if not keep:
            continue
        d_b = C.phase_ramp_shift_robust(rb, bb)
        g_b = C.phase_ramp_shift_robust(rb, gb)
        d_d = C.phase_ramp_shift_robust(rd, bd)
        g_d = C.phase_ramp_shift_robust(rd, gd)
        rows_b.append({"y": y, "x": x, "rb_dy": d_b[0], "rb_dx": d_b[1],
                       "rg_dy": g_b[0], "rg_dx": g_b[1], "coh": coh_b})
        rows_d.append({"y": y, "x": x, "rb_dy": d_d[0] / 2, "rb_dx": d_d[1] / 2,
                       "rg_dy": g_d[0] / 2, "rg_dx": g_d[1] / 2, "coh": coh_d})

    print("  ROIs: %d offered, %d kept (coherence >= %.2f in BOTH arms)"
          % (len(rois), len(rows_b), COH_MIN))
    if len(rows_b) < 6:
        print("  too few coherent ROIs; pair skipped")
        return {"n_kept": len(rows_b), "skipped": True, "diag": diag}

    fb = fit_const_plus_radial(rows_b, "rb_dy", "rb_dx", cy, cx)
    fd = fit_const_plus_radial(rows_d, "rb_dy", "rb_dx", cy, cx)
    gb_ = fit_const_plus_radial(rows_b, "rg_dy", "rg_dx", cy, cx)
    gd_ = fit_const_plus_radial(rows_d, "rg_dy", "rg_dx", cy, cx)

    mb = np.array([[r["rb_dy"], r["rb_dx"]] for r in rows_b])
    md = np.array([[r["rb_dy"], r["rb_dx"]] for r in rows_d])
    print("  R->B raw mean   binned (%+.4f, %+.4f)  sd (%.4f, %.4f)"
          % (mb[:, 0].mean(), mb[:, 1].mean(), mb[:, 0].std(), mb[:, 1].std()))
    print("  R->B raw mean   demosc (%+.4f, %+.4f)  sd (%.4f, %.4f)"
          % (md[:, 0].mean(), md[:, 1].mean(), md[:, 0].std(), md[:, 1].std()))
    print("  R->B const+rad  binned c=(%+.4f,%+.4f) |c|=%.4f k=%+.4f resid=%.4f"
          % (fb["c_dy"], fb["c_dx"], fb["c_mag"], fb["k_radial"], fb["resid_rms"]))
    print("  R->B const+rad  demosc c=(%+.4f,%+.4f) |c|=%.4f k=%+.4f resid=%.4f"
          % (fd["c_dy"], fd["c_dx"], fd["c_mag"], fd["k_radial"], fd["resid_rms"]))
    print("  R->G const+rad  binned c=(%+.4f,%+.4f) |c|=%.4f"
          % (gb_["c_dy"], gb_["c_dx"], gb_["c_mag"]))
    print("  R->G const+rad  demosc c=(%+.4f,%+.4f) |c|=%.4f"
          % (gd_["c_dy"], gd_["c_dx"], gd_["c_mag"]))
    print("  C4 power control: same ROIs, same settings, binned |c|=%.4f vs demosaiced |c|=%.4f"
          % (fb["c_mag"], fd["c_mag"]))

    return {
        "n_offered": len(rois),
        "n_kept": len(rows_b),
        "rb_binned_fit": fb,
        "rb_demosaic_fit": fd,
        "rg_binned_fit": gb_,
        "rg_demosaic_fit": gd_,
        "rb_raw_mean_binned": [float(mb[:, 0].mean()), float(mb[:, 1].mean())],
        "rb_raw_sd_binned": [float(mb[:, 0].std()), float(mb[:, 1].std())],
        "rb_raw_mean_demosaic": [float(md[:, 0].mean()), float(md[:, 1].mean())],
        "rb_raw_sd_demosaic": [float(md[:, 0].std()), float(md[:, 1].std())],
        "per_roi_binned": rows_b,
        "per_roi_demosaic": rows_d,
        "diag": diag,
        "centre": [cy, cx],
    }


def main():
    out = {"coh_min": COH_MIN, "roi_size": S, "pairs": {}}
    for name, (b, d) in PAIRS.items():
        out["pairs"][name] = run_pair(name, b, d)
    C.jdump("s2_cositing.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
