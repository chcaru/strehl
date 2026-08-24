"""M103b -- which EDGES put 22% of the drift into the frame 0 -> 1 step?

`placement.py` established that M103's shipped `iterated_wide` solve carries a
spurious constant offset on frame 0 of ln -0.034, and that removing it takes the
solve from 98.2 px mean placement error to 40.2 px (max 138.3 -> 71.9 px).

This script asks *which subset of edges* causes it, by re-solving the SAME
committed edge measurements (`data/IWW-edges.csv`, 2521 rows produced by the
1096 s `iterated-wide` measure run) with different edge sets, through the REAL
solver (`m103probe solve` -> `strehl_core::align::solve_global`). Nothing is
re-measured, so any difference between variants is attributable to the edge set
alone.

Controls, per house rule (no null-only runs):

  WIRING   variant `IWW-all` is the unfiltered edge set and must reproduce the
           committed `wm-iww-r0.txt` track to ~1e-12. If it does not, the
           filter/solve invocation differs from the one that produced the
           published sidecar and no other row here means anything.
  PLACEBO  variant `PLACEBO-drop1pct` drops a deterministic 1% of edges NOT
           incident on frame 0. A real edge-set effect must be much larger than
           this.
  POSITIVE `placement.py` already showed the scoring metric can be nulled by a
           gain search on a genuinely uniform plant (recovers 1.8416 for a
           planted 0.543, residual 0.000 px).

Scoring is per-frame placement error in plane px at the corner, against
`data/truth-dense.json` -- 39 rungs of an independent RAW ladder with no strehl
code in its measurement path. Two numbers per variant:

  abs    mean |solve(j) - truth(j)| * R_PLANE, both gauged at frame 0
  shape  the same after removing the best constant offset, i.e. the error that
         is NOT a whole-graph gauge shift

usage:
  python src/edgeset.py data/IWW-edges.csv data/truth-dense.json data/edgeset.json
"""

import json
import math
import os
import struct
import subprocess
import sys

R_PLANE = 0.5 * math.hypot(3516.0, 2344.0)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.abspath(
    os.path.join(HERE, "..", "..", ".cargo-target-m103-probe", "release", "m103probe.exe")
)
OUT = r"C:\dev\strehl-out\M103"
EDIR = os.path.join(OUT, "edges")
SDIR = os.path.join(OUT, "es")
DIGEST_DIR = r"D:\personal\macro\bee-3-cpl"

# the span ladder the `measure` run was asked for. Every (i,j) with j-i in this
# set is a ladder edge; every other edge incident on frame 0 came from
# `--anchor-from 0 --anchor-stride 8`, i.e. the anchor fan.
LADDER = {1, 2, 4, 8, 16, 32, 64, 96, 128, 192, 256, 298}
# spans M103's own report Section 6 flagged as over-shooting (recovery 1.25-1.33 on
# only 10-15 surviving tiles) and called "unexplained and may be false peaks".
OVERSHOOT = {192, 256, 298}
SHORT = {1, 2}  # rule 6: "discard spans 1-2 from the solve"


def read_csv(path):
    head, rows = [], []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or line.startswith("i,j,span"):
                head.append(line)
                continue
            if not line.strip():
                continue
            f = line.split(",")
            rows.append((int(f[0]), int(f[1]), int(f[2]), line))
    return head, rows


def is_fan(i, j, span):
    """An edge produced by the frame-0 anchor fan rather than the span ladder."""
    return i == 0 and span not in LADDER


VARIANTS = {
    # name                     predicate(i, j, span) -> keep?
    "IWW-all": lambda i, j, s: True,
    "IWW-nofan": lambda i, j, s: not is_fan(i, j, s),
    "IWW-no12": lambda i, j, s: s not in SHORT,
    "IWW-noovershoot": lambda i, j, s: s not in OVERSHOOT,
    "IWW-nofan-noovershoot": lambda i, j, s: not is_fan(i, j, s) and s not in OVERSHOOT,
    "IWW-rule6": lambda i, j, s: s not in SHORT and not is_fan(i, j, s),
    "IWW-clean": lambda i, j, s: (
        s not in SHORT and s not in OVERSHOOT and not is_fan(i, j, s)
    ),
}


def placebo(rows):
    """Deterministic 1% of edges NOT incident on frame 0, dropped."""
    keep, n = [], 0
    for i, j, s, line in rows:
        if i != 0:
            n += 1
            if n % 100 == 0:
                continue
        keep.append((i, j, s, line))
    return keep


def solve(name, head, rows, reference=0):
    os.makedirs(EDIR, exist_ok=True)
    os.makedirs(SDIR, exist_ok=True)
    cpath = os.path.join(EDIR, name + ".csv")
    tmp = cpath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.writelines(head)
        fh.writelines(r[3] for r in rows)
    os.replace(tmp, cpath)  # M97's torn-read hazard: write then rename
    spath = os.path.join(SDIR, name + ".txt")
    cmd = [
        PROBE, "solve",
        "--edges", cpath,
        "--n", "299",
        "--reference", str(reference),
        "--digest-dir", DIGEST_DIR,
        "--label", name,
        "--warpmap", spath,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None, (p.stdout + p.stderr).strip()
    return spath, p.stdout.strip().splitlines()[0] if p.stdout.strip() else ""


def read_sidecar(path):
    """ln|a| per frame, from the f64 BIT PATTERNS. Trailing decimals are a human
    aid and are explicitly not parsed."""
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


def score(track, truth):
    rungs = sorted(truth)
    miss = [j for j in rungs if j not in track]
    if miss:
        return None
    e = [(track[j] - truth[j]) * R_PLANE for j in rungs]
    off = sum(e) / len(e)  # best constant offset in a mean-abs sense is the median,
    med = sorted(e)[len(e) // 2]  # but report against the median: robust, and this
    shape = [abs(v - med) for v in e]  # is the error that is NOT a gauge shift
    return {
        "abs_mean": sum(abs(v) for v in e) / len(e),
        "abs_max": max(abs(v) for v in e),
        "shape_mean": sum(shape) / len(shape),
        "shape_max": max(shape),
        "offset_px": med,
        "mean_signed": off,
        "per_rung": {str(j): round(v, 2) for j, v in zip(rungs, e)},
    }


def main():
    csv_path, truth_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    if not os.path.exists(PROBE):
        print("probe not built: " + PROBE)
        return 2
    head, rows = read_csv(csv_path)
    truth = {
        int(k): v["ln"] for k, v in json.load(open(truth_path, encoding="utf-8"))["ladder"].items()
    }
    print("edges %d, truth rungs %d, R_PLANE %.1f px" % (len(rows), len(truth), R_PLANE))
    nfan = sum(1 for i, j, s, _ in rows if is_fan(i, j, s))
    print("anchor-fan edges (i==0, span not in ladder): %d of %d" % (nfan, len(rows)))
    print()

    results = {}
    sets = dict(VARIANTS)
    for name, pred in sets.items():
        keep = [r for r in rows if pred(r[0], r[1], r[2])]
        sp, line = solve(name, head, keep)
        if sp is None:
            results[name] = {"n_edges": len(keep), "error": line}
            print("%-24s SOLVE FAILED: %s" % (name, line[:80]))
            continue
        sc = score(read_sidecar(sp), truth)
        results[name] = {"n_edges": len(keep), "solve": line, "score": sc, "sidecar": sp}

    keep = placebo(rows)
    sp, line = solve("PLACEBO-drop1pct", head, keep)
    sc = score(read_sidecar(sp), truth) if sp else None
    results["PLACEBO-drop1pct"] = {"n_edges": len(keep), "solve": line, "score": sc, "sidecar": sp}

    # the shipped solve, scored on the same metric for reference
    base = os.path.join(OUT, "wm-baseline-r0.txt")
    if os.path.exists(base):
        results["SHIPPED (reference)"] = {
            "n_edges": None, "score": score(read_sidecar(base), truth), "sidecar": base
        }

    print("Per-frame placement error against the independent RAW ladder, plane px.")
    print("  abs   = as gauged at frame 0, what the merge actually applies")
    print("  shape = after removing the best constant offset (the non-gauge error)")
    print()
    print("  %-24s %6s %8s %8s %8s %8s %9s"
          % ("variant", "edges", "abs_mean", "abs_max", "shp_mean", "shp_max", "offset"))
    order = list(sets) + ["PLACEBO-drop1pct", "SHIPPED (reference)"]
    for name in order:
        r = results.get(name)
        if not r or not r.get("score"):
            print("  %-24s %6s   (no score)" % (name, r.get("n_edges") if r else "-"))
            continue
        s = r["score"]
        print("  %-24s %6s %8.1f %8.1f %8.1f %8.1f %9.1f"
              % (name, r["n_edges"] if r["n_edges"] else "-",
                 s["abs_mean"], s["abs_max"], s["shape_mean"], s["shape_max"], s["offset_px"]))

    # WIRING CONTROL
    print()
    ref = os.path.join(OUT, "wm-iww-r0.txt")
    if os.path.exists(ref) and results["IWW-all"].get("sidecar"):
        a = read_sidecar(ref)
        b = read_sidecar(results["IWW-all"]["sidecar"])
        d = max(abs(a[k] - b[k]) for k in a if k in b)
        ok = "PASS" if d < 1e-9 else "FAIL"
        print("WIRING  IWW-all vs committed wm-iww-r0.txt: max |dln| = %.3e -> %s" % (d, ok))
        results["_wiring"] = {"max_abs_dln": d, "pass": d < 1e-9}
        if d >= 1e-9:
            print("        the re-solve does not reproduce the published sidecar;")
            print("        every other row above is therefore uninterpretable.")

    p = results.get("PLACEBO-drop1pct", {}).get("score")
    q = results.get("IWW-all", {}).get("score")
    if p and q:
        mv = abs(p["abs_mean"] - q["abs_mean"])
        print("PLACEBO drop 1%% of non-frame-0 edges moves abs_mean by %.1f px" % mv)
        results["_placebo_move_px"] = mv

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1, sort_keys=True)
    print("\nwrote " + out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
