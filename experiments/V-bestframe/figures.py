"""V-bestframe figures: the per-tile ratio map, and the worst-tile side-by-side.

The side-by-side shows BOTH arms at their own native pixel scale. The merge is
magnified 1/s relative to a frame, so the panels differ in size by that factor
and it is printed on the panel. Nothing is resampled: resampling the frame to
match would blur exactly the evidence the picture exists to show.
"""
import argparse
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw          # WRITE ONLY -- no measured pixel is
import bestframe as B                     # ever read back through PIL
import analyse as A

GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")
RAW = Path(r"D:\personal\macro")
IMG = Path(r"C:\dev\strehl-out\V-BESTFRAME\images")


def stretch(a, lo=0.5, hi=99.5):
    p0, p1 = np.percentile(a, [lo, hi])
    return np.clip((a - p0) / max(p1 - p0, 1e-6), 0, 1)


def ratio_map(subj, tag="base"):
    d = A.load(subj, tag)
    im = Image.new("RGB", (22 * 40, 2 * (16 * 40 + 26) + 10), (16, 16, 16))
    dr = ImageDraw.Draw(im)
    for bi, (band, lab) in enumerate(((1, "FINE(1,2)"), (2, "MID(2.5,5)"))):
        r = A.analyse(d, band)
        rat = np.clip(r["ratio"], 0, 2.0)
        y0 = bi * (16 * 40 + 26) + 20
        dr.text((4, y0 - 16), f"{subj}  {lab}  ratio merge/bestframe  "
                              f"(red<0.8 flagged, grey = no detail in any arm)",
                fill=(255, 230, 120))
        for i in range(16):
            for j in range(22):
                v = rat[i, j]
                if not np.isfinite(v):
                    c = (60, 60, 90)
                elif not r["content"][i, j]:
                    c = (70, 70, 70)
                elif v < 0.8:
                    c = (255, int(60 * v / 0.8), 40)
                else:
                    g = int(np.clip(90 + 120 * (v - 0.8), 0, 255))
                    c = (40, g, int(np.clip(60 + 120 * (v - 0.8), 0, 255)))
                dr.rectangle([j * 40, y0 + i * 40, j * 40 + 38, y0 + i * 40 + 38], fill=c)
                dr.text((j * 40 + 3, y0 + i * 40 + 13),
                        "--" if not np.isfinite(v) else f"{v:.2f}"[1:],
                        fill=(255, 255, 255) if r["flagged"][i, j] else (200, 200, 200))
    out = IMG / f"{subj}--ratiomap-{tag}.png"
    im.save(out); print(f"  wrote {out}")


def side_by_side(subj, ti, tj, tag="base", pad=0):
    d = A.load(subj, tag)
    r = A.analyse(d, 1)
    n = int(r["arg"][ti, tj]); k = int(d["frame_index"][n]); name = str(d["frame_names"][n])
    s, tx, ty = d["reg_used"][n]
    ye, xe = d["ye"], d["xe"]
    y0, y1, x0, x1 = ye[ti] - pad, ye[ti + 1] + pad, xe[tj] - pad, xe[tj + 1] + pad
    mL = B.luma(B.read_merge(GAL / f"{subj}.tiff")).astype(np.float32)
    mc = mL[max(0, y0):y1, max(0, x0):x1]
    fs = sorted((RAW / subj).glob("*.ARW"))
    fL = B.luma(B.decode(fs[k])).astype(np.float32)
    xs, ys, _ = B.fit_tone(B.boxdown(mL, 8), B.boxdown(fL, 8), s, (tx, ty))
    fT = B.apply_tone_fast(fL, B.tone_lut(xs, ys))
    fy0, fy1 = int(round(s * y0 + ty)), int(round(s * y1 + ty))
    fx0, fx1 = int(round(s * x0 + tx)), int(round(s * x1 + tx))
    fc = fT[max(0, fy0):fy1, max(0, fx0):fx1]
    lo = min(np.percentile(mc, 0.5), np.percentile(fc, 0.5))
    hi = max(np.percentile(mc, 99.5), np.percentile(fc, 99.5))
    def to8(a):
        return Image.fromarray((np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1) * 255)
                               .astype(np.uint8))
    a, b = to8(mc), to8(fc)
    W, H = a.width + b.width + 24, max(a.height, b.height) + 34
    im = Image.new("RGB", (W, H), (18, 18, 18)); dr = ImageDraw.Draw(im)
    im.paste(a, (0, 30)); im.paste(b, (a.width + 24, 30))
    dr.text((3, 8), f"{subj} tile ({ti},{tj})  MERGE  {mc.shape[1]}x{mc.shape[0]} px "
                    f"@ merge scale   band RMS {r['m_cor'][ti,tj]:.1f} DN",
            fill=(255, 230, 120))
    dr.text((a.width + 27, 8), f"BEST FRAME k={k} {name}  {fc.shape[1]}x{fc.shape[0]} px "
                               f"@ s={s:.4f}  band RMS {r['best'][ti,tj]:.1f} DN   "
                               f"ratio {r['ratio'][ti,tj]:.3f}", fill=(255, 230, 120))
    out = IMG / f"{subj}--tile{ti}_{tj}--merge-vs-k{k}.png"
    im.save(out); print(f"  wrote {out}  ratio={r['ratio'][ti,tj]:.3f}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("subject"); ap.add_argument("--tag", default="base")
    ap.add_argument("--tile", default="")
    ap.add_argument("--map", action="store_true")
    a = ap.parse_args()
    IMG.mkdir(parents=True, exist_ok=True)
    if a.map:
        ratio_map(a.subject, a.tag)
    if a.tile:
        ti, tj = (int(v) for v in a.tile.split(","))
        side_by_side(a.subject, ti, tj, a.tag)
