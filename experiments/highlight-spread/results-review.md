# Independent source-morphology interpretation

**Decision:** the facet plot supports focus-dependent spreading as a descriptive
source-image phenomenon. The dark-glint plot does not establish an isolated
point source. Neither licenses a physical PSF, deconvolution kernel or output
quality claim.

**VERIFIED instrument:** `independent-controls-1.json` passes all coordinate/bin
controls: 432 colour means, 144 populated bins, maximum coordinate error
4.55e-13 native pixels, signed-axis reversal, side-strip displacement,
constant/empty bins and the exact source-margin boundary. The artificial
amplitude-only and spreading examples remain distinguishable, and an unrelated
side object appears in its own strip. This verifies assignment, not optical
identifiability. Root's recorded `measure.py --out .../run-1` execution completed
in 2.953 s job wall time; `execution-1/completion.json` confirms unchanged source
bindings. All 140 original crop hashes match, and each actual bin contains
14–18 source samples. The retained arrays and receipts require no new run.

**VISUALLY OBSERVED, fixed plots:**

- **Facet glint:** the centre strip and both side strips share a conspicuous
  narrowing around the middle of the sequence, followed by extension outward
  along the fixed longitudinal axis. The late positive-distance coloured arm
  is strongest in the centre strip, with different breadth/colour in the outer
  strips. This defeats the simple explanation of one stationary ridge merely
  brightening in one strip. The neighbouring strips broadly corroborate spread,
  without establishing an isotropic or separable point-spread function. They
  contain different local content and do not share one identical profile.
- **Dark glint:** the bright component is broad and displaced along the positive
  axis; its position, width and branching change differently across the three
  strips. The nominated core lies near a dark/bright boundary rather than an
  obviously isolated, compact point throughout the sequence. This activates
  the predeclared mixed-scene/strip-inconsistency falsifier for interpreting the
  entire trace as one glint's PSF. It remains compatible with some real defocus
  spreading, but that component is not separated from extended or neighbouring
  scene structure here.
- **Real-structure control:** there is no similarly conspicuous coloured fan
  on the same fixed code-value scale. However, the retained structure is faint
  on that scale. This is weak evidence for precise stationarity; it cannot
  establish that an informative stationary feature survived visibly enough to
  validate the desired comparison. Do not turn the absence of an obvious trace
  into proof that all geometry is correct or that only highlights spread.

**Plot defect:** `facet-glint.png` retains distance ticks, frame-index ticks and
transverse-strip labels. In the actual `dark-glint.png` and
`real-structure.png`, those labels and numeric ticks are absent. Channel titles,
target titles, core line and colour scale remain visible. Their intended axes
can be read from the fixed plan/array receipt, but the two PNGs are not
self-contained figures. This is a presentation limitation, not evidence that
the saved profile arrays changed; no plot or numerical source was edited here.

These are developed RGB16 display-code means with held tone and WB, not linear
sensor radiance. Different channel traces do not identify axial CA or RAW
saturation. Imperfect local placement, transparency and mixed depth remain
possible contributors. The defensible result is therefore narrower than a
general optical model: one highlight gives coherent spreading morphology;
another visibly confounds it; the structure control is low contrast. No new
positions, fitted scores or scientific gates were introduced in this review.

## Correction: original PNG label-defect claim withdrawn

Root subsequently inspected the original PNG pixels directly with PIL. All
three targets have 870 dark pixels in label rectangle (160,990,460,1030), with
identical SHA256 prefix `e345ed629a2e`; rectangle (5,430,140,710) has 640 dark
pixels and prefix `5998429a1c49` in each. Replots also retain identical nonblank
labels. This contradicts and withdraws the **Plot defect** paragraph above:
the original files contain their labels. The apparent omission occurred while
this reviewer viewed multiple PNGs together; its cause has not been established.
This correction changes no numerical or source-morphology interpretation.
