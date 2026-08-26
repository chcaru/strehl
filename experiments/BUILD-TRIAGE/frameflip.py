"""1:1 crops of the SAME site across the bracket, so a through-focus claim can
be checked by eye rather than believed.

Every frame goes through one identical decode path (rawpy CFA green plane,
black-subtracted, no demosaic/WB/matrix), so the panels are mutually
comparable.  Each panel is stamped with its own mean level in DN and its own
relative HF, because the single most misleading thing about a focus ladder is
that a brighter frame looks sharper.

Display is per-panel-independent normalisation ONLY if --autoscale is given;
the default is a SHARED scale across the ladder, so a brightness ramp stays
visible as a brightness ramp instead of being silently equalised away.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402
import sitescan as ss  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--at", action="append", default=[], metavar="LABEL:X,Y",
                    help="site in MERGE px; located in the frames by NCC")
    ap.add_argument("--frames", default="", help="comma list of frame indices")
    ap.add_argument("--n", type=int, default=6, help="frames if --frames unset")
    ap.add_argument("--half", type=int, default=110, help="crop half-size, green px")
    ap.add_argument("--autoscale", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    assert args.at, "no --at sites"

    d = os.path.join(tri.RAW, args.subject)
    seen: dict[str, str] = {}
    for f in os.listdir(d):
        if f.lower().endswith(".arw"):
            seen.setdefault(os.path.normcase(f), f)
    files = sorted(seen.values())
    n = len(files)
    idx = ([int(v) for v in args.frames.split(",")] if args.frames
           else [int(round(v)) for v in np.linspace(0, n - 1, args.n)])
    for k in idx:
        assert 0 <= k < n, f"frame {k} outside 0..{n-1}"

    sites = []
    for spec in args.at:
        label, _, xy = spec.partition(":")
        sx, _, sy = xy.partition(",")
        sites.append({"label": label, "x": int(sx), "y": int(sy)})

    merge_y = tri.luma(tri.load16(os.path.join(tri.LIN, args.subject + ".tiff")))
    ref = ss.green_plane(os.path.join(d, files[idx[len(idx) // 2]]))
    for s in sites:
        loc = ss.locate(merge_y, ref, s["x"], s["y"], 96, ss.SEARCH_G)
        s.update(loc)
        assert loc["ncc"] >= 0.40, (
            f"{s['label']}: located at ncc={loc['ncc']:.3f}; refusing to show "
            f"a crop of a site I cannot confirm")

    h_ = args.half
    tiles: dict[tuple[int, int], np.ndarray] = {}
    stats: dict[tuple[int, int], tuple[float, float]] = {}
    for i, k in enumerate(idx):
        g = ss.green_plane(os.path.join(d, files[k]))
        for j, s in enumerate(sites):
            w = g[s["gy"] - h_:s["gy"] + h_, s["gx"] - h_:s["gx"] + h_]
            tiles[(j, i)] = w.astype(np.float64)
            stats[(j, i)] = (float(np.mean(w)), ss.hf_rel(w))

    side = 2 * h_
    pad, top, lab = 6, 34, 30
    W = lab + len(idx) * (side + pad) + pad
    H = top + len(sites) * (side + pad + 16) + pad
    im = Image.new("RGB", (W, H), (16, 16, 16))
    dr = ImageDraw.Draw(im)
    dr.text((6, 6), f"{args.subject}   SAME SITE across the bracket, 1:1, raw "
                    f"CFA green (no demosaic/WB/matrix)   "
                    f"{'per-panel autoscale' if args.autoscale else 'SHARED scale'}",
            fill=(235, 235, 235))
    dr.text((6, 19), "each panel: frame index | mean level DN | relative HF "
                     "(Laplacian RMS / mean). Brighter is not sharper.",
            fill=(150, 150, 150))

    for j, s in enumerate(sites):
        row = top + j * (side + pad + 16)
        vals = np.concatenate([tiles[(j, i)].ravel() for i in range(len(idx))])
        glo_hi = float(np.percentile(vals, 99.5)) or 1.0
        dr.text((6, row + side // 2), s["label"][:9], fill=(255, 220, 60))
        for i, k in enumerate(idx):
            t = tiles[(j, i)]
            hi = (float(np.percentile(t, 99.5)) or 1.0) if args.autoscale else glo_hi
            v = np.clip(t / hi, 0, 1) ** (1 / 2.2)
            x = lab + i * (side + pad)
            im.paste(Image.fromarray((v * 255).astype(np.uint8)).convert("RGB"),
                     (x, row))
            mean, rel = stats[(j, i)]
            dr.text((x, row + side + 2),
                    f"f{k}  {mean:.0f} DN  rel {rel:.4f}", fill=(190, 190, 190))

    out = os.path.join(tri.OUT, "frameflip",
                       args.subject + (args.tag or "") + ".jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, quality=93)
    print(f"{args.subject}: frames {idx} -> {out}  ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
