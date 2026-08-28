r"""V-ADJ13 exposure control: did `--auto-exposure` move the pixels the expired
acquittals were measured on?

WHY THIS IS NOT A DIGRESSION

Every expired acquittal is a comparison between two corpora:

    adjudicated  SHIP-V3, pin 740e7056, ARGV `... --srgb --auto-exposure`
                 (113MSDCF's own log: "+2.33 stops (gain 5.028x)")
    scored today DELIVER-V6, commit 6af834da, ARGV `... --srgb`
                 (its own banner: "exposure: none -- a FAITHFUL render")

If the V3 corpus really carried a 5.03x gain then the two arms do not share a
tone operating point, and "the statistic moved 5.6%" would be a statement about
exposure policy rather than about the merge. The frozen baseline's own
`blotch_mean_dn` says otherwise -- 8625.5 recorded against 8544.2 measured
today, 0.9% apart, where a 5.03x linear gain through the sRGB curve predicts
about 2.08x -- so one of the two records is not describing the file it names.

That is a question about a BINARY, and the binary still exists. This renders ONE
frame through the SHIP-V3 pin twice, with and without the flag, and measures the
mean DN of a fixed window in each. No argument, one subtraction.

READ-ONLY on D:\personal\macro. Writes two TIFFs under C:\dev\strehl-out\V-ADJ13
and deletes both.

usage: python vadj_exposure.py [subject] [frame-index]
"""
import os
import pathlib
import subprocess
import sys
import time

import numpy as np
import tifffile

ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
if ORCH not in sys.path:
    sys.path.insert(0, ORCH)
from orch_blotch import blotch_ratio, lum_of                  # noqa: E402

V3EXE = pathlib.Path(r"C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe")
V6EXE = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe")
SRC = pathlib.Path(r"D:\personal\macro")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-ADJ13")
WIN = 900


def render(exe, subj, k, out, extra):
    env = {kk: v for kk, v in os.environ.items() if not kk.startswith("STREHL_")}
    env["STREHL_ONLY_FRAME"] = str(k)
    env["STREHL_CACHE_DIR"] = str(OUT / "cache")
    cmd = [str(exe), "stack", str(SRC / subj), "-o", str(out), "--srgb"] + extra
    t0 = time.time()
    p = subprocess.run(cmd, env=env, capture_output=True, timeout=1800)
    if p.returncode != 0:
        raise RuntimeError("rc=%d\n%s" % (p.returncode,
                                          p.stderr.decode("utf-8", "replace")[-1500:]))
    log = p.stderr.decode("utf-8", "replace")
    print("  cmd  %s" % " ".join(cmd))
    for line in log.splitlines():
        if "exposure" in line or "field of view scaled" in line:
            print("  log  %s" % line.strip()[:150])
    print("  %.1f s" % (time.time() - t0))
    return log


def stat(path, y, x):
    a = tifffile.imread(str(path))
    lum = lum_of(a[:, :, :3].astype(np.float32))
    del a
    r, bd, nd, md = blotch_ratio(lum[y:y + WIN, x:x + WIN])
    del lum
    return r, bd, nd, md


def main(argv):
    subj = argv[0] if argv else "113MSDCF"
    k = int(argv[1]) if len(argv) > 1 else 31
    y, x = 14, 1558          # 113MSDCF's adjudicated blotch window
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cache").mkdir(exist_ok=True)
    rows = []
    for exe, tag, extra in ((V3EXE, "V3pin-740e7056 --srgb", []),
                            (V3EXE, "V3pin-740e7056 --srgb --auto-exposure",
                             ["--auto-exposure"]),
                            (V6EXE, "V6-6af834da --srgb", [])):
        out = OUT / ("expctl-%s-f%04d.tiff" % (tag.split()[0], k))
        print("%s" % tag)
        render(exe, subj, k, out, extra)
        r, bd, nd, md = stat(out, y, x)
        rows.append((tag, r, bd, nd, md))
        print("  window (%d,%d)  contrast %.5f  band %.1f DN  noise %.1f DN  mean %.1f DN"
              % (y, x, r, bd, nd, md))
        out.unlink()
        for side in (".ok", ".provenance.txt"):
            p = pathlib.Path(str(out) + side)
            if p.exists():
                p.unlink()
        sys.stdout.flush()
    print("\n%-42s %9s %9s %9s" % ("arm (1 frame, k=%d, %s)" % (k, subj),
                                   "contrast", "band DN", "mean DN"))
    for tag, r, bd, nd, md in rows:
        print("%-42s %9.5f %9.1f %9.1f" % (tag, r, bd, md))
    if len(rows) >= 2:
        print("\nmean DN ratio auto-exposure / none : %.4f  "
              "(a 5.03x linear gain through sRGB predicts ~2.08)"
              % (rows[1][4] / max(rows[0][4], 1e-9)))
        print("contrast ratio auto-exposure / none : %.4f  "
              "(a power-law curve commutes with a gain, so contrast should be ~1)"
              % (rows[1][1] / max(rows[0][1], 1e-9)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
