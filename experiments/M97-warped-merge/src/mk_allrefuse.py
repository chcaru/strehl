"""Generate an all-refused sidecar from a clean one, for M97 bar D4.

Every per-frame placement line becomes `<index> refused <reason>`. Header
lines are copied verbatim so the stack identity still validates -- the point
of D4 is that the merge rejects a fully-refused solve, not that it rejects a
malformed file.
"""

import sys

src, dst = sys.argv[1], sys.argv[2]
out, n = [], 0
for line in open(src, encoding="utf-8").read().splitlines():
    head = line.split(" ", 1)[0]
    if head.isdigit():
        out.append(f"{head} refused all-refused-M97")
        n += 1
    else:
        out.append(line)

if n == 0:
    raise SystemExit("MUTATION TARGET NOT FOUND: no placement lines in " + src)

open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print(f"refused {n} frames -> {dst}")
