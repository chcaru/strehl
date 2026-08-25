"""Mutation control for the robust pass-one election wiring (M97e).

Ten green tests are ten green tests. They become evidence only once each has
been shown to go RED for the specific error it was written to catch, so this
plants those errors one at a time and requires the matching test to fail.

The four defects are the four ways this wiring can be wrong while still
compiling, still running and still producing a plausible photograph:

  M1  the gate never fires  -- the ring, the kernel and the election all run,
      the frames are all elected, and every z is zero. This is the failure mode
      the project keeps rediscovering: a feature that is wired, green, and
      inert. It is the reason `plant_soft_rejects...` exists at all.
  M2  the chunk tail is never elected -- silently drops the last Z_HALF frames
      of every chunk. An argmax absorbs that almost invisibly: the output is
      merely a little less sharp at the far end of the focus sweep.
  M3  the ring double-elects -- a frame is folded twice. An argmax is
      idempotent under a duplicate, so nothing downstream can see it.
  M4  the cross-chunk reduce collapses the ungated election -- the gate applies
      inside a chunk and stops applying between chunks, so a rejected frame
      returns at a boundary and the defect is periodic in chunk length.

Each mutation is anchored on a unique full-line string and the run hard-errors
if the anchor does not land exactly once: a mutation that silently fails to
apply produces a GREEN indistinguishable from a passing control.

The file is restored from a copy taken in TEMP before any edit, never from git.
A `git checkout --` here would revert to HEAD and destroy uncommitted work in a
tree that ten other agents are writing to.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
TARGET = REPO / "crates" / "strehl-core" / "src" / "merge.rs"

# Every test that is meant to police this wiring. Named explicitly rather than
# by prefix so that a test which stops running is a missing name, not a silently
# smaller filter.
TESTS = [
    "ungated_arm_reproduces_the_shipped_election_bit_for_bit",
    "the_ring_elects_every_frame_exactly_once_at_every_chunk_length",
    "finish_chunk_is_idempotent",
    "trap_soft_keeps_the_only_frame_that_resolves_the_pixel",
    "plant_soft_rejects_a_moved_frame_that_wins_by_a_hair",
    "absorb_combines_gated_scores_across_chunks",
    "folding_without_luma_under_a_robust_election_panics",
    "absorbing_a_robust_pass_one_into_a_plain_one_panics",
    "fold_with_luma_is_fold_when_the_feature_is_off",
    "arm_settings_parse_and_typos_are_refused",
]

# (name, anchor, replacement, test that must go RED, what error this plants)
MUTATIONS = [
    (
        "M1-gate-never-fires",
        "        self.fold_slot(order[Z_HALF], false)",
        "        self.fold_slot(order[Z_HALF], true)",
        "plant_soft_rejects_a_moved_frame_that_wins_by_a_hair",
        "elects every centre with z=0, so the whole ring and kernel run and "
        "the gate is inert -- wired, green and doing nothing",
    ),
    (
        "M2-tail-never-elected",
        "        for back in (0..tail).rev() {",
        "        for back in (0..0).rev() {",
        "the_ring_elects_every_frame_exactly_once_at_every_chunk_length",
        "drops the trailing Z_HALF frames of every chunk, which an argmax "
        "absorbs as a small loss of sharpness and nothing else",
    ),
    (
        "M3-leading-frame-elected-twice",
        "        if self.seen <= Z_HALF {",
        "        if self.seen <= Z_HALF + 1 {",
        "the_ring_elects_every_frame_exactly_once_at_every_chunk_length",
        "elects frame Z_HALF both as a leading frame and later as a centre; "
        "an argmax is idempotent under a duplicate so it is invisible",
    ),
    (
        "M4-reduce-collapses-ungated",
        "                let winners = a.election.winners();",
        "                let winners = a.election.ungated_winners().to_vec();",
        "absorb_combines_gated_scores_across_chunks",
        "collapses the ungated election at the chunk boundary, so the gate "
        "applies within a chunk and stops applying between chunks",
    ),
]


def run_tests():
    """Run every policing test in one invocation and return (code, output)."""
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
    # `merge::tests::` alone would also sweep in the unrelated tests in that
    # module; the election tests do not share a prefix, so run the module and
    # check the named tests are present.
    p = subprocess.run(
        [str(cargo), "test", "--release", "-p", "strehl-core", "merge::tests::"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    return p.returncode, p.stdout + p.stderr


def missing_tests(out):
    return [t for t in TESTS if t not in out]


def main():
    original = TARGET.read_text(encoding="utf-8")
    backup = Path(tempfile.gettempdir()) / "m97_merge_election_backup.rs"
    backup.write_text(original, encoding="utf-8")
    print(f"backup written: {backup} ({len(original)} chars)")

    results = []
    try:
        code, out = run_tests()
        base_pass = "test result: ok." in out
        gone = missing_tests(out)
        print(f"[baseline] exit={code} pass={base_pass} missing={gone}")
        if code != 0 or not base_pass:
            print("BASELINE IS NOT GREEN -- controls cannot be interpreted.")
            print(out[-3000:])
            return 2
        if gone:
            print(f"THESE TESTS DID NOT RUN: {gone}")
            print("A control cannot police a test that the filter never selected.")
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
            caught = code != 0 and must_fail in out and "test result: FAILED" in out
            # A defect caught by the *wrong* test is still a real signal, but it
            # is not the claim being made, so record what actually failed.
            failed_here = [t for t in TESTS if f"{t} ... FAILED" in out or
                           (t in out.split("failures:")[-1] if "failures:" in out else False)]
            results.append((name, code, caught, must_fail, why, failed_here))
            print(f"[{name}] exit={code} caught_by_{must_fail}={caught} "
                  f"failed={failed_here}")
            if not caught:
                tail = [l for l in out.splitlines()
                        if "test result" in l or "error[" in l]
                print("   " + "\n   ".join(tail[:8]))
            TARGET.write_text(original, encoding="utf-8")
    finally:
        TARGET.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        assert TARGET.read_text(encoding="utf-8") == original, "RESTORE FAILED"
        print("\nrestored merge.rs byte-identically from TEMP copy")

    code, out = run_tests()
    print(f"[post-restore] exit={code} green={'test result: ok.' in out}")

    print("\n=== CONTROL SUMMARY ===")
    for name, c, caught, must_fail, why, failed_here in results:
        print(f"{'RED (good)' if caught else 'GREEN (BAD)'}  {name}")
        print(f"    plants: {why}")
        if caught:
            print(f"    caught by: {must_fail}")
        else:
            print(f"    NOT CAUGHT (failures seen: {failed_here})")
    ok = all(r[2] for r in results) and code == 0
    print(f"\n{sum(1 for r in results if r[2])}/{len(MUTATIONS)} mutations caught -- "
          f"{'ALL CONTROLS FIRE' if ok else 'AT LEAST ONE TEST IS DECORATIVE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
