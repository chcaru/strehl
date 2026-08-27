"""V-CALIB s1 -- inventory the dark-frame and flat-field assets.

READ-ONLY on D:. Nothing here writes to the source trees.

Purpose. The orchestrator delivered two capture sets this lane had asked for
(V-LINEAR2 sec.12 item 4: "a dark frame and a flat field for this body and
lens"). Before any of it is used as a calibration input, the metadata must be
grouped, because:

  - the owner disclosed that the first two dark frames of the set are
    stabilisation shots and must be discarded;
  - the owner disclosed that illumination MAY HAVE DRIFTED across the flat
    session (Seattle overcast, moving cloud, patches of blue), so inter-set
    level differences are suspect until checked;
  - a photon-transfer calibration is only valid within a group of frames that
    share ISO, aperture and shutter, and nothing guarantees the folders are
    organised that way.

This step establishes the grouping from EXIF and prints it. It draws no
conclusion and computes no calibration constant.
"""
import json
import os
import subprocess
import sys
from collections import defaultdict

DARKS = r"D:\macro-dark-frames"
FLATS = r"D:\personal\macro\flat-fields"
OUT = r"C:\dev\strehl-out\V-CALIB\logs"

TAGS = ["-ISO", "-ExposureTime", "-FNumber", "-DateTimeOriginal",
        "-Model", "-LensModel", "-FocalLength", "-ImageWidth",
        "-ImageHeight"]


def exif(root):
    """One exiftool pass over a tree; JSON on stdout, decoded in Python.

    Deliberately not routed through a PowerShell redirect: house rule, and
    exiftool's JSON is UTF-8 which a PS pipeline would re-encode.
    """
    cmd = ["exiftool", "-j", "-n", "-r", "-ext", "ARW"] + TAGS + [root]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if p.returncode not in (0, 1):
        raise SystemExit(f"exiftool failed rc={p.returncode}: {p.stderr[:400]}")
    return json.loads(p.stdout)


def summarise(rows, label):
    print(f"\n{'=' * 92}\n{label}   n = {len(rows)}\n{'=' * 92}")
    by = defaultdict(list)
    for r in rows:
        src = os.path.basename(os.path.dirname(r["SourceFile"]))
        key = (src, r.get("ISO"), r.get("ExposureTime"), r.get("FNumber"))
        by[key].append(r)
    print(f"  {'folder':<26}{'ISO':>7}{'shutter':>12}{'f':>7}{'n':>6}   "
          f"{'first frame':<21}{'span s':>8}")
    for key in sorted(by, key=lambda k: (str(k[0]), k[1] or 0, k[2] or 0)):
        src, iso, et, fn = key
        g = by[key]
        ts = sorted(r.get("DateTimeOriginal", "") for r in g)
        span = ""
        if ts[0] and ts[-1]:
            def sec(t):
                d, tm = t.split(" ")
                h, m, s = tm.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
            span = f"{sec(ts[-1]) - sec(ts[0]):.0f}"
        ets = f"1/{1 / et:.0f}" if et and et < 1 else (f"{et}" if et else "?")
        print(f"  {src:<26}{iso if iso else '?':>7}{ets:>12}"
              f"{fn if fn else '?':>7}{len(g):>6}   {ts[0]:<21}{span:>8}")
    return by


def main():
    all_rows = {}
    for label, root in (("DARK FRAMES  " + DARKS, DARKS),
                        ("FLAT FIELDS  " + FLATS, FLATS)):
        if not os.path.isdir(root):
            print(f"MISSING: {root}")
            continue
        rows = exif(root)
        all_rows[root] = rows
        by = summarise(rows, label)
        del by

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "inventory.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in all_rows.items()}, f, indent=1)
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
