# Relevant limits from primary literature

Read September19 while separating source assignment from reconstruction.
[Jacobs, Baek and Levoy, Focal Stack Compositing for Depth of Field Control,
Stanford technical report2012-1](https://graphics.stanford.edu/papers/focalstack/focalstack.pdf)
provides two useful cautions. Section4 says some contrast-derived depth maps
were manually corrected. Section6 distinguishes smooth transitions from choosing
the correct source. Therefore successful feathering does not validate a depth
estimator. Figure14 also demonstrates that clipping a focused specular core
loses brightness needed to predict its defocused appearance by synthetic blur.
Therefore an observed change in thresholded highlight mass is not independently
measured photon loss, and a constant-flux model is unsafe without RAW headroom.

These are literature limits, not evidence of the cause of the vitamin-C tail.
The current RAW counterfactual and its controls remain the relevant experiments.
No external implementation or prohibited repository source was read or copied.
The proposed concentration locator remains conditional and is explicitly a
display-space discriminator; it does not infer sensor noise or clipping from
the developed TIFFs. No new radiance or lens calibration is justified here.
