"""Where do V-ORACLE's bands actually sit in cyc/px, and is that safe?

ORCH correction #5 makes this binding on everyone: no sharpness, softening or
acuity claim may be quoted without naming the band AND the subject's
qualification at that band.  `flowers-cpl`, which carries this lane's verdict,
does NOT appear in V-LINEAR-BANDS.md -- it has never been band-qualified, the
same status that cost `coffee-bubbles` its licence in that correction.

So I cannot lean on qualification.  I have to establish the frequency of my own
bands and show where they sit relative to the corpus-wide boundary range that
V-LINEAR did measure (0.17-0.48 cyc/px, 2.8x spread).  The safe direction is
DOWNWARD: a band well below the lowest boundary observed anywhere in the corpus
cannot be grain on any subject in it, qualified or not.

Measured empirically from the actual band operator rather than from the DoG
algebra, so the number describes the code that ran, including any implementation
detail the algebra would miss.

Grid note, stated because it changes the comparison by 2x and I have NOT
confirmed it: V-ORACLE works on the green sub-lattice, where 1 green px = 2 raw
px = 2 master px.  V-LINEAR works with no demosaic.  If its cyc/px is the green
grid, compare column A; if it is the raw sensor grid, compare column B.  Both are
printed and the conclusion is required to hold under BOTH.

Usage:  python bandfreq.py
"""
from __future__ import annotations

import numpy as np

import ora

# The lowest and highest signal/noise boundaries V-LINEAR measured anywhere in
# the corpus (docs/research/V-LINEAR-BANDS.md).
BOUND_LO, BOUND_HI = 0.17, 0.48


def radial_response(nb: int, n: int = 512, seed: int = 7):
    """Peak and centroid frequency of each band, in cyc/(green px).

    White noise in, band decomposition out, radially averaged power spectrum.
    White noise is flat in frequency, so the output spectrum IS the band's
    squared transfer function.
    """
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((n, n)).astype(np.float64)
    bs = ora.bands(x)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    fr = np.sqrt(fy ** 2 + fx ** 2)
    nbin = 128
    edges = np.linspace(0, 0.5, nbin + 1)
    idx = np.clip(np.digitize(fr.ravel(), edges) - 1, 0, nbin - 1)
    ctr = 0.5 * (edges[:-1] + edges[1:])
    out = []
    for b in range(nb):
        p = np.abs(np.fft.fft2(bs[b])) ** 2
        num = np.bincount(idx, weights=p.ravel(), minlength=nbin)
        den = np.bincount(idx, minlength=nbin).astype(float)
        prof = num / np.maximum(den, 1)
        pk = ctr[int(np.argmax(prof))]
        cen = float((ctr * prof).sum() / prof.sum())
        # half-power support, the honest "this band spans" figure
        m = prof >= 0.5 * prof.max()
        lo, hi = ctr[m].min(), ctr[m].max()
        out.append((pk, cen, lo, hi))
    return out


def main() -> int:
    nb = ora.NBAND
    resp = radial_response(nb)
    print("=== V-ORACLE band frequencies, measured from the band operator ===")
    print(f"SIGMAS = {ora.SIGMAS}   (green px)\n")
    print(f"{'band':<6}{'A: cyc/green-px':>28}{'B: cyc/raw-px':>26}"
          f"{'used by verdict?':>20}")
    print(f"{'':6}{'peak':>10}{'half-power span':>18}{'peak':>10}"
          f"{'half-power span':>16}")
    print("-" * 80)
    used = {1, 2, 3}
    for b, (pk, cen, lo, hi) in enumerate(resp):
        print(f"b{b:<5}{pk:>10.3f}{f'{lo:.3f}-{hi:.3f}':>18}"
              f"{pk / 2:>10.3f}{f'{lo / 2:.3f}-{hi / 2:.3f}':>16}"
              f"{('YES' if b in used else 'no'):>20}")

    print(f"\nV-LINEAR corpus signal/noise boundary range: "
          f"{BOUND_LO}-{BOUND_HI} cyc/px (2.8x spread, per subject)")
    print("A band whose whole half-power span sits BELOW the LOWEST boundary")
    print("observed anywhere in the corpus cannot be grain on any subject in it,")
    print("qualified or not.  That is the only claim available to me, because")
    print("flowers-cpl has never been band-qualified.\n")

    verdict_ok = True
    for b in sorted(used):
        pk, cen, lo, hi = resp[b]
        a_safe = hi < BOUND_LO           # green-grid reading
        b_safe = (hi / 2) < BOUND_LO     # raw-grid reading
        both = a_safe and b_safe
        if not both:
            verdict_ok = False
        print(f"  b{b}: half-power top edge {hi:.3f} (A) / {hi / 2:.3f} (B) "
              f"vs {BOUND_LO} -> "
              f"{'SAFE under both grid readings' if both else 'NOT safe under grid reading A'}")

    print()
    if verdict_ok:
        print("CONCLUSION: every band the verdict uses is below the lowest")
        print("boundary in the corpus under both grid conventions.")
    else:
        print("CONCLUSION: at least one verdict band is NOT unambiguously below")
        print("the lowest corpus boundary under the less favourable grid")
        print("reading.  That band's contribution must be stated as")
        print("licence-withdrawn-pending-measurement, exactly as ORCH did,")
        print("and the verdict must be shown to survive without it.")

    # Band 0 is excluded from the verdict on purpose; show why.
    pk0, _, lo0, hi0 = resp[0]
    print(f"\nb0 (EXCLUDED from the verdict) peaks at {pk0:.3f} cyc/green-px "
          f"= {pk0 / 2:.3f} cyc/raw-px,")
    print(f"   spanning {lo0:.3f}-{hi0:.3f} (A).  This is the band V-LINEAR "
          f"found to be noise or")
    print("   mixed on 5 of 9 subjects.  It was excluded before this check, not "
          "because of it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
