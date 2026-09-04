# Next build path: the requested queue was overtaken before publication

**Date:** 2026-09-03

**Original decision:** **No new product build is authorized today.**

**Current disposition:** do not start D9, dust, or runtime PTC. A later
committed verdict has already authorized the crop-early M8 repair, so the
original headline and global ranking are no longer current
(`docs/STATUS.md:2216-2290,2363-2394`, commits `bf91f823`, `424e66d4`).

The planning snapshot behind this decision had all twelve scorecard axes
unmeasured, and the binding constraint was M1: the detail axis had no admissible
instrument (`docs/proposals/2026-09-sota-scorecard.md:1145-1164`;
`docs/STATUS.md:1905-1912`). That makes most attractive quality work
unscoreable. Within the original three-option queue below, D9 led for one reason:
worker-invariance is verified with exact hashes and does not require M1
(`docs/proposals/2026-09-sota-scorecard.md:1038-1103`).

## Intervening verdicts: the planning premise and rank 1 changed

After the plan was written, M8 produced a committed verdict:
**`FAIL; no blocker`**. The commissioned census found `1.030569%` of merged
pixels outside their source hull, with excursions from `-240.040039` to
`+586.215820` DN (`docs/research/M8-overshoot.md:1-6,37-62`, commit
`76b3d9cc`). `docs/STATUS.md:1992-2010` records that verdict and explicitly says
the scoreboard moved (commit `62c1fe95`).

The follow-up then found that Crop's poor retained area came from a fixable
late-crop boundary-poisoning bug, while the shipping Scale default carries
`0.2901-0.4619%` magnification error against Crop's `0.0174-0.0231%`.
The program record now calls the crop-early fix **“the most consequential open
build in the program”** and assigns implementation and independent verification
to separate lanes (`docs/STATUS.md:2216-2290,2363-2425`, commits `bf91f823`,
`424e66d4`). That is a committed contradiction of D9 as the global rank 1; this
document preserves D9 > dust > PTC only as the ordering among those three
unstarted options.

Two other planning facts also expired before publication:

- Candidate 2 is now empirically **DEAD** on its potent gamma-3 and logistic
  tone arms (`docs/research/M-CAND2.md:1-45`, commit `e9b3f830`; status commit
  `6b39a63a`).
- Repeat-pair FRC remains unavailable as M1, but its report now authorizes a
  synthetic/development commissioning battery rather than permanent
  secondary-only retirement
  (`docs/research/M-FRC-VIABILITY.md:1-13,540-570`, commits `58d04408`,
  `bc3b3af0`).

## What ends the pause

Work resumes only after the following outcomes are committed and the owner
re-ratifies the resulting order.

| Adjudication | Required verdict | What that verdict licenses |
| --- | --- | --- |
| **M8 / Crop** | M8 is **FAIL**. Finish the authorized crop-early implementation and independent verification: the registered prediction is a safe inset `<=8 px` with retained area above the unchanged `80%` gate, followed by an M8 rerun (`docs/STATUS.md:2269-2290,2390-2394`). | Passing geometry, retained-area, and M8 checks licenses reconsideration of Crop as the default and a whole-program re-ranking. It does not pre-authorize the default flip. |
| **M12** | Run the registered `N=33/105/299`, workers `1/2/4/8/16`, six-scored-run cells; the existing `N=20`, workers `1/4/8` sweep is diagnostic only and the formal value remains `UNMEASURED` (`docs/proposals/2026-09-sota-scorecard.md:1038-1103`). | Fixed-worker determinism plus a cross-worker mismatch licenses D9. A formal M12 pass kills D9 and promotes dust correction to rank 1 within this queue. A fixed-worker failure licenses diagnosis, not D9. |
| **Candidate 2** | **Complete: DEAD.** Gamma-3 returned `R=0.502893`, logistic `R=0.486741`, and both intervals missed the frozen `[0.99,1.01]` equivalence region (`docs/research/M-CAND2.md:28-45`, commit `e9b3f830`). | No Candidate-2 product or M1 work is licensed. This outcome leaves the M1-independent three-option queue intact. |

Candidate 2's old clipped-USM run is evidence of nothing beyond an invalid
arm: zero of `2,088,960` values touched a rail, so clipping was a no-op
(`docs/research/M-CAND2.md:27-37` at results commit `8c9966fa`). The replacement
clipping arm also remained below its frozen potency gates; the independent tone
arms, not clipping, killed the candidate (`docs/research/M-CAND2.md:22-45`,
commit `e9b3f830`). Its unclipped-USM arm was only the predicted
algebra/implementation check: the original `R = 1.0000000000000266` (`1 +
2.66e-14`) and the amended `R = 1.0000000000000009` both carried maximum
covariance-congruence residual `1.25e-15`
(`docs/research/M-CAND2.md:19-25` at commit `8c9966fa`;
`docs/research/M-CAND2.md:16-20` at commit `e9b3f830`).
Do not cite either uncommissioned clipping arm for or against the candidate.

## Holdout boundary: **383 image frames, not 319**

The approved, not-yet-shot holdout is now **383 image frames plus 24 witness
frames, 407 total**; it supersedes the 319-frame version
(`docs/capture-requests/2026-09-319-frame-session.md:1-24,131`;
`docs/STATUS.md:1955`, commits `afa9c5eb` and `2102eb1f`). The filename retains
`319`, so searches by the old number are unsafe.

Seal that session on arrival. It is never available for design, tuning,
threshold selection, debugging, or any exploratory reading
(`docs/capture-requests/2026-09-319-frame-session.md:65-68`;
`docs/proposals/2026-09-sota-scorecard.md:319`). None of ranks 1 or 2 needs a
new capture. Rank 3's reference-body work also needs none.

## Conditional remainder of the original queue

The active crop-early repair sits ahead of this list under the later committed
program verdict (`docs/STATUS.md:2383-2394`). The ranks below retain the
planner's requested relative order only; they authorize no implementation.

### Rank 1 — D9: fixed reduction lattice

**Why this is first within the queue.** Worker count currently changes
floating-point reduction order. On the 205-frame `flower-bud-alone-cpl` stack,
workers 2 versus 7 changed `0.2573%` of pixels, with maximum absolute movement
of `1 DN` and no pixel moving farther
(`crates/strehl-cli/src/merge_cmd.rs:5220-5239`). Exact cross-worker hashes test
this defect directly; no detail statistic, comparator, new capture, or holdout
reading is involved (`docs/proposals/2026-09-sota-scorecard.md:1038-1103`).

**Landing.** Change only CLI merge scheduling and its tests in
`crates/strehl-cli/src/merge_cmd.rs`: divide the logical frame sequence into
fixed chunk boundaries independent of worker count, let workers execute those
chunks, and absorb completed chunk accumulators in fixed logical order. This is
the independently specified D9a design
(`docs/proposals/2026-08-sota-path.md:1747-1760`).

This route preserves the current arithmetic. It has a much smaller blast radius
than converting `BandMerge` to fixed-point associative accumulation, which is
the separately specified frontier/GPU route
(`docs/proposals/2026-08-sota-path.md:1761-1776`).

**Frozen pre-code kill gate.** D9 may proceed **if and only if** the formal M12
run shows both:

1. every fixed-worker six-run cell yields exactly one hash; **and**
2. at least one registered `N` yields more than one hash across worker counts.

This gate distinguishes schedule-dependent reduction order from instability at
a fixed schedule. It is frozen here before behavior-changing code.

**Consequences are mandatory.**

- If both conditions hold, implement D9 and require one exact output hash across
  workers `1/2/4/8/16`.
- If any fixed-worker cell produces multiple hashes, stop: D9 is not licensed.
- **If M12 formally passes, D9 dies and default-on dust correction is promoted
  to rank 1 within this queue.**

**Verification.** Exact artifact hashes across all registered worker counts,
while preserving the frozen workers-4 reference, are the acceptance test
(`docs/proposals/2026-09-phase1-design.md:282,322`). Never use the holdout.

### Rank 2 — default-on dust correction

**Evidence.** On the physical mote, correction moved the centre reading from
`-4.644%` to `+0.019%` (`docs/research/V-MOTE.md:253-316`). A deliberately
translated wrong map was refused, and the full 205-frame output was byte-for-byte
identical to correction-off (`docs/research/V-MOTE.md:347-374`).
The adjudication recommends switching the feature on by default
(`docs/research/V-MOTE.md:480-503`).

**Landing.** Flip the default in
`crates/strehl-cli/src/stack.rs::defect_request_from_env` and add default/freeze
tests (`crates/strehl-cli/src/stack.rs:878-895`). Do not broaden the correction
algorithm.

**Frozen acceptance and kill rule.**

- Reproduce direct attenuation at the physical mote.
- Across every eligible existing stack, require translated-map and stale-map
  arms to be byte-exact nulls against correction-off.
- Kill the default flip if any translated or stale-map arm changes even one
  byte.

No new capture is required. The limitation is material: the measured no-harm
byte null covers exactly one subject, not a corpus. A corpus-wide stale-map null
is still owed (`docs/research/V-MOTE.md:375-394,480-503`).

### Rank 3 — runtime PTC port

**Why it is a port.** The temporal, adjacent-frame, per-CFA gain estimator
already exists in research and passed its registered control, while production
explicitly says the promised runtime estimator does not exist
(`docs/research/M-PHASE0-PTC.md:64-83`;
`crates/strehl-core/src/noise.rs:44-60`).

**Landing.** Port the estimator into `crates/strehl-core/src/noise.rs`, connect
profile provenance in `crates/strehl-core/src/profile.rs`, and enforce it in
merge preflight.

**Frozen scope and verification.**

- Estimate **gain only**.
- Require CONSIST-qualified gain within the frozen `+/-3%` band
  (`docs/research/M-PHASE0-PTC.md:142-178`).
- Strike read-floor estimation. The intercept failed on flats and was negative
  in 33 of 48 independent subject rows, so it is not a usable read-noise
  estimator (`docs/research/M-PHASE0-PTC.md:119-138,242-253`).

This verifies noise-model correctness without M1, but it does not currently
move a scorecard axis; that is why it remains below two options with direct
scorecard consequences (`docs/proposals/2026-09-sota-scorecard.md:1145-1164`).
Reference-body work needs no capture. A portability claim would require a
separate set from an unprofiled camera body, never the holdout
(`docs/research/M-PHASE0-PTC.md:251-253`;
`docs/proposals/2026-08-sota-path.md:686-696`;
`docs/capture-requests/2026-09-319-frame-session.md:65-68`).

## M1 ruling: FRC is not the escape hatch

The current Hann-tiled repeat-pair FRC crossing is **NO-GO to pre-admit as
M1**, so it cannot verify a product build today. A later adjudication does,
however, authorize commissioning it now on synthetic and existing development
data (`docs/research/M-FRC-VIABILITY.md:540-570`, commit `bc3b3af0`, superseding
the flatter NO-GO in `34cd4063`).

The reason is structural and must survive any future proposal for a similar
statistic. When the same linear filter multiplies both realizations by a
ring-constant transfer magnitude, that multiplier cancels exactly from the FRC
numerator and both denominator factors. Arbitrarily strong isotropic blur is
therefore canceled by the same property that cancels sharpening: **invariance
and blindness are the same property**
(`docs/research/M-FRC-VIABILITY.md:1-13,261-295`, commit `bc3b3af0`).

That ideal theorem is not exact for the repository estimator after mean
removal, Hann windowing, and finite-width binning. The mandatory battery must
therefore establish power, fixed-pattern nulls, and a structural sharpening
argument before M1 admission (`docs/research/M-FRC-VIABILITY.md:289-295,551-562`,
commit `bc3b3af0`). Until then FRC may serve as a secondary
repeatability/coherence sentinel, but it cannot carry a preserved-resolution
claim.

Consequently, reject FRC as primary M1, reject another sharpness statistic
already defeated by free USM, and reject any noise or detail build whose benefit
can be demonstrated only through M1. Every empirical detail candidate to date
either rewarded sharpening or, for FRC, was blind to blur; M1 has no admissible
instrument (`docs/STATUS.md:1570-1620,1905-1912`;
`docs/proposals/2026-09-sota-scorecard.md:116-120`).

## Closed directions

“Closed” does **not** mean “disproved.” The record contains empirical
refutations, capacity/choice closures, and refusals to build from inadequate
evidence. Conflating them would fabricate stronger conclusions than the work
supports.

### Refutations and kills

| Direction | Classification and consequence | Authority |
| --- | --- | --- |
| **DPAR2** | **KILL.** The measured amplitude was far below the registered depth-conditioned-warp prediction; do not build the warp. | `docs/research/M-PHASE0-DPAR2.md`, commit `7a1a3128` |
| **CAND1** | **KILL.** Its first commissioned USM arm exceeded the frozen invariance bar; do not revive candidate 1. | `docs/research/M-CAND1.md`, freeze `613eaf1a`, kill `efa25bd2` |
| **Phase-1 admission** | **REFUTED.** The registered common-`k` admission predicate had no solution; the design is bannered “do not implement.” | `docs/proposals/2026-09-phase1-design.md`, commit `f5658e5d`; `docs/STATUS.md:1760-1800` |

### Capacity and product-choice closures

| Direction | Classification and consequence | Authority |
| --- | --- | --- |
| **Decoder** | Capacity gate passed; keep rawler. No owned decoder build is warranted. | `docs/research/M-PHASE0-DECODE2.md`, commit `d337daa8` |
| **IOCP** | Storage gate passed with storage materially ahead of decode; no IOCP prefetch build is warranted. | `docs/research/M-PHASE0-NVME2.md`, commit `d337daa8` |
| **Crop default** | At the planning freeze the default flip was closed: retain `scale`. That historical verdict did not know the retained-area failure came from late-crop boundary poisoning. Crop-early implementation is now open, but the default flip still awaits independent geometry/M8 verification. | `docs/research/BUILD-CROP.md:54-79`, commit `66e79043`; superseding diagnosis at `docs/STATUS.md:2216-2290,2363-2425`, commits `bf91f823`, `424e66d4` |

### Failed robustness/admission gates

| Direction | Classification and consequence | Authority |
| --- | --- | --- |
| **ASTIG** | **NOT ROBUST.** The registered outer-sector minimum was missed; no astigmatism build enters the queue. This is lack of build license, not proof of no effect. | `docs/research/M-PHASE0-ASTIG.md`, commit `f063275a` |
| **LCA** | **NOT ROBUST/STOP.** The whole-field validity ladder failed; no LCA correction is licensed. This is not a zero-effect claim. | `docs/research/M-PHASE0-LCA.md`, commit `a3b87d36` |

### Refusals only — explicitly not disproofs

| Direction | What the registrar admitted | Consequence |
| --- | --- | --- |
| **XSPEC** | Its 132 eligible tiles missed the frozen minimum of 160. It **“failed to show C10 works, but did not show C10 cannot work.”** (`docs/STATUS.md:1862-1870`; `docs/research/M-PHASE0-XSPEC.md`, commit `4f1f28ec`) | Refuse the build. A properly powered future study remains a real option. |
| **VEIL2** | Its effective count was 36 clusters rather than 20,000. The 0/7 audit **“blocks building but does not prove zero effect.”** (`docs/STATUS.md:1862-1870`; `docs/research/M-PHASE0-VEIL2.md`, commits `e4e3939f`, `bcc77de9`) | Refuse the build. Do not cite this result as absence of a veil effect. |

These were the ten directions closed at the planning freeze: decoder, IOCP,
DPAR2, XSPEC, ASTIG, VEIL2, LCA, CAND1, Crop default, and phase-1 admission.
Only DPAR2, CAND1, and phase-1 admission were refutations/kills; XSPEC and
VEIL2 are structurally separated because the registrar admitted them as
refusals only. The later crop-early diagnosis reopens implementation order, not
the default flip itself.

## Current ownership and supersessions

- **M8 is owned and measured FAIL**, with causal attribution/remediation still
  active; it is not rejected work (`docs/research/M8-overshoot.md:1-6`;
  `docs/STATUS.md:2216-2290,2363-2394`).
- **Repeat-pair FRC commissioning is owned experimental work**, but the current
  crossing is not admitted as M1 (`docs/research/M-FRC-VIABILITY.md:540-570`,
  commit `bc3b3af0`).
- **Candidate 2 is no longer owned/in-progress work.** The prompt's status was
  superseded by the committed nonlinear-tone kill
  (`docs/research/M-CAND2.md:1-45`, commit `e9b3f830`).

The actionable instruction is: let the assigned crop-early implementation and
independent verification finish; complete formal M12; do not start D9, dust, or
runtime PTC until the owner re-ratifies their order; use only existing
development data for the FRC commissioning battery; and never touch the
383-frame holdout.
