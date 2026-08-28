"""Is the DEF-2f858c62 arm already the HEAD baseline?

ORCH's 13-commit drift list is entirely contained in pin 2f858c62 -- verified
with `git merge-base --is-ancestor` for all twelve named commits, and
`gatefloor.rs` exists at that pin. Only two commits separate 2f858c62 from HEAD
d2193a55 in crates/:

    9c11209e   touches ONLY crates/strehl-cli/examples/ -- three example
               binaries, zero library or CLI source. Cannot reach `strehl stack`.
    aa40cc78   adds --cover / STREHL_COVER, and puts +400 lines into
               align_cmd.rs. Its own doc says DEFAULT_COVER_MODE = Scale and
               "THE DEFAULT DOES NOT MOVE."

THAT LAST SENTENCE IS A DOC COMMENT, NOT A MEASUREMENT. A claim about the shape
of the code is a claim about a commit, and +400 lines in the alignment path is
exactly where an inert-looking change stops being inert. `eb5145d4` is in
recent history precisely because an exact-equality geometry guard broke 11 of 26
renders while passing every test it had.

So: render the same subjects at default flags with the HEAD binary and compare
DECODED ARRAYS against the 2f858c62 arm. A file hash is not a pixel gauge -- a
TIFF differing only in an ImageDescription tag has a different sha and identical
samples, which overturned a correct finding earlier tonight.

Subjects are chosen to stress the two paths at issue, not for convenience:
  * highly-angled-ruler-mm-cpl -- the ONE subject whose alignment REFUSES. If
    +400 lines in align_cmd.rs can move a render, it moves here first.
  * 109MSDCF                   -- the provenance exemplar, 22 frames.
  * coffee-bubbles             -- the mid-scale mottle flagship, 19 frames.

If all three are bit-identical, DEF-2f858c62 IS the HEAD baseline and five lanes
unblock now instead of in 3.5 hours. If any differs, the full 26 must re-render.
"""
import hashlib
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import tifffile

HEAD_EXE = Path(r"C:\dev\strehl-out\acceptance-pins\d2193a55\target\release\strehl.exe")
ARM = Path(r"C:\dev\strehl-out\BUILD-RECERT\arms\DEF-2f858c62")
OUT = Path(r"C:\dev\strehl-out\BUILD-RECERT\headcheck")
SRC = Path(r"D:\personal\macro")

SUBJECTS = ["highly-angled-ruler-mm-cpl", "109MSDCF", "coffee-bubbles"]


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16].upper()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"HEAD binary sha16 : {sha16(HEAD_EXE)}")
    print(f"arm binary sha16  : A058F737DFE695F7 (from provenance)\n")

    rows = []
    for subj in SUBJECTS:
        ref = ARM / f"{subj}--DEF-2f858c62.tiff"
        if not ref.exists():
            print(f"{subj:<30} SKIP -- no reference at {ref}")
            continue
        dst = OUT / f"{subj}--HEAD.tiff"
        t0 = time.time()
        # Identical argv to the arm's provenance, only the binary changes.
        cmd = [str(HEAD_EXE), "stack", str(SRC / subj), "--out", str(dst),
               "--srgb", "--auto-exposure"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        dt = time.time() - t0
        if p.returncode != 0 or not dst.exists():
            tail = (p.stderr or p.stdout).strip().splitlines()[-3:]
            print(f"{subj:<30} RENDER FAILED rc={p.returncode} {tail}")
            rows.append((subj, "RENDER FAILED", None, None))
            continue

        a = tifffile.imread(ref)
        b = tifffile.imread(dst)
        if a.shape != b.shape:
            print(f"{subj:<30} SHAPE DIFFERS {a.shape} vs {b.shape}")
            rows.append((subj, f"SHAPE {a.shape}!={b.shape}", None, None))
            dst.unlink()
            continue
        same = bool(np.array_equal(a, b))
        d = np.abs(a.astype(np.int64) - b.astype(np.int64))
        nz = int((d != 0).sum())
        print(f"{subj:<30} {'BIT-IDENTICAL' if same else 'DIFFERS':<14} "
              f"samples={a.size:,}  differing={nz:,} "
              f"({100.0 * nz / a.size:.4f}%)  max|d|={int(d.max())}  "
              f"filesha {sha16(ref)} vs {sha16(dst)}  [{dt:.0f}s]")
        rows.append((subj, same, nz, int(d.max())))
        dst.unlink()   # 190 MB each; ten lanes share this disk

    ok = [r for r in rows if r[1] is True]
    print(f"\n{len(ok)}/{len(rows)} subjects bit-identical between "
          f"2f858c62 and HEAD d2193a55 at default flags")
    if rows and len(ok) == len(rows):
        print("VERDICT: the two commits are INERT on the shipping render path.")
        print("         DEF-2f858c62 IS the HEAD baseline.")
        return 0
    print("VERDICT: HEAD moves pixels. The full 26 must be re-rendered.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
