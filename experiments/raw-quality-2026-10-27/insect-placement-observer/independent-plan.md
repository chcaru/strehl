# Independent plan: observe alignment without changing it

2026-10-27. **ARGUED / source-only.** Root owns execution. This scope retains actual alignment observations to test whether the existing weevil data can distinguish placement error from defocus-sensitive matching. It changes no warp, pair selection, source admission, peak refinement or merge. No numerical run, RAW read or Rust change was made for this plan.

Read the [insect audit](../../raw-quality-2026-10-26/insect-warp-audit.md), [M6 §1.1](../../../docs/research/M6-residual-halo-measured.md), [M97b §§12.2–12.4](../../../docs/research/M97b-align-visible.md), [M103 §16](../../../docs/research/M103-halfdrift.md) and the [rule 6 amendment](../../../docs/agents/engineering-ledger.md#rule-6). Their constraints remain active: fixed-anchor focus/depth regressors can be confounded; uniform blur can imitate a radial sharpness signature; two merged photographs need not differ by a warp; endpoint error does not measure each frame's placement at the merge consumer.

## Observer contract and first controls

The proposed API keeps `align_pair`/`fit_stage` delegating to the same internal implementation with no observer. The optional callback copies the already computed fine-stage results. Keep every attempted fine pass and which pass was selected. A coarse/preflight failure must emit an explicit reason why no fine observations exist. Serialization occurs after measurement; it must neither refit nor reorder the observations consumed by fitting.

Record pair/source IDs and hashes, source order, guide dimensions and construction, exact configuration, pass/level, seed, tile origin/size, predicted offset, search radius, status, contrast, measured dx/dy/peak, corresponding Observation when present, initial-fit residual, MAD cut, survivor mask and final stage result. Rejected or unevaluated fields remain distinct. Preserve literal nonfinite bits separately from readable null values; a failed tile is not a zero displacement. Retaining only survivors would defeat the question.

| Minimal control | Required producing-path observation | Failure it must expose |
| --- | --- | --- |
| Observer off/on, same inputs/configuration | Bit-identical pair/stage fit values, all edge similarities/RMS/lever/counts, acceptance/refusal and selected-pass decisions; unchanged input bytes | A callback that changes accumulation, fitting or the set of accepted edges |
| Mixed accepted and refused pairs | Every attempted pair counted; all tile statuses and outliers reconciled to the actual census; explicit no-fine records | An observer attached only after successful `filter_map` or final survivor selection |
| Literal coordinate/phase fixture | Actual green-guide construction and exact recorded fit-center/offset mapping agree with independently known original sensel positions | Factor-two, half-pixel, x/y, direction, source-ID or true phase substitution mistakes |

If a global solve is included in the commissioning path, compare its placements and connected-component membership exactly too. Pair equality alone must not be advertised as an executed global-map null. Do not serialize timing-dependent callback order as a geometry difference; canonicalize the receipt by stable pair/pass/tile IDs after the fit.

The guide at index (u,v) averages G sensels centered at active-native (2u+0.5,2v+0.5). Displacement scales by two; an origin offset does not belong in a displacement. The aligner's *fit-center* is exactly `tx+tile/2, ty+tile/2`, relative to `W/2,H/2`, not the template pixel centroid. Preserve that convention and label it rather than silently correcting it. Pair direction is reference i to moving j. Any reference149 or delivered-master coordinate must carry its explicit map and crop; the held weevil master origin (68,46) is not a new guide origin. A wrong-phase foil must substitute R/B or misplace a green: merely swapping G1/G2 is invisible after their average.

## Small geometry/defocus discriminator

Use one independently rendered, textured continuous scene for a matched pair of causes: symmetric defocus with unchanged geometry, and a fixed known non-similarity displacement with the same defocus/noise conditions. Include the sharp fixed-geometry null. Fresh injected sensor noise follows blur; do not blur one noisy input and thereby make the blurred arm quieter. Avoid constructing the sole null by bilinearly resampling a photograph, which introduces the phase-dependent sharpness modulation documented by M6.

Judge signed tile displacement against the known correspondence at the recorded fit centers, including the similarity component removed by the actual pair fit. A smaller survivor RMS or a stronger NCC peak is not the positive's success criterion. The positive must recover the direction and spatially varying movement, while the defocus-only case must not produce the same purported geometric signature. Freeze the plant, scored tile population, vector-error tolerance and a wrong-coordinate rejection before execution; if the control fails, retain the failure and stop interpretation rather than adjust thresholds or search textures.

A two-image fixed-geometry observer commission does not establish deep-stack placement. If a stack/track plant is used for such a claim, preserve measured breathing curvature from a bound recorded track, state its reference and native/guide scale, and compare every planted frame in the merge gauge. Do not substitute a straight endpoint interpolation or transfer the old bee track's 46.1-plane-pixel curvature number to this weevil. A reused fitted track is the known *planted* motion, not proof of the real camera's optical truth.

## Actual 299-source identifiability decision

Retain the exact existing pair policy in one root-owned observer run. Use sliding pairs at the same available span with different pair midpoints, and follow the same physical tile footprint through the declared gauge. Equal grid indices in different source frames do not alone prove equal subject support. Cross that comparison with spatially separated tiles at comparable pair/focus support. Include refusals and changed support so disappearance of difficult tiles cannot create a cleaner field.

Frame ordinal is a bracket coordinate, not a calibrated depth. Existing complete/native source views can support broad focus intervals; a maximum gradient or single sharpness argmax cannot nominate geometric truth. Report signed vectors, scatter, status and support separately. A stable field term must survive different focus offsets and predict preselected held spatial sites/pairs; fitting and scoring the same NCC vectors establishes neither physical placement nor a lens law. No radial model is selected just because a residual points radially.

If common physical support, crossed focus offsets or stable correspondence is missing, report **UNIDENTIFIABLE** with that specific deficiency and stop. This is an informative outcome, not an invitation to a wider crop or span search. No source ranking, placement improvement or photographic improvement follows from an observer receipt alone. Any later correction still needs original-structure placement evidence and complete weevil outputs with the frozen ten witnesses and full-resolution masters.
