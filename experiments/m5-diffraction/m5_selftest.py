"""M5 — estimator self-tests.

These pin the two things that could silently produce a confidently wrong
answer:

  1. The frequency-axis scaling of each lattice (Trap 1). A planted sinusoid
     of known *sensor* frequency must land in the same radial bin whether it
     is read through G1, G2 or GQ. A factor-of-2 slip here would exactly
     mimic a p = 0.5 result.
  2. The periodogram normalisation. White noise of known variance must give a
     flat floor equal to that variance, so that the H4 sigma read off the
     floor is in DN and not in some window-dependent unit.

Run: python m5_selftest.py
"""

from __future__ import annotations

import numpy as np

import m5_lib as L

FAILS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}  {detail}")
    if not cond:
        FAILS.append(name)


def synth_cfa(h, w, fn):
    """Build a full-CFA array from a function of (sensor row, sensor col)."""
    r = np.arange(h)[:, None]
    c = np.arange(w)[None, :]
    return fn(r, c)


def test_lattice_frequency_scaling():
    """A sinusoid at a known sensor frequency lands in the same bin in all
    three lattices. This is the factor-of-2 / sqrt(2) guard."""
    h, w = 1600, 1600
    size = 256
    for f_sensor, ang in ((0.09, 0.0), (0.18, 0.0), (0.09, 90.0), (0.12, 45.0),
                          (0.20, 30.0)):
        kx = f_sensor * np.cos(np.deg2rad(ang))
        ky = f_sensor * np.sin(np.deg2rad(ang))
        a = synth_cfa(h, w, lambda r, c: 2000.0 + 500.0 * np.cos(
            2 * np.pi * (kx * c + ky * r)) + L.BLACK_LEVEL)
        a = np.clip(a, 0, 16383).astype(np.uint16)
        peaks = {}
        for lat in L.LATTICES:
            patch = L.crop_lattice(a, lat, 800, 800, size)
            f, p, n = L.spectrum(patch, lat, tile=128, window="hann")
            peaks[lat] = float(f[np.argmax(p)])
        spread = max(peaks.values()) - min(peaks.values())
        err = max(abs(v - f_sensor) for v in peaks.values())
        check(
            f"sinusoid {f_sensor:.3f} cyc/px @ {ang:.0f} deg lands at the right radius",
            err < 0.006,
            f"G1={peaks['G1']:.4f} G2={peaks['G2']:.4f} GQ={peaks['GQ']:.4f} "
            f"(true {f_sensor:.4f}, spread {spread:.4f})",
        )


def test_white_noise_floor():
    """White noise of variance s^2 gives a flat floor at s^2, for every window
    and every lattice."""
    rng = np.random.default_rng(7)
    h, w = 1400, 1400
    for sigma in (5.0, 40.0):
        a = np.clip(2000.0 + L.BLACK_LEVEL + rng.normal(0, sigma, (h, w)),
                    0, 16383).astype(np.uint16)
        for lat in L.LATTICES:
            patch = L.crop_lattice(a, lat, 700, 700, 512)
            for win in L.WINDOWS:
                f, p, n = L.spectrum(patch, lat, tile=256, window=win)
                lvl = float(np.median(p))
                rel = lvl / sigma**2 - 1.0
                # flatness: ratio of the top-decile median to the bottom-decile
                k = max(2, len(f) // 10)
                flat = float(np.median(p[-k:]) / np.median(p[:k]))
                check(
                    f"white floor {lat}/{win} sigma={sigma}",
                    abs(rel) < 0.06 and abs(flat - 1.0) < 0.10,
                    f"level={lvl:.2f} vs {sigma**2:.2f} ({rel*100:+.2f}%), "
                    f"top/bottom={flat:.3f}",
                )


def test_mtf_shape():
    f = np.linspace(0, 1.5, 200)
    m = L.mtf_diffraction(f, 1.0)
    check("MTF(0) = 1", abs(m[0] - 1.0) < 1e-12, f"{m[0]:.6f}")
    check("MTF(>=f_c) = 0", np.all(m[f >= 1.0] == 0.0))
    check("MTF monotone decreasing", np.all(np.diff(m[f < 1.0]) <= 1e-12))
    # Known value: MTF(0.5) = (2/pi)(arccos .5 - .5*sqrt(.75)) = 0.39100
    check("MTF(0.5) = 0.39100", abs(float(L.mtf_diffraction(0.5, 1.0)) - 0.391002) < 1e-5,
          f"{float(L.mtf_diffraction(0.5,1.0)):.6f}")


def test_cutoff_arithmetic():
    """The published prediction table must fall out of the library."""
    for n_marked, bell, want in ((5.6, 3.0, 0.554), (8.0, 3.0, 0.388),
                                 (11.0, 3.0, 0.282), (5.6, 5.0, 0.332),
                                 (8.0, 5.0, 0.233), (11.0, 5.0, 0.169)):
        got = L.f_cutoff_sensor(n_marked * bell)
        check(f"f_c(N={n_marked}, 1+m/p={bell})", abs(got - want) < 0.0015,
              f"{got:.4f} vs {want}")
        back = L.bellows_from_fc(got, n_marked)
        check(f"  round-trip to 1+m/p={bell}", abs(back - bell) < 1e-9, f"{back:.6f}")


def test_lattice_reach():
    check("G1 reach = 0.250 sensor cyc/px",
          abs(L.lattice_nyquist_sensor("G1") - 0.25) < 1e-12)
    check("GQ reach = 0.3536 sensor cyc/px",
          abs(L.lattice_nyquist_sensor("GQ") - 0.5 / np.sqrt(2)) < 1e-12)
    # GQ must really be the two greens interleaved: its sample count per unit
    # sensor area is twice a single sublattice's.
    check("GQ pitch = sqrt(2) sensor px",
          abs(L.LATTICE_PITCH_PX["GQ"] ** 2 - 2.0) < 1e-12)


def test_gq_reads_only_green():
    """GQ must never read a red or blue photosite."""
    h, w = 600, 600
    r = np.arange(h)[:, None]
    c = np.arange(w)[None, :]
    green = ((r + c) % 2 == 1)
    a = np.where(green, 3000, 60000).astype(np.uint16)  # non-green = absurd
    patch = L.crop_lattice(a, "GQ", 300, 300, 128)
    check("GQ reads green photosites only",
          np.all(patch == 3000 - L.BLACK_LEVEL),
          f"unique={np.unique(patch)[:4]}")
    for lat, off in (("G1", (0, 1)), ("G2", (1, 0))):
        p2 = L.crop_lattice(a, lat, 300, 300, 128)
        check(f"{lat} reads green photosites only",
              np.all(p2 == 3000 - L.BLACK_LEVEL))


def test_padding_guard():
    a = np.full((L.ACTIVE_H, L.ACTIVE_W), 2000, np.uint16)
    ok = False
    try:
        L.crop_lattice(a, "G1", 8, 8, 512)
    except ValueError:
        ok = True
    check("crop_lattice refuses an ROI that leaves the active area", ok)


def test_knee_rule_on_flat_input():
    """Pure white noise: the rule must not invent a cutoff."""
    rng = np.random.default_rng(11)
    a = np.clip(600 + rng.normal(0, 20, (1400, 1400)), 0, 16383).astype(np.uint16)
    for lat in L.LATTICES:
        patch = L.crop_lattice(a, lat, 700, 700, 512)
        f, p, n = L.spectrum(patch, lat, tile=256, window="hann")
        k = L.knee_floor_crossing(f, p, n)
        check(f"knee rule reports no signal on white noise ({lat})",
              not k["has_signal"],
              f"dyn={k['dynamic_range']:.2f} f_c={k['f_c']}")


def test_false_alarm_rate():
    """The detection rule must almost never fire on pure noise.

    This is the quantitative version of C2 and it also validates the
    self-calibrating per-bin scatter (kappa): if kappa were estimated too
    small the threshold would be too tight and this rate would blow up.
    Run over independent white-noise realisations for both tile sizes used
    by the real measurement.
    """
    rng = np.random.default_rng(4242)
    for tile in (128, 256):
        for lat in L.LATTICES:
            fires, kaps = 0, []
            trials = 40
            for _ in range(trials):
                a = np.clip(600 + rng.normal(0, 20, (1300, 1300)), 0,
                            16383).astype(np.uint16)
                patch = L.crop_lattice(a, lat, 650, 650, 512)
                f, p, n = L.spectrum(patch, lat, tile=tile, window="hann")
                k = L.knee_floor_crossing(f, p, n)
                kaps.append(k["kappa"])
                if k["f_c"] is not None:
                    fires += 1
            check(f"false-alarm rate on white noise {lat}/tile{tile}",
                  fires <= 2,
                  f"{fires}/{trials} fired, median kappa={np.median(kaps):.3f}")


def test_kappa_calibration():
    """kappa must track the real per-bin scatter, which Welch tile averaging
    reduces. Fewer tiles -> larger kappa. Measured, not assumed."""
    rng = np.random.default_rng(99)
    a = np.clip(600 + rng.normal(0, 20, (1300, 1300)), 0, 16383).astype(np.uint16)
    patch = L.crop_lattice(a, "G1", 650, 650, 512)
    prev = None
    for tile in (256, 128, 64):
        f, p, n = L.spectrum(patch, "G1", tile=tile, window="hann")
        k = L.knee_floor_crossing(f, p, n)
        # observed scatter of the top band, normalised the same way
        top = f >= 0.8 * f[-1]
        obs = np.std((p[top] / np.median(p[top]) - 1.0) * np.sqrt(n[top])) ** 2
        check(f"kappa matches observed scatter, tile={tile}",
              0.4 < k["kappa"] / obs < 2.5,
              f"kappa={k['kappa']:.3f} observed={obs:.3f} "
              f"ratio={k['kappa']/obs:.2f}")
        prev = k["kappa"]


if __name__ == "__main__":
    test_lattice_reach()
    test_cutoff_arithmetic()
    test_mtf_shape()
    test_gq_reads_only_green()
    test_padding_guard()
    test_lattice_frequency_scaling()
    test_white_noise_floor()
    test_knee_rule_on_flat_input()
    test_kappa_calibration()
    test_false_alarm_rate()
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILURES: {FAILS}")
        raise SystemExit(1)
    print("all self-tests passed")
