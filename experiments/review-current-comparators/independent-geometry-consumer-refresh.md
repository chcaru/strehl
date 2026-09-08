# Independent geometry-consumer refresh read

2026-09-08. Bounded primary-paper/local-record review of
geometry-consumer-refresh.md at ebecc288, Git blob
90614b2cbf4d610226bd5517d6cf2ef61e6bdcf7; current SHA256
1b0c4ab0253563919b111bc32baf56f4ab82a7d6f64ac5a256d8dd724747c289.
The local file matches that committed blob. No external repository source,
model, dataset, PDF, image payload or new experiment was opened/executed.

Verdict: the narrow current-input decision is supported. Preserve the distinction
between unavailable evidence for these existing stacks and lack of advancement
in the wider field. The final paragraph should be read as the former.

## Primary evidence and changed choice of consumer

VERIFIED PAPER CONTENT: FOSSA is the model in Zero-Shot Depth from Defocus;
ZEDD is its benchmark. Section3.1 takes aligned RGB images, static viewpoint and
metric focus distances and returns metric depth. A1.4 chooses a3.08 m canonical
focus setting, estimates image warps from F/16 captures and transfers them to
wider-aperture frames at the same focus settings because direct wide-aperture
alignment is unstable. A6 retains motion/handheld alignment as future work.
The paper therefore contains a real acquisition-based alignment step, not an
alignment-free solution. [Primary HTML,3.1/A1.4/A6](https://arxiv.org/html/2603.26658v2).
Submission/revision dates are27 March/27 June2026, respectively.
[arXiv history](https://arxiv.org/abs/2603.26658).

INFERENCE: those capture-time transforms could in principle supply per-frame
sampling maps after validating their coordinate mapping, transfer and accuracy.
They are not available evidence for the already captured M193c stacks. A depth
array in one canonical image is not itself a collection of reference-to-sensor
maps. The paper does not establish RAW macro placement in strehl's gauge.
This limitation leaves its depth-generalization contribution intact; it does
not justify a general no-advancement claim or permanent exclusion.

VERIFIED PAPER CONTENT: VideoDfD4.1 compensates focus differences using its
current depth/all-in-focus estimates, then uses patch correspondence. It
explicitly accepts visually similar patches from geometrically incorrect sites
for its defocus-preserving objective. The memo's description is faithful.
[Primary HTML,4.1](https://arxiv.org/html/1610.03782v1#S4.SS1).

INFERENCE: this is useful evidence about a different objective, not a physical
placement oracle. Incorrect-site correspondence can reduce an appearance cost
without validating the material gathered into a RAW merge. It also does not
prove that every correspondence, initialization or blur-aware component from
that method is unusable. The paper's complete iterative refocusing system is
not identical to M78's Gaussian cross-blur arm.

## Local record and scope of negative evidence

VERIFIED LOCAL TEXT, no numerical rerun: M78 summary and sections3/4 report both
registered arms failing their strict6.758 plane-pixel held-out criterion.
Section7 confines the decisive test to coffee-bean, treats112MSDCF as a
no-defect placebo, and limits Arm A to its Gaussian model/rate and Arm B to its
bilinear phase treatment. The mechanism plant's failure is not a refutation of
all content-dependent blur mechanisms. The root memo correctly says the same
old arm should not be repeated unchanged; do not broaden this to all blur
compensation. [M78](../../docs/research/M78-blur-equalised-edges.md).

M103 section3 explicitly recognizes the previous R4/R5 attempts and the
pairwise criterion's inability to settle global gain. Its section16 correction
is essential: the merge gathers each frame at its own transform. On the same
39-rung ladder, mean per-frame placement in the rung144 gauge reads36.4 to37.5
plane pixels while the endpoint residual changes150.3 to2.9. The numerical
reproduction is not repeated here. The operative reference is149; rung144 is
the nearest measured gauge, not an interchangeable frame0 reference. The
curved-track requirement and gauge disclosure in the memo match this amended
record. [M103,3 and16](../../docs/research/M103-halfdrift.md).

The2015 Mobile Phone paragraph is outside this read's full-text verification:
primary HTML search results provide its abstract; the opened CVF HTML endpoint
returned403 and no PDF was opened. I have not independently verified its
section4 affine/concatenation sentence. That sentence is unnecessary to the
consumer conclusion above and should retain its original limited read provenance.

## Precise disposition

ARGUED wording for the root conclusion: these papers do not currently provide
validated per-frame geometry for the existing M193c stacks. They remain relevant
advances in their own tasks and sources of ideas whose prerequisites differ.
No new method, capture or experiment is selected by this note. Operational
checker refusals must remain separate from scientific estimator evidence; this
review does not update the pending local probe's numerical disposition.

Read scope: primary arXiv HTML sections named above and arXiv date history;
primary CVF HTML search/failed open; targeted M78 and M103 report text. A broad
initial local search truncated, so the conclusions use subsequent exact-file
reads. No external implementation, model or dataset intake and no subject run.
