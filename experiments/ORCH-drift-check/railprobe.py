"""Why do accept.py and accept2.py disagree about how much black clipping there is?

accept.py  reports flower-bud pyramid at 2.9920% (predicate: any channel == 0).
accept2.py reports the same subject/arm pair as a rise of 1.4014% (black_lit
+0.0401 + black_dark +1.3613), using the IDENTICAL predicate (a == 0).any(2).

Two instruments, one predicate, one subject, factor 2.13 apart. Therefore the
IMAGES differ, not the code. The prime suspect is demosaicing: my clean6 arms
were rendered with --demosaic (7040x4688), BUILD-WIRE's with the shipped default
(2x2 binned, 3520x2344). Interpolation turns an exact 0 into a small nonzero and
the pixel silently leaves the count while remaining just as dead.

If that is what happened, my gate UNDER-REPORTS the clamp by about half, and the
`== 0` predicate is a presence check masquerading as a state check -- the fifth
instance of that failure in this project.

This probe does not assume it. It measures the black end as a THRESHOLD SWEEP on
the files actually staged. A predicate that is robust will be flat in the
threshold; a fragile one will climb steeply off zero.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile


def lit_mask(ref_green: np.ndarray) -> np.ndarray:
    # From the REFERENCE only. Letting each arm define its own lit population is
    # the defect retracted in ORCH-veiling 22.5: pixels lit in the reference and
    # crushed to black in the test re-classified themselves as dark and deleted
    # themselves from their own measurement.
    thresh = np.quantile(ref_green[::4, ::4], 0.20)
    return ref_green > thresh


def sweep(a: np.ndarray, lit: np.ndarray, thresholds) -> list:
    n = a.shape[0] * a.shape[1]
    rows = []
    for t in thresholds:
        lo = (a <= t).any(axis=2)
        rows.append(
            (
                t,
                100.0 * lo.sum() / n,
                100.0 * np.logical_and(lo, lit).sum() / n,
                100.0 * np.logical_and(lo, ~lit).sum() / n,
            )
        )
    return rows


def main() -> int:
    d = Path(sys.argv[1])
    subject = sys.argv[2]
    ref_arm, test_arm = sys.argv[3], sys.argv[4]

    rp = d / f"{subject}--{ref_arm}.tiff"
    tp = d / f"{subject}--{test_arm}.tiff"
    for p in (rp, tp):
        if not p.exists():
            print(f"missing: {p}")
            return 2

    R = tifffile.imread(rp)
    T = tifffile.imread(tp)
    assert R.dtype == np.uint16 and T.dtype == np.uint16, "expected uint16"
    assert R.shape == T.shape, f"shape mismatch {R.shape} vs {T.shape} -- one arm is binned"

    print(f"subject     : {subject}")
    print(f"reference   : {rp.name}   {R.shape}")
    print(f"test        : {tp.name}   {T.shape}")
    mp = R.shape[0] * R.shape[1] / 1e6
    print(f"resolution  : {R.shape[1]}x{R.shape[0]} = {mp:.1f} Mpx"
          f"   ({'FULL (demosaiced)' if R.shape[0] > 4000 else 'BINNED 2x2'})")

    lit = lit_mask(R[:, :, 1].astype(np.float32))
    print(f"lit fraction: {100.0 * lit.mean():.2f}%  (from reference only)\n")

    ths = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256]
    rr = sweep(R, lit, ths)
    tt = sweep(T, lit, ths)

    print("BLACK END, threshold sweep -- percent of frame with any channel <= t")
    print(f"  {'t':>5}{'ref all':>10}{'test all':>10}{'RISE':>10}"
          f"{'ref lit':>10}{'test lit':>10}{'rise lit':>10}")
    for (t, ra, rl, _rd), (_t, ta, tl, _td) in zip(rr, tt):
        print(f"  {t:5d}{ra:10.4f}{ta:10.4f}{ta - ra:10.4f}"
              f"{rl:10.4f}{tl:10.4f}{tl - rl:10.4f}")

    print("\nWHITE END, threshold sweep -- percent with any channel >= 65535-t")
    print(f"  {'t':>5}{'ref all':>10}{'test all':>10}{'RISE':>10}")
    n = R.shape[0] * R.shape[1]
    for t in ths:
        rh = 100.0 * (R >= 65535 - t).any(axis=2).sum() / n
        th = 100.0 * (T >= 65535 - t).any(axis=2).sum() / n
        print(f"  {t:5d}{rh:10.4f}{th:10.4f}{th - rh:10.4f}")

    # The question this exists to answer.
    exact = tt[0][1] - rr[0][1]
    near = tt[4][1] - rr[4][1]
    print(f"\nexact-zero rise      : {exact:.4f}%")
    print(f"near-black (<=8) rise: {near:.4f}%")
    if exact > 1e-9:
        print(f"ratio near/exact     : {near / exact:.3f}x")
        print("  A predicate flat in t is measuring a state. One that climbs is")
        print("  measuring a coincidence -- how many pixels landed on exactly 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
