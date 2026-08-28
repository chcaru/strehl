import io, sys

F = "vh_flipcommission.py"
t = io.open(F, encoding="utf-8").read()

# 1. add trunc2.json to the backup/restore set so a DATA arm on it is reversible
OLD_BJ = 'BJ = r"D:\\strehl-out\\V-REVIEW\\halo\\blind.json"'
NEW_BJ = ('BJ = r"D:\\strehl-out\\V-REVIEW\\halo\\blind.json"\n'
          'TJ = r"D:\\strehl-out\\V-REVIEW\\halo\\trunc2.json"')
if t.count(OLD_BJ) != 1:
    sys.exit("ANCHOR 1 NOT FOUND (%d)" % t.count(OLD_BJ))
t = t.replace(OLD_BJ, NEW_BJ, 1)

for old, new, tag in (
    ("for f in (FP, RS, BJ):\n    shutil.copy2(f, os.path.join(TMP, os.path.basename(f)))",
     "for f in (FP, RS, BJ, TJ):\n    shutil.copy2(f, os.path.join(TMP, os.path.basename(f)))", "2"),
    ("    for f in (FP, RS, BJ):\n        shutil.copy2(os.path.join(TMP, os.path.basename(f)), f)",
     "    for f in (FP, RS, BJ, TJ):\n        shutil.copy2(os.path.join(TMP, os.path.basename(f)), f)", "3"),
):
    if t.count(old) != 1:
        sys.exit("ANCHOR %s NOT FOUND (%d)" % (tag, t.count(old)))
    t = t.replace(old, new, 1)

# 2. a DATA mutator for trunc2.json
OLD_J = 'def jmut(path):'
NEW_J = '''def tmut(path):
    d = json.load(open(path))
    d["couch-fibers-cpl"]["used"] = 7   # would make a 5/7 blind walk look complete
    json.dump(d, open(path, "w"), indent=1)


def jmut(path):'''
if t.count(OLD_J) != 1:
    sys.exit("ANCHOR 4 NOT FOUND (%d)" % t.count(OLD_J))
t = t.replace(OLD_J, NEW_J, 1)

# 3. arms covering the NEW section-6 pins
OLD_ARM = ' ("DATA         leaf-2 coverage 44%->95%", lambda: jmut(BJ), 1),\n]'
NEW_ARM = ''' ("DATA         leaf-2 coverage 44%->95%", lambda: jmut(BJ), 1),
 ("SPECIFICITY  s6 prose reword",
  lambda: sub(RS, "and agrees row-for-row with", "and matches row-for-row with"), 0),
 ("REVERSAL     s6 clean count 11->14",
  lambda: sub(RS, "| clean, full 7-band walk | **11** |",
                  "| clean, full 7-band walk | **14** |"), 1),
 ("REGRESSION   withdrawn 'clean 14' row returns",
  lambda: sub(RS, "| UNMEASURABLE, per-subject reason in section 2 | **7** |",
                  "| UNMEASURABLE, per-subject reason in section 2 | **7** |\\n| clean | **14** |"), 1),
 ("DELETION     s6 residual-risk statement",
  lambda: sub(RS, "**Residual risk is 11 subjects UNSCORED**",
                  "Residual risk is a number of subjects"), 1),
 ("DATA         trunc2 blind walk 5/7->7/7", lambda: tmut(TJ), 1),
]'''
if t.count(OLD_ARM) != 1:
    sys.exit("ANCHOR 5 NOT FOUND (%d)" % t.count(OLD_ARM))
t = t.replace(OLD_ARM, NEW_ARM, 1)

io.open(F, "w", newline="\n", encoding="utf-8").write(t)
print("added 5 arms to", F)
