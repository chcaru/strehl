"""Fold M50 into SYNTHESIS.md.

Source revision, per rule 31: commit b842ea7 (docs/research/M50-*, experiments/m50-*).

M50 began as a fresh investigation of question 20, which M16 had already closed.
That was an orchestration error. It converted into the independent verification
M16's facts were explicitly tagged as lacking, so it folds as VERIFICATION of
fact 93 plus one QUALIFICATION of its wording -- not as a new investigation.

  fact 559  M16's row-FPN refutation is independently verified from the sensor side
  fact 560  QUALIFIES fact 93 -- 11/11 sign, ~5%, and it is not banding
  fact 561  M4 section 5's sigma_FPN table independently verified
  fact 562  M4 section 8.1 verified a THIRD time, here as a loader check
  fact 563  rawpy raw_image_visible is a view; use-after-free that does not crash
  fact 564  a ratio is unusable as an anisotropy measure when a term can be zero
  fact 565  per-pixel FPN cannot contaminate M48's temporal DN floor (rule 10)
  disc 292  an experiment expecting "no" needs an estimator that can return zero
  disc 293  bounded contrast index, never a ratio through zero
  disc 294  check whether a question is closed before investigating it
  disc 295  an eleven-for-eleven sign is not a band around unity
  ques 130  what causes the residual ~5% anisotropy?
  ques 131  why is M50 1.4-1.6% above M4 section 5 at ISO 1600-2000 only?

Also EDITS fact 93's source column to drop NOT INDEPENDENTLY VERIFIED. That is
the only deletion this script makes: exactly one line, re-emitted with the tag
replaced, per rule 29.
"""

import pathlib
import re
import sys

P = pathlib.Path("docs/research/SYNTHESIS.md")
t = P.read_text(encoding="utf-8")
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
NEWF = (559, 560, 561, 562, 563, 564, 565)
for n in NEWF:
    if n in facts:
        sys.exit(f"FATAL: fact {n} taken")
for n in (93, 558):
    if n not in facts:
        sys.exit(f"FATAL: fact {n} missing - a previous fold did not land")

discs = set(int(x) for x in re.findall(NUM, t[D0:D1], re.M))
NEWD = (292, 293, 294, 295)
for n in NEWD:
    if n in discs:
        sys.exit(f"FATAL: discipline {n} taken")
if 291 not in discs:
    sys.exit("FATAL: discipline 291 missing")

ques = set(int(x) for x in re.findall(NUM, t[Q0:Q1], re.M))
for n in (130, 131):
    if n in ques:
        sys.exit(f"FATAL: question {n} taken")
if 129 not in ques:
    sys.exit("FATAL: question 129 missing")

for probe in ("cross-half covariance", "0xC0000005", "never once crosses 1.000"):
    if probe in t:
        sys.exit(f"FATAL: probe {probe!r} present - already folded?")

SRC = "`experiments/m50-fpn-anisotropy`, commit `b842ea7`"

NEW_FACTS = (
    "| 559 | **M16's row-FPN refutation is INDEPENDENTLY VERIFIED, from the "
    "sensor side.** M50 re-measured the sensor's fixed pattern by cross-half "
    "covariance -- disjoint frame halves averaged separately, the reported value "
    "their covariance, so temporal noise contributes **exactly zero in "
    "expectation** and the estimate may go negative -- on full CFA planes at all "
    "11 ISOs. Row and column terms are the same size (the **column** term is the "
    "larger at 4 of 11 ISOs) and are **1.8-12.8%** of ordinary per-pixel FPN; the "
    "row term exceeds twice its own split spread at only 5 of 11 ISOs. The Sobel "
    "anisotropy index measures **+0.005 to +0.061** against **+1.004** on planted "
    "pure row banding. | **The fix stays unbuilt and question 20 stays closed.** "
    "M16 measured the reviewer's fix on the *downstream* statistic (0.0 windows, "
    "fact 96); M50 measures the *sensor*, by a different estimator, on full planes "
    "rather than a 512x512 ROI, through a different decoder. Same verdict from the "
    "opposite direction. Subtracting row and column means moves the index by "
    "**0.009 on a +-1 scale**, while the identical operation destroys **99.96%** of "
    "*planted* banding energy -- so the treatment works and there is nothing here "
    f"to treat. | {SRC} (M50 §5.1) |\n"
    "| 560 | **QUALIFIES fact 93.** Fact 93 calls the fixed pattern \"isotropic at "
    "every measured ISO\". It is very nearly so, but the anisotropy index is "
    "**positive at 11 of 11 ISOs** (p ~ 0.001 two-sided), `Ey/Ex` ~ **1.05**, and "
    "roughly **two-thirds of it survives row and column mean removal** -- so it is "
    "**not banding**. M16's own eleven numbers show the same thing and were read as "
    "noise: `gx²/gy²` = 0.968-0.999 **never once crosses 1.000**. The two agree "
    "quantitatively once M16's master-bias statistic is corrected for the ~25% "
    "isotropic temporal-noise dilution it retains at ISO 100. | **Fact 93's "
    "CONSEQUENCE column stands unchanged.** It requires any row/column-FPN proposal "
    "to \"first move this number\"; M50 moves it from ~1% to ~5%, and M16's "
    "amplitude ladder puts the mechanism's detection threshold at **1774x** the "
    "sensor's row amplitude. A factor of 5 does not approach a factor of 1774. The "
    "residual lives in the per-pixel term -- neighbouring pixels along x are "
    "slightly more correlated than along y within one CFA plane. **ARGUED:** "
    "column-parallel shared-ADC readout has the right sign, and M4's unresolved "
    "G2/B excess may be the same effect; neither is established. A directional bias "
    "in M50's own operator pair is excluded by its isotropic plant, which returns "
    f"+0.004 through the identical code path. | {SRC} (M50 §5.2) |\n"
    "| 561 | **M4 §5's `sigma_FPN` table is INDEPENDENTLY VERIFIED** by a different "
    "estimator (cross-half covariance against M4's bias-corrected asymptote of a "
    "sd-versus-N curve) on a different decoder: mean ratio **1.0043**, worst "
    "deviation **1.55%**, across all 11 ISOs. | A second M4 table confirmed. M4's "
    "arithmetic continues to be right; fact 555's finding was that its *labelling* "
    "was incomplete, and that split verdict is undisturbed. The **+1.4-1.6% excess "
    "at ISO 1600-2000 only** is real and unexplained -- question 131. | "
    f"{SRC} (M50 §4) |\n"
    "| 562 | **M4 §8.1 is verified a THIRD time**, at mean ratio **0.99993**, "
    "spread **0.00007** -- here as a *loader* check rather than as a result. | This "
    "is what proves M50's own pixel data after the use-after-free of fact 563, "
    "whose failure mode is silent corruption rather than a reliable crash. "
    "Corrupted pixels could not reproduce an independently measured table to one "
    f"part in fourteen thousand. Now required of every RAW-decoding script. | {SRC} "
    "(M50 §4) |\n"
    "| 563 | **`rawpy`'s `raw_image_visible` is a VIEW into LibRaw's internal "
    "buffer, not a copy**, and is invalid the instant the `RawPy` context manager "
    "exits. Copying it outside the `with` ran for **four minutes and eleven ISOs' "
    "worth of work** before Windows raised an access violation (**0xC0000005**) "
    "with **no Python traceback at all**. | **The crash is the lucky outcome; the "
    "unlucky one is silently corrupted pixels in a measurement nobody re-checks.** "
    "Now AGENTS rule 32. Allocate and copy inside the `with`; `.astype()` or "
    "`.copy()` on the same line is the safe idiom. `python -X faulthandler` turned "
    "a bare exit code into a line number in one run and should be the first reach "
    "on any native crash. `01-dark-sigma.py` is **not** affected -- it copies "
    f"inside the `with` -- so facts 555-558 stand. | {SRC} (M50 §6) |\n"
    "| 564 | **A ratio is unusable as an anisotropy measure when either term can "
    "legitimately be zero.** M50's self-test, run before any real data was touched, "
    "returned `Ey/Ex` = **-494.885** on *planted pure row banding* -- a large "
    "**negative** number for the most strongly **positive** case that exists -- "
    "because a row-only pattern has no variation along x, so `Ex` is ~0 and its "
    "sign is noise. The bounded index `(Ey-Ex)/(Ey+Ex)` returns **+1.004** on the "
    "same data. | The estimator was correct throughout; the *summary statistic* was "
    "not. Had the self-test not run first, -494.885 would have appeared in a table "
    "about this sensor and been interpreted. **-494.885 does not look like a bug, "
    f"it looks like a measurement.** | {SRC} (M50 §6) |\n"
    "| 565 | The sensor's per-pixel spatial FPN is **0.34-0.86 DN** across ISO "
    "50-2000, which is suspiciously close to M48's hypothesised additive DN-domain "
    "floor near 0.49 DN. **They cannot be the same thing:** per-pixel *temporal* "
    "variance across frames is immune to a static spatial pattern by construction. "
    "| Checked rather than assumed, per rule 10, which has already caused three "
    "retractions from exactly this confusion. **This eliminates one alternative "
    "explanation for question 129's floor and mildly strengthens it; it does not "
    f"confirm it.** | {SRC} (M50 §5.3) |\n"
)

NEW_DISCS = (
    "292. **An experiment whose expected answer is \"no\" needs an estimator that "
    "can return zero, and a placebo that proves it does.** Cross-half covariance "
    "has exactly this property -- temporal noise contributes zero in expectation "
    "and the estimate may go negative -- which is what makes a null from it worth "
    "something. A statistic with a positive null expectation always finds "
    "structure: averaging N frames leaves `sigma_t/sqrt(N)` per pixel, so a row "
    "mean over W pixels has a spread of `sigma_t/sqrt(N*W)` from noise **alone**. "
    "M50's placebo sits at **1.2%** of its plant amplitude, and that row is what "
    "licenses believing its null. Without it, \"there is no row banding\" and "
    "\"this estimator cannot see row banding\" are the same output. This extends "
    "rule 11's placebo requirement from defects to nulls.\n"
    "293. **Use a bounded contrast index, never a ratio, whenever a denominator "
    "can legitimately reach zero.** A sign flip from a denominator crossing zero is "
    "invisible in the output (fact 564). `(a-b)/(a+b)` is bounded, finite wherever "
    "there is any signal, and its magnitude is interpretable.\n"
    "294. **Check whether a question is already closed before investigating it, "
    "and grep the corpus rather than trusting the prompt's framing.** A review that "
    "raises a question is not evidence the question is open. M50 re-investigated "
    "question 20 six hours of measurement after M16 closed it, with the closure "
    "written out in full in §10 and eight facts folded. The cost was recovered only "
    "because M16's facts carried **NOT INDEPENDENTLY VERIFIED** and rule 12 gives "
    "an independent measurement standing regardless of why it was made -- **which "
    "is luck, not method.** The corollary is the useful half: that tag is a "
    "standing work queue, and picking from it is never duplication.\n"
    "295. **A range that sits on one side of the null every time is a detection, "
    "however small.** Fact 93 reported `gx²/gy²` = 0.968-0.999 as \"isotropic\". "
    "Eleven independent measurements all below 1.000 is p ~ 0.001, not a band "
    "around unity. **Report the sign count beside the range** whenever a range "
    "brackets the null on one side only.\n"
)

NEW_QUES = (
    "130. **What causes the residual ~5% gradient anisotropy, and does it matter "
    "on scene content?** It is real (11/11 ISOs), it is **not** banding (two-thirds "
    "survives row/column mean removal), and it is unexplained. **ARGUED:** "
    "column-parallel shared-ADC readout has the right sign, and M4's unresolved "
    "G2/B plane excess may be the same effect. The downstream half is largely "
    "answered -- M16 measured the effect on the window statistic at 0.0 windows -- "
    "so this is a sensor-characterisation question, not a blocker. `UNVERIFIED`.\n"
    "131. **Why is M50's total fixed pattern 1.4-1.6% above M4 §5 at ISO 1600-2000 "
    "only?** Candidates: M4's bias correction over-subtracting where "
    "`sigma_temporal` is large, or a weak frame-to-frame temporal correlation that "
    "cross-half covariance retains and M4's estimator removes. **The second would "
    "matter elsewhere** -- it would mean averaged frames denoise slightly worse "
    "than the model predicts at high ISO. Cheap to settle. `UNVERIFIED`.\n"
)

# --- the single edit: fact 93 loses its NOT INDEPENDENTLY VERIFIED tag ---
m93 = re.search(r"^\| 93 \|.*$", t, re.M)
if not m93:
    sys.exit("FATAL: fact 93 row not found")
old93 = m93.group(0)
TAG = " — **NOT INDEPENDENTLY VERIFIED** |"
if not old93.endswith(TAG):
    sys.exit(f"FATAL: fact 93 does not end with the expected tag: ...{old93[-80:]!r}")
new93 = old93[: -len(TAG)] + (
    " — **INDEPENDENTLY VERIFIED by M50** (different estimator, full planes, all 11 "
    "ISOs, placebo-validated), and **QUALIFIED by fact 560**: the pattern is "
    "isotropic to ~5%, not exactly, with a sign consistent at 11/11 ISOs. The "
    "consequence column stands. |"
)

# Insert facts after the last fact row in section 4.
last = None
for m in re.finditer(r"^\| \d+ \|.*$", t[F0:F1], re.M):
    last = m
if last is None:
    sys.exit("FATAL: no fact rows found in section 4")
ins = F0 + last.end()
t = t[:ins] + "\n" + NEW_FACTS.rstrip("\n") + t[ins:]

# Recompute spans after the insertion, then append disciplines and questions.
D0, D1 = span(t, r"^## 5\. ")
block = t[D0:D1].rstrip("\n")
t = t[:D0] + block + "\n" + NEW_DISCS + "\n" + t[D1:]

Q0, Q1 = span(t, r"^## 10\. ")
block = t[Q0:Q1].rstrip("\n")
t = t[:Q0] + block + "\n" + NEW_QUES + t[Q1:]

if t.count(old93) != 1:
    sys.exit("FATAL: fact 93 row is not unique")
t = t.replace(old93, new93, 1)

# --- guards ---
F0, F1 = span(t, r"^## 4\. ")
for row in re.findall(r"^\| \d+ \|.*$", t[F0:F1], re.M):
    if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
        sys.exit(f"FATAL: fact row is not 4-column: {row[:110]}")
facts2 = [int(x) for x in re.findall(r"^\| (\d+) \|", t[F0:F1], re.M)]
if len(facts2) != len(set(facts2)):
    sys.exit("FATAL: duplicate fact number")
for n in NEWF:
    if n not in facts2:
        sys.exit(f"FATAL: fact {n} did not land")

D0, D1 = span(t, r"^## 5\. ")
d2 = [int(x) for x in re.findall(NUM, t[D0:D1], re.M)]
for n in NEWD:
    if n not in d2:
        sys.exit(f"FATAL: discipline {n} did not land")
Q0, Q1 = span(t, r"^## 10\. ")
q2 = [int(x) for x in re.findall(NUM, t[Q0:Q1], re.M)]
for n in (130, 131):
    if n not in q2:
        sys.exit(f"FATAL: question {n} did not land")

P.write_text(t, encoding="utf-8")
print(f"facts {len(facts2)} max {max(facts2)} | disciplines max {max(d2)} | questions max {max(q2)}")
print("OK")
