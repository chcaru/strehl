# Carry the useful placement correction to the merge

Decision recorded after the fixed four-update photographic rejection, before
any new consumer execution. The current useful intervention is the local
green-based placement correction, demonstrated with the same eight-frame mean.
It is not yet a product improvement.

The next test must use the actual native gather and pyramid consumer, with
both arms consuming frames 146 through 153 from the same saved original CFA
patches, reference 149. The only treatment is adding the measured source-native
translation to the existing pull map within the nominated crop. It must never
publish a whole-image map fitted on this crop. No original pixel decode, new registration
fit, reconstruction variant, threshold change or iteration sweep is authorized
by this experiment design.

The implementation route is under review. Existing `BandWorker::fold` and
`PyramidDomain::cropped` may make a test-only local consumer possible. Seven-band
boundary context, source support, chromatic correction, gate-floor probes and
the distinction between a local merge and a crop of a whole merge must be
resolved before an image can count as evidence. A source buffer populated only
inside retained CFA rectangles must prove, by changing every unsupported value,
that unsupported data cannot affect its scored output. If this cannot be
established, reject that adapter rather than call its result a product render.

The test can fail: correction may reveal no useful separation, amplify colour
artifacts, or change only low-frequency appearance. A lower registration or
prediction residual does not pass it. Both root and an independent image
reviewer must compare unchanged and corrected native images; the reviewer must
look for lost as well as restored structures. Synthetic flat noise remains an
operator control, not evidence that a textured region of the photograph is
featureless. Retain the unchanged source MHC as a visual reference, not truth.

Stop this local integration if the existing consumer cannot safely consume the
saved footprint without expanding the input scope. Do not turn adapter plumbing
into another research campaign. An accepted crop result would justify a
subsequent spatial refinement implementation and a second-scene test, not a
default promotion or SOTA claim.

## Pre-execution integration review

The existing cropped consumer is available without a new production algorithm.
Its 392 native pixels are 196 CFA-plane pixels; current `level_sizes` gives
196, 98, 49, 25, 13, hence four Laplacian levels and a base band. This cannot
reproduce the full seven-band baseline. The commissioned run is explicitly a
four-level consumer diagnostic, to decide whether the useful alignment change
survives the actual gather, noise propagation, band weighting and collapse.
It makes no claim about full-stack scale context. Output dimension and actual
level count must be asserted and recorded.

Use the existing in-memory frame handoff, full sensor coordinate system and an
explicit cropped domain. Add half the measured source-native translation to
the in-memory map's plane-coordinate translation; leave the reference fixed.
Current gear-matched chromatic correction and noise probe are retained. Both
arms must prove complete real-source support, and every collapsed value and
developed output must be identical when unsupported filler changes from black
to white. No output image is admissible if this check fails. An independent
reviewer will inspect the adapter choices before execution.

This is the only additional integration run commissioned here. A positive
result would justify a later full-context test; a failure closes this small
adapter route without widening its scope automatically.

The current capture-identity lookup may read metadata from the original source
paths. This preserves the existing gear-matched chromatic correction without
introducing a test-only substitute profile. It uses the project's bounded
TIFF metadata reader and does not call the pixel decoder. The adapter receipt
must record the resolved body, lens identifier and profile. The source paths
remain read only; all image samples come from the retained u16 patches.
