"""Negative control for section 9.25's verifier.

A checker that has never been shown to fail is not evidence. This plants
defects one at a time and requires each to turn `vn_verify25.py` RED.

TWO KINDS OF PLANT, AND THE SECOND IS THE POINT.

  DOCUMENT plants edit RESULT.md. They catch a checker whose patterns do not
  actually reach the text.
  ORACLE plants edit the JSON RECORDS the checker derives its expectations
  from. They catch a checker that carries its own copy of the answer -- which
  passes every document plant and detects nothing. That is the failure ORCH
  propagated across the fleet after a checker ran 37/37 green and then caught
  5 of 13 plants.

Every mutation is anchored on a string that must occur EXACTLY ONCE in its
target, and a plant that does not land is a hard error rather than a silent
green. A control that cannot fail is the defect it exists to detect: this
project has sighted a short-circuited identity control twice.

Two further arms, both required:

  PLACEBO   a prose edit that changes no measured value must stay GREEN, or
            the checker is merely reacting to the file changing.
  REFUSAL   an unreadable record must exit 2, distinct from both pass (0) and
            fail (1), so "I could not check this" cannot read as "this
            passed".

Restores from a copy taken in TEMP. Never `git checkout`, which reverts to
HEAD and discards concurrent uncommitted work in a shared tree.
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
REC = ("subgate.json", "subgate-ladder.json", "rogue.json", "rogue46.json")
PY = sys.executable


def run():
    p = subprocess.run([PY, os.path.join(HERE, "vn_verify25.py")],
                       capture_output=True, text=True, cwd=HERE)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def doc_plant(old, new):
    def go():
        t = io.open(DOC, encoding="utf-8").read()
        if t.count(old) != 1:
            raise SystemExit("PLANT DID NOT LAND: %r occurs %d times in the "
                             "document, want exactly 1" % (old, t.count(old)))
        io.open(DOC, "w", encoding="utf-8",
                newline="").write(t.replace(old, new, 1))
    return go


def rec_plant(name, path, mult=None, setval=None):
    """Mutate one leaf of one record. `path` is a list of dict keys and list
    indices. The old value is asserted to exist and to change."""
    def go():
        p = os.path.join(OUT, name)
        d = json.load(io.open(p, encoding="utf-8"))
        node = d
        for k in path[:-1]:
            node = node[k]
        last = path[-1]
        before = node[last]
        node[last] = (before * mult) if mult is not None else setval
        if node[last] == before:
            raise SystemExit("PLANT DID NOT LAND: %s%s unchanged at %r"
                             % (name, path, before))
        json.dump(d, io.open(p, "w", encoding="utf-8"), default=float,
                  indent=1)
    return go


def corrupt(name):
    def go():
        io.open(os.path.join(OUT, name), "w",
                encoding="utf-8").write("{ this is not json")
    return go


PLANTS = [
    # ---- document plants -------------------------------------------------
    ("doc: r_subgate headline bound",
     doc_plant("is at most 0.026 on any subject measured",
               "is at most 0.126 on any subject measured"), 1),
    ("doc: sub-gate pixel range low end",
     doc_plant("over pixel counts from 81,109 to",
               "over pixel counts from 81,409 to"), 1),
    ("doc: coffee-bubbles L4 selection cost",
     doc_plant("reaches **+0.456 at L4**", "reaches **+0.556 at L4**"), 1),
    ("doc: pair-split agreement",
     doc_plant("The two agree to 0.0004 at the",
               "The two agree to 0.0009 at the"), 1),
    ("doc: pair-split value",
     doc_plant("(+0.8165 under the pair split", "(+0.8175 under the pair "
               "split"), 1),
    ("doc: rogue share of L5",
     doc_plant("receives **0.62336 of L5**", "receives **0.72336 of L5**"),
     1),
    ("doc: rogue entitlement multiple",
     doc_plant("of L5** -- 179 times its entitlement",
               "of L5** -- 279 times its entitlement"), 1),
    ("doc: rmax amplification",
     doc_plant("**1.36x amplification**", "**1.06x amplification**"), 1),
    ("doc: rmax theta=0.75 share",
     doc_plant("**0.74597 at theta = 0.75**", "**0.54597 at theta = 0.75**"),
     1),
    ("doc: image RMS difference",
     doc_plant("627.4 DN RMS on a mean level", "427.4 DN RMS on a mean "
               "level"), 1),
    ("doc: image L5 amplification",
     doc_plant("**4.6459x at L5**", "**1.6459x at L5**"), 1),
    ("doc: fine-band stability claim",
     doc_plant("unchanged to within 0.2%", "unchanged to within 2.2%"), 1),
    ("doc: fraction of image moved",
     doc_plant("of the\nimage moves by more than 100 DN",
               "of the\nimage moves by more than 900 DN"), 1),
    ("doc: dense-ladder correspondence count",
     doc_plant("**8 of 8 rungs**", "**7 of 8 rungs**"), 1),
    ("doc: commissioning tolerance",
     doc_plant("recovers the closed form to within 0.009",
               "recovers the closed form to within 0.109"), 1),
    ("doc: S4 interior peak location",
     doc_plant("peak sits at signal fraction 0.10",
               "peak sits at signal fraction 0.30"), 1),
    ("doc: frame 46 exposure ratio",
     doc_plant("**0.249x, two stops dark**", "**0.649x, two stops dark**"),
     1),
    ("doc: a single table cell",
     doc_plant("| L5 | 0.62336 | 0.68246 | 0.70615 | 0.71944 | 179x | 206x |",
               "| L5 | 0.62336 | 0.68246 | 0.70615 | 0.71944 | 179x | 306x "
               "|"), 1),
    ("doc: a commissioning table cell",
     doc_plant("| 0.10 | 0.5714 | 0.5651 |", "| 0.10 | 0.5714 | 0.9651 |"),
     1),
    # ---- oracle plants: the checker must not carry its own answer --------
    ("oracle: subgate r_subgate on 112MSDCF",
     rec_plant("subgate.json",
               ["subjects", "112MSDCF", "rows", 0, "r_subgate"], mult=3.0),
     1),
    ("oracle: subgate dead pixel count",
     rec_plant("subgate.json",
               ["subjects", "coffee-bubbles", "rows", 0, "px_dead"],
               setval=12345), 1),
    ("oracle: ladder coffee-bubbles L4 top rung",
     rec_plant("subgate-ladder.json",
               ["subjects", "coffee-bubbles", "rungs", 4, "rows", 4,
                "sel_cost"], mult=1.5), 1),
    ("oracle: ladder bee pair-split L5",
     rec_plant("subgate-ladder.json",
               ["subjects", "bee-2-cpl@registered", "rungs", 4, "rows_pair",
                5, "sel_cost"], mult=1.2), 1),
    ("oracle: rogue shipping share at L5",
     rec_plant("rogue.json", ["rogue", 3, "shipping"], mult=1.3), 1),
    ("oracle: rogue rmax share at L6",
     rec_plant("rogue.json", ["rogue", 4, "rmax0.75"], mult=0.8), 1),
    ("oracle: frame 46 mean level",
     rec_plant("rogue.json", ["f46", "mean_dn"], mult=2.0), 1),
    ("oracle: dense ladder sel_cost at N=260",
     rec_plant("rogue.json", ["dense", 4, "sel_cost", "5"], setval=0.9), 1),
    ("oracle: commissioning sweep measured r",
     rec_plant("subgate.json", ["commission", "S2_sweep", 2, "r_med"],
               mult=1.4), 1),
    ("oracle: S4 peak location",
     rec_plant("subgate.json",
               ["commission", "S4_selection_cost", "argmax_sig_frac"],
               setval=0.3), 1),
    ("oracle: image RMS difference",
     rec_plant("rogue46.json", ["rms_diff_dn"], mult=1.4), 1),
    ("oracle: image band ratio at L5",
     rec_plant("rogue46.json", ["band_rms", 5, "ratio"], mult=0.5), 1),
    ("oracle: fraction of pixels over 100 DN",
     rec_plant("rogue46.json", ["frac_px_over_100dn"], mult=0.5), 1),
    # ---- placebo and refusal --------------------------------------------
    ("PLACEBO: prose edit that changes no measured value",
     doc_plant("That framing was wrong, and the instrument I built to support",
               "That framing was mistaken, and the instrument built to "
               "support"), 0),
    ("REFUSAL: unreadable record must exit 2", corrupt("rogue.json"), 2),
]


def main():
    tmp = tempfile.mkdtemp(prefix="vn_negctl25_")
    shutil.copy2(DOC, os.path.join(tmp, "RESULT.md"))
    for r in REC:
        shutil.copy2(os.path.join(OUT, r), os.path.join(tmp, r))

    rc0, _ = run()
    if rc0 != 0:
        print("REFUSED: the checker is not green before planting (rc %d). "
              "A negative control on a red checker measures nothing." % rc0)
        return 2

    caught, missed = [], []
    try:
        for name, plant, want in PLANTS:
            plant()
            rc, _ = run()
            if rc == want:
                caught.append(name)
            else:
                missed.append("%s: wanted exit %d, got %d" % (name, want, rc))
            shutil.copy2(os.path.join(tmp, "RESULT.md"), DOC)
            for r in REC:
                shutil.copy2(os.path.join(tmp, r), os.path.join(OUT, r))
    finally:
        shutil.copy2(os.path.join(tmp, "RESULT.md"), DOC)
        for r in REC:
            shutil.copy2(os.path.join(tmp, r), os.path.join(OUT, r))

    rc1, _ = run()
    ndoc = sum(1 for n, _, _ in PLANTS if n.startswith("doc:"))
    norc = sum(1 for n, _, _ in PLANTS if n.startswith("oracle:"))
    print("negative control for section 9.25")
    print("  plants           %d  (%d document, %d oracle, 1 placebo, "
          "1 refusal)" % (len(PLANTS), ndoc, norc))
    print("  behaved          %d" % len(caught))
    print("  MISBEHAVED       %d" % len(missed))
    print("  restored green   %s (exit %d)" % (rc1 == 0, rc1))
    for m in missed:
        print("  MISS %s" % m)
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if (not missed and rc1 == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
