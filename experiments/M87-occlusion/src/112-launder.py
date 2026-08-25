"""M87 / probe -- which direction does 8-bit laundering push MY statistics?

ORCH first broadcast the PIL defect as a false-NULL hazard, then corrected
itself: M120 measured a band-pass statistic reading HIGHER through PIL
(Q = 4.407 laundered vs 4.337 true, +1.6%), so quantisation ADDS band-pass
energy.  Both directions are real and which one hits you depends on the
statistic.  ORCH asked me to say which of mine are which.

Rather than inherit M120's number I replicate the effect on my own operands,
and -- more usefully -- I measure what laundering would have done to the
statistic my headline actually rests on.

The design point: comparing a 0..255 PNG against a 0..65535 TIFF confounds
quantisation with SCALE (a 257x factor before any physics).  So both arms here
run on the SAME array, one of them passed through a round trip to 8 bits and
back.  The only difference between arms is the quantisation.

Registered before the numbers exist:
  Q1  band-pass (mean|grad|): laundered / true > 1.000  -- energy ADDED.
      Predicted magnitude: a few percent, same order as M120's +1.6%.
  Q2  small-signal (the veil depth, a median-level difference): laundering
      moves it TOWARD ZERO, i.e. |V_laundered| < |V_true|.
  Q3  the residual veil, ~2.9%, is the number ORCH flagged as "precisely the
      size of thing that floor destroys".  Registered prediction: on the
      LUMA CUBE's own scale the 8-bit quantum is ~14 DN, and the residual is
      ~4% of a ~1900 DN pedestal, i.e. ~76 DN -- about 5x the quantum.  So I
      predict it SURVIVES, and is degraded but not destroyed.  If Q3 fails,
      my residual was never measurable and I must say so.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
SHIP = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")

M120_RATIO = 4.407 / 4.337


def launder(a):
    """Exactly what an 8-bit reader does: quantise to 256 levels, restore scale."""
    lo, hi = float(a.min()), float(a.max())
    q = np.round((a - lo) / max(hi - lo, 1e-9) * 255.0)
    return q / 255.0 * (hi - lo) + lo


def meangrad(g):
    gy, gx = np.gradient(g.astype(np.float64))
    return float(np.hypot(gx, gy).mean())


def main():
    out = {"registered": {"Q1": "laundered/true > 1.000 (band-pass inflates)",
                          "Q2": "|V_laundered| < |V_true| (small-signal -> zero)",
                          "Q3": "residual survives; quantum ~14 DN vs signal ~76 DN",
                          "m120_ratio": M120_RATIO}}

    # ---- Q1: band-pass, on the real render, quantisation isolated ----------
    print("=== Q1: band-pass (mean|grad|), same array, quantisation only ===")
    a = tifffile.imread(SHIP / "30-SHIP-BEFORE-default.tif")
    assert a.dtype == np.uint16, a.dtype
    g = a[1200:1900, 300:1400, 1].astype(np.float64)
    t, l = meangrad(g), meangrad(launder(g))
    print(f"  true       mean|grad| {t:9.4f}")
    print(f"  laundered  mean|grad| {l:9.4f}")
    print(f"  ratio {l / t:.4f}   (M120 measured {M120_RATIO:.4f} on its own operands)")
    q1 = l / t > 1.0
    print(f"  Q1 -> {'PASS, energy ADDED' if q1 else 'FAIL, energy removed'}")
    out["Q1"] = {"true": t, "laundered": l, "ratio": l / t, "pass": q1}

    # ---- Q2/Q3: the headline statistic, laundered ------------------------
    # Uses 70-veil.py's OWN mask/distance/profile machinery (its lines 110-135),
    # not a reconstruction. A first draft of this probe fabricated the distance
    # field from a percentile threshold and reported V = +190.77%, which is
    # nowhere near the real -6.68%. It ran, it printed, and it was measuring
    # two arbitrary regions. Recorded because a control pointed at the wrong
    # node still produces a number.
    print("\n=== Q2/Q3: the veil depth, the number the headline rests on ===")
    sys.path.insert(0, str(HERE / "src"))
    import m87lib as L
    from scipy.ndimage import distance_transform_edt

    sel = np.asarray(np.load(CACHE / "bee3-leg-sel.npy"))
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1
    fmask, _ = L.foreground_mask(sel)
    dd = np.rint(distance_transform_edt(~fmask)).astype(np.int32)
    inner = np.zeros_like(dd, bool)
    inner[M:M + 700, M:M + 1100] = True
    valid = (~fmask) & inner
    dv = dd[valid]
    order = np.argsort(dv, kind="stable")
    edges = np.searchsorted(dv[order], np.arange(0, 202))

    def prof(img):
        v = img[valid][order]
        o = np.full(201, np.nan)
        for d in range(201):
            a, b = edges[d], edges[d + 1]
            if b - a >= 200:
                o[d] = np.median(v[a:b])
        return o

    def veil(img):
        p = prof(img)
        near = np.nanmedian(p[2:23])
        far = np.nanmedian(p[80:121])
        return float(100.0 * (near - far) / far), float(far)

    quantum = (float(sel.max()) - float(sel.min())) / 255.0
    vt, far_t = veil(sel)
    vl, _ = veil(launder(sel))
    f0 = np.asarray(cube[0])
    ft, _ = veil(f0)
    fl, _ = veil(launder(f0))
    print(f"  8-bit quantum on this cube: {quantum:.2f} DN "
          f"(range {sel.min():.0f}..{sel.max():.0f}); far pedestal {far_t:.0f} DN")
    print(f"  merge  V true {vt:+8.4f}%   laundered {vl:+8.4f}%   "
          f"d {vl - vt:+.4f} pp")
    print(f"  frame0 V true {ft:+8.4f}%   laundered {fl:+8.4f}%   "
          f"d {fl - ft:+.4f} pp")
    q2 = abs(vl) < abs(vt)
    q3 = abs(vl) > 0.5 * abs(vt)
    print(f"  Q2 -> {'PASS, pulled toward zero' if q2 else 'FAIL, grew'}")
    print(f"  Q3 -> {'PASS, survives' if q3 else 'FAIL, destroyed'}"
          f"   retains {100 * abs(vl) / max(abs(vt), 1e-9):.1f}% of the true depth")
    out["Q2"] = {"v_true": vt, "v_laundered": vl, "far_dn": far_t,
                 "f0_true": ft, "f0_laundered": fl, "pass": q2}
    out["Q3"] = {"quantum_dn": quantum, "retained_frac": abs(vl) / max(abs(vt), 1e-9),
                 "pass": q3}

    print("\nCLASSIFICATION of M87's statistics:")
    print("  band-pass, inflatable : 44-detail-check.py mean|grad| (8-bit PNG in)")
    print("                          -- superseded by 47-detail-control.py (tifffile)")
    print("  small-signal, floorable: the veil depth / residual (rawpy, never a TIFF)")
    with open(DATA / "launder-direction.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"wrote {DATA / 'launder-direction.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
