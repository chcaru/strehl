"""Verify section 21 of docs/research/M95-kernel.md against primary sources.

Every figure is re-derived from the artifact that produced it: the pre-fix
capture files, the post-fix JSON, the negative control's log, the source of the
gates that were repaired, git ancestry, and the filesystem. Nothing is read
from this section's own prose.

Section 21 is about a gate that could not report its findings, so this file is
held to the standard it describes: stdout is reconfigured so a codepage cannot
silence it, and a tool failure exits 2, distinct from the 1 it uses for "the
report is wrong". A missing artifact is a tool failure here, never a verdict.
"""
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
OUT = SRC.parent / "out"
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
QUAR = Path(r"C:\dev\strehl-out\ORCH-quarantine-sidecars")

ok = bad = 0


def tool_failure(msg):
    print(f"\nTOOL FAILURE  {msg}")
    print("exit 2 -- the verifier did not finish; do not read this as a subject verdict")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(2)


def _unhandled(exc_type, exc, tb):
    traceback.print_exception(exc_type, exc, tb)
    tool_failure(f"unhandled {exc_type.__name__}: {exc}")


sys.excepthook = _unhandled


def section(raw, n):
    m = re.search(rf"^## {n}\. ", raw, re.M)
    if not m:
        tool_failure(f"SECTION {n} NOT FOUND")
    rest = raw[m.end():]
    nxt = re.search(r"^## \d+\. ", rest, re.M)
    body = rest[: nxt.start()] if nxt else rest
    if len(body.splitlines()) < 40:
        tool_failure(f"SECTION {n} SUSPICIOUSLY SHORT: {len(body.splitlines())} lines")
    return body


def flatten(s):
    return re.sub(r"\s+", " ", s)


def read(p, label):
    if not p.exists():
        tool_failure(f"ARTIFACT MISSING for {label}: {p}")
    return p.read_text(encoding="utf-8")


def grab(text, pattern, label, group=1):
    """Pull a number out of a capture file. Absence is a tool failure."""
    m = re.search(pattern, text)
    if not m:
        tool_failure(f"COULD NOT RE-DERIVE {label}: pattern {pattern!r} did not match")
    return m.group(group)


def num(label, token, ctx):
    """Claim `token` appears within 300 chars of the unique anchor `ctx`.

    Three guards, each paid for by a control that had already gone green on a
    report that was wrong:

    - `ctx` must not overlap `token`. A self-anchored check only proves the
      token exists somewhere.
    - `ctx` must be unique in the section, or the window is not the one meant.
    - `token` must occur EXACTLY ONCE inside the window. Section 21's control
      mutated a table cell and the check still passed, because three lines
      below the table the same figure appeared again in prose, inside the same
      300-char window. Ambiguity is a tool failure and fires on the unmutated
      report, at authoring time, which is when it is cheap.
    """
    global ok, bad
    if ctx in token or token in ctx:
        tool_failure(f"SELF-ANCHORED CHECK {label!r}: ctx {ctx!r} overlaps token {token!r}")
    n = FLAT.count(ctx)
    if n != 1:
        tool_failure(f"ANCHOR NOT UNIQUE for {label!r} ({n} occurrences): {ctx!r}")
    i = FLAT.find(ctx)
    hay = FLAT[max(0, i - 300): i + 300]
    seen = hay.count(token)
    if seen > 1:
        tool_failure(
            f"AMBIGUOUS TOKEN for {label!r}: {token!r} occurs {seen} times near "
            f"{ctx!r}; mutating one copy would leave the other and read green"
        )
    if seen == 1:
        print(f"  ok   {label}: {token}")
        ok += 1
    else:
        print(f"  BAD  {label}: {token!r} not found near {ctx!r}")
        bad += 1


def prose(label, phrase):
    global ok, bad
    if flatten(phrase).lower() in FLAT.lower():
        print(f"  ok   {label}")
        ok += 1
    else:
        print(f"  BAD  {label}: {phrase!r}")
        bad += 1


def insrc(label, relpath, needle):
    global ok, bad
    p = ROOT / relpath
    if not p.exists():
        tool_failure(f"SOURCE MISSING for {label}: {relpath}")
    if needle in p.read_text(encoding="utf-8"):
        print(f"  ok   {label}: {relpath} contains it")
        ok += 1
    else:
        print(f"  BAD  {label}: {relpath} lacks {needle!r}")
        bad += 1


RAW = read(REPORT, "the report")
FLAT = flatten(section(RAW, 21))

PRE = read(OUT / "k18_gate702_PREFIX.txt", "pre-fix gate audit")
POST = json.loads(read(OUT / "k18_gate702.json", "post-fix gate audit"))
FPRE = read(OUT / "k18b_gates_PREFIX.txt", "pre-fix fleet check")
FPOST = json.loads(read(OUT / "k18b_gates.json", "post-fix fleet check"))
NEG = read(OUT / "negctl_s20.txt", "negative control log")
LINT = read(OUT / "lint_s21.txt", "corpus_lint capture")

print("=" * 72)
print("verify section 21 -- the gate that could not report its own findings")
print("=" * 72)

# ----------------------------------------------- 21.1 their claim, checked
print("\n-- 21.1 the orchestrator's claim, re-checked --")
anc = subprocess.run(["git", "merge-base", "--is-ancestor", "e3c01aa", "HEAD"],
                     cwd=str(ROOT), capture_output=True)
if anc.returncode == 0:
    print("  ok   e3c01aa is an ancestor of HEAD (git says so)")
    ok += 1
else:
    print(f"  BAD  e3c01aa is NOT an ancestor of HEAD (rc={anc.returncode})")
    bad += 1
prose("report states the ancestry", "e3c01aa` is an ancestor of HEAD")
insrc("corpus_lint carries the repair", "scripts/corpus_lint.py",
      '_stream.reconfigure(encoding="utf-8", errors="backslashreplace")')
num("lint markdown files", grab(LINT, r"(\d+) markdown file", "md count"),
    "rust files")
num("lint fact count", grab(LINT, r"(\d+) facts", "fact count"), "53 rust files")
if "OK" in LINT and "no violations" in LINT:
    print("  ok   pinned 21.1 lint capture says no violations")
    ok += 1
else:
    print("  BAD  pinned 21.1 lint capture does not say no violations")
    bad += 1

# ---- 21.9: the live claim is scoped to files I own, not to the whole tree ----
print("\n-- 21.9 a green linter is a claim about the tree, not about my commit --")
NOW = read(OUT / "lint_s21_now.txt", "live corpus_lint capture")
MINE = ("docs/research/M95-", "experiments/M95-")
viol = re.findall(r"^([\w./-]+\.(?:md|rs)):\d+: \[", NOW, re.M)
guilty = sorted({v for v in viol if v.startswith(MINE)})
print(f"  .. live capture lists {len(viol)} violation line(s); {len(guilty)} in files I own")
if not guilty:
    print("  ok   no violation names a path I own")
    ok += 1
else:
    print(f"  BAD  violations in my files: {guilty}")
    bad += 1
prose("the claim is scoped, not global", "no violation in any file I own")
prose("the scoping is justified", "a property of the tree at an instant, not of my commit")
prose("the unsaved run is marked", "not saved to a file")
prose("nothing depends on the unsaved run", "nothing in §21 depends on it")
prose("the earlier exit 1 stays unattributed", "remains\nunattributable")
sha, date = "82a6dbb", "2026-08-24 13:56:49 -0700"
g = subprocess.run(["git", "log", "-1", "--format=%h %ci", sha],
                   cwd=ROOT, capture_output=True, text=True)
live = g.stdout.strip()
anc2 = subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"],
                      cwd=ROOT, capture_output=True, text=True)
print(f"  .. git resolves {sha}: {live or '(none)'}  ancestor rc={anc2.returncode}")
if live.startswith(sha) and date in live and anc2.returncode == 0:
    print(f"  ok   {sha} exists at {date} and is an ancestor of HEAD")
    ok += 1
else:
    print(f"  BAD  report says {sha} {date}, git says {live!r} anc={anc2.returncode}")
    bad += 1
prose("the attribution is scoped to the runs", "at the time of those two runs")
prose("the decayed check is disclosed", "decayed **inside two minutes**")
prose("the shared tell is named", "the check consulted `now`")
num("the attributed commit", sha, "which is before both of them")
num("the attributed commit date", date, "`82a6dbb`,")
if "the ownership check can say otherwise: PASS" in read(
        OUT / "negctl_s21.txt", "section 21 negative control log"):
    print("  ok   the control's power arm passed in the capture")
    ok += 1
else:
    print("  BAD  the control's power arm did not pass in the capture")
    bad += 1
prose("the vacuous-null risk is named", "green on a capture with no violations in it at all")
prose("the power control's planted line", "planted by the power control")
prose("the power arm's numbers", "**rc=1, BAD=1**, capture")
prose("the guess is owned, not retrofitted",
      "I recorded a guess where I had no measurement")

# ------------------------------------------------------ 21.2 the exposure
print("\n-- 21.2 pre-fix exposure, re-derived from the capture --")
u_rc = grab(PRE, r"verify utf-8\s+rc=(\d+)", "utf-8 rc")
u_ch = grab(PRE, r"verify utf-8\s+rc=\d+\s+stdout=(\d+)", "utf-8 chars")
u_ok = grab(PRE, r"verify utf-8\s+rc=\d+\s+stdout=\d+\s+stderr=\d+\s+ok=(\d+)", "utf-8 ok")
c_ch = grab(PRE, r"verify cp1252\s+rc=\d+\s+stdout=(\d+)", "cp1252 chars")
c_ok = grab(PRE, r"verify cp1252\s+rc=\d+\s+stdout=\d+\s+stderr=\d+\s+ok=(\d+)", "cp1252 ok")
n_rc = grab(PRE, r"verify \(unset\)\s+rc=(\d+)", "unset rc")
n_ch = grab(PRE, r"verify \(unset\)\s+rc=\d+\s+stdout=(\d+)", "unset chars")
can_err = grab(PRE, r"canary cp1252\s+rc=\d+\s+stdout=\d+\s+stderr=(\d+)", "canary stderr")

num("utf-8 arm chars", f"| {u_ch} |", "`PYTHONIOENCODING=utf-8` | 0 |")
num("utf-8 arm ok lines", f"| {u_ok} | GREEN |", "`PYTHONIOENCODING=utf-8` | 0 |")
num("cp1252 arm chars", f"| {c_ch} | {c_ok} |", "`PYTHONIOENCODING=cp1252` | 1 |")
num("cp1252 arm ok lines", f"| {c_ok} | none |", "`PYTHONIOENCODING=cp1252` | 1 |")
num("unset arm chars", f"**{n_ch}**", "| **unset** | **1** |")
num("canary traceback bytes", can_err, "of traceback")

# The unset arm is the whole point: it must be identical to cp1252.
if (n_rc, n_ch) == (grab(PRE, r"verify cp1252\s+rc=(\d+)", "cp1252 rc"), c_ch):
    print(f"  ok   unset is identical to cp1252 (rc={n_rc}, {n_ch} chars) -- re-derived")
    ok += 1
else:
    print("  BAD  unset and cp1252 differ; the report's central claim is wrong")
    bad += 1
prose("report says unset is the default and is broken", "unset is identical to cp1252")

lost_chars = int(u_ch) - int(c_ch)
lost_ok = int(u_ok) - int(c_ok)
print(f"  .. recomputed: {u_ch} - {c_ch} = {lost_chars} chars, {u_ok} - {c_ok} = {lost_ok} ok lines")
num("characters lost", str(lost_chars), "of its own report")
num("died at check", f"{int(c_ok) + 1} of {u_ok}", "It died at check")
for tag in ("B1 = EXPOSED", "B2 = COLLIDING"):
    if tag in PRE:
        print(f"  ok   capture records {tag}")
        ok += 1
    else:
        print(f"  BAD  capture does not record {tag}")
        bad += 1
prose("B1 verdict in the report", "**B1 = EXPOSED.**")
prose("B2 verdict in the report", "**B2 = COLLIDING.**")

# --------------------------------------------------------- 21.3 the fleet
print("\n-- 21.3 fleet, re-derived from the pre-fix capture --")
f_exposed = grab(FPRE, r"(\d+) of (\d+) read-only gates are EXPOSED", "exposed count")
f_total = grab(FPRE, r"(\d+) of (\d+) read-only gates are EXPOSED", "gate count", 2)
f_lost = grab(FPRE, r"output lost across the exposed gates: (\d+)", "chars lost")
s16 = grab(FPRE, r"verify_s16\.py\s+\d+\s+\d+\s+(\d+->\d+)", "s16 lines")
s20 = grab(FPRE, r"verify_s20\.py\s+\d+\s+\d+\s+(\d+->\d+)", "s20 lines")
print(f"  .. capture: {f_exposed} of {f_total} exposed, {f_lost} chars, s16 {s16}, s20 {s20}")
num("fleet exposed", f"{f_exposed} of {f_total}", "characters of verification output lost")
num("fleet chars lost", f_lost, "characters of verification output lost")
num("s16 pre-fix lines", s16.split("->")[0] + " lines", "| `verify_s16.py` | GREEN,")
num("s16 pre-fix broken lines", "**" + s16.split("->")[1] + " lines**", "| `verify_s16.py` | GREEN,")
num("s20 pre-fix lines", s20.split("->")[0] + " lines", "| `verify_s20.py` | GREEN,")
num("s20 pre-fix broken lines", s20.split("->")[1] + " lines", "| `verify_s20.py` | GREEN,")
prose("negctls deliberately excluded", "are deliberately **not** run here")
prose("the other eight are lucky", "not safe, only lucky")

# ------------------------------------------------------------ 21.4 the B3
print("\n-- 21.4 the arm that could have withdrawn section 20 --")
if POST["B3"] != "FAILS SAFE":
    print(f"  BAD  JSON B3 = {POST['B3']}, the report claims FAILS SAFE")
    bad += 1
else:
    print("  ok   JSON B3 = FAILS SAFE")
    ok += 1
prose("B3 verdict", "**B3 = FAILS SAFE. Section 20's 5/5 stands.**")
insrc("the tightened predicate is in the control", "experiments/M95-kernel/src/negctl_s20.py",
      "if rc == 1 and bad > 0:")
num("predicate in the report", "`rc == 1 and bad > 0`", "It is now")
prose("credit is declined", "It paid a debt I had not knowingly taken out")
prose("the counterfactual is stated", "this section would be a withdrawal")
tf = [r for r in POST["tool_failure_exit_codes"]]
print(f"  .. tool-failure exit codes from the JSON: {tf}")
num("tool failure codes", str(tf), "tool-failure codes seen")

# ------------------------------------------------------- 21.5 the repair
print("\n-- 21.5 the repair, re-derived post-fix --")
insrc("verify_s20 reconfigures stdout", "experiments/M95-kernel/src/verify_s20.py",
      'sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")')
insrc("verify_s20 exits 2 on tool failure", "experiments/M95-kernel/src/verify_s20.py",
      "os._exit(2)")
insrc("verify_s20 installs the excepthook", "experiments/M95-kernel/src/verify_s20.py",
      "sys.excepthook = _unhandled")
pv = POST["verify_utf8"]
pc = POST["verify_cp1252"]
pu = POST["verify_unset"]
same = pv["rc"] == pc["rc"] == pu["rc"] and pv["stdout_chars"] == pc["stdout_chars"] == pu["stdout_chars"]
if same:
    print(f"  ok   all three arms identical post-fix (rc={pv['rc']}, {pv['stdout_chars']} chars)")
    ok += 1
else:
    print("  BAD  arms still differ post-fix")
    bad += 1
num("post-fix chars", str(pv["stdout_chars"]), "all three arms | rc=0,")
num("post-fix ok lines", str(pv["ok_lines"]) + " ok", "2377 chars,")
if POST["B1"] == "NOT EXPOSED" and POST["B4"] == "FIXED":
    print("  ok   JSON B1 = NOT EXPOSED, B4 = FIXED")
    ok += 1
else:
    print(f"  BAD  JSON B1 = {POST['B1']}, B4 = {POST['B4']}")
    bad += 1
if POST["C0"] == "PASS":
    print("  ok   the canary still breaks post-fix, so the null is not vacuous")
    ok += 1
else:
    print(f"  BAD  C0 = {POST['C0']}: the post-fix null would be vacuous")
    bad += 1
prose("the canary row is called load-bearing", "The canary row is load-bearing")

n_exp_post = sum(1 for r in FPOST if r["exposed"])
print(f"  .. post-fix fleet: {n_exp_post} of {len(FPOST)} exposed (recomputed from the JSON)")
num("post-fix fleet", f"**{n_exp_post} of {len(FPOST)} exposed**", "restored 4")
s16post = [r for r in FPOST if r["gate"].endswith("verify_s16.py")]
if s16post and s16post[0]["unset"]["verdict"] == "GREEN" and s16post[0]["unset"]["lines"] == 49:
    print("  ok   verify_s16 post-fix: 49 lines, GREEN, in the unset arm")
    ok += 1
else:
    print("  BAD  verify_s16 did not recover")
    bad += 1

neg_caught = grab(NEG, r"negative control: (\d+/\d+) planted", "negctl score")
neg_rc = grab(NEG, r"removed k17_crop\.json -> rc=(\d+)", "tool arm rc")
print(f"  .. negctl log: {neg_caught}, tool arm rc={neg_rc}")
num("negative control score", neg_caught, "under the stricter predicate")
num("tool arm exit code", f"rc={neg_rc}", "tool arm")
if "scored MISSED" in NEG and "distinct: PASS" in NEG:
    print("  ok   negctl log records MISSED and PASS on the tool arm")
    ok += 1
else:
    print("  BAD  negctl log does not record the tool arm passing")
    bad += 1
num("gates patched", "12 patched", "rolling back from memory on failure")

# ------------------------------------------------- 21.6 the two RED gates
print("\n-- 21.6 the two RED gates --")
mt = sorted(datetime.fromtimestamp(f.stat().st_mtime) for f in QUAR.glob("*coffee-bean*"))
if not mt:
    tool_failure("no quarantined coffee-bean files on disk; cannot re-derive the span")
lo, hi = mt[0].strftime("%H:%M:%S"), mt[-1].strftime("%H:%M:%S")
print(f"  .. filesystem: {len(mt)} files, span {lo} to {hi}")
num("mtime span start", lo, "records the mtime span,")
num("mtime span end", hi, "which is the same observation in a form")
prose("the decayed claim is named", "an age is a function of `now`")
prose("the gate was right", "and the gate went RED")
num("the decayed reading", "220 to 290", "Read again four hours later it is")
num("the original decayed claim", "187 to 256", "Section 19 said")
insrc("verify_s19 no longer decays", "experiments/M95-kernel/src/verify_s19.py",
      "does not decay")
insrc("verify_report anchors on the row", "experiments/M95-kernel/src/verify_report.py",
      "ctx=row")
prose("neither failure was a wrong number", "neither failure was a wrong number")
prose("the retroactive mechanism is named",
      "appending a section can retroactively blunt a discriminator")
prose("verifiers rot", "Verifiers rot.")

# ------------------------------------------------------- 21.7 the limits
print("\n-- 21.7 what is not claimed --")
prose("no number is claimed wrong", "I have **not** shown that any number I have reported is wrong")
prose("the defect destroyed, did not fabricate",
      "destroyed output, it did not fabricate it")
prose("the residual is stated", "only\n`verify_s20.py` and `negctl_s20.py` have the distinct tool-failure exit code")

# ------------------------------------------------- 21.8 the control itself
print("\n-- 21.8 the negative control, re-derived from its own captures --")
NEG21 = read(OUT / "negctl_s21.txt", "section 21 negative control log")
FIRST = read(OUT / "negctl_s21_FIRST.txt", "the replayed first run")
final_score = grab(NEG21, r"negative control: (\d+/\d+) planted", "final score")
first_score = grab(FIRST, r"negative control: (\d+/\d+) planted", "first-run score")
n_planted = len(re.findall(r"^\s+(?:CAUGHT|MISSED)\s", NEG21, re.M))
print(f"  .. final {final_score} over {n_planted} planted defects, replayed first run {first_score}")
prose("planted count stated in words", "plants seven defects")
if n_planted == 7:
    print(f"  ok   the log shows {n_planted} planted arms, matching that wording")
    ok += 1
else:
    print(f"  BAD  the log shows {n_planted} planted arms, the report says seven")
    bad += 1
num("first-run score", first_score.split("/")[0], "**On its first run it caught")
num("final score", f"**{final_score} caught**", "After both repairs:")
if final_score.split("/")[0] == final_score.split("/")[1] == str(n_planted):
    print(f"  ok   every planted defect is caught in the final run ({final_score})")
    ok += 1
else:
    print(f"  BAD  final run is not clean: {final_score} of {n_planted}")
    bad += 1
n_missed_first = len(re.findall(r"^\s+MISSED\s+(?!.*tool)", FIRST, re.M))
print(f"  .. MISSED arms in the replayed first run: {n_missed_first}")
if n_missed_first == 2:
    print("  ok   the replay reproduces exactly two misses")
    ok += 1
else:
    print(f"  BAD  the replay shows {n_missed_first} misses, the report says two")
    bad += 1
if "restored byte-identical: True" in FIRST:
    print("  ok   the replay restored the report byte-identically")
    ok += 1
else:
    print("  BAD  the replay did not restore the report")
    bad += 1
insrc("the replay hard-errors on a missed anchor",
      "experiments/M95-kernel/src/k18d_replay_first.py", "ANCHOR DID NOT LAND")
insrc("the ambiguity guard is live", "experiments/M95-kernel/src/verify_s21.py",
      "AMBIGUOUS TOKEN")
prose("the self-count exclusion is reasoned",
      "a verifier that checks how many checks it ran")
prose("the four failure modes are counted", "That makes four distinct ways")
prose("the accumulated rule", "must not be any other checked value")
prose("the incidental difference is disclosed",
      "The incidental BAD counts differ slightly from the")

print("\n" + "=" * 72)
print(f"{ok} checks passed, {bad} failed  ->  {'GREEN' if bad == 0 else 'RED'}")
print("END OF VERIFIER -- reaching this line is part of the contract (exit 0 or 1)")
sys.exit(1 if bad else 0)
