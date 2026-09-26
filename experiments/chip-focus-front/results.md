# Predictive front: fine-band support, failed overall gate

MEASURED, 2026-09-25. The registered two-band admission is false. All42sites
are informative and both optimizers finish away from the registered bounds,
but the coarse-band p90 and lower-colour witness fail. Do not call the chip
nonplanar from this shared-width Gaussian model failure. No photograph is
produced by this experiment.

Root commands executed with the installed Python3.12:

```
python -I -B -X faulthandler experiments/chip-focus-front/run.py --out experiments/chip-focus-front/controls-job-1 -- experiments/chip-focus-front/independent-controls.py --model experiments/chip-focus-front/model.py --out experiments/chip-focus-front/controls-1.json
python -I -B -X faulthandler experiments/chip-focus-front/run.py --out experiments/chip-focus-front/stage-job-1 -- experiments/chip-focus-front/stage.py --out experiments/chip-focus-front/stage-1
python -I -B -X faulthandler experiments/chip-focus-front/run.py --out experiments/chip-focus-front/fit-job-1 -- experiments/chip-focus-front/fit.py --stage experiments/chip-focus-front/stage-1 --controls experiments/chip-focus-front/controls-1.json --controls-job experiments/chip-focus-front/controls-job-1 --out experiments/chip-focus-front/fit-1
```

Generated commissioning passes in1.984s: a nonuniform planar positive, exact
and noisy flats, genuinely2D bowl, two-depth mixture and two wrong-front
destroyers. The positive shares the fitted Gaussian family and validates only
the fitter. Bowl and mixture fail actual held prediction with coverage, not
only optimizer status. Three source-address/filter controls also pass before
photographic reads. See independent-controls.py and independent-plan.md.

One metadata-only preflight initially required exact identity at reference149.
The saved map differs at f64 rounding scale; the repaired preflight preserves
the exact map and bounds its identity displacement by4.834e-13 native pixels.
No rescaling or gauge change occurred. The failure preceded source reads.

Stage1 finishes54.250s; one fit finishes0.656s including process overhead.
These are operational observations, not speed comparisons. All299existing
CA-off same-developer TIFFs contribute all42fixed patches; no original RAW
was opened. Saved input identities and full TIFF hashes are retained from the
earlier development, current metadata is checked, and actual extracted values
are hashed. Current full TIFF contents were not rehashed. Toned/interpolated
power is a proxy, not RAW DN or physical noise. No frame-axis filtering occurs.

| Held prediction relative to even-calibrated constant | Fine | Coarse | Bar |
| --- | --- | --- | --- |
| Aggregate RMS ratio |0.216691|0.383811|<=0.50|
| Per-site p90 |0.371581|0.795418|<=0.75|
| Worst named witness |0.376171|0.874074|<=0.75|
| Worst held grid block |0.352752|0.437100|<=0.65|

All19training and23held sites have temporal modulation in both bands. Every
fine-band witness passes. The coarse worst witness is lower-colour. The frozen
fit uses15primary evaluations and10secondary evaluations, with no restart.
Prediction error can reward flattening noisy curves; informative-site checks
and the constant comparator constrain that failure, not image quality. No
sharpness or sigma claim follows.

The original prediction/photographic admission remains false. Root separately
commissions one native radiance observation in chip-focus-radiance/charter.md,
based on the narrower fine-band held-site result. That explicit scheduling
decision neither passes the old gate nor calibrates a coarse-band PSF. No
parameter rescue or default change is authorized.
