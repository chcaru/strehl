"""M69 arm A3 -- the transfer curve rho(nu/s), and the decomposition of the two
mechanisms that make the response noise texture-dependent.

M-a  Rice/Rayleigh.  |grad| = hypot(gx, gy) with gx, gy uncorrelated and of equal
     variance s^2 is Rayleigh at zero signal (SD 0.6551 s) and tends to a
     projected Gaussian at strong signal (SD -> s). The per-sample noise of the
     operator therefore rises with the deterministic gradient nu, with a hard
     ceiling of 1/sqrt(2 - pi/2) = 1.5264.

M-b  The sigma divisor is evaluated at the NOISY centre luma, so the division
     injects a second, multiplicative noise term proportional to the response
     magnitude. It is absent from the crate's calibration plant, whose gain is
     1e-4 and whose signal is zero.

A3.1  synthetic plant, known nu/s, several texture correlation lengths.
A3.2  the closed-form predictor, tested against A3.1.
A3.3  M-b isolated on real latents by freezing the divisor at the clean latent.
A3.4  M66's REAL arm re-expressed on the curve, with and without its frozen-eta
      inflation of nu.
"""

import json
import pathlib
import sys

import numpy as np
from scipy.stats import rice

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

a2mod = __import__("importlib").import_module("20-a2-m66-replication")

SIZE = 512
NREP = 48
UNIT_GAIN = 1e-4
Z_GRID = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 9.0, 14.0, 22.0, 40.0]
ELLS = [2.0, 4.0, 8.0, 16.0]

RICE_SD0 = np.sqrt(2.0 - np.pi / 2.0)


def r_of_z(z):
    """Rice SD at ratio z, divided by the Rayleigh SD -- per-sample inflation.

    scipy's `rice.std` overflows above b ~ 10; past that the exact variance
    s^2 (2 + b^2) - mean^2 collapses to s^2 (1 - 1/(4 b^2)), which is used there.
    """
    z = np.maximum(np.asarray(z, dtype=np.float64), 0.0)
    out = np.empty(z.shape, dtype=np.float64) if z.ndim else np.array(0.0)
    small = z <= 8.0
    out = np.where(small, rice.std(np.where(small, z, 0.0)), np.sqrt(np.maximum(1.0 - 0.25 / np.maximum(z, 1e-9) ** 2, 0.0)))
    return out / RICE_SD0


def unit_sigma(luma):
    rn = np.sqrt(2.0) / UNIT_GAIN
    v = UNIT_GAIN * np.maximum(luma, 0.0) + (rn * UNIT_GAIN) ** 2
    return np.sqrt(0.25 * (v + v))


def smooth_field(rng, size, ell):
    w = rng.standard_normal((size, size))
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    h = np.exp(-2.0 * (np.pi * ell) ** 2 * (fy * fy + fx * fx))
    f = np.fft.ifft2(np.fft.fft2(w) * h).real
    return f / f.std()


S_SOBEL = 0.125 * np.sqrt(12.0)


def make_latent(rng, z, ell, size=SIZE):
    if z == 0.0:
        return np.zeros((size, size))
    base = smooth_field(rng, size, ell)
    gx, gy = m69.sobel_components(base)
    rms = np.sqrt(np.mean(gx * gx + gy * gy))
    return base * (z * S_SOBEL / rms)


def predictor(latent, sigma_luma):
    """P1: sqrt of the double-box mean of r(z_q)^2 over the operator footprint.

    Assumes the effective sample count that FOCUS_NOISE_SD already encodes is
    unchanged by texture -- only the per-sample SD moves. That assumption is
    what A3.2 tests.
    """
    gx, gy = m69.sobel_components(latent)
    nu = np.hypot(gx, gy)
    z = nu / (S_SOBEL * sigma_luma)
    r2 = r_of_z(z) ** 2
    return np.sqrt(
        m69.box_clamped(m69.box_clamped(r2, m69.WINDOW_RADIUS), m69.REGULARISER_RADIUS)
    )


def measure(latent, sigma_fn, nrep, seed, noise_sd):
    rng = np.random.default_rng(seed)
    acc = None
    for _ in range(nrep):
        luma = latent + noise_sd * rng.standard_normal(latent.shape)
        reg = m69.regularised(luma, sigma=sigma_fn(luma))
        if acc is None:
            acc = m69.Welford(reg.shape)
        acc.push(reg)
    return acc.sd()


def a31():
    m69.banner("A3.1 / A3.2 -- transfer curve rho(nu/s) and the P1 predictor")
    print(f"  Rayleigh SD ratio r(0) = 1 by construction; ceiling r(inf) = {1 / RICE_SD0:.4f}")
    print(f"\n  {'ell':>5} {'nu/s':>7} {'rho measured':>13} {'P1 predicted':>13} {'rel err':>9}")
    print("  " + "-" * 52)
    rows = []
    for ell in ELLS:
        for z in Z_GRID:
            rng = np.random.default_rng(int(1000 * ell) + int(10 * z))
            latent = make_latent(rng, z, ell)
            sd = measure(latent, unit_sigma, NREP, 4242 + int(10 * z), 1.0)
            rho = float(m69.interior(sd).mean() / m69.FOCUS_NOISE_SD)
            pred = predictor(latent, unit_sigma(latent))
            rho_p = float(m69.interior(pred).mean())
            err = rho / rho_p - 1.0
            print(f"  {ell:>5.0f} {z:>7.1f} {rho:>13.4f} {rho_p:>13.4f} {err:>+8.2%}")
            rows.append(
                {"ell": ell, "z": z, "rho": rho, "pred": rho_p, "rel_err": float(err)}
            )
    errs = np.array([abs(r["rel_err"]) for r in rows if r["z"] > 0])
    med = float(np.median(errs))
    print(f"\n  P1 median |relative error| over z > 0 = {med:.2%}   bar 10%"
          f"  ->  {'MET' if med <= 0.10 else 'NOT MET'}")
    return rows, med


def a33():
    m69.banner("A3.3 -- M-b isolated: sigma divisor frozen at the clean latent")
    print("  Shipped chain divides by sigma(L_observed). Freezing the divisor at")
    print("  sigma(L_latent) removes mechanism M-b and leaves M-a alone.\n")
    out = {}
    m69.print_header()
    for tag, stack, name, y, x in (
        ("M62", "109MSDCF", "DSC00020.ARW", 1024, 4096),
        ("coffee-bean", "coffee-bean", None, None, None),
    ):
        lat, path, y, x = a2mod.read_latent(stack, name, y, x)
        iso = m69.iso_of(path)
        sd_dn = a2mod.raw_noise_sd(lat, iso)
        clean_luma = m69.luma_from_raw(lat)
        frozen = m69.green_luma_sigma(clean_luma, iso)

        for mode in ("shipped", "frozen-divisor"):
            rng = np.random.default_rng(555)
            acc = None
            for _ in range(a2mod.NREP_EXTRA):
                frame = lat + sd_dn * rng.standard_normal(lat.shape)
                luma = m69.luma_from_raw(frame)
                sig = m69.green_luma_sigma(luma, iso) if mode == "shipped" else frozen
                reg = m69.regularised(luma, sigma=sig)
                if acc is None:
                    acc = m69.Welford(reg.shape)
                acc.push(reg)
            s = m69.summarise(m69.interior(acc.sd()), f"{tag}/{mode}")
            m69.print_row(s)
            out[f"{tag}/{mode}"] = s
        a = out[f"{tag}/shipped"]["rho"]
        b = out[f"{tag}/frozen-divisor"]["rho"]
        print(f"    -> M-b contributes {a / b - 1:+.2%} of rho on {tag}"
              f"  (shipped {a:.4f} vs frozen {b:.4f})\n")
    return out


def a34(rows):
    m69.banner("A3.4 -- M66's frozen-eta latent, priced on the curve")
    print("  A real frame is T + eta. M66's REAL replicate is T + eta_0 + eps, so its")
    print("  latent carries E|grad eta|^2 = 2 s^2 of gradient that a real frame's")
    print("  latent does not. On the operator's own scale that inflates nu^2 by 2 s^2,")
    print("  i.e. z_M66^2 = z_true^2 + 2.\n")
    out = {}
    for tag, stack, name, y, x in (
        ("M62", "109MSDCF", "DSC00020.ARW", 1024, 4096),
        ("coffee-bean", "coffee-bean", None, None, None),
        ("wrapped-text-1", "wrapped-text-1", None, None, None),
        ("bee-1", "bee-1", None, None, None),
    ):
        lat, path, y, x = a2mod.read_latent(stack, name, y, x)
        iso = m69.iso_of(path)
        luma = m69.luma_from_raw(lat)
        sig = m69.green_luma_sigma(luma, iso)
        gx, gy = m69.sobel_components(luma)
        s = S_SOBEL * sig
        z_obs = np.hypot(gx, gy) / s
        z_true = np.sqrt(np.maximum(z_obs**2 - 2.0, 0.0))
        r_obs = m69.interior(
            np.sqrt(
                m69.box_clamped(
                    m69.box_clamped(r_of_z(z_obs) ** 2, m69.WINDOW_RADIUS),
                    m69.REGULARISER_RADIUS,
                )
            )
        )
        r_true = m69.interior(
            np.sqrt(
                m69.box_clamped(
                    m69.box_clamped(r_of_z(z_true) ** 2, m69.WINDOW_RADIUS),
                    m69.REGULARISER_RADIUS,
                )
            )
        )
        print(
            f"  {tag:<16} ISO {iso:>4.0f}  median z_obs {np.median(z_obs):6.2f}"
            f"  median z_true {np.median(z_true):6.2f}"
            f"   P1(z_obs) {r_obs.mean():.4f}   P1(z_true) {r_true.mean():.4f}"
            f"   ratio {r_obs.mean() / r_true.mean():.4f}"
        )
        out[tag] = {
            "iso": iso,
            "median_z_obs": float(np.median(z_obs)),
            "median_z_true": float(np.median(z_true)),
            "p1_obs": float(r_obs.mean()),
            "p1_true": float(r_true.mean()),
            "p1_obs_p05": float(np.percentile(r_obs, 5)),
            "p1_obs_p95": float(np.percentile(r_obs, 95)),
            "p1_true_p05": float(np.percentile(r_true, 5)),
            "p1_true_p95": float(np.percentile(r_true, 95)),
            "p1_true_iqr_rel": float(
                (np.percentile(r_true, 75) - np.percentile(r_true, 25))
                / np.median(r_true)
            ),
        }
    return out


def main():
    m69.banner("M69 arm A3 -- what makes the response noise texture-dependent")
    m69.dump_constants()
    rows, med = a31()
    mb = a33()
    curve = a34(rows)
    (m69.OUT / "30-a3.json").write_text(
        json.dumps(
            {"transfer": rows, "p1_median_rel_err": med, "mb": mb, "latents": curve},
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\n  wrote out/30-a3.json")


if __name__ == "__main__":
    main()
