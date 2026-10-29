# Full-census cached geometry investigation

**Status: no complete real mosaic photograph, master or qualified join yet.**
These are geometry diagnostics on the complete 339+488 source census. Every
refused arm remains saved. The original source cache and captures are unchanged.

The compact guide reconstruction is commissioned by exact production intensity
and source-witness hashes, documented in `pilot-01-diagnosis.md`. The Rust replay
verifies compact-file, original census, independent alignment and focus receipt
bindings. It invokes production feature/native implementations through strict
cache-only entry points. A missing cached original is an error; no RAW decode
path is called. Every replay records four workers, a 4 GiB budget, the source
and configuration binding, all proposed/accepted/refused measurements and cache
statistics. The direct-link builder records complete source/library/executable
hashes and the actual rustc command. All shown replays report zero decodes.

The first direct link used the UI-unified binary-12 dependency fingerprint
`63ce8e1d9f947ed6`; it was initially described to root as binary-13 and that label
was corrected. Build-02 and later use CLI13 fingerprint `d1b5ff31056b7cf3`.
The matched build-02 baseline produced byte-identical feature, candidate and
native JSON files to build-01. Subsequent source-only lint changes in core
`mosaic.rs` do not change arithmetic, but these direct research binaries retain
the recorded frozen13 libraries until a new root build is explicitly used.

## Findings and rejected changes

**MEASURED:** diverse acquisition/spatial nominations increased retained source
features from 290/193 to 414/488 and reciprocal descriptors from 7 to 12. Only
two FIT descriptors agreed with a single global similarity, so the replay
refused before native refinement. Strongest-response replacement and retention
of alternate orientations increased these counts to 443/535 and 13; it did not
by itself establish a seed. Alternate orientations at the same physical pair
are deduplicated before consensus, rather than counted as independent evidence.

The retained matching originals exposed a focus-dependent displacement field.
A FIT-only search model `q = a*p + b + c*t`, where `t` is acquisition ordinal,
finds four coherent proposals at 6.057 quad RMS. Its 24-quad proposal envelope
is the existing six-guide-pixel coarse tolerance and half the existing 48-quad
coarse native search radius. It is **not a registration-quality tolerance**.
The 0.5-quad native RMS and reciprocal bars, six measured tiles, eight distinct
FIT locations, independent spatial holdouts and mesh/loop checks are unchanged.
No held-out descriptor fits this search model. Its source-order check permits
reversed sweeps; a candidate outside the fitted original-source interval is not
extrapolated. The acquisition coordinate is not physical depth.

The first conditional-model replay reached 24 native candidates but accepted
none. Native observation diagnostics again did not justify an affine local fit:
leave-one-tile-out errors remained above 0.7 quad. The additional flexibility
could not supply reliable independent placement evidence.

The original guide witness can nominate an incompatible focus slice where the
focus shape is ambiguous. One observed grid pair used A138/B645, whereas the
FIT-only source correspondence predicted B near493. B uses the absolute global
census including its339-frame pass offset. A bounded learned source mapping
therefore proposes an original B source in addition to the guide witness. The
denser bounded spatial grid produced90 candidates, still with zero accepts.
Alternative originals at one spatial site count once. If their accepted mapped
points disagree beyond the reciprocal tolerance, the site is excluded.

**MEASURED rejected locality policy:** on exactly those frozen90 candidates,
native tile16 still accepts zero and increases residual refusals from18 to23.
Tile32 reproduces the previous native JSON bytes exactly. Smaller local windows
are not enabled as an adaptive policy by this result.

The native128-quad diagnostic patches show real overlap and changed blur/fine
texture. Their display transform and origins are recorded; they are orientation
evidence, not independent placement ground truth. A fixed native-grid separable
binomial `[1,4,6,4,1]/16` lowpass is now a diagnostic opt-in, default off. It has
no decimation or coordinate change. Its complete two-quad support is included
in clipping/bounds and both views' spatial-role checks. The coarse original
search is unchanged; filter support checking there is conservative.

**MEASURED:** the lowpass arm accepts three original-pair receipts at two distinct
FIT sites; two agreeing source alternatives belong to the same site. Their RMS
pairs are0.276/0.379 and about0.245/0.297 quad, with reciprocal errors0.317 and
about0.19 quad. It still fails the measured connected graph and has no accepted
heldout observations. This supports alias/noise sensitivity at some patches,
not a default-filter decision, a global placement gain or a successful mosaic.

## Controls and next bounded search

Fresh direct controls-run-04 and controls-run-05 passed24/24. These include the
real native consumer on a known alias-contaminated translation (<0.2 quad point
and reciprocal errors), flat/unrelated-noise/pure-Nyquist negatives, complete
filter-halo clipping and heldout-boundary failures, repeated-site false-consensus
protection, and wrong/shuffled/reversed/unrelated source-ordinal controls.
The expanded-source negative tests four independent unrelated noise originals.
These controls establish mechanics; real full-output review is still required.

The next source search keeps at most four B originals per site: the learned
centre, centre plus/minus the measured FIT source-mapping RMS (rounded up, at
least one ordinal), and the guide witness. All remain inside the observed source
interval. Its candidate counts cannot replace independent spatial evidence.

The16-source streaming budget is also under review: it spaces chosen originals
21/30 acquisitions apart, while measured usable focus widths at retained
descriptors are2.4--4.4 frames. A deeper sweep can therefore lose the sharply
focused appearance of fine features before matching. Any expanded source census
must retain the2000-descriptor cap, one-original streaming and explicit memory
reservation, and must be compared through actual native/heldout consumers.

Exact commands, executable hashes, resource observations and exit codes are in
the adjacent generated `cached-geometry-command-index.md`. Host load was sampled
but these runs are not an isolated performance benchmark.

## Width-driven coverage replay

**MEASURED:** `mosaic-focus-coverage-01` streams128 cached originals per pass,
retaining1021/1080 descriptors under the2000 bound. Qualified focus coverage is
51602/51687 and17638/17878 pixels. The unresolved85/240 pixels and their source
intervals remain explicit in the receipt. The narrow width p10 values are
1.4903/1.5826 acquisition ordinals; this is focus-coordinate uncertainty, not
metric depth. Nomination produces57 reciprocal descriptor pairs and22 FIT-only
ordinal-conditioned seeds. These nominate214 native measurements; four distinct
descriptor FIT sites pass, with no accepted heldout or grid sites. The pass graph
remains disconnected. The matched native-lowpass arm on exactly the same frozen
candidates accepts only three FIT sites, still no heldout or connected geometry.
It does not justify enabling lowpass. Neither arm produces a photograph or a
placement-quality claim. Both use four workers, zero RAW decodes, at most
701124608 sampled private bytes and the explicit4GiB budget.

Actual affine image remeasurement is the next separately allocated, default-off
model experiment; see `affine-native-plan.md`. It must re-read original pixels
through its affine warp and preserve independent native/holdout/loop gates.
