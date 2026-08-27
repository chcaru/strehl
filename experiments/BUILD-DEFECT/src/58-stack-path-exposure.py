"""58-stack-path-exposure.py -- does `strehl stack` deliver a commanded
exposure IN THE PIXELS, on the path the shipping subcommand actually runs?

WHY THIS EXISTS, AND WHY A HASH DOES NOT ANSWER IT
==================================================
The orchestrator verified `--exposure=3` against `--exposure=-3` and observed
two DIFFERENT FILE HASHES, and read that as the flag working. That inference is
exactly the one this investigation started by refuting. A 16-bit TIFF from this
renderer carries an `ImageDescription` string holding the tone anchors and the
requested exposure, and section 14 measured those anchors scaling by EXACTLY
the commanded gain (8.0000 / 0.1250 / 6.1050) while the pixel array stayed
BIT-IDENTICAL across all 98,898,048 samples. Two files can therefore differ in
hash, differ in banner, and be pixel-for-pixel the same image.

  An argv records the request and a banner records the claim; a hash records
  the file. Only the pixels record behaviour.

So this reads the pixel arrays and nothing else. The `ImageDescription` is
deliberately not consulted, because it is the surface known to move when the
image does not.

WHAT IS BEING DECIDED
---------------------
Commit `9cb7f5d9` added `Develop::exposure_gain` in `image_out.rs` and wired it
in `stack.rs`. But `main.rs` dispatches `Command::Stack` to `merge_cmd::run`,
not to `stack::run`, so the question is whether the wiring reaches the path the
`stack` subcommand takes. A held patch adds the same call in
`merge_cmd::write_merged`. Either that patch is superseded -- in which case the
pixels already move -- or it is not, in which case they do not.

THE STRUCTURE OF THE ANSWER, WRITTEN BEFORE READING IT
-------------------------------------------------------
Section 14 proved the cancellation is EXACT rather than approximate: both tone
anchors are linear in the data, so `s -> s/g` leaves the normalised value
invariant and the `min(.,s)` cap cancels because both branches carry `1/g`.
An exact cancellation does not leave a residue. So the two outcomes are sharply
separated and there is no ambiguous middle:

  * patch still needed  ->  moved == 0, bit-identical, slope exactly 1.0
  * patch superseded    ->  essentially every unclipped sample moves, slope 2.0

A partial result -- a few samples moving -- would falsify BOTH stories and is
reported as such rather than rounded to whichever is closer.

WHAT THIS SCRIPT MAY NOT CONCLUDE
---------------------------------
It reports the measurement and stops there. It is handed two TIFFs and cannot
know which binary produced them, so it must not name a patch as landed or
superseded -- that inference belongs to the caller, who knows which tree was
built. An earlier revision printed "the held patch IS superseded" on the arm
that was measuring the PATCHED binary, which is the same defect this file was
written to catch: a legible conclusion string that outran what the numbers
established.

COMMISSIONING
-------------
The slope estimator is only reached if the pixels move, but it is commissioned
before it is read either way, on the actual data, by planting known gains and
requiring them back. The planted set is 2.0, 0.5 and 1.0. The 0.5 arm is load
bearing: an estimator bounded below at 1.0, or an inversion that is subtly not
an inverse, sails through a 2.0-only suite. The 1.0 arm is the null -- it
proves the chain is not manufacturing a slope out of quantisation.

The inversion chain is copied deliberately unchanged from
`53-linear-delivered-gain.py`, which was itself commissioned on planted
2.0/0.5/1.0 and then measured a commanded 0.7071068 as 0.7067677 (-0.048%).
Re-deriving it here would be a second implementation to trust; reusing it means
the arithmetic under this verdict is arithmetic that has already been shown to
work.
"""

import sys

import numpy as np
import tifffile

FULL = 65535
CONTRAST = 0.55  # `contrast 0.55` in the render banner; only used by the slope arm.


def srgb_decode(e):
    return np.where(e <= 0.040_448_237, e / 12.92, ((e + 0.055) / 1.055) ** 2.4)


def s_curve_fwd(x, c):
    return x + (x * x * (3.0 - 2.0 * x) - x) * c


def s_curve_inv(y, c, iters=60):
    """Bisection. `s_curve` is monotone on [0,1] for c in [0,1], so this is a
    genuine inverse and not an approximation that happens to be close."""
    lo = np.zeros_like(y)
    hi = np.ones_like(y)
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        too_low = s_curve_fwd(mid, c) < y
        lo = np.where(too_low, mid, lo)
        hi = np.where(too_low, hi, mid)
    return 0.5 * (lo + hi)


def build_lut():
    x = np.arange(FULL + 1, dtype=np.float64) / FULL
    return srgb_decode(s_curve_inv(x, CONTRAST))


LUT = build_lut()


def forward(lin):
    v = np.clip(lin, 0.0, 1.0)
    e = np.where(v <= 0.003_130_8, 12.92 * v, 1.055 * v ** (1.0 / 2.4) - 0.055)
    return np.clip(np.floor(s_curve_fwd(e, CONTRAST) * FULL + 0.5), 0, FULL).astype(
        np.int64
    )


def slope(x, y):
    sxx = float(x @ x)
    if sxx <= 0:
        sys.exit("degenerate regression: no signal in x")
    return float(x @ y) / sxx


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: 58-stack-path-exposure.py <plain.tiff> <exposed.tiff> <stops>")
    plain_path, exp_path, stops = sys.argv[1], sys.argv[2], float(sys.argv[3])
    commanded = 2.0**stops

    a = tifffile.memmap(plain_path, mode="r")
    b = tifffile.memmap(exp_path, mode="r")

    print("=" * 72)
    print("58 -- does the `stack` subcommand deliver a commanded exposure?")
    print("=" * 72)
    print(f"plain     : {plain_path}")
    print(f"exposed   : {exp_path}")
    print(f"commanded : {commanded:.7f}x  (--exposure={stops:+g} stops)")
    print("dispatch  : main.rs Command::Stack -> merge_cmd::run  (NOT stack::run)")
    print()

    if a.shape != b.shape:
        sys.exit(f"shape mismatch {a.shape} vs {b.shape}: not a controlled pair")

    total = int(np.prod(a.shape))
    print(f"samples   : {total:,}")

    # ---- the decisive reading: do the pixels move at all? -----------------
    # Chunked so a 7032x4688x3 pair never has two float copies resident.
    moved = 0
    maxabs = 0
    rows = a.shape[0]
    step = 256
    for r0 in range(0, rows, step):
        ca = np.asarray(a[r0 : r0 + step]).astype(np.int64)
        cb = np.asarray(b[r0 : r0 + step]).astype(np.int64)
        d = cb - ca
        moved += int(np.count_nonzero(d))
        m = int(np.abs(d).max()) if d.size else 0
        maxabs = max(maxabs, m)

    unmoved = total - moved
    print(f"partition : {total:,} samples = {moved:,} moved + {unmoved:,} unmoved")
    print(f"max |delta| : {maxabs} DN")
    print()

    # ---- commission the estimator regardless of which branch is taken ----
    # It is commissioned even when it will not be used for the verdict,
    # because a chain that is only exercised when it is needed has never been
    # shown to work when it is needed.
    print("-- commissioning the inversion + regression chain --")
    row = np.asarray(a[: 8 * 256]).ravel()
    lin = LUT[row]
    keep0 = (row > 0) & (row < FULL)
    commission_ok = True
    for planted in (2.0, 0.5, 1.0):
        replayed = LUT[forward(lin * planted)]
        k = keep0 & (replayed > 0) & (lin > 0) & (lin * planted < 1.0)
        got = slope(lin[k], replayed[k])
        err = abs(got - planted) / planted
        ok = err < 0.01
        commission_ok &= ok
        print(
            f"   planted {planted:<5} -> recovered {got:.7f}"
            f"  ({err * 100:+.3f}%)  n={int(k.sum()):,}  {'PASS' if ok else 'FAIL'}"
        )
    if not commission_ok:
        sys.exit("estimator failed commissioning; no verdict is reported")
    print("   commissioning PASSED")
    print()

    # ---- verdict ---------------------------------------------------------
    if moved == 0:
        print("VERDICT: the pixels are BIT-IDENTICAL. The commanded exposure")
        print("  reached the banner and the file header and did NOT reach the")
        print("  image. Any hash difference is the ImageDescription tone")
        print("  anchors; the picture is unchanged.")
        return 3

    frac = moved / total
    if frac < 0.5:
        print(f"VERDICT: PARTIAL -- only {frac * 100:.4f}% of samples moved.")
        print("  This falsifies both expected outcomes and needs diagnosis")
        print("  before any claim is made about the flag.")
        return 4

    # Enough moved to measure a slope. Use a mid-tone band so clipping, which
    # drags any slope toward 1.0, cannot manufacture the null.
    ka = np.asarray(a[: 8 * 256]).ravel()
    kb = np.asarray(b[: 8 * 256]).ravel()
    la, lb = LUT[ka], LUT[kb]
    k = (ka > 0) & (ka < FULL) & (kb > 0) & (kb < FULL)
    n = int(k.sum())
    if n < 100_000:
        print(f"VERDICT: REFUSED -- only {n:,} unclipped samples, floor 100,000.")
        return 5
    got = slope(la[k], lb[k])
    err = (got - commanded) / commanded
    print(f"delivered : {got:.7f}x against commanded {commanded:.7f}x")
    print(f"error     : {err * 100:+.3f}%   n={n:,}")
    ok = abs(err) < 0.05
    print(
        f"VERDICT: the pixels move and the delivered gain is {'CORRECT' if ok else 'WRONG'}."
    )
    return 0 if ok else 6


if __name__ == "__main__":
    sys.exit(main())
