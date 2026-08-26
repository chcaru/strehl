"""Through-focus probe, V-VEILCLAW edition.

Same measurement as experiments/ORCH-drift-check/throughfocus_probe.py -- mean
|laplacian| of the CFA green lattice, no demosaic, no alignment, no tone curve --
with three changes forced by the way the previous run went wrong:

  1. Every window that is measured is ALSO dumped to a contact sheet, under one
     shared display curve. You cannot run this and not see what you measured.
  2. A NULL window is mandatory alongside the control. The control proves the
     instrument responds; the null proves it can stay quiet. An instrument that
     has only ever been shown to respond has not been shown to discriminate.
  3. Verdict thresholds unchanged from the original so results stay comparable.

Usage:
  python probe.py --win y0 y1 x0 x1 --ctl y0 y1 x0 x1 --nul y0 y1 x0 x1
                  --frames a:b:step  --outdir DIR [--tag NAME]
"""
import argparse
import pathlib

import numpy as np
import rawpy
from PIL import Image, ImageDraw

RAWDIR = pathlib.Path(r"D:\personal\macro\bee-3-cpl")


def sharp(plane):
    p = plane.astype(np.float32)
    lap = np.abs(4 * p[1:-1, 1:-1] - p[:-2, 1:-1] - p[2:, 1:-1] - p[1:-1, :-2] - p[1:-1, 2:])
    return float(lap.mean())


def verdict(vals):
    v = np.asarray(vals, dtype=np.float64)
    n = len(v)
    if n < 5:
        return "TOO-FEW-FRAMES"
    k = int(np.argmax(v))
    lo, hi = float(v.min()), float(v.max())
    contrast = (hi - lo) / max(lo, 1e-9)
    edge = k <= 1 or k >= n - 2
    if contrast < 0.15:
        return f"FLAT (peak/floor={1 + contrast:.3f}) -> never resolved"
    if edge:
        return f"PEAK-AT-END frame#{k}/{n - 1} (ratio {1 + contrast:.2f}) -> bracket ran out"
    return f"INTERIOR-PEAK frame#{k}/{n - 1} (ratio {1 + contrast:.2f}) -> a frame HAD it"


def grade(a, lo, hi):
    x = np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return (np.power(x, 1.0 / 2.2) * 255.0).astype(np.uint8)


def sheet(crops, labels, path, tile=200):
    h, w = crops[0].shape
    sc = max(1, int(np.ceil(max(h, w) / tile)))
    th, tw = h // sc, w // sc
    cols = min(10, len(crops))
    rows = (len(crops) + cols - 1) // cols
    allpx = np.concatenate([c.ravel() for c in crops])
    lo, hi = np.percentile(allpx, [1.0, 99.7])
    img = np.full((rows * th, cols * tw), 255, np.uint8)
    for n, c in enumerate(crops):
        g = grade(c, lo, hi)[::sc, ::sc][:th, :tw]
        r, cc = divmod(n, cols)
        img[r * th:r * th + g.shape[0], cc * tw:cc * tw + g.shape[1]] = g
    im = Image.fromarray(img).convert("RGB")
    d = ImageDraw.Draw(im)
    for n, lab in enumerate(labels):
        r, cc = divmod(n, cols)
        d.rectangle([cc * tw, r * th, cc * tw + tw - 1, r * th + th - 1], outline=(255, 0, 0))
        d.text((cc * tw + 4, r * th + 4), lab, fill=(255, 0, 0))
    im.save(path)


def main():
    ap = argparse.ArgumentParser()
    for f in ("win", "ctl", "nul"):
        ap.add_argument(f"--{f}", nargs=4, type=int, required=True)
    ap.add_argument("--frames", default="0:299:1")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--tag", default="probe")
    a = ap.parse_args()

    b, e, s = (int(v) for v in a.frames.split(":"))
    idxs = list(range(b, e, s))
    out = pathlib.Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(RAWDIR.glob("*.ARW"))

    boxes = {"win": a.win, "ctl": a.ctl, "nul": a.nul}
    for k, (y0, y1, x0, x1) in boxes.items():
        print(f"{k}: master y[{y0}:{y1}] x[{x0}:{x1}]")

    vals = {k: [] for k in boxes}
    crops = {k: [] for k in boxes}
    labels = []
    keep = set(idxs[:: max(1, len(idxs) // 30)])
    for i in idxs:
        with rawpy.imread(str(files[i])) as r:
            g = r.raw_image_visible[0::2, 1::2]
            for k, (y0, y1, x0, x1) in boxes.items():
                c = g[y0 // 2:y1 // 2, x0 // 2:x1 // 2]
                vals[k].append(sharp(c))
                if i in keep:
                    crops[k].append(c.astype(np.float32))
        if i in keep:
            labels.append(f"f{i:03d}")
        if (idxs.index(i) + 1) % 25 == 0:
            print(f"  {idxs.index(i) + 1}/{len(idxs)}")

    for k in boxes:
        sheet(crops[k], labels, out / f"{a.tag}--{k}-SHEET.png")

    csv = out / f"{a.tag}.csv"
    csv.write_text(
        "idx,frame,probe,control,null\n"
        + "".join(
            f"{i},{files[i].stem},{vals['win'][n]:.4f},{vals['ctl'][n]:.4f},{vals['nul'][n]:.4f}\n"
            for n, i in enumerate(idxs)
        ),
        encoding="utf-8",
    )

    print()
    print(f"CONTROL : {verdict(vals['ctl'])}")
    print(f"NULL    : {verdict(vals['nul'])}")
    cv = verdict(vals["ctl"])
    nv = verdict(vals["nul"])
    if not cv.startswith("INTERIOR-PEAK"):
        print("INSTRUMENT NOT COMMISSIONED -- control did not peak in the interior.")
    if not nv.startswith("FLAT"):
        print("INSTRUMENT NOT DISCRIMINATING -- null window did not read flat.")
    print(f"PROBE   : {verdict(vals['win'])}")
    print(f"wrote {csv}")

    # ascii shape of the probe curve
    v = np.asarray(vals["win"])
    lo, hi = v.min(), v.max()
    print("\nprobe curve:")
    for n, i in enumerate(idxs):
        if len(idxs) > 90 and n % max(1, len(idxs) // 90):
            continue
        bar = int(60 * (v[n] - lo) / max(hi - lo, 1e-9))
        print(f"  f{i:03d} {v[n]:9.2f} {'#' * bar}")


if __name__ == "__main__":
    main()
