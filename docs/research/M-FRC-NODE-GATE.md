# M-FRC-NODE-GATE: A7C II focus-ladder witness adjudication

Status: **FROZEN NO-GO for a witness-only node-coincidence gate**

Owner: lane-FRC

Date: 2026-09-03

## Headline verdict

No finite set of fixed-focus witness bursts can prove that two automated Sony
A7C II focus brackets visited the same interior focus nodes. Fixed witnesses
can qualify stability, the reset position, and the final position. They cannot
observe an interior motor error that disappears before the endpoint.

Therefore the proposed fallback

> fixed-focus witnesses alone decide whether A and B are same-node repeats

does **not exist** under the confirmed hardware constraint. The inherited
`0.10` native-pixel bar remains valid for geometry at positions that were
actually witnessed. It is not a threshold for an unobserved focus ladder.

The stronger same-focus requirement is real: correlation to another product
derived from the same noisy realization would also validate amplified sensor
noise (`docs/research/V-HEADTOHEAD3.md:194-201`). The prior FRC adjudication
already found that reset witnesses cannot certify an undisplaced ladder offset
and that no cross-pass ladder-phase bar is registered
(`docs/research/M-FRC-VIABILITY.md:48-112`).

## 1. Witness frames

### 1.1 Strongest useful fixed-focus sentinel set

If the session is shot, collect **60 fixed-focus witnesses**. These are
sentinels, not proof of interior node equality.

All witness frames use the same exposure as the brackets. Turn Focus Bracket
off for each burst. Hold focus with one repeatable method - manual focus or an
electronic focus hold - that does not move the lens when entering or leaving
the mode. Wait at least 3 seconds after focus motion stops before the first
frame. Do not touch focus during a six-frame burst. If changing between the
hold and Focus Bracket moves focus, the witness protocol is invalid.

#### Reset pre-flight: 12 frames before any bracket

1. Approach the recorded near-focus reset from the chosen direction.
2. Lock focus and take six frames: `P0`.
3. Move focus well away.
4. Return to the reset by the identical approach.
5. Lock focus and take six frames: `P1`.
6. Read the geometry sentinel in section 2.2 before shooting a bracket.

This is the only genuinely cheap pre-flight. It can reject an unstable rig or
an unreproducible reset before the main session. It cannot test the ladder.

#### Step width 4: 24 frames around the two passes

1. At the reset, immediately before A: six locked frames, `S4-A`.
2. Run the complete 55-frame step-width-4 A bracket.
3. At A's untouched final focus position: six locked frames, `E4-A`.
4. Return to the reset by the identical approach.
5. Immediately before B: six locked frames, `S4-B`.
6. Run the complete 55-frame step-width-4 B bracket with identical settings.
7. At B's untouched final focus position: six locked frames, `E4-B`.

`E4-A` and `S4-B` are both between A and B because they answer different
questions: endpoint repeatability and reset repeatability.

#### Step width 10: 24 frames around the two passes

Repeat the same sequence as
`S10-A`, bracket A, `E10-A`, `S10-B`, bracket B, `E10-B`, with 27 frames and
step width 10 in each automated bracket.

The total is:

```text
P0/P1                         12
sw4 start/end A/B             24
sw10 start/end A/B            24
fixed-focus witness total     60
```

Start-only witnesses are insufficient because they never observe accumulated
span. Adding one or several midpoint anchors still cannot establish every
unobserved interval.

## 2. Frozen gate

### 2.1 Why no witness-only node gate can pass

Let `L_A(i)` and `L_B(i)` be the physical focus positions reached at bracket
index `i`. A fixed witness observes only a set of anchor positions `W`, such as
the reset and endpoint.

For any pair of ladders that agree at every witnessed anchor, construct another
ladder that:

1. agrees with the first ladder at every `i` in `W`;
2. differs at one unwitnessed interior node by a physically feasible amount
   larger than the proposed same-node tolerance; and
3. uses the following unobserved motor transition to return to the next
   witnessed anchor, which may be the immediately following node.

The fixed witness pixels are identical in the good and bad cases. Every
statistic computed only from those witnesses therefore has the same value in
both cases. No threshold can accept the good ladder without also accepting at
least one bad ladder.

The result does not depend on using only start and endpoint witnesses. Any
finite anchor set smaller than the complete node set leaves an interval in
which the same construction applies. No registered hardware model bounds
interior motor error tightly enough to exclude that alternative; if such a
bound existed, the bound rather than the witnesses would do the certifying.
Observing every node is the primary paired-exposure design that the A7C II
cannot execute.

### 2.2 What can be frozen from the witnesses

The following is a valid **geometry sentinel**, not a node-coincidence gate.
It retains the existing estimator and bars.

For each six-frame burst, compute the within-burst four-quadrant local
registration RMS:

> A burst passes `G0` only if it is `<= 0.033` native-pixel local RMS.

Both P0 and P1 must pass before any bracket is shot. A step width is G0-eligible
only if all four of its start/end bursts pass. A failed burst invalidates its
own step width, not a separately witnessed width.

For each pair `P0/P1`, `S4-A/S4-B`, `E4-A/E4-B`, `S10-A/S10-B`, and
`E10-A/E10-B`, black-subtract every RAW and average the six frames within each
burst. Estimate one global translation and four quadrant translations between
the two burst means and compute:

```text
R = 2 * sqrt(mean_q(||shift_q - shift_global||^2))
```

> Each comparison passes only if its `R < 0.10` native pixel.

Apply that bar in two scopes:

- P0/P1 must pass before any bracket is shot.
- A step width passes G1 only if both its start pair and its endpoint pair pass.
  A failure at one width does not change the other width's G1 result.

Use a common integer shift and crop. The estimator may measure a fractional
residual, but no fractional resampling, scale, rotation, or local warp may be
applied. Integer registration removed a planted 3-pixel displacement exactly;
one 0.37-pixel resample retained a signed `2.3987 um` bias
(`docs/research/M88b-merge-sharpness.md:74-84`).

The bar has real provenance. SPLIT2 passed one block at `0.064031`, failed the
other at `0.107703`, and an independent estimator reproduced the failure at
`0.105202` (`docs/research/M-PHASE0-SPLIT2.md:7-13,73-87`). The historical
witness gate also freezes `G0 <= 0.033` and strict `G1 < 0.10`
(`docs/capture-requests/2026-09-node-coincidence-gate.md:81-125`).

The only allowed witness-only outcomes are:

| G0/G1 outcome | Meaning |
| --- | --- |
| fail | observed stability, reset, or endpoint geometry is unacceptable |
| pass | observed witness geometry passes; interior node coincidence remains **UNPROVEN** |

There is no `NODE_COINCIDENCE PASS` outcome from fixed witnesses alone.

The fixed-focus log high/mid spectral proxy has a `0.10` stability precedent,
but its cross-burst, cross-ladder use has not been commissioned. It must not be
silently relabelled as a node-equivalence threshold. The prior adjudication
records this missing bar explicitly (`docs/research/M-FRC-VIABILITY.md:84-112`).
`FocusPosition2` and `FocusDistance2` cannot replace it: only four distinct
values appeared over a 105-frame fine sweep
(`docs/research/BUILD-CHROMA.md:160-165`).

### 2.3 What would actually unblock same-node use

One of these must exist:

1. per-node paired exposures or absolute focus telemetry, neither available in
   the confirmed camera workflow; or
2. a separately commissioned, input-only gate on the **actual A and B bracket
   RAWs**, comparing frame `i` only with frame `i`, with no result-time
   re-indexing.

The second option is not computable from fixed witnesses alone. It is the only
available way to observe the interior nodes that would be licensed. Until its
focus-equivalence statistic and numerical bar are commissioned on development
data, the A/B passes cannot be called proven same-node repeats.

## 3. Failure and salvage

### 3.1 Reset pre-flight failure

If `P0/P1` fails G0 or G1, stop before shooting any bracket. Correct the rig,
focus-lock method, or reset procedure, then repeat the complete pre-flight.
Never widen the bar or select a favorable subset of the six frames.

### 3.2 Start or endpoint sentinel failure

If either start or endpoint pair fails for a step width, that A/B pair is
unusable for any same-node-repeat claim. Do not re-index frames, replace one
node, or reinterpret the other endpoint as a pass. A failure at one step width
does not logically invalidate the other width, but it does invalidate any
session-level result whose protocol requires both.

### 3.3 Witness pass

A witness pass is partial evidence, not admission. Without the actual-node gate
in section 2.3, both A/B pairs remain `NODE COINCIDENCE UNPROVEN` even when all
60 witnesses pass.

The individual brackets remain ordinary focus stacks. The checker-only `sw1`
run and the independent calibration groups remain usable for purposes that do
not require frame-for-frame same-focus repeats. The physical same-focus
question in `V-HEADTOHEAD3` remains blocked.

## 4. What in-camera bracketing helps

In-camera bracketing removes human per-node placement and timing error. The
camera issues one deterministic command program with a recorded step width,
shot count, direction, and interval. Repeating that exact program from the same
physical start, aperture, and lens state is stronger than asking a person to
recreate dozens of rail or focus-ring moves.

That makes the sentinel protocol worth shooting:

- matching starts test the load-bearing initial condition;
- matching endpoints test accumulated span;
- exact settings eliminate several avoidable causes of divergence; and
- an actual-node pixel gate can compare corresponding indices without guessing
  which human move was intended.

It does not create absolute focus observability. Sony specifies step width as a
relative value whose interval varies with aperture and initial focus
(`docs/research/F-camera-lens-optics.md:905-929`). The available focus metadata
is too coarse to certify a fine ladder. Determinism therefore lowers the prior
probability of an interior mismatch; it does not make a witness-only PASS
logically available.

No step-width choice makes a residual offset harmless. Step width 10 and step
width 4 must be qualified separately.

## 5. Odd/even splitting: two different questions

### 5.1 Invalid as same-node repeats

One finer bracket split by parity gives:

```text
A[i] = frame[2i]       at focus position z[2i]
B[i] = frame[2i + 1]   at focus position z[2i + 1]
```

The frames are separate exposures, so their temporal shot/read noise is
independent. Their latent focus state is not the same. Reducing the step width
makes `z[2i + 1] - z[2i]` smaller but never zero. This construction must be
rejected for frame-for-frame same-node pairing.

### 5.2 Different purpose: D8 split-half self-calibration, not adjudicated here

D8 asks a different question. It deliberately forms two interleaved, disjoint
half-stacks, lets each half re-derive its own pipeline weights, and uses their
separate exposures as noise realizations. It does **not** claim that
`frame[2i]` and `frame[2i + 1]` share one focus node. Its proposal explicitly
prices the doubled z-axis spacing and relies on a sufficiently dense original
bracket (`docs/proposals/2026-08-sota-path.md:1694-1746`).

The implementation likewise partitioned by global filename parity before
folding each half independently (`docs/research/M-PHASE0-SPLIT.md:123-159`).
D8's purpose therefore does not require odd/even frames to share one focus
node. This document makes no ruling on that instrument. It records only that
the construction remains invalid evidence of same-node equality and that D8's
own record carries a common-mode fixed-pattern limitation
(`docs/research/M-PHASE0-SPLIT.md:23-51`).

The two uses must not be conflated.
