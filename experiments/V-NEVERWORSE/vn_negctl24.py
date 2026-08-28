"""Commission vn_verify24.py: plant defects in section 9.24 and require RED.

Every anchor's occurrence count is verified to be exactly 1 before it is used,
and a plant that does not land is a hard error rather than a silent pass -- an
uncommissioned pin and an inert plant both look like one green.

Arms: PLANT must give rc=1, PLACEBO rc=0, CRASH rc=2. The crash arm exists
because a checker that dies and a checker that passes must never agree.

TWO PLANT FAMILIES, deliberately:

  DOCUMENT plants edit RESULT.md, and test that the checker reads the artifact.
  ORACLE plants edit the RECORD (a copy of a split JSON), and test that the
  checker is really deriving its expectations from the data rather than from
  constants of its own. A checker built the wrong way passes every document
  plant and fails every oracle plant to catch nothing at all -- that is the
  37/37-green-then-5-of-13 failure ORCH propagated across the fleet.

A plant that flips a REFUSED verdict into a number is included, because a
refusal silently replaced by a value is the specific failure the refusals in
this section exist to prevent.
"""
import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "RESULT.md")
CHK = os.path.join(HERE, "vn_verify24.py")
SPLIT = r"C:\dev\strehl-out\V-NEVERWORSE\split"
TMP = os.environ["TEMP"]
BAK = os.path.join(TMP, "vn_negctl24_RESULT.md")
CBAK = os.path.join(TMP, "vn_negctl24_verify24.py")
JBAK = {s: os.path.join(TMP, "vn_negctl24_%s.json" % s)
        for s in ("coffee-bubbles", "119MSDCF", "112MSDCF")}

# (anchor, replacement, label) -- edits to the DOCUMENT under test.
DOC_PLANTS = [
    ("| coffee-bubbles | 19 | 0.5404 | 0.5404 | 0.5404 | 0.00e+00 |",
     "| coffee-bubbles | 19 | 0.5404 | 0.5404 | 0.5405 | 0.00e+00 |",
     "hardspread: break the exact-invariance claim"),
    ("| 119MSDCF | 32 | 0.7571 | 0.7571 | 0.7571 | 0.00e+00 |",
     "| 119MSDCF | 32 | 0.7571 | 0.7571 | 0.7571 | 1.00e-09 |",
     "hardspread: nonzero spread"),
    ("three arms read `0.7571462134857859` to every digit",
     "three arms read `0.7571462134857858` to every digit",
     "the bit-identical value, last digit"),
    ("statistic scores **0.4946** on it",
     "statistic scores **0.0946** on it",
     "naive statistic on a perfect input"),
    ("| `recoh_flat` | -0.0558% / +2.7915% |",
     "| `recoh_flat` | +0.0558% / +2.7915% |",
     "margins: flip a wrong-way defect reading"),
    ("on 6 of the 9 defect-side readings",
     "on 5 of the 9 defect-side readings",
     "the wrong-way count I actually got wrong when drafting"),
    ("It fires from `sigma = 0.30 px`",
     "It fires from `sigma = 0.20 px`",
     "blur plant breakdown point"),
    ("where `fine` falls 3.54%",
     "where `fine` falls 3.94%",
     "fine fall at breakdown"),
    ("| coffee-bubbles | 19 | 55.576 | 8.04x | 4.38x | yes |",
     "| coffee-bubbles | 19 | 55.576 | 8.04x | 4.38x | NO |",
     "corpus: the rises-with-N verdict"),
    ("| 112MSDCF | 79 | 23.640 | 10.39x | 9.21x | yes |",
     "| 112MSDCF | 79 | 23.640 | 10.93x | 9.21x | yes |",
     "corpus: transposed digits in the headline excess"),
    ("| 119MSDCF | 32 | 38.6% | 48.9% | -20.2% |",
     "| 119MSDCF | 32 | 38.6% | 44.9% | -20.2% |",
     "fix table: the fine-band cost"),
    ("| 112MSDCF | 79 | 35.7% | 58.7% | -55.6% |",
     "| 112MSDCF | 79 | 35.7% | 58.7% | +55.6% |",
     "fix table: sign of the blur-immune verdict"),
    ("depth -- 28.5%, 48.9%, 58.7% -- so the blur-immune ratio",
     "depth -- 28.5%, 48.9%, 55.7% -- so the blur-immune ratio",
     "fix fine triple in prose"),
    ("ratio goes from +9.2% on the",
     "ratio goes from +9.8% on the",
     "fix efficiency, shallow subject"),
    ("to **-20.2%** and",
     "to **-20.9%** and",
     "fix efficiency, mid subject"),
    ("and **-55.6%** on the 32- and",
     "and **-55.9%** on the 32- and",
     "fix efficiency, deep subject"),
    ("observed-to-twin ratio is **1.006, 1.581, 0.752**",
     "observed-to-twin ratio is **1.006, 1.581, 0.762**",
     "twin ratio triple"),
    ("noise alone accounts for at most 63% of",
     "noise alone accounts for at most 73% of",
     "the derived twin share"),
    ("blur-immune ratio by **9.42x, 57.01x, 57.63x**",
     "blur-immune ratio by **9.42x, 57.01x, 47.63x**",
     "anti-blur: mean efficiency triple"),
    ("retaining 1.32%, 0.62%, 0.17% of the fine band",
     "retaining 1.32%, 0.62%, 0.71% of the fine band",
     "anti-blur: mean fine retained"),
    ("`argmax` reads 0.984 on the blur-immune ratio",
     "`argmax` reads 0.974 on the blur-immune ratio",
     "argmax efficiency ratio"),
    ("(157.2, 145.2, 148.3 at N = 4, 9, 19)",
     "(157.2, 135.2, 148.3 at N = 4, 9, 19)",
     "the plain mean's N-independent floor"),
    ("same pixels moves 5.9%, 15.1%, 9.7%.",
     "same pixels moves 5.9%, 15.1%, 9.8%.",
     "soft margins triple"),
    ("reproducibility there is 0.9972 and 0.9991,",
     "reproducibility there is 0.9972 and 0.9891,",
     "the focus-offset null"),
    ("`coffee-bubbles` (0.7408 -> 0.7407, PASS)",
     "`coffee-bubbles` (0.7408 -> 0.7409, PASS)",
     "the coin-flip pass reading"),
    ("`112MSDCF` (0.9780 -> 0.9781, FAIL)",
     "`112MSDCF` (0.9780 -> 0.9779, FAIL)",
     "the coin-flip fail reading"),
    ("statistic moves 0.46% under a 4x exponent range there",
     "statistic moves 0.86% under a 4x exponent range there",
     "119 blotch margin"),
    ("on the same render moves 5.38%",
     "on the same render moves 6.38%",
     "119 flatvar margin"),
    ("It removed 100.00% of the\nfine band",
     "It removed 100.10% of the\nfine band",
     "the over-strong plant's fine loss"),
    ("removes 48.9% of the fine band. **The build lane",
     "removes 44.9% of the fine band. **The build lane",
     "fine cost quoted beside the invariance finding"),
    ("| `recoh_all` | +0.0098% / +1.2692% | -0.0817% / +0.3214% | "
     "-0.0090% / +0.3712% | 0 of 3 |",
     "| `recoh_all` | +0.0098% / +1.2692% | -0.0817% / +0.3214% | "
     "-0.0090% / +0.3712% | 1 of 3 |",
     "margins: the admitted-on count"),
    ("| shipping | 19 | 0.4660 | REFUSED | REFUSED | REFUSED | 0.06512 |",
     "| shipping | 19 | 0.4660 | 0.7408 | REFUSED | REFUSED | 0.06512 |",
     "a REFUSED cell quietly replaced by the number behind it"),
    ("runs **42 plants**",
     "runs **41 plants**",
     "the negative control's own claimed reach"),
    ("Thirty-five edit the document",
     "Thirty-four edit the document",
     "document-plant count against the real list"),
    ("**Seven edit the record**",
     "**Eight edit the record**",
     "oracle-plant count against the real list"),
]

# (subject, json-path-mutator, label) -- edits to the ORACLE's own record.
# These must ALSO turn the checker red. If they do not, the checker is
# comparing the document against constants it carries rather than against
# the measurement.


def _mut_flatvar(d):
    for r in d["rows"]:
        if r["arm"] == "shipping" and r["N"] == d["ks"][0]:
            r["immune"]["flatvar_L3"] *= 1.10
            return True
    return False


def _mut_fine(d):
    for r in d["rows"]:
        if r["arm"] == "confidence" and r["N"] == d["ks"][0]:
            r["immune"]["fine"] *= 1.20
            return True
    return False


def _mut_admit(d):
    d["commission"]["arms"]["admit"]["recoh_flat"] = True
    return True


def _mut_twin(d):
    d["ceiling"][str(d["ks"][0])]["disc_soft"] *= 1.15
    return True


def _mut_counts(d):
    d["counts"]["measured"] += 1
    return True


def _mut_margin(d):
    d["commission"]["arms"]["margins"]["soft"][0] *= 1.30
    return True


def _mut_hard(d):
    d["commission"]["arms"]["defect"]["disc"]["disc_step"] += 1e-6
    return True


ORACLE_PLANTS = [
    ("coffee-bubbles", _mut_flatvar, "record: shipping flat mid-band variance"),
    ("coffee-bubbles", _mut_fine, "record: confidence fine-band power"),
    ("coffee-bubbles", _mut_admit, "record: un-refuse a refused statistic"),
    ("119MSDCF", _mut_twin, "record: the noise twin's discordance"),
    ("112MSDCF", _mut_counts, "record: break the self-summing partition"),
    ("119MSDCF", _mut_margin, "record: a commissioning margin"),
    ("112MSDCF", _mut_hard, "record: the exponent-invariance spread"),
]


def run():
    p = subprocess.run([sys.executable, CHK], capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    shutil.copyfile(DOC, BAK)
    shutil.copyfile(CHK, CBAK)
    for s, b in JBAK.items():
        shutil.copyfile(os.path.join(SPLIT, "%s.json" % s), b)
    caught, missed, errors = 0, [], []
    try:
        rc, out = run()
        if rc != 0:
            print("REFUSED: baseline is not green (rc=%d)\n%s" % (rc, out))
            return 2
        print("baseline green")

        base = io.open(DOC, encoding="utf-8").read()
        for anchor, repl, label in DOC_PLANTS:
            n = base.count(anchor)
            if n != 1:
                raise SystemExit("PLANT ANCHOR NOT UNIQUE (%d): %s" %
                                 (n, label))
            io.open(DOC, "w", encoding="utf-8",
                    newline="\n").write(base.replace(anchor, repl))
            rc, out = run()
            shutil.copyfile(BAK, DOC)
            if rc == 1:
                caught += 1
                print("  caught  doc     %s" % label)
            elif rc == 2:
                errors.append((label, out.strip().splitlines()[:1]))
                print("  ERROR   doc     %s" % label)
            else:
                missed.append(label)
                print("  MISSED  doc     %s" % label)

        for subj, mut, label in ORACLE_PLANTS:
            path = os.path.join(SPLIT, "%s.json" % subj)
            d = json.load(io.open(path, encoding="utf-8"))
            if not mut(d):
                raise SystemExit("ORACLE PLANT DID NOT LAND: %s" % label)
            json.dump(d, io.open(path, "w", encoding="utf-8"))
            rc, out = run()
            shutil.copyfile(JBAK[subj], path)
            if rc == 1:
                caught += 1
                print("  caught  oracle  %s" % label)
            elif rc == 2:
                errors.append((label, out.strip().splitlines()[:1]))
                print("  ERROR   oracle  %s" % label)
            else:
                missed.append(label)
                print("  MISSED  oracle  %s" % label)

        # PLACEBO: a prose edit that changes no measured value.
        placebo = base.replace(
            "#### 9.24.11 What I did not measure",
            "#### 9.24.11 What I did not measure, and will not claim")
        if placebo == base:
            raise SystemExit("PLACEBO DID NOT LAND")
        io.open(DOC, "w", encoding="utf-8", newline="\n").write(placebo)
        rc, out = run()
        shutil.copyfile(BAK, DOC)
        placebo_ok = (rc == 0)
        print("  placebo rc=%d %s" % (rc, "ok" if placebo_ok else "FALSE FAIL"))

        # CRASH: the record is unreadable. Must be rc=2, never 0 or 1.
        path = os.path.join(SPLIT, "coffee-bubbles.json")
        io.open(path, "w", encoding="utf-8").write("{ not json")
        rc, out = run()
        shutil.copyfile(JBAK["coffee-bubbles"], path)
        crash_ok = (rc == 2)
        print("  crash   rc=%d %s" % (rc, "ok" if crash_ok else "WRONG"))
    finally:
        shutil.copyfile(BAK, DOC)
        shutil.copyfile(CBAK, CHK)
        for s, b in JBAK.items():
            shutil.copyfile(b, os.path.join(SPLIT, "%s.json" % s))

    total = len(DOC_PLANTS) + len(ORACLE_PLANTS)
    print("\n  caught     : %d" % caught)
    print("  MISSED     : %d" % len(missed))
    print("  ERRORED    : %d" % len(errors))
    print("  -----------------")
    print("  total      : %d plants (%d document + %d oracle)"
          % (total, len(DOC_PLANTS), len(ORACLE_PLANTS)))
    for m in missed:
        print("  MISSED   %s" % m)
    for label, head in errors:
        print("  ERRORED  %s :: %s" % (label, head))

    same = io.open(DOC, encoding="utf-8").read() == \
        io.open(BAK, encoding="utf-8").read()
    print("  restored byte-identical: %s" % same)
    return 0 if (caught == total and not missed and not errors
                 and placebo_ok and crash_ok and same) else 1


if __name__ == "__main__":
    sys.exit(main())
