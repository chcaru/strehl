"""M66 arm C - real through-focus stacks, N varied by subsetting.

The cube for a stack is decoded ONCE. Every N in the sweep is a subset of that
one cube, so the operator, the regulariser, the noise model, the scene and the
pixel set are identical across N by construction, and the frame list is the only
thing that moves.

Three subset modes, because none of them isolates N and each confounds it with
something different:

  prefix  first N frames        - preserves focus step, TRUNCATES depth range
  stride  N evenly spaced       - preserves depth range, THINS focus sampling
  random  8 seeded draws        - gives the between-subset SD that rule 39 wants

If prefix and stride disagree in direction, the confound dominates N and the
pre-registration says to report the question as not answerable by subsetting.
"""

import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kernel import load, n_eff, subset  # noqa: E402
from m66 import DATA, GATES, N_GRID, OUT, banner  # noqa: E402

REPS = 8
MODES = ("prefix", "stride", "random")

meta = json.loads((OUT / "02-fields.json").read_text(encoding="utf-8"))
only = sys.argv[1:] or list(meta)

banner("M66 arm C - n_eff versus N at fixed gate, on real through-focus stacks")
out = {}
t0 = time.time()
for s in only:
    if s not in meta:
        continue
    cube = load(s, DATA)
    nt = cube.shape[0]
    ns = sorted({n for n in N_GRID if 3 <= n <= nt} | {nt})
    rows = {}
    for n in ns:
        rec = {}
        for mode in MODES:
            reps = 1 if (n == nt or mode != "random") else REPS
            vals = []
            for rep in range(reps):
                idx = subset(mode, nt, n, rep)
                st, _ = n_eff(cube, idx, GATES)
                vals.append(st)
            rec[mode] = {
                str(g): {
                    "mean_n_eff": float(np.mean([v[g]["mean_n_eff"] for v in vals])),
                    "n_eff_over_N": float(np.mean([v[g]["n_eff_over_N"] for v in vals])),
                    "sd_over_reps": float(
                        np.std([v[g]["n_eff_over_N"] for v in vals], ddof=1)
                    )
                    if reps > 1
                    else 0.0,
                    "frac_n1": float(np.mean([v[g]["frac_n1"] for v in vals])),
                    "reps": reps,
                }
                for g in GATES
            }
        rows[str(n)] = rec
    out[s] = {"N_max": nt, "iso": meta[s]["iso"], "pixels": cube.shape[1], "rows": rows}
    del cube

    print(f"\n  {s}  (N_max={nt}, ISO {meta[s]['iso']:.0f}, {out[s]['pixels']} pixels)"
          f"   [{time.time() - t0:.0f}s]")
    for mode in MODES:
        print(f"    {mode}: admitted fraction n_eff/N   (mean n_eff in brackets)")
        print("      N    " + "".join(f"{'T=' + str(g):>20}" for g in GATES))
        for n in ns:
            line = f"      {n:<5}"
            for g in GATES:
                c = rows[str(n)][mode][str(g)]
                line += f"  {c['n_eff_over_N']:>8.5f} [{c['mean_n_eff']:>7.3f}]"
            print(line)

OUT.mkdir(parents=True, exist_ok=True)
p = OUT / "05-sweep.json"
prev = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
prev.update(out)
p.write_text(json.dumps(prev, indent=2), encoding="utf-8")
print(f"\nwrote {p}   [{time.time() - t0:.0f}s total]")
