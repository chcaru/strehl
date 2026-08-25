"""O3b -- K2 failed. Find out whether the PLANT is wrong or my ESTIMATOR is.

K2 recovered sigma low by 6.9 / 7.3 / 8.7 / 10.3 % at planted 0.25 / 0.50 / 1.00
/ 1.50 px -- a bias that GROWS with sigma. Two candidates:

  (a) fft_blur does not apply the Gaussian it claims to. If so, the synthetic
      ramp's ground truth is wrong and B2 / N0 / N2 / P1s are all void.
  (b) the recovery fit in o3 is biased. It takes |FFT(crop of blurred)|^2 /
      |FFT(crop of source)|^2 with NO window. Blurring mixes in content from
      outside the crop, and an unwindowed FFT of a non-periodic crop leaks
      spectrally. Both push the apparent ratio around.

These have opposite consequences, so guessing is not allowed.

TEST 1 settles it against an INDEPENDENT implementation. scipy.ndimage's
gaussian_filter is a spatial-domain separable convolution -- a completely
different algorithm from spectrum multiplication. If the two agree to numerical
precision, the plant is right and (b) is the answer.

TEST 2 then repairs the estimator (Hann window, interior only) and re-runs the
same recovery. If the bias collapses, that confirms (b) constructively rather
than by elimination.

TEST 3 is the one that actually matters for the milestone: the synthetic ramp's
ground truth does not depend on sigma CALIBRATION at all, only on the peak being
at sigma=0 and blur being monotone in |k-KSTAR|. Both are checked directly.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import o2lib as O  # noqa: E402
from o3_commission import CUBE, KSTAR, OUTD, SIG0, K, fft_blur, trim  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def main() -> int:
    from scipy.ndimage import gaussian_filter

    g1 = np.load(os.path.join(CUBE, "ROI-LOWDRIFT.g1.npy"), mmap_mode="r")
    src = np.asarray(g1[183], dtype=np.float64)
    res = {}

    print("=" * 74)
    print("TEST 1  fft_blur vs scipy.ndimage.gaussian_filter (independent algorithm)")
    rows = []
    for s in (0.25, 0.50, 1.00, 1.50):
        a = fft_blur(src, s)
        b = gaussian_filter(src, sigma=s, mode="reflect", truncate=12.0)
        ai, bi = trim(a, 64), trim(b, 64)
        d = float(np.abs(ai - bi).max())
        rel = d / float(ai.std())
        rows.append(dict(sigma=s, max_abs=d, rel_to_sd=rel))
        print(f"    sigma {s:.2f}  max abs diff {d:.4g} DN   "
              f"{rel*100:.5f} % of the crop's own sd")
    t1ok = all(r["rel_to_sd"] < 0.01 for r in rows)
    print(f"    TEST 1 {'PASS' if t1ok else 'FAIL'} (bar: < 1 % of sd)")
    print("    -> the PLANT is correct; two unrelated algorithms agree." if t1ok
          else "    -> the PLANT is suspect.")
    res["t1"] = dict(rows=rows, passed=bool(t1ok))

    print("\nTEST 2  repair the estimator: Hann window + interior only")
    base_raw = trim(src, 96)
    n = base_raw.shape[0]
    w = O_hann(n)
    rows2 = []
    for s in (0.25, 0.50, 1.00, 1.50):
        b_raw = trim(fft_blur(src, s), 96)
        fa = np.fft.fft2((base_raw - base_raw.mean()) * w)
        fb = np.fft.fft2((b_raw - b_raw.mean()) * w)
        fy = np.fft.fftfreq(n)[:, None]
        fx = np.fft.fftfreq(n)[None, :]
        q = fy * fy + fx * fx
        m = (q > 1e-4) & (q < 0.02)
        ratio = np.abs(fb[m]) ** 2 / np.maximum(np.abs(fa[m]) ** 2, 1e-12)
        y = -np.log(np.maximum(ratio, 1e-12))
        x = 4.0 * (np.pi ** 2) * q[m]
        est = float(np.sqrt(max(np.sum(x * y) / np.sum(x * x), 0.0)))
        err = 100.0 * (est - s) / s
        rows2.append(dict(planted=s, recovered=est, err_pct=err))
        print(f"    sigma {s:.2f} -> recovered {est:.4f}  ({err:+.2f} %)")
    t2ok = all(abs(r["err_pct"]) < 5.0 for r in rows2)
    print(f"    TEST 2 {'PASS' if t2ok else 'FAIL'} (bar: within 5 %)")
    res["t2"] = dict(rows=rows2, passed=bool(t2ok))

    print("\nTEST 3  what the synthetic ramp's ground truth ACTUALLY depends on")
    d0 = float(np.abs(fft_blur(src, 0.0) - src).max())
    print(f"    (a) peak frame is an exact identity: max abs diff {d0:.10g}")
    sds = []
    for k in range(K):
        s = SIG0 * abs(k - KSTAR)
        b = trim(fft_blur(src, s), 96)
        sds.append(float(b.std()))
    left = sds[:KSTAR + 1]
    right = sds[KSTAR:]
    mono = all(left[i] < left[i + 1] for i in range(len(left) - 1)) and \
        all(right[i] > right[i + 1] for i in range(len(right) - 1))
    print(f"    (b) detail is strictly monotone away from the peak: {mono}")
    print(f"        sd at k=KSTAR {sds[KSTAR]:.3f}, at k=0 {sds[0]:.3f}, "
          f"at k={K-1} {sds[K-1]:.3f}")
    t3ok = (d0 == 0.0) and mono
    print(f"    TEST 3 {'PASS' if t3ok else 'FAIL'}")
    print("    -> ground truth is the ORDERING and the peak location, neither of")
    print("       which uses the sigma calibration K2 was testing.")
    res["t3"] = dict(identity_max_abs=d0, monotone=bool(mono), sds=sds, passed=bool(t3ok))

    print("\n" + "=" * 74)
    verdict = ("ESTIMATOR was at fault, plant is sound; B2/N0/N2/P1s stand"
               if (t1ok and t2ok and t3ok) else "UNRESOLVED -- do not report ramp results")
    print(f"VERDICT: {verdict}")
    res["verdict"] = verdict
    with open(os.path.join(OUTD, "o3b_k2diag.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0 if (t1ok and t2ok and t3ok) else 1


def O_hann(n: int) -> np.ndarray:
    w = np.hanning(n + 2)[1:-1]
    return np.outer(w, w)


if __name__ == "__main__":
    raise SystemExit(main())
