"""M40 verification, script 04 -- RE-CHOOSING THE REFERENCE, and what the flat ROI reads
under a defensible inflation.

Fact 428 reports that the corrected gate-0 detail on the flat ROI moves from +35.47% to
0.885x once SELECTION_INFLATION = 1.074 is applied, and calls the -11.5% an overshoot of
unknown size because the ROI is low-detail rather than detail-free.

Two things are re-chosen here.

(1) THE REFERENCE.  Both fact 341's +35.47% and fact 428's 0.885x are ratios against ONE
    frame: the stack's MIDDLE frame, `frames/2`, chosen by position in the file list and
    by nothing else.  On a through-focus stack the middle frame is not the in-focus frame
    for any particular ROI.  If the frames the argmax actually elects are sharper on this
    ROI than the middle frame is, then part of the "+35% detail" is not an artifact at
    all -- it is the reference being the wrong frame.  So: measure the corrected detail
    of EVERY frame on the ROI and see where the middle frame sits.

(2) THE CONSTANT.  Sweep the inflation applied to the model noise and read the retention
    off, then solve for the inflation that makes gate-0 retention exactly 1.000.  That
    number is what SELECTION_INFLATION would have to be for fact 428's own consumer.

Nothing here recomputes the author's arithmetic on the author's inputs; it changes the
reference and the constant and reports how far the conclusion moves.

PRE-REGISTERED (rule 20).  If the middle frame is at or above the median frame in
corrected detail, re-choice (1) changes nothing and the artifact interpretation stands.
If the solved constant lands at 1.074, the shipped value is right for this consumer.

Outputs: out/04-reference.txt, out/04-reference.json
"""

import glob
import json
import os
import sys
import time

import numpy as np
import rawpy

BLACK = 512.0
GAIN_DIV = 436.8
RN_E_LOW = 4.20
SIGMA_EPS = 1e-3
WINDOW_RADIUS, REG_RADIUS, MARGIN = 13, 8, 24
FOCUS_NOISE_SD = 0.015214
GATES = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0]
INFLATIONS = [1.000, 1.0124, 1.0269, 1.0307, 1.045, 1.074]

STACKS = {
    "109MSDCF": dict(
        path=r"C:\dev\macro\test\109MSDCF",
        iso=160.0,
        rois={
            "flat-M2 2272,1344": (2272, 1344, 256, 256),
            "flat-M11 2352,1408": (2352, 1408, 256, 256),
        },
    ),
    "119MSDCF": dict(
        path=r"C:\dev\macro\test\119MSDCF",
        iso=50.0,
        rois={
            "flat-M11 2896,1968": (2896, 1968, 256, 256),
            "flat-M11 3056,416": (3056, 416, 256, 256),
        },
    ),
}


def sigma_luma(S, g, read_dn):
    return np.sqrt(0.5 * (g * np.maximum(S, 0.0) + read_dn * read_dn))


def box_mean(a, r):
    H, W = a.shape
    c = np.pad(np.cumsum(np.cumsum(a, 0), 1), ((1, 0), (1, 0)))
    y0 = np.maximum(np.arange(H) - r, 0)
    y1 = np.minimum(np.arange(H) + r, H - 1)
    x0 = np.maximum(np.arange(W) - r, 0)
    x1 = np.minimum(np.arange(W) + r, W - 1)
    s = (
        c[np.ix_(y1 + 1, x1 + 1)]
        - c[np.ix_(y0, x1 + 1)]
        - c[np.ix_(y1 + 1, x0)]
        + c[np.ix_(y0, x0)]
    )
    return s / np.outer(y1 - y0 + 1, x1 - x0 + 1)


def sobel_mag(a):
    p = np.pad(a, 1, mode="edge")
    gx = (
        p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]
        - p[:-2, :-2] - 2 * p[1:-1, :-2] - p[2:, :-2]
    ) * 0.125
    gy = (
        p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]
        - p[:-2, :-2] - 2 * p[:-2, 1:-1] - p[:-2, 2:]
    ) * 0.125
    return np.hypot(gx, gy)


def raw_rms(v):
    dx = v[:-1, 1:] - v[:-1, :-1]
    dy = v[1:, :-1] - v[:-1, :-1]
    return float(np.sqrt((dx * dx + dy * dy).mean()))


def noise_rms(sig):
    s2 = sig**2
    return float(np.sqrt((2 * s2[:-1, :-1] + s2[:-1, 1:] + s2[1:, :-1]).mean()))


def corrected(r, n):
    return float(np.sqrt(max(0.0, r * r - n * n)))


def load_stack(path, iso, rois):
    frames = sorted(glob.glob(os.path.join(path, "*.ARW")))
    g = iso / GAIN_DIV
    read_dn = RN_E_LOW * g
    acc = {k: dict(L=[], reg=[]) for k in rois}
    t0 = time.time()
    for p in frames:
        r = rawpy.imread(p)
        a = r.raw_image_visible
        for k, (x, y, w, h) in rois.items():
            cx, cy, cw, ch = x - MARGIN, y - MARGIN, w + 2 * MARGIN, h + 2 * MARGIN
            sub = a[2 * cy : 2 * (cy + ch), 2 * cx : 2 * (cx + cw)].astype(np.float64)
            g1 = sub[0::2, 1::2]
            g2 = sub[1::2, 0::2]
            luma_f = 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))
            focus = box_mean(sobel_mag(luma_f), WINDOW_RADIUS) / np.maximum(
                sigma_luma(luma_f, g, read_dn), SIGMA_EPS
            )
            acc[k]["reg"].append(box_mean(focus, REG_RADIUS).astype(np.float32))
            acc[k]["g1"].append(g1) if "g1" in acc[k] else None
            acc[k]["L"].append(0.5 * (g1 + g2) - BLACK)
        del r, a
    print(f"    decoded {len(frames)} frames in {time.time() - t0:.1f}s", flush=True)
    return frames, g, read_dn, acc


def main():
    out = open("out/04-reference.txt", "w", encoding="utf-8")

    def emit(s=""):
        print(s, flush=True)
        out.write(s + "\n")

    emit("=" * 104)
    emit("M40 script 04 -- the reference frame, and the inflation the detail metric needs")
    emit("=" * 104)
    emit("")
    results = {}
    for stack, cfg in STACKS.items():
        emit(f"### stack {stack}  iso {cfg['iso']:.0f}")
        frames, g, read_dn, acc = load_stack(cfg["path"], cfg["iso"], cfg["rois"])
        N = len(frames)
        middle = N // 2
        sl = (slice(MARGIN, MARGIN + 256), slice(MARGIN, MARGIN + 256))
        for k, (x, y, w, h) in cfg["rois"].items():
            L = np.stack(acc[k]["L"])[:, sl[0], sl[1]]
            R = np.stack(acc[k]["reg"])[:, sl[0], sl[1]]
            Rfull = np.stack(acc[k]["reg"])
            best = R.max(axis=0)
            win = R.argmax(axis=0)

            per_frame = []
            for j in range(N):
                v = L[j]
                sg = sigma_luma(v, g, read_dn)
                per_frame.append(corrected(raw_rms(v), noise_rms(sg)))
            per_frame = np.array(per_frame)
            order = np.argsort(-per_frame)
            rank_of_middle = int(np.where(order == middle)[0][0])
            counts = np.bincount(win.ravel(), minlength=N)
            modal = int(np.argmax(counts))

            emit(f"  --- ROI {k} ---")
            emit(
                "    corrected detail of EACH frame on this ROI (single frame, no merge), DN:"
            )
            emit("      " + " ".join(f"{v:.2f}" for v in per_frame))
            emit(
                f"    middle frame is f{middle} at {per_frame[middle]:.4f} DN -- rank "
                f"{rank_of_middle + 1} of {N} (1 = sharpest)."
                f"  best is f{int(order[0])} at {per_frame[order[0]]:.4f} DN "
                f"({per_frame[order[0]] / per_frame[middle]:.4f}x the middle frame)"
            )
            emit(
                f"    the merge's MODAL winner here is f{modal} "
                f"({100 * counts[modal] / counts.sum():.1f}% of pixels) at "
                f"{per_frame[modal]:.4f} DN = {per_frame[modal] / per_frame[middle]:.4f}x "
                f"the middle frame"
            )
            base_mid = per_frame[middle]
            base_best = per_frame[order[0]]

            rows = {}
            emit("")
            emit(
                "      gate  mean n   raw_rms   noise_rms  " +
                "".join(f"  ret@{i:.4f}" for i in INFLATIONS) + "   I* (ret=1 vs mid)"
            )
            for gate in GATES:
                tol = gate * np.sqrt(2.0) * FOCUS_NOISE_SD
                admit = best[None] - R <= tol
                admit[win, np.arange(h)[:, None], np.arange(w)[None, :]] = True
                n = admit.sum(axis=0)
                merged = (L * admit).sum(axis=0) / n
                sg = sigma_luma(merged, g, read_dn) / np.sqrt(n)
                r = raw_rms(merged)
                cells = []
                vals = {}
                for infl in INFLATIONS:
                    nr = noise_rms(sg * np.where(n <= 1, infl, 1.0))
                    c = corrected(r, nr)
                    cells.append(f"  {c / base_mid:8.4f}x")
                    vals[f"{infl:.4f}"] = dict(corrected=c, ret_mid=c / base_mid,
                                               ret_best=c / base_best)
                nr1 = noise_rms(sg)
                # solve for the scalar multiplier on the WHOLE noise term that makes the
                # retention exactly 1.000 against the middle-frame reference
                target = r * r - base_mid * base_mid
                istar = float(np.sqrt(target) / nr1) if target > 0 else float("nan")
                emit(
                    f"      {gate:4.2f}  {n.mean():6.3f}  {r:8.4f}  {nr1:10.4f}"
                    + "".join(cells)
                    + f"   {istar:8.4f}x"
                )
                rows[gate] = dict(mean_n=float(n.mean()), raw_rms=r, noise_rms=nr1,
                                  istar=istar, by_inflation=vals)
            emit("")
            results[f"{stack} | {k}"] = dict(
                per_frame=[float(v) for v in per_frame],
                middle=middle,
                middle_rank=rank_of_middle + 1,
                best_frame=int(order[0]),
                modal_winner=modal,
                base_mid=float(base_mid),
                base_best=float(base_best),
                gates=rows,
            )
        del acc
        emit("")

    json.dump(results, open("out/04-reference.json", "w"), indent=1)
    emit("=" * 104)
    emit("SUMMARY -- gate 0")
    emit("=" * 104)
    emit(
        f"  {'ROI':34s} {'mid rank':>9s} {'best/mid':>9s} {'ret@1.000':>10s} "
        f"{'ret@1.074':>10s} {'I*':>8s}"
    )
    for name, r in results.items():
        g0 = r["gates"][0.0]
        emit(
            f"  {name:34s} {r['middle_rank']:6d}/{len(r['per_frame']):<3d} "
            f"{r['base_best'] / r['base_mid']:8.4f}x "
            f"{g0['by_inflation']['1.0000']['ret_mid']:9.4f}x "
            f"{g0['by_inflation']['1.0740']['ret_mid']:9.4f}x {g0['istar']:7.4f}x"
        )
    out.close()


if __name__ == "__main__":
    sys.exit(main())
