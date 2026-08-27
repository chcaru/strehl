"""ladderdiag -- why the M115 ladder did not measure what it was built for.

WHAT HAPPENED.  The ladder read COARSE R = 2.316 (N=34), 14.364 (N=34, other
split), 5.185 (N=60), 95.404 (N=100), 12.313 (N=299), and 18 commissioning arms
failed across the rungs.  A naive reading of the first and last rungs alone
gives Q = 5.3 and "RISING -- ORCH's dilution mechanism corroborated".  The L1P
control forbids that reading: at CONSTANT N = 34, with half-A bit-identical
between the two rungs (sha16 7600B160797D4446) and only half-B's focus offset
changed from 9 frames to 1, R moves 2.316 -> 14.364, a factor of 6.2 -- LARGER
than the whole L1-to-L4 range.  So R is not a function of N here.

THIS FILE ASKS WHY, because "the instrument failed" is not a diagnosis and the
answer changes what other lanes should do with sec.9's statistic.

TWO CANDIDATE CAUSES, and they make different predictions.

  H1  MISREGISTRATION BETWEEN THE HALVES.  strehl aligns each half
      independently, and at stride 9 a half's frames are 18 apart in focus.
      If that alignment is worse at low N, half-A and half-B sit on different
      pixel grids and phi measures displacement, not selection.  V-HEADTOHEAD2
      sec.7 names exactly this as one of three things that invalidated a pass.
      PREDICTS: a nonzero A-vs-B shift that varies across rungs, and it should
      be larger where phi is larger.

  H2  PHI SATURATION.  phi = P_d/P_m tends to 1 as the halves decorrelate, so
      it is bounded in practice and R becomes a ratio of two saturated numbers.
      PREDICTS: the rungs with extreme R are the ones where an arm's phi sits
      near 1, and R there carries no information about degree.

They are not exclusive and H1 can cause H2.  Both are measured here.

    python ladderdiag.py
"""
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import incoh as I                                                # noqa: E402
import hd2                                                       # noqa: E402
import ladder_run as L                                           # noqa: E402

RUNGS = ("bee-L1", "bee-L1P", "bee-L2", "bee-L3", "bee-L4")


def off_of(man):
    """Resolved half-B focus offset in frames.

    ladder_build.ps1 uses -1 as the sentinel for "same as the stride", so the
    raw manifest field is NOT the offset.  The first version of this file
    printed man['stride'] under a column headed 'off', which labelled bee-L1P
    as 9 when it is 1 -- on the one rung that carries the whole finding.  That
    is the same class of error sec.10 was written about: a true number under a
    false heading is indistinguishable from a wrong number by reading.
    """
    b = int(man.get("boffset", -1))
    return int(man["stride"]) if b < 0 else b


def main():
    print("=" * 108)
    print("LADDERDIAG -- H1 misregistration between halves, H2 phi saturation")
    print("=" * 108)

    with open(os.path.join(hd2.ROOT, "ladder-bee.json"), encoding="utf-8") as fh:
        lad = json.load(fh)
    byr = {o["rung"]: o for o in lad["rungs"]}

    print("\nH1  INTEGER SHIFT BETWEEN THE TWO HALVES OF THE SAME ARM")
    print("    A nonzero shift means phi is partly measuring displacement.")
    print(f"\n  {'rung':9s} {'N':>4s} {'off':>4s} "
          f"{'strehl A-B shift':>18s} {'peak':>7s} | "
          f"{'enfuse A-B shift':>18s} {'peak':>7s}")
    rows = []
    offs = {}
    for r in RUNGS:
        arm = os.path.join(hd2.ROOT, r, "arms")
        with open(os.path.join(hd2.ROOT, r, "manifest.json"),
                  encoding="utf-8") as fh:
            man = json.load(fh)
        offs[r] = off_of(man)
        sA = I.Comp(dict(path=os.path.join(arm, "strehl-A.tiff"), weights=I.W))
        sB = I.Comp(dict(path=os.path.join(arm, "strehl-B.tiff"), weights=I.W))
        eA = I.Comp(dict(path=os.path.join(arm, "coh-enfuse-A.tif"), weights=I.W))
        eB = I.Comp(dict(path=os.path.join(arm, "coh-enfuse-B.tif"), weights=I.W))
        sdy, sdx, spk = L.shift_of(sA, sB)
        edy, edx, epk = L.shift_of(eA, eB)
        print(f"  {r:9s} {man['n']:4d} {offs[r]:4d} "
              f"{f'({sdy:+d}, {sdx:+d})':>18s} {spk:7.4f} | "
              f"{f'({edy:+d}, {edx:+d})':>18s} {epk:7.4f}")
        rows.append((r, man["n"], offs[r],
                     sdy, sdx, spk, edy, edx, epk))

    smax = max(abs(x[3]) + abs(x[4]) for x in rows)
    print(f"\n  largest strehl A-B shift over all rungs: {smax} px "
          f"(REG_D = {I.REG_D} px blocks)")
    if smax == 0:
        print("  H1 IS REFUTED: every arm's two halves sit on the same pixel")
        print("  grid to within one block.  phi is not measuring displacement,")
        print("  so the ladder's instability is not misregistration.")
    else:
        print("  H1 SURVIVES: at least one rung's halves are displaced, and")
        print("  phi there is partly a registration reading.")

    print("\n\nH2  PHI SATURATION -- how close to 1 does each arm sit?")
    print("    phi -> 1 means the halves share no coherent structure in the")
    print("    band.  Once an arm saturates, R is a ratio of two ceilings and")
    print("    says nothing about degree.")
    for bname, _ in I.BANDS:
        print(f"\n  {bname}")
        print(f"  {'rung':9s} {'N':>4s} {'off':>4s} {'phi strehl':>11s} "
              f"{'phi enfuse':>11s} {'R':>10s}  note")
        for r in RUNGS:
            b = byr[r]["bands"][bname]
            ps, pe, R = b["phi_s"], b["phi_e"], b["R"]
            note = []
            if b.get("degenerate"):
                note.append("DEGENERATE (phi >= 1)")
            else:
                if ps > 0.9:
                    note.append("strehl SATURATED")
                if isinstance(pe, float) and pe == pe and pe > 0.9:
                    note.append("enfuse SATURATED")
            print(f"  {r:9s} {byr[r]['n']:4d} "
                  f"{offs[r]:4d} {ps:11.5f} "
                  f"{pe if pe == pe else float('nan'):11.5f} {R:10.3f}  "
                  f"{', '.join(note)}")

    print("\n" + "=" * 108)
    print("H1 DIRECTION TEST, on the one pair where everything else is held")
    print("  incoh.pairs(cA, cB, cells) is called with placer=None for the")
    print("  half-vs-half comparison, i.e. it crops the SAME (y, x) from both")
    print("  halves and does NOT register A to B.  So a real A-B displacement")
    print("  lands directly in d = (a - b)/2 and inflates phi.  H1's mechanism")
    print("  is therefore live, and the question is only whether it drives the")
    print("  ladder.  H1 predicts phi_strehl RISES with the A-B shift.")
    l1 = byr["bee-L1"]["bands"]["COARSE"]
    l1p = byr["bee-L1P"]["bands"]["COARSE"]
    s1 = next(x for x in rows if x[0] == "bee-L1")
    s1p = next(x for x in rows if x[0] == "bee-L1P")
    sh1, sh1p = abs(s1[3]) + abs(s1[4]), abs(s1p[3]) + abs(s1p[4])
    print(f"\n  bee-L1   shift {sh1:2d} px   phi_strehl {l1['phi_s']:.5f}")
    print(f"  bee-L1P  shift {sh1p:2d} px   phi_strehl {l1p['phi_s']:.5f}")
    if sh1p > sh1 and l1p["phi_s"] < l1["phi_s"]:
        print("  H1 PREDICTS THE WRONG DIRECTION HERE: the rung with TWICE the")
        print(f"  displacement has {l1['phi_s'] / l1p['phi_s']:.1f}x LOWER phi. "
              "Misregistration is real but")
        print("  it is not what drives the ladder.")
    else:
        print("  H1's direction is consistent on this pair.")

    print("\n\nH3  THE HALF-SPLIT FOCUS OFFSET, which was confounded with N")
    print("    BY MY OWN BUILDER'S DEFAULT.  ladder_build.ps1 defaults")
    print("    -BOffset to the stride, so the offset FELL as N rose:")
    print(f"\n  {'rung':9s} {'N':>4s} {'offset':>7s} {'phi strehl':>11s} "
          f"{'phi enfuse':>11s} {'R':>10s}")
    for r in RUNGS:
        b = byr[r]["bands"]["COARSE"]
        print(f"  {r:9s} {byr[r]['n']:4d} {offs[r]:7d} {b['phi_s']:11.5f} "
              f"{b['phi_e']:11.5f} {b['R']:10.3f}")
    seq = [(byr[r]["n"], offs[r]) for r in RUNGS if r != "bee-L1P"]
    mono = all(seq[i + 1][1] <= seq[i][1] for i in range(len(seq) - 1))
    print(f"\n  offset monotonically non-increasing in N over the original")
    print(f"  ladder (L1, L2, L3, L4): {mono}")
    print("  So the ladder as built cannot separate 'R rises with N' from")
    print("  'R rises as the half-split offset falls'.  The L1/L1P pair")
    print("  prices the second at CONSTANT N:")
    print(f"    offset 9 -> R = {l1['R']:.3f}    offset 1 -> R = {l1p['R']:.3f}"
          f"    {l1p['R'] / l1['R']:.2f}x")
    print(f"  and phi_enfuse carries it: {l1['phi_e']:.5f} -> {l1p['phi_e']:.5f}"
          f", a {l1['phi_e'] / l1p['phi_e']:.1f}x collapse,")
    print(f"  against only {l1['phi_s'] / l1p['phi_s']:.1f}x in strehl.  At "
          "offset 9 the two halves are")
    print("  genuinely different SCENES (different focus), and enfuse -- which")
    print("  blends by local contrast -- reproduces that depth difference")
    print("  faithfully, inflating its own half-disagreement and dragging R")
    print("  toward 1.  Removing the depth difference is what makes strehl's")
    print("  residual disagreement stand out.")

    print("\n" + "=" * 108)
    print("THE CONTROLLED PAIR, which is the whole reason no ladder number is")
    print("reported:")
    print(f"  bee-L1   N=34  half-B  9 frames from half-A   R = {l1['R']:.3f}")
    print(f"  bee-L1P  N=34  half-B  1 frame  from half-A   R = {l1p['R']:.3f}")
    print(f"  ratio {l1p['R'] / l1['R']:.2f}x at IDENTICAL N, with half-A")
    print("  bit-identical between the two.  The L1-to-L4 range is 5.32x.")
    print("  A nuisance parameter moves the statistic further than the variable")
    print("  under test does, so R(N) on this subject is not a measurement of N.")
    print("\n  THE DEFECT IS IN THE DESIGN, NOT THE INSTRUMENT, AND IT IS")
    print("  FIXABLE: hold the offset at 1 on every rung.  bee-L1P (N=34) and")
    print("  bee-L4 (N=299) already satisfy that.  bee-L2 and bee-L3 must be")
    print("  rebuilt with -BOffset 1.  See PREREGISTRATION sec.12.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
