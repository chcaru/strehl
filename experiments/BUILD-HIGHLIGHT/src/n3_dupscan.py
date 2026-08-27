"""n3_dupscan.py -- find measurements printed more than once under different-looking headings.

ORCH's closing brief: "three identical rows are the most persuasive-looking thing on a page
and the least informative". I found that failure mode in section 12 by accident. This scans
for it mechanically, because auditing my own report by eye is the same error one level up.

A row's SIGNATURE is the tuple of numeric tokens in its cells after the label. Two rows with
the same signature and different labels are ONE measurement wearing two names. Across tables,
the same signature under a different heading is the same hazard at document scale.

A hit is not automatically a defect -- a reference row may be repeated on purpose. The scan
locates candidates; a human reads each one. It is a sieve, not a verdict.
"""
import re, sys, collections

NUM = re.compile(r'[-+]?\d*\.\d+|[-+]?\d+')

def rows_of(text):
    """Yield (table_id, heading, lineno, label, signature) for every numeric row."""
    heading, tid, out = "(top)", 0, []
    lines = text.split("\n")
    intable = False
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith("#"):
            heading, intable = s.lstrip("# ").strip(), False
            continue
        if s.startswith("|"):
            if not intable:
                tid += 1; intable = True
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells if c):   # separator row
                continue
            label = cells[0] if cells else ""
            sig = tuple(NUM.findall(" ".join(cells[1:])))
            if sig:
                out.append((tid, heading, i, label, sig))
        else:
            intable = False
    return out

def scan(text):
    rs = rows_of(text)
    within, across = [], []
    by_table = collections.defaultdict(list)
    for r in rs:
        by_table[r[0]].append(r)
    for tid, group in by_table.items():
        seen = {}
        for (_, h, i, lab, sig) in group:
            if sig in seen and seen[sig][1].strip() != lab.strip():
                within.append((h, seen[sig][0], seen[sig][1], i, lab, sig))
            else:
                seen.setdefault(sig, (i, lab))
    bysig = collections.defaultdict(list)
    for (tid, h, i, lab, sig) in rs:
        if len(sig) >= 3:
            bysig[sig].append((tid, h, i, lab))
    for sig, hits in bysig.items():
        tids = {t for (t, _, _, _) in hits}
        heads = {h for (_, h, _, _) in hits}
        if len(tids) > 1 and len(heads) > 1:
            across.append((sig, hits))
    return rs, within, across


def fence_rows(text):
    """Same hazard, second habitat: pasted program output inside ``` fences.

    Scanning only markdown tables was a declared blind spot, and a declared blind spot is
    the same kind of promise as `support_r_max` -- worth nothing unless something checks it.
    """
    heading, fid, inf, out = "(top)", 0, False, []
    for i, ln in enumerate(text.split("\n"), 1):
        s = ln.strip()
        if s.startswith("```"):
            inf = not inf
            if inf: fid += 1
            continue
        if s.startswith("#") and not inf:
            heading = s.lstrip("# ").strip(); continue
        if inf:
            sig = tuple(NUM.findall(s))
            if len(sig) >= 3:
                out.append((fid, heading, i, s[:44], sig))
    return out

def scan_fences(text):
    rs, hits = fence_rows(text), []
    bysig = collections.defaultdict(list)
    for (fid, h, i, lab, sig) in rs:
        bysig[sig].append((fid, h, i, lab))
    for sig, g in bysig.items():
        if len(g) > 1:
            hits.append((sig, g))
    return rs, hits
def selftest():
    clean = "## H\n\n| a | 1.0 | 2.0 |\n|---|---|---|\n| x | 0.10 | 0.20 |\n| y | 0.11 | 0.21 |\n| z | 0.12 | 0.22 |\n"
    dup   = "## H\n\n| a | 1.0 | 2.0 |\n|---|---|---|\n| luma | 0.10 | 0.20 |\n| rb | 0.10 | 0.20 |\n| max | 0.10 | 0.20 |\n"
    near  = "## H\n\n| a | 1.0 |\n|---|---|\n| x | 0.100 |\n| y | 0.101 |\n"
    cross = "## A\n\n| a | b | c |\n|---|---|---|\n| r | 1.5 | 2.5 | 3.5 |\n\n## B\n\n| a | b | c |\n|---|---|---|\n| q | 1.5 | 2.5 | 3.5 |\n"
    _, w, _ = scan(clean);  assert not w, "clean table must not flag"
    print("  distinct rows            -> 0 flags (correct)")
    _, w, _ = scan(dup)
    assert len(w) == 2, f"planted 3 identical rows, expected 2 flags, got {len(w)}"
    print("  3 identical rows planted -> %d flags (DETECTED)" % len(w))
    _, w, _ = scan(near); assert not w, "0.100 vs 0.101 must NOT flag"
    print("  0.100 vs 0.101           -> 0 flags (does not over-trigger)")
    _, _, a = scan(cross); assert len(a) == 1, "cross-table repeat must flag"
    print("  same row under 2 headings-> 1 flag  (DETECTED)")
    fdup = "## H\n\n```\nalpha 1.5 2.5 3.5\nbeta  1.5 2.5 3.5\n```\n"
    fok  = "## H\n\n```\nalpha 1.5 2.5 3.5\nbeta  1.6 2.6 3.6\n```\n"
    _, fh = scan_fences(fdup); assert len(fh) == 1, "planted fence repeat must flag"
    print("  repeat inside a ``` fence -> 1 flag  (DETECTED)")
    _, fh = scan_fences(fok);  assert not fh, "distinct fence lines must not flag"
    print("  distinct fence lines      -> 0 flags (correct)")
    print("n3 selftest: PASS -- detects planted repeats in tables AND fences, silent on distinct data.")

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest(); sys.exit(0)
    text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    rs, within, across = scan(text)
    print("scanned %d numeric rows\n" % len(rs))
    print("== WITHIN-TABLE repeats (same numbers, different label) ==")
    if not within: print("  none")
    for (h, i1, l1, i2, l2, sig) in within:
        print("  [%s]\n    line %d '%s'  ==  line %d '%s'\n    %s" % (h, i1, l1, i2, l2, " ".join(sig)))
    print("\n== CROSS-TABLE repeats (same numbers, different heading) ==")
    if not across: print("  none")
    for (sig, hits) in across:
        print("  %s" % " ".join(sig))
        for (t, h, i, lab) in hits: print("     line %-5d [%s] '%s'" % (i, h[:52], lab))

    frs, fh = scan_fences(text)
    print("\n== REPEATS INSIDE ``` FENCES (%d numeric lines scanned) ==" % len(frs))
    if not fh:
        print("  none")
    for (sig, g) in fh:
        print("  %s" % " ".join(sig))
        for (t, h, i, lab) in g:
            print("     line %-5d [%s] '%s'" % (i, h[:52], lab))

# ---------------------------------------------------------------------------
# MAGNITUDE FORM. ORCH: "A boolean pass carries no scale, so it cannot
# self-check." The exact-signature test above answers match / no-match, and in
# 14.3 I declared its blind spot: the same run reported at different roundings
# evades it completely. That blind spot is a property of the BOOLEAN, not of
# the question. Asked as "how close are these two rows?" the same data returns
# a number, and an implausibly small number on rows that should differ is
# visible in a way that no boolean can be.
# ---------------------------------------------------------------------------
def closeness(a, b):
    """Median relative difference between two numeric row signatures.

    0.0 == identical. Returns None when the rows are not comparable, rather
    than a number that would silently mean "very different".
    """
    if len(a) != len(b) or not a:
        return None
    d = []
    for x, y in zip(a, b):
        try:
            x, y = float(x), float(y)
        except ValueError:
            return None
        s = max(abs(x), abs(y))
        d.append(0.0 if s == 0 else abs(x - y) / s)
    d.sort()
    return d[len(d) // 2]

def scan_near(text, thresh=0.02):
    """Row PAIRS that are suspiciously close without being identical."""
    rs, out = rows_of(text), []
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            (t1, h1, l1, lab1, s1), (t2, h2, l2, lab2, s2) = rs[i], rs[j]
            if s1 == s2:
                continue                     # exact: the boolean already has it
            c = closeness(s1, s2)
            if c is not None and c <= thresh and len(s1) >= 3:
                out.append((c, h1, l1, lab1, h2, l2, lab2))
    out.sort()
    return out
