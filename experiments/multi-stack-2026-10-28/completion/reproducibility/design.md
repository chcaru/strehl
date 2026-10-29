# Reproducible structure inspection

Allocation: multi-stack-2026-10-28-completion-reproducibility. This is an optional
inspection tool, not a tuning score or automatic resolution certificate. Its
positive outcome is an explorable spatial map and frequency curve of repeated
structure, together with support, independent-acquisition and focus-compatibility
qualifications. Values do not change the photograph.

Primary sources consulted: [van Heel and Schatz, 2005](https://pubmed.ncbi.nlm.nih.gov/16125414/),
[Koho et al., 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6629685/).
The former challenges universal fixed correlation thresholds; the latter defines
the independent-noise paired-image construction. Repository prior evidence is
[M-FRC-VIABILITY](../../../../docs/research/M-FRC-VIABILITY.md): finite windows,
common processing, fixed-pattern noise and focus mismatch matter. None of the
microscopy acquisition assumptions automatically transfers to macro photographs.

The implementation exports the normalized real cross-spectrum in Fourier rings,
the two powers and ring sample count, using a fixed Hann window and weighted DC
removal. A narrow ring is not an independent-observation count. The scalar map is
a descriptive power-weighted correlation over a stated band, not a thresholded
resolution estimate. Raw signed correlations are retained. Paired relative RMS
disagreement and signal-power ratio expose changes that correlation alone hides.

Controls run first: exact flat, independent noisy flat, common deterministic
structure with separate noise, unrelated structures, duplicated acquisition IDs,
one-pixel displacement, one-arm blur, shared fixed pattern, and common blur or
sharpening. The common-processing and shared-pattern examples must demonstrate
the known blindness rather than be called passed resolution tests. Missing
support and incompatible focus produce an explicit unqualified patch.

No new per-stage sensor noise estimate is introduced. Where an injected noise
prediction is unavailable after adaptive reconstruction, the diagnostic must
say so instead of inventing variance. Full photographs and native crops remain
the photographic acceptance evidence; a favorable correlation curve is not a
replacement for them.
