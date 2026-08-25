"""M116 exposure audit for the PIL 16-bit RGB TIFF truncation hazard (ORCH).

Three parts, all measurement, no argument from first principles:

  A. Static scan of every .py in this milestone: how is each TIFF read, and
     what is PIL used for.
  B. Reproduce ORCH's finding on THIS milestone's own render outputs rather
     than on a synthetic probe file.
  C. The counterfactual that matters: recompute both of campaign 5's
     registered metrics from the arrays PIL would have handed me, and print
     them beside the numbers actually reported. This answers "would the bug
     have changed the verdict" with a number instead of a reassurance.

Read-only. Writes one JSON to the M116 output tree; touches nothing in the
repository and nothing on D:.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = Path(r"C:\dev\strehl-out\M116")
MEAS = ROOT / "measure"
OUT = ROOT / "patch"
OUT.mkdir(parents=True, exist_ok=True)

# Metric constants, copied verbatim from the registered scorers so this audit
# cannot drift from them. score_patch.py:49-50, score_patch2.py:40-41.
COARSE_SIGMA = 32.0
BIN = 4
MULT = 4.0

# The ROIs the headline numbers were computed on.
ROI_G1 = (64, 2944, 256)          # score_patch.py flattest-decile pick, bee
ROI_W = (256, 768, 384)           # score_patch2.py NAMED, bee
ROI_N = (1024, 2560, 256)         # score_patch2.py NAMED, bee


# ---------------------------------------------------------------- metrics ---
def luma(a):
    if a.ndim == 2:
        return a
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def laplacian_kurtosis(g):
    lap = ndimage.laplace(g.astype(np.float64))
    v = lap.ravel() - lap.mean()
    sd = v.std()
    if sd <= 0:
        return 0.0, 0.0
    return float(np.mean((v / sd) ** 4) - 3.0), float(sd)


def binned(x, f=BIN):
    h, w = x.shape
    h2, w2 = (h // f) * f, (w // f) * f
    return x[:h2, :w2].reshape(h2 // f, f, w2 // f, f).mean(axis=(1, 3))


def f4(roi):
    t = binned(roi.astype(np.float64))
    gy, gx = np.gradient(t)
    e = np.hypot(gy, gx).ravel()
    med = float(np.median(e))
    if med <= 0:
        return 0.0, 0.0
    return float((e > MULT * med).mean()), med


def cut(a, roi):
    y, x, r = roi
    return a[y:y + r, x:x + r]


# ----------------------------------------------------------------- part A ---
def part_a():
    """Every TIFF read in this milestone, classified by reader."""
    rows = []
    for p in sorted(HERE.glob("*.py")):
        if p.name == Path(__file__).name:
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        rows.append({
            "file": p.name,
            "Image.open": len(re.findall(r"\bImage\.open\s*\(", src)),
            "tifffile.imread": len(re.findall(r"\btifffile\.imread\s*\(", src)),
            "Image.fromarray": len(re.findall(r"\bImage\.fromarray\s*\(", src)),
            "imports_PIL": bool(re.search(r"^\s*from PIL import|^\s*import PIL",
                                          src, re.M)),
        })
    return rows


# ----------------------------------------------------------------- part B ---
def part_b(paths):
    """PIL versus tifffile on this milestone's own 16-bit RGB renders."""
    rows = []
    for label, p in paths:
        t = tifffile.imread(p)
        with Image.open(p) as im:
            mode = im.mode
            q = np.asarray(im)
        rows.append({
            "arm": label,
            "file": p.name,
            "tifffile_dtype": str(t.dtype),
            "tifffile_shape": list(t.shape),
            "tifffile_min": int(t.min()),
            "tifffile_max": int(t.max()),
            "tifffile_levels": int(np.unique(t).size),
            "pil_mode": mode,
            "pil_dtype": str(q.dtype),
            "pil_shape": list(q.shape),
            "pil_levels": int(np.unique(q).size),
            "level_loss_factor": (float(np.unique(t).size) /
                                  max(1, np.unique(q).size)),
        })
    return rows


# ----------------------------------------------------------------- part C ---
def part_c(paths):
    """The two registered metrics, computed from truth and from PIL's array.

    PIL's uint8 is rescaled by 257 so both arms sit on the same nominal 0-65535
    range. Rescaling cannot restore the discarded levels; it only removes a
    trivial units difference so the two columns are directly comparable.
    """
    truth, lost = {}, {}
    for label, p in paths:
        truth[label] = luma(tifffile.imread(p).astype(np.float32))
        with Image.open(p) as im:
            lost[label] = luma(np.asarray(im).astype(np.float32) * 257.0)

    out = {"kurtosis_G1": {}, "f4_ROI-W": {}, "f4_ROI-N": {}}
    for label in truth:
        kt, sdt = laplacian_kurtosis(cut(truth[label], ROI_G1))
        kl, sdl = laplacian_kurtosis(cut(lost[label], ROI_G1))
        out["kurtosis_G1"][label] = {"true_K": kt, "pil_K": kl,
                                     "true_sd": sdt, "pil_sd": sdl}
        for name, roi in (("f4_ROI-W", ROI_W), ("f4_ROI-N", ROI_N)):
            ft, mt = f4(cut(truth[label], roi))
            fl, ml = f4(cut(lost[label], roi))
            out[name][label] = {"true_F4": ft, "pil_F4": fl,
                                "true_med": mt, "pil_med": ml}
    return out


# ----------------------------------------------------------------- part D ---
def part_d(paths):
    """POST-HOC, NOT REGISTERED. Offered as corroboration of ONE thing only:
    that M0 is a valid plant. It rescues no metric and changes no verdict.

    A piecewise-constant field spends its dynamic range on few levels. So if
    the gate-0 plant really is made of flat polygons, it should occupy fewer
    distinct 16-bit levels than the shipped arm over the SAME region -- a
    property of the pixel histogram alone, with no filter, no threshold and no
    ROI-selection step to go wrong.
    """
    rows = []
    for label, p in paths:
        a = tifffile.imread(p)
        g = luma(a.astype(np.float32))
        for name, roi in (("ROI-W", ROI_W), ("ROI-N", ROI_N)):
            r = cut(a, roi)
            gr = cut(g, roi)
            lap = np.abs(ndimage.laplace(gr.astype(np.float64)))
            rows.append({
                "arm": label, "roi": name,
                "levels": int(np.unique(r).size),
                "flat_frac": float((lap < 1.0).mean()),
            })
    return rows


def main():
    paths = [(a, MEAS / f"bee-3-cpl__{a}.tif") for a in ("A0", "A2", "M0")]
    missing = [str(p) for _, p in paths if not p.exists()]
    if missing:
        raise SystemExit("missing renders: " + ", ".join(missing))

    a = part_a()
    print("=== A. how this milestone reads TIFFs ===")
    tot_open = sum(r["Image.open"] for r in a)
    tot_tf = sum(r["tifffile.imread"] for r in a)
    print(f"  files scanned          : {len(a)}")
    print(f"  Image.open(...) calls  : {tot_open}")
    print(f"  tifffile.imread calls  : {tot_tf}")
    pil_files = [r for r in a if r["imports_PIL"]]
    print(f"  files importing PIL    : {len(pil_files)}  "
          f"(Image.fromarray calls: "
          f"{sum(r['Image.fromarray'] for r in pil_files)})")
    print("  -> PIL is used to WRITE PNG previews, never to read a TIFF."
          if tot_open == 0 else "  -> EXPOSED: a TIFF is read through PIL.")

    b = part_b(paths)
    print("\n=== B. PIL vs tifffile on M116's own renders ===")
    print(f"  {'arm':<4} {'tifffile':<26} {'PIL':<20} {'levels t/p':>16} "
          f"{'loss':>7}")
    for r in b:
        tf = f"{r['tifffile_dtype']} max {r['tifffile_max']}"
        pl = f"{r['pil_dtype']} mode {r['pil_mode']}"
        lv = f"{r['tifffile_levels']} / {r['pil_levels']}"
        print(f"  {r['arm']:<4} {tf:<26} {pl:<20} {lv:>16} "
              f"{r['level_loss_factor']:>6.1f}x")

    c = part_c(paths)
    print("\n=== C. the registered metrics, truth vs what PIL would have given ===")
    print("  --- K, excess Laplacian kurtosis, ROI-G1 (campaign 5 metric 1) ---")
    print(f"  {'arm':<4} {'true K':>12} {'PIL K':>12} {'change':>12}")
    for k, v in c["kurtosis_G1"].items():
        d = (v["pil_K"] / v["true_K"] - 1.0) * 100 if v["true_K"] else float("nan")
        print(f"  {k:<4} {v['true_K']:>12.3f} {v['pil_K']:>12.3f} {d:>11.1f}%")
    kt, kl = c["kurtosis_G1"]["M0"], c["kurtosis_G1"]["A0"]
    print(f"  G1 plant ratio K(M0)/K(A0): true "
          f"{kt['true_K'] / kl['true_K']:.3f}   PIL "
          f"{kt['pil_K'] / kl['pil_K']:.3f}   (bar was >= 2.0)")

    for name in ("f4_ROI-W", "f4_ROI-N"):
        print(f"\n  --- F4, {name.split('_')[1]} (campaign 5 metric 2) ---")
        print(f"  {'arm':<4} {'true F4':>12} {'PIL F4':>12} {'change':>12}")
        for k, v in c[name].items():
            d = ((v["pil_F4"] / v["true_F4"] - 1.0) * 100
                 if v["true_F4"] else float("nan"))
            print(f"  {k:<4} {v['true_F4']:>12.5f} {v['pil_F4']:>12.5f} "
                  f"{d:>11.1f}%")
        m0, a0 = c[name]["M0"], c[name]["A0"]
        print(f"  H1 plant ratio F4(M0)/F4(A0): true "
              f"{m0['true_F4'] / a0['true_F4']:.3f}   PIL "
              f"{m0['pil_F4'] / a0['pil_F4']:.3f}   (bar was >= 1.5)")

    d = part_d(paths)
    print("\n=== D. POST-HOC, NOT REGISTERED: is M0 a piecewise-constant field? ===")
    print(f"  {'roi':<7} {'arm':<4} {'distinct levels':>16} {'flat-pixel frac':>17}")
    for r in d:
        print(f"  {r['roi']:<7} {r['arm']:<4} {r['levels']:>16} "
              f"{r['flat_frac']:>16.4f}")
    for roi in ("ROI-W", "ROI-N"):
        a0 = next(r for r in d if r["arm"] == "A0" and r["roi"] == roi)
        m0 = next(r for r in d if r["arm"] == "M0" and r["roi"] == roi)
        print(f"  {roi}: M0 occupies {a0['levels'] / m0['levels']:.3f}x "
              f"FEWER levels than A0; flat-pixel fraction "
              f"{m0['flat_frac'] / max(a0['flat_frac'], 1e-9):.3f}x A0")

    rec = {"part_a": a, "part_b": b, "part_c": c, "part_d": d}
    (OUT / "pil16-audit.json").write_text(json.dumps(rec, indent=1),
                                          encoding="utf-8")
    print(f"\nwrote {OUT / 'pil16-audit.json'}")


if __name__ == "__main__":
    main()
