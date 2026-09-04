# M169 — M3 occlusion-veil execution

**Feasibility verdict: YES — the existing captures satisfy the frozen
500-site / 50-per-capture / 400-native-pixel-reach requirement. No new M3
photon capture is needed.**

**Measurement verdict: `NOT_ADMITTED_COMMISSIONING_FAILED`. NO SCORE. NO CI.**

**Axis-contract verdict: CONJUNCTIVE ABSOLUTE AND COMPARATIVE.** The `0.05`
maximum is an absolute candidate gate, but it is not by itself an M3 axis
score. The scorecard also requires Strehl's paired `p99(a_e)` to be no worse
than the required M1-qualified comparator envelope in every scope.

The score was not run because the frozen M161 commissioning battery failed its
own registered improvement assertion before any candidate or comparator pixel
was opened. Required common-input and product packages are also absent, and
the scorecard's M1-qualified comparator envelope does not exist.

## 1. Feasibility before measurement

**VERIFIED BY RUNNING.** `capture_feasibility.py` performed only path, directory
entry, manifest and SHA-256 checks. It did not open an ARW. The frozen M152
census manifest still hashes to
`35d5058afc1f310923ba2a3e5bf0cd3b91b3eb2df0e8d4868c22099de7bcd38d`,
the value pinned by M161
(`experiments/M169-m3-veil/out/capture-feasibility.json`).

| Frozen capture | ARWs in census | ARWs on disk | Eligible ±400 px sites | Selected sites | Result |
|---|---:|---:|---:|---:|---|
| `m3-duck-tape` | 197 | 197 | 221 | 133 | PASS |
| `m3-chia` | 130 | 130 | 399 | 133 | PASS |
| `m3-flower-fern` | 299 | 299 | 511 | 132 | PASS |
| `m3-razor-control` | 67 | 67 | 102 | 102 | PASS |
| **Total** | **693** | **693** | **1,233** | **500** | **PASS** |

The paths are the four frozen M152 paths under `D:\personal\macro`, including
the horizontal razor control under `requests\19-razor-edge`. A second
`Get-ChildItem -Force` count independently returned `197`, `130`, `299`, and
`67`. Every selected source filename still exists and every selected site
records `reach_native_px = 400`.

**INFERRED BY READING.** M152 had already decoded the protected inputs under a
pre-output freeze and concluded that M3 had 1,233 broad-eligible edges and
needed no new photons (`docs/research/M152-site-census.md`, “Headline,”
“M3 edge rule,” and “Census results”). M169 did not repeat that bulk decode.
M152 also states the limitation: its input-only selector proves isolated
high-CNR step geometry, not that every natural edge is independently known to
separate two physical depth planes. The scorecard nevertheless freezes this
exact population
(`docs/proposals/2026-09-sota-scorecard.md`, unique anchor `The frozen
population is exactly 500 sites`).

## 2. Frozen instrument and bar

**VERIFIED BY RUNNING.** The copied checker and definition are byte-identical
to M161 commit `47d67a9f`:

- `m3_checker_v2.py`:
  `05d291c8c24712d46666e9ed398f39cb982fa3b4c918a7e0cfcdee200dec2eda`;
- `m3-checker-definition-v2.json`:
  `578022e6eeefecce60a00191024e9ffd4dc3c621410b398709b3f92b987b67ca`.

The six frozen checker unit tests pass. The numerical bar was not changed:

```text
maximum over frozen scored sites of max(h_e, v_e) <= 0.05
```

The remaining median, p99, affected-rate, Wilson, width, coherence and
comparator gates also remain exactly as registered
(`docs/research/M161-m3-ratification.md:56-87`;
`docs/proposals/2026-09-sota-scorecard.md`, unique anchors `The candidate must
satisfy every bar` and `For the comparator clause`).

M169 changed only the copied full-commission runner's obsolete scheduling
gate. The checker, definition, random seed, plants, assertions and numerical
code are unchanged. A source diff against M161 confirms that the other changes
are the local filename used for self-hashing and a non-timing host-policy
annotation.

### 2.1 The `0.05` bar is not the whole M3 axis contract

**INFERRED BY READING.** The scorecard makes the absolute and comparative
limbs conjunctive. It first says:

> The candidate must satisfy every bar both on each of the four capture
> populations and on the pooled 500 sites

and then requires:

> Strehl's value must be `<=` that reference in every scope. If any required
> comparator product is absent, or no mode has admitted M1 qualification, M3
> is `UNMEASURED_COMPARATOR_QUALIFICATION`.

The reference is the lowest paired `p99(a_e)` among available modes with
admitted M1 qualification; required products are the fresh fork and licensed
Zerene PMax and DMap. M161's frozen preregistration independently describes
the score as `absolute M3 gates plus strehl paired p99 no worse than the best
required comparator`
(`experiments/M161-m3-ratification/preregistration.json`, `measurement.score`).

An absolute candidate-only result is separately reportable as a **diagnostic**:
M161 states that the p99, rate, Wilson, comparator, width and coherence
summaries remain reported. It cannot be labelled an M3 axis PASS without the
comparator limb.

Once commissioning is adjudicated, an absolute candidate diagnostic still
requires:

- the hashed common-input manifest in the registered native-size,
  uncompressed 16-bit linear ProPhoto RGB D50 form;
- the final, un-post-processed Strehl output and its complete 500-site profile
  package; and
- one input-only common-to-output transform per capture, with held-out
  residuals passing the frozen geometry limits.

A full M3 axis verdict additionally requires:

- fresh-fork, licensed Zerene PMax and licensed Zerene DMap profile packages
  on the identical common input, plus each obtainable Helicon A/B/C mode; and
- admitted M1 qualification on the same comparator output bytes so that the
  required paired envelope exists.

The M161 `score_m3_packages.py` bundle checks required package presence and
the paired p99 comparison, but it contains no M1-qualification field or check.
Therefore M161 alone does not demonstrate an execution path that enforces the
current scorecard's M1-qualified-envelope clause. M169 did not alter another
lane's scorer.

## 3. Recommissioning

### 3.1 Line-anchored required controls

**VERIFIED BY RUNNING.** `anchored_controls.py` derives each planted
configuration from
`experiments/M169-m3-veil/fixtures/control-template.json`. Every change
replaces an exact full line only after proving that line occurs exactly once.
An explicit missing-anchor probe hard-errors; it printed
`MISSING_ANCHOR HARD_ERROR`.

“Flat null” is interpreted strictly for this edge-normalized instrument as an
eligible source edge whose output-minus-reference residual is identically flat
zero: there is nothing in either veil side for the statistic to find. A
literal constant/no-edge input has no positive normalization step, cannot
belong to the frozen M3 population, and was separately verified to fail closed
as `INVALID_OUTPUT_CHARGED: nonpositive_source_step`.

Exact output:

```text
FLAT_NULL GREEN h50=0.000000 v50=0.000000 max=0.000000 affected=0/500
DEFECT RED h50=0.000000 v50=0.054486 max=0.054486 affected=500/500
IMPROVEMENT GREEN h50=0.000000 v50=0.004541 max=0.004541 affected=0/500
LITERAL_FLAT DOMAIN_REFUSAL status=INVALID_OUTPUT_CHARGED reason=nonpositive_source_step
MISSING_ANCHOR HARD_ERROR
ANCHORED_CONTROLS PASS
```

The RED arm is a one-sided 6% veil over offsets `+33..+232`; the score samples
the overlapping `+16..+200` side, so the exact noiseless expectation is
`168/185 * 0.06 = 0.0544864864864865`. Reducing the same plant to 0.5% gives
`0.00454054054054054`, below the unchanged 0.05 bar. The narrow control
therefore moves in both directions and does not reward that improvement as a
veil defect
(`experiments/M169-m3-veil/out/anchored-controls.json`).

### 3.2 Full frozen M161 battery

**VERIFIED BY RUNNING.** The complete M161 battery produced the following
planted-degradation outputs:

```text
noise_sensitivity_degradation: h50=0.017706 v50=0.013934 v99=0.015554 max=0.041471 affected=0.000% verdict=FAIL
planted_6pct_rim: h50=0.061584 v50=0.005134 v99=0.005394 max=0.065829 affected=100.000% verdict=FAIL
planted_6pct_opposite_sign_rim: h50=0.061637 v50=0.005139 v99=0.005428 max=0.066017 affected=100.000% verdict=FAIL
planted_6pct_two_sided_veil: h50=0.061765 v50=0.060122 v99=0.060511 max=0.066947 affected=100.000% verdict=FAIL
planted_6pct_one_sided_far_veil: h50=0.002943 v50=0.054700 v99=0.055140 max=0.055313 affected=100.000% verdict=FAIL
planted_6pct_rim_and_veil: h50=0.120339 v50=0.062933 v99=0.063404 max=0.124805 affected=100.000% verdict=FAIL
planted_blur_degradation: h50=0.133095 v50=0.001735 v99=0.001889 max=0.167289 affected=100.000% verdict=FAIL
planted_rho_phase_degradation: h50=0.002943 v50=0.002320 v99=0.002592 max=0.006863 affected=0.000% verdict=FAIL
allowed_warp_one_sided_6pct_veil: h50=0.002894 v50=0.054700 v99=0.055140 max=0.055313 affected=100.000% verdict=FAIL
single_site_6pct_one_sided_veil: h50=0.002943 v50=0.002320 v99=0.002595 max=0.054862 affected=0.200% verdict=FAIL
```

The noisy clean null passed:

```text
clean_noise_null: h50=0.002943 v50=0.002320 v99=0.002592 max=0.006863 affected=0.000% verdict=PASS
```

The registered combined improvement moved strongly in the correct direction,
from `h50=0.1203389656, v50=0.0629325008` to
`h50=0.0104133574, v50=0.0053386838`, and no site exceeded the 5% headline
bar. It nevertheless failed the unchanged median `h_e <= 0.01` gate:

```text
planted_improvement_0_5pct_rim_and_veil: h50=0.010413 v50=0.005339 v99=0.005761 max=0.014730 affected=0.000% verdict=FAIL
NOT ADMITTED: failed assertions=improved_arm_passes
```

This exact failure was independently reproduced by importing and running the
untouched M161 source, rather than M169's copy. It is not a host-load or copy
effect. The fixed-seed battery is deterministic and contains no wall-clock
measurement
(`experiments/M169-m3-veil/out/m161-source-reproduction.json`).

**Result:** `NOT_ADMITTED_COMMISSIONING_FAILED`. The bar and plant were not
changed to make the arm pass. M161's paper preregistration was sound enough to
expose this failure, but its statement that the checker was ready to run did
not constitute successful commissioning because the battery had never run.

### 3.3 Improvement-arm failure: explanation B

**VERIFIED BY RUNNING.** The frozen clean-noise null's actual value is
`median_h_e = 0.0029430516302103543`, leaving
`0.007056948369789646` below the unchanged `0.01` gate. The gate is therefore
reachable; the clean null is not sitting near `0.0104`.

The registered 0.5% combined rim-and-veil arm reads
`median_h_e = 0.010413357351919823`. On the paired fixed-seed population,
`h_e` increased at **500/500** sites relative to the clean null; the median
paired increase was `0.007544986400730763`. This is evidence for explanation
**(B)**: the instrument separates the clean null from the still-nonzero
0.5%-of-step plant, while the commissioning assertion requires that planted
arm to pass. It is not evidence for a clean measurement floor near `0.0104`.

`characterize_improvement_curve.py` imported the untouched, hash-verified
M161 checker and commissioning source and varied only a separate
characterisation argument. The registered 0.5% arm, its assertion and every
gate remain unchanged:

| Combined rim + veil magnitude | `median_h_e` | `median_v_e` | Median-`h_e` gate |
|---:|---:|---:|---|
| 0.00% | 0.002943052 | 0.002320178 | PASS |
| 0.10% | 0.003411812 | 0.002475393 | PASS |
| 0.20% | 0.004775802 | 0.002910812 | PASS |
| 0.30% | 0.006526127 | 0.003577053 | PASS |
| 0.40% | 0.008449086 | 0.004400187 | PASS |
| 0.45% | 0.009443927 | 0.004863109 | PASS |
| **0.50% (registered)** | **0.010413357** | **0.005338684** | **FAIL** |
| 0.60% | 0.012398952 | 0.006332077 | FAIL |
| 1.00% | 0.020386842 | 0.010494231 | FAIL |
| 2.00% | 0.040379006 | 0.020980872 | FAIL |
| 4.00% | 0.080351369 | 0.041953202 | FAIL |
| 6.00% | 0.120338966 | 0.062932501 | FAIL |

A fixed 16-step bisection brackets the median-`h_e` crossing:

```text
0.477798461914% plant -> median_h_e=0.009999873321180 PASS
0.477806091309% plant -> median_h_e=0.010000025902681 FAIL
```

This is deterministic synthetic transfer characterisation, not a product
measurement or an inferential population estimate; no confidence interval is
claimed. It establishes the internal incompatibility of the registered 0.5%
pass assertion with the frozen plant, checker, noise population and gate. It
does not pre-empt M174's independent ruling on which requirement, if any,
should be revised.

## 4. Score

**VERIFIED BY RUNNING.** Scoring stopped before any candidate or comparator
pixel was opened:

```text
NOT_ADMITTED_COMMISSIONING_FAILED
denominator=500
subjects=m3-chia:133,m3-duck-tape:133,m3-flower-fern:132,m3-razor-control:102
score=NO SCORE
confidence_interval=NO CI
```

The failed commissioning assertion is sufficient to prohibit a score.
Independently, files needed even for the absolute candidate diagnostic are
absent:

- common-input manifest;
- Strehl profile package; and
- profile-package-builder/input-only warp evidence.

The full comparative axis additionally lacks:

- fresh-fork profile package;
- Zerene PMax profile package; and
- Zerene DMap profile package.

**INFERRED BY READING.** The scorecard also makes the comparator limb
unavailable until an M1-qualified comparator envelope and input-only
profile-warp evidence exist
(`docs/proposals/2026-09-sota-scorecard.md`, unique M3 `Definition status` and
`For the comparator clause` anchors). Therefore even a repaired commissioning
run would still be
`UNMEASURED_COMPARATOR_QUALIFICATION` today. Producing the missing product
packages would require a separate common-input rendering/profile-extraction
run over 693 RAWs plus licensed comparator outputs. M169 did not begin that
heavy work without owner approval.

No new capture is requested. The next technical decision is whether to revise
and re-register the combined improvement control or the median-`h_e` gate;
M169 makes neither change.

## 5. Reproduction and artifacts

Run from the repository root:

```powershell
python experiments\M169-m3-veil\capture_feasibility.py
python experiments\M169-m3-veil\test_m3_checker_v2.py
python experiments\M169-m3-veil\full_commission.py
python experiments\M169-m3-veil\anchored_controls.py
python experiments\M169-m3-veil\reproduce_m161_failure.py
python experiments\M169-m3-veil\characterize_improvement_curve.py
python experiments\M169-m3-veil\measurement_preflight.py
python experiments\M169-m3-veil\verify_artifacts.py
```

Expected exits for this committed state are `0`, `0`, `3`, `0`, `0`, `0`, `5`,
`0`. The nonzero exits are deliberate fail-closed verdicts, not command
failures. No absolute timing is recorded.

Primary artifacts:

- `out/capture-feasibility.json` — capture sufficiency;
- `out/commission-v2.json` and `.sha256` — full frozen commissioning;
- `out/anchored-controls.json` and `out/control-configs/` — required
  line-anchored controls;
- `out/improvement-response-curve.json` — fixed-seed combined rim-and-veil
  transfer characterisation and median-`h_e` crossing bracket;
- `out/measurement-verdict.json` — final refusal, denominator, subjects and
  explicit `NO CI`.

The mechanical prior-art search named `M87-occlusion`, `M36-VERIFICATION`,
`ORCH-veiling`, `M63-bimodality`, `M161-m3-ratification`,
`M35-fit-generality-measured`, `M25-simulator-measured`, `M31-VERIFICATION`,
`M152-site-census`, `M79-edof-microscopy-survey`, `M133-blocker-audit`,
`BUILD-HALO`, `M146-unlock-audit`, `M39-verify-detail-metric`, `V-veiling`,
and `M151-m5-checker`. This run changes none of their conclusions or files.
