"""Verify section 22 of BUILD-DEFECT.md against the artifacts it cites.

Two rules this obeys, both learned the hard way.

1. A VERIFIER MUST NOT CARRY THE EXPECTED VALUES. Every number below is
   re-derived from the JSON the measuring scripts wrote. A checker holding its
   own constants proves only that two files in the same commit agree.

2. A PRESENCE TEST IS SATISFIED BY ANY DUPLICATE OF THE VALUE. The first version
   of this script searched for each number near an anchor string and reported
   `37 declared = 37 matched`. Commissioning then planted eight defects and it
   MISSED three, every one for the same reason: the sealed sha and the sealed
   median each appear twice on their own table row (replay equals reference, so
   the value is legitimately repeated), and `26 rewritten` appears again in the
   evidence table. Corrupting one copy left another to satisfy the search.

   The repair is not a better anchor, it is a different instrument. Tables are
   parsed STRUCTURALLY -- located by header, indexed by row key, checked cell by
   cell -- so every measured number has exactly one site and a corruption of any
   single occurrence has nothing to hide behind. Counts that legitimately recur
   in prose are checked with an ALL-OCCURRENCES rule instead: every stated
   instance must equal the artifact, so one stale copy fails.

Outcomes partition: declared = matched + mismatched + unresolved. A claim whose
row or cell cannot be located is UNRESOLVED, which is a different fact from a
claim whose value disagrees, and neither can be read as a pass.

Run with --commission to plant known defects and require every one to be caught.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DOC = os.path.join(ROOT, "docs", "research", "BUILD-DEFECT.md")
OUTD = os.path.join(HERE, "..", "out")

log = []


def say(s=""):
    print(s)
    log.append(s)


def jload(name):
    p = os.path.join(OUTD, name)
    if not os.path.isfile(p):
        raise SystemExit(
            "%s is missing. Refusing to verify against artifacts that are not "
            "there -- an empty load makes every partition sum 0 == 0." % p)
    d = json.load(io.open(p, encoding="utf-8"))
    if not d:
        raise SystemExit("%s loaded empty" % p)
    return d


def section22(text=None):
    t = text if text is not None else io.open(DOC, encoding="utf-8").read()
    a = t.find("\n## 22.")
    if a < 0:
        raise SystemExit("section 22 not found in %s" % DOC)
    b = t.find("\n## 23.", a)
    return t[a:] if b < 0 else t[a:b]


def tables(text):
    """Every markdown table as (header_cells, [row_cells])."""
    out, cur, hdr = [], None, None
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s[1:-1].split("|")]
            if hdr is None:
                hdr, cur = cells, []
            elif set("".join(cells)) <= set("-: "):
                continue
            else:
                cur.append(cells)
        else:
            if hdr is not None and cur:
                out.append((hdr, cur))
            hdr, cur = None, None
    if hdr is not None and cur:
        out.append((hdr, cur))
    return out


def find_table(tabs, *needles):
    hits = [t for t in tabs if all(any(n in h for h in t[0]) for n in needles)]
    return hits[0] if len(hits) == 1 else None


def nums(cell):
    """All numbers in a cell, commas and markdown emphasis stripped."""
    c = cell.replace(",", "").replace("*", "")
    return [float(x) for x in re.findall(r"-?\d+\.?\d*", c)]


class Check(object):
    def __init__(self):
        self.m = self.mm = self.un = 0
        self.bad = []

    def eq(self, label, got, want, tol=0.0):
        if got is None:
            self.un += 1
            self.bad.append("  UNRESOLVED %-42s could not locate it" % label)
        elif got == want or (isinstance(got, float) and isinstance(want, float)
                             and abs(got - want) <= tol):
            self.m += 1
        else:
            self.mm += 1
            self.bad.append("  MISMATCHED %-42s doc %r vs artifact %r"
                            % (label, got, want))

    def total(self):
        return self.m + self.mm + self.un


def row_of(tab, pred):
    if tab is None:
        return None
    hits = [r for r in tab[1] if pred(r)]
    return hits[0] if len(hits) == 1 else None


def _conclusions(ck, text, cb, dl, re_, b4, pin, neg):
    """Conclusions, not only numbers.

    ORCH's warning, measured on this very script before it was extended: five of
    six conclusion flips passed. Flipping section 22.4's RED and GREEN, or the
    22.1 pin row's `0 DN` to `65,535 DN`, or "disturbed none of them" to
    "disturbed several", left every checked number intact and the verifier
    reported 49 matched. That is the shape that carried another lane's report
    through 712 green checks with its verdict reversed from refuted to
    confirmed.

    A number is not a conclusion. Each check below derives the CONCLUSION from
    the artifact and requires the document to state that one, so reversing the
    prose is a MISMATCH rather than an absence.
    """
    tabs = tables(text)

    # -- 22.1: the two pre-fix arms, keyed by binary --------------------
    t = find_table(tabs, "binary", "repro line", "replay vs original")
    for key, art, subst in (("HEAD", b4, False), ("pin", pin, True)):
        r = row_of(t, lambda x, k=key: x[0].strip().startswith(k))
        rows = [q for q in art["rows"] if "max_abs" in q]
        want_max = float(max(q["max_abs"] for q in rows)) if rows else None
        want_n = float(rows[0]["n"]) if rows else None
        v = nums(r[2]) if r and len(r) > 2 else None
        ck.eq("22.1 %s replay max abs" % key, v[0] if v else None, want_max)
        ck.eq("22.1 %s sample count" % key, v[1] if v and len(v) > 1 else None,
              want_n)
        # Was the line substituted? Read from the artifact, not from the prose.
        got = None
        if r and len(r) > 1:
            got = ("substituted" in r[1]) and ("verbatim" not in r[1])
        art_subst = bool(rows) and any(
            re.search(r"--exposure[= ]", q.get("repro", "")) for q in rows)
        ck.eq("22.1 %s substitution stated" % key, got, art_subst)
        ck.eq("22.1 %s substitution matches artifact" % key, art_subst, subst)

    # -- 22.4: the negative control's two verdicts ----------------------
    t = find_table(tabs, "script under test", "verdict")
    for key, want, phase in (("pre-fix", neg["prefix_verdict"], "negred"),
                             ("fixed", neg["fixed_verdict"], "neggreen")):
        r = row_of(t, lambda x, k=key: k in x[0])
        c = r[1] if r and len(r) > 1 else None
        tok = re.search(r"\b(RED|GREEN|BLOCKED)\b", c) if c else None
        ck.eq("22.4 %s arm verdict" % key, tok.group(1) if tok else None, want)
        v = nums(c) if c else None
        art = jload("77-repro-contract-%s.json" % phase)
        ck.eq("22.4 %s passed" % key, v[0] if v else None, float(art["passed"]))
        ck.eq("22.4 %s failed" % key, v[1] if v and len(v) > 1 else None,
              float(art["failed"]))
        ck.eq("22.4 %s undefined" % key, v[2] if v and len(v) > 2 else None,
              float(art["undefined"]))
    ck.eq("22.4 pre-fix rev cited", neg["prefix_rev"] in text, True)

    # -- prose conclusions, each derived from an artifact ---------------
    # Whitespace-normalised: these phrases wrap across lines in the rendered
    # document, and a plain substring probe reports a false absence on wrapped
    # prose. One of the six audit probes read UNANCHORED for exactly that.
    norm = re.sub(r"\s+", " ", text)

    def polarity(label, yes, no, truth):
        y, n = yes in norm, no in norm
        if y == n:
            ck.eq(label, None, truth)
        else:
            ck.eq(label, y, truth)

    prefix_clean = all(q["max_abs"] == 0 for a in (b4, pin) for q in a["rows"]
                       if "max_abs" in q)
    polarity("22.1 conclusion: control did not fire",
             "The negative control did not fire",
             "The negative control fired", prefix_clean)
    polarity("22.1 conclusion: accidentally correct",
             "**accidentally correct**", "**actively destructive**",
             prefix_clean)
    polarity("22.6 conclusion: no master disturbed",
             "disturbed none of them", "disturbed several of them",
             all(q.get("verdict") == "PASS" for q in dl["rows"]))
    subs = set(q["subject"] for q in cb["rows"])
    worse = all(
        [q for q in cb["rows"] if q["subject"] == s and q["label"].startswith("B_")][0]["max_abs"]
        < [q for q in cb["rows"] if q["subject"] == s and q["label"].startswith("A_")][0]["max_abs"]
        for s in subs)
    polarity("22.3 conclusion: direction of the improvement",
             "the substitution destroys it",
             "the substitution preserves it", worse)


def verify(text, quiet=False):
    cb, dl, re_ = (jload("78-crossbinary.json"), jload("81-delivered.json"),
                   jload("80-reemit.json"))
    tabs = tables(text)
    ck = Check()

    # -- commissioning table -------------------------------------------
    t = find_table(tabs, "arm", "mutation", "required")
    for key, art in (("C_PLANTED", cb["commission_planted"]),
                     ("D_NULL", cb["commission_null"])):
        r = row_of(t, lambda x, k=key: k in x[0])
        c = r[2] if r and len(r) > 2 else None
        v = nums(c) if c else None
        ck.eq("%s max abs" % key, v[0] if v else None, float(art["max_abs"]))
        ck.eq("%s result verdict" % key, (art["verdict"] in c) if c else None, True)
        ck.eq("%s required verdict" % key,
              (r[3].strip() if r and len(r) > 3 else None), art["verdict"])
        if key == "C_PLANTED":
            ck.eq("C_PLANTED differing samples",
                  v[1] if v and len(v) > 2 else None,
                  float(art["n_diff"]))
            ck.eq("C_PLANTED sample count",
                  v[2] if v and len(v) > 2 else None, float(art["n"]))

    # -- substituted-vs-verbatim table ---------------------------------
    t = find_table(tabs, "subject", "contract", "max abs")
    for r0 in cb["rows"]:
        word = "substituted" if r0["label"].startswith("A_") else "verbatim"
        key = "%s/%s" % (r0["subject"], word)
        hit = row_of(t, lambda x, s=r0["subject"], w=word:
                     x[0].strip() == s and w in x[1])
        for col, name, want in ((2, "clip", (r0["clip_a"], r0["clip_b"])),
                                (3, "median", (r0["med_a"], r0["med_b"])),
                                (4, "maxabs", (float(r0["max_abs"]),))):
            v = nums(hit[col]) if hit and col < len(hit) else None
            for i, w in enumerate(want):
                ck.eq("%s %s[%d]" % (key, name, i),
                      v[i] if v and len(v) > i else None, round(w, 4), 5e-5)

    # -- delivered table ------------------------------------------------
    t = find_table(tabs, "sealed master", "replay", "difference")
    for r0 in dl["rows"]:
        hit = row_of(t, lambda x, s=r0["subject"]: x[0].strip() == s)
        for col, side in ((1, "a"), (2, "b")):
            c = hit[col] if hit and col < len(hit) else None
            v = nums(c) if c else None
            ck.eq("%s cell[%s] clip" % (r0["subject"], side),
                  v[0] if v else None, round(r0["clip_%s" % side], 4), 5e-5)
            ck.eq("%s cell[%s] median" % (r0["subject"], side),
                  v[1] if v and len(v) > 1 else None, r0["med_%s" % side])
            sha = re.search(r"[0-9A-F]{16}", c) if c else None
            ck.eq("%s cell[%s] sha" % (r0["subject"], side),
                  sha.group(0) if sha else None, r0["sha_%s" % side])
        c = hit[3] if hit and len(hit) > 3 else None
        v = nums(c) if c else None
        ck.eq("%s delivered max abs" % r0["subject"], v[0] if v else None,
              float(r0["max_abs"]))
        ck.eq("%s delivered sample count" % r0["subject"],
              v[1] if v and len(v) > 1 else None, float(r0["n"]))

    # -- counts that legitimately recur: EVERY stated instance must agree
    n_rw = sum(1 for x in re_["rows"] if x["outcome"] == "rewritten")
    for pat, want, label in (
            (r"(\d+) rewritten", n_rw, "sidecars rewritten"),
            (r"(\d+) untouched", dl["seals_untouched"], "seals untouched"),
            (r"(\d+)\s*\n?correct \+ 0 still wrong", n_rw, "sidecars verified")):
        found = re.findall(pat, text)
        if not found:
            ck.eq(label, None, want)
            continue
        vals = [int(f) for f in found]
        ck.eq("%s (all %d instances)" % (label, len(vals)), vals,
              [want] * len(vals))

    # Verdict tokens recur too (prose plus evidence table), so the same
    # all-occurrences rule applies: every token of the family must equal the
    # artifact's verdict. A plain `verdict in text` was satisfied by the second
    # copy while the first read SUBSTITUTION-IS-BETTER -- caught in
    # commissioning, which is what commissioning is for.
    for fam, want, label in (
            (r"SUBSTITUTION-IS-[A-Z]+", cb["verdict"], "crossbinary verdict"),
            (r"\b(?:RE-EMITTED|INCOMPLETE|ABORTED)\b", re_["verdict"],
             "re-emit verdict")):
        found = re.findall(fam, text)
        if not found:
            ck.eq(label, None, want)
        else:
            ck.eq("%s (all %d instances)" % (label, len(found)), found,
                  [want] * len(found))

    _conclusions(ck, text, cb, dl, re_,
                 jload("77-repro-contract-before.json"),
                 jload("77-repro-contract-pin.json"),
                 jload("79-negcontrol.json"))

    if not quiet:
        for b in ck.bad:
            say(b)
        say("  %d declared = %d matched + %d mismatched + %d unresolved"
            % (ck.total(), ck.m, ck.mm, ck.un))
    return ck


DEFECTS = [
    ("31,792 DN", "31,793 DN", "planted max abs off by one"),
    ("85.5637%", "85.5638%", "substituted clip last digit"),
    ("13,547 DN", "13,548 DN", "verbatim max abs off by one"),
    ("18E6EDA98DEC9930", "18E6EDA98DEC9931", "sealed sha last nibble"),
    ("26 untouched", "25 untouched", "seals untouched count"),
    ("26 rewritten", "25 rewritten", "rewritten count"),
    ("15.0839%", "15.0840%", "foam substituted clip"),
    ("60,918", "60,917", "sealed median"),
    ("96,349,077", "96,349,078", "planted differing samples"),
    ("SUBSTITUTION-IS-WORSE", "SUBSTITUTION-IS-BETTER", "crossbinary verdict"),
    ("54,925", "54,926", "foam substituted replay median"),
    ("6,768", "6,767", "foam sealed median"),
    ("41,990 DN", "41,991 DN", "foam substituted max abs"),
    ("| PASS |", "| FAIL |", "null required verdict"),
]


def commission():
    say("=== COMMISSIONING: plant a defect, require the verifier to catch it ===")
    base = section22()
    ck0 = verify(base, quiet=True)
    say("  clean section : %d matched + %d mismatched + %d unresolved of %d"
        % (ck0.m, ck0.mm, ck0.un, ck0.total()))
    if ck0.mm or ck0.un:
        for b in ck0.bad:
            say(b)
        say("VERDICT: NOT-COMMISSIONED -- the clean section does not verify, so "
            "a caught defect could not be attributed to the plant.")
        raise SystemExit(2)
    caught = missed = unanchored = 0
    for old, new, label in DEFECTS:
        if old not in base:
            unanchored += 1
            say("  UNANCHORED %-42s %r absent -- a plant that does not land is "
                "a second null, not a pass" % (label, old))
            continue
        ck = verify(base.replace(old, new, 1), quiet=True)
        if ck.mm + ck.un > 0:
            caught += 1
        else:
            missed += 1
            say("  MISSED     %-42s %r -> %r undetected" % (label, old, new))
    say("  %d planted = %d caught + %d missed + %d unanchored"
        % (len(DEFECTS), caught, missed, unanchored))
    if caught + missed + unanchored != len(DEFECTS):
        raise SystemExit("partition does not sum")
    ok = caught == len(DEFECTS)
    say()
    say("VERDICT: %s" % ("COMMISSIONED" if ok else "NOT-COMMISSIONED"))
    return ok


def main():
    com = "--commission" in sys.argv
    say("=== verify section 22 against the artifacts it cites ===")
    say()
    if com:
        ok = commission()
    else:
        say("=== CLAIMS ===")
        ck = verify(section22())
        ok = (ck.mm == 0 and ck.un == 0 and ck.m == ck.total())
        say()
        say("VERDICT: %s" % ("PASS" if ok else "FAIL"))
    io.open(os.path.join(OUTD, "82-verify-s22%s.log" % ("-commission" if com else "")),
            "w", encoding="utf-8").write("\n".join(log) + "\n")
    if not ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
