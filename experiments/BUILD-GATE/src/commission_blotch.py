"""Commission the blotch statistic BOTH ways before any arm is quoted.

ORCH's condition, and the reason for it: this project has already shipped a
gauge that was perverse on its own arm -- a planted clip made the reading FALL --
and a mid-band statistic that was refuted for charging for subject structure. A
statistic commissioned only against damage passes trivially: an instrument whose
error is bounded below zero can ignore a defect but can never charge for one, and
every planted defect makes the picture worse, so "the number went the right way"
is satisfied by a blind gauge.

Four arms, and all four must pass:

  C1  PLANTED BLOTCH        add correlated noise in the 20-60px band.
                            sigma_mid must RISE, and by roughly the planted
                            amount in quadrature.
  C2  PLANTED IMPROVEMENT   suppress the 20-60px band toward its local mean.
                            sigma_mid must FALL. This is the arm a blind
                            statistic fails.
  C3  SPECIFICITY, blotch   the planted blotch is band-limited to 20-60px, so
                            the FINE sharpness column must NOT move. If it does,
                            the two columns are not independent and a blotch
                            result could be a sharpness result in disguise.
  C4  SPECIFICITY, blur     a real blur must MOVE the sharpness column down.
                            Without this, C3 is satisfied by a sharpness column
                            that never moves at all -- the frozen-probe failure.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blotch as bl                                               # noqa: E402
from orch_eye_check import boxblur                                # noqa: E402
from orch_sharp1to1 import CROP, luma                             # noqa: E402
from ceiling import pick_sites                                    # noqa: E402
import tifffile                                                   # noqa: E402
import bandceiling as bc                                          # noqa: E402

REF = os.path.join(bl.SWEEP, "WHITE200")


def band_noise(shape, rng, amp):
    """Noise confined to 20-60px by an FFT bandpass.

    The first version filtered white noise with the same difference-of-box-means
    the statistic uses. That was wrong twice, and the commissioning caught both:
    box filters have poor stopband rejection, so the plant leaked into
    0.20-0.25 cyc/px and moved the sharpness column by 4.8% (C3 FAIL); and
    passing the plant through the band filter a second time inside sigma_mid
    attenuated it, so the measured rise fell short of quadrature (C1 FAIL).

    A brick-wall FFT bandpass has no sidelobes, so the plant lives in 20-60px
    and nowhere else. Both failures were defects in the instrument's test rig,
    which is what a commissioning run is for.
    """
    n0, n1 = shape
    fy = np.fft.fftfreq(n0)[:, None]
    fx = np.fft.fftfreq(n1)[None, :]
    f = np.sqrt(fy ** 2 + fx ** 2)
    m = (f >= 1.0 / 60.0) & (f <= 1.0 / 20.0)
    b = np.real(np.fft.ifft2(np.fft.fft2(rng.normal(0, 1, shape)) * m))
    return b / max(np.std(b), 1e-12) * amp


def fine(c):
    """The sharpness column, stated: band 0.20-0.25 cyc/px, same pixels."""
    return float(np.mean(bc.tile_bands(luma(c * 257.0))[..., 1]))


def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"
    p = os.path.join(REF, subject + ".tiff")
    flat, rej, ncand = bl.pick_flat_sites(p)
    y, x = flat[0]
    c = bl.codes(p, y, x)
    rng = np.random.default_rng(7)
    base_mid = np.mean([bl.sigma_mid(c[..., k]) for k in range(3)])
    base_fine = fine(c)
    print("%s FLAT site (%d,%d) of %d candidates, rejected %r"
          % (subject, y, x, ncand, rej))
    print("baseline sigma_mid %.4f codes  fine %.4g" % (base_mid, base_fine))
    print("(a textured site reads sigma_mid 25.34, ~99%% subject structure, "
          "where a 2-code plant is unresolvable -- hence the flat population)")
    bad = []

    print("\nC1 PLANTED BLOTCH -- sigma_mid must rise, ~quadrature")
    print("  amplitudes are FRACTIONS OF THE BASELINE, because an absolute plant")
    print("  is only meaningful against the sigma it is competing with")
    print("%8s %10s %10s %10s %10s" % ("amp/base", "sigma_mid", "x base", "predicted", "verdict"))
    for f in (0.25, 0.5, 1.0, 2.0):
        amp = f * base_mid
        plant = band_noise(c.shape[:2], rng, amp)
        # Predict from the plant's OWN sigma_mid, not from its amplitude. The
        # statistic measures a band; the plant's amplitude is defined over its
        # whole spectrum. Predicting from amp tests my filter algebra, not the
        # instrument.
        s_plant = bl.sigma_mid(plant)
        d = c + plant[..., None]
        m = np.mean([bl.sigma_mid(d[..., k]) for k in range(3)])
        pred = np.hypot(base_mid, s_plant)
        ok = m > base_mid and abs(m / pred - 1) < 0.15
        if not ok:
            bad.append("C1 f=%.2f measured %.4f predicted %.4f" % (f, m, pred))
        print("%8.2f %10.4f %10.3f %10.4f %10s"
              % (f, m, m / base_mid, pred, "ok" if ok else "FAIL"))

    print("\nC2 PLANTED IMPROVEMENT -- sigma_mid must FALL (the arm a blind gauge fails)")
    print("%8s %10s %10s %10s" % ("strength", "sigma_mid", "x base", "verdict"))
    last = base_mid
    for s in (0.25, 0.5, 0.75, 1.0):
        d = c.copy()
        for k in range(3):
            band = boxblur(c[..., k], 10) - boxblur(c[..., k], 30)
            d[..., k] = c[..., k] - s * band
        m = np.mean([bl.sigma_mid(d[..., k]) for k in range(3)])
        ok = m < last
        if not ok:
            bad.append("C2 s=%.2f did not fall: %.4f >= %.4f" % (s, m, last))
        print("%8.2f %10.4f %10.3f %10s" % (s, m, m / base_mid, "ok" if ok else "FAIL"))
        last = m

    print("\nC3 SPECIFICITY -- a 20-60px plant must NOT move the fine column")
    d = c + band_noise(c.shape[:2], rng, 1.0)[..., None]
    f = fine(d)
    ok = abs(f / base_fine - 1) < 0.02
    if not ok:
        bad.append("C3 fine moved %.3f%% under a band-limited plant"
                   % (100 * (f / base_fine - 1)))
    print("  fine %.1f -> %.1f  (%+.3f%%)  %s"
          % (base_fine, f, 100 * (f / base_fine - 1), "ok" if ok else "FAIL"))

    print("\nC4 SPECIFICITY -- a real blur MUST move the fine column down")
    print("      (without this, C3 passes on a column that never moves)")
    for r in (1, 2):
        d = np.stack([boxblur(c[..., k], r) for k in range(3)], axis=2)
        f = fine(d)
        m = np.mean([bl.sigma_mid(d[..., k]) for k in range(3)])
        ok = f < base_fine * 0.9
        if not ok:
            bad.append("C4 r=%d fine only %.3fx" % (r, f / base_fine))
        print("  blur r=%d  fine %.3fx  sigma_mid %.3fx  %s"
              % (r, f / base_fine, m / base_mid, "ok" if ok else "FAIL"))

    print()
    if bad:
        print("COMMISSION FAILED (%d):" % len(bad))
        for b in bad:
            print("  " + b)
        return 1
    print("BLOTCH STATISTIC COMMISSIONED BOTH WAYS -- catches a planted blotch, "
          "scores a planted improvement, and is independent of the sharpness column")
    return 0


if __name__ == "__main__":
    sys.exit(main())
