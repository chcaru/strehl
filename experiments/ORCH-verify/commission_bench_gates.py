"""Commission the bench-gate pins added to vowner0906.py.

Those pins assert that the owner's shooting thresholds are the ones the owning
lanes actually registered: the three-way `133` eligible-tile gate from M151,
and the Q05/Q95 sign gates and `1.33x` ceiling from M135. Both lanes are live
and free to revise those bars. A pin that has never been observed to go red is
a claim about the pin, not about the documents, so each one is proved here by
planting the exact defect it reads.

Three properties beyond "it went red":

1. THE LIVE TREE IS NEVER WRITTEN. ~25 agents share this working directory, and
   a mutation window in which `M135-detail-instrument.md` states a false bar is
   a window in which another lane can read it. docs/ is copied into TEMP and
   every mutation is applied there; vowner0906.py takes a repo root as argv[1],
   which is what makes that possible.

2. DUPLICATE-SITE DETECTION. Every check is presence-based, so any duplicate of
   a needle elsewhere in the file satisfies it. A needle with several sites is
   not anchored to a canonical one, and its pin could be a silent no-op. Each
   arm counts occurrences and reports that rather than hiding it.

3. AN INERT ARM. A harness in which every mutation goes red cannot distinguish
   a working pin from a verifier that reds on any edit at all.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(__file__).resolve().parents[2]
V = REAL / "experiments" / "ORCH-verify" / "vowner0906.py"

REL_OWNER = "docs/OWNER-ACTIONS.md"
REL_M135 = "docs/research/M135-detail-instrument.md"
REL_M151 = "docs/research/M151-m5-checker.md"

# (arm, relative path, needle, replacement, bench labels that must go RED)
ARMS = [
    ("src sw4 bar moved", REL_M151,
     "at least 133 eligible tiles in the pass-averaged sw4 manifest",
     "at least 140 eligible tiles in the pass-averaged sw4 manifest",
     {"133 sw4"}),
    ("src sw10 bar moved", REL_M151,
     "at least 133 eligible tiles in the pass-averaged sw10 manifest",
     "at least 140 eligible tiles in the pass-averaged sw10 manifest",
     {"133 sw10"}),
    ("src intersection -> union", REL_M151,
     "at least 133 common eligible physical tiles in the intersection",
     "at least 133 common eligible physical tiles in the union",
     {"133 intersection"}),
    ("src Q05 sign flipped", REL_M135,
     "| Genuine optical improvement | up | q05 ratio `>1.10`",
     "| Genuine optical improvement | up | q05 ratio `<1.10`",
     {"Q05 sharp gate"}),
    ("src Q95 sign flipped", REL_M135,
     "| Pre-noise blur | down | q95 ratio `<0.90`",
     "| Pre-noise blur | down | q95 ratio `>0.90`", {"Q95 blur gate"}),
    ("src Q05 evidence altered", REL_M135, "**VERIFIED PASS**, `1.241840`",
     "**VERIFIED PASS**, `1.241841`", {"Q05 improvement arm"}),
    ("src Q95 evidence altered", REL_M135, "**VERIFIED PASS**, `0.631511`",
     "**VERIFIED PASS**, `0.631510`", {"Q95 degradation arm"}),
    ("src 1.33x ceiling raised", REL_M135, "with a hard `1.33x` maximum",
     "with a hard `1.40x` maximum", {"1.33x ceiling"}),
    ("src averaging order dropped", REL_M151,
     "regularisation, best-frame election, ratios",
     "best-frame election, ratios", {"M5 gate averaging order"}),
    # Owner-side. Dropping a term from the owner's shooting instruction is the
    # specific expensive error this block exists to catch: it understates the
    # registered gate, so the owner could shoot a session that satisfies the
    # printed gate and fails the real one.
    ("owner drops intersection", REL_OWNER,
     "their physical-coordinate intersection `>=133` eligible tiles",
     "their physical-coordinate intersection considered separately",
     {"133 intersection"}),
    ("owner drops sw10 threshold", REL_OWNER,
     "pass-averaged `sw10` `>=133` eligible tiles",
     "pass-averaged `sw10` counted for information",
     {"133 sw10"}),
    ("owner drops averaging order", REL_OWNER,
     "regularisation, best-frame election, ratios",
     "best-frame election, ratios", {"M5 gate averaging order"}),
    ("owner Q05 threshold moved", REL_OWNER,
     "`Q05` must be strictly above `1.10`.",
     "`Q05` must be strictly above `1.05`.", {"Q05 sharp gate"}),
    ("owner Q95 threshold moved", REL_OWNER,
     "`Q95` must be strictly below `0.90`.",
     "`Q95` must be strictly below `0.95`.", {"Q95 blur gate"}),
    ("INERT owner prose reworded", REL_OWNER,
     "That gate adds no frames.", "That gate adds no extra frames.", set()),
]

RED_RE = re.compile(r"^RED   bench  (.+?)\s+(?:source=|SOURCE)", re.M)


def wrapped(needle):
    """A pattern matching `needle` even when Markdown has wrapped it.

    OWNER-ACTIONS is a blockquote, so a phrase that wraps is stored as
    '... must each retain\n>    at least ...'. A literal search for the
    unwrapped phrase finds nothing and the arm dies with MUTATION TARGET NOT
    FOUND -- which reads exactly like a needle that no longer exists. Joining
    the tokens on [\\s>]+ makes the wrapped and unwrapped forms one pattern.
    """
    return re.compile(r"[\s>]+".join(re.escape(t) for t in needle.split()))


def run(root):
    p = subprocess.run([sys.executable, str(V), str(root)],
                       capture_output=True)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def bench_reds(out):
    return {m.group(1).strip() for m in RED_RE.finditer(out)}


tmp = Path(tempfile.mkdtemp(prefix="orch-bench-"))
try:
    shutil.copytree(REAL / "docs", tmp / "docs")
    (tmp / "experiments" / "ORCH-verify").mkdir(parents=True)
    shutil.copy2(REAL / "experiments" / "ORCH-verify"
                 / "host-load-2026-09-06.json",
                 tmp / "experiments" / "ORCH-verify")

    base = run(tmp)
    if "VERDICT: GREEN" not in base:
        raise SystemExit("FATAL: TEMP baseline is not GREEN; the copy is not a "
                         "faithful stand-in and no arm below would mean "
                         "anything.\n" + base[-3000:])
    print("TEMP baseline VERDICT: GREEN")
    print("live tree written: NO (all mutations applied under %s)\n" % tmp)

    caught = missed = dupes = 0
    for label, rel, old, new, expect in ARMS:
        f = tmp / rel
        text = f.read_bytes().decode("utf-8")
        pat = wrapped(old)
        n = len(pat.findall(text))
        if n == 0:
            raise SystemExit("MUTATION TARGET NOT FOUND: %s :: %r"
                             % (label, old))
        if n > 1 and expect:
            print("DUPLICATE %-28s %d sites -- not canonically anchored"
                  % (label, n))
            dupes += 1
        orig = f.read_bytes()
        try:
            f.write_bytes(pat.sub(lambda _: new, text).encode("utf-8"))
            out = run(tmp)
            got = bench_reds(out)
        finally:
            f.write_bytes(orig)

        if not expect:
            ok = "VERDICT: GREEN" in out and not got
            print(("INERT-OK   " if ok else "INERT-FAIL ") + "%-28s reds=%s"
                  % (label, sorted(got) or "none"))
            caught += 1 if ok else 0
            missed += 0 if ok else 1
        elif got == expect:
            print("CAUGHT     %-28s -> %s" % (label, sorted(got)))
            caught += 1
        else:
            print("MISSED     %-28s expected %s got %s"
                  % (label, sorted(expect), sorted(got) or "NOTHING (no-op)"))
            missed += 1

    after = run(tmp)
    restored = "VERDICT: GREEN" in after
    print("\npost-restore TEMP VERDICT: "
          + ("GREEN" if restored else "RED -- copy not restored"))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

live = run(REAL)
print("live tree VERDICT: "
      + ("GREEN" if "VERDICT: GREEN" in live else "RED -- LIVE TREE DISTURBED"))
print("\nARMS %d  CAUGHT %d  MISSED %d  DUPLICATE-SITE %d"
      % (len(ARMS), caught, missed, dupes))
ok = missed == 0 and restored and "VERDICT: GREEN" in live
print("COMMISSIONED" if ok else "NOT COMMISSIONED")
sys.exit(0 if ok else 1)
