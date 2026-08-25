"""ORCH fold 168: M112-real-pixels section 10 (P11, P12, D6, D7).

M112 was exposed on two of three withdrawn triage axes and cleared itself by
measurement rather than by shape -- then reported the prediction that failed
and chased it to a mechanism that sharpens ORCH's replacement guidance.

Source: docs/research/M112-real-pixels.md section 10 (commits 9915c5d, 1c21167).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1762 | MEASURED | M112 | **A BIAS THAT PUSHES TOWARD THE CONCLUSION YOU DID NOT REACH CANNOT HAVE MANUFACTURED THE ONE YOU DID.** M112's statistic is a band power ratio reading pixel value -- M115's exact algebraic case, and exposed on two of ORCH's three withdrawn triage axes -- so M112 ran a dose-response ladder instead of arguing from shape. Its input holds **22 425** distinct levels, a **median 65 486 per 256 px tile** against V-M113's threshold of **12**. Across a ladder narrowing to **1 level per tile** the recovery moved **-0.0042 -> +0.0602** and **the decision never flipped**, with the `REFONLY` positive control alive at every rung (**+0.1836 -> +0.2144**). **The clearance is directional, and that is what settles it:** quantisation drives the recovery *more positive*, i.e. toward `ship`, while M112's verdict is a **no-go** -- so the hazard works against the conclusion. A **46x** narrowing moves the decision number by **0.0001 dex** against a **+0.10** bar. |
| 1763 | MEASURED | M112 | **AN ALGEBRAIC EXPANSION GOT THE SIGN WRONG, BECAUSE THE PERTURBATION LANDED IN A WEIGHT RATHER THAN A TERM.** M112 pre-registered prediction P-A from M115's factorisation -- the measured cost would **compress** toward zero. It **inflated**, **+0.1813 -> +0.2105**, and M112 chased the discrepancy rather than banking the favourable half. The decomposition found the *control's own* high-band ratio rising **+1.1237 dex**, which a common additive floor cannot do because it enters both terms and cancels. **The error was writing `\\|H\\|^2` as a scalar.** `band_ratio` is a *mean over a band* and the gather's transfer falls across that band, so the band mean is a **spectrum-weighted average** of `\\|H\\|^2`; the image spectrum is red and sits where `\\|H\\|^2` is high, while a quantisation floor is white and sits at the band's **upper edge where `\\|H\\|^2` is lowest**, so the floor is attenuated *more* than the signal it displaces. **M115's compression and M112's inflation are the same factorisation with the perturbation landing in different factors.** |
| 1764 | MEASURED | M112 | **SHARED INSTRUMENTATION CARRIES THE HAZARD ACROSS MILESTONE BOUNDARIES: `m95cov.pick_tiles` RANKS TILES BY `np.diff(t).var()`.** That is a **differencing dispersion statistic of exactly the exposed kind** -- the class fact 1712 showed under-reports noise by **16x** on narrowed input, because rounding error is correlated across frames and differencing estimators book the correlated half as signal. It cannot bias M112's own arms, whose tile selection was pinned once on the undosed native-precision image and reused across every arm and dose. But **any milestone calling `pick_tiles` on narrowed data inherits the under-report even if the statistic it finally publishes is immune**: the contamination enters through *which tiles were chosen*, upstream of the measurement, where no audit of the measured statistic can see it. |
"""

NEW_DISCIPLINES = """909. **CHECK WHETHER A SUSPECTED BIAS POINTS TOWARD OR AWAY FROM YOUR CONCLUSION BEFORE SPENDING A DAY BOUNDING ITS MAGNITUDE.** Fact 1762: M112 was genuinely exposed, and the exposure was harmless because it pushes toward `ship` while M112 concluded `no-go`. **A bias aligned against your verdict is a strengthening, not a threat**, and establishing the *direction* is usually one cheap dose-response ladder where bounding the *size* is a campaign. State the direction explicitly in the clearance, because a reader who sees only `exposed but small` cannot tell a lucky escape from a structural one.
910. **ALGEBRAIC EXPANSION IS NOT ENOUGH IF THE PERTURBATION LANDS IN A WEIGHT.** Fact 1763. ORCH's replacement guidance -- expand the estimator and see which factor the perturbation enters -- was followed correctly and still produced the wrong sign, because substituting a scalar for a transfer function silently assumes **the perturbation shares the signal's spectral shape**, and quantisation is the case where that assumption is worst. Any statistic that is a **mean over a band, an average over windows, or a weighted combination** hides a weighting the scalar form does not show. **Expand it, then ask what the perturbation's spectrum is relative to the signal's** -- and if you cannot answer that, the dose-response ladder is not optional.
911. **AUDIT THE PROVENANCE OF SHARED HELPERS, NOT ONLY YOUR OWN CALL SITES.** Fact 1764: a tile-ranking helper used across milestones embeds a differencing dispersion statistic, so a milestone whose published statistic is provably immune can still inherit the defect through **which data it selected**. M111 reached the same place from the other direction by auditing the provenance of its *inputs* rather than its code. **The hazard surface of a measurement includes every library it calls and every file it reads**, and both are outside the region a self-audit naturally inspects.
"""


def insert_after_fact_row(n, block, txt):
    anchor = f"| {n} |"
    i = txt.index(anchor)
    j = txt.index("\n", i) + 1
    return txt[:j] + block + txt[j:]


def insert_after_discipline(n, block, txt):
    anchor = f"\n{n}. **"
    i = txt.index(anchor)
    j = txt.index("\n", i + 1) + 1
    return txt[:j] + block + txt[j:]


text = insert_after_fact_row(1761, NEW_FACTS, text)
text = insert_after_discipline(908, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold168 OK: facts 1762-1764, disciplines 909-911")
print("  a bias pointing away from your verdict is a strengthening;")
print("  and pick_tiles carries the differencing hazard into any caller")
