"""Readout for the band-separation 2x2.

Two statistics, both chosen to match ORCH's band-sweep table so the arms here can
be laid beside theirs without re-scaling:

  * **exactly-zero percentage, per channel** -- ORCH's acceptance metric, on the
    linear 16-bit TIFF.  Rendered --unclamped so the excursion is visible; with
    the hull clamp on, every arm reads 0.000% and the experiment measures
    nothing.

  * **ink p1** -- the 1st percentile of green inside the artifact crop at
    (6136, 1360).  ORCH's density column.  LOW means correct dark ink; a value
    pinned at 0.0000 means the darkest percentile has gone below black and is
    being eaten, which is the excursion showing up as a density number rather
    than as a count.

The two together are what make the result readable.  A count alone cannot
distinguish "the ink got correctly darker" from "the ink fell off the bottom",
and that ambiguity is exactly what ORCH's density column was introduced to
resolve.

One guard, because the count is the kind of statistic that fails silently:
`sanity_zero_metric` plants a known number of zeros into a copy of the array and
requires the counter to find them.  A non-contiguous channel slice returns a COPY
in numpy, so a counter written the obvious way can report a confident 0.000% on
an array that certainly contains zeros.  That bug has already cost this project
one wrong verdict, so the guard hard-errors rather than warns.
"""

import pathlib
import sys

import numpy as np
import tifffile

X, Y, S = 6136, 1360, 600
CH = ("R", "G", "B")


def sanity_zero_metric():
    rng = np.random.default_rng(7)
    a = rng.integers(1, 65535, size=(64, 64, 3), dtype=np.uint16)
    ys, xs = np.unravel_index(rng.choice(64 * 64, 40, replace=False), (64, 64))
    a[ys, xs, 2] = 0
    got = int((a[:, :, 2] == 0).sum())
    if got != 40:
        raise SystemExit(f"COMMISSIONING FAILED: planted 40 zeros in blue, counted {got}")
    if int((a[:, :, 0] == 0).sum()) != 0:
        raise SystemExit("COMMISSIONING FAILED: zeros leaked into an unplanted channel")
    print("zero-counter commissioned: 40/40 planted zeros found, 0 leaked\n")


def report(path):
    img = tifffile.imread(path)
    n = img.shape[0] * img.shape[1]
    zeros = [100.0 * float((img[:, :, c] == 0).sum()) / n for c in range(3)]
    crop = img[Y - S // 2:Y + S // 2, X - S // 2:X + S // 2]
    ink = float(np.percentile(crop[:, :, 1].astype(np.float64), 1)) / 65535.0
    return zeros, ink, img.shape


def main():
    sanity_zero_metric()
    d = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                     else r"C:\dev\strehl-out\BUILD-BLEND\bandsep")
    arms = [("A-bands7", "yes", "yes"), ("B-bands6", "no", "no"),
            ("C-ramp-only", "no", "yes"), ("D-newband-only", "yes", "no")]

    print(f"{'arm':<16}{'M1':>4}{'M2':>4}{'R':>9}{'G':>9}{'B':>9}{'ink p1':>9}")
    print("-" * 60)
    res = {}
    for name, m1, m2 in arms:
        p = d / f"{name}.tiff"
        if not p.exists():
            print(f"{name:<16}{m1:>4}{m2:>4}    MISSING")
            continue
        z, ink, _ = report(p)
        res[name] = (z, ink)
        print(f"{name:<16}{m1:>4}{m2:>4}{z[0]:>9.4f}{z[1]:>9.4f}{z[2]:>9.4f}{ink:>9.4f}")

    if len(res) < 4:
        print("\nincomplete -- not attributing on a partial factorial")
        return

    print("\nATTRIBUTION (worst channel, percentage points)")
    worst = {k: max(v[0]) for k, v in res.items()}
    a, b = worst["A-bands7"], worst["B-bands6"]
    c, dd = worst["C-ramp-only"], worst["D-newband-only"]
    print(f"  A (both)        {a:8.4f}")
    print(f"  B (neither)     {b:8.4f}   <- floor")
    print(f"  C (ramp only)   {c:8.4f}   effect of M2 alone: {c - b:+8.4f}")
    print(f"  D (band only)   {dd:8.4f}   effect of M1 alone: {dd - b:+8.4f}")
    print(f"  interaction     {a - c - dd + b:+8.4f}   (A - C - D + B)")

    span = a - b
    if span <= 0.05:
        print("\n  INCONCLUSIVE: A and B differ by <= 0.05 pt, so there is no effect "
              "to attribute in this build. ORCH's 52x step did not reproduce.")
        return
    fm1, fm2 = (dd - b) / span, (c - b) / span
    print(f"\n  M1 (new selected coarse band) explains {100 * fm1:5.1f}% of the A-B gap")
    print(f"  M2 (exponent ramp shift)      explains {100 * fm2:5.1f}% of the A-B gap")
    lead = "M1 -- the newly SELECTED coarse band" if fm1 > fm2 else "M2 -- the exponent ramp shift"
    print(f"  dominant mechanism: {lead}")


if __name__ == "__main__":
    main()
