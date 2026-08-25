"""M120 step 27 -- repair ORCH's two patchwork* readers.

Delegated: "M120: these two patchwork* scripts are in your lane -- this is the
one to act on first."

Anchored on unique full-line strings; hard-errors if any anchor does not land
exactly once. Backs each file up to $env:TEMP first (never `git checkout --`).

Three changes per file:
  1. pixels read via tifffile for .tif/.tiff, PIL only for genuinely 8-bit formats
  2. the dtype guard becomes FATAL -- patchwork16.py already had the guard, it
     fired on every run ("!! NOT 16-BIT (uint8)"), and it was non-fatal, so the
     run continued and printed a results table. A warning that does not stop the
     run is not a check.
  3. patchwork_16bit.py had no guard at all; one is added.
"""
import os
import shutil
import sys
from pathlib import Path

D = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
TMP = Path(os.environ["TEMP"]) / "M120-patchwork-backup"

HELPER = '''

def _read_pixels(path):
    """Read pixels honestly.

    Fact 1615: PIL silently returns uint8 for a 16-bit RGB TIFF (mode 'RGB',
    241x fewer levels, no warning). Never read TIFF pixels through PIL.
    `Image.open` for TIFF *tags* is fine; np.asarray on its pixels is not.
    """
    import numpy as _np
    if str(path).lower().endswith((".tif", ".tiff")):
        import tifffile
        return tifffile.imread(path)
    from PIL import Image as _I
    return _np.asarray(_I.open(path))

'''

EDITS = {
    "patchwork16.py": [
        ("im = Image.open(src)\na = np.asarray(im)\n",
         "a = _read_pixels(src)\n"),
        ('print("mode  %s  size %dx%d  dtype %s  min %s max %s" % (im.mode, im.width, im.height, a.dtype, a.min(), a.max()))\n',
         'print("shape %s  dtype %s  min %s max %s" % (a.shape, a.dtype, a.min(), a.max()))\n'),
        ('    print("!! NOT 16-BIT (%s). Quantisation contouring is NOT ruled out by this run." % a.dtype)\n',
         '    print("!! NOT 16-BIT (%s). Quantisation contouring is NOT ruled out by this run." % a.dtype)\n'
         '    sys.exit(3)  # M120: a warning that does not stop the run is not a check\n'),
    ],
    "patchwork_16bit.py": [
        ("im = Image.open(src)\n",
         "a = _read_pixels(src)\n"),
        ('print("mode  %s  size %dx%d  frames? %s" % (im.mode, im.width, im.height, getattr(im, "n_frames", 1)))\n',
         'if a.dtype != np.uint16:\n'
         '    print("!! NOT 16-BIT (%s) -- this script exists to rule OUT quantisation\\n"\n'
         '          "   contouring, so it cannot run on quantised input." % a.dtype)\n'
         '    sys.exit(3)\n'),
        ("a = np.asarray(im)\n", ""),
    ],
}


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    for fn, edits in EDITS.items():
        p = D / fn
        src = p.read_text(encoding="utf-8")
        shutil.copy2(p, TMP / fn)
        print(f"{fn}: backed up to {TMP / fn}")

        out = src
        for old, new in edits:
            n = out.count(old)
            if n != 1:
                raise SystemExit(
                    f"ANCHOR FAILED in {fn}: found {n} occurrences (want exactly 1) of:\n"
                    f"---\n{old}---\nNo file was modified beyond backups.")
            out = out.replace(old, new, 1)

        marker = "def _read_pixels(path):"
        if marker not in out:
            anchor = "Image.MAX_IMAGE_PIXELS = None\n"
            if out.count(anchor) != 1:
                raise SystemExit(f"ANCHOR FAILED in {fn}: helper insertion point")
            out = out.replace(anchor, anchor + HELPER, 1)

        if "import sys" not in out:
            raise SystemExit(f"{fn} does not import sys; sys.exit would NameError")

        p.write_text(out, encoding="utf-8")
        print(f"{fn}: {len(edits)} anchored edits applied + reader helper inserted")

    print("\nverifying no pixel path still goes through PIL ...")
    bad = 0
    for fn in EDITS:
        t = (D / fn).read_text(encoding="utf-8")
        body = t.split("def _read_pixels")[0] + t.split("return _np.asarray(_I.open(path))")[-1]
        if "np.asarray(im)" in body or "np.asarray(Image.open" in body:
            print(f"  FAIL {fn} still reads pixels through PIL")
            bad += 1
        else:
            print(f"  ok   {fn}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
