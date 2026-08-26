"""Gradient energy on the do-no-harm guard, with the confound reported beside it.

ORCH asked for gradient energy on `couch-fibers-cpl` before and after. That
number alone cannot answer the question it is being asked, and this project has
been burned by it twice -- "+6.7% gradients, therefore not a blur" while
measuring a blotchy artifact, and "+16.8% high-pass energy" on crops chosen for
containing no structure. **A sharper image and a noisier image both raise
gradient energy.**

So this reports three columns and they only mean something together:

  gradient energy   what was asked for, whole frame, no crop
  flat-region       the same statistic restricted to the smoothest 20% of the
                    frame by local variance in the CONTROL arm -- pixel sets
                    frozen on the control so the treatment cannot choose its
                    own scoring region. There is no subject detail there by
                    construction, so any gradient is noise.
  textured          the complement: the sharpest 20%, where acuity lives.

A blur reads: textured DOWN. Added noise reads: flat UP. Genuine sharpening
reads: textured UP, flat FLAT. The three cases are distinguishable; the single
scalar's are not.

Usage:  python gradenergy.py <label> <ctrl.tiff> <treat.tiff>
"""

import sys

import numpy as np
import tifffile


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, not uint16 -- refusing to guess"
    a = a.astype(np.float64)
    if a.ndim == 3:
        a = 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
    return a


def grad_sq(a):
    gy, gx = np.gradient(a)
    return gx * gx + gy * gy


def local_var(a, r=4):
    """Box variance via summed-area tables, so the mask is cheap on 33 MP.

    The SAT needs a leading zero row and column or the four-corner difference
    is one pixel short in each axis -- which surfaces as a shape mismatch
    rather than a wrong answer, and did.
    """
    p = np.pad(a, r, mode="reflect")
    k = 2 * r + 1

    def sat(x):
        c = np.cumsum(np.cumsum(x, 0), 1)
        return np.pad(c, ((1, 0), (1, 0)), mode="constant")

    c1, c2 = sat(p), sat(p * p)

    def box(c):
        s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
        assert s.shape == a.shape, f"SAT box gave {s.shape}, expected {a.shape}"
        return s / (k * k)

    return np.maximum(box(c2) - box(c1) ** 2, 0.0)


def verdict(gc, gt, flat, tex):
    """The three-way reading. Returned as a tag so it can be tested."""
    tex_r = gt[tex].mean() / gc[tex].mean()
    flat_r = gt[flat].mean() / gc[flat].mean()
    if tex_r < 0.98:
        return "SOFTER", tex_r, flat_r
    if flat_r > 1.05 and tex_r <= flat_r:
        return "NOISIER", tex_r, flat_r
    return "CLEAN", tex_r, flat_r


def commission():
    """Three planted cases with known answers, and the instrument must separate them.

    A single gradient-energy number cannot: a blur and added noise move it in
    opposite directions but a sharpening and added noise move it the same way.
    If this cannot tell case 2 from case 3 it has no business scoring a merge.
    """
    rng = np.random.default_rng(7)
    h, w = 600, 800
    yy, xx = np.mgrid[0:h, 0:w]
    # A subject with genuinely flat regions and genuinely textured ones, so the
    # quantile split has something real to find.
    base = 8000 + 3000 * np.sin(xx / 90.0)
    tex_mask = (xx > w // 2)
    base = base + tex_mask * 900 * np.sin(xx * 1.7) * np.cos(yy * 1.9)
    ctrl = base + rng.normal(0, 40, (h, w))

    def blur(a, n=2):
        for _ in range(n):
            a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
        return a

    cases = [
        ("identity", ctrl.copy(), "CLEAN"),
        ("blurred", blur(ctrl), "SOFTER"),
        ("noise +3x", ctrl + rng.normal(0, 80, (h, w)), "NOISIER"),
    ]
    v = local_var(ctrl)
    flat = v <= np.quantile(v, 0.20)
    tex = v >= np.quantile(v, 0.80)
    gc = grad_sq(ctrl)

    ok = True
    print(f"{'case':14s} {'expected':10s} {'got':10s} {'textured':>10s} {'flat':>10s}")
    print("-" * 60)
    for name, treat, want in cases:
        got, tr, fr = verdict(gc, grad_sq(treat), flat, tex)
        hit = got == want
        ok &= hit
        print(
            f"{name:14s} {want:10s} {got:10s} {tr:9.4f}x {fr:9.4f}x"
            f"{'' if hit else '   <-- MISS'}"
        )
    print("\nCOMMISSION:", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main(argv):
    if argv and argv[0] == "--commission":
        return commission()
    if len(argv) != 3:
        print(__doc__)
        return 2
    label, cpath, tpath = argv
    c, t = load(cpath), load(tpath)
    assert c.shape == t.shape, f"shape mismatch {c.shape} vs {t.shape}"

    # Regions chosen on the CONTROL only. A treatment that picks its own
    # scoring pixels is scoring itself.
    v = local_var(c)
    flat = v <= np.quantile(v, 0.20)
    tex = v >= np.quantile(v, 0.80)

    gc, gt = grad_sq(c), grad_sq(t)
    rows = [
        ("gradient energy", gc.mean(), gt.mean()),
        ("  flat 20% (noise)", gc[flat].mean(), gt[flat].mean()),
        ("  textured 20% (acuity)", gc[tex].mean(), gt[tex].mean()),
        ("mean level DN", c.mean(), t.mean()),
    ]
    print(f"\n=== {label} ===")
    print(f"{'statistic':26s} {'ctrl':>14s} {'treat':>14s} {'ratio':>9s}")
    print("-" * 68)
    for name, a, b in rows:
        print(f"{name:26s} {a:14.2f} {b:14.2f} {b / a if a else float('nan'):9.4f}")

    tag, tex_r, flat_r = verdict(gc, gt, flat, tex)
    print()
    if tag == "SOFTER":
        print(f"VERDICT: textured energy DOWN {100 * (1 - tex_r):.1f}% -- this is a softening.")
    elif tag == "NOISIER":
        print(
            f"VERDICT: flat-region energy UP {100 * (flat_r - 1):.1f}% and no more in texture "
            f"({100 * (tex_r - 1):+.1f}%) -- this is added noise, not acuity."
        )
    else:
        print(
            f"VERDICT: textured {100 * (tex_r - 1):+.1f}%, flat {100 * (flat_r - 1):+.1f}% -- "
            f"no softening and no noise inflation."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
