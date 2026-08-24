"""M111 -- the gate arms, the synthetic-injection control, and the visuals.

Arm F: `--gate` is swept with the shipping 17x17 regulariser in place. The
mechanism claim is that the waxy patches are single-frame regions produced when
the gate's ABSOLUTE tolerance (threshold * sqrt(2) * FOCUS_NOISE_SD) collapses
admission in the intermediate focus-response band. If that is right:

  gate -> 0     every pixel is one elected frame; patches at their worst
  gate = 4      shipping; patches present
  gate -> inf   every pixel is the mean of all 299 frames; patches gone,
                and the whole image is a defocused mush -- which is the point:
                the fix cannot simply be "open the gate".

NC3 (discipline 722): a synthetic patchwork of known amplitude is injected into
the HIGH-admission flat population -- the population where the detector reads
0.897, i.e. below its null -- and pushed through the identical `edge_step`. A
detector that cannot see a planted signal cannot be trusted when it reports one.

Usage:  python gate_arms.py
"""

import json
import os

import numpy as np
import tifffile
from scipy import ndimage

ROOT = r"C:\dev\strehl-out\M111"
RENDER = os.path.join(ROOT, "render")
GATES = [("g0p25", 0.25), ("g1", 1.0), ("g4", 4.0), ("g16", 16.0), ("g64", 64.0),
         ("g100000", 100000.0)]
FLAT_SD = 300.0
LOW_N = 8
HIGH_N = 64
SHIFTS = [(137, 211), (-263, 89), (451, -337)]
MARGIN = 64
RNG = np.random.default_rng(111)


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def plane_luma(path):
    y = luma(tifffile.imread(path))
    return 0.25 * (y[0::2, 0::2] + y[1::2, 0::2] + y[0::2, 1::2] + y[1::2, 1::2])


def local_sd(y, r=4):
    k = 2 * r + 1
    m = ndimage.uniform_filter(y, k, mode="nearest")
    m2 = ndimage.uniform_filter(y * y, k, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def edge_step(idx, y, mask):
    dh = idx[:, 1:] != idx[:, :-1]
    dv = idx[1:, :] != idx[:-1, :]
    mh = mask[:, 1:] & mask[:, :-1]
    mv = mask[1:, :] & mask[:-1, :]
    step = np.concatenate([np.abs(y[:, 1:] - y[:, :-1])[mh], np.abs(y[1:, :] - y[:-1, :])[mv]])
    on = np.concatenate([dh[mh], dv[mv]])
    if step.size < 5000 or on.sum() < 500 or (~on).sum() < 500:
        return None
    a, b = float(np.median(step[on])), float(np.median(step[~on]))
    return {"pairs": int(step.size), "bdens": float(on.mean()), "on": a, "off": b,
            "ratio": a / max(b, 1e-9)}


def null_ratio(idx, y, mask):
    r = [edge_step(np.roll(idx, s, (0, 1)), y, mask) for s in SHIFTS]
    r = [x for x in r if x]
    return (float(np.mean([x["ratio"] for x in r])),
            float(np.std([x["ratio"] for x in r], ddof=1))) if r else (None, None)


def flatness_score(y, mask):
    """How waxy is the flat population? Two complementary scalars.

    `interior_sd` -- the median 9x9 local sd inside plateau interiors. Waxy
    means the interior carries less variation than the defocused optics deliver.
    `hard_frac`   -- the fraction of in-mask pixels whose 1-px luma difference
    exceeds 4x the population's own median difference. Waxy means hard edges in
    a region that is otherwise flat.
    """
    sd = local_sd(y)
    d = np.abs(np.diff(y, axis=1))
    dm = np.zeros(y.shape, bool)
    dm[:, 1:] = mask[:, 1:] & mask[:, :-1]
    vals = d[dm[:, 1:]]
    if vals.size < 1000:
        return None
    med = float(np.median(vals))
    return {"interior_sd_median": float(np.median(sd[mask])),
            "step_median": med,
            "hard_frac": float((vals > 4 * max(med, 1e-9)).mean())}


def nc3_injection(y, idx, high_mask, amplitude):
    """Plant a patchwork of known amplitude and re-detect it (discipline 722)."""
    src = np.roll(idx, (911, 577), (0, 1))
    offs = RNG.normal(0.0, amplitude, size=int(src.max()) + 1).astype(np.float32)
    planted = y.copy()
    planted[high_mask] += offs[src[high_mask]]
    got = edge_step(src, planted, high_mask)
    base = edge_step(src, y, high_mask)
    return {"amplitude_dn": amplitude, "planted_ratio": got["ratio"],
            "unplanted_ratio": base["ratio"],
            "planted_on": got["on"], "unplanted_on": base["on"]}


def crop(y, x0, y0, w, h, lo, hi):
    a = y[y0:y0 + h, x0:x0 + w]
    a = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)
    return (a * 255).astype(np.uint8)


def main():
    st8 = os.path.join(RENDER, "state-r8")
    y8 = plane_luma(os.path.join(RENDER, "marker-dump.tif"))
    ne8 = np.load(os.path.join(st8, "n_eff_gate4.00.npy"))
    idx8 = np.load(os.path.join(st8, "best_index.npy"))
    inner = np.zeros(y8.shape, bool)
    inner[MARGIN:-MARGIN, MARGIN:-MARGIN] = True
    flat8 = (local_sd(y8) < FLAT_SD) & inner
    low8 = flat8 & (ne8 <= LOW_N)
    high8 = flat8 & (ne8 >= HIGH_N)

    res = {"nc3": [], "gate_arms": []}
    for amp in (0.0, 3.0, 6.0, 12.0, 24.0):
        res["nc3"].append(nc3_injection(y8, idx8, high8, amp))
    print("--- NC3 synthetic injection into the HIGH-admission flat population ---")
    print(f"{'amp DN':>8} {'planted ratio':>14} {'unplanted':>11} {'planted on':>11}")
    for r in res["nc3"]:
        print(f"{r['amplitude_dn']:8.1f} {r['planted_ratio']:14.3f}"
              f" {r['unplanted_ratio']:11.3f} {r['planted_on']:11.2f}")

    print("\n--- Arm F: gate sweep (17x17 regulariser in place, masks FIXED at gate 4) ---")
    print(f"{'arm':>9} {'gate':>9} {'n_eff':>8} {'low%flat':>9} {'edge on/off':>12}"
          f" {'null':>14} {'intSD':>8} {'hard%':>7}")
    for tag, g in GATES:
        tif = os.path.join(RENDER, f"marker-{tag}.tif")
        st = os.path.join(RENDER, f"state-{tag}")
        if not os.path.exists(tif):
            print(f"{tag:>9}   MISSING")
            continue
        y = plane_luma(tif)
        idx = np.load(os.path.join(st, "best_index.npy"))
        nes = [f for f in os.listdir(st) if f.startswith("n_eff_gate")]
        ne = np.load(os.path.join(st, nes[0]))
        e = edge_step(idx, y, low8)
        nr, ns = null_ratio(idx, y, low8)
        fs = flatness_score(y, low8)
        row = {"arm": tag, "gate": g, "n_eff_mean": float(ne[inner].mean()),
               "low_frac_of_flat": float((flat8 & (ne <= LOW_N)).sum() / flat8.sum()),
               "edge_low_fixedmask": e, "null_ratio": nr, "null_sd": ns, "flatness": fs}
        res["gate_arms"].append(row)
        print(f"{tag:>9} {g:9.2f} {row['n_eff_mean']:8.1f} {row['low_frac_of_flat']:9.4f}"
              f" {e['ratio']:12.3f} {nr:8.3f}+-{ns:.3f}"
              f" {fs['interior_sd_median']:8.1f} {100 * fs['hard_frac']:7.3f}")

    with open(os.path.join(ROOT, "gate_arms.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

    # visual sheet: blobB at output (2048,1300) 320x300 -> plane (1024,650) 160x150
    px, py, pw, ph = 1024, 650, 160, 150
    lo, hi = 20000.0, 40000.0
    sheets = [("r0", "marker-r0.tif"), ("r8", "marker-dump.tif"), ("r32", "marker-r32.tif"),
              ("g0.25", "marker-g0p25.tif"), ("g4", "marker-g4.tif"),
              ("g1e5", "marker-g100000.tif")]
    tiles, labels = [], []
    for lab, fn in sheets:
        p = os.path.join(RENDER, fn)
        if not os.path.exists(p):
            continue
        tiles.append(np.repeat(np.repeat(crop(plane_luma(p), px, py, pw, ph, lo, hi), 2, 0), 2, 1))
        labels.append(lab)
    if tiles:
        gap = np.zeros((tiles[0].shape[0], 8), np.uint8)
        sheet = tiles[0]
        for t in tiles[1:]:
            sheet = np.concatenate([sheet, gap, t], 1)
        dst = os.path.join(ROOT, "_ARMS-blobB.png")
        tifffile.imwrite(dst.replace(".png", ".tif"), sheet)
        try:
            from PIL import Image, ImageDraw

            im = Image.fromarray(sheet).convert("RGB")
            d = ImageDraw.Draw(im)
            for i, lab in enumerate(labels):
                d.text((i * (pw * 2 + 8) + 6, 4), lab, fill=(255, 255, 0))
            im.save(dst)
            print(f"\nwrote {dst}  ({' | '.join(labels)})")
        except Exception as exc:  # pragma: no cover
            print(f"PNG label pass failed: {exc}")


if __name__ == "__main__":
    main()
