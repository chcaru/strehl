"""
b4_controls.py -- the two controls the brief makes mandatory, plus rule 2.

Arm A  LOW-CONTRAST NEGATIVE CONTROL
    The brief: "run the identical measurement on a subject and region where you
    predict NO effect ... a low-contrast flat region where no channel has a
    well-defined peak. If your instrument reports a confident per-channel offset
    there too, your instrument is broken."

    This is the RIGHT null for the axial question because it matches the
    treatment in STRUCTURE (rule 3): same stack, same optics, same registration
    track, same estimator, same box support, same frame count. The ONLY thing
    that changes is that the through-focus curve has no prominence. An additive
    random null would not have been admissible.

    Two sub-arms:
      A1  points that produce an interior unimodal peak but FAIL the prominence
          gate -- the instrument is forced to answer where it should not.
      A2  the tiles with the lowest median prominence, as whole tiles.

    Rule 4: the control is binned by radius too, and its radial trend is
    reported, because a control that trends on the binning axis is not a
    control on that axis.

Arm B  QUANTISATION DOSE-RESPONSE (rule 2)
    "Quantisation contaminates POOLED statistics, not just differences."
    The algebraic argument says we are safe: the raw step is 1 ADU and shot
    noise at the working level is ~40 ADU, so the input is dithered ~40x over.
    But rule 5 says form-based triage rules do not work here, so the argument
    is not accepted as a substitute. This plants a dose-response ladder in the
    quantisation step -- 1, 4, 16, 64, 256 ADU -- and re-measures dR, dB and the
    NULL at each. If the headline is a quantisation artefact it must move along
    the ladder.

    The ladder shares one decode per frame across all doses, so it costs one
    stack pass, not five.
"""
import os
import sys
import time

import numpy as np

from common import (OUT, PLANES, WIN, frames, read_cfa, planes_of, grad_energy,
                    integral, box_at, parabola_peak, dump)
from b1_curves import CX, CY, PLANE_W, PLANE_H
import b2_analyse as b2

QUANT_DOSES = (1, 4, 16, 64, 256)     # ADU; 1 = native (no coarsening)


# --------------------------------------------------------------------------
# Arm A: low-contrast negative control
# --------------------------------------------------------------------------
def radial_fit(rad, val):
    """Least-squares slope of val on radius, with a permutation p-value."""
    ok = np.isfinite(val)
    r, v = rad[ok], val[ok]
    if r.size < 4:
        return dict(n=int(r.size), slope=float("nan"), r2=float("nan"),
                    p=float("nan"))
    A = np.polyfit(r, v, 1)
    pred = np.polyval(A, r)
    ss = np.sum((v - v.mean()) ** 2)
    r2 = 1.0 - np.sum((v - pred) ** 2) / ss if ss > 0 else float("nan")
    rng = np.random.default_rng(20260825)
    hits = 0
    for _ in range(2000):
        p = np.polyfit(r, rng.permutation(v), 1)
        if abs(p[0]) >= abs(A[0]):
            hits += 1
    return dict(n=int(r.size), slope=float(A[0]), r2=float(r2),
                p=(hits + 1) / 2001.0,
                centre_to_corner=float(A[0] * (r.max() - r.min())))


def arm_a(stack="lavendar-cpl", tag="main", thr=1.5):
    z = b2.load(stack, tag)
    res, nt, npt = b2.peaks(z)
    rad = z["rad"].ravel()
    track_ok = np.repeat(z["track_res"] <= 2.0, npt)

    kR, kG1, kG2, kB = (res[c]["k"] for c in PLANES)
    kG = 0.5 * (kG1 + kG2)
    dR, dB, dN = kR - kG, kB - kG, kG1 - kG2

    interior = np.ones(kR.shape, bool)
    for c in PLANES:
        interior &= res[c]["ok"]
    prom = np.minimum.reduce([res[c]["prom"] for c in PLANES])

    treat = interior & track_ok & (prom >= thr)          # the headline arm
    a1 = interior & track_ok & (prom < thr)              # forced low-contrast

    # A3: the instrument is FORCED to answer where it wanted to decline.
    #
    # A1 turned out to be empty: the prominence gate never binds, because the
    # interior+unimodal test rejects a flat curve first. So "the instrument
    # reports nothing on flat regions" is true but untestable as written --
    # a control that cannot fire is not a control. A3 removes the refusal:
    # every point the estimator rejected is re-estimated by the same parabola
    # about its argmax, with no quality test at all. These are, by
    # construction, the points where no channel has a well-defined peak, which
    # is precisely the region the brief names. If the instrument's arithmetic
    # manufactures a per-channel offset, it will appear here.
    a3 = (~interior) & track_ok

    # A2: whole tiles ranked by median prominence
    pt = prom.reshape(nt, npt)
    it = interior.reshape(nt, npt)
    tile_prom = np.array([np.median(pt[t][it[t]]) if it[t].sum() >= 12
                          else np.nan for t in range(nt)])
    order = np.argsort(np.where(np.isfinite(tile_prom), tile_prom, np.inf))
    n_low = max(6, int(round(0.25 * np.isfinite(tile_prom).sum())))
    low_tiles = order[:n_low]
    a2 = np.zeros(nt, bool)
    a2[low_tiles] = True
    a2 = np.repeat(a2, npt) & interior & track_ok

    out = {"stack": stack, "gate_thr": thr, "arms": {},
           "n_total_points": int(kR.size),
           "frac_rejected_by_estimator": float((~interior).mean())}
    for name, sel in (("treatment", treat), ("A1_low_prominence", a1),
                      ("A2_low_prominence_tiles", a2),
                      ("A3_forced_no_peak", a3)):
        if sel.sum() == 0:
            continue
        tw = {}
        for lbl, v in (("dR", dR), ("dB", dB), ("NULL_G1_G2", dN)):
            tv, keep = b2.tilewise(v, sel, nt, npt)
            tw[lbl] = dict(
                pooled_median=float(np.median(v[sel])),
                tilewise_mean=float(np.mean(tv[keep])) if keep.sum() else float("nan"),
                tilewise_sem=float(np.std(tv[keep], ddof=1) / np.sqrt(keep.sum()))
                if keep.sum() > 1 else float("nan"),
                n_tiles=int(keep.sum()),
                frac_negative=float(np.mean(v[sel] < 0)))
        # radial behaviour of this arm (rule 4)
        tvR, keepR = b2.tilewise(dR, sel, nt, npt)
        tvN, keepN = b2.tilewise(dN, sel, nt, npt)
        tr = z["rad"].reshape(nt, npt).mean(axis=1)
        out["arms"][name] = {
            "n_points": int(sel.sum()),
            "frac_points": float(sel.mean()),
            "median_prominence": float(np.median(prom[sel])),
            "stats": tw,
            "radial_dR": radial_fit(tr[keepR], tvR[keepR]),
            "radial_NULL": radial_fit(tr[keepN], tvN[keepN]),
        }
    return out


# --------------------------------------------------------------------------
# Arm B: quantisation dose-response
# --------------------------------------------------------------------------
def quantise(cfa, step):
    """Coarsen to `step` ADU. step=1 returns the native array untouched."""
    if step <= 1:
        return cfa
    return np.round(cfa / step) * step


def arm_b(stack="lavendar-cpl", tag="main", doses=QUANT_DOSES, max_tiles=None):
    """Re-measure the focus curves at each quantisation dose.

    Reuses the registration track already saved by b1_curves so that the only
    thing varying across the ladder is the quantisation, and so that the
    integer-shift discipline of rule 6 is inherited unchanged.
    """
    z = b2.load(stack, tag)
    idy, idx = z["idy"], z["idx"]
    px0, py0 = z["px"], z["py"]
    nt, npt = px0.shape
    fs = frames(stack)
    nk = int(z["nk"])
    assert len(fs) == nk, f"frame count changed: {len(fs)} vs {nk}"

    # restrict to the tiles that carry signal, to keep the ladder affordable
    res, _, _ = b2.peaks(z)
    prom = np.minimum.reduce([res[c]["prom"] for c in PLANES]).reshape(nt, npt)
    ok = np.ones(prom.shape, bool)
    for c in PLANES:
        ok &= res[c]["ok"].reshape(nt, npt)
    good = np.array([(ok[t] & (prom[t] >= 1.5)).sum() >= 12 for t in range(nt)])
    good &= (z["track_res"] <= 2.0)
    tsel = np.where(good)[0]
    if max_tiles:
        tsel = tsel[:max_tiles]
    print(f"== quantisation ladder on {stack}: {nk} frames, "
          f"{len(tsel)}/{nt} tiles, doses {doses}")

    F = {d: {c: np.zeros((nk, len(tsel), npt), np.float32) for c in PLANES}
         for d in doses}
    t0 = time.time()
    for k, path in enumerate(fs):
        cfa = read_cfa(path)
        yy = py0[tsel] + idy[k][tsel][:, None]
        xx = px0[tsel] + idx[k][tsel][:, None]
        for d in doses:
            pls = planes_of(quantise(cfa, d))
            for c in PLANES:
                sat = integral(grad_energy(pls[c].astype(np.float32)))
                F[d][c][k] = box_at(sat, yy, xx, WIN).astype(np.float32)
        if k % 40 == 0:
            print(f"   {k}/{nk}  ({time.time()-t0:.0f}s)", flush=True)

    out = {"stack": stack, "doses": list(doses), "n_tiles": int(len(tsel)),
           "n_frames": nk, "ladder": {}}
    for d in doses:
        r = {}
        for c in PLANES:
            A = F[d][c].reshape(nk, -1).astype(np.float64)
            kh, pk, pr, interior, uni = parabola_peak(A)
            r[c] = dict(k=kh, prom=pr, ok=interior & uni)
        conf = np.ones(r["R"]["k"].shape, bool)
        for c in PLANES:
            conf &= r[c]["ok"] & (r[c]["prom"] >= 1.5)
        kG = 0.5 * (r["G1"]["k"] + r["G2"]["k"])
        dR = r["R"]["k"] - kG
        dB = r["B"]["k"] - kG
        dN = r["G1"]["k"] - r["G2"]["k"]
        ent = {"n_conf": int(conf.sum()),
               "frac_conf": float(conf.mean())}
        for lbl, v in (("dR", dR), ("dB", dB), ("NULL_G1_G2", dN)):
            tv, keep = b2.tilewise(v, conf, len(tsel), npt)
            ent[lbl] = dict(
                pooled_median=float(np.median(v[conf])) if conf.sum() else float("nan"),
                tilewise_mean=float(np.mean(tv[keep])) if keep.sum() else float("nan"),
                tilewise_sem=float(np.std(tv[keep], ddof=1) / np.sqrt(keep.sum()))
                if keep.sum() > 1 else float("nan"),
                n_tiles=int(keep.sum()),
                frac_negative=float(np.mean(v[conf] < 0)) if conf.sum() else float("nan"))
        out["ladder"][str(d)] = ent
        print(f"   dose {d:4d} ADU  n={ent['n_conf']:6d}  "
              f"dR {ent['dR']['pooled_median']:+.4f}  "
              f"dB {ent['dB']['pooled_median']:+.4f}  "
              f"NULL {ent['NULL_G1_G2']['pooled_median']:+.4f}")
    return out


def show_a(o):
    print(f"===== ARM A negative control: {o['stack']} =====")
    hdr = f"{'arm':<26}{'n':>8}{'medprom':>9}{'dR':>10}{'dB':>10}{'NULL':>10}{'sign_dR':>9}"
    print(hdr)
    for name, a in o["arms"].items():
        s = a["stats"]
        print(f"{name:<26}{a['n_points']:>8}{a['median_prominence']:>9.2f}"
              f"{s['dR']['pooled_median']:>+10.4f}"
              f"{s['dB']['pooled_median']:>+10.4f}"
              f"{s['NULL_G1_G2']['pooled_median']:>+10.4f}"
              f"{100*s['dR']['frac_negative']:>8.1f}%")
    print("  radial behaviour of each arm (rule 4):")
    for name, a in o["arms"].items():
        rd, rn = a["radial_dR"], a["radial_NULL"]
        print(f"   {name:<26} dR: R2 {rd['r2']:.4f} p {rd['p']:.4f} | "
              f"NULL: R2 {rn['r2']:.4f} p {rn['p']:.4f}")


if __name__ == "__main__":
    args = sys.argv[1:]
    which = args[0] if args else "a"
    stack = args[1] if len(args) > 1 else "lavendar-cpl"
    if which == "a":
        o = arm_a(stack)
        show_a(o)
        dump(f"b4_armA_{stack}", o)
    elif which == "b":
        o = arm_b(stack)
        dump(f"b4_armB_{stack}", o)
        print("done")
