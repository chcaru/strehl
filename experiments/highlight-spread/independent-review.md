# Independent coordinate and bin review

Pre-execution scope: validate only source-pixel coordinate assignment and the
reported RGB16 bin means/counts. Root executes; this reviewer reads no RAW or
photographic source pixels and changes no author implementation.

`independent-controls.py --output <new-json-path>` imports the sibling
`measure.py`. It independently plants a nonidentity similarity with scale,
rotation and source translation around the full native pivot (3516,2344),
including the cropped-output offset (56,38). Complex arithmetic serves as the
inverse oracle. Literal identity/translation checks catch a hidden half-pixel
shift or lost factor 2. A 224x224 integer RGB linear field is assigned by scalar
source-pixel enumeration into the actual signed intervals; all 144 bins must
be occupied, counts exact and mean error <=0.008 RGB16 DN (float32 rounding).
The expected value is the mean over assigned sample centres, not the analytic
field evaluated at a bin midpoint, which would be wrong on an affine lattice.

A cardinal fixture with a quarter-pixel core avoids half-open boundary ties.
Reversing the axis must reverse overlapping distance bins and swap outer side
strips. Moving the core 8 pixels along the positive normal must map its centre
strip onto the previous positive side strip. An unsupported tiny source patch
must return count 0 / NaN bins, not invented samples. A constant RGB field must
remain constant in every populated bin. The separate complete-support check
must admit the exact inclusive two-pixel margin and reject one just outside.

Fixed rectangles distinguish changed amplitude from changed spatial support:
a doubled stationary feature must retain its exact bin support, while a
four-times-longer feature with quarter amplitude must occupy 4x as many bins
at equal profile integral. These are deliberately transparent operator
examples, not simulated optics. An unrelated coloured object in a side strip
must appear in that strip without entering the centre strip. The measurement
can reveal such mixture; it cannot label neighbouring scene content as the
glint's PSF.

These controls do not prove that the held photographic transform is locally
accurate, that development preserves linear radiometry, or that either real
highlight is an isolated point source. The existing sources are developed
RGB16, and brightness/profile differences may combine defocus, geometry,
colour and other scene features. Interpret them as registered source
morphology. No PSF identification, deconvolution kernel, quality ranking or
new fusion rule follows from a passing coordinate test.

Execution is pending root's receipt. No author-source or fixture tuning is
planned after results.
