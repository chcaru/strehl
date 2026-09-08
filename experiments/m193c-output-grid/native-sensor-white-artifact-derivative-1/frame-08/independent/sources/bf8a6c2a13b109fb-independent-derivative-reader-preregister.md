# Independent registration derivative consumer — source preparation

This source-only preregistration covers the two private derivative TIFFs and a
separate reader process for each of the nine already selected native snapshots.
No RAW bytes, decoder, numerical helper, image reader or private control has run
while preparing these sources. Root freezes sources, dependencies and exact
commands before execution. The reader does not grant registration coverage,
physical calibration or a qualified common-TIFF route.

## Interfaces and authority

`independent-derivative-read.py --private --request ABS --request-sha256 SHA
--output NEWDIR` consumes `m193c-derivative-private-read-request-v1`, exactly
`schema,execution_release,build,producer_result,producer_launch,reader_runtime,
limits`. All FileRefs are absolute `{path,sha256,bytes}`. Private reader_runtime
is the pinned interpreter FileRef. Limits have exactly cpu_seconds, wall_seconds,
artifact_bytes and are locally capped at120CPU/240wall/32MiB. The encompassing
private campaign owns the nonresetting600CPU/1200wall/128MiB account and8GiB Job;
the reader does not create a fresh campaign allowance. Its release is
`m193c-private-campaign-release-v1` / `private-twelve`, with this exact actual
argv in commands.derivative_reader, substituting only
`ACTUAL_DERIVATIVE_REQUEST_SHA256`. Parent validates build/launch Job authority;
this reader also binds the successful launch to the actual producer command,
environment, executable and output files, and rejects conflicting consumed refs.

Private result schema is `m193c-derivative-private-independent-v1`, success
`PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY`. Exact fields: schema,status,request,
build,producer_result,producer_launch,outputs,checks,invocation,error,
finalization_errors. outputs has affine and signed_border, each exactly
`tiff,pixel_sha256_u16_le,shape,compared_sites,max_code_error`. checks has exactly
source and reader: source is the32 original ordered `{id,pass,evidence}` records;
reader is the41 ordered records below. Partial lists remain in failed results.
Invocation is the closed object argv,orig_argv,executable,cwd,xoptions,
thread_environment,runtime,source_bindings,work; orig_argv is the exact released
interpreter command. This shape is shared by the native result.
PASS requires all73 records true and both complete actual TIFF comparisons.

Native CLI omits --private and uses the exact request,11 check IDs and result
schema in native-derivative-run-preregister.md. Its release.reader.commands must
contain the actual interpreter argv with only ACTUAL_FRAME_REQUEST_SHA256
substitution. Native request limits remain remaining CPU/wall,8GiB committed
memory and at most4MiB metadata. Parent carries all observed child CPU, wall and
new extents through the1200CPU/1800wall/4GiB real stage. Reader produces metadata
only. Full snapshot bytes are bounded64MiB and hashed before passing those same
bytes through BytesIO to rawpy; it never opens the original corpus path.

The native runtime record is `m193c-derivative-reader-runtime-v1`, exactly
schema,python_executable,python_version,numpy_version,rawpy_version,libraw_version,
module_files,thread_environment. It is captured by the separate future command
`--capture-runtime NEWFILE`, with no RAW access. module_files is a sorted list
of absolute FileRefs for actual loaded NumPy/rawpy Python and native module
files plus their installed .libs DLLs. Runtime capture is a dependency import,
so it also requires a root command release; AST validation does not execute it.
Native reader rechecks runtime versions, paths and all file bytes before decode.
Private runtime reports actual NumPy identities in invocation, without rawpy.
Both branches set OMP/OPENBLAS/MKL/NUMEXPR threads to2 before NumPy import.

## Independent native observation

Rawpy is a separate linked decoder API; no forbidden decoder implementation is
read. Public contracts are the [RawPy API](https://letmaik.github.io/rawpy/api/rawpy.RawPy.html)
and [imread API](https://letmaik.github.io/rawpy/api/index.html). The visible
array is borrowed: allocate and copy it inside the context, require owned
C-contiguous native u16 storage and no memory sharing, then hash every active
row after context exit. A poisoned fake context commissions that actual helper.
Record LibRaw margins and storage separately; they need not equal the other
decoder's padding. Active width/height must match exactly, with no crop search.
Actual local four CFA indices are queried at the visible origin via full-buffer
coordinates and mapped through color_desc; the resulting letters must be RGGB.
Raw postprocess is never called.

Every used CFA index's black level must equal the producer's resolved scalar.
Rawpy white_level must equal its white scalar; if camera_white_level_per_channel
is present, every positive used-channel value must also agree. Zero/None is
recorded as unavailable and uses the scalar white, never as measured metadata.
Nonfinite/negative levels refuse. This verifies resolved-scalar agreement,
not absence of the producer's inherited0/65535 fallbacks. Rawpy camera WB is
mapped at local R/G1/B and divided by G1; each positive finite RGB gain agrees
within2^-20*max(1,abs(primary_gain)). G2 metadata is recorded but does not change
the existing RGB convention. There is no fitted normalization or orientation.
Whole active and all row u16 hashes must exactly match the producer. Native TIFF
checks fully consume the actual output and authenticate shape, tags and canonical
pixel hash; they do not pretend to independently recompute every native MHC pixel.

## TIFF extension and independent private oracle

The held M194g parser remains unchanged. The new
independent-derivative-tiff.py copies its strict classic RGB16 tag/strip policy,
with only native bounds and streaming payload handling changed. Bounds are
8192 per axis,36million pixels and217048576 file bytes. Expected native shape is
typed and exact. The reader hashes the supplied checked byte buffer, verifies
every strip/region/no trailing bytes, and streams all u16 pixels into a canonical
little-endian hash using64KiB chunks. It does not allocate a native RGB array.
Only private shapes up to322×22 may materialize pixels, under the same budget.
Both byte buffers and ndarray scope are stated; outer8GiB committed memory is
not an ndarray-only or predecoder-allocation guarantee.

Private source samples, WB and the two30×22 populations are exactly those in
derivative-controls-preregister.md. Independent Fraction arithmetic evaluates
the MHC five-by-five stencils, reflecting at borders with period2*(extent-1).
WB multiplies signed black-subtracted CFA before demosaicing. Final clipping
and round-half-up are applied only to RGB. Affine comparison uses the fixed
54 interior sites (9 x values2:3:26 and6 y values2:3:17), all three channels;
signed-border comparison covers all660 sites and1980 codes. Max error is1u16
code, fixed before observations. Fractions provide an independent arithmetic
setting from the producer's f32 path. This tolerance is not the0.1 native-pixel
registration bar, and no geometric placement claim is made from it.

The early-black-clamp alternative must change the red estimate at G1(11,8) by
exactly1/256 before final encoding and fail the same pixel comparator; the
WB-after-MHC alternative must fail at G at R(10,8). Padding65000→17 leaves all
active samples and expected pixels unchanged. This reader-side array-layout null
is an arithmetic identity after extraction; the separate actual producer's
source32 padding-null commissions the pipeline's padding isolation. Small private TIFF encodings and
rehashed mutations are reader fixtures, not additional production renders.

## Fixed independent41 controls, before actual TIFF admission

The first ID is `refusal-helper-false-acceptance`: a normally returning subject
named tiff-compression, with expected refusal substring compression, must fail
the actual control helper and retain pass=false. This directly kills the
source-review defect where the helper caught its own failed expectation and
mistook the matching ID substring for a subject refusal. It precedes these40
ordered IDs (41 records total):

1. producer-valid
2. producer-false-check
3. producer-omitted-check
4. producer-unknown-key
5. producer-output-association
6. producer-changed-reference
7. producer-restored
8. tiff-little-endian
9. tiff-big-endian
10. tiff-wide322
11. old-parser-width-refusal
12. tiff-appended
13. tiff-truncated
14. tiff-duplicate-tag
15. tiff-compression
16. tiff-orientation
17. tiff-description
18. tiff-software
19. tiff-wrong-shape
20. tiff-bool-shape
21. tiff-changed-code
22. tiff-restored
23. affine-rational
24. signed-rational
25. premature-black-clamp
26. white-balance-after-mhc
27. padding-null
28. oracle-restored
29. owned-lifetime
30. borrowed-lifetime-refusal
31. lifetime-restored
32. wrong-cfa
33. wrong-black
34. wrong-white
35. wrong-wb
36. metadata-restored
37. wrong-active-hash
38. wrong-row-hash
39. conflicting-reference
40. json-overflow

Refusals must be the declared ValueError boundary, not arbitrary exceptions.
Valid/restored cases call the same entry or comparator. Entry fixtures copy the
genuine producer metadata but use private correctly bound fixture TIFFs; actual
producer TIFFs are decoded for their final comparison only after these controls
pass. No new noise draws, RAW reads or producer calls occur in this41 population.
All generated fixture bytes count against the same artifact limit and remain
available on failure. No favorable subset or retry is authorized.

## Terminal closure

Reader entry starts clocks before dependency import; child process clock is
charged from zero. It copies only the four small reader execution/spec sources
(this reader, its TIFF extension, the held TIFF parser and this preregistration),
and preserves compact bindings for the entire common release. It never repeats
the119 compiled sources inside each frame's4MiB allowance. It rechecks all
release sources, all consumed refs,
actual interpreter/runtime and output extents. Metadata writes use strict finite
JSON, with4MiB per record. It checks after terminal persistence. A late failure
preserves first bytes under a fresh rejected name, records the original failure
and secondary persistence errors separately, and cannot exit success. Invocation
records exact argv/orig_argv/executable/cwd/thread environment, actual runtime,
and the last sampled work. Parent-observed Job exit/accounting covers process
startup and final publication; the receipt is not represented as exit time.

This is a preregistered implementation/control plan, not a passed measurement.
