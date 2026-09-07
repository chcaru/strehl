# M194c consumed-site probe layout preregistration

2026-09-07, before product edits and candidate runs. M194c is allocated in
AGENTS.md before dispatch. Product edits wait for the M194b commit; its frozen
baseline inputs, producer and scorer are reused without revision.

## Question, evidence and prior art

Does assigning the existing measured-floor probe sequence to canonical consumed
photosites remove output dependence on unused decoded-buffer storage?

M194b independently measured149804 of180624 TIFF components changing, maximum8
LSB, when identical active CFA data moved from origin(2,4)/stride327/height247
to origin(7,3)/stride339/height251. Both measured-floor arms reproduced exactly;
the existing white-floor intervention made their TIFFs byte-identical and itself
changed the original output. The observed failure and its causal control remain
in M194b, including the initial51/52 control result.

Read before design: SYNTHESIS architecture and floor records1805/1809,
BUILD-GATE, BUILD-GATE-2, BUILD-GATE-4, M194, M194b consumer notes and actual
gatefloor/warp/extract code. Parent's prior-art search also returned V-GATHER,
M77, M69, M98, M48, M71, M189, ORCH-veiling, M87, BUILD-SHARP, M111, M70 and
A-prior-corpus. This is a storage-addressing continuation, not a repeat of their
gate/noise-quality sweeps. In particular BUILD-GATE-2 corrects BUILD-GATE's
unity-WB/no-CA inference: no universal direction of quality change is inherited.

## Small implementation boundary

Only the destination traversal changes. `Probe::run` will fill the complete
consumed native extent `2*domain.full.width` by `2*domain.full.height`, ordered
by active-relative y then x, regardless of analysis crop, origin, padding or
storage stride. Both current gather implementations consume that complete-quad
extent. An odd trailing active row/column is not consumed and will neither draw
RNG samples nor be overwritten. Padding and discarded tails retain their prior
values; tests poison them.

Keep the existing SplitMix64 state, frame-local index seed, Box-Muller draw order
and spare, mean/sigma, rounding and u16 clamp byte-for-byte. Keep the real frame's
WB/path/geometry/levels metadata. Keep measured floor enabled; change no noise
coefficients, denominator, mean removal, band limits, NaN fallback, sampling
margin, gate constant or merge consumer. A small private destination helper may
reuse existing frame validation; it introduces no CLI or product option.

Packed even active dimensions at origin0/stride=width retain the legacy RNG
sequence exactly. Other layouts are expected to change realization and may
change rendered bytes across versions. No cross-version byte-identity claim is
made for padded real captures. No new real RAW run is authorized in this phase.

## Falsifiers fixed before execution

1. **Sampler identity before output.** Independently packed and relocated frames
   with the same consumed extent/index must receive exactly the same active
   u16 sequence. Poisoned outside sites and odd active tails must stay untouched.
   The frozen old flat-buffer traversal must fail this identity, proving the
   null has power. A changed seed must change consumed samples.
2. **Legacy packed sequence.** Compare with the original unmodified fill function
   frozen from source, for several indices and non-square even dimensions.
   Any sample difference fails. This is a lineage check, not RNG-distribution
   commissioning or sensor calibration.
3. **Actual probe identity.** Through production `Probe::measure`, corresponding
   layouts must give bit-identical beta, including matching NaNs, in separate
   fullres and plane gather processes, at identity and a nonlinear per-frame
   scale track. Check whole and offset cropped analysis domains, and several
   band depths. Assert finite and empty normal results actually occur. Exercise
   pooling refusal/NaN preservation only through explicitly labelled helper or
   fault injection, not a fabricated valid-scene NaN case. Require a
   live seed or nonidentity-warp change where finite measurement exists.
4. **Delivered output.** Independently render original and relocated M194b
   plane/noise-off fixtures with the measured floor. TIFF pixels and whole
   bytes must now agree. The white-floor pair remains an inert layout control;
   the original measured-floor failure is retained as the before arm. Optional
   confidence observation must leave the main TIFF byte-identical.
5. **Fixed quality readout, not tuning.** Reuse the complete M194b40-output matrix,
   exact producer files, curved geometry, ROI, target, noise coefficients and
   scorer. Report candidate/baseline differences with all scenes/repeats retained.
   Do not select a seed, parameter or subset after reading the result. A clean
   layout fix alone makes no claim of quality improvement or SOTA. If the frozen
   quality readout materially worsens, report it before promotion rather than
   tuning constants to compensate.
6. **Build and source lineage.** Preserve source hashes, visible Compiling and
   Checking proof, focused tests and raw logs. The production diff must contain
   only the scoped traversal/helper and explanatory comments. Tests may live in
   this experiment and be included by the private module under cfg(test).

Exact byte comparisons can be fooled by a dead path; changed seed/warp and the
old-layout failure provide the positive controls. Beta ratios can be fooled by
shared calibration, so no calibration conclusion is allowed. Output-error scores
can reward blur or average noise at the cost of detail; the already commissioned
flat/plane/color controls and unchanged full matrix remain necessary.

**Pre-execution design correction:** the independent verifier identified that
`level_sizes` stops below extent8 while the probe measures at most `len-2`
levels. A normally measured level therefore has two descendants and minimum
extent29, leaving at least23x23=529 pooled samples. The original plan for a tiny
valid scene to produce a NaN was impossible under these guards; tiny scenes give
an empty beta instead. Author tests are amended before any build/run. The direct
pooling refusal and injected NaN branch are labelled as such. No source scene or
NoiseModel perturbation is claimed to change normalized beta: the probe replaces
real samples and receives no NoiseModel. Seed/warp/WB can change it; image/model
controls belong to delivered output.

## Planned artifacts

`legacy-fill-noise.rs` freezes the pre-edit function; `author-tests.rs` supplies
sampler and actual-probe tests; `run-controls.py` will launch isolated gather
processes and retain compile/test/lint evidence. An independent verifier rechooses
layouts, seeds and geometry before reading the candidate implementation. Parent
owns the fixed matrix comparison and final promotion/commit decision.
