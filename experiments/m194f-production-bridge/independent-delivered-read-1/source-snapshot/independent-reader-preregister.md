# M194f independent delivered-file commission

Zeno, 2026-09-07. Prospective reader/control choices, before any new product
TIFF read in this lane. The committed main preregistration fixes eleven files
and the scientific/engineering bars. This adds a separately chosen instrument,
not a new product or acceptance population. No authored pixel summaries are
used as samples. No M194e numerical source, reference, or authority changes.

The reader parses bounded classic TIFF bytes directly with Python struct and
NumPy. tifffile is only the independent commissioning fixture writer and
cross-reader. Both byte orders, several strips, absent/default orientation,
and explicit orientation1 are legitimate companions. The closed semantic
contract is one uncompressed, unsigned16, contiguous image, RGB/BlackIsZero,
unit orientation/predictor, with no ICC/TransferFunction or unknown tags. RGB
must carry the literal CameraLinear description and package-only software
`strehl 0.0.0`; plain Gray carries neither color description nor software.
Resolution tags, if present, must declare1/1 and unit1. File input is bounded
to1MiB before parsing, entry count64, each count4096, width/height128, and the
caller supplies the exact expected dimensions. Strip spans must have exact
row sizes, no overlap with metadata or each other, and no trailing bytes beyond
the last referenced byte. This is a narrow commissioned writer format, not a
general TIFF decoder. Bounds/unknown metadata can reject otherwise legal TIFFs.

Before product read, require valid synthetic constant/affine RGB and both
rank Gray fixtures to pass; require independent tifffile cross-read agreement.
All control files and outcomes remain. Rehashed pixel faults must pass file
structure but fail the independent value check. Tag/header failures include
orientation8, ICC, transfer table, wrong description/software, sample format,
bits, photometric, planar order, predictor, compression, unknown/duplicate
tags, dimensions, extra IFD, and strip offset/count/overlap/truncation/trailing
bytes. These controls call the actual reader, not a copied acceptance predicate.

The numerical oracle is the fixed analytic rank-two RGB field at native
coordinates output+(6,10), including the represented f32 WB. It uses all80
registered sites with an absolute .25DN per-channel bar and no fitted gain,
offset, registration or tolerance. Constant controls run first. Correct
half-up output quantization must pass. All named geometric/color/normalization
destroyers in the main protocol must fail on a fixed site: omit/double crop,
half-pixel x/y, swapped offsets, transpose/reflection, R/B swap, the explicit
native(20,24) red-as-green CFA error, omitted WB, second black subtraction.
Input ties-to-even and output half-up are distinct; a half-code numerical
control demonstrates the difference without treating it as a sensor scene.
The +64DN all-copy green-site control is compared with the unchanged affine
TIFF at output(23,16), threshold >63.5DN, with no saturation accepted.

Rank counts are computed from strict comparisons of the declared green
values, independently of TIFF codes. Check actual product below/seen arrays
as well as code bytes; code symmetry cannot recover a unique below count.
Actual product population uses manually unseen linear entry0 and reached-zero
entry1, as root explicitly clarified before execution. My reader-only fixture
re-chooses unseen(5,3), originally code800, and reached-zero(0,0). It is not a
replacement for those actual files. Wrong <= ties, red/blue luma, omitted
duplicate200,65535 scaling, missing/moved sentinel and corruption of reached
zero must fail. Genuine confidence is checked on the recorded quad grid for
codes in {0,400,800}, with no65535; no exact genuine ranks are reconstructed
from demosaiced, normalized, quantized RGB.

Final integration will bind the external build/index digests, each actual
plan/receipt/command and all eleven TIFF hashes and samples. Off/count/placebo
and confidence RGB nulls require entire file and pixel identity; exposure1
must change pixels. Raw decode/hook counts must agree with the registered
observer mode. Root/Socrates own compiler/input/refusal authority; this lane
must not replace it with a self-generated hash. Source snapshots and exact
`sys.orig_argv`, fresh cache prefix, versions and thread environment accompany
each run. A failure stops admission and is retained. This commission says
nothing about optical confidence, capture calibration or SOTA quality.
