"""Verify docs/research/V-LINEAR-BANDS.md against the JSON it claims to quote.

WHY THE FIRST VERSION OF THIS FILE WAS WORTHLESS, RECORDED BECAUSE THE FAILURE
IS THE INSTRUCTIVE PART.  It tested `f"{R:.3f}" in whole_document`.  That reads
GREEN for 40/40 claims and STAYS GREEN when a number is corrupted, because each
R appears in up to three tables (sec.3 verdicts, sec.3 CIs, sec.4 ladder) and any
surviving copy satisfies the check.  Measured: mutating the sec.3 cell
`**4.874** PASS` to `**4.875**` left the verifier reading "40 claims verified, 0
missing", exit 0.  Its own docstring claimed it anchored on the subject row; the
code computed that anchor into a variable and then never used it.

So every check below is bound to ONE table row, located by its leading
`| \\`subject\\` |` cell, and a value must appear in THAT row.  A row that cannot
be found is counted as UNRESOLVED and fails the run -- a check that silently
matches nothing must not be readable as a check that passed, so the printed
summary partitions every claim into located-and-correct, located-and-wrong, and
unresolved, which sum to the number attempted.

    python verify_bands_doc.py     # exit 0 = every claim located in its own row
"""
import json
import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _HERE)
import bandsweep                                                 # noqa: E402

DOC = os.path.join(_ROOT, "docs", "research", "V-LINEAR-BANDS.md")
BANDS = ["0.17-0.20", "0.20-0.25", "0.25-0.30", "0.30-0.40", "0.40-0.48"]
BAND0 = ["0.25-0.30", "0.30-0.40", "0.40-0.48"]

# Round 2 (sec.9) is stored one file per subject rather than one file for the
# sweep, because those subjects were developed and swept one at a time under a
# disk constraint.  Every `bandsweep-far20*.json` beside this script is loaded,
# so a subject added later is verified without editing this list -- the failure
# mode being avoided is a new table row that no check ever looks at, which is
# the same "silently matches nothing" defect this file was rewritten for.
#
# Two kinds of file are NOT canonical subject records:
#   `simdecim`                     -- the decimation commissioning arm (sec.9.5)
#   `bandsweep-far20-leaf-2-cpl`   -- the sec.6.1 reproduction control, which
#                                     sweeps a subject ALONE to show that
#                                     `bandsignal.py`'s module-level RNG makes
#                                     the CI call-order dependent.  It disagrees
#                                     with the canonical row BY DESIGN.
# Loading that control shadowed the canonical `leaf-2-cpl` record on the first
# run of the glob and reported the document WRONG at 2 checks.  The document was
# right and the loader was wrong.
#
# The collision rule is NOT "first file wins" and NOT "declared controls only".
# It is: AGREEMENT IS NOT AMBIGUITY, DISAGREEMENT IS.  A key in two files whose
# measured values match is harmless and is accepted silently -- that is how
# `bandsweep-far20-noPF.json` is handled, a round-1 robustness arm that repeats
# all five subjects and was MEASURED here to agree to 1e-9 on all 60 of its
# R values.  A key in two files whose values differ is a real ambiguity about
# what the document quotes and is a hard error.  Written this way, a future
# control that happens to disagree cannot slip through by being added to a list.
CONTROLS = ("simdecim", "bandsweep-far20-leaf-2-cpl", "bandsweep-far20-bee-1-cpl")


def _payload(r):
    return (r["n_real"], r["step"], r["kept"],
            {b: (v["R"], v["lo"], v["hi"]) for b, v in r["bands"].items()})


def load(pattern, controls):
    recs, src = {}, {}
    for path in sorted(glob.glob(os.path.join(_HERE, pattern))):
        base = os.path.basename(path)
        if any(c in base for c in controls):
            continue
        with open(path) as fh:
            for r in json.load(fh):
                k = r["key"]
                if k in recs:
                    if _payload(recs[k]) != _payload(r):
                        raise SystemExit(
                            f"AMBIGUOUS: subject {k!r} has DIFFERENT values in "
                            f"{src[k]} and {base}; the verifier cannot know "
                            f"which the document quotes. Declare one a control.")
                    continue
                recs[k], src[k] = r, base
    return recs


def rows_for(lines, key):
    """Every table row whose FIRST cell is `key`, in document order."""
    pat = re.compile(r"^\|\s*`" + re.escape(key) + r"`\s*\|")
    return [ln.strip() for ln in lines if pat.match(ln.strip())]


def split_cells(row):
    return [c.strip() for c in row.strip("|").split("|")]


# The document's shorthand for the instrument's verdict strings.
TOKEN = {"PASS": "PASS", "MARGINAL": "MARG", "FAIL(noise)": "FAIL"}

# sec.13 writes verdicts out in full rather than in the four-character
# shorthand sec.3/9 use, so it needs its own map.  Two maps is not duplication:
# a check that accepted either spelling in either table would stop detecting a
# table quoting the wrong vocabulary.
TOKEN13 = {"PASS": "PASS", "MARGINAL": "MARGINAL", "FAIL(noise)": "FAIL (noise)"}

# Loaded by the far=20 glob but NOT a canonical subject -- see main().
NONCANON = "coffee-bubbles"

# The five subjects swept at 0.30-0.35 (sec.13.4).
NARROW_BANDS = ("0.25-0.30", "0.30-0.35", "0.35-0.40")


def band0_verdict(rec):
    """sec.10's band-0 conclusion, DERIVED from the three slice verdicts.

    The document states the rule in prose: NOISE means every FINE slice of
    band 0 FAILs; SIGNAL means they all PASS; anything else is mixed.  Deriving
    it here rather than reading it means the CONCLUSION is certified against the
    measurement, not against itself.
    """
    vs = [rec["bands"][b]["verdict"] for b in BAND0]
    if all(v.startswith("FAIL") for v in vs):
        return "NOISE"
    if all(v == "PASS" for v in vs):
        return "SIGNAL"
    return "mixed"


def locate(lines, key):
    """The verdict row and the CI row for `key`, found by SHAPE not by ordinal.

    SECOND DEFECT IN THIS FILE, FOUND THE SAME WAY AS THE FIRST -- BY RUNNING IT.
    The previous version took `rows[0]` and `rows[1]` of every row whose first
    cell is the subject.  That is positional, and it was only ever correct while
    the document had exactly three subject-keyed tables in a fixed order.
    Section 9.1 (a prose "why this subject is here" table) and section 10
    (band-0 verdicts) each add another row keyed by the same subject, so
    `rows[0]` silently became the PROSE row and all 50 checks for round-2
    subjects reported WRONG against a row that was never meant to carry numbers.

    Anchoring on the row's SHAPE fixes the class rather than the instance:

      verdict row : 10 cells, carries a PASS/MARG/FAIL token
      CI row      :  3 cells, carries exactly two `[`
      band-0 row  :  5 cells, carries a NOISE/mixed/SIGNAL token  (sec.10)
      ladder row  :  4 cells, carries a same/MOVED token          (sec.9.4)

    and each must match EXACTLY ONCE.  A shape that matches twice is ambiguous
    and is reported as unresolved rather than resolved to whichever came first,
    because "resolved to the first of several" is how the first defect survived.
    """
    verdict, ci, band0, ladder = [], [], [], []
    for s in rows_for(lines, key):
        cells = split_cells(s)
        if len(cells) == 10 and any(t in s for t in ("PASS", "MARG", "FAIL")):
            verdict.append(cells)
        elif len(cells) == 3 and s.count("[") == 2:
            ci.append(cells)
        elif len(cells) == 5 and any(t in s for t in ("NOISE", "mixed", "SIGNAL")):
            band0.append(cells)
        elif len(cells) == 4 and any(t in s for t in ("same", "MOVED")):
            ladder.append(cells)
    return verdict, ci, band0, ladder


def locate13(lines, key):
    """Section 13's two subject-keyed tables, again found by SHAPE.

    sec.13.4 results row : 7 cells, carries a PASS/MARGINAL/FAIL token
    sec.13.7 delta row   : 4 cells, last cell carries '%'

    The delta row's shape is checked on the '%' and not on the cell count
    alone, because sec.13.6's far-control table ALSO has four cells and is
    ALSO keyed by `dry-erase-marker-head-cpl`.  Cell count alone would make
    that subject ambiguous -- which the exactly-once rule would have caught,
    but as an UNRESOLVED rather than as a correct reading.
    """
    res, delta = [], []
    for s in rows_for(lines, key):
        cells = split_cells(s)
        if len(cells) == 7 and any(t in s for t in ("PASS", "MARGINAL", "FAIL")):
            res.append(cells)
        elif len(cells) == 4 and cells[3].endswith("%"):
            delta.append(cells)
    return res, delta


def main():
    lines = open(DOC, encoding="utf-8").read().splitlines()
    text = "\n".join(lines)
    recs_all = load("bandsweep-far20*.json", CONTROLS)
    far8 = load("bandsweep-far8*.json", CONTROLS)

    # `coffee-bubbles` is a far=20 record but is NOT a canonical subject: its
    # 19-frame stack forces the realised `far` down to 6, so it is measured on
    # a different protocol from the other eleven and sec.13.6 excludes it from
    # sec.0/7/8/10 on purpose.
    #
    # Excluding it here without checking that the DOCUMENT excludes it would be
    # defect 3 again -- a loader decision that silently disagrees with the
    # prose.  So the exclusion is asserted against the text below, and the
    # subject is still fully checked, by sec.13's own tables.
    recs = {k: v for k, v in recs_all.items() if k != NONCANON}

    # sec.13.9's `bee-1-cpl` single-subject rerun.  It is declared a CONTROL
    # above for the same reason sec.6.1's leaf control is: swept alone, it sees
    # a different bootstrap stream from the five-subject round-1 run, so its
    # CIs differ from the canonical record BY DESIGN and would otherwise shadow
    # it.  Its point estimates do not differ, and that is the real acceptance
    # condition for the re-develop -- enforced below rather than described.
    #
    # sec.13 quotes THIS record for bee (it is the only one carrying the narrow
    # bands), while sec.3/9/10 quote the canonical one.  `s13src` keeps that
    # explicit: a silent fallback to the canonical record would make sec.13's
    # bee row unverifiable and print the same green as a verified one.
    bee_narrow = load("bandsweep-far20-bee-1-cpl.json", ())["bee-1-cpl"]
    s13src = dict(recs_all)
    s13src["bee-1-cpl"] = bee_narrow

    ok = bad = unresolved = 0
    ladder_rows = band0_rows = ladder_same = 0
    res13_rows = delta13_rows = 0

    def check(desc, cell, needle):
        """`needle` must be in THIS CELL, not merely somewhere in the row.

        Row-wide `in` was the surviving remnant of the presence-test defect:
        an R quoted in the wrong band's cell, or a verdict token belonging to a
        neighbouring band, satisfied it.  A cell is the smallest unit that
        carries one claim, so it is the unit a check is pinned to.
        """
        nonlocal ok, bad
        if needle in cell:
            ok += 1
        else:
            bad += 1
            print(f"  WRONG      {desc}: expected {needle!r}, cell reads {cell!r}")

    for key, r in sorted(recs.items()):
        vrows, crows, brows, lrows = locate(lines, key)
        if len(vrows) != 1 or len(crows) != 1:
            unresolved += 11
            print(f"  UNRESOLVED {key}: need exactly 1 verdict row and 1 CI row, "
                  f"found {len(vrows)} and {len(crows)}")
            continue
        v, c = vrows[0], crows[0]

        check(f"{key} n_real", v[1], str(r["n_real"]))
        check(f"{key} step", v[2], str(r["step"]))
        check(f"{key} kept", v[3], str(r["kept"]))

        for j, b in enumerate(BANDS):
            cell, rec_b = v[4 + j], r["bands"][b]
            check(f"{key} {b} R", cell, f"{rec_b['R']:.3f}")
            # THE CONCLUSION, not the evidence.  A flipped verdict with an
            # intact number is the mutation that passed 712 green checks in
            # another lane; it is caught here because the token is derived
            # from the instrument's own verdict string.
            check(f"{key} {b} verdict", cell, TOKEN[rec_b["verdict"]])

        # THE HEADLINE.  The boundary is the single value other lanes act on,
        # and it is recomputed by the instrument that produced the record
        # rather than read back out of the document.
        check(f"{key} BOUNDARY", v[9], f"{bandsweep.boundary(r):.2f}")

        for j, b in enumerate(("0.17-0.20", "0.20-0.25")):
            rec_b = r["bands"][b]
            check(f"{key} {b} R+CI", c[1 + j],
                  f"{rec_b['R']:.3f} [{rec_b['lo']:.3f}, {rec_b['hi']:.3f}]")

        # sec.10 band-0 verdict (all eleven subjects).
        if len(brows) == 1:
            band0_rows += 1
            b0 = brows[0]
            for j, b in enumerate(BAND0):
                check(f"{key} band0 {b} R", b0[1 + j],
                      f"{r['bands'][b]['R']:.3f}")
            check(f"{key} BAND-0 VERDICT", b0[4], band0_verdict(r))
        elif len(brows) > 1:
            unresolved += 1
            print(f"  UNRESOLVED {key}: {len(brows)} band-0 rows")

        # sec.9.4 far ladder (round-2 subjects only; round 1's ladder is a
        # differently-shaped table in sec.4 and is NOT re-checked here -- that
        # is declared, not silent, and is asserted by the count below).
        if len(lrows) == 1:
            ladder_rows += 1
            L, r8 = lrows[0], far8.get(key)
            if r8 is None:
                unresolved += 1
                print(f"  UNRESOLVED {key}: ladder row with no far=8 record")
            else:
                b20, b8 = bandsweep.boundary(r), bandsweep.boundary(r8)
                check(f"{key} ladder far20", L[1], f"{b20:.2f}")
                check(f"{key} ladder far8", L[2], f"{b8:.2f}")
                check(f"{key} LADDER VERDICT", L[3],
                      "same" if b20 == b8 else "MOVED")
                if L[3] == "same":
                    ladder_same += 1
        elif len(lrows) > 1:
            unresolved += 1
            print(f"  UNRESOLVED {key}: {len(lrows)} ladder rows")

    # A check that matches nothing prints the same green as one that matches.
    # These counts are what make the derived tables non-vacuous.
    #
    # The ladder count is pinned to the DOCUMENT'S OWN SUMMARY CLAIM ("6/6
    # unchanged") rather than to a magic number or to len(far8).  len(far8) is
    # 11 because round 1 also has far=8 records, but round 1's ladder lives in
    # sec.4 in a differently-shaped six-cell table and is NOT re-checked here.
    # Pinning to the claim means the summary line cannot drift away from the
    # rows it summarises, which is the same failure the conclusion checks above
    # exist for.
    # The claim is now quoted in more than one place (sec.9.4 states it, sec.12
    # discusses it), so taking the FIRST match would be the same positional
    # mistake that produced defect 2. Every occurrence is collected and they
    # must AGREE -- the same rule the loader uses for duplicate records.
    claims = set(re.findall(r"\*\*(\d+)/(\d+) unchanged\*\*", "\n".join(lines)))
    if len(claims) != 1:
        bad += 1
        print(f"  WRONG      sec.9.4 summary claim: found {len(claims)} "
              f"distinct '**N/N unchanged**' claims {sorted(claims)}; "
              "they must agree or the document contradicts itself")
    else:
        n_same, n_tot = (int(x) for x in claims.pop())
        for label, got, want in (("ladder rows vs claimed denominator",
                                  ladder_rows, n_tot),
                                 ("ladder rows reading 'same' vs claimed",
                                  ladder_same, n_same)):
            if got == want:
                ok += 1
            else:
                bad += 1
                print(f"  WRONG      {label}: found {got}, claimed {want}")

    if band0_rows == len(recs):
        ok += 1
    else:
        bad += 1
        print(f"  WRONG      band-0 rows: found {band0_rows}, "
              f"expected {len(recs)}")

    # ------------------------------------------------------------------
    # sec.13 -- the 0.30-0.35 narrow-band measurement.
    # ------------------------------------------------------------------
    # The exclusion of `coffee-bubbles` from the canonical tables is a LOADER
    # decision above; here it is required to be a DOCUMENTED one.  If the
    # sentence goes, the check goes red even though every number is intact.
    #
    # Matched against WHITESPACE-COLLAPSED text.  The first version of this
    # check used a literal-with-spaces regex and reported the sentence missing
    # when it was present, because Markdown had wrapped it between
    # "eleven-subject" and "tables".  A prose check that cannot survive a
    # reflow is a check that will eventually fire on a document that is right.
    flat = re.sub(r"\s+", " ", text)
    if ("`coffee-bubbles` is **deliberately excluded from the canonical "
            "eleven-subject tables in §0, §7, §8 and §10.**") in flat:
        ok += 1
    else:
        bad += 1
        print("  WRONG      sec.13.6: the verifier excludes `coffee-bubbles` "
              "from the canonical tables but the document no longer says so")

    # sec.9.1's halo retraction.  This lane has never measured a halo, so this
    # is a CITATION, not a finding of ours -- and a citation is exactly the
    # shape of claim that can be reversed with every number in the document
    # left correct.  Four subjects entered sec.9 *because of* halo verdicts
    # that V-REVIEW has since shown to be artifacts of a walk that never
    # samples 120-400 px.  Restoring the old wording would re-assert a dead
    # premise and no numeric check would notice.
    #
    # Pinned on POLARITY, not presence: the negation must be there AND the
    # affirmative must not.  A presence test alone would pass a document that
    # said both, which is the sixth defect (sec.12.3) in a new costume.
    halo_neg = "**No halo is demonstrated on any of the 26 masters.**"
    halo_pos = re.search(r"\bA halo is demonstrated\b|"
                         r"\bfails the halo measurement\b", flat)
    if halo_neg in flat and halo_pos is None:
        ok += 1
    else:
        bad += 1
        print(f"  WRONG      sec.9.1: halo retraction not stated in the "
              f"retracted direction (negation present: {halo_neg in flat}, "
              f"affirmative present: {halo_pos is not None})")

    # ...and the four selection rows must carry the retraction with them.  The
    # sentence above is three paragraphs from the table; a reader scanning the
    # table alone must not be told these subjects fail a measurement that has
    # been withdrawn.
    for key in ("flat-on-ruler-cpl", "tweezers-cpl", "lavendar-cpl",
                "dry-erase-marker-head-cpl"):
        sel = [ln for ln in lines
               if ln.startswith(f"| `{key}` |") and "halo" in ln]
        if len(sel) == 1 and "retracted" in sel[0]:
            ok += 1
        else:
            bad += 1
            print(f"  WRONG      sec.9.1 selection row for {key}: expected "
                  f"exactly one halo row carrying 'retracted', found "
                  f"{len(sel)}")

    # ------------------------------------------------------------- sec.14
    # The grid is GENERATED by bandq.py, so checking it against bandq's own
    # loader would be close to tautological.  These checks read the raw JSON
    # independently instead, so bandq's loader and this verifier's reading of
    # the records have to agree cell by cell.
    #
    # The exit-code table is the check that earns its keep: other lanes are
    # wiring `bandq.py` into their own gates on the strength of that table, so
    # if the codes in the document and the codes in the code ever disagree, the
    # document silently lies to every one of them.
    import glob as _glob
    raw = {}
    for _p in sorted(_glob.glob(os.path.join(_HERE, "bandsweep*.json"))):
        for _rec in json.load(open(_p, encoding="utf-8")):
            _far = _rec.get("far_real", -1)
            for _sl, _b in _rec["bands"].items():
                raw.setdefault((_rec["key"], _sl, _far), set()).add(_b["verdict"])

    # `far` is part of a cell's identity: records sharing a far agree exactly,
    # records at different far do not and are not supposed to.  This reader
    # applies that rule INDEPENDENTLY of bandq.py rather than importing its
    # picker, so the two have to arrive at the same grid by separate routes.
    #
    # The rule, restated here on purpose: quote far=20 (the matched protocol
    # sec.3/sec.9/sec.13 all use); if a cell exists at exactly one other far,
    # quote that and expect the grid to show it; if it exists at several
    # non-20 fars, the grid must not claim a verdict.
    def canon(subject, slice_key):
        fars = sorted({f for (k, s, f) in raw if k == subject and s == slice_key})
        if not fars:
            return None
        if 20 in fars:
            vs = raw[(subject, slice_key, 20)]
        elif len(fars) == 1:
            vs = raw[(subject, slice_key, fars[0])]
        else:
            return "REFUSED"
        # `next(iter(...))`, NOT `vs.pop()`.  `raw[...]` hands back the STORED
        # set, so popping drained it: the grid loop consumed every verdict on
        # its way past, and sec.14.9's later lookup of the same cell then saw
        # an empty set and reported REFUSED for a cell that reads PASS.  A
        # check that destroys the evidence it reads will disagree with itself
        # depending on what ran first.
        return next(iter(vs)) if len(vs) == 1 else "REFUSED"

    grid_glyph = {"**PASS**": "PASS", "marg": "MARGINAL", "FAIL": "FAIL(noise)",
                  "??": "REFUSED"}
    grid_hdr = [ln for ln in lines if ln.startswith("| subject | 0.02-0.05")]
    if len(grid_hdr) != 1:
        bad += 1
        print("  WRONG      sec.14.3: need exactly one grid header, found %d"
              % len(grid_hdr))
    else:
        cols = [c.strip() for c in grid_hdr[0].strip("|").split("|")][1:]
        ncells = 0
        for ln in lines:
            if not ln.startswith("| `") or " | " not in ln:
                continue
            cells_ = [c.strip() for c in ln.strip("|").split("|")]
            if len(cells_) != len(cols) + 1:
                continue
            subj = cells_[0].strip("`")
            for col, cell in zip(cols, cells_[1:]):
                got = canon(subj, col)
                if cell == "--":
                    if got:
                        bad += 1
                        print("  WRONG      sec.14.3 %s %s: grid says "
                              "UNQUALIFIED but a record exists (%s)"
                              % (subj, col, got))
                    else:
                        ok += 1
                elif cell in grid_glyph:
                    ncells += 1
                    if got == grid_glyph[cell]:
                        ok += 1
                    else:
                        bad += 1
                        print("  WRONG      sec.14.3 %s %s: grid says %s, "
                              "records say %s" % (subj, col, cell, got))
        if ncells == 0:
            bad += 1
            print("  WRONG      sec.14.3: parsed no measured grid cells -- "
                  "the row shape changed and this check went quiet")

    # sec.14.3's count sentence, derived rather than read.
    subs14 = sorted({k for (k, _s, _f) in raw} |
                    {"109MSDCF", "bee-2-cpl", "bee-3-cpl", "chia-seeds-cpl",
                     "coffee-bean", "couch-fibers-cpl",
                     "dime-flat-narrow-slices-cpl", "duck-tape-side-layers-cpl",
                     "flower-bud-with-background-fern-cpl",
                     "flower-inner-edge-cpl", "flowers-cpl", "foam",
                     "highly-angled-ruler-mm-cpl", "lead-1-cpl",
                     "maldon-sea-salt-cpl", "medication-pill-cpl",
                     "pencil-flatter-angle-cpl", "pencil-steep-angle-cpl",
                     "pottery-art-glazed-cpl", "unpopped-popcorn-kernels-cpl",
                     "wrapped-text-1", "wrapped-text-2"})
    n_unq = sum(1 for s in subs14 if not any(k == s for (k, _s, _f) in raw))
    want14 = ("%d of %d corpus subjects have never been band-qualified at "
              "any slice." % (n_unq, len(subs14)))
    if want14 in flat:
        ok += 1
    else:
        bad += 1
        print("  WRONG      sec.14.3: expected %r" % want14)

    # sec.14.4's exit codes, checked against bandq.py's ACTUAL constants.
    #
    # The first version of this check was `if cell in text`, where cell was
    # "| 3 |".  That is defect class 1 (sec.12.3) written INTO the section
    # that documents defect class 1: "| 3 |" occurs 3 times in this document,
    # so mutating the UNQUALIFIED row to "| 2 |" was absorbed by an unrelated
    # table cell and the harness read MISSED at exit 0.  Measured, not
    # supposed -- arm s14-exit-code-table-wrong caught nothing until this was
    # rewritten.  Each code is now bound to its VERDICT NAME, must occur
    # exactly once in that pairing, and the name must not appear against any
    # other code.
    sys.path.insert(0, _HERE)
    try:
        import bandq
        codes = [("PASS", bandq.PASS), ("FAIL(noise)", bandq.FAIL),
                 ("MARGINAL", bandq.MARGINAL),
                 ("UNQUALIFIED", bandq.UNQUALIFIED),
                 ("UNKNOWN", bandq.UNKNOWN), ("REFUSED", bandq.REFUSED)]
        for name, val in codes:
            want = "| %d | `%s` |" % (val, name)
            others = [c for c in range(10)
                      if c != val and ("| %d | `%s` |" % (c, name)) in text]
            if text.count(want) == 1 and not others:
                ok += 1
            else:
                bad += 1
                print("  WRONG      sec.14.4: `%s` must be documented as exit "
                      "code %d exactly once (found %d; also seen against %s)"
                      % (name, val, text.count(want), others or "nothing"))

        # ...and the licence column, which the pairing check above does not
        # reach.  Turning UNQUALIFIED's "no" into "yes" moves no code and no
        # number and would tell every lane that a subject nobody measured is
        # licensed -- the precise error this section exists to prevent.
        polarity = [("PASS", bandq.PASS, True), ("FAIL(noise)", bandq.FAIL,
                    False), ("MARGINAL", bandq.MARGINAL, False),
                    ("UNQUALIFIED", bandq.UNQUALIFIED, False)]
        for name, val, licensed in polarity:
            m = re.search(r"^\| %d \| `%s` \| ([^|]*)\|" % (val,
                          re.escape(name)), text, re.M)
            if m is None:
                bad += 1
                print("  WRONG      sec.14.4: no licence cell for `%s`" % name)
                continue
            cell = m.group(1).strip().lower()
            got = cell.startswith("yes")
            if got == licensed and (got or cell.startswith("no")):
                ok += 1
            else:
                bad += 1
                print("  WRONG      sec.14.4: `%s` must be documented as %s a "
                      "licence; its cell reads %r"
                      % (name, "granting" if licensed else "NOT granting",
                         m.group(1).strip()))
    except ImportError as exc:
        bad += 1
        print("  WRONG      sec.14.4: cannot import bandq to check exit "
              "codes: %s" % exc)

    # sec.14.9's anti-interpolation example.  It is the ONLY concrete evidence
    # offered that refusing to interpolate is worth the cost, so if the two
    # verdicts stopped disagreeing the argument would be gone while the
    # sentence still read plausibly.
    ps_wide = canon("paper-sweep", "0.30-0.40")
    ps_narrow = canon("paper-sweep", "0.30-0.35")
    if ps_wide == "PASS" and ps_narrow == "MARGINAL":
        ok += 1
    else:
        bad += 1
        print("  WRONG      sec.14.9: the anti-interpolation example needs "
              "paper-sweep PASS at 0.30-0.40 and MARGINAL at 0.30-0.35; "
              "records say %s and %s" % (ps_wide, ps_narrow))

    # ...and the SENTENCE has to say it, in that direction.  The check above
    # certifies the records and none of the claim -- flipping the prose to
    # "MARGINAL at 0.30-0.40 and PASS at 0.30-0.35" would leave it green while
    # inverting the only concrete evidence sec.14.9 offers that refusing to
    # interpolate is worth the cost.  That is defect class 4 (sec.12.3) and it
    # was live in this section until this check was added.
    if len(re.findall(
            r"`paper-sweep` is PASS at 0\.30.0\.40 and \*\*marg\*\* at "
            r"0\.30.0\.35", flat)) == 2:
        ok += 1
    else:
        bad += 1
        print("  WRONG      sec.14.3/14.9: the anti-interpolation sentence "
              "must appear twice and must read PASS at the WIDE slice and "
              "marg at the NARROW one")

    for key in sorted(recs_all):
        r = s13src[key]
        res, delta = locate13(lines, key)
        if not res and not delta:
            continue

        if len(res) == 1:
            res13_rows += 1
            R = res[0]
            check(f"{key} s13 N", R[1], str(r["n_real"]))
            for j, b in enumerate(NARROW_BANDS):
                col = (2, 3, 5)[j]
                check(f"{key} s13 {b} R", R[col], f"{r['bands'][b]['R']:.3f}")
            nb = r["bands"]["0.30-0.35"]
            check(f"{key} s13 0.30-0.35 CI", R[4],
                  f"[{nb['lo']:.3f}, {nb['hi']:.3f}]")
            # THE CONCLUSION.  Derived from the instrument's verdict string,
            # so flipping FAIL to PASS while leaving R=1.079 in place -- the
            # mutation that four arms of this file's own harness once missed
            # at 88/88 green -- goes red here.
            check(f"{key} s13 VERDICT", R[6], TOKEN13[nb["verdict"]])
        elif len(res) > 1:
            unresolved += 1
            print(f"  UNRESOLVED {key}: {len(res)} sec.13.4 rows")

        if len(delta) == 1:
            delta13_rows += 1
            D = delta[0]
            wide, narrow = r["bands"]["0.30-0.40"]["R"], r["bands"]["0.30-0.35"]["R"]
            check(f"{key} s13.7 wide", D[1], f"{wide:.3f}")
            check(f"{key} s13.7 narrow", D[2], f"{narrow:.3f}")
            # Recomputed, not read.  A delta table is a conclusion about how
            # far the narrow band moved; quoting it back would certify it
            # against itself.
            check(f"{key} s13.7 DELTA", D[3].replace("\u2212", "-"),
                  f"{100.0 * (narrow - wide) / wide:+.1f}%")
        elif len(delta) > 1:
            unresolved += 1
            print(f"  UNRESOLVED {key}: {len(delta)} sec.13.7 rows")

    # sec.13.6's far-matched control, from its own record.
    #
    # SIXTH INSTANCE OF THE PRESENCE-TEST DEFECT, AND IT WAS WRITTEN INTO THE
    # SECTION THAT DOCUMENTS THE DEFECT.  The first version of this check was
    # `needle in text` for "**PASS**".  That token appears all over sec.13.4,
    # so flipping the far-control's own verdict to FAIL left the check green:
    # arm `s13-far-control-flipped` read MISSED at 294/294.  Caught only
    # because the arm existed.  Pinned to the row's cells now, like every
    # other conclusion in this file.
    far24 = load("bandsweep-far24*.json", CONTROLS)
    ctl = far24.get("dry-erase-marker-head-cpl")
    ctl_rows = [split_cells(ln.strip()) for ln in lines
                if ln.strip().startswith("| `--far 24`")]
    if ctl is None:
        bad += 1
        print("  WRONG      sec.13.6: no far=24 control record on disk")
    elif len(ctl_rows) != 1:
        unresolved += 2
        print(f"  UNRESOLVED sec.13.6: {len(ctl_rows)} far-control rows, need 1")
    else:
        cb, row = ctl["bands"]["0.30-0.35"], ctl_rows[0]
        check("sec.13.6 far-control R", row[2], f"{cb['R']:.3f}")
        check("sec.13.6 far-control VERDICT", row[3], TOKEN13[cb["verdict"]])

    # sec.13.5's two arithmetic claims about the CI upper bound, recomputed.
    # Counted rather than tested for presence, for the reason immediately
    # above: a claim satisfied by a duplicate of itself is not certified.
    hi = recs["112MSDCF"]["bands"]["0.30-0.35"]["hi"]
    for bar, name in ((1.5, "MARGINAL"), (2.0, "PASS")):
        needle = f"**{bar - hi:.3f} below the {name} bar**"
        if text.count(needle) == 1:
            ok += 1
        else:
            bad += 1
            print(f"  WRONG      sec.13.5 distance to {name} bar: "
                  f"{needle!r} occurs {text.count(needle)} times, need 1")

    # sec.13.9's ACCEPTANCE CONDITION for the re-developed `bee-1-cpl`, in the
    # CORRECTED form.  The pre-registered version said all 12 pre-existing
    # bands must reproduce exactly; that failed, because the CIs are
    # call-order dependent (sec.6.1).  The substantive requirement is that the
    # POINT ESTIMATES reproduce, and it is checked here rather than asserted:
    # max |dR| must be exactly 0 across all 12 pre-existing bands.
    #
    # The document's claim that the CIs DO differ is deliberately not checked.
    # It is an incidental property of the run, not a conclusion; pinning a
    # check to it would fail the day someone legitimately re-runs round 1.
    canon_bee = recs["bee-1-cpl"]
    drs = [abs(v["R"] - bee_narrow["bands"][b]["R"])
           for b, v in canon_bee["bands"].items()]
    if drs and max(drs) == 0.0:
        ok += 1
    else:
        bad += 1
        print(f"  WRONG      sec.13.9 re-develop acceptance: max |dR| = "
              f"{max(drs) if drs else 'n/a'}, must be exactly 0 over "
              f"{len(drs)} pre-existing bands")

    # ...and that the two records really are the two the document describes,
    # so the check above cannot pass by comparing a record with itself.
    if canon_bee is not bee_narrow and len(drs) == 12:
        ok += 1
    else:
        bad += 1
        print(f"  WRONG      sec.13.9: expected two distinct bee records over "
              f"12 pre-existing bands, got {len(drs)} "
              f"(same object: {canon_bee is bee_narrow})")

    # Non-vacuity: the commissioning table must have one row per swept subject
    # and every one of them must read zero.
    zero_rows = len(re.findall(r"\|\s*0 of 12\s*\|\s*exact zero\s*\|", text))
    if zero_rows == 4:
        ok += 1
    else:
        bad += 1
        print(f"  WRONG      sec.13.2 commissioning rows: found {zero_rows}, "
              "expected 4")

    for label, got, want in (("sec.13.4 result rows", res13_rows, 6),
                             ("sec.13.7 delta rows", delta13_rows, 6)):
        if got == want:
            ok += 1
        else:
            bad += 1
            print(f"  WRONG      {label}: found {got}, expected {want}")

    # The document states its own instrument counts in sec.2 and sec.12.3, and
    # BOTH went stale during sec.14 -- it still claimed 310 checks and 29 arms
    # after the real figures had moved.  A stale instrument count is not a
    # cosmetic error: it is the document overstating or understating how hard
    # its own claims have been pushed on.  So the counts are pinned to the
    # live values.  The arm and null counts come from the harness module
    # itself; the check count is compared to this run's own total, which makes
    # it a fixed point -- adding a check requires updating the number, which is
    # the intended cost.
    try:
        import commission_verify_doc as cvd
        n_arms = len(cvd.ARMS) + cvd.TOTAL_ARMS_EXTRA
        pinned = [("defect arms", n_arms,
                   r"`commission_verify_doc\.py` at (\d+) defect arms caught"),
                  ("null arms", len(cvd.NULLS),
                   r"at \d+ defect arms caught and (\d+) null arms quiet"),
                  ("sec.12.3 caught", n_arms,
                   r"two channels separately \u2014 (\d+) caught / 0 missed"),
                  ("sec.12.3 total", n_arms,
                   r"Three of the (\d+) defect arms are the \u00a79\.1")]
        for label, want, pat in pinned:
            hits = re.findall(pat, flat)
            if len(hits) == 1 and int(hits[0]) == want:
                ok += 1
            else:
                bad += 1
                print("  WRONG      %s: document says %s, harness declares %d"
                      % (label, hits or "nothing", want))
    except ImportError as exc:
        bad += 1
        print("  WRONG      cannot import commission_verify_doc to pin arm "
              "counts: %s" % exc)

    attempted = ok + bad + unresolved
    claim = re.findall(r"verify_bands_doc\.py` \((\d+) checks", flat)
    # +1 because this check is itself one of the attempted checks.
    if len(claim) == 1 and int(claim[0]) == attempted + 1:
        ok += 1
    else:
        bad += 1
        print("  WRONG      check count: document says %s, this run attempted "
              "%d" % (claim or "nothing", attempted + 1))

    attempted = ok + bad + unresolved
    print(f"\n  located-and-correct : {ok}")
    print(f"  located-and-WRONG   : {bad}")
    print(f"  unresolved          : {unresolved}")
    print(f"  ------------------------------")
    print(f"  attempted           : {attempted}   over {len(recs)} subjects "
          f"({band0_rows} band-0 rows, {ladder_rows} ladder rows)")
    return 1 if (bad or unresolved) else 0


if __name__ == "__main__":
    sys.exit(main())
