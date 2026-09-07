# Independent read of the retained interval diagnostic

2026-09-07. **VERIFIED: diagnostic artifacts and observation scope only.**
`independent-interval-diagnostic-read.py` reads JSON/trace/source bytes with the
Python standard library. It imports no numerical helper and executes no
quadrature. Its first run completed successfully; the exact reader and original
diagnostic interpreter arguments are retained in
`independent-interval-diagnostic-read.json`.

Externally pinned diagnostic result:
`194dbdb0454a02db985b4e28305c9f5a0f5f42fe4223829b3ea8db0f21e5e1f0`.
Execution release:
`cec6cb4fcb803b57b04b736777e8160264ce45e0e8e5b4fb8fb49048bbcca6e1`.
The actual original command matches the released argv, including absolute
Python path, `-X utf8`, `-X faulthandler`, fresh cache prefix and release digest.
All 28 source/input bindings match current files and both retained snapshots.
The reviewed diagnostic source is `1ae00e6c…`, unchanged frozen reference
`40199977…`, and frozen M194e independent model `0cd8ea23…`.

All 32 selected call signatures in each of off/count/placebo match the original
component result byte-for-byte, including status, value/receipt or refusal and
integrand count. Their common SHA-256 is
`0a3e0c9732216609e94d0605f55eb7c9c21dc598fa196f9492c8e9b0ec644375`.
The 96 calls account for 31,878 actual integrand evaluations; none are analytic
factor calls. Count mode records all 10,626 callbacks in a 1,904,485-byte trace.
Off collects/calls no optional hook; count collects every hook; placebo reaches
the same number of hooks without collecting. No cleanup or source-capture
failure is recorded. Producer-observed CPU/wall time is 2.25/2.406 seconds,
within the 10/20-second diagnostic caps. This is not a timing comparison.

I independently regrouped actual samples by call/interval, checked numerical
and hexadecimal representations, bounds, complete callback counts, distinct
coordinates and endpoint multiplicities. For warned intervals I counted
successive `math.nextafter` steps, rather than reusing the author's integer-bit
ordering computation:

| Representable steps | Distinct queried coordinates | Queries | Warning intervals |
| --- | --- | --- | --- |
| 5 | 6 | 63 | 10 |
| 13 | 14 | 63 | 2 |
| 16 | 17 | 63 | 16 |

Every one of the 28 warnings belongs to the predeclared 14 failed cases at both
targets, has an endpoint exactly -1 or +1, falls below the fixed 256-step
definition, and revisits coordinates. All four ordinary-width positive
companion calls retain their original values and have no warnings. This is
actual support for the proposed representability mechanism; it is not merely
an inference from a total-call counter.

The retained author checks include the coherent interval-bound mutation and
restored trace. I additionally changed the **sample**, re-choosing the last
warned interval's first sample, and made its numeric/hex pair agree at the next
representable value beyond the right bound. My independent correspondence
reader rejects it specifically as outside the bound; restoring the actual
trace passes. This tests the consuming bound check, not a stale redundant
metadata field. The original trace was not modified.

The earlier static review's cleanup-restoration, bounded same-byte trace
loading, overflowed JSON and coherent-bound power issues were corrected before
the released run. Source inspection still establishes unchanged forwarding of
`epsabs`, `epsrel=0`, `limit=128`, callback values, and warning re-emission into
the original outer refusal guard; actual mode signatures provide the
observation-invariance evidence for these fixed inputs.

The result leaves the original 28 reference refusals intact. Tiny returned
subinterval estimates do not authorize dropping their domains or suppressing
warnings. A normalized interval would be a new numerical method, requiring its
own prospective controls, both complete numerical batches and the strict
independent reader. No complete M194g reference, float or CFA authority is
conferred by this diagnostic.

Reproducible artifact-only read:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194g-larger-pupil/work/cache-independent-interval-diagnostic-read-1 experiments/m194g-larger-pupil/independent-interval-diagnostic-read.py
```
