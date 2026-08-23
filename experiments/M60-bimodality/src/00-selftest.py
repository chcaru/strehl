"""M60 gate 0 — prove the instrument before using it.

Discharges:
  * AGENTS rule 33's spirit for Python: read the content back, do not trust exit codes
    (discipline 351).
  * The noise-model transcription is checked against `crates/strehl-core` by parsing
    the Rust source, not by re-typing the numbers.
  * The two-peak decomposition is checked on curves whose answer is known by hand.
  * rule 23: sobel is never applied to a cube.
"""

import os
import re
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def check_constants():
    prof = open(os.path.join(ROOT, "crates", "strehl-core", "src", "profile.rs"), encoding="utf-8").read()
    got = {}
    for key in ("gain_divisor", "base_iso", "read_noise_e_low", "read_noise_e_high", "second_base_iso"):
        m = re.search(r"^\s*%s:\s*([0-9.]+)," % key, prof, re.M)
        got[key] = float(m.group(1))
    want = dict(gain_divisor=L.GAIN_DIVISOR, base_iso=L.BASE_ISO,
                read_noise_e_low=L.READ_NOISE_E_LOW, read_noise_e_high=L.READ_NOISE_E_HIGH,
                second_base_iso=L.SECOND_BASE_ISO)
    for k in want:
        assert got[k] == want[k], "profile.rs %s = %r but m60lib has %r" % (k, got[k], want[k])
    lv = re.search(r"black:\s*([0-9.]+),\s*\n\s*white:\s*([0-9.]+),", prof)
    assert float(lv.group(1)) == L.BLACK and float(lv.group(2)) == L.WHITE
    print("G0.1  noise constants match crates/strehl-core/src/profile.rs :", got)

    # The relation itself, checked against noise.rs's own doc formula at two points.
    g = L.gain_dn_per_e(500.0)
    rn = L.read_noise_e(500.0)
    want_sigma = np.sqrt(g * 1000.0 + (rn * g) ** 2)
    assert abs(L.sigma_dn(np.float64(1000.0), 500.0) - want_sigma) < 1e-9
    # clamping below black, as noise.rs does
    assert L.sigma_dn(np.float64(-50.0), 500.0) == L.sigma_dn(np.float64(0.0), 500.0)
    print("G0.2  sigma(S) affine + clamped:  ISO500 g=%.6f RN=%.4f e-  sigma(0)=%.4f sigma(1000)=%.4f DN"
          % (g, rn, L.sigma_dn(np.float64(0.0), 500.0), L.sigma_dn(np.float64(1000.0), 500.0)))


def check_second_peak():
    """Curves whose two-peak answer is known by hand."""
    def cube(vals):
        a = np.array(vals, np.float32)[:, None, None]
        return np.repeat(np.repeat(a, 2, 1), 2, 2)

    # 1: strictly unimodal -> no second peak
    V = cube([1, 2, 3, 4, 5, 4, 3, 2, 1])
    r = L.second_peak(V)
    assert not r["has2"].any(), "unimodal curve reported a second peak"
    print("G0.3  unimodal curve -> has2 False everywhere   (k1=%d)" % r["k1"][0, 0])

    # 2: two clean peaks, taller at 2, second at 7, dip at 5
    V = cube([1, 5, 9, 5, 2, 1, 3, 6, 3, 1])
    r = L.second_peak(V)
    assert r["has2"].all()
    assert r["k1"][0, 0] == 2 and r["k2"][0, 0] == 7, (r["k1"][0, 0], r["k2"][0, 0])
    assert abs(r["prom"][0, 0] - (6 - 1)) < 1e-5, r["prom"][0, 0]
    kd = L.dip_index(V, r["k1"], r["k2"])
    assert kd[0, 0] == 5, kd[0, 0]
    print("G0.4  bimodal curve -> k1=2 k2=7 dip=5 prominence=%.3f (hand value 5.000)" % r["prom"][0, 0])

    # 3: a shoulder (local max inside the main basin, no dip) is NOT a second peak
    V = cube([1, 2, 6, 5, 6.5, 12, 6, 2, 1])
    r = L.second_peak(V)
    # frame 2 is a local max but the dip between it and k1=5 is 5.0, so prominence
    # is 6-5 = 1.0 -- small but real. Assert the arithmetic rather than the label.
    assert r["k1"][0, 0] == 5 and r["k2"][0, 0] == 2
    assert abs(r["prom"][0, 0] - 1.0) < 1e-5, r["prom"][0, 0]
    print("G0.5  shoulder -> prominence 1.000, i.e. small not zero; the noise gate must do the rejecting")

    # 4: three peaks -> the SECOND-tallest-by-prominence wins, not the second-tallest-by-height
    V = cube([1, 8, 1, 20, 1, 6, 1])
    r = L.second_peak(V)
    assert r["k1"][0, 0] == 3 and r["k2"][0, 0] == 1 and abs(r["prom"][0, 0] - 7.0) < 1e-5
    print("G0.6  three peaks -> k2 is the most prominent non-global peak (k2=1, prom=7.000)")

    # 5: boundary-mass case -- max at the last frame
    V = cube([1, 2, 3, 4, 5, 6, 7])
    r = L.second_peak(V)
    assert r["k1"][0, 0] == 6 and not r["has2"].any()
    print("G0.7  monotone-to-the-end curve -> k1 at the stack boundary, has2 False")


def check_power_of_the_z_statistic():
    """A test that cannot fail is not a test (rule 20). Plant a curve the gate must REJECT."""
    n = 60
    rng = np.random.default_rng(60_000)
    # pure noise, no structure at all
    V = rng.normal(100.0, 1.0, (n, 64, 64)).astype(np.float32)
    S = np.full_like(V, 1.0)
    r = L.second_peak(V)
    z, prom, den, _ = L.prominence_z(V, S, r)
    frac_hi = float((z > 6.0).mean())
    print("G0.8  POWER: pure-noise cube, n=%d, %d px -> max z = %.2f, frac(z>6) = %.4f"
          % (n, z.size, z.max(), frac_hi))
    assert frac_hi < 0.02, "the z gate has no power: pure noise clears it at %.3f" % frac_hi

    # and a planted real second peak the gate must ACCEPT
    V2 = V.copy()
    V2[10] += 8.0
    V2[40] += 8.0
    r2 = L.second_peak(V2)
    z2, _, _, _ = L.prominence_z(V2, S, r2)
    hit = float((z2 > 6.0).mean())
    print("G0.9  POWER: same cube with two planted +8 sigma bumps -> frac(z>6) = %.4f, median z = %.2f"
          % (hit, float(np.median(z2))))
    # 0.85, not 1.00, and the shortfall is not a defect: `prom = f2 - fd` where the
    # dip is a running MINIMUM over ~n/2 noise samples, so the statistic has its own
    # spread. Recorded rather than tuned away.
    assert hit > 0.75, "the z gate missed an 8-sigma planted second peak (%.3f)" % hit


def check_rule23():
    G = np.random.default_rng(1).normal(0, 1, (5, 32, 32)).astype(np.float32)
    try:
        L.sobel_mag(G)
    except AssertionError:
        print("G0.10 rule 23: sobel_mag refuses a (frames,y,x) cube")
        return
    raise SystemExit("rule 23 guard did not fire")


if __name__ == "__main__":
    check_constants()
    check_second_peak()
    check_power_of_the_z_statistic()
    check_rule23()
    print("\nGATE 0 PASSED")
