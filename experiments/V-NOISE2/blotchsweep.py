"""blotchsweep -- WHY the BLOTCH commissioning arm failed on 10 of the 18
failing rung/band cells, and whether that failure is potency or ceiling.

THIS IS A POST-HOC DIAGNOSTIC OF A PRE-REGISTERED ARM'S FAILURE.  It is not a
new pre-registered measurement and no verdict is moved by it.  The BLOTCH arm
still failed and is still reported as having failed.

THE SUSPICION, from reading incoh.py rather than from the numbers.  sec.9.6
established that a FIXED plant amplitude is wrong across bands, because the
COARSE annulus captures 10x less white noise than FINE, and it fixed that for
the NOISE-INC arm by DERIVING beta per band in plant_beta().  BLOTCH was left
on the module constant:

    ("NOISE-INC", "RISE", mut_noise_inc(beta)),   <- derived per band
    ("BLOTCH",    "rise", mut_blotch(BETA)),      <- fixed 0.020

So the same defect sec.9.6 named was fixed on one arm and not the other, and
the ladder -- which moves the baseline phi over two orders of magnitude,
0.00997 at L4 to 0.95322 at L3 -- is the first thing that could expose it.

TWO RIVAL EXPLANATIONS, which this file separates by measurement.

  POTENCY.  The fixed plant is simply too weak RELATIVE to that rung's larger
  baseline disagreement.  PREDICTS: raising the plant amplitude recovers a
  >5% response, so the arm is commissionable at that rung and only the
  amplitude was wrong.

  CEILING.  mut_blotch replaces patches with a BLURRED COPY of the same half,
  under a mask that saturates to 0/1 as beta grows.  Its effect on phi is
  therefore BOUNDED: past some amplitude the mask is already binary and more
  beta buys nothing.  If the baseline disagreement is already large, no
  amplitude may reach +5%.  PREDICTS: d_phi saturates below the gate and the
  arm CANNOT be commissioned at that rung at any potency -- which is a real
  limitation of the sec.9 statistic and qualifies sec.9 itself.

COMMISSIONING OF THIS DIAGNOSTIC.  A sweep that always finds a response would
prove nothing.  bee-L4/COARSE is the cell where the committed BLOTCH arm
PASSED, so the sweep must reproduce a >5% response there at the committed
beta = 0.020.  If it does not, the sweep is not reading the same thing the
harness read and its other rows are worthless.  That check is asserted, and a
failure of it exits non-zero.

    python blotchsweep.py
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import incoh as I                                                # noqa: E402
import ladder_run as L                                           # noqa: E402

RUNGS = ("bee-L1", "bee-L1P", "bee-L2", "bee-L2P", "bee-L3", "bee-L3P",
         "bee-L4")
SUBJECTS = ("119", "113")
BETAS = (0.020, 0.05, 0.10, 0.20, 0.40, 0.80, 1.60, 3.20)
GATE = 0.05
SEED = 11


def det_pairs(rung):
    """strehl half-A vs half-B over the DETAIL tile population.

    Replicates ladder_run.measure's selection EXACTLY -- same census file,
    same 'top |emax| tiles, as many as there are FLAT tiles' rule, same
    placer=None for the half comparison.  If this drifts from measure(), the
    sweep is not diagnosing the numbers that were reported.
    """
    P, _ge, man, z = L.load_rung(rung)
    cells, emax = z["cells"], z["emax"]
    flat = [int(i) for i in z["flat"]]
    det = [int(i) for i in np.argsort(emax)[-len(flat):]]
    DET = [tuple(cells[i]) for i in det]
    sA = L.Comp(dict(path=P["sA"], weights=I.W))
    sB = L.Comp(dict(path=P["sB"], weights=I.W))
    return I.pairs(sA, sB, DET), man


def subject_pairs(key):
    """strehl half-A vs half-B for a PLAIN subject (119, 113), not a rung.

    Mirrors incoh.main's own loading: geom-full.json rather than geom.json,
    and the identical DETAIL selection.  This exists because the ladder's
    BLOTCH failures raise the question of whether sec.9's OWN reading on 119
    was commissioned, and that question must be answered by measurement on
    119 rather than by pointing at the earlier run's pass.
    """
    arm = os.path.join(L.hd2.ROOT, key, "arms")
    z = np.load(os.path.join(L.hd2.ROOT, key, "census.npz"))
    cells, emax = z["cells"], z["emax"]
    flat = [int(i) for i in z["flat"]]
    det = [int(i) for i in np.argsort(emax)[-len(flat):]]
    DET = [tuple(cells[i]) for i in det]
    sA = L.Comp(dict(path=os.path.join(arm, "strehl-A.tiff"), weights=I.W))
    sB = L.Comp(dict(path=os.path.join(arm, "strehl-B.tiff"), weights=I.W))
    return I.pairs(sA, sB, DET)


def sweep(prs, band):
    """(baseline phi, [d_phi at each BETAS]) or (phi, None) if degenerate."""
    b_ph, b_am, _ = I.phi_of(prs, band)
    b_phi = float(np.median(b_ph))
    b_amp = float(np.median(b_am))
    if not (b_amp > 0) or b_phi >= 1.0:
        return b_phi, None
    ds = []
    for beta in BETAS:
        ph, _am, _rh = I.phi_of(prs, band, mutate=I.mut_blotch(beta),
                                rng=np.random.default_rng(SEED))
        ds.append(float(np.median(ph)) / b_phi - 1.0)
    return b_phi, ds


def verdict_of(ds):
    if ds is None:
        return "DEGENERATE"
    best = max(ds)
    if ds[0] > GATE:
        return "PASSES at committed beta"
    if best > GATE:
        nb = BETAS[int(np.argmax(np.array(ds) > GATE))]
        return f"POTENCY: recovers at beta {nb:.2f}"
    return f"CEILING: max {best:+.1%} at any potency"


def main():
    print("=" * 100)
    print("BLOTCHSWEEP -- is the BLOTCH arm's failure POTENCY or CEILING?")
    print("=" * 100)
    print(f"  committed plant amplitude: incoh.BETA = {I.BETA}")
    print(f"  gate the arm must clear:   d_phi > {GATE:+.0%}")

    rows = {}
    for rung in RUNGS:
        prs, _man = det_pairs(rung)
        for bname, band in I.BANDS:
            rows[(rung, bname)] = sweep(prs, band)
        del prs
    for key in SUBJECTS:
        if not os.path.exists(os.path.join(L.hd2.ROOT, key, "census.npz")):
            print(f"  NOTE: subject {key} has no census.npz -- skipped, and it "
                  f"is NOT counted as a pass.")
            continue
        prs = subject_pairs(key)
        for bname, band in I.BANDS:
            rows[(key, bname)] = sweep(prs, band)
        del prs
    have_sub = [k for k in SUBJECTS if (k, I.BANDS[0][0]) in rows]

    keys = list(RUNGS) + have_sub
    for bname, _band in I.BANDS:
        print(f"\n  {bname}")
        hdr = "  ".join(f"{b:>7.2f}" for b in BETAS)
        print(f"  {'key':9s} {'base phi':>9s}  {hdr}   verdict")
        for k in keys:
            b_phi, ds = rows[(k, bname)]
            if have_sub and k == have_sub[0]:
                print(f"  {'-' * 96}")
            if ds is None:
                print(f"  {k:9s} {b_phi:9.5f}  "
                      f"{'band degenerate, no baseline to plant against':<70s}")
                continue
            cells_ = "  ".join(f"{d:+7.1%}" for d in ds)
            print(f"  {k:9s} {b_phi:9.5f}  {cells_}   {verdict_of(ds)}")

    print("\n" + "=" * 100)
    print("COMMISSIONING OF THIS SWEEP")
    ok = True
    b_phi, ds = rows[("bee-L4", "COARSE")]
    if ds is not None and ds[0] > GATE:
        print("  bee-L4/COARSE is the cell where the committed BLOTCH arm")
        print(f"  PASSED.  This sweep reads {ds[0]:+.1%} there at the committed")
        print(f"  beta = {I.BETA}, clearing the same {GATE:+.0%} gate.  The sweep")
        print("  is reading what the harness read.")
    else:
        ok = False
        print("  FAILED: bee-L4/COARSE does not reproduce the harness's pass.")
        print("  This sweep is NOT reading what the harness read; its other")
        print("  rows are worthless and no conclusion is drawn from them.")

    print("\n  DOES THIS TOUCH sec.9?  sec.9's R = 12.424 was measured on 119.")
    if "119" in have_sub:
        for bname, _band in I.BANDS:
            b_phi, ds = rows[("119", bname)]
            print(f"    119/{bname:6s} baseline phi {b_phi:.5f}  ->  "
                  f"{verdict_of(ds)}")
    else:
        ok = False
        print("    119 COULD NOT BE READ, so this question is UNANSWERED and")
        print("    sec.9 is neither confirmed nor cleared here.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
