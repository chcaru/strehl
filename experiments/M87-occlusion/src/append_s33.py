"""Append section 33 to M87-occlusion.md.  CRLF preserved; facts P127-P132."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

SECTION = """
## 33. The gate ladder: averaging is not the mechanism

The orchestrator rendered `bee-3-cpl` four times varying only `--gate`, pinned
the exposure, and reused one solved sidecar so that placements, reference
frame, stack digest, frame count and resampler are byte-identical across the
arms. Their eye judgement, which they explicitly declined to promote to a
finding, was that the veil is strongest at gate 4.00 and substantially weaker
by gate 0.00. If true it would be the first positive localisation of the
mechanism, because fact 1375 has already shown the veil is invariant across
all three resampler kernels.

**It is not true. The veil survives.** Between gate 4.00 and gate 0.00 the
number of frames averaged per pixel changes by **55.3×** and the veil loses
**11.7%** of its amplitude — and §33.5 shows that 96% of even that 11.7% is a
level offset rather than the veil. The gate is not the mechanism.

### 33.1 Provenance (rule 47)

Operands are the orchestrator's four pinned renders in
`C:\\dev\\strehl-out\\ORCH-gate\\`, each 197 797 874 bytes:

```
strehl stack D:\\personal\\macro\\bee-3-cpl --gate <G> --srgb --exposure=1.54 \\
    --out pin-bee-3-cpl-gate-<G>.tif
env: STREHL_WARPMAP=<orchestrator scratch sidecar>   (sidecar-override)
     STREHL_ALIGN   unset   STREHL_FIX_HALO unset
G in {4.00, 2.00, 0.7078, 0.00};  4.00 is the shipped DEFAULT_GATE
alignment ON, reference frame 149, 299 placed / 0 refused, CatmullRom
```

**The gate-4.00 arm hashes `E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A`
`7ABC30D8E7F17112`, which is byte-identical to this milestone's own
`s31-bee3.tif`.** The assertion is in `96-gate-final.py` and fails the run if
it ever stops holding. So the ladder is anchored on the exact render §31
characterised, and §31's **+4296 DN** is its gate-4.00 point rather than a
separate measurement that has to be reconciled.

Two caveats recorded from the same logs and not swept: the solve's held-out
error is **13.578 px**, above M86's `T_usable` of 4.0 px, and coverage scales
the field of view to **0.9315**. Both apply identically to all four arms, so
they cannot produce a gate difference, but neither arm is a precise
registration. Separately, the owner's original brief recorded gate 2.00 as
`mean n_eff = 23.043` with 46.57% at `n_eff = 1`; this ladder records
**19.182** and **51.15%** for the same stack and gate. Unreconciled, and
plausibly the M86c watershed of §32.2, but not measured here.

### 33.2 The metric the orchestrator's failure demanded

Their own ring-profile instrument failed and they said exactly how, which is
what made this cheap. Both failures are repaired by construction rather than
by care.

**Their failure 1, the reference moved.** Every ring including the far
reference shifted monotonically across arms, because lowering the gate stops
averaging away the unfitted per-frame photometric drift. **Repair R1: every
mask — subject, far field, hair — is derived once from the gate-4.00 arm and
applied unchanged to all four.** The arms are then compared on identical
pixels, so a change is the image and not the segmentation. Deriving a mask per
arm is what let their reference move.

**Their failure 2, hair contamination.** A 45th-percentile threshold on a crop
that is 45.2% subject left hair tips in the near rings, and their 1–5 px ring
read **−3232 DN** — darker than far field, which is hair and not veil.
**Repair R2: thin dark structure is excluded by depth below a 9 px grey
dilation**, the population §31's `92-erasure.py` already uses, at a threshold
proportional to scene contrast rather than an absolute DN so that the excluded
set does not itself move between arms.

They asked for invariance to a 2.14% level shift. Weak invariance is not worth
registering, so the metric is built to be invariant to **any** affine map
`x → a·x + b`:

```
V  =  (peak ring residual)  /  (far background level − subject level)
```

Numerator and denominator are both first-order in the image, so `a` cancels
and `b` cancels twice. The local reference is a ratio of uniform filters,
which is linear, so the residual scales exactly. Medians are affine
equivariant. With the masks frozen by R1 the invariance is **exact**, and
`C-AFFINE` demands bit-level agreement rather than a tolerance.

### 33.3 Two of my own controls failed, and the worse one was my bar

I registered four controls before running and **two went red.** Neither bar
was weakened; both failures were diagnosed to a mechanism first
(`95-control-diag.py`).

**C-AFFINE returned 2.451e−07 against a registered 1e−12.** My own standing
rule is that a binary-exact factor must reproduce bit for bit, and that this
is what separates round-off from a leak. Diagnosis: the local reference sums a
251 px box, ~63 001 samples of magnitude ~5×10⁴, so the accumulator reaches
**~1.795e+09** against float32's exact-integer ceiling of 2²⁴ = 16 777 216 —
**107× over**. The sum cannot be exact, and it rounds differently once the
operands are scaled. Prediction: float64 collapses it. Measured: **3.664e−15,
6.69e+07× tighter**, on the same three factors. A genuine leak is
accumulator-width independent. The metric now runs in float64 and meets the
original bar.

**C-ROT returned 44.5% of the real veil against a registered 25%, and two
separate things were wrong.**

First, the control was contaminated by construction. I rotated the subject
mask *and* the far field *and* the valid set, re-admitting the real bee — 22.5%
of the crop — as ordinary background. Measured: **30.7%** of the rotated
2–60 px ring band lies in the real 2–60 px veil band and **23.4%** of it lies
inside the real subject. §31's `C-FAR` rotated only the distance geometry and
kept the real subject excluded, which is the better construction.

Second, **and this is the more serious error, my bar was sign-blind.** `V` is
a signed peak-hump amplitude and the hypothesis I registered in my own
docstring was directional — *“a hump under C-FAR would mean the estimator
manufactures one”*. I then coded `abs(V_ctl / V_real) < 0.25`. The repaired
control returns **V = −0.079502**: the maximum over the entire 2–60 px search
window is *negative*, so no hump exists at any distance, which is exactly what
a null should look like. `abs()` reported that as “0.590, FAIL”. **I did not
fail to find a null; I built a bar that cannot recognise one.**

That is the third sign-blindness failure in this milestone's family — `P95`'s
share-of-change ratio reading a 16.24% increase as “+99.6%, driver confirmed”,
the orchestrator's two-branch bar printing the wrong verdict for a 7.8× effect,
and now this. **A ratio of magnitudes is not a test of a directional claim.**

The replacement does not relax the threshold; it tests the registered
hypothesis, and then proves the null three ways rather than asserting it:

| control | construction | result | bar | verdict |
|---|---|---|---|---|
| `C-AFFINE` | `x → a·x + b`, a ∈ {0.5, 2, 4} binary-exact, b = 1000 | max \\|ΔV\\| **3.664e−15** | < 1e−12 | PASS |
| `C-DRIFT` | `x → 0.9786·x`, the measured 2.14% drop | V moves **0.000000%**, raw DN moves **2.1400%** | < 2% | PASS |
| `C-ROT-A` | mask rotated 180°, directional and signed | **−0.079502** against a bar of +0.033699 | < 0.25·V | PASS |
| `C-ROT-B` | shape: any hump in 2–60 px? | max over the window **−150 DN**, negative at every distance | no hump | PASS |
| `C-ROT-C` | independent null: mask **translated** by (−420, 520), band overlap 17.6% | **−0.093960** | < 0.25·V | PASS |
| `C-POS` | plant 0 / 1000 / 2000 / 4000 DN into the 8–45 px band | monotone, and **exactly** `V + A/C` — error **0.00e+00** at three of four levels | calibrated | PASS |

`C-DRIFT` is the one that answers the orchestrator directly: **the hazard they
warned about is real and present in these operands — the raw DN amplitude
moves by exactly the 2.14% they measured — and the metric does not move at
all.** `C-POS` is the one that makes the nulls mean something: an instrument
that is quiet and an instrument that can respond are different claims, and
this one returns a planted amplitude exactly in units of scene contrast.

### 33.4 The ladder

| gate | far level DN | amp DN | C DN | V | V/V(4.00) | peak d |
|---|---|---|---|---|---|---|
| **4.00** (shipped) | 52 527.0 | 4296 | 31 870 | **0.13480** | 1.0000 | 25 px |
| 2.00 | 52 120.0 | 3899 | 31 464 | 0.12393 | 0.9194 | 25 px |
| 0.7078 | 51 939.0 | 3712 | 31 285 | 0.11865 | 0.8803 | 25 px |
| **0.00** | 51 864.0 | 3716 | 31 208 | **0.11906** | **0.8833** | 25 px |

**B15: PARTIAL, r = 0.8833.** Not `GATE-DEPENDENT`, whose branch required
r ≤ 0.70. The peak sits at **25 px in every arm** — the gate does not move the
veil, it barely dents it. The ladder is not even monotone: 0.7078 reads
0.11865 and 0.00 reads 0.11906, a slight rise.

Against the orchestrator's own `neff-ladder.txt` for this stack:

| gate | mean n_eff | n_eff = 1 | veil V | veil retained |
|---|---|---|---|---|
| 4.00 | **55.321** | 38.77% | 0.13480 | — |
| 0.00 | **1.000** | 100.00% | 0.11906 | **88.3%** |

**A 55.3× change in the number of frames averaged per pixel buys an 11.7%
change in the veil.** At gate 0.00 every pixel is a single unaveraged frame,
and 88.3% of the veil is still there.

**B17, robustness.** 27 settings over hair threshold {0.06, 0.12, 0.24}, far
field {50, 70, 100} px and reference window {151, 251, 351} px: r ranges
**0.8717 … 0.9843**, median **0.9076**. Registered `ROBUST` required all of
[0.80, 0.95], so the verdict is **SOFT** — the spread crosses the upper edge.
What matters is which branch it crosses into: **no setting reaches
`GATE-DEPENDENT`, and several land in `GATE-INDEPENDENT`.** The conclusion is
robust in the direction that carries it even though the magnitude is not.
`C-SWEEP-NULL` — each arm against itself — returns r = 1 at all 27 settings.

### 33.5 The residual 11.7% is an offset, not weakening

It would be easy, and wrong, to report “the gate weakens the veil by 11.7%”.

**B16 refutes the proportional reading.** If the gate scaled the veil down,
`delta(d)` would track the veil profile with slope ≈ 1 − 0.8833 = 0.1167.
Measured over 56 rings: Pearson **0.1569**, slope **0.0186**. `NOT
PROPORTIONAL`.

Reading the profile instead of the correlation shows why. The veil residual
falls from **+4296 DN** at d = 25 to **+838 DN** at d = 60 — it has nearly
vanished. The delta over the same span goes **+580 → +486 DN**. A quantity
that stays put while the veil decays by 80% is not a fraction of the veil; it
is an offset sitting underneath it.

**That is precisely the hazard affine invariance does not cover, and the
orchestrator named it.** The metric is immune to `x → a·x + b` applied
globally — `C-DRIFT` proves that at 0.000000%. It is *not* immune to a level
change that differs between the near zone and the far zone, because the
baseline is taken from the far zone. They wrote that the drift is “organised
spatially by the election”; a spatially organised level change *is* a
near/far difference.

**B18** fits two one-parameter models to `delta(d)` over d = 5…60:

| model | fit | RMS residual |
|---|---|---|
| `M_const`: delta = c | **+473.2 DN** | **148.4 DN** |
| `M_prop`: delta = k · veil(d) | 0.1398 · veil | 221.1 DN |

Ratio **0.671** against a registered 0.70 — **`CONSTANT OFFSET`**, and by a
margin of only 4%, which is disclosed rather than rounded away. Its three
controls pass: `C-ZERO` returns 0 for both models on identically zero input,
and the two positive plants — data whose true form I chose — are each labelled
correctly, so the discriminator can respond and not merely stay quiet.

Removing the offset:

| | peak veil | r |
|---|---|---|
| gate 4.00 | 4296 DN | 1.0000 |
| gate 0.00, as measured | 3716 DN | 0.8833 |
| gate 0.00, offset removed | **4189 DN** | **0.9958** |

**96% of the apparent shortfall is the near/far offset.** The better estimate
is that **99.6%** of the veil survives with averaging switched off entirely,
and **88.3% is a lower bound.** The conclusion does not depend on which of the
two is preferred, which is the point of reporting both.

### 33.6 What this closes off

Three candidate mechanisms have now been tested against this artifact and all
three are excluded:

1. **Resampling** — fact 1375, invariant across all three kernels.
2. **The averaging gate** — this section, invariant across a 55.3× change in
   `n_eff`.
3. **Demosaic** — §27's photometric-step work.

The orchestrator's prediction that a gate-dependent veil would have to live in
the regime where the gate acts is a good one, and it is worth noting that it
*fails in the useful direction*: they measured the gate to have no effect where
there is detail (flattest tile 33.5×, most-detailed tile 1.00×), so the veil's
persistence at `n_eff = 1` cannot be dismissed as measuring a region the gate
never reached. The veil sits in flat background adjacent to a hard edge, which
is exactly where the gate *does* act, and it survives anyway.

**What remains is selection itself** — the owner's original hypothesis, and
what §1 found when the halo looked identical at `--gate 0` and `--gate 2`. This
section is that reproduction done with a controlled instrument instead of an
eye, on a 55× wider ladder, with the drift the eye could not have separated
removed by construction.

### 33.7 The standing question: model or support? Neither

The orchestrator has twice asked whether §13's **−28.2%** was a *model* failure
or a *support* failure, and says the two route completely differently. The
answer is already in this report and it is neither. It is a third thing, and
that third thing is now partly located.

**Not the model.** `P83`: hand the fit the true `alpha_k` cube on a plant with
known truth and it captures **+100.59%** of available headroom — band RMSE
1.7837% against a merge at 4.5271% and a single-frame noise floor of 1.7999%.
The forward model is right. It exceeds 100% because the intercept is estimated
across 121 frames and is quieter than any one of them.

**Not the support.** `P107` refutes it three ways. (1) `fit()` regresses across
the **frame axis at each pixel independently** — there is no spatial
neighbourhood that could be starved. (2) Finite observations per band pixel
measure **38.000 thin against 38.000 broad**, identical. (3) The recorded arms
run the wrong way: the per-pixel arm treated **19.8%** of the band against the
global arm's 12.5% and did **better**. More coverage with a better result is
the opposite of starvation.

**It is a third limiter, and it is structure-scale dependent.** `P106`: the
shipped per-pixel arm captures **−11.01%** on the thinnest quartile of boundary
points against **−32.80%** on the broadest — a **21.78 point** gap at **7.3**
null standard deviations. Against the registered −50% bar the thin quartile is
the *worse* performer. One pooled number, −28.16%, concealed a 3× difference
between two halves of its own population.

And `P108` sharpens it further in a way worth repeating, because it is a trap:
the alpha-attenuation mechanism that would explain the split **is real but
non-operative.** Thin structures do attenuate alpha as predicted — median
`amax` **0.1627** against **0.3444**, 2.1× — yet the admission gate still
passes **90.51%** of thin band pixels. The coverage limit is set by the
`R² ≥ 0.5` term instead. *A mechanism can be directionally correct and still
explain nothing if the valve it operates is already wide open.*

So the routing the orchestrator asked for: **not a rewrite of the forward
model, and not a change of support.** The next experiment is whether per-pixel
`k_F` is *estimable* on thin structures at all, which is §29's own conclusion
and remains open. This section adds one constraint to it: since the veil is
unchanged by a 55.3× change in averaging, the difficulty on thin structures is
unlikely to be a noise-averaging problem, which makes an estimability limit
more likely than a precision limit. That is an inference from tonight's
result, not a measurement of it.

### 33.8 The +72.9% concern, restated

The orchestrator's caution stands and is already answered. The metric that
reported **+72.9%** while erasing the bee's abdomen hairs is not the metric
that certifies the correction. `B14` measures **tip contrast on a referenced
thin-structure population** — 6316 → 3739 DN, **33.1%** of tips destroyed —
and that is the number that caught the erasure the halo metric could not see.
The acceptance gate is the rendered 100% crop, outranking every scalar here,
exactly as they asked. `P104` records the audit: M87's halo metric is a median
*level* profile against distance, not a sharpness proxy, and a Catmull-Rom
gather that destroys ~49% of gradient energy moves it by **+0.6%**.

Nothing in §33 is used to certify a correction. It measures what the artifact
*is*, and what it is not caused by.

### 33.9 Verification

`verify_s33.py` re-derives every figure here from `96-gate-final.json`,
`97-gate-attrib.json`, `98-delta-form.json` and `95-control-diag.json`,
re-hashes the gate-4.00 arm against §31's render, and re-reads the `n_eff`
ladder from the orchestrator's `neff-ladder.txt` rather than from my
transcription of it. `control_s33.py` mutates operands with the prose
untouched to prove the harness re-derives rather than matching the document
against itself.

"""

FACTS = [
    ("P127", "**A veil metric can be made EXACTLY invariant to a level shift, "
     "and exactly calibrated, rather than approximately either.** "
     "`V = peak ring residual / (far background level − subject level)` is "
     "first-order in the image top and bottom, so `x → a·x + b` cancels. "
     "Measured against the orchestrator's 2.14% drift: **V moves 0.000000% "
     "while the raw DN amplitude moves 2.1400%**. Planting a known veil "
     "returns `V + A/C` with error **0.00e+00** at three of four levels.",
     "Answers the orchestrator's constraint that any veil metric must be "
     "invariant to a 2.14% global level shift. Invariance by construction is "
     "checkable at 1e−15; invariance by care is not checkable at all. The "
     "calibration matters as much as the nulls: it proves the instrument can "
     "respond, which no null does.", "MEASURED"),

    ("P128", "**The occlusion veil is NOT an admission artifact: it survives a "
     "55.3× change in how many frames are averaged per pixel.** On four "
     "`bee-3-cpl` renders differing only in `--gate`, sharing one sidecar and "
     "a pinned exposure, mean `n_eff` falls **55.321 → 1.000** (38.77% → "
     "100.00% of pixels at `n_eff = 1`) while V falls only **0.13480 → "
     "0.11906**, r = **0.8833**, peak fixed at **25 px** in every arm. Across "
     "27 parameter settings r ∈ [**0.8717**, **0.9843**], median 0.9076, and "
     "**no setting reaches the `GATE-DEPENDENT` branch**.",
     "Refutes the orchestrator's eye judgement, which they had explicitly "
     "declined to promote. With resampling excluded by fact 1375 and demosaic "
     "by §27, averaging was the last cheap candidate; its exclusion leaves "
     "**selection itself**, which is the owner's original hypothesis and "
     "cannot be tuned away by any gate setting.", "MEASURED"),

    ("P129", "**And 96% of even that 11.7% is a level offset, not the veil.** "
     "`delta(d)` correlates with the veil profile at Pearson **0.1569**, slope "
     "**0.0186** where 0.1167 was predicted, and stays at **+486 DN** at "
     "d = 60 where the veil itself has decayed from +4296 to +838 DN. A "
     "constant fits it at RMS **148.4 DN** against **221.1 DN** for a "
     "proportional model, ratio 0.671 against a 0.70 bar. Removing the "
     "**+473.2 DN** offset gives r = **0.9958**.",
     "The near/far offset is exactly the spatially organised drift the "
     "orchestrator described, and it is the one form of level change affine "
     "invariance CANNOT cover, because the baseline is taken from the far "
     "zone. So 88.3% is a lower bound on veil survival and 99.6% is the "
     "better estimate. Reporting both is what makes the conclusion "
     "independent of the 4% margin on B18.", "MEASURED"),

    ("P130", "**I wrote a control bar that could not recognise a null: "
     "`abs(V_ctl / V_real) < 0.25` on a SIGNED hump amplitude.** The repaired "
     "rotated-mask control returns **−0.079502** — negative at every distance "
     "in the 2–60 px window, so no hump exists to manufacture — and the "
     "absolute-value form reported that as **0.590, FAIL**. Two independent "
     "nulls of different construction agree: rotated **−0.079502**, "
     "translated **−0.093960**.",
     "The third sign-blindness failure in this milestone's family, after "
     "`P95`'s share-of-change ratio and the orchestrator's two-branch bar. "
     "**A ratio of magnitudes is not a test of a directional claim.** The "
     "control was also contaminated by construction — 30.7% of its ring band "
     "lay in the real veil band — so one red control had two independent "
     "causes and neither was the metric.", "MEASURED"),

    ("P131", "**A binary-exact invariance control failed at 2.451e−07 because "
     "of the ACCUMULATOR, not a leak.** A 251 px box reference sums ~63 001 "
     "samples of magnitude ~5×10⁴, reaching **~1.795e+09** against float32's "
     "exact-integer ceiling 2²⁴ = 16 777 216 — **107× over**. In float64 the "
     "same three exact factors give **3.664e−15**, **6.69e+07× tighter**.",
     "Extends the standing rule that binary-exact factors must reproduce bit "
     "for bit: when they do not, the next question is the accumulator width, "
     "because a real leak is width-independent and round-off is not. The bar "
     "was diagnosed and met, never relaxed.", "MEASURED"),

    ("P132", "**The −28.2% unmix is neither a model failure nor a support "
     "failure.** Not the model: with the true `alpha_k` cube the fit captures "
     "**+100.59%** of headroom (`P83`). Not the support: the regression runs "
     "along the **frame** axis per pixel with **38.000** observations on thin "
     "and broad alike, and the arm with **19.8%** coverage beat the one with "
     "12.5% (`P107`). It is a **structure-scale** limiter — **−11.01%** thin "
     "against **−32.80%** broad, 21.78 points at 7.3 null sd (`P106`).",
     "Answers the orchestrator's twice-asked routing question with a third "
     "option they did not offer. The routing that follows: not a rewrite of "
     "the forward model and not a change of support, but whether per-pixel "
     "`k_F` is estimable on thin structures at all. `P128` adds that this is "
     "unlikely to be a noise-averaging limit, since a 55.3× change in "
     "averaging leaves the artifact intact.", "DERIVED"),
]


def main():
    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"
    assert "## 33." not in raw, "section 33 already present"

    for f in (DATA / "96-gate-final.json", DATA / "97-gate-attrib.json",
              DATA / "98-delta-form.json", DATA / "95-control-diag.json"):
        assert f.exists(), f"missing operand {f}"
    json.loads((DATA / "96-gate-final.json").read_text(encoding="utf-8"))

    rows = []
    for pid, claim, why, prov in FACTS:
        row = f"| {pid} | {claim} | {why} | {prov} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"{pid}: {n} unescaped pipes, need 5"
        assert row.count("`") % 2 == 0, f"{pid}: odd backtick count"
        rows.append(row)

    body = SECTION.replace("\r\n", "\n").replace("\n", "\r\n")
    if not raw.endswith("\r\n"):
        raw += "\r\n"
    text = raw + body

    anchor = "| P126 |"
    i = text.index(anchor)
    j = text.index("\r\n", i) + 2
    text = text[:j] + "\r\n".join(rows) + "\r\n" + text[j:]

    assert text.count("\n") == text.count("\r\n"), "CRLF broken by append"
    DOC.write_bytes(text.encode("utf-8"))
    print(f"appended section 33 and {len(rows)} fact rows (P127-P132)")
    print(f"  {DOC}: {text.count(chr(10))} lines, {len(text)} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
