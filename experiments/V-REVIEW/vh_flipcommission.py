"""Commission vh_verify.py. Six lanes have shipped a verifier blind to a
reversed conclusion; this proves mine is not one of them, or finds out.

Arms follow ORCH's three earned lessons:
  REVERSAL  - flip a CONCLUSION while leaving every number correct -> must RED
  DELETION  - remove a finding entirely (cheaper than stating it wrongly) -> RED
  DATA      - corrupt the measurement the conclusion rests on -> must RED
  SPECIFICITY - innocuous prose edit -> must stay GREEN (noise rejected)
  NULL      - untouched -> must stay GREEN

Every mutation is anchored on a unique full string and HARD-ERRORS if it does
not land: a mutation that silently fails to apply produces a green that means
nothing.
"""
import io, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.join(HERE, "HALO-falsepositive.md")
RS = os.path.join(HERE, "HALO-residual.md")
BJ = r"D:\strehl-out\V-REVIEW\halo\blind.json"
TJ = r"D:\strehl-out\V-REVIEW\halo\trunc2.json"
TMP = tempfile.mkdtemp(prefix="vhcom_")
for f in (FP, RS, BJ, TJ):
    shutil.copy2(f, os.path.join(TMP, os.path.basename(f)))
print("backups in %s\n" % TMP)


def restore():
    for f in (FP, RS, BJ, TJ):
        shutil.copy2(os.path.join(TMP, os.path.basename(f)), f)


def run():
    r = subprocess.run([sys.executable, "vh_verify.py"], capture_output=True,
                       text=True, cwd=HERE)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def sub(path, old, new):
    t = io.open(path, encoding="utf-8").read()
    if t.count(old) != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND (%d occurrences): %.60s"
                         % (t.count(old), old))
    io.open(path, "w", newline="\n", encoding="utf-8").write(t.replace(old, new, 1))


def tmut(path):
    d = json.load(open(path))
    d["couch-fibers-cpl"]["used"] = 7   # would make a 5/7 blind walk look complete
    json.dump(d, open(path, "w"), indent=1)


def jmut(path):
    d = json.load(open(path))
    b = [x for x in d["leaf-2-cpl"] if x["lo"] == 50][0]
    b["cov"] = 0.95          # would make the sliver look isotropic
    json.dump(d, open(path, "w"), indent=1)


ARMS = [
 ("NULL         untouched", None, 0),
 ("SPECIFICITY  innocuous prose",
  lambda: sub(RS, "Three causes, not one (MEASURED, `vh_trunc2.py`):",
                  "There are three distinct causes (MEASURED, `vh_trunc2.py`):"), 0),
 ("REVERSAL     headline 'all four'",
  lambda: sub(FP, "**Answer: yes. All four.", "**Answer: no. None of them."), 1),
 ("REVERSAL     flat-on-ruler acquittal",
  lambda: sub(FP, "**`flat-on-ruler-cpl` -- FALSE POSITIVE.**",
                  "**`flat-on-ruler-cpl` -- CONFIRMED HALO.**"), 1),
 ("REVERSAL     leaf-2 acquittal",
  lambda: sub(RS, "`leaf-2-cpl` is **acquitted of halo**",
                  "`leaf-2-cpl` is **convicted of halo**"), 1),
 ("REVERSAL     commission outcome",
  lambda: sub(RS, "**COMMISSION FAILED**, and I will not present its corpus table as certified.",
                  "**COMMISSION PASSED**, and its corpus table is certified."), 1),
 ("REVERSAL     STREHL_HULL disposition",
  lambda: sub(RS, "**For V-SPEED's `STREHL_HULL`:** nothing here puts the fix back on the table.",
                  "**For V-SPEED's `STREHL_HULL`:** this puts the fix back on the table."), 1),
 ("DELETION     the NOT ENTITLED section",
  lambda: sub(RS, "**NOT ENTITLED:**", "**Further notes:**"), 1),
 ("DELETION     the 1600 DN detection floor",
  lambda: sub(RS, "| bee-1-cpl | **1600 DN** | 400 DN | 1 of 4 (at 3000 DN) |",
                  "| bee-1-cpl | (n/a) | 400 DN | 1 of 4 (at 3000 DN) |"), 1),
 ("DATA         leaf-2 coverage 44%->95%", lambda: jmut(BJ), 1),
 ("SPECIFICITY  s6 prose reword",
  lambda: sub(RS, "and agrees row-for-row with", "and matches row-for-row with"), 0),
 ("REVERSAL     s6 clean count 11->14",
  lambda: sub(RS, "| clean, full 7-band walk | **11** |",
                  "| clean, full 7-band walk | **14** |"), 1),
 ("REGRESSION   withdrawn 'clean 14' row returns",
  lambda: sub(RS, "| UNMEASURABLE, per-subject reason in section 2 | **7** |",
                  "| UNMEASURABLE, per-subject reason in section 2 | **7** |\n| clean | **14** |"), 1),
 ("DELETION     s6 residual-risk statement",
  lambda: sub(RS, "**Residual risk is 11 subjects UNSCORED**",
                  "Residual risk is a number of subjects"), 1),
 ("DATA         trunc2 blind walk 5/7->7/7", lambda: tmut(TJ), 1),
]

bad = []
for name, mut, want in ARMS:
    restore()
    if mut: mut()
    rc, out = run()
    got = 1 if rc != 0 else 0
    ok = (got == want)
    if not ok: bad.append(name)
    print("%-42s expect %-5s got %-5s  %s" % (
        name, "RED" if want else "GREEN", "RED" if got else "GREEN",
        "ok" if ok else "*** MISSED ***"))
restore()
rc, out = run()
print("\nrestored -> %s" % ("GREEN" if rc == 0 else "RED (RESTORE FAILED)"))
print("\nCOMMISSION %s   (%d/%d arms correct)" % (
    "PASSED" if not bad and rc == 0 else "FAILED", len(ARMS) - len(bad), len(ARMS)))
for b in bad: print("   MISSED: %s" % b)
sys.exit(0 if (not bad and rc == 0) else 1)
