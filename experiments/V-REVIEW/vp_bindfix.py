"""Bind report.md's VERDICTS and NUMBERS to the measured baseline in vr_recheck.py.

Anchored on unique full lines; hard-errors if an anchor does not land exactly once.
Backs the file up to $TEMP first. Never `git checkout --`.
"""
import os, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "vr_recheck.py")
BK = os.path.join(os.environ.get("TEMP", tempfile.gettempdir()), "vr_recheck.py.ORIG")
shutil.copy2(TARGET, BK)
print("backup ->", BK)

src = open(TARGET, encoding="utf-8").read()


def sub(old, new, label):
    global src
    n = src.count(old)
    if n != 1:
        raise SystemExit("ANCHOR NOT UNIQUE (%s): %d occurrences" % (label, n))
    src = src.replace(old, new, 1)
    print("applied:", label)


A_OLD = 'HELD, MOVED, MISSING, NOTEX = "HELD", "MOVED", "MISSING", "NOT-EXAMINED"\n'
A_NEW = A_OLD + '''BOUND, CONTRA, UNPARSED, NOROW = "BOUND", "CONTRADICTED", "UNPARSED", "NO-ROW"

# Row: | subject | stat | master | source (max of N) | **ratio** | VERDICT | note |
ROW_RE = re.compile(
    r"^\\|\\s*([A-Za-z0-9_.-]+)\\s*\\|\\s*(blotch|chroma)\\s*\\|\\s*([0-9.]+)\\s*\\|"
    r"\\s*([0-9.]+)\\s*\\(max of (\\d+)\\)\\s*\\|\\s*\\*\\*([0-9.]+)\\*\\*\\s*\\|"
    r"\\s*([A-Z]+)\\s*\\|", re.M)
HEAD_RE = re.compile(r"\\*\\*([A-Za-z]+) ACQUIT, ([A-Za-z]+) CONVICT\\.\\*\\*")
WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
         "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "thirteen": 13}


def bind_report(base, path, tol=2e-3):
    """Check report.md's stated verdicts and numbers against the baseline.

    A verifier that re-derives numbers but never opens the report cannot detect
    a REVERSED CONCLUSION: flipping ACQUIT to CONVICT leaves every number intact
    and every such checker green. Measured on this very script -- 3 of 3
    conclusion flips MISSED -- which is why this exists. See vp_flipcommission.py.
    """
    out = {BOUND: [], CONTRA: [], UNPARSED: [], NOROW: []}
    notes = []
    if not os.path.exists(path):
        return out, ["report not found: %s" % path], None
    text = open(path, encoding="utf-8").read()
    subs = base["subjects"]
    elev = base["gate_rule"]["elevated_multiple"]

    seen = set()
    for m in ROW_RE.finditer(text):
        subj, stat, mv, sv, nsrc, ratio, verdict = m.groups()
        tag = "%s/%s" % (subj, stat)
        if subj not in subs:
            out[UNPARSED].append(tag)
            notes.append("%s: row for a subject absent from the baseline" % tag)
            continue
        seen.add(tag)
        b = subs[subj]
        bad = []
        for label, got, want in (
                ("master", float(mv), b["master"][stat]),
                ("source", float(sv), b["source_frame_max"][stat]),
                ("ratio", float(ratio), b["ratio"][stat])):
            if want and abs(got - want) / abs(want) > tol:
                bad.append("%s %s != measured %.6g" % (label, got, want))
        if int(nsrc) != b["n_source_frames_registered"]:
            bad.append("source frame count %s != %d" % (nsrc, b["n_source_frames_registered"]))
        if verdict != b["verdict"]:
            bad.append("VERDICT %s != adjudicated %s" % (verdict, b["verdict"]))
        implied = "ACQUIT" if float(ratio) <= elev else "CONVICT"
        if verdict != implied:
            bad.append("VERDICT %s contradicts the %.2fx rule on its own ratio %s"
                       % (verdict, elev, ratio))
        if bad:
            out[CONTRA].append(tag)
            notes.append("%s: %s" % (tag, "; ".join(bad)))
        else:
            out[BOUND].append(tag)

    for s, b in subs.items():
        for stat in ("blotch", "chroma"):
            if b["ratio"].get(stat) is None:
                continue
            tag = "%s/%s" % (s, stat)
            if tag not in seen and b.get("flagged_for") in (stat, "both"):
                out[NOROW].append(tag)
                notes.append("%s: adjudicated but no row states it in the report" % tag)

    hm = HEAD_RE.search(text)
    head = None
    if hm is None:
        notes.append("headline 'N ACQUIT, M CONVICT' not found -- cannot bind the count")
    else:
        acq = WORDS.get(hm.group(1).lower())
        con = WORDS.get(hm.group(2).lower())
        real_a = len({t.split("/")[0] for t in out[BOUND] + out[CONTRA]
                      if subs[t.split("/")[0]]["verdict"] == "ACQUIT"})
        real_c = len({t.split("/")[0] for t in out[BOUND] + out[CONTRA]
                      if subs[t.split("/")[0]]["verdict"] == "CONVICT"})
        head = (acq, con, real_a, real_c)
        if acq != real_a or con != real_c:
            notes.append("HEADLINE says %s ACQUIT / %s CONVICT; the baseline holds "
                         "%d / %d" % (hm.group(1), hm.group(2), real_a, real_c))
    return out, notes, head

'''

B_OLD = '    ap.add_argument("--only", default="")\n'
B_NEW = B_OLD + '    ap.add_argument("--report", default=os.path.join(HERE, "report.md"))\n'

C_OLD = '''    green = (total > 0 and n[HELD] == total)
    if green:
        print("GREEN  all %d adjudicated masters still read what report.md ruled on." % total)
        return 0
    why = []
'''
C_NEW = '''    rb, rnotes, head = bind_report(base, a.report)
    rtot = sum(len(v) for v in rb.values())
    print("")
    print("REPORT BINDING  %s  (verdicts and numbers checked against the baseline)"
          % os.path.basename(a.report))
    print("PARTITION  bound %d  contradicted %d  unparsed %d  no-row %d  = %d rows"
          % (len(rb[BOUND]), len(rb[CONTRA]), len(rb[UNPARSED]), len(rb[NOROW]), rtot))
    if head:
        print("HEADLINE   states %d ACQUIT / %d CONVICT; baseline holds %d / %d"
              % head)
    for ln in rnotes:
        print("   ! " + ln)

    report_ok = (rtot > 0 and not rb[CONTRA] and not rb[UNPARSED]
                 and not rb[NOROW] and not rnotes)
    green = (total > 0 and n[HELD] == total and report_ok)
    if green:
        print("GREEN  %d masters reproduce their adjudicated statistics AND %d report "
              "rows state the verdict the measurements support." % (total, len(rb[BOUND])))
        return 0
    why = []
    if rtot == 0:
        why.append("REPORT: no rows parsed -- a report that states nothing cannot be checked")
    if rb[CONTRA]:
        why.append("REPORT CONTRADICTS MEASUREMENT: " + ", ".join(rb[CONTRA]))
    if rb[UNPARSED]:
        why.append("REPORT UNPARSED ROWS: " + ", ".join(rb[UNPARSED]))
    if rb[NOROW]:
        why.append("ADJUDICATED BUT UNSTATED: " + ", ".join(rb[NOROW]))
    if rnotes and not (rb[CONTRA] or rb[UNPARSED] or rb[NOROW]):
        why.append("REPORT: " + "; ".join(rnotes))
'''

sub(A_OLD, A_NEW, "A: bind_report + row/headline parsers")
sub(B_OLD, B_NEW, "B: --report argument")
sub(C_OLD, C_NEW, "C: verdict incorporates the report binding")

src = src.replace("import argparse, json, os, sys, traceback",
                  "import argparse, json, os, re, sys, traceback", 1)
assert "import argparse, json, os, re, sys, traceback" in src, "re import failed"

open(TARGET, "w", encoding="utf-8", newline="\n").write(src)
print("wrote", TARGET, len(src), "chars")
