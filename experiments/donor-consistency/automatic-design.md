# Automatic concentration-track discriminator

**SAVED, CONDITIONAL DESIGN: not authorized for implementation.** I independently
inspected baseline/candidate/late facet-edges and dark-inclusion crops. Focused
donors locally contract rays while retaining compact glint cores; late69
broadens/softens those regions. The independent photographic decision is only
partially positive for the facet: the dark cyan/pink tail persists, well beyond
Helicon B, and the facet retains diffuse residue. The joint photo requirement
therefore failed. Close the exact masks/band-mixing recipe without donor,
radius, feather or band-count tuning. Local externally labelled headroom is
not a demonstrated complete consumer solution or automatic source estimator.

**Consumer attribution comes first.** Gaussian reduction of a tiny finest mask
can leave substantial baseline membership in coarse AC bands. An exact-core
mask-only expansion can quantify that support loss, but its result is a
constant-coefficient response, not a general effective image-pixel weight:
`Expand(m*C) != Expand(m)*Expand(C)`. Existing mask hashes/counts and the saved
per-band argmax/neff fields do not contain the normalized AC coefficients.
Reanalysing the rendered TIFF cannot recover them through collapse, limiting,
MHC and tone. If the root's mask probe confirms dilution, use an observer on
the unchanged recipe to isolate actual expanded baseline remainder
`Expand((1-sum m)*C)` and donor terms `Expand(m*D)` at the frozen windows, with
the final hull residual kept separate. Prove observer output neutrality. That
would locate the residual before choosing another consumer. It does not reopen
the closed recipe as a parameter search. No such execution is claimed here.

The proposed future locator below would produce nominations/refusal reasons,
not another rendered candidate. It should proceed only if a viable consumer
question remains after that attribution.

## One rule to try

**ARGUED hypothesis:** a tracked bright feature's most concentrated spatial
footprint can nominate a compact-source neighbourhood, even where a fan pixel's
local finest-band energy peaks late. Follow the footprint through focus, rather
than letting its brightest off-centre ray nominate its own source. A long real
thin feature is allowed: the rule uses both covariance axes and never requires
the feature to be round. Crossing depths, changing component identity and weak
signal require abstention, not forced agreement.

This is one fixed first discriminator, with no parameter sweep. All distances
below are reference-output native pixels. Reuse the140 saved384-square source
crop bindings, exact held map and coordinate-only assignment from highlight-spread.
Do not interpolate source images or refit alignment. RGB16 stays at its existing
common tone. No sensor noise constant may be inferred from these exports.
The original384 crops are insufficient context for this particular support:
the dark core is only30native from its crop's left edge. A future authorized
locator must read expanded regions from the same retained TIFFs, verify the
old384 overlap against its existing hash, and hash the newly read crop. It must
not rerun RAW development or pad a crop edge and call it scene support.

1. For each source, compute a positive local colour-contrast field
   `q=max(0, R-G32(R), G-G32(G), B-G32(B))`, where G32 is one fixed separable
   Gaussian with sigma32native in that source image. Use existing crop context;
   refuse a requested support lacking its stated filter margin. This max-channel
   locator is intentionally colour-sensitive; genuine red/blue detail is not
   required to appear in green. It is a display-space locator, not a calibrated
   sharpness or RAW significance measure.
2. Assign original pixel centres to fixed2-native reference cells and retain
   the maximum q observed per cell across the70 sources. The cells are coordinate
   bins for locating features, not a resampled photograph. In each fixed32-native
   grid cell, nominate its maximum as a seed; suppress seeds within32native of a
   stronger seed, with row-major tie breaking. This runs over the whole available
   field, without receiving glint coordinates or source indices. The frozen
   targets are read only afterwards for evaluation.
3. For each seed and frame, find the strongest q peak within8native. In a disk
   of radius64 around the seed, take its8-connected component above0.1 times
   that frame's local peak. Use original source pixels, with their continuous
   mapped reference coordinates, for all following sums. Record component
   mass `M=sum(q)`, peak, centroid and q-weighted2x2 covariance. Refuse clipped
   support at the disk/crop boundary, centroid displacement>4native from the
   seed, or ambiguous peak identity. Define the latter concretely as a second
   disconnected above0.8-peak component inside the8-native search disk.
4. Report both covariance eigenvalues. Rank concentration by
   `r=(lambda_min*lambda_max)^(1/4)` with no fitted regularizer. Zero/singular
   covariance is unknown, not perfect focus. A real thin feature can have a
   large major axis and a small minor axis; it must survive the controls below.
   Require mass>=0.25 of that track's maximum mass and peak>=0.5 of its maximum
   peak before comparing radii. These conservative eligibility cuts prevent a
   disappearing low-flux remnant from winning solely because it is small; they
   do not assert conserved flux. Report excluded frames and both raw quantities.
5. Nominate the minimum eligible r only if it lies at least5frames from either
   stack end, its immediate neighbours are eligible and have r<=1.25*r_min,
   and both samples5frames away are eligible with r>=1.25*r_min. Ties use the
   central frame of the tied interval; separated tied intervals refuse.
   Otherwise report no stable contraction. This fixed through-focus condition
   is a falsifiable locator gate, not an optical law or calibrated confidence.

The Gaussian's support must be explicit in the implementation contract. Use
truncate2 (radius64 source-native), with the expanded source context described
above covering both the measurement disk and filter support. No result may
silently use padded crop edges as real context. The coordinate mapping changes geometric distances, not
the stored samples. Connected components are in the original source lattice;
reference-cell binning is used only for seeds.

## What can reject it cheaply

Run a compact known-answer suite first, then the two retained windows once:

- **Flat/noise first:** constant RGB and independent seeded noise at two supplied
  amplitudes. No stable track may be admitted. Add a persistent hot point:
  fixed small size through focus must fail the contraction condition. These
  validate the discriminator, not the camera noise calibration.
- **Coherent real bright thin feature:** a coloured thin segment is focused in
  a different frame from an adjacent compact glint; vary only its true blur.
  Its own nomination must remain within one frame of its planted focus or
  explicitly abstain. It must never borrow the glint label. Include independent
  R-only and B-only versions and a narrow one-frame focus opportunity, for
  which abstention is acceptable and silent replacement is not.
- **Crossing depths and late fan:** a known compact glint develops a long bright
  fan late, beside and crossing the independently focused thin feature. The
  glint must nominate within one frame of its planted compact focus and the
  thin feature must retain its own nomination or abstain. Use the same geometry
  with the radial feature genuinely sharp late: a rule that simply bans rays
  or late indices must fail. Reverse frame order and transform expected labels.
- **Flux/identity sabotage:** attenuate one defocused frame to a faint compact
  remnant; transfer brightness between two neighbouring glints; impose output
  clipping before measuring. Require an explicit rejection/unknown status when
  the inputs cease to identify one complete feature. Do not count low radius
  under changed support as improvement.

On real data, compare the automatic nominated tracks against the already
inspected compact-source neighbourhoods around28/33, late52/69 witnesses and
nearby real structure25 versus35. Report every seed/track in the two windows,
not just successful associations. A track must spatially cover the existing
core/fan pair through its observed source footprints; failure to associate
them is a failure to explain that target. If an uninspected frame wins, retain
its native crop and immediate neighbours for independent review before any
admission. No source-window score alone licenses a new merge.

## Native route and stopping point

The eventual output would be one source assignment per tracked component,
shared across colour and detail bands with unchanged mean base. Unassigned
areas keep the current merge. Support comes from the observed tracked
footprints, never the two hand-labelled capsules. Overlapping components at
different depths abstain initially; no automatic depth propagation or graph
solver is authorized by this proposal.

The locator needs two sequential passes plus one current source field, a
maximum seed field and bounded per-track summaries: O(N) in frame count,
no aligned-frame volume. Connected-component moments should be accumulated
once per frame and reused across seeds; speed has not been measured. A native
implementation would consume original-u16-derived, WB-aware fields at the
actual gather and use the existing injected noise/transfer and per-source RAW
clipping authority. Toned TIFFs cannot supply those safeguards. Record display
ceiling contact separately from unknown RAW clipping; a display-space success
licenses only that native validation, not automatic correction.

This differs from the rejected radius32 energy pool: it tracks normalized
spatial footprint shape through focus and retains competing feature identities.
It does not revive BUILD-ELECT's unconditional hard pixel election. M63/M96
still apply: a smooth or unimodal track can be confidently wrong. The explicit
thin-feature, crossing-depth, flux and identity controls are therefore binding.
If either target cannot be associated or the controls expose wrong assignments,
close this fixed rule without changing radius, thresholds or donor ranges.

Here `mass` means summed positive toned contrast, not photon count or conserved
optical flux. Clipping can change both covariance and component connectivity;
the proposed export-space thresholds are heuristic refusal conditions, never
substitutes for the original RAW noise/clipping authority.

No new image processing, RAW read, build or locator execution was performed
for this design. Only retained native images and prior reports were inspected.
