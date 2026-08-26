"""How far does a per-frame subject mask move across a focus bracket?

Section 15.5's ground truth profiled every frame with ITS OWN mask. If the mask
moves with defocus, then 'the band at d=120-250' is a DIFFERENT SET OF PIXELS in
every frame, and the spread across frames is partly the mask moving rather than
the shadow changing. This measures the motion directly.
"""
import pathlib, numpy as np, rawpy, ringprofile as rp

fr = sorted(pathlib.Path(r"D:\personal\macro\coffee-bean").glob("*.ARW"))
pick = [fr[0], fr[26], fr[52], fr[78], fr[104]]
rows, masks = [], []
for f in pick:
    with rawpy.imread(str(f)) as r:
        rgb = r.postprocess(half_size=True, no_auto_bright=True, output_bps=16,
                            gamma=(1,1), user_flip=0)
    L = rgb.astype(np.float32).mean(axis=2)
    m, thr, kept, found = rp.subject_mask(L)
    s = rp.signed_distance(m)
    band = (s >= 120) & (s <= 250)
    masks.append((f.stem, m, band))
    rows.append((f.stem, m.mean()*100, thr, int(band.sum())))

print(f"  {'frame':<12} {'mask %':>8} {'thr DN':>9} {'band px':>10}")
for n, a, t, b in rows:
    print(f"  {n:<12} {a:>7.2f}% {t:>9.0f} {b:>10}")
a0 = rows[0][1]; print()
print(f"  mask area swing across the bracket: "
      f"{min(r[1] for r in rows):.2f}% to {max(r[1] for r in rows):.2f}% "
      f"-- {max(r[1] for r in rows)-min(r[1] for r in rows):.2f} points of frame")

base = masks[len(masks)//2][2]
print(f"\n  OVERLAP of each frame's d=120-250 band with the middle frame's band:")
for n, m, b in masks:
    inter = int((b & base).sum()); uni = int((b | base).sum())
    print(f"    {n:<12} IoU {100.0*inter/max(uni,1):>6.2f}%   "
          f"shares {100.0*inter/max(int(b.sum()),1):>6.2f}% of its own band")
print(f"\n  A per-frame mask makes 'the same band' a different set of pixels in")
print(f"  every frame. The IoU above is how much the same it actually is.")
