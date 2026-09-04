# M164 M2 repair — preregistration amendment 1

Status: **FROZEN BEFORE THE SECOND EXECUTION**

The first registered execution passed G0–G9. No existing arm, threshold, seed,
or interpretation changes. This amendment adds two tests needed to make the
M1 dependency explicit rather than merely verbal.

## G10 — blur-plus-denoising trade

Add a fresh-output arm with pre-noise Gaussian sigma `1.05 px` and downstream
noise RMS `0.15`, versus the baseline sigma `0.65 px` and noise RMS `0.45`.

Frozen expected result:

- `Q_EIN` q95 `<0.80` (the noise coordinate can prefer the trade); and
- transfer-ratio q95 `<0.70` (the arm has materially lost transfer).

Interpretation: `Q_EIN` is a noise coordinate, not an admissibility gate. M1
must reject the lost-detail arm. This is the counterexample to any claim that
truth normalization alone makes M2 independent of M1.

## G11 — same-resolution cross-fit residual kill probe

Test the scorecard-shaped alternative `MAD(BP(O-R))` in a spatial simulation.
The held-out reference `R` has the same capture transfer as the baseline
output. Compare:

- a pre-noise optical blur, sigma `1.05 px`;
- a genuine pre-noise optical improvement, sigma `0.30 px`; and
- a same-transfer denoising improvement, output-noise RMS halved.

The registered radial band is `0.15–0.35 cyc/px`. The probe uses `64`
independent `128x128` trials and the same seed family as the main
commissioning.

Frozen expected result:

- blur cross-fit residual ratio q05 `>1.10`;
- genuine optical improvement cross-fit residual ratio q05 `>1.10`;
- the optical-improvement truth-error ratio q95 `<0.90`;
- the blur truth-error ratio q05 `>1.10`; and
- same-transfer denoising cross-fit ratio q95 `<0.90`.

Interpretation: replacing the output-only residual with `O-R` can catch blur,
but it labels a real optical improvement as more “noise” whenever `R` carries
the old optical transfer. That fails the mandatory improvement arm and cannot
be the M2 repair.

