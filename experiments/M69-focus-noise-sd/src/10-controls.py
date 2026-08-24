"""M69 controls K1, K5, K6 -- and the closed-form Rice ceiling.

K1  my pipeline on the crate's own plant must return rho within 0.02 of 1.
K6  a plant whose luma noise is scaled by 1.30 must read rho = 1.30 +- 0.01.
K5  the A3 plant at nu/s = 0 must read rho = 1.00 +- 0.02.

Nothing measured by M69 is believed unless K1 passes.
"""

import json
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import m69  # noqa: E402

SIZE = 512
SEEDS = 12
UNIT_GAIN = 1e-4


def unit_sigma(luma):
    """merge.rs::unit_sigma_model -- gain 1e-4, read_noise_e = sqrt(2)/gain."""
    rn = np.sqrt(2.0) / UNIT_GAIN
    v = UNIT_GAIN * np.maximum(luma, 0.0) + (rn * UNIT_GAIN) ** 2
    return np.sqrt(0.25 * (v + v))


def crate_plant(rng, size=SIZE, scale=1.0):
    return scale * rng.standard_normal((size, size))


def arm(scale, seeds=SEEDS, size=SIZE, label=""):
    sds = []
    for s in range(seeds):
        rng = np.random.default_rng(20250 + s)
        luma = crate_plant(rng, size, scale)
        reg = m69.regularised(luma, sigma=unit_sigma(luma))
        sds.append(float(m69.interior(reg, 22).std(ddof=1)))
    sds = np.array(sds)
    mean = sds.mean()
    sem = sds.std(ddof=1) / np.sqrt(len(sds))
    print(
        f"  {label:<28} sd = {mean:.6e} +- {sem:.2e}   rho = {mean / m69.FOCUS_NOISE_SD:.4f}",
        flush=True,
    )
    return mean, sem


def smooth_field(rng, size, ell):
    """Isotropic Gaussian random field, unit variance, correlation length `ell`."""
    w = rng.standard_normal((size, size))
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    k2 = fy * fy + fx * fx
    h = np.exp(-2.0 * (np.pi * ell) ** 2 * k2)
    f = np.fft.ifft2(np.fft.fft2(w) * h).real
    return f / f.std()


def a3_plant(rng, z, ell, size=SIZE):
    """Bandlimited texture plus unit white noise, scaled so E|grad_det| = z * s_sobel.

    s_sobel = 0.125 * sqrt(12) * sigma_luma is the per-component SD the Sobel
    stencil imposes on white luma noise of SD sigma_luma (verified in K0 below).
    """
    base = smooth_field(rng, size, ell)
    g = m69.sobel_mag(base)
    med = np.median(g[8:-8, 8:-8])
    s_sobel = 0.125 * np.sqrt(12.0)
    amp = 0.0 if z == 0 else (z * s_sobel) / med
    return amp * base


def main():
    m69.banner("M69 / K0 -- structural constants of the Sobel stencil")
    m69.dump_constants()
    rng = np.random.default_rng(7)
    n = 2048
    w = rng.standard_normal((n, n))
    gx, gy = m69.sobel_components(w)
    s_pred = 0.125 * np.sqrt(12.0)
    print(
        f"\n  Sobel component SD  measured gx {gx.std():.6f}  gy {gy.std():.6f}"
        f"   predicted 0.125*sqrt(12) = {s_pred:.6f}"
    )
    print(f"  corr(gx, gy)        {np.corrcoef(gx.ravel(), gy.ravel())[0, 1]:+.6f}  (predicted 0)")
    mag = np.hypot(gx, gy)
    print(
        f"  |grad| mean         {mag.mean():.6f}   Rayleigh prediction"
        f" s*sqrt(pi/2) = {s_pred * np.sqrt(np.pi / 2):.6f}"
    )
    print(
        f"  |grad| SD           {mag.std():.6f}   Rayleigh prediction"
        f" s*sqrt(2-pi/2) = {s_pred * np.sqrt(2 - np.pi / 2):.6f}"
    )
    r_inf = 1.0 / np.sqrt(2 - np.pi / 2)
    print(f"\n  Rice ceiling r(inf) = 1/sqrt(2-pi/2) = {r_inf:.4f}")
    print("  (the largest per-sample noise inflation this mechanism can produce)")

    m69.banner("M69 / K1 -- crate plant through the M69 pipeline")
    print(f"  crate FOCUS_NOISE_SD = {m69.FOCUS_NOISE_SD:.6f}")
    mean, sem = arm(1.0, label="K1 crate plant (512^2, 12)")
    rho = mean / m69.FOCUS_NOISE_SD
    k1 = abs(rho - 1.0) <= 0.02
    print(f"\n  K1  |rho - 1| = {abs(rho - 1.0):.4f}  bar 0.02   ->  {'MET' if k1 else 'NOT MET'}")

    m69.banner("M69 / K6 -- planted scale 1.30 must read back as 1.30")
    m30, _ = arm(1.30, label="K6 luma noise x1.30")
    ratio = m30 / mean
    k6 = abs(ratio - 1.30) <= 0.01
    print(f"\n  K6  recovered scale = {ratio:.4f}  planted 1.30  bar +-0.01  ->  {'MET' if k6 else 'NOT MET'}")

    m69.banner("M69 / K5 -- A3 plant at nu/s = 0")
    sds = []
    for s in range(SEEDS):
        rng = np.random.default_rng(31400 + s)
        luma = a3_plant(rng, 0.0, 8.0) + rng.standard_normal((SIZE, SIZE))
        reg = m69.regularised(luma, sigma=unit_sigma(luma))
        sds.append(float(m69.interior(reg, 22).std(ddof=1)))
    sds = np.array(sds)
    rho5 = sds.mean() / m69.FOCUS_NOISE_SD
    k5 = abs(rho5 - 1.0) <= 0.02
    print(f"  A3 plant z=0            sd = {sds.mean():.6e}   rho = {rho5:.4f}")
    print(f"\n  K5  |rho - 1| = {abs(rho5 - 1.0):.4f}  bar 0.02   ->  {'MET' if k5 else 'NOT MET'}")

    res = {
        "sobel_component_sd": float(gx.std()),
        "sobel_component_sd_pred": float(s_pred),
        "corr_gx_gy": float(np.corrcoef(gx.ravel(), gy.ravel())[0, 1]),
        "rice_ceiling": float(r_inf),
        "K1_sd": float(mean),
        "K1_sem": float(sem),
        "K1_rho": float(rho),
        "K1": bool(k1),
        "K6_ratio": float(ratio),
        "K6": bool(k6),
        "K5_rho": float(rho5),
        "K5": bool(k5),
    }
    (m69.OUT / "10-controls.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("\n  wrote out/10-controls.json")


if __name__ == "__main__":
    main()
