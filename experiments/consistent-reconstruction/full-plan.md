# One unchanged complete-chip reconstruction observation

2026-09-25. Preparation authorized by root; no photograph has been run by this
author. This is a separately scheduled observation, not a passed general gate.

The unchanged generated method improves the independently registered contact
boundary while damaging focused glints and genuine far-coarse detail. The
four-test, twelve-case result remains `preservation_pass=false`,
`candidate_qualified=false`, `photographic_replay_admitted=false`. Its screen
SHA256 is `63ea41b7eb9be8bc6e8e4450c0649fddff87865773fdd69f76a1844203c59ac0`.
The fresh build must reproduce that screen exactly, not reinterpret or relax it.
The independent interpretation is in `independent-results.md`.

Root's reason for observing one photograph is the exercised contact improvement
and the existing complete-chip contact/duplicate-edge gap. That does not erase
the measured harms or predict a useful photographic tradeoff. No second norm,
filter, penalty, iteration limit, source weighting or stack transfer is included.

## Held consumer and one intervention

Use all 299 original `uncapped-IC-chip-cpl` sources in exact production order,
reference 149, full CFA-plane geometry 3516x2344, current crop
`[133,89,3250,2166]`, and final native output 6500x4332. The current map,
per-source camera/WB/levels/ISO, composed optical CA, rounded GPU gathers,
probed injected noise, seven-band default configuration and production chunk
association are held. There is exactly one canonical `BandWorker::fold` pass.
No aligned-source image volume is saved or allocated.

The only intervention is the already frozen solver applied separately to the
four actual resolved coefficient pyramids, including the terminal mean. It
minimizes the ordinary unweighted sum `||A X - C||²` in camera DN across every
coefficient, with actual finite analysis A, exact-transpose implementation,
fixed `S Sᵀ` preconditioner, 32-iteration cap and 0.02 DN RMS numerical bar.
The correction system and final full objective checks are unchanged. The bar
is an exact-linear error bound qualified by generated f32 oracle controls; it
is not an interval enclosure of arbitrary floating-point errors.

Targets C, canonical weights, corrected accumulators and input bounds remain
held. Reanalyzed candidate bands, terminal value, image mean and brightness
are not promised unchanged. The candidate receives the same actual InputRange
hull before the existing one-time MHC and color development.

## Evidence and refusals

First finish and write the actual canonical output before resolved-C extraction.
It must match the bound current production baseline's complete decoded RGB16
and ICC. Resolve its automatic tone once, and prove a literal pinned-tone rewrite
has identical complete RGB16/ICC. Then extract, hash and save C and hash canonical
state/hull. Finish the untouched canonical merge again and write through the
same pinned writer. Its **whole TIFF bytes** must equal the pre-extraction pinned
rewrite. Save both images and the observer-placebo receipt. Candidate synthesis
has not started during this observer test.

`canonical-coefficients.f32` holds complete plane-major, level-major f32 C;
the JSON sidecar gives every extent, byte offset, size, hash and RAW-development
binding. This O(image) cache reproduces the solver input without another RAW
pass. It contains pre-hull C, not a replacement hull or source volume. Actual
canonical/cache planes, source CFA/gather/guide/variance/weight/coefficient
hashes and before/after target/accumulator/hull hashes are retained separately.

Each of four solves writes its diagnostics immediately, including a refused
last-iterate hash. A candidate requires all four planes to converge with no
refusal, finite valid image, nonincreasing full objective and the unchanged
numerical bar. A numerical refusal returns a successful diagnostic test with
`status=NUMERICAL_REFUSAL`, saves all available solver records, and writes **no**
candidate TIFF or plane cache. It never renders a partial subset, refused
iterate or baseline placeholder. Success uses `status=OBSERVATION_COMPLETE`;
neither status means image-quality qualification.

The candidate uses exactly the baseline's actually resolved development. Its
resolved metadata and ICC must remain identical. Source stamps and map hash
are rechecked at completion. Root's bounded runner verifies actual cache data,
complete file hashes, fresh compile/source bindings and the preserved generated
screen; the author does not run builds or RAW work.

## Decisive photographic review

Root limits the entire full process to 16 GiB private bytes, 1800 seconds wall
and 12000 CPU seconds, retaining normal progress and numerical refusals. These
are operational limits, not a speed claim. The single canonical pass costs the
existing complete-source work; no performance gain is presumed for the new
global solve.

Deliver baseline and candidate complete TIFFs, full JPEGs and whole-image
overviews, plus all 25 fixed native target pairs from
`experiments/chip-stock-selectivity/targets.json`. Do not rechoose coordinates,
scale or omit difficult pairs. Review the whole image first, then contact
plumes/duplicate edges, scratches, branches, gaps, dark texture and color at
the frozen targets. A useful contact cleanup must remain visible without
unacceptable loss of real detail or new color/glint damage. Lower coefficient
residual is not a quality score: projection can erase genuine multiscale
structure and already did so in the generated near/far case. Sharpness energy
is not an acceptance criterion.

## Root integration

The new adapter is a sibling of the frozen generated module. It calls
`consistent_reconstruction::operator`, existing donor/real-source-contributions
core accessors, existing production chunk helpers and the held writer. No
generated or shared source is edited by this author.

```rust
#[cfg(all(test, feature = "native-direct-planes", feature = "native-correction-variance", feature = "native-gpu-gather"))]
mod consistent_reconstruction_full {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/consistent-reconstruction/full-adapter.rs"));
}
```

Root's explicit config env is `STREHL_CONSISTENT_RECONSTRUCTION_CONFIG`;
the ignored test filter is
`merge_cmd::consistent_reconstruction_full::complete_pair`. Config uses the
existing chip full-adapter fields, `phase=full`,
`mode=consistent-reconstruction`, and
`tone_policy=automatic-baseline-then-exact-pinned-candidate`.
The separately owned `full-run.py` must bind this adapter/plan plus the existing
generated files, reused compiled includes and fixed target file before build.
