"""N4: plant a defect in the instrument and confirm the registered bars catch it.

The defect: `merge_pattern` stops applying the transform, so every frame is read
at the reference coordinates. That is the single most plausible silent failure
of this instrument -- if the warp were never applied, every number it produced
would be a measurement of nothing, and F would read ~W everywhere.

The bar that must catch it is N3, the registered decorrelation bound: with
BIG_SHIFT_PX per frame the frames cannot possibly stay correlated, so
F < 2/n = 0.25 is required. Unwarped, F must rise to about W.

Discipline: the mutation is anchored on a unique multi-line string and this
script HARD ERRORS if it does not land exactly once. A green control run that
silently patched nothing is a claim about the harness, not about the code.

Restore is from a temp copy taken here, never `git checkout --`: four sibling
agents have uncommitted work in this tree.
"""

import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "crates" / "strehl-cli" / "examples" / "m90-rho.rs"
BACKUP = pathlib.Path(os.environ["TEMP"]) / "m90-rho.rs.n4-backup"
CARGO = pathlib.Path(os.environ["USERPROFILE"]) / ".cargo" / "bin" / "cargo.exe"
TARGET = ROOT / "experiments" / "M90-prnu" / "target-m90"
EXE = TARGET / "release" / "examples" / "m90-rho.exe"

ANCHOR = """            let (sx, sy) = t.apply_at(f64::from(lat.xs[i]), f64::from(lat.ys[i]), cx, cy);
            let va = f64::from(resampler.sample(a, sx, sy));
            let vb = f64::from(resampler.sample(b, sx, sy));
            ma[i] += va;"""

PLANT = """            let (sx, sy) = (f64::from(lat.xs[i]), f64::from(lat.ys[i]));
            let va = f64::from(resampler.sample(a, sx, sy));
            let vb = f64::from(resampler.sample(b, sx, sy));
            ma[i] += va;"""


def build():
    r = subprocess.run(
        [str(CARGO), "build", "--release", "-p", "strehl-cli",
         "--example", "m90-rho", "--target-dir", str(TARGET)],
        cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        raise SystemExit("build failed:\n" + r.stderr.decode("utf-8", "replace"))


def control():
    r = subprocess.run([str(EXE), "control"], cwd=ROOT, capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def n3_rows(out):
    """Rows of the N3 block only, anchored on its exact header."""
    rows, grab = [], False
    for line in out.splitlines():
        if line.strip().startswith("--- N3 decorrelation bound"):
            grab = True
            continue
        if grab:
            if line.strip().startswith("---"):
                break
            if any(k in line for k in ("Nearest", "Bilinear", "CatmullRom")):
                rows.append(line.strip())
    if not rows:
        raise SystemExit("N3 block not found in control output -- parser is broken")
    return rows


def main():
    original = SRC.read_bytes()
    shutil.copy2(SRC, BACKUP)
    print(f"backed up to {BACKUP}")

    text = original.decode("utf-8")
    # The working tree is CRLF (core.autocrlf=true), so match on a normalised
    # copy. Restore is byte-exact from the backup regardless.
    norm = text.replace("\r\n", "\n")
    hits = norm.count(ANCHOR)
    if hits != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND: anchor occurs {hits} times, expected 1. "
            "Refusing to run -- a control that patches nothing proves nothing.")

    try:
        SRC.write_bytes(norm.replace(ANCHOR, PLANT, 1).encode("utf-8"))
        print("planted: merge_pattern no longer applies the transform")
        build()
        out = control()
        rows = n3_rows(out)
        print("\nN3 rows WITH the defect planted:")
        for r in rows:
            print("  " + r)
        planted_fails = sum(1 for r in rows if "FAIL" in r)
        print(f"\nN3 failures with defect planted: {planted_fails} of {len(rows)}")
        caught = planted_fails > 0
    finally:
        shutil.copy2(BACKUP, SRC)
        # copy2 preserves the backup's mtime, which is OLDER than the artefact
        # just built from the planted source -- cargo would then skip the
        # rebuild and leave the PLANTED binary on disk while the source reads
        # clean. Touch forward so the rebuild actually happens.
        os.utime(SRC, None)
        restored = SRC.read_bytes()
        print(f"\nrestored from temp copy; byte-identical: {restored == original}")
        if restored != original:
            raise SystemExit("RESTORE FAILED -- file does not match the original")
        build()

    out = control()
    rows = n3_rows(out)
    print("\nN3 rows after restore:")
    for r in rows:
        print("  " + r)
    clean_fails = sum(1 for r in rows if "FAIL" in r)
    print(f"N3 failures after restore: {clean_fails} of {len(rows)}")

    print()
    if caught and clean_fails == 0:
        print("N4 PASS: the registered bar caught the planted defect and is "
              "green again after restore.")
        return 0
    if not caught:
        print("N4 FAIL: the planted defect was NOT caught. Every number this "
              "instrument produced is void.")
    if clean_fails:
        print("N4 FAIL: bars still red after restore.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
