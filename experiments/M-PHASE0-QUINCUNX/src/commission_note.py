"""commission_note.py -- prove check_note.py can fail.

A checker that has only ever returned GREEN is an untested instrument. This
plants a defect at a time and requires the checker to go RED *and to name the
right check*. Requiring only a RED exit code would pass even if some unrelated
check happened to break.

THREE FAMILIES OF PLANT
-----------------------
TEXT  a number or sentence altered in the note. Exercises DERIVED and CLAIM.
DATA  a value altered in the lane's stored JSON. Exercises PINNED -- without
      these, 23 of the 64 checks would never have been shown to fire.
BOTH  a number altered consistently in note AND JSON. This is the plant that
      matters most: it is what a wrong-but-self-consistent run looks like, and
      only a checker that re-derives from primary data can catch it.

INERT PLANT DETECTION
---------------------
Every anchor is compiled to a \\s+-joined regex and must resolve to exactly one
site in the raw file. A plant that silently fails to apply produces a GREEN that
is indistinguishable from a caught defect; resolve_once() hard-errors instead.
Substitution is token-by-token so the original line wrapping is preserved and
the planted file differs from the original in the value alone.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(LANE))
NOTE = os.path.join(ROOT, "docs", "research", "M-PHASE0-QUINCUNX.md")
Q1 = os.path.join(LANE, "out", "q1-band.json")
Q2 = os.path.join(LANE, "out", "q2-bhyp.json")
CHECK = os.path.join(HERE, "check_note.py")

ORIG = open(NOTE, encoding="utf-8").read()


def wrap_re(phrase):
    return re.compile(r"\s+".join(re.escape(t) for t in phrase.split()))


def resolve_once(phrase, label):
    hits = list(wrap_re(phrase).finditer(ORIG))
    if len(hits) != 1:
        print("FATAL: plant %r anchor matched %d sites (need exactly 1)"
              % (label, len(hits)))
        print("       INERT PLANT -- would have produced a false CAUGHT.")
        sys.exit(2)
    return hits[0]


def retoken(matched, old, new):
    to, tn = old.split(), new.split()
    assert len(to) == len(tn), "token count differs: %r vs %r" % (old, new)
    out, i = [], 0
    for p in re.split(r"(\s+)", matched):
        if p.strip() == "":
            out.append(p)
        else:
            out.append(tn[i])
            i += 1
    assert i == len(tn)
    return "".join(out)


# ---------------------------------------------------------------- the plants
# (label, expected failing check, kind, payload)
#   TEXT payload: (old phrase, new phrase)
#   DATA payload: (json file, dotted path, new value)
#   BOTH payload: (old, new, json file, dotted path, new value)
TEXT_PLANTS = [
    ("headline multiple f5.6", "headline multiples",
     "**12.0\u00d7, 15.3\u00d7", "**12.1\u00d7, 15.3\u00d7"),
    ("headline multiple f14", "headline multiples",
     "17.8\u00d7 and 1.8\u00d7** a detection",
     "17.8\u00d7 and 1.9\u00d7** a detection"),
    ("f11 vs f5.6 snr", "f11 strongest vs f5.6",
     "median power SNR 0.823 against", "median power SNR 0.824 against"),
    ("apertures detected", "apertures detected",
     "detected at **4 of 5** corpus", "detected at **5 of 5** corpus"),
    ("band lower edge", "band edges",
     "**(0.260, 0.330) sensor cyc/px**", "**(0.250, 0.330) sensor cyc/px**"),
    ("lattice pitch", "lattice GQ quincunx",
     "| GQ quincunx | 7.2408 |", "| GQ quincunx | 7.2400 |"),
    ("lattice nyquist", "lattice G1 or G2 alone",
     "| G1 or G2 alone | 10.2400 | 48.83 |",
     "| G1 or G2 alone | 10.2400 | 48.84 |"),
    ("quincunx reach", "quincunx reach",
     "reaches only **0.35355**, the inscribed",
     "reaches only **0.35356**, the inscribed"),
    ("cell count", "cell count",
     "for 30 cells", "for 36 cells"),
    ("null mean", "null mean/sd",
     "mean **\u22120.0198**, sd", "mean **\u22120.0199**, sd"),
    ("null sd", "null mean/sd",
     "sd **0.0088** over 6 cells", "sd **0.0089** over 6 cells"),
    ("threshold", "threshold",
     "= **0.0462**", "= **0.0463**"),
    ("table row f11 count", "row f/11",
     "| f/11 | 11.314 | 6/6 | +0.823 | 17.8 |",
     "| f/11 | 11.314 | 5/6 | +0.823 | 17.8 |"),
    ("table row f18 sign", "row f/18",
     "| f/18 | 17.959 | 0/6 | \u22120.021 | \u22120.4 |",
     "| f/18 | 17.959 | 0/6 | +0.021 | \u22120.4 |"),
    ("table row f14 median", "row f/14",
     "| f/14 | 14.254 | 5/6 | +0.083 | 1.8 |",
     "| f/14 | 14.254 | 5/6 | +0.084 | 1.8 |"),
    ("floor extremes", "floor extremes",
     "(99.3 against f/5.6's 3762.2)", "(99.3 against f/5.6's 3762.3)"),
    ("cells above 1", "n_above_1 framing",
     "only 2 of 30 cells clear it", "only 3 of 30 cells clear it"),
    ("cutoff f11 H2", "cutoff row f/11",
     "| f/11 | 11.314 | 0.2205 | 0.2675 | 0.3426 |",
     "| f/11 | 11.314 | 0.2205 | 0.2676 | 0.3426 |"),
    ("cutoff f18 H3", "cutoff row f/18",
     "| f/18 | 17.959 | 0.1389 | 0.1685 | 0.2158 |",
     "| f/18 | 17.959 | 0.1389 | 0.1685 | 0.2159 |"),
    ("transfer swing", "transfer swing",
     "by a factor of **\u221225.7** from", "by a factor of **\u221225.6** from"),
    ("f5.6 to f8 rise", "f5.6->f8 rise",
     "rises 1.916\u00d7** from f/5.6", "rises 1.917\u00d7** from f/5.6"),
    ("bracket upper", "bracket hi line",
     "=>  B < 2.5118", "=>  B < 2.5119"),
    ("bracket lower", "bracket lo line",
     "=>  B > 1.9936", "=>  B > 1.9937"),
    ("bracket headline", "bracket headline",
     "**1.994 \u2013 2.512**, excluding two",
     "**1.994 \u2013 2.513**, excluding two"),
    ("H3 verdict flipped", "hyp row H3",
     "| H3 | 2.402 | yes |", "| H3 | 2.402 | no |"),
    ("H1 verdict flipped", "hyp row H1",
     "| H1 | 3.732 | no \u2014 excluded |", "| H1 | 3.732 | no \u2014 included |"),
    ("lambda 500 bracket", "lambda 0.500 bracket",
     "brackets 2.193\u20132.763 at 0.500",
     "brackets 2.193\u20132.764 at 0.500"),
    ("lambda 600 bracket", "lambda 0.600 bracket",
     "and 1.827\u20132.302 at 0.600", "and 1.827\u20132.303 at 0.600"),
    ("f14 z margin", "f14 z",
     "**11.7 null sd** above", "**11.8 null sd** above"),
    ("f14 floor ratio", "f14 floor ratio",
     "within 50% of f/18's", "within 51% of f/18's"),
    ("C1 relative", "C1 agreement quoted",
     "to 8.13e-15 relative (control C1)", "to 8.13e-14 relative (control C1)"),
    ("cut location claim", "cut location",
     "the cut falls between f/14 and f/18**, not between",
     "the cut falls between f/5.6 and f/11**, not between"),
    ("M88 attribution removed", "M88 attribution",
     "attributing that to M88. Measured, **f/11 is the",
     "attributing that to M90. Measured, **f/11 is the"),
    ("scope claim weakened", "kill gate only",
     "**This lane answers C12's kill gate and only its kill gate.**",
     "**This lane answers C12's phase-0 gate and all of its items.**"),
    ("open items hidden", "three items open",
     "**None of those three is answered here.** They need per-frame G1/G2 planes",
     "**All three of those are answered here.** They need per-frame G1/G2 planes"),
    ("H3 election claim", "H3 not robust",
     "This evidence does not elect H3.", "This evidence does not elect H2."),
    ("C3 disclosure removed", "median disclosure",
     "**Every reported \"median\" was biased upward, and no control caught it.**",
     "**Every reported \"median\" was biased upward, and one control caught it.**"),
    ("median attribution removed", "median found by checker",
     "It was found by `check_note.py`, which re-derives the same quantities",
     "It was found by `commission_note.py`, which re-derives the same quantities"),
    ("median controls claim", "median controls blind",
     "None of the five controls could see it, because all five compare the lane to",
     "None of the five controls could see it, because all six compare the lane to"),
    ("banding attribution flipped", "banding was mine",
     "A second discrepancy in the same run was my checker's fault, not the lane's.",
     "A second discrepancy in the same run was the lane's fault, not my checker's."),
    ("monotonicity disclosure", "C3 disclosure",
     "The monotonicity control had a wrong premise.",
     "The monotonicity control had a sound premise."),
    ("bar disclosure removed", "bar disclosure",
     "**The detection bar was arbitrary.**",
     "**The detection bar was principled.**"),
    ("blinder direction", "blinder direction",
     "they made the instrument look blinder than it is",
     "they made the instrument look sharper than it is"),
]

DATA_PLANTS = [
    ("run null mean", "run agrees: null mean", Q1, "c5_null.mean", -0.0199),
    ("run null sd", "run agrees: null sd", Q1, "c5_null.sd", 0.0089),
    ("run threshold", "run agrees: threshold", Q1, "c5_null.threshold", 0.0463),
    ("run median f11", "run agrees: median f11", Q1,
     "q2.f11.median_snr", 0.8230),
    ("run floor f18", "run agrees: floor f18", Q1,
     "q2.f18.median_floor", 99.4),
    ("run ndet f14", "run agrees: ndet f14", Q1,
     "detections.f14.n_detected", 6),
    ("run rise", "run agrees: rise f5.6->f8", Q1, "rise_f56_to_f8", 1.917),
    ("run bracket lo", "run agrees: bracket lo", Q2, "bracket.lo", 1.9937),
    ("run bracket hi", "run agrees: bracket hi", Q2, "bracket.hi", 2.5119),
    ("run f14 z", "run agrees: f14 z", Q2, "c10_f14_z", 11.8),
]

# The self-consistent plant: note and run agree with each other and are both
# wrong. Only the DERIVED re-derivation from M129's raw spectra can see this.
BOTH_PLANTS = [
    ("self-consistent median f11", "f11 strongest vs f5.6",
     "median power SNR 0.823 against", "median power SNR 0.824 against",
     Q1, "q2.f11.median_snr", 0.824),
    ("self-consistent rise", "f5.6->f8 rise",
     "rises 1.916\u00d7** from f/5.6", "rises 1.917\u00d7** from f/5.6",
     Q1, "rise_f56_to_f8", 1.917),
]


def setpath(obj, dotted, val):
    parts = dotted.split(".")
    for p in parts[:-1]:
        obj = obj[p]
    if parts[-1] not in obj:
        print("FATAL: json path %r missing -- INERT PLANT" % dotted)
        sys.exit(2)
    if obj[parts[-1]] == val:
        print("FATAL: json path %r already equals %r -- INERT PLANT"
              % (dotted, val))
        sys.exit(2)
    obj[parts[-1]] = val


def run(note_path, q1_path, q2_path):
    env = dict(os.environ)
    env["NOTE_PATH"] = note_path
    env["Q1_PATH"] = q1_path
    env["Q2_PATH"] = q2_path
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, CHECK], capture_output=True, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace").replace("\r\n", "\n")


caught, missed = [], []
tmp = tempfile.mkdtemp(prefix="quincunx-commission-")
try:
    # ---- null run: nothing planted must be GREEN --------------------------
    rc, out = run(NOTE, Q1, Q2)
    if rc != 0:
        print("FATAL: null run is not GREEN. Fix the checker before "
              "commissioning it.")
        print(out)
        sys.exit(2)
    print("null run GREEN (unmodified inputs)")
    print("")

    def attempt(label, expect, note_txt, q1_obj, q2_obj):
        np_ = os.path.join(tmp, "note.md")
        q1p = os.path.join(tmp, "q1.json")
        q2p = os.path.join(tmp, "q2.json")
        open(np_, "w", encoding="utf-8").write(note_txt)
        json.dump(q1_obj, open(q1p, "w", encoding="utf-8"))
        json.dump(q2_obj, open(q2p, "w", encoding="utf-8"))
        rc, out = run(np_, q1p, q2p)
        named = ("] %s\n" % expect) in out or ("] %s " % expect) in out
        if rc != 0 and named:
            caught.append(label)
            print("  CAUGHT   %-32s -> %s" % (label, expect))
        elif rc != 0:
            missed.append((label, "went RED but did not name %r" % expect))
            print("  WRONG    %-32s -> RED, but not via %s" % (label, expect))
        else:
            missed.append((label, "GREEN"))
            print("  MISSED   %-32s -> checker stayed GREEN" % label)

    base1 = json.load(open(Q1, encoding="utf-8"))
    base2 = json.load(open(Q2, encoding="utf-8"))

    print("TEXT plants (exercise DERIVED and CLAIM)")
    print("-" * 74)
    for label, expect, old, new in TEXT_PLANTS:
        m = resolve_once(old, label)
        txt = ORIG[:m.start()] + retoken(m.group(0), old, new) + ORIG[m.end():]
        if txt == ORIG:
            print("FATAL: plant %r produced an identical file -- INERT" % label)
            sys.exit(2)
        attempt(label, expect, txt, base1, base2)

    print("")
    print("DATA plants (exercise PINNED)")
    print("-" * 74)
    for label, expect, path, dotted, val in DATA_PLANTS:
        a = json.loads(json.dumps(base1))
        b = json.loads(json.dumps(base2))
        setpath(a if path == Q1 else b, dotted, val)
        attempt(label, expect, ORIG, a, b)

    print("")
    print("BOTH plants (a wrong run and a note that agrees with it)")
    print("-" * 74)
    for label, expect, old, new, path, dotted, val in BOTH_PLANTS:
        m = resolve_once(old, label)
        txt = ORIG[:m.start()] + retoken(m.group(0), old, new) + ORIG[m.end():]
        a = json.loads(json.dumps(base1))
        b = json.loads(json.dumps(base2))
        setpath(a if path == Q1 else b, dotted, val)
        attempt(label, expect, txt, a, b)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

total = len(TEXT_PLANTS) + len(DATA_PLANTS) + len(BOTH_PLANTS)
print("")
print("=" * 74)
for label, why in missed:
    print("  NOT CAUGHT: %-32s (%s)" % (label, why))
print("caught      %3d" % len(caught))
print("not caught  %3d" % len(missed))
print("-" * 30)
print("total       %3d plants" % total)
assert len(caught) + len(missed) == total, "plant accounting does not sum"
print("")
print("VERDICT: %s" % ("COMMISSIONED" if not missed else "NOT COMMISSIONED"))
sys.exit(0 if not missed else 1)
