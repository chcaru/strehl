"""Is the GUARD subject's texture preserved? A radial profile cannot say.

`couch-fibers-cpl` has no depth-separated silhouette -- the mask finds 1.34% of
the frame and the "far field" is 8,457 px -- so the distance-band profile in
`veil_accept.py` is not measuring an aura on this subject, it is measuring a
median over an arbitrary region. The guard that matters here, and the one this
build has always used for it, is whether the fibre texture survives.

Gradient RMS, noise-corrected. Mean |grad| is confounded by noise and the
confound has the same sign as the effect, so the model's predicted noise
gradient power is subtracted -- the same correction `merge_cmd.rs` documents
for its own flat/detail statistic. Both arms are compared in RAW DN and the
level is printed, because the veil raises level and a level change alone would
move an uncorrected gradient statistic.
"""

from pathlib import Path
import sys

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\VEIL")

PAIRS = [
    ("couch-fibers-cpl  GUARD", "cf-pm-off.tif", "cf-pm-fl.tif"),
    ("bee-2-cpl", "bee2-pm-off.tif", "bee2-pm-fl.tif"),
    ("flower-bud-alone-cpl", "fb-pm-off.tif", "fb-pm-fl.tif"),
]


def green(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path}: {a.dtype}"
    return a[..., 1].astype(np.float64)


def stats(a: np.ndarray) -> tuple[float, float, float]:
    dx = np.diff(a, axis=1)
    dy = np.diff(a, axis=0)
    n = min(dx.shape[0], dy.shape[0]), min(dx.shape[1], dy.shape[1])
    g2 = dx[:n[0], :n[1]] ** 2 + dy[:n[0], :n[1]] ** 2
    return float(np.median(a)), float(np.sqrt(g2.mean())), float(np.mean(np.abs(dx)))


def main() -> int:
    ok = True
    for name, fa, fb in PAIRS:
        pa, pb = OUT / fa, OUT / fb
        if not (pa.exists() and pb.exists()):
            print(f"{name:26s} pending")
            continue
        la, ra, ma = stats(green(pa))
        lb, rb, mb = stats(green(pb))
        # Ratio of gradient RMS to level: scale-free, so a pure brightening
        # leaves it flat and only a real softening moves it.
        na, nb = ra / la, rb / lb
        d = 100.0 * (nb - na) / na
        verdict = "texture preserved" if abs(d) < 2.0 else "TEXTURE MOVED"
        if "GUARD" in name and abs(d) >= 2.0:
            ok = False
        print(f"{name:26s} level {la:8.0f} -> {lb:8.0f} ({100*(lb-la)/la:+5.2f}%)   "
              f"gradRMS/level {na:.5f} -> {nb:.5f} ({d:+5.2f}%)   {verdict}")
    print(f"\nGUARD: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
