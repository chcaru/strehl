# M97 — the warped merge, independently verified, and a null with a mechanism

**Milestone:** M97
**Question as dispatched:** wire the M86 warp sidecar into `strehl stack`, so the
merge gathers every frame through its registration before merging it.
**Question as answered:** the wiring landed while I was building it. So: *is the
shipped registration correct, and does it measurably improve the photograph?*

**Headline (MEASURED):** the wiring is correct — right sign, right per-CFA-plane
handling, and it survives an identity placebo, a wrong-stack control and a
whole-frame NaN sweep with a recovered plant. **But the solve behind it applies
only 54.3% of the drift that is actually there**, leaving ~150 plane px of
residual misregistration where M86's own usability threshold is 4.0 px. That is
why the photograph does not improve, and it costs **2.58x** to not improve it.
The estimator's gain, not the wiring, is the bug.

---

## 1. The collision, and why this milestone changed shape

My dispatch said `merge.rs` and `merge_cmd.rs` "contain zero references to
`warpmap`" and that closing that gap was the night's largest quality lever.

**That was true when written and false ~20 minutes later.** While my first
`cargo build` was running, sibling milestone **M86c** committed `885e9f7`
("wire alignment into strehl stack; fix the black-fill defect", 17 files,
1827 insertions) — my assignment, done, and done well. Their §15 in
`docs/research/M86-alignment.md` is the record.

I did not discover this cleanly. I first found a large **uncommitted** diff in
the working tree with an mtime two minutes before my session started, could not
attribute it, and — correctly — chose to preserve and verify rather than
rewrite. I backed all four affected files up to `$env:TEMP\m97-backup-20260824-031429`
first. A second `git log` a few minutes later showed the commit and resolved the
provenance. **The rule that saved this was "never `git checkout --`"**; the
instinct to "clean up" an unexplained diff would have destroyed a sibling's work.

Per AGENTS rule 12 (*the author never verifies their own work*), the useful thing
left for M97 was not to re-ship the wiring. It was to be its **independent
verifier**, and to run the experiment M86c named as their own #1 open follow-up
and did not run: a **geometry metric with ground truth** that can actually see
misregistration. M86c's sharpness metric (Tenengrad, 0.9859) could not, and they
said so.

**M97 therefore owns: the verification, the ruler experiment, the mechanism, the
cost, and two defects in the shipped code.** M86c owns the wiring.

---

## 2. What I pre-registered, before computing any metric

`experiments/M97-warped-merge/PREREG.md`, written before the first number
existed. Abbreviated:

| # | Bar | Named failing input |
|---|---|---|
| P1 | The metric must be **responsive**: planted misregistration must move it by >= 3x the aligned-vs-null difference | if it does not move, no reading of it means anything |
| P2 | Registration improves ruler baseline straightness | — |
| P3 | No NaN and no black rim, **whole frame**, not a crop | — |
| P4 | An identity sidecar is a measured no-op | — |
| P5 | A wrong-stack sidecar is refused, not silently applied | bee-3's map fed to the ruler bracket |
| P6 | A refused frame is **dropped**, and `n_eff` reflects it | a sidecar with planted refusals |
| P7 | Timing, before and after, same machine, same stack | — |

I also pre-registered the risk that **a flat subject makes the test inert**, so
that a null could not be quietly reinterpreted afterwards as success.

---

## 3. The instrument, and the three defects I caught in it

**Subject:** `D:\personal\macro\flat-on-ruler-cpl`, 79 frames. A steel rule.
`highly-angled-ruler-mm-cpl` is in `TILTED_SUBJECTS` and is refused by the merge,
so the flat rule is the only ruler available — exactly the stack M86c named.

**Ground truth:** the engraved baseline of a machined rule is *straight*. Any
bend in the merged render is misregistration, not subject. The metric `S` is the
RMS deviation of the tracked baseline from its own least-squares line, in output
pixels; `S_block` is the block-median form, which suppresses per-row tracking
noise.

**Solve (MEASURED):** drift **111.05 plane px**, held-out error **11.08 px**,
cycle floor **0.799 px**, **79/79 placed**, solve 7.2 s. Written with
`strehl align --out` to `C:\`, never into the capture directory.

Three instrument defects, each caught **before** I trusted a number:

1. **`np.convolve(..., "same")` zero-pads.** The pad is smaller than any real
   signal, so `argmin` reliably returned the *search-window edge*. The first
   "baseline" I found was 1900 px from the real one. Fixed with
   `scipy.ndimage.uniform_filter1d(..., mode="nearest")`.
2. **Max-gradient edge tracking latched onto the wrong feature.** Brushed steel
   has thin, high-contrast machining scratches; the engraving is a soft, pitted
   trough. Gradient prefers the scratch. It reported `S = 62.9 px` and I nearly
   believed it. Fixed by requiring a **sustained** dark run (24 rows) — duration
   is what separates an engraving from a scratch. **Verified by overlaying the
   tracked edge on the image and looking at it**, not by the number improving.
3. **Pillow silently truncates 16-bit RGB TIFF to 8-bit.** `Image.open(...)`
   reports `mode='RGB'`, `max=255`; `tifffile.imread` on the same file gives
   `uint16`, `max=65535`. No warning, no error, no exception. Every measurement
   was re-run through `tifffile`. Conclusions were unchanged (S moved < 0.05 px)
   but the numbers are now on true data.

A fourth, in my own timing harness, found while writing this up:
**PowerShell `[int](3/2)` is `2`** — `[int]` rounds half to *even* — so
`$v[[int]($v.Count/2)]` on a sorted 3-element array returns the **max** and calls
it the median. It printed `29.51 s` for a set whose median is `21.67 s`. Fixed
with `[math]::Floor`; the medians below are taken from the raw rows.

---

## 4. Arms

All five are the same bracket, same gate, same everything but registration.

| arm | what it is |
|---|---|
| `UNALIGNED` | `STREHL_ALIGN=0`. No registration, no resample. |
| `ALIGNED` | the real solved sidecar. |
| `ZOOMNULL` | `STREHL_ALIGN=zoom`. **The matched null.** Same cover-zoom `k`, same Catmull-Rom resample, relative registration discarded. This is the arm `ALIGNED` must beat; `UNALIGNED` is not a fair comparison because it pays no resample. |
| `JITTER6` | the solved sidecar plus planted pseudorandom translation. **The plant that proves the metric is alive.** |
| `IDENTITY` | every placement replaced with the identity. The placebo. |

Plants are built by `src/sidecar_tool.py` with a self-contained LCG, so they are
exactly reproducible. Perturbing only the sidecar's `b` term is a translation
**regardless of which transform convention is in force**, so the plant cannot be
invalidated by my having misread the convention.

---

## 5. Results against the pre-registered bar

### P1 — responsiveness: **PASS** (MEASURED)

| arm | `S_raw` | `S_block` |
|---|---|---|
| UNALIGNED | 15.408 | 9.548 |
| ALIGNED | 15.414 | 9.832 |
| ZOOMNULL | 15.124 | 9.794 |
| **JITTER6** | 19.908 | **14.084** |
| IDENTITY | 15.305 | 10.066 |

Planted misregistration moves `S_block` by **+4.252 px**. `ALIGNED` vs its
matched null moves it by **+0.038 px**. The bar was 3x; the margin is **~110x**.
**The metric is not a disconnected probe.** This is the plant that discipline 598
demands, on the same wiring, and it is the reason the next line is admissible.

### P2 — does registration straighten the ruler: **NULL** (MEASURED)

`ALIGNED` 9.832 vs `ZOOMNULL` 9.794. Registration is **0.038 px worse**, on an
instrument that sees 4.25 px of planted error. There is no straightness win.

I pre-registered "a flat subject may make this inert" as the escape hatch, and
**it does not apply**: `ALIGNED` and `ZOOMNULL` differ in **89.8%** of pixels
(mean |d| 7.37/255). The two renders are emphatically not the same image. They
are merely the same *straightness*.

### P3 — no NaN, no black rim, whole frame: **PASS** (MEASURED)

Exact-zero pixel fraction over the entire frame, and separately over the outer
2% annulus where a gather rim would live. **True 16-bit**, read with `tifffile`:

| arm | whole frame | outer annulus |
|---|---|---|
| UNALIGNED | 0.00000% | 0.00000% |
| ALIGNED | 0.00000% | 0.00000% |
| ZOOMNULL | 0.00000% | 0.00000% |
| IDENTITY | 0.00000% | 0.00000% |
| JITTER6 | 0.00000% | 0.00000% |
| bee-3 BEFORE / AFTER / NULL | 0.00000% | 0.00000% |

Zero black pixels in 33 MP, in every arm. No NaN reaches the output and there is
no black rim.

**This null needed a plant, and my first version of it did not have one.** At
8 bits, `JITTER6` read 0.00068% and I recorded that as the control proving the
sweep could see a rim. It was not: at 16 bits that arm reads 0.00000% like every
other, because the 8-bit reader truncates 1..255 to 0 and manufactures black that
is not there. So the sweep's null was, briefly, exactly the disconnected probe
discipline 598 warns about — **five arms all reading 0.000 and nothing
demonstrating the instrument was attached.**

`src/blackplant.py` fixes that by planting known black into a real render and
running the same reader over it:

```
planted   : 18 black px (9 of them in the annulus)
recovered : 18 black px (9 in the annulus)
fractions : whole 0.0000546%  outer 0.0004151%
PLANT RECOVERED -- the sweep is live
```

18 black pixels in 33 MP are found exactly. **The zeros above are a measured
null, not a dead probe.**

**DERIVED**, from reading the source: the null is structural rather than lucky —
the gather writes `black_dn` rather than `f32::NAN` for uncovered destinations,
so NaN cannot enter the accumulators by this path at all, and M86c's
`fit_to_cover` then shrinks the field of view by `k <= 1` so every frame covers
every output pixel.

### P4 — identity placebo: **PASS** (MEASURED)

With an identity sidecar, `fit_to_cover` reports **k = 0.9974** — it correctly
detects that identity placements need essentially no crop. The real maps report
k = 0.9315 (bee-3), 0.9708 (ruler). The identity render is not bit-identical to
`UNALIGNED`, and should not be: it still pays one full Catmull-Rom resample at
k = 0.9974. Its straightness (10.066) sits inside the scatter of the other
non-plant arms.

### P5 — wrong-stack sidecar: **PASS** (MEASURED)

Feeding `bee-3-cpl`'s sidecar to the ruler bracket:

```
Error: the sidecar named by STREHL_WARPMAP (D:\personal\macro\bee-3-cpl\warpmap.txt)
       was not fitted on this bracket
Caused by:
    this warp map was fitted on stack "bee-3-cpl" (digest 8d023c0fe355d109, 299 frames)
    but was applied to "flat-on-ruler-cpl" (digest d59b4ed1a1042f02, 79 frames)
```

`rc=1`. Both stacks named, both digests, both frame counts. This is a good error.

### P6 — refused frames: **FAIL against the pre-registered bar** (MEASURED)

The bar said *"a refused frame is dropped, and `n_eff` reflects that it was
dropped."* The shipped behaviour is to **abort the entire render**:

```
alignment      : ON (sidecar-override), reference frame 39, 71 placed / 8 refused
Error: frame 0 was refused by the alignment solve: planted-refusal-M97
```

`rc=1`. The accounting line is correct — it knows 8 were refused — and then the
render produces nothing.

I want to be careful about what this is. M86c's reasoning is sound as far as it
goes: **a refused frame is not a frame with an identity warp**, and laundering
one into the merge would be a silent lie. But *dropping* is not laundering
either, and it is the third option. As shipped, a single refusal anywhere in a
299-frame bracket costs the user the whole photograph, with no recourse but
`STREHL_ALIGN=0`, which discards registration entirely. See §9, defect 2.

### P7 — cost: **2.58x** (MEASURED)

Alternating protocol per AGENTS rule 16 (`OFF ON ON OFF OFF ON`), so a warming
cache or a busy machine cannot masquerade as the cost of the feature. bee-3-cpl,
299 frames, sidecar pre-solved, so this is pure gather cost with no solve in it:

| arm | runs | median | min | max |
|---|---|---|---|---|
| alignment OFF | 3 | **21.67 s** | 20.39 | 29.51 |
| alignment ON | 3 | **55.85 s** | 51.90 | 63.08 |

**+34.2 s, a 2.58x end-to-end regression.** My earlier single-shot pair read
22.19 / 67.92 s (3.06x); the alternating medians are the number to trust and the
single-shot pair is why rule 16 exists. Note the OFF median (21.67 s)
**corroborates the README's 23.1 s** on a machine with several other agents live.

This is a real cost against a genuine SOTA speed claim, and it currently buys no
measured image improvement. That is the trade as it stands tonight.

---

## 6. The detail metric, condemned by its own control

I also built a tile-wise band-limited detail metric, intending it as the
sharpness half of the verdict. **Its responsiveness control disqualifies it, and
this is the most important methodological result in the milestone.**

Ruler, `ALIGNED` as reference:

| test arm | overall | flattest 20% | top 10% |
|---|---|---|---|
| `JITTER6` (**known worse**) | **1.0557** | 1.1033 | 1.0337 |
| `ZOOMNULL` | 0.9956 | 0.9996 | 0.9811 |

**Planted misregistration *raises* the detail metric by 5.6%.** Higher reads as
better; the arm that is definitionally worse scores highest. Misregistration
manufactures band-limited energy — seams, doubled edges, admitted noise — that
the metric cannot tell from detail.

Therefore my bee-3 reading of `ALIGNED/ZOOMNULL = 0.9913` (and its 0.8487 in the
flattest tiles) **means nothing about sharpness** and I withdraw the
interpretation I was building on it. My pre-registration required exactly this
outcome — *"if it raises this metric, the metric is fooled in this regime and no
reading of it means anything"* — and it is the only reason I caught it rather
than publishing a confounded win.

The signs are also **inconsistent between subjects** (bee: worse arm reads
higher; ruler `ZOOMNULL`: worse arm reads lower), which is independent evidence
of confounding rather than signal.

This **independently corroborates M86c §15.4** with a different metric and a
different subject: gradient-energy sharpness metrics cannot adjudicate
registration in this regime. Two milestones, two instruments, same conclusion.

---

## 7. The mechanism: the registration is correct, and it under-corrects by half

**This section replaces the mechanism I proposed before the orchestrator's
independent drift measurement arrived. My earlier hypothesis — that the merge
was already robust to smooth breathing drift — is superseded. The real
explanation is simpler and worse.**

### 7.1 The sign is correct as shipped (MEASURED)

The orchestrator measured, with no strehl code, that the **subject shrinks**
through `bee-3-cpl`: a feature at radius `r` in frame 0 sits at `0.85715·r` in
frame 298. M86 §4.2 says the opposite — *"Frame 0 is roughly 10–12% smaller than
frame 298"* — and a flipped sign would double the drift silently.

I resolved it by gathering, not by reading, in `src/signtest.py`: a green
sub-lattice extractor, a `map_coordinates` gather and an NCC scale ladder, all
written here rather than imported, so that a shared bug cannot make two
measurements agree with each other and with nothing else.

| arm | scale | corner, plane px | NCC |
|---|---|---|---|
| SELF (frame 0 vs itself) | 0.99997 | 0.1 | 1.0000 |
| RAW (frame 0 vs 298) | **0.85714** | 301.6 | 0.9877 |
| AS-IS (both gathered through the sidecar) | **0.92887** | 150.2 | 0.9872 |
| **INVERTED** (the plant) | **0.78811** | 447.3 | 0.9874 |

- **RAW = 0.85714 against the orchestrator's 0.85715.** Independent
  implementation, agreement to five decimal places.
- **AS-IS moves toward 1.0; INVERTED moves away, to 1.48x the raw drift.** The
  test can see a sign error, and the shipped sign is not one.

**The sidecar settles it too, without any gather.** Reading `bee-3-cpl`'s map
directly (`src/sidecar_scale.py`): reference frame 149 carries an exact
identity, and `|a|` falls **monotonically** 1.050368 → 0.968875 across the
bracket. The subject shrinks. **M86's sidecar contradicts M86's prose.** This is
a documentation error in §4.2, not a code error — see Notes.

### 7.2 But it applies only half the drift that is there (MEASURED)

The same test measures the residual, and this is the finding that matters:

```
RAW drift              301.6 plane px  (true scale span 0.85714)
sidecar's scale span   0.92241  -- it applies 54.3% of the span that is there
predicted residual     0.92924 from the sidecar alone
MEASURED residual      0.92887  (150.2 plane px, 50.2% of the drift removed)
```

Two independent routes agree. Reading the sidecar's own numbers predicts a
residual of 0.92924; gathering real frames through it measures **0.92887**.
Agreement to 4e-4. **The gather does exactly what the sidecar tells it to. The
sidecar is the thing that is short.**

**After alignment, frames 0 and 298 are still misregistered by ~150 plane px
(~300 sensor px) at the corner.** M86 quotes `E*` = 11.56 px held-out and the
sidecar's own header records 13.5776 px. The end-to-end residual is **11–13x
that**.

The arithmetic is not contradictory, and it is worth being precise about why.
**`E*` is a held-out *pairwise edge* error, not an end-to-end absolute one.** A
solve whose every pairwise estimate is attenuated by a common factor is almost
perfectly self-consistent — every edge agrees with every other — while the
absolute scale it accumulates is badly short. A pairwise residual cannot see a
global gain error. M86 anticipated the *direction* of this in its own P8
(*"unit-weighted global solve underestimates drift by 12–16%"*); the measured
shortfall is **46%**, three to four times P8's estimate.

**This explains every null in this report.** Registration is not failing to help
because misregistration does not matter. It is failing to help because after
registration the frames are *still grossly misregistered* — 150 plane px against
M86's own usability threshold `T_usable` of 4.0 px. The wiring is correct; the
solve's gain is not.

### 7.3 Controls for the instrument itself (MEASURED)

| control | result |
|---|---|
| plant 0.940 | 0.93841 (err −0.00159) |
| plant 0.860 | 0.85858 (err −0.00142) |
| gather round-trip, `a` = 0.92 | residual 0.99655 (**7.3 plane px**) |
| gather round-trip, `a` = 1.08 | residual 0.94408 (118.1 plane px) — **FAIL** |

The `a` = 0.92 round-trip sits at the operating point — the real placements span
1.000 → 0.922 on this sidecar — and closes to **7.3 plane px**. That is this
instrument's noise floor, and the 150.2 px residual is **20x** above it.

The `a` = 1.08 arm fails, and I report the failure rather than dropping it.
Magnifying by 1.08 and then de-magnifying asks for border data that the first
step destroyed; it is an information artefact of my synthetic plant, not of the
gather. **No arm reported above uses that branch** — every placement on this
sidecar has `|a| <= 1`. It is a stated limit on how far this instrument can be
pushed.

I also got the round-trip's **direction** wrong on the first attempt, feeding
`1/p` where the placement is `p`. It returned 0.85399 where `p/(1/p)` predicts
0.8573 — **the control faithfully reported my error rather than the gather's**,
which is the entire reason for having it.

### 7.4 `n_eff`, for the record (MEASURED)

| arm | mean `n_eff` | `n_eff=1` % |
|---|---|---|
| UNALIGNED | 23.043 | 46.57% |
| **ALIGNED** | **19.182** | 51.15% |
| ZOOMNULL (matched null) | 18.622 | 50.67% |

Against the matched null, registration buys **+3.0% `n_eff`** — real, in the
right direction, and far too small to see. Against `UNALIGNED` it is a 17%
*loss*, which is the resample's doing rather than misregistration's. §7.2 is why
the gain is only 3%: half the drift is still there.

---

## 8. The owner deliverable, and an error of mine

Written to `C:\dev\strehl-out\M97-before-after\`:
`bee-3-BEFORE-unaligned.tif`, `bee-3-AFTER-aligned.tif`,
`bee-3-NULL-zoomonly.tif`, plus previews, thorax and hair crops, side-by-sides
and absolute-difference maps.

**I opened them.** Honestly, at native resolution:

- The two renders are **visibly different images** — the aligned frame is
  slightly tighter in field of view (k = 0.9315, so ~7% cropped and resampled
  back up) and 89.8% of pixels differ.
- They are **not visibly different in sharpness**. On the thorax hairs, where a
  232 px registration error should be devastating, I cannot pick the aligned
  render out of a side-by-side.
- Neither has a black rim, a NaN hole, or a colour artefact. **Whatever else is
  true, the CFA-plane warping is not damaging the photograph.**

**My own error, recorded because it is the point.** My first look was at the
aligned crop alone and I wrote down that it was clearly sharper. It is not. When
I built the *side-by-side* the impression evaporated. I had seen a sharp
photograph and credited the treatment. **Expectation, not evidence** — and the
only reason it did not reach this report is that I stopped comparing crops from
memory and put them next to each other. The ROI check at six spatial octaves
across the thorax reads **0.970–0.997**: null at every scale.

**So the answer to the owner's "those stacks don't look too good yet" is: this
was not the lever.** The stacks do not look bad because they are unregistered.
That is a negative result and it is worth having, because it redirects the next
milestone away from a dead end that everyone — including my own dispatch — was
confident about.

---

## 9. Defects in the shipped code

### Defect 1 — rendering a bracket **writes into the read-only corpus**, non-atomically (MEASURED)

`align_cmd::sidecar_path` is `dir.join("warpmap.txt")`, and `load_or_solve`
caches a fresh solve there on a miss. `D:\personal\macro\` is the owner's
capture corpus and is read-only by rule.

**This is worse than I first filed it, and it is spreading during the session.**
At 03:15 there were two polluting files. At 04:55 there are **eight**, six of
them created between 04:34 and 04:53 by other milestones' renders:

```
D:\personal\macro\bee-2-cpl\warpmap.txt              03:12:36
D:\personal\macro\lavendar-cpl\warpmap.txt           04:34:44
D:\personal\macro\flowers-cpl\warpmap.txt            04:35:56
D:\personal\macro\leaf-2-cpl\warpmap.txt             04:36:51
D:\personal\macro\flower-bud-alone-cpl\warpmap.txt   04:37:48
D:\personal\macro\tweezers-cpl\warpmap.txt           04:38:35
D:\personal\macro\coffee-bean\warpmap.txt            04:39:05
D:\personal\macro\bee-3-cpl\warpmap.txt              04:53:20
```

**And the write is not atomic.** At 04:53:20, while I was reading
`bee-3-cpl/warpmap.txt`, another agent's render rewrote it. My reader saw a
**torn file**: `reference 30`, no record for frame 298. Re-reading moments later
gave the whole file back (`reference 149`, 299 records). **MEASURED**, by
accident, and it is the more serious half of this defect: with several agents
live, a concurrent reader — including `strehl stack` itself — can load a
half-written sidecar. Whether `WarpMap::load` would reject such a file or
silently render a partial registration is **not verified**; my Python reader
accepted it and simply lacked a key.

The caching itself is right — a 7 s solve should not be repeated. The **location**
and the **non-atomicity** are the defects. `align_cmd.rs` is not mine; verbatim
patch in §11, which moves the cache out of the corpus *and* writes via a
temporary file plus a rename.

### Defect 2 — one refused frame destroys the whole render (MEASURED, §5/P6)

Recommendation: **drop refused frames** rather than aborting, and report the
drop in the alignment line and in `n_eff`. Abort only if the placed count falls
below a floor. I deliberately have **not** implemented this: it touches the
fold/`n_eff` path in `merge.rs`, which M87 and M93 are both live in tonight, and
a 05:00 refactor of a contended file is how a good night becomes a bad merge.

### Defect 3 — the solve applies half the drift it measures (MEASURED, §7.2)

The most consequential of the three, and the reason the feature does not pay.
Not mine to fix — it is M86's estimator, and the brief was explicit that I
should not chase it there. Routed in Notes.

---

## 9a. Coverage: what `stack` actually does with the uncovered region

The orchestrator's estimate was that gathering frame 298 at scale 0.857 needs
samples from outside its own bounds over `1 − 0.857² ≈ 26%` of the destination.
**That is the right calculation for the drift that is there, but not for the
drift the sidecar applies.** Because the solve applies only 54.3% of the span
(§7.2), the realised deficit is about half that.

**MEASURED, and the question is already settled in the shipped code:**
`fit_to_cover` reports `k = 0.9315` on bee-3-cpl. So `strehl stack` **crops to
the fully-covered region** — it shrinks the field of view until *every* frame
covers *every* output pixel — which is `1 − 0.9315² = 13.2%` of the area, then
**upsamples back to the original output dimensions**. Measured `k` elsewhere:
0.9044 (bee-2), 0.9708 (ruler), 0.9974 (identity sidecar).

The consequences, stated explicitly because the orchestrator asked which choice
was made and why:

- **There is no soft, low-`n_eff` margin, and no black rim.** §5/P3 measures
  0.00000% black over the whole frame in all eight arms, with an 18-pixel plant
  recovered, so this is a measured null and not a dead probe. Nothing is clamped
  and no NaN reaches the output.
- **`n_eff` does not have to be faked up at the edges**, because after the crop
  there are no partially-covered edges left.
- **The cost is a full-frame resample.** Output dimensions are preserved, so the
  delivered image is **upsampled by `1/k` = 1.0735** — a 7.35% enlargement of
  every pixel in the photograph. **DERIVED:** that is a real sharpness cost paid
  by every aligned render, and it acts against any registration gain. With the
  gain reduced to ~3% `n_eff` by §7.2, it is entirely plausible that the
  upsample cancels what alignment buys. I did not isolate the two, and doing so
  is a named follow-up.
- I did not choose this policy — M86c did — but I verified it holds and I think
  it is the right default. The alternative, emitting a smaller image, silently
  changes output dimensions between aligned and unaligned runs.

---

## 10. Not measured

- **Whether `WarpMap::load` rejects a torn sidecar.** I observed a half-written
  file being read (§9 defect 1) but did not test what `strehl` itself does with
  one. This should be checked before the next long run.
- **Isolating the `1/k` upsample from the registration gain** (§9a). Both act on
  the same render and I did not separate them.
- **Graduation spacing** as a second geometry metric: the tick-detection
  instrument returned unstable counts across arms (14/14/16/18/14), so it is
  measuring its own thresholding. **Reported as instrument failure, not as a
  result.** No number from it appears in this report.
- **Frame-level refusal on real data.** It has never fired on a real bracket;
  every refusal here was planted. M86's 0.0% / 13.2% / 16.2% figures are
  *edge*-level, not frame-level.
- **The `a` > 1 branch of my gather instrument** (§7.3), which fails a
  round-trip for reasons I attribute to border information loss but did not
  prove.
- **Whether a corrected-gain solve would actually improve the image.** §7.2 says
  the residual is 150 px; it does not say that fixing it delivers a visible win.
  That is the experiment the next milestone should run, and it is now a sharp,
  well-posed one.
- **Whether registration helps a genuinely non-smooth bracket** — handheld, or
  wind. Every stack available is a rail sweep.
- P3's numbers were first taken through the 8-bit-truncating reader, which
  **manufactured a control that did not exist** (§5/P3). Every arm has been
  re-swept at true 16 bits and the sweep now carries a real plant.

---

## 11. Verbatim patch for a file I do not own

`crates/strehl-cli/src/align_cmd.rs` — stop caching solves inside the capture
directory. Replace the body of `sidecar_path`:

```rust
/// Where the cached sidecar for `dir` lives.
///
/// This is deliberately *not* `dir.join("warpmap.txt")`. Capture directories are
/// read-only corpus: merely rendering a bracket must not mutate it. M97 measured
/// this firing on the owner's captures -- `bee-2-cpl/warpmap.txt` and
/// `bee-3-cpl/warpmap.txt` were both created by `strehl stack`.
///
/// The cache key is the absolute capture path, so two brackets with the same
/// leaf name cannot collide; `check_stack` remains the real guard.
fn sidecar_path(dir: &Path) -> PathBuf {
    let mut hasher = DefaultHasher::new();
    dunce::canonicalize(dir)
        .unwrap_or_else(|_| dir.to_path_buf())
        .hash(&mut hasher);
    let key = hasher.finish();
    let leaf = dir
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| "stack".to_string());
    cache_root().join(format!("{leaf}-{key:016x}.warpmap.txt"))
}

/// Root of the warp-map cache: `%LOCALAPPDATA%\strehl\warpmaps` on Windows,
/// `$XDG_CACHE_HOME/strehl/warpmaps` elsewhere, falling back to the temp dir.
fn cache_root() -> PathBuf {
    let base = std::env::var_os("LOCALAPPDATA")
        .or_else(|| std::env::var_os("XDG_CACHE_HOME"))
        .map(PathBuf::from)
        .unwrap_or_else(std::env::temp_dir);
    base.join("strehl").join("warpmaps")
}
```

with, at the top of the file:

```rust
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
```

and the write site made atomic and non-fatal — a cache that cannot be written is
not a reason to fail a render, and a cache that is written in place can be read
half-formed by a concurrent process (§9, measured tonight):

```rust
    let write = || -> Result<()> {
        let dir = path.parent().unwrap_or(Path::new("."));
        std::fs::create_dir_all(dir)?;
        // Write-then-rename: a concurrent reader sees either the old file or
        // the new one, never a half-written one. M97 measured a torn read of
        // `bee-3-cpl/warpmap.txt` while a sibling milestone rewrote it.
        let tmp = path.with_extension(format!("tmp{}", std::process::id()));
        map.save(&tmp)?;
        std::fs::rename(&tmp, path)?;
        Ok(())
    };
    if let Err(e) = write() {
        eprintln!("  note          : could not cache the warp map ({e}); it will be re-solved next run");
    }
```

**I have not applied this and have not compiled it** — `align_cmd.rs` is the
orchestrator's file. It needs `dunce` (already a dependency of `strehl-cli`) or
`std::fs::canonicalize` if not. **Until it is applied, the corpus write is
live**, and `STREHL_WARPMAP` is the only way to render without it.

---

## 11a. Does correcting the gain reach the photograph? Rendered, and looked at

§7 established by measurement that the sidecar applies **54.3%** of the drift
that is present, leaving **150.2 plane px** of residual where M86's own
`T_usable` is 4.0 px, and that a scalar gain of **1.9083** applied in the log
takes the residual to **3.3 px (98.9% removed)**. That was measured on my own
gather. This section asks the only question that matters: **does it reach the
image the owner opens?**

The probe needs no Rust change. `experiments/M97-warped-merge/src/regain.py`
rewrites a sidecar with `a' = exp(g·ln a)`, `b' = g·b`, copying every non-record
line verbatim so the `stack-digest` survives and `check_stack` still passes. It
is then fed to the shipped binary through `STREHL_WARPMAP`.

**The control comes first.** A gain of 1.0 must be a byte-level no-op:

- MEASURED: `regain.py <src> <dst> 1.0` reproduces scale span **0.922414**,
  identical to the source sidecar, and `signtest.py` on it returns **0.92887** —
  exactly the as-shipped number from §7. The rewriter is transparent.
- MEASURED: `regain.py <src> <dst> 1.9083` yields a sidecar reading **603.07
  sensor px** of corner drift, against the orchestrator's independently measured
  **603 px**. The rewriter is also correct where it is supposed to act.

Both renders: `--gate 2 --srgb --demosaic`, 299 frames, same machine.

| arm | n_eff | n_eff=1 | boundary | cover k | time |
|---|---:|---:|---:|---:|---:|
| GAIN 1.0 (as shipped) | 17.792 | 49.90% | 1.28% | 0.9974 | 60.15 s |
| GAIN 1.9083 (corrected) | 15.516 | 54.05% | 0.96% | 0.9974 | 57.55 s |

### `cover k = 0.9974` on both is correct, and I nearly reported it as a bug

It reads like the identity value, and §9a measured `k = 0.9315` on bee-3. I held
the result until I could explain it. **DERIVED, and it is a property of the
reference choice, not a defect:** this sidecar's reference is frame 0, so every
placement has `|a| ≤ 1`. The gather is a pull, `dst(z) = src(a·z)`, so `a ≤ 1`
samples *inward* — strictly inside the source bounds — and no destination pixel
is ever uncovered. The `k = 0.9315` figure came from the reference-149 sidecar,
where frames on the far side of the reference have `|a| > 1` and genuinely do
run off the edge.

Two consequences worth stating: **the orchestrator's "coverage is a quarter of
the image" warning is real but is a function of which frame is the reference**,
and choosing an endpoint reference costs nothing in coverage — which also means
these two renders are a **perfectly matched pair**, identical in resampling,
crop and output scale, differing in registration alone.

### `n_eff` falls, and that is the gate working

MEASURED: 17.792 → 15.516, a 12.8% fall, with the fraction of single-frame
pixels rising 49.90% → 54.05%. My earlier instinct was that better registration
should admit *more* agreeing frames. ARGUED, and I now think the opposite is
right: under misregistration a given output pixel is fed a different scene point
by every frame, so the through-focus response is smeared and many frames look
indistinguishable from the winner. Correct registration sharpens that response,
so fewer frames qualify. **A high `n_eff` under misregistration is spurious
averaging, not signal**, which retires the "`n_eff` is the payoff" reading I was
heading toward in §5.

### The radial test I designed, and why I threw it out

A scale error is zero at the centre and grows linearly with radius, so a
treatment that is registration and nothing else must sharpen the corners and
leave the centre alone. That is a spatial control *inside a single pair of
images*, and I built it (`src/radial.py`). Its self-null is clean
(gain-1.0 against itself: ratio 1.0000 in every band, corner−centre `+0.0000`).

**MEASURED, and it is inert on this subject.** Median tile gradient energy falls
from **767661** in the centre band to **4135** in the corner band — the bee is
central and the corners are empty background, so the treatment region contains
no subject to sharpen. The metric also flagged a **2.6% green-mean difference**
between the arms, which follows from the `n_eff` change above and confounds any
gradient comparison. I am reporting the design and its failure rather than its
number, because a metric whose treatment region is empty cannot produce evidence
either way. Reported corner−centre was `−0.0489`; **I do not interpret it.**

### So I looked. Native resolution, side by side

`src/sbs.py` builds 1:1 crops of both renders at the same pixel coordinates in
three radius bands, picking the highest-detail tile in each. Everything below is
me looking at
`C:\dev\strehl-out\M97-before-after\SBS-gain1p0-vs-gain1p9083.png` and
`SBS-OWNER-unaligned-vs-corrected.png`. Earlier tonight I claimed a sharpness
win from memory that a true side-by-side then destroyed (§8), so this is
deliberately cautious.

**Gain 1.0 vs gain 1.9083** — centre band: I cannot tell them apart, which is
what a scale correction must do at zero radius. Mid band: marginal; the granular
patch on the leg is slightly better defined on the corrected side, but not
enough to call alone. Outer band: **the corrected render is visibly better** —
the bristle cluster is more defined, with better micro-contrast and less haze.
That is the radial signature the design predicted.

**Unaligned vs gain-corrected** — the owner's actual before/after. The outer
band lands on the wing, which is the best sharpness target on this subject
(high-contrast micro-hairs on a bright membrane). Centre: indistinguishable.
Mid: marginal. Wing: a slight edge to the corrected render on the vein edges and
the micro-hairs. **Not dramatic.**

**The honest conclusion, and it is a negative result. MEASURED (geometry),
ARGUED (visual):** taking end-to-end misregistration from 150.2 plane px to
3.3 px — a 98.9% reduction, from 37x M86's usability threshold to under it —
does **not** transform this photograph. It produces a real but subtle
improvement, concentrated at large radius exactly as theory requires, and it
costs 2.58x (§5, P7). This is consistent with, and independently corroborates,
M86c's §15.4 inability to show a sharpness win.

**One caveat I will not paper over:** the crops are taken at fixed pixel
coordinates, and changing the registration moves content through those
coordinates. So this is not a strict same-scene-point A/B, and part of what I am
comparing is "what happens to be at that address" in each render. A rigorous
version would register the two outputs to each other before cropping. I did not
build it; it is the first thing I would do with more time.

**Why the image is stubborn is the interesting question, and I did not answer
it.** The merge elects a per-pixel winner from the sharpest frame; a plausible
reading (ARGUED, untested) is that misregistration mostly changes *which* frame
wins rather than corrupting the winner's data, so the output degrades far more
gracefully than a 150 px number suggests. If that is right, the quality ceiling
the owner is hitting is not registration at all, and the next milestone should
be looking somewhere else. **I flag this as the most valuable open question
this milestone produced.**

### The gain is a probe, not a fix

**1.9083 is `ln(0.85714)/ln(0.92241)`, measured on bee-3-cpl frames 0 and 298
alone.** It is per-stack and empirical. It must not be shipped as a constant.
Its only status is as evidence that the residual is a *common multiplicative
gain error in the solve*, which `E*` is structurally blind to (§7), and that
correcting it is worth 45x in geometric residual. **The fix belongs in M86's
estimator, not at my consumption point**, and `signtest.py` gives that milestone
a sharp four-minute end-to-end test.

---

## 12. Status / Changes / Verified / Not verified / Notes

### Status

**DONE, as a verification that located the real defect.** The dispatched work
(wiring) was completed by M86c in `885e9f7` before I could land it; I verified it
independently instead, ran the ground-truth geometry experiment M86c named as
their top follow-up, priced the feature, and — with the orchestrator's
independent drift measurement — **found why alignment does not pay.**

**The wiring is correct. The solve applies 54.3% of the drift that is there.**

### Changes

- `crates/strehl-cli/src/merge_cmd.rs` (+62/−2) — added `WARPMAP_ENV`
  (`STREHL_WARPMAP`) and `alignment_for()`, and pointed the call site at it.
  Needed for three things `load_or_solve` cannot do: consume a **planted**
  sidecar, **never write** to the capture directory, and **hard-refuse** a bad
  sidecar rather than silently re-solving a different registration than the one
  named. `STREHL_ALIGN=0` still wins. No behaviour change when unset.
- `experiments/M97-warped-merge/**` — `PREREG.md`, 13 scripts, logs and JSON.
- `docs/research/M97-warped-merge.md` — this report.
- **No changes** to `merge.rs`, `warpmap.rs`, `align.rs`, `align_cmd.rs`,
  `lib.rs`, `main.rs`, or any other milestone's tree.

### Verified

- `cargo build --release -p strehl-cli`, `cargo fmt`, `cargo clippy --bins
  --tests -- -D warnings` — all clean. `corpus_lint` rc=0.
- **Sign correct as shipped**, by gather: AS-IS 0.92887 toward 1.0, INVERTED
  0.78811 away, at 1.48x raw drift. Independent RAW 0.85714 reproduces the
  orchestrator's 0.85715 to five decimals.
- **Residual after alignment 150.2 plane px, 50.2% of drift removed**, predicted
  0.92924 from the sidecar and measured 0.92887 — two independent routes.
- Gather round-trip closes to 7.3 plane px at the operating point.
- P1 responsiveness **PASS** (+4.252 px plant vs +0.038 px signal, ~110x).
- P2 **NULL**, P3 **PASS** (0.00000% black, 8 arms, 16-bit, 18-px plant
  recovered), P4 **PASS**, P5 **PASS**, P7 **2.58x**.
- Detail metric **disqualified** by its own plant (worse registration reads
  +5.6% better).
- `n_eff` +3.0% aligned vs matched null.
- **Gain probe (§11a)**: the `regain.py` rewriter is a byte-level no-op at gain
  1.0 (0.922414 reproduced; `signtest.py` returns the as-shipped 0.92887), and
  reads 603.07 sensor px at gain 1.9083 against the orchestrator's 603 px. The
  corrected sidecar takes residual **150.2 → 3.3 plane px, 98.9% removed**,
  under M86's `T_usable` of 4.0 px.
- **`cover k = 0.9974` on both gain renders explained, not waved through**: a
  reference-0 sidecar has every `|a| ≤ 1`, so a pull gather samples strictly
  inward and nothing is uncovered. The §9a `k = 0.9315` came from a
  reference-149 sidecar. Held the result until I could explain it.
- The bee-3 renders, **opened and looked at, side by side**, at 1:1 in three
  radius bands.

### Not verified

- P6 **FAILS the pre-registered bar**: refused frames abort the render.
- Whether `WarpMap::load` rejects the torn sidecar I observed.
- ~~Whether fixing the solve's gain would deliver a *visible* win.~~ **Now
  measured (§11a): it does not deliver a dramatic one.** It gives a real but
  subtle improvement concentrated at large radius. What I did **not** verify is
  *why* the image is so insensitive to a 45x geometric correction — that is the
  most valuable question this milestone produced and it is open.
- My side-by-side crops are at fixed pixel coordinates, so registration moves
  content through them; this is not a strict same-scene-point A/B (§11a).
- The radial sharpness test is **inert on this subject** (corners are empty
  background, 767661 → 4135 in gradient energy); its self-null is clean but its
  treatment number means nothing and I do not interpret it.
- The `a` > 1 branch of my gather instrument (§7.3).
- The §11 patch is **uncompiled**.

### Notes

**For routing to M86, three items:**

1. **§4.2's sign is wrong.** *"Frame 0 is roughly 10–12% smaller than frame
   298"* contradicts M86's own sidecar, which places frame 0 at `|a|` = 1.0504
   and frame 298 at 0.9689 about reference 149 — the subject **shrinks**. The
   magnitude in that sentence (10–12%) is just 232.7/2111.2, so only the
   direction is wrong. Code unaffected.
2. **The gain shortfall is 46%, not P8's 12–16%** (§7.2). This is the finding
   that matters and it is squarely M86's estimator, which the brief told me not
   to chase. It is well-posed now: the sidecar's end-to-end scale span is
   0.92241 where ground truth is 0.85714.
3. **`E*` cannot detect this.** A held-out *pairwise* residual is blind to a
   common multiplicative gain error, so 11.56 px can coexist with a 150 px
   end-to-end residual. Any future acceptance bar for the solve needs an
   absolute, end-to-end check — `src/signtest.py` is one and takes ~4 minutes.

**Corrections to the orchestrator's brief, as invited:**

- Your plane-vs-sensor inference was **ARGUED; it is now MEASURED and correct.**
  M86 L106–107: *"the worst **plane** corner … where 1 plane px = 2 sensor px"*,
  and L201–202: *"Total corner drift is … in plane px."* So 232.7 is plane px
  and your 603 sensor px is 301.6 plane px. Your reading was right.
- **But 232.7 and 301.6 are not the same quantity.** M86's figure is the corner
  *displacement* of the solved transforms, including translation and rotation;
  your NCC maximises over translation and reports **scale only**. Like for like,
  the sidecar's scale-only span is **163.8 plane px** against your 301.6 — so
  the shortfall is larger than the 232.7-vs-302 comparison suggests, and your
  measurement is corroborated more strongly than you claimed for it.
- **Coverage is ~13%, not 26%** (§9a) — because the solve only applies half the
  span. And `stack` already crops to the fully-covered region (`k` = 0.9315),
  so there is no low-`n_eff` margin, at the price of a 7.35% full-frame
  upsample.

**Other:**

- Three instrument defects in §3, one in my timing harness, one in my own
  round-trip control (§7.3), and one manufactured control (§5/P3). Every one was
  caught by a plant or by looking at the image. The Pillow 16-bit truncation is
  the one most likely to bite another milestone.
- **My earlier "smooth drift" mechanism was wrong** and is withdrawn. It was
  DERIVED and plausible and it survived until an independent measurement of the
  ground truth arrived. That is the argument for having asked for one.
- **Recommendation.** Do not spend the next milestone on the merge. Spend it on
  the solve's gain: it is a 46% shortfall with a sharp, cheap end-to-end test,
  and it is the only thing standing between this machinery and the ~20x
  reduction M86 believed it had. Until then, alignment costs 2.58x and buys 3%.
- **"Those stacks don't look too good yet" is now partly explained**: not
  because registration is the wrong lever, but because the registration being
  applied is half-strength. That is a better answer than the one I had an hour
  ago, and it came from your measurement, not mine.
