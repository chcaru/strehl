"""Append section 24 to the M95 report, byte-safe, refusing to duplicate."""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
REPORT = os.path.join(ROOT, "docs", "research", "M95-kernel.md")
DRAFT = os.path.join(ROOT, "experiments", "M95-resample", "out", "s24.md")
MARKER = "## 24. The cache-contamination control"

with io.open(REPORT, "r", encoding="utf-8", newline="") as fh:
    body = fh.read()
with io.open(DRAFT, "r", encoding="utf-8", newline="") as fh:
    draft = fh.read()

if MARKER in body:
    print("ALREADY APPENDED -- refusing to duplicate")
    sys.exit(2)

nl = "\r\n" if body.count("\r\n") > body.count("\n") - body.count("\r\n") else "\n"
draft = draft.replace("\r\n", "\n").replace("\n", nl)
if not body.endswith(nl):
    body += nl
out = body + draft
with io.open(REPORT, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print(f"line ending: {'CRLF' if nl == chr(13)+chr(10) else 'LF'}")
print(f"before {len(body)} bytes, draft {len(draft)}, after {len(out)}")
print(f"section 24 present: {MARKER in out}")
print(f"total lines: {out.count(nl) + 1}")
