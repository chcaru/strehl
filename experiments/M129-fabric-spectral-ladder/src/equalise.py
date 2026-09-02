"""Amendment 5/6's equalisation, and the commissioning that shows it does what it claims.

THE CLAIM, in two parts, both asserted in Amendment 6 and neither yet tested.

  (a) Adding spatially white Gaussian noise of variance v to a patch raises the
      measured PSD floor by exactly v, in the normalisation m5_lib.welch_psd2 uses,
      and leaves the scene power alone.

  (b) Equalising the LOW-band signal-to-noise ratio equalises the crossing
      estimator's bias, so that the bias cancels in f_c(N)*N -- which is the
      condition Amendment 1 registered as the one that decides whether this ladder
      can run at all.

(a) is arithmetic and could be argued. (b) cannot: it is a claim about an estimator
whose bias is a complicated function of where a roll-off meets a floor, and the only
honest way to know is to plant a cutoff, degrade two copies differently, equalise,
and look.

THE POTENCY CONTROL MATTERS MORE THAN THE TEST HERE. A test that says "after
equalising, the two biases agree" is worthless unless the same test says "before
equalising, they did not". Both are run, and the run without equalisation must FAIL
for the run with it to mean anything. This is the lesson of xspec.py's test 4, where
a hard band limit made both arms look identical and certified nothing.

Read-only with respect to D:\\personal\\macro; this module touches no raw file.
"""

import os
import sys

import numpy as np

M5 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "m5-diffraction")
sys.path.insert(0, M5)
import m5_lib as L  # noqa: E402

LOW_BAND = (0.040, 0.090)   # Amendment 6's registered equalisation band


def floor_and_scene(f, p, band=LOW_BAND):
    """Noise floor from the top of the band, and excess scene power in `band`."""
    top = f >= 0.8 * f[-1]
    floor = float(np.median(p[top]))
    sel = (f >= band[0]) & (f <= band[1])
    scene = float(np.mean(p[sel])) - floor
    return floor, scene


def low_snr(patch, lattice="GQ", tile=128, band=LOW_BAND):
    f, p, c = L.spectrum(patch, lattice, tile=tile, window="hann")
    floor, scene = floor_and_scene(f, p, band)
    return scene / floor if floor > 0 else float("nan"), floor, scene


def equalise_to(patch, target_snr, rng, lattice="GQ", tile=128, band=LOW_BAND):
    """Add white noise until the low-band SNR falls to `target_snr`.

    Returns (degraded patch, variance added). The variance is never negative: this
    can only make a patch worse, so the target must be at or below the patch's
    current SNR. That asymmetry is why the target is set by the WORST aperture.
    """
    snr, floor, scene = low_snr(patch, lattice, tile, band)
    if not np.isfinite(snr) or target_snr <= 0:
        return patch, 0.0
    v = scene / target_snr - floor
    if v <= 0:
        return patch, 0.0
    return patch + rng.normal(0.0, np.sqrt(v), patch.shape), float(v)


# ---------------------------------------------------------------------------
# Commissioning
# ---------------------------------------------------------------------------

def _scene(n, slope, fc_lat, rng, amp=300.0):
    """A power-law texture rolled off by the diffraction MTF at fc_lat."""
    fu = np.fft.fftfreq(n)[:, None]
    fv = np.fft.fftfreq(n)[None, :]
    r = np.hypot(fu, fv)
    a = np.zeros((n, n))
    a[r > 0] = r[r > 0] ** (-slope / 2.0)
    s = np.real(np.fft.ifft2(np.fft.fft2(rng.normal(size=(n, n)))
                             * a * L.mtf_diffraction(r, fc_lat)))
    return s / s.std() * amp


def _fc(patch, tile=128):
    f, p, c = L.spectrum(patch, "GQ", tile=tile, window="hann")
    k = L.knee(f, p, c, tile, patch.shape[0], "GQ")
    return k.get("f_c")


def selftest():
    n, tile, slope = 256, 128, 2.2
    fc_lat = 0.18
    truth = fc_lat / L.LATTICE_PITCH_PX["GQ"]
    rng = np.random.default_rng(20260825)
    ok = True

    print("equalisation self-test")
    print("=" * 70)

    # --- (a) the floor rises by exactly the added variance -----------------
    print("\n(a) does adding variance v raise the floor by v?")
    print(f"    {'added v':>10} {'floor before':>13} {'floor after':>12} "
          f"{'rise':>10} {'rise/v':>8}")
    a_ok = True
    lin = []
    base = _scene(n, slope, fc_lat, rng) + rng.normal(0, 40.0, (n, n))
    f0, p0, c0 = L.spectrum(base, "GQ", tile=tile, window="hann")
    fl0, _ = floor_and_scene(f0, p0)
    for v in (500.0, 2000.0, 8000.0):
        deg = base + rng.normal(0.0, np.sqrt(v), (n, n))
        f1, p1, c1 = L.spectrum(deg, "GQ", tile=tile, window="hann")
        fl1, _ = floor_and_scene(f1, p1)
        ratio = (fl1 - fl0) / v
        good = 0.9 <= ratio <= 1.1
        a_ok &= good
        lin.append({"v": v, "rise": fl1 - fl0, "ratio": ratio})
        print(f"    {v:10.0f} {fl0:13.1f} {fl1:12.1f} {fl1 - fl0:10.1f} "
              f"{ratio:8.3f}{'' if good else '   <-- off'}")
    print(f"    normalisation {'CONFIRMED' if a_ok else 'WRONG'}: the PSD is scaled")
    print("    so that white noise of variance s^2 reads as a flat s^2, which is")
    print("    what makes the prescription add_var = scene/target - floor valid.")
    ok &= a_ok

    # --- (b) does equalising the low band equalise the bias? ---------------
    # Two copies of the SAME scene, degraded differently, standing in for two
    # apertures that differ only in exposure. The cutoff is identical in both, so
    # any difference in recovered f_c is bias and nothing else.
    print("\n(b) two copies of one scene, same planted cutoff, different noise")
    print(f"    planted f_c {truth:.4f} sensor cyc/px "
          f"({truth * 1000 / L.PITCH_UM:.1f} cy/mm)")
    print()
    NREP = 12
    quiet_n, loud_n = 30.0, 90.0     # 9x in variance, like f/11 against f/18
    raw_q, raw_l, eq_q, eq_l = [], [], [], []
    snr_q, snr_l, snr_qe = [], [], []
    for k in range(NREP):
        r = np.random.default_rng(4000 + 31 * k)
        s = _scene(n, slope, fc_lat, r)
        q = s + r.normal(0, quiet_n, (n, n))
        l = s + r.normal(0, loud_n, (n, n))
        sq, _, _ = low_snr(q)
        sl, _, _ = low_snr(l)
        snr_q.append(sq)
        snr_l.append(sl)
        qe, _ = equalise_to(q, sl, r)
        sqe, _, _ = low_snr(qe)
        snr_qe.append(sqe)
        for dst, patch in ((raw_q, q), (raw_l, l), (eq_q, qe), (eq_l, l)):
            fc = _fc(patch)
            dst.append((fc - truth) / truth * 100 if fc else np.nan)

    def m(x):
        return float(np.nanmean(x))

    print(f"    {'arm':>22} {'low SNR':>10} {'bias %':>9} {'sd':>7}")
    print(f"    {'quiet, as captured':>22} {m(snr_q):10.0f} {m(raw_q):+9.2f} "
          f"{np.nanstd(raw_q):7.2f}")
    print(f"    {'loud, as captured':>22} {m(snr_l):10.0f} {m(raw_l):+9.2f} "
          f"{np.nanstd(raw_l):7.2f}")
    print(f"    {'quiet, equalised':>22} {m(snr_qe):10.0f} {m(eq_q):+9.2f} "
          f"{np.nanstd(eq_q):7.2f}")
    print(f"    {'loud, unchanged':>22} {m(snr_l):10.0f} {m(eq_l):+9.2f} "
          f"{np.nanstd(eq_l):7.2f}")

    gap_raw = abs(m(raw_q) - m(raw_l))
    gap_eq = abs(m(eq_q) - m(eq_l))
    print()
    print(f"    differential bias BEFORE equalising: {gap_raw:5.2f} points")
    print(f"    differential bias AFTER  equalising: {gap_eq:5.2f} points")

    # POTENCY. The "after" number is meaningless unless the "before" number is
    # large enough to have been detectable. Both gates are stated, and the test
    # fails if either does.
    potent = gap_raw > 3.0
    print(f"    potency: the un-equalised gap is {gap_raw:.2f} points, which must")
    print(f"             exceed 3.0 for the comparison to mean anything: "
          f"{'PASS' if potent else 'FAIL'}")
    shrunk = gap_eq < gap_raw / 2.0
    print(f"    the gap {'shrinks by more than half' if shrunk else 'DOES NOT shrink'}"
          f": {'PASS' if shrunk else 'FAIL'}")
    snr_match = abs(m(snr_qe) - m(snr_l)) / m(snr_l) < 0.10
    print(f"    the equalised SNRs actually match to 10%: "
          f"{'PASS' if snr_match else 'FAIL'}")
    b_ok = potent and shrunk and snr_match
    ok &= b_ok

    print()
    print("    WHAT THIS DOES NOT SHOW. The residual gap is not zero and is not")
    print("    claimed to be. Equalising the low band equalises the floor relative")
    print("    to the texture, but the estimator also sees the roll-off's own shape,")
    print("    and two apertures genuinely differ there. On real data that residual")
    print("    is entangled with the signal, which is exactly why the native-SNR arm")
    print("    is run alongside and the two are compared rather than averaged.")

    print()
    print("=" * 70)
    print(f"self-test {'PASS' if ok else 'FAIL'}")

    import json
    out = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "out")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "equalise-selftest.json"), "w",
              encoding="utf-8") as fh:
        json.dump({
            "pass": bool(ok),
            "planted_fc": truth,
            "nrep": NREP,
            "variance_linearity": lin,
            "arms": {
                "quiet_raw": {"snr": m(snr_q), "bias": m(raw_q),
                              "sd": float(np.nanstd(raw_q))},
                "loud_raw": {"snr": m(snr_l), "bias": m(raw_l),
                             "sd": float(np.nanstd(raw_l))},
                "quiet_eq": {"snr": m(snr_qe), "bias": m(eq_q),
                             "sd": float(np.nanstd(eq_q))},
                "loud_eq": {"snr": m(snr_l), "bias": m(eq_l),
                            "sd": float(np.nanstd(eq_l))},
            },
            "gap_raw": gap_raw,
            "gap_eq": gap_eq,
            "snr_ratio": m(snr_q) / m(snr_l),
            "points_per_efold_power": gap_raw / np.log(m(snr_q) / m(snr_l)),
        }, fh, indent=2)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest())
