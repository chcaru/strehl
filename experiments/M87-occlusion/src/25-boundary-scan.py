"""M87 step 25 -- full-frame streaming merge, then classify EVERY boundary in
bee-3-cpl by contrast polarity and by BOUNDARY-LOCAL depth separation.

Why this exists.  Step 23 scouted five hand-picked boxes with a crude statistic
(median elected frame of the Otsu-bright region vs the Otsu-dark region) and it
disqualified my own registered occluding boundary, ROI_LEG, at +10 frames --
below the |dk| >= 20 admission bar registered in addendum 3 A3.5.  That is a
failure of the STATISTIC, not of ROI_LEG: both regions are large and
heterogeneous (the "bright" region is a whole background card spanning its own
depth range), so their medians say nothing about the depth step ACROSS a
boundary.

The right statistic is boundary-local:

    k_in  = median elected frame on an interior band, EDT_in  in [3, 15]
    k_out = median elected frame on an exterior band, EDT_out in [30, 60]
    dk    = k_in - k_out

This pass also answers a question I cannot answer by eye and must not assume:
IS THERE ANY genuine bright-foreground / dark-background OCCLUDING boundary in
this capture at all?  The orchestrator proposed the pale thorax hairs and the
dark eye; step 23 measured both at |dk| <= 3 frames, i.e. reflectance edges at
a single depth, which are the PLACEBO, not a polarity test.  If the capture
contains no reversed-polarity occlusion, the honest result is that the
falsifier cannot be run on it, and I say so and name the capture needed.

Streams the stack so the full cube is never held: 299 frames at 2344x3516 would
be 9.8 TB.  Saves only full-frame best / argbest / sel.
"""
import json
import pathlib
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
CACHE = HERE / "cache"
for p in (OUT, DATA, CACHE):
    p.mkdir(exist_ok=True)

STACK = r"D:\personal\macro\bee-3-cpl"
ISO = 100


def stream_merge(stack, iso, tag):
    ab_p = CACHE / f"25-{tag}-argbest.npy"
    sel_p = CACHE / f"25-{tag}-sel.npy"
    if ab_p.exists() and sel_p.exists():
        print(f"  loaded cached full-frame merge for {tag}", flush=True)
        return np.load(ab_p), np.load(sel_p)

    files = L.frames(stack)
    n = len(files)
    h, w = L.binned_grid_shape(files[0])
    print(f"  {tag}: {n} frames, green lattice {h}x{w}", flush=True)
    best = np.full((h, w), -np.inf, np.float32)
    arg = np.zeros((h, w), np.int16)
    sel = np.zeros((h, w), np.float32)
    t0 = time.time()
    for k, p in enumerate(files):
        _, g1, g2, _ = L.read_planes(p)
        lm = 0.5 * (np.maximum(g1 - L.BLACK, 0.0) + np.maximum(g2 - L.BLACK, 0.0))
        fl = L.regularised_field(lm.astype(np.float64), iso)
        better = fl > best
        best[better] = fl[better]
        arg[better] = k
        sel[better] = lm[better]
        if k % 40 == 0:
            print(f"    {k}/{n}  {time.time() - t0:.0f}s", flush=True)
    np.save(ab_p, arg)
    np.save(sel_p, sel)
    print(f"    done in {time.time() - t0:.0f}s", flush=True)
    return arg, sel


def classify(arg, sel, tag):
    """Segment the subject, walk its boundary, and report per-boundary-point
    contrast polarity and boundary-local depth separation."""
    tau = L.otsu(sel)
    # On bee-3 the SUBJECT is the dark side (bee) and the card is bright.
    # Do not hard-code that: decide by which side touches the frame border.
    dark = sel <= tau
    border = np.zeros_like(dark)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    dark_on_border = float(dark[border].mean())
    subject_is_dark = dark_on_border < 0.5
    subj = dark if subject_is_dark else ~dark
    subj = ndi.binary_opening(subj, np.ones((5, 5)))
    subj = ndi.binary_closing(subj, np.ones((9, 9)))
    lbl, nl = ndi.label(subj)
    if nl > 1:
        sizes = ndi.sum(subj, lbl, range(1, nl + 1))
        subj = lbl == (1 + int(np.argmax(sizes)))
    print(f"  subject is the {'dark' if subject_is_dark else 'bright'} side; "
          f"{subj.mean() * 100:.1f}% of frame", flush=True)

    edt_out = ndi.distance_transform_edt(~subj)
    edt_in = ndi.distance_transform_edt(subj)

    kin = np.where((edt_in >= 3) & (edt_in <= 15), arg.astype(np.float64), np.nan)
    kout = np.where((edt_out >= 30) & (edt_out <= 60), arg.astype(np.float64),
                    np.nan)
    lin = np.where((edt_in >= 3) & (edt_in <= 15), sel.astype(np.float64), np.nan)
    lout = np.where((edt_out >= 30) & (edt_out <= 60), sel.astype(np.float64),
                    np.nan)

    # aggregate in tiles so each number is a local boundary statement
    T = 64
    h, w = arg.shape
    rows = []
    for y in range(0, h - T, T):
        for x in range(0, w - T, T):
            a = kin[y:y + T, x:x + T]
            b = kout[y:y + T, x:x + T]
            if np.isfinite(a).sum() < 200 or np.isfinite(b).sum() < 200:
                continue
            ki = float(np.nanmedian(a))
            ko = float(np.nanmedian(b))
            li = float(np.nanmedian(lin[y:y + T, x:x + T]))
            lo = float(np.nanmedian(lout[y:y + T, x:x + T]))
            rows.append(dict(y=y, x=x, k_in=ki, k_out=ko, dk=ki - ko,
                             lvl_in=li, lvl_out=lo,
                             contrast=li / max(lo, 1e-9),
                             fg_brighter=bool(li > lo)))
    print(f"  {len(rows)} boundary tiles with enough support", flush=True)

    dks = np.array([r["dk"] for r in rows])
    fgb = np.array([r["fg_brighter"] for r in rows])
    print(f"  |dk| : median {np.median(np.abs(dks)):.1f}  "
          f"p90 {np.percentile(np.abs(dks), 90):.1f}  "
          f"max {np.abs(dks).max():.1f} frames", flush=True)
    print(f"  foreground brighter than background in "
          f"{fgb.mean() * 100:.1f}% of boundary tiles", flush=True)

    ok = np.abs(dks) >= 20
    print(f"  tiles passing the |dk|>=20 occlusion bar: {ok.sum()} "
          f"({ok.mean() * 100:.1f}%)", flush=True)
    both = ok & fgb
    print(f"  ... of which foreground is BRIGHTER (reversed polarity): "
          f"{both.sum()}", flush=True)
    if both.sum():
        cand = [rows[i] for i in np.nonzero(both)[0]]
        cand.sort(key=lambda r: -abs(r["dk"]))
        print("  top reversed-polarity occluding tiles:", flush=True)
        for r in cand[:8]:
            print(f"    y={r['y']:5d} x={r['x']:5d}  dk={r['dk']:+7.1f}  "
                  f"in {r['lvl_in']:7.1f} / out {r['lvl_out']:7.1f}  "
                  f"contrast {r['contrast']:.2f}", flush=True)

    same = ok & ~fgb
    if same.sum():
        cand2 = [rows[i] for i in np.nonzero(same)[0]]
        cand2.sort(key=lambda r: -abs(r["dk"]))
        print("  top NORMAL-polarity occluding tiles (dark FG / bright BG):",
              flush=True)
        for r in cand2[:8]:
            print(f"    y={r['y']:5d} x={r['x']:5d}  dk={r['dk']:+7.1f}  "
                  f"in {r['lvl_in']:7.1f} / out {r['lvl_out']:7.1f}  "
                  f"contrast {r['contrast']:.2f}", flush=True)

    return rows, subj, subject_is_dark


def main():
    print("=== full-frame streaming merge (gate 0, green lattice) ===",
          flush=True)
    arg, sel = stream_merge(STACK, ISO, "bee3")

    print("\n=== boundary classification ===", flush=True)
    rows, subj, subj_dark = classify(arg, sel, "bee3")

    # sweep direction: which end of k is NEARER?  The bee occludes the card,
    # so the subject interior is the near layer by construction.
    kin = float(np.nanmedian(np.where(ndi.distance_transform_edt(subj) >= 3,
                                      arg.astype(np.float64), np.nan)))
    kout = float(np.nanmedian(np.where(
        ndi.distance_transform_edt(~subj) >= 30, arg.astype(np.float64), np.nan)))
    print(f"\n  subject median k = {kin:.1f}, far background median k = {kout:.1f}",
          flush=True)
    print(f"  => {'LOWER' if kin < kout else 'HIGHER'} k is NEARER in this sweep",
          flush=True)

    (DATA / "25-boundaries.json").write_text(
        json.dumps(dict(rows=rows, subject_is_dark=bool(subj_dark),
                        k_subject=kin, k_far=kout), indent=2),
        encoding="utf-8")

    lo, hi = np.percentile(sel, [0.5, 99.5])
    v = np.clip((sel - lo) / (hi - lo), 0, 1) ** (1 / 2.2)
    Image.fromarray((v[::3, ::3] * 255).astype(np.uint8)).save(
        OUT / "25-sel-prev.png")
    a = arg.astype(np.float64)
    va = np.clip((a - np.percentile(a, 1)) /
                 max(np.percentile(a, 99) - np.percentile(a, 1), 1e-9), 0, 1)
    Image.fromarray((va[::3, ::3] * 255).astype(np.uint8)).save(
        OUT / "25-argbest-prev.png")
    print("  -> out/25-sel-prev.png, out/25-argbest-prev.png, "
          "data/25-boundaries.json", flush=True)


if __name__ == "__main__":
    main()
