"""M87 / 78 -- C-INV failed in 77 at 2.768e-09 against a 1e-9 bar.  Diagnose it
rather than wave at it.

C-INV requires that multiplying every frame by a constant leaves E(d) exactly
unchanged, because E is a ratio to the far-field level.  77 measured 2.768e-09
at x1.37 and the bar FAILED as registered.

Two candidate diagnoses, and they are distinguishable:

  (i) FLOAT32 ROUND-OFF.  The frames are float32.  1.37 is not exactly
      representable in binary, so f*1.37 rounds, and the rounding survives into
      a median.  If this is the cause, a factor that IS exactly representable --
      any power of two -- must give EXACTLY zero, and non-representable factors
      must give something of order float32 epsilon.
  (ii) A REAL LEAK: my normaliser touching the denominator, in which case the
      error would not care whether the factor is a binary-exact value.

REGISTERED, before running: if every power-of-two factor gives exactly 0.0 and
every non-representable factor gives a nonzero of order 1e-9 or below, the
diagnosis is round-off, C-INV's THRESHOLD was unphysical rather than E being
non-invariant, and I restate the bar at the float32 noise floor and say the
original failed.  If a power-of-two factor gives nonzero, it is a real leak and
77's photometry shares are contaminated.
"""
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"

ISO = 100.0
FAR = (80, 120)
DMAX = 200
EXACT = (0.5, 2.0, 4.0)
INEXACT = (1.37, 1.1, 3.7)


def main():
    t0 = time.time()
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    n, h, w = cube.shape
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1

    fmask, _ = L.foreground_mask(sel0)
    dd = np.rint(distance_transform_edt(~fmask)).astype(np.int32)
    inner = np.zeros((h, w), bool)
    inner[M:M + 700, M:M + 1100] = True
    valid = (~fmask) & inner
    dv = dd[valid]
    order = np.argsort(dv, kind="stable")
    edges = np.searchsorted(dv[order], np.arange(0, DMAX + 2))

    def prof(img):
        v = img[valid][order]
        out = np.full(DMAX + 1, np.nan)
        for d in range(DMAX + 1):
            a, b = edges[d], edges[d + 1]
            if b - a >= 200:
                out[d] = np.median(v[a:b])
        return out

    def E_of(g):
        sel = np.empty((h, w), np.float32)
        Pk = np.empty((n, DMAX + 1))
        for k in range(n):
            f = (np.asarray(cube[k], dtype=np.float32) * np.float32(g)).astype(np.float32)
            Pk[k] = prof(f)
            s = argbest == k
            if s.any():
                sel[s] = f[s]
        with np.errstate(invalid="ignore"):
            e = np.nanmean(Pk, axis=0)
        return (prof(sel) - e) / float(np.nanmedian(e[FAR[0]:FAR[1] + 1]))

    base = E_of(1.0)
    fin = np.isfinite(base)
    pk, tr = 13, 92
    print(f"reference E: box {base[pk]:+.9f} at d={pk}, shelf {base[tr]:+.9f} "
          f"at d={tr}", flush=True)
    eps32 = float(np.finfo(np.float32).eps)
    floor = eps32 * max(abs(base[pk]), abs(base[tr]))
    print(f"float32 eps {eps32:.3e} -> absolute noise floor on E is "
          f"~{floor:.3e}\n", flush=True)

    rows = []
    for tag, factors in (("binary-exact", EXACT), ("not representable", INEXACT)):
        for g in factors:
            e = E_of(g)
            dall = float(np.nanmax(np.abs(e[fin] - base[fin])))
            dbt = max(abs(e[pk] - base[pk]), abs(e[tr] - base[tr]))
            rows.append({"factor": g, "kind": tag, "max_dE_all": dall,
                         "max_dE_box_shelf": dbt})
            print(f"  x{g:<6} {tag:<18} max |dE| over all d = {dall:.3e}   "
                  f"at box/shelf = {dbt:.3e}", flush=True)

    ex = [r for r in rows if r["kind"] == "binary-exact"]
    ix = [r for r in rows if r["kind"] == "not representable"]
    ex_zero = all(r["max_dE_all"] == 0.0 for r in ex)
    ix_small = all(r["max_dE_box_shelf"] <= 1e-8 for r in ix)
    print("\n" + "=" * 74 + "\n=== DIAGNOSIS ===", flush=True)
    if ex_zero and ix_small:
        diag = ("FLOAT32 ROUND-OFF.  Every binary-exact factor reproduces E "
                "bit-for-bit; only non-representable factors move it, and only "
                "at the float32 noise floor.  E is invariant; C-INV's 1e-9 "
                "THRESHOLD was below the arithmetic's own resolution and should "
                "not have been registered there.  The bar failed as written and "
                "I report it as failed.")
    elif not ex_zero:
        diag = ("REAL LEAK.  A binary-exact rescale moved E, so the normaliser "
                "is reaching the denominator and 77's shares are contaminated.")
    else:
        diag = ("INCONCLUSIVE: exact factors are clean but inexact ones move E "
                "by more than the float32 floor.")
    print(f"  {diag}", flush=True)
    smallest = 0.02348
    if ix:
        worst = max(r["max_dE_box_shelf"] for r in rows)
        print(f"  worst deviation {worst:.3e} against the smallest effect 77 "
              f"reports ({smallest:.5f}): a factor of "
              f"{smallest / max(worst, 1e-30):.3g}", flush=True)

    with open(DATA / "78-invariance.json", "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "eps32": eps32, "floor": floor,
                   "exact_all_zero": bool(ex_zero),
                   "inexact_below_1e8": bool(ix_small),
                   "diagnosis": diag, "E_box": float(base[pk]),
                   "E_shelf": float(base[tr])}, fh, indent=1)
    print(f"\nwrote {DATA / '78-invariance.json'}   {time.time() - t0:.0f}s",
          flush=True)


if __name__ == "__main__":
    main()
