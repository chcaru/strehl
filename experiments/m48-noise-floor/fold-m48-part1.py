"""Fold the M48 dark-sigma verification into SYNTHESIS.md.

Source revision, per rule 31: commit 4f7f683 (experiments/m48-noise-floor).

Only MEASURED and directly-DERIVED material lands as facts. The additive
DN-floor model is a hypothesis I formed tonight and dispatched M48 to falsify,
so it goes in as a QUESTION, not a fact.

  fact 555  M4's table is independently verified, and by which estimator
  fact 556  that estimator is the pooled RMS, inflated by the hot-pixel tail
  fact 557  read_noise_e_high = 1.47 is wrong on BOTH bases
  fact 558  the base_iso gain fix, confirmed a third time and independently
  disc 291  a sensor constant without a stated estimator is not a measurement
  ques 128  which statistic is the noise model supposed to predict?
  ques 129  is there an additive DN-domain noise floor? (M48 is testing it)
"""

import pathlib
import re
import sys

P = pathlib.Path("docs/research/SYNTHESIS.md")
t = P.read_text(encoding="utf-8")
orig = t
NUM = r"^(\d+)\. \*\*"


def span(text, title_re):
    m = re.search(title_re, text, re.M)
    if not m:
        sys.exit(f"FATAL: section {title_re!r} not found")
    nxt = re.compile(r"^## ", re.M).search(text, m.end())
    return m.end(), (nxt.start() if nxt else len(text))


F0, F1 = span(t, r"^## 4\. ")
D0, D1 = span(t, r"^## 5\. ")
Q0, Q1 = span(t, r"^## 10\. ")
if Q1 != len(t):
    sys.exit("FATAL: section 10 is not last")

facts = set(int(x) for x in re.findall(r"^\| (\d+) \|", t[F0:F1], re.M))
for n in (555, 556, 557, 558):
    if n in facts:
        sys.exit(f"FATAL: fact {n} taken")
if 554 not in facts:
    sys.exit("FATAL: fact 554 missing - the previous fold did not land")

discs = set(int(x) for x in re.findall(NUM, t[D0:D1], re.M))
if 291 in discs:
    sys.exit("FATAL: discipline 291 taken")
if 290 not in discs:
    sys.exit("FATAL: discipline 290 missing")

ques = set(int(x) for x in re.findall(NUM, t[Q0:Q1], re.M))
for n in (128, 129):
    if n in ques:
        sys.exit(f"FATAL: question {n} taken")
if 127 not in ques:
    sys.exit("FATAL: question 127 missing")

for probe in ("0.9999 at every one of eleven", "pooled RMS", "8.6189"):
    if probe in t:
        sys.exit(f"FATAL: probe {probe!r} present - already folded?")

NEW_FACTS = (
    "| 555 | **M4 §8.1's dark-sigma table is INDEPENDENTLY VERIFIED.** Re-measured "
    "from the same 242 darks through a different decoder (`rawpy`, not "
    "`strehl-raw`), the estimator `sqrt(mean over pixels of per-pixel temporal "
    "variance)` over 20 frames reproduces M4 at **0.9999 at every one of eleven "
    "ISOs, total spread 0.0001** across a 6x range. Including the owner's two "
    "stabilisation frames gives 1.0004 / spread 0.0057, so M4 also dropped them. | "
    "**The first independent check any sensor constant in this project has ever "
    "had, and it passes.** M4's method is now fully reconstructed from its outputs "
    "rather than trusted: 20 frames, pooled RMS. Every read-noise number downstream "
    "inherits that estimator, which is fact 556. | `experiments/m48-noise-floor`, "
    "commit `4f7f683` |\n"
    "| 556 | The same frames under two other estimators give **0.8873** of M4 (mean "
    "over pixels of per-pixel sd, ranging 0.9408 at ISO 50 to 0.8538 at ISO 1600) "
    "and **0.8158** (median, 0.9040 to 0.7593). The gap **grows with ISO** and "
    "tracks the hot-pixel tail: the mean-median gap runs +4.0% at ISO 100 to +12.5% "
    "at ISO 1600. | **Every read-noise constant in this project is a pooled RMS "
    "inflated by the hot-pixel tail, and the noise model consumes it as if it "
    "described a typical pixel.** The merge gate compares a per-pixel response "
    "against a per-pixel predicted sigma, so a tail-inflated scalar desensitises "
    "the gate at *every* pixel to cover a defect in a tiny fraction of them — while "
    "M22 already builds a hot-pixel map and M29 treats static defects separately. "
    "Which statistic the model should predict is question 128. | "
    "`experiments/m48-noise-floor`, commit `4f7f683` |\n"
    "| 557 | On the verified table and the gain relation the code uses, the "
    "high-gain mode's mean implied read noise is **1.2414 e-** (RMS basis) or "
    "**1.0772 e-** (typical-pixel basis). The shipped `read_noise_e_high = 1.47` is "
    "**+18.4%** and **+36.5%** against those. The shipped model over-predicts "
    "measured dark sigma by **12.3% at ISO 400 rising to 22.2% at ISO 1600**. "
    "`read_noise_e_low = 4.20` is -2.3% at ISO 100 but +10.4% at ISO 200 and +11.4% "
    "at ISO 250. | **A second shipped sensor constant is wrong, measured, and was "
    "already reported.** M4 §8.3 published \"4.30 → 1.31 e-\" against fact 14's "
    "4.20/1.47 and called the high side \"11% off\"; against the *plateau* rather "
    "than the single ISO-400 point it is 18.4%. This is the same failure as the "
    "gain defect (fact 550): measured, written down, never reached the code. "
    "`read_noise_e_low`'s error is a **shape** error within the mode that no scalar "
    "can fix. M48 owns the fix. | `experiments/m48-noise-floor`, commit `4f7f683`; "
    "M4 §8.3 |\n"
    "| 558 | **The `base_iso` gain fix is confirmed a THIRD time, on a route that "
    "did not exist when it was made.** Under the corrected gain, M4's own ISO-50 "
    "dark row implies **4.3095 e-** against ISO 100's **4.3003 e-** — agreement to "
    "**+0.21%**. M4 published **8.6189 e-** for that row and called it \"visibly "
    "nonsense … the tell\". | **The tell was correct and the correction lands on "
    "it.** The three routes are now independent: darks at equal sigma (M4 §8.2), "
    "photon transfer on signal (M25 fact 200), and this — a *quantitative* "
    "agreement, not merely a consistent sign. Fact 550's diagnosis is as well "
    "supported as anything in this corpus. | `experiments/m48-noise-floor`, commit "
    "`4f7f683`; M4 §8.3's own table |\n"
)

F0, F1 = span(t, r"^## 4\. ")
seg = t[F0:F1]
last = None
for m in re.finditer(r"^\| \d+ \|.*$\n?", seg, re.M):
    last = m
if last is None:
    sys.exit("FATAL: no fact rows")
ins = F0 + last.end()
t = t[:ins] + NEW_FACTS + t[ins:]

NEW_DISC = """291. **A sensor constant without a stated estimator is not a
measurement.** M4's dark-sigma table is exactly right and is now verified to 1
part in 10^4 — but nothing anywhere said *which* statistic it is, and it turns
out to be the pooled RMS, which is 13% above the mean pixel and 23% above the
median at high ISO (facts 555, 556). Three constants were fitted to it as
though it described a typical pixel. This is the failure class §5's preamble
calls this project's worst: the arithmetic was right and the column heading was
missing. **Every constant in `profile.rs` must name the statistic it is, the
frame count, and the exclusion rule — not just its value and its source.**

"""

D0, D1 = span(t, r"^## 5\. ")
seg = t[D0:D1]
sep = None
for m in re.finditer(r"\n---\n", seg):
    sep = m
ins = (D0 + sep.start() + 1) if sep else D1
t = t[:ins] + NEW_DISC + t[ins:]

NEW_QUES = """
128. **Which statistic is the noise model supposed to predict — the pooled RMS,
the mean pixel, or the median pixel?** They differ by 18% at ISO 100 and 32% at
ISO 1600 (fact 556), and every sensor constant currently uses the RMS by
accident rather than by choice. The gate is per-pixel, and hot pixels are
handled elsewhere (M22, M29), which argues for the typical pixel; conservatism
argues for the RMS. The honest answer may be that a scalar is the wrong shape
and the model owes a per-pixel sigma *distribution*. **M48 is deciding this and
must write the decision where the constants live.**

129. **Is there a constant additive DN-domain noise floor the model omits?**
**ARGUED, from a fit I have not validated.** `sigma_DN^2 = a*ISO^2 + c` fitted
on the verified table, anchored on each mode's endpoints, leaves residuals
within **±1%** across both modes against **±4%** for the best single `RN_e` —
and the two independently-fitted floors, 0.470 DN (high) and 0.513 DN (low),
agree to 9%, consistent with one floor near 0.49 DN. 14-bit quantisation alone
would give 0.289 DN. If real, `sigma^2 = g*S + (RN_e*g)^2` is the wrong shape at
low signal, which is exactly where the gate does its work. **This is a
hypothesis formed from an endpoint-anchored two-point fit, which is the weakest
kind; M48 is trying to kill it with a proper all-ISO fit.** Do not build on it
until that lands.
"""

Q0, Q1 = span(t, r"^## 10\. ")
if Q1 != len(t):
    sys.exit("FATAL: section 10 stopped being last")
t = t.rstrip("\n") + "\n" + NEW_QUES.rstrip("\n") + "\n"

if t == orig:
    sys.exit("FATAL: no change")

F0, F1 = span(t, r"^## 4\. ")
D0, D1 = span(t, r"^## 5\. ")
Q0, Q1 = span(t, r"^## 10\. ")
f2 = sorted(int(x) for x in re.findall(r"^\| (\d+) \|", t[F0:F1], re.M))
d2 = sorted(int(x) for x in re.findall(NUM, t[D0:D1], re.M))
q2 = sorted(int(x) for x in re.findall(NUM, t[Q0:Q1], re.M))
for n in (555, 556, 557, 558):
    assert n in f2, n
assert 291 in d2
for n in (128, 129):
    assert n in q2, n
assert len(f2) == len(set(f2)) and len(d2) == len(set(d2)) and len(q2) == len(set(q2))

bad = [r[:90] for r in re.findall(r"^\| \d+ \|.*\|$", t[F0:F1], re.M)
       if len(re.findall(r"(?<!\\)\|", r[1:-1])) != 3]
if bad:
    sys.exit("FATAL: non-4-column rows:\n  " + "\n  ".join(bad))
if len(re.findall(r"^## ", orig, re.M)) != len(re.findall(r"^## ", t, re.M)):
    sys.exit("FATAL: heading count changed")

P.write_text(t, encoding="utf-8")
print(f"facts {len(f2)} max {max(f2)} | disciplines max {max(d2)} | questions max {max(q2)}")
print("OK")
