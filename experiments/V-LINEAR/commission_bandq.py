"""Commissioning for `bandq.py` -- the band licence check.

Run:  python commission_bandq.py

WHY THIS IS SHAPED THE WAY IT IS
--------------------------------
`bandq.py` is a gate other lanes will wire into their own scripts, so its EXIT
CODE is the product.  A gate that always exits 0 and a gate that is genuinely
licensing every cell it is asked about are indistinguishable from the outside;
so are a gate that always exits non-zero and a working refusal.

Three lessons from tonight, all earned elsewhere on this project, are built in:

  1. An inert plant and a dead instrument give the identical green.  So the
     MUTATION arms below edit the RECORD and require the verdict to follow.  If
     bandq were returning canned answers, every non-mutation arm would still
     pass and only these would fail.

  2. Commissioning sensitivity is not commissioning specificity.  Arms that
     must NOT change the answer are in NULLS and are counted separately.

  3. Commission DELETION as well as reversal.  Deleting a record must turn a
     licensed cell into UNQUALIFIED -- and specifically NOT into UNKNOWN, which
     is the distinction the whole tool exists to preserve.

ORCH's three required cases are arms 1, 2/5/6, and 7/8 respectively.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BANDQ = os.path.join(HERE, "bandq.py")

PASS, FAIL, MARGINAL, UNQUALIFIED, UNKNOWN, REFUSED = 0, 1, 2, 3, 4, 5
NAME = {0: "PASS", 1: "FAIL", 2: "MARGINAL", 3: "UNQUALIFIED",
        4: "UNKNOWN", 5: "REFUSED"}

BEE = os.path.join(HERE, "bandsweep-far20-bee-1-cpl.json")
M112 = os.path.join(HERE, "bandsweep-far20-112MSDCF.json")


def run(args, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([sys.executable, BANDQ] + args,
                       cwd=HERE, capture_output=True, env=e)
    return p.returncode, p.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------- plain arms
# (name, argv, expected exit, why)
ARMS = [
    ("licensed-pass",
     ["bee-1-cpl", "0.30", "0.35"], PASS,
     "ORCH's first required case: a subject that IS qualified must exit 0. "
     "bee-1-cpl at 0.30-0.35 is R=5.311, the strongest qualifier measured, "
     "and is where two lanes are scoring tonight."),

    ("not-licensed-fail",
     ["112MSDCF", "0.30", "0.35"], FAIL,
     "ORCH's second required case. R=1.079 with the CI upper bound 0.379 "
     "below MARGINAL: measured noise, and the cell that killed the -44.6%."),

    ("marginal-refused-by-default",
     ["lavendar-cpl", "0.30", "0.35"], MARGINAL,
     "MARGINAL must not silently count as a licence. A caller who does not "
     "say otherwise gets a refusal."),

    ("marginal-allowed-on-request",
     ["lavendar-cpl", "0.30", "0.35", "--allow-marginal"], PASS,
     "...but a caller who has decided marginal is good enough for their "
     "purpose must be able to say so explicitly. If this arm did not exist, "
     "--allow-marginal could be a no-op and nothing would show it."),

    ("unqualified-slice-never-swept",
     ["leaf-2-cpl", "0.30", "0.35"], UNQUALIFIED,
     "leaf-2-cpl IS measured -- at 0.30-0.40, and it FAILS there. It has "
     "never been measured at 0.30-0.35. Reporting the wider slice's FAIL "
     "here would be exactly the conflation that produced ORCH correction #5."),

    ("unqualified-subject-never-swept",
     ["chia-seeds-cpl", "0.30", "0.35"], UNQUALIFIED,
     "a real corpus subject with no record at any slice. Same verdict as the "
     "arm above, different reason, and the tool must say which."),

    ("unknown-typo",
     ["bee-1-cpll", "0.30", "0.35"], UNKNOWN,
     "ORCH's third required case: a name that does not exist must fail LOUDLY "
     "rather than reporting UNQUALIFIED. If a typo returned UNQUALIFIED, a "
     "misspelled subject would look exactly like a working licence refusal."),

    ("unknown-plausible-but-absent",
     ["bee-4-cpl", "0.30", "0.35"], UNKNOWN,
     "harder than the typo arm: a name that follows the corpus's own naming "
     "pattern and could easily be believed. bee-1/2/3 exist; bee-4 does not."),

    ("wide-slice-still-answerable",
     ["leaf-2-cpl", "0.30", "0.40"], FAIL,
     "the wide slice on the same subject IS measured and does answer. This is "
     "the control for the arm above: it shows UNQUALIFIED there is a property "
     "of the SLICE, not of the subject being unreachable."),

    # ---- protocol (`far`) selection ------------------------------------
    # `far` is part of a cell's identity.  The first version of bandq.py
    # pooled every protocol together, which made four cells look like
    # contradictions; verify_bands_doc.py caught it by reading the raw JSON.
    ("protocol-split-is-not-a-disagreement",
     ["112MSDCF", "0.02", "0.05"], PASS,
     "REGRESSION ARM for the pooling defect. This cell reads PASS at far=20 "
     "and MARGINAL at far=8. Those are two measurements, not a contradiction, "
     "and the tool must quote the canonical far=20 rather than REFUSE."),

    ("explicit-far-selects-the-other-protocol",
     ["112MSDCF", "0.02", "0.05", "--far", "8"], MARGINAL,
     "the same cell, asked for explicitly at far=8, must return the OTHER "
     "answer. If --far were ignored, the arm above would pass on a tool that "
     "can only ever see one protocol."),

    ("unmeasured-far-does-not-fall-back",
     ["112MSDCF", "0.02", "0.05", "--far", "99"], UNQUALIFIED,
     "the dangerous case: a protocol that was never run must be UNQUALIFIED, "
     "NOT a silent fallback to far=20. A caller who asked for far=99 and got "
     "a far=20 answer labelled PASS would be misled in the worst way."),
]

# ------------------------------------------------------------ mutation arms
# These edit a record on disk and require the answer to follow it.  Without
# them, every arm above would pass on a tool that never opened a JSON file.


def mutate_verdict(path, key, slice_key, new_verdict):
    d = json.load(open(path, encoding="utf-8"))
    hits = 0
    for rec in d:
        if rec["key"] == key and slice_key in rec["bands"]:
            rec["bands"][slice_key]["verdict"] = new_verdict
            hits += 1
    if hits != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND EXACTLY ONCE: %s %s in %s "
                         "(%d hits)" % (key, slice_key, path, hits))
    json.dump(d, open(path, "w", encoding="utf-8"), indent=1)


def mutate_r(path, key, slice_key, new_r):
    d = json.load(open(path, encoding="utf-8"))
    hits = 0
    for rec in d:
        if rec["key"] == key and slice_key in rec["bands"]:
            rec["bands"][slice_key]["R"] = new_r
            hits += 1
    if hits != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND EXACTLY ONCE")
    json.dump(d, open(path, "w", encoding="utf-8"), indent=1)


def main():
    backups = {}
    for p in (BEE, M112):
        b = tempfile.mktemp(suffix=".bak")
        shutil.copy2(p, b)
        backups[p] = b

    caught = missed = 0
    nulls_ok = nulls_bad = 0

    try:
        print("=" * 78)
        print("PLAIN ARMS -- the exit code is the product")
        print("=" * 78)
        for name, argv, want, why in ARMS:
            rc, out = run(argv)
            ok = rc == want
            print("[%-9s] want %-11s got %-11s  %s"
                  % ("ok" if ok else "WRONG", NAME[want],
                     NAME.get(rc, rc), name))
            print("             why: %s" % why)
            if ok:
                caught += 1
            else:
                missed += 1
                print("             OUTPUT:\n%s" % out)

        print()
        print("=" * 78)
        print("MUTATION ARMS -- does it actually read the record?")
        print("=" * 78)

        # M1: flip bee's verdict in the record; the licence must follow.
        mutate_verdict(BEE, "bee-1-cpl", "0.30-0.35", "FAIL(noise)")
        rc, out = run(["bee-1-cpl", "0.30", "0.35"])
        ok = rc == FAIL
        print("[%-9s] want %-11s got %-11s  mutate-verdict-pass-to-fail"
              % ("ok" if ok else "WRONG", NAME[FAIL], NAME.get(rc, rc)))
        print("             why: the single most important arm. If bandq "
              "returned a canned answer for bee, every plain arm above would "
              "still pass and only this would fail.")
        caught, missed = (caught + 1, missed) if ok else (caught, missed + 1)
        shutil.copy2(backups[BEE], BEE)

        # M2: flip 112MSDCF the other way -- a refusal must be able to become
        # a licence, or the tool is just biased toward refusing.
        mutate_verdict(M112, "112MSDCF", "0.30-0.35", "PASS")
        rc, out = run(["112MSDCF", "0.30", "0.35"])
        ok = rc == PASS
        print("[%-9s] want %-11s got %-11s  mutate-verdict-fail-to-pass"
              % ("ok" if ok else "WRONG", NAME[PASS], NAME.get(rc, rc)))
        print("             why: the opposite direction. A gate that refuses "
              "everything passes the FAIL arm trivially; this is the arm it "
              "cannot pass.")
        caught, missed = (caught + 1, missed) if ok else (caught, missed + 1)
        shutil.copy2(backups[M112], M112)

        # M3: change R without touching the verdict -- the printed number must
        # follow, or bandq is quoting something other than the record.
        mutate_r(BEE, "bee-1-cpl", "0.30-0.35", 9.8765)
        rc, out = run(["bee-1-cpl", "0.30", "0.35"])
        ok = rc == PASS and "9.8765" in out and "5.3109" not in out
        print("[%-9s] want %-11s got %-11s  mutate-R-only"
              % ("ok" if ok else "WRONG", "PASS+9.8765", NAME.get(rc, rc)))
        print("             why: the verdict is unchanged, so exit code alone "
              "cannot detect this. It catches a tool that reports the right "
              "licence with the wrong evidence beside it.")
        caught, missed = (caught + 1, missed) if ok else (caught, missed + 1)
        if not ok:
            print("             OUTPUT:\n%s" % out)
        shutil.copy2(backups[BEE], BEE)

        # M4: DELETION.  Removing the record must give UNQUALIFIED, and must
        # NOT give UNKNOWN -- the subject still exists.
        held = tempfile.mktemp(suffix=".json")
        shutil.move(BEE, held)
        rc, out = run(["bee-1-cpl", "0.30", "0.35"])
        ok = rc == UNQUALIFIED
        print("[%-9s] want %-11s got %-11s  delete-record"
              % ("ok" if ok else "WRONG", NAME[UNQUALIFIED], NAME.get(rc, rc)))
        print("             why: ORCH's third lesson. Deleting a measurement "
              "must make the cell UNMEASURED, not UNKNOWN and not FAIL. This "
              "is the exact distinction the tool exists to preserve.")
        caught, missed = (caught + 1, missed) if ok else (caught, missed + 1)
        shutil.move(held, BEE)

        # M5: two records disagreeing about one cell must be REFUSED, not
        # silently first-wins.  Same defect class as loader defect 3.
        clash = os.path.join(HERE, "bandsweep-CLASH-TEMP.json")
        d = json.load(open(BEE, encoding="utf-8"))
        for rec in d:
            if rec["key"] == "bee-1-cpl":
                rec["bands"]["0.30-0.35"]["verdict"] = "FAIL(noise)"
        json.dump(d, open(clash, "w", encoding="utf-8"), indent=1)
        rc, out = run(["bee-1-cpl", "0.30", "0.35"])
        ok = rc == REFUSED
        print("[%-9s] want %-11s got %-11s  two-records-disagree"
              % ("ok" if ok else "WRONG", NAME[REFUSED], NAME.get(rc, rc)))
        print("             why: agreement is not ambiguity; disagreement is. "
              "Picking a winner silently is how a control shadowed a canonical "
              "record earlier in this lane.")
        caught, missed = (caught + 1, missed) if ok else (caught, missed + 1)
        os.remove(clash)

        # M6/M7: roster drift, both directions.
        fake = tempfile.mkdtemp()
        os.mkdir(os.path.join(fake, "bee-1-cpl"))
        rc, out = run(["bee-1-cpl", "0.30", "0.35"], {"BANDQ_MACRO": fake})
        ok = rc == PASS and "ROSTER DRIFT" in out and "in ROSTER but not on disk" in out
        print("[%-9s] want %-11s got %-11s  roster-drift-subjects-missing"
              % ("ok" if ok else "WRONG", "PASS+DRIFT", NAME.get(rc, rc)))
        print("             why: a static roster goes stale silently, which is "
              "the same class of defect this tool prevents. The drift "
              "detector must be seen to fire.")
        caught, missed = (caught + 1, missed) if ok else (caught, missed + 1)

        os.mkdir(os.path.join(fake, "brand-new-capture"))
        rc, out = run(["bee-1-cpl", "0.30", "0.35"], {"BANDQ_MACRO": fake})
        ok = rc == PASS and "on disk but not in ROSTER" in out
        print("[%-9s] want %-11s got %-11s  roster-drift-new-subject"
              % ("ok" if ok else "WRONG", "PASS+DRIFT", NAME.get(rc, rc)))
        print("             why: the direction that matters in practice -- a "
              "new capture would otherwise report UNKNOWN and look like a typo.")
        caught, missed = (caught + 1, missed) if ok else (caught, missed + 1)
        shutil.rmtree(fake, ignore_errors=True)

        # ------------------------------------------------------------ nulls
        print()
        print("=" * 78)
        print("NULL ARMS -- these must NOT change the answer")
        print("=" * 78)
        NULLS = [
            ("float-formatting-0.3-vs-0.30",
             ["bee-1-cpl", "0.3", "0.35"], PASS,
             "0.3 and 0.30 are the same slice. If they were not, a lane would "
             "get UNQUALIFIED for a cell that is measured, and would read it "
             "as a refusal."),
            ("quiet-flag-does-not-change-verdict",
             ["112MSDCF", "0.30", "0.35", "--quiet"], FAIL,
             "--quiet suppresses output, not judgement. A flag that silently "
             "changed an exit code would be the worst possible defect in a "
             "gate."),
            ("allow-marginal-does-not-rescue-a-FAIL",
             ["112MSDCF", "0.30", "0.35", "--allow-marginal"], FAIL,
             "--allow-marginal must widen the licence to MARGINAL and NO "
             "further. If it also passed FAIL, it would be an off switch for "
             "the whole gate."),
        ]
        for name, argv, want, why in NULLS:
            rc, out = run(argv)
            ok = rc == want
            print("[%-9s] want %-11s got %-11s  %s"
                  % ("quiet" if ok else "FALSE ALARM", NAME[want],
                     NAME.get(rc, rc), name))
            print("             why: %s" % why)
            if ok:
                nulls_ok += 1
            else:
                nulls_bad += 1

    finally:
        # Restore, then CHECK the restore against the backup bytes.  The first
        # version of this compared each file to itself and reported "yes"
        # unconditionally -- an inert check, which is the defect this whole
        # harness is built to catch, written into the harness.
        restored = True
        for p, b in backups.items():
            want = open(b, "rb").read()
            shutil.copy2(b, p)
            if open(p, "rb").read() != want:
                restored = False
                print("  RESTORE FAILED: %s" % p)
            os.remove(b)

    print()
    print("records restored byte-identical: %s" % ("yes" if restored else "NO"))

    total_defect = len(ARMS) + 7
    print()
    print("  correct     : %d" % caught)
    print("  WRONG       : %d" % missed)
    print("  -----------------")
    print("  arms        : %d   (declared %d)" % (caught + missed, total_defect))
    print()
    print("  quiet       : %d" % nulls_ok)
    print("  FALSE ALARM : %d" % nulls_bad)
    print("  -----------------")
    print("  null arms   : %d   (declared 3)" % (nulls_ok + nulls_bad))
    if caught + missed != total_defect:
        print("  ARM COUNT MISMATCH -- an arm did not run.")
        return 1
    return 0 if (missed == 0 and nulls_bad == 0 and restored) else 1


if __name__ == "__main__":
    sys.exit(main())
