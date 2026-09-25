# One current-native garnet base counterfactual

Root executes one complete183-frame comparison after independent source review.
No build, extra stack, parameter sweep, base-only ownership model or production
default change is part of this experiment. Author has not executed the runner,
decoded RAW or rendered either arm.

Baseline is the corrected current production delivery in
`outputs/quality-september25/garnet-104`. The script reads its actual frozen
invocation, input-order and completion receipts and checks their SHA256 values.
It reuses production executable `bec4c357836ad1383800a6c933460ee7ef072c525b5957a6f5deb5194b203314`,
including its numerical-range correction. Map, reference91, all183 original
paths/order/content/mtime, full-resolution rounded GPU gather, original matching
CA, as-shot WB, crop[127,85,3262,2174], seven bands, gate2, exponent2,
sharpen1.4, soft selection, exposure0.0 and the entire explicit environment
are copied from the delivered invocation. Both arms use the same executable
and RAW samples; the source-level near-island structure remains present.

Exactly two argv values may differ: `--pyramid-base mean` becomes `weighted`,
and `--out` names a fresh TIFF. No other command value or environment field is
changed. An explicit diff is recorded and asserted before execution. The
candidate banner must confirm weighted-from-coarsest, all183 placements and
the same current camera/geometry/settings. Full original content hashes and
mtime/order checks occur before and after; the retained map and baseline are
also rechecked. No new alignment is requested or written into the capture tree.

The existing production writer automatically measures tone independently in
each arm. This is explicit: the log retains each rounded tone description, but
the comparison does not claim exact shared f32 tone anchors. Neither histogram
matching nor a compensating exposure tweak is permitted. Darker output alone
is not improvement. Independent review must judge preserved real facets,
boundaries and broad spill together with flat background wander, color change,
clipping and noise. A null, degradation or merely darker rendering closes this
one counterfactual. The old weighted-base tonal failures and A2's failed causal
audit remain adverse evidence; this observation cannot overturn them generally.

The owned render job has180 seconds wall,900 CPU seconds,8GiB committed memory
and8MiB log limits, against the retained mean render's single57.297-second,
approximately3.25GB operational observation. These are bounded margins, not
speed claims. Streaming original-hash audits and full-image JPEG preparation
run outside the render child; total wrapper time is recorded separately.

Output: complete6524x4348 RGB16 TIFF and full-resolution JPEG with identical
ICC to the baseline, plus a separate <=1617 overview. Baseline and candidate
whole-file/pixel hashes, actual crop and ICC identity are recorded. Any later
fine-detail claim still requires independently chosen native tiles <=400px;
the overview is for whole-image orientation only. Completion leaves the
photographic verdict unset for root's independent review.

Root command (not run by author):

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/base-band-transfer/run.py --out experiments/base-band-transfer/garnet104-1
```
