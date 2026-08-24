"""Negative controls on the Rust tests that certify the co-siting fix.

Discipline 594: a green test suite is a claim about the code only if the suite
could have said otherwise, and I have to show it saying otherwise. Each mutation
below plants a specific, plausible defect and names the test that must catch it.
A mutation that leaves the suite green is a test I should not be trusting.

Two operating hazards, both previously measured on this machine and both avoided
here deliberately:

  * A mutation anchored on a short substring can land somewhere I did not intend
    and "pass" for the wrong reason. Every anchor below is a unique full line,
    and a miss is a hard error, not a silent skip.
  * Restoring a file with a preserved mtime lets cargo skip the rebuild, so the
    mutated binary stays live under clean source and the restore reads green
    when nothing was actually rebuilt. The restore here writes bytes and stamps
    the mtime forward, and the final baseline re-run is what proves it took.
"""

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl")
TGT = ROOT / "crates" / "strehl-cli" / "src" / "image_out.rs"
ENV = dict(os.environ)
ENV["PATH"] = os.path.expanduser(r"~\.cargo\bin") + os.pathsep + ENV["PATH"]
ENV["CARGO_TARGET_DIR"] = str(ROOT / "target-m95")
CARGO = os.path.join(os.path.expanduser("~"), ".cargo", "bin", "cargo.exe")
assert os.path.exists(CARGO), CARGO

MUTATIONS = [
    (
        "R1-backwards",
        "the correction applied in the wrong direction",
        "    let red = resample_shift(&plane(0), width, height, d, d);\n"
        "    let blue = resample_shift(&plane(2), width, height, -d, -d);\n",
        "    let red = resample_shift(&plane(0), width, height, -d, -d);\n"
        "    let blue = resample_shift(&plane(2), width, height, d, d);\n",
        "the_binned_path_leaves_green_untouched_and_separates_red_from_blue",
    ),
    (
        "R2-green-resampled",
        "green resampled too, i.e. the fix blurs everything",
        "        *out = develop_pixel([red[i], src[i][1], blue[i]], dev);\n",
        "        *out = develop_pixel([red[i], green[i], blue[i]], dev);\n",
        "the_binned_path_leaves_green_untouched_and_separates_red_from_blue",
    ),
    (
        "R3-wrong-magnitude",
        "shift of half a binned pixel instead of a quarter",
        "const COSITE_SHIFT: f32 = 0.25;\n",
        "const COSITE_SHIFT: f32 = 0.5;\n",
        "the_binned_path_leaves_green_untouched_and_separates_red_from_blue",
    ),
    (
        "R4-no-partition-of-unity",
        "a kernel whose weights do not sum to one",
        "        (A + 2.0) * t3 - (A + 3.0) * t2 + 1.0,\n",
        "        (A + 2.0) * t3 - (A + 3.0) * t2 + 0.98,\n",
        "a_constant_plane_is_invariant_including_at_the_clamped_borders",
    ),
]

# R2 needs a `green` binding to exist for the mutation to compile at all.
R2_PREP = (
    "    let blue = resample_shift(&plane(2), width, height, -d, -d);\n",
    "    let blue = resample_shift(&plane(2), width, height, -d, -d);\n"
    "    let green = resample_shift(&plane(1), width, height, d, d);\n",
)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_tests(filt="image_out"):
    r = subprocess.run(
        [CARGO, "test", "-p", "strehl-cli", "--bin", "strehl", filt],
        cwd=ROOT, env=ENV, capture_output=True, text=True,
    )
    return r.returncode, (r.stdout + r.stderr)


def write(path, text):
    path.write_text(text, encoding="utf-8", newline="")
    os.utime(path, (time.time() + 1, time.time() + 1))


def main():
    backup = pathlib.Path(tempfile.gettempdir()) / "M95-image_out.rs.bak"
    shutil.copyfile(TGT, backup)
    original = TGT.open("r", encoding="utf-8", newline="").read()
    orig_sha = sha(TGT)
    print("backed up to %s  sha %s" % (backup, orig_sha[:16]))

    rc, out = run_tests()
    print("\nBASELINE: rc=%d  %s" % (rc, "GREEN" if rc == 0 else "RED"))
    if rc != 0:
        print(out[-3000:])
        return 1

    results = []
    try:
        for name, why, old, new, expect in MUTATIONS:
            text = original
            if name.startswith("R2"):
                assert text.count(R2_PREP[0]) == 1, "R2 prep anchor not unique"
                text = text.replace(R2_PREP[0], R2_PREP[1], 1)
            n = text.count(old)
            if n != 1:
                raise SystemExit(
                    "MUTATION TARGET NOT FOUND OR NOT UNIQUE for %s: %d matches of %r"
                    % (name, n, old[:60])
                )
            write(TGT, text.replace(old, new, 1))
            rc, out = run_tests()
            caught = rc != 0
            named = expect in out and "FAILED" in out or (expect + " ... FAILED") in out
            failing = [
                ln.split()[1] for ln in out.splitlines()
                if ln.startswith("test image_out::tests::") and ln.rstrip().endswith("FAILED")
            ]
            print("\n%-22s %s" % (name, why))
            print("   rc=%d -> %s" % (rc, "RED (caught)" if caught else "GREEN (MISSED)"))
            print("   failing tests: %s" % (", ".join(f.split("::")[-1] for f in failing) or "none"))
            ok = caught and any(expect in f for f in failing)
            print("   expected %s to fail: %s" % (expect, "YES" if ok else "NO"))
            results.append((name, ok, failing))
    finally:
        write(TGT, original)

    assert sha(TGT) == orig_sha, "restore did not reproduce the original bytes"
    rc, out = run_tests()
    print("\nRESTORED: sha matches original, rc=%d %s" % (rc, "GREEN" if rc == 0 else "RED"))

    allok = all(ok for _, ok, _ in results) and rc == 0
    print("\n%d/%d mutations caught by the named test. %s"
          % (sum(1 for _, ok, _ in results), len(results),
             "ALL CONTROLS PASS" if allok else "AT LEAST ONE CONTROL FAILED"))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
