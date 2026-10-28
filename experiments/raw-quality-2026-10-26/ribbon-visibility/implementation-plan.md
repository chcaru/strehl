# Two-capsule original-CFA consumer

Source preparation only. Root owns execution and the120-second, below4GiB first-job envelope. `model.py` imports only Python standard modules and Torch. No RAW decoder, aligned-frame volume, per-source RGB volume, alpha lattice, broad curve framework, or product hook is added. The independent reviewer owns truth, controls, result scoring and the execution entry; the source reviewer independently checks this consumer. No numerical operation was executed by the author.

## Frozen coordinate and optical contract

Physical original sensel centers have integer native-pixel coordinates `(x,y)`. RGGB phase is `2*(y mod2)+(x mod2)`, with phases0/1/2/3 selecting R/G1/G2/B and camera RGB channel0/1/1/2. A transformed reference coordinate never chooses CFA phase. Query storage is `xy[N,2]` float32, `phase[N]` int64, `view[N]` int64, and optional original `codes[N]` uint16. Reconstruction converts observed codes to float32 only when evaluating the supplied likelihood approximation.

`views[V,3]` contains focus coordinate, x shift, y shift. A source query maps into scene coordinates by **adding** its supplied shift. A structure moved right in source coordinates therefore requires a negative source-to-scene x shift to align with the same scene location. All positions, endpoints, radii and shifts use native-pixel units. Depth increases away from the camera. The signed pupil displacement is `defocus_scale * (depth - focus) * pupil_xy`, with scale measured in native pixels per arbitrary depth unit. These are explicit synthetic optics, not Sony calibration or a fitted physical focus-distance model.

Each scene has exactly two finite line-segment capsules, each with two continuous endpoints, positive radius and depth. The finite end caps are circles: distance is measured to the segment after projecting and clamping its parameter to[0,1]. Centerline lengths must exceed0.5pixels, depths differ by at least0.01 and both precede the background depth. The current renderer supports three constant camera-linear RGB colors in black-subtracted DN, one for each capsule and background. Background depth is explicit but inactive when its radiance is constant. The implementation does not optimize spatial radiance fields; that limitation is deliberate for this first discriminator.

The pupil is the uniform unit disk and the sensor footprint the uniform unit square `[-.5,.5]^2`. **The two explicit arrays have the same length K and their rows are paired**, not crossed. At each query and row, evaluate both capsule intersections using the same pupil and footprint pair. The nearer hit wins; otherwise the farther hit wins; otherwise the background contributes. Average only after this first-hit decision. There is no product of averaged coverages.

The fixed producer quadrature uses2048 unscrambled Sobol4D points: the first two coordinates map to an equal-area unit disk, the last two to the pixel square. The earlier provisional4×4 Cartesian footprint was discarded before code freeze because in-focus pupil rays would repeat only16footprint positions and strongly quantize subpixel widths. Paired semantics are agreed with both reviewers. The independent interval/Gauss-Legendre reference must establish adequate precision across Bayer phases, caps and crossings before any inverse score is interpreted. Increasing quadrature to rescue a failed screen is not silently authorized.

`pinhole` uses the same footprint positions with zero pupil displacement and returns the final camera-linear RGB field. It does not remosaic or apply MHC. A latent camera-linear image estimated from original CFA observations is a joint reconstruction; it is not a demosaiced source-stack fusion. The present output is only the complete small synthetic domain.

## API

| Entry | Contract |
| --- | --- |
| `make_scene(endpoints,radii,depths,colors,background_depth=1.5,device="cuda")` | Returns `Scene` with float32 GPU arrays; constant colors shape3×3. |
| `make_queries(xy,phase,view,codes=None,device="cuda")` | Creates the physical-query dictionary; supplied codes must already be uint16. |
| `Optics(defocus_scale)` | Stores the explicit scalar synthetic defocus convention. |
| `quadrature(power=11,device="cuda")` | Returns paired pupil and footprint arrays; fixed default2048rows. |
| `visibility_weights(scene,queries,views,optics,pupil_xy,footprint_xy,batch_queries=128)` | Returns Nx3float32 first-hit weights. It retains source/channel identity in the query arrays. |
| `predict(...,black=512,batch_queries=128)` | Returns one raw-DN prediction per original sensel, with no quantization or clipping before averaging. |
| `pinhole(scene,xy,footprint_xy,batch_queries=128)` | Returns Nx3final camera-linear signal-DN values. Final-image centers need not be CFA sites. |
| `fit_geometry(initial,queries,views,optics,pupil_xy,footprint_xy,sensor,lower,upper,steps,...)` | One bounded training-only geometry/constant-color fit, with fixed73evaluation maximum. |

The independent entry provides explicit observations, query identities, fixed bounds/initialization, and one noise authority. Proposed synthetic coefficients are black512, white15360, read variance `[9,9,9,12]` DN² and shot coefficients `[.15,.13,.13,.17]` DN per phase. They are test assumptions, not a newly estimated camera profile. The fit freezes variance at the observed nonnegative signal using this model for every candidate. Its objective is feasible weighted least squares, not exact signal-dependent Gaussian NLL. It has no censored likelihood and explicitly refuses training observations at/beyond white or bottom clip. The independent no-object/glint foil must be unsaturated or record that refusal; it cannot be advertised as clipped-highlight recovery.

## Bounded unknown geometry and radiance

Hard membership under finite quadrature is piecewise constant. The implementation deliberately does not differentiate comparisons or use a soft opacity surrogate. It evaluates fixed positive/negative coordinate proposals on12parameters:8endpoint coordinates,2radii and2depths. Three predetermined sweep scales `(1,.5,.25)` and caller-frozen step sizes give exactly at most73forward evaluations, including initialization. There is no parameter sweep, random restart, topology search, adaptive iteration extension or stationarity claim. Finite sampling thresholds can bias the selected geometry; independent phase and denser-reference scoring are required.

Each candidate estimates9constant color values from the training original-CFA samples. Three channel-specific3×3normal systems use the identical frozen noise weights. A float32 eigendecomposition forms a relative1e-6 pseudoinverse, followed by24fixed projected steps in the nonnegative camera range. Conditional ranks, eigenvalues, active bounds and the final projected step are reported. This is an explicit bounded numerical method, not an exact constrained optimum or an identifiability certificate. No hidden-layer radiance is supplied from truth; an unseen layer or degenerate design may remain unidentified. Equal-color geometry is unidentifiable even with a full-rank conditional color system.

The fit accepts48..512training queries; held queries are never passed to it. It also returns a fitted constant no-element null and its training error. It always reports `identified=false` and `converged=false`; the independent controls decide null/refusal and require held prediction plus complete pinhole-image evidence. Lower training error alone cannot admit geometry. Wrong depth order, a spatial glint without an opaque ribbon, and true material translucency remain explicit adverse cases, not alternative opaque parameters. The supplied finite topology and initialization are substantial assumptions.

## Resources and photographic route

Default128query batches ×2048paired rays give262,144joint evaluations at a time. Point positions, distances and two hit masks are current-batch temporaries; only Nx3visibility weights survive the batch. Geometry/colors are tiny, observations remain uint16 and output is one small final RGB field. This O(query-count + batch×rays) structure avoids a full aligned-frame volume. Actual Torch/driver/process peaks and wall time are unmeasured; root must enforce the declared envelope, including driver memory outside the Torch allocator cap. No timing estimate is a performance claim.

A general photograph would still require automatic original-CFA multi-focus ridge/paired-edge proposals, association across focus, competing depth orders, birth/death/split of elements, a no-object option, and support/uncertainty tests that reject glints and symmetric defocus as movement. Spatial camera-linear radiance must then be represented independently of sparse geometry and inferred from original sensels without erasing other-depth detail. Full-image tile overlaps, visibility support outside each tile, corrected forward calibration and a conservative fallback remain unresolved. Hand-seeded constant-color capsules cannot substitute for that work. A future final latent RGB field can be developed once without forced remosaic/MHC.

This small test can reject the continuous-geometry premise or expose practical sensitivities. It cannot establish why the actual weevil is soft, remedy the rejected marigold fit, or earn a photographic quality claim. Complete all-source weevil, bug2, flat/mineral transfer, full-resolution masters and independent full-image inspection remain the later acceptance surface.
