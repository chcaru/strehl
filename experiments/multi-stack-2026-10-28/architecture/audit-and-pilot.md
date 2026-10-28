# Multi-stack architecture audit and geometry pilot

Base audited: origin/main c149e52834fc1c86c2af0fe022713c39fa25f33c. VERIFIED means source was read, not an experiment. ARGUED identifies proposed design. No build/RAW campaign or product edit was performed by this lane.

## Main recommendation

Add an opt-in session preparation route feeding existing merge consumers. Preserve the ordinary one-directory route and arithmetic. A session has ordered passes; each pass may contain multiple ordered segment directories (the marigold .1/.2 captures are continuations, not independent repeats). Keep pass, segment, local frame and global frame identity separate.

One common solve must use all direct intra- and cross-pass measurements in the anchor gauge, with smoothness only inside each pass's original adjacency. Geometric registration is not proof of same-focus equality. A combined-focus/aligned-layer consumer is useful before the stronger repeat-denoising contract is established.

## Verified current source seams

| Area | Source and finding | Consequence |
| --- | --- | --- |
| Input | strehl-cli/src/lib.rs raw_paths; merge_cmd.rs run_pyramid | One directory and sorted paths; leave old branch unchanged. |
| Calibration | run_pyramid, PreparedPyramid, load_frame_impl_observed | Frame0 supplies geometry/levels/ISO/WB/matrix/noise; subsequent frames check geometry and levels. Validate session calibration explicitly. |
| Metadata | strehl-raw/src/sony-optical.rs read; identity.rs identity | Own existing readers expose ISO, exposure rational, aperture, dates and gear; no decoder-source inspection needed. |
| Alignment storage | align_cmd.rs decode_stack_observed and measure_edges_traced | Retains full f32 green plane and pyramid for every frame; O(N) memory before merge planner. |
| Pair refinement | core/align.rs fit_stage_observed | Public API accepts a seed and full-plane views, but correlates selected tiles only. |
| Solve | solve_global_in_component | Correct measured-component policy exists; smoothness triples still follow flattened indices. |
| Cache | sidecar_path, solve_config_key, StackIdentity::from_paths | Directory/config hash and name/size frame identity do not bind session layout or duplicated content. |
| Merge | PyramidFrameSource, PreparedPyramid, BandWorker::prepare_observed | Reuse actual decoded-CFA test and production consumers. |
| Merge memory | canonical_band_chunks; run_pyramid_prepared_with_sensor | Canonical chunks execute serially through reusable workspaces; row operators parallelize. Proposal's simultaneous worker accumulator estimate is stale. |
| Desktop | jobs.rs StackScan/RenderRequest; workspace-history.rs Run/StackDraft | Single source PathBuf plus retained frame identities; add immutable session snapshot and bracket ranges with serde defaults. |
| Resources | jobs.rs MachineResources | Existing logical CPU and Windows RAM detection can inform execution/cache budget. |

Do not change MEMORY_BUDGET_BYTES merely to increase utilization: it sets canonical reduction grouping and can move image bytes. Introduce a separate execution/cache budget and keep old arithmetic partitions. Dense Cholesky also has O(N^2) memory and O(N^3) work; preflight it for large sessions.

## Concrete geometry pilot with existing APIs

1. Resolve explicit pass/segment frame lists and identities. Decode each source once, cache original active u16 CFA outside captures, and build a box-averaged green guide. Preserve active geometry, levels, CFA phase and source hash in cache metadata. A native-cache identity must bind bytes/parameters, not just a filename.
2. Use PlaneRef::from_geometry, downsample and AlignPyramid::build. Integer downsample factor keeps guide max side <=1024; 512 is a cheap candidate-screen option. Retained guide memory is budgeted; cache/LRU beyond that bound.
3. Intra-pass edges keep multiscale direct ladders including short edges. Across candidate passes, first probe a fixed distributed focus-index matrix (e.g. 7x7), retaining competing candidates and spatial coverage. Do not use one fixed reference or infer true focus equality from low residual.
4. Measure guide candidates with tile_grid and align_pair_observed. Guide placements only seed full-resolution measurement. Read just the selected pair's u16 CFA from cache, generate green planes, and refine through public fit_stage_observed(reference,moving,tile,&spots,radius,Some(seed.to_params()),&cfg,observer). Candidate full-resolution settings: tile128, grid12x8, radius6, margin96, warp_tiles=true; commission these, do not treat them as established bars.
5. For re-seeding, fit_stage_iterated is private. Add a small public seeded-refinement wrapper around fit_stage_iterated_impl with identical convergence/refusal tracing. Avoid copying its logic into production. A pilot may temporarily iterate public fit_stage_observed and retain every pass receipt.
6. Use AlignEdge::from_stage(global_i,global_j,&fit). Build one graph of actual full-resolution direct intra/cross edges. Report graph_stats and anchor-component cycle rank; solve_global_in_component then rebase with placements[anchor].invert().then(placements[k]). Never deliver a composition of independently fitted pass reference poses.
7. Before the explicit-track API exists, pilot smooth=0 is honest and safe but must be labelled. Final feature must use per-pass original-adjacency smoothness; no boundary rows.
8. Score per-frame placement in the delivered anchor gauge using held-out full-resolution spatial sites distributed over depth. Fit RMS and leave-one-edge-out among near-duplicate edges are diagnostics, not independent placement truth.

Bound full-green storage to two pair planes plus bounded source-cache/decode workspaces per worker. Group pairs by shared source so one decoded/cached green plane services several edges. Use a bounded LRU keyed by source identity; serialize pairs into batches whose unique source set fits budget. Cache original u16 CFA once to avoid thousands of repeated RAW decompressions. Low-res guides and cached raw samples must not be mistaken for aligned volumes.

### Guide-to-full coordinate lift

The box decimator truncates dimensions; guide sample x represents full-plane block centroid s*x+(s-1)/2. Define d = s*Cguide + (s-1)/2 - Cfull in each axis. For equal scale factors:

    a_full = a_guide
    b_full = s*b_guide + d_moving - a_guide*d_reference

Complex multiplication follows core Similarity. Simply scaling b omits the center offset. Commission odd dimensions, nonzero scale/rotation and half-pixel offsets; refinement recovering a seed bias does not prove the lift was correct.

### Controls

Before actual pilot interpretation: curved focus tracks with pass offsets/reversed order/unequal steps; zero self-pair; known scale+rotation+translation lift; wrong seeds/shuffled cross pairs; disconnected pass retained as refused even with smoothing; boundary jump untouched across tracks; real graph cycles; repeated-texture distractor; depth-dependent viewpoint warp rejected at distributed sites. Record raw tile refusals and accepted edges, not only final map.

## Proposed additive core APIs

Keep solve_global_in_component as a wrapper supplying the original adjacent triples in original order. Add solve_global_in_tracks(edges,n,options,reference,tracks) -> Result<Placement,TrackError>. Tracks are ordered global indices/ranges; validate range, uniqueness and nonoverlap. Include only triples entirely in the measured anchor component, never compress missing frames. Use identical triples for row assembly and IRLS penalty reweighting. A singleton track adds no prior. One-track comparison must be bit-identical.

Add refine_pair_observed(reference,moving,spots,cfg,seed,observer) -> Result<StageFit,AlignFailure>, delegating to fit_stage_iterated_impl using cfg.fine_tile/radius. Existing align_pair callers are unchanged.

Cache ownership belongs in CLI. A bounded cache API should return an immutable source plane handle (Arc or scoped borrow) and account for original u16 bytes, f32 working plane bytes, guide pyramids, concurrent decode scratch and solve matrices. Pin both pair handles before releasing the budget guard; no eviction of a borrowed plane. Read-only cache records validate active bounds and identity before use. Expose high-water accounting for experiments.

## Session and consumer contract

Manifest: version, ordered passes, each with label/intent/direction and ordered segments/frame limits; requested consumer; anchor; cache/resource/matching settings. Relative paths resolve against manifest. Canonical paths detect duplicate directories and unsafe output placement. All pass/segment identities are retained in run snapshots and diagnostic frame mapping.

Cache envelope: session schema and algorithm generation, ordered canonical paths and frame identities, pass/segment boundaries, direction, role, pairing config, anchor, estimator/refinement config, resampler, photometry/noise policy and all solver environment inputs. Embed current exact WarpMap format rather than changing legacy map parsing. Explicit maps require the same checks. Filename+size is not adequate to certify independent acquisitions: hash duplicated-size candidates and reject repeated content from noise-gain counts.

Validate body, dimensions/CFA, levels, ISO, exposure, aperture and WB/light assumptions before fusion. Aligned layers preserve separate photometry. Repeat fusion cannot silently classify changes as noise. One-bracket session can delegate to ordinary stack for exact compatibility.

Repeat reduction: proposal g/K and RN*sqrt(K) is correct only for fixed equal independent samples under one model. Local gating/heterogeneous weighting needs y=sum(w*x)/sum(w), var(y)=sum(w*w*var)/sum(w)^2. BandMerge::add_frame_with_gain already accepts per-pixel luma variance. Reduce one group in bounded memory or reread for its agreement pass; never store K aligned frames.

Per-warp band beta must be propagated with squared weights/variance; taking an unweighted mean beta is not generally valid. Spatial admission adds covariance and data-dependent weights can bias noise. Commission the actual grouping consumer on independent flat noise, duplicate noise, blur mismatch, motion, clipping and half-step interleave. Unknown focus equality stays separate inputs; do not invent repeat gains.

Aligned layers share one joint geometry and common output domain, but fold each pass independently through CFA and retain a linear master each. Do not stack each pass to TIFF and register those TIFFs again. Session source attribution remains per-original source even when the reducer groups frames.

HDR needs radiometric gain, clipped support and propagated variance before focus weighting; the current base mean does not recover saturation automatically. SR requires original source CFA phase before gather; it is a separate reconstruction consumer. Mosaics require coverage-aware multiscale operators/depth+visibility; cover_or_explain currently computes an intersection, not a union canvas. Keep unsupported modes explicit rather than reachable no-ops.

## Regression and performance

Compare old single-directory and one-pass-session whole TIFF+master hashes at fixed resolved settings. Test actual prepared-CFA/BandWorker/BandMerge paths, not only reducer arithmetic. Old catalogs deserialize without session fields; retained revision identity and timeline must not change when draft pass ordering changes. Source-range repairs need stable pass-local mapping. Temporal-energy mode assumes a single dense ordered bracket and should refuse sessions until its neighborhoods become pass/focus-aware.

Separate memory limit from canonical sum order. Benchmark decode cache, guide screen, full-res refinement, global solve, merge and write times independently; alternate resource settings, record host load/peak committed memory and pair exact output hashes with timings. CPU decode/cache prefetch and existing row parallelism are the first optimizations. GPU is optional only after correspondence controls and measured benefit.

## Reading and commands

Read README/CONTRIBUTING, architecture sections7/9, SYNTHESIS3.1-3.3 and amendments, engineering rules1-13/16, capture reference, and M-FRC-VIABILITY. The latter requires input-only focus equality beyond geometric coincidence and identifies shared-processing/fixed-pattern confounds.

Commands run from feature worktree:

    python scripts/research.py search repeat focus --limit 5
    python experiments/ORCH-drift-check/prior_art.py focus pairing repeat

Search locators: M189-repeat-referenced-detail, M70-through-focus-spectrum, M69-focus-noise-sd, M6-residual-halo-measured. No novelty/absence claim follows. All source inspections were Get-Content/rg against this base.
