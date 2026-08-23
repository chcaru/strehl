"""04 -- breaking M61's own result: robustness variants and a REAL-DATA plant.

Post-hoc, and labelled post-hoc.  Script 02's answer is pre-registered; this
script is the attempt to make it go away.  Four independent attacks, each with
the outcome that would kill the headline written next to it.

ATTACK 1 -- THE REAL-DATA PLANT (rule 39: plant a wrong answer)
---------------------------------------------------------------
Script 03's positive control is synthetic and so it shares its scene model
with nothing real.  This one does not.  Take the REAL frames of a stack and
average DISJOINT horizontally-adjacent same-plane pixel pairs before running
the estimator.  Two independent samples averaged have the same mean and half
the variance, so the pair-averaged frame is a frame of the SAME scene, with
the SAME texture, the SAME defects, the SAME motion and the SAME photometric
drift, taken with an effective conversion gain of exactly `g / 2`.

M48c's H1 predicts `g / 2.174`.  So if the estimator reports 0.500 x its own
unbinned answer on real pair-averaged frames, it would have reported 0.460 had
H1 been true, on this same real data, with every real nuisance intact.

  KILLS THE HEADLINE IF: the estimator does not fall to ~0.500 here, i.e. it
  cannot see a halved gain on real data, in which case its inability to see
  H1's 0.460 in script 02 means nothing.

A 2x2 quad average (variance / 4, effective gain g / 4) is run as a second
point, and an identity pass (no averaging) as the null of this attack.

ATTACK 2 -- ESTIMATOR CHOICE (rule 24: re-choose, do not re-compute)
--------------------------------------------------------------------
Re-run the ladder's core with a different tile size (16 instead of 8) and a
different structure quantile (40 and 10 instead of 20).  These change the
degrees of freedom per tile, the spatial scale at which "smooth" is defined,
and how much scene texture is allowed through, all of which are exactly the
choices an author picks to get the answer they want.

  KILLS THE HEADLINE IF: r_high / r_low moves materially -- say outside
  0.90-1.15 -- under any of them.

ATTACK 3 -- LEVEL DEPENDENCE
-----------------------------
The high-ISO stacks sit at lower DN than the low-ISO ones, so a level-
dependent bias fakes an ISO effect.  Printed here: r restricted to the common
50-800 DN window, already computed by 02, side by side with the full-range r.

  KILLS THE HEADLINE IF: the common-window ladder and the full-range ladder
  disagree about r_high / r_low.

ATTACK 4 -- WHICH STACKS SURVIVE THEIR OWN FIT
-----------------------------------------------
`coffee-bubbles` returned PTC residuals of 174%-1064%, a NaN in variant B and
a NEGATIVE gain in variant C.  Dropping it is a post-hoc choice, so both
numbers are reported: with it (as pre-registered) and without it, plus the
direction the contamination pushes.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m61-ptc-high-iso/src/04-break-it.py
"""

from __future__ import annotations

import csv
import glob
import importlib.util
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CSVIN = os.path.join(HERE, "..", "data", "ptc-ladder.csv")
OUT = os.path.join(HERE, "..", "data", "break-it.txt")
CORPUS = r"D:\personal\macro"
PLANES = ("R", "G1", "G2", "B")
LINES: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    LINES.append(s)


def load_ladder():
    spec = importlib.util.spec_from_file_location(
        "ladder", os.path.join(HERE, "02-ptc-ladder.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_rows():
    with open(CSVIN, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            if k not in ("stack", "plane"):
                r[k] = float(v)
    return rows


def pair_avg(p: np.ndarray, factor: int) -> np.ndarray:
    """Average disjoint same-plane neighbours: variance / factor, mean kept."""
    a = p.astype(np.float64)
    if factor == 1:
        return p
    if factor == 2:
        w = a.shape[1] - a.shape[1] % 2
        out = 0.5 * (a[:, 0:w:2] + a[:, 1:w:2])
    elif factor == 4:
        h = a.shape[0] - a.shape[0] % 2
        w = a.shape[1] - a.shape[1] % 2
        out = 0.25 * (a[0:h:2, 0:w:2] + a[0:h:2, 1:w:2]
                      + a[1:h:2, 0:w:2] + a[1:h:2, 1:w:2])
    else:
        raise ValueError(factor)
    return np.clip(np.round(out), 0, 65535).astype(np.uint16)


def measure_variant(L, name, iso, planes=("G1", "G2"), tile=None, qa=None,
                    factor=1, npairs=10):
    old_tile, old_q = L.TILE, L.Q_A
    if tile:
        L.TILE = tile
    if qa:
        L.Q_A = qa
    try:
        fs = sorted(glob.glob(os.path.join(CORPUS, name, "*.ARW")))
        starts = np.unique(np.linspace(0, len(fs) - 2,
                                       min(npairs, len(fs) - 1)).astype(int))
        acc = {p: {"m": [], "v": [], "u": []} for p in planes}
        for k in starts:
            a = L.read_raw(fs[k])
            b = L.read_raw(fs[k + 1])
            for p in planes:
                pa = pair_avg(L.plane_of(a, p), factor)
                pb = pair_avg(L.plane_of(b, p), factor)
                ma = float(pa.mean()) - L.BLACK
                mb = float(pb.mean()) - L.BLACK
                if ma <= 0 or mb <= 0 or abs(ma / mb - 1.0) > L.PAIR_LEVEL_TOL:
                    continue
                m, v, u, ok = L.tile_stats(pa, pb)
                acc[p]["m"].append(m[ok])
                acc[p]["v"].append(v[ok])
                acc[p]["u"].append(u[ok])
            del a, b
        gs = []
        for p in planes:
            if not acc[p]["m"]:
                continue
            m = np.concatenate(acc[p]["m"])
            v = np.concatenate(acc[p]["v"])
            u = np.concatenate(acc[p]["u"])
            est = L.bin_estimates(m, v, u, float(np.percentile(m, 1.0)),
                                  float(np.percentile(m, 99.5)))
            gs.append(L.fit_ptc([(e[0], e[1], e[2]) for e in est])[0])
        return float(np.nanmean(gs)) / L.g_model(iso)
    finally:
        L.TILE, L.Q_A = old_tile, old_q


def main() -> int:
    t0 = time.time()
    L = load_ladder()
    rows = read_rows()
    say("M61 script 04 -- attempts to break M61's own result (POST HOC)")
    say()

    say("=" * 78)
    say("ATTACK 1 -- REAL-DATA PLANT: in-plane pair averaging halves the gain")
    say("=" * 78)
    say("  averaging n disjoint same-plane neighbours keeps the mean and")
    say("  divides the variance by n, i.e. plants an effective gain g/n on")
    say("  real frames with real texture, defects, motion and level drift.")
    say(f"  {'stack':<15} {'ISO':>5} {'n=1':>8} {'n=2':>8} {'ratio':>8} "
        f"{'expect':>8} {'n=4':>8} {'ratio':>8} {'expect':>8}")
    for name, iso in (("109MSDCF", 160.0), ("112MSDCF", 500.0),
                      ("foam", 1000.0)):
        r1 = measure_variant(L, name, iso, factor=1)
        r2 = measure_variant(L, name, iso, factor=2)
        r4 = measure_variant(L, name, iso, factor=4)
        say(f"  {name:<15} {iso:>5.0f} {r1:>8.4f} {r2:>8.4f} "
            f"{r2 / r1:>8.4f} {0.5:>8.3f} {r4:>8.4f} {r4 / r1:>8.4f} "
            f"{0.25:>8.3f}")
    say("  H1's predicted step is 0.460, which sits between the two planted")
    say("  values, so an estimator that recovers both brackets it.")
    say()

    say("=" * 78)
    say("ATTACK 2 -- ESTIMATOR CHOICE: tile size and structure quantile")
    say("=" * 78)
    variants = [("tile 8  q20 (as run)", None, None),
                ("tile 16 q20", 16, None),
                ("tile 8  q40", None, 40.0),
                ("tile 8  q10", None, 10.0),
                ("tile 16 q40", 16, 40.0)]
    lows = ["109MSDCF", "bee-3"]
    highs = ["112MSDCF", "foam"]
    isos = {"109MSDCF": 160.0, "bee-3": 100.0, "112MSDCF": 500.0,
            "foam": 1000.0}
    say(f"  {'variant':<22} {'r(109)':>8} {'r(bee-3)':>9} {'r(112)':>8} "
        f"{'r(foam)':>8} {'rhi/rlo':>9}")
    for tag, tile, qa in variants:
        vals = {}
        for n in lows + highs:
            vals[n] = measure_variant(L, n, isos[n], tile=tile, qa=qa)
        rlo = np.mean([vals[n] for n in lows])
        rhi = np.mean([vals[n] for n in highs])
        say(f"  {tag:<22} {vals['109MSDCF']:>8.4f} {vals['bee-3']:>9.4f} "
            f"{vals['112MSDCF']:>8.4f} {vals['foam']:>8.4f} "
            f"{rhi / rlo:>9.4f}")
    say("  KILL CONDITION was rhi/rlo outside 0.90-1.15 under any variant.")
    say()

    say("=" * 78)
    say("ATTACK 3 -- LEVEL DEPENDENCE: common 50-800 DN window vs full range")
    say("=" * 78)
    say(f"  {'stack':<15} {'ISO':>5} {'r full':>8} {'r common':>9} "
        f"{'diff':>8}")
    full_by_stack, comm_by_stack, iso_by_stack = {}, {}, {}
    for r in rows:
        full_by_stack.setdefault(r["stack"], []).append(r["gA"]
                                                        / r["g_model"])
        comm_by_stack.setdefault(r["stack"], []).append(r["g_common"]
                                                        / r["g_model"])
        iso_by_stack[r["stack"]] = r["iso"]
    for s in full_by_stack:
        f_ = float(np.nanmean(full_by_stack[s]))
        c_ = float(np.nanmean(comm_by_stack[s]))
        say(f"  {s:<15} {iso_by_stack[s]:>5.0f} {f_:>8.4f} {c_:>9.4f} "
            f"{c_ - f_:>+8.4f}")
    lo_f = np.mean([np.nanmean(full_by_stack[s]) for s in full_by_stack
                    if iso_by_stack[s] < 400])
    lo_c = np.mean([np.nanmean(comm_by_stack[s]) for s in comm_by_stack
                    if iso_by_stack[s] < 400])
    for iso in (400.0, 500.0, 1000.0):
        hf = np.mean([np.nanmean(full_by_stack[s]) for s in full_by_stack
                      if iso_by_stack[s] == iso])
        hc = np.mean([np.nanmean(comm_by_stack[s]) for s in comm_by_stack
                      if iso_by_stack[s] == iso])
        say(f"  ISO {iso:>6.0f}: r_high/r_low  full {hf / lo_f:.4f}   "
            f"common-window {hc / lo_c:.4f}")
    say()

    say("=" * 78)
    say("ATTACK 4 -- WHICH STACKS SURVIVE THEIR OWN FIT")
    say("=" * 78)
    say(f"  {'stack':<15} {'ISO':>5} {'max PTC resid %':>16} "
        f"{'A/B spread %':>13} {'A/C spread %':>13} {'half-split %':>13}")
    for s in full_by_stack:
        rr = [r for r in rows if r["stack"] == s]
        resid = max(r["resid_pct"] for r in rr)
        ab = 100 * np.nanmax([abs(r["gB"] / r["gA"] - 1) for r in rr])
        ac = 100 * np.nanmax([abs(r["gC"] / r["gA"] - 1) for r in rr])
        hh = 100 * np.nanmax([abs(r["g_half1"] / r["g_half0"] - 1)
                              for r in rr])
        say(f"  {s:<15} {iso_by_stack[s]:>5.0f} {resid:>16.1f} "
            f"{ab:>13.1f} {ac:>13.1f} {hh:>13.1f}")
    say()
    for tag, drop in (("as pre-registered", []), ("without coffee-bubbles",
                                                  ["coffee-bubbles"])):
        lo = [np.nanmean(full_by_stack[s]) for s in full_by_stack
              if iso_by_stack[s] < 400 and s not in drop]
        say(f"  [{tag}]  r_low = {np.mean(lo):.4f} +- {np.std(lo):.4f}")
        for iso in (400.0, 500.0, 1000.0):
            hi = [np.nanmean(full_by_stack[s]) for s in full_by_stack
                  if iso_by_stack[s] == iso and s not in drop]
            if not hi:
                continue
            say(f"      ISO {iso:>6.0f}  r_high = {np.mean(hi):.4f} "
                f"+- {np.std(hi):.4f}   r_high/r_low = "
                f"{np.mean(hi) / np.mean(lo):.4f}")
    say()

    say("=" * 78)
    say("PER-PLANE STRUCTURE -- reported because it is ISO-INDEPENDENT")
    say("=" * 78)
    say(f"  {'stack':<15} {'ISO':>5} " + " ".join(f"{p:>8}" for p in PLANES)
        + f" {'B/mean(G)':>10} {'R/mean(G)':>10}")
    for s in sorted(full_by_stack, key=lambda x: iso_by_stack[x]):
        d = {r["plane"]: r["gA"] / r["g_model"] for r in rows
             if r["stack"] == s}
        gmean = 0.5 * (d["G1"] + d["G2"])
        say(f"  {s:<15} {iso_by_stack[s]:>5.0f} "
            + " ".join(f"{d[p]:>8.4f}" for p in PLANES)
            + f" {d['B'] / gmean:>10.4f} {d['R'] / gmean:>10.4f}")
    bg = [({r["plane"]: r["gA"] for r in rows if r["stack"] == s}["B"]
           / (0.5 * ({r["plane"]: r["gA"] for r in rows
                      if r["stack"] == s}["G1"]
                     + {r["plane"]: r["gA"] for r in rows
                        if r["stack"] == s}["G2"])))
          for s in full_by_stack if s != "coffee-bubbles"]
    say(f"  B / green slope ratio over 11 stacks and a 20x ISO range: "
        f"{np.mean(bg):.4f} +- {np.std(bg):.4f}")
    say()
    say(f"[{time.time() - t0:.0f}s]")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
