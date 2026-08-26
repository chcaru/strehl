"""Commission the restore.rs applicator tests by planting defects.

A green test suite is a claim about the code. This script tests that claim by
breaking the code in five specific ways and requiring a specific test to go red
each time. A plant that stays green identifies a test that is not looking at
what it says it is looking at.

Discipline carried from earlier failures in this project:

  * Every mutation is anchored on a UNIQUE FULL-LINE string and the script hard
    errors if the anchor does not land. A bare `replace(x, y, 1)` that silently
    hits the wrong occurrence reports a false GREEN, which is a claim about the
    instrument rather than about the code.
  * The file is restored from a copy in TEMP, never with `git checkout --`, and
    the restore is verified by reading the bytes back and comparing.
  * Each plant names the test it must break, so a plant caught by some OTHER
    test counts as a MISS: it would mean the named test is not the one doing
    the work.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
TARGET = os.path.join(ROOT, "crates", "strehl-core", "src", "restore.rs")
CARGO = os.path.join(os.environ["USERPROFILE"], ".cargo", "bin", "cargo.exe")

# (label, [(anchor line, replacement line), ...], test that MUST go red)
PLANTS = [
    (
        "zero-phase broken: one tap made asymmetric",
        [
            (
                "                acc += t * (f64::from(plane[y * w + xl]) + f64::from(plane[y * w + xr]));",
                "                acc += t * (f64::from(plane[y * w + xl]) * 0.94 + f64::from(plane[y * w + xr]) * 1.06);",
            )
        ],
        "the_filter_sharpens_the_edge_without_moving_it",
    ),
    (
        "DC gain broken: centre tap normalised with 1.98 instead of 2.0",
        [
            (
                "    let mut taps = vec![1.0 - 2.0 * outer.iter().sum::<f64>()];",
                "    let mut taps = vec![1.0 - 1.98 * outer.iter().sum::<f64>()];",
            )
        ],
        "the_dc_gain_is_exactly_one_so_this_cannot_become_an_exposure_change",
    ),
    (
        "cap enforcement removed: realised overshoot no longer rescaled",
        [("    if realised > cap && realised > 1.0 {", "    if false {")],
        "the_dc_gain_is_exactly_one_so_this_cannot_become_an_exposure_change",
    ),
    (
        # Breaking the short-circuit ALONE is inert, and plant 6 demonstrates
        # that rather than asserting it. With gain_cap = 1.0 the identity is
        # defended three separate times: (1) the explicit short-circuit in
        # restore_plane; (2) the clamp in gain(), which pins the Wiener target
        # to 1.0 at every frequency so the least-squares right-hand side is
        # exactly zero; and (3) design_fir's realised-cap rescale, whose
        # lambda = (cap - 1)/(realised - 1) is exactly 0 when cap is 1, zeroing
        # every outer tap. All three must break before a green result here
        # means anything.
        #
        # An earlier version of this plant used `gain_cap > 1.0001`, which
        # makes the short-circuit fire MORE readily rather than less, and was
        # inert for that reason alone. It reported a MISS that I nearly read as
        # redundancy in the code. The mutation must be checked for potency in
        # the direction intended, not merely for being a change.
        "identity broken on ALL THREE routes: short-circuit, clamp, and rescale",
        [
            ("    if !(cfg.gain_cap > 1.0) {", "    if false {"),
            (
                "        g.clamp(1.0, self.gain_cap.max(1.0))",
                "        g.clamp(1.0, self.gain_cap.max(1.4))",
            ),
            (
                "    if realised > cap && realised > 1.0 {",
                "    if realised > cap + 0.5 && realised > 1.0 {",
            ),
        ],
        "a_gain_cap_of_one_is_byte_identical",
    ),
    (
        "filter made inert: design returns the identity kernel",
        [
            (
                "    let cap = cfg.gain_cap.max(1.0);",
                "    let cap = cfg.gain_cap.max(1.0);\n    return vec![1.0];\n    #[allow(unreachable_code)]\n    let cap = cap;",
            )
        ],
        "a_real_gather_loss_is_partly_recovered_measured_as_10_90_edge_width",
    ),
    (
        # EXPECTED INERT. This is not a test of the tests, it is a measurement
        # of the code: it demonstrates the redundancy claimed in plant 4 rather
        # than asserting it. Removing the short-circuit alone must leave the
        # identity intact, because the clamp and the rescale each independently
        # force it. If this ever goes RED, the redundancy has been lost and
        # plant 4's comment is wrong.
        "CONTROL, expected inert: short-circuit removed but clamp and rescale left intact",
        [("    if !(cfg.gain_cap > 1.0) {", "    if false {")],
        None,
    ),
]


def run_tests() -> tuple[bool, str]:
    proc = subprocess.run(
        [CARGO, "test", "-p", "strehl-core", "--lib", "restore::tests"],
        cwd=ROOT,
        capture_output=True,
    )
    out = proc.stdout.decode("utf-8", "replace") + proc.returncode.__str__()
    return proc.returncode == 0, out


def failing_tests(output: str) -> set[str]:
    names = set()
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("test restore::tests::") and line.endswith("FAILED"):
            names.add(line.split("::")[2].split(" ")[0])
    return names


def main() -> int:
    original = open(TARGET, "rb").read()
    backup = os.path.join(tempfile.gettempdir(), "restore_rs_plant_backup.rs")
    with open(backup, "wb") as fh:
        fh.write(original)
    assert open(backup, "rb").read() == original, "backup did not round trip"

    text = original.decode("utf-8")

    print("baseline (no plant): ", end="", flush=True)
    ok, out = run_tests()
    if not ok:
        print("RED -- the suite must be green before commissioning")
        print(out[-3000:])
        return 2
    print("GREEN")

    results = []
    try:
        for label, edits, expect in PLANTS:
            mutated = text
            for anchor, replacement in edits:
                count = mutated.count(anchor)
                if count != 1:
                    raise SystemExit(
                        f"ANCHOR NOT UNIQUE for plant {label!r}: found {count} "
                        f"occurrences of {anchor!r}. Refusing to plant, because a "
                        f"mis-landed mutation reports a meaningless GREEN."
                    )
                mutated = mutated.replace(anchor, replacement)
            assert mutated != text
            with open(TARGET, "w", encoding="utf-8", newline="") as fh:
                fh.write(mutated)
            ok, out = run_tests()
            reds = failing_tests(out)
            if expect is None:
                # An expected-inert control. The claim is that the identity
                # survives this mutation, so the pass condition is that
                # a_gain_cap_of_one_is_byte_identical stays GREEN.
                held = "a_gain_cap_of_one_is_byte_identical" not in reds
                results.append((label, "INERT", held, sorted(reds)))
                print(f"  {'HELD   ' if held else 'BROKE  '} {label}")
                if not held:
                    print("      the redundancy is GONE; plant 4's comment is now wrong")
                continue
            caught = (not ok) and (expect in reds)
            results.append((label, expect, caught, sorted(reds)))
            print(f"  {'CAUGHT ' if caught else 'MISSED '} {label}")
            if not caught:
                print(f"      expected {expect} to go red; red tests were {sorted(reds)}")
            elif len(reds) > 1:
                print(f"      (also red: {sorted(reds - {expect})})")
    finally:
        with open(TARGET, "wb") as fh:
            fh.write(original)
        restored = open(TARGET, "rb").read()
        if restored != original:
            shutil.copyfile(backup, TARGET)
            restored = open(TARGET, "rb").read()
        print(f"restore verified by read-back: {restored == original}")
        assert restored == original, "FAILED TO RESTORE restore.rs -- fix by hand from " + backup

    # Every plant is accounted for in exactly one bucket and the buckets sum to
    # the total, so a plant that was skipped cannot be read as one that passed.
    lethal = [r for r in results if r[1] != "INERT"]
    controls = [r for r in results if r[1] == "INERT"]
    caught_n = sum(1 for r in lethal if r[2])
    held_n = sum(1 for r in controls if r[2])
    print(
        f"\ncommissioning: {caught_n}/{len(lethal)} lethal plants caught by their "
        f"named test, {held_n}/{len(controls)} inert controls held"
    )
    print(f"  accounted for: {len(lethal)} + {len(controls)} = {len(results)} of {len(PLANTS)} planted")
    assert len(results) == len(PLANTS), "a plant produced no result row"

    print("post-restore rerun: ", end="", flush=True)
    ok, _ = run_tests()
    print("GREEN" if ok else "RED")
    good = caught_n == len(lethal) and held_n == len(controls) and ok
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
