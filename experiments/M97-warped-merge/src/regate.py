"""M97 — re-verify every pass/fail gate I reported, using subprocess.returncode.

ORCH fact 1490 / discipline 762: `$LASTEXITCODE` is NOT UPDATED after a
truncated PowerShell pipeline, so it retains the previous command's code. The
error runs in both directions and a plausible-looking code is not evidence the
read was live. Every gate below is therefore re-run through
subprocess.run().returncode, which has none of that behaviour.

Also scans my committed artefacts for the control characters ORCH fact 1488
describes (backticks eaten by a double-quoted here-string).
"""

import subprocess
import sys
import unicodedata
from pathlib import Path

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
CARGO = Path.home() / ".cargo" / "bin" / "cargo.exe"
CODE_COMMIT = "8be4b38"
DOC_COMMIT = "1913c58"

MINE = [
    "crates/strehl-core/src/outlier.rs",
    "crates/strehl-core/src/lib.rs",
    "crates/strehl-cli/examples/m97-outlier.rs",
    "docs/research/M97r-outlier-mask.md",
]

results = []


def run(label, args, cwd, env=None, expect=0):
    """Run a command and report its TRUE exit code."""
    import os

    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run(args, cwd=str(cwd), capture_output=True, env=e)
    code = p.returncode
    ok = code == expect
    results.append((label, ok, f"exit {code} (expected {expect})"))
    return p, code


def main():
    print("=" * 72)
    print("HARNESS NEGATIVE CONTROL — the gate must be able to read a failure")
    print("=" * 72)
    # If this reads 0, the harness is disconnected and nothing below means
    # anything. Proving the instrument can go red before trusting its greens.
    p = subprocess.run(
        [sys.executable, "-c", "import sys; sys.exit(3)"], capture_output=True
    )
    print(f"  deliberate exit 3 -> returncode {p.returncode}")
    assert p.returncode == 3, "HARNESS DEAD: cannot read a nonzero exit code"
    p = subprocess.run(
        [sys.executable, "-c", "import sys; sys.exit(0)"], capture_output=True
    )
    print(f"  deliberate exit 0 -> returncode {p.returncode}")
    assert p.returncode == 0, "HARNESS DEAD: cannot read a zero exit code"
    print("  harness LIVE in both directions\n")

    print("=" * 72)
    print("GATE 1 — ancestry of my two commits (reported: both ancestors)")
    print("=" * 72)
    for c in (CODE_COMMIT, DOC_COMMIT):
        _, code = run(
            f"merge-base --is-ancestor {c}",
            ["git", "merge-base", "--is-ancestor", c, "HEAD"],
            REPO,
        )
        print(f"  {c} ancestor of HEAD -> exit {code}")
    # Negative control: a commit that must NOT be an ancestor.
    p = subprocess.run(
        ["git", "merge-base", "--is-ancestor", "HEAD", CODE_COMMIT],
        cwd=str(REPO),
        capture_output=True,
    )
    print(f"  CONTROL: HEAD ancestor of {CODE_COMMIT} -> exit {p.returncode} (want nonzero)")
    results.append(("ancestry negative control", p.returncode != 0, f"exit {p.returncode}"))

    print()
    print("=" * 72)
    print("GATE 2 — control characters in my committed artefacts (fact 1488)")
    print("=" * 72)
    bad = 0
    for rel in MINE:
        blob = subprocess.run(
            ["git", "show", f"{DOC_COMMIT}:{rel}"],
            cwd=str(REPO),
            capture_output=True,
        )
        if blob.returncode != 0:
            print(f"  {rel}: NOT IN COMMIT")
            bad += 1
            continue
        text = blob.stdout.decode("utf-8")
        hits = [
            (i, ch)
            for i, ch in enumerate(text)
            if unicodedata.category(ch) == "Cc" and ch not in "\r\n\t"
        ]
        print(f"  {rel}: {len(hits)} control chars")
        if hits:
            bad += 1
            for i, ch in hits[:5]:
                line = text[:i].count("\n") + 1
                print(f"      line {line}: 0x{ord(ch):02X} near {text[i-20:i+20]!r}")
    results.append(("no control characters", bad == 0, f"{bad} file(s) with hits"))

    # Plant: prove the scanner can see one, on the same wiring.
    planted = "a `b" + "\x08" + "ee-3-cpl` row"
    hits = [c for c in planted if unicodedata.category(c) == "Cc" and c not in "\r\n\t"]
    print(f"  PLANT: synthetic 0x08 row -> scanner found {len(hits)} (want 1)")
    results.append(("control-char scanner plant", len(hits) == 1, f"{len(hits)} found"))

    print()
    print("=" * 72)
    print(f"GATE 3 — cargo check --workspace --all-targets AT {CODE_COMMIT}")
    print("   (reported EXIT=0 via $LASTEXITCODE after a Select-Object pipeline)")
    print("=" * 72)
    wt = Path(r"C:\dev\strehl-out\M97\wt2")
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(wt)],
        cwd=str(REPO),
        capture_output=True,
    )
    p, code = run(
        "worktree add",
        ["git", "worktree", "add", "--detach", str(wt), CODE_COMMIT],
        REPO,
    )
    if code != 0:
        print("  worktree add FAILED:", p.stderr.decode("utf-8", "replace")[-400:])
    else:
        print(f"  worktree at {CODE_COMMIT} created")
        p, code = run(
            "cargo check --workspace --all-targets",
            [str(CARGO), "check", "--workspace", "--all-targets"],
            wt,
            env={"CARGO_TARGET_DIR": r"C:\dev\strehl-target-m97-wt"},
        )
        tail = p.stderr.decode("utf-8", "replace").strip().splitlines()[-3:]
        for t in tail:
            print("   ", t)
        print(f"  TRUE returncode = {code}")
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=str(REPO),
            capture_output=True,
        )

    print()
    print("=" * 72)
    print("GATE 4 — strehl-core test suite (reported 318 passed / 0 failed)")
    print("=" * 72)
    p, code = run(
        "cargo test -p strehl-core",
        [str(CARGO), "test", "--release", "-p", "strehl-core"],
        REPO,
        env={"CARGO_TARGET_DIR": r"C:\dev\strehl-target-m97"},
    )
    out = p.stdout.decode("utf-8", "replace")
    for line in out.splitlines():
        if "test result" in line:
            print("   ", line.strip())
    print(f"  TRUE returncode = {code}")

    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    worst = 0
    for label, ok, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {detail}")
        if not ok:
            worst = 1
    print()
    print("VERDICT:", "ALL REPORTED GATES HOLD" if worst == 0 else "A REPORTED GATE MOVED")
    return worst


if __name__ == "__main__":
    sys.exit(main())
