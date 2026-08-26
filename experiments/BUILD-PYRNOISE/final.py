"""The damage number: what the README's 0.006381 -> 0.000987 becomes.

Everything upstream has established the following, each measured:

  * The claim's ROI is recovered exactly -- `claim_roi.py` reproduces 0.006381,
    0.000987, 0.1546x and 41.82 frames from the claim's own 925d03d renders.
  * The claim's ROI FAILS my admission test at 1.494 raw, but PASSES at 1.017
    once a per-frame photometric gain is removed, and the excess is predicted
    from independently measured terms to +0.3%.
  * The gain is GLOBAL: the patch's level series correlates +0.9886 with the
    whole-plane per-frame level, and the whole-plane span 1.0953 reproduces the
    run's own banner figure of 1.1010.
  * The claim's build did NOT remove it. `git merge-base --is-ancestor` shows
    27646057 ("M97q: wire photometric.rs into the merge behind --photometric")
    is not an ancestor of 925d03d.
  * The pinned shipping binary DOES remove it: the flagless default renders
    bytes different from an explicit `--photometric off`, so the default is on,
    whatever `--help` says.

So the two conditions can be compared WITHIN ONE BUILD -- `--photometric off`
reproduces the claim's condition, the flagless default reproduces today's -- and
the difference between them is the inflation, measured on real arms rather than
simulated. That is what this file computes, together with the arm-vs-arm
reconciliation against the binary's own n_eff map in each condition.
"""

import json
import pathlib
import sys

import numpy as np
import tifffile

from claim_roi import flat_patch, hp_sigma, F, ORCH

CLAIM = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\claim")


def banner_val(err, key):
    for ln in pathlib.Path(err).read_text(encoding="utf8", errors="replace").splitlines():
        if key in ln:
            return ln.strip()
    return "(absent)"


def neff_predict(nm, x, y, w=F, h=F):
    t = nm[y // 2:(y + h) // 2, x // 2:(x + w) // 2].astype(np.float64)
    inv = 1.0 / np.clip(t, 1.0, None)
    return float(np.sqrt(inv.mean())), float(1.0 / inv.mean()), float(t.mean())


def main():
    print("=" * 78)
    print("THE DAMAGE NUMBER")
    print("=" * 78)

    arms = {}
    for tag in ("gate0", "gate2", "gate0_poff", "gate2_poff"):
        arms[tag] = tifffile.imread(CLAIM / f"{tag}.tif").astype(np.float32) / 65535.0
    old = {"gate0": tifffile.imread(ORCH / "leaf-2-cpl-selection-gate0.tif").astype(np.float32) / 65535.0,
           "gate2": tifffile.imread(ORCH / "leaf-2-cpl-estimation-gate2.tif").astype(np.float32) / 65535.0}

    print("\nN0  BANNERS -- what each condition actually did")
    for tag in ("gate0", "gate2", "gate0_poff", "gate2_poff"):
        print(f"    {tag:<11} {banner_val(CLAIM / f'{tag}.err', 'merge backend')}")
        print(f"    {'':<11} photometric mode : "
              f"{banner_val(CLAIM / f'{tag}.err', 'mode            :').split(':')[-1].strip()}")
    for tag in ("gate2", "gate2_poff"):
        print(f"    {tag:<11} {banner_val(CLAIM / f'{tag}.err', 'gain span')}")
    print(f"    gate2       {banner_val(CLAIM / 'gate2.err', '2.00      0.04')}")
    print(f"    gate2_poff  {banner_val(CLAIM / 'gate2_poff.err', '2.00      0.04')}")

    print("\nN1  WHERE thesis_demo.py's OWN ROI SEARCH LANDS, PER CONDITION")
    picks = {}
    for lbl, a, b in (("925d03d (the claim)", old["gate0"], old["gate2"]),
                      ("pin, photometric ON  (today's default)", arms["gate0"], arms["gate2"]),
                      ("pin, photometric OFF (the claim's condition)",
                       arms["gate0_poff"], arms["gate2_poff"])):
        fy, fx = flat_patch(0.5 * (a + b))
        sa, sb = hp_sigma(a, fy, fx), hp_sigma(b, fy, fx)
        picks[lbl] = (fy, fx, sa, sb)
        print(f"    {lbl:<44} y={fy:5d} x={fx:4d}   {sa:.6f} -> {sb:.6f}"
              f"   {sb / sa:.4f}x   {(sa / sb) ** 2:6.2f} frames")

    print("\nN2  THE CLAIM'S OWN PATCH (y=912, x=384) IN EVERY CONDITION")
    print(f"    {'condition':<44}{'gate0':>10}{'gate2':>10}{'ratio':>9}{'frames':>9}")
    cy, cx = 912, 384
    res = {}
    for lbl, a, b in (("925d03d (the claim, photometric absent)", old["gate0"], old["gate2"]),
                      ("pin, photometric OFF (same condition)", arms["gate0_poff"], arms["gate2_poff"]),
                      ("pin, photometric ON  (shipping default)", arms["gate0"], arms["gate2"])):
        sa, sb = hp_sigma(a, cy, cx), hp_sigma(b, cy, cx)
        res[lbl] = (sa, sb, sb / sa)
        print(f"    {lbl:<44}{sa:10.6f}{sb:10.6f}{sb / sa:8.4f}x{(sa / sb) ** 2:9.2f}")

    r_off = res["pin, photometric OFF (same condition)"][2]
    r_on = res["pin, photometric ON  (shipping default)"][2]
    print(f"\n    INFLATION from the uncorrected per-frame gain, measured on real arms")
    print(f"    of ONE build at ONE patch: {r_on:.4f}x / {r_off:.4f}x = {r_on / r_off:.2f}x")
    print(f"    Applied to the claim's own 0.1546x: {0.1546 * (r_on / r_off):.4f}x,"
          f"  {1 / (0.1546 * (r_on / r_off)) ** 2:.1f} frames rather than 41.8")

    print("\nN3  RECONCILIATION AGAINST THE BINARY'S OWN n_eff MAP, PER CONDITION")
    print(f"    {'condition':<24}{'patch':<10}{'mean n_eff':>11}{'predicted':>11}"
          f"{'measured':>10}{'dev':>8}")
    for cond, nfile, a, b in (("photometric ON", "neff.tif", arms["gate0"], arms["gate2"]),
                              ("photometric OFF", "neff_poff.tif", arms["gate0_poff"], arms["gate2_poff"])):
        nm = tifffile.imread(CLAIM / nfile)
        for plbl, (py, px) in (("claim", (912, 384)),
                               ("own argmin", (picks["pin, photometric ON  (today's default)"][0],
                                               picks["pin, photometric ON  (today's default)"][1]))):
            pred, eqn, mn = neff_predict(nm, px, py)
            meas = hp_sigma(b, py, px) / hp_sigma(a, py, px)
            print(f"    {cond:<24}{plbl:<10}{mn:11.2f}{pred:11.4f}{meas:10.4f}"
                  f"{(meas / pred - 1) * 100:+7.1f}%")
        print(f"    {'':<24}{'(whole map mean n_eff ' + f'{nm.mean():.3f}' + ')':<40}")

    json.dump({"picks": {k: list(v) for k, v in picks.items()},
               "claim_patch": {k: list(v) for k, v in res.items()},
               "inflation": r_on / r_off},
              open(CLAIM / "_final.json", "w"), indent=1, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())
