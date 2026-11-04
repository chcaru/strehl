# First-light fixed-focus bee: bounded repeat control

PROPOSED native preparation; metadata and roles FROZEN before new CFA decode. Only the32originals DSC00328.ARW..DSC00359.ARW under `requests/12-bee-iso-var-no-bracket-32-repeat-diff-light` are in scope. Maximum8workers,16GiB; outputs/cache stay outside captures. No second light, other ISO, FRC, Fourier bandwidth claim or original-CFA reconstruction.

## Identity and prior evidence

`outputs/multi-stack/completion/noise-bee-repeat-01/inputs/` records all32 full-file SHA256s, source stamps, complete metadata and three embedded JPEG hashes. All32 are distinct, total1,162,788,864bytes. Current metadata exactly reproduces the old first-light ISO100 group: ILCE-7CM2,1.6s,f/5.6,200mm,14bit, manual focus, focuscode57/distance0.273841307296975m, shutter16467..16498. Capture time is2026-08-30T19:52:44.315..19:53:53.454−07:00 (69.139s), maximum gap2.278s. Stabilization is On. BrightnessValue range0.20703125EV is a warning against assuming constant illumination; metadata does not calibrate pixel gain.

These are the already measured development bee originals documented by M-PHASE0-SPLIT2, not the separately requested407-frame grid+fabric/independent-calibration session in captures-needed section35. No407capture was opened. Existing evidence is conditional: the old central, translation-only protocol measured finite nontranslation RMS0.064031native pixels, independently0.070005. These are neither zero error nor a whole-scene/current-resampler certificate. The original zero-shift failure and second-light failure remain unchanged. No old FRC measurement is revived.

The first/middle/last embedded JPEGs show similar pose and gross focus. They nominate physical regions only; no CFA quality or temporal stationarity follows from them.

## Fixed source roles and primary estimand

Four disjoint8-acquisition windows start at ordinal0,8,16,24. Within each, Q={0,7}, V={1,6}, R={2,5}, M={3,4}. Q photons supply a frozen linear temporal signal prediction and optional precision guide; this shared qualification/weight role is explicit. V tests model adequacy; two Q endpoints have no residual degrees of freedom. R is excluded from Q/V, guide values, mask selection and candidate numerical estimates. All acquisition IDs and actual timestamp interpolation coefficients are stored before pixels in `inputs/protocol.json`.

Primary actual-core arms are singleM3, singleM4 and equal Repeat ofM3+M4. Precision Repeat with the Q-only frozen guide is a secondary near-null comparison under equal calibrated noise; do not invent separateW observations. The Q-guide filter has its full radius8 support halo, and an unsupported neighbor must invalidate its influence exactly as in the commissioned preceding observer.

R2/R5 independently predict both physical measurement states using their actual timestamps: R_at_M3=(1−a3)R2+a3R5 and R_at_M4=(1−a4)R2+a4R5. Every candidate is scored against both references on the same frozen Q/V-qualified masks. The conservative primary paired risk is one half of `[risk(candidate,R_at_M3)−risk(singleM3,R_at_M3) + risk(candidate,R_at_M4)−risk(singleM4,R_at_M4)]`. Preserve each signed component/state/window term. A midpoint target is descriptive only: noiseless linear drift can flatter midpoint averaging.

For exact linear signal and equal independent noise, the equal mean's primary risk difference is `−sigma²/2 + (S4−S3)²/4`: drift penalizes the pair. This is DERIVED, not measured calibration. The actual nonlinear core need not attain this expression. The resulting real estimand is conditional predictive risk to two photographed states, not absolute sensor noise, developed-RGB sigma, independent fixed-pattern truth or extended-depth benefit.

## Spatial nomination and independence

Nine384sensor-pixel square photographic witnesses are fixed from ordinal15's embedded preview: dark background, upper background, antenna shaft, eye facets, dark eye, brow hairs, chin hairs, defocused body, and specular face. Their exact normalized active-image centres are in JSON; origins are floor(fraction*active_extent−192). Retain all nine even if clipping, darkness, insufficient texture or motion makes qualification fail. Never relocate using candidate quality.

Separate nominated geometry patches cover antenna tip, upper forehead and lower-body hairs; a separate photometry patch covers defocused right thorax. They are not declared usable merely by nomination. Before an independent-reference assay, verify original-CFA support footprints—including search/filter halos—are disjoint from scored witnesses. Estimate each source's geometry from these disjoint physical pixels; the R source's own disjoint patch may estimate its placement but no R scored pixel may influence M placement or a selected mask. Freeze fitted placements before scoring. If this cannot be achieved with qualified patches, report conditional joint-map repeatability only; do not call the reference independent. Local geometry errors and shared optical/fixed-pattern effects remain explicit nuisance even with disjoint pixels.

Primary photometry is gain1 at equal exposure. A separately reported sensitivity arm may use gains fitted only on the disjoint frozen photometry patch, with uncertainty and clipping/support failures retained. Do not derive gain from the measured witness or subtract an R/M-fitted signal model. Q/V reports include signed mean, slope, per-site prediction discrepancy and focus/structure response; block means alone cannot establish common latent texture.

## Commissioning and stops

Before R/M real replay, run flat independent original-u16 noise through exact production sampling and core fusion first; known linear drift must expose midpoint confounding while the primary two-state risk remains conservative. Challenge curvature, focus/PSF change, registration shift and spatial motion, wrong correspondence, common blur, constant output, channel-only damage, missing/clipped nonzero interpolation taps and radius8 guide-halo poison. Preserve all Q/V-qualified pixels including candidate fallback. Test exact source-role exclusion and reference/pass swaps. Q/V cannot validate a saturated model by its own fit.

Do not tune thresholds against real risk. The preceding fixed1.35 consistency gate is not automatically calibrated for a new two-endpoint/two-validation covariance; commission the exact matrix and finite actual-noise plants before applying it. No pixel-count confidence interval: windows are the acquisition replication unit, and four windows provide limited uncertainty. Report all four, all components and both physical states, plus raw/signed/centred contrasts where relevant.

## Full-photo preservation arm

Prepare two balanced16-acquisition passes A={i:i mod4 in{0,3}} and B={i:i mod4 in{1,2}}. Each four-shot block gives equal average ordinal1.5; actual times are retained. These are disjoint original exposures of one reported fixed-focus scene, not extra focus depth. Immutable workspace input copies may express this grouping for the existing manifest directory API; verify bytes against all original hashes. Never alter originals.

Use product16 with one native direct-global alignment envelope and original-u16 cache. Render passA, passB, equal Repeat and precision Repeat on the same map/canvas/default development, sequentially at8workers/16GiB. Preserve complete photographs, masters, focus/contribution/placement diagnostics and cache; SR stays off. Joint full-photo geometry may use all sources and is not the independent-reference assay geometry. Inspect complete outputs first, then all nine identical native crops. Repeat should preserve hairs, eye facets and contrast rather than merely smooth them. Precision-versus-equal is secondary at equal exposure/noise. No quality claim follows from a mechanical completed render alone.
