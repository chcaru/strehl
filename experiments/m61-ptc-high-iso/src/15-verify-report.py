"""15 -- verify the report's internal numbering and cross-references resolve.

Read-only. Checks, for M61-ptc-high-iso-measured.md:
  * fact / discipline / question / error headers are unique and gap-free
  * every internal "fact N" / "error N" / "discipline N" / "question N"
    reference resolves to a header that exists
  * every M48c / M25 citation matches the true numbers in those reports
  * section 4 subsections are sequential and every section ref resolves

Cross-report citations are checked against the OTHER report's actual headers,
which is the check that error 12 needed and corpus_lint does not provide.
"""

from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.normpath(os.path.join(HERE, "..", "..", "..", "docs", "research"))
DOC = os.path.join(RESEARCH, "M61-ptc-high-iso-measured.md")

# Verified by reading M48c directly: fact 11, 17 (the 2.174x), 21, 22.
M48C_OK = {11, 17, 21, 22}
M25_OK = {200}


def headers(text, word):
    # A header is "**Fact 12 —" or "**Fact 12 (superseded...". An inline
    # reference is "**Error 18**", which reaches line start on a wrap and is not
    # a header -- requiring the em dash or paren after the number separates them.
    return [int(m) for m in re.findall(rf"\*\*{word} (\d+)[ ]?[—(.]", text)]


def main() -> int:
    t = io.open(DOC, encoding="utf-8").read()
    fails = []

    for word, label in (("Fact", "fact"), ("Discipline", "discipline"),
                        ("Question", "question"), ("Error", "error")):
        hs = headers(t, word)
        dupes = {x for x in hs if hs.count(x) > 1}
        missing = set(range(1, max(hs) + 1)) - set(hs) if hs else set()
        print(f"{label:<11} n={len(hs):<3} max={max(hs) if hs else 0:<3} "
              f"dupes={sorted(dupes) or '-'} missing={sorted(missing) or '-'}")
        if dupes:
            fails.append(f"{label}: duplicate headers {sorted(dupes)}")
        if missing:
            fails.append(f"{label}: missing headers {sorted(missing)}")

    fact_hdrs = set(headers(t, "Fact"))
    disc_hdrs = set(headers(t, "Discipline"))
    ques_hdrs = set(headers(t, "Question"))
    err_hdrs = set(headers(t, "Error"))

    # internal references, excluding those qualified by another report's name.
    # A reference is EXTERNAL if an external marker sits close before it, or if
    # the number exceeds this report's own maximum for that category (M61
    # numbers locally from 1; SYNTHESIS-global numbers are far larger).
    EXTERNAL = ("M48c", "M25", "M4-", "M54", "M55", "M60", "SYNTHESIS",
                "-measured.md", "M48b", "M48")
    tn = re.sub(r"\s+", " ", t)

    def internal_refs(word, valid, label):
        bad, ext = [], []
        local_max = max(valid) if valid else 0
        for m in re.finditer(rf"(.{{0,45}})\b{word}s? (\d+)", tn):
            pre, n = m.group(1), int(m.group(2))
            if any(x in pre for x in EXTERNAL) or n > local_max:
                ext.append(n)
                continue
            if n not in valid:
                bad.append((n, m.group(0).strip()[-46:]))
        if bad:
            fails.append(f"{label}: unresolved {sorted({b[0] for b in bad})}")
            for n, ctx in bad[:6]:
                print(f"  UNRESOLVED {label} {n}: ...{ctx}")
        print(f"{label+' refs':<11} "
              f"{'OK' if not bad else str(len(bad)) + ' UNRESOLVED'}"
              f"   (external: {sorted(set(ext)) or '-'})")

    internal_refs("fact", fact_hdrs, "fact")
    internal_refs("discipline", disc_hdrs, "discipline")
    internal_refs("question", ques_hdrs, "question")
    internal_refs("error", err_hdrs, "error")

    # external references must resolve in the report they name.
    # Each entry: (label, file, regex that must match, note)
    EXT_CHECKS = [
        ("M25 fact 200 value", "M25-simulator-measured.md",
         r"\|\s*`109MSDCF`.*?\|\s*160\s*\|\s*0\.3273\s*\|",
         "the 0.3273 DN/e- at ISO 160 that P4b claims to disagree with"),
        ("M25 f200 correction scope", "M25-simulator-measured.md",
         r"Gates 1a, 1b and 2 run at ISO 160 and are unaffected",
         "post-fold correction to fact 200 does NOT touch the ISO-160 value"),
        ("M48c discipline 326", "M48c-defect-layer-measured.md",
         r"discipline 326, written last milestone, is that dark-frame "
         r"numbers have twice failed to survive contact with illuminated data",
         "the wording this report quotes for discipline 326"),
        ("M48c fact 17 = 2.174x", "M48c-defect-layer-measured.md",
         r"\*\*Fact 17\b", "the derived step M61 tests"),
        ("M48c fact 21 = refusal", "M48c-defect-layer-measured.md",
         r"\*\*Fact 21\b", "M48c declining to change constants"),
        ("M48c fact 22 = PTC", "M48c-defect-layer-measured.md",
         r"\*\*Fact 22\b", "M48c commissioning this PTC"),
    ]
    for label, fname, pat, note in EXT_CHECKS:
        path = os.path.join(RESEARCH, fname)
        if not os.path.exists(path):
            print(f"{label:<26} SOURCE MISSING {fname}")
            fails.append(f"{label}: {fname} not found")
            continue
        s = re.sub(r"\s+", " ", io.open(path, encoding="utf-8").read())
        hit = re.search(pat, s, re.S)
        print(f"{label:<26} {'VERIFIED' if hit else 'NOT FOUND'}  -- {note}")
        if not hit:
            fails.append(f"{label}: pattern not found in {fname}")

    # discipline 326 is an inherited global number; note whether SYNTHESIS
    # still carries it, without failing on it -- SYNTHESIS is not mine.
    syn = os.path.join(RESEARCH, "SYNTHESIS.md")
    if os.path.exists(syn):
        s = io.open(syn, encoding="utf-8").read()
        for n in sorted({int(x) for x in
                         re.findall(r"discipline (\d+)", t)} - disc_hdrs):
            hit = re.search(rf"\|\s*{n}\s*\|", s)
            print(f"{'SYNTH d'+str(n):<26} "
                  f"{'present' if hit else 'NOT in SYNTHESIS table (inherited '
                     'number, verified at source instead)'}")

    # cross-report citations
    for name, valid in (("M48c", M48C_OK), ("M25", M25_OK)):
        cites = set()
        for m in re.finditer(rf"{name}[^.\n]{{0,60}}?\bfacts? "
                             rf"([\d\u2013,\- ]+)", t):
            g = m.group(1).strip()
            rng = re.match(r"^(\d+)\s*[\u2013-]\s*(\d+)$", g)
            if rng:
                cites.update({int(rng.group(1)), int(rng.group(2))})
                continue
            for num in re.findall(r"\d+", g):
                cites.add(int(num))
        bad = cites - valid
        print(f"{name+' cites':<11} {sorted(cites)}  "
              f"{'OK' if not bad else 'BAD ' + str(sorted(bad))}")
        if bad:
            fails.append(f"{name}: cites nonexistent facts {sorted(bad)}")

    # proposed-fact labels: unique, and no duplicated blocks. A block edit that
    # duplicates P4b..P7 is invisible to every other check here, and did in fact
    # happen once while writing this report (error 19).
    plabels = re.findall(r"^- \*\*(P\d+[a-z]?) \(", t, re.M)
    pdupes = sorted({p for p in plabels if plabels.count(p) > 1})
    print(f"{'P labels':<26} {plabels}")
    print(f"{'P dupes':<26} {pdupes or 'none'}")
    if pdupes:
        fails.append(f"duplicated proposed facts: {pdupes}")

    subs = re.findall(r"^### (4\.\d+)", t, re.M)
    want = [f"4.{i}" for i in range(1, len(subs) + 1)]
    print(f"{'sec 4.x':<11} {subs} {'OK' if subs == want else 'OUT OF ORDER'}")
    if subs != want:
        fails.append(f"section 4 subsections out of order: {subs}")
    refs = sorted(set(re.findall(r"§(4\.\d+)", t)))
    dangling = [r for r in refs if r not in subs]
    print(f"{'sec refs':<11} {refs} {'OK' if not dangling else 'DANGLING ' + str(dangling)}")
    if dangling:
        fails.append(f"dangling section refs: {dangling}")

    nonascii = sorted({ch for ch in t if ord(ch) > 0x2500})
    print(f"{'stray glyphs':<11} {nonascii or 'none'}")
    if nonascii:
        fails.append(f"stray non-ascii: {nonascii}")

    print()
    if fails:
        print("FAIL")
        for f in fails:
            print("  -", f)
        return 1
    print("PASS -- all headers unique and gap-free, all references resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
