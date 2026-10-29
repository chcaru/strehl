# Original-sampling repeat hypothesis for reconstruction

Allocation: parent-released continuation of completion/sr. Experiment-only Python/source; no product files, no new real original reads, no FocusEvidence peak or width. Original CFA is stored u16. Numerical fit uses f32; independent analytic plant/oracle and diagnostic accumulations may use f64. The entire protocol is frozen in `repeat-forward-protocol.json` before simulated photons are inspected.

## Changed question and prior art

Native equal-mean equivalence can reject useful phase-dependent alias. This hypothesis instead asks whether five independent original acquisitions predict the sixth under one local continuous pre-aperture RGB field and the actual source sampling operators. This is a compatibility instrument, not an image renderer or a revival of the rejected spectral-fusion recipe. Wronski et al. motivate direct CFA sampling and phase diversity; their phone-specific quality conclusions do not validate this observer. Primary research: https://arxiv.org/abs/1905.03277 and https://research.google/pubs/handheld-multi-frame-super-resolution/ .

Local precedents include the direct-CFA kernel/held prediction controls, M95/BUILD-DEMOSAIC alias and color warnings, the retained strict native-mean compatibility negative, and the rejected native spectral full-scene result. Actual searches: `python scripts/research.py search "original sampling forward prediction common scene"` and `python experiments/ORCH-drift-check/prior_art.py "original sampling forward prediction common scene"`. The latter finds no exact matching historical report; that is not a claim that the idea is absent from the corpus.

## Frozen sources, geometry and model

Use the saved brow cohort globals[3,4,20,23,12,28], guides[0,15], corrected consuming RGB pulls and fullquad[3516,2344]. Geometry is already conditional on original photons, including prior all32-source joint alignment. A leave-acquisition-out score is not unconditional independence from that ancestry. Preserve every cohort source and all six folds; guides never become additional acquisitions.

Twenty-five positions are parity00 of each original5x5 phase cell. The other three nearby parities are not treated as independent patches. Fit each24sensor square and score original pixels whose entire transformed aperture lies in its central8sensor square. Use a fixed20x20 tensor cubic B-spline field, open clamped knots uniformly spaced over24sensor, and a restricted14x14 field as a frozen operator-detail placebo. No ridge, eigen truncation, complexity selection or fitted noise. Rank/condition failures produce UNKNOWN; they do not trigger model changes in this revision. Require at least coefficients+64 training samples, scaled Gram condition<=1e6, and maximum held prediction variance<=4times held original variance.

For each original CFA photosite, invert the actual color pull in absolute sensor coordinates about(fullquad.width+.5,fullquad.height+.5), including2*b translation. Integrate the pre-aperture field over that original sensor's unit-square footprint, a parallelogram in reference coordinates, using fixed4x4 Gauss quadrature. All aperture corners must fit the declared model domain. No image resampling forms the fit input. R/B use their actual sites; green uses both actual green sites while retaining six independent acquisition IDs.

Original noise variance comes only from the injected model evaluated at a frozen source-specific expected signal. The first controls use an explicitly known latent oracle. A future actual guide must trace Q0/Q15 original taps, clipping and support at each target original site, and retain its plug-in-model limitation. No held measurement sets its own inverse variance.

## Leave-acquisition-out score

For each held source, unregularized WLS uses only the other five original acquisitions. Column scaling is numerical only. With N=A_train^T D_train^-1 A_train, the linear held prediction has covariance A_hold N^-1 A_hold^T. The full residual covariance adds D_hold, including off-diagonal training-prediction covariance. Whiten with that full matrix. Retain every held residual and every fold separately; the six folds share training photons and are not iid replicates.

Across25 structurally disjoint patches, conditional Gaussian quadratic envelopes use fixed t=log100. A whitened noncentral discrepancy interval entirely below0.5per held degree of freedom is consistent with this model; an interval entirely above is inconsistent; overlap is UNKNOWN. This is a specified operating point, not a calibrated real probability. Require a positive lower energy bound for the full-minus-restricted prediction exceeding one held-noise energy, using its actual shared-training covariance. This is operator-detail support, not a universal spatial bandwidth or optical-resolution proof. Flat/weak detail remains UNKNOWN even when residuals are small. All structural/support failures are retained; no survivor-only region score.

The typed research outcome is `ForwardModelConsistent`, `ForwardModelInconsistent`, or `Unknown(reasons)`, with separate geometry/model/detail evidence. It never sets product admission or fabricates a sweep focus field. A stable common defocus may remain consistent with a common field, but cannot be called sharp. Coherent RGB evidence needs all three colors and all six acquisition folds, not favorable averaging of results.

## Controls frozen before execution

Flat first. Independent analytic aperture integration and nonidentity/CA absolute-sensor mapping oracle; constant/linear reproduction; zero or invalid variance, duplicate identity, guide overlap, missing or clipped original support, changed held photons leaving that fold's training prediction exactly unchanged. Then known same-PSF phase-diverse nonbasis sinusoidal/color texture beyond a single CFA's sampling band; independently constructed nonperiodic edges/texture report model misspecification rather than claiming source PSF contradiction.

Retain unequal Gaussian PSF, channel-only blur/motion/illumination, fixed wrong phase/geometry, drift (including phase-correlated drift), opposite texture, and strong common low-pass/null plants. Same-count duplicate/one-axis phase geometry must not certify reconstruction information. A same-count native bilinear original-sample prediction baseline uses the same five sources and known interpolation noise; it is a causal blur/alias foil, not a reference truth. Positive raw prediction must be assessed alongside known-signal response and per-color error, so a blurred prediction cannot win by low residual alone. Keep all seeds192..199, patches, colors, sources and failures.

Resource cap is4workers/4GiB, with explicit bounded model/sample counts and serialized or bounded patch work. No real RAW/cache campaign is released by this protocol. A later real pilot requires the complete source/guide/footprint identity chain, measured support, and parent release.
