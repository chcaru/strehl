"""What IS the "flat 20%", and does a ratio taken over it mean what it looks like?

`gradenergy.py` reported flat-region gradient energy 4.17x higher in the blend
arm on `couch-fibers-cpl`. The pictures show no such thing: at the worst
disagreement window the two arms are indistinguishable. On this project the
standing rule is that when the pictures and the number disagree, the pictures
are right -- so this asks what the number is actually made of.

The suspicion is composition. A region selected as "flat" in the control can be
flat because it is CLIPPED, and a clipped region has near-zero gradient by
construction. If the treatment does not clip there, the ratio explodes without
any visible grain.

Usage:  python flatwhat.py <ctrl.tiff> <treat.tiff>
"""

import sys

import numpy as np
import tifffile

from gradenergy import grad_sq, load, local_var


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    c, t = load(argv[0]), load(argv[1])
    v = local_var(c)
    flat = v <= np.quantile(v, 0.20)
    tex = v >= np.quantile(v, 0.80)

    # Clipping has to be read from the RAW files, not the luma, because a
    # channel can pin while luma does not.
    craw = tifffile.imread(argv[0])
    traw = tifffile.imread(argv[1])
    hi_c = (craw >= 65535).any(axis=2) if craw.ndim == 3 else (craw >= 65535)
    hi_t = (traw >= 65535).any(axis=2) if traw.ndim == 3 else (traw >= 65535)
    lo_c = (craw <= 0).any(axis=2) if craw.ndim == 3 else (craw <= 0)
    lo_t = (traw <= 0).any(axis=2) if traw.ndim == 3 else (traw <= 0)

    gc, gt = grad_sq(c), grad_sq(t)
    print(f"{'region':16s} {'px':>12s} {'ctrl lvl':>10s} {'treat lvl':>10s} "
          f"{'ctrl clip%':>11s} {'treat clip%':>12s} {'grad ratio':>11s}")
    print("-" * 88)
    for name, m in (("flat 20%", flat), ("textured 20%", tex), ("whole frame", np.ones_like(flat))):
        cc = 100 * (hi_c | lo_c)[m].mean()
        tc = 100 * (hi_t | lo_t)[m].mean()
        print(
            f"{name:16s} {int(m.sum()):12,} {c[m].mean():10.1f} {t[m].mean():10.1f} "
            f"{cc:10.3f}% {tc:11.3f}% {gt[m].mean() / gc[m].mean():11.4f}"
        )

    # The decisive split: inside the flat set, separate pixels that are clipped
    # in the CONTROL from those that are not. If the ratio collapses on the
    # unclipped part, the headline was composition and not noise.
    print("\nflat 20% split by whether the CONTROL is clipped there:")
    print(f"{'subset':22s} {'px':>12s} {'ctrl grad':>12s} {'treat grad':>12s} {'ratio':>9s}")
    print("-" * 72)
    clipped = flat & (hi_c | lo_c)
    clean = flat & ~(hi_c | lo_c)
    for name, m in (("control clipped", clipped), ("control not clipped", clean)):
        n = int(m.sum())
        if n == 0:
            print(f"{name:22s} {0:12,} {'--':>12s} {'--':>12s} {'--':>9s}")
            continue
        print(
            f"{name:22s} {n:12,} {gc[m].mean():12.1f} {gt[m].mean():12.1f} "
            f"{gt[m].mean() / gc[m].mean():9.4f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
