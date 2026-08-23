"""M55b E15 -- SYNTHESIS question 199: is a block-4 half-stack split inside the
roll-null?

PRE-REGISTERED as PR34 before this file was written.  Fact 861 put a contiguous
split inside the null on 6 of 6 cells and parity outside it.  Block-4 sits
between them on fact 705's leverage table (0.35870 against contiguous 0.99530)
and nobody has run the null on it.

COMPARABILITY IS THE POINT.  This file does not reimplement anything: it
imports e12_null, which produced fact 861, and reuses its `spec`, `canon_from`,
`mode_se`, `null_by_roll`, `load_cube`, `merge` and `STACKS` as the identical
objects.  Same 48 rolls, same minshift 64, same seed 5, same z convention
(value - mean_null) / sd_null, same six cells, same frame ranges.  e12_null.py
is NOT modified (rule 15) -- it is imported.

Decision rule, fixed in advance: INSIDE the null at |z| < 2.0, the threshold
e12 used verbatim for PR31.  The spec's own B9 gate is stricter at |z| >= 3.0
and is reported alongside so a reader may apply either.
"""
import os, sys, glob, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import e12_null as E12
import m41lib as L1

INSIDE = 2.0          # PR31's threshold, reused verbatim
B9_GATE = 3.0         # spec_v1 TH["b9_min_z"]

# fact 861, for the reproducibility check
F861_CONTIG = {("112MSDCF", "detail"): +0.53, ("112MSDCF", "flat"): +0.84,
               ("113MSDCF", "centre"): -1.25, ("113MSDCF", "flat"): +1.45,
               ("foam", "centre"): +1.91, ("foam", "flat"): +1.28}


def splits_for(nf):
    idx = np.arange(nf)
    h = nf // 2
    return {"parity": (idx[0::2], idx[1::2]),
            "block-4": (idx[(idx // 4) % 2 == 0], idx[(idx // 4) % 2 == 1]),
            "contiguous": (idx[:h], idx[h:2 * h])}


def main():
    res, t0 = {}, time.time()
    print("=" * 78)
    print("M55b E15 -- question 199: is a block-4 split inside the roll-null?  (PR34)")
    print("=" * 78)
    print("  Instrument imported from e12_null (fact 861).  48 rolls, minshift 64,")
    print("  seed 5, z = (value - mean_null) / sd_null.  INSIDE at |z| < 2.0.\n")
    hdr = ("   stack      ROI      split         C            sd(NULL)        z      verdict")
    print(hdr)
    rows = []
    for sname, cfg in E12.STACKS.items():
        files = sorted(glob.glob(os.path.join(r"D:\personal\macro", sname, "*.ARW")))
        files = files[cfg["lo"]:cfg["hi"]]
        for rname, roi in cfg["rois"].items():
            cube = E12.load_cube(files, roi)
            fine, coarse, reg = L1.focus_fields(cube, E12.G, E12.RN_E)
            nf = cube.shape[0]
            st = res.setdefault(f"{sname}|{rname}", {})
            for split, (ia, ib) in splits_for(nf).items():
                a, b = E12.merge(cube, coarse, reg, ia), E12.merge(cube, coarse, reg, ib)
                A, B = E12.spec(a), E12.spec(b)
                C = E12.canon_from(A, B)
                nul = E12.null_by_roll(a, b)
                sd = float(nul.std(ddof=1))
                z = (C - float(nul.mean())) / sd
                st[split] = dict(C=C, null_sd=sd, null_mean=float(nul.mean()),
                                 z=float(z), nf=int(nf),
                                 n_a=int(len(ia)), n_b=int(len(ib)))
                v = "INSIDE null" if abs(z) < INSIDE else "outside"
                print(f"   {sname:10s} {rname:8s} {split:11s} {C:+12.4e} {sd:12.4e}"
                      f" {z:+8.2f}   {v}")
                rows.append((sname, rname, split, float(z)))
            print()
            del cube, fine, coarse, reg

    cells = [k for k in res if "|" in k]

    print("=" * 78)
    print("  REPRODUCIBILITY CHECK -- contiguous z must reproduce fact 861")
    print("=" * 78)
    ok861 = True
    for k in cells:
        s, r = k.split("|")
        got, want = res[k]["contiguous"]["z"], F861_CONTIG[(s, r)]
        agree = abs(got - want) < 0.05
        ok861 = ok861 and agree
        print(f"   {s:10s} {r:8s} contiguous z = {got:+7.2f}   fact 861 {want:+7.2f}"
              f"   {'match' if agree else 'MISMATCH'}")
    print(f"   -> run is comparable to fact 861: {ok861}")

    print("\n" + "=" * 78)
    print("  PR34 -- where does block-4 sit?")
    print("=" * 78)
    n_in = sum(1 for k in cells if abs(res[k]["block-4"]["z"]) < INSIDE)
    n_b9 = sum(1 for k in cells if abs(res[k]["block-4"]["z"]) >= B9_GATE)
    for k in cells:
        s, r = k.split("|")
        zb, zp, zc = (res[k]["block-4"]["z"], res[k]["parity"]["z"],
                      res[k]["contiguous"]["z"])
        print(f"   {s:10s} {r:8s} contiguous {zc:+7.2f} | block-4 {zb:+8.2f} | "
              f"parity {zp:+9.2f}   block-4 {'INSIDE' if abs(zb) < INSIDE else 'outside'}")
    print(f"\n   block-4 INSIDE the null (|z| < {INSIDE}) in {n_in} of {len(cells)} cells")
    print(f"   block-4 passes the spec's B9 gate (|z| >= {B9_GATE}) in {n_b9} of {len(cells)} cells")
    if n_in == len(cells):
        verdict = ("ALL cells inside -- nullity is a property of BLOCK SIZE, not of "
                   "contiguity, so parity's own distance from the null is an assumption")
    elif n_in == 0:
        verdict = ("NO cell inside -- contiguity is doing something specific; parity "
                   "is safe and the family is bounded")
    else:
        verdict = (f"SPLIT VERDICT -- {n_in} of {len(cells)} cells inside.  Reported as "
                   "ambiguous by pre-registration; no side is picked.  The null boundary "
                   "depends on the cell, not on the split alone")
    print(f"   -> {verdict}")

    print("\n" + "=" * 78)
    print("  PR34 second observable -- is |z| ordered contiguous <= block-4 <= parity?")
    print("=" * 78)
    viol = []
    for k in cells:
        s, r = k.split("|")
        zc, zb, zp = (abs(res[k]["contiguous"]["z"]), abs(res[k]["block-4"]["z"]),
                      abs(res[k]["parity"]["z"]))
        good = zc <= zb <= zp
        if not good:
            viol.append(k)
        print(f"   {s:10s} {r:8s} |z| {zc:7.2f} <= {zb:8.2f} <= {zp:9.2f}   "
              f"{'ordered' if good else 'VIOLATION'}")
    print(f"\n   ordering violations: {len(viol)} of {len(cells)}  {viol}")
    if viol:
        print("   -> focus offset between paired halves is NOT the sole ordering variable;")
        print("      the continuum framing is wrong regardless of the in/out verdict")
    else:
        print("   -> ordering consistent with focus offset as the controlling variable")

    res["pr34"] = dict(n_inside=n_in, n_cells=len(cells), n_pass_b9=n_b9,
                       verdict=verdict, reproduces_861=bool(ok861),
                       ordering_violations=viol, inside_threshold=INSIDE)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "e15_block4_null.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\n   wrote out/e15_block4_null.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
