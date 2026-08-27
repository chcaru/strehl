"""Negative control for true11.py's two repairs.

Rule earned earlier tonight: a green negative control is a claim about the
instrument, so the mutation is anchored on a unique FULL-LINE string and this
script hard-errors if the anchor does not land. `replace(x, y, 1)` that
silently matches nothing produces a GREEN that means nothing.

Git safety: the original is copied to TEMP and restored from that copy.
Never `git checkout --` - that reverts to HEAD and destroys uncommitted work.

Two arms:
  D1  a site whose master does not exist  -> must exit 1, must say FAIL
  D2  the unclipped 16->8 conversion       -> must put black pixels back
"""
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "true11.py")
DST = r"C:\dev\strehl-out\ORCH-TRUE11"

ANCHOR_SITE = '    ("wrapped-text-1", None, None, "known geometry, curvature, printed type"),\n'
DEFECT_SITE = '    ("wrapped-text-1-cpl", None, None, "known geometry, curvature, printed type"),\n'

ANCHOR_CLIP = "            c8 = np.clip((c.astype(np.uint32) + 128) >> 8, 0, 255).astype(np.uint8)\n"
DEFECT_CLIP = "            c8 = ((c.astype(np.uint32) + 128) >> 8).astype(np.uint8)\n"


def run():
    p = subprocess.run([sys.executable, TARGET], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def black_px():
    """Count pure-black pixels across every crop currently on disk."""
    n = 0
    files = 0
    for f in sorted(os.listdir(DST)):
        if not f.endswith(".png"):
            continue
        files += 1
        a = np.asarray(Image.open(os.path.join(DST, f)))
        n += int((a == 0).all(axis=-1).sum() if a.ndim == 3 else (a == 0).sum())
    return n, files


def mutate(src, anchor, defect):
    if anchor not in src:
        raise SystemExit("MUTATION TARGET NOT FOUND - the control is not "
                         "testing what it claims:\n  %r" % anchor[:70])
    if src.count(anchor) != 1:
        raise SystemExit("anchor is not unique (%d hits) - refusing"
                         % src.count(anchor))
    return src.replace(anchor, defect)


def main():
    orig = open(TARGET, encoding="utf-8").read()
    backup = os.path.join(tempfile.gettempdir(), "true11.py.orig")
    shutil.copy2(TARGET, backup)
    print("backup -> %s" % backup)

    results = []
    try:
        print("\n=== HOLD: repaired file must pass and must cut every site ===")
        rc, out = run()
        held = rc == 0 and "missing 0 = 4 of 4" in out
        base_black, base_files = black_px()
        print("  rc=%d  partition line present=%s  black px across %d crops=%d"
              % (rc, "missing 0 = 4 of 4" in out, base_files, base_black))
        results.append(("HOLD-repaired-passes", held, True))

        print("\n=== D1: a site with no master must FAIL, not print and exit 0 ===")
        open(TARGET, "w", encoding="utf-8").write(
            mutate(orig, ANCHOR_SITE, DEFECT_SITE))
        rc, out = run()
        caught = rc == 1 and "FAIL:" in out and "missing 1" in out
        print("  rc=%d (want 1)  says FAIL=%s  partition shows missing 1=%s"
              % (rc, "FAIL:" in out, "missing 1" in out))
        results.append(("D1-missing-site-caught", caught, True))

        print("\n=== D2: unclipped conversion must put black pixels back ===")
        open(TARGET, "w", encoding="utf-8").write(
            mutate(orig, ANCHOR_CLIP, DEFECT_CLIP))
        rc, out = run()
        defect_black, _ = black_px()
        # the whole claim: the clip is what removes them
        caught = rc == 0 and defect_black > base_black
        print("  rc=%d  black px with defect=%d  vs repaired=%d  delta=+%d"
              % (rc, defect_black, base_black, defect_black - base_black))
        results.append(("D2-white-wrap-caught", caught, True))
    finally:
        shutil.copy2(backup, TARGET)
        restored = open(TARGET, encoding="utf-8").read()
        print("\nrestored from TEMP copy: byte-identical=%s" % (restored == orig))
        if restored != orig:
            raise SystemExit("RESTORE FAILED - true11.py is not as it was")
        # leave the tree holding the repaired output, not the defect's
        run()

    print("\n=== verdict ===")
    ok = 0
    for name, got, want in results:
        good = got == want
        ok += good
        print("  %-26s %s" % (name, "OK" if good else "FAIL"))
    print("  caught %d + missed %d = %d of %d"
          % (ok, len(results) - ok, len(results), len(results)))
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    sys.exit(main())
