"""V-KILLB0 coherence instrument -- separates DENOISING from BLURRING.

WHY IT EXISTS.  V-KILLB0's own commissioning (commission.py C4) established
that on this corpus the 0.40-0.50 cyc/px band is noise-dominated EVEN IN EDGE
TILES: planted white noise removal reads 0.883 at edge sites and planted blur
reads 0.415, so a band-ENERGY ratio at edge sites is only weakly separating and
a band-energy ratio at flat sites is not separating at all.  contrast_ms.py has
no statistic that separates them; it works around the problem by declaring one
band "noise" and refusing to read acuity there.  This measures the thing
directly.

THE STATISTIC.  Per tile, per hard radial frequency bin, with C_A and C_B the
complex spectra of the two arms:

    rho = sqrt(P_B / P_A)                  amplitude ratio (what a variance
                                           metric sees; NOT discriminating)
    g   = Re<C_A conj(C_B)> / P_A          COHERENT GAIN: how much of arm A's
                                           actual waveform survives into B
    D   = ln(g) / ln(rho)                  the discriminator

  * PURE DENOISE.  B = S, A = S + N with N independent of S.  Then
    P_A = S^2 + N^2, P_B = S^2, <C_A conj(C_B)> = S^2, so g = S^2/(S^2+N^2)
    and rho = sqrt(S^2/(S^2+N^2)) = sqrt(g).  Hence  D = 2.
  * PURE BLUR.  B = h A with h a real transfer.  Then g = h and rho = h.
    Hence  D = 1.

So D near 2 means "energy left because noise was removed", D near 1 means
"energy left because the image was softened".  D is dimensionless, needs no
site selection, and cannot be moved by a level change.  Both controls are run
on every invocation.
"""
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp


def tile_pair(ta, tb):
    ta = (ta - ta.mean()) * bp._win()
    tb = (tb - tb.mean()) * bp._win()
    fa = np.fft.rfft2(ta)
    fb = np.fft.rfft2(tb)
    pa = fa.real ** 2 + fa.imag ** 2
    pb = fb.real ** 2 + fb.imag ** 2
    cx = fa.real * fb.real + fa.imag * fb.imag
    return pa, pb, cx


def pooled(fa, fb, idx, nx):
    PA = np.zeros(len(bp.BINS)); PB = np.zeros(len(bp.BINS)); CX = np.zeros(len(bp.BINS))
    for f in idx:
        ty, tx = divmod(int(f), nx)
        y, x = ty * bp.TILE, tx * bp.TILE
        pa, pb, cx = tile_pair(fa[y:y + bp.TILE, x:x + bp.TILE],
                               fb[y:y + bp.TILE, x:x + bp.TILE])
        for i, m in enumerate(bp._masks()):
            PA[i] += pa[m].mean(); PB[i] += pb[m].mean(); CX[i] += cx[m].mean()
    n = len(idx)
    PA /= n; PB /= n; CX /= n
    rho = np.sqrt(PB / PA)
    g = CX / PA
    with np.errstate(divide="ignore", invalid="ignore"):
        D = np.log(g) / np.log(rho)
    return rho, g, D


def table(name, rho, g, D):
    out = [f"   {name}", f"      {'cyc/px':>12s} {'rho':>8s} {'g':>8s} {'D':>7s}  reading"]
    for i, (lo, hi) in enumerate(bp.BINS):
        if D[i] > 1.6:
            rd = "denoise"
        elif D[i] < 1.25:
            rd = "BLUR"
        else:
            rd = "mixed"
        if abs(rho[i] - 1.0) < 0.003:
            rd = "inert"
        out.append(f"      {f'{lo:.2f}-{hi:.2f}':>12s} {rho[i]:8.4f} {g[i]:8.4f} "
                   f"{D[i]:7.3f}  {rd}")
    return "\n".join(out)


def sites_of(lumA):
    ny, nx = bp.grid(lumA.shape)
    g = np.hypot(*np.gradient(gaussian_filter(lumA, 2.0)))
    tg = bp.tile_means(g, ny, nx).ravel()
    o = np.argsort(tg)
    return nx, {"FLAT": o[:12], "EDGE": o[-12:], "ALL": np.arange(ny * nx)}


def main():
    A, B, label = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "")
    la = bp.channels(bp.load(A))["L"]
    lb = bp.channels(bp.load(B))["L"]
    assert la.shape == lb.shape
    nx, sites = sites_of(la)
    print(f"== COHERENCE {label}")

    # commissioning, every run
    h, w = la.shape
    sub = la[h // 2 - 1024:h // 2 + 1024, w // 2 - 1024:w // 2 + 1024]
    nxc = bp.grid(sub.shape)[1]
    idc = np.arange(bp.grid(sub.shape)[0] * nxc)
    rng = np.random.default_rng(3)
    noisy = sub + rng.normal(0, 300.0, sub.shape)
    r1, g1, D1 = pooled(noisy, sub, idc, nxc)             # planted pure denoise
    r2, g2, D2 = pooled(sub, gaussian_filter(sub, 0.55), idc, nxc)  # planted pure blur
    r0, g0, D0 = pooled(sub, sub.copy(), idc, nxc)        # null
    okn = np.allclose(r0, 1.0, atol=1e-9) and np.allclose(g0, 1.0, atol=1e-9)
    okd = D1[0] > 1.7 and D1[1] > 1.7
    okb = D2[0] < 1.2 and D2[1] < 1.2
    print(f"  [C0 NULL ] rho={r0[0]:.9f} g={g0[0]:.9f}  {'PASS' if okn else 'FAIL'}")
    print(f"  [C1 DENOISE plant] D at 0.40-0.50 = {D1[0]:.3f}, 0.30-0.40 = {D1[1]:.3f} "
          f"(want ~2)  {'PASS' if okd else 'FAIL'}")
    print(f"  [C2 BLUR plant   ] D at 0.40-0.50 = {D2[0]:.3f}, 0.30-0.40 = {D2[1]:.3f} "
          f"(want ~1)  {'PASS' if okb else 'FAIL'}")
    if not (okn and okd and okb):
        print("  INSTRUMENT NOT COMMISSIONED -- results below are void")

    for sname, idx in sites.items():
        rho, g, D = pooled(la, lb, idx, nx)
        print(table(f"{sname} (n={len(idx)})", rho, g, D))


if __name__ == "__main__":
    main()
