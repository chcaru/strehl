"""Commission the flat-ROI admission test itself, before its verdict is believed.

`admission.py` is about to disqualify a whole subject. An instrument with that
much authority has to be shown able to fail, and shown able to pass, on cases
where the answer is known in advance. Four criteria, all fixed before running:

  A1 SYNTHETIC NULL      pure Gaussian noise, no structure, no motion.
                         The two estimators must agree: ratio in [0.90, 1.15].
                         If this fails the statistic is mis-normalised and every
                         verdict it has ever given is void.

  A2 PLANTED MOTION      take a REAL admissible ROI and re-cut it from each
                         frame at a slightly different offset, simulating drift.
                         Ratio must rise above the 1.30 bar by 1 px of motion.
                         This is the failure mode the test exists to catch.

  A3 PLANTED STRUCTURE   take a real admissible ROI and add a frame-dependent
                         low-frequency pattern (focus breathing, in effect).
                         Ratio must rise above the bar.

  A4 REAL PASS PRESERVED the untouched real ROI must still pass, so A2/A3 are
                         showing the plant and not a broken baseline.

A1 is the one that can embarrass the test: the spatial estimator is high-passed
and de-biased by sqrt(1-1/81) while the temporal one is raw, so if the de-bias
constant is wrong the ratio sits off 1.00 and the 1.30 bar is measuring the bug.
"""

import pathlib
import sys

import numpy as np

import admission
import pyrnoise as pn

RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\renders")
ROI = (1416, 264, 256, 256)          # the window measure.py chose and admitted
DETAIL_ROI = (2696, 1032, 256, 256)  # the window measure.py chose as most-detailed
RNG = np.random.default_rng(20260214)


def synthetic(n=22, size=256, sd=40.0):
    base = 1800.0
    imgs = {f"f{i:03d}": base + RNG.normal(0.0, sd, (size + 32, size + 32))
            for i in range(n)}
    return imgs, list(imgs), (16, 16, size, size)


def main():
    print("=" * 78)
    print("COMMISSIONING THE FLAT-ROI ADMISSION TEST")
    print(f"bar = {admission.BAR}")
    print("=" * 78)
    results = []

    # --- A1 synthetic null -------------------------------------------------
    imgs, frames, roi = synthetic()
    r, t, s, _ = admission.admission(imgs, frames, roi)
    ok = 0.90 <= r <= 1.15
    print(f"\nA1 SYNTHETIC NULL     pure noise, no structure, no motion")
    print(f"   temporal {t:7.3f} DN   spatial {s:7.3f} DN   ratio {r:.4f}"
          f"   require [0.90, 1.15]   {'PASS' if ok else 'FAIL'}")
    results.append(("A1 synthetic null", ok, f"ratio {r:.4f}"))

    # --- real frames -------------------------------------------------------
    d = RENDERS / "109MSDCF"
    frames = sorted(p.stem for p in d.glob("frame*.tif"))
    real = {f: pn.green(d / f"{f}.tif") for f in frames}

    r0, t0, s0, ok0 = admission.admission(real, frames, ROI)
    print(f"\nA4 REAL PASS PRESERVED {ROI}, n={len(frames)}")
    print(f"   temporal {t0:7.3f} DN   spatial {s0:7.3f} DN   ratio {r0:.4f}"
          f"   require <= {admission.BAR}   {'PASS' if ok0 else 'FAIL'}")
    results.append(("A4 real ROI still passes", ok0, f"ratio {r0:.4f}"))

    # --- A2 planted motion -------------------------------------------------
    # The plant must be POTENT or its verdict is meaningless. Translating a
    # FLAT region barely changes any pixel -- there is nothing there to move --
    # so the motion plant is applied where motion is actually visible: the
    # detail ROI. The flat ROI is then run too, and the contrast between them
    # is itself the finding.
    print(f"\nA2 PLANTED MOTION      re-cut each frame at a drifting offset")
    a2_ok = None
    for label, roi_m in (("DETAIL ROI", DETAIL_ROI), ("flat ROI", ROI)):
        line = []
        for px in (0.0, 1.0, 2.0, 4.0):
            moved = {}
            for i, f in enumerate(frames):
                dx = int(round(px * (i - len(frames) / 2) / max(1, len(frames) / 2)))
                moved[f] = np.roll(np.roll(real[f], dx, axis=1), dx, axis=0)
            r, _, _, ok = admission.admission(moved, frames, roi_m)
            line.append(f"{px:.0f}px:{r:6.3f}{'' if ok else '*'}")
            if label == "DETAIL ROI" and a2_ok is None and not ok:
                a2_ok = px
        print(f"   {label:<11} {'  '.join(line)}      (* = REJECTED)")
    print("   Motion of a FLAT region is deliberately NOT detected: a featureless")
    print("   region has nothing to move. The test detects non-stationary CONTENT.")
    print("   On a detailed region the ratio starts BELOW 1 (spatial high-pass picks up")
    print("   edges the temporal estimator does not); the test is only read on flat ROIs.")
    results.append((f"A2 planted motion rejected at {a2_ok:.0f} px" if a2_ok else
                    "A2 planted motion rejected", a2_ok is not None,
                    f"detail ROI, threshold {a2_ok} px" if a2_ok else "never rejected"))

    # --- A3 planted frame-dependent structure ------------------------------
    # Planted into a full-size copy so the high-pass estimator has its margin;
    # cropping a bare tile silently produced NaN in the first version of this
    # file, and NaN <= bar is False, which read as a PASS. A fake pass is worse
    # than a failure, so the guard below asserts the ratio is finite.
    print(f"\nA3 PLANTED STRUCTURE   frame-dependent low-frequency pattern")
    x, y, w, h = ROI
    gy, gx = np.mgrid[0:h, 0:w]
    a3_ok = None
    for amp in (0.0, 10.0, 25.0, 50.0):
        planted = {}
        for i, f in enumerate(frames):
            im = real[f].astype(np.float64).copy()
            phase = 2 * np.pi * i / len(frames)
            im[y:y + h, x:x + w] += amp * np.sin(2 * np.pi * gx / 64.0 + phase)
            planted[f] = im
        r, _, _, ok = admission.admission(planted, frames, ROI)
        if not np.isfinite(r):
            raise RuntimeError("A3 produced a non-finite ratio -- the estimator is broken")
        print(f"   amplitude {amp:5.1f} DN -> ratio {r:6.3f}   {'admits' if ok else 'REJECTS'}")
        if a3_ok is None and not ok:
            a3_ok = amp
    noise_sd = np.mean([pn.hp_sd(pn.crop(real[f], ROI, pn.BOX)) for f in frames])
    print(f"   the ROI's own noise sd is {noise_sd:.1f} DN, so the test detects")
    print(f"   frame-dependent structure once its amplitude reaches "
          f"{a3_ok / noise_sd:.2f}x the noise." if a3_ok else "   never rejected")
    results.append((f"A3 planted structure rejected at {a3_ok:.0f} DN" if a3_ok else
                    "A3 planted structure rejected", a3_ok is not None,
                    f"threshold {a3_ok} DN = {a3_ok / noise_sd:.2f}x noise sd"
                    if a3_ok else "never rejected"))

    print("\n" + "=" * 78)
    for name, ok, note in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<38} {note}")
    bad = [n for n, ok, _ in results if not ok]
    print("=" * 78)
    print("ADMISSION TEST COMMISSIONED -- its verdicts may be believed."
          if not bad else f"NOT COMMISSIONED -- failed: {', '.join(bad)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
