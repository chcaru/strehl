#!/usr/bin/env python3
"""M111 -- negative control for softgate.rs.

A green test suite is a claim about the instrument, not about the code. This
plants five mutations that a correct suite must catch and asserts that each one
turns the suite RED. A mutation that survives names a hole in the tests.

Rules this obeys, from the corpus and from M111's own scars:

  * Every anchor is a UNIQUE FULL LINE, checked by line equality rather than
    substring count, because an indented anchor also matches deeper-indented
    copies. A miss is a hard error, never a silent pass.
  * The expected exit code is asserted EXACTLY. "Nonzero" is not a test: rule
    47's corrupted `$LASTEXITCODE` is 0 on PowerShell 7 and -1 on 5.1, so a
    nonzero check is satisfied by the corruption itself.
  * Restore is from a byte copy taken before the first edit, never
    `git checkout --`, which reverts to HEAD and has destroyed uncommitted work
    on this machine. The file is re-stamped after restore so cargo cannot skip
    the rebuild and leave a sabotaged binary live.
  * The restore is verified by SHA-256 and the suite is re-run green at the end,
    so the control tests its own cleanup as well as its sabotage.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time

SRC = r"C:\dev\blog\death-of-software\projects\strehl\crates\strehl-core\src\softgate.rs"
BACKUP = r"C:\dev\strehl-out\M111\softgate.rs.orig"
REPO = r"C:\dev\blog\death-of-software\projects\strehl"
CARGO = os.path.join(os.environ["USERPROFILE"], ".cargo", "bin", "cargo.exe")

PASS, FAIL = 0, 101  # cargo test: 0 on success, 101 on a failing test
# A distinct code for "the instrument or its environment broke", so a harness
# fault can never be read as a measured result. See the post-restore leg.
HARNESS = 3

MUTATIONS = [
    ("M1 wrong kernel width",
     "        let w = (-0.5 * z * z).exp();",
     "        let w = (-1.0 * z * z).exp();"),
    ("M2 above-winner frames penalised",
     "            return 1.0;",
     "            return 0.0;"),
    ("M3 n_eff returns the plain sum",
     "    if s2 <= 0.0 { 0.0 } else { (s * s / s2) as f32 }",
     "    if s2 <= 0.0 { 0.0 } else { s as f32 }"),
    ("M4 tolerance loses its sqrt(2) -- FOCUS_NOISE_SD's unit broken",
     "        self.threshold * std::f32::consts::SQRT_2 * FOCUS_NOISE_SD",
     "        self.threshold * FOCUS_NOISE_SD"),
    ("M5 NaN responses admitted at full weight",
     "            return 0.0;\n        }\n        let gap = best - focus;",
     "            return 1.0;\n        }\n        let gap = best - focus;"),
]


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest().upper()


def run_tests():
    env = dict(os.environ, CARGO_TARGET_DIR=r"C:\dev\strehl-out\M111\.cargo-target")
    p = subprocess.run([CARGO, "test", "-p", "strehl-core", "--lib", "softgate"],
                       cwd=REPO, env=env, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def apply(text, old, new, tag):
    """Line-exact for single-line anchors; count-checked for multi-line ones."""
    if "\n" in old:
        n = text.count(old)
        if n != 1:
            sys.exit(f"MUTATION TARGET NOT FOUND [{tag}]: expected 1 block, found {n}")
        return text.replace(old, new, 1)
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln == old]
    if len(hits) != 1:
        sys.exit(f"MUTATION TARGET NOT FOUND [{tag}]: {len(hits)} lines equal the anchor "
                 f"(need exactly 1). Anchor: {old!r}")
    lines[hits[0]] = new
    return "\n".join(lines)


def main():
    os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
    shutil.copy2(SRC, BACKUP)
    original = sha(SRC)
    print(f"softgate.rs SHA-256 {original[:16]}...  backed up to {BACKUP}")

    code, out = run_tests()
    if code != PASS:
        sys.exit(f"BASELINE IS NOT GREEN (exit {code}); the control cannot run.\n{out[-3000:]}")
    print(f"baseline GREEN (exit {code} == {PASS})\n")

    with open(SRC, "r", encoding="utf-8") as fh:
        pristine = fh.read()

    caught, missed = 0, []
    try:
        for tag, old, new in MUTATIONS:
            mutated = apply(pristine, old, new, tag)
            if mutated == pristine:
                sys.exit(f"MUTATION IS A NO-OP [{tag}]")
            with open(SRC, "w", encoding="utf-8", newline="") as fh:
                fh.write(mutated)
            os.utime(SRC, None)
            time.sleep(0.05)
            code, out = run_tests()
            if code == FAIL:
                failed = [ln.strip() for ln in out.splitlines() if "FAILED" in ln or "panicked" in ln]
                print(f"  RED   {tag}  (exit {code} == {FAIL})")
                for ln in failed[:6]:
                    print(f"        {ln[:110]}")
                caught += 1
            elif code == PASS:
                print(f"  GREEN {tag}  <-- MUTATION SURVIVED, the suite has a hole here")
                missed.append(tag)
            else:
                sys.exit(f"UNEXPECTED EXIT {code} for [{tag}] -- neither {PASS} nor {FAIL}\n"
                         f"{out[-2000:]}")
    finally:
        shutil.copy2(BACKUP, SRC)
        os.utime(SRC, None)

    restored = sha(SRC)
    print(f"\nrestored SHA-256 {restored[:16]}...  match={restored == original}")
    if restored != original:
        sys.exit("RESTORE FAILED -- the working tree is not what it was")

    code, out = run_tests()
    print(f"post-restore suite exit {code} (expect {PASS})")
    if code != PASS:
        # The restore is already proven byte-exact by the SHA-256 above, so a
        # red suite here is NOT a failed restore. In a working tree shared with
        # other agents, a red post-restore leg is usually somebody else's
        # in-flight edit landing mid-run: this control has seen `strehl-core`
        # stop compiling on `outlier::Discriminator::Shift` while softgate.rs
        # was untouched. Attributing that to the restore would be a harness
        # fault reported as a measurement, so the two are separated by their
        # exit codes and by whether the breakage names the file under test.
        ours = [ln.strip() for ln in out.splitlines()
                if "softgate" in ln and ("FAILED" in ln or "error" in ln)]
        if ours:
            for ln in ours[:6]:
                print(f"        {ln[:110]}")
            sys.exit("RESTORE LEFT THE SUITE RED IN softgate -- "
                     "the restore is byte-exact, so this is a real hole")
        for ln in [l.strip() for l in out.splitlines() if l.startswith("error")][:6]:
            print(f"        {ln[:110]}")
        print("\n  The breakage does not name softgate and the restore is byte-exact,")
        print("  so this is the SHARED TREE, not this control. The mutation results")
        print("  above stand. Re-verify in an isolated extraction:")
        print("    git archive HEAD | tar -x -C <dir>; copy softgate.rs over; cargo test")
        sys.exit(HARNESS)

    print(f"\n{caught}/{len(MUTATIONS)} mutations caught")
    if missed:
        sys.exit("SUITE HAS HOLES: " + "; ".join(missed))
    print("NEGATIVE CONTROL PASSED -- every planted defect turned the suite red, "
          "and the restore is byte-exact.")


if __name__ == "__main__":
    main()
