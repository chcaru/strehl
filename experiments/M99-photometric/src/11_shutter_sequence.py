"""Where do the two exposures sit in the bracket, and what does the camera's
own meter say?

Program AE re-meters every frame. If the shutter switches partway through the
sweep, the bracket contains a photometric STEP that no geometric model can
predict -- and any 1/m^2 story fitted to it is fitting the camera's meter.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rat(s):
    s = (s or "").strip()
    if not s:
        return None
    if "/" in s:
        a, b = s.split("/")
        return float(a) / float(b)
    return float(s)


def main(stack):
    path = os.path.join(HERE, "data", "exif-%s-full.csv" % stack)
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: r["FileName"])
    et = [rat(r["ExposureTime"]) for r in rows]
    bv = []
    for r in rows:
        v = (r.get("BrightnessValue") or "").strip()
        bv.append(float(v) if v else None)
    n = len(rows)
    print("%s: %d frames" % (stack, n))

    # Run-length encode the shutter sequence.
    runs = []
    cur, start = et[0], 0
    for i in range(1, n):
        if et[i] != cur:
            runs.append((start, i - 1, cur))
            cur, start = et[i], i
    runs.append((start, n - 1, cur))
    print("shutter runs (%d):" % len(runs))
    for a, b, v in runs[:60]:
        print("  [%3d..%3d] %d frames  %.5f s" % (a, b, b - a + 1, v))
    if len(runs) > 60:
        print("  ... %d more runs" % (len(runs) - 60))

    lo, hi = min(v for v in et), max(v for v in et)
    print("exposure ratio hi/lo = %.4f  (%.3f stops)"
          % (hi / lo, __import__("math").log2(hi / lo)))

    # If we only knew the exposure, what brightness drift would it alone
    # produce end to end?
    print("frame 0 shutter %.5f, frame %d shutter %.5f -> ratio %.4f"
          % (et[0], n - 1, et[-1], et[0] / et[-1]))
    if any(v is not None for v in bv):
        good = [v for v in bv if v is not None]
        print("BrightnessValue: %.3f .. %.3f (first %.3f last %.3f)"
              % (min(good), max(good), bv[0], bv[-1]))

    out = os.path.join(HERE, "data", "shutter-%s.csv" % stack)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "file", "exposure_s", "brightness_value"])
        for i, r in enumerate(rows):
            w.writerow([i, r["FileName"], et[i], bv[i]])
    print("wrote %s" % out)


if __name__ == "__main__":
    for s in sys.argv[1:] or ["bee-3-cpl"]:
        main(s)
        print()
