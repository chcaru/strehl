"""Is the rustfmt/clippy noise mine, or was it already at HEAD?

Reads the HEAD blob as BYTES via subprocess -- never `git show > file`, which
re-encodes the stream on Windows and has previously produced false diffs.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

RUSTFMT = Path.home() / ".cargo" / "bin" / "rustfmt.exe"
FILES = [
    "crates/strehl-core/src/align.rs",
    "crates/strehl-core/src/warpmap.rs",
    "crates/strehl-cli/src/align_cmd.rs",
]

tmp = Path(tempfile.mkdtemp(prefix="m95head-"))
for rel in FILES:
    blob = subprocess.run(["git", "show", f"HEAD:{rel}"],
                          capture_output=True, check=True).stdout
    p = tmp / Path(rel).name
    p.write_bytes(blob)
    r = subprocess.run([str(RUSTFMT), "--edition", "2024", "--check", str(p)],
                       capture_output=True, text=True)
    ndiff = r.stdout.count("Diff in ")
    print(f"{rel:<44} HEAD rustfmt diffs: {ndiff}")
    for line in r.stdout.splitlines():
        if line.startswith("Diff in "):
            print(f"    {line.split(chr(92))[-1]}")
sys.exit(0)
