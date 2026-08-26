"""JPEG encode-parameter audit: is anything other than pixels different?"""
import sys, hashlib
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

RUNS = {
    "run1_tonefix": Path(r"C:\dev\strehl-out\gallery-history\2026-08-25-tone-fix"),
    "run2_1327":    Path(r"C:\dev\strehl-out\gallery-history\2026-08-25-1327"),
}

def qthash(im):
    qt = getattr(im, "quantization", None)
    if not qt:
        return "none"
    h = hashlib.sha256()
    for k in sorted(qt):
        h.update(bytes(bytearray(qt[k])))
    return h.hexdigest()[:12]

rows = []
names = sorted(p.name for p in RUNS["run2_1327"].glob("*.jpg"))
for n in names:
    rec = {"subject": n}
    for tag, d in RUNS.items():
        p = d / n
        with Image.open(p) as im:
            rec[tag] = (im.size, qthash(im), im.info.get("subsampling", "?"),
                        im.info.get("progression", 0), p.stat().st_size)
    rows.append(rec)

print(f"{'subject':38s} {'size==':>7s} {'qtable==':>9s} {'subsmp==':>9s} {'bytes r1':>9s} {'bytes r2':>9s}")
print("-"*90)
nsz = nqt = nss = 0
for r in rows:
    a, b = r["run1_tonefix"], r["run2_1327"]
    sz, qt, ss = a[0]==b[0], a[1]==b[1], a[2]==b[2]
    nsz += sz; nqt += qt; nss += ss
    print(f"{r['subject'][:38]:38s} {str(sz):>7s} {str(qt):>9s} {str(ss):>9s} {a[4]:>9d} {b[4]:>9d}")
print()
print(f"{len(rows)} subjects: identical dims {nsz}, identical quant tables {nqt}, identical subsampling {nss}")
print("distinct quant-table hashes run1:", sorted({r['run1_tonefix'][1] for r in rows}))
print("distinct quant-table hashes run2:", sorted({r['run2_1327'][1] for r in rows}))
print("distinct subsampling run1:", sorted({str(r['run1_tonefix'][2]) for r in rows}))
print("distinct subsampling run2:", sorted({str(r['run2_1327'][2]) for r in rows}))
