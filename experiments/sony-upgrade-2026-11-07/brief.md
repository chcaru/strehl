# Macro capture upgrade: physical opportunity and reconstruction

Owner: root. Date: 2026-11-07. User asks about 900 distinct fine-focus planes
instead of 300 native width-1 planes over the same depth, an A7CR body, and four
or sixteen pixel-shift exposures per plane. SD capacity is assumed adequate.
Targets are stationary in a cleanroom macro studio. Equipment: FE 100mm Macro
GM, Viltrox 2x, Breakthrough X4 CPL, KL1500 LCD with diffuser and light polarizer;
reported working aperture f/5.6, already inclusive of the converter factor.

Scope: a bounded analytical model and source-backed recommendation, not a
measured upgrade or new reconstruction. No changes to capture corpora, engine
defaults or SYNTHESIS. One CPU worker; no RAW campaign. Stop after checking
physical limits, existing algorithm status, source accuracy and model arithmetic.

Prior lookup executed: `python scripts/research.py search pixel shift diffraction --limit 5`
and `python experiments/ORCH-drift-check/prior_art.py 'pixel shift' 'effective aperture' 'focus breathing'`.
Read the current capture reference, M5 diffraction measurement, M84b ruler
metrology (including corrected Viltrox identity and nonunit pupil magnification),
the November 1 rejected breathing-SR experiment, current multi-stack docs and
the November 7 SDK audit/capture review. Earlier F-camera-lens-optics claims
based on p=1 or Sony-branded converter identification are superseded. New
question: equal-focus, deliberately two-dimensional sensor shifts, instead of
breathing diversity confounded with defocus and absent at the image center.

Consumer: a purchasing/capture-design decision. The model computes sensor-plane
optical MTF, sampling limits, exposure count and ideal noise scaling. Gauge is
line pairs/mm on the sensor; object-space figures require explicit magnification.
The range effective f/13.5-17 is a reference-capture estimate, not a new calibration
of the current slide or A7CR. Representative 40-micrometre focus spacing is an
illustration near the older ruler's 32-49 micrometre range, not a conversion from
today's normalized commands. Pupil aberration, camera spectral response, real
pixel aperture, coherence and optical drift remain outside the simple model.

Controls: ideal circular-pupil MTF equals one at DC and zero beyond cutoff;
quadrature at zero defocus agrees with the analytic expression; a finer output
grid alone leaves the optical/pixel-aperture transfer unchanged; halving total
photons decreases Poisson SNR. A threefold finer depth grid is compared at its
worst midpoint and at an already-in-focus plane (zero-gain placebo). These check
operators and arithmetic, not the supplied optical parameters. No sharpness
metric is run on photographs; flat-ROI and full-photo comparisons would be
mandatory for a future reconstruction claim. No independent review is claimed.
