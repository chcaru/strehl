# M159 — the owner's flat-ROI noise clause

**VERDICT: SCOREABLE TODAY.**
**Current shipping score: FAIL.** On the only pre-existing frozen comparator
flat-ground population, DELIVER-V6 / fork is `1.515208×` median high-pass RMS;
all `12/12` sites are above `1`, so DELIVER-V6 is noisier under the owner's named instrument.
The scorecard's M1/`98%` gate and `eta <= 1.10` bar do not govern this score.

This is a scoreability finding, not a claim that the historical result was fabricated.
The archived SHIP-V2 report records a `0.224×` PASS on one of these sites. The same
fork pixels and statistic reproduce its `0.5025%` denominator today, but the SHIP-V2
numerator is no longer on disk. The surviving current DELIVER-V6 master reads
`0.824501%` at that site, or `1.640791×` the fork. The plan's unqualified
**“Ahead, measured ... Nothing — quotable now”** is therefore a versioned historical
statement, not a current-default result.

## 1. The plan's exact requirement

The governing plan introduces the target as “The end-state sentence the project
should be able to print, each clause with its licensing instrument in parentheses”
and then says, verbatim:

> On [subjects], strehl resolves detail at or beyond the best shipping comparator
> (D1: FRC + slant-edge, licensed Zerene PMax *and* DMap), at strictly lower noise
> (existing flat-ROI instrument), with zero invented structure (hull census, stamped
> per file), no occlusion veil above [bar] (halo instrument at full reach), while
> emitting per-pixel certified acuity, n_eff, and depth in physical units that no
> comparator emits at all (D2/D8/A5/C5), in [X] s per frame on CPU (existing harness).

That is `docs/proposals/2026-08-sota-path.md:189-197`. The noise clause and its
licence, exactly, are:

> at strictly lower noise
> (existing flat-ROI instrument)

The plan's axis table says, verbatim:

> | Noise, flat/defocused ground | **Ahead, measured.** 4.5× vs the fork (≥2.4× worst-case grade-corrected); 0.746× vs one unstacked frame at gate 4.5; 9.9× flat-field rms on the deepest stack with the compound eye indistinguishable (README) | Nothing — quotable now |

That row is `docs/proposals/2026-08-sota-path.md:172-174`. No `eta` bar, 32-ROI
minimum, cross-fit repeated-capture design, or detail-retention percentage appears in
the clause or row. The plan later says explicitly that the noise instrument remains
live (`:2208-2210`) and that scorecard rule 4 and its `98%` threshold are the
scorecard author's invention (`:2399-2406`).

The scorecard asks a different question. Its M2 requires two 32-frame repeat blocks,
external 16-frame means, temporal `sigma_1`, cross-fit residuals, at least 32 ROIs,
and a future-M1-qualified comparator (`docs/proposals/2026-09-sota-scorecard.md:
674-697`). Its `eta <=1.10` and comparator UCB `<=0.950` are expressly labelled
**SCORECARD ADDITION** (`:695-697`), and rule 4 is expressly
**“SCORECARD ADDITION — UNRATIFIED”** (`:126-139`). M2 remains `UNMEASURED`.
None of that prevents reporting the owner's narrower flat-ROI axis.

The pass rule used here adds no threshold: the owner says **strictly lower**, so
`strehl/comparator < 1` passes and `>=1` does not.

M158 was right that the historical `0.746×` single-frame result is not a free
**M2 PASS** because its detail cost is unmeasured
(`docs/research/M158-scorecard-drift.md:53-58,152-180`). M159 does not promote it.
This report scores the separately named owner-plan instrument and reports a FAIL;
it makes no “better stack” or full-SOTA claim.

## 2. Instrument inventory and commissioning status

### 2.1 The instrument that produced the plan's comparator number

`experiments/V-HEADTOHEAD/hplook.py:10-11` defines:

```python
def hp(a, r=4):
    return a / ndimage.uniform_filter(a, 2*r+1) - 1.0
```

It takes the population standard deviation of that fractional 9×9-box residual
(`:18-20`). It reads each arm's integer crop covering the same scene area; it does
not resample the scored pixels (`experiments/V-HEADTOHEAD/spec.py:36-47`).
The original comparator-relative site was a 320×320 region at `(y=968,x=584)`
(`hplook.py:39`). The committed result is fork `0.5025%`, Strehl `0.1125%`,
ratio `0.224` (`docs/research/V-HEADTOHEAD.md:253-268`).

The original result had three important strengths:

* both arms used the same 105 captures (`V-HEADTOHEAD.md:77-86`);
* the fork arm was linear Rec.2020 and the Strehl viewing transform was inverted and
  falsifiably checked (`:101-120`);
* the selected region was visibly flat/defocused paper, and the report inspected the
  residual rather than trusting the scalar alone (`:253-264`).

But the noise statistic itself had **not** received the required three-way
commissioning. `spec.py` had an identical-byte null and a blur control
(`experiments/V-HEADTOHEAD/spec.py:94-108`), but they commission its spectral-detail
statistic; the identical-byte null is also tautologically `1.000`.

M159 therefore retained the exact `hplook.py` statistic, expanded the already-frozen
population to all twelve `FLAT_ROIS` from `spec.py:91-92`, and commissioned the noise
statistic before reading the current output. Site selection came from the existing
comparator-only survey: 384×384 cells on a 192-pixel grid, reject clipping and means
outside `(0.05,0.85)`, rank by `std(x-box9(x))`
(`experiments/V-HEADTOHEAD/survey.py:8-26`). Selecting on the comparator is
conservative for a lower-is-better Strehl claim.

### 2.2 The later in-product flat statistic

`crates/strehl-core/src/flat_ratio.rs` is a stronger **within-stack** diagnostic:

* `highpass_residual` computes `x - box9(x)` only on the valid interior
  (`:145-179`);
* its derived white-noise gain is
  `sqrt(1 - 1/81) = 0.9938079899999065` (`:111-124`);
* `FlatReference` retains every source frame, and `ratio` reports the median
  denominator plus the quietest/noisiest range (`:246-258,278-352`);
* white noise is checked against the closed form (`:425-478`) and a planted
  10× degradation is caught on structured ground (`:539-629`).

It fixes the privileged-single-frame denominator used by older internal acceptance
checks. It does **not** compare Strehl with an external stacker, so it cannot by itself
answer the owner's comparator clause. Its checked plants also did not include a
planted improvement. It is inventory, not the scoring implementation used below.

### 2.3 Related single-frame instrument

`experiments/BUILD-PYRNOISE/measure.py` compares stack arms with every unstacked
frame, discloses the complete denominator distribution, and uses a valid-interior
`x-box9(x)` statistic. It produced the plan row's `0.746×` gate-4.5 number
(`docs/research/BUILD-PYRNOISE.md:328-370`). It is not comparator-relative.
Its report also supplies the warning that a lower flat statistic is only half a
trade: a plain mean can win by destroying detail (`:240-247,452-463`).

## 3. Comparator inventory

The usable, frame-matched artifacts found today are:

| subject | comparator artifact | status |
| --- | --- | --- |
| `coffee-bean`, 105 frames | `C:\dev\macro\out\coffee-bean\stack.tif` | focus-stack fork; linear Rec.2020; **used for the scored result** |
| `113MSDCF`, 63 frames | `D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif` | Zerene Stacker PMax; linear Adobe RGB; used only as the supplemental diagnostic below |
| `113MSDCF`, 63 frames | `C:\dev\macro\out\stack_test2_rec2020.tif` | fork output exists, but not used: the prior commissioned registration audit found 5.3 px RMS local disagreement and rejected 41/64 regions (`docs/research/V-HEADTOHEAD2.md:765-769`) |

The matching statements—105/63 identical source-frame sets, comparator develop
settings, and raw-vs-Lightroom asymmetry—are recorded at
`docs/research/V-HEADTOHEAD.md:77-86`. M159 decoded the embedded profiles rather than
guessing: the fork is linear Rec.2020; the PMax output and its input are both
“Adobe RGB (1998) (Linear RGB Profile)”; the current Strehl masters are tagged sRGB
viewing renders (`experiments/M159-noise-clause/inspect_inputs.py`,
`results.json:inputs`).

Five PMax TIFFs exist under `D:\edited\macro` (`marker`, `marker2`, `test`, and
`test2`). Only `test2` has the already-established 63-frame match to a current Strehl
subject. The marker pairing was previously abandoned because it is a different
capture (`V-HEADTOHEAD.md:88-94`). There is **no DMap output** and **no Helicon
output** in the searched comparator roots.

The surviving current Strehl files are:

* `C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff`, SHA-256
  `F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC`;
* `C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff`, SHA-256
  `4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F`.

Both were built by binary `6af834dac08d` with plain `stack ... --srgb`
(`experiments/DELIVER-V6/BANK-33.md:8-18,60-67`). The historical SHIP-V2 files named
by `V-HEADTOHEAD.md:80` are absent from both current output roots. Their archived
recipe was binary `b9b6921`, explicitly `--merge pyramid --pyramid-gate 4.5 --srgb
--auto-exposure` (`docs/research/BUILD-RENDER.md:2030-2037`). This version/configuration
split is why the old `0.224` must not silently be attached to DELIVER-V6.

The missing DMap/Helicon files do not block this narrow score. In the six-clause
sentence, PMax and DMap license **D1 detail**, while noise has its own parenthetical
instrument. The plan's own noise row specifically names the fork. Their absence does
block broader “best commercial comparator” language and the full conjunctive SOTA
sentence.

## 4. Holdout and burn analysis

The governing unit is exactly **subject plus uninterrupted capture session**.
Reading any output or verdict for one member burns the unit
(`docs/proposals/2026-09-sota-scorecard.md:397-403`).

Before reading an outcome, M159 established:

* `coffee-bean`: **FIXED HISTORICAL BENCHMARK — NOT HOLDOUT**, 105 frames
  (`experiments/M141-capture-inventory/holdout-register.json:288-294`);
* `113MSDCF`: **HISTORICAL CONTROL — NOT HOLDOUT**, 63 frames (`:297-301`);
* the registered bee repeat remains protected holdout (`:130-139`);
* the calibration-grid and high-resolution-slide sessions are burned/development
  (`:8-54`);
* the three ruler sessions are **BURNED — DEVELOPMENT ONLY** in the current
  scorecard (`2026-09-sota-scorecard.md:372-374`), despite stale “clean” rows in the
  generated holdout register (`holdout-register.json:94-127`).

No protected or indeterminate pixels were opened. M159 read only the two historical
subjects and their already-existing outputs.

## 5. The number

### 5.1 Primary owner-plan score: coffee-bean versus the fork

**Sign convention:** every ratio is `Strehl high-pass RMS / comparator high-pass
RMS`. Lower is quieter. The owner's clause passes only below `1`.

The score uses the twelve pre-existing 384×384 `FLAT_ROIS`, in their frozen order.
Each arm reads an integer box covering the same scene area; neither scored arm is
resampled. A robust 51-tile similarity fit found scale `1.034433`, rotation
`+0.03017°`, translation `(+14.08,+4.98)` px, with `2.58` px component RMS residual.
This closely reproduces the old `1.035063` / `+0.03148°` geometry
(`V-HEADTOHEAD.md:101-107`) closely enough for 384-pixel flat boxes.

Denominators:

* candidate grid: **693**;
* excluded before ranking: **385** for comparator clipping, **12** for the
  comparator mean gate, **0** for target bounds;
* eligible for comparator-only ranking: **296**;
* frozen sites selected: **12**;
* actually scored: **12**;
* excluded after selection: **0**.

| site `(y,x)` | fork RMS | DELIVER-V6 RMS | Strehl / fork |
| --- | ---: | ---: | ---: |
| `(968,584)` | 0.005242 | 0.008234 | 1.570850 |
| `(1160,584)` | 0.005203 | 0.008265 | 1.588428 |
| `(968,392)` | 0.005501 | 0.008241 | 1.497986 |
| `(1160,392)` | 0.005670 | 0.008262 | 1.457075 |
| `(1736,392)` | 0.005204 | 0.008278 | 1.590879 |
| `(1736,584)` | 0.005242 | 0.008136 | 1.552260 |
| `(968,776)` | 0.005530 | 0.008248 | 1.491656 |
| `(1160,776)` | 0.005479 | 0.008198 | 1.496315 |
| `(1928,584)` | 0.005309 | 0.008167 | 1.538359 |
| `(1928,392)` | 0.005343 | 0.008187 | 1.532431 |
| `(1352,584)` | 0.005649 | 0.008214 | 1.453918 |
| `(776,584)` | 0.006112 | 0.008160 | 1.335062 |

**Distribution:** min `1.335062`, p25 `1.483011`, median **`1.515208×`**, p75
`1.556907`, max `1.590879`; fixed-seed site bootstrap interval for the median
`[1.474366, 1.561555]`. **Zero of twelve sites are below 1.**

Thus, under the exact named flat-ROI statistic, the current shipping output has
**51.5% higher**, not lower, high-pass RMS than the fork on the scored population.
This is an owner-plan-axis **FAIL**. It is not scorecard M2 and is not compared with
the scorecard's `eta` or `0.950` bars.

The strongest audit tie-back is the original 320×320 site `(968,584)`. M159 reads the
fork at `0.5025019%`, reproducing the archived `0.5025%` denominator. The current
DELIVER-V6 master reads `0.8245006%`, ratio **`1.640791×`**. The archived SHIP-V2
numerator was `0.1125%`, ratio `0.224`. Same comparator, site, and statistic; a
different Strehl version/configuration reverses the sign.

The historical grade correction cannot rescue the current result. Repeating the
existing coarse-cell transfer-slope method (`experiments/V-HEADTOHEAD/grade.py:
1-42`) and taking the largest positive measured elasticity as an intentionally
hostile correction raises the median ratio to `2.475710×`; all 12 remain above 1.
This sensitivity is reported, not made into a new acceptance bar.

### 5.2 Supplemental PMax diagnostic: 113MSDCF

PMax-to-Strehl registration is much tighter: 88/88 phase tiles, `0.86` px component
RMS and `2.48` px maximum residual. From 693 grid candidates, 523 survived PMax
clipping/level/bounds; 12 were frozen by the same comparator-only selection; one was
then excluded because the Strehl box clipped; **11 were scored**.

The ratios are:

`1.489753, 1.613540, 1.230970, 1.347825, 1.474152, 1.489344, 1.377766,
1.213455, 1.392478, 1.191439, 1.189916`.

Distribution: min `1.189916`, p25 `1.222212`, median **`1.377766×`**, p75
`1.481748`, max `1.613540`; bootstrap interval for the site median
`[1.213455,1.489344]`; **0/11 below 1**.

I do **not** elevate this to the primary noise score. Even PMax's flattest eligible
sites carry `5.4%–10.5%` high-pass RMS, so “flat/defocused ground” is not established;
the statistic is visibly structure-contaminated in this frost subject. It is a
same-sign commercial-comparator diagnostic, not a second clean noise population.

All exact per-site values, input hashes, geometry, exclusions, grade sensitivity, and
bootstrap draws are in `experiments/M159-noise-clause/results.json`; the executable
measurement is `measure.py`.

## 6. Commissioning evidence

M159 commissioned the exact fractional box9 RMS before reading the real outcome.
The fixture is a smooth latent flat field with independent Gaussian capture noise;
128 deterministic trials were used.

| control | construction | measured result |
| --- | --- | --- |
| movable null | two independent equal-noise captures; neither arm reuses the other's noise | median `0.999622×`, range `[0.993655,1.008012]`; 69 below and 59 above 1 |
| planted degradation | add independent noise at `1.5×` the capture sigma | median `1.801389×`, range `[1.789131,1.816619]`; **128/128 above 1** |
| planted improvement | average four independent captures of the same latent field | median `0.499915×`, range `[0.496874,0.503378]`; **128/128 below 1** |

The null can move and does move on both sides of one. The improvement is real
independent-capture averaging, not blur and not a value defined to be zero.

Two additional checks bound the implementation:

* current tone placement → sRGB → display S-curve → 16-bit quantisation → M159 inverse
  recovers high-pass RMS at `0.9999967×`, with maximum linear error `9.42e-6`;
* the known defeat is live: blurring a noisy field containing real six-pixel texture
  reads `0.571215×` and is therefore falsely “rewarded.” This instrument licenses
  only predeclared flat/defocused ground. It cannot license detail or overall quality.

The commissioning and measurement code is
`experiments/M159-noise-clause/measure.py`; `verify.py` independently checks the
primary-source quotations, pinned-build tone formula, file hashes, control directions,
arithmetic, and frozen headline values.

## 7. Defects for the orchestrator

No file below was edited.

### 7.1 Scorecard status contradicts its own admitted M8 result

`docs/proposals/2026-09-sota-scorecard.md:3-14` says no v1.7 score has been read and
the scoreboard is “0 measured / 12 unmeasured.” The same file says M8 is the only
produced-and-read score (`:518`) and records M8 as FAIL (`:1349`).

**Replace the opening status sentences with:**

> One v1.7 axis score has been produced and read: M8, which FAILS. Eleven axes
> remain UNMEASURED. The competitive position remains UNKNOWN and zero axes
> currently pass.

### 7.2 STATUS repeats the stale zero-score claim

`docs/STATUS.md:5352-5360` says “still no axis has a score,” contradicting its own
current header at `:25-28`.

**Replace the first paragraph under `2.9.49.7 Position` with:**

> **Current position: `0 of 12` passed; `1 of 12` measured.** M8 has a read,
> admitted FAIL. Four other instruments got more trustworthy, one axis was freed
> from the capture queue, and one owner ask became free. The remaining risk is
> not literally zero scoring; it is spending lanes on instrument refinement
> without converting the remaining eleven axes into admitted results.

### 7.3 The scorecard's comparator rule contradicts its own amendment

The amendment at `2026-09-sota-scorecard.md:97-106` makes the fork required and
Helicon optional. Decision rule 3 at `:121-125` still omits the fork and lists all
Helicon modes without the optional qualification.

**Replace decision rule 3 with:**

> 3. A comparative quality gate uses the **best qualifying comparator envelope**:
> Zerene PMax, Zerene DMap, and the focus-stack fork at its best-known build, each
> at its frozen setting with user post-processing disabled. Include Helicon
> Methods A, B, and C when obtainable; their absence is recorded and is not fatal.
> “Best” is chosen in the comparator-favouring direction for each metric.

### 7.4 The M1/M2/M4/M8 joint row still vetoes the owner's independent noise clause

The scorecard amendment correctly says the owner's sentence separately licenses M2
through the existing flat-ROI instrument (`:82-96`), but the joint row at `:196-200`
still says no noise-only claim is valid until M1 exists and M4/M8 pass.

**Replace that row's binding-rule cell with:**

> This joint constraint governs scorecard M2/M4 and any combined quality claim. It
> does not suspend the owner's separately licensed flat-ROI noise clause. Until M1
> is replaced, no matched-information M2 PASS or detail claim is valid; an
> owner-plan flat-ROI score may still be reported separately, with the exact output
> configuration and the anti-blur/detail caveat.

### 7.5 OWNER-ACTIONS leaves a false payoff table before its later correction

`docs/OWNER-ACTIONS.md:80-115` still tells the owner that changing rule 4 turns
`2 of 12` into `6 of 12` and `4 of 12` into `8 of 12`. The correction at `:900-980`
later says that claim was false. A later correction does not make the earlier advice
safe to skim.

**Replace the earlier table and “Twice the scoreboard” paragraph with:**

> **WITHDRAWN.** The `2→6` and `4→8` payoff table was false. M146 established that
> rule 4 is not the sole blocker on those axes, so narrowing it unlocks no scorecard
> axis today. See Ask 3's correction below. This does not bar the owner's separately
> licensed flat-ROI noise clause from being scored outside scorecard M2.

### 7.6 The plan's empirical row is stale across output versions

The plan's requirement remains coherent, but its current-state row at
`2026-08-sota-path.md:174` attaches SHIP-V2's `0.224×` result to an unversioned
“today.” DELIVER-V6 reverses that result. The orchestrator should not silently replace
the owner's text, but should ask the owner to version-scope it.

**Proposed owner-approved replacement for the row's `Today` cell:**

> **Historical SHIP-V2 PASS; current DELIVER-V6 FAIL.** SHIP-V2 at pyramid gate
> 4.5 measured `0.224×` the fork on one flat-paper site (`>=2.4×` lower under the
> archived worst-grade bound), but that Strehl artifact is no longer retained.
> DELIVER-V6 on the twelve frozen flat-paper sites measures median `1.515208×`
> the same fork, range `1.335062×–1.590879×`, with `0/12` lower.

## 8. What would make this wrong

The strongest objection is version selection. If “the stacker's output” means the
historical SHIP-V2 gate-4.5 binary rather than the surviving current shipping master,
then the archival score is a PASS at `0.224×`, not today's DELIVER-V6 FAIL. Recovering
the exact SHIP-V2 TIFF (and matching its recorded hash, if one exists) would make that
historical numerator independently auditable. A current pinned gate-4.5 linear render
would answer whether the old operating point still passes, but M159 did not launch
that compute job under the host's quiet order.

The scientific objection is equally important: box9 residual includes fine scene
structure. A registered temporal/cross-fit measurement on the same non-holdout
subject could show that DELIVER-V6's extra residual is recovered paper structure
rather than stochastic noise. That would overturn a physical-noise interpretation,
though not the score of the exact instrument the owner named. The visual residual
check shows structured content in the Strehl arm, and the blur challenge proves why
this number must never be presented as a detail-preserving quality verdict.

Finally, a frame-matched PMax or DMap render of `coffee-bean`, or a previously
unindexed quieter comparator output, could change which comparator is “best.” The
inventory found none. No claim here extends to the full six-clause SOTA sentence.
