# Independent review of the prospective software-noise contract

2026-09-07, Curie. **SOURCE-REVIEWED / DERIVED / UNEXECUTED.** Subject:
`next-noise-contract.md` at
`2b34218d04dbac2d89a8efb28d93fc6e504cd400c6ce074dce2e67518798306d`.
No noise draws, optical helpers, output generation or product calls were run.
Root authorized resolving the following choices in the draft after this review;
that amended document still requires root review and an execution release.

The proposed law is appropriate for a bounded software test. Sampling
Poisson(c*S), then adding independent 4-electron read noise, gives raw,
black-subtracted DN mean d=.25*c*S and variance .25*d+1 on every CFA plane.
The channel factor changes the photon mean, not the injected gain or read-noise
constant. This oracle does not validate camera calibration, nor predict the
post-WB, demosaiced or merged TIFF variance. The separate temporal and spatial
dependence checks, active c-after-Poisson and green-clone faults, and fixed
restored seeds are useful choices.

## Corrections required before implementation

1. **Read the consumed quantity in each fault.** Raw Poisson counts remain
   integer samples even when the c-after-Poisson fault supplies fractional
   photoelectrons to the sum. Calling both arrays P makes the named c²*S
   variance falsifier ambiguous. Retain raw photo counts and consumed read
   samples; bind actual consumed-photo, raw-normal, electron-sum and encoder
   input hashes. Store the exceptional consumed-photo/raw-normal arrays when
   normal lossless reconstruction no longer applies. Test moments on consumed
   photo/read components. Keep the gain and black-clamp faults' actual encoder
   input, rather than substituting the value their nominal equation predicts.
   A structural or hash rejection cannot replace the promised numerical fault
   response.

2. **Freeze actual pair populations and the tagged array.** The original
   tagged fixture had no values, and “neighboring repeats” did not name its
   components or pooling. Use a literal 4×6 scalar ramp
   S(y,x)=1600+80*x+160*y; its first quad encodes to
   [[812,932],[952,788]]. Swap actual within-quad photosites, not merely the
   equal green factors. Keep all correlations separate by scalar level and
   originating CFA parity: consumed photo/read, adjacent-repeat photo and
   read, nonwrapping horizontal/vertical read pairs, and quad G1/G2. Read all
   ten distinct frame pairs by concatenating the three already retained
   homoskedastic read groups: live-a701, live-a709 and dark701. This gives
   36864 pairs per test; the smaller3072-site parity/frame strata have derived
   null correlation scale about .018 and are descriptive, not additional .02
   acceptance tests. This prospective choice avoids an implausibly restrictive
   collection of small-subset tests without changing the bar or adding draws.
   The shared-dark-key fault still forces equality there and approximately1/3
   correlation in the combined population. Mark zero photon
   variance undefined, and refuse other zero denominators in healthy controls.

3. **Distinguish population and sample rounding bounds.** The proposed bright
   bound is valid for population variance. For 64-sample variances with
   denominator 63, the paired bound is
   |s²Q-s²X| <= sqrt((64/63)*s²X)+(64/63)/4. Averaging it over a parity remains
   bounded by the same expression using that parity's mean sample variance.
   State which observed quantities are compared; do not silently apply a
   population identity to a different estimator. Exact reconstructed Q and
   the tighter X moments carry much more power than this broad bound.
   Evaluate dark positive-bin probabilities using erfc survival differences
   and symmetry, avoiding subtraction of two CDF values rounded to one.
   The stated <1e-30 tail bound is truncation error, not a total floating-point
   error guarantee.

4. **Close the draw and storage schedule.** The 18 complete temporal
   populations require 28,311,552 requested variates. The now-literal 34
   supplemental noisy calls bring the count to 29,147,136. Four baseline
   payload arrays at 26 bytes/site require 378,912,768 bytes across those
   1,186 calls. Four exceptional 64-repeat arrays add 25,165,824 bytes:
   **404,078,592 raw payload bytes**, leaving 132,792,320 bytes under the
   unchanged 512 MiB ceiling for headers, receipts and bounded fixtures.
   Retaining two extra full arrays for every temporal call would not fit.
   A counter measures requested vector elements even when a zero-mean Poisson
   call consumes fewer internal PRNG words. It never resets at a fault,
   restored run or observer boundary.

5. **Keep intended-output evidence honest.** The 90 CFA files consume
   13,824,000 bytes. Full P/R/X/Q traces for their 80 noisy frames alone would
   consume 159,744,000 bytes, incompatible with the intended 32 MiB ceiling.
   Persist the CFA files and bound stream/intermediate hashes there; retain
   full traces in the private commission only. The final independent file
   read checks actual pixels, shape, parity, rails and complete source/input
   lineage, and exactly predicts noise-off files. It must not claim to have
   reread every intended noisy intermediate or independently replayed its
   distribution under a budget that includes only the producer's draws.

6. **Use a new noisy bridge contract.** The frozen M194f child fixes 6144-byte
   64×48 inputs and explicitly requires 512 <= DN < 15360. Those are correct
   restrictions for its admitted noiseless package, but reject this law's
   valid below-black samples and declared inclusive white endpoint. A later
   versioned source must accept exactly 153600 bytes and the declared
   0 <= DN <= 15360 sample range, validate its own genuine noise authority,
   and preserve M194f unchanged. Reuse the prepared consumer seam, with the
   same four injected gain/read pairs; separately commission the larger actual
   plan, three bands, measured-floor prefix, crop, reference2 and baseline WB.
   Those are prerequisites for the later eight-repeat quality comparison,
   not evidence supplied by a noise-file commission.

The tuple-specific RNG identity is defensible within the frozen software
environment. It guarantees whole-frame ordering invariance, not arbitrary
changes to the vector call or per-pixel lambda array. NumPy explicitly scopes
distribution compatibility to the same calls, build and environment, whereas
PCG64DXSM's integer-stream promise is narrower than the complete distribution
pipeline. The draft correctly separates those claims.
([Generator compatibility](https://numpy.org/doc/2.4/reference/random/compatibility.html),
[PCG64DXSM](https://numpy.org/doc/2.4/reference/random/bit_generators/pcg64dxsm.html))

All proposed thresholds remain prospective engineering bars. The fixed
software model can fail its implementation tests, but shared constants cannot
establish physical calibration. No numerical admission or quality conclusion
is made by this review.

Sources read: current SYNTHESIS noise-model rules; the subject draft;
`next-quality-design.md`; M194f `joint-pupil-bridge.rs` prepared source and
decode boundary; official NumPy distribution/stream documentation. Review
arithmetic used only the declared dimensions and field sizes, with no random
or optical execution.
