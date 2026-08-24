"""M97: materialise a pre-patch tree from git, as a plant for patchcheck.py.

`patchcheck.py <tree>` checks the NEW blocks against <tree>. Pointing it at the
repo answers "is M100's patch already applied at HEAD?" -- but a check that
reports "found" on everything is worthless unless it can also report "absent".

So build the tree as it stood immediately BEFORE 925d03d (the commit that
applied the patch) and run the same check against it. The NEW blocks must be
absent there. If they are found in both, the probe is not discriminating and
its verdict on HEAD means nothing.

Reads git blobs as BYTES via subprocess -- on Windows `git show x:y > f`
re-encodes the stream and corrupts the comparison.
"""
import os
import subprocess
import sys

REPO = r"C:\dev\blog\death-of-software\projects\strehl"
OUT = r"C:\dev\strehl-out\M97\prepatch-tree"
REV = "925d03d^"
FILES = [
    "crates/strehl-cli/src/main.rs",
    "crates/strehl-cli/src/merge_cmd.rs",
]


def main():
    for rel in FILES:
        r = subprocess.run(["git", "show", f"{REV}:{rel}"],
                           cwd=REPO, capture_output=True)
        if r.returncode != 0:
            print(f"FAIL: git show {REV}:{rel} -> {r.stderr.decode(errors='replace')}")
            return 1
        dst = os.path.join(OUT, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh:
            fh.write(r.stdout)
        print(f"wrote {dst}  ({len(r.stdout)} bytes from {REV})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
