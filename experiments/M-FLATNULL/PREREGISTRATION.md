# M-FLATNULL preregistration

Status: FROZEN BEFORE ANY NEW TARGET RENDER OR PER-EXPOSURE RESULT

This lane commissions M8-O on real development data with an a-priori physical
null, an exposure/noise ladder, and a downstream unsharp-mask positive control.
It is not a scorecard run and opens no holdout.

## 1. Prior-result disclosure

This is not a blind first look. The orchestrator explicitly permitted reading
`docs/research/M8-COMPARATIVE.md`; that report disclosed an aggregate flat-slide
M8-O rate of `1.326144%`. The mandatory rule-40 search then identified
`docs/research/M8-overshoot.md`, whose committed prior run disclosed the
per-exposure rates `3.888441%`, `0.059407%`, and `0.030585%` for 6 s, 2.5 s,
and 1 s. Its committed `results.json` was also read while checking the
instrument contract, so all prior target outcomes were known before the
predicates below were written.

Those values cannot confirm this campaign. This is a replication against a
newer pinned production source, with predicates below frozen before the new
renders. The primary exact-zero bar predates both runs in scorecard v1.7. The
prior values bias expectations toward finding a clean-stack null failure and
against finding the orchestrator's proposed noise-monotone failure; both
directions are declared rather than hidden.

The rule-40 searches were:

```text
python experiments\ORCH-drift-check\prior_art.py source hull overshoot flat noise unsharp mask
python experiments\ORCH-drift-check\prior_art.py source hull overshoot comparator sharpening
```

They identified `BUILD-HULL.md`, `M71-flat-fields.md`, `V-GATHER.md`,
`M89-robustness-mask.md`, `BUILD-PYRNOISE.md`,
`BUILD-PYRNOISE-ADJUDICATION.md`, `M69-focus-noise-sd.md`,
`M40-VERIFICATION.md`, `M8-overshoot.md`, `V-hull.md`, `C-landscape.md`,
`V-SPEED.md`, `V-ADJ13.md`, `V-REVIEW-halo.md`, and
`M60-prior-art-and-the-rival-explanations.md`. The load-bearing definitions are
scorecard v1.7's M8 card, `M8-overshoot.md`, and `M8-COMPARATIVE.md`.

## 2. Frozen inputs and source

Capture root, strictly read-only:

```text
D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl
```

| label | directory | exposure | full N |
|---|---|---:|---:|
| clean | `flat-et6s-sw4-cpl` | 6 s | 65 |
| middle | `flat-et2.5s-sw4-cpl` | 2.5 s | 61 |
| noisy | `flat-et1s-sw4-cpl` | 1 s | 60 |

The full-N arms answer the literal request. A required matched-N control uses
the first 60 filename-sorted ARWs from every directory. This removes the
known 65/61/60 hull-width difference. Prefix selection can omit different tail
focus positions; that can move the merge and is reported as a limitation.

The production source is commit
`c88733098ffb512468a830dceb700d831dbc5c7f`. It will be exported with
`git archive`, instrumented only in a lane-owned snapshot, and built with
`STREHL_BUILD_ID=c88733098ffb`.

The unchanged M8 implementation is pinned to commit
`76b3d9cc8b5185735d6c19d4339ce74d29e333e2`:

| file | SHA-256 |
|---|---|
| `experiments/M8-overshoot/checker.py` | `B66C9465D5F644D66646A14722475987F187E32B02ED3B687997C18CE1670B89` |
| `experiments/M8-overshoot/inject_trace.py` | `EB80E1EB5F44B0AAD0B17C165179E91976CAB8BF019604EC9269ACAC5E435913` |
| `experiments/M8-overshoot/m8_trace.rs` | `D6DB609AC725A89377EAF9B0272E8ED62E69AC12E840F6DD89416B7E044A2E0D` |

The checker remains producer-independent: the trace supplies source values,
gathered values, and placement coefficients, never a hull or verdict.

## 3. Frozen merge configuration

Every treatment uses:

```text
strehl align <absolute-stack> --out <lane-owned-map> --limit <N-or-omitted>
  --resampler catmull-rom

strehl stack <absolute-stack> --out <lane-owned-linear-u16-tiff>
  --limit <N-or-omitted> --merge pyramid --cover scale
  --resampler catmull-rom
```

Environment:

```text
STREHL_WARPMAP=<matching lane-owned map>
STREHL_DEFECT=off
STREHL_PYRAMID_WORKERS=1
STREHL_ALIGN=<unset>
STREHL_FIX_HALO=<unset>
STREHL_M8_TRACE_DIR=<lane-owned state>
STREHL_M8_CHECKER=<pinned checker snapshot>
STREHL_M8_CAPTURE=<arm label>
RAYON_NUM_THREADS=8
CARGO_BUILD_JOBS=8
```

The sidecar's recorded Catmull-Rom kernel wins; the explicit stack flag is
recorded too. `--cover scale` is frozen because crop has an active,
separately-owned boundary investigation. Any border anomaly is reported and
not repaired here. Nothing writes a sidecar or any other file under the
capture root.

## 4. Required commissioning before real output

The pinned checker must reproduce all existing known-answer controls:

* fractional Catmull-Rom hard step: RED, at least one M8-R violation;
* exact copy: GREEN, zero violations and zero copy error;
* convex bilinear gather: GREEN, zero violations;
* explicit `hi/lo +/- 32*tau`: exactly two violations, one per sign;
* checker independence audit: no Strehl import.

The lane's USM generator is separately commissioned on arrays that the M8
checker never reads:

* amount 0 produces an array exactly equal to its input;
* a constant field is unchanged at amount 1;
* a `0.25/0.75` vertical step at amount 1 changes both signs, at least 0.1%
  of samples, with maximum absolute displacement at least 16 u16 DN.

Any failed control stops the real run. Fixes require a committed preregistration
amendment before target outputs are opened.

## 5. Frozen measures

M8-O is the unchanged checker result: final linear u16 output against the
minimum/maximum exact Catmull support over every geometrically valid frame,
with `8*ULP_f32` plus exactly `0.5/65535` serialization tolerance.

For each arm report:

* denominator; lower, upper, and total violations; percent;
* maximum signed excess in linear units and u16 DN;
* low/high rail occupancy;
* full-frame and 256-pixel-inset values;
* violation counts in a fixed 8x8 grid over the inset;
* full invocation, environment, input/output/tool hashes, cover scale, and
  coordinate-validity mismatches.

The 256-pixel inset is frozen before results and deliberately favours the
instrument by excluding far more than Catmull's nominal support. Full-frame
results remain primary for the scorecard exact-zero invariant; inset results
distinguish boundary concentration from an interior null failure.

## 6. Predicates

### P1: flat clean-stack null

The pre-existing scorecard bar is exact: M8-O must be `0.0000%`.

For this commissioning, the 6-second full-N result is **materially nonzero**
only if its 256-pixel-inset result satisfies either:

1. violation rate at least `0.0100%`; or
2. at least 64 distinct violating pixels and maximum excess beyond the
   checker's tolerance at least 16 u16 DN.

If only the full frame is material and the inset is not, classify the result
`BOUNDARY-CONCENTRATED`, not a general flat-null failure. Report how many of
the 64 inset blocks contain a violation. These materiality thresholds are
lenient relative to the exact scorecard bar and therefore bias toward retaining
the instrument.

### P2: exposure/noise ladder

The noise-sensitivity hypothesis is

```text
p_6s < p_2.5s < p_1s
```

for 256-pixel-inset M8-O rates. It **falsifies M8-O as a comparative invention
axis on these data** only if:

1. the matched-N=60 rates are strictly monotone in that direction;
2. `p_1s - p_6s >= 0.0100` percentage points;
3. `p_1s / p_6s >= 1.25` (infinite if `p_6s=0`); and
4. at least 40 of 64 paired inset blocks have `p_1s > p_6s`.

The full-N rates must not reverse the ordering. If only full-N passes, the
65/61/60 frame-count confound makes the result `INCONCLUSIVE`. If neither
passes, the registered noise false-positive mechanism is **not observed**;
that does not prove noise invariance beyond these three development stacks.

More frames can widen the all-frame hull for a fixed output, which biases the
full-N ladder toward the proposed rise as exposure and N fall. The merge output
also changes with N, so its net bias is not assumed; matched N is required.

### P3: downstream USM sensitivity

Apply one frozen plant to the full-N 6-second linear output:

```text
blur = scipy.ndimage.gaussian_filter(
    image_linear, sigma=(1.0, 1.0, 0.0), mode="reflect", truncate=4.0
)
planted = clip(image_linear + 1.0 * (image_linear - blur), 0, 1)
encoded = floor(planted * 65535 + 0.5).astype(uint16)
```

SciPy is pinned by the run manifest. The plant is post-merge and
post-serialization; it is not evidence about pre-clamp excursions.

Plant potency requires, within the 256-pixel inset:

* at least 0.1% of samples change by at least 1 DN;
* at least 1,000 positive and 1,000 negative changes;
* maximum absolute change at least 16 DN;
* newly clipped low/high samples each at most 1% of inset samples.

The M8-O sensitivity control passes only if:

1. planted inset rate exceeds baseline by at least `0.0100` percentage points;
2. planted/baseline inset-rate ratio is at least `1.25` (infinite at zero);
3. at least 40 of 64 inset blocks increase; and
4. planted maximum excess is no smaller than baseline.

An exact-copy amount-0 TIFF must reproduce the baseline M8-O counts and
violation-manifest hash. Any potency or response failure means the instrument
is uncommissioned for this use; no predicate is weakened.

## 7. Load, validity, and stopping

Scientific counts are deterministic and are not rejected for a busy host.
Any reported timing is valid only with five-second pre-load at most 15% and
during-run external busy at most 10% after subtracting whole-process-tree CPU
from system busy. Loaded timings are retained but labelled invalid; this lane
makes no throughput claim.

Every arm must have the expected frame/site count, zero coordinate-validity
mismatches, no unconsumed trace blocks, a nonzero linear u16 TIFF, complete
bracketing, and unchanged `Get-ChildItem -Force` input manifests before/after.
Any failure stops interpretation. Capture inputs remain strictly read-only.

No modification to Strehl, M8, or a predicate is allowed after a target output
is observed. The only writable paths are `experiments/M-FLATNULL/` and
`docs/research/M-FLATNULL.md`.

## 8. Verdict vocabulary

* `NULL-MATERIAL`: P1 materiality passes in the inset.
* `BOUNDARY-CONCENTRATED`: P1 is material only outside the inset.
* `NOISE-SENSITIVE`: every P2 condition passes.
* `NOISE-TREND-NOT-OBSERVED`: P2 does not pass in either ladder.
* `NOISE-INCONCLUSIVE`: full-N and matched-N disagree or only full-N passes.
* `SENSITIVITY-PASS`: every P3 potency and response condition passes.
* `UNCOMMISSIONED`: any required commissioning, potency, or response condition
  fails.

These labels commission scope; none is a scored M8 result.
