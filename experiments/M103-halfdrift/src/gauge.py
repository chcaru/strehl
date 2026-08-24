"""M103b -- score the candidate solves in the gauge the MERGE ACTUALLY USES.

`edgeset.py` produced two columns that disagree about which solve is better:

    variant                abs_mean   shape_mean
    IWW-nofan-noovershoot      49.2         28.8
    SHIPPED                    39.4         36.4

`abs` is gauged at frame 0; `shape` removes a constant offset. The difference is
not a statistical nicety -- it is a *gauge*, and which one reaches the photograph
depends on the frame the merge warps everything to. The shipped
`bee-3-cpl/warpmap.txt` header says `reference 149`, so the operative gauge is
mid-stack, not frame 0.

A placement error that is a constant offset on frames 1..298 relative to frame 0
costs one frame out of 299 when the merge references mid-stack, and costs all 298
of them when it references frame 0. So this script re-gauges both the truth
ladder and each solve to a COMMON rung and re-scores. No re-solving, no
re-measuring: the same tracks, read in the gauge the merge uses.

Controls:
  PLACEBO   gauge the truth ladder against itself at every rung -- must be
            identically 0 px in every gauge.
  POSITIVE  plant a known constant offset of +0.02 ln on a copy of the truth
            ladder. Gauged at frame 0 it must read 0.02*R_PLANE = 42.3 px on
            every rung but rung 0; re-gauged to any interior rung it must read
            ~0. That is the whole claim of this script, on a case where the
            answer is known in closed form.
  SANITY    re-gauging must not change the SPREAD of the errors, only their
            offset. Reported as the max-minus-min, which is gauge-invariant.

usage:
  python src/gauge.py data/truth-dense.json data/edgeset.json data/gauge.json
"""

import json
import math
import os
import struct
import sys

R_PLANE = 0.5 * math.hypot(3516.0, 2344.0)
OUT = r"C:\dev\strehl-out\M103"


def read_sidecar(path):
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            f = line.split()
            if len(f) > 5 and f[1] in ("placed", "held"):
                try:
                    idx = int(f[0])
                except ValueError:
                    continue
                a = struct.unpack(">d", bytes.fromhex(f[2]))[0]
                b = struct.unpack(">d", bytes.fromhex(f[3]))[0]
                m = math.hypot(a, b)
                if m > 0:
                    out[idx] = math.log(m)
    return out


def errs(track, truth, gauge):
    """Placement error in plane px with both tracks re-gauged to rung `gauge`."""
    rungs = sorted(truth)
    if gauge not in track or gauge not in truth:
        return None
    return {
        j: ((track[j] - track[gauge]) - (truth[j] - truth[gauge])) * R_PLANE
        for j in rungs
        if j in track
    }


def stat(e):
    v = list(e.values())
    a = [abs(x) for x in v]
    return {
        "mean": sum(a) / len(a),
        "median": sorted(a)[len(a) // 2],
        "max": max(a),
        "rms": math.sqrt(sum(x * x for x in v) / len(v)),
        "spread": max(v) - min(v),
    }


def main():
    truth_path, edgeset_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    truth = {
        int(k): v["ln"]
        for k, v in json.load(open(truth_path, encoding="utf-8"))["ladder"].items()
    }
    es = json.load(open(edgeset_path, encoding="utf-8"))
    rungs = sorted(truth)

    arms = {}
    for name, r in es.items():
        if isinstance(r, dict) and r.get("sidecar") and os.path.exists(r["sidecar"]):
            arms[name] = read_sidecar(r["sidecar"])
    arms["SHIPPED"] = read_sidecar(os.path.join(OUT, "wm-baseline-r0.txt"))
    arms.pop("SHIPPED (reference)", None)

    # ---- CONTROLS -------------------------------------------------------
    print("CONTROLS")
    ok = True
    pl = max(abs(v) for v in errs(truth, truth, 144).values())
    print("  PLACEBO  truth vs truth, gauged at 144: max %.3e px -> %s"
          % (pl, "PASS" if pl < 1e-9 else "FAIL"))
    ok &= pl < 1e-9

    planted = {j: v + (0.02 if j != 0 else 0.0) for j, v in truth.items()}
    e0 = errs(planted, truth, 0)
    e144 = errs(planted, truth, 144)
    at0 = sum(abs(v) for j, v in e0.items() if j != 0) / (len(e0) - 1)
    at144 = max(abs(v) for v in e144.values() if abs(v) > 0) if any(
        abs(v) > 0 for v in e144.values()) else 0.0
    want = 0.02 * R_PLANE
    p1 = abs(at0 - want) < 0.05
    # gauged at an interior rung the planted constant cancels for every frame
    # except frame 0, which is the one frame that did not receive it
    p2 = max(abs(v) for j, v in e144.items() if j != 0) < 1e-9
    print("  POSITIVE planted +0.02 ln on frames 1..298:")
    print("           gauged at 0   -> %.1f px (closed form %.1f) -> %s"
          % (at0, want, "PASS" if p1 else "FAIL"))
    print("           gauged at 144 -> %.3e px on frames 1..298   -> %s"
          % (max(abs(v) for j, v in e144.items() if j != 0), "PASS" if p2 else "FAIL"))
    print("           (so a whole-graph offset IS a gauge artefact, by construction)")
    ok &= p1 and p2
    print("  -> controls %s\n" % ("PASS" if ok else "FAIL"))
    if not ok:
        return 1

    # ---- the real arms, in three gauges ---------------------------------
    order = ["SHIPPED", "IWW-all", "IWW-nofan", "IWW-noovershoot",
             "IWW-nofan-noovershoot", "IWW-no12", "IWW-rule6", "PLACEBO-drop1pct"]
    gauges = [0, 144, 298]
    res = {}
    print("Per-frame placement error, plane px at the corner, 39 rungs.")
    print("`spread` is max-minus-min and is GAUGE-INVARIANT: it is the part of the")
    print("error no choice of reference frame can remove.")
    print()
    hdr = "  %-24s" % "arm"
    for g in gauges:
        hdr += " | %s" % ("gauge %-3d  mean   max" % g)
    print(hdr + " |   spread")
    for name in order:
        if name not in arms:
            continue
        row = "  %-24s" % name
        rec = {}
        for g in gauges:
            e = errs(arms[name], truth, g)
            if e is None:
                row += " |      -      -      "
                continue
            s = stat(e)
            rec["gauge_%d" % g] = s
            row += " |          %6.1f %6.1f" % (s["mean"], s["max"])
        row += " |  %7.1f" % rec["gauge_0"]["spread"]
        res[name] = rec
        print(row)

    print()
    print("SANITY  spread must be identical in every gauge (it is a difference of")
    print("        differences). Max deviation across gauges, per arm:")
    worst = 0.0
    for name, rec in res.items():
        sp = [rec[k]["spread"] for k in rec]
        worst = max(worst, max(sp) - min(sp))
    print("        %.3e px -> %s" % (worst, "PASS" if worst < 1e-6 else "FAIL"))

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"arms": res, "controls": {"placebo_px": pl, "positive_gauge0_px": at0,
                                             "positive_closed_form_px": want}},
                  fh, indent=1, sort_keys=True)
    print("\nwrote " + out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
