"""Commission vn_verify9.py: plant defects in section 9 and require RED.

Every anchor's occurrence count is verified to be exactly 1 before it is used,
and a plant that does not land is a hard error rather than a silent pass.

Arms: PLANT must give rc=1, PLACEBO rc=0, CRASH rc=2. The crash arm exists
because a checker that dies and a checker that passes must never agree.
"""
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "RESULT.md")
CHK = os.path.join(HERE, "vn_verify9.py")
BAK = os.path.join(os.environ["TEMP"], "vn_negctl9_RESULT.md")
CBAK = os.path.join(os.environ["TEMP"], "vn_negctl9_verify9.py")

PLANTS = [
    ("| L3 | 8 | 5.49 | 2.42 | 2.02 | 0.371 | 13.9 px | **0.543** |",
     "| L3 | 8 | 5.49 | 2.42 | 2.02 | 0.371 | 13.9 px | **0.443** |",
     "L3 frac 20-60px"),
    ("| L1 | 2 | 8.00 | 1.36 | 1.16 | **0.680** | 3.5 px | 0.026 |",
     "| L1 | 2 | 8.00 | 1.36 | 1.16 | **0.580** | 3.5 px | 0.026 |",
     "L1 single-winner"),
    ("| L0 | 1 | 8.00 | 17.75 | 19.00 | 0.065 | 1.7 px | 0.000 |",
     "| L0 | 1 | 8.00 | 16.75 | 19.00 | 0.065 | 1.7 px | 0.000 |",
     "L0 n_eff"),
    ("| a. shipping (`2 3 4 5 8 8 8`) | 0.06716 | **1.354x** | 0.06905 | 0.755 |",
     "| a. shipping (`2 3 4 5 8 8 8`) | 0.06716 | **1.254x** | 0.06905 | 0.755 |",
     "shipping ratio"),
    ("| b. plain unweighted mean | 0.04874 | **0.983x** | 0.01986 | **0.217** |",
     "| b. plain unweighted mean | 0.04874 | **0.983x** | 0.01986 | **0.317** |",
     "plain-mean sharpness"),
    ("| c. exponent 1, flat ramp | 0.05714 | **1.152x** | 0.06269 | 0.685 |",
     "| c. exponent 1, flat ramp | 0.05714 | **1.152x** | 0.06269 | 0.785 |",
     "exp1 sharpness"),
    ("= **57%** of the merge-attributable excess", 
     "= **67%** of the merge-attributable excess", "derived 57%"),
    ("a **9.3%** relative sharpness cost", "a **7.3%** relative sharpness cost",
     "derived sharpness cost"),
    ("destroys\n**78% of the sharpness**", "destroys\n**68% of the sharpness**",
     "derived mean loss"),
    ("| x0.5 | 1.327x | 1.141x | exp-1 lower |",
     "| x0.5 | 1.327x | 1.241x | exp-1 lower |", "varscale x0.5"),
    ("scores `coffee-bubbles` at **1.354x**",
     "scores `coffee-bubbles` at **1.454x**", "reimplementation fidelity"),
    ("shipped master scores **1.444x**", "shipped master scores **1.544x**",
     "shipped master fidelity"),
    ("but **min 300, max 2700, overall std 61.87**",
     "but **min 300, max 2700, overall std 71.87**", "expand bug std"),
    ("> The rate is driven by the selection exponent, not the gate: 0 violations at",
     "> The rate is driven by the selection exponent, not the gate: 9 violations at",
     "quote fidelity (word changed)"),
    ("**3 requested = 3 measured + 0 not attempted + 0 failed.**",
     "**3 requested = 2 measured + 0 not attempted + 0 failed.**",
     "subject partition"),
    ("| `112MSDCF` | 79 | 1.122x | **1.053x** | 1.099x | 1.260x |",
     "| `112MSDCF` | 79 | 1.122x | **0.953x** | 1.099x | 1.260x |",
     "9.6 arms: plain mean below 1 (kills the 2-of-3 claim)"),
    ("| `flat-on-ruler-cpl` | 73 | 1.287x | **1.229x** | 1.261x | 1.297x |",
     "| `flat-on-ruler-cpl` | 73 | 1.287x | **1.229x** | 1.161x | 1.297x |",
     "9.6 arms: exponent-1 cell"),
    ("| `coffee-bubbles` | 19 | 1.354x | **0.983x** | 1.152x | 1.444x |",
     "| `coffee-bubbles` | 18 | 1.354x | **0.983x** | 1.152x | 1.444x |",
     "9.6 arms: OK frame count"),
    ("| `flat-on-ruler-cpl` | 20.3% | **9.1%** | 30.2% |",
     "| `flat-on-ruler-cpl` | 20.3% | **9.1%** | 20.2% |",
     "9.6 shares: sharpness cost"),
    ("| `112MSDCF` | 56.3% | **19.1%** | 25.3% |",
     "| `112MSDCF` | 66.3% | **19.1%** | 25.3% |",
     "9.6 shares: selection-attributable"),
    ("| `112MSDCF` | 1.814 | **0.131** | 1.355 |",
     "| `112MSDCF` | 1.814 | **0.231** | 1.355 |",
     "9.8 sharpness: plain mean"),
    ("| `flat-on-ruler-cpl` | 0.156 | 0.083 | 0.154 | 0.366 | 0.327 | 0.215 | 0.000 | **0.693** |",
     "| `flat-on-ruler-cpl` | 0.156 | 0.083 | 0.154 | 0.366 | 0.327 | 0.215 | 0.000 | **0.793** |",
     "9.8 plateau: L3+L4 sum"),
    ("| `112MSDCF` | 0.002 | 0.017 | 0.125 | 0.460 | 0.669 | 0.354 | 0.000 | **1.129** |",
     "| `112MSDCF` | 0.002 | 0.017 | 0.125 | 0.560 | 0.669 | 0.354 | 0.000 | **1.129** |",
     "9.8 plateau: L3 cell"),
    ("of the three is 19.1%", "of the three is 29.1%", "9.6 median ceiling"),
    ("**79 in the stack = 73\nadmitted + 5 unregistered + 1 poor-registration.**",
     "**79 in the stack = 73\nadmitted + 4 unregistered + 1 poor-registration.**",
     "frame partition sum"),
    ("**79 in the stack = 73\nadmitted + 5 unregistered + 1 poor-registration.**",
     "**78 in the stack = 72\nadmitted + 5 unregistered + 1 poor-registration.**",
     "frame partition vs record"),
    # ---- plants in 9.11 - 9.16, added with the sections ----
    ("| 64.0 (shipping) | 0.002793 | 0 (reference) | 0 |",
     "| 64.0 (shipping) | 0.002893 | 0 (reference) | 0 |",
     "9.11 shipping clamp-binding fraction"),
    ("| 1.0 | 0.000041 | **606.3 DN** | **0.4666** |",
     "| 1.0 | 0.000041 | **606.3 DN** | **0.4566** |",
     "9.11 normalised-weight delta"),
    ("| 4096.0 | 0.163599 | **1060 DN** | 0.8075 |",
     "| 4096.0 | 0.163599 | **1060 DN** | 0.9075 |",
     "9.11 high-SNR_REF weight delta"),
    ("binds on **1 coefficient in 358** at the shipping value",
     "binds on **1 coefficient in 258** at the shipping value",
     "9.11 derived one-in-N"),
    ("| 4 (flattest) | 2554 | **2.28** | 0.695 | **0.316** |",
     "| 4 (flattest) | 2554 | **2.28** | 0.695 | **0.416** |",
     "9.12 flattest single-winner"),
    ("| 0 (most structured) | 2554 | 2.50 | 0.652 | 0.256 |",
     "| 0 (most structured) | 2554 | 2.50 | 0.652 | 0.356 |",
     "9.12 structured single-winner"),
    ("| shipping merge | 0.6385 | 0.0717 | **+0.5668** | 1.000 |",
     "| shipping merge | 0.6385 | 0.0717 | **+0.4668** | 1.000 |",
     "9.12 coherence excess"),
    ("| null: same scene, no focus signal | 0.4928 | 0.0535 | +0.4392 | 0.992 |",
     "| null: same scene, no focus signal | 0.4928 | 0.0535 | +0.3392 | 0.992 |",
     "9.12 null excess"),
    ("**77.5% of the coherence excess survives that**",
     "**67.5% of the coherence excess survives that**",
     "9.12 derived survival percentage"),
    ("| confidence | `kappa` 0.010 | 1.219x | 0.720x | **-0.0113** |",
     "| confidence | `kappa` 0.010 | 1.219x | 0.720x | **-0.0213** |",
     "9.13 frontier gap cell"),
    ("| scalar | `exponent` 1.2 | 1.214x | 0.725x | -- |",
     "| scalar | `exponent` 1.2 | 1.214x | 0.825x | -- |",
     "9.13 scalar frontier sharpness"),
    ("| 0.90 | **1.160x** | 0.708x |",
     "| 0.90 | **1.150x** | 0.708x |",
     "9.13 oracle best blotch"),
    ("largest gain anywhere is +0.0033 blotch",
     "largest gain anywhere is +0.0133 blotch",
     "9.13 derived largest frontier gain"),
    ("| best confidence arm | 1.196x | **44.6%** |",
     "| best confidence arm | 1.196x | **54.6%** |",
     "9.13 derived fix ceiling percentage"),
    ("| shipping, as delivered | 2.08466 | 99.46558 | **1.840x** | 1.149x |",
     "| shipping, as delivered | 2.08466 | 99.46558 | **1.740x** | 1.149x |",
     "9.14 shipping band ratio"),
    ("| plain unweighted mean | 0.28218 | 19.86664 | **0.249x** | 0.229x |",
     "| plain unweighted mean | 0.28218 | 19.86664 | **0.849x** | 0.229x |",
     "9.14 plain-mean ratio (kills the sqrt-n control)"),
    ("| hard admission threshold only | 1.264x | **63.8%** |",
     "| hard admission threshold only | 1.264x | **53.8%** |",
     "9.14 admission share"),
    ("they sum to 148%", "they sum to 158%", "9.14 derived share total"),
    ("intends -- removes **26.0%**", "intends -- removes **36.0%**",
     "9.14 derived exponent removal"),
    ("| shipping, as delivered | 1.06870 | 45.85142 | **3.160x** | 1.755x |",
     "| shipping, as delivered | 1.06870 | 45.85142 | **3.060x** | 1.755x |",
     "9.14b shipping band ratio"),
    ("| hard admission threshold only, 79 frames | 1.616x | **49.3%** |",
     "| hard admission threshold only, 79 frames | 1.616x | **59.3%** |",
     "9.14b admission share"),
    ("**7.39x on 19 frames and 27.46x on 79**",
     "**7.39x on 19 frames and 24.46x on 79**",
     "9.14b depth claim"),
    ("**7.39x on 19 frames and 27.46x on 79**",
     "**27.46x on 19 frames and 7.39x on 79**",
     "9.14b depth claim, direction reversed"),
    ("at 138%, so the two mechanisms are again redundant",
     "at 128%, so the two mechanisms are again redundant",
     "9.14b derived share total"),
    ("best\ncase removes **34.4%**", "best\ncase removes **44.4%**",
     "9.14b derived exponent removal"),
    ("**4 requested = 4 measured + 0 refused + 0 failed.**",
     "**4 requested = 3 measured + 0 refused + 0 failed.**",
     "9.16 asks partition sum"),
    ("**2 attempted = 2 measured +\n0 refused + 0 failed.**",
     "**2 attempted = 1 measured +\n0 refused + 0 failed.**",
     "9.16 manufacture subject partition sum"),
]


PLANTS += [
    ('| shipping | 19 | 0.0783 | 0.0117 | 0.0062 | 0.0033 | 0.06716 | 1.78 | 0.755 | **0.30** |',
     '| shipping | 19 | 0.0983 | 0.0117 | 0.0062 | 0.0033 | 0.06716 | 1.78 | 0.755 | **0.30** |',
     '9.17 cb shipping N=19 band 0.10-0.15'),
    ('| shipping | 19 | 0.0783 | 0.0117 | 0.0062 | 0.0033 | 0.06716 | 1.78 | 0.755 | **0.30** |',
     '| shipping | 19 | 0.0783 | 0.0117 | 0.0062 | 0.0033 | 0.06716 | 1.78 | 0.755 | **0.40** |',
     '9.17 cb shipping N=19 SNR'),
    ('| argmax | 19 | 0.0780 | 0.0119 | 0.0061 | 0.0033 | 0.07481 | 1.00 | 1.000 | 0.29 |',
     '| argmax | 19 | 0.0780 | 0.0119 | 0.0061 | 0.0033 | 0.07481 | 1.00 | 0.900 | 0.29 |',
     '9.17 cb argmax N=19 share (breaks the no-dilution control)'),
    ('| mean | 19 | 0.0411 | 0.0149 | 0.0068 | 0.0020 | 0.04874 | 19.00 | 0.053 | 0.69 |',
     '| mean | 19 | 0.0411 | 0.0149 | 0.0068 | 0.0020 | 0.04874 | 18.00 | 0.053 | 0.69 |',
     '9.17 cb mean N=19 n_eff'),
    ('| shipping | 79 | 0.1088 | 0.0308 | 0.0167 | 0.0092 | 0.21187 | 3.60 | 0.470 | **1.28** |',
     '| shipping | 79 | 0.1088 | 0.0308 | 0.0167 | 0.0092 | 0.21187 | 3.60 | 0.470 | **1.38** |',
     '9.17 112 shipping N=79 SNR'),
    ('| confidence | 79 | 0.1168 | 0.0386 | 0.0210 | 0.0107 | 0.20721 | 19.22 | 0.142 | 1.21 |',
     '| confidence | 79 | 0.1168 | 0.0386 | 0.0210 | 0.0107 | 0.20721 | 9.22 | 0.142 | 1.21 |',
     '9.17 112 confidence N=79 n_eff'),
    ('| argmax | 79 | 0.1043 | 0.0286 | 0.0157 | 0.0090 | 0.22411 | 1.00 | 1.000 | 1.24 |',
     '| argmax | 79 | 0.1043 | 0.0286 | 0.0157 | 0.0090 | 0.22411 | 1.00 | 1.100 | 1.24 |',
     '9.17 112 argmax N=79 share'),
    ('| confidence | 79 | 0.1168 | 0.0386 | 0.0210 | 0.0107 | 0.20721 | 19.22 | 0.142 | 1.21 |',
     '| confidence | 79 | 0.1168 | 0.0386 | 0.0210 | 0.0107 | 0.20821 | 19.22 | 0.142 | 1.21 |',
     '9.17 112 confidence N=79 blotch'),
    ('| `coffee-bubbles` | shipping | 0.9892 | **0.8157** |',
     '| `coffee-bubbles` | shipping | 0.9892 | **0.8457** |',
     '9.17 cb shipping noise-corrected ratio'),
    ('| `112MSDCF` | shipping | 1.2805 *(reads sharper)* | **0.9378** *(is softer)* |',
     '| `112MSDCF` | shipping | 1.3805 *(reads sharper)* | **0.9378** *(is softer)* |',
     '9.17 112 shipping raw ratio'),
    ('| `coffee-bubbles`, 9 -> 19 | -0.1843 | -0.1342 | **27.2%** |',
     '| `coffee-bubbles`, 9 -> 19 | -0.1843 | -0.1342 | **37.2%** |',
     '9.17 fix ceiling on coffee-bubbles'),
    ('| `112MSDCF`, 39 -> 79 | -0.0622 | -0.0900 | **-44.6%** |',
     '| `112MSDCF`, 39 -> 79 | -0.0622 | -0.0900 | **44.6%** |',
     '9.17 fix ceiling sign on 112MSDCF'),
    ('| `coffee-bubbles` | argmax | 1.000 -> 1.000 | **none, by construction** | **-0.194** |',
     '| `coffee-bubbles` | argmax | 1.000 -> 1.000 | **none, by construction** | **-0.094** |',
     '9.18 cb argmax softening'),
    ('| `112MSDCF` | mean | 0.026 -> 0.013 | **x0.494, maximal** | **-0.032** |',
     '| `112MSDCF` | mean | 0.026 -> 0.013 | **x0.594, maximal** | **-0.032** |',
     '9.18 112 mean dilution'),
    ('| `112MSDCF` | confidence | 0.245 -> 0.142 | x0.579 | -0.090 |',
     '| `112MSDCF` | confidence | 0.245 -> 0.142 | x0.579 | -0.060 |',
     '9.18 112 confidence softening'),
    ('softening is **-0.929**, which reads as the hypothesis being contradicted in',
     'softening is **-0.829**, which reads as the hypothesis being contradicted in',
     '9.18 coffee-bubbles correlation'),
    ('sign. On `112MSDCF` it is only **-0.155**. The strong anti-correlation is a',
     'sign. On `112MSDCF` it is only **-0.255**. The strong anti-correlation is a',
     '9.18 112MSDCF correlation'),
    ('| `coffee-bubbles` | 19 | **24.82x** |',
     '| `coffee-bubbles` | 19 | **14.82x** |',
     '9.19 cb premium at N=19'),
    ('| `112MSDCF` | 79 | **240.70x** |',
     '| `112MSDCF` | 79 | **140.70x** |',
     '9.19 112 premium at N=79'),
    ('prediction for `112MSDCF` at **N=79** was a selection premium of **153.2**,',
     'prediction for `112MSDCF` at **N=79** was a selection premium of **253.2**,',
     '9.20 pre-registered point prediction'),
    ('**Measured: 240.70. Growth 10.36x against a predicted 6.17x. The model is',
     '**Measured: 220.70. Growth 10.36x against a predicted 6.17x. The model is',
     '9.20 the measurement itself'),
    ('**Measured: 240.70. Growth 10.36x against a predicted 6.17x. The model is',
     '**Measured: 240.70. Growth 6.36x against a predicted 6.17x. The model is',
     '9.20 measured growth'),
    ('The miss is only 4.8% outside the interval and it is in the direction that',
     'The miss is only 0.8% outside the interval and it is in the direction that',
     '9.20 size of the miss'),
    ('the two subjects give an empirical exponent of **N^1.566** and **N^1.640**,',
     'the two subjects give an empirical exponent of **N^1.500** and **N^1.640**,',
     '9.20 coffee-bubbles empirical exponent'),
    ('the two subjects give an empirical exponent of **N^1.566** and **N^1.640**,',
     'the two subjects give an empirical exponent of **N^1.566** and **N^1.700**,',
     '9.20 112MSDCF empirical exponent'),
    ('attempted = 24\nmeasured + 0 refused + 0 failed.**',
     'attempted = 23\nmeasured + 0 refused + 0 failed.**',
     '9.21 arm partition does not sum'),
    ('4 arms x 3 depths x 2 subjects = **24 arm-measurements attempted = 24',
     '4 arms x 3 depths x 2 subjects = **26 arm-measurements attempted = 24',
     '9.21 arm count disagrees with the records'),
    ('   and **-0.062** on a 79-frame one.',
     '   and **-0.082** on a 79-frame one.',
     '9.21 restated shipping softening'),
    ('Five. Four were caught by controls rather than by inspection, and the fifth was caught by the negative control after the verifier had already reported itself green.',
     'Six. Four were caught by controls rather than by inspection, and the fifth was caught by the negative control after the verifier had already reported itself green.',
     '9.22 defect count disagrees with the list'),
    ('The model is\nrefuted.**',
     'The model is\nconfirmed.**',
     '9.20 verdict word flipped to confirmed, numbers untouched'),

    # ---- section 9.23 ----
    ('| shipping | 19 | 5.403e+10 | 2.797e+08 | 1.295e+09 | 5.237e+08 |',
     '| shipping | 19 | 5.503e+10 | 2.797e+08 | 1.295e+09 | 5.237e+08 |',
     '9.23 coffee-bubbles ladder cell scene_mot altered'),
    ('| confidence | 79 | 1.058e+10 | 1.069e+07 | 1.205e+08 | 4.250e+07 |',
     '| confidence | 79 | 1.058e+10 | 1.069e+07 | 4.250e+07 | 1.205e+08 |',
     '9.23 112MSDCF ladder row TRANSPOSED, both values still present'),
    ('| shipping | 19<-9 | 1.3567 |',
     '| shipping | 19<-9 | 1.4567 |',
     '9.23 coffee-bubbles per-doubling scene mid ratio altered'),
    ('| 79<-39 | 0.4396 | 0.1970 | **55.2%** |',
     '| 79<-39 | 0.4396 | 0.1970 | **65.2%** |',
     '9.23 112MSDCF fix ceiling overstated'),
    ('**Cells: 12 examined = 9 measured + 3 refused.** The plain mean',
     '**Cells: 12 examined = 10 measured + 3 refused.** The plain mean',
     '9.23 coffee-bubbles partition no longer sums'),
    ('> **RETRACTED -- see section 9.23.**',
     '> **A note on section 9.23.**',
     '9.23 the retraction banner at 9.17 removed'),
    ('and against the direction dilution predicts',
     'and in the direction dilution predicts',
     '9.23.7 ordering verdict flipped, every number left intact'),
    ('3.6% / 5.8% / 47.1%',
     '3.6% / 5.8% / 17.1%',
     '9.23 112MSDCF separation breakdown understated'),
    ('the over-statement is 2.724x in variance',
     'the over-statement is 2.824x in variance',
     '9.23.1 variance over-statement altered'),
    ('measures **0.4963 and\n0.5127** per doubling',
     'measures **0.5963 and\n0.5127** per doubling',
     '9.23.6 the measured 0.5 ideal altered'),
    ('| confidence | 4.250e+07 | 1.917e+07 | 2.217 |',
     '| confidence | 4.250e+07 | 1.917e+07 | 2.417 |',
     '9.23.8b fine-scale SNR at N=79 altered'),
    ('Six of these eleven were caught by a test failing',
     'Six of these twelve were caught by a test failing',
     '9.23.12 defect count disagrees with the list'),
]

PLACEBO = ("So the counterfactual below is run on the exponent, not on a tolerance.",
           "The counterfactual below is therefore run on the exponent, not a tolerance.")


def run():
    p = subprocess.run([sys.executable, CHK], capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def apply(old, new, label):
    t = io.open(DOC, encoding="utf-8").read()
    n = t.count(old)
    if n != 1:
        raise SystemExit("PLANT ANCHOR NOT UNIQUE (%s): %r occurs %d times"
                         % (label, old[:70], n))
    io.open(DOC, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))


def main():
    shutil.copyfile(DOC, BAK)
    shutil.copyfile(CHK, CBAK)
    caught = missed = crashes = 0
    placebo_ok = crash_ok = False
    try:
        rc, out = run()
        if rc != 0:
            raise SystemExit("baseline is not green (rc=%d):\n%s" % (rc, out))
        print("baseline GREEN")

        for old, new, label in PLANTS:
            apply(old, new, label)
            rc, out = run()
            shutil.copyfile(BAK, DOC)
            if rc == 2:
                crashes += 1
                print("  CRASH   %-30s (a crash is not a catch)" % label)
            elif rc == 1:
                caught += 1
                print("  caught  %s" % label)
            else:
                missed += 1
                print("  MISSED  %-30s rc=%d" % (label, rc))

        apply(PLACEBO[0], PLACEBO[1], "placebo")
        rc, _ = run()
        shutil.copyfile(BAK, DOC)
        placebo_ok = (rc == 0)
        print("  placebo %s (rc=%d)" % ("clean" if placebo_ok else "DIRTY", rc))

        t = io.open(CHK, encoding="utf-8").read()
        anchor = "    d = json.load(io.open(PLAT, encoding=\"utf-8\"))"
        if t.count(anchor) != 1:
            raise SystemExit("crash-arm anchor not unique")
        io.open(CHK, "w", encoding="utf-8", newline="\n").write(
            t.replace(anchor, "    raise RuntimeError('planted crash')\n" + anchor))
        rc, out = run()
        shutil.copyfile(CBAK, CHK)
        crash_ok = (rc == 2 and "REFUSED" in out)
        print("  crash arm %s (rc=%d, expected 2)"
              % ("distinguishes refusal from pass" if crash_ok else "BROKEN", rc))
    finally:
        shutil.copyfile(BAK, DOC)
        shutil.copyfile(CBAK, CHK)

    same = (io.open(DOC, encoding="utf-8").read()
            == io.open(BAK, encoding="utf-8").read())
    print("\n%d/%d plants caught; placebo %s; %d crash(es); restore %s"
          % (caught, len(PLANTS), "clean" if placebo_ok else "DIRTY", crashes,
             "verified byte-identical" if same else "DIFFERS"))
    ok = (caught == len(PLANTS) and placebo_ok and crashes == 0
          and crash_ok and same)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
