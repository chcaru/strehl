"""commission_entry.py -- commission verify_bandqual.py THROUGH ITS SHIPPED ENTRY POINT.

ORCH, after six lanes found their own verifiers blind to a reversed conclusion:
  * "An inert plant and a dead instrument give the identical green. Commission the
     pass/fail channel per verifier: clean -> 0, planted digit -> non-zero,
     innocuous prose -> 0."
  * "Commissioning sensitivity is not commissioning specificity. Plant noise too."
  * "Commission DELETION as well as reversal. Deleting a finding is cheaper than
     stating it wrongly."

My earlier commissioning called failing() in-process and only ever REVERSED claims. This
runs the real script as a subprocess and reads its PROCESS EXIT CODE, over three arms:

  CLEAN      unmodified            -> must exit 0
  DELETION   a finding removed     -> must exit non-zero   (sensitivity to omission)
  INNOCUOUS  prose that asserts    -> must exit 0          (specificity: no false alarm)
             nothing new

Mutated copies go to TEMP. The tracked document is never written to, and nothing is
reverted with `git checkout --`.
"""
import io, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"C:\dev\blog\death-of-software\projects\strehl"
DOC  = "docs/research/V-SOFTCHECK-bandqual.md"
SCRIPT = os.path.join(HERE, "verify_bandqual.py")

def head_text():
    r = subprocess.run(["git", "show", "HEAD:" + DOC], capture_output=True, cwd=REPO)
    if r.returncode: sys.exit("git show failed")
    return r.stdout.decode("utf-8")

def cut(text, phrase):
    """Delete a finding. Hard-errors if the phrase is absent -- a deletion that deletes
    nothing is an inert plant, and an inert plant is indistinguishable from a dead
    instrument, which is the exact failure being commissioned against."""
    pat = re.compile(r"\s+".join(re.escape(t) for t in phrase.split()))
    if not pat.search(text):
        sys.exit("DELETION TARGET NOT FOUND (inert plant): %r" % phrase[:70])
    return pat.sub("", text, count=1)

def add(text, phrase, where="end"):
    return text + "\n\n" + phrase + "\n"

DELETIONS = [
 ("headline verdict",        "**Verdict: PARTIAL WITHDRAWAL.**"),
 ("section 4 withdrawal",    "-- 17.8% and 18.8% softer -- are withdrawn as resolution"),
 ("lower-bound qualifier",   "**the surviving deficits in section 5 are lower bounds, not point estimates.**"),
 ("bee disagreement row",    "| `bee-1-cpl` | 0.48 | 0.30 | **no** -- mine is more conservative |"),
 ("refuted-hypothesis line", "**I tested it and it is wrong.**"),
 ("raw-power guard",         "no single number in this document can be trusted on its own in a flat region"),
]
INNOCUOUS = [
 ("trailing blank lines",    lambda t: t + "\n\n\n"),
 ("appended neutral prose",  lambda t: add(t, "This document was reviewed for typographical consistency.")),
 ("reworded non-claim",      lambda t: t.replace("no re-render", "without re-rendering")),
 ("added neutral heading",   lambda t: add(t, "## Appendix: file inventory\n\nScripts referenced above live in `experiments/V-SOFTCHECK/`.")),
]

def run_entry(text):
    fd, path = tempfile.mkstemp(suffix=".md"); os.close(fd)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    env = dict(os.environ); env["VBQ_DOC"] = path
    r = subprocess.run([sys.executable, SCRIPT], capture_output=True, env=env, cwd=HERE)
    os.unlink(path)
    return r.returncode, r.stdout.decode("utf-8", "replace")

def main():
    doc = head_text()
    print("=== ARM 1: CLEAN -- must exit 0 ===")
    rc, out = run_entry(doc)
    clean_ok = (rc == 0)
    print("  clean document -> exit %d  %s\n" % (rc, "ok" if clean_ok else "FAIL"))

    print("=== ARM 2: DELETION -- a removed finding must exit non-zero ===")
    d_ok = 0
    for name, phrase in DELETIONS:
        rc, out = run_entry(cut(doc, phrase))
        hit = rc != 0
        d_ok += hit
        print("  %-26s -> exit %d  %s" % (name, rc, "RED (caught)" if hit else "*** GREEN -- DELETION UNDETECTED ***"))
    print("  %d/%d deletions caught\n" % (d_ok, len(DELETIONS)))

    print("=== ARM 3: INNOCUOUS -- prose that asserts nothing must exit 0 ===")
    i_ok = 0
    for name, fn in INNOCUOUS:
        mut = fn(doc)
        if mut == doc: sys.exit("INNOCUOUS ARM INERT (changed nothing): %s" % name)
        rc, out = run_entry(mut)
        hit = rc == 0
        i_ok += hit
        print("  %-26s -> exit %d  %s" % (name, rc, "ok" if hit else "*** FALSE ALARM ***"))
    print("  %d/%d innocuous edits correctly ignored\n" % (i_ok, len(INNOCUOUS)))

    ok = clean_ok and d_ok == len(DELETIONS) and i_ok == len(INNOCUOUS)
    print("PASS/FAIL CHANNEL: clean=0 %s, deletion!=0 %d/%d, innocuous=0 %d/%d"
          % ("ok" if clean_ok else "FAIL", d_ok, len(DELETIONS), i_ok, len(INNOCUOUS)))
    print("VERDICT: %s" % ("GREEN -- sensitivity AND specificity commissioned at the entry point"
                           if ok else "RED -- see above"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
