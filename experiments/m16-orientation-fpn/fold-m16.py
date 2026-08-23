"""Fold M16 — the orientation anomaly, and the reserved-block collision it flagged.

M16 was told to number from 90 and correctly refused to assume that was safe:
its own report says it "has not checked it for collisions". It was right to
flag. Facts 100, 101 and 102 are already taken, so M16's last three rows are
renumbered to 506-508. Its 90-99 land as issued, and disciplines 40-44 are free.

The rows are PARSED OUT OF M16'S OWN REPORT rather than retyped. Thirteen long
pipe-tables transcribed by hand is a defect waiting to happen, and the report
file is the artefact M16 verified; this script must not become a second,
divergent copy of it.

Facts 90-99 go after fact 88 (the 89-99 gap sits between 88 and 100).
Facts 506-508 go after 505. Disciplines 40-44 go after 34 (35-49 is the gap).
Question 20 is marked closed, which is fact 90's own headline.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
RPT = pathlib.Path("docs/research/M16-orientation-fpn-measured.md")
DOC = "M16-orientation-fpn-measured.md"

RENUMBER = {100: 506, 101: 507, 102: 508}

Q20_MARK = (
    "\n\n    **CLOSED by facts 90-92** (M16, after 6.0 h of measurement). The answer is\n"
    "    that nothing is broken: the asymmetry is a property of the corpus subjects.\n"
    "    Transposing the plant's textures 90° while holding every piece of machinery\n"
    "    fixed transposes the asymmetry exactly (median shift difference **0.0**\n"
    "    windows against **8.0** for the same geometry), and symmetrising the texture\n"
    "    nulls it outright. The mechanism is that a horizontal edge is localised by\n"
    "    `Gy` and a vertical edge by `Gx`, and this corpus carries **14-22x more\n"
    "    vertical gradient energy**. **The review's proposed fix — per-frame row and\n"
    "    column mean subtraction — changes the statistic by 0.0 windows** (fact 96),\n"
    "    and the row-FPN mechanism it assumed is refuted at source: this sensor's\n"
    "    fixed pattern is isotropic at all 11 measured ISOs (fact 93). "
    "**`WINDOW_RADIUS = 13` survives** (fact 97)."
)


def cells(row):
    return [c.strip() for c in re.split(r"(?<!\\)\|", row)[1:-1]]


def parse_report():
    text = RPT.read_text(encoding="utf-8")
    m = re.search(r"^## 13\.", text, re.M)
    if not m:
        raise SystemExit("section 13 not found in the M16 report")
    seg = text[m.start():]

    facts, disciplines = {}, {}
    for line in seg.split("\n"):
        if not line.startswith("| "):
            continue
        c = cells(line)
        if len(c) == 4 and c[0].isdigit():
            facts[int(c[0])] = c[1:]
        elif len(c) == 2 and c[0].isdigit():
            disciplines[int(c[0])] = c[1]

    if sorted(facts) != list(range(90, 103)):
        raise SystemExit(f"expected facts 90-102 in the report, got {sorted(facts)}")
    if sorted(disciplines) != list(range(40, 45)):
        raise SystemExit(f"expected disciplines 40-44, got {sorted(disciplines)}")
    return facts, disciplines


def build_row(n, claim, consequence, source):
    prov = f"M16 (MEASURED — {source}; see [`{DOC}`]({DOC})) — **NOT INDEPENDENTLY VERIFIED**"
    row = f"| {n} | {claim} | {consequence} | {prov} |"
    if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
        raise SystemExit(f"row {n}: unescaped pipe")
    return row


def insert_after(lines, prefix, new, label):
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    if len(idx) != 1:
        raise SystemExit(f"{label}: expected exactly one line starting {prefix!r}, got {len(idx)}")
    lines[idx[0] + 1 : idx[0] + 1] = new
    return lines


def main():
    facts, disciplines = parse_report()
    text = SRC.read_text(encoding="utf-8")

    present = {int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", text, re.M)}
    want = {RENUMBER.get(n, n) for n in facts}
    if present & want:
        raise SystemExit(f"fact collision after renumber: {sorted(present & want)}")

    dsec = re.search(r"^## 5\.", text, re.M)
    dend = re.search(r"^## ", text[dsec.end():], re.M)
    dseg = text[dsec.start():dsec.end() + dend.start()]
    dpresent = {int(x) for x in re.findall(r"^(\d+)\. \*\*", dseg, re.M)}
    if dpresent & set(disciplines):
        raise SystemExit(f"discipline collision: {sorted(dpresent & set(disciplines))}")

    lines = text.split("\n")

    late = [build_row(RENUMBER[n], *facts[n]) for n in sorted(RENUMBER)]
    lines = insert_after(lines, "| 505 |", late, "facts 506-508")

    early = [build_row(n, *facts[n]) for n in range(90, 100)]
    lines = insert_after(lines, "| 88 |", early, "facts 90-99")

    text = "\n".join(lines)

    # disciplines: numbered list items, insert the 40-44 block after item 34
    dsec = re.search(r"^## 5\.", text, re.M)
    dend = re.search(r"^## ", text[dsec.end():], re.M)
    lo, hi = dsec.start(), dsec.end() + dend.start()
    seg = text[lo:hi]
    m34 = re.search(r"^34\. \*\*", seg, re.M)
    if not m34:
        raise SystemExit("discipline 34 not found")
    nxt = re.search(r"^\d+\. \*\*", seg[m34.end():], re.M)
    ins = lo + (m34.end() + nxt.start() if nxt else len(seg.rstrip("\n")))
    block = "".join(f"{n}. {disciplines[n]}\n\n" for n in sorted(disciplines))
    text = text[:ins] + block + text[ins:]

    # question 20
    q = re.search(r"^## 10\.", text, re.M)
    qseg = text[q.start():]
    m20 = re.search(r"^20\. \*\*", qseg, re.M)
    if not m20:
        raise SystemExit("question 20 not found")
    nxt = re.search(r"^\d+\. \*\*", qseg[m20.end():], re.M)
    end = (m20.end() + nxt.start()) if nxt else len(qseg.rstrip("\n"))
    at = q.start() + len(qseg[:end].rstrip("\n"))
    text = text[:at] + Q20_MARK + text[at:]

    SRC.write_text(text, encoding="utf-8")
    print(
        f"inserted facts {sorted(range(90, 100))} + {sorted(RENUMBER.values())} "
        f"(renumbered from {sorted(RENUMBER)}), disciplines 40-44, marked question 20"
    )


if __name__ == "__main__":
    main()
