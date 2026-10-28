# Original-CFA output consumer: one bounded architectural question

Root allocation, 2026-10-27, while the complete V3 comparator is rendering.
Source-only; no new numerical job or implementation release. This does not
assume the comparator will improve the photograph.

Root ran unified and mechanical searches for joint MHC / composed kernel /
RGB gather, and read BUILD-DEMOSAIC and M95-demosaic. BUILD-DEMOSAIC already
contains a one-demosaic RGB-warp arm and measured errors from remosaicing and
the second demosaic. It did not build a complete replacement stacker, and its
error findings do not prove a gain on this weevil. M95 shows why more high-band
energy or reduced chroma difference cannot stand in for genuine detail. The
current direct-lattice, local-fit and band-residual failures remain relevant.

The exact question is whether an output RGB consumer can evaluate a composed
linear reconstruction row directly against original u16 CFA samples, accumulate
noise-gated source/band contributions in f32, and deliver camera-linear RGB
without an intermediate aligned/remosaiced/rounded CFA image or final second
MHC. A conceptual row is a weighted sum over original source sensels of a
declared color reconstruction and geometry kernel. Do not hide the fact that
such a row may algebraically factor into per-source MHC plus interpolation;
algebraic fusion alone neither removes that interpolation bias nor proves the
user's native-RAW/demosaic-once contract. Identify the actual information
preserved, lost, invented and counted in each candidate interpretation.

This is not an assumed-PSF inverse, a new chroma smoother, an argmax reference,
or permission to fuse developed sRGB in the native engine. A learned RGB guide
could be considered only as focus evidence; actual reconstructed values must
come from original CFA and the one injected noise model. A learned probability
map is not itself a calibrated noise gate. Preserve different-depth bands;
the previous whole-value scalar-mixture counterexample must remain explicit.

Owners:

- cfa-residual writes `operator-audit.md`: locate the existing once-RGB arm and
  current consumer, state the smallest actual operator change and its relation
  to the strict storage/reconstruction contract. Give one concrete feasible
  route or explain why the proposed composition is merely renamed old work.
- integration-review writes `independent-contract-review.md`: independently
  challenge native-RAW claims, single-source behavior, cross-color and shared
  covariance, actual sampling/resampling count, and the different-depth
  preservation requirement. Reuse prior evidence rather than invent new tests.
- root chooses any later implementation only after these concise reviews and
  the complete photograph. No source edits outside these two reports, no
  RAW/image decoding, model inference, new dependency or numerical experiments.

The requested outcome is a concrete go/no-go architectural answer, not a survey
or a broad family prohibition. Keep it short enough to act on immediately.
