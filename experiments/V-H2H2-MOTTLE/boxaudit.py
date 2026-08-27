"""Audit `orch_blotch.boxblur` against the defect ORCH found in his own copy.

ORCH reported: "the running-sum box blur returned an array one row and one column
short, silently, and only broke when I differenced two blurs of different radius
against the original."

Every number in section 10 of V-HEADTOHEAD2.md is computed through this helper, and
the blotch term differences two blurs of different radius. So the question is not
academic: if this copy carries the same defect, section 10 is void.

Reading the source is not measuring it. This does three things:

  1. SHAPE     - output shape must equal input shape, over even and odd sizes and a
                 range of radii including r >= the input dimension.
  2. VALUE     - the running-sum result must equal a brute-force edge-padded mean to
                 float tolerance. A helper that is the right shape and the wrong
                 numbers is worse than one that crashes.
  3. REACH     - ORCH's exact defect is planted into a local copy and both checks
                 must FAIL on it. An audit that has never been shown to fail is not
                 evidence, and this is the specific failure it is claimed to exclude.

Exit 0 only if the shipped helper passes and the planted defect is caught.
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "ORCH-drift-check"))
import orch_blotch  # noqa: E402


def boxblur_defective(a, r):
    """ORCH's defect: the +1 offset pad on the cumulative sum is missing.

    Without it the four corner lookups are each taken one sample early, so the
    result is one row and one column short. This is the arithmetic that produced a
    silently truncated array.
    """
    if r < 1:
        return a.copy()
    p = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(p, axis=0), axis=1)
    k = 2 * r + 1
    s = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k])
    return (s / (k * k)).astype(np.float32)


def brute(a, r):
    """Edge-padded box mean, written independently of the running-sum trick."""
    if r < 1:
        return a.copy()
    p = np.pad(a, r, mode="edge").astype(np.float64)
    h, w = a.shape
    out = np.empty((h, w), np.float64)
    k = 2 * r + 1
    for y in range(h):
        for x in range(w):
            out[y, x] = p[y:y + k, x:x + k].mean()
    return out


SIZES = [(64, 64), (65, 65), (64, 65), (33, 48), (17, 16)]
RADII = [0, 1, 2, 3, 5, 8, 20]


def audit(fn, name):
    """Returns (shape_failures, value_failures). Both must be 0 for a sound helper."""
    rng = np.random.default_rng(20260827)
    shape_bad = value_bad = 0
    for (h, w) in SIZES:
        a = rng.normal(1000.0, 50.0, (h, w)).astype(np.float32)
        for r in RADII:
            try:
                got = fn(a, r)
            except Exception as exc:
                shape_bad += 1
                print("    %-10s %dx%d r=%-3d RAISED %s" % (name, h, w, r, type(exc).__name__))
                continue
            if got.shape != a.shape:
                shape_bad += 1
                print("    %-10s %dx%d r=%-3d shape %s, expected %s"
                      % (name, h, w, r, got.shape, a.shape))
                continue
            ref = brute(a, r)
            err = float(np.abs(got.astype(np.float64) - ref).max())
            tol = 1e-3 * max(1.0, float(np.abs(ref).max()))
            if err > tol:
                value_bad += 1
                print("    %-10s %dx%d r=%-3d max abs err %.4g > tol %.4g"
                      % (name, h, w, r, err, tol))
    return shape_bad, value_bad


def difference_probe(fn, name):
    """ORCH's trigger: difference two blurs of different radius AGAINST THE ORIGINAL.

    This is the operation that exposed the defect for him, and it is exactly what the
    blotch term does. A helper that is one short makes this raise or broadcast.
    """
    rng = np.random.default_rng(7)
    a = rng.normal(1000.0, 50.0, (97, 61)).astype(np.float32)
    try:
        band = fn(a, 5) - fn(a, 17)
        resid = a - fn(a, 3)
        _ = band.std() + resid.std()
        return band.shape == a.shape and resid.shape == a.shape
    except Exception:
        return False


def main():
    print("AUDITING orch_blotch.boxblur (the helper every section 10 number runs through)")
    sb, vb = audit(orch_blotch.boxblur, "shipped")
    ok_diff = difference_probe(orch_blotch.boxblur, "shipped")
    print("  shape failures %d, value failures %d, difference probe %s"
          % (sb, vb, "OK" if ok_diff else "BROKEN"))
    shipped_ok = (sb == 0 and vb == 0 and ok_diff)

    print("\nREACH: planting ORCH's exact defect; the audit must fail on it")
    dsb, dvb = audit(boxblur_defective, "defective")
    d_diff = difference_probe(boxblur_defective, "defective")
    print("  shape failures %d, value failures %d, difference probe %s"
          % (dsb, dvb, "OK" if d_diff else "BROKEN"))
    caught = (dsb > 0 or dvb > 0 or not d_diff)

    print("\n%-42s %s" % ("shipped helper sound", "YES" if shipped_ok else "NO"))
    print("%-42s %s" % ("audit catches ORCH's defect", "YES" if caught else "NO"))
    verdict = shipped_ok and caught
    print("\n%s" % ("GREEN - section 10's helper is not the one ORCH found"
                    if verdict else "RED - do not trust downstream numbers"))
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
