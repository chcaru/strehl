"""Re-derive every number in RESULT.md section 6.5 from the measurement records.

Section 6.5 names the four subjects where merge-attributable band excess is not
covered by the bounded detail gain -- the only genuine regression candidates in
the corpus, and the rows ORCH said it will act on. Numbers typed into prose are
where this lane has made every one of its transcription errors, so none of them
is trusted here: each is recomputed from `report\\null.json`, the per-subject
`ratio\\<subject>.json` records and `report\\table.txt`, then matched against
the document.

Two defects this checker is built to avoid, both found the hard way in
vn_verify23.py's own commissioning:

  * a bare presence test is satisfied by a DUPLICATE of the value elsewhere in
    the file, so every check is anchored within `NEAR` characters of a phrase
    unique to its own row;
  * a `beat` column was misread as an admitted-frame count while writing 6.5,
    so frames-registered and stack-depth are re-read from the records rather
    than from the section 3 table they were transcribed out of.

  python vn_verify65.py     # rc=0 iff every claim re-derives
"""
import json
import os
import re
import sys

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RESULT.md")
REP = r"C:\dev\strehl-out\V-NEVERWORSE"
NEAR = 200          # a claim must sit this close to its own anchor
WARP = 0.82         # the conservative warp correction applied to relhf
SUBJECTS = ["bee-2-cpl", "flowers-cpl", "coffee-bubbles", "coffee-bean"]

fails = []
checked = 0


def section(text, start, end):
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


def _flat(s):
    """Collapse whitespace runs so a claim can span a line break.

    Prose in this document is hard-wrapped, so an anchor phrase or a bolded
    value routinely straddles a newline and a raw substring search reports a
    false ANCHOR MISSING.
    """
    return re.sub(r"\s+", " ", s)


def claim(body, anchor, value, what):
    """Assert `value` appears within NEAR chars of `anchor`, which must exist."""
    global checked
    checked += 1
    body, anchor, value = _flat(body), _flat(anchor), _flat(value)
    if anchor not in body:
        fails.append("%-34s ANCHOR MISSING: %r" % (what, anchor))
        return
    ok = False
    for m in re.finditer(re.escape(anchor), body):
        lo = max(0, m.start() - NEAR)
        if value in body[lo:m.end() + NEAR]:
            ok = True
            break
    if not ok:
        fails.append("%-34s expected %s near %r" % (what, value, anchor))


def cell(row, value, what):
    """Assert `value` appears in this subject's own table ROW.

    Anchoring a table-cell claim on the subject name and a proximity window is
    not enough: negative-control plant 8 mutated the +8% cell of
    `coffee-bubbles` and the check stayed green, because the same "+8%" also
    appears in the prose paragraph a hundred characters away. A cell claim is
    checked against the cell's own line and nothing else.
    """
    global checked
    checked += 1
    if value not in row:
        fails.append("%-34s expected %s in its own table row" % (what, value))


def main():
    global checked
    with open(DOC, encoding="utf-8") as f:
        doc = f.read()
    body = section(doc, "## 6.5 The four unadjudicated subjects",
                   "## 6.6 For the owner's README")

    with open(os.path.join(REP, "report", "null.json"), encoding="utf-8") as f:
        nul = json.load(f)
    with open(os.path.join(REP, "report", "table.txt"), encoding="utf-8") as f:
        table = f.read()

    # the section must name exactly these four subjects and no others
    named = set(re.findall(r"`([a-z0-9][a-z0-9-]+)`", body))
    named = {s for s in named if s in nul}
    if named != set(SUBJECTS):
        fails.append("subject set: doc names %s, expected %s"
                     % (sorted(named), sorted(SUBJECTS)))

    depths, samps, adms = [], [], []
    for s in SUBJECTS:
        b = nul[s]["blotch"]
        with open(os.path.join(REP, "ratio", "%s.json" % s),
                  encoding="utf-8") as f:
            r = json.load(f)

        excess = b["vs_min"] / b["loo_med"]
        bound = b["relhf_ratio"] * WARP
        over = excess / bound

        # cross-check: the recorded excess must equal the re-derived one
        if abs(excess - b["excess"]) > 5e-4:
            fails.append("%-34s recomputed excess %.4f != recorded %.4f"
                         % (s, excess, b["excess"]))
        checked += 1

        docrow = [ln for ln in body.splitlines()
                  if ln.startswith("| `%s` |" % s)]
        if len(docrow) != 1:
            fails.append("%-34s has %d table rows in 6.5, need 1"
                         % (s, len(docrow)))
            continue
        docrow = docrow[0]

        cell(docrow, "%.4fx" % r["ratio_blotch"]["vs_min"], "%s blotch/min" % s)
        cell(docrow, "%.4fx" % r["ratio_band"]["vs_min"], "%s band/min" % s)
        cell(docrow, "%.3f" % excess, "%s excess" % s)
        cell(docrow, "%.3f" % bound, "%s detail bound" % s)
        cell(docrow, "+%d%%" % round((over - 1) * 100), "%s over bound" % s)

        # absolute blotch comes from the gate, via the section 3 transcript
        row = [ln for ln in table.splitlines() if ln.startswith(s + " ")]
        if not row:
            fails.append("%-34s no row in table.txt" % s)
        else:
            cell(docrow, row[0].split()[1], "%s absBlot" % s)

        n_samp = r["n_asked"]              # frames rendered for the source arm
        n_adm = r["admit"]["blotch"]["ok"]  # survived registration + admission
        depth = r["n_total"]                # full stack depth on disk
        # cross-check the three against the section 3 transcript's n and N
        if row:
            cols = row[0].split("|")[-2].split()
            if (int(cols[-2]), int(cols[-1])) != (n_adm, depth):
                fails.append("%-34s table.txt says n=%s N=%s, records say "
                             "admitted=%d depth=%d"
                             % (s, cols[-2], cols[-1], n_adm, depth))
            checked += 1
        cell(docrow, "%d / %d / %d" % (n_samp, n_adm, depth),
             "%s samp/adm/depth" % s)
        samps.append(n_samp)
        adms.append(n_adm)
        depths.append(depth)

        if s == "coffee-bubbles":
            if not (n_samp == n_adm == depth == 19):
                fails.append("coffee-bubbles: samp=%d adm=%d depth=%d, doc "
                             "says all 19 sampled and admitted"
                             % (n_samp, n_adm, depth))
            checked += 1

    # the prose ranges over the three deep stacks must bracket the real values
    deep = [(a, d) for a, d in zip(adms, depths) if d > 50]
    if len(deep) != 3:
        # A missing subject row must be REPORTED, not crash the checker on an
        # index. The negative control caught exactly this: substituting a
        # subject in the table raised IndexError here, the FAILED: block was
        # never printed, and the control read the crash as a pass.
        fails.append("expected 3 deep stacks among the 4 subjects, found %d; "
                     "prose range checks skipped" % len(deep))
        checked += 1
    else:
        claim(body, "it still shows", "+%d%%"
              % round((nul["coffee-bubbles"]["blotch"]["vs_min"]
                       / nul["coffee-bubbles"]["blotch"]["loo_med"]
                       / (nul["coffee-bubbles"]["blotch"]["relhf_ratio"] * WARP)
                       - 1) * 100), "bubbles prose pct")
        claim(body, "at most", "**21 frames per stack**", "sample cap")
        claim(body, "admitted only", "**%d, %d and %d**"
              % (deep[0][0], deep[1][0], deep[2][0]), "deep admitted")
        claim(body, "stacks of", "%d, %d and %d"
              % (deep[0][1], deep[1][1], deep[2][1]), "deep depths")
        claim(body, "minimum over", "%d to %d draws"
              % (min(a for a, _ in deep), max(a for a, _ in deep)),
              "deep admitted range")
        claim(body, "standing in for", "%d to %d"
              % (min(d for _, d in deep), max(d for _, d in deep)),
              "deep depth range")
    if any(s != 21 for s in samps if s != 19):
        fails.append("sample cap is not 21 on the deep stacks: %s" % samps)
    checked += 1

    # 20 of 24 / 4 of 24 must agree with section 5.2's own partition
    s52 = section(doc, "### 5.2 Bounding the innocent", "## 6. VERDICT")
    rows = re.findall(r"^\| `[^`]+` \| ([\d.]+) \| ([\d.]+) \| \*{0,2}([\d.]+)",
                      s52, re.M)
    exceed = [r for r in rows if float(r[2]) > 1.0]
    checked += 1
    if len(exceed) != 4:
        fails.append("5.2 lists %d subjects over the bound, 6.5 names 4"
                     % len(exceed))

    print("%d claims checked over %d subjects\n" % (checked, len(SUBJECTS)))
    if fails:
        print("FAILED:")
        for f in fails:
            print("  " + f)
        return 1
    print("all section 6.5 numbers re-derive from the records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
