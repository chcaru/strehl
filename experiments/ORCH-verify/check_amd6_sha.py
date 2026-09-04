"""Verify the Amendment 6 SHA claim against the actual git object.

docs/proposals/2026-08-sota-path.md:2668-2670 asserts that at commit
`19f6f54a` the regenerated commission.json hashed to
418D2D852DC15B072CB65DD6BAAECAA9B4CBF82843BA825F00B0440ACC733C43.

That figure reached the owner's plan through an agent transcript and appears
in no committed file. It is checkable, so check it.

Bytes are read via subprocess stdout, never via shell redirection: on
Windows `git show ... > file` re-encodes the stream and silently corrupts
the hash.
"""
import hashlib
import subprocess

REV = "19f6f54a"
CLAIMED = "418D2D852DC15B072CB65DD6BAAECAA9B4CBF82843BA825F00B0440ACC733C43"
CANDIDATES = [
    "experiments/M164-m2-repair/commission.json",
    "experiments/M164-m2-repair/out/commission.json",
]

print(f"claimed : {CLAIMED}")
print(f"rev     : {REV}\n")

found = False
for path in CANDIDATES:
    r = subprocess.run(["git", "cat-file", "blob", f"{REV}:{path}"],
                       capture_output=True)
    if r.returncode != 0:
        print(f"  absent  {path}")
        continue
    found = True
    got = hashlib.sha256(r.stdout).hexdigest().upper()
    verdict = "MATCH" if got == CLAIMED else "MISMATCH"
    print(f"  {verdict:9s} {path}")
    print(f"            {got}  ({len(r.stdout)} bytes)")

if not found:
    print("\nVERDICT: the claimed artifact does not exist at that revision.")
