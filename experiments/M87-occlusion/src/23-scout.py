"""M87 step 23 -- rebase the visual reference onto M85's render, and scout for
reversed-polarity occluding boundaries.

Two jobs:

1. M85 landed a colour-managed full-resolution render an hour ago.  Every
   *visual* reference I used before that was the old binned grey-green render.
   This makes downsampled previews of the new one so the report's visual claims
   are made against what the owner is actually looking at.

   NOTE the quantitative situation, which is better than the orchestrator
   feared: every surviving number in M87 was computed from
   `bee3-leg-luma.npy`, which `04-through-focus.py` builds by calling
   `L.read_planes` -> the native Bayer green sites.  No demosaic, no white
   balance, no colour matrix, no resample, no bin, no align.  So the M85 change
   cannot move any of them.

2. The orchestrator's polarity falsifier needs boundaries where the FOREGROUND
   IS BRIGHTER THAN THE BACKGROUND.  It proposed the bee's pale thorax hairs
   against the darker body and the dark eye against pale hairs.  Both of those
   are worth a hard look before use, because a reflectance boundary at a single
   depth is my PLACEBO, not a polarity test -- the test needs a genuine
   occluding boundary (two different depths) whose contrast runs the other way.
   This script measures, per candidate box, both the contrast polarity and
   whether the two sides actually sit at different depths.

Writes previews to out/ and a depth/contrast table to data/23-scout.json.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent.parent
OUT = HERE / "out"
DATA = HERE / "data"
CACHE = HERE / "cache"
OUT.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

M85 = pathlib.Path(r"C:\dev\strehl-out\M85-before-after")
STACK = r"D:\personal\macro\bee-3-cpl"
ISO = 100


def preview(src, dst, factor):
    im = Image.open(src)
    w, h = im.size
    im2 = im.convert("RGB").resize((w // factor, h // factor), Image.LANCZOS)
    im2.save(dst)
    return (w, h), im2.size


def main():
    print("=== 1. rebase visual reference onto M85's render ===", flush=True)
    for name, factor in (("full-2-after", 6), ("full-1-before", 6)):
        src = M85 / f"{name}.png"
        if not src.exists():
            print(f"  MISSING {src}")
            continue
        full, small = preview(src, OUT / f"23-{name}-prev.png", factor)
        print(f"  {name}: {full} -> {small}  (out/23-{name}-prev.png)", flush=True)

    print("\n=== 2. scout candidate boundaries on the green lattice ===",
          flush=True)
    # Full-frame merged luma at gate 0 on a coarse decimation is too costly;
    # instead reuse the frame-wise field argmax over a set of candidate boxes.
    files = L.frames(STACK)
    n = len(files)
    print(f"  stack: {n} frames", flush=True)

    # Candidate boxes on the BINNED/green grid (y0,y1,x0,x1).
    # ROI_LEG is the registered dark-on-bright case, carried for reference.
    cands = {
        "ROI_LEG": L.ROIS["ROI_LEG"],
        "thorax_hairs": (900, 1400, 1500, 2100),
        "abdomen_left": (1150, 1650, 900, 1500),
        "head_eye": (700, 1150, 1450, 1950),
        "wing_margin": (600, 1100, 1900, 2500),
    }

    cache_p = CACHE / "23-scout-cubes.npz"
    if cache_p.exists():
        z = np.load(cache_p)
        cubes = {k: z[k] for k in z.files}
        print("  loaded cached scout cubes", flush=True)
    else:
        cubes = {}
        for tag, box in cands.items():
            h = box[1] - box[0]
            w = box[3] - box[2]
            lum = np.empty((n, h, w), np.float32)
            fld = np.empty((n, h, w), np.float32)
            for k, p in enumerate(files):
                _, g1, g2, _ = L.read_planes(p, box)
                lm = 0.5 * (np.maximum(g1 - L.BLACK, 0.0)
                            + np.maximum(g2 - L.BLACK, 0.0))
                lum[k] = lm
                fld[k] = L.regularised_field(lm.astype(np.float64), ISO)
                if k % 60 == 0:
                    print(f"    {tag} {k}/{n}", flush=True)
            ab = fld.argmax(axis=0).astype(np.int32)
            sel = np.take_along_axis(lum, ab[None], 0)[0]
            cubes[tag + "__sel"] = sel
            cubes[tag + "__arg"] = ab
            print(f"  {tag}: box {box} -> {sel.shape}", flush=True)
        np.savez_compressed(cache_p, **cubes)

    rows = []
    for tag, box in cands.items():
        sel = cubes[tag + "__sel"].astype(np.float64)
        arg = cubes[tag + "__arg"].astype(np.float64)
        tau = L.otsu(sel)
        fg = sel > tau
        # which side is which: "fg" here is merely the BRIGHT side.
        bright_lvl = float(np.median(sel[fg])) if fg.any() else float("nan")
        dark_lvl = float(np.median(sel[~fg])) if (~fg).any() else float("nan")
        bright_k = float(np.median(arg[fg])) if fg.any() else float("nan")
        dark_k = float(np.median(arg[~fg])) if (~fg).any() else float("nan")
        frac = float(fg.mean())
        rows.append(dict(tag=tag, box=list(box), tau=float(tau),
                         bright_level=bright_lvl, dark_level=dark_lvl,
                         contrast=bright_lvl / max(dark_lvl, 1e-9),
                         bright_median_k=bright_k, dark_median_k=dark_k,
                         depth_sep_frames=bright_k - dark_k,
                         bright_frac=frac))
        print(f"  {tag:14s} bright {bright_lvl:8.1f} @k={bright_k:6.1f} | "
              f"dark {dark_lvl:8.1f} @k={dark_k:6.1f} | "
              f"depth sep {bright_k - dark_k:+7.1f} frames | "
              f"bright frac {frac:.3f}", flush=True)

        lo, hi = np.percentile(sel, [0.5, 99.5])
        v = np.clip((sel - lo) / max(hi - lo, 1e-9), 0, 1) ** (1 / 2.2)
        Image.fromarray((v * 255).astype(np.uint8)).save(
            OUT / f"23-scout-{tag}.png")

    (DATA / "23-scout.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8")
    print("\n  -> data/23-scout.json", flush=True)
    print("\nINTERPRETATION GUIDE (not a result):", flush=True)
    print("  a usable reversed-polarity OCCLUDING boundary needs BOTH", flush=True)
    print("   (a) bright side is the near/foreground layer, and", flush=True)
    print("   (b) |depth_sep_frames| large -- the two sides at different focus.",
          flush=True)
    print("  |depth_sep| ~ 0 means a reflectance edge at one depth = PLACEBO.",
          flush=True)


if __name__ == "__main__":
    main()
