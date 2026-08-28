"""Harvest the fit_to_cover scale k and frame count N from every render log.

The banner line is:
  coverage      : field of view scaled to 0.9208 so that EVERY frame covers
                  every pixel (7.9% of width dropped, then upsampled ...)
"""
import os, re, glob

K = re.compile(r"field of view scaled to\s+([0-9.]+)")
NPL = re.compile(r"(\d+)\s+placed\s*/\s*(\d+)\s+refused")
DIM = re.compile(r"\((\d+) x (\d+),")

ROOTS = [r"C:\dev\strehl-out\V-SOFTCHECK\ncurve",
         r"C:\dev\strehl-out\V-DILUTE\runs",
         r"C:\dev\strehl-out\V-REVIEW"]

rows = []
for root in ROOTS:
    for log in glob.glob(os.path.join(root, "**", "*.log"), recursive=True):
        t = open(log, encoding="utf-8", errors="replace").read()
        mk, mn, md = K.search(t), NPL.search(t), DIM.search(t)
        if not (mk and mn):
            continue
        subj = os.path.basename(os.path.dirname(log))
        if subj in ("runs", "ncurve"):
            subj = os.path.basename(log).split("_")[0]
        rows.append((subj, int(mn.group(1)), float(mk.group(1)),
                     os.path.basename(log),
                     f"{md.group(1)}x{md.group(2)}" if md else "?"))

rows.sort(key=lambda r: (r[0], r[1]))
print(f"{'subject':<22s} {'N':>5s} {'k':>8s} {'1/k':>8s} {'% upsample':>11s}  {'dims':>11s}  log")
for s, n, k, f, d in rows:
    print(f"{s:<22s} {n:5d} {k:8.4f} {1/k:8.4f} {100*(1/k-1):10.2f}%  {d:>11s}  {f}")

print()
by = {}
for s, n, k, f, d in rows:
    by.setdefault(s, []).append((n, k))
print("MONOTONE CHECK -- does k fall as N rises, within each subject?")
for s, v in sorted(by.items()):
    v = sorted(set(v))
    if len(v) < 2:
        print(f"  {s:<22s} only {len(v)} point(s), cannot test")
        continue
    ks = [k for _, k in v]
    mono = all(ks[i] >= ks[i + 1] for i in range(len(ks) - 1))
    print(f"  {s:<22s} N={[n for n,_ in v]}  k={[round(k,4) for k in ks]}  "
          f"monotone-decreasing={mono}")
