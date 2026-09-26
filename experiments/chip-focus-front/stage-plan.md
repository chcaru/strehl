# Fixed chip focus-front extraction

Prepared before any photographic extraction. Root executes under120s wall,
600s CPU and4GiB. No original RAW is read, no merge/build is performed, and no
aligned full-frame volume is created. This is a toned-RGB focus-response proxy,
not calibrated DN, a noise estimate or geometric truth.

Use all299 existing `chip-competitor/run-1/developed/DSC00001.tiff` through
`DSC00299.tiff`, in that order. Reuse the complete developer receipt's source
identities/output hashes and successful developer/ICC commissioning, plus the
retained Helicon input-after hash list. Do not rehash the approximately59GB of
TIFF data. Check current file size, header geometry/type/ICC and metadata before
and after the bounded read; hash the actual sampled values/curves. This binds
retained content identities and current metadata, not a fresh full-content audit.
Development is fixed but nonlinear/toned and preceded external fusion. Prepared
TIFFs have CA off; current native fusion has CA on. These curves do not exactly
reproduce the native CFA focus statistic.

Gauge: current delivered6500x4332 image, reference149, quad crop
[133,89,3250,2166], complete source map
`quality-september14/chip-baseline-1/chip.warpmap.txt`, SHA256
`ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922`.
Decode the four f64 bit patterns, not rounded annotations. For delivered native
position p, let u=p+[266,178]; sample source position
`[3516,2344]+a*(u-[3516,2344])+2*b`, treating a and b as complex numbers.
The TIFF active origin is[0,0], with7032x4688 native pixels. Source map direction
is reference-to-frame. No additional reference normalization or chain is fitted.

Metadata-preflight repair, before any photographic extraction: the initially
assumed bit-exact identity at149 is false. The pinned map stores
`a=(0.9999999999999999,0)`, `b=(0,7.105427357601002e-15)` in quad units;
its bits are `3fefffffffffffff 0000000000000000 0000000000000000 3d00000000000000`.
These values remain unchanged. Replace only the unsupported exact-identity
assertion with a finite displacement bound
`|a-1|*hypot(3516,2344)+2*|b| <= 1e-9` native pixel over the complete active
domain. The stored values give a DERIVED bound4.833584748946457e-13 native pixel.
Record the actual bits, bound and limit in the plan. This accepts negligible
f64 gauge-normalization residual, not a fitted geometry correction; the complete
map SHA remains mandatory. Root's failed metadata preflight is preserved.

Fixed42 patch centres: the row-major6x6 Cartesian grid
x=[500,1600,2700,3800,4900,6000],
y=[350,1070,1790,2510,3230,3950], omitting(row4,col4) because its128-square
overlaps the already-frozen lower-colour witness; then append these seven
existing target centres in order:
rail-crossing[1290,1150], upper-colour[1292,452], central-stipple[3232,1562],
lower-array[822,3052], lower-colour[4922,3272], surface-scratches[5112,1512],
upper-left-contact-grid[304,592]. This geometry-only omission and all positions
precede profile extraction. No texture/focus selection or recentering is allowed.
The35 remaining grid sites are ordered row-major, then the seven named targets.
Only grid sites where `(row//2+col//2)%2==0` train the model:19 sites. The other16
grid sites and all seven named targets are held out:23 sites. Export labels,
row/column, target flag and this mask before extraction; no image selects it.
Each128x128 core spans centre+[-64,63] in both axes. Extract a192x192 footprint
with32 native pixels of filter support on each side. Assert nonoverlap of every
192-square support and complete mapped source/interpolation support for every source and site;
any unsupported sample refuses the entire extraction.

The fixed sampler is OpenCV cubic interpolation on each bounded source RGB
rectangle (A=-.75,1/32-phase interpolation table); it is an RGB diagnostic
sampler, not the product's CFA gather. Bounds include every four-tap source
footprint; no border extension supplies photographic samples.
Preserve f32 arithmetic and its interpolated values without a clipping repair.
Convert RGB16 to f32 /65535 and then luma=.2126R+.7152G+.0722B. Two fixed
2D spatial DoG bands are Gaussian(sigma1)-Gaussian(sigma2) and
Gaussian(sigma4)-Gaussian(sigma8). Each Gaussian has explicit radius4*sigma,
separable normalized coefficients and replicated borders; only the central128
square contributes mean squared band response. Filter one source/patch at a
time, never the source/time axis. A curve is band power, not a noise sigma or
photographic quality score; texture, glare, interpolation and tone can change it.

The stage API exposes `xy_native[P,2]`, `contrast[299,P,2]` f32 and exact
ordinal order, plus fixed spatial train/held-out masks chosen by the independent
reviewer before execution. Save mapping/support/hash and mean-luma receipts;
do not estimate a peak, discard flat sites or fit a local temporal centre here.
Model author consumes the curves with its separately frozen schedule/plane
hypothesis. Known-shift/source-address and constant-image controls must pass
before opening photographic TIFFs; an incorrect crop origin, map direction or
missing factor2 translation must have a rejecting control. No photograph was
read by this plan's author.
