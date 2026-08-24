"""Scan the corpus for C0 control characters and DEL, which no linter currently checks."""
import io
import os
import re

BAD = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
EXT = (".md", ".py", ".rs", ".toml")

hits = {}
scanned = 0
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in (".git", "target", "node_modules")]
    for fn in files:
        if not fn.endswith(EXT):
            continue
        p = os.path.join(root, fn).replace("\\", "/")
        with io.open(p, "rb") as fh:
            data = fh.read()
        scanned += 1
        for m in BAD.finditer(data):
            line = data[: m.start()].count(b"\n") + 1
            hits.setdefault(p, []).append((line, m.group()[0]))

total = sum(len(v) for v in hits.values())
print("scanned %d files; %d file(s) contain C0/DEL; %d occurrence(s)" % (scanned, len(hits), total))
for p in sorted(hits):
    v = hits[p]
    codes = ",".join(sorted(set("0x%02X" % b for _, b in v)))
    lines = ",".join(str(l) for l, _ in v[:10])
    print("  %-62s %2d  lines %s  codes %s" % (p, len(v), lines, codes))
