# Independent mechanical controls for observational full replay

Preregistered before execution, 2026-09-19. Root owns execution and resource
decisions; new_captures authors the adapter; full_context_placement owns this
independent review/control. The prior generated quality screen remains failed
and unchanged. This is a separately scoped observation, not promotion.

One new mechanical test will emit BOUNDARY_CFA_FULL_MECHANICAL. Existing
generated controls are rerun unchanged after the refactor; this is regression
verification, not a new truth campaign or weakened guard.

- Exercise full-depth transform on4096x1 and1x4096 complex data: independent
  packing occupancy, twelve reached AC levels plus terminal DC, roundtrip
  max error <=5e-5 of input scale, relative Parseval error <=5e-5; constant
  non-DC energy <=1e-6 per coefficient. These are arithmetic checks, not
  image quality. Full3460x2306 plan must be4096x4096 with offsets318/895,
  while the generated entry retains its former extent refusal. No4096²
  array is needed for the structural control.
- One explicitly nonzero CA profile and asymmetric active/crop geometry must
  take the full profile/domain validation path and produce changed red/blue
  source coordinates. The same profile must apply to signal and noisy source.
  Check exact composition/domain values, invalid geometry/profile refusal,
  and actual coverage; no calibration or newly fitted CA. Use the existing
  commissioned GPU/CPU convention, never a newly invented sampler.
- Reproduce the fixed ISO100 fractional weak-red fixture and exact prior
  baseline RGB hash76b42e87ca9a53011af3f8a9d6d81b0925534c9075d67476be3c192a57c8be40
  and candidate893ef6e6fbf4ab76e42e94a8506cfc7ff4bf94c8d33bd2e86142a2a7335a22b7.
  This binds shared fold/probe/finalization refactors to the actual former
  result, including its failure; unchanged output is not an improvement.
- The new output helper's small RGB16 TIFF must exactly equal the existing
  held developer with pinned tone. Assert shape/type, native CFA addressing,
  finite samples, actual tone liveness and input immutability. Any full-size
  display factor must retain its exact declared arithmetic and be neutral
  when1; it may not become an undeclared exposure fit.
- Retain source-space u16 rounding/headroom behavior: invalid variance and
  out-of-u16 draws refuse; the helper must not silently clamp at sensor white
  or change its original simulation distribution. Test zero and65535
  endpoints with zero variance as deterministic refusal witnesses; legal
  near-white samples remain allowed just as before. This does not establish
  a physical clipped-sensor noise model.

Read-only adapter review additionally requires original source/WB/black/white/
matrix/active/stride identity, all70 held transforms and actual CA-supported
crop, exact original four-plane canonical chunk boundaries/reduction order,
baseline decodedRGB16 hash2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda,
and fixed tone[.090420,.914606,.55]. Cost mode must use source35 at the full
4096²/12-level domain with all eight pairs, inverse and actual writer; no
partial probe masquerading as whole-frame cost. Full mode remains one active
worker, current source/current pair plus accumulators, with no aligned N-frame
collection. It must retain admission=false and the observational label.

Root runs fresh compilation and the mechanical/generated filters under its
bounded process wrapper, then one actual-source35 cost witness. Only root may
authorize a complete70-frame replay after measured wall/CPU/peak-memory and
mechanical results. No full photographic quality judgment is part of this task.
