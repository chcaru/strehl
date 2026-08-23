"""M59 power probe: prove every corpus_lint check can fail.

A check that has never been seen to fail has not been tested (AGENTS rule 36,
SYNTHESIS discipline 351). For each check this harness:

  1. builds a probe root on which that check is CLEAN (negative control),
  2. plants exactly one violation,
  3. runs `scripts/corpus_lint.py --root <probe> --only <ID>`,
  4. asserts exit code 1, asserts the output names *that* check, and asserts
     there is no traceback -- a red exit code is not evidence of the red you
     wanted (discipline 351).

The probe root is a copy of `SYNTHESIS.md` with the three S2 blank lines
removed, plus `AGENTS.md` and one small Rust file, so the control is clean for
every check. Nothing under `docs/` or `crates/` is written.

Run:  python experiments/M59-corpus-linter/power_probe.py
"""
import io
import os
import re
import shutil
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PROBE = os.path.join(HERE, ".probe")
LINT = os.path.join("scripts", "corpus_lint.py")
SYN_REL = "docs/research/SYNTHESIS.md"

RUST = """//! Probe crate. Cites SYNTHESIS so the citation check has something to read.
//! The gate constant is discussed in fact 500 and question 126.
pub const K: f32 = 1.815;
"""


def read(path):
    with io.open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def write(path, text):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def rmtree(path):
    """Git makes loose objects read-only; Windows refuses to unlink those."""
    def onerror(func, p, exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    if os.path.isdir(path):
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=lambda f, p, e: onerror(f, p, e))
        else:
            shutil.rmtree(path, onerror=onerror)


def build_probe():
    rmtree(PROBE)
    syn = read(os.path.join(ROOT, SYN_REL)).replace("\r\n", "\n")
    lines = syn.split("\n")
    # repair S2 so the control is clean: drop blank lines between two pipe-rows
    keep = [l for i, l in enumerate(lines)
            if not (l.strip() == "" and 0 < i < len(lines) - 1
                    and lines[i - 1].startswith("|") and lines[i + 1].startswith("|"))]
    write(os.path.join(PROBE, SYN_REL), "\n".join(keep))
    write(os.path.join(PROBE, "AGENTS.md"),
          read(os.path.join(ROOT, "AGENTS.md")).replace("\r\n", "\n"))
    write(os.path.join(PROBE, "crates", "strehl-probe", "src", "lib.rs"), RUST)
    git(["init", "-q"])


GIT_CFG = ["-c", "core.autocrlf=false", "-c", "core.safecrlf=false",
           "-c", "user.name=probe", "-c", "user.email=probe@localhost"]


def git(args):
    return subprocess.run(["git"] + GIT_CFG + args, cwd=PROBE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def stage():
    """S3's CR half and all of S4 are judged on the committed blob, not on disk
    (see corpus_lint.git_index_eol), so the probe must have a real index. This
    stages verbatim -- autocrlf off -- so a planted CRLF survives into it."""
    git(["add", "--", "docs", "AGENTS.md", "crates"])


def run(only=None):
    stage()
    cmd = [sys.executable, LINT, "--root", os.path.relpath(PROBE, ROOT)]
    if only:
        cmd += ["--only", only]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# --------------------------------------------------------------------------
# plants: each returns a short description; each mutates the probe root
# --------------------------------------------------------------------------

def syn_lines():
    return read(os.path.join(PROBE, SYN_REL)).split("\n")


def syn_write(lines):
    write(os.path.join(PROBE, SYN_REL), "\n".join(lines))


def first_fact_row(lines):
    s = next(i for i, l in enumerate(lines) if l.startswith("## 4. "))
    return next(i for i in range(s, len(lines)) if re.match(r"^\|\s*\d+\s*\|", lines[i]))


def section_start(lines, n):
    return next(i for i, l in enumerate(lines) if l.startswith("## %d. " % n))


def plant_s1_over():
    ls = syn_lines()
    i = first_fact_row(ls)
    ls[i] = ls[i] + " gain |grad| over the ROI |"
    syn_write(ls)
    return "line %d: unescaped |grad| appended to a fact row" % (i + 1)


def plant_s1_under():
    ls = syn_lines()
    i = first_fact_row(ls) + 3
    ls[i] = ls[i].rstrip()[:-1].rstrip()          # drop the closing pipe
    syn_write(ls)
    return "line %d: closing pipe removed from a fact row" % (i + 1)


def plant_s2():
    ls = syn_lines()
    i = first_fact_row(ls) + 5
    ls.insert(i, "")
    syn_write(ls)
    return "line %d: blank line inserted between two fact rows" % (i + 1)


def plant_s3_eof():
    p = os.path.join(PROBE, SYN_REL)
    write(p, read(p).rstrip("\n"))
    return "trailing newline stripped (rule 37's \\Z bug)"


def plant_s3_crlf():
    p = os.path.join(PROBE, SYN_REL)
    write(p, read(p).replace("\n", "\r\n"))
    return "SYNTHESIS.md committed wholesale as CRLF"


def plant_s4():
    p = os.path.join(PROBE, "AGENTS.md")
    t = read(p).split("\n")
    for k in (10, 11, 12):
        t[k] = t[k] + "\r"
    write(p, "\n".join(t))
    return "AGENTS.md committed with three CRLF lines among LF ones"


def plant_n1_fact():
    ls = syn_lines()
    i = first_fact_row(ls)
    ls.insert(i + 2, ls[i])
    syn_write(ls)
    return "line %d: fact row 1 duplicated" % (i + 3)


def plant_n1_discipline():
    ls = syn_lines()
    s = section_start(ls, 5)
    j = next(i for i in range(s, len(ls)) if re.match(r"^\d+\. ", ls[i]))
    num = re.match(r"^(\d+)\. ", ls[j]).group(1)
    e = section_start(ls, 6)
    ls.insert(e - 1, "%s. **A second item claiming the same number.**" % num)
    syn_write(ls)
    return "line %d: discipline %s declared twice" % (e, num)


def plant_n2_item_in_4():
    ls = syn_lines()
    i = first_fact_row(ls)
    ls.insert(i + 4, "9991. **A question that landed in the fact section.**")
    syn_write(ls)
    return "line %d: numbered list item inside §4" % (i + 5)


def plant_n2_row_outside_4():
    ls = syn_lines()
    e = section_start(ls, 6)
    ls.insert(e + 2, "| 9992 | A fact row in §6 | Consequence | Orchestrator (MEASURED) |")
    syn_write(ls)
    return "line %d: four-column `| N |` row in §6" % (e + 3)


def plant_n4():
    ls = syn_lines()
    i = first_fact_row(ls)
    ls.insert(i + 1, "| 57 | A fold into a block §4 calls unallocated | Consequence | "
                     "Orchestrator (MEASURED) |")
    syn_write(ls)
    return "line %d: fact 57 folded into the declared-unallocated 55-59 block" % (i + 2)


def plant_c1_dangling():
    ls = syn_lines()
    e = section_start(ls, 6)
    ls.insert(e + 2, "This design rests on fact 9994, which does not exist.")
    syn_write(ls)
    return "line %d: reference to a nonexistent fact 9994" % (e + 3)


def plant_c1_wrong_namespace():
    ls = syn_lines()
    e = section_start(ls, 6)
    ls.insert(e + 2, "As discipline 694 records, the pipe count must be checked globally.")
    syn_write(ls)
    return "line %d: `discipline 694` where 694 is a fact" % (e + 3)


def plant_c1_rust():
    p = os.path.join(PROBE, "crates", "strehl-probe", "src", "lib.rs")
    write(p, read(p) + "\n// Calibrated per fact 9995 and question 9996.\n")
    return "crates/strehl-probe/src/lib.rs: citations to fact 9995 / question 9996"


def plant_a1():
    ls = syn_lines()
    i = first_fact_row(ls)
    ls.insert(i + 1, "| 9997 | **Pairing is a normalisation** (closes question 119). "
                     "A clean result. | The idea is settled. | M-probe (MEASURED) |")
    syn_write(ls)
    return "line %d: a row claiming to close question 119, which §10 marks REOPENED" % (i + 2)


def plant_a2():
    """Restore fact 725's ORIGINAL defective wording. This is the historical
    defect question 178 names, replayed."""
    ls = syn_lines()
    for i, l in enumerate(ls):
        if l.startswith("| 725 |") and "8 of 515" in l:
            ls[i] = l.replace("8 of 515", "7 of 515")
            syn_write(ls)
            return "line %d: fact 725 reverted to its original \"7 of 515\"" % (i + 1)
    return None


PLANTS = [
    ("S1", "over-count (fact 694's mechanism)", plant_s1_over, "DISCARDED"),
    ("S1", "under-count against the table's mode", plant_s1_under, "missing a cell"),
    ("S2", "blank line inside a table", plant_s2, "blank line inside a table"),
    ("S3", "trailing newline stripped", plant_s3_eof, "does not end in a newline"),
    ("S3", "SYNTHESIS committed as CRLF", plant_s3_crlf, "committed with CRLF"),
    ("S4", "mixed line endings in the committed blob", plant_s4, "MIXED line endings"),
    ("N1", "duplicate fact number", plant_n1_fact, "is already declared"),
    ("N1", "duplicate discipline number", plant_n1_discipline, "is already declared"),
    ("N2", "list item inside §4", plant_n2_item_in_4, "numbered list item inside"),
    ("N2", "fact row outside §4", plant_n2_row_outside_4, "outside"),
    ("N4", "fold into a declared-unallocated block", plant_n4, "unallocated"),
    ("C1", "dangling fact number", plant_c1_dangling, "9994"),
    ("C1", "right number, wrong namespace", plant_c1_wrong_namespace, "exists as fact"),
    ("C1", "dangling citation in Rust source", plant_c1_rust, "9995"),
    ("A1", "closes a REOPENED question", plant_a1, "REOPENED"),
    ("A2", "fact 725's original 7-versus-8", plant_a2, "count and the list disagree"),
]


def count_for(output, check):
    return len(re.findall(r"\[%s\]" % check, output))


def main():
    print("M59 power probe — every check must be SEEN to fail")
    print("repo root: %s" % ROOT)
    print("")

    build_probe()
    rc, out = run()
    base = count_for(out, "")
    print("NEGATIVE CONTROL (whole probe root, all checks): exit=%d" % rc)
    tail = [l for l in out.split("\n") if l.startswith("corpus_lint:")]
    for l in tail:
        print("   " + l)
    if rc != 0:
        print("   !! control is NOT clean; per-check controls below still apply")
        for l in out.split("\n"):
            if re.search(r"\[[A-Z]\d\]", l):
                print("   " + l)
    print("")

    results = []
    for check, name, plant, needle in PLANTS:
        build_probe()
        rc0, out0 = run(check)
        n0 = count_for(out0, check)
        desc = plant()
        rc1, out1 = run(check)
        n1 = count_for(out1, check)
        crashed = "Traceback" in out1 or rc1 == 2
        # the exact violation lines this check emitted
        fired = [l for l in out1.split("\n") if ("[%s]" % check) in l]
        ok = (rc0 == 0 and n0 == 0 and rc1 == 1 and n1 >= 1
              and not crashed and any(needle in l for l in fired))
        results.append((check, name, rc0, n0, rc1, n1, ok, desc, fired[:1]))

    print("%-4s %-42s %-14s %-14s %s" % ("ID", "plant", "control", "planted", "verdict"))
    print("-" * 100)
    for check, name, rc0, n0, rc1, n1, ok, desc, fired in results:
        print("%-4s %-42s exit=%d n=%-6d exit=%d n=%-6d %s"
              % (check, name[:42], rc0, n0, rc1, n1, "POWER PROVEN" if ok else "** FAILED **"))
        print("      plant: %s" % desc)
        for f in fired:
            print("      fired: %s" % f.strip()[:150])
    print("")
    bad = [r for r in results if not r[6]]
    print("%d of %d plants proved power; %d failed" % (len(results) - len(bad), len(results), len(bad)))

    # --- advisories: never fail the build, but must still be seen to emit ---
    print("")
    print("--- advisory power (heuristics; --advisory never changes the exit code) ---")
    build_probe()
    rc, out = run("S1")           # S1 only, so nothing else can fire
    env = dict(os.environ, PYTHONIOENCODING="utf-8")

    def adv_run():
        p = subprocess.run([sys.executable, LINT, "--root", os.path.relpath(PROBE, ROOT),
                            "--only", "S1", "--advisory"],
                           cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    rc0, out0 = adv_run()
    n3_0, a3_0 = count_for(out0, "N3"), count_for(out0, "A3")
    ls = syn_lines()
    e = section_start(ls, 6)
    ls.insert(e - 1, "9993. **Should the gate be solved rather than chosen?** A "
                     "discipline phrased as an open question.")
    syn_write(ls)
    rc1, out1 = adv_run()
    n3_1 = count_for(out1, "N3")
    print("N3  control n=%d, planted n=%d, exit stayed %d->%d  %s"
          % (n3_0, n3_1, rc0, rc1,
             "POWER PROVEN" if (n3_1 > n3_0 and rc1 == rc0 == 0) else "** FAILED **"))
    for l in out1.split("\n"):
        if "[N3]" in l:
            print("      fired: %s" % l.strip()[:150])
            break
    print("A3  emits n=%d on the unmodified probe root (seen to fire without a plant)"
          % a3_0)

    # --- A2's negative control, stated explicitly ---
    print("")
    print("--- A2 negative control (the check that must NOT fire constantly) ---")
    build_probe()
    rc, out = run("A2")
    print("repaired corpus, fact 725 reading \"8 of 515\": exit=%d, A2 n=%d  %s"
          % (rc, count_for(out, "A2"),
             "SILENT as required" if count_for(out, "A2") == 0 else "** FALSE POSITIVE **"))

    # --- tokenizer probe: fact 763's word-boundary property, directly ---
    print("")
    print("--- fact 763's substring bug, tested directly on the tokenizer ---")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import corpus_lint as CL

    class FakeDoc(object):
        def __init__(self, text):
            self.text = text
            self.lines = text.split("\n")

    sample = "All five sites cite M25 fact 200, and :92 cites fact 200a."
    toks = list(CL.iter_citations(FakeDoc(sample)))
    print("input: %s" % sample)
    for kind, num, off, raw, klass in toks:
        print("   %-9s %-6d %-22r class=%s" % (kind, num, raw, klass))
    naive = len(re.findall(r"fact 200", sample))
    exact = sum(1 for t in toks if t[1] == 200 and t[4] != "sub")
    print("naive substring `fact 200` matches: %d" % naive)
    print("tokenizer references to fact 200:   %d   (200a classified '%s')"
          % (exact, [t[4] for t in toks if t[3].endswith("a")][0]))
    print("fact 763's over-count %s"
          % ("REPRODUCED by the naive matcher and AVOIDED by the tokenizer"
             if naive > exact else "NOT reproduced -- probe is vacuous"))

    rmtree(PROBE)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
