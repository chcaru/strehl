"""Diagnose where rewrap_s34's transform changes text rather than line breaks."""
import importlib.util
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
DOC = HERE.parents[2] / "docs" / "research" / "M87-occlusion.md"

spec = importlib.util.spec_from_file_location("rw", HERE / "rewrap_s34.py")
rw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rw)

raw = DOC.read_bytes().decode("utf-8")
tail = raw[raw.index("## 34."):]
lines = tail.split("\r\n")
new = rw.rewrap(lines)
a, b = rw.collapse(tail), rw.collapse("\r\n".join(new))
print(f"before {len(a)} chars, after {len(b)} chars, delta {len(b) - len(a)}")

n = min(len(a), len(b))
i = 0
while i < n and a[i] == b[i]:
    i += 1
print(f"first divergence at char {i}")
print(f"  before: ...{a[max(0, i - 90):i + 90]!r}")
print(f"  after : ...{b[max(0, i - 90):i + 90]!r}")

wa = a.split(" ")
wb = b.split(" ")
sa, sb = set(wa), set(wb)
print(f"tokens only in before: {sorted(sa - sb)[:12]}")
print(f"tokens only in after : {sorted(sb - sa)[:12]}")
