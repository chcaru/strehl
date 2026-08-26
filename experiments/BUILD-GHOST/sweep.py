"""BUILD-GHOST Part 1 -- residual local motion across all 26 corpus subjects.

WHAT THIS MEASURES
------------------
For a pair of frames it reports the LOCAL displacement field that survives the
global similarity the aligner fits.  Not the total displacement: focus breathing
moves the corner of a bee-3-cpl frame by 232.7 px across its bracket and that is
the rig working as designed, not motion.  What is left after a similarity is
removed is the part no global 2D transform can explain.

WHY IT IS A DISPLACEMENT AND NOT A DIFFERENCE
---------------------------------------------
Defocus is a convolution with a symmetric unit-sum kernel.  It changes the
AMPLITUDE of structure, not its POSITION -- a correlation peak gets shorter
under blur but does not move.  Motion moves it.  Those are different axes of the
same correlation surface, and this reads only the one defocus cannot touch.
controls.py C4 proves the separation empirically: a naive difference detector
flags several times more tiles on a pair where nothing moved and focus changed
than on a pair with 8 sensor px of real motion.

THE MULTI-BASELINE DESIGN
-------------------------
Each anchor is measured against frames K steps away for several K.  This is not
redundancy, it closes a real blind spot:

    steady drift    residual grows LINEARLY in K
    random jitter   residual grows as sqrt(K)
    nothing         residual stays flat at the detector floor

A 0.2 sensor px per frame drift is invisible at K=1 -- it is under the floor --
but it is 60 px end to end across a 299 frame bracket, and THAT is what folds a
smear into the estimate.  A K=1-only sweep cannot see it.  Reporting the K
slope is how a real drift is distinguished from a noisy floor.

USAGE
    python experiments/BUILD-GHOST/sweep.py --all --jobs 5
    python experiments/BUILD-GHOST/sweep.py --subject bee-3-cpl
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghostlib as G

RAW_ROOT = r"D:\personal\macro"
OUT = r"C:\dev\strehl-out\BUILD-GHOST"
BASELINES = (1, 4, 16)
N_ANCHORS = 9


def subjects() -> list[str]:
    """Every subject directory that actually contains frames.

    flat-fields/ is present and empty; it produced no master and is not one of
    the 26.  Excluding it by 'has frames' rather than by name means the count is
    derived from the disk, not asserted here.
    """
    out = []
    for d in sorted(os.listdir(RAW_ROOT)):
        p = os.path.join(RAW_ROOT, d)
        if os.path.isdir(p) and G.frames_of(p):
            out.append(d)
    return out


def anchor_plan(n_frames: int) -> list[tuple[int, int]]:
    """(i, K) pairs: N_ANCHORS anchors spread over the bracket, each measured at
    every baseline that stays in range.  Anchors avoid the extreme ends, where a
    bracket often runs past the subject entirely and nothing is in focus."""
    kmax = max(BASELINES)
    lo, hi = 2, n_frames - kmax - 2
    if hi <= lo:
        lo, hi = 0, max(n_frames - min(BASELINES) - 1, 0)
    if hi <= lo:
        return []
    idx = np.unique(np.linspace(lo, hi, min(N_ANCHORS, hi - lo + 1)).round().astype(int))
    plan = []
    for i in idx:
        for k in BASELINES:
            if i + k < n_frames:
                plan.append((int(i), int(k)))
    return plan


def measure_subject(name: str) -> dict:
    t0 = time.time()
    sdir = os.path.join(RAW_ROOT, name)
    frames = G.frames_of(sdir)
    plan = anchor_plan(len(frames))
    rec = {"subject": name, "n_frames": len(frames), "n_pairs_planned": len(plan),
           "pairs": [], "errors": []}
    if not plan:
        rec["errors"].append("bracket too short for any planned baseline")
        return rec

    # One photon-transfer estimate per subject, from a mid-bracket frame, reused
    # for every pair.  The noise model is a property of the sensor and the
    # exposure, not of the pair, and re-fitting it per pair would let a
    # defocused frame's own smoothness bias its focus gate.
    cache: dict[int, np.ndarray] = {}

    def plane(i: int) -> np.ndarray:
        if i not in cache:
            if len(cache) > 6:
                cache.pop(next(iter(cache)))
            cache[i] = G.decode_plane(frames[i])["g"]
        return cache[i]

    k, r2 = G.photon_transfer(plane(len(frames) // 2))
    rec["photon_k"] = k
    rec["photon_r2"] = r2

    for (i, kk) in plan:
        try:
            r = G.measure_pair(plane(i), plane(i + kk), noise=(k, r2))
        except Exception as e:                       # noqa: BLE001
            rec["errors"].append(f"{i}+{kk}: {e.__class__.__name__}: {e}")
            rec["pairs"].append({"i": i, "k": kk, "ok": False,
                                 "reason": f"{e.__class__.__name__}"})
            continue
        p = {"i": i, "k": kk, "ok": bool(r.ok), "reason": r.reason,
             "a": os.path.basename(frames[i]), "b": os.path.basename(frames[i + kk])}
        if r.ok:
            p.update(G.resid_summary(r))
            p["census"] = r.census()
            p["focus_diff_ln_p50"] = r.stats.get("focus_diff_ln_p50")
            p["focus_diff_ln_p90"] = r.stats.get("focus_diff_ln_p90")
            p["sim_scale_minus_one"] = r.stats.get("sim_scale_minus_one")
            p["sim_rotation_rad"] = r.stats.get("sim_rotation_rad")
            p["sim_t_plane"] = [r.stats.get("sim_ty_plane"), r.stats.get("sim_tx_plane")]
            p["sim_mad_plane"] = r.stats.get("sim_mad_plane")
            p["rho_kept_median"] = r.stats.get("rho_kept_median")
            # Cluster sites at a deliberately low threshold: this list only
            # nominates places to LOOK at 1:1 in Part 3, it does not decide
            # anything.  Filtering happens later, against the control floor.
            p["clusters"] = G.clusters(r.origins, r.resid, 0.60)[:6]
        else:
            p["census"] = r.census() if r.n_fine_total else {}
        rec["pairs"].append(p)

    rec["elapsed_s"] = time.time() - t0
    rec.update(summarise_subject(rec))
    return rec


def summarise_subject(rec: dict) -> dict:
    """Per-baseline aggregates plus the K-slope that separates drift from jitter."""
    out: dict = {"by_k": {}}
    ok = [p for p in rec["pairs"] if p.get("ok")]
    out["n_pairs_ok"] = len(ok)
    out["n_pairs_failed"] = len(rec["pairs"]) - len(ok)
    for kk in BASELINES:
        sub = [p for p in ok if p["k"] == kk]
        if not sub:
            out["by_k"][str(kk)] = {"n_pairs": 0}
            continue
        out["by_k"][str(kk)] = {
            "n_pairs": len(sub),
            "n_tiles": int(sum(p["census"]["kept"] for p in sub)),
            "n_tiles_total": int(sum(p["census"]["total"] for p in sub)),
            "n_saturated": int(sum(p["census"]["saturated"] for p in sub)),
            "p50_med": float(np.median([p["p50"] for p in sub])),
            "p90_med": float(np.median([p["p90"] for p in sub])),
            "p99_med": float(np.median([p["p99"] for p in sub])),
            "p99_max": float(max(p["p99"] for p in sub)),
            "max_max": float(max(p["max"] for p in sub)),
            "focus_diff_ln_p50_med": float(np.median(
                [p["focus_diff_ln_p50"] for p in sub if p.get("focus_diff_ln_p50") is not None]
            )) if any(p.get("focus_diff_ln_p50") is not None for p in sub) else None,
        }
    # slope of log(p99) against log(K): ~0 flat, ~0.5 jitter, ~1.0 steady drift
    xs, ys = [], []
    for kk in BASELINES:
        b = out["by_k"].get(str(kk), {})
        if b.get("n_pairs"):
            xs.append(np.log(kk))
            ys.append(np.log(max(b["p99_med"], 1e-6)))
    out["k_slope"] = float(np.polyfit(xs, ys, 1)[0]) if len(xs) >= 2 else None
    return out


def one(name: str) -> dict:
    try:
        return measure_subject(name)
    except Exception:                                 # noqa: BLE001
        return {"subject": name, "fatal": traceback.format_exc()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", action="append", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(OUT, "data"))
    args = ap.parse_args()

    names = args.subject if args.subject else (subjects() if args.all else None)
    if not names:
        ap.error("give --subject NAME (repeatable) or --all")
    os.makedirs(args.out, exist_ok=True)
    print(f"sweeping {len(names)} subjects, baselines K={BASELINES}, "
          f"{N_ANCHORS} anchors each, jobs={args.jobs}", flush=True)

    t0 = time.time()
    recs: list[dict] = []
    if args.jobs > 1:
        with cf.ProcessPoolExecutor(max_workers=args.jobs) as ex:
            for r in ex.map(one, names):
                recs.append(r)
                report(r)
    else:
        for n in names:
            r = one(n)
            recs.append(r)
            report(r)

    # A census that partitions EVERY subject.  A subject that crashed must not
    # be able to read as a subject with no motion.
    fatal = [r for r in recs if "fatal" in r]
    nodata = [r for r in recs if "fatal" not in r and r.get("n_pairs_ok", 0) == 0]
    good = [r for r in recs if "fatal" not in r and r.get("n_pairs_ok", 0) > 0]
    print(f"\nsubjects examined {len(recs)}   measured {len(good)}   "
          f"no-usable-pair {len(nodata)}   crashed {len(fatal)}   "
          f"(sums to {len(good) + len(nodata) + len(fatal)})")
    for r in fatal:
        print(f"    CRASH  {r['subject']}")
    for r in nodata:
        print(f"    NODATA {r['subject']}: {r.get('errors')}")

    path = os.path.join(args.out, "sweep.json")
    with open(path, "w") as fh:
        json.dump({"baselines": list(BASELINES), "n_anchors": N_ANCHORS,
                   "raw_root": RAW_ROOT, "subjects": recs,
                   "n_subjects": len(recs), "n_measured": len(good),
                   "n_nodata": len(nodata), "n_crashed": len(fatal),
                   "elapsed_s": time.time() - t0}, fh, indent=2, default=float)
    print(f"wrote {path}  ({time.time() - t0:.0f}s)")
    return 0 if not fatal else 1


def report(r: dict) -> None:
    if "fatal" in r:
        print(f"  {r['subject']:38s} CRASH", flush=True)
        return
    bits = []
    for kk in BASELINES:
        b = r.get("by_k", {}).get(str(kk), {})
        bits.append(f"K{kk}:" + (f"{b['p99_med']:6.3f}" if b.get("n_pairs") else "   --- "))
    ks = r.get("k_slope")
    print(f"  {r['subject']:38s} n={r['n_frames']:3d} "
          f"pairs {r.get('n_pairs_ok', 0):2d}/{r['n_pairs_planned']:2d}  "
          f"p99(sensor px) {' '.join(bits)}  slope "
          f"{('%+.2f' % ks) if ks is not None else ' n/a'}  "
          f"({r.get('elapsed_s', 0):.0f}s)", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
