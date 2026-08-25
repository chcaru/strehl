"""ORCH's sign law, measured across the gallery.

    PREDICTION:  sign(rim - far_background) = -sign(subject - far_background)
    i.e. the rim is always pushed AWAY from the subject's own brightness.

The gallery is rendered --srgb, so its tone curve is baked in.  MAGNITUDES here
are not measurable and none are claimed.  SIGNS are, because the tone curve is
monotonic and a monotonic map cannot reorder two values.  Every quantity below
is reported raw and signed, as asked.

The weak point is segmentation, not photometry, so each subject's mask is
sanity-checked and a subject that fails is REPORTED AS SKIPPED rather than
silently contributing a wrong sign.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

GALLERY = Path(r"C:\dev\strehl-out\gallery")
RIM = (2, 16)     # SOBEL_RADIUS + WINDOW_RADIUS
FAR = 200


def load_luma(p):
    im = Image.open(p).convert("RGB")
    a = np.asarray(im, dtype=np.float64) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def mask_of(L):
    lo, hi = np.percentile(L, [1, 99])
    if hi - lo < 0.05:
        return None, "flat frame"
    t = 0.5 * (lo + hi)
    a = L > t
    m = a if a.mean() < 0.5 else ~a
    m = ndimage.binary_closing(m, np.ones((7, 7)))
    m = ndimage.binary_opening(m, np.ones((7, 7)))
    lbl, n = ndimage.label(m)
    if n == 0:
        return None, "no component"
    sizes = ndimage.sum(m, lbl, range(1, n + 1))
    m = lbl == (int(np.argmax(sizes)) + 1)
    m = ndimage.binary_fill_holes(m)
    f = m.mean()
    if not (0.01 < f < 0.60):
        return None, f"mask {f:.0%}"
    return m, None


rows, skipped = [], []
for p in sorted(GALLERY.glob("*.jpg")):
    L = load_luma(p)
    m, why = mask_of(L)
    if m is None:
        skipped.append((p.stem, why))
        continue
    d = ndimage.distance_transform_edt(~m)
    far_sel = d > FAR
    if far_sel.sum() < 20000:
        skipped.append((p.stem, "no far background"))
        continue
    subj = float(np.median(L[m]))
    far = float(np.median(L[far_sel]))
    rim = float(np.median(L[(d >= RIM[0]) & (d < RIM[1])]))
    if abs(subj - far) < 0.02:
        skipped.append((p.stem, "no subject/bg contrast"))
        continue
    rows.append((p.stem, subj, far, rim, rim - far, subj - far))

print(f"{'subject':<40}{'subj':>8}{'far bg':>9}{'rim':>8}{'rim-far':>10}{'subj-far':>10}  law")
print("-" * 96)
agree = 0
for name, subj, far, rim, dr, ds in rows:
    ok = (dr != 0) and (np.sign(dr) == -np.sign(ds))
    agree += ok
    print(f"{name:<40}{subj:>8.4f}{far:>9.4f}{rim:>8.4f}{dr:>+10.4f}{ds:>+10.4f}  "
          f"{'HOLDS' if ok else 'FAILS'}")

print("-" * 96)
n = len(rows)
print(f"\nsign law holds on {agree}/{n} subjects" + (f" ({agree/n:.0%})" if n else ""))
if skipped:
    print(f"\nskipped {len(skipped)} (segmentation, not photometry):")
    for s, w in skipped:
        print(f"  {s:<40} {w}")
print("\nA coin would give ~50%. The law is a MECHANISM FINGERPRINT only if it")
print("holds well above that AND the two signs are both populated -- if every")
print("subject is dark-on-bright, the law is untested, not confirmed.")
if rows:
    nb = sum(1 for r in rows if r[5] > 0)
    print(f"\npolarity balance: {nb} bright-subject, {n - nb} dark-subject")
