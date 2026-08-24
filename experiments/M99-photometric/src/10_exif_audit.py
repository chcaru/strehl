"""Rule exposure variation and capture-duration light drift in or out.

If shutter, ISO or f-number vary across a bracket, every photometric
conclusion downstream is about the camera, not the optics. If they are
constant, the drift is optical or illumination. Timestamps separate a
monotonic-in-TIME mechanism (a warming LED) from a monotonic-in-SCALE one
(focus breathing) only when the capture is not perfectly uniform in time --
which it is not, so the two are still nearly collinear; we report the
timestamps so the collinearity is on the record rather than assumed away.
"""
import csv
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_shutter(s):
    s = s.strip()
    if not s:
        return None
    if "/" in s:
        a, b = s.split("/")
        return float(a) / float(b)
    return float(s)


def audit(stack):
    path = os.path.join(HERE, "data", "exif-%s.csv" % stack)
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: r["FileName"])
    n = len(rows)
    shut = [parse_shutter(r.get("ExposureTime", "")) for r in rows]
    iso = [float(r["ISO"]) for r in rows]
    fnum = [float(r["FNumber"]) if r.get("FNumber", "").strip() else None
            for r in rows]
    ts = []
    for r in rows:
        d = r.get("DateTimeOriginal", "").strip()
        sub = r.get("SubSecTimeOriginal", "").strip() or "0"
        if not d:
            ts.append(None)
            continue
        t = datetime.strptime(d, "%Y:%m:%d %H:%M:%S")
        ts.append(t.timestamp() + float("0." + sub))

    def uniq(vals):
        s = sorted(set(v for v in vals if v is not None))
        return s

    print("=== %s: %d frames ===" % (stack, n))
    for name, vals in (("ExposureTime", shut), ("ISO", iso),
                       ("FNumber", fnum)):
        u = uniq(vals)
        if len(u) == 1:
            print("  %-13s CONSTANT  %s" % (name, u[0]))
        else:
            print("  %-13s VARIES    %d distinct: %s%s"
                  % (name, len(u), u[:6], " ..." if len(u) > 6 else ""))
    print("  LensModel     %s" % sorted(set(r.get("LensModel", "") for r in rows)))
    print("  WhiteBalance  %s" % sorted(set(r.get("WhiteBalance", "") for r in rows)))
    if ts[0] is not None and ts[-1] is not None:
        span = ts[-1] - ts[0]
        gaps = [b - a for a, b in zip(ts, ts[1:]) if a is not None and b is not None]
        gaps_s = sorted(gaps)
        print("  capture span  %.1f s (%.1f min); median gap %.2f s; "
              "gap range %.2f..%.2f s"
              % (span, span / 60.0, gaps_s[len(gaps_s) // 2], gaps_s[0], gaps_s[-1]))
    return {"n": n, "t": ts, "shutter": shut, "iso": iso, "fnum": fnum,
            "files": [r["FileName"] for r in rows]}


if __name__ == "__main__":
    stacks = sys.argv[1:] or ["bee-3-cpl", "bee-2-cpl", "lavendar-cpl",
                              "leaf-2-cpl"]
    out = {}
    for s in stacks:
        out[s] = audit(s)
        print()
    import json
    with open(os.path.join(HERE, "data", "exif-audit.json"), "w",
              encoding="utf-8") as f:
        json.dump({k: {"n": v["n"], "t": v["t"], "files": v["files"]}
                   for k, v in out.items()}, f)
