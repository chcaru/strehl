"""Fold M19 (workstream G, the EDOF/microscopy survey) into SYNTHESIS.md.

M19 proposed facts 120-139, but M20-V already occupies 122-139 -- the collision
class that has cost this project twice. Shifting to 400-419, a block above every
allocated number, so no future fold has to reason about a partial overlap.

Cross-references are audited rather than blind-substituted: a reference to
"fact 150" inside an M19 row points at an EXISTING corpus fact and must NOT move.
Only references to M19's own 120-139 shift.
"""
import re, pathlib

SHIFT = 280
LO, HI = 120, 139
SRC = pathlib.Path("docs/research/G-edof-deconvolution.md")
DST = pathlib.Path("docs/research/SYNTHESIS.md")

src = SRC.read_text(encoding="utf-8").split("\n")
i = next(i for i, l in enumerate(src) if l.startswith("## 9."))
j = next(j for j, l in enumerate(src) if l.startswith("## 10."))

rows, seen = [], []
for l in src[i:j]:
    m = re.match(r"\| (\d+) \| (.*?)\s*\|\s*$", l)
    if not m:
        continue
    n = int(m.group(1))
    if not (LO <= n <= HI):
        continue
    body = m.group(2)
    for ref in re.findall(r"[Ff]act (\d+)", body):
        r = int(ref)
        seen.append((n, r, LO <= r <= HI))
    rows.append((n + SHIFT, body))

assert len(rows) == 20, len(rows)

print("cross-reference audit (row -> referenced fact, in-block?):")
for n, r, inblock in seen:
    print(f"  {n:>3} -> {r:<4} {'SHIFTS' if inblock else 'external, left alone'}")
assert not any(x[2] for x in seen), "an in-block reference needs shifting; handle it explicitly"

note = " *(M19 proposed this as fact {orig}; shifted +{s} because M20-V already held 122–139.)*"
block = [f"| {n} | {b} |" for n, b in rows]
block[0] = block[0][:-1] + note.format(orig=rows[0][0] - SHIFT, s=SHIFT) + " |"

cur, last = "", None
dst = DST.read_text(encoding="utf-8").split("\n")
for k, l in enumerate(dst):
    if l.startswith("## "):
        cur = l
    if cur.startswith("## 4.") and re.match(r"\| \d+ \|", l):
        last = k
assert last is not None
dst = dst[: last + 1] + block + dst[last + 1 :]
DST.write_text("\n".join(dst), encoding="utf-8")
print(f"\nadded facts {rows[0][0]}-{rows[-1][0]} (M19's {LO}-{HI}, shifted +{SHIFT})")
