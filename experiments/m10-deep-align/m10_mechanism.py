"""P6 vs P7 at matched differential displacement.

The two controls plant the *same* geometric increment and differ in exactly one
thing: whether the two frames also differ in real image content.

  P6 `field` arm  - two frames are independent point samples of one continuous
                    band-limited function.  Same content, no resampler, only the
                    geometry differs.
  P7 `increment`  - a real, defocus-mismatched coffee-bean pair, fitted twice:
                    once as-is and once with a known extra similarity on the
                    moving frame.  The recovered increment is the difference.
                    Defocus mismatch, tile dropout and overlap are held fixed.

If the estimator's response to geometry were biased, both arms would shrink.
If the shrinkage needs a real content change, only P7 shrinks.
"""

import csv
import numpy as np

LEVER = 1200.0  # median anchor lever arm, plane px (see out/edge-quality.txt)


def load(path, keys):
    with open(path, newline="") as f:
        return [{k: r[k] for k in keys if k in r} for r in csv.DictReader(f)]


def field_rows():
    out = []
    with open("data/lock-lock.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["arm"] != "field" or r["cfg"] != "m10" or not r["g"]:
                continue
            out.append((float(r["g_true"]), float(r["ratio"])))
    return out


def incr_rows():
    out = []
    with open("data/coffee-bean-increment.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["cfg"] != "m10" or not r["ratio"]:
                continue
            if int(r["span"]) > 4:
                continue
            out.append((abs(float(r["g_plant"])), float(r["ratio"])))
    return out


def summarise(rows, g):
    v = np.array([x[1] for x in rows if abs(x[0] - g) < 1e-6 * max(g, 1e-6)
                  or abs(abs(x[0]) - g) < 1e-6 * max(g, 1e-6)])
    if v.size == 0:
        return None
    return v.size, np.median(v), np.percentile(v, 25), np.percentile(v, 75)


def main():
    print("=" * 78)
    print("P6 vs P7 - does the shrinkage need a real inter-frame content change?")
    print("  ratio = recovered scale change / planted scale change")
    print("  1.000 unbiased; below 1 is shrinkage toward 'no scale change'")
    print("=" * 78)
    fr = field_rows()
    ir = incr_rows()
    print(f"\n  {'|g|':>9} {'diff disp':>10} | {'P6 field (same content)':>32}"
          f" | {'P7 increment (real pair)':>32}")
    print(f"  {'':>9} {'px':>10} | {'n':>4} {'ratio':>8} {'p25':>8} {'p75':>8}"
          f" | {'n':>4} {'ratio':>8} {'p25':>8} {'p75':>8}")
    for g in [1e-4, 2e-4, 4e-4, 8e-4, 1.6e-3, 4e-3]:
        a = summarise(fr, g)
        b = summarise(ir, g)
        fa = (f"{a[0]:>4} {a[1]:>8.3f} {a[2]:>8.3f} {a[3]:>8.3f}"
              if a else f"{'-':>4} {'-':>8} {'-':>8} {'-':>8}")
        fb = (f"{b[0]:>4} {b[1]:>8.3f} {b[2]:>8.3f} {b[3]:>8.3f}"
              if b else f"{'-':>4} {'-':>8} {'-':>8} {'-':>8}")
        print(f"  {g:>9.5f} {g * LEVER:>10.2f} | {fa} | {fb}")
    print("\n  For reference, the real coffee-bean span-1 edges sit at")
    print("  differential displacement 0.19 px and are shrunk by 3.33x")
    print("  (ratio 0.30) - see out/conservation.txt.")


if __name__ == "__main__":
    raise SystemExit(main())
