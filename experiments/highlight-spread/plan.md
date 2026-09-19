# Fixed source morphology diagnostic

This is a distance-versus-frame description of existing developed RGB16
photographs, not an output improvement, focus selector, calibrated PSF or
sensor-channel axial-CA measurement. No RAW is read and no Rust is changed.

Read the same 70 exports used by the frozen source-highlight scan. Recheck its
140 recorded 384-square crop hashes, source dimensions, byte lengths and mtimes;
do not hash the complete approximately 14 GB export collection. Bind the scan
receipt, original export receipt and held map. Reuse the map's exact transform
bits only to assign original source pixel centres to reference-output coordinates.
No source image interpolation, channel registration, exposure adjustment or
per-frame normalization is permitted.

The three fixed targets in reference output native coordinates are:

| Target | Core | Direction | Existing source window |
| --- | --- | --- | --- |
| facet-glint | 2624,2906 | -22,+39 | facet-edges |
| dark-glint | 3080,2150 | +22,+53 | dark-inclusion |
| real-structure | 3240,2070 | +22,+53 | dark-inclusion |

Normalize each direction to unit length. Signed longitudinal distance is
[-24,72) native pixels, in 48 fixed 2-pixel bins. Positive transverse distance
uses the left normal (-dy,dx). Retain three separate contiguous strips:
[-12,-4), [-4,4), [4,12). Each bin stores the mean of its original RGB16 samples
and its sample count. Means are descriptive; no gradient score, best-frame
argmax, spatial background subtraction, parameter sweep or fitted curve is made.
Require the entire transect footprint to remain inside its bound original crop
with two native pixels of margin. Empty bins refuse the actual run.

Save all RGB profiles/counts as compact arrays, full geometry/source provenance
as JSON, and one distance-by-frame figure per target. All channel plots use
the same fixed 0..65535 display-code scale; rendering uses nearest cells.
The central-strip RGB composite preserves relative display colour. These plots
are diagrams of binned samples, not resampled stack photographs.

The falsifiable interpretation is whether a continuous feature extends from
the compact glint toward the late-frame fan while the nearby real structure
stays spatially stationary and changes contrast. A separate stationary feature,
inconsistent neighbouring strips, or similar behaviour in the structure control
defeats attribution to one glint spreading. Apparent channel offsets are only
descriptive: MHC, the colour matrix, nonlinear tone/gamut/highlight development,
missing CA gather and imperfect held geometry prevent physical attribution.
No display endpoint is evidence of RAW pinning. Extended transparent features
can make PSF recovery unidentifiable even when these diagrams are readable.

Prior art read before this plan: BUILD-CHROMA (real axial offsets, prior defect
attribution negative), BUILD-HIGHLIGHT section13.5 (two confounded chromatic
sharpness measures), V-THESIS (failed direct PSF estimator measured tonal ramps),
M70 section19 (mixed depths imitate unusual focus responses), and M194e (shared
pupil model explicitly omits transparency, aberrations and spectral effects).
Mechanical search: prior_art.py axial longitudinal PSF pupil glint.

Independent controls own the coordinate/binning choices: nonidentity forward
similarity, exact original pixel enumeration, side-strip orientation, signed-axis
reversal, constant/noise placebo and stationary/spreading profile examples.
Those establish instrument behaviour, never physical calibration or quality.
Root runs controls and the actual export scan after author/verifier freeze.
