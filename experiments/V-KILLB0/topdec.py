"""V-KILLB0 top-decile forensics.

deciles.py reported leaf-2-cpl losing 32% of fine amplitude at its MOST
structured decile, a shape neither planted control makes.  Before that is
reported as a defect it has to survive three separate objections:

 (a) the planted-denoise control failed its bar on this subject, so the
     instrument was not commissioned in-regime.  Re-run the plant at an
     amplitude comparable to the grain actually present (measured from the
     subject, not assumed), and require the SHAPE test rather than a fixed bar:
     blur must fall roughly uniformly, denoise must fall far more at the bottom
     than the top.
 (b) "structure" is defined by a mid-frequency selector.  If the selector is
     really picking noise clumps on this subject, a fall there is a win not a
     loss.  Test by measuring COHERENT GAIN inside the top decile: g < 1 with
     rho ~ 1 means genuine signal attenuation (softening); rho < 1 with g ~ 1
     means decorrelated content (noise) went away.
 (c) it must be visible.  Emit the worst 512x512 tile so it can be looked at.
"""
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp


def fine(x):
    return x - gaussian_filter(x, 0.6366)


def selector(la):
    return gaussian_filter(np.abs(gaussian_filter(la, 1.5) - gaussian_filter(la, 4.0)), 2.0)


def shape(la, lb, sel, nd=10):
    fa, fb = fine(la), fine(lb)
    e = np.percentile(sel, np.linspace(0, 100, nd + 1))
    r = []
    for i in range(nd):
        m = (sel >= e[i]) & (sel < e[i + 1]) if i < nd - 1 else (sel >= e[i])
        r.append(np.sqrt((fb[m] ** 2).mean()) / np.sqrt((fa[m] ** 2).mean()))
    return np.array(r)


def coherent(fa, fb, m):
    a, b = fa[m].astype(np.float64), fb[m].astype(np.float64)
    a -= a.mean(); b -= b.mean()
    ea, eb = np.sqrt((a * a).mean()), np.sqrt((b * b).mean())
    g = (a * b).mean() / (a * a).mean()
    rho = (a * b).mean() / (ea * eb)
    return rho, g, eb / ea


def main():
    A, B, label = sys.argv[1], sys.argv[2], sys.argv[3]
    la = bp.channels(bp.load(A))["L"]
    lb = bp.channels(bp.load(B))["L"]
    h, w = la.shape
    cy, cx = h // 2, w // 2
    sub = la[cy - 1024:cy + 1024, cx - 1024:cx + 1024]
    s = selector(sub)
    top = s >= np.percentile(s, 90)

    # (a) in-regime commissioning: plant at the subject's own bottom-decile grain
    bot = s < np.percentile(s, 10)
    amp = float(np.sqrt((fine(sub)[bot] ** 2).mean()))
    rng = np.random.default_rng(23)
    sh_blur = shape(sub, gaussian_filter(sub, 0.55), s)
    sh_dn = shape(sub + rng.normal(0, amp, sub.shape), sub, s)
    blur_flat = sh_blur[-1] / sh_blur[0]
    dn_tilt = sh_dn[-1] / sh_dn[0]
    print(f"== TOPDECILE {label}")
    print(f"  plant amplitude taken from subject's own bottom-decile grain: {amp:.1f} DN")
    print(f"  C1 blur  shape: " + " ".join(f"{v:5.3f}" for v in sh_blur)
          + f"  top/bottom = {blur_flat:5.3f}")
    print(f"  C2 denoi shape: " + " ".join(f"{v:5.3f}" for v in sh_dn)
          + f"  top/bottom = {dn_tilt:5.3f}")
    ok = dn_tilt > blur_flat * 1.3
    print(f"  C_SHAPE the two plants are separable on THIS subject "
          f"(denoise tilt {dn_tilt:.3f} > 1.3x blur tilt {blur_flat:.3f}): "
          f"{'PASS' if ok else 'FAIL'}")

    # (b) coherent gain inside the top decile, full frame
    fa, fb = fine(la), fine(lb)
    sfull = selector(la)
    tf = sfull >= np.percentile(sfull, 90)
    rho, g, ratio = coherent(fa, fb, tf)
    print(f"  TOP DECILE full frame: rho={rho:.4f}  g={g:.4f}  rms_ratio={ratio:.4f}")
    print(f"     rho~1 & g<1 => genuine softening of real structure")
    print(f"     rho<1 & g~1 => decorrelated (noise-like) content removed")
    for q in (99.0, 99.9):
        tq = sfull >= np.percentile(sfull, q)
        r2, g2, x2 = coherent(fa, fb, tq)
        print(f"  TOP {100-q:4.1f}% full frame: rho={r2:.4f}  g={g2:.4f}  rms_ratio={x2:.4f}")

    # (c) locate the worst 512 tile inside the top decile
    st = 512
    worst, wij = 9e9, None
    for i in range(0, h - st, st):
        for j in range(0, w - st, st):
            m = tf[i:i + st, j:j + st]
            if m.sum() < st * st * 0.35:
                continue
            ta, tb = fa[i:i + st, j:j + st][m], fb[i:i + st, j:j + st][m]
            r = np.sqrt((tb ** 2).mean()) / np.sqrt((ta ** 2).mean())
            if r < worst:
                worst, wij = r, (i, j)
    print(f"  worst heavily-structured 512 tile: ratio={worst:.4f} at {wij}")
    if wij:
        i, j = wij
        ca = la[i:i + st, j:j + st]; cb = lb[i:i + st, j:j + st]
        print(f"     tile A: median={np.median(ca):.0f} clip%={100*(ca>=65000).mean():.3f} "
              f"black%={100*(ca<=200).mean():.3f}")
        print(f"     tile B: median={np.median(cb):.0f} clip%={100*(cb>=65000).mean():.3f} "
              f"black%={100*(cb<=200).mean():.3f}")
        print(f"     tile mean A={ca.mean():.1f} B={cb.mean():.1f} d={100*(cb.mean()/ca.mean()-1):+.3f}%")


if __name__ == "__main__":
    main()
