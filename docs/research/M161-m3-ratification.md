# M161 — M3 bar ratification, recommissioning freeze, and measurement preflight

**Ruling:** `[bar] = 5%` of the independently selected local source step.
The literal publication gate is `max_e max(h_e,v_e) <= 0.05` over the frozen
scored sites. The v2 checker and its null/degradation/improvement controls are
pre-registered, but formal commissioning and scoring are **BLOCKED** while M153
owns the host. Independently, the required common-input manifest, strehl
package, fork package, Zerene PMax package, Zerene DMap package, and external
warp/profile evidence do not exist in the supplied M161 contract. No holdout,
candidate, or comparator pixel was opened.

| Item | Ruling | Evidence |
|---|---|---|
| Numerical placeholder | **RATIFIED: 5%** | Largest round threshold below the confirmed merge-rim lower 95% bound of 5.33%, while the matched no-merge upper bound is 0.33%. |
| Literal owner clause | **TIGHTENED** | The owner says “no ... above”; p99 plus a 1% affected allowance can admit five of 500 observed violations. V2 adds an observed maximum gate. |
| Side-max checker | **FROZEN, NOT YET ADMITTED** | V2 makes `v_e=max(v_neg,v_pos)`, separates broad from narrow normalization, and pre-registers movable-null, degradation, and improvement arms. |
| External-warp control | **FROZEN, NOT YET ADMITTED** | Input-only split-landmark null, planted similarity, and held-out corrected improvement are specified. |
| M3 product verdict | **BLOCKED** | Host release and every required common-input product/profile package are absent. This is neither PASS nor FAIL. |

## 1. What the owner actually fixed, and what was left blank

The authoritative plan's unique single-line anchor is:

> `per file), no occlusion veil above [bar] (halo instrument at full reach), while`

The plan fixes four things:

1. the construct is **stack-induced occlusion veil / halo**, not absolute optical
   flare;
2. the statistic must run at **full reach**, not stop before the broad shoulder;
3. the claim is an upper-bound claim (“no ... above”); and
4. the output is the final, un-post-processed product under the plan's common
   input and geometry contract.

It does **not** determine a number. The scorecard's 1% median and 5% p99 are
therefore additions, not quotations from the owner.

## 2. Why the defensible value is 5%

The cleanest measured separation uses the same dimensionless scale M3 needs:
rim amplitude divided by the local edge step.

- In `docs/research/M121-halo-polarity.md`, the unique table row beginning
  `| N1 pooled, dark-object class |` measures the no-merge floor at `0.0023`
  with 95% interval `[0.0012,0.0033]`.
- The unique row beginning
  `| shipped, gate 4 | **dark obj / bright surround** |` measures the
  merge-created rim at `0.0634` with 95% interval `[0.0533,0.0754]`.
- The same report states, at anchor
  `**The merged rim is 28× the no-merge floor.** N1 passes.`, that this is a
  merge effect rather than the photographed edge.

Any threshold between 0.33% and 5.33% separates the upper 95% null bound from
the lower 95% bound of that confirmed defect. **Five percent is the largest
round percentage inside that interval.** It is deliberately permissive: it
rejects the known 6.34% defect while making the least claim the evidence can
support. It remains 15.2 times the measured null upper bound.

The broad-veiling evidence is not close to the decision boundary. At the unique
anchor `2. **Dark aura** — peak`, `docs/research/ORCH-veiling.md` reports a
22.8% broad defect reaching roughly 300 px. A 5% bar rejects it by a wide
margin.

No current M3 candidate or comparator output was inspected in selecting 5%.
The value may therefore produce a strehl failure; that would be evidence, not a
reason to move it.

### What 1% means

The scorecard's median `h_e,v_e <=0.01` remains a useful **typical-boundary**
requirement. It is not the value of the owner's placeholder. The placeholder is
the per-site severity limit, 5%.

### Why v2 adds a maximum

The scorecard's unique success anchor begins
`**Success.** **SCORECARD ADDITION:** median `h_e` and `v_e <=0.01`; p99 of each`.
With 500 sites, its p99 and affected-rate tuple can permit up to five measured
sites above 5%. That cannot license the literal word **no**.

V2 therefore requires:

```text
maximum over frozen scored sites of max(h_e, v_e) <= 0.05
```

The p99, rate, Wilson, comparator, width, and coherence summaries remain
reported. The new maximum only tightens the scorecard; it cannot turn any
previous failure into a pass.

## 3. Two repairs, not one

### 3.1 The side maximum

M152's failure is anchored by
`The non-normative side-max diagnostic,` in
`docs/research/M152-site-census.md`. Its one-sided 6% far-veil plant read about
`0.0545` under `max(v_neg,v_pos)` and was detected at every planted site, while
the pooled two-side mean read `0.027243` and detected none.

V2 makes the diagnostic normative:

```text
v_e = max(
    mean_{-200 <= s <= -16} |O(s)-R_far(s)| / broad_step,
    mean_{  16 <= s <= 200} |O(s)-R_far(s)| / broad_step
)
```

For non-negative side values `a,b`,
`max(a,b) >= (a+b)/2` pointwise. This repair cannot lower any recorded defect.

### 3.2 Broad and narrow normalization must be separate

The scorecard's unique anchor
`For the narrow halo arm, use median source plateaus at` requires narrow
plateaus `[-64,-48]`, `[48,64]` and broad plateaus `[-400,-320]`, `[320,400]`.
M152 v1 instead has one normalization step, and its code's unique line
`residual = np.abs(output - far) / step` applies that narrow step to `v_e`.

The synthetic M152 edge happened to have the same asymptotic step at both
reaches, so this did not cause its commissioning failure. It would matter on a
real profile with broad illumination or veiling drift. V2 uses the narrow step
for `h_e` and edge width, and the broad step for `v_e`.

M152's definition and red result remain unchanged as historical evidence.

## 4. Recommissioning frozen before outputs

`experiments/M161-m3-ratification/preregistration.json` is the decision record.
Every statistic has a null that can move, a planted degradation, and a planted
improvement.

| Channel | Movable null | Degradation | Improvement | Admission rule |
|---|---|---|---|---|
| Side-max `v_e` | Independent source/output noise at `sigma=0.002` of step; median must be nonzero and all gates pass. A `sigma=0.012` sensitivity arm must move and fail. | 6% two-sided veil and 6% one-sided far veil; each detected on at least 95% of sites. | The same seeded 6% rim+veil population reduced to 0.5%; median `v_e` must fall by at least 5 points and the arm must pass. | Any miss is `NOT_ADMITTED_COMMISSIONING_FAILED`; thresholds do not move after candidate pixels are seen. |
| Hull excess `h_e` | Same independent-noise population. | Positive and opposite-sign 6% rims; each detected on at least 95%. | Paired 6% to 0.5% rim reduction; median `h_e` must fall by at least 5 points and pass. | Both signs are mandatory. |
| Width guard | Clean noisy edge. | Gaussian blur must leave `[0.95,1.05]`. | Paired clean edge must return to the interval. | Width, not normalized coherence, carries the common-blur veto. |
| `rho_edge` diagnostic | Clean noisy patch. | A translated patch must fall below 0.90. | Paired restored patch must pass. | This proves phase sensitivity only; it is not a transfer-magnitude licence. |
| Literal maximum | 500-site clean population. | Exactly one of 500 sites receives a 6% one-sided veil. | Removal returns the paired clean population. | V2 must fail while the prior tuple without the maximum passes, proving the new gate is not redundant. |
| External warp | Identity landmarks plus independent 0.008-px coordinate noise; residual must be nonzero and pass. | Plant scale 1.0025, rotation 0.05 degrees and translation `(0.45,-0.30)`; at least one geometry limit must fail. | Fit on even landmarks, invert, and score odd landmarks; all limits must pass. | Fit and holdout are disjoint and input-only. |

The profile arm also bounds independent residual source shifts at `+/-0.08`
native px. Its clean population must pass, and the same shifts must not hide the
one-sided 6% veil.

The existing M152 outputs are useful prior evidence but are **not** v2
admission. At anchor `The improvement arm moves median`, M152 records
`h_e: 0.119885 -> 0.009885` and `v_e: 0.060000 -> 0.005000`; its blur arm moved
the width ratio to `1.771028`. Those results establish that the basic channels
can move in both directions. V2 must still run because side-max, broad
normalization, the exact maximum, noise null, and warp controls are new.

## 5. Why no control result was manufactured under the host lock

The orchestrator's unique status anchor says
`M139 is stood down and asked to deliver from data it already holds; M153 has the`.
The following line queues M3 behind that timing campaign. The user's instruction
forbids image processing capable of contaminating it.

I therefore ran only:

- Python bytecode compilation of the six new scripts: **PASS**;
- pre-output hash verification of the checker bundle and M152 census:
  **PASS**; and
- the metadata-only preflight: **BLOCKED**, with `pixel_files_opened: 0`.

I did **not** run the 500-site FFT/image commissioning, decode a RAW, render a
stack, build a profile package, or score a product.

## 6. Measurement verdict

`experiments/M161-m3-ratification/out/measurement-preflight.json` records:

1. `HOST_RESERVED` — no explicit M153 release record;
2. `COMMON_INPUT_MANIFEST_ABSENT`;
3. required strehl profile package absent;
4. required fork profile package absent;
5. required Zerene PMax profile package absent; and
6. required Zerene DMap profile package absent.

The scorecard itself requires the same hashed, uncompressed, native-size,
16-bit linear ProPhoto RGB D50 TIFFs for every arm. M152 independently recorded
at anchor `M3 also cannot yet produce a registered product score:` that no
common-input candidate/comparator outputs or external source-profile warps had
been supplied. Nothing in the repository now closes that requirement.

**M3 = BLOCKED.** There is no admissible PASS or FAIL score to report.

After host release, the run order is fixed:

1. run `test_m3_checker_v2.py`;
2. run `commission_m3_v2.py`; stop unless every assertion passes;
3. build the common-input profile packages without inspecting holdout scores;
4. rerun `preflight.py`; and
5. run `score_m3_packages.py` once on strehl and every required comparator.

## 7. Two corrections the orchestrator should carry forward

These files are orchestrator-owned, so this lane does not edit them.

1. The `docs/STATUS.md` anchor
   `The consequence is the operative fact of the current plan: **the shared-optic inversion`
   overstates the shared-capture result. One coordinated shooting session can
   acquire the physical truth roles for M1, M2, and M9, but one inversion stack
   does not itself supply M2's eligible two-light fixed-focus ISO-100 repeats or
   M9's independent depth-stack repeat truth. The shared
   truth-reference/transfer-veto architecture is valid; the claim that one
   capture alone unblocks all three is not.
2. The anchor `M161 replaced every reported uncertainty in the M10 pipeline with zero`
   describes an experiment M161 did not run. M161 proved a functional
   invariance: the registered verdict has no `sigma_z` input, so arbitrary
   replacement cannot change it. The conclusion stands; the reported method
   should be corrected.

## 8. Artifacts

- `experiments/M161-m3-ratification/m3-checker-definition-v2.json`
- `experiments/M161-m3-ratification/preregistration.json`
- `experiments/M161-m3-ratification/freeze-manifest.json`
- `experiments/M161-m3-ratification/m3_checker_v2.py`
- `experiments/M161-m3-ratification/commission_m3_v2.py`
- `experiments/M161-m3-ratification/test_m3_checker_v2.py`
- `experiments/M161-m3-ratification/measurement-contract.json`
- `experiments/M161-m3-ratification/profile-package.example.json`
- `experiments/M161-m3-ratification/preflight.py`
- `experiments/M161-m3-ratification/score_m3_packages.py`
- `experiments/M161-m3-ratification/verify_freeze.py`
- `experiments/M161-m3-ratification/out/measurement-preflight.json`
