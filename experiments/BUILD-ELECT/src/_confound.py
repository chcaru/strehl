"""Is the coffee-bean / flower-bud pair controlled?

The owner's inference is "these two differ in ONE property, a fine fringe, and
the ring tracks it". That inference is only as good as the pairing. Veiling glare
scales with the flux and the contrast of the bright region against the dark one,
so if the pair also differs in contrast, the correlation has a second explanation
and cannot choose between them.
"""
import numpy as np, tifffile
from scipy import ndimage

rows = []
for tag, p in (("coffee-bean (smooth)", r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif"),
               ("flower-bud (fringed)", r"C:\dev\strehl-out\ORCH-rim\fb-1cacb61-lin.tif")):
    img = tifffile.imread(p); assert img.dtype == np.uint16
    lum = img.astype(np.float32).mean(axis=2)
    lo, hi = np.percentile(lum, [5, 95]); thr = 0.5 * (lo + hi)
    m = lum < thr
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    m = lab == (1 + int(np.argmax(sizes)))

    pad = 8
    pm = np.pad(m, pad, constant_values=False)
    d_out = ndimage.distance_transform_edt(~pm)[pad:-pad, pad:-pad]
    d_in = ndimage.distance_transform_edt(m)
    signed = d_out - d_in

    far = (signed > 600) & (signed < 1400)
    back = float(np.median(lum[far]))
    deep = float(np.median(lum[d_in > 150]))
    clip = float((lum > 64000).mean() * 100)
    # how much backdrop actually exists to measure a profile across
    reach = float(np.percentile(d_out[~m], 99))
    rows.append((tag, back, deep, back / deep, m.mean() * 100, reach, clip,
                 float(lum.max())))

hdr = ("subject", "backdrop DN", "deep subj DN", "contrast", "subj % frame",
       "backdrop reach p99", "clip %", "max DN")
print(f"{hdr[0]:<22}" + "".join(f"{h:>19}" for h in hdr[1:]))
for r in rows:
    print(f"{r[0]:<22}" + f"{r[1]:>19.0f}{r[2]:>19.0f}{r[3]:>19.2f}"
          f"{r[4]:>19.1f}{r[5]:>19.0f}{r[6]:>19.2f}{r[7]:>19.0f}")

print()
print(f"contrast ratio differs by {rows[1][3] / rows[0][3]:.2f}x "
      f"(flower-bud / coffee-bean)")
print(f"subject area differs by   {rows[0][4] / rows[1][4]:.2f}x "
      f"(coffee-bean / flower-bud)")
print(f"backdrop reach differs by {rows[1][5] / rows[0][5]:.2f}x "
      f"(flower-bud / coffee-bean)")
