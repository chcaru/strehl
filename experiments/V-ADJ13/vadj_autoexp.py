r"""V-ADJ13: is `--auto-exposure` a no-op on the PIXELS of the SHIP-V3 pin?

vadj_binary.py found the two files differ by SHA256 while every statistic
measured inside them agreed to seven significant figures. Those two facts are
only compatible if the difference is metadata, and "only compatible if" is an
argument, not a measurement. This compares the decoded arrays.

It matters because every expired acquittal is a SHIP-V3 number compared against
a DELIVER-V6 number, and SHIP-V3's ARGV carried `--auto-exposure` while
DELIVER-V6's does not. If that flag moved the pixels, the comparison is between
two tone operating points and no conclusion about the merge can be drawn from
it at all.

READ-ONLY on D:\personal\macro. Deletes both renders.

The flag under test is an argument, so the same instrument answers the narrower
question it raises -- whether an EXPLICIT `--exposure=<stops>` is applied when
the automatic one is not. V-REVIEW's source arm forced exactly that flag to keep
its two arms tone-matched, so the answer decides whether that control worked.

usage: python vadj_autoexp.py [subject] [frame] [flag ...]
"""
import hashlib
import os
import pathlib
import subprocess
import sys

import numpy as np
import tifffile

V3EXE = pathlib.Path(r"C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe")
SRC = pathlib.Path(r"D:\personal\macro")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-ADJ13")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest().upper()


def render(subj, k, out, extra):
    env = {kk: v for kk, v in os.environ.items() if not kk.startswith("STREHL_")}
    env["STREHL_ONLY_FRAME"] = str(k)
    env["STREHL_CACHE_DIR"] = str(OUT / "cache")
    cmd = [str(V3EXE), "stack", str(SRC / subj), "-o", str(out), "--srgb"] + list(extra)
    p = subprocess.run(cmd, env=env, capture_output=True, timeout=3600)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[-1200:])
    return " ".join(cmd)


def main(argv):
    subj = argv[0] if argv else "113MSDCF"
    k = int(argv[1]) if len(argv) > 1 else 31
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cache").mkdir(exist_ok=True)
    flags = tuple(argv[2:]) or ("--auto-exposure",)
    paths, arrays = [], []
    for tag, extra in (("none", ()), ("flag", flags)):
        p = OUT / ("autoexp-%s-%s.tiff" % (subj, tag))
        print(render(subj, k, p, extra))
        print("  sha256 %s  %d bytes" % (sha256(p), p.stat().st_size))
        paths.append(p)
        arrays.append(tifffile.imread(str(p)))
    a, b = arrays
    same = bool(a.shape == b.shape and np.array_equal(a, b))
    print("\nshapes %s / %s" % (a.shape, b.shape))
    print("PIXELS IDENTICAL: %s" % same)
    if not same and a.shape == b.shape:
        d = (a.astype(np.int64) - b.astype(np.int64))
        print("  differing samples %d of %d (%.6f%%), max |delta| %d"
              % (int((d != 0).sum()), d.size, 100.0 * (d != 0).mean(), int(np.abs(d).max())))
    for p in paths:
        with tifffile.TiffFile(str(p)) as tf:
            tags = {t.name: t.value for t in tf.pages[0].tags
                    if t.name in ("Software", "ImageDescription", "DocumentName",
                                  "Artist", "DateTime")}
        print("  %-6s tags: %s" % (p.stem.split("-")[-1],
                                   {k2: (str(v)[:70]) for k2, v in tags.items()}))
    for p in paths:
        for q in (p, pathlib.Path(str(p) + ".ok"), pathlib.Path(str(p) + ".provenance.txt")):
            try:
                q.unlink()
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
