# Cached single-exposure chart decomposition

Root allocation: `multi-stack-2026-10-28-completion-sr-chart-decomposition`.
This is a bounded continuation of the reviewer's next-instrument proposal.
No threshold, fitter, reconstruction kernel or source cache changes are made.
The seed-only translation/similarity ablation was negative as a general remedy;
translation is not promoted into this photographic experiment.

Use the complete126-source HDR03 map, calibration and sealed chart census02,
with original-cache loading only, four workers and the existing2GiB bound.
The two physical192-square regions were frozen before SR: dot field at
sensor[4105,3245], and fine bars at[5305,1945]. The latter is the existing
192 region inside the complete-photo384 witness, not a new selected crop.

| Arm | Targets | Excluded guide acquisitions | Focus nomination |
| --- | --- | --- | --- |
| dot-short | 27 through33 | 26,34 | Original joint mode30/32 |
| dot-long | 90 through96 | 89,97 | Same original joint mode30/32 |
| dot-union | Both sets above | 26,34,89,97 | Exact earlier14-source nomination |
| bars-short | 31 through37 | 30,38 | Most frequent qualified short-pass mode34 |

The bar long pass has zero qualified focus sites in the sealed census; it has
no valid source nomination and therefore no reconstructed arm. Retain this
negative rather than selecting a convenient long neighborhood. Dot single-pass
arms have fewer observations; they diagnose exposure/focus mixing rather than
establish an equal-count comparison. Native fallback remains the same full
HDR03 output for every arm. Each guide is independent of its targets, but the
historical global geometry/focus/admission are conditional on target photons.

First run registration-only with the unchanged46quad/3grid/sigma1.2 geometry,
all original train/held footprints and0.15sensor bar, and export unresampled
original96-square same-color patches around mapped region centers. These
patches are in each original sensor gauge. Directional tapered spectra compare
sampled high-band energy with the injected noise model, with flat/noisy-flat,
known-frequency and deliberately aliased controls first. An original sampled
spectrum cannot distinguish above-Nyquist optical structure from its alias;
no physical cutoff or super-resolution claim follows from this diagnostic.

Then execute the same frozen arms with exact product RGB motion, direct CFA,
same-data bilinear-CFA plus one MHC, and unchanged native. Keep all refusals and
exact coherent fallback. Repeat the older14-source legacy arm to verify that
generalizing the harness to4..14targets/2..4guides did not change existing data.
Held-original scores remain conditional prediction only, with each evaluation
acquisition excluded from the corresponding numerical estimate. Inspect full
fixed regions under one display transform; blur/desaturation/phase foils must
not masquerade as signal recovery. A bounded gain would trigger a separately
scheduled complete original-source output. No full RAW render is released here.
