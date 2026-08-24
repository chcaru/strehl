"""Append section 31 and facts P118-P123 to docs/research/M87-occlusion.md.

Written to a .py file rather than a PowerShell here-string on purpose: the
@"..."@ form treats the backtick as an escape and silently injects C0 control
characters into code spans (P116).
"""
import pathlib
import re
import shutil
import os

DOC = pathlib.Path("docs/research/M87-occlusion.md")
raw = DOC.read_bytes()
s = raw.decode("utf-8")
assert "\r\n" in s and s.count("\n") == s.count("\r\n"), "expected pure CRLF"
bak = pathlib.Path(os.environ["TEMP"]) / "M87-occlusion.before-s31.md"
shutil.copy2(DOC, bak)
print(f"backup {bak}")

FACTS = [
    ("P118",
     "**The veil is 4133 DN, not \u201ca few DN\u201d \u2014 6.31% of full scale, and "
     "plainly visible with no stretch at all.** Measured on `bee-3-cpl` at the "
     "shipped default against a LOCAL background reference (mean of far-field "
     "pixels beyond 70 px within a 251 px window, which cancels the scene "
     "gradient at any order): the residual rises from \u221235.5 DN at d = 5 px "
     "to **+3390.8 DN at d = 25 px** over a \u2212742.5 DN far-field baseline, "
     "amplitude **+4133 DN** = **35.7** codes of the diagnostic cast = "
     "**16.1 of 255** codes in an 8-bit viewer.",
     "The orchestrator described the step as \u201ca few DN and invisible at normal "
     "display gamma\u201d and reached for a 4\u00d7 stretch to show it. That is wrong "
     "by three orders of magnitude, and it matters: the veil is visible in the "
     "**as-rendered** panel, so it needs no diagnostic view to justify it and "
     "no stretch artefact can be blamed for it. Control C-FAR, the same "
     "pipeline against a 180\u00b0-rotated subject mask of identical area and "
     "shape, returns **\u2212316 DN** with no hump \u2014 13.1\u00d7 smaller and the "
     "wrong sign.",
     "MEASURED"),
    ("P119",
     "**The render\u2019s noise field is exactly `n_eff` averaging, with no free "
     "parameter.** Local noise sd against local mean `n_eff`, over 710 160 "
     "background windows spanning `n_eff` 1.3 \u2192 282.8 (218\u00d7) and noise "
     "219.0 \u2192 15.4 DN (14\u00d7), fits `noise = 283.3 * n_eff^-0.5228`. The "
     "exponent predicted by arithmetic alone is **\u22120.5000**.",
     "Predicted before it was measured: \u00a784\u2019s pocket/far noise ratio of 7.2\u00d7 "
     "implies an `n_eff` ratio of 52, and the run printed **mean n_eff = "
     "55.321** before I looked. This is the strongest quantitative statement "
     "in the milestone and it is about the estimator working, not failing \u2014 "
     "the merge really is averaging \u221an frames per pixel, everywhere, "
     "including in the veil.",
     "MEASURED"),
    ("P120",
     "**The concentric banding is none of the three things offered \u2014 it is the "
     "diagnostic cast\u2019s quantum crossing the `n_eff` field.** One output code "
     "of the 4\u00d7 stretch is **115.7 DN**; P119\u2019s noise law sweeps 257 \u2192 15 DN "
     "across the region; they cross. Simulating the flatness statistic against "
     "the measured lag-1 correlation **+0.4676** and gradient **16.44 DN/px** "
     "puts the flatness-0.5 crossing at `n_eff` **12.86**, against **19.10** "
     "measured \u2014 ratio **0.67\u00d7**.",
     "So the band SHAPES are real (they are `n_eff` contours, set by occlusion "
     "geometry) while the band VISIBILITY is the 8-bit cast: above the "
     "crossing the field posterises into plateaus, below it the noise "
     "self-dithers. Neither \u201cveil falling off in steps\u201d nor \u201cquantisation in "
     "the stretch\u201d alone. Control C-SIM reproduces the low-`n_eff` flatness "
     "the simulator was **not** tuned to \u2014 0.170 predicted against 0.178 "
     "measured, **4.6%** error.",
     "MEASURED"),
    ("P121",
     "**The photometric step at election boundaries is below 1.00 DN per "
     "adjacent frame, and a coffee-bean-grade drift is excluded.** Median "
     "high-pass on election-index boundaries is **27.0 DN** against 26.0 DN "
     "off them \u2014 enrichment **1.04\u00d7**, rot180 null **0.93\u00d7**. Planting a "
     "MONOTONE per-frame ramp (M99 fact 23) calibrates that: 1 DN/frame reads "
     "1.115\u00d7, 10 reads 1.269\u00d7, 100 reads 1.692\u00d7. M24\u2019s worst corpus stack "
     "(coffee-bean, 11.70% end to end) is 20.0 DN/frame and would read "
     "**1.37\u00d7**.",
     "**My registered bar was mis-set and I am withdrawing what it said.** "
     "\u201cEnrichment \u2265 1.5\u00d7 means detected\u201d needs a plant of **100 DN/frame** = "
     "**58.5%** drift across the bracket, five times the largest drift anyone "
     "in this corpus has measured; a bar that only fires at 5\u00d7 the largest "
     "known effect is not a test. The response CURVE is the result, not the "
     "threshold I hung on it. At 27.0 DN the step is **0.233** of one output "
     "code, so it is invisible in the figure regardless.",
     "MEASURED"),
    ("P122",
     "**The rendered gate overturned my own scalars on the flagship image.** "
     "The shipped correction scored leakage **0.000** into the subject "
     "(interior median and p99 both 0.0 DN) and a **96.3%** veil reduction "
     "(4133 \u2192 153 DN). The 100% crop then showed the hair tips truncated to "
     "stubs against a hard stair-stepped edge. Re-measured on a population "
     "defined from the reference render \u2014 thin dark structure in near "
     "background \u2014 tip contrast falls **6316 \u2192 3739 DN**, ratio **0.5919**, "
     "with **33.1%** of tip pixels dropping below half the selection "
     "threshold.",
     "The scalar was blind for a reason that generalises: **0 of 39 274** "
     "hair-tip pixels lie inside the segmented subject mask, so 100% of the "
     "damaged population is invisible to a leakage test that only looks for "
     "spill INTO the subject. Near a silhouette the hairs ARE the background "
     "pixels. Same hole as the +72.9% episode. Controls C-INT (subject "
     "interior, untouched) and C-NULL (after replaced by before) both return "
     "**1.0000** exactly, so the estimator is sound and the erasure is real. "
     "The correction stays OFF, now for a measured reason on `bee-3-cpl` "
     "rather than an impression.",
     "MEASURED"),
    ("P123",
     "**Reproduce another agent\u2019s artefact byte-for-byte before analysing it.** "
     "Re-rendering `bee-3-cpl` at the shipped default with `STREHL_WARPMAP` "
     "pinned to my own reference-149 sidecar produced a file **SHA-256 "
     "identical** to the orchestrator\u2019s `bee-3-cpl.tif` "
     "(`e400a63aa9f6ab1f1957940d`), so the `--index-map` and `--n-eff-map` "
     "written in the same run are the election and `n_eff` fields OF THAT "
     "EXACT FIGURE.",
     "Every claim in \u00a731 about what the figure shows is therefore anchored to "
     "the figure rather than to a similar render, and the assertion is in the "
     "script so it cannot drift. This is the cheap move that converts \u201cI "
     "looked at a render like yours\u201d into evidence, and it cost one hash.",
     "MEASURED"),
]

rows = []
for fid, claim, conseq, status in FACTS:
    row = f"| {fid} | {claim} | {conseq} | {status} |"
    n = len(re.findall(r"(?<!\\)\|", row))
    assert n == 5, (fid, n)
    assert row.count("`") % 2 == 0, (fid, "unbalanced backticks")
    assert not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", row), (fid, "C0")
    rows.append(row)

anchor = "| P117 | **At HEAD the merge does not read"
i = s.index(anchor)
j = s.index("\r\n", i) + 2
s = s[:j] + "\r\n".join(rows) + "\r\n" + s[j:]
print(f"inserted {len(rows)} fact rows after P117")

BODY = """
## 31. The wild veil: what the figure actually shows

The orchestrator sent a two-panel figure of `bee-3-cpl` at `(700,3150)
1100x900` \u2014 the shipped default gate, an isolated sidecar, the claw and the
hair mass \u2014 and asked three things: separate the concentric banding near the
claw into veil-falling-off-in-steps, quantisation in the stretch, or a
separate defect; build a rendered before/after gate on that exact region and
let it outrank any scalar; and say if the wild veil contradicts my model.

The banding is a fourth thing. The gate failed. Both are below.

### 31.1 Provenance: this is that figure, not one like it

Re-rendered from `D:\\personal\\macro\\bee-3-cpl` at the shipped default with
`STREHL_WARPMAP` pinned to my own reference-149 sidecar (rule 45), the output
is SHA-256 **identical** to the orchestrator\u2019s file:

```
alignment      : ON (sidecar-override), reference frame 149, 299 placed / 0 refused
mean n_eff     : 55.321      n_eff = 1: 38.77%      exposure: +1.54 stops
sha256(mine) == sha256(ORCH-gallery3/bee-3-cpl.tif) == e400a63aa9f6ab1f1957940d
```

The `--index-map` and `--n-eff-map` from the same run are therefore the
election and `n_eff` fields *of that figure*, at half resolution on the plane
grid, scaled 2\u00d7 to overlay. `87-election.py` asserts the equality before it
measures anything (`P123`).

### 31.2 The veil is 4133 DN, and needs no stretch

The covering message said the step is \u201ca few DN and invisible at normal
display gamma\u201d. Reconstructing the diagnostic stretch from `blob.py` shows
that cannot be so: `span = (p99 \u2212 p1) * 0.35 = 14 696 DN`, so **one output
code is 115.7 DN** and a 3 DN step is 0.026 of a code \u2014 the stretch would
*hide* a few DN, not reveal it. Anything visible in that panel is large.

`86` first measured the veil as median DN against distance from the
silhouette. That was confounded: the subject fills the upper left, so every
far pixel is lower right and the scene\u2019s own gradient rides in. `90-veil.py`
repairs it with a **local** reference \u2014 the mean of far-field pixels within a
251 px window \u2014 which follows any gradient and cancels it, and whose residual
sd on the far field is 1048.8 DN against the global quadratic\u2019s 1736.3 DN.

| d (px) | 1 | 3 | 5 | 8 | 12 | 18 | **25** | 35 | 50 | 70 | 140 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residual (DN) | \u221211721 | \u22123976 | \u221236 | +2077 | +2847 | +3061 | **+3391** | +2782 | +479 | \u2212113 | \u2212836 |

Amplitude **+4133 DN** over the \u2212742.5 DN baseline: 35.7 codes of the
diagnostic cast, 6.31% of full scale, **16.1 of 255** codes in an ordinary
8-bit viewer. Control C-FAR, the same pipeline against a 180\u00b0-rotated subject
mask \u2014 same area, same perimeter, same shape, no registration to the image \u2014
returns \u2212316 DN and no hump (`P118`).

### 31.3 The noise field is the estimator working

Pass two averages `n_eff` frames per pixel, so if the noise field is nothing
but un-averaged pixels then `noise * sqrt(n_eff)` is constant and the log-log
slope is **\u22120.5000** exactly. Measured over 710 160 background windows:

| n_eff | 1.3 | 3.6 | 10.4 | 16.0 | 24.5 | 42.2 | 59.7 | 86.2 | 180.9 | 282.8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| noise (DN) | 219.0 | 169.1 | 91.6 | 65.3 | 47.4 | 39.4 | 34.1 | 27.2 | 18.5 | 15.4 |

Slope **\u22120.5228**, intercept 283.3 DN at `n_eff` = 1, across a 218\u00d7 range of
`n_eff` and 14\u00d7 of noise. Nothing was fitted to produce the \u22120.5 (`P119`).

### 31.4 The banding: neither of the two candidates, and the third is wrong too

`84-banding.py` registered a dither discriminator \u2014 quantisation introduced
by a uint8 cast is removed by dithering *before* the cast; real 16-bit
structure is not \u2014 and it split the region rather than the hypothesis:

| box | noise sd | code/noise | dither ratio | codes | median run |
| --- | --- | --- | --- | --- | --- |
| pocket, inside the claw | 160.1 DN | **0.72\u00d7** | 1.0\u00d7 | 149 | 1.0 px |
| far background | 22.2 DN | **5.20\u00d7** | 1.8\u00d7 | 42 | 2.0 px |

Banding is *impossible* where ORCH reported it (the noise self-dithers) and
*expected* a few hundred px away. Meanwhile the high-pass of the **16-bit**
data at \u00b1480 DN, computed before any cast, still shows concentric arcs. So
there are two phenomena and they are in different places.

The `n_eff` map resolves it: rendered as a map (discipline 677), the arcs
**are** the `n_eff` contours. And P119\u2019s noise law crosses the cast\u2019s 115.7 DN
quantum inside the region, so the same contours become visible as flat
plateaus on one side and dithered speckle on the other. Simulating the
flatness statistic against the measured lag-1 correlation +0.4676 and
gradient 16.44 DN/px puts the crossing at `n_eff` **12.86** against **19.10**
measured, ratio 0.67\u00d7 (`P120`).

**A wrong bar of mine, disclosed.** I first predicted the crossing at `n_eff`
5.54 from \u201cposterisation appears when the noise falls below about one code\u201d
and scored the 3.45\u00d7 miss PARTIAL. That constant is simply wrong \u2014 adjacent
samples share a code with probability of order `q/s`, and the render\u2019s pixels
are correlated by the demosaic anyway. The miss measured my arithmetic. The
simulation has no closed form to get wrong, and control C-SIM makes it earn
its keep by reproducing the low-`n_eff` flatness it was not tuned to: 0.170
against 0.178, 4.6%.

### 31.5 The photometric step, bounded \u2014 and a bar I set too coarse

The election-index boundaries carry **1.04\u00d7** the high-pass of non-boundary
background (rot180 null 0.93\u00d7). A null is a claim about the instrument, so
`88-controls.py` plants the exact mechanism \u2014 `g\u2032 = g + s * index`, monotone
in frame index as M99 fact 23 requires \u2014 and sweeps `s`:

| s (DN/frame) | 0 | 1 | 3 | 10 | 30 | 100 | 300 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| enrichment | 1.038 | 1.115 | 1.154 | 1.269 | 1.462 | 1.692 | 1.769 |

My pre-registered \u201c\u2265 1.5\u00d7 means detected\u201d therefore fires only at 100 DN per
frame \u2014 **58.5% drift across the bracket**, five times M24\u2019s worst stack. As
written it could not have detected any realistic photometric step and its
\u201cexcluded\u201d reading is **withdrawn**. What replaces it is the curve: the
statistic resolves to 1/26 (the high-pass is integer DN on a base of 26), so
a 2-resolution threshold of 1.115\u00d7 puts an upper limit of **1.00 DN per
adjacent frame** = 0.58% across the bracket. Coffee-bean\u2019s 11.70% would read
1.37\u00d7 and is excluded (`P121`).

### 31.6 The gate the orchestrator asked for, and what it did

Rendered before/after of exactly `(700,3150) 1100x900`, shipped default gate,
`STREHL_WARPMAP` pinned, AFTER = `STREHL_FIX_HALO=1`
(`C:\\dev\\strehl-out\\M87-bee\\BEFORE-AFTER.png`, hair mass at 100% in
`HAIR-100PCT.png`, tips at 2\u00d7 in `HAIR-TIPS-2X.png`).

The scalars were excellent:

| zone | n | median abs delta | p99 abs delta |
| --- | --- | --- | --- |
| subject interior (>10 px in) | 160 241 | **0.0 DN** | **0.0 DN** |
| subject edge (\u226410 px in) | 62 039 | 0.0 DN | 11 832 DN |
| background near (\u226440 px) | 147 004 | 5078 DN | 14 182 DN |
| background far (>70 px) | 536 802 | 0.0 DN | 2992 DN |

Leakage into the subject **0.000**; veil amplitude 4133 \u2192 153 DN, **\u221296.3%**.
By every number I had registered, it worked.

**The render says otherwise.** At 100% the hair tips are truncated to stubs
against a hard stair-stepped boundary, the wispy isolated hairs over the pale
background are gone, and a hard-edged rim with blocky terracing stands where
a soft veil used to be. `92-erasure.py` measures it on a population defined
from the reference render rather than from a mask \u2014 thin dark structure in
near background, depth below a 9 px grey dilation \u2014 and tip contrast falls
**6316 \u2192 3739 DN**, ratio **0.5919**, with 33.1% of tip pixels dropping below
half the selection threshold. Controls C-INT and C-NULL both return 1.0000.

The reason the scalar was blind generalises past this correction: **0 of
39 274** hair-tip pixels lie inside the segmented subject mask. A leakage
test that looks for spill *into* the subject cannot see damage to a
population that is classified as background \u2014 and near a silhouette, the
hairs are the background pixels. This is the same hole as the +72.9%
episode, in a metric written after it (`P122`).

The correction stays **OFF**. That was already the ruling; it now has a
measured reason on the flagship image.

### 31.7 Does the wild veil contradict my model?

No, and the two-layer reading survives, but the population is not the one my
cells were built on. The hair mass is not one silhouette; it is thousands of
occluding edges a few pixels apart, which is the thin-structure regime \u00a729\u2019s
T4 flagged as **not measured** (bee thin quartile \u2264 13.19 px against
flowers\u2019 3.00 px median). Two things follow, and both are testable rather
than argued:

- The veil profile peaks **25 px** from the silhouette and is still +479 DN
  at 50 px. That is far wider than the spacing between adjacent hairs, so at
  the hair mass the veils of neighbouring edges **overlap**, and a per-edge
  two-layer fit is solving for a background that is itself veiled by the next
  hair over. My cells never had that.
- `n_eff` is 1 in exactly that band and the winner field is structurally
  undefined there, so the correction has no reliable elected index to build
  on \u2014 which is consistent with it reaching for the nearest confident
  background and taking the hair tips with it.

### 31.8 Verification

`verify_s31.py` re-derives every figure in this section from the JSON in
`experiments/M87-occlusion/data/`, asserts exact occurrence counts rather
than presence (`P113`), re-hashes both renders, and enforces the
zero-C0-control-character guard. `control_s31.py` runs the registered
negative controls, each anchored on a unique single line with a hard error if
the anchor does not land.
"""

s = s.rstrip("\r\n") + "\r\n" + BODY.replace("\n", "\r\n")
assert not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", s), "C0 control character"
DOC.write_bytes(s.encode("utf-8"))
print(f"wrote {DOC}: {len(s.splitlines())} lines")
