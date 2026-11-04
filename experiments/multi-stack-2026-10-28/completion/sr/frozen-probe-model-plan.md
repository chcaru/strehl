# Frozen-probe translation/similarity diagnostic

The independent next-instrument review proposed a two-parameter residual
translation against the four-parameter local similarity. First test the model
choice on already frozen seed NCC observations. This is a mathematical
diagnostic, not a production registrar or a photographic candidate.

Prior-art searches actually run: `python scripts/research.py search residual
translation registration` and `python experiments/ORCH-drift-check/prior_art.py
residual translation registration`. M6 reports focus-dependent correspondence
residuals; its related historic causal claims must be read with M23/fact174's
resampler-confound amendment. M-PHASE0-SPLIT2 already demonstrates that small
translation residuals need not mean reliable nontranslation behavior. The
m193c fixed-coarse-representation decision distinguishes an instrument failure
from absent shared geometry and rejects a past blur-equalization recipe.

Use every17 diagnostic seed patch from the two previously frozen insect ROIs.
Fixed seed eligibility requires original support, the unchanged information
gate and NCC Ok. Both models use exactly the same eligible training patches,
unit weights, at least four patches, no outlier pruning and no held-out input.
Keep saved scale/rotation in the translation arm; fit the additional complex
linear residual only in the similarity arm. Evaluate both on every eligible
held patch, in anchor sensor units. Record missing held coverage separately;
four held sites and the unchanged0.15sensor criterion are required for the
descriptive all-four consistency count. No best-of-model selection follows.

The script runs constant/translation positives before reading any real JSON.
Scale/rotation must expose translation misspecification; checkerboard-invisible
curvature must fail both models on held sites. Degenerate rank and insufficient
count refuse. An independent absolute-sensor calculation checks nonzero complex
placements, physical color-site offsets and off-center crop conjugation.
These controls validate the coordinate algebra and conditional model fit, not
the accuracy of the already measured NCC observations.

This one-pass fixed-observation comparison differs from the engine's repeated
warped-probe/refit path. It cannot justify a model promotion, source certificate,
new support or a photographic gain. Any promising result still needs the full
original-CFA estimator controls with actual search footprints, measured curved
trajectories, wrong maps, periodic textures, changing PSF and signal/noise tests.
The raw data and ordinary rendered outputs remain unchanged. Resource scope:
one Python worker, small existing JSON only; no RAW, image or cache loading.
