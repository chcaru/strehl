"""M116-promotion -- score the DELTA dose ladder (prereg-ladder.txt).

Reuses score_halo.py's metrics UNCHANGED: same halo index, same Otsu,
same foreground_mask, same highpass. Nothing about the ruler was adjusted for
the ladder; only the arms are new.

Two things differ from score_halo.py by design, both traceable to source read
S3 (`Plan::build` fills `treated` from mask and yoke only, `delta` appears
nowhere in the predicate):

  * The treated pixel set is GEOMETRIC (mask & yoke), built once on H0, and
    shared by every rung. score_halo.py derived it empirically as "pixels that
    changed", which is correct for a binary A/B but wrong for a ladder: a low
    dose forbids few frames and therefore changes few pixels, so an empirical
    set would shrink at the bottom of the ladder and every rung would be scored
    on a different population. Scoring the identical population at every rung is
    the whole reason the ladder can be read.

  * D_or restricts D to ORIENTED content -- structure-tensor coherence >= 0.6,
    selected on H0, which is not a compared arm. This is the hairs-and-claws
    statistic, and the case on which the analogous CA control failed by 93%.

Run: python score_ladder.py
"""

import json
import hashlib
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

import score as S
import score_halo as SH

ROOT = Path(r"C:\dev\strehl-out\M116")
HALO = ROOT / "halo"

COH_MIN = 0.6      # prereg-ladder section 2, D_or
TENSOR_SIGMA = 2.0
HP_BOX = 5         # score.highpass's box; the control erosion is HP_BOX + 2

# Rung label -> delta actually in force. H1/H2 were rendered by run_halo.ps1.
RUNGS = [("L1", 1), ("L5", 5), ("L10", 10), ("L20", 20),
         ("H1", 40), ("H2", 80), ("L160", 160)]

SUBJECTS = ["bee-3-cpl", "flower-bud-with-background-fern-cpl"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def oriented_mask(g: np.ndarray) -> np.ndarray:
    """Structure-tensor coherence, (l1-l2)/(l1+l2) >= COH_MIN.

    Hairs, claws and antennae are locally one-dimensional, so they sit at high
    coherence; noise and flat background sit near zero. Selected on H0 only.
    """
    gy, gx = np.gradient(g.astype(np.float64))
    jxx = ndimage.gaussian_filter(gx * gx, TENSOR_SIGMA)
    jyy = ndimage.gaussian_filter(gy * gy, TENSOR_SIGMA)
    jxy = ndimage.gaussian_filter(gx * gy, TENSOR_SIGMA)
    tr = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    l1 = tr / 2.0 + disc
    l2 = tr / 2.0 - disc
    with np.errstate(divide="ignore", invalid="ignore"):
        coh = np.where(tr > 0, (l1 - l2) / np.maximum(tr, 1e-30), 0.0)
    return coh >= COH_MIN, coh


def detail(hp: np.ndarray, m: np.ndarray):
    """log10 of high-pass amplitude over a mask. NaN if the mask is too thin."""
    if m.sum() < 5000:
        return float("nan"), 0
    sd = float(hp[m].std())
    return (float(np.log10(sd)) if sd > 0 else float("nan")), int(m.sum())


def main() -> None:
    out = {"pinned_sha": "4beac7300e318f6f0aaf10b6a88e57f311b9e814",
           "coh_min": COH_MIN, "subjects": {}}

    # ---- LB1: the dead rung ------------------------------------------------
    lz = HALO / "measure" / "bee-3-cpl__LZ.tif"
    h1 = HALO / "measure" / "bee-3-cpl__H1.tif"
    h0 = HALO / "measure" / "bee-3-cpl__H0.tif"
    if lz.exists():
        a, b, c = sha256(lz), sha256(h1), sha256(h0)
        out["LB1_dead_rung"] = {
            "delta0_sha": a[:12], "delta40_sha": b[:12], "H0_sha": c[:12],
            "delta0_equals_delta40": a == b,
            "delta0_equals_off": a == c,
        }
        print(f"LB1 dead rung: d0={a[:12]} d40={b[:12]} "
              f"identical={a == b}")

    for subj in SUBJECTS:
        print(f"\n==== {subj} ====", flush=True)
        mdir = HALO / "measure"
        p0 = mdir / f"{subj}__H0.tif"
        paths = {lab: mdir / f"{subj}__{lab}.tif" for lab, _ in RUNGS}
        missing = [lab for lab, p in paths.items() if not p.exists()]
        if missing or not p0.exists():
            print(f"  SKIP, missing: {missing}")
            continue

        rec = {"rungs": {}}

        # ---- the ruler is built ONCE, on H0 -------------------------------
        g0 = S.green(p0)
        fg, tau = SH.foreground_mask(g0)
        d = ndimage.distance_transform_edt(~fg)
        treated = (~fg) & (d <= SH.YOKE) & (d > 0)
        # The control is the untreated set eroded by the high-pass support,
        # because an untouched pixel within HP_BOX//2 + 1 of a touched one
        # still changes value under a box filter.
        untouched = ~treated
        control = ndimage.binary_erosion(
            untouched, structure=np.ones((3, 3), bool),
            iterations=HP_BOX + 2)
        orient, coh = oriented_mask(g0)
        t_or = treated & orient
        c_or = control & orient

        rec["mask"] = {
            "tau": tau,
            "fg_pct": 100.0 * float(fg.mean()),
            "treated_px": int(treated.sum()),
            "treated_pct": 100.0 * float(treated.mean()),
            "control_px": int(control.sum()),
            "oriented_pct": 100.0 * float(orient.mean()),
            "treated_oriented_px": int(t_or.sum()),
            "control_oriented_px": int(c_or.sum()),
        }
        print(f"  tau {tau:.1f}  treated {rec['mask']['treated_pct']:.3f}%  "
              f"oriented&treated {int(t_or.sum())} px")

        hp0 = S.highpass(g0)
        d0_t, _ = detail(hp0, treated)
        d0_c, _ = detail(hp0, control)
        d0_to, _ = detail(hp0, t_or)
        d0_co, _ = detail(hp0, c_or)

        hi0 = SH.halo_index(g0, fg)
        rec["H0"] = {"sha256": sha256(p0)[:12], "H": hi0["H"],
                     "D_treated_abs": d0_t, "D_control_abs": d0_c,
                     "D_or_treated_abs": d0_to}
        print(f"  H0: H={hi0['H']:+.5f}")

        for lab, delta in RUNGS:
            g = S.green(paths[lab])
            hp = S.highpass(g)
            hi = SH.halo_index(g, fg)
            dt, nt = detail(hp, treated)
            dc, nc = detail(hp, control)
            dto, nto = detail(hp, t_or)
            dco, nco = detail(hp, c_or)
            changed = int(np.any(
                tifffile.imread(p0) != tifffile.imread(paths[lab]),
                axis=2).sum())
            r = {
                "delta": delta,
                "sha256": sha256(paths[lab])[:12],
                "H": hi["H"] if hi else None,
                "dHALO_pct": (100.0 * (hi["H"] - hi0["H"]) / hi0["H"]
                              if hi and hi0["H"] else None),
                "D": dt - d0_t,           # dex, relative to H0, treated set
                "D_control": dc - d0_c,   # must stay at 0
                "D_or": dto - d0_to,      # oriented, treated
                "D_or_control": dco - d0_co,
                "changed_px": changed,
                "n": {"treated": nt, "control": nc,
                      "t_or": nto, "c_or": nco},
            }
            rec["rungs"][lab] = r
            print(f"  {lab:>4} d={delta:>3}  H={r['H']:+.5f}  "
                  f"dHALO={r['dHALO_pct']:+8.2f}%  D={r['D']:+.5f}  "
                  f"D_or={r['D_or']:+.5f}  ctl={r['D_control']:+.5f}  "
                  f"changed={changed}")

        # ---- adjacent-rung differences, per ORCH --------------------------
        labs = [l for l, _ in RUNGS]
        adj = []
        for i in range(1, len(labs)):
            a, b = labs[i - 1], labs[i]
            ra, rb = rec["rungs"][a], rec["rungs"][b]
            adj.append({
                "step": f"{a}->{b}",
                "d_delta": rb["delta"] - ra["delta"],
                "dH_pct": rb["dHALO_pct"] - ra["dHALO_pct"],
                "dD": rb["D"] - ra["D"],
                "dD_or": rb["D_or"] - ra["D_or"],
            })
        rec["adjacent"] = adj

        # ---- LB4 exchange rate --------------------------------------------
        # X = dHALO% per unit detail spent. Only formable where detail was in
        # fact spent (D < 0) -- a rung that lost no detail has no exchange rate.
        xs = {}
        for lab, _ in RUNGS:
            r = rec["rungs"][lab]
            if r["D"] is not None and r["D"] < -0.002:
                xs[lab] = r["dHALO_pct"] / (-r["D"])
        rec["LB4_exchange"] = {
            "X": xs,
            "n_formable": len(xs),
            "spread": (max(xs.values()) / min(xs.values())
                       if len(xs) >= 2 and min(xs.values()) > 0 else None),
            "signs": sorted({("+" if v > 0 else "-") for v in xs.values()}),
        }

        out["subjects"][subj] = rec

    (HALO / "scores-ladder.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {HALO / 'scores-ladder.json'}")


if __name__ == "__main__":
    main()
