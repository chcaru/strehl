# Fixed in-focus consumer: independent checks

Prospective, read-only, no optimization or parameter choice. Root executes;
the controls author does not run or verify these controls. This is a new output
question after the pinhole failures, not a repair of their original verdicts.
The supplied synthetic sigma0.7 is not camera calibration. Earlier physical
64-versus1024 pupil inadequacy and unchanged held-out predictions remain visible.

The target is the original composed pinhole truth passed once through the exact
supplied f32 sigma0.7, radius3 normalized separable PSF. Apply it on full96x96
arrays before the unchanged whole16:80 domain and original nested boxes. All
four inverse arms and the latent far-only inverse get exactly one application.
The observed mean and retained training-only donor already contain the sensor
PSF: their files remain byte-identical, without further filtering or donor
reselection. The retained donor is not the optimum donor for this new target.

## Commission before delivery

An independent SciPy implementation constructs the seven coefficients and uses
explicit zero padding with y-then-x passes, versus the actual Torch x-then-y
consumer. Constants, a central RGB impulse and signed nonconstant input check
full output, channel separation, unit mass and input immutability. The fixed
arithmetic bound is32 times f32 epsilon times max(1,maximum input magnitude),
covering kernel normalization, two seven-tap reductions and reversed order.
It is not an image-quality allowance. A focused one-layer forward supplies an
additional supported consumer witness. Frozen independent generator `psf` uses
nearest padding; check full96 inputs through both filters on16:80, where neither
boundary can reach. Do this for truth and every signed template/absent image.
No existing generator or model source is changed.

An impulse at native(15,35) demonstrates the real context lost by filtering the
cropped16:80 image; the wrong shortcut must differ by more than1DN. Alternating
coverage together with varying near radiance demonstrates the incorrect
filter-sheets-before-composition shortcut; supported difference must exceed
100DN. These are mechanical destroyers, not photographic quality evidence.

True-detail commissioning uses fixed layered truth with once-filtered glint and
glint-free ridge templates. Each no-component background is separately filtered
from the full latent truth minus that full latent template. A separate half
removal in each RGB channel must recover0.5 in that channel and violate the
same per-colour0.98 capped-reference component guard used in actual comparisons.
The ideal once-PSF target is the commissioning reference (recovery1); actual
outputs instead use filtered visibility1 as reference. A second identical PSF
on that target must violate this0.98 detail guard for both fixed components.
If it does not, save an inadequate-instrument result and stop before delivery;
never change sigma, ROI, reference or threshold. R/B-swapped truth before
filtering must also fail the coloured-ridge component and exceed100DN chroma
error. This guards against interpreting smoothing or colour loss as improvement.

## Fixed saved-output scoring

Bind all16 source/output files, original latent receipts, actual kernel bytes,
frozen controls/model, and old scored results. Assert exact geometry and one
PSF for latents versus zero extra for observations. Check every filtered output
against independent full-context convolution. Verify input/output files before
and after. No new raw prediction or fit is performed.

Flat is first. Both RGB and chroma RMSE must be at most1.05 of the unchanged
observed mean and at most1.05 of filtered visibility. Layered absolute bars keep
their old form: whole/core/ridge RGB at most0.90 observed mean (mean error>1DN),
whole/crossing at most0.95 filtered latent far-only, core/ridge at most1.05
far-only. That far-only fit is the restricted historical comparator, not a
claim about the best possible one-layer model. Glint and ridge components must
remain live in every colour, capped recovery at least0.8 and at least0.98 of
the retained observed donor. Donor projections are recomputed against the new
filtered template and separately filtered absent background, never reused from
the old pinhole scores.

Paired core and ridge RGB AND chroma must be at most1.02 filtered visibility1.
Each glint/core and ridge/glint-free-segment colour must retain at least0.98
of that reference's capped recovery; reference recovery below0.5 fails the
qualification. Existing ridge-detail box is native[39,31,63,41] half-open.
Overshoot cannot buy additional component credit. Component projections can
still be fooled by correlated error; all RGB/chroma guards remain alongside
them. RMSE can reward smoothing, hence the commissioned extra-PSF destroyer.
No arms or regions are averaged to erase a failure.

Report target-specific image bars separately from original pinhole verdicts,
retained raw held-out bars, optimizer status and physical adequacy. Also report
the conjunction of target bars with the unchanged held-out bars. No automatic
photo admission or optical-nullspace inference follows from this alternate
consumer. Whole generated scenes are required for visual interpretation by root.

Commands for root:

```text
python in-focus-controls.py commission --out <run/commission>
python in-focus-consumer.py --out <run/delivered>
python in-focus-controls.py score --candidate <run/delivered> --out <run/scored>
```

Root requires commission/result.json `passed` before the next command.
No numerical execution has been performed by this controls author.
