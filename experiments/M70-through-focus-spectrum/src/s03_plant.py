"""M70 s03 - the plant, the placebo and the negative control.

Rule 3 / rule 13 / rule 20. Before the through-focus estimator is pointed at
the corpus, three things must be established, and each of them can fail:

  PLANT (positive control).  A REAL macro texture patch is declared the latent
  and pushed through a KNOWN through-focus OTF ladder with calibrated noise.
  Truth for `n_eff_MF` is then computable in closed form from the OTFs and the
  latent's own spectrum. The recovery ratio is measured, not assumed. Using a
  real patch rather than synthetic texture is deliberate: M63's lesson is that
  a plant whose relationship to real texture is unexamined is the failure mode.
  It is an inverse crime (the estimator sees exactly the OTF that was applied)
  and is therefore a control on the HARNESS, not on realism - same caveat M41
  attached to its own planted control.

  RULE 20 DISCHARGE (the input that makes the answer come out LARGE).  A static
  repeat burst: H_k = 1 for every frame, independent calibrated noise. Truth is
  n_eff_MF = K exactly. If the estimator cannot return ~K here it has no power
  to report "many frames carry mid-band signal" and every low reading on real
  data would be an artefact. This is the arm that gives the measurement the
  ability to answer the other way.

  NEGATIVE CONTROL.  Latent = flat, noise only. n_eff_MF must collapse and the
  detection count must go to ~0.

  RULE 13 DISCHARGE.  The step-density sweep spans 16x, so the plant CAN
  express both an interior-wide and a collapsed through-focus response. Both
  ends are reported.

The winner's-curse bias in `n_eff_MF`'s denominator (rule 4 - the denominator
is a max over a noisy response) is MEASURED here rather than argued, by
comparing the raw and [1,2,1]-smoothed denominators against known truth.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.special import j1

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
from m70lib import L  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

PATCH = 256  # GQ samples
TILE = 128
LATENT_STACK = r"D:\personal\macro\119MSDCF"  # f/5.6, the sharpest corpus optics
LATENT_ISO = 50.0
SEED = 70


def defocus_otf(f_sensor: np.ndarray, radius_px: float) -> np.ndarray:
    """Geometric defocus disc of radius `radius_px` (sensor px).
    OTF(f) = 2 J1(2 pi R f) / (2 pi R f), 1 at f=0. Signed; |.| is what the
    power spectrum sees."""
    if radius_px <= 0:
        return np.ones_like(f_sensor)
    x = 2.0 * np.pi * radius_px * f_sensor
    out = np.ones_like(x)
    nz = x > 1e-12
    out[nz] = 2.0 * j1(x[nz]) / x[nz]
    return out


def gq_freq_grid(n: int):
    """Sensor-frequency magnitude for an n x n GQ-lattice FFT grid."""
    fu = np.fft.fftfreq(n)[:, None]
    fv = np.fft.fftfreq(n)[None, :]
    fx = (fu - fv) / 2.0
    fy = (fu + fv) / 2.0
    return np.hypot(fx, fy)


def load_latent() -> tuple[np.ndarray, float]:
    frames = sorted(f for f in os.listdir(LATENT_STACK) if f.lower().endswith(".arw"))
    # Pick the frame whose centre patch has the most high-band power: this is a
    # selection over frames and therefore an argmax (rule 4). It is used only
    # to pick a LATENT for a synthetic plant, so no reported statistic depends
    # on it; the plant's truth is computed from the OTFs, not from the frame.
    best, best_sc, best_mean = None, -1.0, 0.0
    rc, cc = 2344, 3514
    for name in frames:
        a = L.load_active(os.path.join(LATENT_STACK, name))
        p = L.crop_lattice(a, "GQ", rc, cc, PATCH)
        f, pw, c = L.spectrum(p, "GQ", tile=TILE, window="hann", sector="iso")
        m = (f >= 0.15) & (f < 0.25)
        sc = float((pw[m] * c[m]).sum() / c[m].sum())
        if sc > best_sc:
            best, best_sc, best_mean = p.copy(), sc, M.w2_weighted_mean(p, TILE)
        del a
    print(f"latent: {LATENT_STACK} centre patch, high-band power {best_sc:.1f}, mean {best_mean:.1f} DN")
    return best, best_mean


def make_frames(latent, radii_px, iso, rng, noise=True):
    """Blur the latent by each OTF and (optionally) add calibrated shot+read noise."""
    n = latent.shape[0]
    fr = gq_freq_grid(n)
    Fl = np.fft.fft2(latent)
    frames = []
    for R in radii_px:
        H = defocus_otf(fr, R)
        img = np.real(np.fft.ifft2(Fl * H))
        if noise:
            # Poisson-equivalent Gaussian at the LOCAL level (signal-dependent).
            var = M.noise_var_dn2(np.clip(img, 0.0, None), iso)
            img = img + rng.normal(0.0, 1.0, img.shape) * np.sqrt(var)
        frames.append(img)
    return frames


def truth_neff(latent, radii_px, band):
    """Exact n_eff_MF for the planted ladder: band-averaged |H_k|^2 |L|^2,
    computed on the same annulus the estimator averages over."""
    n = latent.shape[0]
    fr = gq_freq_grid(n)
    w = L.window_2d(n, "hann")
    Fl = np.fft.fft2((latent - latent.mean()) * w)
    P0 = (Fl.real**2 + Fl.imag**2) / float((w * w).sum())
    lo, hi = band
    m = (fr >= lo) & (fr < hi)
    s = np.array([float((P0[m] * defocus_otf(fr, R)[m] ** 2).sum()) for R in radii_px])
    return s


def measure_frames(frames, iso, subtract_noise=True):
    """The estimator under test: band powers minus the modelled noise floor."""
    rows = []
    for img in frames:
        f, p, c = L.spectrum(img, "GQ", tile=TILE, window="hann", sector="iso")
        ba = M.band_average(f, p, c)
        if subtract_noise:
            sig = M.w2_weighted_mean(np.clip(img, 0.0, None), TILE)
            nvar = float(M.noise_var_dn2(sig, iso))
        else:
            nvar = 0.0
        rows.append({k: (v[0] - nvar) for k, v in ba.items()})
    return rows


def run_case(tag, latent, radii_px, iso, mean_dn, rng, report_bands=M.MID_BANDS):
    """Three columns per band:

      analytic  - closed form from the KNOWN OTFs and the latent's own spectrum
      noiseless - the estimator run on the blurred frames with no noise added,
                  which isolates the band/window discretisation
      measured  - the estimator run on the noisy frames, which is what the real
                  measurement does
    """
    clean = make_frames(latent, radii_px, iso, rng, noise=False)
    noisy = make_frames(latent, radii_px, iso, rng, noise=True)
    m_clean = measure_frames(clean, iso, subtract_noise=False)
    m_noisy = measure_frames(noisy, iso, subtract_noise=True)
    out = {"tag": tag, "K": len(radii_px)}
    for name, lo, hi in M.BANDS:
        if name not in report_bands:
            continue
        s_an = truth_neff(latent, radii_px, (lo, hi))
        s_cl = np.array([r[name] for r in m_clean])
        s_no = np.array([r[name] for r in m_noisy])
        a = M.through_focus_stats(s_an)
        c = M.through_focus_stats(s_cl)
        e = M.through_focus_stats(s_no)
        out[name] = {
            "analytic_n_eff_mf": a["n_eff_mf_raw"],
            "noiseless_n_eff_mf": c["n_eff_mf_raw"],
            "meas_n_eff_mf_raw": e["n_eff_mf_raw"],
            "meas_n_eff_mf_smoothed": e["n_eff_mf_smoothed"],
            "recovery_raw": e["n_eff_mf_raw"] / c["n_eff_mf_raw"] if c["n_eff_mf_raw"] else np.nan,
            "recovery_smoothed": (
                e["n_eff_mf_smoothed"] / c["n_eff_mf_raw"] if c["n_eff_mf_raw"] else np.nan
            ),
            "analytic_vs_noiseless": (
                c["n_eff_mf_raw"] / a["n_eff_mf_raw"] if a["n_eff_mf_raw"] else np.nan
            ),
            "truth_rel_amp_1": c["rel_amp_1"],
            "meas_rel_amp_1": e["rel_amp_1"],
            "truth_rel_amp_2": c["rel_amp_2"],
            "meas_rel_amp_2": e["rel_amp_2"],
            "truth_pr": c["pr"],
            "meas_pr": e["pr"],
        }
    return out


def main() -> None:
    rng = np.random.default_rng(SEED)
    latent, mean_dn = load_latent()
    K = 41
    results = []

    print()
    print("=" * 78)
    print("RULE 20 DISCHARGE - the input that makes n_eff_MF come out LARGE")
    print("=" * 78)
    # Static repeat burst: every OTF is identity, truth n_eff_MF = K exactly.
    static = run_case("static-burst", latent, [0.0] * K, LATENT_ISO, mean_dn, rng)
    for b in M.MID_BANDS:
        r = static[b]
        print(
            f"  {b:8s} analytic {r['analytic_n_eff_mf']:7.3f}  noiseless {r['noiseless_n_eff_mf']:7.3f}"
            f" (= K = {K})   measured raw {r['meas_n_eff_mf_raw']:7.3f}"
            f"  smoothed {r['meas_n_eff_mf_smoothed']:7.3f}"
            f"   recovery {r['recovery_raw']:.3f} / {r['recovery_smoothed']:.3f}"
        )
    results.append(static)

    print()
    print("=" * 78)
    print("NEGATIVE CONTROL - flat latent, noise only")
    print("=" * 78)
    flat = np.full_like(latent, float(np.mean(latent)))
    neg = run_case("flat-noise-only", flat, [0.0] * K, LATENT_ISO, mean_dn, rng)
    for b in M.MID_BANDS:
        r = neg[b]
        print(
            f"  {b:8s} measured n_eff_MF raw {r['meas_n_eff_mf_raw']:8.4f}  "
            f"smoothed {r['meas_n_eff_mf_smoothed']:8.4f}   "
            f"(a large value here would void every reading)"
        )
    results.append(neg)

    print()
    print("=" * 78)
    print("PLANT - real texture, known through-focus OTF ladder, 16x step-density sweep")
    print("=" * 78)
    print(f"{'delta px/step':>13} {'band':>8} {'analyt':>8} {'noisels':>8} {'raw':>8} {'smooth':>8} "
          f"{'rec_raw':>8} {'rec_sm':>7} {'truthA1':>8} {'measA1':>7} {'truthA2':>8} {'measA2':>7}")
    for delta in (0.125, 0.25, 0.5, 1.0, 2.0):
        k0 = K // 2
        radii = [abs(k - k0) * delta for k in range(K)]
        case = run_case(f"plant-delta-{delta}", latent, radii, LATENT_ISO, mean_dn, rng)
        results.append(case)
        for b in M.MID_BANDS:
            r = case[b]
            print(
                f"{delta:13.3f} {b:>8s} {r['analytic_n_eff_mf']:8.3f} "
                f"{r['noiseless_n_eff_mf']:8.3f} "
                f"{r['meas_n_eff_mf_raw']:8.3f} {r['meas_n_eff_mf_smoothed']:8.3f} "
                f"{r['recovery_raw']:8.3f} {r['recovery_smoothed']:7.3f} "
                f"{r['truth_rel_amp_1']:8.3f} {r['meas_rel_amp_1']:7.3f} "
                f"{r['truth_rel_amp_2']:8.3f} {r['meas_rel_amp_2']:7.3f}"
            )

    with open(os.path.join(OUT, "s03_plant.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    print()
    print(f"wrote {os.path.join(OUT, 's03_plant.json')}")


if __name__ == "__main__":
    main()
