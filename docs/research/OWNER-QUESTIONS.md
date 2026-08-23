# Questions for the owner

Decisions I could not make alone, and things only you can supply. Newest first.
Nothing here blocks current work — I picked a defensible default in every case and
recorded it. Answering changes what ships, not what runs tonight.

---

## Needs you to capture something

| # | What | Status |
| --- | --- | --- |
| C1 | **Flat fields.** You said you would shoot these in daylight. Recipe and frame count in [`docs/captures-needed.md`](../captures-needed.md) §3. | **Outstanding.** Now load-bearing: fact 230's "flats give 42–51σ" is wrong without a PRNU term, and M31-V bounds PRNU only to ≲0.26% without them. |
| C2 | **A focus-rail bracket**, if you ever get a rail. Deferred from v1 by your instruction; the `CaptureMode` seam is in place. | Deferred, not blocking. |

## Decisions

**Q1 — `tenengrad-sq` window.** Candidate (c) beats the shipped operator on the
monotone-edge blind spot (D 1.0000 → 0.1860), ties on quality (15/30 cells, p = 1.00),
ties on noise (ΔN = −0.0015) and is *cheaper* (0.96×). But `w13` was chosen by M13 for the
**mean** operator, and candidate (c)'s per-shape sign is not uniform — consistent with a
window mismatch.
*Options:* re-run M13's window ladder for `tenengrad-sq` before calling it shipped, or land
it at `w13` now behind a flag with the sweep as follow-up.
**What I did:** landed it, per M17's own recommendation — the blind spot is a correctness
hole in the confidence story and a neutral-quality, cheaper operator that closes it should
not wait on an optimisation. The ladder re-run is still open.

**Q2 — how hard to chase fact 45.** M23 withdrew fact 45's *causal* reading (its numbers
reproduce; the attribution to defocus does not — it was the plant's own resampler). I
checked that fact 43 and the M12 ruling do not depend on it. I have **not** audited every
downstream use.
**What I did:** marked fact 45 in place and moved on.

**Q3 — `predicted_sigma`'s definition.** Three of six reasonable definitions **flip the
sign** of fact 281's correlation (question 80). M18's confidence contract must not rest on
a definition that arbitrary.
**What I did:** left it open; the shipped contract uses the acceptance-set-size channel,
which is the only quantity that generalised across all three stacks.

## Warnings — things I am deliberately not surfacing to users yet

**W1 — the f/5.6 advice.** M20 §7 suggests shooting wider and letting reconstruction do the
work. This is a **two-stop extrapolation with no aberration term**, and M20 §4.4 and §7
point in opposite directions. It must not reach a user-facing recommendation until measured
at f/5.6 on real glass. Flagged in M20-VERIFICATION §5.5.

**W2 — fact 242 is withdrawn.** Anything you read in an older report citing "2.3× more
clipping whole-stack" is dead: at the shipped regularisation it is 1.4×, and heavier still
1.0×. Fact 243's HDR verdict rests partly on it and has not been re-derived.

## Cheap follow-ups I did not run

- Run `113MSDCF` as a second placebo for M23's gate (b); currently n=1. ~63 frames, cheap.
- Open question 25: re-measure `coffee-bean` span-1 edges with a known
  integer-plus-half-pixel pre-shift removed analytically, to see whether sub-pixel locking
  contributes to fact 43's span dependence. This is the live thread M23 left behind.
- R5 (blur-equalised edges) is untested and is now the better candidate than R4, because it
  plants nothing and so is immune to the mechanism that killed R4.
