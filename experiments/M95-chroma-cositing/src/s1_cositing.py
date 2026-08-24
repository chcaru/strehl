"""C6 + the real measurement: is red misregistered against blue in binned output?

C6 FIRST, AND WHY IT EXISTS
---------------------------
The pre-registration predicted `d(R->B) = (+0.5, +0.5)` binned px. Re-deriving
it before measuring, I get the opposite sign:

    R_ch[u] = f(2u)        B_ch[u] = f(2u+1) = f(2(u+0.5)) = R_ch(u + 0.5)

and with the estimator's convention `b(x) ~= a(x - d)` that is `d = -0.5`.

So one of my two derivations is wrong, and I cannot settle it by doing the
algebra a third time -- that is just the same instrument again. C6 settles it by
CONSTRUCTION: build a synthetic scene, bin it with exactly the arithmetic
`merge_cmd.rs` uses, and measure. The truth is known because I built it.

C6 validates the whole chain at once -- geometry, binning, and estimator -- on
data with no lens, no noise and no aliasing. If C6 does not read half a pixel
along the diagonal, the hypothesis is wrong before any real pixel is touched.

THE REAL MEASUREMENT
--------------------
Grid of ROIs across the field, on the same frame rendered both ways, then

    d(x, y) = c + k * r_hat(x, y)

fitted per component to split the constant (binning) from the radial (lens).
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m95c as C  # noqa: E402

BIN = os.path.join(C.OUT, "armF-f183.tif")
DEMO = os.path.join(C.OUT, "armF-f183-demo.tif")
S = 256


# ---------------------------------------------------------------- C6
def synth_scene(n, cutoff, seed):
    """Band-limited random field on the SENSOR grid.

    Band-limited strictly below the binned Nyquist (0.25 cy/sensor px) so that
    binning introduces no aliasing. Aliasing would fold high frequencies onto
    low ones with a phase error, which is a second effect and would contaminate
    a measurement whose whole subject is phase.
    """
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    r = np.sqrt(fy**2 + fx**2)
    return np.real(np.fft.ifft2(np.fft.fft2(a) * (r <= cutoff)))


def bin_rggb(f):
    """Exactly `merge_cmd.rs`'s binning of an RGGB mosaic, on a mono scene.

        R = site(2px,   2py)
        G = (site(2px+1, 2py) + site(2px, 2py+1)) / 2
        B = site(2px+1, 2py+1)

    A mono scene is used so that the three channels differ ONLY by where they
    were sampled. Any displacement measured between them is therefore the
    sampling geometry and nothing else -- no scene colour, no lens.
    """
    r = f[0::2, 0::2]
    g1 = f[0::2, 1::2]
    g2 = f[1::2, 0::2]
    b = f[1::2, 1::2]
    return r, 0.5 * (g1 + g2), b


def c6_synthetic():
    print("== C6: synthetic RGGB binning, truth known by construction ==")
    rows = []
    for seed in (1, 2, 3, 4, 5):
        f = synth_scene(1024, 0.20, seed)
        r, g, b = bin_rggb(f)
        drb = C.phase_ramp_shift(r, b)
        drg = C.phase_ramp_shift(r, g)
        dgb = C.phase_ramp_shift(g, b)
        rows.append(
            {
                "seed": seed,
                "R_to_B": [drb[0], drb[1]],
                "R_to_G": [drg[0], drg[1]],
                "G_to_B": [dgb[0], dgb[1]],
            }
        )
        print(
            "  seed %d  R->B (%+.4f,%+.4f)   R->G (%+.4f,%+.4f)   G->B (%+.4f,%+.4f)"
            % (seed, drb[0], drb[1], drg[0], drg[1], dgb[0], dgb[1])
        )
    rb = np.array([r_["R_to_B"] for r_ in rows])
    rg = np.array([r_["R_to_G"] for r_ in rows])
    m_rb, m_rg = rb.mean(axis=0), rg.mean(axis=0)
    print("  mean R->B = (%+.4f, %+.4f) binned px" % (m_rb[0], m_rb[1]))
    print("  mean R->G = (%+.4f, %+.4f) binned px" % (m_rg[0], m_rg[1]))
    # The bar: half a pixel on both components of R->B, quarter on R->G.
    ok = (
        np.all(np.abs(np.abs(m_rb) - 0.5) < 0.02)
        and np.all(np.abs(np.abs(m_rg) - 0.25) < 0.02)
        and np.all(np.sign(m_rb) == np.sign(m_rg))
    )
    print("  C6: %s (bars: |R->B| = 0.50, |R->G| = 0.25, same sign)" % ("PASS" if ok else "FAIL"))
    return ok, rows, m_rb.tolist(), m_rg.tolist()


# ---------------------------------------------------------------- field grid
def field_rois(h, w, s, nx, ny, margin=64):
    ys = np.linspace(margin, h - s - margin, ny).astype(int)
    xs = np.linspace(margin, w - s - margin, nx).astype(int)
    return [(int(y), int(x)) for y in ys for x in xs]


def measure(img, rois, scale, detail_min):
    """Per-ROI R->B and R->G displacement, expressed in BINNED px.

    `scale` is 1 for the binned render and 2 for the demosaiced one, whose
    pixels are sensor pitch; dividing by it puts both on one axis so the
    constant terms are directly comparable, which is what C4 requires.
    """
    out = []
    for y, x in rois:
        yy, xx, ss = y * scale, x * scale, S * scale
        r = img[yy : yy + ss, xx : xx + ss, 0].astype(np.float64)
        g = img[yy : yy + ss, xx : xx + ss, 1].astype(np.float64)
        b = img[yy : yy + ss, xx : xx + ss, 2].astype(np.float64)
        hp = C.highpass(g, 4.0)
        detail = float(np.std(hp))
        if detail < detail_min:
            continue
        drb = C.phase_ramp_shift(r, b)
        drg = C.phase_ramp_shift(r, g)
        out.append(
            {
                "y": y,
                "x": x,
                "detail": detail,
                "rb_dy": drb[0] / scale,
                "rb_dx": drb[1] / scale,
                "rb_rms": drb[2],
                "rg_dy": drg[0] / scale,
                "rg_dx": drg[1] / scale,
            }
        )
    return out


def fit_const_plus_radial(rows, key_y, key_x, cy, cx):
    """Split d(x,y) = c + k * r_hat into the constant and radial parts.

    Solved as one weighted least-squares over both components together, since
    `k` is shared between them and `c` is not.
    """
    A, rhs = [], []
    for r in rows:
        ry, rx = r["y"] + S / 2 - cy, r["x"] + S / 2 - cx
        n = np.hypot(ry, rx)
        uy, ux = (ry / n, rx / n) if n > 0 else (0.0, 0.0)
        A.append([1.0, 0.0, uy])
        rhs.append(r[key_y])
        A.append([0.0, 1.0, ux])
        rhs.append(r[key_x])
    A = np.array(A)
    rhs = np.array(rhs)
    sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    resid = rhs - A @ sol
    return {
        "c_dy": float(sol[0]),
        "c_dx": float(sol[1]),
        "k_radial": float(sol[2]),
        "resid_rms": float(np.sqrt(np.mean(resid**2))),
        "n_roi": len(rows),
    }


def main():
    res = {}
    c6ok, c6rows, c6_rb, c6_rg = c6_synthetic()
    res["C6"] = {"rows": c6rows, "mean_R_to_B": c6_rb, "mean_R_to_G": c6_rg, "pass": bool(c6ok)}
    if not c6ok:
        C.jdump("s1_cositing.json", res)
        print("\nC6 FAILED -- the hypothesis is wrong before any real pixel. Stopping.")
        return 1

    print("\n== real frame 183, same frame through both output paths ==")
    ib = C.load_tif(BIN)
    idm = C.load_tif(DEMO)
    print("  binned %s   demosaiced %s" % (ib.shape, idm.shape))
    h, w = ib.shape[0], ib.shape[1]
    cy, cx = h / 2.0, w / 2.0

    rois = field_rois(h, w, S, nx=6, ny=4)
    # One detail floor, chosen from the binned render and reused verbatim on the
    # demosaiced one, so both arms use the SAME ROIs. C4 requires that.
    probe = measure(ib, rois, 1, detail_min=-1.0)
    dets = sorted(p["detail"] for p in probe)
    floor = dets[len(dets) // 3]
    print("  detail floor (lower third of ROIs dropped) = %.2f DN" % floor)

    rb_bin = measure(ib, rois, 1, floor)
    keep = {(r["y"], r["x"]) for r in rb_bin}
    rb_dem = [r for r in measure(idm, rois, 2, -1.0) if (r["y"], r["x"]) in keep]
    print("  ROIs kept: binned %d, demosaiced %d" % (len(rb_bin), len(rb_dem)))
    assert len(rb_bin) == len(rb_dem), "ROI sets diverged; C4 comparison invalid"

    fb = fit_const_plus_radial(rb_bin, "rb_dy", "rb_dx", cy, cx)
    fd = fit_const_plus_radial(rb_dem, "rb_dy", "rb_dx", cy, cx)
    gb = fit_const_plus_radial(rb_bin, "rg_dy", "rg_dx", cy, cx)
    gd = fit_const_plus_radial(rb_dem, "rg_dy", "rg_dx", cy, cx)

    print("\n  R->B  binned      c = (%+.4f, %+.4f)  k_radial %+.4f  resid %.4f  n=%d"
          % (fb["c_dy"], fb["c_dx"], fb["k_radial"], fb["resid_rms"], fb["n_roi"]))
    print("  R->B  demosaiced  c = (%+.4f, %+.4f)  k_radial %+.4f  resid %.4f  n=%d"
          % (fd["c_dy"], fd["c_dx"], fd["k_radial"], fd["resid_rms"], fd["n_roi"]))
    print("  R->G  binned      c = (%+.4f, %+.4f)  k_radial %+.4f"
          % (gb["c_dy"], gb["c_dx"], gb["k_radial"]))
    print("  R->G  demosaiced  c = (%+.4f, %+.4f)  k_radial %+.4f"
          % (gd["c_dy"], gd["c_dx"], gd["k_radial"]))

    mag_bin = float(np.hypot(fb["c_dy"], fb["c_dx"]))
    mag_dem = float(np.hypot(fd["c_dy"], fd["c_dx"]))
    print("\n  |c| binned     = %.4f binned px" % mag_bin)
    print("  |c| demosaiced = %.4f binned px" % mag_dem)
    print("  C4 power control: the instrument read %.4f px on the binned render"
          % mag_bin)
    print("     using the SAME ROIs and settings, so the demosaiced %.4f px is a"
          % mag_dem)
    print("     measured absence and not a silent instrument.")

    res["real"] = {
        "rb_binned_fit": fb,
        "rb_demosaic_fit": fd,
        "rg_binned_fit": gb,
        "rg_demosaic_fit": gd,
        "per_roi_binned": rb_bin,
        "per_roi_demosaic": rb_dem,
        "mag_c_binned_px": mag_bin,
        "mag_c_demosaic_px": mag_dem,
        "detail_floor": floor,
        "centre": [cy, cx],
    }
    C.jdump("s1_cositing.json", res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
