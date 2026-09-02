"""The G1 x G2 cross-spectrum: a noise floor removed by construction, not by fitting.

WHY THIS EXISTS. Registered threat T2. Exposure was held at 1.3 s across all five
apertures, so f/18 receives about a tenth of the light of f/5.6 and its photon noise
floor sits about ten times lower in absolute terms but far higher relative to the
signal. The primary estimator finds the highest frequency distinguishable from that
floor, so a floor that moves with aperture is a confound sitting directly on top of
the quantity being measured.

THE IDEA. The two green planes read DIFFERENT photosites, so their read and photon
noise are statistically independent, while they see the SAME scene. The expectation
of their cross-spectrum therefore contains the scene power and NONE of the noise
power. The floor is removed by construction. Nothing is fitted and nothing is
subtracted, so there is no floor model to be wrong.

THE COMPLICATION, AND WHY IT IS NOT FATAL. G1 and G2 are not co-located. G1 sits at
(even row, odd col) and G2 at (odd row, even col), so for a common index the two
lattices are offset by (+1, -1) sensor pixels, which is (+0.5, -0.5) in units of the
lattice pitch. A shift is a linear phase ramp in the Fourier domain, so the raw cross
spectrum is complex and its real part oscillates through zero. Removing the ramp
first makes the real part an unbiased estimate of scene power.

The ramp is known exactly from the sensor geometry, so this module DE-ROTATES BY THE
KNOWN SHIFT -- no free parameters -- and separately FITS the shift as a diagnostic.
If the fitted shift does not agree with the geometry, the sign convention is wrong
and the module says so instead of quietly returning a biased spectrum.

Taking the magnitude |C| instead would avoid the geometry but is BIASED UPWARD by
noise, because a magnitude cannot cancel; the de-rotated real part can and does
average to zero on pure noise. That difference is measured in the self-test below.

`m5_lib` is imported and never modified.
"""

import os
import sys

import numpy as np

M5 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "m5-diffraction")
sys.path.insert(0, M5)
import m5_lib as L  # noqa: E402

# G2 relative to G1, in units of the G-lattice pitch (2 sensor px).
# G1[i,j] = S(2i, 2j+1); G2[i,j] = S(2i+1, 2j) = G1 evaluated at (i+0.5, j-0.5).
SHIFT_DI, SHIFT_DJ = 0.5, -0.5


def cross_psd2(p1: np.ndarray, p2: np.ndarray, tile: int, window: str):
    """Welch-averaged complex cross-periodogram of two co-registered patches.

    Same tiling, windowing and normalisation as `m5_lib.welch_psd2`, so the two
    are directly comparable: white noise of variance s^2 gives E[auto] = s^2 per
    bin, and E[cross] = 0 per bin when the two noises are independent.
    """
    assert p1.shape == p2.shape and p1.shape[0] == p1.shape[1]
    n = p1.shape[0]
    step = tile // 2
    starts = list(range(0, n - tile + 1, step))
    w = L.window_2d(tile, window)
    wnorm = float((w * w).sum())
    acc = np.zeros((tile, tile), dtype=complex)
    count = 0
    for i in starts:
        for j in starts:
            a = p1[i:i + tile, j:j + tile]
            b = p2[i:i + tile, j:j + tile]
            A = np.fft.fft2((a - a.mean()) * w)
            B = np.fft.fft2((b - b.mean()) * w)
            acc += A * np.conj(B) / wnorm
            count += 1
    return acc / count


def _ramp(n: int, di: float, dj: float) -> np.ndarray:
    fu = np.fft.fftfreq(n)[:, None]
    fv = np.fft.fftfreq(n)[None, :]
    return np.exp(2j * np.pi * (fu * di + fv * dj))


def derotate(cx: np.ndarray, di: float = SHIFT_DI, dj: float = SHIFT_DJ):
    """Undo the known inter-plane shift and return the real part.

    C = A conj(B) carries exp(-2pi i (fu*di + fv*dj)) when b is a shifted by
    (di, dj), so multiplying by the conjugate ramp aligns the two.
    """
    return np.real(cx * _ramp(cx.shape[0], di, dj))


def fit_shift(cx: np.ndarray, power_frac: float = 0.001):
    """Fit (di, dj) from the cross-phase, as a diagnostic on the geometry.

    Uses only bins carrying real power, weighted by that power, and solves the
    linear phase model without unwrapping. That is legitimate ONLY because the
    true shift is half a sample: the ramp then spans at most +-pi/2 over the
    band. For a shift of one sample or more the phase wraps and this function
    returns nonsense -- measured, not assumed: planting (+1, +2) makes it
    report (+0.01, -0.01).

    KNOWN BIAS, measured. On a steep spectrum this fit is biased TOWARD ZERO by
    spectral leakage: a Hann-windowed tile mixes each bin with its neighbours,
    and when power falls as f^-2 the leakage into a bin comes mostly from lower
    frequencies, which carry a smaller phase. Restricting to high-power bins
    makes it worse, because those are exactly the steep low-frequency ones. On
    an exactly planted +-0.5 shift the recovered value runs 0.458 at
    power_frac=0.1, 0.484 at 0.02 and 0.496 at 0.001. The default is therefore
    0.001, and this is a DIAGNOSTIC only: `derotate` uses the shift given by the
    sensor geometry, never this fit.
    """
    n = cx.shape[0]
    fu = (np.fft.fftfreq(n)[:, None] * np.ones((1, n))).ravel()
    fv = (np.fft.fftfreq(n)[None, :] * np.ones((n, 1))).ravel()
    c = cx.ravel()
    mag = np.abs(c)
    keep = mag > power_frac * mag.max()
    keep &= (fu != 0) | (fv != 0)
    if keep.sum() < 10:
        return None, None
    ph = np.angle(c[keep])
    X = np.vstack([fu[keep], fv[keep]]).T
    W = mag[keep]
    # C carries exp(-2pi i (fu di + fv dj)) so phase = -2pi (fu di + fv dj)
    y = -ph / (2 * np.pi)
    beta = np.linalg.solve((X * W[:, None]).T @ X, (X * W[:, None]).T @ y)
    return float(beta[0]), float(beta[1])


def sign_check(cx: np.ndarray, di: float = SHIFT_DI, dj: float = SHIFT_DJ,
               min_phase: float = np.pi / 8, power_frac: float = 1e-6):
    """Decisive, leakage-immune check that the de-rotation sign is right.

    De-rotating by the correct shift aligns every bin's phase to zero, so the
    power-weighted mean of cos(residual phase) goes to +1. De-rotating by the
    negated shift doubles the ramp instead of removing it and the mean falls.

    RESTRICTED TO BINS WHERE THE RAMP ACTUALLY MATTERS. A first version summed
    over all bins and returned a ratio of 1.1, which looked like a failure but
    was a blunt instrument: most power sits at low frequencies, where the ramp
    phase is near zero and both signs therefore score alike. Only bins whose
    ramp phase exceeds `min_phase` can discriminate at all, so only those are
    used. The measured discrimination went from 1.1 to the value printed by the
    self-test once this restriction was applied.

    Returns (score with +shift, score with -shift, number of bins used). Each
    score is a mean cosine in [-1, 1]; the correct convention gives ~+1.
    """
    n = cx.shape[0]
    fu = (np.fft.fftfreq(n)[:, None] * np.ones((1, n))).ravel()
    fv = (np.fft.fftfreq(n)[None, :] * np.ones((n, 1))).ravel()
    c = cx.ravel()
    mag = np.abs(c)
    ramp = 2 * np.pi * (fu * di + fv * dj)
    keep = (mag > power_frac * mag.max()) & (np.abs(ramp) > min_phase)
    if keep.sum() < 10:
        return None, None, int(keep.sum())
    ph = np.angle(c[keep])
    w = mag[keep]
    good = float((w * np.cos(ph + ramp[keep])).sum() / w.sum())
    bad = float((w * np.cos(ph - ramp[keep])).sum() / w.sum())
    return good, bad, int(keep.sum())



# ---------------------------------------------------------------------------
# A knee estimator for a spectrum whose floor is zero by construction
# ---------------------------------------------------------------------------

def knee_cross(f, p, counts, z=L.Z_DETECT, run_len=L.RUN_LEN,
               f_lo=L.F_LO_ABS, top_frac=0.75, iters=6):
    """Highest frequency whose CROSS power is distinguishable from zero.

    WHY m5_lib.knee CANNOT BE USED HERE, measured rather than argued. That rule
    tests `p - N > z*sqrt(kappa)*N/sqrt(n)`: its threshold is PROPORTIONAL to
    the floor N. The cross spectrum's entire purpose is to have no floor, so N
    comes out near zero and the threshold with it, and every bin is 'detected'.
    Run directly on a cross spectrum it returned a floor of -8.7 -- a negative
    power -- and placed the knee at 0.238 against a planted 0.090 sensor cyc/px.

    So the noise model changes from multiplicative to ADDITIVE. Under the null
    the cross power is zero-mean with a variance set by the two independent
    noise fields, falling as 1/counts. The scale is measured from the top of
    the band, where scene power is certainly gone, and then re-measured above
    the provisional knee, exactly as the auto rule re-estimates its floor.

    This estimator is NOT assumed to share the auto rule's bias. Registered
    condition A6 asks the two arms to agree, and two differently-biased
    estimators would disagree even when both are right, so the commissioning
    battery must measure this one's bias separately and the comparison must be
    made between BIAS-CORRECTED values.
    """
    f = np.asarray(f, float)
    p = np.asarray(p, float)
    counts = np.asarray(counts, float)
    lo = f >= f_lo
    if lo.sum() < run_len + 3:
        return {"f_c": None, "sigma": None, "reason": "band too narrow"}

    band = f >= top_frac * f[-1]
    if band.sum() < 5:
        band = f >= 0.6 * f[-1]
    # sigma_bin = s / sqrt(counts); estimate s robustly from the top band.
    x = p[band] * np.sqrt(counts[band])
    s = 1.4826 * float(np.median(np.abs(x - np.median(x))))
    if not np.isfinite(s) or s <= 0:
        s = float(np.std(x)) or 1.0

    fc = None
    for _ in range(iters):
        thr = z * s / np.sqrt(counts)
        det = (p > thr) & lo
        end = L._last_run_end(det, run_len)
        new_fc = float(f[end]) if end is not None else None
        if new_fc == fc:
            break
        fc = new_fc
        above = f > fc if fc is not None else band
        if above.sum() >= 5:
            x = p[above] * np.sqrt(counts[above])
            s2 = 1.4826 * float(np.median(np.abs(x - np.median(x))))
            if np.isfinite(s2) and s2 > 0:
                s = s2
    return {"f_c": fc, "sigma": s, "n_floor_bins": int((f > (fc or 0)).sum()),
            "neg_frac_floor": float(np.mean(p[f > (fc or 0)] < 0))
            if (f > (fc or 0)).any() else None}


def cross_spectrum(patch1, patch2, tile=128, window="hann", sector="iso"):
    """Radially averaged, noise-free-in-expectation spectrum of a G1/G2 pair.

    Returned on the G1 lattice, which is what both planes are.
    """
    cx = cross_psd2(patch1, patch2, tile, window)
    return L.radial_psd(derotate(cx), "G1", sector)


# ---------------------------------------------------------------------------
# Self-test. Runs on synthetic data only, with truth planted.
# ---------------------------------------------------------------------------

def _bandlimited(n, alpha, fmax_lat, rng, shift=None):
    """A power-law field, hard band-limited, optionally shifted EXACTLY.

    Built in the Fourier domain so the shift is applied as a phase ramp rather
    than by decimating a finer grid. The earlier version of this helper made the
    two planes by taking `fine[0::2,0::2]` and `fine[1::2,1::2]`, which is a
    sound way to make a shifted pair but adds decimation effects on top of the
    leakage bias and so confounded the diagnostic it was meant to test.
    """
    fu = np.fft.fftfreq(n)[:, None]
    fv = np.fft.fftfreq(n)[None, :]
    r = np.hypot(fu, fv)
    amp = np.zeros((n, n))
    amp[r > 0] = r[r > 0] ** (-alpha / 2.0)
    amp[r > fmax_lat] = 0.0
    F = np.fft.fft2(rng.normal(size=(n, n))) * amp
    if shift is not None:
        F = F * np.exp(2j * np.pi * (fu * shift[0] + fv * shift[1]))
    return np.real(np.fft.ifft2(F))


def selftest(seed=11):
    rng = np.random.default_rng(seed)
    n, tile = 256, 128
    ok = True

    print("cross-spectrum self-test\n" + "=" * 62)

    # --- 1. geometry --------------------------------------------------------
    base = _bandlimited(n, 2.0, 0.20, rng)
    fu = np.fft.fftfreq(n)[:, None]
    fv = np.fft.fftfreq(n)[None, :]
    F = np.fft.fft2(base)
    shifted = np.real(np.fft.ifft2(
        F * np.exp(2j * np.pi * (fu * SHIFT_DI + fv * SHIFT_DJ))))
    cx = cross_psd2(base, shifted, tile, "hann")
    di, dj = fit_shift(cx)
    good, bad, nb = sign_check(cx)
    print(f"1. geometry, planted shift ({SHIFT_DI:+.2f}, {SHIFT_DJ:+.2f})")
    print(f"   fit_shift          ({di:+.4f}, {dj:+.4f})   "
          f"(biased toward zero by leakage; see docstring)")
    print(f"   sign_check         +shift {good:+.4f}  -shift {bad:+.4f}  "
          f"over {nb} discriminating bins")
    g1 = good > 0.9 and good - bad > 0.3 and di > 0.3 and dj < -0.3
    print(f"   convention {'CORRECT' if g1 else 'WRONG'}")
    ok &= g1

    # --- 2. does the cross spectrum cancel noise? ---------------------------
    sig = 200.0
    a = rng.normal(0, sig, (n, n))
    b = rng.normal(0, sig, (n, n))
    auto = L.welch_psd2(a, tile, "hann")
    raw = cross_psd2(a, b, tile, "hann")
    cro = derotate(raw, 0.0, 0.0)
    print(f"\n2. pure independent noise, variance {sig ** 2:.0f}")
    print(f"   auto-spectrum mean   {auto.mean():11.1f}  the floor the primary "
          f"estimator must fight")
    print(f"   cross real part mean {cro.mean():11.1f}  expected 0, "
          f"{abs(cro.mean()) / auto.mean() * 100:.2f}% of auto")
    print(f"   cross |C| mean       {np.abs(raw).mean():11.1f}  biased up, which "
          f"is why |C| is not used")
    g2 = abs(cro.mean()) < 0.02 * auto.mean() and np.abs(raw).mean() > 0.2 * auto.mean()
    print(f"   noise cancellation {'CONFIRMED' if g2 else 'FAILED'}")
    ok &= g2

    # --- 3. the auto rule really does break on a floorless spectrum ---------
    # From here on the scene rolls off with the DIFFRACTION MTF rather than a
    # hard band limit. A hard cliff is found easily by any estimator at any
    # noise level, which made an earlier version of test 4 report equal spans
    # and certify nothing. A soft roll-off is what the real subject has and it
    # is the only case in which the floor's height can move the crossing.
    fc_lat = 0.18
    fu2 = np.fft.fftfreq(n)[:, None]
    fv2 = np.fft.fftfreq(n)[None, :]
    rr = np.hypot(fu2, fv2)
    amp = np.zeros((n, n))
    amp[rr > 0] = rr[rr > 0] ** (-2.2 / 2.0)
    soft = np.real(np.fft.ifft2(np.fft.fft2(rng.normal(size=(n, n)))
                                * amp * L.mtf_diffraction(rr, fc_lat)))
    s = soft / soft.std() * 300.0
    v1 = s + rng.normal(0, 60.0, (n, n))
    v2 = s + rng.normal(0, 60.0, (n, n))
    fx, px, cxo = cross_spectrum(v1, v2, tile=tile, window="hann")
    kbad = L.knee(fx, px, cxo, tile, n, "G1")
    print(f"\n3. m5_lib.knee applied to a cross spectrum (the wrong tool)")
    print(f"   reported floor {kbad.get('floor'):.2f}"
          f"{'  <-- NEGATIVE POWER' if (kbad.get('floor') or 0) < 0 else ''}")
    print(f"   reported f_c   {kbad.get('f_c')}")
    g3 = (kbad.get("floor") or 0) < 0 or (kbad.get("f_c") or 0) > 0.9 * fx[-1]
    print(f"   failure mode reproduced: {g3}  (this is why knee_cross exists)")
    ok &= g3

    # --- 4. potency: stability against the floor, which is T2's whole point --
    truth = fc_lat / L.LATTICE_PITCH_PX["G1"]
    print(f"\n4. potency, planted cutoff {truth:.4f} sensor cyc/px "
          f"({L.sensor_cyc_px_to_cyc_mm(truth):.1f} cy/mm), diffraction roll-off")
    print(f"   {'noise':>7} {'SNR':>7} {'auto f_c':>10} {'auto err':>9} "
          f"{'cross f_c':>10} {'cross err':>9}")
    errs = []
    for nz in (20.0, 60.0, 150.0, 300.0):
        ea_s, ec_s = [], []
        for k in range(5):
            r2 = np.random.default_rng(1000 + 17 * k)
            v1 = s + r2.normal(0, nz, (n, n))
            v2 = s + r2.normal(0, nz, (n, n))
            fa, pa, ca = L.spectrum(v1, "G1", tile=tile, window="hann")
            ka = L.knee(fa, pa, ca, tile, n, "G1")
            fxx, pxx, cxx = cross_spectrum(v1, v2, tile=tile, window="hann")
            kc = knee_cross(fxx, pxx, cxx)
            if ka.get("f_c"):
                ea_s.append((ka["f_c"] - truth) / truth * 100)
            if kc.get("f_c"):
                ec_s.append((kc["f_c"] - truth) / truth * 100)
        ea = float(np.mean(ea_s)) if ea_s else float("nan")
        ec = float(np.mean(ec_s)) if ec_s else float("nan")
        errs.append((nz, ea, ec))
        print(f"   {nz:7.0f} {300.0 / nz:7.1f} "
              f"{truth * (1 + ea / 100):10.4f} {ea:+8.1f}% "
              f"{truth * (1 + ec / 100):10.4f} {ec:+8.1f}%")
    span_a = float(np.nanmax([e[1] for e in errs]) - np.nanmin([e[1] for e in errs]))
    span_c = float(np.nanmax([e[2] for e in errs]) - np.nanmin([e[2] for e in errs]))
    print(f"\n   error SPAN across a 15x range of noise: auto {span_a:.1f} points, "
          f"cross {span_c:.1f} points")
    g4 = span_c < span_a
    print(f"   cross arm is {'LESS' if g4 else 'MORE'} sensitive to the noise "
          f"floor.")
    print("   That stability, not a smaller error, is what makes it a control")
    print("   for T2: the floor is what differs by aperture, so an estimator")
    print("   whose answer moves with the floor cannot separate diffraction")
    print("   from exposure.")
    ok &= g4

    print("\n   Registered condition A6 asks the two arms to AGREE on real data.")
    print("   They have different biases by construction, so the commissioning")
    print("   battery must measure both and A6 must compare CORRECTED values.")

    print("\n" + "=" * 62)
    print(f"self-test {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1



if __name__ == "__main__":
    sys.exit(selftest())
