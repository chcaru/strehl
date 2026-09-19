# Complete commercial comparison, September19

MEASURED: official Helicon Focus8.3.11 trial produced complete70-frame RGB16
vitamin-C images for fixed B radius8/smoothing4 and C smoothing4. Radius is
inactive for C. The full images and native fixed-region boards are retained;
both methods use the same70 previously developed TIFFs as the retained fork.

Commands actually run, Python3.12 from repository root:

```
python -I -B -X faulthandler experiments/helicon-current/run-witness.py
python -I -B -X faulthandler experiments/helicon-current/run-tiff-witness.py
python -I -B -X faulthandler experiments/helicon-current/run-full-tiff.py b
python -I -B -X faulthandler experiments/helicon-current/run-full-tiff.py c
python -X faulthandler experiments/helicon-current/compare.py
python -I -B experiments/helicon-current/full-views.py
```

The first full-B invocation refused the unfiltered directory because it also
contains golden.tiff. It produced no image. The corrected runner explicitly
selects/asserts DSC00094 through DSC00163; both completed runs use that manifest.
Original prepared input hashes are identical before/after both runs. The RAW
witness uses workspace copies and verifies originals/copies separately.

The RAW witness timed out after180.031s without output. Vendor diagnostics
explicitly state that Adobe DNG Converter was absent and RAW rendering failed;
the process remained open after that failure. This does not show unsupported
A7CII RAW. The two-TIFF witness then completed in3.625s at7032x4688 RGB16.
Both full runs produced the same full-resolution shape and bit depth. B child
wall13.250s; C10.437s. These exclude development and cannot be compared with
native RAW-to-output time. Application alignment/brightness/interpolation state
was not numerically recovered; record it as unknown, not as claimed defaults.
The first RAW startup log reports OpenCL unselected, but no fresh full-run log
could be written under the sandbox, so GPU use during B/C is not established.

VERIFIED metadata: Helicon B/C and the Strehl comparison outputs carry the same
2716-byte sRGB profile. Both complete previews were visually inspected without
a visible trial overlay; this is a visual observation, not a pixel-level
watermark absence proof. The canonical full-views exports retain that ICC and
use rounded u16-to-u8 division by257. Initial run-local previews used division
by256; TIFF masters are unchanged. Canonical views supersede those previews.

Independent photographic review supports a concrete mixed outcome:
Helicon B contracts the conspicuous glint fans in facet-edges/dark-inclusion
while retaining nearby visible crystal boundaries. Residual flare remains.
Strehl green-match has cleaner smooth fields. Helicon C often strengthens rays
and shows no decisive general resolved-detail advantage. The fork retains more
grain and enlarged bright contamination. Details, coordinate residuals and
untagged-fork caveat are in photo-comparison-1/results-review.md.

Root independently inspected all five native boards and both full images and
adopts that limited conclusion. Helicon's roughly1.07% scale difference was
measured, not ignored: the boards use matched centres but unresampled native
pixels. The whole-workflow difference includes premerge development, alignment
and blending; it cannot identify a proprietary mechanism or prove SOTA.

Program decision: save the complete-periodic wavelet result, but prioritize
the fixed donor-consistency intervention in depth-route-audit.md and
../donor-consistency/charter.md. B shows that a better outcome on the retained
input set is possible; the source witnesses offer a directly testable cause.

Official executable acquisition is bound in download.json: installer signature
Valid, vendor signer GELIKON SOFT,TOV, SHA256
a0f5e558d05a56bb9fd37efe88a03f97da4cbd0a159b2d5c492a85645bc11d56.
The installer exited0 without a restart. It created normal vendor registration
and invoked its Lightroom installation helper despite workspace destination;
do not describe the installation as a portable-only filesystem operation.
No purchase, licence reset, or trial circumvention occurred.

Vendor references: [official downloads](https://www.heliconsoft.com/software-downloads/),
[CLI, methods and trial documentation](https://www.heliconsoft.com/focus/help/english/HeliconFocus.html).
