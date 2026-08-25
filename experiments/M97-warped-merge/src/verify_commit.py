"""Check a COMMIT, not the working tree.

Fact 1475's failure mode is that a path-scoped commit can take a reference
without its definition: the working tree still builds, because the missing
artefact is sitting untracked beside it, and `HEAD` is broken for everyone
else. The only instrument that can see that is a build of the commit in a
tree that has nothing else in it.

Gating is on `subprocess.run().returncode`, never on `$LASTEXITCODE` after a
pipeline: fact 1490 measured that a `Select-Object -First N` truncation leaves
`$LASTEXITCODE` NOT UPDATED, so it inherits the previous command's code and can
read as a false pass OR a false failure.

The harness proves itself live before it reports: it first runs a command that
must fail and a command that must succeed, and refuses to continue unless it
reads both correctly. A checker that has never been seen to say RED is not
evidence of GREEN.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
CARGO = Path.home() / ".cargo" / "bin" / "cargo.exe"
WORKTREE = Path(r"C:\dev\strehl-wt-m97")
TARGET = r"C:\dev\strehl-target-m97-wt"


def run(args, cwd, env=None):
    p = subprocess.run(args, cwd=str(cwd), capture_output=True, env=env)
    out = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
    return p.returncode, out


def prove_the_gate_is_live():
    """Refuse to trust a returncode we have not seen move in both directions."""
    bad, _ = run([sys.executable, "-c", "import sys; sys.exit(3)"], REPO)
    good, _ = run([sys.executable, "-c", "import sys; sys.exit(0)"], REPO)
    if bad != 3 or good != 0:
        raise SystemExit(f"GATE IS NOT LIVE: expected 3 and 0, read {bad} and {good}")
    print(f"gate proved live: deliberate failure read {bad}, deliberate success read {good}")


def main():
    commit = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    prove_the_gate_is_live()

    rc, out = run(["git", "rev-parse", commit], REPO)
    if rc != 0:
        raise SystemExit(f"cannot resolve {commit}: {out}")
    sha = out.strip()
    print(f"checking commit {sha}")

    if WORKTREE.exists():
        run(["git", "worktree", "remove", "--force", str(WORKTREE)], REPO)
        shutil.rmtree(WORKTREE, ignore_errors=True)

    rc, out = run(["git", "worktree", "add", "--detach", str(WORKTREE), sha], REPO)
    if rc != 0:
        raise SystemExit(f"worktree add failed ({rc}):\n{out}")

    try:
        env = dict(os.environ)
        env["PATH"] = str(CARGO.parent) + os.pathsep + env["PATH"]
        env["CARGO_TARGET_DIR"] = TARGET
        rc, out = run(
            [str(CARGO), "check", "--workspace", "--all-targets"], WORKTREE, env
        )
        print(f"\ncargo check --workspace --all-targets  ->  exit {rc}")
        for line in out.splitlines():
            if line.startswith(("error", "warning:")) or "-->" in line:
                print("   " + line.strip())
        if rc != 0:
            raise SystemExit("THE COMMIT DOES NOT BUILD")
        print("\nTHE COMMIT BUILDS CLEAN")
    finally:
        run(["git", "worktree", "remove", "--force", str(WORKTREE)], REPO)
        shutil.rmtree(WORKTREE, ignore_errors=True)
        print("worktree removed")


if __name__ == "__main__":
    main()
