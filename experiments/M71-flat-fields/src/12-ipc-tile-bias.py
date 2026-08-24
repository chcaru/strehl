"""
M71 step 12 — can inter-pixel correlation explain M61's tile-size climb?

M61 §4.7 (its fact 29) bounds the "tile sample variance under-reports when the
noise is spatially correlated" failure mode by growing the tile and watching the
B/green ratio climb:

    stack              tile 8   tile 16  tile 32
    109MSDCF (ISO 160) 0.8283   0.8464   0.8377
    112MSDCF (ISO 500) 0.8407   0.8517   0.8466
    bee-3    (ISO 100) 0.8408   0.8607   0.8699
    foam     (ISO1000) 0.8376   0.8529   0.8558

M61 concluded, correctly, that this "cannot supply the missing 16%". But it left
the residual size of the effect unquantified, and M68 fact 39 then recorded that
PRNU leakage into those tile variances "remains unchecked by me".

M71 is in a position to check it, because M71 measured the per-plane noise
autocorrelation directly on a defocused uniform field with no subject at all.

This script measures the in-plane noise ACF for ALL FOUR planes (07-structure.py
did only the two greens) and evaluates the exact sample-variance bias for an
n x n tile:

    E[s^2]/sigma^2 = 1 - (1/(N(N-1))) * sum_{i!=j} rho_ij ,  N = n^2

summed over the measured lags with their signed multiplicities. If IPC were the
cause of the climb, this must reproduce ~3.5% between tile 8 and tile 32.
"""
import csv
import json
import pathlib
from fractions import Fraction

import numpy as np
import rawpy

HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = HERE / "data"
OUT = DATA / "12-ipc-tile-bias.json"

LAGS = [(0, 1), (1, 0), (1, 1), (0, 2), (2, 0), (1, 2), (2, 1), (2, 2),
        (0, 3), (3, 0)]

PLANES = {"R": (slice(0, None, 2), slice(0, None, 2)),
          "G1": (slice(0, None, 2), slice(1, None, 2)),
          "G2": (slice(1, None, 2), slice(0, None, 2)),
          "B": (slice(1, None, 2), slice(1, None, 2))}


def multiplicity(dy, dx, n):
    """Ordered-pair count at displacement (dy,dx) in an n x n tile, summed over
    the sign variants of that lag."""
    base = (n - abs(dy)) * (n - abs(dx))
    if dy == 0 and dx == 0:
        return 0
    if dy == 0 or dx == 0:
        return 2 * base          # (0,+d) and (0,-d)
    return 4 * base              # (+dy,+dx) (+dy,-dx) (-dy,+dx) (-dy,-dx)


def tile_factor(acf, n):
    """E[s^2]/sigma^2 for an n x n tile given the measured ACF."""
    N = n * n
    tot = 0.0
    for (dy, dx), r in acf.items():
        tot += r * multiplicity(dy, dx, n)
    return 1.0 - tot / (N * (N - 1))


def main():
    src = list(csv.DictReader(
        (DATA / "exif-all.csv").open(encoding="utf-8-sig")))
    grp = sorted([r for r in src
                  if pathlib.Path(r["Directory"]).name == "flat-fields"
                  and abs(float(Fraction(r["ExposureTime"])) - 0.05) < 1e-6],
                 key=lambda r: r["SubSecDateTimeOriginal"])
    assert len(grp) == 40, len(grp)

    # same adjacent pair 07-structure.py used, so the greens must reproduce
    fs = []
    for r in (grp[8], grp[9]):
        with rawpy.imread(r["SourceFile"]) as raw:
            fs.append(raw.raw_image_visible.astype(np.float32).copy())  # rule 32
    d = fs[0] - fs[1]

    print("=== in-plane noise autocorrelation, all four planes")
    print("    (temporal difference: every fixed pattern, including PRNU and")
    print("     the paper, cancels identically -- this is pure noise)")
    res = {}
    for name, sl in PLANES.items():
        p = d[sl][200:-200, 200:-200].astype(np.float64)
        p = p - p.mean()
        v0 = float(np.mean(p * p))
        acf = {}
        for (dy, dx) in LAGS:
            q = p[dy:, dx:]
            pp = p[:q.shape[0], :q.shape[1]]
            acf[(dy, dx)] = float(np.mean(pp * q) / v0)
        nn = 2 * (acf[(0, 1)] + acf[(1, 0)])
        res[name] = {"var_diff": v0, "acf": {f"{a},{b}": v for (a, b), v in acf.items()},
                     "nn_sum": nn, "_acf": acf}
        print(f"  {name}: var(d)={v0:9.2f}  "
              f"r(0,1)={acf[(0,1)]:+.5f} r(1,0)={acf[(1,0)]:+.5f} "
              f"r(1,1)={acf[(1,1)]:+.5f}   4nn sum={nn:+.5f}")

    # cross-check against 07-structure.py's committed greens
    prev = json.load(open(DATA / "07-structure.json"))["ipc"]["planes"]
    print("\n  reproduction check against 07-structure.json:")
    for name in ("G1", "G2"):
        a = res[name]["acf"]["0,1"]
        b = prev[name]["acf"]["0,1"]
        print(f"    {name} r(0,1): now {a:+.6f} vs committed {b:+.6f}  "
              f"ratio {a/b:.6f}")

    print("\n=== sample-variance bias E[s^2]/sigma^2 by tile size")
    print(f"  {'plane':>6} {'tile 8':>12} {'tile 16':>12} {'tile 32':>12}")
    fac = {}
    for name in PLANES:
        fac[name] = {n: tile_factor(res[name]["_acf"], n) for n in (8, 16, 32)}
        print(f"  {name:>6} " + " ".join(f"{fac[name][n]:12.8f}" for n in (8, 16, 32)))

    gmean = {n: 0.5 * (fac["G1"][n] + fac["G2"][n]) for n in (8, 16, 32)}
    print("\n=== predicted B/green ratio distortion from IPC alone")
    print(f"  {'tile':>6} {'B/green factor':>18} {'distortion':>14}")
    pred = {}
    for n in (8, 16, 32):
        rr = fac["B"][n] / gmean[n]
        pred[n] = rr
        print(f"  {n:>6} {rr:18.8f} {100*(rr-1):+13.5f}%")

    climb_pred = 100 * (pred[32] / pred[8] - 1)
    print(f"\n  IPC predicts the B/green ratio changes by {climb_pred:+.5f}% "
          f"from tile 8 to tile 32.")

    m61 = {"109MSDCF": (160, 0.8283, 0.8464, 0.8377),
           "112MSDCF": (500, 0.8407, 0.8517, 0.8466),
           "bee-3": (100, 0.8408, 0.8607, 0.8699),
           "foam": (1000, 0.8376, 0.8529, 0.8558)}
    print(f"\n  M61 measured, tile 8 -> tile 32:")
    obs = []
    for k, (iso, t8, t16, t32) in m61.items():
        c = 100 * (t32 / t8 - 1)
        obs.append(c)
        print(f"    {k:<10} ISO {iso:>4}   {t8:.4f} -> {t32:.4f}   {c:+.3f}%")
    print(f"    mean observed climb {np.mean(obs):+.3f}%")
    print(f"\n  RULING: IPC accounts for {climb_pred:+.5f}% of an observed "
          f"{np.mean(obs):+.3f}% -> "
          f"{abs(np.mean(obs)/climb_pred) if climb_pred else float('inf'):.0f}x too small.")

    # the ISO-matched comparison
    G_MEAS = 0.5 * (json.load(open(DATA / "03-ptc.json"))["G1"]["g"]
                    + json.load(open(DATA / "03-ptc.json"))["G2"]["g"])
    gB = json.load(open(DATA / "03-ptc.json"))["B"]["g"]
    mine = gB / G_MEAS
    print(f"\n=== ISO-matched comparison")
    print(f"  M71 flat-field B/green at ISO 100 (temporal, per-pixel, no tiles)"
          f" = {mine:.4f}")
    print(f"  M61 bee-3 (ISO 100) tile 32                                     "
          f" = {m61['bee-3'][3]:.4f}")
    print(f"  M61 headline across 11 stacks, tile 8                           "
          f" = 0.8396 +- 0.0112")
    print(f"  agreement with the ISO-matched tile-32 value: "
          f"{mine/m61['bee-3'][3]:.5f}")
    print(f"  NOTE: bee-3 is the ONLY ISO-100 row in M61's table. The other "
          f"three are\n        ISO 160/500/1000 and read "
          f"{m61['109MSDCF'][3]:.4f}/{m61['112MSDCF'][3]:.4f}/{m61['foam'][3]:.4f} "
          f"at tile 32. One matching\n        row out of four is weak on its own; "
          f"it is the only matched one, which\n        is what makes it worth "
          f"reporting, not proof.")

    out = {
        "planes": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                   for k, v in res.items()},
        "tile_factor": {k: {str(n): v for n, v in fac[k].items()} for k in fac},
        "predicted_B_over_green_distortion": {str(n): pred[n] for n in pred},
        "ipc_predicted_climb_pct": climb_pred,
        "m61_observed_climb_pct": {k: 100 * (v[3] / v[1] - 1) for k, v in m61.items()},
        "m61_mean_observed_climb_pct": float(np.mean(obs)),
        "m71_ratio": mine,
        "m61_bee3_iso100_tile32": m61["bee-3"][3],
        "m71_over_m61_iso_matched": mine / m61["bee-3"][3],
        "verdict": ("IPC is orders of magnitude too small to explain M61's "
                    "tile-size climb; the climb has another cause, unruled here"),
        "frames": [pathlib.Path(grp[8]["FileName"]).name,
                   pathlib.Path(grp[9]["FileName"]).name],
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
