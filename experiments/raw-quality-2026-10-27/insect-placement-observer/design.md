# Existing fine-alignment observations, without a new fit model

2026-10-27. **VERIFIED source / proposed instrument only.** Read the [prior insect audit](../../raw-quality-2026-10-26/insect-warp-audit.md), actual `align.rs` and `align_cmd.rs` call paths. No Rust edit, build, RAW read or numerical execution. This allocation retains evidence from one unchanged complete299-source alignment; it neither installs a field warp nor claims placement or photographic improvement.

## Smallest change

Keep existing public APIs and ordinary callers. Add an optional fine-stage callback through the same core stage/iteration/pair implementation; existing APIs supply `None`. It copies already computed measurements, residuals and decisions. It must not call NCC, fitting, residual evaluation or the solver again. Coarse alignment remains unchanged; a pair that never reaches fine alignment records its existing failure reason/level.

A test-only CLI adapter invokes the existing `measure_edges_observed` loop with optional per-pair trace collection. No product environment knob or new alignment configuration. Each Rayon pair owns its small trace; collect once per completed pair, then sort by the predeclared pair ordinal for serialization. Keep the existing edge collection and reduction order. No observer file I/O occurs inside NCC or fitting. The adapter writes a create-new deterministic JSONL plus a complete receipt after fitting, and saves the ordinary map only to its isolated output directory.

## Retained population

For every requested pair, including missing pyramid/plane and coarse failures, retain pair ordinal, reference-frame i, moving-frame j, literal outcome and the selected fine-pass index if any. Every attempted fine pass retains:

- Its index, actual optional seed parameters and f64 bits, guide dimensions, tile size/radius, relevant config, and whether warped-tile NCC was actually used.
- Every tile in original grid order: ordinal, origin, exact fitting centre and centred offset, predicted displacement copied from its actual `TileProbe`, complete `TileMeasurement` status/contrast/dx/dy/peak, and the corresponding `Observation` when one exists.
- Initial fit, residual and outlier cutoff/mask from the existing arithmetic, final fit and survivor residuals when evaluated. Use an explicit not-evaluated state for early refusal; never encode it as a rejected false mask.
- Stage result, census, termination cause and whether this pass supplies the returned pair fit. A failed later pass remains recorded even when the previous successful pass is retained.

Finite numbers may have human-readable values, but all floating fields retain their original f32/f64 bits. Failed measurements contain genuine NaNs; JSON stores null plus bits, never fabricated zeros or nonstandard NaN tokens. This instrument does not retain complete NCC surfaces or invent unavailable integer peaks/curvature scores.

## Coordinate contract

The actual guide is `green_luma`: the mean of the two individually black-subtracted, nonnegative greens per active2x2 CFA cell. Guide index(u,v) has active-native centroid(2u+.5,2v+.5); displacements scale by2 with no origin addition. These guides are not the original independent G1/G2 observations, and swapping G1/G2 would be an ineffective foil.

In `fit_stage`, the fitting centre is literally `(tx+tile/2,ty+tile/2)` and the plane centre is `(width/2,height/2)`. This differs from the template's sample-support centroid by half a guide pixel. Preserve the actual convention. Pair measurements describe reference i to moving j; the fit displacement is `(ax+g*ux-rot*uy, ay+rot*ux+g*uy)`. For warped NCC, the recorded displacement already contains the seed and the residual carried into moving-guide coordinates. Do not reinterpret it as an anchor149 displacement.

The complete receipt binds the resulting anchor149 pull map, sorted original identities, all299 placement states and actual active geometry. Later analysis may map a source-i coordinate through the inverse of that source's stored anchor-to-source pull. It must not assume the same grid ordinal in different reference frames denotes the same physical subject point.

## Size, controls and release boundary

Current defaults are `AlignConfig::deep`:128-guide-pixel tiles,12x8 grid, margin96, one fine pass, separable peak, unwarped tiles; ordinary spans are1,2,4,8,16,32,64,96,128. For299 sources this is2340 requested pairs and at most224640 fine-tile rows. The held log measured2314 successful edges; that is historical context, not a required new acceptance count. Traces should be tens of MiB; cap trace allocation256MiB and serialized output512MiB, refusing incomplete export rather than dropping tiles. The existing299 green guides alone are about9.85GB. Root should budget the actual normal alignment, not infer a small job from the trace size.

First commission on/off/count/full observation against identical small producing inputs: exact edge/result bits, original guide hashes, refusal census and selected-pass accounting. Include flat/coarse refusal, ordinary successful geometry, outlier rejection and the physically commissioned fixed-geometry defocus/non-similarity witnesses owned by photo-review. A guide-phase foil must misplace a green or substitute another channel, not swap the averaged greens.

For the single real run, compare all parsed placement bits/states against the held299 map only if configuration/input provenance agrees. Predeclare four additional on/off pair checks `(0,1),(104,105),(148,149),(0,128)` using the already decoded guides; no extra RAW decoding or second complete alignment. Record these extra checks separately from the2340-pair census. Root chooses final job bounds; a300s/1200CPU-second/16GiB starting envelope is a proposal informed by the old20.9s decode plus106.6s edge measurement, not a speed guarantee.

Interpretation remains limited: tile NCC displacement can change with defocus, occlusion and texture. Same physical field regions across already measured sliding focus pairs are necessary to test a field term; aggregate3.3588-guide-pixel residual is not a hair-placement error. If crossed field/focus support is absent, record unidentifiable and stop. No richer map or full-stack render follows automatically from a complete observation receipt.
