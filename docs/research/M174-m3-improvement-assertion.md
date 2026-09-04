# M174 — M3 improvement-assertion adjudication

**Verdict: (B) ASSERTION DEFECT.**

**INFERRED (RULING).** For this disputed control, the numerical instrument is admissible; the failed
assertion is not evidence of an instrument floor.

**VERIFIED BY RUNNING.** The frozen checker does not have the proposed `0.0104` floor. Its clean-noise
null has `median_h_e = 0.0029430516302103543`, passes every gate, and sits
`3.397833697x` below the unchanged `0.01` median gate. The registered 0.5%
arm is not 0.5% at the place `h_e` reads: its 0.5% rim and 0.5% veil overlap
additively at nine samples inside the halo support, creating a 1.0% noiseless
excursion before the registered noise is applied.

**INFERRED FROM THE FROZEN DESIGN.** The correct pre-run registration was therefore **not** “improved arm passes.”
For this frozen stochastic fixture it was
`improved_arm_fails_median_h_e`, while retaining the two existing assertions
that median `h_e` and `v_e` each improve by at least five percentage points.

**INFERRED (SCOPE OF RULING).** This ruling changes no numerical gate, plant, seed, checker, or population. It
does not retroactively turn M161's failed run green and does not authorize an
M3 score. A later lane may make an explicit assertion-only version change and
rerun commissioning; M174 does not make that repair.

## 1. Decisive discriminator

**VERIFIED BY RUNNING.** M174 imported the untouched M161 checker and
commissioner, regenerated the fixed-seed 500-site arms, and reproduced M169's
reported values:

| Arm | median `h_e` | median `v_e` | maximum `max(h_e,v_e)` | Gate result |
|---|---:|---:|---:|---|
| clean-noise null | `0.0029430516302103543` | `0.002320178352496525` | `0.006863374246262382` | PASS |
| 0.5% rim + 0.5% veil | `0.010413357351919823` | `0.005338683767680065` | `0.014729783758402937` | FAIL, only median `h_e` |

The clean-null and improvement summaries match M169's committed
`commission-v2.json` field-for-field to `1e-12` across median, p99, maximum,
width, and coherence values.

**INFERRED FROM THE VERIFIED RUN.** Explanation (A) is rejected. A floor near
`0.0104` would also place the clean null near that value. Instead the clean
null is lower by `0.007470305721709468` and has more than threefold headroom
to the gate. The checker cleanly distinguishes the clean fixture from the
slightly defective fixture.

## 2. Why the pass assertion was wrong before execution

**VERIFIED BY READING.** The frozen plant definitions are:

- rim: subtract `a` on offsets `-24..-12` and add `a` on `+12..+24`;
- two-sided veil: add `a` wherever `16 <= |s| <= 200`;
- `h_e` support: `2 <= |s| <= 32`;
- improvement-arm component amplitude: `a = 0.005`;
- median `h_e` gate: `0.01`.

**INFERRED FROM THE FROZEN DEFINITIONS.** On positive offsets `+16..+24`,
the two plants overlap. The output delta is therefore

```text
0.005 rim + 0.005 veil = 0.010
```

at nine samples inside `h_e` support. The noiseless combined plant is exactly
at the median gate before independent source/output noise with
`sigma = 0.002` of the step is added. Calling this a mandatory green arm had
zero design margin. “0.5% rim and veil” names the amplitude of each component,
not the combined local excursion.

**VERIFIED BY RUNNING.** At the same 0.5% component amplitude, the fixed
population separates the components from their combination:

| Plant | median `h_e` | `0.01` median gate |
|---|---:|---|
| clean | `0.0029430516302103543` | PASS |
| rim only | `0.006586935284439988` | PASS |
| veil only | `0.006758747128664467` | PASS |
| rim + veil | `0.010413357351919823` | FAIL |

**INFERRED FROM THE VERIFIED RUN.** This is the response expected from
additive defects, not an unreachable gate.

## 3. Response curve and crossing

**VERIFIED BY RUNNING.** M174 swept a fixed, uniformly spaced
`0.00%..0.60%` component-amplitude grid in `0.05` percentage-point steps,
using the same 500 sites, source/output noise realization, checker, and gates
at every point:

| Rim amplitude | Veil amplitude | median `h_e` | median gate |
|---:|---:|---:|---|
| `0.00%` | `0.00%` | `0.002943051630` | PASS |
| `0.05%` | `0.05%` | `0.003041248093` | PASS |
| `0.10%` | `0.10%` | `0.003411811924` | PASS |
| `0.15%` | `0.15%` | `0.004062507905` | PASS |
| `0.20%` | `0.20%` | `0.004775801765` | PASS |
| `0.25%` | `0.25%` | `0.005648873328` | PASS |
| `0.30%` | `0.30%` | `0.006526127291` | PASS |
| `0.35%` | `0.35%` | `0.007461084479` | PASS |
| `0.40%` | `0.40%` | `0.008449086051` | PASS |
| `0.45%` | `0.45%` | `0.009443927364` | PASS |
| `0.50%` | `0.50%` | `0.010413357352` | FAIL |
| `0.55%` | `0.55%` | `0.011399664354` | FAIL |
| `0.60%` | `0.60%` | `0.012398952011` | FAIL |

The 13 examined points partition into 10 median-gate passes and 3 failures.
No point was skipped.

**VERIFIED BY RUNNING.** Bisection on that frozen response places the
median-`h_e` crossing at approximately `0.477804796%` per component. The
corresponding noiseless combined peak is approximately `0.955609592%` of the
source step. Thus the 0.5%+0.5% arm lies above the instrument's measured
crossing, while the clean null remains far below it.

**INFERRED FROM THE VERIFIED CURVE.** The subsidiary median gate is doing its
declared typical-boundary job. It detects a repeated, sub-1% local combined
excursion even though the arm remains comfortably inside the separate 5%
per-site headline ceiling.

## 4. Pre-existing lineage rules out outcome-driven tuning

**VERIFIED BY READING AND HASHING.** M152's committed commissioning artifact
hashes to
`cd997c28a6e0532c48858350f0f3c0c0434285ede91413ce43952a6880b36ad6`,
the hash printed in `M152-site-census.md`. Before M161 existed, the same
nominal 0.5% rim-plus-veil arm already read:

- median `h_e = 0.009884948408137492`;
- p99 `h_e = 0.009998092697349402`.

That p99 had only `0.000001907302650598` absolute margin to `0.01`.
M152 registered only the two directional assertions:

- `improvement_reduces_h_by_at_least_5pp`;
- `improvement_reduces_v_by_at_least_5pp`.

It did **not** register a whole-arm pass assertion.

**VERIFIED BY READING.** M161 explicitly cited those M152 values as evidence
that the channels move in both directions. M161 then retained the 0.5%
component amplitudes, replaced M152's exact-in-hull synthetic null with
independent `sigma=0.002` source/output noise, and added the new
`improved_arm_passes` assertion.

**INFERRED FROM THE FROZEN DESIGN AND PRE-M161 EVIDENCE.** The inconsistency
was knowable before the M161 battery ran. The prior p99 was already only
`1.9e-6` below the median gate, the revised fixture deliberately added
nonzero noise, and the two 0.5% components sum to the full 1% gate where they
overlap. No observed candidate, comparator, or holdout value is needed to
derive that “must pass” was the wrong oracle.

**INFERRED FROM THE LINEAGE.** The arm's name and original role were coherent: it was a **planted
improvement**, meaning a large red defect was made much smaller and both
channels had to move downward. It was still a planted `rim_and_veil` defect.
The later whole-arm-green assertion was the clerical mismatch.

## 5. Correct registration and goalpost discipline

**INFERRED FROM THE FROZEN DESIGN (RULING).** The frozen arm should have been registered as:

```text
planted_improvement_0_5pct_rim_and_veil:
    improvement_reduces_h_by_at_least_5pp = true
    improvement_reduces_v_by_at_least_5pp = true
    expected_gate_result = FAIL_MEDIAN_H_E
```

**INFERRED.** At minimum, it must not be registered as a whole-arm PASS. If a future lane
wants a green paired-recovery arm, it must pre-register a separate removal or
sub-boundary plant before running that new version; choosing a new amplitude
now to make this result green would be tuning and is not licensed here.

**INFERRED FROM THE SCOPE OF THE RULING.** The following remain unchanged:

- the ratified headline bar remains `max_e max(h_e,v_e) <= 0.05`;
- median `h_e` and median `v_e` remain `<=0.01`;
- every p99, affected-rate, Wilson, width, coherence, and warp gate remains
  unchanged;
- the 0.5% rim and 0.5% veil plants remain unchanged;
- the checker source, fixed seed, and population remain unchanged.

**INFERRED.** Correcting an oracle from “a deliberately planted boundary
defect must pass” to “that defect remains red while moving strongly downward”
does not relax product acceptance. It preserves and correctly exercises the
strict gate. The old M161 artifact remains
`NOT_ADMITTED_COMMISSIONING_FAILED`; only a newly registered assertion version
and fresh rerun can supersede it.

## 6. Controls, accounting, and scope

**VERIFIED BY RUNNING.** `adjudicate.py` completed 23 checks: 23 PASS, 0 FAIL,
0 ERROR. Its response curve accounted for 13 of 13 points: 10 PASS and 3 FAIL.
The oracle control replaced one unique full line with the exact defect under
adjudication (`PASS_ALL_GATES`) and proved the checker rejects it. A
missing-anchor probe hard-errors.

**VERIFIED BY RUNNING.** The current M161 checker, definition, and commissioner
match their pinned SHA-256 values, and `git diff 47d67a9f --` is empty for the
four frozen M161 source/registration files. M169's checker and definition are
byte-identical to M161. No capture, candidate, comparator, or protected
holdout pixel was opened.

**VERIFIED BY READING.** M169's present refusal to score remains correct.
Separately from this assertion defect, required product packages and the
scorecard's comparator-qualification limb remain absent. This report
adjudicates only the improvement assertion.

**VERIFIED BY RUNNING.** Reproduce from the project root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python experiments\M174-m3-assertion\adjudicate.py
```

**VERIFIED BY RUNNING.** Primary artifacts:

- `experiments/M174-m3-assertion/adjudicate.py`;
- `experiments/M174-m3-assertion/oracle-template.json`;
- `experiments/M174-m3-assertion/out/adjudication.json`;
- `experiments/M174-m3-assertion/out/adjudication.sha256`.

**VERIFIED BY RUNNING.** The committed adjudication JSON has SHA-256
`db0ae4e650d7254bb8a77c15d67eceec245835b3635434f27865cde422e50388`.
