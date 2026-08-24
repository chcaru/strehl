"""M100 shortlist checks.

1. How much of each render is ALREADY at 65535 before any exposure -- because
   bar B3 is a bar on the output, and clipping that was there at zero stops is
   not clipping the exposure caused.
2. Luminance vs max-channel as the statistic, on the shortlist only.
3. Does the statistic care whether it is computed on the binned grid or the
   demosaiced one? (The shipped rule always uses the binned grid.)
4. Does it care how many frames were stacked?

READ-ONLY on D:\\.
"""
import os
import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\M100"
YW = np.array([0.2126729, 0.7151522, 0.0722750], dtype=np.float64)
STACKS = ["bee-2-cpl", "bee-3-cpl", "coffee-bean", "flat-on-ruler-cpl",
          "foam", "highly-angled-ruler-mm-cpl", "lead-1-cpl"]
SHORTLIST = [(99.9, 0.85), (99.9, 0.90), (99.9, 0.95), (99.95, 0.95)]


def srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def q(s):
    return round(float(np.clip(s, -6.0, 6.0)) * 100.0) / 100.0


def load(path):
    a = tifffile.imread(path).astype(np.float32) / 65535.0
    return srgb_to_linear(a.astype(np.float64))


def stat(lin, kind):
    if kind == "luma":
        return np.clip(lin, 0.0, None) @ YW
    return np.clip(lin, 0.0, None).max(axis=2)


def apply_and_score(lin, stops):
    enc = linear_to_srgb(lin * (2.0 ** stops))
    u16 = (enc * 65535.0 + 0.5).astype(np.uint16)
    at = u16 == 65535
    return (float(at.any(axis=2).mean()), float(at.all(axis=2).mean()),
            float(np.percentile(enc.mean(axis=2), 99.9)),
            float(np.percentile(enc @ YW, 99.9)))


print("--- 1. clipping ALREADY present at zero stops ---")
print("%-30s %12s %12s" % ("stack", "any-at-max%", "all-at-max%"))
lins = {}
for s in STACKS:
    lin = load(os.path.join(SRC, "tune-%s-srgb.tif" % s))
    a0, l0, _, _ = apply_and_score(lin, 0.0)
    print("%-30s %12.6f %12.6f" % (s, 100 * a0, 100 * l0))
    lins[s] = lin

print()
print("--- 2. luminance vs max-channel, shortlist only ---")
for kind in ("luma", "maxch"):
    for p, t in SHORTLIST:
        rows = []
        for s in STACKS:
            lin = lins[s]
            v = float(np.percentile(stat(lin, kind), p, method="inverted_cdf"))
            st = q(np.log2(t / v)) if v > 0 else 0.0
            rows.append((s, st) + apply_and_score(lin, st))
        anyc = max(r[2] for r in rows)
        allc = max(r[3] for r in rows)
        minm = min(r[4] for r in rows)
        minb = min(r[5] for r in rows)
        ok = anyc <= 0.005 and allc <= 0.002 and minm >= 0.90
        print("%-6s p%-6.2f t%-5.2f  worst any %7.4f%%  all %7.4f%%  "
              "min p99.9(mean) %.4f  (bt709) %.4f  %s"
              % (kind, p, t, 100 * anyc, 100 * allc, minm, minb,
                 "PASS" if ok else "FAIL"))
        for r in rows:
            print("        %-30s %+6.2f  any %7.4f%%  all %7.4f%%  "
                  "p99.9 %.4f / %.4f"
                  % (r[0], r[1], 100 * r[2], 100 * r[3], r[4], r[5]))
    print()

print("--- 3. binned grid vs demosaiced grid, same stack (bee-3, 60 frames) ---")
for name, path in [("binned", "freeze-before-srgb.tif"),
                   ("demosaiced", "freeze-before-srgb-demo.tif")]:
    lin = load(os.path.join(SRC, path))
    y = stat(lin, "luma")
    for p in (99.5, 99.9, 99.95):
        v = float(np.percentile(y, p, method="inverted_cdf"))
        print("  %-11s p%-6.2f Y=%.6f  ->  %+.2f stops at target 0.90"
              % (name, p, v, q(np.log2(0.90 / v))))
    del lin, y

print()
print("--- 4. frame count: bee-3 at 60 frames vs all 299, binned ---")
for name, path in [("60 frames", "freeze-before-srgb.tif"),
                   ("299 frames", "tune-bee-3-cpl-srgb.tif")]:
    lin = load(os.path.join(SRC, path))
    v = float(np.percentile(stat(lin, "luma"), 99.9, method="inverted_cdf"))
    print("  %-11s Y_p99.9 = %.6f  ->  %+.2f stops at target 0.90"
          % (name, v, q(np.log2(0.90 / v))))
    del lin
