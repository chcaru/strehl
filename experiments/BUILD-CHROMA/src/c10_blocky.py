"""Is my displacement field radial, or is it blocky? (contamination check)

WHY. ORCH's concern: a lateral-CA estimate made on a MERGED image assumes the
three channels at a given pixel came from the same frame. A blocky winner field
with any channel-dependence in the focus measure breaks that, and would print as
apparent lateral CA that is really an election artifact -- spatially blocky
rather than smoothly radial.

The structural answer is that this cannot touch my coefficient (see section 21.3:
c1 measures raw CFA planes frame by frame and never reads a merged image, and the
elected index is shared across all four CFA planes so an election error is
common-mode in any channel difference). But a structural argument is a claim
about code, and this project's standing rule is to measure rather than argue. So:
two numbers.

TEST 1 -- HOW MUCH OF THE FIELD IS RADIAL. R^2 of the one-parameter radial model.
A blocky artifact cannot be fitted by a smooth radial function, so a high R^2 is
a direct bound on how much blockiness can be hiding in the measurement.

TEST 2 -- IS THE RESIDUAL SPATIALLY CLUSTERED. Blockiness means neighbouring
tiles err TOGETHER. White noise does not. Moran's I on the fit residual over the
tile lattice, against a permutation null built by reshuffling the residuals over
the same lattice -- which holds the residual distribution exactly fixed and
destroys only the spatial arrangement, so it is a null matched in structure and
not merely in magnitude (rule 3).

The G2 arm is carried through as the null, as everywhere else in this report.
"""

import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import lateral

RNG = np.random.default_rng(31415)
N_PERM = 2000


def morans_i(xy, v):
    """Moran's I with a nearest-neighbour-tile weight, plus a permutation p.

    Weights are 1 for tile pairs within 1.5 tile pitches, 0 otherwise, so this
    asks exactly the blockiness question: do ADJACENT tiles share their error?
    """
    v = v - v.mean()
    d = np.hypot(xy[:, 0][:, None] - xy[:, 0][None, :],
                 xy[:, 1][:, None] - xy[:, 1][None, :])
    pitch = np.min(d[d > 0])
    W = ((d > 0) & (d <= 1.5 * pitch)).astype(float)
    s = W.sum()
    if s == 0:
        return None
    def I(z):
        return (len(z) / s) * (z @ W @ z) / (z @ z)
    obs = I(v)
    null = np.array([I(RNG.permutation(v)) for _ in range(N_PERM)])
    p = (1 + np.sum(np.abs(null) >= abs(obs))) / (N_PERM + 1)
    return {"I": float(obs), "null_mean": float(null.mean()),
            "null_sd": float(null.std()), "p": float(p),
            "z": float((obs - null.mean()) / null.std())}


def main():
    stacks = sorted(os.path.basename(p)[len("c1_lateral_"):-len(".json")]
                    for p in glob.glob(os.path.join(common.OUT, "json",
                                                    "c1_lateral_*.json")))
    out = []
    print("=" * 100)
    print("IS THE MEASURED DISPLACEMENT FIELD RADIAL OR BLOCKY?")
    print("  R2      fraction of the field explained by a SMOOTH RADIAL model")
    print("  I       Moran's I of the residual on the tile lattice")
    print("          (0 = no spatial clustering; >0 = neighbours err together)")
    print("  p       permutation test, residuals reshuffled over the same tiles")
    print("=" * 100)
    print(f"{'stack':>18} {'ch':>3} {'n':>4} {'R2':>7} {'resid px':>9} "
          f"{'I':>8} {'null I':>8} {'z':>7} {'p':>7}")
    for st in stacks:
        for ch in ("R", "B", "G2"):
            z = np.load(os.path.join(common.OUT, "json", f"c1_{st}_{ch}.npz"))
            u, d = z["u"], z["d"]
            f = lateral.fit_model(u, d, robust=True)
            pred = u * f["eps"] + np.array([f["ty"], f["tx"]])
            res = d - pred
            # One scalar residual per tile: the magnitude of the miss.
            rv = np.hypot(res[:, 0], res[:, 1])
            m = morans_i(u, rv)
            if m is None:
                continue
            rec = {"stack": st, "ch": ch, "n": len(u), "r2": f["r2"],
                   "resid_px": float(rv.mean()), **m}
            out.append(rec)
            tag = "  <- NULL" if ch == "G2" else ""
            print(f"{st:>18} {ch:>3} {len(u):4d} {f['r2']:7.3f} "
                  f"{rv.mean():9.4f} {m['I']:8.3f} {m['null_mean']:8.3f} "
                  f"{m['z']:7.1f} {m['p']:7.4f}{tag}")
        print()

    print("=" * 100)
    print("VERDICT")
    print("=" * 100)
    for ch in ("R", "B", "G2"):
        rows = [r for r in out if r["ch"] == ch]
        if not rows:
            continue
        print(f"  {ch:>3}  mean R2 {np.mean([r['r2'] for r in rows]):.3f}   "
              f"mean Moran I {np.mean([r['I'] for r in rows]):+.3f}   "
              f"significant at p<0.05: "
              f"{sum(r['p'] < 0.05 for r in rows)}/{len(rows)}")
    print()
    print("  A blocky election artifact cannot be fitted by a smooth radial")
    print("  function, so high R2 bounds how much of the measurement could be")
    print("  one. Moran's I near zero says the residual that is left is not")
    print("  spatially organised either -- neighbouring tiles do not err")
    print("  together, which is what blockiness means.")

    common.dump("c10_blocky", out)
    print("\nwrote c10_blocky.json")


if __name__ == "__main__":
    main()
