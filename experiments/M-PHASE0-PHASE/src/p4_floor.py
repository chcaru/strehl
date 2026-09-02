"""What registration accuracy is actually achievable, by span and field radius.

`p1_bar.py` derived what the unfolding NEEDS: about 0.10 sensor px (raw gauge) or
0.12 (gauge-fixed) at `kappa ~ 3`, `rho = 0.1`. This measures what the aligner
DELIVERS, so the two can be compared. That comparison is C1's go/no-go.

Two quantities, deliberately bracketing the truth from both sides:

  cycle floor   median corner disagreement of the raw pairwise measurements
                around a closed triple. `align.rs:2544` argues no reconciliation
                of mutually contradictory measurements can be right to much
                better than this. It is the OPTIMISTIC end, because a global
                solve averages many edges and can beat the per-edge noise.

  held-out      the solve's own prediction error on edges it did not fit,
                recorded in the sidecar by `strehl align`. It is the PESSIMISTIC
                end, because it also carries model error: a global 4-DOF
                similarity cannot represent whatever the true motion was.

If the optimistic end is already far above the bar, the pessimistic end cannot
rescue it, and no averaging argument is needed. That is the only case in which
this script settles anything on its own.

Both are resolved by SPAN, because within-DOF frames are 1 to 8 apart while the
shipped pooled figure averages over spans up to 128, and by FIELD RADIUS, because
a similarity's error grows linearly with distance from the plane centre while the
census reports by radius (section 6.1).

Output: out/p4_floor.json
"""

import json
import os
import sys

import numpy as np

import flib

EDGES = os.path.join(os.path.dirname(__file__), "..", "out", "edges")
CANON = os.path.join(os.path.dirname(__file__), "..", "out", "canon")
OUT = os.path.join(os.path.dirname(__file__), "..", "out", "p4_floor.json")

# Ten equal-area annuli over the plane disc, reported at their mid-radius, as
# registered in section 6.1.  Fraction of the plane half-diagonal.
RFRAC = [float(np.sqrt((m + 0.5) / 10.0)) for m in range(10)]

# The bar from out/p1_bar.json, G-1x, rho = 0.1, sensor px.  Both gauge reads.
BAR_RAW, BAR_ZM = 0.1006, 0.1231

WITHIN_DOF = 8  # frames within one depth of field are at most this far apart


def summarise(stack, path):
    edges = flib.load_edges(path)
    plane = flib.plane_of(path)
    rc = flib.corner_radius(plane)
    radii = [f * rc for f in RFRAC]
    r = flib.cycle_errors(edges, plane, radii=radii)
    if not len(r["err"]):
        return None
    out = dict(stack=stack, plane=list(plane), n_triples=int(len(r["err"])),
               corner_radius_plane=rc, rfrac=RFRAC, by_span={}, by_radius={})

    for s in sorted(set(int(v) for v in r["span"])):
        sel = r["span"] == s
        if sel.sum() < 3:
            continue
        out["by_span"][str(s)] = dict(
            n=int(sel.sum()),
            median=float(np.median(r["err"][sel])),
            p90=float(np.percentile(r["err"][sel], 90)),
            median_sensor=float(flib.to_sensor(np.median(r["err"][sel]))),
            scale_part=float(np.median(r["err_scale"][sel])),
            trans_part=float(np.median(r["err_trans"][sel])),
        )

    dof = r["span"] <= WITHIN_DOF
    if dof.sum() >= 3:
        at = r["at_radius"][dof]
        out["by_radius"] = dict(
            n=int(dof.sum()),
            median_sensor=[float(flib.to_sensor(np.median(at[:, i])))
                           for i in range(at.shape[1])],
            p90_sensor=[float(flib.to_sensor(np.percentile(at[:, i], 90)))
                        for i in range(at.shape[1])],
        )
    return out


def main():
    if not os.path.isdir(EDGES):
        print("no edge sets in %s" % EDGES)
        return 1
    stacks = {}
    for f in sorted(os.listdir(EDGES)):
        if not f.endswith(".csv"):
            continue
        s = summarise(f[:-4], os.path.join(EDGES, f))
        if s:
            stacks[f[:-4]] = s

    # Held-out error from the canonical sidecars, the pessimistic bracket.
    held = {}
    if os.path.isdir(CANON):
        import clib
        for f in sorted(os.listdir(CANON)):
            if not f.endswith(".warpmap.txt"):
                continue
            h = clib.parse_warpmap(os.path.join(CANON, f))["header"]
            for k, key in (("heldout-px", "heldout"), ("cycle-floor-px", "cyclefloor")):
                v = h.get(k, "none")
                val = float(v.split("#")[-1]) if "#" in v else None
                held.setdefault(f[:-len(".warpmap.txt")], {})[key] = val

    payload = dict(stacks=stacks, heldout=held, bar_raw=BAR_RAW, bar_zm=BAR_ZM,
                   within_dof=WITHIN_DOF, rfrac=RFRAC)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1)

    report(stacks, held)
    print("\nwrote %s" % os.path.normpath(OUT))
    return 0


def report(stacks, held):
    print("\ncycle-consistency floor by span, SENSOR px")
    print("(the optimistic end: raw measurement self-consistency, no solver)")
    print("-" * 84)
    spans = ["1", "2", "3", "4", "6", "8", "16", "32"]
    print("  %-15s %s" % ("stack", "".join("%9s" % s for s in spans)))
    for s, d in stacks.items():
        line = "  %-15s" % s
        for sp in spans:
            v = d["by_span"].get(sp)
            line += "%9s" % ("%.4f" % v["median_sensor"] if v else "-")
        print(line)

    print("\n  bar to beat: %.4f sensor px (raw gauge) / %.4f (gauge-fixed)"
          % (BAR_RAW, BAR_ZM))

    print("\nratio of achievable floor to the bar, at span<=8, SENSOR px")
    print("-" * 84)
    print("  %-15s %10s %10s %10s %12s" % ("stack", "floor", "/bar_raw", "/bar_zm",
                                           "heldout px"))
    worst = []
    for s, d in stacks.items():
        vals = [v["median_sensor"] for k, v in d["by_span"].items()
                if int(k) <= WITHIN_DOF]
        if not vals:
            continue
        f = float(np.median(vals))
        worst.append(f)
        ho = held.get(s, {}).get("heldout")
        print("  %-15s %10.4f %10.1fx %10.1fx %12s"
              % (s, f, f / BAR_RAW, f / BAR_ZM,
                 "%.3f" % (ho * flib.PLANE_TO_SENSOR) if ho else "not measured"))
    if worst:
        print("\n  median over stacks: %.4f sensor px = %.1fx the raw bar, %.1fx gauge-fixed"
              % (np.median(worst), np.median(worst) / BAR_RAW,
                 np.median(worst) / BAR_ZM))

    print("\nfloor by field radius (span<=8), SENSOR px, 10 equal-area annuli")
    print("-" * 84)
    print("  %-15s %s" % ("stack", "".join("%7.2f" % f for f in RFRAC)))
    for s, d in stacks.items():
        if not d["by_radius"]:
            continue
        print("  %-15s %s" % (s, "".join("%7.3f" % v
                                         for v in d["by_radius"]["median_sensor"])))


if __name__ == "__main__":
    sys.exit(main())
