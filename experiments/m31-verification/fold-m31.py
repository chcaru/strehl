"""Fold M31-VERIFICATION.md, which deliberately reserved no numbers.

Every finding is a correction to, or confirmation of, an existing claim, so the
fold is a set of in-place markings rather than new rows. Appending to the FINAL
column programmatically because doing it by hand added a spurious column twice
this session (facts 322 and 270), which tablecheck caught both times.
"""
import re, pathlib

DST = pathlib.Path("docs/research/SYNTHESIS.md")

MARKS = {
    220: "**MECHANISM REFUTED by M31-V:** the residual is **photometric, not geometric**. Swapping script 02's median-gain estimator for the mean estimator M28 §6 itself recommends takes dk=16 from **12.301 → 4.094**, and a single least-squares *scalar* per pair removes **73.3%** of it — a scalar cannot express a displacement. The residual is non-monotone in `|∇|` and a constant 3.5–4.5% of signal. The half-normal assumption is **not** the problem (simulated Gaussian and Poisson both return 0.6744/0.6745 through the same pipeline)",
    221: "**QUALIFIED by M31-V:** \"9.9% with no free parameters\" is **1.005 / 1.099 / 1.449** across tile scale and **1.505** without the 22 fitted gains — so there are free parameters, and the number moves 1.5× with them",
    222: "**OPERATING POINT UNKNOWN (M31-V):** the placebo reads **9.85 / 8.33 / 10.61%** at a nominal 5% and **0.00%** at 1% (0/132, CI [0, 2.8%]). \"@FPR 1%\" therefore names a threshold the calibration cannot resolve. Conclusions survive recalibration",
    230: "**SPEC INCOMPLETE (M31-V): the flat-field map floor IS PRNU** (`g/blur(g) ≈ 1+p`), and PRNU does not fall with `n`. Bounded at **≲0.26%** from M29's own script-01 data. Consequence: **42–51σ becomes 17–19σ, and flats stop helping at n≈4–5, not 16.** M4 declines to measure PRNU, so `captures-needed.md`'s flat-field campaign is load-bearing for this fact",
    231: "**CONFIRMED and SHARPENED by M31-V:** the exact pipeline algebra is **0.9148**, not the 0.885 the report derives — its gap was a linearisation error, so **the lesson is stronger than stated**. Measured/pure-algebra agrees to 0.3499/0.3542/0.3557 across σ",
    232: "**QUALIFIED by M31-V:** the `sep 1` column is **peak-locked at ~0.5× truth** (Fourier-shift plant: true 0.05/0.10/0.20/0.30 → 0.0251/0.0510/0.1086/0.1827), and the disclosure calls it \"clean\". `sep 4` is also broken (3.381 px vs 0.103 at sep 8) and undisclosed. **Pre-registered Q12 fails and is unreported**",
    233: "**THE DISCRIMINATOR HAD NO POWER (M31-V).** \"+0.0250 against −0.5 for shot noise\" names the wrong alternative: under pure shot noise this map's exponent is **−0.0045**, not −0.5, because the map is PRNU-dominated (fact 230). The measured and null exponents are indistinguishable, so the test could not have rejected. Discipline 250",
    234: "**M31-V:** the detection limit is quoted from the arm the milestone itself declares defective — `04-limit.json` has `raw.limit = [null,null,null]`. **Pre-registered Q7 fails for the primary statistic by the milestone's own criterion**",
    240: "**M31-V: CONFIRMED**, re-derived by hand before reading the script (`precision_HDR − precision_base = m·12R²/[(4gL+R²)(gL+R²)] > 0`; ratio `= (1/5)[1+16(1+x)/(4+x)]`, exactly 1 at x=0) and by Monte Carlo. **Wording defect: the row says variance and measures sd**",
    241: "**M31-V: conclusion CONFIRMED, implementation DEFECTIVE.** The boundary `S < RN_e²·g` is algebraically right but the script implements `S < RN_e²` — off by 8.7× / 0.87× / 2.7×. The 0.000000% survives at the documented boundary, checked on the full green plane, but **the script never tested the quantity the fact states**",
    242: "**REFUTED by M31-V — THIS IS A RULE-4 VIOLATION AND THE ROW IS WITHDRAWN.** The 2.3× is an artefact of a **raw argmax**: at the shipped 31×31 regularisation it is **1.4×**, and heavier still **1.0×** — against a uniform-random-frame null of 0.1710%. Mechanism: the argmax *flees* clipped frames because clipping flattens the gradient (median focus 262.26 clipped vs 311.11 unclipped). **Do not cite this row. Fact 243's HDR verdict rests partly on it and must be re-derived**",
}

DISC = {
    120: "**M31-V: partially retracted.** The specific worry that fact 73 is a self-normalised shape statistic does **not** hold — **fact 211 is a genuine third mechanism**. The discipline itself stands on facts 260 and 211.",
}


def append_to_last_column(row, text):
    m = re.match(r"^(\| \d+ \|.*)\|\s*$", row)
    assert m, row[:60]
    return f"{m.group(1).rstrip()} — {text} |"


lines = DST.read_text(encoding="utf-8").split("\n")
cur, hit_f, hit_d = "", set(), set()
out = []
for l in lines:
    if l.startswith("## "):
        cur = l
    if cur.startswith("## 4.") and (m := re.match(r"\| (\d+) \|", l)):
        n = int(m.group(1))
        if n in MARKS:
            l = append_to_last_column(l, MARKS[n])
            hit_f.add(n)
    elif cur.startswith("## 5.") and (m := re.match(r"(\d+)\. \*\*", l)):
        n = int(m.group(1))
        if n in DISC:
            hit_d.add(n)
            out.append(l)
            continue
    out.append(l)

missing_f, missing_d = set(MARKS) - hit_f, set(DISC) - hit_d
assert not missing_f, f"fact rows not found: {sorted(missing_f)}"
assert not missing_d, f"discipline rows not found: {sorted(missing_d)}"

# discipline 120: append a sentence to the end of its indented block
final, i = [], 0
while i < len(out):
    final.append(out[i])
    if re.match(r"120\. \*\*", out[i]):
        j = i + 1
        while j < len(out) and out[j].startswith("     "):
            final.append(out[j])
            j += 1
        final.append("     " + DISC[120])
        i = j
        continue
    i += 1

DST.write_text("\n".join(final), encoding="utf-8")
print(f"marked facts {sorted(hit_f)}")
print(f"marked disciplines {sorted(hit_d)}")
