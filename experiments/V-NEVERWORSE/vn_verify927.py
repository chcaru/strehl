"""Re-derive every number quoted in section 9.27 from the records.

WHY ANCHORS.  Several values in 9.27 are short or repeat legitimately -- 1.0783
is both `coffee-bubbles` mean-arm mot invariance AND `coffee-bubbles` L0
amplitude ratio; 0.14, 0.20 and 0.25 occur throughout the file as band edges.
A bare substring test would be satisfied by the wrong occurrence, so every
check carries a neighbouring literal that pins it to its own sentence.

WHY THE SUMMARY PARTITIONS.  A count that does not move reads the same whether
nothing was wrong or nothing was examined.  Outcomes are verified / mismatched
/ absent / unresolvable and they must sum to the number of checks defined.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, "RESULT.md")
QB = r"C:\dev\strehl-out\V-NEVERWORSE\qband"
LB = r"C:\dev\strehl-out\V-NEVERWORSE\l0band"

BANDS = ("mot", "qual", "mid", "fine")


def _heading(text, head):
    """Offset of `head` as a LINE-START heading, not as prose.

    `## 10. Files` also occurs inside a sentence earlier in this document, and
    an unanchored find() sliced from there -- silently pulling section 9.27's
    own text into what was supposed to be the file list, and inflating a count
    by exactly one.  The check that caught it was the partition, not the total.
    """
    m = re.search(r"^" + re.escape(head), text, re.M)
    if not m:
        raise AssertionError("heading %r not found at line start" % head)
    return m.start()


def section(text, head="### 9.27", nxt=None):
    """Section 9.27 up to the NEXT heading of any level.

    Originally this stopped at the literal `## 10. Files`, which broke as soon
    as 9.28 was added -- the body would have swallowed it and the occurrence
    counts below would have silently shifted.  Stopping at the next heading is
    the property actually wanted.
    """
    i = _heading(text, head)
    m = re.search(r"^#{2,3} ", text[i + len(head):], re.M)
    return text[i:i + len(head) + m.start()] if m else text[i:]


class Checker:
    def __init__(self, body):
        self.body = body
        self.flat = re.sub(r"\s+", " ", body)
        self.verified = []
        self.mismatched = []
        self.absent = []
        self.unresolvable = []

    def has(self, name, value, anchor):
        """`value` must occur inside a window around `anchor`."""
        if anchor not in self.flat:
            self.unresolvable.append("%s: anchor %r not present" % (name, anchor))
            return
        ok = False
        for m in re.finditer(re.escape(anchor), self.flat):
            w = self.flat[m.start():m.end() + 400]
            if value in w:
                ok = True
                break
        (self.verified if ok else self.mismatched).append(
            "%s = %s" % (name, value))

    def count(self, name, pattern, want, whole):
        n = len(re.findall(pattern, whole))
        if n == want:
            self.verified.append("%s occurs %d time(s)" % (name, n))
        else:
            self.mismatched.append(
                "%s: expected %d occurrence(s), found %d" % (name, want, n))

    def conclusion(self, name, anchor, must_say, must_not_say, window=520):
        """Pin a CONCLUSION to the record that determines it.

        A presence test for a word like "refuted" is satisfied by any duplicate
        or paraphrase elsewhere in the document and cannot notice that the
        sentence now says the opposite.  So each check here takes a window
        around ONE anchor, requires the phrasing the RECORD implies, and
        forbids the phrasings that would reverse it.  `must_say` is derived
        from data wherever a record exists, so the document cannot drift away
        from its own evidence.
        """
        if anchor not in self.flat:
            self.unresolvable.append("%s: anchor %r not present" % (name, anchor))
            return
        i = self.flat.find(anchor)
        w = self.flat[i:i + window]
        if must_say not in w:
            self.mismatched.append(
                "%s: does not assert %r" % (name, must_say))
            return
        for bad in must_not_say:
            if bad in w:
                self.mismatched.append(
                    "%s: asserts the reverse, %r" % (name, bad))
                return
        self.verified.append("%s asserts %r" % (name, must_say))

    def report(self):
        total = (len(self.verified) + len(self.mismatched)
                 + len(self.absent) + len(self.unresolvable))
        for c in self.mismatched:
            print("  MISMATCH    %s" % c)
        for c in self.absent:
            print("  ABSENT      %s" % c)
        for c in self.unresolvable:
            print("  UNRESOLVED  %s" % c)
        print("\n  verified %d   mismatched %d   absent %d   unresolvable %d"
              "   = %d checks"
              % (len(self.verified), len(self.mismatched), len(self.absent),
                 len(self.unresolvable), total))
        bad = len(self.mismatched) + len(self.absent) + len(self.unresolvable)
        print("  %s" % ("GREEN" if bad == 0 else "RED (%d failing)" % bad))
        return bad == 0


VL = os.path.join(os.path.dirname(HERE), "V-LINEAR")


def vlband(subject, band):
    """One band verdict straight out of V-LINEAR's committed bandsweep record.

    Quoting another lane's number means re-deriving it from that lane's record,
    not transcribing it. Transcription is exactly how this section came to head
    two columns `0.30-0.35` / `0.40-0.45` over values measured at `0.30-0.40`
    and `0.40-0.48`.
    """
    p = os.path.join(VL, "bandsweep-far20-%s.json" % subject)
    with open(p, encoding="utf-8") as fh:
        rows = json.load(fh)
    return rows[0]["bands"][band]


def ratios(rec):
    """scene(deepest N) / scene(half N) per arm, recomputed from the record."""
    by = {}
    for r in rec["rows"]:
        by.setdefault(r["arm"], []).append(r)
    out = {}
    for arm, rows in by.items():
        rows.sort(key=lambda r: -r["N"])
        deep, half = rows[0], rows[1]
        out[arm] = {}
        for b in BANDS:
            d, h = deep["bands"][b]["scene"], half["bands"][b]["scene"]
            out[arm][b] = (d / h) if h > 0 else None
    return out


def main():
    whole = open(RESULT, encoding="utf-8").read()
    body = section(whole)
    ck = Checker(body)

    # ---- the qualified-band ladder, recomputed from the records
    subj_anchor = {"coffee-bubbles": "`coffee-bubbles` | ",
                   "112MSDCF": "`112MSDCF` | "}
    for subj in ("coffee-bubbles", "112MSDCF"):
        rec = json.load(open(os.path.join(QB, subj + ".json")))
        rr = ratios(rec)
        for arm in ("mean", "confidence", "shipping", "argmax"):
            for b in BANDS:
                v = rr[arm][b]
                nm = "%s/%s/%s" % (subj, arm, b)
                if v is None:
                    ck.has(nm, "REFUSED", subj_anchor[subj] + arm)
                else:
                    ck.has(nm, "%.4f" % v, subj_anchor[subj] + arm)

    # ---- the L0 qualification
    for subj, pub in (("coffee-bubbles", "0.25"), ("112MSDCF", "0.20")):
        rec = json.load(open(os.path.join(LB, subj + ".json")))
        a = rec["L0"]
        anc = "`%s` | **" % subj
        ck.has(subj + " L0 R", "%.4f" % a["R"], anc)
        ck.has(subj + " L0 ci_lo", "%.4f" % a["ci_lo"], anc)
        ck.has(subj + " L0 ci_hi", "%.4f" % a["ci_hi"], anc)
        ck.has(subj + " L0 amplitude", "%.4f" % a["R_amplitude"], anc)
        if a["verdict"] != "FAIL(noise)":
            ck.mismatched.append("%s L0 verdict is %s, section says FAIL(noise)"
                                 % (subj, a["verdict"]))
        else:
            ck.verified.append("%s L0 verdict FAIL(noise)" % subj)
        if rec["boundary_agrees"]:
            ck.mismatched.append(
                "%s boundary AGREES in the record but 9.27 withholds" % subj)
        else:
            ck.verified.append("%s boundary disagrees, verdict withheld" % subj)
        ck.has(subj + " published boundary", pub,
               "published **0.25** and **0.20**")
        ck.has(subj + " my boundary", "0.14", "mine reads **0.14** on both")

    # ---- the gauge control: 48 of 48 identical, recomputed
    a = json.load(open(os.path.join(QB, "coffee-bubbles.json")))
    b = json.load(open(os.path.join(QB, "coffee-bubbles-green.json")))
    same = sum(1 for ra, rb in zip(a["rows"], b["rows"]) for t in BANDS
               if ra["bands"][t]["scene"] == rb["bands"][t]["scene"])
    tot = sum(1 for _ in a["rows"]) * len(BANDS)
    ck.has("gauge identical cells", "%d of %d" % (same, tot),
           "gave **48 of 48 scene cells bit-identical**")
    if b.get("gauge") != "green-replicated (from RGB, control)":
        ck.mismatched.append("gauge label is %r" % b.get("gauge"))
    else:
        ck.verified.append("gauge label confirms the plant landed")

    # ---- the zero-occurrence claims.
    # SCOPE, STATED.  The claim is about this lane's PRIOR record, so 9.27 is
    # excluded: the section necessarily contains both strings in the act of
    # stating that they do not occur.  Counting the whole file would report a
    # failure caused by the claim itself.
    outside = whole.replace(body, "")
    ck.count("contrast_ms outside 9.27", r"contrast_ms", 0, outside)
    ck.count("contrast_ms inside 9.27", r"contrast_ms", 2, body)
    # 0.20-0.25 is NOT absent -- the first draft of 9.27 claimed it was and
    # this check is what refuted it.  Both occurrences must sit inside 9.17,
    # which 9.23 retracts; an occurrence anywhere else would be a live
    # fixed-band quotation and must fail.
    s917 = whole[_heading(whole, "### 9.17"):_heading(whole, "### 9.18")]
    files = whole[_heading(whole, "## 10. Files"):]
    ck.count("0.20-0.25 inside retracted 9.17", r"0\.20-0\.25", 2, s917)
    ck.count("0.20-0.25 inside 9.27", r"0\.20-0\.25", 1, body)
    ck.count("0.20-0.25 inside the file list", r"0\.20-0\.25", 1, files)
    # The partition must exhaust the file: 2 retracted + 1 claim + 1 file list.
    # A bare total would let an occurrence move between sections unnoticed.
    ck.count("0.20-0.25 anywhere in the file", r"0\.20-0\.25", 4, whole)

    # ---- CONCLUSIONS, pinned to the records that determine them.
    # Added after ORCH's 2026-08-28 broadcast reported that a verifier of this
    # lane's passed 712 checks with a section's verdict flipped from "refuted"
    # to "confirmed".  Measured on THIS verifier before the fix: 6 of 6 numeric
    # plants caught, 0 of 5 conclusion plants caught.  A GREEN that certifies
    # only arithmetic is worth very little.
    cb = json.load(open(os.path.join(LB, "coffee-bubbles.json")))
    m112 = json.load(open(os.path.join(LB, "112MSDCF.json")))
    qcb = ratios(json.load(open(os.path.join(QB, "coffee-bubbles.json"))))
    qm = ratios(json.load(open(os.path.join(QB, "112MSDCF.json"))))

    for subj, rec in (("coffee-bubbles", cb), ("112MSDCF", m112)):
        wrong = [v for v in ("PASS", "MARGINAL") if v != rec["L0"]["verdict"]]
        ck.conclusion("%s L0 table verdict" % subj, "`%s` | **" % subj,
                      rec["L0"]["verdict"], wrong, window=120)

    # WITHHELD is not a stylistic choice -- it follows from boundary_agrees
    withheld = not (cb["boundary_agrees"] or m112["boundary_agrees"])
    ck.conclusion("subject-level verdict", "The subject-level verdict is",
                  "WITHHELD" if withheld else "GRANTED",
                  ["CONFIRMED", "ESTABLISHED", "GRANTED"] if withheld else [])

    # the sign flip survives only if shipping gains where the mean loses, on
    # BOTH subjects; the word in the document must follow the arithmetic
    survives = all(q["shipping"]["qual"] > 1.0 > q["mean"]["qual"]
                   for q in (qcb, qm))
    ck.conclusion("sign flip survival", "Section 9.23.6's sign flip",
                  "survives" if survives else "dies",
                  ["dies", "does not survive", "fails"] if survives
                  else ["survives"])

    # the acuity claim is licensed only if L0 is focus-discriminable
    lic = cb["L0"]["verdict"] != "FAIL(noise)"
    ck.conclusion("acuity licensing", '"9.3% relative sharpness cost"',
                  "is licensed as an acuity" if lic
                  else "is not licensed as an acuity",
                  [] if lic else ["cost\" is licensed as an acuity"])

    # the fixture refuted the hypothesis; the direction is fixed by 1.904 <
    # 8.704, both of which are checked as numbers elsewhere in this run
    ck.conclusion("hypothesis refutation", "spectrally truncated so",
                  "refuted it", ["confirmed it", "supported it", "upheld it"])

    # ---- V-LINEAR's band verdicts, re-derived from V-LINEAR's records ----
    for subj in ("coffee-bubbles", "112MSDCF"):
        anc = "| `%s` | 0." % subj
        for band in ("0.30-0.35", "0.30-0.40", "0.40-0.48"):
            b = vlband(subj, band)
            # value and verdict pinned TOGETHER: this row carries three
            # columns and a bare "FAIL(noise)" is satisfied by either of the
            # other two, which is the duplicate-satisfaction defect again.
            ck.has("%s %s" % (subj, band),
                   "R=%.3f %s" % (b["R"], b["verdict"]), anc)
    _de = vlband("decim4-dry-erase-marker-head-cpl", "0.30-0.35")
    ck.has("width gate dry-erase 0.30-0.35", "R=%.3f" % _de["R"],
           "gate-tested first")
    ck.conclusion(
        "width gate is a subject property, not a slice artefact",
        "gate-tested first", _de["verdict"],
        ("FAIL(noise)** at that width", "MARGINAL** at that width"))
    _cb = vlband("coffee-bubbles", "0.30-0.35")
    ck.conclusion(
        "coffee-bubbles narrowing follows the record",
        "V-LINEAR reads 1.542", _cb["verdict"],
        ("MARGINAL is noise",))

    print("section 9.27 -- re-derivation from records\n")
    ok = ck.report()
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
