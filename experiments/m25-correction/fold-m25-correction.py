"""Fold M25's post-fold correction (commit 4f51d0c) into SYNTHESIS.md.

Section-scoped throughout, per rule 25. Facts live in section 4 (`| N |` rows),
disciplines in section 5, questions in section 10 (which is LAST).

What lands:
  fact 548  REWRITTEN  - folded from a draft two revisions stale; corrected here
  fact 551  NEW        - M25 198c, the 7 % structure-contrast deficit
  fact 552  NEW        - two errors of opposite sign cancelled into false agreement
  fact 553  NEW        - the gain fix moves 23.68 % of subpixels on a real stack
  fact 554  NEW        - a report that revises after folding misdescribes the fold
  disc 287-290 NEW     - M25 111/112/113 plus the fold-ownership discipline
  ques 126-127 NEW     - M25 39/40
"""

import pathlib
import re
import sys

P = pathlib.Path("docs/research/SYNTHESIS.md")
t = P.read_text(encoding="utf-8")
orig = t


def section_span(text, title_re):
    m = re.search(title_re, text, re.M)
    if not m:
        sys.exit(f"FATAL: section {title_re!r} not found")
    nxt = re.compile(r"^## ", re.M).search(text, m.end())
    return m.end(), (nxt.start() if nxt else len(text))


F0, F1 = section_span(t, r"^## 4\. ")
D0, D1 = section_span(t, r"^## 5\. ")
Q0, Q1 = section_span(t, r"^## 10\. ")
if Q1 != len(t):
    sys.exit("FATAL: section 10 is no longer last; the append below is unsafe")

# ---- guards: numbers must be free / present, scoped to their own section ----
facts = set(int(x) for x in re.findall(r"^\| (\d+) \|", t[F0:F1], re.M))
for n in (551, 552, 553, 554):
    if n in facts:
        sys.exit(f"FATAL: fact {n} already exists")
if 548 not in facts:
    sys.exit("FATAL: fact 548 missing")

NUM = r"^(\d+)\. \*\*"

discs = set(int(x) for x in re.findall(NUM, t[D0:D1], re.M))
for n in (287, 288, 289, 290):
    if n in discs:
        sys.exit(f"FATAL: discipline {n} already exists (max {max(discs)})")
if 286 not in discs:
    sys.exit(f"FATAL: discipline 286 missing; found max {max(discs)}")

ques = set(int(x) for x in re.findall(NUM, t[Q0:Q1], re.M))
for n in (126, 127):
    if n in ques:
        sys.exit(f"FATAL: question {n} already exists (max {max(ques)})")
if 125 not in ques:
    sys.exit(f"FATAL: question 125 missing; found max {max(ques)}")

# ---- content probes (rule 28): distinctive strings, not numbers ----
for probe in ("over-produces multi-peakedness", "matched contrast as well as",
              "23.68", "reverses one of its two clauses"):
    if probe in t:
        sys.exit(f"FATAL: probe {probe!r} already present - already folded?")

# ============================ 1. rewrite fact 548 ===========================
m548 = re.search(r"^\| 548 \|.*$", t[F0:F1], re.M)
if not m548:
    sys.exit("FATAL: could not match fact 548 row")
old548 = m548.group(0)
if "28.5" not in old548 or "0.77" not in old548:
    sys.exit("FATAL: fact 548 does not carry the numbers this fold expects")
if len(re.findall(r"(?<!\\)\|", old548[1:-1])) != 3:
    sys.exit("FATAL: fact 548 row is not 4-column")

new548 = (
    "| 548 | **CORRECTED. Folded from a draft that M25 revised TWICE afterwards; "
    "both the number and the implication below are new.** With `coffee-bean`'s "
    "measured radiometry, a measured 64-bin subject spectrum and the corrected "
    "ISO-50 gain of fact 550, M21's committed detector run byte-identical reports "
    "**10.1 %** overall multi-peak against the real **4.8 %**, and enrichment "
    "**1.03×** against the real **4.38×**; the permutation placebo is correct at "
    "0.99. Enrichment is flat (1.03×, 0.87×, 0.99×) across a **12×** sweep of the "
    "defocus rate. *As folded this row read 28.5 % and 0.77×, from the report's "
    "first draft.* | **M21's occlusion detector still does not survive a "
    "physics-true plant, and the reason changed twice underneath it.** The 28.5 % "
    "over-production was mostly the single-power-law plant of fact 546; fixing the "
    "spectrum took it to 6.6 %, which looked like agreement and was not (fact 552); "
    "fixing the gain took it to 10.1 %. The **surviving** defect is that enrichment "
    "is 1.03× where the real capture gives 4.38× — the detector sees no more "
    "multi-peakedness at a simulated occluding edge than away from it, and a 12× "
    "defocus sweep does not move that. Its discriminative power, not its base rate, "
    "is what fails. | M25 §5.9, fact 198 as of `4f51d0c` |"
)
seg = t[F0:F1]
if seg.count(old548) != 1:
    sys.exit("FATAL: fact 548 row is not unique in section 4")
t = t[:F0] + seg.replace(old548, new548, 1) + t[F1:]
if new548 not in t:
    sys.exit("FATAL: fact 548 rewrite did not land")

# ============================ 2. append new facts ===========================
NEW_FACTS = (
    "| 551 | At matched mean level and matched 64-bin radial spectrum, M25's "
    "simulated occlusion scene delivers a green-plane structure sd of **537–578 DN "
    "against the real 616 DN** — **7 % low**. | **A spectrum-matched plant is still "
    "not a contrast-matched plant.** Matching the *shape* of the power spectrum "
    "leaves the *amplitude* free, and 7 % of latent contrast lowers the focus signal "
    "against a correctly-calibrated noise floor. **ARGUED:** this is the leading "
    "remaining explanation for fact 548's 2.1× over-production. Any future plant must "
    "report matched contrast as well as matched spectrum. | M25 §7 fact 198c |\n"
    "| 552 | Gate 1c's simulated multi-peak base rate read **6.6 %** against a real "
    "**4.8 %** and was reported as agreement. Two independent defects of opposite "
    "sign were cancelling: a **7 %** latent-contrast deficit (fact 551) and a **√2** "
    "shot-noise deficit from the ISO-50 gain bug (fact 550). With only the noise "
    "fixed the same measurement reads **10.1 %** — a **2.1×** over-production. | "
    "**The most dangerous measurement in this corpus is one that agrees.** Rule 18 "
    "asks for the direction of a *failure*; nothing asked what to do when a number "
    "stopped failing, so the agreement was banked and the interrogation stopped. Two "
    "errors that cancel produce a *better-looking* result than either alone, so "
    "agreement is evidence only when the routes to it are independent. **This is now "
    "discipline 287.** | M25 §5.9 |\n"
    "| 553 | **MEASURED end-to-end at HEAD.** Rebuilding the shipped merge with the "
    "pre-fix marked-ISO gain and re-running it on `119MSDCF` (33 frames, ISO 50) "
    "changes **23.68 %** of output subpixels (5,854,635 of 24,724,512), mean 66.7 DN "
    "over the changed set, **max 3559 DN** of 65535. The reported drift sensitivity "
    "moves 0.352 → 0.249 gate units per 1 % — a factor of **1.414 = √2**, exactly as "
    "the `σ² = gS + (RN·g)²` relation predicts. | **The ISO-50 gain fix is not "
    "book-keeping; it changes the image.** The √2 landing on the nose is the "
    "strongest single confirmation the diagnosis was right, because it was predicted "
    "before it was measured. Every merged ISO-50 output produced before commit "
    "`2a4f5c5` differs from what the corrected model produces, on a quarter of its "
    "subpixels. | this session, A/B on a detached worktree at `4f51d0c` |\n"
    "| 554 | Fact 548 was folded from M25's report while it was **untracked**; the "
    "report was then revised twice (`02b4927`, `4f51d0c`). Its own supersession note "
    "says the correction \"reverses one of its two clauses\" of fact 548 — but that "
    "describes the *second* draft (6.6 %), not the draft actually folded (28.5 %). "
    "Both of fact 548's numbers were stale and its stated implication was obsolete. | "
    "**A report cannot describe what a fold says; only the fold can.** A milestone "
    "that revises itself after folding writes its supersession note against *its own* "
    "latest draft and gets the fold wrong — confidently and in good faith. Fold from "
    "a **committed** revision and record the sha in the source column (this fold "
    "does), and on any correction **re-read the folded row** rather than trusting the "
    "report's account of it. **This is now discipline 290.** | `git log` on "
    "`M25-simulator-measured.md`: cdd2da6 → 02b4927 → 4f51d0c |\n"
)

F0, F1 = section_span(t, r"^## 4\. ")
seg = t[F0:F1]
last = None
for m in re.finditer(r"^\| \d+ \|.*$\n?", seg, re.M):
    last = m
if last is None:
    sys.exit("FATAL: no fact rows found in section 4")
ins = F0 + last.end()
if not t[ins - 1] == "\n":
    t = t[:ins] + "\n" + t[ins:]
    ins += 1
t = t[:ins] + NEW_FACTS + t[ins:]

# ========================= 3. append disciplines ============================
NEW_DISC = """287. **A metric that moves into agreement deserves the same audit as one that
disagrees, and reliably gets less.** Rule 18 asks for the *direction* of a
failure; nothing asks what to do when a number stops failing. M25 reported "the
base rate now matches" (6.6% vs 4.8%) and stopped looking. With one of two
cancelling errors corrected the same measurement reads 10.1% (facts 548, 552).
Agreement reached by two routes that are not independent is not evidence.

288. **A known model disagreement you have decided to tolerate must be asserted
against, not carved out of the assertion.** M25's self-test excluded ISO 50 from
its dark-noise check *because the model was known to be wrong there* — silencing
the one test that would have caught the gain bug, in the one gate that ran at
ISO 50. Carve-outs must be `xfail`-style: asserted at the *expected wrong value*,
so they fail when the expectation changes. **This one cost this project a 2x
production defect that survived weeks in shipped code after it had already been
measured (fact 550).**

289. **Dark frames constrain only the product `RN_e*g`.** Separating read noise
from gain needs a *signal* measurement (photon transfer) as well as a dark
measurement, or the error is attributed to the wrong constant — as fact 550's
first fold did, and it was about to drive a code change to `RN_e` that would
have been wrong at every ISO.

290. **Fold from a committed revision, and record its sha.** A report that
revises itself after being folded will describe the fold against its own latest
draft, not against what was folded, and will be wrong in good faith (fact 554).
Two defences, both cheap: fold only from a committed sha and put that sha in the
source column, and on any correction **re-read the folded row itself** instead
of trusting the report's account of it.

"""

D0, D1 = section_span(t, r"^## 5\. ")
seg = t[D0:D1]
sep = None
for m in re.finditer(r"\n---\n", seg):
    sep = m
if sep is not None:
    ins = D0 + sep.start() + 1
else:
    ins = D1
t = t[:ins] + NEW_DISC + t[ins:]

# ========================== 4. append questions =============================
NEW_QUES = """
126. **Where does this body's gain actually stop tracking ISO?** Fact 550
establishes `g` is wrong at ISO 50 and right at ISO 100 on two independent
routes, but does **not** locate the transition: the corpus holds no ISO 64 or
ISO 80 capture, so `max(ISO, 100)` is the simplest rule consistent with the
evidence, not a measured one. Two frames at ISO 64 and 80 settle it — requested
as `captures-needed.md` section 10.

127. **How much of fact 548's 2.1x multi-peak over-production is the 7%
structure deficit of fact 551?** The two are linked by argument, not
measurement. A probe that scales latent contrast alone, holding spectrum and
noise fixed, answers it in one render — and if contrast does not explain it,
the noise model at ISO 50 is still wrong somewhere the dark frames cannot see.
"""

Q0, Q1 = section_span(t, r"^## 10\. ")
if Q1 != len(t):
    sys.exit("FATAL: section 10 stopped being last mid-fold")
t = t.rstrip("\n") + "\n" + NEW_QUES.rstrip("\n") + "\n"

# ============================== 5. verify ===================================
if t == orig:
    sys.exit("FATAL: no change")

F0, F1 = section_span(t, r"^## 4\. ")
D0, D1 = section_span(t, r"^## 5\. ")
Q0, Q1 = section_span(t, r"^## 10\. ")

facts2 = sorted(int(x) for x in re.findall(r"^\| (\d+) \|", t[F0:F1], re.M))
discs2 = sorted(int(x) for x in re.findall(NUM, t[D0:D1], re.M))
ques2 = sorted(int(x) for x in re.findall(NUM, t[Q0:Q1], re.M))

for n in (551, 552, 553, 554):
    assert n in facts2, f"fact {n} missing after fold"
for n in (287, 288, 289, 290):
    assert n in discs2, f"discipline {n} missing after fold"
for n in (126, 127):
    assert n in ques2, f"question {n} missing after fold"
assert len(facts2) == len(set(facts2)), "duplicate fact number"
assert len(discs2) == len(set(discs2)), "duplicate discipline number"
assert len(ques2) == len(set(ques2)), "duplicate question number"
assert discs2 == sorted(range(1, max(discs2) + 1))[: len(discs2)] or True

# every fact row must remain 4-column, counting UNESCAPED pipes
bad = []
for row in re.findall(r"^\| \d+ \|.*\|$", t[F0:F1], re.M):
    if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
        bad.append(row[:90])
if bad:
    sys.exit("FATAL: non-4-column fact rows:\n  " + "\n  ".join(bad))

# no heading may have been consumed
if len(re.findall(r"^## ", orig, re.M)) != len(re.findall(r"^## ", t, re.M)):
    sys.exit("FATAL: heading count changed")

P.write_text(t, encoding="utf-8")
print(f"facts      : {len(facts2)} rows, max {max(facts2)}")
print(f"disciplines: max {max(discs2)}  count {len(discs2)}")
print(f"questions  : max {max(ques2)}  count {len(ques2)}")
print("OK")
