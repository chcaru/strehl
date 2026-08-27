"""ORCH's blob-level CRLF check, run verbatim at several refs.

Reads the blob as BYTES via subprocess rather than through a shell redirect:
on Windows `git show HEAD:path > tmp` re-encodes the stream and reports a file
as fixed when it is not.
"""
import subprocess
import sys

PATH = "crates/strehl-cli/src/merge_cmd.rs"
REFS = [
    ("HEAD", "current tip"),
    ("658e5638", "my BUILD-GATE-2 commit"),
    ("78fed9a1", "my gate-floor commit -- the one that rewrote the file"),
    ("78fed9a1~1", "ITS PARENT -- the state ORCH measured"),
    ("e017c0bf", "the revision this lane started from"),
]

print(f"{'ref':<14}{'':<48}{'CRLF':>7}{'LF':>8}   verdict")
for ref, note in REFS:
    p = subprocess.run(["git", "show", f"{ref}:{PATH}"], capture_output=True)
    if p.returncode != 0:
        print(f"{ref:<14}{note:<48}  <missing: {p.stderr.decode(errors='replace').strip()[:40]}>")
        continue
    d = p.stdout
    crlf = d.count(b"\r\n")
    lf = d.count(b"\n") - crlf
    verdict = "CLEAN" if crlf == 0 else "MIXED"
    print(f"{ref:<14}{note:<48}{crlf:>7}{lf:>8}   {verdict}")

# The diff size, because ORCH's stated worry is that a fix shows as a
# full-file rewrite and buries the real change.
print()
d = subprocess.run(
    ["git", "show", "--numstat", "--format=", "78fed9a1", "--", PATH],
    capture_output=True, text=True).stdout.strip()
print(f"78fed9a1 diff for {PATH}:  {d or '<none>'}")
print("(added/deleted/path -- a full-file rewrite would read ~8680/8680)")
