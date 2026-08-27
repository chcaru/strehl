"""Freeze the softness instrument so a later re-run can only differ by the merge.

WHY THIS EXISTS. Another lane is about to change the merge's noise gate, and the
plan is to read the four exact-ceiling ratios before and after. That comparison
is only worth anything if the instrument is byte-identical across the two
readings. Everything else -- the tile selection, the block size, the noise-floor
estimator, the envelope, the seven arms, the library versions, the developing
binary -- has to be nailed down in advance, because any of them moving would be
indistinguishable from the merge moving.

The pin lives OUTSIDE the working tree. Six lanes are editing this repository and
a pin that can be edited by the thing it is meant to detect is not a pin. The
manifest is committed inside the tree so the hashes are reviewable, but the
authoritative copies are elsewhere and --verify compares the two.

WHAT IS PINNED, and each of these has bitten someone:
  - the instrument sources and their transitive imports, by SHA256;
  - the numpy / opencv / tifffile versions, because the estimator is a chain of
    library calls and a resampling or RNG change would move the number silently;
  - the developing binary by SHA256, NOT by size -- the two candidate binaries on
    this box are 9,568,768 bytes each and differ in hash;
  - the exact command lines, including the flags left at default;
  - the four before-readings themselves, so the after-run has something to be
    compared against that was written down first.

A PRE-REGISTERED HAZARD, recorded now rather than discovered later. The reference
arm is developed by the SAME binary as the master, one frame per otherwise-empty
directory, which is what makes the demosaic common-mode. If the merge fix also
changes single-frame develops -- and a convex-combination merge over one frame
should be an identity, but "should" is not a measurement -- then the CEILING
moves too, and a change in the ratio is no longer attributable to the master
alone. So the after-run must hash the reference TIFFs and compare them to the
before-run's hashes. If they are identical the ceiling is fixed and the ratio
change is the master. If they are not, the reading must be decomposed before it
is interpreted, and that must be stated rather than averaged over.

Usage:
  python pin_instrument.py create <pindir>
  python pin_instrument.py verify <pindir>
"""

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

SOURCES = [
    "softness_verdict3.py",
    "corpus_softness.py",
    "envelope_null.py",
    "density_check.py",
    "floor_sensitivity.py",
]

BINARY = pathlib.Path(
    r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe")

# The before-reading. Ratios are the raw medians at a COMPLETE bracket (n == N),
# with the envelope_null correction factor beside each, measured at the tile and
# size named. Anything the after-run reports must be read against these.
BEFORE = {
    "coffee-bubbles": dict(n=19, N=19, size=2048, ratio=0.9007,
                           ci=[0.8796, 0.9194], null=0.9988, corrected=0.9018),
    "109MSDCF": dict(n=22, N=22, size=2048, ratio=0.8735,
                     ci=[0.8595, 0.8934], null=0.9865, corrected=0.8855),
    "119MSDCF": dict(n=33, N=33, size=2048, ratio=0.8110,
                     ci=[0.7869, 0.8311], null=0.9955, corrected=0.8147),
    "flower-bud-alone-cpl": dict(n=205, N=205, size=1024, ratio=0.9389,
                                 ci=[0.8861, 1.0130], null=0.9851,
                                 corrected=0.9531),
}

COMMANDS = [
    "python corpus_softness.py --keep --out <rows>.tsv",
    "python density_check.py <density>.tsv 2048 coffee-bubbles:19 109MSDCF:22 "
    "119MSDCF:33",
    "python density_check.py <density_full>.tsv 1024 flower-bud-alone-cpl:205",
    "python envelope_null.py <subject> 13,22,33",
    "python envelope_null.py flower-bud-alone-cpl 13,26,52,104",
    "python floor_sensitivity.py 2048 coffee-bubbles:19 109MSDCF:22 119MSDCF:33",
    "python floor_sensitivity.py 1024 flower-bud-alone-cpl:205",
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def versions():
    import numpy
    import cv2
    import tifffile
    return {
        "python": sys.version.split()[0],
        "numpy": numpy.__version__,
        "cv2": cv2.__version__,
        "tifffile": tifffile.__version__,
    }


def git_head(here):
    r = subprocess.run(["git", "-C", str(here), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def main():
    op, pindir = sys.argv[1], pathlib.Path(sys.argv[2])
    here = pathlib.Path(__file__).parent

    if op == "create":
        (pindir / "src").mkdir(parents=True, exist_ok=True)
        man = {
            "purpose": "before-reading for the merge noise-gate change",
            "git_head": git_head(here),
            "binary": {"path": str(BINARY), "sha256": sha(BINARY),
                       "bytes": BINARY.stat().st_size},
            "versions": versions(),
            "sources": {},
            "commands": COMMANDS,
            "before": BEFORE,
            "hazard": "reference frames are developed by the SAME binary as the "
                      "master; if the merge fix changes single-frame develops the "
                      "ceiling moves too. The after-run MUST hash the frame TIFFs "
                      "and compare to the before-run before interpreting a delta.",
        }
        for s in SOURCES:
            shutil.copy2(here / s, pindir / "src" / s)
            man["sources"][s] = sha(here / s)
        (pindir / "MANIFEST.json").write_text(
            json.dumps(man, indent=2), encoding="utf-8")
        rows = ["file\tsha256"]
        rows += [f"{k}\t{v}" for k, v in man["sources"].items()]
        rows.append(f"strehl.exe\t{man['binary']['sha256']}")
        (here / "PIN-MANIFEST.tsv").write_text("\n".join(rows) + "\n",
                                               encoding="utf-8")
        print(f"pinned to {pindir}")
        print(f"  git HEAD  {man['git_head']}")
        print(f"  binary    {man['binary']['sha256']}")
        for k, v in man["sources"].items():
            print(f"  {k:<26}{v}")
        print(f"  versions  {man['versions']}")
        return

    man = json.loads((pindir / "MANIFEST.json").read_text(encoding="utf-8"))
    bad = []
    for s, h in man["sources"].items():
        live = sha(here / s) if (here / s).exists() else "MISSING"
        copy = sha(pindir / "src" / s)
        state = "ok" if live == h == copy else "CHANGED"
        if state != "ok":
            bad.append(s)
        print(f"  {s:<26}{state:<9}live={live[:16]} pinned={h[:16]}")
    b = sha(BINARY) if BINARY.exists() else "MISSING"
    print(f"  {'strehl.exe':<26}"
          f"{'ok' if b == man['binary']['sha256'] else 'CHANGED':<9}{b[:16]}")
    if b != man["binary"]["sha256"]:
        bad.append("strehl.exe")
    v = versions()
    for k, val in man["versions"].items():
        if v.get(k) != val:
            bad.append(f"{k} {val}->{v.get(k)}")
            print(f"  LIBRARY MOVED {k}: pinned {val}, live {v.get(k)}")
    print("\nVERIFY: " + ("CLEAN -- comparison is valid" if not bad else
                          f"BROKEN -- {bad}; before/after comparison is dead"))
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
