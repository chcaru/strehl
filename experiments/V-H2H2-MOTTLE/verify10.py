r"""Verify every numeric claim in V-HEADTOHEAD2 section 10 against its source log.

DISCIPLINE, from this lane's own prior failures:
  * Each claim is anchored on a neighbouring literal, not merely searched for.
    A bare presence test for "0.9271" is satisfied by any duplicate of that value
    anywhere in the document, so it is a statement about the corpus of digits
    rather than about the claim.
  * The doc is READ AS BYTES via subprocess where git is involved; here it is read
    directly, but whitespace is collapsed before matching, because a phrase that
    spans a line break defeats a plain substring probe.
  * Commissioned by mutating a COPY in $TEMP -- never `git checkout --`.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "docs", "research", "V-HEADTOHEAD2.md")
LOGS = r"C:\dev\strehl-out\V-H2H2\logs"


def read_doc(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        txt = f.read()
    i = txt.find("# \u00a710 The mid-scale mottle")
    if i < 0:
        raise SystemExit("section 10 not found in %s" % path)
    return txt[i:]


def flat(s):
    return re.sub(r"\s+", " ", s)


def log_rows(subject):
    """Parse the dose table out of the subject's own run log."""
    p = os.path.join(LOGS, "dose5-%s.txt" % subject)
    txt = open(p, "r", encoding="utf-8", errors="replace").read()
    rows = {}
    for m in re.finditer(
            r"^\s*mc=(\d+)\s+([\d.]+) \[([\d.]+),([\d.]+)\]\s+([\d.]+) \[[\d.,]+\]"
            r"\s+([\d.]+) \[[\d.,]+\]\s+([\d.]+) \[", txt, re.M):
        rows[int(m.group(1))] = dict(blotch=m.group(2), blo=m.group(3), bhi=m.group(4),
                                     noise=m.group(5), sharp=m.group(6), detail=m.group(7))
    com = {}
    for m in re.finditer(
            r"^\s{4}(clone|gain x1\.5|mottle\+ repair|mottle\+|band- global|blur s2)\s+"
            r"([\d.]+) \[([\d.]+),([\d.]+)\]\s+([\d.]+) \[[\d.,]+\]"
            r"\s+([\d.]+) \[[\d.,]+\]\s+([\d.]+) \[([\d.]+),([\d.]+)\]", txt, re.M):
        com[m.group(1)] = dict(blotch=m.group(2), blo=m.group(3), bhi=m.group(4),
                               noise=m.group(5), sharp=m.group(6),
                               detail=m.group(7), dlo=m.group(8), dhi=m.group(9))
    lad = re.search(r"repair/defect\s+([\d.]+) \[([\d.]+),([\d.]+)\]\s+([\d.]+)"
                    r" \[[\d.,]+\]\s+([\d.]+) \[[\d.,]+\]\s+([\d.]+) \[", txt)
    absf = re.search(r"flat\s+: blotch ([\d.]+)\s+noise ([\d.]+)\s+sharp ([\d.]+)", txt)
    verd = re.findall(r"^\s{4}(\S.*?)\s+(PASS|FAIL)\s*$", txt, re.M)
    return rows, com, lad, absf, verd


def check(doc, claims):
    """Each claim carries its own SPAN KEY: the search is scoped to the region of
    the document that region belongs to, and only then anchored within it.

    The first version anchored on `\\| mc=5 \\|` alone. After whitespace
    collapsing, the end of the `coffee-bubbles` mc=4 row followed by the start of
    the mc=5 row spells exactly `| | mc=5 |`, so every per-subject claim in the
    THREE-SUBJECT table matched the FIRST table instead and was compared against
    the wrong subject's numbers -- 32 false failures, and had the values happened
    to coincide it would have been 32 false passes. An anchor that can match in
    the wrong section is not an anchor.
    """
    ok = bad = 0
    for label, span_key, anchor, value in claims:
        span = scope(doc, span_key)
        if span is None:
            bad += 1
            print("  FAIL  %-46s span %r absent" % (label, span_key))
            continue
        m = re.search(anchor, span)
        if m and value in m.group(0):
            ok += 1
        else:
            bad += 1
            why = "anchor absent in span" if not m else "value %r not in anchored span" % value
            print("  FAIL  %-46s %s" % (label, why))
    return ok, bad


SPANS = {
    "cb-table": (r"\*\*`coffee-bubbles`\*\* \(19 frames",
                 r"\*\*The other three"),
    "cb-com": (r"Representative ladder,", r"The cheat scores"),
    "lead-1-cpl": (r"\| `lead-1-cpl` \(123 fr\) \|", r"\| `foam` \(100 fr\) \|"),
    "foam": (r"\| `foam` \(100 fr\) \|", r"\| `113MSDCF` \(63 fr\) \|"),
    "113MSDCF": (r"\| `113MSDCF` \(63 fr\) \|", r"`mc >= 7` sets every band"),
    "ceiling": (r"## 10\.5 The ceiling", r"The ceiling costs"),
    "verdict": (r"## 10\.6 Verdict", r"Recommendation, for ORCH"),
    "free": (r"At doses that keep sharpness", r"## 10\.6"),
    "abs": (r"\*\*`coffee-bubbles`\*\* \(19 frames", r"\| arm \|"),
}


def scope(doc, key):
    a, b = SPANS[key]
    ma = re.search(a, doc)
    if not ma:
        return None
    mb = re.search(b, doc[ma.start():])
    return doc[ma.start(): ma.start() + (mb.start() if mb else len(doc))]


def build_claims():
    claims = []
    for subj in ("coffee-bubbles", "lead-1-cpl", "foam", "113MSDCF"):
        rows, com, lad, absf, verd = log_rows(subj)
        n_pass = sum(1 for _, v in verd if v == "PASS")
        n_fail = sum(1 for _, v in verd if v == "FAIL")
        if n_fail:
            raise SystemExit("REFUSED: %s log shows %d FAIL verdicts" % (subj, n_fail))
        if n_pass != 9:
            raise SystemExit("REFUSED: %s log shows %d PASS verdicts, expected 9"
                             % (subj, n_pass))
        if subj == "coffee-bubbles":
            for mc, r in sorted(rows.items()):
                if mc == 0:
                    continue
                # Exactly four data columns. An earlier `{5}` matched every row
                # except the LAST, because each non-final row borrowed the next
                # row's leading pipe as its fifth cell -- so the anchored span ran
                # one row long and a wrong value in the following row would have
                # satisfied it.
                anchor = r"\| mc=%d \|([^|]*\|){4}" % mc
                for term in ("blotch", "blo", "bhi", "sharp", "detail"):
                    claims.append(("cb mc=%d %s" % (mc, term), "cb-table", anchor, r[term]))
            for name, key in (("mottle\\+ repair", "mottle+ repair"), ("mottle\\+", "mottle+"),
                              ("band- global", "band- global"), ("blur s2", "blur s2")):
                c = com[key]
                anchor = r"\| `%s` vs base \|([^|]*\|){4}" % name
                claims.append(("cb com %s blotch" % key, "cb-com", anchor, c["blotch"]))
                claims.append(("cb com %s detail" % key, "cb-com", anchor, c["detail"]))
            lad_anchor = r"\| repair / defect \|([^|]*\|){4}"
            for i, term in ((1, "blotch"), (2, "ci-lo"), (3, "ci-hi")):
                claims.append(("cb ladder %s" % term, "cb-com", lad_anchor, lad.group(i)))
            claims.append(("cb abs blotch", "abs", r"absolute blotch [\d.]+\)", absf.group(1)[:5]))
        else:
            for mc in (3, 5, 7):
                r = rows[mc]
                anchor = r"\| mc=%d \|([^|]*\|){3}" % mc
                for term in ("blotch", "blo", "sharp", "detail"):
                    claims.append(("%s mc=%d %s" % (subj, mc, term), subj, anchor, r[term]))
    return claims


def derived(doc):
    """Arithmetic stated in the document must actually be the arithmetic.

    THE STATED VALUE IS READ OUT OF THE DOCUMENT. An earlier version computed the
    value from the log and compared it to a string constant typed into this file,
    so it never read the document at all -- two planted defects in exactly these
    numbers were MISSED by the commissioning suite while every table claim was
    caught. A check that cannot see the claim it certifies is a statement about
    its own source code.
    """
    out = []
    cbrows, _, _, _, _ = log_rows("coffee-bubbles")

    def stated(span_key, pat, label):
        s = scope(doc, span_key)
        if s is None:
            return None
        m = re.search(pat, s)
        return m.group(1) if m else None

    for mc, pat in ((5, r"1\.4501 x 0\.8622 = \*\*([\d.]+)\*\*"),
                    (8, r"1\.4501 x 0\.8025 = \*\*([\d.]+)\*\*")):
        got = stated("verdict", pat, "conviction")
        want = "%.3f" % (1.4501 * float(cbrows[mc]["blotch"]))
        out.append(("conviction x mc=%d" % mc, got == want,
                    "doc %s, computed %s" % (got, want)))

    for subj, top, pat in (
            ("coffee-bubbles", 8,
             r"`coffee-bubbles` \| \*\*([\d.]+)% \[([\d.]+), ([\d.]+)\]\*\*"),
            ("113MSDCF", 7,
             r"`113MSDCF` \| \*\*([\d.]+)% \[([\d.]+), ([\d.]+)\]\*\*")):
        r, _, _, _, _ = log_rows(subj)
        s = scope(doc, "ceiling")
        m = re.search(pat, s) if s else None
        want = ("%.1f" % ((1.0 - float(r[top]["blotch"])) * 100.0),
                "%.1f" % ((1.0 - float(r[top]["bhi"])) * 100.0),
                "%.1f" % ((1.0 - float(r[top]["blo"])) * 100.0))
        got = m.groups() if m else None
        out.append(("ceiling %s" % subj, got == want, "doc %s, computed %s" % (got, want)))

    got = stated("free", r"lowers blotch \*\*([\d.]+)%\*\*", "free gain")
    want = "%.1f" % ((1.0 - float(cbrows[5]["blotch"])) * 100.0)
    out.append(("cb mc=5 free gain", got == want, "doc %s, computed %s" % (got, want)))

    got = stated("free", r"detail falls only \*\*([\d.]+)%\*\*", "detail cost")
    want = "%.1f" % ((1.0 - float(cbrows[5]["detail"])) * 100.0)
    out.append(("cb mc=5 detail cost", got == want, "doc %s, computed %s" % (got, want)))
    return out


def run(doc_path, quiet=False):
    doc = flat(read_doc(doc_path))
    claims = build_claims()
    ok, bad = check(doc, claims)
    for label, good, shown in derived(doc):
        if good:
            ok += 1
        else:
            bad += 1
            print("  FAIL  %-46s computed %s" % (label, shown))
    if not quiet:
        print("  %d/%d numeric claims verified  %s"
              % (ok, ok + bad, "GREEN" if bad == 0 else "RED"))
    return bad


def commission():
    """Plant last-digit defects in a COPY and require each to be caught."""
    print("COMMISSIONING the verifier (each planted defect must turn it RED)")
    src = os.path.abspath(DOC)
    defects = [
        ("cb mc=3 blotch", "| mc=3 | 0.9271 [0.8832, 0.9474] |", "| mc=3 | 0.9272 [0.8832, 0.9474] |"),
        ("cb mc=8 blotch", "| mc=8 | **0.8025 [0.7423, 0.8603]**", "| mc=8 | **0.8026 [0.7423, 0.8603]**"),
        ("cheat detail", "**0.4586 [0.4488, 0.4839]** |", "**0.4587 [0.4488, 0.4839]** |"),
        ("ladder blotch", "| **0.8529 [0.8031, 0.9131]** |", "| **0.8530 [0.8031, 0.9131]** |"),
        ("foam mc=5 detail", "| | mc=5 | 0.5873 [0.5684, 0.5993] | 0.8632 | **0.5811** |",
         "| | mc=5 | 0.5873 [0.5684, 0.5993] | 0.8632 | **0.5812** |"),
        ("derived conviction", "= **1.250**", "= **1.251**"),
        ("derived ceiling", "| `coffee-bubbles` | **19.8% [14.0, 25.8]**",
         "| `coffee-bubbles` | **19.7% [14.0, 25.8]**"),
    ]
    caught = 0
    orig = open(src, "r", encoding="utf-8", errors="replace").read()
    tmp = os.path.join(tempfile.gettempdir(), "vh2_s10_commission.md")
    for name, find, repl in defects:
        if orig.count(find) != 1:
            print("  MUTATION TARGET NOT FOUND (%d hits): %s" % (orig.count(find), name))
            continue
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(orig.replace(find, repl, 1))
        bad = run(tmp, quiet=True)
        print("  %-22s planted -> %s" % (name, "CAUGHT" if bad else "MISSED"))
        caught += 1 if bad else 0
    if os.path.exists(tmp):
        os.remove(tmp)
    print("  commissioned %d/%d" % (caught, len(defects)))
    return caught == len(defects)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    okc = commission()
    print()
    print("VERIFYING the shipped section 10")
    bad = run(os.path.abspath(DOC))
    sys.exit(0 if (okc and bad == 0) else 1)
