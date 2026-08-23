"""Fold M44 (M41 second pass) into SYNTHESIS.md.

Facts 460-479 were reserved for M41 by the orchestrator and are still free, so
they fold unchanged. Disciplines and questions were deliberately proposed
WITHOUT numbers by M44 -- the correct behaviour under rule 28 -- and are
assigned here: disciplines 276-283, questions 117-122.

The fact rows are already four-column and pipe-escaped in the report, so they
are parsed verbatim; nothing is retyped.

This fold also annotates two existing facts that M44's measurements correct:

  417  M19's external-literature claim that FRC "cannot be fooled upward by
       noise amplification". Measured false on this sensor by fact 468: FRC
       resists INDEPENDENT noise amplification, not COMMON-MODE amplification,
       and ranks arm E (295x noise, 99% out-of-range) at 0.970.
  49   the coffee-bubbles constant-focus claim, refuted by fact 470.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
DOC = "M41-r3-kill-measured.md"
RPT = pathlib.Path("docs/research") / DOC

DISCIPLINES_BASE = 276
QUESTIONS_BASE = 117

MARK = {
    417: " **CORRECTED IN-HOUSE by M44 (fact 468), 12 hours after this row was folded.** The literature claim is true of *independent* noise amplification and false of *common-mode* amplification, which is the case that matters here. Measured: split-half FRC ranks the plain mean **above** the shipped merge, and ranks arm E — **295x** the noise and 99% of pixels out of range — at **0.970**. It also crosses 1/7 at Nyquist on a **flat ROI**, which has no resolution in it by construction. Split-half FRC on two halves of one capture is **not** an admissible resolution metric on this sensor; see facts 475-478 for the mechanism and the failed 32-setting repair.",
    49: " **The `coffee-bubbles` clause is REFUTED by M44 (fact 470).** It is not at constant focus in the shipped operator's units: its regularised focus response spans **235.02 gate sigma** across 19 frames with a through-focus FWHM of 8 frames. It cannot serve as a degenerate control, which is what M19's kill-experiment design (§8, \"degenerate control, free\") assumed. Impose `s = 0` instead — discipline 278.",
}


def parse_facts():
    text = RPT.read_text(encoding="utf-8")
    m = re.search(r"^## Proposed SYNTHESIS entries(.*)$", text, re.M | re.S)
    if not m:
        raise SystemExit("'## Proposed SYNTHESIS entries' not found")
    out = {}
    for line in m.group(1).split("\n"):
        if not line.startswith("| "):
            continue
        c = [x.strip() for x in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(c) == 4 and c[0].isdigit():
            out[int(c[0])] = c[1:]
    if sorted(out) != list(range(460, 480)):
        raise SystemExit(f"expected 460-479, parsed {sorted(out)}")
    return out


def parse_list(pattern, flatten):
    text = RPT.read_text(encoding="utf-8")
    body = re.search(pattern, text, re.M | re.S).group(1)
    items = [x.strip() for x in re.split(flatten, body, flags=re.M)[1:]]
    return [" ".join(i.split()).rstrip("-").strip() for i in items]


def main():
    facts = parse_facts()
    disciplines = parse_list(r"^## 7\..*?$(.*?)^## 8\.", r"^- \*\*")
    questions = parse_list(r"^## 8\..*?$(.*?)^## ", r"^- ")
    if len(disciplines) != 8 or len(questions) != 6:
        raise SystemExit(f"expected 8 disciplines / 6 questions, got {len(disciplines)} / {len(questions)}")

    text = SRC.read_text(encoding="utf-8")

    present = {int(m) for m in re.findall(r"^\| (\d+) \|", text, re.M)}
    if present & set(facts):
        raise SystemExit(f"fact collision: {sorted(present & set(facts))}")
    # Rule 28: content check.
    for n, (claim, _, _) in facts.items():
        if claim[:60] in text:
            raise SystemExit(f"fact {n} already folded (content match)")

    dnums = list(range(DISCIPLINES_BASE, DISCIPLINES_BASE + len(disciplines)))
    qnums = list(range(QUESTIONS_BASE, QUESTIONS_BASE + len(questions)))

    d5 = re.search(r"^## 5\.", text, re.M)
    d5e = re.search(r"^## ", text[d5.end():], re.M)
    dseg = text[d5.start(): d5.end() + d5e.start()]
    if {int(x) for x in re.findall(r"^(\d+)\. \*\*", dseg, re.M)} & set(dnums):
        raise SystemExit("discipline collision")
    q10 = re.search(r"^## 10\.", text, re.M)
    if {int(x) for x in re.findall(r"^(\d+)\. \*\*", text[q10.start():], re.M)} & set(qnums):
        raise SystemExit("question collision")

    rows = []
    for n in sorted(facts):
        claim, cons, srcref = facts[n]
        row = f"| {n} | {claim} | {cons} | {srcref} |"
        if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
            raise SystemExit(f"row {n}: unescaped pipe")
        rows.append(row)

    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("| 459 |")]
    if len(idx) != 1:
        raise SystemExit("anchor 459 not unique")
    lines[idx[0] + 1: idx[0] + 1] = rows
    text = "\n".join(lines)

    # Annotate the two facts M44 corrects.
    lines = text.split("\n")
    hits = 0
    for i, line in enumerate(lines):
        m = re.match(r"^\| (\d+) \| ", line)
        if not m or int(m.group(1)) not in MARK:
            continue
        n = int(m.group(1))
        c = re.split(r"(?<!\\)\|", line)
        if len(c) != 6:
            raise SystemExit(f"row {n}: bad shape")
        if "by M44" in c[3]:
            raise SystemExit(f"row {n} already marked")
        c[3] = c[3].rstrip() + MARK[n] + " "
        lines[i] = "|".join(c)
        hits += 1
    if hits != len(MARK):
        raise SystemExit(f"marked {hits}, expected {len(MARK)}")
    text = "\n".join(lines)

    d5 = re.search(r"^## 5\.", text, re.M)
    d5e = re.search(r"^## ", text[d5.end():], re.M)
    lo, hi = d5.start(), d5.end() + d5e.start()
    seg = text[lo:hi]
    m = re.search(r"^275\. \*\*", seg, re.M)
    if not m:
        raise SystemExit("discipline 275 not found")
    nxt = re.search(r"^\d+\. \*\*", seg[m.end():], re.M)
    ins = lo + (m.end() + nxt.start() if nxt else len(seg.rstrip("\n")) + 1)
    body = "".join(
        f"{n}. {d} (M44; see [`{DOC}`]({DOC}) §7.)\n\n"
        for n, d in zip(dnums, disciplines)
    )
    text = text[:ins] + body + text[ins:]

    text = text.rstrip("\n") + "\n\n" + "".join(
        f"{n}. **{q[0].upper()}{q[1:]} (M44 §8.)\n\n" if q.startswith("**") else f"{n}. **{q}** (M44 §8.)\n\n"
        for n, q in zip(qnums, questions)
    )

    SRC.write_text(text, encoding="utf-8")
    print(f"facts {sorted(facts)}")
    print(f"disciplines {dnums}")
    print(f"questions {qnums}")
    print(f"annotated {sorted(MARK)}")


if __name__ == "__main__":
    main()
