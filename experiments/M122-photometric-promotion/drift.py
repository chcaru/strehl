"""M122 — per-stack inter-frame level drift, over exactly the frames the merge gathers.

PRIMARY estimator `Dpp`, registered in PREREGISTRATION.md section 4.1, is M24's
estimator verbatim (`experiments/m24-photometric-drift/src/01-levels.py`): the
mean of the CFA green plane per frame, black-subtracted, normalised to the stack
mean, reported as per-cent peak-to-peak.

Why that one and not a window mean: defocus and focus breathing redistribute
light within the frame but conserve it, so a whole-visible-plane mean is close to
invariant to both, while a fixed window is not (SYNTHESIS question 202). And it
is commissioned against four independently folded numbers rather than against
itself (M24's 0.91 / 2.88 / 6.84 / 8.93 / 11.70 %).

SECONDARY estimator `Dwin` uses ORCH's six fixed 256-px background windows
(`experiments/ORCH-drift-check/level_drift_budget.py`), which land on the same
coordinate grid: `raw_image_visible[0::2, 1::2]` is 2344 x 3516, the same shape
as the merge's binned plane.

AGENTS.md rule 7  : `raw_image_visible`, never the full decoded buffer.
AGENTS.md rule 32 : the slice is cast on the same line, inside the `with`, and
                    reduced to a scalar before the context manager exits.
D:\\ is read-only here. This script opens files there and writes nothing.
"""

import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import rawpy

LIB = r"D:\personal\macro"
OUT = r"C:\dev\strehl-out\M122"
BLACK = 512

# ORCH's six windows, on the green-plane grid (level_drift_budget.py).
WINDOWS = [(2832, 400), (400, 528), (1552, 1680), (656, 1552), (2704, 400), (400, 1040)]
S = 256


def frame_levels(path):
    """Whole-visible-green mean and the six window means, for one frame.

    Everything is reduced to floats INSIDE the `with`, so no view outlives the
    RawPy context (AGENTS.md rule 32 — the use-after-free does not reliably
    crash, which is the dangerous part).
    """
    with rawpy.imread(path) as rr:
        g = rr.raw_image_visible[0::2, 1::2].astype(np.float64) - BLACK
        full = float(g.mean())
        h, w = g.shape
        wins = []
        for x, y in WINDOWS:
            if x + S <= w and y + S <= h:
                wins.append(float(g[y:y + S, x:x + S].mean()))
            else:
                wins.append(float("nan"))
        shape = (int(h), int(w))
    return full, wins, shape


def p2p(v):
    v = np.asarray(v, dtype=np.float64)
    return float((v.max() - v.min()) / v.mean() * 100.0)


def measure(name, sub=1, nmax=None, workers=8):
    d = os.path.join(LIB, name)
    fs = sorted(glob.glob(os.path.join(d, "*.ARW")))[::sub]
    if nmax is not None:
        fs = fs[:nmax]
    if not fs:
        return None
    with ProcessPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(frame_levels, fs))
    full = np.array([r[0] for r in res], dtype=np.float64)
    wins = np.array([r[1] for r in res], dtype=np.float64)
    shape = res[0][2]

    rel = full / full.mean()
    idx = np.arange(len(full), dtype=np.float64)
    slope = float(np.polyfit(idx, rel, 1)[0])
    resid = rel - np.polyval(np.polyfit(idx, rel, 1), idx)
    lin_frac = float(1.0 - resid.var() / rel.var()) if rel.var() > 0 else float("nan")

    per_win = []
    for j in range(wins.shape[1]):
        col = wins[:, j]
        per_win.append(float("nan") if not np.isfinite(col).all() else p2p(col))
    finite = [v for v in per_win if np.isfinite(v)]

    return {
        "stack": name,
        "n_used": int(len(fs)),
        "sub": int(sub),
        "green_plane_shape": list(shape),
        "first": os.path.basename(fs[0]),
        "last": os.path.basename(fs[-1]),
        "mean_level_dn": float(full.mean()),
        "Dpp": p2p(full),
        "trend_pct_over_stack": float(slope * len(full) * 100.0),
        "jitter_pct": float(np.std(np.diff(rel)) * 100.0),
        "linear_var_removed": lin_frac,
        "Dwin_per_window": per_win,
        "Dwin_median": float(np.median(finite)) if finite else float("nan"),
        "levels": [float(v) for v in full],
    }


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "corpus"

    if mode == "m24":
        # R2 -- like-for-like replication of M24's own sampling, so the
        # commissioning comparison is against the same estimator on the same
        # frame subset, not merely the same stacks.
        plan = [("109MSDCF", 1, 40), ("119MSDCF", 1, 40), ("coffee-bean", 3, 40),
                ("112MSDCF", 2, 40), ("coffee-bubbles", 1, 40)]
        published = {"109MSDCF": 0.91, "119MSDCF": 2.88, "coffee-bean": 11.70,
                     "112MSDCF": 6.84, "coffee-bubbles": 8.93}
        rows = []
        print("R2 -- M24 replication (M24's sampling: sub, nmax=40)")
        print("%-16s %5s %10s %10s %9s" % ("stack", "n", "M24 p2p", "mine", "delta"))
        for name, sub, nmax in plan:
            r = measure(name, sub=sub, nmax=nmax)
            if r is None:
                print("%-16s MISSING" % name)
                continue
            r["m24_published"] = published[name]
            rows.append(r)
            print("%-16s %5d %9.2f%% %9.2f%% %+8.2f"
                  % (name, r["n_used"], published[name], r["Dpp"],
                     r["Dpp"] - published[name]))
        with open(os.path.join(OUT, "drift-m24-replication.json"), "w") as fh:
            json.dump(rows, fh, indent=1)
        return

    subjects = sorted(
        n for n in os.listdir(LIB)
        if os.path.isdir(os.path.join(LIB, n))
        and glob.glob(os.path.join(LIB, n, "*.ARW"))
    )
    rows = []
    print("%-38s %5s %10s %10s %10s %10s %9s"
          % ("stack", "n", "Dpp", "Dwin med", "trend", "jitter", "lin var"))
    for name in subjects:
        n = len(glob.glob(os.path.join(LIB, name, "*.ARW")))
        L = min(100, n)
        r = measure(name, sub=1, nmax=L)
        if r is None:
            continue
        rows.append(r)
        print("%-38s %5d %9.3f%% %9.3f%% %+9.3f%% %9.3f%% %8.3f"
              % (name, r["n_used"], r["Dpp"], r["Dwin_median"],
                 r["trend_pct_over_stack"], r["jitter_pct"], r["linear_var_removed"]))
        with open(os.path.join(OUT, "drift-corpus.json"), "w") as fh:
            json.dump(rows, fh, indent=1)
    print("\nwrote %s" % os.path.join(OUT, "drift-corpus.json"))


if __name__ == "__main__":
    main()
