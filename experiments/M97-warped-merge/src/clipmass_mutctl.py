"""Mutation control for the gate-weighted clip-mass accumulator (M97/M109).

Five green tests are five green tests. They only become evidence once each one
has been shown to go RED for the specific error it was written to catch, so
this plants those errors one at a time and requires the matching test to fail.

Each mutation is anchored on a unique full-line string and the run hard-errors
if the anchor does not land exactly once -- a mutation that silently fails to
apply produces a GREEN that looks exactly like a passing control.

The file is restored from a copy taken in TEMP before any edit, never from git:
a `git checkout --` here would revert to HEAD and destroy uncommitted work in a
tree four other agents are writing to.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
TARGET = REPO / "crates" / "strehl-core" / "src" / "merge.rs"
FILTER = "merge::tests::clip_mass"

# (name, anchor, replacement, test that must go RED, what error this is)
MUTATIONS = [
    (
        "M1-unweighted-numerator",
        "                        self.clip_w[s][i] += wt;",
        "                        self.clip_w[s][i] += 1.0;",
        "clip_mass_carries_the_same_weights_the_merged_value_does",
        "counts pinned frames instead of accumulating their weight, so the "
        "numerator is a count over a weighted denominator -- discipline 769",
    ),
    (
        "M2-unweighted-denominator",
        "        if self.wsum.is_empty() {\n            f32::from(self.n[i])\n"
        "        } else {\n            self.wsum[i]\n        }",
        "        f32::from(self.n[i])",
        "clip_mass_carries_the_same_weights_the_merged_value_does",
        "returns the integer admitted count as the divisor even under a soft "
        "kernel, so the fraction is taken against the wrong denominator",
    ),
    (
        "M3-absent-collapsed-to-zero",
        "        if self.clip_w[s].is_empty() {\n            None\n        } else {\n"
        "            Some(self.clip_w[s][i])\n        }",
        "        Some(if self.clip_w[s].is_empty() {\n            0.0\n        } else {\n"
        "            self.clip_w[s][i]\n        })",
        "clip_mass_is_absent_rather_than_zero_when_nothing_censors",
        "reports an estimator that never looked as one that looked and found "
        "nothing, making an unwired producer indistinguishable from clean",
    ),
]


def run_tests():
    env = dict(os.environ)
    cargo_bin = Path.home() / ".cargo" / "bin"
    env["PATH"] = str(cargo_bin) + os.pathsep + env["PATH"]
    env["CARGO_TARGET_DIR"] = r"C:\dev\strehl-target-m97"
    env["PYTHONIOENCODING"] = "utf-8"
    # Windows resolves the executable against the *parent* process PATH, not
    # the child env above, so name it absolutely rather than by name.
    cargo = cargo_bin / "cargo.exe"
    if not cargo.is_file():
        raise SystemExit(f"cargo not found at {cargo}")
    p = subprocess.run(
        [str(cargo), "test", "--release", "-p", "strehl-core", FILTER],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    return p.returncode, p.stdout + p.stderr


def main():
    original = TARGET.read_text(encoding="utf-8")
    backup = Path(tempfile.gettempdir()) / "m97_merge_clipmass_backup.rs"
    backup.write_text(original, encoding="utf-8")
    print(f"backup written: {backup} ({len(original)} chars)")

    results = []
    try:
        code, out = run_tests()
        base_pass = "test result: ok." in out
        print(f"\n[baseline] exit={code} pass={base_pass}")
        if code != 0 or not base_pass:
            print("BASELINE IS NOT GREEN -- controls cannot be interpreted.")
            print(out[-3000:])
            return 2

        for name, anchor, repl, must_fail, why in MUTATIONS:
            n = original.count(anchor)
            if n != 1:
                raise SystemExit(
                    f"MUTATION TARGET NOT FOUND for {name}: anchor occurs "
                    f"{n} times, expected exactly 1. Refusing to report a "
                    f"control that never planted its defect."
                )
            TARGET.write_text(original.replace(anchor, repl, 1), encoding="utf-8")
            code, out = run_tests()
            caught = code != 0 and must_fail in out
            results.append((name, code, caught, must_fail, why))
            print(f"[{name}] exit={code} caught_by_{must_fail}={caught}")
            if not caught:
                tail = [l for l in out.splitlines() if "test result" in l or "error" in l]
                print("   " + "\n   ".join(tail[:6]))
            TARGET.write_text(original, encoding="utf-8")
    finally:
        TARGET.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        assert TARGET.read_text(encoding="utf-8") == original, "RESTORE FAILED"
        print("\nrestored merge.rs byte-identically from TEMP copy")

    code, out = run_tests()
    print(f"[post-restore] exit={code} green={'test result: ok.' in out}")

    print("\n=== CONTROL SUMMARY ===")
    for name, c, caught, must_fail, why in results:
        print(f"{'RED (good)' if caught else 'GREEN (BAD)'}  {name}")
        print(f"    plants: {why}")
        print(f"    caught by: {must_fail}" if caught else "    NOT CAUGHT")
    ok = all(r[2] for r in results) and code == 0
    print(f"\n{len(results)}/{len(MUTATIONS)} mutations caught -- "
          f"{'ALL CONTROLS FIRE' if ok else 'AT LEAST ONE TEST IS DECORATIVE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
