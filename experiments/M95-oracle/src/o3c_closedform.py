"""O3c -- settle TEST 1 against a CLOSED FORM, not against another implementation.

TEST 1 compared fft_blur to scipy.ndimage.gaussian_filter and they disagreed at
sigma 0.25 and 0.50 but agreed to 4e-5 % at sigma 1.50. A genuine algorithmic
error grows with the effect; this SHRANK with it. That pattern points at scipy's
spatial kernel discretisation, which is a poor approximation to a Gaussian when
sigma is well under one pixel -- but pointing is not measuring, and comparing two
implementations can never say which one is wrong.

A sinusoid can. Convolution with a Gaussian multiplies a pure sinusoid of
frequency f by exactly

    exp( -2 * pi^2 * sigma^2 * f^2 )

with no approximation. That is an external answer neither implementation had any
part in choosing, so it can convict either of them.

C1  fft_blur vs the closed form
C2  scipy.ndimage.gaussian_filter vs the same closed form
C3  negative control for the REPAIRED estimator. Comparing a sigma=1.0 blur
    against a sigma=0.5 blur of the same source must recover
    sqrt(1.0^2 - 0.5^2) = 0.8660, not 1.0. An estimator that just echoes the
    number it was handed cannot produce 0.866.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from o3_commission import OUTD, fft_blur, trim  # noqa: E402
from o3b_k2diag import O_hann  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

N = 1024
CROP = 256


def amplitude(img, fy, fx):
    """Projection of img onto the complex exponential at (fy, fx)."""
    n0, n1 = img.shape
    y = np.arange(n0)[:, None]
    x = np.arange(n1)[None, :]
    ph = np.exp(-2j * np.pi * (fy * y + fx * x))
    return 2.0 * np.abs(np.sum(img * ph)) / (n0 * n1)


def recover_sigma(a, b):
    n = a.shape[0]
    w = O_hann(n)
    fa = np.fft.fft2((a - a.mean()) * w)
    fb = np.fft.fft2((b - b.mean()) * w)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    q = fy * fy + fx * fx
    m = (q > 1e-4) & (q < 0.02)
    ratio = np.abs(fb[m]) ** 2 / np.maximum(np.abs(fa[m]) ** 2, 1e-12)
    y = -np.log(np.maximum(ratio, 1e-12))
    x = 4.0 * (np.pi ** 2) * q[m]
    return float(np.sqrt(max(np.sum(x * y) / np.sum(x * x), 0.0)))


def main() -> int:
    from scipy.ndimage import gaussian_filter

    res = {}
    yy = np.arange(N)[:, None]
    xx = np.arange(N)[None, :]

    print("=" * 74)
    print("C1/C2  transfer of a pure sinusoid vs the closed form exp(-2 pi^2 s^2 f^2)")
    print(f"{'sigma':>6} {'f':>8} {'exact':>10} {'fft_blur':>10} {'err%':>8} "
          f"{'scipy':>10} {'err%':>8}")
    rows = []
    for s in (0.25, 0.50, 1.00, 1.50):
        for cyc in (64, 128, 256):
            f = cyc / N
            base = np.sin(2.0 * np.pi * f * xx + 0.7) * np.ones_like(yy, dtype=np.float64)
            exact = float(np.exp(-2.0 * (np.pi ** 2) * (s ** 2) * (f ** 2)))
            a0 = amplitude(trim(base, CROP), 0.0, f)
            gf = amplitude(trim(fft_blur(base, s), CROP), 0.0, f)
            gs = amplitude(trim(gaussian_filter(base, sigma=s, mode="reflect",
                                                truncate=12.0), CROP), 0.0, f)
            rf, rs = gf / a0, gs / a0
            ef = 100.0 * (rf - exact) / exact
            es = 100.0 * (rs - exact) / exact
            rows.append(dict(sigma=s, f=f, exact=exact, fft=rf, scipy=rs,
                             fft_err_pct=ef, scipy_err_pct=es))
            print(f"{s:6.2f} {f:8.4f} {exact:10.6f} {rf:10.6f} {ef:+8.4f} "
                  f"{rs:10.6f} {es:+8.4f}")

    fmax = max(abs(r["fft_err_pct"]) for r in rows)
    smax = max(abs(r["scipy_err_pct"]) for r in rows)
    print(f"\n    worst |err| -- fft_blur {fmax:.4f} %   scipy {smax:.4f} %")
    c1ok = fmax < 0.05
    print(f"    C1 fft_blur vs closed form : {'PASS' if c1ok else 'FAIL'} (bar: < 0.05 %)")
    print(f"    C2 scipy vs closed form    : "
          f"{'agrees' if smax < 0.05 else 'DISAGREES by up to %.2f %%' % smax}")
    res["c1"] = dict(rows=rows, fft_worst_pct=fmax, scipy_worst_pct=smax, passed=bool(c1ok))

    print("\nC3  negative control: the repaired estimator must NOT echo its input")
    g1 = np.load(os.path.join(r"C:\dev\strehl-out\M95-oracle", "ROI-LOWDRIFT.g1.npy"),
                 mmap_mode="r")
    src = np.asarray(g1[183], dtype=np.float64)
    a = trim(fft_blur(src, 0.5), 96)
    b = trim(fft_blur(src, 1.0), 96)
    got = recover_sigma(a, b)
    want = float(np.sqrt(1.0 ** 2 - 0.5 ** 2))
    err = 100.0 * (got - want) / want
    print(f"    sigma=1.0 measured against a sigma=0.5 reference")
    print(f"    expected sqrt(1.0^2 - 0.5^2) = {want:.4f}   recovered {got:.4f}  "
          f"({err:+.2f} %)")
    print(f"    an estimator echoing its input would have returned 1.0000")
    c3ok = abs(err) < 5.0 and abs(got - 1.0) > 0.05
    print(f"    C3 {'PASS' if c3ok else 'FAIL'}")
    res["c3"] = dict(expected=want, recovered=got, err_pct=err, passed=bool(c3ok))

    ok = c1ok and c3ok
    print("\n" + "=" * 74)
    if ok:
        print("VERDICT: fft_blur matches the closed form; scipy's small-sigma kernel")
        print("         discretisation caused TEST 1. The PLANT IS SOUND and the")
        print("         synthetic ramp's ground truth stands. K2's original failure")
        print("         was an unwindowed estimator, now repaired and controlled.")
    else:
        print("VERDICT: UNRESOLVED -- ramp results stay unreported.")
    res["verdict_ok"] = bool(ok)
    with open(os.path.join(OUTD, "o3c_closedform.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
