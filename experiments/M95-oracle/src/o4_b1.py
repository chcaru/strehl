"""O4 -- B1, the kill switch: does my modelled elector reproduce the SHIPPED one?

Everything downstream is a claim about strehl's election. That claim is only
admissible if the elector I model is the elector that ships. This is the
pre-registered kill switch from docs/research/M95-election-quality.md B1: below
80 % agreement I report that I could not model the product and I report NO
election offset at all.

HOW THE REAL ELECTION IS RECOVERED. At --gate 0 the merge averages exactly one
frame per pixel, and my own merge-vs-frame report established that the merged
output is then BYTE-IDENTICAL to the frame that won each pixel -- 180,697 px,
47 frame/ROI combinations, 100.0000 % exact, max 0 DN of 65535. So the election
map is not inferred, it is read off: for each pixel, find which rendered frame
carries exactly the bytes the merge emitted.

That gives ground truth for the elector without asking the elector anything.

FAIRNESS. Only 23 single frames were rendered, so only pixels won by one of
those 23 are testable. The modelled elector is therefore restricted to the SAME
23-frame candidate set. Letting the model choose from 299 while truth can only
be one of 23 would manufacture disagreement.
"""

from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "M95-merge-vs-frame", "src"))
import m95lib as L  # noqa: E402
import o2lib as O  # noqa: E402
from o3_commission import CUBE, OUTD  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

TIF = r"C:\dev\strehl-out\M93-out"
MERGED = os.path.join(TIF, "armM-gate0-binlin.tif")
ROIS = {"ROI-LOWDRIFT": (576, 64), "ROI-MIDDRIFT": (2112, 64),
        "ROI-HIGHDRIFT": (2368, 320), "ROI-FLAT": (2112, 1088)}
WIN = 512
MARGIN = 32


def find_offset(tif_g: np.ndarray, plane: np.ndarray) -> tuple:
    """Integer (dy, dx) mapping plane coords into the TIFF. Integer only: any
    sub-pixel registration would resample, and resampling changes exactly the
    quantity this milestone measures."""
    py, px = 900, 900
    n = 256
    ref = plane[py:py + n, px:px + n].astype(np.float64)
    ref = ref - ref.mean()
    best = None
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            c = tif_g[py + dy:py + dy + n, px + dx:px + dx + n].astype(np.float64)
            c = c - c.mean()
            r = float(np.sum(ref * c) / np.sqrt(np.sum(ref ** 2) * np.sum(c ** 2) + 1e-30))
            if best is None or r > best[0]:
                best = (r, dy, dx)
    return best


def main() -> int:
    meta = json.load(open(os.path.join(CUBE, "cube_meta.json"), encoding="utf-8"))
    black = meta["black"]

    frames = {}
    for f in sorted(os.listdir(TIF)):
        m = re.fullmatch(r"armF-f(\d+)\.tif", f)
        if m:
            frames[int(m.group(1))] = os.path.join(TIF, f)
    idx = sorted(frames)
    print(f"rendered single frames: {len(idx)}  {idx}")

    merged = L.read_tif_green(MERGED)
    print(f"merged: {merged.shape}")

    g1full = np.load(os.path.join(CUBE, "ROI-LOWDRIFT.g1.npy"), mmap_mode="r")
    print(f"cube ROI shape: {g1full.shape}")

    # Geometry: locate the plane inside the TIFF, once, on a full frame.
    ref_i = 183 if 183 in frames else idx[0]
    tif183 = L.read_tif_green(frames[ref_i])
    import rawpy  # noqa: F401
    r = L.decode_raw(os.path.join(L.STACK, meta["arw"][ref_i]))
    plane = 0.5 * (r.cfa[0::2, 1::2].astype(np.float64) + r.cfa[1::2, 0::2].astype(np.float64))
    corr, dy, dx = find_offset(tif183, plane)
    print(f"TIFF vs plane offset: dy={dy} dx={dx}  correlation r={corr:.6f}")
    assert corr > 0.95, f"could not locate the plane inside the TIFF (r={corr:.4f})"
    del plane, r

    noise_src1 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g1.npy"),
                                    mmap_mode="r")[::12], dtype=np.float64)
    noise_src2 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g2.npy"),
                                    mmap_mode="r")[::12], dtype=np.float64)
    noise, fit = O.fit_noise(noise_src1.reshape(-1, noise_src1.shape[-1]),
                             noise_src2.reshape(-1, noise_src2.shape[-1]), black)
    print(f"noise model: {noise}  R^2={fit['r2']:.5f}")
    del noise_src1, noise_src2

    tif_cache = {}
    for i in idx:
        g = L.read_tif_green(frames[i])
        for nm, (x, y) in ROIS.items():
            side = WIN + 2 * MARGIN
            ty0, tx0 = y - MARGIN + dy, x - MARGIN + dx
            tif_cache[(nm, i)] = g[ty0:ty0 + side, tx0:tx0 + side].copy()
        del g
    merged_crop = {}
    for nm, (x, y) in ROIS.items():
        side = WIN + 2 * MARGIN
        ty0, tx0 = y - MARGIN + dy, x - MARGIN + dx
        merged_crop[nm] = merged[ty0:ty0 + side, tx0:tx0 + side].copy()
    del merged

    res = {}
    tot_test = tot_agree = 0
    for nm, (x, y) in ROIS.items():
        g1 = np.load(os.path.join(CUBE, f"{nm}.g1.npy"), mmap_mode="r")
        g2 = np.load(os.path.join(CUBE, f"{nm}.g2.npy"), mmap_mode="r")
        side = g1.shape[1]

        # Truth: which rendered frame carries exactly the merged bytes?
        mcrop = merged_crop[nm]
        truth = np.full(mcrop.shape, -1, dtype=np.int32)
        nmatch = np.zeros(mcrop.shape, dtype=np.int16)
        for i in idx:
            eq = tif_cache[(nm, i)] == mcrop
            truth[eq & (nmatch == 0)] = i
            nmatch += eq.astype(np.int16)

        # Model: same 27x27 focus rule, restricted to the same candidate set.
        best = None
        arg = np.zeros((side - 2 - 2 * O.BOX_R, side - 2 - 2 * O.BOX_R), dtype=np.int32)
        for i in idx:
            binned = 0.5 * (g1[i].astype(np.float64) + g2[i].astype(np.float64))
            s = O.elector_score(binned, noise)
            if best is None:
                best = s.copy()
                arg[:] = i
            else:
                m = s > best
                best[m] = s[m]
                arg[m] = i

        k = 1 + O.BOX_R
        t = truth[k:k + arg.shape[0], k:k + arg.shape[1]]
        amb = nmatch[k:k + arg.shape[0], k:k + arg.shape[1]] > 1
        ok = (t >= 0) & (~amb)
        agree = float(np.mean(arg[ok] == t[ok])) * 100.0 if ok.sum() else float("nan")
        within1 = float(np.mean(np.abs(arg[ok] - t[ok]) <= 1)) * 100.0 if ok.sum() else float("nan")
        cov = 100.0 * float(ok.mean())
        print(f"\n{nm}")
        print(f"  testable pixels {int(ok.sum()):,} of {ok.size:,} ({cov:.2f} %) "
              f"[unmatched {100.0*float((t<0).mean()):.2f} %, ambiguous "
              f"{100.0*float(amb.mean()):.2f} %]")
        print(f"  modelled elector == shipped election : {agree:.4f} %")
        print(f"  within +/-1 frame                    : {within1:.4f} %")
        res[nm] = dict(testable=int(ok.sum()), total=int(ok.size), coverage_pct=cov,
                       agree_pct=agree, within1_pct=within1)
        if nm != "ROI-FLAT":
            tot_test += int(ok.sum())
            tot_agree += int((arg[ok] == t[ok]).sum())
        del g1, g2

    overall = 100.0 * tot_agree / max(tot_test, 1)
    print("\n" + "=" * 74)
    print(f"B1 overall (detail ROIs): {tot_agree:,}/{tot_test:,} = {overall:.4f} %")
    b1 = overall >= 80.0
    print(f"B1 {'PASS' if b1 else 'FAIL'} (pre-registered bar: >= 80 %)")
    if not b1:
        print("KILL SWITCH: the modelled elector is not the shipped elector.")
        print("No election offset will be reported.")
    res["overall_pct"] = overall
    res["passed"] = bool(b1)
    res["offset"] = dict(dy=dy, dx=dx, corr=corr)
    res["candidates"] = idx
    res["noise"] = dict(gain=noise.gain, floor=noise.floor, r2=fit["r2"])
    with open(os.path.join(OUTD, "o4_b1.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0 if b1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
