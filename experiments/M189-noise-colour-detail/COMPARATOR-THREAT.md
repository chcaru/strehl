# M189 comparator threat audit

Status: **ADAPTIVE DENOISE/RE-NOISE IS UNKNOWN FOR PROPRIETARY COMPARATORS,
NOT SHOWN PRESENT**

Date: 2026-09-05

This audit asks only whether the measured M189 adaptive attack is known to be
part of the named comparison. It does not infer proprietary implementation
details from output appearance and does not reverse engineer a binary.

## Zerene Stacker

The official Zerene FAQ describes:

- PMax as a pyramid method that preserves fine detail but tends to **increase
  noise and contrast**;
- DMap as a depth-map method that better preserves smoothness but retains less
  detail
  (`experiments/M132-blocker-d-routes/zerene-faq.html:1191-1203`);
- DMap's contrast threshold as a way to mark regions where smoothness should be
  preferred over pixel noise mistaken for detail
  (`experiments/M132-blocker-d-routes/zerene-faq.html:1242-1250`); and
- PMax “grit suppression”, enabled by default, as sacrificing some finest-scale
  detail to obtain less output noise
  (`experiments/M132-blocker-d-routes/zerene-faq.html:1404-1409`).

The same FAQ says noise copied from PMax into DMap by retouching becomes visible
because PMax is the noisier output
(`experiments/M132-blocker-d-routes/zerene-faq.html:1528-1536`). That wording is
consistent with propagating or suppressing source noise, not replacing it with
fresh calibrated noise.

**Ruling: UNKNOWN, NOT EVIDENCED.** Zerene publicly documents adaptive
noise/detail tradeoffs, including a default noise-suppression option. It does
not document estimating a clean signal and then synthesizing fresh
signal-dependent noise. Public documentation cannot prove that a proprietary
implementation omits an undocumented step.

The default PMax grit-suppression path is close enough to the first half of the
M189 attack that actual licensed PMax and DMap outputs must be tested. It may
not be declared absent from documentation alone.

## Helicon Focus

The official Helicon 9 guide describes:

- Method A as contrast-weighted averaging;
- Method B as sharpest-source selection through a depth map; and
- Method C as a high/low-frequency pyramid method
  (`experiments/M132-blocker-d-routes/helicon-help9.html:523-531`).

Radius and Smoothing trade fine detail against noise, halos, and transition
artifacts (`experiments/M132-blocker-d-routes/helicon-help9.html:650-692`).
The raw-development “Noise threshold” is explicitly a **noise removal** control
whose cost can be lost fine detail
(`experiments/M132-blocker-d-routes/helicon-help9.html:1042-1071`).

The frozen scorecard requires Helicon's built-in post-sharpening, denoising, and
auto-adjustment to be neutral/off. It likewise requires Zerene output
contrast/brightness/sharpening neutral/off
(`docs/proposals/2026-09-sota-scorecard.md:477-505`).

**Ruling: UNKNOWN, NOT EVIDENCED.** No committed official Helicon material
describes fresh noise synthesis or calibrated re-noising. The documented
stacking methods are averaging, selection, and pyramid fusion; an optional
raw-development denoiser exists but is excluded by the scorecard settings.
Proprietary internals remain unaudited.

## strehl

The scored strehl executable is source-auditable and hash-freezable. Its
shipping merge help states that the default path does not deconvolve
(`crates/strehl-cli/src/main.rs:175-205`). Synthetic noise generation reachable
from the plugin crate is host-side focus-operator calibration: it runs lazily
only when a contributed `--focus` surface is requested, and the default path
never constructs it or draws a seed
(`crates/strehl-cli/src/focus_plugin.rs:1-34`;
`crates/strehl-cli/src/merge_cmd.rs:3060-3090`).

The default pyramid merge does use a calibrated noise model for selection and
averaging. That is not denoise/sharpen/re-noise: no fresh noise field is emitted
into the image. The scored source commit, settings, and executable hash can
freeze that absence.

**Ruling: ABSENT BY AUDITABLE CONSTRUCTION for the scored default**, provided
the run manifest excludes experimental restoration paths and contributed focus
operators exactly as the scorecard requires.

## Threat-model conclusion

| arm | adaptive denoise followed by fresh calibrated re-noise |
|---|---|
| strehl scored default | **Absent by source/configuration audit** |
| Zerene PMax | **Unknown; no public evidence of re-noising, but documented default grit suppression requires an output test** |
| Zerene DMap | **Unknown; no public evidence of re-noising** |
| Helicon A/B/C | **Unknown; no public evidence, and explicit post-denoise is frozen off** |

The attack is therefore a **declared unexcluded proprietary-internals
limitation**, not a demonstrated operation of the named comparators. A claim
must not say “robust to arbitrary renderers”. It may say “commissioned against
common linear post-filters; adaptive denoise/re-noise was not found in public
comparator documentation and remains unexcluded pending licensed-output
testing.”

