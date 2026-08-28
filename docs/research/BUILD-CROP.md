# BUILD-CROP — an opt-in crop-to-cover output mode

**Lane:** BUILD-CROP. **Owner of this file:** BUILD-CROP only.
**Binary under test:** `strehl-BUILD-CROP-aa40cc78.exe`, built from the
working tree at HEAD `69ee6532` plus this lane's four files; kept at
`D:\strehl-out\BUILD-CROP\`.
**Outputs:** `D:\strehl-out\BUILD-CROP\` (moved off C: for the disk emergency).
**Scripts:** `experiments\BUILD-CROP\`.

Every number below is from a command that was run and whose output was read.
Anything not measured is labelled **ASSUMED** and says why.

Pasted output that names `C:\dev\strehl-out\BUILD-CROP\` or
`.cargo-target-crop\` is a **historical record** of the run that produced it;
both were deleted for the disk emergency and current work lives on D:.

---

## 0. What this lane does and does not claim

This lane was commissioned on the hypothesis that `fit_to_cover`'s uniform
scale `k` is the root cause of deep-stack softness. **That hypothesis is dead.**
V-REVIEW adjudicated it in commit `cc985615` and found `fit_to_cover` **too
small by 270×** to explain the observed softness; the two contradicting softness
measurements were taken on different subjects and both go VOID on their null.
The softness root cause is **UNKNOWN**, not reassigned.

Accordingly:

> **This lane makes NO sharpness, acuity, or quality claim for `crop` mode.**
> Nothing in this document should be quoted as one. §3 contains a single
> laplacian number measured on a degenerate one-frame render; §3.4 explains in
> detail why it does **not** transfer to real stacks and does **not** survive
> the 270× objection.

What the lane does claim, and what it measured:

| # | Claim | Status |
| --- | --- | --- |
| 1 | `crop` mode removes a resample that has no reason to exist. At unity scale nothing is composed into the placements. | **VERIFIED** §3.2 |
| 2 | The default did not move, on either backend. | **VERIFIED** §2 |
| 3 | The pixel-exactness null passes **exactly** on green: an identity placement is a bit-perfect copy. | **VERIFIED** §3.1 |
| 4 | The null **does not pass on red and blue** — an identity placement is not a pass-through for chroma. | **VERIFIED, and reported loudly** §3.1 |
| 5 | The energy the placement removes from R/B is noise and aliasing on the CFA chroma subgrid, **not** scene detail. | **VERIFIED** §3.3 |
| 6 | `crop` changes output pixel dimensions — a user-visible print-size consequence. | **VERIFIED** §4, quantified §4.1 |

This is a correctness and honesty change, not a quality change.

---

## 0b. The two open defects are now diagnosed

Both items left open at the end of the first pass have mechanisms. One of them
**reverses a claim made earlier in this document**, and one of them **dissolves
the lane's own headline negative result**. Both are written up in full at §10
(the border overshoot) and §11 (the R/B null).

| | finding | status |
| --- | --- | --- |
| **A** | The near-border level difference is **not** in `scale`. It is a **bright ringing overshoot in the `crop`/no-fit render**, caused by the black-filled uncovered region forming a hard step that the pyramid's per-band election spreads inward by **~2^bands px**. | **DIAGNOSED** §10 |
| **B** | The R/B null failure is **not a defect**. It is the gear-gated **lateral chromatic aberration correction**, which by design holds green fixed and moves R and B. With `STREHL_FIX_CA=off` the null passes **100.0000% on all three channels at 0 DN**. | **DIAGNOSED, not a bug** §11 |

**Correction to §6c.** That section speculated "on this evidence it is the
*scale* render's outer ring that is depressed". **That was wrong, and §10
measures it wrong.** `scale` is the clean one; `crop` carries the artifact.

**Correction to §0 claim 4 and §3.1.** The null does not fail. It passes
completely once the CA correction — an unrelated, intended transform that
`STREHL_ALIGN=0` silently disables — is held constant. §11 replaces §3.1.

---

## 1. What the mode is, and how you ask for it

| | |
| --- | --- |
| flag | `strehl stack --cover <scale\|crop>` |
| env | `STREHL_COVER=scale` / `STREHL_COVER=crop` |
| default | **`scale`** — unchanged, see §2 |
| precedence | flag wins, then env, then default (same rule as `--photometric`) |
| bad value | **hard error** in either channel, no fallback |

`STREHL_COVER` already existed as an on/off measurement control. Its old
vocabulary is untouched: `0`/`off`/`false`/`no` still means *apply no coverage
fit at all and leave uncovered edges in the picture*. That spelling is
deliberately **not reachable from `--cover`** — it produces a knowingly wrong
render, and a command line is the channel a caller reaches for when they want
output they intend to keep.

Extending the existing variable rather than adding `STREHL_COVER_MODE` was a
deliberate choice: `scripts/check-defaults.py` treats an undeclared environment
switch as a hard failure, `STREHL_COVER` is already declared there, and that
file is being edited concurrently by at least three other lanes (§8 item 3).

### What `crop` does

`scale` (the default) bisects for the largest `k <= 1` such that the reference
grid scaled by `k` about the plane centre lands inside every placed frame, then
**composes that scale into every placement**. The field of view shrinks by `k`
and the output keeps its pixel dimensions, so every pixel of every render is
upsampled by `1/k` — including the reference frame's, whose placement is
otherwise the identity.

`crop` fits **the same `k` from the same placements** and then composes
**nothing**. It emits the axis-aligned rectangle that is the image of the full
plane under that scale, at unity scale:

```rust
lo = 0.5 * n * (1 - k)        // image of coordinate 0
hi = lo + k * (n - 1)         // image of coordinate n-1
x0 = ceil(lo)   x1 = floor(hi)   width = x1 - x0 + 1     // rounded INWARD
```

Fitting the crop from the scale path's own `k` is what makes the two modes
comparable: crop renders *exactly the region scale renders*, so a difference
between them is the resampling and nothing else.

### Where the crop is applied, and why not in the merge

`strehl_core::warpmap::gather_checked` returns `GeometryMismatch` unless the
source geometry equals the destination geometry, and `warp_frame_in_place`
warps into the frame's own buffer. The merge therefore **cannot** be run onto a
smaller grid without reworking the gather. The crop is instead a pure integer
window applied at `write_merged`, ahead of every downstream branch (exposure
statistic, restore/demosaic, binned, byte-frozen encode), via an index
remapper with an identity fast path when the rectangle is the whole plane.

**Consequence, measured not assumed (§6):** in crop mode the merge still runs on
the full plane and still folds each frame's fill outside the covered region; the
crop discards that ring rather than preventing it.

The rectangle is in **plane (quad) pixels**, so the `--srgb`/`--demosaic`
full-resolution path doubles an integer offset and the CFA phase of the emitted
image is the one the merge produced. Verified: §4, Test 2.

### Files changed

| file | change |
| --- | --- |
| `crates/strehl-cli/src/align_cmd.rs` | `CoverMode`, `CropRect`, `CoverFit`, `cover_rect`, `crop_banner`, `cover_mode_from_env`, `COVER_MARGIN_PX`; `fit_to_cover` split into `cover_scale` (the bisection) + `fit_to_cover` (the composition, unchanged); `cover_or_explain` now takes a mode |
| `crates/strehl-cli/src/merge_cmd.rs` | `MergeOptions.cover` / `.cover_source`; `resolve_cover_mode`; `cover_mode_line`; banner match over `CoverFit` in **both** backends; `write_merged` takes `Option<CropRect>` |
| `crates/strehl-cli/src/main.rs` | the `--cover` flag on `stack`, resolved once and passed to both backends |
| `crates/strehl-cli/examples/blend-render.rs` | stays on the default path; **refuses** `crop` rather than accepting it and silently emitting the uncropped picture |

`resolve_cover_mode` lives in `merge_cmd.rs`, not `align_cmd.rs`, because
`SettingSource` is a merge-path type and `align_cmd.rs` is `#[path]`-included by
three examples that do not compile the merge path. Discovered by a compile
failure, not by inspection.

---

## 2. The default did not move — VERIFIED, both backends

Two independent instruments, because "I only touched the new arm" is an
argument, not a measurement.

### 2a. The byte-freeze registry (estimator arm)

```
$ cargo test --release -p strehl-cli --target-dir .cargo-target-crop
...
test result: ok. 115 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out

     Running tests\byte-freeze.rs
running 5 tests
test every_registry_row_records_a_complete_invocation ... ok
test no_two_rows_freeze_the_same_invocation ... ok
test the_alignment_parser_names_every_mode_the_tool_can_report ... ok
test the_hasher_reproduces_the_published_test_vectors ... ok
freeze `coffee-bean-20-gate2-unaligned` HOLDS:
  88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620
  (49450019 bytes, alignment off, 10 chunks of <= 2 frames) -- reproduced twice
freeze `coffee-bean-20-gate2-sidecar` HOLDS:
  52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206
  (49450019 bytes, alignment on-sidecar-override, 10 chunks of <= 2 frames,
   20 placed / 0 refused) -- reproduced twice
test result: ok. 5 passed; 0 failed
```

The `sidecar` row runs with alignment ON, so it exercises `cover_or_explain` and
`fit_to_cover` — the functions this lane rewrote. Both rows are `--merge
estimator` rows (hardcoded at `tests/byte-freeze.rs:544`), so **this instrument
says nothing about the pyramid backend**, which is the shipping default.

### 2b. A control binary, for the pyramid default

`cargo fmt`-style reasoning is not enough here, so: the source tree was copied
to `C:\dev\strehl-out\BUILD-CROP\ctl`, this lane's **four files only** were
reverted to `HEAD` with `git show HEAD:<path>` (a read-only git operation — no
`checkout`, no `stash`, nothing that could disturb another agent), and the other
lane's in-flight `crates/strehl-core/src/pyramid.rs` was **left in place** and
hash-verified identical to the live tree. That isolates this lane's four files
and nothing else.

```
### CONTROL binary (my 4 files at HEAD), default pyramid, no flags
$ ctl\tgt\release\strehl.exe stack D:\personal\macro\109MSDCF --out ctl-109-default.tiff
  coverage      : field of view scaled to 0.9870 so that EVERY frame covers every pixel
                  (1.3% of width dropped, then upsampled to keep the output dimensions).
wrote           : ctl-109-default.tiff (3516 x 2344, ...)

Path : ctl-109-default.tiff
Hash : A938C14CD2357D629F5CB5E39331AB89F9C0BE799F94641353E0DC600516B91C
Path : t2-109-scale.tiff
Hash : A938C14CD2357D629F5CB5E39331AB89F9C0BE799F94641353E0DC600516B91C
IDENTICAL: True
sizes: 49450019 vs 49450019
```

And the estimator with default flags (photometric ON, which the frozen rows
turn off), for completeness:

```
control : 51A10827F49E26021669D75DDB3D3F292444714AC2F15091ED1D838DB2EBFF56
mine    : 51A10827F49E26021669D75DDB3D3F292444714AC2F15091ED1D838DB2EBFF56
IDENTICAL: True
```

**VERIFIED: an invocation that omits `--cover` is byte-identical on both
backends.** The new `coverage mode :` provenance line prints only when the
caller actually asked (`SettingSource::asked()`), so the default banner is
unchanged too — visible above, the control and the live binary print the same
stderr.

---

## 3. Test 1 — the mechanism proof, and where the null FAILS

This section carries the entire weight of the lane. It has four parts, and the
second-most important one is a **failure**.

### 3.1 The null passes exactly on green — and FAILS on red and blue

**HEADLINE FINDING. Reported loudly, as commissioned.**

Subject: one ARW (`DSC00009.ARW`) alone in a private directory
(`D:\strehl-out\BUILD-CROP\one\`). Its solved sidecar placement is **exactly
the identity** (`a = 1.0 + 0i`, `b = 0 + 0i`, read from
`%LOCALAPPDATA%\strehl\warpmaps\one-2ca189e6463d3f43.warpmap.txt`). In `crop`
mode nothing is composed onto it, so the gather is asked to perform an exact
identity. Against the directly-demosaiced input (`STREHL_ALIGN=0`, no warp path
at all) it should therefore be a bit-perfect copy.

`python experiments\BUILD-CROP\nullcheck.py n-base.tiff 5 4 ...`:

```
=== crop, default gather (fullres ON)  (3506x2337 vs base window at (5,4))
 ch   bit-exact    max|d|    mean|d|     lap base   lap render     ratio
  R     4.8217%      1402   133.7171     548661.1     278426.3   0.50747
  G   100.0000%         0     0.0000     101490.8     101490.8   1.00000
  B    12.5086%       399    30.0014     240923.5     193482.7   0.80309
```

**Green: 100.0000% bit-exact, max difference 0 DN, laplacian ratio exactly
1.00000.** Every one of the 8.19 million green samples in the covered rectangle
survives the round trip unchanged. That is the null, and on green it passes
perfectly.

**Red and blue do not.** Only 4.8% of red and 12.5% of blue samples are
reproduced, and both planes lose laplacian energy — red **half** of it. This is
not a shift: an integer-offset scan finds the minimum at exactly `dx=+0 dy=+0`,
the median ratio is exactly 1.0, and the global gain is 0.99877.

**So placements ARE lossy for a reason other than `k`** — this is exactly the
outcome the orchestrator flagged as more interesting than the sharpness
question. It is a chroma-plane effect, present at the exact identity, at unity
scale, with nothing composed. It is **pre-existing**, not introduced by this
change; `crop` mode is simply the first configuration in which it is visible,
because it is the first one in which the placement is an exact identity.

I isolated the full-resolution gather, which was my working hypothesis for it:

```
=== crop, per-phase-plane gather (fullres OFF)  (3506x2337 vs base window at (5,4))
 ch   bit-exact    max|d|    mean|d|     lap base   lap render     ratio
  R     5.6748%      1351   129.1910     548661.1     253418.2   0.46188
  G   100.0000%         0     0.0000     101490.8     101490.8   1.00000
  B    19.5946%       308    17.9296     240923.5     183639.0   0.76223
```

**Hypothesis refuted.** `STREHL_FULLRES_GATHER=0` does not fix it and makes red
slightly *worse* (0.462 vs 0.507). The effect is present in both gather
backends. **Cause NOT DIAGNOSED** — handed over, see §9 lead 1.

### 3.2 What `crop` mode itself removes — the clean null

`STREHL_ALIGN=0` is not the right null for the *coverage* question, because it
mixes "no `S_k`" with "no warp at all" — as §3.1 shows, those are not the same.
The clean null is `STREHL_COVER=0` versus `--cover crop` on the same stack:
identical merge, identical placements, identical everything, the **only**
difference being whether `S_k` is composed and which window is written.

Note the fit still returns `k = 0.9974` for a perfect identity, because
`COVER_MARGIN_PX = 3` forces `k <= 1 - 6/2344` regardless. This is the extreme
case the defect report named: the reference frame, which should pass untouched.

```
### A) CROP vs NO-FIT (same aligned path, only S_k differs), window at (5,4)
full t1-nofit.tiff       (2344, 3516, 3) uint16
crop t1-ident-crop.tiff  (2337, 3506, 3) uint16
window at (5,4) size 3506x2337, 24580566 samples
  exact-equal samples : 24580566 / 24580566  (100.0000 %)
  max |diff|          : 0 DN
  VERDICT             : BIT-IDENTICAL

### B) SCALE vs NO-FIT, same render, whole frame
window at (0,0) size 3516x2344, 24724512 samples
  exact-equal samples : 515852 / 24724512  (2.0864 %)
  max |diff|          : 9736 DN
  mean |diff|         : 131.608035 DN
  p99.9 |diff|        : 1633.000 DN
  VERDICT             : DIFFERS
```

**The prediction held for the part of the pipeline this lane owns.** In `crop`
mode the covered region is written with **zero** interpolation from `S_k` —
24,580,566 of 24,580,566 samples bit-identical, all three channels, max
difference 0 DN. In `scale` mode the same render differs on **97.9%** of its
samples, by up to 9,736 DN. `S_k` does ride on every placement, and removing it
does remove that resample entirely.

### 3.3 Is the R/B loss detail, or noise? — it is noise

A laplacian drop alone cannot distinguish "detail was removed" from "noise and
aliasing were removed". The base R and B planes are **one raw CFA sample per
quad** (critically sampled, aliased, full per-sample noise), while base G is the
mean of two samples. Base R carries 5.4× green's laplacian energy, which is not
plausible as scene structure — red detail in a real subject is not five times
greener — so much of it must be noise and aliasing.

`flatvstex.py` splits the frame into 32 px cells and partitions them by the
**green** gradient — an unbiased referee, since green is reproduced exactly and
therefore cannot itself be moved by the effect under test:

```
cells 109x73 of 32px; green gradient p25=64.67 p75=80.58
 ch   partition      lap base    lap render     ratio
  R        flat      298481.3      131255.2   0.43974
  R    textured      563311.1      300593.8   0.53362
  G        flat       27297.1       27297.1   1.00000
  G    textured      109032.7      109032.7   1.00000
  B        flat      100610.0       87288.9   0.86760
  B    textured      249808.9      203653.2   0.81524
```

**The loss does not concentrate in textured cells.** For red it is *worse in
flat cells* (0.440) than in textured ones (0.534). Detail removal would show the
opposite ordering. This is the signature of **noise and aliasing suppression on
the chroma subgrids**, not an acuity loss.

So the honest reading of §3.1 is: the identity placement **rewrites** the R and
B planes rather than passing them through, and what it removes is predominantly
noise. That is still a null failure and still worth knowing — a placement that
claims to be the identity should be the identity — but it is **not** evidence of
a detail loss, and I am not offering it as one.

### 3.4 The one laplacian number in this report, and why it proves nothing

For completeness, on the same one-frame identity render (green channel, fixed
interior window):

```
t1-base-align0   laplacian-energy      83821.5  mean   5074.05
t1-nofit         laplacian-energy      83821.5  mean   5074.05
t1-ident-crop    laplacian-energy      83823.5  mean   5072.97
t1-ident-scale   laplacian-energy      75876.3  mean   5068.34
```

`scale` carries 9.5% less high-frequency energy than the same pixels
unresampled. **This number must not be quoted as a win, and it does not survive
V-REVIEW's 270× objection.** Three reasons, stated head-on:

1. **It is a degenerate case that never occurs in production.** One frame, an
   exactly-identity placement, `k = 0.9974`. The upsample buys literally nothing
   here because one frame covers itself. Every real stack has non-identity
   placements.
2. **Catmull-Rom's top-octave attenuation depends on sampling *phase*, not on
   the magnitude of `(1-k)`.** The 9.5% appears because removing `S_k` takes
   this render from a non-integer step to an *exactly integer* one — a
   pass-through. In a real deep stack the placements are already non-integer, so
   removing `S_k` moves the step from 0.9315 to ~1.0014: still non-integer,
   still paying the full kernel cost. The saving does not transfer.
3. **It was already measured on real stacks and came out the wrong sign.**
   SYNTHESIS facts 1419 / 1459 measured **−0.0030 dex** — sharpness got very
   slightly *worse* — on 8 of 9 stacks when the enlargement was removed.
4. **Laplacian energy is a raw band-power statistic and counts noise as
   sharpness** (ORCH's guard, after an arm read +0.142 sharper raw and −0.134
   softer once noise-corrected — a sign flip). This number is **not**
   noise-corrected, so on its own it cannot be trusted, and least of all in flat
   regions. §3.3 is the only place in this report where a laplacian reading is
   load-bearing, and there it is explicitly partitioned flat-vs-textured for
   exactly this reason.

Point 2 is precisely why V-REVIEW's 270× stands: the effect scales with the
kernel, not with `k`, so shrinking `k` toward 1 does not buy back the kernel.
**No sharpness claim survives.** What §3.2 proves is the *mechanism* — crop mode
composes nothing, so a placement that *is* an exact integer now survives
exactly. Whether that is ever worth anything on a real subject is the verifier's
measurement, not mine, and the prior evidence says it is not.

---

## 4. Test 2 — dimensions

| stack | frames | mode | k | output | rect origin |
| --- | --- | --- | --- | --- | --- |
| `109MSDCF` | 22 | scale | 0.9870 | **3516 x 2344** | — |
| `109MSDCF` | 22 | crop | 0.9870 | **3470 x 2312** | (23, 16) |
| `bee-1-cpl` | 299 | scale | 0.9236 | **3516 x 2344** | — |
| `bee-1-cpl` | 299 | crop | 0.9236 | **3246 x 2164** | (135, 90) |
| `109MSDCF --srgb` | 22 | scale | 0.9870 | **7032 x 4688** | — |
| `109MSDCF --srgb` | 22 | crop | 0.9870 | **6940 x 4624** | (23, 16) quad px |

The full-resolution sRGB outputs are exactly `2 x` the quad-plane dimensions in
both modes (`6940 = 2 x 3470`, `4624 = 2 x 2312`), so the doubled crop origin
lands on an even boundary and the CFA phase is preserved. **VERIFIED.**

Banners, verbatim:

```
coverage mode   : crop -- as asked, --cover
  coverage      : CROPPED to the region EVERY frame covers -- 3470 x 2312 plane px
                  at (23, 16) of 3516 x 2344, emitted at UNITY SCALE. 1.3% of width
                  dropped and NOT upsampled (k=0.9870), so the output is SMALLER than
                  the plane by design and no placement carries a coverage scale. The
                  reference frame's own placement reaches the gather unmodified.
wrote           : t2-109-crop.tiff (3470 x 2312, 16-bit RGB, ...)
```

```
  coverage      : CROPPED to the region EVERY frame covers -- 3246 x 2164 plane px
                  at (135, 90) of 3516 x 2344, emitted at UNITY SCALE. 7.6% of width
                  dropped and NOT upsampled (k=0.9236), ...
wrote           : t2-bee-crop.tiff (3246 x 2164, 16-bit RGB, ...)
```

The crop banner shares **no phrase** with the scale banner, so the ~30 harnesses
under `experiments/` that regex `field of view scaled to ([0-9.]+)` cannot match
a crop render and silently record a scale factor that was never applied.

**Discrepancy with the brief, worth flagging:** the task described `bee-1-cpl` as
`k = 0.9321`. I measure **`k = 0.9236`** (banner, and independently fitted from
the render pair in §6 to `0.923600`). I did not chase the difference; possible
causes are a re-solved sidecar or a different frame set. The tax is 7.6% of
width, not 6.8%.

### 4.1 Yes, `crop` changes output pixel dimensions — the print-size consequence

**This is a user-visible behaviour change and is documented here rather than
left to be discovered.** `scale` keeps the plane's dimensions and upsamples to
fill them; `crop` keeps unity scale and therefore emits a **smaller image**.

| subject | frames | `k` | scale dims | crop dims | width | height | **pixel count** |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| `109MSDCF` | 22 | 0.9870 | 3516 x 2344 | 3470 x 2312 | −1.31% | −1.37% | **−2.66%** |
| `bee-1-cpl` | 299 | 0.9236 | 3516 x 2344 | 3246 x 2164 | −7.68% | −7.68% | **−14.77%** |

On a 299-frame stack the output loses **7.7% of its width and 7.7% of its
height, i.e. 14.8% of its pixels** — 8.24 MP down to 7.02 MP. At 300 dpi the
print goes from **11.72 x 7.81 inches to 10.82 x 7.21 inches**, a loss of about
nine tenths of an inch on the long edge.

Two things follow, and both are consequences of the trade, not defects:

- **The tax grows with stack depth.** `k` shrinks as `N` grows, so the deepest
  stacks — the showcase images — lose the most print size. This is the exact
  mirror of the upsample tax `scale` pays, moved from resolution to dimensions.
- **No pixel is invented.** `scale`'s 8.24 MP contains 7.02 MP of real
  information stretched over 8.24 MP of grid. `crop`'s 7.02 MP is 7.02 MP of
  information on a 7.02 MP grid. The *information* content is the same; only the
  honesty of the container differs. That is the whole argument for this mode.

**ASSUMED, not measured:** that downstream consumers (web export presets, print
templates, any fixed-size comparison harness) tolerate a varying output size. A
harness that hardcodes 3516 x 2344 will break on a crop render. This is a real
integration risk of flipping the default and is the main reason the mode ships
opt-in.

---

## 5. Test 3 — both backends honour the mode

Run, not grepped. Both on `109MSDCF`, both with `--cover crop`.

```
### default backend (pyramid)
coverage mode   : crop -- as asked, --cover
alignment       : ON (sidecar), reference frame 11, 22 placed / 0 refused, 0.0 s
  coverage      : CROPPED to the region EVERY frame covers -- 3470 x 2312 plane px at (23, 16) ...
wrote           : t2-109-crop.tiff (3470 x 2312, ...)

### --merge estimator
merge backend   : estimator (--merge)
strehl stack -- regularised winner + noise-gated average (--merge estimator; reachable, NOT the default)
coverage mode   : crop -- as asked, --cover
alignment      : ON (sidecar), reference frame 11, 22 placed / 0 refused
  coverage      : CROPPED to the region EVERY frame covers -- 3470 x 2312 plane px at (23, 16) ...
wrote           : t3-109-est-crop.tiff (3470 x 2312, ...)
```

Both emit **3470 x 2312**. The mode is resolved **once** in `main.rs` and stored
on `MergeOptions`, and both backends print through the same `crop_banner`
function, which is the structural reason a fix cannot land in one backend only.

### 5a. The banner and the dimensions are not enough — the estimator's pixels

**Added after ORCH's instrument-defect broadcast** (a presence test cannot
detect a reversed conclusion). As first written, Test 3 checked the estimator
backend's *banner text* and *output dimensions*. Both are satisfiable by a
backend that crops at the **wrong origin**: the banner is printed from the
resolved mode, not from the window actually written, and the dimensions are
right for any origin. That is exactly the defect shape being warned about, and
the commission warned that a previous fix here landed in one backend and
shipped broken.

So the estimator backend now carries the same bit-exact guard as the default:

```
=== ESTIMATOR backend: crop window vs no-fit, at the banner's origin (23,16)
full e-nofit.tiff  (2344, 3516, 3) uint16
crop e-crop.tiff   (2312, 3470, 3) uint16
window at (23,16) size 3470x2312, 24067920 samples
  exact-equal samples : 24067920 / 24067920  (100.0000 %)
  max |diff|          : 0 DN
  VERDICT             : BIT-IDENTICAL
```

**24,067,920 of 24,067,920 exact.** The estimator crops at the origin its banner
claims, not merely to the right size.

**And the guard has teeth** — commissioned with a mutation that flips the
conclusion rather than perturbing a number. If the same comparison passed at a
neighbouring origin it would be certifying nothing:

```
=== MUTANT origin (22,16)   exact 248651 / 24067920 (1.0331 %)  max 10651 DN  DIFFERS
=== MUTANT origin (24,16)   exact 248618 / 24067920 (1.0330 %)  max 10651 DN  DIFFERS
=== MUTANT origin (23,15)   exact 245336 / 24067920 (1.0193 %)  max  7394 DN  DIFFERS
=== MUTANT origin (23,17)   exact 245284 / 24067920 (1.0191 %)  max  7394 DN  DIFFERS
```

A one-pixel error in **either** axis collapses the check from 100.0000% to
~1.03%. The guard is pinned to the specific origin it certifies.

---

## 6. Test 4 — no content regression, and the off-by-one guard

### 6a. The exact guard (this is the one that matters)

A crop render must be bit-identical to the same render with no fit at all,
windowed at the rectangle origin. Any off-by-one or half-pixel error in
`cover_rect` destroys this instantly. Run on the **real 22-frame stack**, not
just the single frame:

```
### 22-frame CROP vs NO-FIT windowed at (23,16)
full t4-109-nofit.tiff  (2344, 3516, 3) uint16
crop t2-109-crop.tiff   (2312, 3470, 3) uint16
window at (23,16) size 3470x2312, 24067920 samples
  exact-equal samples : 24067920 / 24067920  (100.0000 %)
  max |diff|          : 0 DN
  VERDICT             : BIT-IDENTICAL
```

**24,067,920 of 24,067,920 samples exact.** Together with the 24,580,566-sample
single-frame result in §3.2 and the 24,067,920-sample estimator result in §5a,
that is **72.7M samples with zero mismatches**, across two values of `k`, two
rectangle origins, and both merge backends — plus four one-pixel mutants that
all fail as they must (§5a).

**No bug was found in the rectangle computation.**

### 6b. Same scene as the scale render, no sub-pixel shift

`scale` output pixel `p` carries reference-plane point `c + k(p - c)`; `crop`
output pixel `r` carries `r + (x0, y0)`. Equating gives
`p = c + (r + (x0,y0) - c)/k`. Resampling the scale render through that map and
comparing to the crop render, over a grid of sub-pixel offsets:

```
### 109MSDCF crop vs scale, k=0.9870, rect (23,16)
patch 1735x1156 at crop (867,578)
   dx=+0.00 dy=+0.00  mean |resid| =   37.5854 DN
   dx=+0.25 dy=+0.00  mean |resid| =   43.2660 DN
   dx=-0.25 dy=+0.00  mean |resid| =   43.8648 DN
   dx=+0.00 dy=+0.25  mean |resid| =   46.1272 DN
   dx=+0.00 dy=-0.25  mean |resid| =   46.6894 DN
   ARGMIN: dx=+0.00 dy=+0.00
   at (0,0): pearson r = 0.99978063, mean|resid| = 37.5854 DN, level ratio = 0.999982
```

The residual minimises at **exactly (0.00, 0.00)** — a half-pixel error would
move it to ±0.5. `r = 0.99978`, level ratio `0.999982` (no gain change). The
37.6 DN residual is 0.75% of the interior level and is the expected difference
between an upsampled render and an unresampled one.

Independently, the scale factor itself was **fitted from the pixels** rather than
trusted from the banner, because at 1600 px from centre a `k` error of 1e-4 is a
0.19 px shift that could fake an edge effect:

```
### bee-1-cpl, scanning k about the printed 0.9236
   k=0.923500  mean|resid| =  299.9455 DN
   k=0.923550  mean|resid| =  297.2583 DN
   k=0.923600  mean|resid| =  296.5125 DN   <- clean parabolic minimum
   k=0.923650  mean|resid| =  297.8574 DN
   k=0.923700  mean|resid| =  301.0230 DN
   BEST k = 0.923600
```

The fitted `k` **equals the printed `k`**. The mapping is right.

### 6c. Fill from outside the rectangle — checked, and a finding

In crop mode the merge still runs on the full plane and the region no frame
reaches is filled before the window discards it. The pyramid's coarse bands have
support of order `2^k` px, so that fill could in principle be dragged inward past
the rectangle edge. Two checks:

**Black pixels.** `clipcheck` reports `black%` = fraction of pixels at zero in
any channel:

| render | black% |
| --- | --- |
| `t4-109-nofit` (full plane, no fit) | **1.62%** |
| `t2-109-crop` (the same render, windowed) | **0.00%** |
| `t1-nofit` (one frame, full plane) | **0.17%** |
| `t1-ident-crop` (the same, windowed) | **0.00%** |

The rectangle excludes **every** uncovered pixel.

**Edge level profile.** The outermost columns/rows of both crop renders are
*flat* and, in these subjects, brighter than the interior (bright background):
`t2-109-crop` column 0 = 7561.66 DN against column 40 = 7559.78 DN, a 0.03%
difference. **No dark ramp. No black-fill bleed.**

**But a real effect was found, and it is not black-fill bleed.** Comparing crop
against scale in bands by distance from the crop border (both renders resampled
onto a common grid with the fitted `k`):

```
### bee-1-cpl (299 frames, k=0.9236, pyramid)
     band px           n    crop mean   scale mean      ratio
         0-2       21624     15844.94     13877.88   1.141740
         4-8       43088     15775.02     13886.89   1.135965
        16-32      170048     15415.75     13836.36   1.114148
        64-128      643328     14224.70     13777.34   1.032471
        128+     5704920      9556.33      9546.95   1.000982

### 109MSDCF (22 frames, k=0.9870, rectangle only 23 px inside the plane)
         0-2       23112      6798.42      6613.42   1.027974
        64-128      690944      6731.41      6604.40   1.019232
        128+     6607984      6059.30      6050.46   1.001462

### ONE FRAME (k=0.9974) -- the control
         0-2       23356      6596.08      6595.89   1.000029
        16-32      183904      6598.98      6599.03   0.999992
        128+     6763250      6052.09      6052.14   0.999992
```

The **crop** render is up to **14% brighter** than the **scale** render at the
same scene points near the border, decaying to ~1.001 by 128 px in. Ruled out:

- **my rectangle** — the bit-identical windowing in §6a forbids an offset error;
- **my `k`** — fitted from the pixels in §6b, equals the printed value;
- **a merge/plane-boundary artifact** — the single-frame control is flat to
  **1.00003** at the very border;
- **the direction expected of black-fill bleed into crop** — the sign is wrong;
  bleed would make crop *darker*, and crop is *brighter*.

So it is a **multi-frame effect that appears only where frames disagree about
coverage**, and on this evidence it is the **scale** render whose outer ring is
depressed, not the crop render's. I did **not** isolate the cause and I am not
going to guess at one. **Handed to the verifier as an open finding** — if it is
real it is a defect in the current default, and it is worth a look at 1:1.

---

## 7. Test 5 — exposure guard

```
$ python experiments\ORCH-drift-check\clipcheck.py C:\dev\strehl-out\BUILD-CROP
subject                                     clip%   black%   median    verdict
t1-base-align0                              0.00%    0.00%     7181         ok
t1-ident-crop                               0.00%    0.00%     7161         ok
t1-ident-scale                              0.00%    0.00%     7161         ok
t1-nofit                                    0.00%    0.17%     7161         ok
t2-109-crop                                 0.00%    0.00%     7226         ok
t2-109-scale                                0.00%    0.00%     7209         ok
t2-bee-crop                                 0.00%    0.00%    11294         ok
t2-bee-scale                                0.00%    0.00%    10892         ok
t3-109-est-crop                             0.00%    0.00%     7209         ok
t3-109-est-scale                            0.00%    0.00%     7210         ok
t4-109-nofit                                0.00%    1.62%     7104         ok
t6-109-srgb-crop                            0.00%    7.35%    61296         ok
t6-109-srgb-scale                           0.00%    7.54%    61063         ok

0/13 BLOWN (>25% clipped), 0 high, 13 ok
```

**13/13 `ok`, 0 BLOWN.** Every crop render passes, on both backends and both
output paths.

Re-run after the move to D:, covering the re-measured null renders of §3.1:

```
$ python experiments\ORCH-drift-check\clipcheck.py D:\strehl-out\BUILD-CROP
subject                                     clip%   black%   median    verdict
n-base                                      0.00%    0.00%     7181         ok
n-crop-nofullres                            0.00%    0.00%     7161         ok
n-crop                                      0.00%    0.00%     7161         ok
t2-109-crop                                 0.00%    0.00%     7226         ok
t2-109-scale                                0.00%    0.00%     7209         ok
t2-bee-crop                                 0.00%    0.00%    11294         ok
t2-bee-scale                                0.00%    0.00%    10892         ok

0/7 BLOWN (>25% clipped), 0 high, 7 ok
```

**20/20 `ok` across both runs, 0 BLOWN.**

---

## 8. Known gaps, and things left alone deliberately

1. **An exactly-identity placement does not reproduce the R and B planes**
   (§3.1). This is the lane's headline negative result. Green is 100.0000%
   bit-exact through the identity; R is 4.8% and B is 12.5%, at zero spatial
   offset, in **both** gather backends (`STREHL_FULLRES_GATHER` on and off).
   §3.3 establishes the removed energy is flat-field-dominated, i.e. noise and
   aliasing on the CFA chroma subgrids rather than scene detail — so it is not
   an acuity loss — but the cause is **NOT DIAGNOSED**. It is **pre-existing**,
   not introduced here; `crop` mode is merely the first configuration in which
   a placement is an exact identity and the failure becomes visible. Someone
   should find out why the chroma planes do not survive an identity warp. Not
   this lane's change and not this lane's file.
2. **The near-border level difference between crop and scale** (§6c) is
   characterised, has four candidate causes ruled out, and is **not diagnosed**.
3. **`scripts/check-defaults.py` was not edited.** Its `STREHL_COVER` row
   describes the on/off polarity only, and is now *incomplete* rather than
   wrong: `scale` is still the default and `0` still turns the fit off. It was
   left alone because it is a shared file that at least three other lanes must
   edit right now — verified: the control tree (this lane's four files reverted
   to HEAD) **fails the lint identically**, `FAIL: 3 switch(es) are not declared`
   (`STREHL_GATE_FLOOR_SCALE`, `STREHL_HULL`, `STREHL_PYRAMID_WEIGHT_DUMP` — all
   other lanes') and `FAIL: 1 quality switch(es) default to OFF`. This lane adds
   **nothing** to that failure. Adding the `crop` spelling to the row is a
   one-line follow-up for whoever holds that file next.
4. **`cargo fmt --check` is not clean, before or after.** The tree has **300**
   hunks with this lane's four files reverted and **304** with them present, so
   4 hunks (1 unique location, in `align_cmd.rs`) are attributable here.
   `cargo fmt` was **not** run: it would rewrite `build.rs`, `blend-render.rs`
   and five example files that other lanes are actively editing.
5. **`k >= 1` in crop mode is ASSUMED, not exercised.** `crop_banner` and
   `CropRect::is_whole` handle it (whole-plane rect, identity fast path, a
   banner that says nothing was cropped), but `COVER_MARGIN_PX = 3` means real
   data never produces `k >= 1`, so no run in this report took that branch.
6. **A maximal, non-centred rectangle is not implemented.** The rect is derived
   from the scale path's centred `k` so the two modes render the same region and
   §6b is meaningful. When drift is one-sided a non-centred rectangle would
   recover more field of view. Follow-up, deliberately not done here.
7. **This lane makes no sharpness claim** (§0, §3.4). Test 1 is a mechanism
   proof on a pixel-exactness null, not a quality measurement. V-REVIEW commit
   `cc985615` found `fit_to_cover` **270× too small** to explain the observed
   softness, and SYNTHESIS facts 1419/1459 already record that removing the
   enlargement measured **−0.0030 dex, the wrong sign**, on 8 of 9 stacks. The
   single laplacian number in §3.4 is a degenerate one-frame result and §3.4
   explains why it does not transfer. A separate verifier owns the quality
   question; on the present evidence there is nothing there to find.
8. **`crop` changes output pixel dimensions** — −2.7% of pixels at N=22, −14.8%
   at N=299 (§4.1). Any consumer that hardcodes 3516 x 2344 will break on a crop
   render. Not measured: which consumers those are. Principal reason the mode
   ships opt-in.

---

## 9. Reproduction

```powershell
# NB: outputs now go to D: (C: hit 4.4% free). D:\personal\macro is READ-ONLY.
cargo build --release --target-dir D:\strehl-out\BUILD-CROP\tgt
$exe = "D:\strehl-out\BUILD-CROP\strehl-BUILD-CROP-aa40cc78.exe"
$o   = "D:\strehl-out\BUILD-CROP"

# the mode
& $exe stack D:\personal\macro\109MSDCF --cover crop --out "$o\crop.tiff"
$env:STREHL_COVER = "crop"; & $exe stack D:\personal\macro\109MSDCF --out "$o\crop.tiff"

# the exact guard (Test 1 / Test 4a)
$env:STREHL_COVER = "0"; & $exe stack D:\personal\macro\109MSDCF --out "$o\nofit.tiff"
Remove-Item Env:\STREHL_COVER
& $exe stack D:\personal\macro\109MSDCF --cover crop --out "$o\crop.tiff"
python experiments\BUILD-CROP\cmp.py "$o\nofit.tiff" "$o\crop.tiff" 23 16

# the null that FAILS on R/B (§3.1, §3.3) -- one frame, identity placement
$env:STREHL_ALIGN = "0"; & $exe stack "$o\one" --out "$o\n-base.tiff"
Remove-Item Env:\STREHL_ALIGN
& $exe stack "$o\one" --cover crop --out "$o\n-crop.tiff"
python experiments\BUILD-CROP\nullcheck.py  "$o\n-base.tiff" 5 4 "crop=$o\n-crop.tiff"
python experiments\BUILD-CROP\flatvstex.py  "$o\n-base.tiff" "$o\n-crop.tiff" 5 4

# the rest
python experiments\BUILD-CROP\crop_vs_scale.py  "$o\scale.tiff" "$o\crop.tiff" 0.9870 23 16 3516 2344
python experiments\BUILD-CROP\fitk.py           "$o\scale.tiff" "$o\crop.tiff" 0.9870 23 16 3516 2344
python experiments\BUILD-CROP\bleedband.py      "$o\scale.tiff" "$o\crop.tiff" 0.9870 23 16 3516 2344
python experiments\BUILD-CROP\borderprofile.py  "$o\crop.tiff"
python experiments\ORCH-drift-check\clipcheck.py $o
```

---

## 10. DEFECT A -- the near-border level difference, diagnosed

**Verdict: the artifact is in the `crop` / no-fit render, NOT in `scale`. It is
ringing from the black-filled uncovered region, spread inward by the pyramid.**

This reverses the guess in §6c. It was wrong; here is the measurement.

### 10.1 First: the detector was commissioned before it was believed

Required by ORCH, and it changes what the 14% is allowed to mean.
`plantcheck.py` runs the band-ratio detector in a NULL arm (crop against itself
through the same mapping, so every step is shared except the effect) and a
PLANT arm (a known multiplicative error inside a known border width):

```
== NULL (crop vs itself through the same mapping; must read 1.000000)
null k=1            0-2:1.000000  4-8:1.000000  16-32:1.000000  64-128:1.000000  128-:1.000000

== PLANT (known error in the outer 8 px of crop; detector must recover it)
plant x1.100 -> 1.100000 PASS   0-2:1.100000  4-8:1.100000  16-32:1.000000
plant x1.020 -> 1.020000 PASS   0-2:1.020000  4-8:1.020000  16-32:1.000000
plant x1.005 -> 1.005000 PASS   0-2:1.005000  4-8:1.005000  16-32:1.000000
plant x1.001 -> 1.001000 PASS   0-2:1.001000  4-8:1.001000  16-32:1.000000
```

**Detection floor: 0.001 (0.1%), recovered exactly**, and correctly localised to
the planted 8 px width -- the 16-32 band stays at unity, so the detector does
not smear an edge error inward. The null reads **exactly** 1.000000, bounding
the tool's own mapping and band-bookkeeping error below 1e-6.

The one thing the null does not exercise is the bilinear resample at
`k = 0.9236`. That is bounded separately by the **interior** band of the real
measurement, which runs through the identical resampling and reads
**1.000982** -- so resampling bias is at most ~0.1%, two orders below the
effect.

### 10.2 The effect is entirely in the crop render, because crop is verbatim

On the deep stack, `crop` is a bit-exact window of the no-fit render:

```
=== bee: is crop a verbatim window of the no-fit render? origin (135,90)
  exact-equal samples : 21073032 / 21073032  (100.0000 %)
  max |diff|          : 0 DN          VERDICT : BIT-IDENTICAL
```

So `crop` invents nothing, and whatever the 14% is, it is already present in a
plain unity-scale render. The question is which of the two is *wrong*.

### 10.3 The lever: the ring width is the pyramid support

`reduce` in `pyramid.rs` replicates borders and `DEFAULT_BANDS = 7`. If the
merge is transporting a boundary effect inward, the reach must scale as
`2^bands`. `--pyramid-bands` tests that directly. 109MSDCF, crop vs scale:

```
bands=7   0-2:1.027974  16-32:1.025726  64-128:1.019232  128+:1.001462
bands=4   0-2:1.028133  16-32:1.010154  32-64:1.000048  64-128:0.999956
bands=2   0-2:1.024745  4-8:1.001024   8-16:0.999997   16-32:0.999980
```

| bands | support `2^b` | ratio returns to 1.000 at |
| ---: | ---: | --- |
| 2 | 4 px | **8 px** |
| 4 | 16 px | **32 px** |
| 7 | 128 px | **128+ px** |

**The reach is the pyramid support, to within a factor of one band.** The peak
amplitude at the very edge barely moves (1.0280 / 1.0281 / 1.0247); what the
depth controls is how far inward it reaches. That is transport, not source.

### 10.4 Which render is wrong: absolute levels, same rings

`edgeprofile.py` walks in from the plane edge in absolute DN. 109MSDCF:

```
ring px      no-fit b7    no-fit b2    b7 excess    scale b7
  24-32        6792.58      6631.14      +2.43%      6604.56
  48-64        6780.15      6619.64      +2.42%      6622.53
  96-128       6731.97      6605.50      +1.91%      6595.29
 160-192       6668.87      6595.84      +1.11%      6583.40
 256-384       6545.21      6543.27      +0.03%      6527.95
    512+       5595.04      5595.62      -0.01%      5573.95
```

**Two independent boundary-free references agree and the 7-band no-fit render
is the outlier.** `scale` (no uncovered region at all, so no step) and the
2-band no-fit render (step present but support only 4 px) agree to within 0.4%
at every ring; the 7-band no-fit render sits up to **+2.4%** above both. The
deep interior of all three agrees to 0.01-0.03%, so band count is not shifting
levels globally -- the excess is boundary-localised.

The same on the deep stack, where it is five times larger:

```
ring px    bee no-fit b7   bee no-fit b2   b7 excess
  64-96        13079.73        12455.98      +5.01%
  96-128       14768.92        13514.46      +9.28%
 128-160       15082.71        13846.57      +8.93%
 192-256       14160.00        13597.12      +4.14%
 256-384       12902.04        12762.58      +1.09%
    512+        7519.68         7516.14      +0.05%
```

**The crop rectangle on bee starts at 135 px, so the overshoot peaks INSIDE the
delivered image.**

### 10.5 The mechanism

`warp_frame_in_place` documents that **uncovered destination pixels are set to
the black level**. In `crop` / no-fit mode the plane therefore carries a hard
step from image down to black all the way round, at the coverage boundary. The
pyramid merge **elects per band coefficient**, so analysis-synthesis is not the
identity, and a step passed through a non-invertible multi-scale reconstruction
rings -- overshooting **bright on the bright side**. The overshoot reaches
inward by the coarsest band's support, `~2^bands` px.

`scale` mode composes `S_k` precisely so that every frame covers the whole
plane. There is no uncovered region, no black fill, no step, and therefore no
ringing. Measured: `scale` shows `black% = 0.00%` in every ring and a flat
profile from ring 0 (6611.55) through ring 96 (6614.72).

Every observation follows:

| observation | explained by |
| --- | --- |
| reach scales as `2^bands` (4/16/128 px measured) | pyramid transport |
| `scale` unaffected, stable across band counts | no step to ring |
| single frame flat to **1.00003** (§6c) | N=1 election is invertible, so no ringing |
| sign is *bright*, not dark | overshoot on the bright side of a step, not black bleeding in |
| bigger on bee (9.3%) than 109 (2.4%) | on 109 the rect sits only 23 px in, so crop keeps most of the ringing too and the two renders differ less |

The last row is why §6c's ratio looked like "scale is depressed": on 109 both
renders carry some of the artifact. The band-depth lever separates them.

**ORCH's candidate list, resolved:**

- *coverage count falling off near the boundary* -- **it is the source of the
  step**, but not the transport: the excess persists at rings where `black%` is
  0.00% and, decisively, it changes with pyramid depth while the coverage
  geometry does not.
- *gather edge-clamp/padding differing between paths* -- **ruled out**.
  `gather_checked` writes NaN and never clamps, and it is the same code on both
  paths; the effect vanishes at `bands=2` with a byte-identical gather.
- *normalisation over a region including/excluding the border* -- **ruled out**
  by the same lever: a normalisation difference would not scale with `2^bands`.
- *placement rectangle partly outside some frames' valid area* -- **ruled out**
  by §10.2: crop is a bit-exact window, so its content is not placement-dependent.

### 10.6 What follows, and why I did not "fix" it

**No code change this turn, deliberately.** The mechanism admits two remedies
and both are product decisions with costs I can price but should not pick:

1. **Inset the crop rectangle past the ringing.** Principled -- it is what the
   rectangle already does for the black -- but the measurements say it needs
   ~256 px on 109 and ~384-512 px on bee to get under 0.1%. bee would go
   `3246 x 2164` to about `2478 x 1396`: **3.46 MP from an 8.24 MP sensor, -58%
   of pixels.** That is not a trade worth making silently.
2. **Remove the step** by filling uncovered pixels continuously instead of with
   the black level. This is the correct fix, but the black fill is a
   *deliberate, documented* decision in `warp_frame_in_place` ("clamping is not
   an option", with `align.rs` cited), and changing it would also move the
   `STREHL_COVER=0` measurement control other lanes may be using. Not mine to
   take unilaterally.

**It is byte-safe to fix.** `scale` renders contain **zero** uncovered pixels
(`black% = 0.00%` in every ring, measured), so any change to the uncovered-fill
policy cannot touch the shipping default or the byte-freezes.

**The finding that matters for the product:** `crop` mode delivers a border ring
contaminated by up to **+9%** on a 299-frame stack, and `scale` mode does not.
The upsample `scale` pays for is also, incidentally, what protects it from this
ringing. That is a second, independent reason -- unrelated to print size -- for
`--cover crop` to remain opt-in.

---

## 11. DEFECT B -- the R/B null failure was the CA correction

**Verdict: not a defect. The null passes completely. §3.1 is superseded.**

### 11.1 The chroma-phase hypothesis, tested and refuted

ORCH's structural hint was a chroma phase error: in a Bayer quad the two greens
are diagonal so their mean is co-sited with the quad centre, while R and B sit
at opposite corners, so code that treats all three as co-sited would be right
for G and wrong by a quarter pixel for R and B in opposite directions. That is
a sharp prediction, and `subshift.py` solves for translation directly rather
than on an integer grid:

```
window 3506x2337 at (5,4)
 ch      dx px      dy px   rms before   rms after   explained
  R    -0.0109    -0.0046      184.246     184.239       0.00%
  G    -0.0000     0.0000        0.000       0.000         n/a
  B     0.0093     0.0005       43.532      43.522       0.02%
```

The signs **are** opposite as predicted, but the magnitudes are ~0.01 px rather
than 0.25, and the translation model explains **0.00%** of the residual.
**REFUTED**: the R/B difference is not a displacement of the sampling grid.

### 11.2 What it actually is

`warp_frame_in_place_plane` composes a **lateral chromatic aberration profile**
per CFA phase, resolved through a gear guard on body and lens id, and its own
comment records that it recently became default-on. `STREHL_ALIGN=0` never
calls the warp, so **the align-off baseline silently has no CA correction**.
I was comparing a CA-corrected render against an uncorrected one.

Holding it constant:

```
$ STREHL_FIX_CA=off strehl stack one --cover crop
lateral CA      : off (operator asked for "off")

=== CA-OFF  (3506x2337 vs base window at (5,4))
 ch   bit-exact    max|d|    mean|d|     lap base   lap render     ratio
  R   100.0000%         0     0.0000     548661.1     548661.1   1.00000
  G   100.0000%         0     0.0000     101490.8     101490.8   1.00000
  B   100.0000%         0     0.0000     240923.5     240923.5   1.00000
```

**All three channels bit-exact, 0 DN, laplacian ratio exactly 1.00000.** An
exactly-identity placement at unity scale IS a bit-perfect pass-through. The
pixel-exactness null passes without qualification.

### 11.3 Colour, measured -- not only bits

Required by ORCH, because a chroma error would also be a colour defect.
`cafit.py` fits the displacement between the CA-off and CA-on renders (same
scene content, so a gradient estimate measures the applied transform itself):

```
3506x2337, centre (1753.0,1168.5), 128px blocks
 ch   alpha (px/px)   corner px   blocks   r (radial fit)
  R       3.796e-04      0.7998      486          -0.2894
  G       0.000e+00      0.0000      486              nan
  B      -1.638e-04     -0.3451      486           0.9769
```

**Green is held exactly fixed (alpha = 0.000e+00), and R and B move in OPPOSITE
radial directions** -- +0.80 px outward and -0.35 px inward at the corner. That
is the definitive signature of a lateral CA correction and rules out a general
resampling error, which would move all three channels the same way.

**Caveat, stated rather than buried:** the linear-radial model fits blue well
(r^2 = 0.977) but red badly (r^2 = -0.29). Red is the noisiest plane -- its base
laplacian energy is 5.4x green's -- and the estimator is also being asked to fit
a pure translation to a pair that differs by a resample, which violates its
model. The **sign and magnitude** for red are trustworthy; the **radial form**
for red is **NOT VERIFIED** by this measurement.

### 11.4 What §3.3's noise finding now means

§3.3 measured that the energy removed from R and B is flat-field dominated
(R: 0.440 flat against 0.534 textured) and concluded it was noise suppression
rather than detail loss. That conclusion **stands and is now explained**: the
CA correction resamples R and B at a sub-pixel offset, which attenuates the
noise and aliasing carried on the critically-sampled chroma subgrids. It is the
ordinary cost of a geometric correction, paid on the two channels being
corrected, and it buys colour registration.

### 11.5 The instrument defect worth propagating

**`STREHL_ALIGN=0` is not a clean control.** It disables the warp, and the warp
is the only site that applies lateral CA -- so an A/B that uses `STREHL_ALIGN=0`
as its baseline is silently toggling a colour correction as well as alignment.
This lane published `R 4.8% / B 12.5% bit-exact` as a null failure on exactly
that confound. Any lane using an align-off baseline for a chroma or colour claim
should pin `STREHL_FIX_CA` explicitly in both arms.

---

## 12. Exposure guard on the diagnostic renders

```
$ python experiments\ORCH-drift-check\clipcheck.py D:\strehl-out\BUILD-CROP
0/17 BLOWN (>25% clipped), 0 high, 17 ok
```

All 17 renders cited in §10 and §11 pass, including every `--pyramid-bands` arm
and both CA arms.
