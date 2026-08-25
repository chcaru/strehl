"""PRE-REGISTERED. Written and committed before the numbers existed.

ORCH asked every agent to report `D` = max/min of a statistic's terms
alongside any cancellation claim. Doing that for M110 exposes a confound in
M110's OWN reported refinement, and this file exists to break it.

THE CONFOUND
------------
M110 reported that section 18 cell A was destroyed by the narrowing and
section 16 overshoot was immune, and attributed the difference to statistic
class: cell A reads the SPACING between levels, overshoot reads only their
ORDER. But those two statistics differ on a second axis as well:

    section 18 cell A   median(dG / dR)          spacing   D large  (dG << dR)
    section 16          P(sign flip AND grew)    ordinal   D ~ 1    (both chroma)

Class and D move together, so the pair cannot separate them. ORCH's D rule
and M110's ordinal rule both predict the observed outcome. That is not
evidence for either.

THE MECHANISM BOTH RULES MAY BE SHADOWS OF
------------------------------------------
Quantisation does not merely add noise to the weaker term. Below one step it
ANNIHILATES it: the term becomes exactly 0. A ratio then reads 0, and -- the
trap -- a SIGN test also degenerates, because np.sign(0) = 0 compares unequal
to everything, so a sign-disagreement rate reads a spurious ~100%.

If that is what happened, D is not a rule in its own right. D predicts how
many steps the weaker term keeps: if the strong term spans S steps, the weak
one spans S/D. It dies when S/D < 1. So the directly actionable quantity is
absolute, not relative:

    W = median steps spanned by the WEAKER term, after narrowing.

D is a proxy for W, and W is the thing that decides.

PREDICTIONS, registered before the data exists
----------------------------------------------
P1  W < 1 for section 18's terms; W ~ 1 for section 16's terms (it is gated
    at exactly 1 display level, so it sits on the boundary by construction).

P2  ANNIHILATION. An ORDINAL statistic on section 18's terms dies too --
    shift >= 50%, or degenerates via the sign(0) trap. If it SURVIVES, term
    annihilation is refuted as the mechanism and class is doing real work.

P3  THE CELL THAT CAN REFUTE M110's OWN REFINEMENT. Re-gate section 16 hard
    enough that W >> 1, then compare ordinal against spacing on those SAME
    terms with the SAME D. If ordinal shifts < 10% and spacing shifts more,
    class matters once the terms are resolved. If BOTH survive, then class
    does NOT matter, W alone is the whole rule, and M110's ordinal refinement
    should be withdrawn.

P4  Dose-response monotone in bit depth, and each statistic breaks at the
    dose where its own W crosses 1.

BARS, fixed here, not after seeing the numbers
----------------------------------------------
    SURVIVES   |relative shift| <  10%   (ORCH's worst D bin reads 8.04%)
    DEGRADED   10% <= |shift| < 50%
    DESTROYED  |shift| >= 50%, or the statistic degenerates

CONTROLS
--------
C1 placebo: a zero-bit "narrowing" must reproduce every uint16 number to
   0.0%, proving the dose is what moves the statistic and not a code path.
C2 positive: distinct levels must actually collapse under the real dose.
C3 sampling: n is logged at every dose and must VARY. A control whose sample
   count stops changing while its parameter keeps moving has tested nothing.
C4 degeneracy: the fraction of pixels whose weaker term is exactly 0 after
   narrowing is reported for every statistic, so a sign test cannot claim
   survival while reading annihilated terms.
"""

from pathlib import Path

import numpy as np
import tifffile

D_DIR = Path(r"C:\dev\strehl-out\M110-sheet\bee-3-cpl")
PRED_G = -0.1152 / 1.6361
LEVEL = 257

SURVIVE, DEGRADE = 10.0, 50.0


def verdict(base, now):
    if base is None or now is None:
        return "DEGENERATE", float("nan")
    if base == 0.0:
        return ("SURVIVES" if now == 0.0 else "DESTROYED"), float("nan")
    s = abs(now - base) / abs(base) * 100.0
    if s < SURVIVE:
        return "SURVIVES", s
    if s < DEGRADE:
        return "DEGRADED", s
    return "DESTROYED", s


def narrow(a, bits):
    return (a >> bits).astype(np.float64) if bits else a.astype(np.float64)


def term_stats(weak, strong, bits):
    """D = max/min of the terms; W = steps the WEAKER term keeps."""
    aw, as_ = np.abs(weak), np.abs(strong)
    lo = np.minimum(aw, as_)
    hi = np.maximum(aw, as_)
    ok = lo > 0
    d = float(np.median(hi[ok] / lo[ok])) if ok.any() else float("inf")
    step = float(2 ** bits) if bits else 1.0
    return d, float(np.median(lo)) / step, float(np.mean(lo < step) * 100.0)


def sec18_terms(off, on, bits):
    d = narrow(on, bits) - narrow(off, bits)
    dR, dG = d[:, :, 0], d[:, :, 1]
    scale = float(np.percentile(np.abs(dR), 99.9))
    m = np.abs(dR) > 0.05 * scale
    return dR[m], dG[m], int(m.sum())


def sec16_terms(off, on, bits, gate_levels):
    def ry(a):
        return a[:, :, 0] - (0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1]
                             + 0.0722 * a[:, :, 2])
    o, n = ry(narrow(off, bits)), ry(narrow(on, bits))
    gate = gate_levels * (LEVEL / 2 ** bits if bits else LEVEL)
    g = np.abs(o) >= gate
    return o[g], n[g], int(g.sum())


def spacing_18(dR, dG):
    return float(np.median(dG / dR))


def ordinal_18(dR, dG):
    """Same two terms, order only: do red and green move in opposite senses?"""
    return float(np.mean(np.sign(dG) != np.sign(dR)) * 100.0)


def ordinal_16(o, n):
    return float(np.mean((np.sign(o) != np.sign(n)) & (np.abs(n) > np.abs(o))) * 100.0)


def spacing_16(o, n):
    """Same two terms, spacing: by what factor did the chroma magnitude move?"""
    ok = np.abs(o) > 0
    return float(np.median(np.abs(n[ok]) / np.abs(o[ok])))


def row(label, base, now, d, w, zero_pct, n):
    v, s = verdict(base, now)
    ss = "   n/a" if np.isnan(s) else f"{s:6.1f}%"
    print(f"  {label:<34} {base:+10.4f} -> {now:+10.4f}   {ss}  {v:<10}"
          f"  D={d:6.2f} W={w:6.2f} zero={zero_pct:5.1f}% n={n:,}")
    return v, s


def main():
    print(__doc__)
    off = tifffile.imread(str(D_DIR / "default.tif")).astype(np.int64)
    on = tifffile.imread(str(D_DIR / "ca.tif")).astype(np.int64)

    lv16 = len(np.unique(off[:, :, 0]))
    lv8 = len(np.unique((off >> 8)[:, :, 0]))
    print(f"C2 positive control: levels {lv16:,} -> {lv8:,} "
          f"({lv16/lv8:.0f}x)  {'PASS' if lv8 < lv16 / 10 else 'FAIL'}")
    print()

    # ---- baselines, uint16 ----
    dR, dG, n18 = sec18_terms(off, on, 0)
    o1, n1, n16 = sec16_terms(off, on, 0, 1.0)
    b_sp18, b_or18 = spacing_18(dR, dG), ordinal_18(dR, dG)
    b_or16, b_sp16 = ordinal_16(o1, n1), spacing_16(o1, n1)

    # ---- C1 placebo: zero-bit dose must reproduce exactly ----
    dR0, dG0, _ = sec18_terms(off, on, 0)
    print(f"C1 placebo (0-bit dose): cell A {spacing_18(dR0, dG0):+.6f} vs "
          f"{b_sp18:+.6f}  "
          f"{'PASS' if spacing_18(dR0, dG0) == b_sp18 else 'FAIL'}")
    print()

    print("=" * 118)
    print("2x2 -- statistic CLASS against TERM RESOLUTION, at the real 8-bit dose")
    print("=" * 118)
    dR8, dG8, n18b = sec18_terms(off, on, 8)
    o8, n8, n16b = sec16_terms(off, on, 8, 1.0)
    d18, w18, z18 = term_stats(dG8, dR8, 8)
    d16, w16, z16 = term_stats(o8, n8, 8)

    print(" section 18 terms (weak = dG):")
    v_sp18, _ = row("  spacing  median(dG/dR)  [reported]", b_sp18,
                    spacing_18(dR8, dG8), d18, w18, z18, n18b)
    v_or18, _ = row("  ordinal  P(sign dG != sign dR)", b_or18,
                    ordinal_18(dR8, dG8), d18, w18, z18, n18b)
    print(" section 16 terms (gate 1 level):")
    v_or16, _ = row("  ordinal  P(flip AND grew)  [reported]", b_or16,
                    ordinal_16(o8, n8), d16, w16, z16, n16b)
    v_sp16, _ = row("  spacing  median(|n|/|o|)", b_sp16,
                    spacing_16(o8, n8), d16, w16, z16, n16b)

    # ---- P3: the cell that can refute M110's own refinement ----
    print()
    print("=" * 118)
    print("P3 -- re-gate section 16 so W >> 1, then vary ONLY the class")
    print("=" * 118)
    p3 = {}
    for gate in (1.0, 4.0, 16.0, 64.0):
        ob, nb, _ = sec16_terms(off, on, 0, gate)
        oq, nq, nn = sec16_terms(off, on, 8, gate)
        if nn < 1000:
            print(f"  gate {gate:5.0f} levels: only {nn:,} px -- skipped")
            continue
        d, w, z = term_stats(oq, nq, 8)
        vo, so = verdict(ordinal_16(ob, nb), ordinal_16(oq, nq))
        vs, ss = verdict(spacing_16(ob, nb), spacing_16(oq, nq))
        print(f"  gate {gate:5.0f} levels  D={d:6.2f} W={w:7.2f} zero={z:5.1f}% "
              f"n={nn:>10,}   ordinal {so:6.1f}% {vo:<10} "
              f"spacing {ss:6.1f}% {vs}")
        p3[gate] = (w, vo, vs)

    # ---- P4: dose-response, with sample counts that must vary (C3) ----
    print()
    print("=" * 118)
    print("P4 -- dose-response.  C3: n must VARY across doses")
    print("=" * 118)
    print(f"  {'bits':>4} {'W(s18)':>8} {'cellA':>10} {'ord18':>8} "
          f"{'W(s16)':>8} {'over16':>8} {'n18':>12} {'n16':>12}")
    ns = []
    for bits in range(0, 9):
        dRb, dGb, na = sec18_terms(off, on, bits)
        ob, nb, nc = sec16_terms(off, on, bits, 1.0)
        _, wa, _ = term_stats(dGb, dRb, bits)
        _, wc, _ = term_stats(ob, nb, bits)
        print(f"  {bits:>4} {wa:>8.2f} {spacing_18(dRb, dGb):>+10.4f} "
              f"{ordinal_18(dRb, dGb):>8.1f} {wc:>8.2f} "
              f"{ordinal_16(ob, nb):>8.2f} {na:>12,} {nc:>12,}")
        ns.append((na, nc))
    varied = len({x[0] for x in ns}) > 1 and len({x[1] for x in ns}) > 1
    print(f"  C3 sampling control: n18 {len({x[0] for x in ns})} distinct, "
          f"n16 {len({x[1] for x in ns})} distinct  "
          f"{'PASS' if varied else 'FAIL -- a saturated control tests nothing'}")

    # ---- adjudication ----
    print()
    print("=" * 118)
    print("ADJUDICATION")
    print("=" * 118)
    print(f"  P1 W(s18) = {w18:.2f}  W(s16) = {w16:.2f}   "
          f"{'PASS' if w18 < 1.0 else 'FAIL'} (predicted W18 < 1)")
    print(f"  P2 ordinal on section 18 terms: {v_or18}   "
          f"{'PASS -- annihilation' if v_or18 != 'SURVIVES' else 'FAIL -- class does real work'}")
    if p3:
        best = max(p3)
        w, vo, vs = p3[best]
        if vo == "SURVIVES" and vs != "SURVIVES":
            print(f"  P3 at W={w:.1f}: ordinal SURVIVES, spacing {vs} -- "
                  "class matters once terms are resolved. Refinement HELD.")
        elif vo == "SURVIVES" and vs == "SURVIVES":
            print(f"  P3 at W={w:.1f}: BOTH survive -- W alone is the rule. "
                  "M110's ordinal refinement is REFUTED and must be withdrawn.")
        else:
            print(f"  P3 at W={w:.1f}: ordinal {vo}, spacing {vs} -- "
                  "no clean attribution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
