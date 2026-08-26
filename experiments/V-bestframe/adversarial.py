"""The adversarial check. Look at EVERY tile that could support H2, not one.

For each tile with real frame detail (SNR >= 3) where the merge reads below the
best frame, put the merge and that frame side by side at native pixel scale. If
H2 is true, at least one of these must show structure in the frame that is
absent from the merge. If they all show sensor noise, H2 is dead on this subject.
"""
import argparse
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
import bestframe as B
from curve import arms

OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME"); IMG = OUT / "images"
GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB"); RAW = Path(r"D:\personal\macro")

ap = argparse.ArgumentParser()
ap.add_argument("subject"); ap.add_argument("--snr", type=float, default=3.0)
ap.add_argument("--ratio", type=float, default=0.80); ap.add_argument("--max", type=int, default=8)
a = ap.parse_args()

A = arms(a.subject); z = A["z"]; ye, xe = z["ye"], z["xe"]
cand = (A["snr"] >= a.snr) & (A["ratio"] < a.ratio) & np.isfinite(A["ratio"])
ij = np.argwhere(cand)
order = np.argsort(A["ratio"][cand])[:a.max]
print(f"{a.subject}: {int(cand.sum())} H2-candidate tiles (SNR>={a.snr}, ratio<{a.ratio}) "
      f"of {int((A['snr']>=a.snr).sum())} real-detail tiles; showing {len(order)}")
if not len(order):
    raise SystemExit(0)
kb = np.nanargmax(np.where(np.isnan(z["S"]), -np.inf, z["S"]), 0)
mL = B.luma(B.read_merge(GAL / f"{a.subject}.tiff")).astype(np.float32)
m8, m16 = B.boxdown(mL, 8), B.boxdown(mL, 16)
fs = sorted((RAW / a.subject).glob("*.ARW"))
need = sorted({int(z["anchors"][kb[tuple(ij[n])]]) for n in order})
cache = {}
for k in need:
    fL = B.luma(B.decode(fs[k])).astype(np.float32)
    s, t, pk = B.register2(m16, B.boxdown(B.raw_green_half(fs[k])), down=16) \
        if False else B.register2(m16, B.boxdown(B.raw_green_half(fs[k]), 8), down=16)
    xs, ys, cv = B.fit_tone(m8, B.boxdown(fL, 8), s, t)
    cache[k] = (B.apply_tone_fast(fL, B.tone_lut(xs, ys)), s, t)
    del fL
    print(f"   decoded k={k} s={s:.4f} peak={pk:.3f}")

TS = 300
sheet = Image.new("RGB", (2 * TS + 30, len(order) * (TS + 22) + 8), (16, 16, 20))
d = ImageDraw.Draw(sheet)
for row, n in enumerate(order):
    i, j = ij[n]; k = int(z["anchors"][kb[i, j]])
    fT, s, t = cache[k]
    my0, my1, mx0, mx1 = ye[i], ye[i + 1], xe[j], xe[j + 1]
    cy, cx = (my0 + my1) // 2, (mx0 + mx1) // 2
    mt = mL[cy - TS // 2:cy + TS // 2, cx - TS // 2:cx + TS // 2]
    fcy = int(round(s * cy + t[1])); fcx = int(round(s * cx + t[0]))
    h = int(round(TS * s / 2))
    ft = fT[fcy - h:fcy + h, fcx - h:fcx + h]
    lo, hi = np.percentile(mt, 1), np.percentile(mt, 99)
    def u8(x):
        return np.clip((x - lo) * (255.0 / max(hi - lo, 1e-6)), 0, 255).astype(np.uint8)
    y = row * (TS + 22) + 20
    sheet.paste(Image.fromarray(u8(mt)).convert("RGB"), (8, y))
    sheet.paste(Image.fromarray(u8(ft)).resize((TS, TS), Image.NEAREST).convert("RGB"), (TS + 22, y))
    d.text((8, y - 15), f"tile({i},{j}) ratio {A['ratio'][i,j]:.3f} snr {A['snr'][i,j]:.2f}  "
                        f"| MERGE | frame k={k} {fs[k].name} (view-only x{1/s:.3f})",
           fill=(255, 240, 120))
sheet.save(IMG / f"FIG4-{a.subject}-all-H2-candidates.jpg", quality=92)
print(f"  -> FIG4-{a.subject}-all-H2-candidates.jpg {sheet.size}")
