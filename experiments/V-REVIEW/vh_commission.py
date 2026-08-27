"""Commission the overshoot statistic BEFORE using it, in BOTH directions.

This project has caught two instruments reading backwards: tri.blur_equiv
bounded its own error below at zero, and overshoot_frac was amplitude-invariant
to six significant figures and scored a planted 2 px ring as a GAIN.  So:

  A  clean monotone step            -> must read ~0 (not positive)
  B  planted rim ladder             -> must RECOVER the planted amplitude and
                                       must TRACK it (kills amplitude-invariance)
  C  planted improvement            -> must go DOWN, not up
  D  Gaussian-blurred step          -> must read ~0 (no negative lobes anywhere)
  E  noise-only null distribution   -> the detection floor, declared not assumed
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_lib as H

H_, W_ = 260, 400
CY, CX = 130, 200


def synth(step_amp=8000.0, base=9000.0, width=3.0, noise=0.0, seed=1,
          rim=0.0, rim_pos=1.6, rim_w=0.7, blur_only=False):
    """Vertical step at x=CX. width = 10-90 rise in px (erf profile)."""
    rng = np.random.default_rng(seed)
    x = np.arange(W_, dtype=np.float32) - CX
    from math import sqrt
    # erf with 10-90 width `width`: erf arg scale
    s = width / 2.563103          # 10-90 of erf(x/(s*sqrt2)) is 2.5631*s
    prof = 0.5 * (1.0 + _erf(x / (s * np.sqrt(2.0))))
    p = base + step_amp * prof
    if rim > 0 and not blur_only:
        # a bright rim just outside the bright shoulder, and its dark twin
        p = p + rim * np.exp(-((x - rim_pos * width) / (rim_w * width)) ** 2)
        p = p - rim * np.exp(-((x + rim_pos * width) / (rim_w * width)) ** 2)
    img = np.repeat(p[None, :], H_, axis=0).astype(np.float32)
    if noise > 0:
        img = img + rng.standard_normal(img.shape).astype(np.float32) * noise
    return img


def _erf(z):
    # Abramowitz-Stegun 7.1.26, plenty for a synthetic fixture
    t = 1.0 / (1.0 + 0.3275911 * np.abs(z))
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
                - 0.284496736) * t + 0.254829592) * t * np.exp(-z * z)
    return np.sign(z) * y


def measure(img, R=180.0, tan_len=40.0):
    us, p = H.profile_at(img, CY, CX, 1.0, 0.0, R, tan_len)
    return H.analyse(us, p)


def main():
    print("=" * 78)
    print("ARM A -- clean monotone step must read ~0")
    print("%8s %8s %10s %12s %12s" % ("width", "step", "w_meas", "overshoot", "undershoot"))
    for width in (2.0, 3.0, 5.0, 8.0):
        for amp in (3000.0, 8000.0, 20000.0):
            r = measure(synth(step_amp=amp, width=width))
            if r is None:
                print("%8.1f %8.0f   REJECTED" % (width, amp)); continue
            print("%8.1f %8.0f %10.2f %12.4f %12.4f"
                  % (width, amp, r["w"], r["overshoot_dn"], r["undershoot_dn"]))

    print("")
    print("=" * 78)
    print("ARM B -- planted rim ladder: must RECOVER and TRACK the amplitude")
    print("%10s %12s %12s %10s %10s" % ("planted", "overshoot", "undershoot", "over/plant", "pct"))
    base = measure(synth(step_amp=8000.0, width=3.0))
    for rim in (0.0, 25.0, 50.0, 100.0, 200.0, 400.0, 800.0):
        r = measure(synth(step_amp=8000.0, width=3.0, rim=rim))
        if r is None:
            print("%10.0f   REJECTED" % rim); continue
        ratio = r["overshoot_dn"] / rim if rim else float("nan")
        print("%10.0f %12.3f %12.3f %10.3f %10.3f%%"
              % (rim, r["overshoot_dn"], r["undershoot_dn"], ratio, r["overshoot_pct"]))

    print("")
    print("  amplitude-invariance check (the overshoot_frac failure mode):")
    v = [measure(synth(step_amp=8000.0, width=3.0, rim=r))["overshoot_dn"]
         for r in (100.0, 200.0, 400.0)]
    print("  planted 100/200/400 -> %.4f / %.4f / %.4f  (ratios %.3f, %.3f)"
          % (v[0], v[1], v[2], v[1] / v[0], v[2] / v[1]))
    print("  a statistic that is amplitude-invariant would print 1.000, 1.000 here.")

    print("")
    print("=" * 78)
    print("ARM C -- planted IMPROVEMENT must lower the reading, not raise it")
    ring = measure(synth(step_amp=8000.0, width=3.0, rim=400.0))
    fixed = measure(synth(step_amp=8000.0, width=3.0, rim=0.0))
    print("  ringing edge   overshoot %10.3f DN" % ring["overshoot_dn"])
    print("  same edge, rim removed    %10.3f DN" % fixed["overshoot_dn"])
    print("  direction: %s" % ("DOWN (correct)" if fixed["overshoot_dn"] < ring["overshoot_dn"]
                               else "UP -- INSTRUMENT IS BACKWARDS, STOP"))

    print("")
    print("=" * 78)
    print("ARM D -- Gaussian-blurred step (no negative lobes) must read ~0")
    import cv2
    for sg in (1.0, 2.0, 4.0, 8.0):
        img = synth(step_amp=8000.0, width=0.5)
        img = cv2.GaussianBlur(img, (0, 0), sg)
        r = measure(img)
        print("  sigma %4.1f  w_meas %6.2f  overshoot %10.4f  undershoot %10.4f"
              % (sg, r["w"], r["overshoot_dn"], r["undershoot_dn"]))

    print("")
    print("=" * 78)
    print("ARM E -- noise-only null: the DETECTION FLOOR, measured not assumed")
    for noise in (20.0, 60.0, 150.0):
        vals = []
        for seed in range(1, 25):
            r = measure(synth(step_amp=8000.0, width=3.0, noise=noise, seed=seed))
            if r is not None:
                vals.append(r["overshoot_dn"])
        v = np.array(vals)
        print("  pixel noise %5.0f DN  ->  overshoot null  mean %7.3f  sd %6.3f  "
              "max %7.3f  (n=%d)" % (noise, v.mean(), v.std(), v.max(), len(v)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
