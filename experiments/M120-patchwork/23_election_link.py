"""M120d -- ORCH's two open questions, answered from cached pipeline data.

ORCH asks for `strehl stack --index-map`. I do not need it for `bee-3-cpl`: the
cached pipeline focus field `bee3-leg-field.npy` (299,744,1144) IS the post-
regulariser field the shipped merge elects on, and its argmax reproduces the
cached `bee3-leg-argbest` at 100.00% (verified in step 14). So the election is
already observable at the pixel level here.

GATE DISCIPLINE (ORCH's caution, merge.rs:298 vs :3027):
  T2 is a pure argmax = single winner = GATE 0 BY CONSTRUCTION. Stated as such.
  T1 is run at BOTH gate 0 and the shipped gate 4, labelled separately.

READER DISCIPLINE (fact 1615): every .tif via tifffile + dtype assert.

=====================================================================
PRE-REGISTERED, WRITTEN BEFORE THE RUN
=====================================================================

T2 -- ORCH's kill test. "Its patch size should scale with the focus-measure
window radius. If patch size does not move when the window radius moves, my
chain has a broken link."

  Sweep WINDOW_RADIUS r in {0,2,4,8,13,20,28}, regulariser OFF, measure
  area-weighted equivalent diameter of constant-index patches in smooth
  background. Fit eq_diam against window diameter D = 2r+1.

  CONFIRM the link : slope > 0.5 px/px AND R^2 > 0.8 AND monotone increasing.
  BREAK  the link  : slope < 0.2 px/px OR not monotone.
  Anything between is reported as EQUIVOCAL and neither is claimed.

T1 -- the link ORCH says is unmeasured: "the merge elects different frames in
different regions, and regions therefore inherit their frame's level."

  ORCH measured (a) level drift is a smooth ramp in frame index, and (b)
  correcting levels removes the blotches. The untested middle is whether
  background luma actually tracks the elected index. Regress merged background
  luma on the effective elected index (at gate 4 the merge averages many frames,
  so the effective index is the ADMISSION-WEIGHTED MEAN index, which is the
  correct generalisation of "which frame did this pixel come from").

  CONFIRM : |rho| > 0.3 at gate 0 AND null |rho| < 0.1.
  REFUTE  : |rho| < 0.1 at gate 0 -- then regions do NOT inherit their frame's
            level and ORCH's chain has a broken link at the step he flagged.
  Secondary prediction (falsifiable): the effective-index SPREAD is much
  narrower at gate 4 than gate 0, which is why gate 4 halves the defect.

VALIDATION GATE: gating the cached field at 4*UNIT must reproduce the pipeline's
known n_eff = 166.8. If it does not, I report nothing from T1.
"""
import json
import numpy as np
from scipy import ndimage as ndi, stats
from pathlib import Path
from PIL import Image

C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
FOCUS_NOISE_SD = 0.015214          # merge.rs:187
UNIT = np.sqrt(2.0) * FOCUS_NOISE_SD
N_EFF_PIPELINE = 166.8             # merge.rs run, verified in step 19
RADII = [0, 2, 4, 8, 13, 20, 28]
SHIPPED_R = 13                     # focus.rs:899 WINDOW_RADIUS


def sigma_luma(dn):
    return np.sqrt(np.maximum(dn - 100.0, 0.0) * 0.229 + 1.47 ** 2) * 0.229 / np.sqrt(2.0)


def grad_mag(a):
    return np.hypot(ndi.sobel(a, 0, mode="nearest"), ndi.sobel(a, 1, mode="nearest"))


def box(a, r):
    return a if r == 0 else ndi.uniform_filter(a, 2 * r + 1, mode="nearest")


def patch_diam(idx, mask):
    """Area-weighted equivalent diameter of constant-index patches."""
    tot = 0.0
    lab, n = ndi.label(mask & np.isin(idx, np.unique(idx[mask])), structure=np.ones((3, 3)))
    # relabel properly: components of equal index within mask
    out_areas = []
    for v in np.unique(idx[mask]):
        lab, n = ndi.label((idx == v) & mask, structure=np.ones((3, 3)))
        if n:
            out_areas.append(np.bincount(lab.ravel())[1:])
    a = np.concatenate(out_areas).astype(np.float64)
    aw = float((a * a).sum() / a.sum())        # area-weighted mean area
    return 2.0 * np.sqrt(aw / np.pi), int(a.size), aw


def main():
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    K, H, W = luma.shape
    bg = np.load(OUT / "m1_bg_mask.npy")
    argbest = np.load(C / "bee3-leg-argbest.npy")
    print(f"cube {luma.shape}  background mask {bg.sum():,} px ({100*bg.mean():.1f}%)\n")

    # ---------------- T2: ORCH's kill test -------------------------------
    print("=" * 70)
    print("T2  PATCH SIZE vs FOCUS-MEASURE WINDOW RADIUS   [gate 0 by construction:")
    print("    a pure argmax elects exactly one frame, which IS gate 0]")
    print("=" * 70)
    best = {r: np.full((H, W), -np.inf, np.float32) for r in RADII}
    bidx = {r: np.zeros((H, W), np.int32) for r in RADII}
    for k in range(K):
        f = np.asarray(luma[k], np.float32)
        g = grad_mag(f)
        sig = sigma_luma(f)
        for r in RADII:
            resp = box(g, r) / sig
            hit = resp > best[r]
            best[r][hit] = resp[hit]
            bidx[r][hit] = k
        if k % 60 == 0:
            print(f"  frame {k:3d}/{K}")

    rows = []
    for r in RADII:
        d, ncomp, aw = patch_diam(bidx[r], bg)
        rows.append(dict(r=r, D=2 * r + 1, eq_diam=d, ncomp=ncomp, aw_area=aw))
        print(f"  r={r:3d}  window {2*r+1:3d}x{2*r+1:<3d}  #patch {ncomp:>8,}"
              f"  eq diam {d:7.2f} px")

    D = np.array([x["D"] for x in rows], float)
    Y = np.array([x["eq_diam"] for x in rows], float)
    sl, ic, rv, pv, se = stats.linregress(D, Y)
    mono = bool(np.all(np.diff(Y) > 0))
    verdict_t2 = ("LINK CONFIRMED" if (sl > 0.5 and rv ** 2 > 0.8 and mono)
                  else "LINK BROKEN" if (sl < 0.2 or not mono) else "EQUIVOCAL")
    print(f"\n  fit eq_diam = {sl:.3f} * D + {ic:.2f}   R^2 = {rv**2:.4f}  p = {pv:.3g}")
    print(f"  monotone increasing: {mono}")
    print(f"  PRE-REGISTERED VERDICT (T2): {verdict_t2}")
    print(f"  [rule: confirm if slope>0.5 and R^2>0.8 and monotone; break if slope<0.2]")
    print(f"  ratio patch/window at shipped r=13: "
          f"{Y[RADII.index(SHIPPED_R)]/(2*SHIPPED_R+1):.3f}")

    # ---------------- T1: does luma track the elected frame? --------------
    print("\n" + "=" * 70)
    print("T1  DOES BACKGROUND LUMA TRACK THE ELECTED FRAME INDEX?")
    print("=" * 70)
    field = np.load(C / "bee3-leg-field.npy", mmap_mode="r")
    fmax = np.full((H, W), -np.inf, np.float32)
    for k in range(K):
        np.maximum(fmax, np.asarray(field[k], np.float32), out=fmax)

    res = {}
    for gate in (0.0, 4.0):
        thr = fmax - gate * UNIT
        num = np.zeros((H, W), np.float64)
        den = np.zeros((H, W), np.float64)
        lsum = np.zeros((H, W), np.float64)
        for k in range(K):
            adm = (np.asarray(field[k], np.float32) >= thr)
            num += adm * k
            den += adm
            lsum += adm * np.asarray(luma[k], np.float32)
        eff = num / np.maximum(den, 1)
        merged = lsum / np.maximum(den, 1)
        n_eff = float(den[bg].mean())
        res[gate] = (eff, merged, n_eff)
        print(f"\n  gate {gate:.0f}:  n_eff over background = {n_eff:.1f} frames"
              f"   effective-index sd = {eff[bg].std():.2f}"
              f"   p1-p99 spread = {np.subtract(*np.percentile(eff[bg],[99,1])):.1f}")

    n4 = res[4.0][2]
    ok = abs(n4 - N_EFF_PIPELINE) / N_EFF_PIPELINE < 0.05
    print(f"\n  VALIDATION GATE: gate-4 n_eff {n4:.1f} vs pipeline {N_EFF_PIPELINE} "
          f"-> {'PASS' if ok else 'FAIL - T1 NOT REPORTED'}")
    if not ok:
        json.dump(dict(t2=rows, t2_verdict=verdict_t2, t1="REFUSED", n_eff=n4),
                  open("m9_election.json", "w"), indent=1)
        return

    smooth = bg & (ndi.uniform_filter(np.asarray(luma[K // 2], np.float32), 9,
                                      mode="nearest") > 0)
    out_t1 = {}
    for gate in (0.0, 4.0):
        eff, merged, _ = res[gate]
        x, y = eff[smooth], merged[smooth]
        rho = stats.spearmanr(x, y)
        yn = np.roll(np.roll(merged, 331, 0), 557, 1)[smooth]
        rho_n = stats.spearmanr(x, yn)
        sl2, ic2, rv2, _, _ = stats.linregress(x, y)
        print(f"\n  gate {gate:.0f}  luma vs effective index : rho {rho.statistic:+.4f}"
              f"  p {rho.pvalue:.3g}   slope {sl2:+.2f} DN/frame")
        print(f"         NULL (merged shifted 331,557): rho {rho_n.statistic:+.4f}"
              f"  p {rho_n.pvalue:.3g}")
        lo, hi = np.percentile(x, [1, 99])
        print(f"         predicted level swing across the elected-index range "
              f"= {abs(sl2)*(hi-lo):.1f} DN "
              f"({100*abs(sl2)*(hi-lo)/np.median(y):.2f}% of median luma)")
        out_t1[str(gate)] = dict(rho=float(rho.statistic), p=float(rho.pvalue),
                                 rho_null=float(rho_n.statistic), slope=float(sl2),
                                 swing=float(abs(sl2) * (hi - lo)),
                                 swing_pct=float(100 * abs(sl2) * (hi - lo) / np.median(y)),
                                 n_eff=res[gate][2], eff_sd=float(eff[smooth].std()))
    r0, rn0 = out_t1["0.0"]["rho"], out_t1["0.0"]["rho_null"]
    verdict_t1 = ("CHAIN CONFIRMED" if abs(r0) > 0.3 and abs(rn0) < 0.1
                  else "CHAIN BROKEN" if abs(r0) < 0.1 else "EQUIVOCAL")
    print(f"\n  PRE-REGISTERED VERDICT (T1): {verdict_t1}")

    # picture: election vs render, shipped gate
    eff4 = res[4.0][0]
    eff0 = res[0.0][0]
    ys, xs = slice(476, 604), slice(442, 570)
    pan = []
    for nm, a in (("elected idx gate0", eff0[ys, xs]), ("elected idx gate4", eff4[ys, xs]),
                  ("merged luma gate0", res[0.0][1][ys, xs]),
                  ("merged luma gate4", res[4.0][1][ys, xs])):
        lo, hi = np.percentile(a, [1, 99])
        v = np.clip((a - lo) / (hi - lo + 1e-9), 0, 1)
        pan.append(np.array(Image.fromarray((v * 255).astype(np.uint8))
                            .resize((300, 300), Image.NEAREST)))
    Image.fromarray(np.vstack([np.hstack(pan[:2]), np.hstack(pan[2:])])).save(
        OUT / "M8-election-vs-render.png")
    print("  wrote M8-election-vs-render.png")

    json.dump(dict(t2=rows, t2_slope=sl, t2_r2=rv ** 2, t2_verdict=verdict_t2,
                   t1=out_t1, t1_verdict=verdict_t1),
              open("m9_election.json", "w"), indent=1)
    print("\nwrote m9_election.json")


if __name__ == "__main__":
    main()
