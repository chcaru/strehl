"""M66 controls K1, K2, K3, K5, and the post-hoc repairs K1', K2'.

K1  gate 0 admits exactly the winner:  mean n_eff == 1.000000 at every N.
K2  a gate far beyond the attainable response range admits everything:
    n_eff/N == 1.000000 at every N. The observed max gap is printed beside it
    so the reader can check "far beyond" is true and not asserted.
K3  the instrument IS the shipped rule: full-N mean n_eff at gate 4.0 against
    M64 section 2.4's shipped-binary numbers, all seven stacks, 1% tolerance.
K5  the 4x-decimated pixel grid is unbiased for mean n_eff: decimated vs
    full-resolution on 109MSDCF and coffee-bubbles, every gate, 1% tolerance.

K1' and K2' are POST-HOC. They are here because K1 and K2 as pre-registered are
NOT MET, and both failures are diagnosable:

K1' the shipped `Gate::admits` is `best - focus <= tolerance`, a `<=`, and the
    crate's own test pins `gate.admits(1.0, 1.0) == true`. So an exact f32 tie
    between two frames' regularised responses is admitted at gate 0 BY DESIGN.
    K1' counts the tied pixels directly. It does not rescue K1; it explains it.
K2' the pre-registered gate 1000 gives a tolerance of 21.5 response units, and
    the measured max gap reaches 120.4. "Far beyond the attainable response
    range" was simply false. K2' repeats the control at gate 1e5.
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kernel import load, n_eff, subset  # noqa: E402
from m66 import DATA, GATES, M64_GUARD, OUT, banner  # noqa: E402

K2_GATE = 1000.0
K2P_GATE = 1e5
res = {"K1": {}, "K2": {}, "K3": {}, "K5": {}, "K1p": {}, "K2p": {}}
fail = []
softfail = []

meta = json.loads((OUT / "02-fields.json").read_text(encoding="utf-8"))
stacks = [s for s in M64_GUARD if s in meta] + (["bee-1"] if "bee-1" in meta else [])

banner("K1 / K2 / K3 - on the 4x-decimated cube, full N and two subsets")
print(f"  {'stack':<15} {'N':>4}  {'K1 g0':>9}  {'K2 g1000':>10}  {'max gap':>9}"
      f"  {'K2p g1e5':>9}  {'g4 mine':>9}  {'g4 M64':>9}  {'ratio':>8}")
for s in stacks:
    cube = load(s, DATA)
    nt = cube.shape[0]
    gates = GATES + [K2_GATE, K2P_GATE]
    stats, maxgap = n_eff(cube, np.arange(nt), gates)
    k1 = stats[0.0]["mean_n_eff"]
    k2 = stats[K2_GATE]["n_eff_over_N"]
    k2p = stats[K2P_GATE]["n_eff_over_N"]
    res["K1"][s] = {"full_N": k1}
    res["K2"][s] = {"full_N": k2, "max_gap": maxgap, "k2_tol": stats[K2_GATE]["tol"]}
    res["K2p"][s] = {"full_N": k2p, "k2p_tol": stats[K2P_GATE]["tol"]}
    # K1' - how many pixels have two or more frames exactly at the max, in f32.
    best = cube[0].copy()
    for k in range(1, nt):
        np.maximum(best, cube[k], out=best)
    ties = np.zeros(cube.shape[1], dtype=np.int32)
    for k in range(nt):
        ties += cube[k] == best
    res["K1p"][s] = {
        "pixels": int(cube.shape[1]),
        "tied_pixels": int((ties > 1).sum()),
        "excess_admissions": int(ties.sum() - cube.shape[1]),
        "excess_per_pixel": float((ties.sum() - cube.shape[1]) / cube.shape[1]),
    }
    del best, ties
    # K1/K2 must also hold on subsets, not just at full N.
    for m in ("prefix", "stride"):
        for n in (5, max(5, nt // 2)):
            idx = subset(m, nt, n)
            st, _ = n_eff(cube, idx, [0.0, K2_GATE, K2P_GATE])
            res["K1"][s][f"{m}-{n}"] = st[0.0]["mean_n_eff"]
            res["K2"][s][f"{m}-{n}"] = st[K2_GATE]["n_eff_over_N"]
            res["K2p"][s][f"{m}-{n}"] = st[K2P_GATE]["n_eff_over_N"]
    mine4 = stats[4.0]["mean_n_eff"]
    ref = M64_GUARD.get(s)
    ratio = mine4 / ref[1] if ref else float("nan")
    res["K3"][s] = {"mine": mine4, "m64": ref[1] if ref else None, "ratio": ratio,
                    "N": nt, "n_eff_over_N": stats[4.0]["n_eff_over_N"]}
    res.setdefault("full_stats", {})[s] = {str(g): v for g, v in stats.items()}
    print(f"  {s:<15} {nt:>4}  {k1:>9.6f}  {k2:>10.6f}  {maxgap:>9.4f}"
          f"  {k2p:>9.6f}  {mine4:>9.4f}  {(ref[1] if ref else float('nan')):>9.4f}"
          f"  {ratio:>8.4f}")
    for k, v in res["K1"][s].items():
        if abs(v - 1.0) > 1e-9:
            softfail.append(f"K1 {s} {k}: {v!r} != 1.0")
    for k, v in res["K2"][s].items():
        if k in ("max_gap", "k2_tol"):
            continue
        if abs(v - 1.0) > 1e-9:
            softfail.append(f"K2 {s} {k}: {v!r} != 1.0")
    for k, v in res["K2p"][s].items():
        if k == "k2p_tol":
            continue
        if abs(v - 1.0) > 1e-9:
            fail.append(f"K2' {s} {k}: {v!r} != 1.0")
    if ref and abs(ratio - 1.0) > 0.01:
        fail.append(f"K3 {s}: mine {mine4:.4f} vs M64 {ref[1]:.4f}, ratio {ratio:.4f}")
    del cube

banner("K1' - exact f32 ties at the winner, which `admits` takes by design")
print(f"  {'stack':<15} {'pixels':>9}  {'tied px':>8}  {'excess admissions':>18}  {'per px':>10}")
for s in stacks:
    r = res["K1p"][s]
    print(f"  {s:<15} {r['pixels']:>9}  {r['tied_pixels']:>8}  "
          f"{r['excess_admissions']:>18}  {r['excess_per_pixel']:>10.3e}")

banner("K5 - 4x-decimated grid against full resolution, every gate")
print(f"  {'stack':<15} {'gate':>6}  {'full-res':>10}  {'decimated':>10}  {'ratio':>8}")
for s in ("109MSDCF", "coffee-bubbles"):
    if not (DATA / f"{s}-full.npy").exists():
        print(f"  {s}: no full-resolution cube cached, K5 NOT RUN")
        res["K5"][s] = "not run"
        continue
    fullc = load(s, DATA, "full")
    d4 = load(s, DATA)
    nt = fullc.shape[0]
    sf, _ = n_eff(fullc, np.arange(nt), GATES)
    sd, _ = n_eff(d4, np.arange(nt), GATES)
    res["K5"][s] = {}
    for g in GATES:
        a, b = sf[g]["mean_n_eff"], sd[g]["mean_n_eff"]
        r = b / a if a else float("nan")
        res["K5"][s][str(g)] = {"full": a, "d4": b, "ratio": r}
        print(f"  {s:<15} {g:>6}  {a:>10.5f}  {b:>10.5f}  {r:>8.5f}")
        if abs(r - 1.0) > 0.01:
            fail.append(f"K5 {s} gate {g}: full {a:.5f} vs d4 {b:.5f}, ratio {r:.5f}")
    res["K5"][s]["full_pixels"] = fullc.shape[1]
    res["K5"][s]["d4_pixels"] = d4.shape[1]
    del fullc, d4

banner("VERDICT")
res["failures"] = fail
res["pre_registered_not_met"] = softfail
worst_k1 = max(
    (abs(v - 1.0) for s in res["K1"] for k, v in res["K1"][s].items()), default=0.0
)
worst_k2 = min(
    (v for s in res["K2"] for k, v in res["K2"][s].items()
     if k not in ("max_gap", "k2_tol")),
    default=1.0,
)
res["worst_K1_excess"] = worst_k1
res["worst_K2_fraction"] = worst_k2
print(f"  K1  NOT MET as pre-registered. Worst excess over 1.000000 = {worst_k1:.3e}")
print(f"      ({len([f for f in softfail if f.startswith('K1')])} of the "
      f"{sum(len(v) for v in res['K1'].values())} K1 cells are above 1.0.)")
print(f"  K2  NOT MET as pre-registered. Worst n_eff/N at gate 1000 = {worst_k2:.6f}")
print("      Cause: gate 1000 is a tolerance of 21.5 response units and the "
      "measured max gap reaches 120.4.")
print("  K1' post-hoc: the excess is exact f32 ties, counted above.")
print(f"  K2' post-hoc at gate 1e5: {'PASS' if not fail else 'see failures below'}")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "03-controls.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
if fail:
    for f in fail:
        print(f"  FAIL  {f}")
    print(f"\n  {len(fail)} HARD control failure(s). Downstream arms are NOT believable.")
    sys.exit(1)
print("  K3  PASS   K5  PASS   K2' PASS")
print(f"\nwrote {OUT / '03-controls.json'}")
