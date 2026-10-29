# Native mosaic pilot 01: nomination failure and correction

## Measured failure

Root ran the frozen binary-06 executable, SHA256
`5daf8d5437484da32b53e12f33af3679ae8037d4250688fbbf1fddc4be4c22d6`, with:

```powershell
outputs/multi-stack/completion/binary-06/strehl.exe session stack outputs/multi-stack/completion/mosaic-native-pilot-inputs/pilot.json --out-dir outputs/multi-stack/completion/mosaic-native-pilot-01 --cache outputs/multi-stack/completion/mosaic-source-cache --memory-limit-gib 48 --threads 16
```

`STREHL_WARPMAP` named the isolated output's `legacy-warpmap.txt`. The authoritative
command, process and host receipts are in
`outputs/multi-stack/completion/mosaic-native-pilot-run-01/`. Exit was 1 after
51.6695 seconds, sampled peak private bytes 5,532,483,584. This is a commissioning
run, not an isolated performance claim. It produced no photograph or completion
receipt; the refusal was a disconnected measured view graph.

Both per-pass alignments and focus exports completed. The first pass placed 15
of its 17 originals; the second placed all 17. Source ordinals 0 and 1 in the
first pass remained outside the measured anchor component. Its complete-census
focus rule therefore marked every focus pixel unusable. The second pass had
118,353 usable pixels in its 879 by 586 diagnostic guide. These sparse inputs
skip about 21 or 30 original focus steps per retained acquisition; they are not
equivalent to the complete 339 and 488 acquisition sweeps.

`mosaic-candidates.json` contains 729 and 692 detector features, **zero** reciprocal
ratio matches, and no coarse seed. `mosaic-native-measurements.json` is empty.
Thus the immediate refusal occurred before native refinement or mesh tests.

## Bounded independent diagnosis

Root authorized one-source-at-a-time existing-cache inspection, at most four CPU
threads, without RAW decoding. The command actually run was:

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/completion/mosaic/inspect-pilot-guide.py --pilot outputs/multi-stack/completion/mosaic-native-pilot-01 --cache outputs/multi-stack/completion/mosaic-source-cache --out outputs/multi-stack/completion/mosaic-pilot-analysis-01
```

It exited 0 in about 5.7 seconds with zero RAW decodes. Every per-source accepted
pixel count matched the production guide receipt exactly. The independent NumPy
guide construction is diagnostic; floating-point bit equivalence to production
is not asserted. Saved PNGs are display-transformed orientation images, not
quality evidence or final pixels.

The two guides visibly retain overlapping flower regions but also severe sparse
focus-selection terraces. An independent OpenCV SIFT call on these guides found
29 reciprocal matches with the same 0.75 descriptor ratio. A 6-guide-pixel robust
similarity had only nine inliers, six in fit blocks and three in held-out blocks
before footprint guards; none survived the existing all-block-boundary guards.
This establishes some recognizable overlap. It does **not** establish accepted
native geometry, qualified cells or a successful panorama. The external matcher
was used only as a diagnostic; its implementation was not read or copied.

## Implementation correction awaiting fresh verification

The original Harris detector used a fixed descriptor radius and only octave
changes. [Lowe's scale-space paper](https://www.cs.ubc.ca/~lowe/papers/ijcv04.pdf)
provides a better-supported nomination design: localized extrema across spatial
scale and stable gradient orientation, followed by an interpolated descriptor.
The new Rust implementation follows the published equations without importing
external implementation source.

More fundamentally, geometry now streams diagnostic guides from separately
observed originals instead of detecting features on focus-composite terraces.
At most 16 originals per pass are nominated from the recorded regularized focus
witnesses. Their scale-space features retain the actual acquisition ID and map
through that acquisition's inverse pose into the independent pass gauge. The
pool retains at most 2,000 descriptors per pass and discards each intensity guide
before loading the next. Final-image rendering still consumes every placed
original. Spatial holdout support includes the descriptor and finite Gaussian
dependency footprint. It does not silently relax the native, reciprocal-loop,
held-out-error or Jacobian bars.

The consumer now saves its actual bounded composite diagnostic TIFF and mask
even when geometry refuses, plus directional ratio counts and per-original
detected/retained feature counts. New controls plant rotation, noninteger scale,
subpixel displacement and brightness gain; existing flat, unrelated and repeated
texture negatives remain. Separate controls reject a wrong-pass source witness
and verify the pass-gauge footprint transformation. Root schedules the fresh
compile, controls and next native run. No positive photographic or performance
claim follows from this source change alone.

## Causal reservation control

The first root-scheduled fresh compile succeeded, but `session-expanded-09`
exposed two real positive-control failures in the new detector. The transformed
texture retained 198 and 254 guarded features but only six reciprocal matches,
three in fit blocks. Flat, unrelated and repeated-pattern negatives passed.
The other twelve suite failures were filesystem publication failures under the
sandbox, separately handled by root; they do not explain the detector failures.

The spatial reservation had unnecessarily discarded dependencies crossing a
boundary between two **fit** blocks. It now admits a feature only if its entire
finite dependency square occupies a single role, allowing fit-to-fit boundaries
while continuing to exclude every fit-to-held-out boundary in both directions.
A new exhaustive sampled-footprint control asserts that no accepted opposite-role
dependency squares overlap. Rotation of the dependency square uses the inverse
similarity matrix's row L1 norm, rather than its smaller radial scale. A negative
control exposes this distinction at a 45-degree rotation. The source pool also
enforces its global capacity when the configured feature limit is smaller than
the number of nominated originals. The required eight fit matches and all native
geometry thresholds remain intact.

Root then ran `cargo test --locked -p strehl-cli session_ -- --nocapture` with a
fresh **Compiling** line; `cli-expanded-10` records exit 0 and **83 passed**, zero
failed. Both formerly failing positive controls passed, as did the flat,
unrelated, repeated-pattern, wrong-witness, pool-cap, rotated-footprint and
opposite-role nonoverlap controls. This verifies the mechanics of the correction.
The next native pilot remains the test of usefulness on the recorded captures.

## Pilot 02 and distributed measurement nominations

Root ran the same manifest/cache/resource settings with frozen binary-08,
SHA256 `b482a70159d7c6e402f4f9fa4a83466002a5a6fee58689037c235b57187a5950`,
to `mosaic-native-pilot-02`; its authoritative command and host receipt is
`mosaic-native-pilot-run-02/receipt.json`. It exited 1 after 35.5175 seconds,
sampled peak private bytes 5,504,065,536. Both independent alignment caches were
verified and reused. The source pool retained 122 and 128 features from 15 and
16 original guides and found three reciprocal fit-role matches. No native
measurement ran because the coarse descriptor count could not establish a seed.
No photograph, complete output or accepted geometry is claimed.

The bounded diagnostic command actually run next was:

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/completion/mosaic/inspect-source-features.py --pilot outputs/multi-stack/completion/mosaic-native-pilot-02 --cache outputs/multi-stack/completion/mosaic-source-cache --out outputs/multi-stack/completion/mosaic-source-feature-analysis-01 --sources 5 21
```

It read two existing cached originals, never decoded RAW, and used at most four
threads. On their linear box guides, the external diagnostic detected 543/591
features and 20 reciprocal matches, of which 18 supported a 6-guide-pixel coarse
similarity. Restricting features to diameter at least four guide pixels reduced
this to 199/226 features and 15 matches (12 inliers). A square-root contrast arm
had 24 matches/21 inliers across all sizes, but only 13/9 after the same size cut.
These arms implicate omitted small spatial scales more strongly than a need to
adjust the contrast threshold. They do not certify native placement. Raw cached
guide TIFFs, display PNGs and exact source hashes accompany that receipt.

The next implementation restores the half-guide-pixel octave and raises its
explicit scratch reservation. More substantially, a coherent set of three
descriptors may now nominate an **unverified search transform**. That transform
only nominates distributed grid points and their actual original witnesses.
Each grid point receives one direct box-decimated original-green NCC search and
then the same full-native forward/reverse refinement. At least eight accepted
native fit observations are still required before any measured pass edge or
extended canvas exists. Held-out and loop/Jacobian checks remain separate.

Observed per-iteration correlation footprints now verify spatial role membership
for every executed coarse and native search. Both images must reserve the same
role: assigning a pair to held-out merely because one image was held-out could
otherwise let its other-image footprint overlap a training observation. A
candidate that leaves its reserved role is refused. New controls exercise the
actual coarse-plus-native path with correct, wrong-shift and unrelated-noise
proposals; three even-perfect native observations cannot establish a view edge.
Root's fresh `cli-expanded-11` run of
`cargo test --locked -p strehl-cli session_ -- --nocapture` exited 0 with
**86 passed**, zero failed. The actual coarse/native correct, wrong-shift and
unrelated-noise tests, cross-view role-footprint refusal, three-perfect-point
edge refusal, scale/rotation positive, and periodic-alias negative all passed.
The next real pilot is scheduled by root; these mechanical controls alone do not
establish a useful mosaic.
## Pilot 03: native refusal is now measured

Root ran the same command with frozen `binary-09/strehl.exe` (SHA256
`07b86a0aaad92686d0936c0f72d09bbfaaf9d11e867ecbcf61ae9a699b2756f4`),
changing only the output to `mosaic-native-pilot-03`. The command, explicit
48 GiB/16 worker configuration and host sampling are recorded in
`mosaic-native-pilot-run-03/receipt.json`. It exited 1 after 43.5647 seconds;
sampled peak private bytes were 4,670,566,400. This is not an isolated speed
comparison.

The restored fine octave produced 512/583 retained original-source features,
19 reciprocal descriptor matches and five coherent fit-role nominations. Their
unverified seed RMS was 5.7644 full-native quad pixels. Thirty candidates reached
the native-receipt stage. Eight failed the native residual bar, seven were
outside the coarse nomination support, four had incompatible spatial roles,
six lacked enough coarse correlated tiles, two coarse patches left the image,
and two lacked enough native correlated tiles. One held-out descriptor point
passed (forward RMS 0.3240 quad, reciprocal error 0.0742 quad). No fit point
passed; refusing a connected view graph is therefore correct.

The saved refusal currently omits measured residual magnitudes and surviving
tile coordinates. A cached-only observer is prepared to retain these actual
production-consumer quantities before changing the local model. It uses saved
candidates and original u16 cache entries, never RAW decoding or an alternate
merge. The sparse 17/339 and 17/488 commissioning census also leaves large focus
steps; its chosen source pair can differ in defocus even where a full sweep has
adequate focus coverage. This is a hypothesis to distinguish using the complete
827-source focus/geometry run, not a reason to relax the native or holdout bars.
## Cached native replay and next full-density test

Root authorized one four-worker cached-only replay. The exact harness links to
frozen binary-10's CLI/core libraries; `mosaic-native-replay-build-02` records
library fingerprints and SHA256 values, the harness hash and executable hash
`57999046d2bcaa289e4ce9648d79cfc511c9bbc54fd650828c84459ff460cbbe`.
The initial direct link omitted ThinLTO and failed; build-02 restored the
workspace's ThinLTO/codegen settings and exited 0. Both logs are preserved.

The executed command, also in `mosaic-native-replay-run-01/receipt.json`, was:

```powershell
outputs/multi-stack/completion/mosaic-native-replay-build-02/native-replay.exe outputs/multi-stack/completion/mosaic-native-pilot-03 outputs/multi-stack/completion/mosaic-source-cache outputs/multi-stack/completion/mosaic-native-replay-build-02/observations.json
```

It calls `SourceCache::load` only, refusing a missing or stale cached original;
there is no decode path. It replays the seven failed descriptor cases and the
accepted held-out control through the same `refine_pair_observed` config,
spots and original-green plane coordinates. It records all actual attempted
fine-stage tile probes, offsets, peaks, keep masks and residuals. Exit 0 was
recorded in 1.093 seconds, under a four-worker pool. Resource polling missed most
of this short process; its sampled peak is not a reliable memory measurement or
performance claim. Root was running small unrelated mechanics controls.

Measured forward/reverse RMS values on the seven refusals are respectively:
0.919/0.973, 2.778/1.881, 0.634/0.664, 1.007/0.807, 0.553/0.884,
1.085/1.051 and 0.542/0.490 quad pixels. Their reciprocal loops are mostly
0.03--0.22 quad; one is 0.58. The accepted control remains 0.324/0.305 with a
0.074 quad loop. This is evidence of locally inconsistent displacement fields,
not merely missing descriptor candidates.

A read-only affine least-squares diagnostic was then run with:

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/completion/mosaic/inspect-native-replay.py outputs/multi-stack/completion/mosaic-native-replay-build-02/observations.json outputs/multi-stack/completion/mosaic-native-replay-build-02/affine-diagnostic.json
```

It fits the same selected observed tile displacements; it does not rerun image
measurements or admit geometry. Only one formerly refused fit-role point gets
both affine residuals below 0.5 quad (0.399/0.430); its leave-one-tile-out RMS is
0.683/0.720. An affine switch cannot establish the missing eight reliable native
fit points and is not justified as a fix by these data. Native acceptance bars
and the production local model remain unchanged. Root approved the next test as
the complete 339+488 acquisition census to investigate focus-density limitations.

The production observer now retains selected-stage measurements even on a
refusal and checks the bounding support of every attempted search against actual
original green clipping and bounds. It uses the estimator's f32 predicted tile
centers, including bilinear taps and complete coarse box footprints. A control
plants clipping beyond the nominal seed radius but inside a later iteration's
query. The exact identity guide specialization removes unnecessary bilinear
address arithmetic, and Gaussian passes parallelize independent rows without
changing per-pixel reduction order. New controls compare guide bits and complete
feature coordinates/descriptors/order with one and four workers. These changes
are frozen for root's next fresh compile/test; numerical and full-density results
remain pending.
Root subsequently ran `cargo test --locked -p strehl-cli session_mosaic --
--nocapture` with a fresh **Compiling** line. Receipt
`mosaic-expanded-controls-03` records exit 0 and **19 passed**, zero failed.
The identity box exactness control, one/four-worker complete feature equality,
and later-iteration clipping/receipt-roundtrip control all passed. The full
339+488 density experiment remains the next photographic-usefulness test; these
controls establish mechanics and preservation, not a successful mosaic.

## Complete 827-source census and cached replay commissioning

**MEASURED:** `mosaic-full-run-01/receipt.json` records the actual command:

```powershell
outputs/multi-stack/completion/binary-11/strehl.exe session stack outputs/multi-stack/completion/mosaic-native-pilot-inputs/complete-827.json --out-dir outputs/multi-stack/completion/mosaic-full-01 --cache outputs/multi-stack/completion/mosaic-source-cache --memory-limit-gib 48 --threads 16
```

The isolated `STREHL_WARPMAP` is in the receipt. Binary SHA256 is
`bd41dd5f06d75c4afdb5ce5373c15c565487a0d4dd6865c136ebf5a5573c5610`.
The run exited 1 after 1675.036 seconds, with sampled peak private bytes
18,279,268,352. This is a campaign resource observation, not an isolated speed
claim. Independent pass alignment placed all 339 and 488 frames, using 1841 and
2913 measured edges, with cycle ranks 1503 and 2426. Both passes have one
connected component. No photograph, master or accepted mosaic geometry exists.

The two 879-by-586 guides each cover 499100 pixels. Usable focus evidence covers
51687 and 17878 guide pixels. The old source nominator retained mostly neighboring
acquisition ordinals: pass 0 chose many sources 200--209; pass 1 chose sources
607--624 (global IDs, mostly local 268--285). This reduced the retained source
features to 290 and 193, with seven reciprocal descriptors and three coherent
fit-role seed nominations. Nineteen native receipts contain zero accepted
correspondences. Four fail the native residual bar; four mix reserved spatial
roles; the remainder fail coarse/native tile support or bounds. The four native
forward/reverse RMS pairs are 0.878/0.729, 2.830/1.665, 1.487/1.277 and
3.168/5.396 quad pixels. High patch peaks alone did not certify placement.

**DERIVED:** selecting the greatest whole-image source support repeatedly picked
the same region's neighboring focus frames. The revised bounded nominator
maximizes marginal spatial-bin coverage and enforces acquisition separation;
this changes nominations only. All descriptors and native measurements still
come from the named original sources. Root's fresh `mosaic_` controls-05 passed
23/23 outside the sandbox. The earlier controls-04 had two filesystem access
failures; its causal source-diversity control passed. The planted control gives
sixteen neighboring sources a dominant region and one other source a smaller
unique region: the old selection loses that region, and the revised selection
retains it without exceeding the source quota.

**VERIFIED:** the bounded cache reconstruction ran:

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/completion/mosaic/rebuild-cached-guides.py --pilot outputs/multi-stack/completion/mosaic-full-01 --cache outputs/multi-stack/completion/mosaic-source-cache --out outputs/multi-stack/completion/mosaic-cached-guides-01
```

Receipt `mosaic-guide-rebuild-run-01` records exit 0, four workers, zero RAW
decodes, 46.361 seconds and 295,989,248 sampled private bytes. It verifies focus
file bindings, source cache headers and payload digests, original source IDs,
and exact production intensity/source-witness guide hashes. Both match the
original full run, with zero differing intensity bits. Guide hashes are
`80ef51e6abe53b492e4be39e69e495a0471638b65db1bc4c05c9920d471ec621`
and `1dc3d28ed249ae6f60bd8a8fdd3b4c1210d3f6a809726059007b6fed6d49a736`.
The compact guides retain intensity, support, focus ordinal/width and all four
original source witnesses. The next replay uses the production feature and
native paths with strict cache-only entry points; a missing cache entry is an
error, never an implicit RAW decode. Acceptance bars remain unchanged.
