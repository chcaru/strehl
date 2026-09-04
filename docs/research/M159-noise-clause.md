# M159 — what can honestly be called lower noise

**CORRECTION TO `249f77db`: THE OWNER'S COMPARATIVE “STRICTLY LOWER NOISE”
CLAUSE CANNOT BE CLAIMED TODAY.**
The only claimable current number is narrower and negative: on twelve frozen
flat-paper ROIs, DELIVER-V6 has `1.515208×` the fork's fractional box9 residual.
That is an output-residual result, not a detail-controlled physical-noise claim.

Detail is not the only gate. The current output also loses the named residual
comparison, no existing comparator pair was rendered on a certified featureless
target, and the archived SHIP-V2 numerator is absent.

## 1. Scope and correction

M158 already completed the document-governance audit. This report accepts its
`TARGET 1` ruling rather than repeating it:

* the scorecard's global M1 coupling and `98%` threshold are not owner-authored;
* the underlying anti-blur coupling is nevertheless real; and
* the historical “quotable now” values do not establish the current comparative
  claim because their detail cost was unmeasured
  (`docs/research/M158-scorecard-drift.md`, “Priority verdicts” and
  “Priority target 1 / finding 14”).

M135 independently closes the apparent escape through the old detail metrics.
Its exact common-postfilter argument eliminates FRC, FSC, normalized spectral
SNR, magnitude-squared coherence, NCC, and `C/(C+U)` as stand-alone guards
against both post-render blur and sharpening
(`docs/research/M135-detail-instrument.md`, “The precise impossibility
result”). Its replacement is the
non-compensating `J_TR` information coordinate plus veto-only `T_TR` transfer
and `U_TR` unexplained-structure coordinates. The estimator is synthetically
commissioned, but the physical reference, coded target, independent
calibration, and matched-flat lineage do not exist in a scored capture
(`M135-detail-instrument.md`, “Recommended physical protocol,” “Admission
decision,” and “Bottom line”).

The previous M159 report made a categorical error: it treated the plan's
parenthetical “existing flat-ROI instrument” as sufficient to license a
comparative noise score. M159's own blur challenge had already disproved that
inference. A blur reduced the statistic to `0.571215×`. The instrument measures
a useful output residual, but without a separate transfer bound it rewards the
exact cheat that makes “lower noise” uninformative.

No holdout was opened for this correction. No image measurement was repeated.
The already-committed, byte-pinned M159 outcomes and controls are reinterpreted
below.

## 2. (a) Which formulations survive without a detail instrument?

### 2.1 Decision table

| proposed formulation | survives in principle without M1? | supported by existing data today? | ruling |
| --- | --- | --- | --- |
| **Matched delivered detail, then compare noise** | **No.** Exact matching needs independently anchored transfer/information, not equal dimensions or equal settings. | No truth-referenced detail instrument or qualifying capture exists. | **BLOCKED** |
| **Matched on one named proxy, then compare residual** | Yes, but only if the claim says “matched on `<proxy>`”; it may not say “matched detail.” | No current positive result has a commissioned, adequately powered proxy. | **NO CURRENT CLAIM** |
| **Noise on a featureless subject fixed by construction** | **Yes**, as a target- and mode-specific noise/nonuniformity claim. It does not imply equal photographic detail elsewhere. | No common-input Strehl/comparator output pair exists on a certified flat or dark repeated target. | **VIABLE AFTER NEW CAPTURE/OUTPUTS** |
| **Lower residual and no worse on a named observable** | Yes as an explicitly bounded conjunction; it does not become a general detail claim. | Current DELIVER-V6 fails the lower-residual limb. Historical SHIP-V2 lacks a retained numerator and did not establish fine-detail parity. | **NO CURRENT CLAIM** |
| **Dominance: lower noise and not-lower delivered detail** | Only with a valid non-compensating detail certificate, or a scope where scene detail is absent by construction. | Neither condition exists, and DELIVER-V6's residual ratio is above one. | **BLOCKED** |
| **Fractional box9 residual only** | **Yes.** This is a direct property of the output bytes. | Yes; the result is `1.515208×` and is adverse. | **CLAIMABLE, BUT NOT AS “NOISE”** |

The answer depends on the noun. A **residual** claim is available today. A
positive comparative **noise** claim is not.

### 2.2 What “matched” can mean without a detail instrument

Without truth or a commissioned detail instrument, “matched detail” has no
defensible global meaning. The following do **not** establish it:

* the same source frames, output dimensions, pixel pitch, or nominal scale;
* equal parameter names in different programs;
* equal local contrast or histogram;
* equal FRC/coherence/normalized-SNR values, because a common post-render blur
  can leave those values unchanged;
* equal gradient, Laplacian, or high-band energy, because noise and sharpening
  can raise them.

A weaker statement may condition on a frozen observable:

> On the declared sites, modes A and B are equal within the registered
> uncertainty on observable X; under that condition, A has lower estimator Y.

That sentence is defensible only as **X-matched**, not detail-matched. It needs
X to have a movable null, degradation and improvement controls, adequate power,
tone/clipping/geometry guards, frozen sites, and an explicit defeat list.

No existing proxy supplies that result:

* the coffee-bean 10–90% edge width had no power against a `0.8 px` Gaussian,
  so its real value was explicitly discarded
  (`docs/research/V-HEADTOHEAD.md:138-149`);
* the archived shape-normalized spectrum was not a general detail certificate
  and reported SHIP-V2 below the fork in the `0.20–0.30` and `0.30–0.40`
  cycles/prior-pixel bands (`0.833×` and `0.766×` before its later
  retraction; `V-HEADTOHEAD.md:171-196`);
* M135's slanted-edge `S_25` and ordinal `Q25` candidates failed their
  sharpening, tone, noise, angle, sample-size, or genuine-improvement controls
  (`M135-detail-instrument.md`, “Slanted edge, `S_25`, and `Q25`”).

Choosing only a favourable coarse band after seeing that vector would be
outcome-selected. It cannot rescue the historical claim.

### 2.3 A subject fixed or bounded by construction

There is one honest route around a general detail instrument: remove scene
detail from the scope of the claim.

On a preregistered uniform radiance target or dark target, independently
verified to be featureless over the measured band, the latent spatial signal is
constant by construction. Independent repeat captures can then separate
temporal noise from fixed pattern, and a common-input comparator pair can
support a statement such as:

> On this uniform target, at these exposure, tone, output-size, and mode
> settings, Strehl's temporal output residual is lower than comparator C's.

That is a valid **flat-target output-noise** claim. It says nothing about
photographic detail, general noise efficiency, or the full owner sentence.
Blur is no longer hiding target detail locally because the target has none,
although the report must still disclose that a renderer may spatially smooth
sensor noise. A constant-output renderer would win this narrow statistic; that
is why it cannot be promoted to a quality or efficiency claim.

No existing pair qualifies:

* the coffee background is paper, not a calibrated uniform source; the archived
  inspection found dust, a diagonal band, and blobs in the Strehl residual
  (`V-HEADTOHEAD.md:253-268`);
* the 113MSDCF “flat” candidates carry `5.4%–10.5%` box9 residual and visible
  frost structure;
* the repository has dark, paper, and flat-field controls, but no matched
  external-comparator output on them; the surviving flat-named TIFFs under
  `C:\dev\strehl-out` are Strehl-only;
* M71's 484 flat-field frames are already extensively analyzed development
  evidence and have no comparator render, so they are not the requested
  non-burned score substrate;
* the ISO-100 flat-round target is registered holdout and was not opened
  (`experiments/M141-capture-inventory/holdout-register.json:202-214`).

### 2.4 Bounded and dominated claims

A bounded conjunction could be scientifically honest if it named every limit,
for example:

> Lower temporal residual on the frozen flat sites, with no larger median
> 10–90% width and no greater overshoot on the frozen edge sites.

That wording does not generalize beyond those observables. It also does not
survive the current evidence:

1. DELIVER-V6 fails the lower-residual limb against both usable comparators.
2. The coffee edge-width instrument failed its blur sensitivity control.
3. The historical spectrum did not show fine-band parity.
4. The historical SHIP-V2 TIFF needed to remeasure the joint tuple is absent.

Therefore neither a bounded positive claim nor a dominance claim can be made
from existing outputs. The strongest true statement today is the adverse
metric-only result in §4.

## 3. Existing-data admissibility

### 3.1 Comparator and capture inventory

The usable existing pairs remain:

| subject | comparator | capture status | use here |
| --- | --- | --- | --- |
| `coffee-bean`, 105 frames | focus-stack fork, linear Rec.2020 | fixed historical benchmark, not holdout | primary residual result |
| `113MSDCF`, 63 frames | Zerene PMax, linear Adobe RGB | historical control, not holdout | structured diagnostic only |

There is no DMap or Helicon output. The historical SHIP-V2 Strehl TIFFs are
absent. Current DELIVER-V6 masters are byte-pinned in
`experiments/M159-noise-clause/results.json:inputs`.

The protected bee repeat and flat-round target were not opened. Calibration
grid, slide, and ruler development units were not used. The correction reads no
new outcome and changes no burn status.

### 3.2 What the existing instrument computes

The historical implementation is:

```python
def hp(a, r=4):
    return a / ndimage.uniform_filter(a, 2*r+1) - 1.0
```

It reports the population standard deviation of that fractional residual
(`experiments/V-HEADTOHEAD/hplook.py:10-20`). M159 applies the same statistic to
the twelve pre-existing comparator-selected `FLAT_ROIS`
(`experiments/V-HEADTOHEAD/spec.py:87-92`; selection method
`survey.py:8-26`).

The quantity is now named precisely:

```text
R_box9 = population_sd(green / box9(green) - 1).
```

It contains stochastic noise, fixed pattern, dust, surface texture, residual
grade, registration mismatch, and any other structure in that band. It is not
a decomposition of those terms.

## 4. (b) The number that can be produced today

**Sign convention:** every ratio below is
`Strehl R_box9 / comparator R_box9`. A ratio below one means lower fractional
box9 residual. It does not by itself mean lower physical noise.

### 4.1 Coffee-bean versus fork — primary

Denominators:

* 693 grid candidates;
* 385 excluded for comparator clipping;
* 12 excluded by the comparator mean gate;
* 296 eligible for comparator-only ranking;
* 12 frozen sites selected and 12 scored;
* 0 post-selection exclusions.

Per-site ratios, in frozen order:

```text
1.570850  1.588428  1.497986  1.457075
1.590879  1.552260  1.491656  1.496315
1.538359  1.532431  1.453918  1.335062
```

Distribution: minimum `1.335062`, p25 `1.483011`, median **`1.515208×`**,
p75 `1.556907`, maximum `1.590879`; fixed-seed bootstrap interval for the site
median `[1.474366,1.561555]`. **0/12 sites are below one.**

Claimable sentence:

> On the twelve frozen coffee-paper ROIs, DELIVER-V6's fractional box9
> residual is `1.515208×` the fork's median site value, with all twelve site
> ratios above one.

Not claimable: “DELIVER-V6 has 51.5% more physical noise.” Some or all of the
excess may be recovered paper structure. Conversely, that uncertainty cannot
be turned into a lower-noise claim.

### 4.2 113MSDCF versus PMax — diagnostic

Of 693 candidates, 9 were comparator-clipped, 161 failed the mean gate, 523
were eligible, 12 were selected, one was excluded for Strehl clipping, and 11
were scored. The median ratio is `1.377766×`, range
`1.189916×–1.613540×`, with **0/11 below one**.

This is not promoted even to a flat-residual population claim because the
selected regions visibly retain frost structure. It is only a same-sign
diagnostic.

### 4.3 Archived SHIP-V2

The archived report records one coffee-paper site at fork `0.5025%`, SHIP-V2
`0.1125%`, ratio `0.224×`. M159 reproduces the fork denominator at
`0.5025019%`, but the SHIP-V2 numerator TIFF is absent. More importantly, the
same report did not establish non-lower fine detail. The number may be cited as
an **archived fractional-residual observation**, not as a current comparative
noise or dominance result.

## 5. Commissioning evidence and its limit

The exact `R_box9` implementation was commissioned before the current images
were read:

| control | construction | measured result |
| --- | --- | --- |
| movable null | two independent equal-noise captures of one smooth latent field | median `0.999622×`, range `0.993655–1.008012`; 69/128 below and 59/128 above one |
| planted degradation | add independent noise at `1.5×` the capture sigma | median `1.801389×`, range `1.789131–1.816619`; 128/128 above one |
| planted improvement | average four independent captures of the same latent field | median `0.499915×`, range `0.496874–0.503378`; 128/128 below one |

The current tone inverse recovers source high-pass RMS at `0.9999967×`.
Arithmetic, hashes, geometry, distributions, and controls are independently
checked by `experiments/M159-noise-clause/verify.py`.

Those controls commission **sensitivity** to noise. They do not commission
**specificity**. The specificity challenge is decisive:

| challenge | result | implication |
| --- | ---: | --- |
| blur a noisy field containing real six-pixel texture | `0.571215×` | the statistic strongly rewards lost detail |

Thus the instrument is commissioned for the exact residual it reports and
explicitly **not** commissioned as a stand-alone comparative noise-quality
instrument.

## 6. (c) Minimum additions, ranked by cost

### To the first defensible positive noise statement

| rank | addition | type | claim it would enable |
| ---: | --- | --- | --- |
| 1 | Preregister and capture two independent repeat blocks of a verified uniform target plus matching dark/flat calibration; render the identical inputs through Strehl and one comparator; use input-only ROIs and temporal/cross-fit residuals. | **new photons**, comparator output, small bounded analysis | narrow flat-target output-noise claim; no general detail claim |
| 2 | Add a frozen edge/transfer sentinel to the same capture and commission a proxy with null, blur, sharpening, genuine-improvement, tone, clipping, angle, and power controls. | **new photons + analysis/code** | explicitly proxy-conditioned “lower noise while no worse on X” claim |
| 3 | Run M135's full physical `J_TR + T_TR + U_TR` protocol with coded target, independently sampled higher-resolution reference, disjoint calibration, matched flat sentinels, and the same frozen Strehl/comparator modes. | **new physical target + new photons + integration** | broad non-compensating comparative detail/noise claim, if both limbs pass |

No analysis-only transformation of the current outputs can create the missing
lineage. Recovering the exact SHIP-V2 TIFF or rerendering gate 4.5 after the
quiet order would make the old residual result auditable, but would still yield
only a residual or proxy-conditioned result until transfer is independently
bounded.

The cheapest route to a real noise statement is therefore **new flat-target
photons**, not J_TR. The cheapest route to the owner's broad comparative clause
is the full M135 physical campaign.

## 7. (d) Is J_TR the single gate?

**No.** Detail is one gate among several.

The clause does not become claimable when the `J_TR` code merely exists; that
code already exists synthetically. It becomes relevant only when the physical
reference chain is commissioned and the same frozen output bytes/settings pass
the non-compensating `J_TR`, `T_TR`, and `U_TR` certificate.

Even then all of the following remain:

1. **Noise substrate:** the same mode needs a certified flat sentinel or an
   independent temporal/cross-fit noise estimate.
2. **Comparator:** the same common inputs need a retained, hashable comparator
   output. A full commercial-comparator claim still lacks DMap/Helicon today.
3. **Same-output binding:** detail and residual may not come from different
   parameter settings or versions.
4. **Actual sign:** the candidate must really score below one. Current
   DELIVER-V6 scores `1.515208×`, so admitting J_TR would not turn this output
   into a noise pass.
5. **Provenance and power:** physical extraction, calibration independence,
   site population, uncertainty, and refusal paths must survive commissioning.

If a future M135 campaign includes its required matched flat sentinels,
comparator outputs, and same-settings binding, then it can close items 1–3 in
one campaign. It still cannot manufacture item 4.

## 8. Defects for the orchestrator

M158 owns the completed governance inventory; it is not repeated here. Two
exact replacements follow from this scientific correction.

### 8.1 Owner-plan current-state row

The plan row calling the historical noise values “quotable now” is too broad.

**Proposed owner-approved replacement for the row's status/result text:**

> **Historical flat-residual result; comparative noise claim not admitted.**
> SHIP-V2 recorded `0.224×` the fork's fractional box9 residual at one
> flat-paper site, but the numerator artifact is no longer retained and
> delivered detail was not independently pinned. Current DELIVER-V6 measures
> median `1.515208×` on twelve frozen sites, with `0/12` below one. Report these
> as versioned residual observations until a same-output detail/transfer guard
> or a certified featureless-target protocol exists.

### 8.2 Scorecard joint anti-cheat row

The scorecard is right that the anti-blur coupling exists, but it hard-codes an
unratified global M1/`98%` solution and additionally requires M4 and M8 to pass.

**Proposed replacement for the M1/M2/M4/M8 binding-rule cell:**

> A comparative lower-noise claim requires either (a) a commissioned,
> non-compensating detail/transfer certificate on the same output bytes and
> settings, or (b) an explicitly featureless-target scope that makes no
> photographic-detail claim. No owner-ratified retention percentage currently
> exists. Until one route is commissioned, publish flat-ROI values only as
> output residuals. M4 and M8 remain separately reported axes and do not veto
> that descriptive residual.

`docs/STATUS.md:5575-5578` already states the corrected substantive position:
the noise clause cannot be quoted while detail cost is unmeasured. No
replacement is needed there.

## 9. What would make this wrong

The strongest counterexample would be a retained, hash-matching SHIP-V2 output
plus a pre-outcome, adequately powered transfer observable showing no loss on
the same bytes/settings. That could support a narrow proxy-conditioned lower
residual claim without waiting for full M1.

A previously unindexed common-input comparator output on a certified uniform
repeat target would also defeat the “new photons” conclusion and permit the
narrow flat-target claim immediately. The inventory found none.

Finally, if the owner intends “noise” to mean only the literal
`R_box9` output statistic, with no implication of stochastic noise, efficiency,
or preserved detail, then the clause is scoreable now and DELIVER-V6 fails at
`1.515208×`. The orchestrator's clarified meaning rejects that interpretation;
this report therefore uses “residual” for the observable and reserves “noise”
for a claim whose detail or featureless-target condition is pinned.
