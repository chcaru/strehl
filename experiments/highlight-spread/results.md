# Source highlight morphology, with interpretation limits

The fixed source-image profiles support focus-dependent spreading around the
facet highlight. The second nominated highlight mixes extended scene structure
and cannot identify an isolated point-spread function. This is a diagnosis of
source images, not an output improvement or a recovered optical kernel.

Commands run from the repository root using Python 3.12:

```
python -I -B experiments/highlight-spread/independent-controls.py --output experiments/highlight-spread/independent-controls-1.json
python -I -B experiments/highlight-spread/measure.py --out experiments/highlight-spread/run-1
python -I -B experiments/highlight-spread/replot.py --out experiments/highlight-spread/views-2
python -I -B experiments/highlight-spread/check-label-pixels.py
```

The measurement ran under the existing bounded process wrapper. Its command,
input and source bindings, resource accounting, and successful completion are
in `execution-1/`. **MEASURED:** 2.953 seconds of job wall time; all 140 saved
source-crop hashes matched and all source bindings remained unchanged. No new
RAW decode or stack render was run. Every bin contains 14–18 actual source
pixels. These are developed RGB16 display-code values under the held tone and
white balance, not linear sensor radiance.

**VERIFIED instrument:** independent coordinate and bin controls passed,
including a wrong-translation negative control, axis reversal, side-strip
displacement, populated versus empty bins, a constant field, and source-margin
refusal. Artificial stationary-amplitude and spreading profiles are
distinguishable. This checks the measurement's mechanics; it does not validate
the assumption that a photographed feature is a point source.

**VISUALLY OBSERVED:** the facet's centre and both side strips narrow around
the middle of the stack and subsequently spread. This is stronger evidence
than one bright ridge at one location. The dark feature branches and moves
differently across strips, activating the predeclared mixed-scene objection.
The real-structure control is faint on the common code-value scale; absence of
an obvious fan is insufficient evidence of precise stationarity. Root and the
independent reviewer agree on these limited interpretations. See
`results-review.md` for the independent account and falsifiers.

The original review incorrectly reported missing labels in two PNG files
after viewing several images together. **CORRECTION / VERIFIED:** direct PNG
pixel reads show nonblank, byte-identical selected label rectangles across all
three targets in both versions (`label-pixels-1.json`). The file-defect claim
is withdrawn; the cause of the viewing discrepancy is unestablished.
`views-2` is an optional alternative presentation of the unchanged saved
profiles, not a repair to numerical data.

Do not fit a shared optical kernel, claim axial chromatic aberration, infer
sensor saturation, or promote deconvolution from these plots. The next merge
candidate is instead a separately controlled source-colour reconstruction;
these profiles supplied no tuned coefficient to it.
