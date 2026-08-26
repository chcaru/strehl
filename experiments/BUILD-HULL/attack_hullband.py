"""Attack on `experiments/ORCH-drift-check/hullband.py`.

ORCH asked: "If my band decomposition is the thing that is wrong, that is the
most useful thing you could tell me tonight."

It is wrong, in one line, and the error is arithmetic rather than a matter of
filter taste.

THE DEFECT
  `hullband.py` builds a DECIMATED Laplacian pyramid: level k holds N/4^k
  coefficients. It then forms the share of total change as

      tot_d2 += rd * rd * w        with   w = a.size = N / 4**k

  weighting each band by its own coefficient count. But when a decimated band is
  reconstructed it is upsampled back to full resolution, and each of its
  coefficients covers 4^k full-resolution pixels. The full-resolution energy of
  band k is therefore

      (N / 4**k) coefficients  x  4**k pixels each  x  rd^2   =   N * rd^2

  a constant N per band, NOT N/4^k. `hullband.py` under-weights band k by exactly
  4^k: 4x at band 1, 1024x at band 5, and 4096x at the residual. That is why its
  residual reads 0.1% and its finest band reads 60.4%.

  Nothing here depends on the box filter being crude. The docstring's claim that
  "nothing here depends on filter shape" is true and is not the problem. The
  problem is the pixel-count weighting, which would corrupt the share even with a
  perfect filter.

COMMISSIONING
  The correction is not asserted. A synthetic pair is built whose change is
  known by construction to be 99.9% coarse. The corrected weighting must recover
  that and `hullband.py`'s weighting must not. If the plant does not separate the
  two methods, this attack proves nothing and says so.
"""

import sys
import numpy as np
import tifffile

CL = r"C:\dev\strehl-out\BUILD-HULL\accept\coffee-bean--clamped.tiff"
UN = r"C:\dev\strehl-out\BUILD-HULL\accept\coffee-bean--unclamped.tiff"


# ---- ORCH's code, copied verbatim so the comparison is of weightings only ----
def decimate(a):
    h, w = a.shape
    a = a[: h // 2 * 2, : w // 2 * 2]
    return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])


def upsample(a, shape):
    out = np.repeat(np.repeat(a, 2, axis=0), 2, axis=1)
    return out[: shape[0], : shape[1]]


def bands(g, levels=6):
    out = []
    cur = g
    for _ in range(levels):
        h, w = cur.shape
        cur = cur[: h // 2 * 2, : w // 2 * 2]
        small = decimate(cur)
        out.append(cur - upsample(small, cur.shape))
        cur = small
    return out, cur
# ---- end verbatim -----------------------------------------------------------


def shares(cl, un, levels=6):
    """Return (orch_share, corrected_share) per band plus residual."""
    bc, rc = bands(cl, levels)
    bu, ru = bands(un, levels)
    rds, ws = [], []
    for a, b in zip(bc, bu):
        rds.append(float(np.sqrt(((a - b) ** 2).mean())))
        ws.append(a.size)
    rds.append(float(np.sqrt(((rc - ru) ** 2).mean())))
    ws.append(rc.size)

    orch = np.array([r * r * w for r, w in zip(rds, ws)], dtype=np.float64)
    # Each band restored to full resolution: constant pixel count per band.
    corrected = np.array([r * r for r in rds], dtype=np.float64)
    return 100.0 * orch / orch.sum(), 100.0 * corrected / corrected.sum(), rds


def report(title, cl, un, levels=6):
    o, c, rds = shares(cl, un, levels)
    names = [f"band{k} ({2**(k+1)}px)" for k in range(len(rds) - 1)] + ["residual"]
    print(f"\n{title}")
    print(f"  {'band':<16}{'RMS of diff':>13}{'hullband.py':>14}{'corrected':>12}")
    for n, r, a, b in zip(names, rds, o, c):
        print(f"  {n:<16}{r:>13.2f}{a:>13.2f}%{b:>11.2f}%")
    print(f"  {'':<16}{'':>13}{o.sum():>13.2f}%{c.sum():>11.2f}%")
    return o, c


def main():
    print("=" * 78)
    print("COMMISSIONING: a synthetic pair whose change is 99.9% coarse")
    print("=" * 78)
    rng = np.random.default_rng(7)
    n = 2048
    y, x = np.mgrid[0:n, 0:n]
    base = 20000.0 + 3000.0 * np.sin(2 * np.pi * x / 977.0)
    # The planted change: a large, purely COARSE component (period 512 px) plus a
    # small fine-scale component. Their full-resolution energies are known.
    coarse = 200.0 * np.cos(2 * np.pi * x / 512.0) * np.cos(2 * np.pi * y / 512.0)
    fine = rng.normal(0.0, 5.0, size=(n, n))
    e_coarse = float((coarse ** 2).mean())
    e_fine = float((fine ** 2).mean())
    truth = 100.0 * e_coarse / (e_coarse + e_fine)
    print(f"\nby construction, coarse carries {truth:.2f}% of the change energy")
    print(f"  (coarse mean-square {e_coarse:.1f}, fine mean-square {e_fine:.1f})")

    un_s = base
    cl_s = base + coarse + fine
    o, c = report("synthetic pair", cl_s, un_s)
    # coarse content at period 512 lands in the coarse bands and residual
    o_coarse = o[4:].sum()
    c_coarse = c[4:].sum()
    print(f"\n  hullband.py attributes {o_coarse:6.2f}% to bands 4+/residual")
    print(f"  corrected   attributes {c_coarse:6.2f}% to bands 4+/residual")
    print(f"  truth is                {truth:6.2f}%")
    ok_corr = abs(c_coarse - truth) < 15.0
    ok_sep = (truth - o_coarse) > 40.0
    print(f"\n  corrected recovers the truth      : {'PASS' if ok_corr else 'FAIL'}")
    print(f"  the plant separates the two methods: {'PASS' if ok_sep else 'FAIL'}")
    if not (ok_corr and ok_sep):
        print("\nThe plant does not discriminate. This attack proves nothing.")
        return 1

    print("\n" + "=" * 78)
    print("THE REAL PAIR: coffee-bean, the subject hullband.py reports on")
    print("=" * 78)
    cl = tifffile.imread(CL)[:, :, 1].astype(np.float64)
    un = tifffile.imread(UN)[:, :, 1].astype(np.float64)
    o, c = report(f"coffee-bean  {cl.shape}", cl, un)
    print(f"\n  hullband.py : bands 0-1 carry {o[0] + o[1]:.1f}% "
          f"-> 'the clamp acts on fine detail'")
    print(f"  corrected   : bands 0-1 carry {c[0] + c[1]:.1f}%, "
          f"residual {c[-1]:.1f}% -> 'the clamp acts on tone'")
    print("\n  Section 17 of BUILD-HULL.md, using a NON-decimated decomposition")
    print("  where the weighting question cannot arise, independently reads")
    print("  coffee-bean as detail0 14.81% / base 82.48%.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
