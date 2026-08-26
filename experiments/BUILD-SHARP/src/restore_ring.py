"""Paired ringing check on the restoration's sigma^2 sweep.

s24 asks where the restoration "stops being inert and starts ringing". The
inertness half is a byte-comparison and needs no instrument. This is the other
half, and it is the half that decides shippability: a Wiener filter driven with
an understated sigma^2 is a deconvolution, and deconvolution rings.

WHY PAIRED. `demosaic_ab.edge_overshoot` selects its own edge population from
the image it is handed. Run independently on two arms that is a confound: a
sharper arm produces different gradient peaks, so the two runs measure different
edges and the difference between them is partly a difference of population. Here
the edge sites and the amplitude floor are chosen ONCE from the OFF arm and the
SAME profiles are measured in every arm, so the only thing that varies is the
pixels. That also gives a PAIRED delta per edge, which is far more sensitive
than differencing two p99s.

The detector itself is the commissioned one (null 0.0000; plants recovered at
exactly 0.0500 and 0.1500 after it caught five defects in itself). Its ABSOLUTE
value on real textured data is not trustworthy -- real subjects have no true
plateaux -- so only the OFF-to-arm comparison is read here, never the level.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

HALF = 12
N_EDGES = 40000


def luma(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path)).astype(np.float64)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def pick_edges(y: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Edge sites and amplitude floor, taken from the reference arm only."""
    h, w = y.shape
    lo, hi = np.quantile(y[::11, ::11], [0.001, 0.999])
    amp_floor = 0.05 * (hi - lo)
    gx = np.abs(np.diff(y, axis=1))
    peak = (gx[:, 1:-1] >= gx[:, :-2]) & (gx[:, 1:-1] > gx[:, 2:])
    ys, xs = np.nonzero(peak)
    xs = xs + 1
    keep = (xs > HALF + 2) & (xs < w - HALF - 2)
    ys, xs = ys[keep], xs[keep]
    vals = gx[ys, xs]
    take = np.argsort(vals)[-min(N_EDGES, len(vals)):]
    return ys[take], xs[take], float(amp_floor)


def overshoot_at(y: np.ndarray, ys: np.ndarray, xs: np.ndarray,
                 amp_floor: float) -> tuple[np.ndarray, np.ndarray]:
    """Overshoot fraction at FIXED sites. Returns (values, kept_mask).

    `kept` is returned rather than applied so that callers pair edge-for-edge
    and so a rejected edge can never be counted as a passing one.
    """
    out = np.full(len(ys), np.nan)
    for i, (r, c) in enumerate(zip(ys, xs)):
        prof = y[r, c - HALF:c + HALF + 2]
        left = np.median(prof[:5])
        right = np.median(prof[-5:])
        lo_p, hi_p = min(left, right), max(left, right)
        amp = hi_p - lo_p
        if amp < amp_floor:
            continue
        out[i] = max(prof.max() - hi_p, lo_p - prof.min(), 0.0) / amp
    return out, np.isfinite(out)


def ring_plant(y: np.ndarray, a: float) -> np.ndarray:
    """Apply [-a, 1+2a, -a] along x. Calibrated: on an ideal step of amplitude
    A this filter places a single sample at exactly `a*A` beyond the plateau,
    so the detector must return the planted `a` itself, not merely something
    positive. At a=0 it is the identity and must reproduce the null exactly.
    """
    k = np.array([-a, 1.0 + 2.0 * a, -a])
    out = np.empty_like(y)
    for i in range(y.shape[0]):
        out[i] = np.convolve(y[i], k, mode="same")
    return out


def commission() -> int:
    """The paired machinery is new code and is not covered by demosaic_ab's
    commissioning. Two demands: it must return EXACTLY zero difference when an
    arm is the reference, and it must recover a planted overshoot at its
    planted size.
    """
    rng = np.random.default_rng(11)
    h, w = 256, 256
    y = np.zeros((h, w))
    # Random step edges, well separated so each profile window spans one edge.
    for r in range(h):
        x = 20
        lvl = rng.uniform(2000, 8000)
        while x < w:
            run = int(rng.integers(30, 50))
            y[r, x:x + run] = lvl
            lvl = rng.uniform(2000, 8000)
            x += run
    ys, xs, amp_floor = pick_edges(y)
    v_ref, k_ref = overshoot_at(y, ys, xs, amp_floor)
    print("COMMISSIONING the paired detector")
    print(f"  synthetic edges paired : {int(k_ref.sum())}")
    ok = True

    v_n, k_n = overshoot_at(y, ys, xs, amp_floor)
    both = k_ref & k_n
    dmax = float(np.abs(v_n[both] - v_ref[both]).max())
    print(f"  NULL  (arm IS the reference)   max |d| = {dmax:.6f}"
          f"   {'PASS' if dmax == 0.0 else 'FAIL'}")
    ok &= dmax == 0.0

    for a in (0.05, 0.15, 0.30):
        v_p, k_p = overshoot_at(ring_plant(y, a), ys, xs, amp_floor)
        both = k_ref & k_p
        med = float(np.median(v_p[both]))
        hit = abs(med - a) < 0.005
        print(f"  PLANT a={a:.2f}  recovered median = {med:.4f}"
              f"   {'PASS' if hit else 'FAIL'}")
        ok &= hit
    print("  COMMISSIONED" if ok else "  NOT COMMISSIONED -- do not read results")
    return 0 if ok else 1


def commission_on(path: Path) -> int:
    """Commission the detector on a REAL supplied render.

    `commission()` plants into a synthetic field of ideal steps, and an ideal
    step is the one case where this detector is guaranteed to recover the
    planted amplitude exactly. That is a licence to trust it on ideal steps and
    nothing more. A render from a different stacker carries a different noise
    level, a different grade and a different edge population, and a detector
    that has only ever been seen to respond on our own images has not been
    shown to respond on theirs.

    So the same two demands are made again, on the actual file that will be
    measured:

      NULL   the arm IS the reference -- max |d| must be EXACTLY 0, which tests
             that pairing and site selection are deterministic on this image.
      PLANT  a calibrated [-a, 1+2a, -a] overshoot must come back at its
             planted size, measured as the PAIRED median delta rather than as
             an absolute value, because a real render has no true plateaux and
             its absolute overshoot is therefore not a meaningful zero.

    Whatever recovery this reports is the tolerance every later number on this
    image inherits, and it is printed rather than assumed.
    """
    y = luma(path)
    ys, xs, amp_floor = pick_edges(y)
    v_ref, k_ref = overshoot_at(y, ys, xs, amp_floor)
    print(f"COMMISSIONING on a real render: {path.name}")
    print(f"  shape {y.shape}, amplitude floor {amp_floor:.6g}"
          "   (units are the file's own -- it may be float or DN)")
    print(f"  sites that are real steps : {int(k_ref.sum())} of {len(ys)}")
    print(f"  baseline p99 overshoot    : {np.nanquantile(v_ref, 0.99):.4f}"
          "   (NOT a zero -- real edges are not steps)")
    ok = True

    v_n, k_n = overshoot_at(y, ys, xs, amp_floor)
    both = k_ref & k_n
    dmax = float(np.abs(v_n[both] - v_ref[both]).max())
    print(f"  NULL   max |d| = {dmax:.6f}   {'PASS' if dmax == 0.0 else 'FAIL'}")
    ok &= dmax == 0.0

    # The plant is calibrated on an IDEAL step, where it deposits exactly `a`
    # beyond the plateau. Real edges are blurred over several pixels, so the
    # kernel's negative lobes sit on intermediate values rather than on the
    # plateau and the SAME ringing yields proportionally less overshoot. Exact
    # recovery is therefore the wrong demand on a real render, and loosening it
    # to "pass" would be tuning the test to the answer. What is demanded instead
    # is what a usable instrument actually needs -- determinism, a monotone
    # response, and a clear direction -- and the recovery fraction is REPORTED
    # as this image's sensitivity, which every later number on it inherits.
    rec, prev = [], None
    mono = True
    for a in (0.05, 0.15, 0.30):
        v_p, k_p = overshoot_at(ring_plant(y, a), ys, xs, amp_floor)
        both = k_ref & k_p
        if both.sum() == 0:
            print(f"  PLANT a={a:.2f}  VACUOUS -- no paired edges")
            ok = False
            continue
        delta = float(np.median(v_p[both] - v_ref[both]))
        worse = float((v_p[both] > v_ref[both]).mean())
        if prev is not None and delta <= prev:
            mono = False
        prev = delta
        rec.append(delta / a)
        flag = "PASS" if (delta > 0 and worse > 0.6) else "FAIL"
        print(f"  PLANT a={a:.2f}  paired median delta = {delta:.4f} "
              f"({delta / a:.2f}x of planted), worse = {worse:.4f}   {flag}")
        ok &= delta > 0 and worse > 0.6
    ok &= mono
    print(f"  MONOTONE in plant size : {'PASS' if mono else 'FAIL'}")
    if rec:
        print(f"  SENSITIVITY on this image: recovers {np.mean(rec):.2f}x of planted "
              "ringing.")
        print("  => its magnitudes are a LOWER BOUND on this image, and magnitudes")
        print("     may NOT be compared across images with different edge blur.")
        print("     Paired `worse` and delta, within one image, remain valid.")
    print("  COMMISSIONED ON THIS IMAGE" if ok
          else "  NOT COMMISSIONED ON THIS IMAGE -- do not read results from it")
    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--commission":
        return commission()
    if len(sys.argv) == 3 and sys.argv[1] == "--commission-on":
        return commission_on(Path(sys.argv[2]))
    if len(sys.argv) < 3:
        raise SystemExit("usage: restore_ring.py <off.tif> <arm.tif> [arm.tif ...]\n"
                         "       restore_ring.py --commission\n"
                         "       restore_ring.py --commission-on <real.tif>")
    poff = Path(sys.argv[1])
    off = luma(poff)
    ys, xs, amp_floor = pick_edges(off)
    v_off, k_off = overshoot_at(off, ys, xs, amp_floor)
    print(f"reference arm : {poff.name}")
    print(f"  edge sites chosen from the reference : {len(ys)}")
    print(f"  amplitude floor                      : {amp_floor:.1f} DN")
    print(f"  sites that are real steps            : {int(k_off.sum())}")
    print(f"  sites rejected (texture, no plateau) : {int((~k_off).sum())}")
    print(f"  reference p99 overshoot              : {np.nanquantile(v_off, 0.99):.4f}")
    print()
    hdr = (f"{'arm':16s} {'paired':>7s} {'p99 off':>8s} {'p99 arm':>8s} "
           f"{'ratio':>7s} {'worse':>7s} {'d p99':>8s} {'max d':>8s}")
    print(hdr)
    print("-" * len(hdr))
    for a in sys.argv[2:]:
        pa = Path(a)
        arm = luma(pa)
        if arm.shape != off.shape:
            raise SystemExit(f"shape mismatch {arm.shape} vs {off.shape}")
        v_a, k_a = overshoot_at(arm, ys, xs, amp_floor)
        both = k_off & k_a
        n = int(both.sum())
        if n == 0:
            print(f"{pa.stem:16s}      0   -- no paired edges, VACUOUS --")
            continue
        o, w = v_off[both], v_a[both]
        d = w - o
        p99o, p99a = float(np.quantile(o, 0.99)), float(np.quantile(w, 0.99))
        print(f"{pa.stem:16s} {n:7d} {p99o:8.4f} {p99a:8.4f} "
              f"{p99a/p99o:7.4f} {float((d > 0).mean()):7.4f} "
              f"{p99a-p99o:8.4f} {float(d.max()):8.4f}")
    print()
    print("`worse` is the fraction of paired edges where the arm overshoots more")
    print("than the reference. 0.5 is what a pixel-shuffle would give; a real")
    print("ringing arm drives it toward 1.0 with a positive `d p99`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
