"""Absolute band luminance, not deficit-against-far-field.

`veil_accept` reports each band as a deficit relative to the far field. That is
the right frame only while the far field is fixed: on `flower-bud` it moved 4 DN
between arms and the deficits mean what they say. On `coffee-bean` it moved
+2903 DN, so every band's deficit changes by construction whether or not the
band itself moved. This prints the absolute level so the two can be separated.

The question a veil correction has to answer is not "did the deficit shrink"
but "did the profile FLATTEN" -- did near-silhouette pixels rise toward the far
field faster than the far field itself rose.
"""

import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import binary_closing, binary_opening, distance_transform_edt

BANDS = [(1, 4), (4, 12), (12, 16), (16, 30), (30, 60), (60, 120),
         (120, 200), (200, 300), (300, 420), (500, 900)]


def luma(p: pathlib.Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    if a.ndim == 3:
        return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(np.float32)
    return a.astype(np.float32)


def main() -> int:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\VEILZ2")
    stem = sys.argv[2] if len(sys.argv) > 2 else "cb"

    ref = luma(out / f"{stem}-off.tif")
    on = luma(out / f"{stem}-on.tif")

    backdrop = float(np.median(ref))
    subj = ref < 0.5 * backdrop
    subj = binary_opening(binary_closing(subj, np.ones((9, 9))), np.ones((9, 9)))
    dist = distance_transform_edt(~subj)

    print(f"{stem}: backdrop {backdrop:.0f} DN, subject {100 * subj.mean():.2f}% of frame\n")
    print(f"{'band':>10}  {'off DN':>10}  {'veil DN':>10}  {'delta':>9}  {'as % of band':>12}")

    rows = []
    for lo, hi in BANDS:
        m = (dist >= lo) & (dist < hi) & ~subj
        if not m.any():
            continue
        a, b = float(ref[m].mean()), float(on[m].mean())
        rows.append((lo, hi, a, b))
        print(f"{lo:>4}-{hi:<5}  {a:>10.0f}  {b:>10.0f}  {b - a:>+9.0f}  {100 * (b - a) / a:>11.2f}%")

    far_off, far_on = rows[-1][2], rows[-1][3]
    print(f"\nfar field moved {far_on - far_off:+.0f} DN "
          f"({100 * (far_on - far_off) / far_off:+.2f}%)\n")

    # The shape test. A veil correction must raise veiled pixels TOWARD the far
    # field. Expressing each band as a fraction of its own arm's far field
    # divides the global lift out, so a genuine flattening shows as the ratio
    # rising and a uniform brightening shows as no change at all.
    print(f"{'band':>10}  {'off /far':>9}  {'veil /far':>10}  {'flattened?':>11}")
    better = worse = 0
    for lo, hi, a, b in rows[:-1]:
        ra, rb = a / far_off, b / far_on
        verdict = "yes" if rb > ra + 1e-4 else ("no" if rb < ra - 1e-4 else "flat")
        if verdict == "yes":
            better += 1
        elif verdict == "no":
            worse += 1
        print(f"{lo:>4}-{hi:<5}  {ra:>9.4f}  {rb:>10.4f}  {verdict:>11}")

    print(f"\nbands flattened {better}, bands worsened {worse}, of {len(rows) - 1}")
    if worse > better:
        print("VERDICT: the correction did NOT flatten this subject's profile.")
    elif better > worse:
        print("VERDICT: the profile flattened -- the correction works here.")
    else:
        print("VERDICT: no net change in profile shape.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
