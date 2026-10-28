# Independent stage1 highlight-location review

2026-10-27. **VERIFIED source/metadata review only; no pixel measurement, RAW decode, fit or correction by this reviewer.** No blocker was found for root's tiny retained-output accounting pass. This is stage1 of [highlight-support-next](../campaign/highlight-support-next.md), alongside the independent ongoing complete green-phase trial. A positive locator result is not a photographic improvement or automatic authorization for a source-provenance campaign.

## Fixed quantities and geometry

Reviewed [observe.py](observe.py), SHA-256 `1f3f70cc202292e5e32fa1e1f78baddb7c50144daebb1efbcb88e9ef45b56923`. Its `parents[3]` resolves the worktree root. The pinned source/sidecar hashes bind the existing complete299-source CA-off sensor observation; the sidecar confirms `strehl-merged-cfa-f32-v1`, RGGB,6896x4596, payload offset292 and126,776,064 payload bytes. The actual file length126,776,356 is checked before a read-only little-endian f32 map. This is signed camera DN after merge and its input bound, before final WB, demosaic and development; it is not the RGB master or original unwarped RAW.

The manifest's full384-square windows are frozen: bright-wing-rim `(4050,1810)` and upper-occlusion `(3850,1300)` in delivered coordinates. Adding `(68,46)` gives reference149 active coordinates. All origins and the two-pixel-expanded origins preserve RGGB parity. Both expansions are safely interior, so final demosaic's mirror-border behavior is irrelevant. The script copies only these388-square regions for threshold analysis, checks finiteness, and preserves direct-site maps separately from destination dependency maps.

## Actual final MHC support

I read `F_G`, `F_H`, `F_V`, `F_X` and `demosaic_malvar_row` in [demosaic.rs](../../../crates/strehl-core/src/demosaic.rs). Including the directly known channel at the center, the union of nonzero R/G/B taps is the same for every output CFA phase: center, axial offsets at distance1 and2, and four distance1 diagonals. This is13 sites, not the whole25-site square. The script's offsets match that union exactly; its expanded-array slicing maps source hits to the correct384-square output domain.

Union support is sufficient for this stage. It deliberately omits channel-specific coefficient signs and magnitudes; negative taps may darken one channel, and other taps may cancel them. WB/normalization preserve zero/nonzero support but change magnitudes. Later matrix/highlight/tone operations can change or suppress visibility. Therefore the map means **possible final MHC dependency**, not a positive bright contribution, a displayed halo footprint or quantified causal influence. No MHC rerender is needed to establish this binary dependency.

## Controls and interpretation

The prepared flat, exact-threshold exclusion,13-site impulse, wrong-position foil and four-phase-label controls exercise the accounting before photographic samples. The impulse expectation uses the same offset list as the implementation; independent comparison of that list with the actual Rust stencils is the separate protection against a shared missing-tap error. Input files, script and demosaic source are hashed/stat-bound before and after; fresh outputs are required, and each PNG is read back for exact map equality. Timing must retain the concurrent full-stack workload annotation.

Both comparisons are strictly greater than the stated values:14848 is product working white15360 minus black512;15871 is nominal14-bit maximum16383 minus512. They classify the final sensor values numerically. Neither calibrates physical saturation, proves original censoring or detects every saturated source; equality at a rail is intentionally excluded from these strict exceedance counts.

If neither threshold reaches a region, close only the proposition that these exceptional **final** CFA values directly enter that region's final MHC support. This does not exclude original clipping subsequently attenuated, earlier pyramid influence, sub-white ringing, or final MHC overshoot formed from individually subthreshold samples. It is not a capture ceiling or general explanation of the pale contour.

If sites are found, inspect the complete unchanged photograph and the full frozen native windows beside the maps. A hit anywhere in384 pixels is not automatically on the pale contour; compact genuine glints and the contour must remain distinct. Coincidence cannot distinguish a legitimate interpolated bright scene point from an artifact, identify the source frame or determine whether MHC versus Catmull first created an excursion. Record phase, threshold, direct count and support count without promoting any to an artifact score. Only a useful visible spatial relationship could justify root's separately scoped next provenance stage; this review adds no correction, RAW pass or threshold tuning.
