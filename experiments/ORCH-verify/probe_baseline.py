"""One-off probe: build the same scratch commission_header.py builds, run
v2954 against it, and print ONLY the RED/XDOC-fail lines plus a live-vs-scratch
comparison. Answers 'why is the unmutated baseline red', which no amount of
staring at a truncated tail will answer."""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commission_header as ch  # noqa: E402

scratch = ch.build_scratch()
print("scratch:", scratch)


def red_lines(root):
    p = subprocess.run([sys.executable, "-B", str(ch.V2954), str(root)],
                       capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    keep = [ln for ln in out.splitlines()
            if re.match(r"^(RED|XDOC-FAIL|FATAL)", ln) or "FAIL" in ln[:60]]
    return p.returncode, keep


rc_s, red_s = red_lines(scratch)
print("\n=== SCRATCH rc=%d ===" % rc_s)
for ln in red_s:
    print(" ", ln)

rc_l, red_l = red_lines(ch.ROOT)
print("\n=== LIVE rc=%d ===" % rc_l)
for ln in red_l:
    print(" ", ln)

# If a file the verifier reads differs between live and scratch, that is the
# cause. Compare every docs/ and experiments/ file present in BOTH.
diffs = []
for sub in ("docs", "experiments"):
    for p in (ch.ROOT / sub).rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".md", ".json"):
            continue
        q = scratch / sub / p.relative_to(ch.ROOT / sub)
        if not q.exists():
            diffs.append(("MISSING-IN-SCRATCH", str(p.relative_to(ch.ROOT))))
        elif p.read_bytes() != q.read_bytes():
            diffs.append(("CONTENT-DIFFERS", str(p.relative_to(ch.ROOT))))
print("\n=== file differences: %d ===" % len(diffs))
for kind, rel in diffs[:40]:
    print(" ", kind, rel)

shutil.rmtree(scratch, ignore_errors=True)
