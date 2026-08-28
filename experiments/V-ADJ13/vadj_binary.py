r"""V-ADJ13 arm BINARY: separate a RENDER CHANGE from a WINDOW MOVE, on pixels
neither corpus can bias.

THE QUESTION

Three acquittals expired on a value move at an UNCHANGED window (112MSDCF and
113MSDCF on chroma, and the blotch halves of both). "The statistic moved" has
two mechanisms and the gate cannot separate them:

  RENDERER   SHIP-V3 was rendered by pin 740e7056, DELIVER-V6 by 6af834da.
             Two different binaries render the same RAW differently.
  MERGE      the election itself started producing structure it did not before.

The source arm (vadj_source.py) answers the merge question. This answers the
renderer question, and it answers it on ONE FRAME rendered by BOTH binaries with
identical flags -- so the bracket, the election and the corpus are all held
fixed and the only free variable left is the executable.

The window used is the master's recorded window coordinate. In a one-frame
render that coordinate does not land on exactly the same scene content as it
does in the master (the two renders crop to different fit-to-cover ratios), but
it lands on the SAME content in both arms, which is all a binary-vs-binary
difference needs.

Also settles, by SHA256 rather than by reading a banner, whether `--auto-exposure`
-- which SHIP-V3's ARGV carried and DELIVER-V6's does not -- changed any pixel.

READ-ONLY on D:\personal\macro. Writes TIFFs under C:\dev\strehl-out\V-ADJ13 and
deletes each one as soon as it is measured.

usage: python vadj_binary.py SUBJECT FRAME WINY WINX
"""
import hashlib
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
from orch_blotch import WIN as BWIN                           # noqa: E402
from orch_chroma import chroma_blotch                         # noqa: E402
from orch_chroma import WIN as CWIN                           # noqa: E402

V3EXE = pathlib.Path(r"C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe")
V6EXE = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe")
SRC = pathlib.Path(r"D:\personal\macro")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-ADJ13")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest().upper()


def render(exe, subj, k, out, extra=()):
    env = {kk: v for kk, v in os.environ.items() if not kk.startswith("STREHL_")}
    env["STREHL_ONLY_FRAME"] = str(k)
    env["STREHL_CACHE_DIR"] = str(OUT / "cache")
    cmd = [str(exe), "stack", str(SRC / subj), "-o", str(out), "--srgb"] + list(extra)
    t0 = time.time()
    p = subprocess.run(cmd, env=env, capture_output=True, timeout=3600)
    if p.returncode != 0:
        raise RuntimeError("rc=%d\n%s" % (p.returncode,
                                          p.stderr.decode("utf-8", "replace")[-1500:]))
    return " ".join(cmd), round(time.time() - t0, 1)


def measure(path, by, bx, cy, cx):
    a = tifffile.imread(str(path))
    rgb = a[:, :, :3].astype(np.float32)
    del a
    lum = lum_of(rgb)
    r, bd, nd, md = blotch_ratio(lum[by:by + BWIN, bx:bx + BWIN])
    del lum
    cb = chroma_blotch(rgb, (cy, cx))
    del rgb
    return dict(blotch=float(r), band=float(bd), noise=float(nd), mean=float(md),
                chroma=float(cb[0]))


def main(argv):
    subj = argv[0]
    k = int(argv[1])
    cy, cx = int(argv[2]), int(argv[3])
    by, bx = (int(argv[4]), int(argv[5])) if len(argv) > 5 else (cy, cx)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cache").mkdir(exist_ok=True)
    print("SUBJECT %s  frame %d  blotch window (%d,%d) %dpx  chroma window (%d,%d) %dpx"
          % (subj, k, by, bx, BWIN, cy, cx, CWIN))
    res = {}
    shas = {}
    arms = (("V3pin-740e7056", V3EXE, ()),
            ("V3pin-740e7056+auto-exposure", V3EXE, ("--auto-exposure",)),
            ("V6-6af834da", V6EXE, ()))
    for tag, exe, extra in arms:
        out = OUT / ("bin-%s-%s-f%04d.tiff" % (subj, tag.replace("+", "_"), k))
        cmd, secs = render(exe, subj, k, out, extra)
        shas[tag] = sha256(out)
        res[tag] = measure(out, by, bx, cy, cx)
        print("  %-30s %5.1f s  sha %s" % (tag, secs, shas[tag]))
        print("     %s" % cmd)
        print("     blotch %.5f  band %.1f  noise %.1f  mean %.1f  chroma %.6f"
              % (res[tag]["blotch"], res[tag]["band"], res[tag]["noise"],
                 res[tag]["mean"], res[tag]["chroma"]))
        for p in (out, pathlib.Path(str(out) + ".ok"),
                  pathlib.Path(str(out) + ".provenance.txt")):
            try:
                p.unlink()
            except OSError:
                pass
        sys.stdout.flush()

    a, b, c = (r[0] for r in arms)
    print("\nAUTO-EXPOSURE  SHIP-V3's ARGV carried --auto-exposure; DELIVER-V6's does not.")
    print("  %s" % ("IDENTICAL FILES: --auto-exposure changed no pixel (same SHA256)"
                    if shas[a] == shas[b] else
                    "DIFFERENT FILES: --auto-exposure did change the render"))
    print("RENDERER  same frame, same flags, %s vs %s:" % (a, c))
    for key in ("blotch", "chroma", "band", "mean", "noise"):
        v0, v1 = res[a][key], res[c][key]
        print("  %-7s %12.6f -> %12.6f   %+7.2f%%"
              % (key, v0, v1, 100.0 * (v1 - v0) / max(abs(v0), 1e-12)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
