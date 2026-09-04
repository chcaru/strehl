# M169 — M3 occlusion-veil execution

**Feasibility verdict: YES — the existing captures satisfy the frozen
500-site / 50-per-capture / 400-native-pixel-reach requirement. No new M3
photon capture is needed.**

**Measurement verdict: `NOT_ADMITTED_COMMISSIONING_FAILED`. NO SCORE. NO CI.**

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
(`docs/proposals/2026-09-sota-scorecard.md:994-996`).

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
`docs/proposals/2026-09-sota-scorecard.md:1057-1078`).

M169 changed only the copied full-commission runner's obsolete scheduling
gate. The checker, definition, random seed, plants, assertions and numerical
code are unchanged. A source diff against M161 confirms that the other changes
are the local filename used for self-hashing and a non-timing host-policy
annotation.

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
Independently, the required files are absent:

- common-input manifest;
- Strehl profile package;
- fresh-fork profile package;
- Zerene PMax profile package; and
- Zerene DMap profile package.

**INFERRED BY READING.** The scorecard also makes the comparator limb
unavailable until an M1-qualified comparator envelope and input-only
profile-warp evidence exist
(`docs/proposals/2026-09-sota-scorecard.md:970-974,1070-1078`). Therefore even
a repaired commissioning run would still be
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
python experiments\M169-m3-veil\measurement_preflight.py
python experiments\M169-m3-veil\verify_artifacts.py
```

Expected exits for this committed state are `0`, `0`, `3`, `0`, `0`, `5`, `0`.
The nonzero exits are deliberate fail-closed verdicts, not command failures.
No absolute timing is recorded.

Primary artifacts:

- `out/capture-feasibility.json` — capture sufficiency;
- `out/commission-v2.json` and `.sha256` — full frozen commissioning;
- `out/anchored-controls.json` and `out/control-configs/` — required
  line-anchored controls;
- `out/measurement-verdict.json` — final refusal, denominator, subjects and
  explicit `NO CI`.

The mechanical prior-art search named `M87-occlusion`, `M36-VERIFICATION`,
`ORCH-veiling`, `M63-bimodality`, `M161-m3-ratification`,
`M35-fit-generality-measured`, `M25-simulator-measured`, `M31-VERIFICATION`,
`M152-site-census`, `M79-edof-microscopy-survey`, `M133-blocker-audit`,
`BUILD-HALO`, `M146-unlock-audit`, `M39-verify-detail-metric`, `V-veiling`,
and `M151-m5-checker`. This run changes none of their conclusions or files.
