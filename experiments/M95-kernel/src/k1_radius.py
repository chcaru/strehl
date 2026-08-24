"""Arm 9 k1 -- choose the B-spline FIR radius by measurement, not by taste.

The prefiltered cubic B-spline is normally implemented as a recursive IIR pass
over the whole plane followed by evaluation of the beta^3 basis. Resampler::sample
is a pure function of (plane, x, y) and merge_cmd.rs is contended, so there is
nowhere to hold coefficients. The prefilter therefore has to be folded into the
kernel:

    prefilter impulse response   h[k] = sqrt(3) * z^|k|,  z = sqrt(3) - 2
    effective kernel             w(u) = sum_k h[k] * beta3(u - k)

truncated at |k| <= K and evaluated over taps |j| <= R. This picks the smallest
R that matches the exact IIR result to better than 1e-4 on a real tile, because
support() feeds sample_checked and every extra pixel of radius rejects a wider
border at the frame edge.

Registered bars B20/B21 are in ../PRE-REGISTRATION.md.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "M95-coverage" / "src"))
import m95cov as M  # noqa: E402

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
OUT = Path(__file__).resolve().parents[1] / "out" / "k1_radius.json"

Z = np.sqrt(3.0) - 2.0
K_TRUNC = 24  # inner truncation of the prefilter sum; z^24 ~ 1e-14


def beta3(u):
    """Cubic B-spline basis, support (-2, 2)."""
    a = np.abs(np.asarray(u, dtype=np.float64))
    return np.where(
        a < 1.0,
        (4.0 - 6.0 * a * a + 3.0 * a**3) / 6.0,
        np.where(a < 2.0, ((2.0 - a) ** 3) / 6.0, 0.0),
    )


def w_eff(u):
    """The prefiltered B-spline's effective interpolating kernel."""
    u = np.asarray(u, dtype=np.float64)
    acc = np.zeros_like(u)
    for k in range(-K_TRUNC, K_TRUNC + 1):
        acc += np.sqrt(3.0) * (Z ** abs(k)) * beta3(u - k)
    return acc


def fir_weights(f, R):
    """Tap weights for fractional offset f in [0,1), taps j = -R+1 .. R."""
    j = np.arange(-R + 1, R + 1, dtype=np.float64)
    w = w_eff(f - j)
    return j.astype(int), w / w.sum()


def bspline_prefilter_exact(a, axis):
    """Unser's exact recursive prefilter -- the reference this FIR must match."""
    z = Z
    a = np.moveaxis(a.astype(np.float64), axis, 0).copy()
    n = a.shape[0]
    k = np.arange(min(n, 40))
    c0 = (a[: len(k)] * (z ** k)[:, None]).sum(axis=0) / (1.0 - z ** (2 * n))
    a *= 6.0
    a[0] = c0 * 6.0
    for i in range(1, n):
        a[i] += z * a[i - 1]
    a[-1] = (z / (z * z - 1.0)) * (a[-1] + z * a[-2])
    for i in range(n - 2, -1, -1):
        a[i] = z * (a[i + 1] - a[i])
    return np.moveaxis(a, 0, axis)


def shift_exact(tile, f):
    """Exact prefiltered B-spline sub-pixel shift by f along axis 0."""
    c = bspline_prefilter_exact(tile, 0)
    n = c.shape[0]
    out = np.zeros_like(c)
    for d in range(-2, 3):
        w = beta3(f - d)
        if w == 0.0:
            continue
        out += w * np.roll(c, -d, axis=0)
    return out


def shift_fir(tile, f, R):
    j, w = fir_weights(f, R)
    out = np.zeros_like(tile, dtype=np.float64)
    for jj, ww in zip(j, w):
        out += ww * np.roll(tile.astype(np.float64), -jj, axis=0)
    return out


def main():
    if not B0.exists():
        sys.exit("missing input")
    img = M.load_luma(B0)
    tiles = M.pick_tiles(img)[:8]
    print(f"source: {B0.name}  tiles {len(tiles)}\n")
    res = {"z": float(Z), "k_trunc": K_TRUNC}

    # -------------------------------------------------- B21 interpolating
    j0, w0 = fir_weights(0.0, 8)
    delta = np.zeros_like(w0)
    delta[np.where(j0 == 0)[0][0]] = 1.0
    e_interp = float(np.abs(w0 - delta).max())
    ok21 = e_interp < 1e-5
    print(f"B21 interpolating at integer phase  max|w - delta| = {e_interp:.3e}  "
          f"{'PASS' if ok21 else 'FAIL'}")
    res["B21_interp_err"] = e_interp
    res["B21_pass"] = ok21

    # ---------------------------------------------- B20 radius calibration
    # Interior only: the exact IIR uses whole-row support, so comparing at the
    # borders would measure boundary handling rather than kernel truncation.
    print(f"\n{'R':>3} {'taps':>5} {'max abs err vs exact IIR':>26}  bar 1e-4")
    rows, chosen = [], None
    for R in range(2, 13):
        worst = 0.0
        for ty, tx in tiles:
            t = img[ty : ty + M.TILE, tx : tx + M.TILE].astype(np.float64)
            if t.shape != (M.TILE, M.TILE):
                continue
            for f in (0.25, 0.5, 0.75):
                a = shift_exact(t, f)[R + 4 : -(R + 4)]
                b = shift_fir(t, f, R)[R + 4 : -(R + 4)]
                worst = max(worst, float(np.abs(a - b).max()))
        rows.append({"R": R, "taps": 2 * R, "max_err": worst})
        mark = "PASS" if worst < 1e-4 else ""
        print(f"{R:>3} {2 * R:>5} {worst:>26.3e}  {mark}")
        if worst < 1e-4 and chosen is None:
            chosen = R
    res["radius_sweep"] = rows
    res["R_chosen"] = chosen
    res["B20_pass"] = chosen is not None

    if chosen is None:
        print("\nB20 FAILS at every R <= 12 -- the B-spline does not ship.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1
    print(f"\nB20 PASSES. smallest radius clearing 1e-4: R = {chosen} "
          f"({2 * chosen} taps, support {float(chosen)})")

    # the weights the Rust will carry, printed so the port can be checked
    j, w = fir_weights(0.5, chosen)
    print(f"\nweights at f = 0.5, R = {chosen} (sum {w.sum():.12f}):")
    print("  " + "  ".join(f"{v:+.8f}" for v in w))
    res["weights_at_half"] = {"taps": j.tolist(), "w": w.tolist(),
                              "sum": float(w.sum())}

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
