"""Verify every numeric claim in V-HEADTOHEAD2.md section 9 against the JSON
that the runs actually wrote.

Two rules learned the hard way in this lane:

  * ANCHOR each check.  A bare token like `0.371` occurs by chance elsewhere in
    a 2300-line document, so a presence test is satisfied by a duplicate and
    proves nothing.  Every check below carries a `ctx` string that must appear
    in the SAME line, so the number is pinned to its own claim site.

  * COMMISSION the verifier.  `--selftest` plants a one-character defect into a
    copy of the document and requires the checker to catch it.  An all-clear
    from an instrument with no demonstrated reach is worth nothing.
"""
import io
import json
import re
import sys

DOC = r"docs\research\V-HEADTOHEAD2.md"
JD = r"C:\dev\strehl-out\V-H2H2\rimclip"


def load(kind, subj):
    return json.load(io.open(r"%s\%s-%s.json" % (JD, kind, subj), encoding="utf-8"))


def pct(x, nd=3):
    return ("%." + str(nd) + "f") % (x * 100.0)


def build_checks():
    """(label, ctx, literal) -- literal must occur on a line containing ctx."""
    c = []
    for subj in ("113", "119"):
        r = load("rim", subj)
        f = r["instrument_floor"]
        # floors: quoted in the per-subject heading line
        c.append(("rim %s floor bright" % subj, "floor bright", pct(f["bright_residual"])))
        c.append(("rim %s floor dark" % subj, "floor bright", pct(abs(f["dark_residual"]))))
        c.append(("rim %s cut" % subj, "floor bright", "cut %g" % r["cut"]))
        for arm in ("strehl", "enfuse", "fs15-coh"):
            m = r["measured"][arm]
            lo_b, hi_b, lo_d, hi_d = m["ci"]
            row = "| %s |" % arm
            c.append(("rim %s %s n" % (subj, arm), row, "| %d |" % m["n"]))
            c.append(("rim %s %s bright" % (subj, arm), row, pct(m["bright"])))
            c.append(("rim %s %s bright lo" % (subj, arm), row, pct(lo_b)))
            c.append(("rim %s %s bright hi" % (subj, arm), row, pct(hi_b)))
            c.append(("rim %s %s dark" % (subj, arm), row, pct(m["dark"])))
            c.append(("rim %s %s dark lo" % (subj, arm), row, pct(lo_d)))
            c.append(("rim %s %s dark hi" % (subj, arm), row, pct(hi_d)))
            c.append(("rim %s %s width" % (subj, arm), row, "%.2f px" % r["widths"][arm]))
            for ax in ("bright", "dark"):
                if arm not in r["diffs"]:
                    continue  # strehl is the reference; it has no difference row
                d = r["diffs"][arm][ax]
                # the verdict rows are "| enfuse | bright | ..."
                vrow = "| %s | %s |" % (arm, ax)
                c.append(("rimdiff %s %s %s corr" % (subj, arm, ax), vrow, pct(d["corrected"])))
                c.append(("rimdiff %s %s %s lo" % (subj, arm, ax), vrow, pct(d["lo"])))
                c.append(("rimdiff %s %s %s hi" % (subj, arm, ax), vrow, pct(d["hi"])))
                c.append(("rimdiff %s %s %s bar" % (subj, arm, ax), vrow, pct(d["bar"])))
                want = "RESOLVED, comparator worse" if d["resolved"] else "UNRESOLVED"
                if d["resolved"] and d["strehl_worse"]:
                    want = "RESOLVED, STREHL WORSE"
                c.append(("rimdiff %s %s %s verdict" % (subj, arm, ax), vrow, want))

    cl = load("clip", "113")
    for arm in ("strehl", "enfuse", "fs15-coh"):
        ce = cl["ceiling"][arm]
        row = "| 113 | %s |" % arm
        c.append(("clip 113 %s ceil" % arm, row, pct(ce["at_ceiling"], 5)))
        c.append(("clip 113 %s floor" % arm, row, pct(ce["at_floor"], 5)))
    for arm in ("enfuse", "fs15-coh"):
        for ax, name in (("hi", "highlight"), ("lo", "shadow")):
            v = cl["verdict"][arm][ax]
            vrow = "| %s | %s |" % (arm, name)
            nd = 3 if abs(v["diff"] * 100) < 1 else 2
            c.append(("clipdiff %s %s" % (arm, ax), vrow, ("%." + str(nd) + "f") % (v["diff"] * 100)))
            c.append(("clipbar %s %s" % (arm, ax), vrow, ("%." + str(nd) + "f") % (v["ladder"] * 100)))
            c.append(("clipverd %s %s" % (arm, ax), vrow, "UNRESOLVED" if not v["resolved"] else "RESOLVED"))
    cl9 = load("clip", "119")
    c.append(("clip 119 strehl commissions", "ALL ARMS COMMISSIONED", ""))
    for arm in ("strehl", "enfuse", "fs15-coh"):
        ce = cl9["ceiling"][arm]
        row = "| 119 | %s |" % arm
        c.append(("clip 119 %s ceil" % arm, row, pct(ce["at_ceiling"], 5)))
        c.append(("clip 119 %s floor" % arm, row, pct(ce["at_floor"], 5)))
    return c


def section9(text):
    i = text.find("# \u00a79 Clipping and occlusion rims")
    if i < 0:
        raise SystemExit("FATAL: section 9 not found")
    return text[i:]


def run(text):
    sec = section9(text)
    lines = sec.split("\n")
    ok = bad = skip = 0
    fails = []
    for label, ctx, lit in build_checks():
        if lit == "":
            skip += 1
            continue
        hits = [ln for ln in lines if ctx in ln]
        if not hits:
            bad += 1
            fails.append("%-38s NO ANCHOR  ctx=%r" % (label, ctx))
            continue
        if any(lit in ln for ln in hits):
            ok += 1
        else:
            bad += 1
            fails.append("%-38s want %-28r in %d anchored line(s)" % (label, lit, len(hits)))
    return ok, bad, skip, fails


def main():
    text = io.open(DOC, encoding="utf-8").read()
    if "--selftest" in sys.argv:
        print("COMMISSIONING: the checker must catch planted defects.\n")
        planted = [
            ("last-digit, rim reading", "+16.745%", "+16.755%"),
            ("interval bound", "[+2.524, +3.958]", "[+2.524, +3.968]"),
            ("verdict flipped", "| fs15-coh | dark | **+3.562%**", "| fs15-coh | dark | **+3.462%**"),
            ("clip bar", "54.67 pts", "54.68 pts"),
            ("edge width", "4.46 px", "4.47 px"),
            ("n dropped", "| strehl | 1026 |", "| strehl | 1027 |"),
        ]
        base_ok, base_bad, _, _ = run(text)
        print("  clean document:            %d ok / %d bad" % (base_ok, base_bad))
        if base_bad:
            print("  ABORT: cannot commission against a document that already fails")
            return 2
        caught = 0
        for name, old, new in planted:
            if text.count(old) < 1:
                print("  %-26s MUTATION TARGET NOT FOUND %r -- HARD ERROR" % (name, old))
                return 2
            o, b, _, _ = run(text.replace(old, new, 1))
            got = "CAUGHT" if b > 0 else "MISSED"
            caught += b > 0
            print("  %-26s %s  (%d bad)" % (name, got, b))
        print("\n  %d/%d planted defects caught" % (caught, len(planted)))
        return 0 if caught == len(planted) else 1

    ok, bad, skip, fails = run(text)
    for f in fails:
        print("  FAIL " + f)
    total = ok + bad + skip
    print("\n  verified %d / ambiguous-or-textual %d / FAILED %d   (sum %d)" % (ok, skip, bad, total))
    print("  " + ("GREEN" if bad == 0 else "RED"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
