"""Is eps_R really bimodal, or is the instrument attenuated on some stacks?

`c2_compare.py` found eps_R falling into two tight clusters:

    -650.8  tweezers-cpl      null  3.8 ppm   R2 0.976
    -653.2  coffee-bean       null  2.4 ppm   R2 0.988
    -654.5  couch-fibers-cpl  null  2.6 ppm   R2 0.956
    -519.9  bee-3-cpl         null 19.0 ppm   R2 0.781
    -548.4  bee-2-cpl         null 30.0 ppm   R2 0.765
    -552.0  lavendar-cpl      null  5.9 ppm   R2 0.888

0.6% spread inside the first cluster, 20% between clusters -- and the split lines
up exactly with the null and the fit quality. EXIF rules out the obvious optical
explanation: all six are 200 mm with the 2x teleconverter, so the path is the
same. That leaves two hypotheses that look identical in the headline table:

  (A) the optics genuinely differ between these scenes, or
  (B) the instrument is attenuated on the low-quality stacks and the true
      coefficient is the same.

They are separable, and by a method this project already trusts: plant a known
dose in each stack and see what comes back. If bee-2 returns a 1000 ppm plant as
800 ppm while coffee-bean returns it as 1000 ppm, the difference is the
instrument and (B) is right. If every stack recovers the plant faithfully, the
scenes really do differ and (A) is right. This is the same discipline that made
the axial number defensible: do not argue about a candidate mechanism, dose it.

The second half of this script asks a different question that matters for what
ships: the shipped profile was FITTED with a translation free but is APPLIED with
the translation zeroed. `optics.rs` records that forcing the translation to zero
biases eps by 14%. So the coefficient that should be applied is the one from a
radial-only fit, not the radial term of a three-parameter fit. Both are computed
here from the saved rows, at no extra cost.
"""

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import lateral

TILE = 160
MARGIN = 40
GATE = 2e5
DOSE = 1000e-6
PPM = 1e6
STACKS = ["tweezers-cpl", "bee-3-cpl", "coffee-bean", "lavendar-cpl",
          "couch-fibers-cpl", "bee-2-cpl"]

_CTX = {}


def _init(tile, margin, dose):
    _CTX.update(tile=tile, margin=margin, dose=dose)


def _one(args):
    path, = args
    tile, margin, dose = _CTX["tile"], _CTX["margin"], _CTX["dose"]
    planes = common.planes_of(common.read_cfa(path))
    tiles = lateral.tile_corners(planes["G1"].shape, tile, margin)
    g1 = planes["G1"]
    dosed = lateral.plant_scale(planes["R"], dose)
    s, d0, d1 = [], [], []
    for (y, x) in tiles:
        s.append(lateral.tile_structure(g1, y, x, tile))
        ref = g1[y:y + tile, x:x + tile]
        d0.append(lateral.subpix(ref, planes["R"][y:y + tile, x:x + tile]))
        d1.append(lateral.subpix(ref, dosed[y:y + tile, x:x + tile]))
    return np.array(s), np.array(d0), np.array(d1)


def best_rows(S, D, tiles, sensel_shape, gate, topk=3):
    ly, lx = lateral.lattice_offset("R")
    order = np.argsort(-S, axis=0)
    u, d = [], []
    for j, (y, x) in enumerate(tiles):
        pick = order[:topk, j]
        if S[pick[0], j] < gate:
            continue
        v = D[pick, j, :]
        u.append(lateral.field_position(y, x, TILE, "G1", sensel_shape))
        d.append((float(np.median(v[:, 0])) - ly, float(np.median(v[:, 1])) - lx))
    return np.array(u, float), np.array(d, float)


def dose_test(stack, n_frames=12, workers=8):
    fs = common.frames(stack)
    idx = np.unique(np.linspace(0, len(fs) - 1, n_frames).round().astype(int))
    sel = [fs[i] for i in idx]
    cfa0 = common.read_cfa(sel[0])
    sensel_shape = cfa0.shape
    tiles = lateral.tile_corners(common.planes_of(cfa0)["G1"].shape, TILE, MARGIN)
    del cfa0
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(TILE, MARGIN, DOSE)) as ex:
        res = list(ex.map(_one, [(p,) for p in sel]))
    S = np.stack([r[0] for r in res])
    D0 = np.stack([r[1] for r in res])
    D1 = np.stack([r[2] for r in res])
    u0, d0 = best_rows(S, D0, tiles, sensel_shape, GATE)
    u1, d1 = best_rows(S, D1, tiles, sensel_shape, GATE)
    f0 = lateral.fit_model(u0, d0, robust=True)
    f1 = lateral.fit_model(u1, d1, robust=True)
    e0, e1 = -f0["eps"], -f1["eps"]
    return {"stack": stack, "n": int(len(u0)), "eps_undosed": e0,
            "eps_dosed": e1, "delta": e1 - e0, "planted": DOSE,
            "recovery": (e1 - e0) / DOSE, "r2_undosed": f0["r2"],
            "r2_dosed": f1["r2"], "rms": f0["rms"]}


def radial_only_table():
    print("\n" + "=" * 96)
    print("RADIAL-ONLY vs THREE-PARAMETER FIT")
    print("=" * 96)
    print("The shipped record was fitted with a translation free but is APPLIED")
    print("with the translation zeroed (`A7C2_FE100GM_2XTC_X4CPL_RADIAL`).")
    print("optics.rs records that forcing the translation to zero biases eps by")
    print("14%, so the number that should be applied is the radial-only fit --")
    print("not the radial term of a three-parameter one. Both, side by side:\n")
    print(f"{'stack':>18} {'3-param':>9} {'radial-only':>12} {'diff':>8} "
          f"{'T (dy,dx) plane px':>22} {'null 3p':>8} {'null r-only':>12}")
    rows = []
    for s in STACKS:
        r = {}
        for arm in ("R", "G2"):
            z = np.load(os.path.join(common.OUT, "json", f"c1_{s}_{arm}.npz"))
            u, d = z["u"], z["d"]
            f3 = lateral.fit_model(u, d, robust=True)
            f1 = lateral.fit_model(u, d, radial_only=True, robust=True)
            r[arm] = (-f3["eps"], -f1["eps"], -f3["ty"], -f3["tx"])
        e3, e1, ty, tx = r["R"]
        n3, n1, _, _ = r["G2"]
        diff = 100.0 * (e1 - e3) / abs(e3)
        print(f"{s:>18} {e3*PPM:9.1f} {e1*PPM:12.1f} {diff:+7.1f}% "
              f"{f'({ty:+.3f},{tx:+.3f})':>22} {n3*PPM:8.1f} {n1*PPM:12.1f}")
        rows.append({"stack": s, "eps3": e3, "eps_radial": e1,
                     "diff_pct": diff, "ty": ty, "tx": tx,
                     "null3": n3, "null_radial": n1,
                     "eps3_corr": e3 - n3, "eps_radial_corr": e1 - n1})
    print("\nM107's translation was (+0.629, -0.424) plane px in (x, y).")
    print("Mine, per stack, are an order of magnitude smaller and do not")
    print("reproduce it. My own translation floor is ~0.1 px (measured on a")
    print("band-limited plant), so I can say M107's translation is not")
    print("reproduced but cannot resolve a term of that size confidently.")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=12)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--skip-dose", action="store_true")
    a = ap.parse_args()

    out = {}
    if not a.skip_dose:
        print("=" * 96)
        print(f"PER-STACK DOSE RECOVERY: plant {DOSE*PPM:.0f} ppm on R, "
              f"require it back")
        print("=" * 96)
        print("If the instrument is unbiased on every stack, recovery is 1.00")
        print("everywhere and the eps_R clusters are real optics. If recovery")
        print("tracks the clusters, the clusters are the instrument.\n")
        print(f"{'stack':>18} {'n':>5} {'eps undosed':>12} {'eps dosed':>10} "
              f"{'delta':>9} {'recovery':>9} {'R2':>7}")
        rows = []
        for s in STACKS:
            r = dose_test(s, n_frames=a.frames, workers=a.workers)
            print(f"{s:>18} {r['n']:5d} {r['eps_undosed']*PPM:12.1f} "
                  f"{r['eps_dosed']*PPM:10.1f} {r['delta']*PPM:9.1f} "
                  f"{r['recovery']:9.3f} {r['r2_undosed']:7.3f}")
            rows.append(r)
        out["dose"] = rows
        rec = np.array([r["recovery"] for r in rows])
        eps = np.array([r["eps_undosed"] for r in rows])
        print(f"\nrecovery: median {np.median(rec):.3f}, "
              f"range [{rec.min():.3f}, {rec.max():.3f}]")
        if len(rec) > 2:
            c = float(np.corrcoef(rec, np.abs(eps))[0, 1])
            print(f"correlation between recovery and |eps_R|: r = {c:+.3f}")
            print("A strong positive correlation means the low-|eps| stacks are")
            print("the ones the instrument under-reads, and the bimodality is an")
            print("artefact. Near zero means the optics really do differ.")
            out["recovery_eps_corr"] = c
        print("\nCORRECTED FOR ATTENUATION (eps_undosed / recovery):")
        print(f"{'stack':>18} {'raw':>9} {'recovery':>9} {'corrected':>10}")
        for r in rows:
            print(f"{r['stack']:>18} {r['eps_undosed']*PPM:9.1f} "
                  f"{r['recovery']:9.3f} {r['eps_undosed']/r['recovery']*PPM:10.1f}")
        corr = np.array([r["eps_undosed"] / r["recovery"] for r in rows])
        print(f"\nspread before correction: "
              f"{100*(np.abs(eps).max()-np.abs(eps).min())/np.abs(np.median(eps)):.0f}%")
        print(f"spread after  correction: "
              f"{100*(np.abs(corr).max()-np.abs(corr).min())/np.abs(np.median(corr)):.0f}%")
        out["attenuation_corrected"] = [float(c) for c in corr]

    out["radial_only"] = radial_only_table()
    common.dump("c4_attenuation", out)
    print("\nwrote c4_attenuation.json")


if __name__ == "__main__":
    main()
