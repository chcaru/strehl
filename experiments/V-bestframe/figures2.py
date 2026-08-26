"""Evidence figures for the V-bestframe verdict.

Fig 1  per-tile best-frame SNR map, flowers-cpl beside the control bee-1-cpl.
       This is the INPUT difference: how many tiles hold frame detail at all.
Fig 2  the adversarial tile. Among tiles that DO hold real frame detail
       (SNR >= 3, the crossover measured on both subjects), the one where the
       merge under-performs the best frame most. If H2 is real anywhere it is
       real there, so that is the tile to look at.
Fig 3  the per-frame sweep at the worst mush tile: band detail against frame
       index for every measured frame. Under H2 some frame must spike. Under H1
       the whole sweep sits on the fixed-pattern floor.

PIL is imported to WRITE jpegs only. Every pixel READ is tifffile or rawpy with
an immediate uint16 assert.
"""
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
from scipy import ndimage
import bestframe as B
from curve import arms
from paircov import band_of

OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME"); IMG = OUT / "images"
GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB"); RAW = Path(r"D:\personal\macro")
IMG.mkdir(parents=True, exist_ok=True)


def u8(a, lo, hi):
    return np.clip((a.astype(np.float32) - lo) * (255.0 / max(hi - lo, 1e-6)), 0, 255).astype(np.uint8)


def snr_map(subj, a, w=44):
    s = a["snr"]
    g = np.zeros(s.shape + (3,), np.uint8)
    for i in range(s.shape[0]):
        for j in range(s.shape[1]):
            v = s[i, j]
            g[i, j] = (60, 60, 70) if not np.isfinite(v) or v < 1 else \
                      (150, 60, 40) if v < 3 else (60, 150, 90) if v < 8 else (120, 230, 140)
    im = Image.fromarray(g).resize((s.shape[1] * w, s.shape[0] * w), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for i in range(s.shape[0]):
        for j in range(s.shape[1]):
            v = s[i, j]
            d.text((j * w + 4, i * w + w // 2 - 6),
                   "-" if not np.isfinite(v) else f"{v:.1f}", fill=(255, 255, 255))
    d.text((6, 6), f"{subj}  best-frame detail SNR (floor units)  "
                   f">=3 in {100*np.mean(s>=3):.1f}% of tiles", fill=(255, 255, 0))
    return im


def fig1():
    ims = []
    for subj in ("bee-1-cpl", "flowers-cpl"):
        ims.append(snr_map(subj, arms(subj)))
    W = max(i.width for i in ims); H = sum(i.height for i in ims) + 10
    c = Image.new("RGB", (W, H), (20, 20, 24)); y = 0
    for i in ims:
        c.paste(i, (0, y)); y += i.height + 10
    c.save(IMG / "FIG1-snr-map.jpg", quality=88)
    print("FIG1-snr-map.jpg", c.size)


def fig2(subj="flowers-cpl", snr_min=3.0):
    a = arms(subj)
    z = a["z"]; ye, xe = z["ye"], z["xe"]
    cand = (a["snr"] >= snr_min) & np.isfinite(a["ratio"])
    if not cand.any():
        print(f"fig2 {subj}: no tile with SNR>={snr_min}"); return
    r = np.where(cand, a["ratio"], np.inf)
    i, j = np.unravel_index(np.argmin(r), r.shape)
    kbest = int(z["anchors"][int(np.nanargmax(np.where(np.isnan(z["S"]), -np.inf, z["S"]), 0)[i, j])])
    print(f"fig2 {subj}: worst REAL-DETAIL tile ({i},{j}) ratio {a['ratio'][i,j]:.3f} "
          f"snr {a['snr'][i,j]:.2f} best frame k={kbest}")
    mL = B.luma(B.read_merge(GAL / f"{subj}.tiff")).astype(np.float32)
    my0, my1, mx0, mx1 = ye[i], ye[i + 1], xe[j], xe[j + 1]
    mt = mL[my0:my1, mx0:mx1]
    m8, m16 = B.boxdown(mL, 8), B.boxdown(mL, 16); del mL
    fs = sorted((RAW / subj).glob("*.ARW"))
    fL = B.luma(B.decode(fs[kbest])).astype(np.float32)
    s, t, pk = B.register2(m16, B.boxdown(B.raw_green_half(fs[kbest]), 8), down=16)
    xs, ys, cov = B.fit_tone(m8, B.boxdown(fL, 8), s, t)
    fT = B.apply_tone_fast(fL, B.tone_lut(xs, ys)); del fL
    fy0 = int(round(s * my0 + t[1])); fx0 = int(round(s * mx0 + t[0]))
    ft = fT[fy0:fy0 + int(round(s * (my1 - my0))), fx0:fx0 + int(round(s * (mx1 - mx0)))]
    lo, hi = np.percentile(mt, 1), np.percentile(mt, 99)
    A = Image.fromarray(u8(mt, lo, hi))
    # frame is 1/s smaller on its own grid; upsample FOR VIEWING ONLY, never measured
    Bi = Image.fromarray(u8(ft, lo, hi)).resize(A.size, Image.NEAREST)
    c = Image.new("RGB", (A.width * 2 + 24, A.height + 40), (16, 16, 20))
    c.paste(A.convert("RGB"), (8, 32)); c.paste(Bi.convert("RGB"), (A.width + 16, 32))
    d = ImageDraw.Draw(c)
    d.text((8, 6), f"{subj} tile ({i},{j})  merge/bestframe={a['ratio'][i,j]:.3f}  "
                   f"frameSNR={a['snr'][i,j]:.2f}   LEFT: merge   RIGHT: frame {fs[kbest].name} "
                   f"(k={kbest}, nearest-neighbour upsampled x{1/s:.3f} FOR VIEWING ONLY)",
           fill=(255, 255, 120))
    c.save(IMG / f"FIG2-{subj}-worst-real-tile.jpg", quality=92)
    print(f"  -> FIG2-{subj}-worst-real-tile.jpg {c.size}")


def fig3(subj="flowers-cpl"):
    """Every measured frame at the mushiest tiles. Under H2 something must spike."""
    a = arms(subj); z = a["z"]
    b = np.load(OUT / f"{subj}__base.npz")
    ft = b["frame_tiles"][:, :, :, 1]          # FINE rms per frame per tile
    idx = b["frame_index"]
    fl = np.sqrt(np.nanmedian(a["F"]))
    low = np.argsort(a["snr"].ravel())[:6]
    print(f"\nFIG3 {subj}: per-frame FINE band rms at the 6 lowest-SNR tiles "
          f"({ft.shape[0]} of {int(b['n_on_disk'])} frames measured). "
          f"fixed-pattern floor = {fl:.1f} DN")
    print(f"    {'tile':>8} {'snr':>6} {'merge':>8} " +
          " ".join(f"k{int(idx[q]):03d}" for q in range(0, ft.shape[0], 4)))
    for q in low:
        i, j = np.unravel_index(q, a["snr"].shape)
        row = " ".join(f"{ft[n,i,j]:4.0f}" for n in range(0, ft.shape[0], 4))
        print(f"    ({i:2d},{j:2d}) {a['snr'][i,j]:6.2f} "
              f"{np.sqrt(a['Em'][i,j]):8.1f} {row}")


if __name__ == "__main__":
    fig1(); fig2("flowers-cpl"); fig2("bee-1-cpl"); fig3("flowers-cpl")
