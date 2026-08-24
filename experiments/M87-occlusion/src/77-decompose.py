"""M87 / 77 -- the shelf moved under photometric normalisation; decide WHY.

76 established two things about ORCH's photometric-step hypothesis:

  BOX (the bright veil at the silhouette): refuted.  Survives gain+offset
  normalisation at 102.22% and level-only normalisation at 116.32%, while a
  planted +/-10% per-frame ramp is removed at 89.0%.
  SHELF (the darker stand-off band): moved.  Gain+offset normalisation removes
  54.3% of it, level-only removes 37.8%, and a shuffled normaliser that corrects
  nothing moves it the OTHER way (+55.7% deeper).

But normalising the frames does two things at once: it changes what the merge
COMPOSITES, and it changes the focus measure, so it changes WHAT THE ELECTION
PICKS.  Under level-only normalisation the election still moved at 10.708% of
pixels.  76 cannot tell those apart, and the difference is the whole claim: only
the first is ORCH's mechanism.  The second would be my own election artifact
wearing a photometric costume.

So: hold one factor fixed at a time.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

The 2x2.  Elect from {original frames, level-normalised frames}; composite from
{original frames, level-normalised frames}; all four cells, same E(d).

  cell 00  elect original,   composite original    == the shipped merge
  cell 10  elect original,   composite normalised  == PHOTOMETRY ALONE
  cell 01  elect normalised, composite original    == ELECTION ALONE
  cell 11  elect normalised, composite normalised  == 76's A3 arm

B1 -- PHOTOMETRY SHARE = (E00 - E10) / (E00 - E11) at the shelf.
B2 -- ELECTION SHARE   = (E00 - E01) / (E00 - E11) at the shelf.
    REGISTERED: whichever exceeds 0.60 is named as the driver.  If neither does,
    the effect is interactive and I say that instead of picking a winner.  The
    two shares need not sum to 1; an interaction term is expected and reported.

B3 -- the same two shares at the BOX, reported whatever they are.  76 says the
    box is indifferent to photometry; this is the sharper version of that test,
    because cell 10 changes the composite WITHOUT touching the election at all.

C-ID -- IDENTITY CHECK.  Cell 00 must reproduce the cached E(d) to 1e-9 at every
    finite distance.  A decomposition harness that cannot reproduce the thing it
    is decomposing is measuring its own plumbing.  Registered as a hard abort.

C-INV -- INVARIANCE CHECK, and this one is a trap I set for myself.  E is a
    RATIO to the far-field level, so any GLOBAL rescale of every frame must
    leave E exactly unchanged.  Multiply every frame by 1.37 and require
    |dE| <= 1e-9 at the box and the shelf.  If this fails, the "photometry"
    I am attributing to ORCH's mechanism is partly my own normaliser leaking
    into the denominator.

READ-ONLY: D:\\personal\\macro.
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
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")

ISO = 100.0
FAR = (80, 120)
REF_D = 140
DMAX = 200
GLOBAL_RESCALE = 1.37


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def main():
    t0 = time.time()
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
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
    ref_px = valid & (dd >= REF_D)

    def prof(img):
        v = img[valid][order]
        out = np.full(DMAX + 1, np.nan)
        for d in range(DMAX + 1):
            a, b = edges[d], edges[d + 1]
            if b - a >= 200:
                out[d] = np.median(v[a:b])
        return out

    lvl = np.empty(n)
    for k in range(n):
        lvl[k] = float(np.asarray(cube[k], dtype=np.float32)[ref_px].mean())
    Lref = float(lvl.mean())
    scale = (Lref / lvl).astype(np.float32)
    print(f"level-normalisation factors: min {scale.min():.5f} max "
          f"{scale.max():.5f}  (true exposure p-p "
          f"{100 * (lvl.max() - lvl.min()) / Lref:.3f}%)", flush=True)

    def frame(k, norm, g=1.0):
        f = np.asarray(cube[k], dtype=np.float32) * np.float32(g)
        return (f * scale[k]).astype(np.float32) if norm else f

    def election(norm, g=1.0):
        best = np.full((h, w), -np.inf, np.float32)
        arg = np.zeros((h, w), np.int32)
        for k in range(n):
            fl = L.regularised_field(frame(k, norm, g), ISO)
            b = fl > best
            best[b] = fl[b]
            arg[b] = k
        return arg

    def E_of(arg, norm, g=1.0):
        sel = np.empty((h, w), np.float32)
        Pk = np.empty((n, DMAX + 1))
        for k in range(n):
            f = frame(k, norm, g)
            Pk[k] = prof(f)
            s = arg == k
            if s.any():
                sel[s] = f[s]
        with np.errstate(invalid="ignore"):
            e = np.nanmean(Pk, axis=0)
        return (prof(sel) - e) / float(np.nanmedian(e[FAR[0]:FAR[1] + 1]))

    print("\n--- electing twice (original frames, level-normalised frames) ---",
          flush=True)
    arg_o = election(False)
    arg_n = election(True)
    moved = float((arg_o != arg_n).mean())
    print(f"  election moved at {100 * moved:.3f}% of pixels", flush=True)

    print("\n--- the 2x2 ---", flush=True)
    E00 = E_of(arg_o, False)
    E10 = E_of(arg_o, True)
    E01 = E_of(arg_n, False)
    E11 = E_of(arg_n, True)

    fin = np.isfinite(E00)
    cached = np.array(json.load(open(DATA / "76-photometric-audit.json",
                                     encoding="utf-8"))["E_base"], float)
    err = float(np.nanmax(np.abs(E00[fin] - cached[fin])))
    print(f"  C-ID  cell 00 against 76's baseline: max |dE| = {err:.3e}  "
          f"({'OK' if err <= 1e-9 else 'ABORT'})", flush=True)
    if err > 1e-9:
        raise SystemExit(f"C-ID FAILED at {err:.3e}: harness does not reproduce "
                         f"the merge it claims to decompose")

    pk = int(np.nanargmax(np.where(fin, E00, -np.inf)[1:121])) + 1
    tr = int(np.nanargmin(np.where(fin, E00, np.inf)[1:121])) + 1

    E00g = E_of(arg_o, False, GLOBAL_RESCALE)
    inv = max(abs(E00g[pk] - E00[pk]), abs(E00g[tr] - E00[tr]))
    print(f"  C-INV every frame x{GLOBAL_RESCALE}: max |dE| at box and shelf = "
          f"{inv:.3e}  ({'OK' if inv <= 1e-9 else 'FAIL'})", flush=True)

    rows = []
    for name, d0 in (("BOX", pk), ("SHELF", tr)):
        tot = E00[d0] - E11[d0]
        ph = E00[d0] - E10[d0]
        el = E00[d0] - E01[d0]
        s_ph = ph / tot if abs(tot) > 1e-9 else float("nan")
        s_el = el / tot if abs(tot) > 1e-9 else float("nan")
        inter = 1.0 - s_ph - s_el
        print(f"\n  {name} at d={d0}", flush=True)
        print(f"    00 shipped                  {E00[d0]:+.5f}", flush=True)
        print(f"    10 photometry alone         {E10[d0]:+.5f}   "
              f"share {100 * s_ph:+7.1f}%", flush=True)
        print(f"    01 election alone           {E01[d0]:+.5f}   "
              f"share {100 * s_el:+7.1f}%", flush=True)
        print(f"    11 both (76's A3)           {E11[d0]:+.5f}   "
              f"total change {tot:+.5f}", flush=True)
        print(f"    interaction                 {100 * inter:+7.1f}%", flush=True)
        if abs(tot) < 1e-4:
            drv = "NOTHING MOVED: total change below the reporting floor"
        elif s_ph > 0.60 and s_ph >= s_el:
            drv = "PHOTOMETRY (ORCH's mechanism)"
        elif s_el > 0.60 and s_el > s_ph:
            drv = "THE ELECTION (my mechanism)"
        else:
            drv = "INTERACTIVE: neither factor exceeds the registered 0.60"
        print(f"    -> driver: {drv}", flush=True)
        rows.append({"feature": name, "d": d0, "E00": float(E00[d0]),
                     "E10": float(E10[d0]), "E01": float(E01[d0]),
                     "E11": float(E11[d0]), "total": float(tot),
                     "share_photometry": float(s_ph),
                     "share_election": float(s_el),
                     "share_interaction": float(inter), "driver": drv})

    print("\n" + "=" * 74 + "\n=== VERDICT ===", flush=True)
    for r in rows:
        print(f"  {r['feature']:>5} at d={r['d']:<4} photometry "
              f"{100 * r['share_photometry']:+7.1f}%   election "
              f"{100 * r['share_election']:+7.1f}%   -> {r['driver']}",
              flush=True)

    rep = {"election_moved": moved, "C_ID_err": err, "C_INV_err": float(inv),
           "C_ID_ok": bool(err <= 1e-9), "C_INV_ok": bool(inv <= 1e-9),
           "Lref": Lref, "pk": pk, "tr": tr, "rows": rows,
           "E00": E00.tolist(), "E10": E10.tolist(), "E01": E01.tolist(),
           "E11": E11.tolist()}
    with open(DATA / "77-decompose.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        d = np.arange(DMAX + 1)
        fig, ax = plt.subplots(figsize=(8.4, 4.6))
        ax.axhline(0, color="k", lw=0.6)
        ax.plot(d, E00, color="C3", lw=1.6, label="00 shipped merge")
        ax.plot(d, E10, color="C0", lw=1.3, label="10 photometry alone")
        ax.plot(d, E01, color="C2", lw=1.3, ls="--", label="01 election alone")
        ax.plot(d, E11, color="C1", lw=1.1, ls=":", label="11 both")
        ax.axvline(pk, color="0.7", lw=0.7)
        ax.axvline(tr, color="0.7", lw=0.7)
        ax.set_xlim(0, 130)
        ax.set_xlabel("distance from subject, px")
        ax.set_ylabel("E(d)")
        ax.set_title("what does level normalisation actually move?")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / "77-decompose.png", dpi=130)
        print(f"  wrote {OUT / '77-decompose.png'}", flush=True)
    except Exception as exc:  # pragma: no cover
        print(f"  (no figure: {exc})", flush=True)

    print(f"\nwrote {DATA / '77-decompose.json'}   {time.time() - t0:.0f}s",
          flush=True)


if __name__ == "__main__":
    main()
