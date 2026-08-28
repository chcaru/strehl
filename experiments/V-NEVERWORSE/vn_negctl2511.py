"""Negative control for section 9.25.11's verifier.

Same contract as `vn_negctl25.py`: plants in BOTH the document and the RECORDS,
because a checker that carries its own copy of the answer passes every document
plant and detects nothing. Every mutation is anchored on a string that must
occur exactly once and a plant that does not land is a hard error, so a control
that cannot fail is caught rather than counted as a pass.

Also required, and separate from the plants:
  PLACEBO  a prose edit that changes no measured value must stay GREEN
  REFUSAL  an unreadable record must exit 2, distinct from pass and fail
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "RESULT.md")
OUT = r"C:\dev\strehl-out\V-NEVERWORSE\dilute"
GB = r"C:\dev\strehl-out\V-NEVERWORSE\gbundle"
REC = [(OUT, "shipfr-pin-9b05d0b7.json"), (OUT, "regout.json"),
       (OUT, "shipped46.json"), (OUT, "pfvar.json"),
       (GB, "bee-2-cpl.json")]
PY = sys.executable


def run():
    p = subprocess.run([PY, os.path.join(HERE, "vn_verify2511.py")],
                       capture_output=True, text=True, cwd=HERE)
    return p.returncode


def doc_plant(old, new):
    def go():
        t = io.open(DOC, encoding="utf-8").read()
        if t.count(old) != 1:
            raise SystemExit("PLANT DID NOT LAND: %r occurs %d times"
                             % (old, t.count(old)))
        io.open(DOC, "w", encoding="utf-8",
                newline="").write(t.replace(old, new, 1))
    return go


def rec_plant(where, name, path, mult=None, setval=None):
    def go():
        p = os.path.join(where, name)
        d = json.load(io.open(p, encoding="utf-8"))
        node = d
        for k in path[:-1]:
            node = node[k]
        before = node[path[-1]]
        node[path[-1]] = (before * mult) if mult is not None else setval
        if node[path[-1]] == before:
            raise SystemExit("PLANT DID NOT LAND: %s%s unchanged at %r"
                             % (name, path, before))
        json.dump(d, io.open(p, "w", encoding="utf-8"), default=float, indent=1)
    return go


def corrupt(where, name):
    def go():
        io.open(os.path.join(where, name), "w",
                encoding="utf-8").write("{ not json")
    return go


def frame_row(idx):
    """Locate a frame's row in the gbundle record by its frame number."""
    d = json.load(io.open(os.path.join(GB, "bee-2-cpl.json"),
                          encoding="utf-8"))
    for i, r in enumerate(d["rows"]):
        if int(r["frame"]) == idx:
            return i
    raise SystemExit("PLANT DID NOT LAND: no row for frame %d" % idx)


PLANTS = [
    ("doc: the rogue-below-null claim",
     doc_plant("**The rogue step is\nsmaller than a null.**",
               "**The rogue step is\nlarger than a null.**"), 1),
    ("doc: the 0.58x fitted scale",
     doc_plant("fitted a 0.58x similarity", "fitted a 0.98x similarity"), 1),
    ("doc: the 65x margin",
     doc_plant("a 65x margin", "a 6x margin"), 1),
    ("doc: the next-worst deviation",
     doc_plant("sits just -0.0141 below", "sits just -0.5141 below"), 1),
    ("doc: the correction banner",
     doc_plant("READ 9.25.11\n> BEFORE QUOTING", "READ 9.25.12\n> BEFORE "
               "QUOTING"), 1),
    ("doc: the not-reproduced verdict phrase",
     doc_plant("does not reproduce any of this",
               "does not reproduce most of this"), 1),
    ("doc: the screen commissioning claim",
     doc_plant("All four pass.", "Three of four pass."), 1),
    ("doc: a cell of the shipping-binary table",
     doc_plant("| 46 -> 47 | `DSC00047.ARW` | **the accused** | 1.010 | 1.014 "
               "| 1.011 | 1.005 |",
               "| 46 -> 47 | `DSC00047.ARW` | **the accused** | 1.010 | 1.014 "
               "| 1.911 | 1.005 |"), 1),
    ("doc: a cell of the registration table",
     doc_plant("| **46** | **POOR-REG** | **0.0275** | **0.5800** |",
               "| **46** | **POOR-REG** | **0.0275** | **0.9800** |"), 1),
    ("doc: the sufficiency figure",
     doc_plant("**4.63x of the 4.97x**", "**1.63x of the 4.97x**"), 1),
    ("doc: the necessity figure",
     doc_plant("only 1.04x", "only 4.04x"), 1),
    ("doc: the gain-invariance drift",
     doc_plant("moves it by 1.78e-15", "moves it by 1.78e-05"), 1),
    ("doc: the ordinary-frame move",
     doc_plant("**3017665x**", "**3017x**"), 1),
    ("doc: the shipping L5 share",
     doc_plant("entitlement of 0.00348", "entitlement of 0.00448"), 1),
    ("oracle: the rogue step in the binary",
     rec_plant(OUT, "shipfr-pin-9b05d0b7.json", ["steps", 2, "ratio", 5], mult=2.0), 1),
    ("oracle: the worst null",
     rec_plant(OUT, "shipfr-pin-9b05d0b7.json", ["worst_null"], setval=1.9), 1),
    ("oracle: the binary's verdict string",
     rec_plant(OUT, "shipfr-pin-9b05d0b7.json", ["verdict"],
               setval="THE SHIPPING BINARY CARRIES IT"), 1),
    ("oracle: the rogue's deviation",
     rec_plant(OUT, "regout.json", ["rogue_deviation"], mult=0.5), 1),
    ("oracle: the next-worst deviation",
     rec_plant(OUT, "regout.json", ["next_worst"], mult=3.0), 1),
    ("oracle: the flagged-frame list",
     rec_plant(OUT, "regout.json", ["flagged"], setval=[46, 77]), 1),
    ("oracle: POOR-REG frames flagged",
     rec_plant(OUT, "regout.json", ["n_poor_flagged"], setval=9), 1),
    ("oracle: frames screened",
     rec_plant(OUT, "regout.json", ["n_screened"], setval=250), 1),
    ("oracle: the screen commissioning flag",
     rec_plant(OUT, "regout.json", ["commission", "passed"], setval=False), 1),
    ("oracle: the sufficiency plant",
     rec_plant(OUT, "shipped46.json", ["commission", "g4_sufficiency"],
               mult=0.3), 1),
    ("oracle: the necessity plant",
     rec_plant(OUT, "shipped46.json", ["commission", "g5_necessity"],
               mult=4.0), 1),
    ("oracle: the gain-invariance drift",
     rec_plant(OUT, "shipped46.json", ["commission", "g1_gain_drift"],
               setval=1e-5), 1),
    ("oracle: the per-frame variance ratio",
     rec_plant(OUT, "pfvar.json", ["var_rogue_over_median"], mult=50.0), 1),
    ("oracle: the ordinary-frame move",
     rec_plant(OUT, "pfvar.json", ["ordinary_move"], mult=0.001), 1),
    ("oracle: the shipping L5 share",
     rec_plant(OUT, "pfvar.json", ["rows", 3, "rogue_shared"], mult=0.5), 1),
    ("oracle: frame 46's ncc_b in the bundle record",
     rec_plant(GB, "bee-2-cpl.json", ["rows", frame_row(46), "ncc_b"],
               setval=0.91), 1),
    ("oracle: frame 46's fitted scale in the bundle record",
     rec_plant(GB, "bee-2-cpl.json", ["rows", frame_row(46), "scale"],
               setval=0.96), 1),
    ("oracle: a neighbour's state in the bundle record",
     rec_plant(GB, "bee-2-cpl.json", ["rows", frame_row(45), "state"],
               setval="POOR-REG"), 1),
    ("PLACEBO: prose that changes no measured value",
     doc_plant("The warped window is junk; the junk is broadside coarse-scale;",
               "The warped window is junk, the junk is broadside coarse "
               "scale,"), 0),
    ("REFUSAL: unreadable record must exit 2", corrupt(OUT, "regout.json"), 2),
]


def main():
    tmp = tempfile.mkdtemp(prefix="vn_negctl2511_")
    shutil.copy2(DOC, os.path.join(tmp, "RESULT.md"))
    for w, r in REC:
        shutil.copy2(os.path.join(w, r), os.path.join(tmp, r))

    if run() != 0:
        print("REFUSED: the checker is not green before planting; a negative "
              "control on a red checker measures nothing")
        return 2

    def restore():
        shutil.copy2(os.path.join(tmp, "RESULT.md"), DOC)
        for w, r in REC:
            shutil.copy2(os.path.join(tmp, r), os.path.join(w, r))

    caught, missed = [], []
    try:
        for name, plant, want in PLANTS:
            plant()
            rc = run()
            (caught if rc == want else missed).append(
                name if rc == want else "%s: wanted %d got %d"
                % (name, want, rc))
            restore()
    finally:
        restore()

    rc1 = run()
    nd = sum(1 for n, _, _ in PLANTS if n.startswith("doc:"))
    no = sum(1 for n, _, _ in PLANTS if n.startswith("oracle:"))
    print("negative control for section 9.25.11")
    print("  plants           %d  (%d document, %d oracle, 1 placebo, "
          "1 refusal)" % (len(PLANTS), nd, no))
    print("  behaved          %d" % len(caught))
    print("  MISBEHAVED       %d" % len(missed))
    print("  restored green   %s (exit %d)" % (rc1 == 0, rc1))
    for m in missed:
        print("  MISS %s" % m)
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if (not missed and rc1 == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
