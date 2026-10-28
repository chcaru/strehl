# Capture-dependent CA: a narrow next observation

**VERIFIED report/cache-metadata reading only.** No RAW opened, CFA buffer read, numerical fit, metadata census, build or render ran in this lane. Root's complete weevil/bug2 CA ablations and original 149 metadata observations motivate this allocation; they do not calibrate table units or identify why the profile transfers differently.

## What must not be repeated

| Retained evidence | Boundary for this allocation |
| --- | --- |
| `docs/research/M113-ca.md` and `M114-ca-verify.md`, plus `experiments/M114-ca-verify/RETRACTION.txt` | Demosaic and camera-to-sRGB mixing biased cross-channel geometry in opposite directions. Earlier scalar-gain fixes were retracted. Historical coefficients/defaults are not today's product state. |
| `docs/research/M113-spectral.md` | Scene variation survived clean camera-native measurement, but the proposed spectral explanation failed its directional prediction. Narrow-range focus/aperture/TC comparisons did not explain that population. This does not rule out all larger capture-state changes. A single defocused anchor over the whole field was an invalid measurement population. |
| `rea-a7c2-2026-10-24-i/{results.md,optics/notes.md,optics/diagnostic-design.md}` | The 32 signed CA entries and candidate 2^-21 scale were already investigated. Firmware descriptor tracing did not establish units; capture counters do not guarantee fresh optical data. The four-RAW edge test had insufficient support despite exact 48-window independent decode agreement. |
| `rea-a7c2-2026-10-24-j/optics/results.md` | The subsequent 2D direct-CFA test already evaluated 9 fixed CA arms. Primary Sony 2^-21 failed: source 75 red worsened 0.54166->1.15730 native pixels while source 225 improved 1.70562->1.47062. The pooled red 0.04801 gain was below its bar with an interval crossing zero. Reversed knots/other-focus tables did not establish current-table causality. Do not repeat this as an untried recipe. |
| `rea-a7c2-2026-10-24-w/{results.md,method.md}` | A later independent camera-reference result supports coarse **achromatic distortion** on one public lens/body source. It does not validate the 32-value CA law, this macro rig, or subpixel color registration. |

All paths above are under `C:/Users/chris/AppData/Local/Temp/strehl-core-main-0d466788/`, except current campaign files. No external implementation was consulted. The public unit conversion remains a reported hypothesis; no new primary-source claim is made here.

## Historical stack-to-table pairing audit

**VERIFIED, source and retained JSON only:** BUILD-CHROMA's `c1_lateral.py` really measured original CFA channels inside each source frame. It scanned 24 uniformly spaced indices in the sorted stack, selected the three strongest green frames per tile, and took median channel displacements before its radial fit. It did not measure a merged image. In contrast, M113-ca's `c9_binned.py` measured binned **merged** outputs: absence of demosaicing does not make those original-source observations.

The historical archive is incomplete at the recorded locations. `C:/dev/strehl-out/BUILD-CHROMA/json`, `C:/dev/strehl-out/M113-ca`, and `C:/dev/strehl-out/M113-spectral` are absent. Targeted inventories of the retained October 24 tree and the original repository's `outputs/` and `experiments/` found no `c1_lateral_*.json`, `c1_*_[R/B/G2].npz`, `c4_attenuation.json`, `c9_binned.json`, or `s2_measure.json`. This is a bounded path search, not a claim that no other backup exists.

Even the `c1` writer did not bind individual RAW hashes or filenames. It saved sampled `frame_idx`, per-frame aggregate fits, and selected-tile NPZ fields `u,d,s,spread,best_frame`; `best_frame` was the index of the strongest of three contributing frames. Reconstructing a filename from today's directory order would not prove historical identity. Its aperture follow-up read only the first sorted source. The report's six-stack coefficients survive, but its de-attenuated `e_true` values are model-derived estimates, not independently known optical truth. They must not be joined to arbitrary representative Sony tables as calibrated pairs.

There is nevertheless one useful exact metadata bridge. The retained `rea-a7c2-2026-10-24-i/optics/audit-results.json` contains full source hashes and all 32 CA values for ten files from **bee-3-cpl**, one of BUILD-CHROMA's six stacks. No other calibration stack appears in that 36-file audit.

| Retained source | Identity and observed state |
| --- | --- |
| `bee-3-cpl/DSC00001.ARW` | SHA256 `bcf575f697d690b483b22d63539327920fe384d6c388ed34d2c61c6409440ef6`; focus code 58; red knots from -2176 to -2560 |
| `bee-3-cpl/DSC00299.ARW` | SHA256 `a5a83423d7a66002282f2258a0b79342c50b6c2e42620363d4b40fdd0b5df529`; focus code 66; red knots from -1920 to -2304 |

The first source has red `[-2176x8,-2304x4,-2432x3,-2560]` and blue `[0,0,128,128,128,256,256,384,384,384,384,384,384,384,256,128]`. These are stored metadata facts, with no assumed conversion to pixels. Intermediate retained sources are 2, 38, 75, 112, 150, 187, 224, and 261; their codes progress through 58-65. The current campaign's root-reported bug2 code 58/red range agrees with this old starting state (its eighth red knot differs by 128 counts; the full tables are not identical), whereas weevil code 86/red -512...-1024 differs substantially. **ARGUED:** the current evidence supports questioning profile applicability outside the directly evidenced historical metadata state. It does not establish an applicability threshold, prove physical focus distance, validate table units, or prove that all six old stacks shared the bee-3 state. Do not fit a metadata-to-correction law to this one historical stack.

## Exact reusable inputs  -  held, no new single-window run

The small useful cache is `outputs/rea-a7c2-i/native-roi-2/` under that retained tree. Its `manifest.json` has recorded SHA256 `684d191e76e1d29858d9a5a7d09edb485468a955bc6242ea57fdb7e580d2134e`. The two selected files exist:

| Cache | Original | CFA hash |
| --- | --- | --- |
| `source-2-roi-5.u16le` | calibration-slide2 `DSC00075.ARW` | `6d9bddbf8256ee74b6389f9e6f28d693a920ec132b9ba824769cd8a50c4d3ab3` |
| `source-3-roi-5.u16le` | calibration-slide2 `DSC00225.ARW` | `41b559025b2d7d63b97b65b3aaaaf21f9343e04f6352032780e9e05b5fc063ba` |

Each is 384x384 uint16 little-endian, 294912 bytes, at active-native origin (384,1536), with RGGB integer sensel centers. Original hashes are respectively `020add189e34ec0aa97fc38d05ddd9669a4a3695c6d00e1aba8296f892aac803` and `80ca4e7b7063ecda5d5a7b3ddecca26094e9c81ce4cfac137c2877ba8abbf6d1`. The native manifest retains injected noise/levels and buffer geometry.

Bindings: `experiments/rea-a7c2-2026-10-24-i/native-roi/source-identities.json`; `i/optics/crosscheck-2/crosscheck.json` (recorded hash `a9c199fe821caed3885dbc72cfd6e4e4eb338f05adac78f41328c38ec3cae063`); and `j/optics/support-2/support.json`. The crosscheck records exact native/RawPy equality and both optical tables. No decoder-coordinate guess is needed. Source75 versus225 red tables differ by 128 counts at every knot; blue changes only some inner/middle knots. Default crop (12,8,7008,4672) is common. This is metadata contrast, not an observed displacement or freshness result.

The old source-only 2D gates accepted source 75 windows 3,5 and source 225 windows 5,10,11,12,17,18. **Only window 5 is common.** Same sensor rectangle does not yet prove that the same sharp feature appears in both frames: breathing and focus must be checked from those saved samples. No additional CFA bytes are needed for that first local support check; no original-file reopen is justified yet.

## Changed observable retained for reference, not dispatched

Measure each physical color against itself across the two sources: R->R, G1->G1, G2->G2 and B->B. Parameterize each local map about the **same native reference point**, initially the geometric window center (576,1728), and evaluate all channel maps at that point. Compare R/B temporal motion to the two separate green estimates. Do not subtract translations implicitly centered on different channel features; achromatic magnification would then create `(A-I)*(p_C-p_G)` and look chromatic.

This removes the assumption that a red insect structure and a blue structure have identical geometry. It measures local differential **effective channel motion**, not an absolute CA coefficient. Before implementation, the cache must support the same manufactured 2D feature at both focus settings and a disjoint held subfeature inside the fixed window. Source support must be selected from green/physical geometry before color-motion outcomes; preserve empty/ambiguous/blurred refusals. One window cannot test radial shape or a spatially held correction field, and cannot distinguish table ordering/freshness where predictions coincide.

The smallest actual observation would bind these two caches, keep one original u16 buffer per source, fit source-to-source geometry using original physical CFA coordinates and one injected noise model, and compare its held common-point differential motion with two predeclared predictions: frozen-table/no-state-change and the exact composition of the two recorded tables under the existing uncalibrated 2^-21 convention. Do not fit dose, center, knot order or optical sign. Common achromatic breathing/distortion is nuisance geometry; composition order and its gauge must be explicit. Report full vector residuals, both green nulls, source/held support and uncertainty; no sRGB, MHC, merged image, chroma-energy objective or arbitrary sharp-source election enters the measurement.

Required pre-pixel controls are a continuous original-CFA plant with achromatic breathing and genuinely different fixed RGB textures; a known channel-specific differential shift at the common point; phase omission and wrong common-point destroyers; symmetric focus broadening with no displacement; and a zero-geometric-shift, focus-changing asymmetric color PSF. The last is not necessarily distinguishable from CA. If it shifts the fitted image response, the instrument must retain the ambiguity rather than certify an optical map.

**DERIVED identifiability boundary:** replacing a channel PSF by `h_f(u-delta_f)` with no geometric CA produces the same channel images as shifting the scene response by `delta_f` under the unshifted PSF. Original CFA access does not break that equivalence. Same-color temporal comparison avoids colored-edge circularity but cannot alone distinguish a PSF centroid change from lateral geometry. A metadata correlation across one pair would therefore be an association under declared optical assumptions, not calibration.

This is a boundary on **optical attribution**, not a veto on useful effective chromatic registration. A shift that compensates an asymmetric response may still improve a complete photograph. Such a consumer must preserve genuinely distinct colored structures and be evaluated on held focus and held field locations, then complete outputs. Its asymmetric-PSF control should score known colored-scene recovery and preservation; it must not require a zero estimated shift merely because the planted geometric CA is zero. No optical explanation is needed to accept a demonstrated photographic improvement, but no fringe reduction alone proves preservation.

## Decision

Do not build or schedule the old single-window fitter. Root explicitly declined another run on that narrow pair, and `temporal-observation-plan.json` is held. No pixel-reading executable was added. The useful result of the follow-up is the exact **bee-3 metadata-domain bridge**, together with the missing historical coefficient identities. Recovering an already existing `c1` archive and its source manifest could enable a bounded join; without them, this is not an exact measured coefficient/table dataset and does not justify a metadata census or re-running the old instrument.

For a future effective-registration consumer, the changed question is whether a fixed correction with capture-dependent evidence transfers across held focus and field while preserving real color structure. The current complete weevil/bug2 opposite-direction ablation supplies a reason to investigate that question; the historical six-stack report does not close it. Any fit needs stronger support than the one retained slide window. This audit proposes no pixel run and no default/profile change. Root subsequently requested `header-domain.py`: a current replay of 24 selected headers from each of the six named calibration stacks, with frozen native parsing and exact source identities. It tests sampled metadata-domain overlap only; source preparation is complete and root owns execution.

No fixed-profile replacement, table-unit selection, current-camera applicability rule or photographic improvement follows. Any later conditional consumer still needs complete weevil and bug2 outputs, full-resolution masters and general-corpus transfer. This is a bounded prior audit and concrete cache-level option, not another CA ablation or a proposed scalar tweak.
