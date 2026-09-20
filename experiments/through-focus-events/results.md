# Complete-sequence RAW association measurement

**MEASURED: a useful dark-region association, not a general ownership rule.**
All seventy original vitamin-C captures were measured through the held native
rounded GPU/CA gather. Signed RAW brightness changes connect the dark core to
its column and fan more strongly than to the nearby ridge. The facet does not
show the same relationship. Signed finest-Laplacian box means fail the spatial
sensitivity and real-structure controls. No automatic correction, photograph,
quality improvement or SOTA result is claimed.

The frozen plan names the inputs that can defeat the proposal: comparable
coupling at spatial nulls or the competing ridge, opposed colour signs hidden
by the joint statistic, independent permutation coupling, phase sensitivity,
or failure to recognize the known ridge continuation. Cosine can be inflated
by shared broad brightness changes; it measures neither optical ownership nor
focus. Its amplitude companion includes scene change and is not noise sigma.

Across the two fixed translations and full/checkerboard subsets, joint signed
DN cosine is 0.651–0.708 for dark core/column, 0.736–0.771 for core/fan, and
0.076–0.117 for core/ridge. All four full-box colour-plane signs support the
dark associations. But the plots show chiefly shared late broad brightening;
these numbers do not select the compact source33 or establish transport from
the core. Target reversal retains substantial association. Spatial nulls are
not brightness-matched, and the weaker ridge is not a matched-amplitude null.

Facet core/extension joint DN cosine spans −0.033 to +0.024, with R/B opposed
to the greens. Signed L0 dark-column cosine changes +0.182 to −0.116 after a
one-quad shift, while ridge-continuation L0 is near zero. Do not build a generic
signed-L0 selector from these observations. The independent interpretation,
including per-plane and null comparisons, is in `results-review.md`.

Commands actually executed by root, using the installed Python 3.12:

```text
python -I -B experiments/through-focus-events/independent-analysis.py --controls-only --out experiments/through-focus-events/analysis-controls-1
python -I -B -X faulthandler experiments/through-focus-events/run.py build --out experiments/through-focus-events/build-1
python -I -B -X faulthandler experiments/through-focus-events/run.py controls --build experiments/through-focus-events/build-1 --out experiments/through-focus-events/controls-1
python -I -B -X faulthandler experiments/through-focus-events/run.py export --build experiments/through-focus-events/build-1 --out experiments/through-focus-events/export-1
python -I -B -X faulthandler experiments/through-focus-events/independent-analysis.py --receipt experiments/through-focus-events/export-1/output/receipt.json --out experiments/through-focus-events/analysis-1
```

The analysis used workspace-local `MPLCONFIGDIR=experiments/through-focus-events/plot-cache`.
Fresh `Compiling strehl-cli` build: 175.391 s. Independent Rust arithmetic
controls: 0.281 s, one test passed with signed, parity, translation, invalid-input
and immutability cases exercised. Python arithmetic controls also passed their
coupled, opposed, independent, constant and colour-cancellation cases. These
commission the instrument, not optics. RAW export: 57.297 s, peak owned-process
committed memory 3,043,672,064 bytes; operational costs, not a speed comparison.

VERIFIED by executable assertions: original active-u16 and full gathered
known4/guide/variance hashes are identical before and after measurement for
every source. The four retained witnesses25/28/33/69 additionally match their
old full hashes, beta bits and every stored512-square field byte. All source
bindings, original file metadata and held map are unchanged. No final merge
is produced, so field immutability is the observer guarantee in this experiment;
it must not be represented as a new rendered-output on/off proof.

The original-headroom receipt remains bound: broad sampled core neighbourhoods
reach16383 at those four sources; other frames and exact branch stencils are
unknown. Guide variance is not four-plane covariance. Clipping, mixed structure
and the finite capture endpoint remain possible confounders. Checkerboard
subsets share spatial-filter context and are sensitivity checks, not independent
noise realizations. Common reversal is an algebraic placebo only.

Source author and independent control/analysis author did not execute the RAW
job. Root executed and inspected all three signed-trace plots. A separate
reviewer re-chose channel, sign, null and spatial-sensitivity interpretations.
The surviving dark-only association may inform a further hypothesis about
spatial support; it does not by itself supply automatic seeds or a donor.

Export receipt SHA256:
`86f067b8d887f44f18ff0a5e4c02c17f09c8f04ee15ef19663ca512eeb680508`.
Analysis result SHA256:
`355613b767ebf7ff9ddb53220b4bd3d2a7aa19faaa616bf9a22d6a5b3687c33b`.
