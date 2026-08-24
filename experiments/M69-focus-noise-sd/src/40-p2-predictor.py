"""M69 -- P2, the derived per-pixel response-noise predictor.

A3 refuted P1, the pointwise-Rice predictor pre-registered under D3: the measured
transfer curve is not a function of nu/s at all. It falls with the texture's
correlation length, from rho = 1.14 at ell = 2 to rho = 0.28 at ell = 16, because
the Sobel stencil has zero DC gain. When the deterministic gradient DIRECTION is
coherent across the operator's window, the windowed mean of the projected noise
telescopes to a few edge columns and nearly cancels; when the direction scrambles
faster than the window, it does not.

P2 keeps that structure. Write the per-sample fluctuation of |grad| as a linear
part along the local gradient direction plus a rectified residual:

    d|grad|_q  ~  alpha(z_q) * (dhat_q . dgrad_q)  +  xi_q

alpha(z) = d/dnu E_Rice(nu, s) is the exact linear-regression coefficient, and
Var(xi) = Var_Rice(z) - alpha(z)^2 s^2 is what the linearisation leaves behind.
The linear part is propagated through the operator EXACTLY, using the closed-form
cross-correlation of the two Sobel stencils; the residual part is propagated as
white noise anchored at FOCUS_NOISE_SD, which is precisely the z = 0 limit the
crate measured. So the shipped constant survives as the anchor of a formula
rather than as the answer.

    sigma_F^2(p) = Var_lin(p) + FOCUS_NOISE_SD^2 * <Var(xi)_q / Var(xi)_0>_{K^2}

P2 is POST HOC. It was not pre-registered and D3 is reported NOT MET regardless
of how it scores.
"""

import json
import pathlib
import sys

import numpy as np
from scipy.signal import fftconvolve
from scipy.stats import rice

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

a3 = __import__("importlib").import_module("30-a3-transfer")
a2 = __import__("importlib").import_module("20-a2-m66-replication")

SX = np.array([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]]) * 0.125
SY = np.array([[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]]) * 0.125
S_SOBEL = 0.125 * np.sqrt(12.0)
RICE_VAR0 = 2.0 - np.pi / 2.0

ZGRID = np.concatenate([np.linspace(0.0, 8.0, 1601), np.array([1e9])])


def _tables():
    h = 1e-4
    m1 = rice.mean(np.maximum(ZGRID[:-1] - h, 0.0))
    m2 = rice.mean(ZGRID[:-1] + h)
    alpha = (m2 - m1) / (2.0 * h)
    alpha[0] = 0.0
    var = rice.var(ZGRID[:-1])
    resid = np.maximum(var - alpha**2, 0.0)
    return np.append(alpha, 1.0), np.append(resid, 0.0)


ALPHA_T, RESID_T = _tables()


def alpha_resid(z):
    z = np.asarray(z, dtype=np.float64)
    zc = np.clip(z, 0.0, 8.0)
    a = np.interp(zc, ZGRID[:-1], ALPHA_T[:-1])
    r = np.interp(zc, ZGRID[:-1], RESID_T[:-1])
    big = z > 8.0
    if np.any(big):
        a = np.where(big, 1.0 - 0.5 / np.maximum(z, 1e-9) ** 2, a)
        r = np.where(big, 0.75 / np.maximum(z, 1e-9) ** 2, r)
    return a, r


def _box(n):
    return np.ones((n, n)) / (n * n)


def combined_kernel(pad=2):
    k = fftconvolve(_box(2 * m69.WINDOW_RADIUS + 1), _box(2 * m69.REGULARISER_RADIUS + 1))
    return np.pad(k, pad)


K = combined_kernel()
KW = K * K
KW /= KW.sum()


def _cab(sa, sb):
    """C_ab(Delta) = sum_m Sa(m) Sb(m - Delta), Delta over a 5x5 lag window."""
    out = np.zeros((5, 5))
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            tot = 0.0
            for my in range(3):
                for mx in range(3):
                    qy, qx = my - dy, mx - dx
                    if 0 <= qy < 3 and 0 <= qx < 3:
                        tot += sa[my, mx] * sb[qy, qx]
            out[dy + 2, dx + 2] = tot
    return out


CXX, CXY, CYY = _cab(SX, SX), _cab(SX, SY), _cab(SY, SY)


def shift(a, dy, dx):
    out = np.zeros_like(a)
    ys = slice(max(0, -dy), a.shape[0] - max(0, dy))
    yd = slice(max(0, dy), a.shape[0] - max(0, -dy))
    xs = slice(max(0, -dx), a.shape[1] - max(0, dx))
    xd = slice(max(0, dx), a.shape[1] - max(0, -dx))
    out[yd, xd] = a[ys, xs]
    return out


def p2(latent, sigma_luma):
    """Per-pixel predicted sigma_F for a clean latent and its luma sigma field."""
    gx, gy = m69.sobel_components(latent)
    nu = np.hypot(gx, gy)
    s = S_SOBEL * sigma_luma
    z = nu / s
    a, resid = alpha_resid(z)
    with np.errstate(invalid="ignore", divide="ignore"):
        u = np.where(nu > 0, gx / np.maximum(nu, 1e-30), 0.0)
        v = np.where(nu > 0, gy / np.maximum(nu, 1e-30), 0.0)
    ax, ay = a * u, a * v

    var_lin = np.zeros_like(latent)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            c = {
                "xx": CXX[dy + 2, dx + 2],
                "xy": CXY[dy + 2, dx + 2],
                "yy": CYY[dy + 2, dx + 2],
            }
            if max(abs(c["xx"]), abs(c["xy"]), abs(c["yy"])) < 1e-15:
                continue
            g = K * shift(K, dy, dx)
            pxx = ax * shift(ax, -dy, -dx)
            pyy = ay * shift(ay, -dy, -dx)
            pxy = ax * shift(ay, -dy, -dx) + ay * shift(ax, -dy, -dx)
            acc = c["xx"] * pxx + c["yy"] * pyy + c["xy"] * pxy
            var_lin += fftconvolve(acc, g, mode="same")
    var_lin = np.maximum(var_lin, 0.0)

    var_white = (m69.FOCUS_NOISE_SD**2) * fftconvolve(resid / RICE_VAR0, KW, mode="same")
    return np.sqrt(var_lin + np.maximum(var_white, 0.0))


def check_synthetic():
    m69.banner("P2 -- against the A3.1 transfer curve")
    print(f"  {'ell':>5} {'nu/s':>7} {'rho measured':>13} {'P2':>10} {'rel err':>9}")
    print("  " + "-" * 49)
    rows = []
    for ell in a3.ELLS:
        for z in a3.Z_GRID:
            rng = np.random.default_rng(int(1000 * ell) + int(10 * z))
            latent = a3.make_latent(rng, z, ell)
            sd = a3.measure(latent, a3.unit_sigma, a3.NREP, 4242 + int(10 * z), 1.0)
            rho = float(m69.interior(sd).mean() / m69.FOCUS_NOISE_SD)
            pred = float(m69.interior(p2(latent, a3.unit_sigma(latent))).mean() / m69.FOCUS_NOISE_SD)
            err = rho / pred - 1.0
            print(f"  {ell:>5.0f} {z:>7.1f} {rho:>13.4f} {pred:>10.4f} {err:>+8.2%}")
            rows.append({"ell": ell, "z": z, "rho": rho, "p2": pred, "rel_err": float(err)})
    e = np.array([abs(r["rel_err"]) for r in rows])
    print(f"\n  P2 median |relative error| = {np.median(e):.2%}, worst {e.max():.2%}")
    return rows, float(np.median(e)), float(e.max())


def check_real():
    m69.banner("P2 -- against the A2 real latents (frozen-eta plant)")
    print("  The A2 plants freeze one noise realisation into the latent, so P2 is")
    print("  evaluated on that same frozen latent -- the comparison is like for like.\n")
    print(f"  {'latent':<16} {'rho measured':>13} {'P2':>10} {'rel err':>9}"
          f" {'P2 on debiased nu':>19}")
    print("  " + "-" * 72)
    rows = {}
    meas = json.loads((m69.OUT / "20-a2.json").read_text(encoding="utf-8"))["latents"]
    for tag, stack, name, y, x in (
        ("M62", "109MSDCF", "DSC00020.ARW", 1024, 4096),
        ("coffee-bean", "coffee-bean", None, None, None),
        ("wrapped-text-1", "wrapped-text-1", None, None, None),
        ("bee-1", "bee-1", None, None, None),
    ):
        lat, path, y, x = a2.read_latent(stack, name, y, x)
        iso = m69.iso_of(path)
        luma = m69.luma_from_raw(lat)
        sig = m69.green_luma_sigma(luma, iso)
        pred = float(m69.interior(p2(luma, sig)).mean() / m69.FOCUS_NOISE_SD)

        gx, gy = m69.sobel_components(luma)
        s = S_SOBEL * sig
        nu2 = np.maximum(gx * gx + gy * gy - 2.0 * s * s, 0.0)
        scale = np.sqrt(nu2 / np.maximum(gx * gx + gy * gy, 1e-30))
        pred_deb = float(m69.interior(p2_scaled(luma, sig, scale)).mean() / m69.FOCUS_NOISE_SD)

        key = "M62" if tag == "M62" else stack
        rho = meas[key]["REAL"]["rho"]
        print(f"  {tag:<16} {rho:>13.4f} {pred:>10.4f} {rho / pred - 1:>+8.2%}"
              f" {pred_deb:>19.4f}")
        rows[tag] = {
            "iso": iso,
            "rho_measured": rho,
            "p2": pred,
            "rel_err": float(rho / pred - 1.0),
            "p2_debiased": pred_deb,
        }
    return rows


def p2_scaled(latent, sigma_luma, scale):
    """P2 with the deterministic gradient shrunk by `scale` at every pixel.

    Used to price the frozen-eta inflation: a real frame's latent carries
    E|grad T|^2 = E|grad L|^2 - 2 s^2, not E|grad L|^2.
    """
    gx, gy = m69.sobel_components(latent)
    nu = np.hypot(gx, gy) * scale
    s = S_SOBEL * sigma_luma
    z = nu / s
    a, resid = alpha_resid(z)
    with np.errstate(invalid="ignore", divide="ignore"):
        n0 = np.hypot(gx, gy)
        u = np.where(n0 > 0, gx / np.maximum(n0, 1e-30), 0.0)
        v = np.where(n0 > 0, gy / np.maximum(n0, 1e-30), 0.0)
    ax, ay = a * u, a * v
    var_lin = np.zeros_like(latent)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            cxx, cxy, cyy = CXX[dy + 2, dx + 2], CXY[dy + 2, dx + 2], CYY[dy + 2, dx + 2]
            if max(abs(cxx), abs(cxy), abs(cyy)) < 1e-15:
                continue
            g = K * shift(K, dy, dx)
            acc = (
                cxx * (ax * shift(ax, -dy, -dx))
                + cyy * (ay * shift(ay, -dy, -dx))
                + cxy * (ax * shift(ay, -dy, -dx) + ay * shift(ax, -dy, -dx))
            )
            var_lin += fftconvolve(acc, g, mode="same")
    var_white = (m69.FOCUS_NOISE_SD**2) * fftconvolve(resid / RICE_VAR0, KW, mode="same")
    return np.sqrt(np.maximum(var_lin, 0.0) + np.maximum(var_white, 0.0))


def main():
    m69.banner("M69 -- P2 derived per-pixel predictor (POST HOC)")
    m69.dump_constants()
    print(f"\n  combined kernel {K.shape}, sum {K.sum():.6f},"
          f" 1/sum(K^2) = {1.0 / (K * K).sum():.1f} effective taps")
    print(f"  C_xx(0,0) = {CXX[2, 2]:.6f}   s^2 = {(0.125 * np.sqrt(12)) ** 2:.6f}")
    print(f"  C_xx(0,+-2) = {CXX[2, 4]:+.6f}  -> lag-2 correlation"
          f" {CXX[2, 4] / CXX[2, 2]:+.3f}")
    syn, med, worst = check_synthetic()
    real = check_real()
    (m69.OUT / "40-p2.json").write_text(
        json.dumps({"synthetic": syn, "median_rel_err": med, "worst_rel_err": worst,
                    "real": real}, indent=2),
        encoding="utf-8",
    )
    print("\n  wrote out/40-p2.json")


if __name__ == "__main__":
    main()
