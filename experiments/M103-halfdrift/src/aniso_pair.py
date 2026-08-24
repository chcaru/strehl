"""M103: PAIRED before/after run of the orchestrator's anisotropy instrument.

WHY THIS EXISTS, AND WHY IT IS NOT A REBUILD
--------------------------------------------
The orchestrator asked me to use `experiments/ORCH-drift-check/anisotropy.py`
and not to rebuild it. I am not rebuilding it: this file imports that module and
calls its `measure()` unmodified. Every number below is computed by the
orchestrator's code.

What this adds is PAIRING, using the `tile_keys` argument that `measure()`
already exposes for exactly this purpose.

The instrument's own docstring explains why pairing matters, and it is emphatic:

    "The first version re-derived the texture threshold inside each arm. A
     planted radial smear destroys power in exactly the outer tiles it acts on
     hardest, so those tiles fell below the per-arm quantile and were dropped --
     leaving a survivor set enriched for tiles the plant had failed to affect.
     The sensitivity control consequently read 0.5268 -> 0.5294 for a 150 px
     smear that should have flattened the outer annuli. The selection must not
     be allowed to depend on the treatment."

`controls()` obeys that rule. The multi-file path in `__main__` does NOT: it
calls `measure(y, basename(p))` with `tile_keys=None` for each file, so every
file re-derives its own 35th-percentile texture threshold. For a gate ladder,
where all arms are the same solve, that is a minor effect. For a before/after
comparison of two DIFFERENT solves it is the very failure mode quoted above,
with the sign reversed: my fix ADDS high-frequency power at large radius, so an
unpaired run lets the after-arm admit outer tiles the before-arm rejected, and
the two A(r) curves are then computed over different subjects.

So this script reports BOTH: the paired numbers (primary) and the stock unpaired
numbers (for comparability with the orchestrator's gate ladder), and prints the
disagreement between them so nobody has to take my word for which matters.

GEOMETRIC PRECONDITION, CHECKED NOT ASSUMED
-------------------------------------------
Pairing tiles by (ty, tx) is only meaningful if tile (ty, tx) shows the same
subject content in both renders. That holds here because both renders use the
SAME reference frame (0) and therefore the same output canvas and the same
magnification; only the placement of frames 1..298 differs. The script verifies
this by reporting the global normalised cross-correlation of the two frames --
if the two renders had different effective magnification, that would fall well
below 1 and the pairing would be void.

ARMS
  paired      before/after on the tile set pinned to `before`
  pinned-after  same, pinned to `after`   (robustness: the answer must not
                depend on which arm pins the set)
  PLACEBO     before vs before, paired -- must be bit-identical, A ratio 1.0000
  unpaired    the stock __main__ behaviour, for comparison

USAGE
  python aniso_pair.py <before.tif> <after.tif> <controls.json|-> <out.json>
"""

import importlib.util
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ANISO = os.path.normpath(os.path.join(HERE, "..", "..", "ORCH-drift-check",
                                      "anisotropy.py"))

CLUST_MAX = 0.30  # the orchestrator's own threshold, from aniso_px.py


def load_instrument():
    if not os.path.exists(ANISO):
        sys.exit(f"instrument not found: {ANISO}")
    spec = importlib.util.spec_from_file_location("orch_anisotropy", ANISO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def annulus_map(m):
    return {round(a["r_mid"], 6): a for a in m["annuli"]}


def invert_dose(pts, a_val):
    """Piecewise-linear inverse of a monotone-decreasing dose->A curve.

    Lifted in behaviour from the orchestrator's aniso_px.py so the px numbers
    here are on the same ruler as theirs.
    """
    d = [p[0] for p in pts]
    v = [p[1] for p in pts]
    if a_val >= v[0]:
        return 0.0
    if a_val <= v[-1]:
        return float("inf")
    for i in range(len(v) - 1):
        if v[i] >= a_val >= v[i + 1]:
            t = (v[i] - a_val) / (v[i] - v[i + 1])
            return d[i] + t * (d[i + 1] - d[i])
    return float("nan")


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    before_p, after_p, ctrl_p, out_p = sys.argv[1:5]
    A = load_instrument()

    yb = A.load_luma(before_p)
    ya = A.load_luma(after_p)
    if yb.shape != ya.shape:
        sys.exit(f"shape mismatch {yb.shape} vs {ya.shape}: not comparable")

    # --- geometric precondition -------------------------------------------
    b64 = yb.astype(np.float64)
    a64 = ya.astype(np.float64)
    bz, az = b64 - b64.mean(), a64 - a64.mean()
    ncc = float((bz * az).sum() / np.sqrt((bz ** 2).sum() * (az ** 2).sum()))
    del b64, a64, bz, az
    print(f"before: {os.path.basename(before_p)}  {yb.shape}")
    print(f"after : {os.path.basename(after_p)}  {ya.shape}")
    print(f"global NCC(before, after) = {ncc:.6f}")
    print("  (pairing tiles by (ty,tx) requires the two renders to share a")
    print("   canvas and magnification; a value near 1 confirms they do)")
    if ncc < 0.90:
        print("  WARNING: low NCC -- the renders may not share geometry.")
    print()

    # --- pin the tile set on `before` (the untreated / shipped arm) --------
    base = A.measure(yb, "before")
    keys = set(base["keys"])
    print(f"tile set pinned on BEFORE: {len(keys)} tiles")
    after_paired = A.measure(ya, "after", keys)

    # robustness: pin on the other arm
    base_a = A.measure(ya, "after-pin")
    keys_a = set(base_a["keys"])
    before_pinA = A.measure(yb, "before", keys_a)
    print(f"tile set pinned on AFTER : {len(keys_a)} tiles "
          f"({len(keys & keys_a)} shared)")

    # placebo: before vs before on the same pinned set
    placebo = A.measure(yb, "placebo", keys)

    # stock unpaired behaviour
    before_un = base
    after_un = A.measure(ya, "after-unpaired")

    ctrl = None
    if ctrl_p != "-" and os.path.exists(ctrl_p):
        ctrl = json.load(open(ctrl_p))

    mb, ma = annulus_map(base), annulus_map(after_paired)
    m_pl = annulus_map(placebo)
    m_bA, m_aA = annulus_map(before_pinA), annulus_map(base_a)
    m_un = annulus_map(after_un)

    print()
    print("PAIRED (tile set pinned on BEFORE).  A -> 1.0 is correct geometry.")
    print(f"  {'r':>5} {'clust':>6} {'A_before':>9} {'A_after':>9} {'delta':>8} "
          f"{'placebo':>8} {'use?':>5}")
    rows = []
    for r in sorted(mb):
        if r not in ma:
            continue
        b, a = mb[r], ma[r]
        pl = m_pl.get(r)
        clust = b["angular_clustering"]
        use = clust <= CLUST_MAX
        d = a["A"] - b["A"]
        rows.append({
            "r_mid": r, "angular_clustering": clust, "usable": use,
            "A_before": b["A"], "A_after": a["A"], "delta": d,
            "ci_before": b["ci"], "ci_after": a["ci"],
            "n_tiles": b["n_tiles"],
            "A_placebo": (pl["A"] if pl else None),
            "A_before_pinAfter": (m_bA[r]["A"] if r in m_bA else None),
            "A_after_pinAfter": (m_aA[r]["A"] if r in m_aA else None),
            "A_after_unpaired": (m_un[r]["A"] if r in m_un else None),
        })
        print(f"  {r:>5.2f} {clust:>6.3f} {b['A']:>9.4f} {a['A']:>9.4f} "
              f"{d:>+8.4f} {(pl['A'] if pl else float('nan')):>8.4f} "
              f"{'yes' if use else 'NO':>5}")

    # --- placebo bar -------------------------------------------------------
    pl_max = max((abs(r["A_placebo"] - r["A_before"])
                  for r in rows if r["A_placebo"] is not None), default=0.0)
    print()
    print(f"PLACEBO (before vs before, same tiles): max |dA| = {pl_max:.2e} "
          f"-- {'PASS' if pl_max < 1e-9 else 'FAIL'}")

    # --- pinning robustness ------------------------------------------------
    dif = [abs((r["A_after_pinAfter"] - r["A_before_pinAfter"]) - r["delta"])
           for r in rows
           if r["usable"] and r["A_after_pinAfter"] is not None
           and r["A_before_pinAfter"] is not None]
    if dif:
        print(f"PIN ROBUSTNESS: max change in delta when pinning on the other "
              f"arm = {max(dif):.4f}")

    # --- unpaired disagreement --------------------------------------------
    dun = [abs((r["A_after_unpaired"] - r["A_before"]) - r["delta"])
           for r in rows if r["usable"] and r["A_after_unpaired"] is not None]
    if dun:
        print(f"UNPAIRED BIAS : max |delta_unpaired - delta_paired| = "
              f"{max(dun):.4f}  (this is what the stock __main__ path would "
              f"have reported)")

    # --- the built-in null -------------------------------------------------
    inner = [r for r in rows if r["r_mid"] < 0.25]
    if inner:
        print(f"BUILT-IN NULL : A_before(centre) = "
              f"{np.mean([r['A_before'] for r in inner]):.4f}, "
              f"A_after(centre) = "
              f"{np.mean([r['A_after'] for r in inner]):.4f}  "
              f"(geometry forbids a scale-induced change here)")

    # --- px conversion via the orchestrator's dose curve -------------------
    px_rows = []
    if ctrl:
        doses = {"identity": 0.0, "radial 1px@corner": 1.0,
                 "radial 3px@corner": 3.0, "radial 10px@corner": 10.0}
        print()
        print("Residual radial displacement, px AT THE CORNER, by inverting the")
        print("planted dose curve at the same radius (upper bounds, not")
        print("estimates -- subject anisotropy inflates both rows equally, so")
        print("the DIFFERENCE is the defensible quantity):")
        print(f"  {'r':>5} {'px_before':>10} {'px_after':>10} {'improvement':>12}")
        for r in sorted(mb):
            if not any(x["r_mid"] == r and x["usable"] for x in rows):
                continue
            pts = []
            for name, dose in doses.items():
                if name not in ctrl:
                    continue
                am = annulus_map(ctrl[name])
                if r in am:
                    pts.append((dose, am[r]["A"]))
            pts.sort()
            if len(pts) < 2:
                continue
            pb = invert_dose(pts, mb[r]["A"])
            pa = invert_dose(pts, ma[r]["A"])
            px_rows.append({"r_mid": r, "px_before": pb, "px_after": pa,
                            "improvement_px": pb - pa})
            print(f"  {r:>5.2f} {pb:>10.2f} {pa:>10.2f} {pb - pa:>+12.2f}")

    json.dump({
        "before": before_p, "after": after_p, "global_ncc": ncc,
        "n_tiles_pinned_before": len(keys), "n_tiles_pinned_after": len(keys_a),
        "placebo_max_abs_delta": pl_max,
        "annuli": rows, "px": px_rows,
    }, open(out_p, "w"), indent=1)
    print(f"\nwrote {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
