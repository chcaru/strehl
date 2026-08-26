# BUILD-HALO: removing the occluding-edge halo

Implementation notes. Not a research paper. What I changed, what it cost, what
still fails.

**Nothing here has been independently verified.** Every number below is mine and
should be read as UNVERIFIED until a verifier has repeated it.

---

## 1. The mechanism, confirmed by dose-response

M121 measured the halo at `w50` 10.0 px with a 13.25 px cutoff and observed that
this matches `WINDOW_RADIUS = 13` and none of three physical alternatives. That
is a coincidence of one number. Before building anything I made
`WINDOW_RADIUS` overridable at runtime (`STREHL_WINDOW_RADIUS`) and swept it.

`bee-3-cpl`, 299 frames, `--gate 0`, `STREHL_ALIGN=0`, binned linear. Scored with
M121's own `halo_lib.scan()` so the units are commensurable with fact 1778.

| `WINDOW_RADIUS` | 3 | 6 | 9 | 13 | 20 | 26 |
|---|---|---|---|---|---|---|
| rim `w50` (bright surround), px | 8.75 | 8.75 | 9.50 | 10.75 | 19.00 | 25.75 |
| rim **cutoff**, px | 9.25 | 9.75 | 10.75 | 14.00 | 21.25 | 29.00 |
| `C` `w50` (M121 headline stat) | 9.75 | 9.75 | 13.25 | 13.50 | 17.25 | 19.75 |

Over w9–w26, clear of the instrument floor, **the cutoff is linear in the window
radius with slope 1.07 and intercept 1.08** — that is
`SOBEL_RADIUS + WINDOW_RADIUS`, 1:1 over a 3x range.

**The halo is the focus window. It is our artefact and it is this constant.**

Two things fall out of the ladder that were not in the brief:

- Radii 3 and 6 are floored at ~8.75 px by the instrument, not by the image:
  M121's transition exclusion is `C_d0 = 1.6 x rise_p90 ~ 7.6-8.3 px`, so **the
  `C` statistic is structurally blind to a rim narrower than ~8 px.** When
  reporting a *reduced* halo, report the `bright` component. `C` cannot see the
  win.
- Because the halo paints the foreground's elected frame across the background
  out to one window radius, **the shipped winner field's own depth step sits ~13
  px into the background, not on the silhouette.** Any guide built from the
  shipped winner field is therefore useless for locating the edge it has to
  avoid. The guide must be elected narrow. This killed my first design.

---

## 2. What did not work: shrinking the support

The obvious fix is to make the window smaller than the distance to the
discontinuity. I built it (`SelectionScale`, a five-level radius ladder
`[1,2,4,8,13]`) and it fails, twice, for two different reasons.

**First failure — no confidence test.** In a defocused background no frame is in
focus, so the narrow guide's argmax is essentially uniform over the bracket, its
local range is ~N frames *everywhere*, and the range test marks the entire
background as a depth step. 47.53% of the plane treated, 24.67% of it at radius
1, background `grad_mean` **+31.4%**. A noise explosion, not a halo fix. Fixed by
a confidence veto: a pixel is only treated when there is genuinely sharp content
within reach of its window, measured against a low percentile of the guide
response rather than a DN constant. That took treatment to ~21%.

**Second failure — the one that killed the approach.** With the veto in place I
swept four operating points and **every one moved the M121 statistic the wrong
way.** The reason is structural and I should have seen it earlier: at `--gate 0`
the gate census reports `n_eff = 1.000` on every pixel, so the merge is a *pure
selection* and the output pixel IS the elected frame's sample. Cutting the
support from 729 gradient samples (radius 13) to 81 (radius 4) elects a visibly
more random frame. **Shrinking support trades the halo for election noise at a
bad rate.** The corpus already warned about this shape of error (fact 86: a
regulariser of width 3 is worse than none).

`SelectionScale` is left in the tree because it is what proves the dose-response
and it is fully tested, but **the shipped path does not use it.**

---

## 3. What worked: depth-layer masked support

Keep the full 13 px radius. Drop only the samples that do not belong to the
pixel's own depth.

For a background pixel one radius outside a silhouette, roughly half its window
is still background, so the masked support is ~350 samples rather than 81. It
discards the contamination without discarding the statistics.

The operator is a joint bilateral filter of the gradient magnitude with the
range term driven by the narrow guide winner field:

```text
focus_k(p) = sum_q g_k(q) K(w(q) - w(p)) / sum_q K(w(q) - w(p))
```

which is not separable as written. It is made separable exactly the way a
bilateral grid is: quantise the depth axis into `N_LAYERS = 6` bins over the
guide's own robust span, run one ordinary separable box filter per bin, and have
each pixel read the bin its own guide winner falls in.

Because `box_mean` normalises numerator and denominator by the identical window
area, the border handling cancels and the ratio is the exact masked mean at every
pixel including the plane edges.

### Pipeline

Three passes instead of two, and only when asked for:

0. **Depth guide.** Elect a winner field at `GUIDE_RADIUS = 4` with the
   regulariser capped to match, so the guide's own step is displaced ~5 px
   rather than ~13. This pass never elects an output pixel.
1. **Pass one**, as shipped, but the focus field and the regulariser both use
   layer-masked support at the treated pixels.
2. **Pass two**, as shipped, same substitution.

Both ends of the box cascade have to be masked or neither: an edge-aware focus
window under an unmodified radius-8 regulariser just re-manufactures the rim at
the regulariser's own scale.

### The three guards, all of which are load-bearing

- **Confidence veto** (`STREHL_EDGE_CONF`, default 2.0): treat only where the
  strongest guide response within a window exceeds 2x the 10th percentile of
  that same statistic. Both sides are a max-over-window, so the upward bias an
  extremum carries over noise cancels instead of having to be modelled. Without
  this the fix fires over dead ground and explodes noise (§2).
- **Depth tolerance** (`STREHL_EDGE_TAU`): how many frames of guide variation a
  window may span before it is judged to cross a discontinuity. Defaults to an
  eighth of the bracket's own robust winner span (36.4 frames on `bee-3-cpl`),
  so it is a property of the bracket, not of the sensor.
- **`MIN_LAYER_FRACTION = 0.12`**: a pixel whose own layer occupies less than
  12% of its window is withdrawn to the shipped operator. This is the antenna
  case — it is §2's failure arriving by a different road, and the invariant is
  unit-tested directly rather than through a hand-computed instance.

### Shipping dark

Off by default behind `STREHL_EDGE_AWARE`, following the repository's existing
convention (`STREHL_ALIGN`, `STREHL_FIX_HALO`, `STREHL_SOFT_GATE`,
`STREHL_ROBUST_ELECTION`) because `main.rs` belongs to another agent.

Both `compute_layered` and `regularise_layered` compute the shipped box mean
first and overwrite only the treated minority, so a support that treats nothing
is byte-identical to the shipped operator. `STREHL_EDGE_AWARE=0` was confirmed
byte-identical to a pristine-HEAD build (both `965AA23B...`).

---

## 4. Cost

On `bee-3-cpl`, 299 frames, 13 workers:

| | shipped | edge-aware |
|---|---|---|
| wall clock | 18.8 s | 61.5 s |
| passes over the frames | 2 | 3 |
| box filters per frame | 2 | up to 14 |

**3.3x wall clock.** The third decode pass is about a third of it; the rest is
the per-layer box filters. The obvious optimisation — skip layers with no
treated pixels — is already in. Memory is `N_LAYERS` fraction planes per radius,
shared across workers, not per worker.

---

## 5. Results

Three subjects, including one of the owner's new stacks
(`flower-inner-edge-cpl`, captured 08/25). Both arms of every pair rendered
back-to-back from **one binary** (see §7 for why that matters). `--gate 0`,
`STREHL_ALIGN=0`, binned linear — never `--srgb`.

### 5.1 The pictures

Written as 16-bit `before | after | 3x difference` panels:

- `C:\dev\strehl-out\BUILD-HALO\ab2\crops\bee3-crop{0,2}-*-before-after-diff3x.tif`
- `C:\dev\strehl-out\BUILD-HALO\subjects\crops\flower-inner-edge-cpl-crop{0,1,2}-*-before-after-diff3x.tif`
- `C:\dev\strehl-out\BUILD-HALO\subjects\crops\flower-bud-with-background-fern-cpl-crop{0,1,2}-*-before-after-diff3x.tif`

8-bit viewing previews (gamma applied, **do not measure on these**) alongside in
`...\ab2\preview\` and `...\subjects\preview\`.

Crop locations were not hand-picked to flatter: they are the highest
mean-absolute-difference blocks between the two arms, i.e. wherever the operator
did the most work.

**What I see, on all three subjects:** the bright rim along occluding
silhouettes is narrower and weaker, the background reaches closer to the
subject, and structure the halo had veiled comes back — most clearly on
`bee-3-cpl` at the antenna and claw, where mouthparts and small dark features
that were washed out are legible again.

**The halo is not gone.** A light rim is still visible on the bee's claw and
along the flower bud's left edge.

### 5.2 Halo width, measured M121's way

M121's own `halo_lib.scan()`, so the units are fact 1778's.

| subject | arm | `C` peak | `C` w50 | cutoff | n edges |
|---|---|---|---|---|---|
| `bee-3-cpl` | before | +0.634 | 17.25 | 25.50 | 36 |
| `bee-3-cpl` | after | **+0.248** | **14.50** | **17.50** | 15 |
| `flower-inner-edge-cpl` | before | +0.185 | 19.00 | nan | 31 |
| `flower-inner-edge-cpl` | after | +0.340 | 19.25 | 29.75 | 16 |
| `flower-bud-…-fern-cpl` | before | +0.118 | 15.50 | 29.50 | 101 |
| `flower-bud-…-fern-cpl` | after | +0.228 | 22.25 | nan | 59 |

**The statistic agrees with the pictures on `bee-3-cpl` and contradicts them on
the other two. I am not claiming the metric supports this fix.**

Three things are wrong with reading these numbers as a verdict, and I would say
so whichever way they had come out:

1. **It is not a paired comparison.** `scan()` re-detects edges in each arm's own
   image, and the edge counts differ by 2x between arms. Different edges,
   different widths.
2. **The paired read returns `nan`.** The matched-pixel (DONOR) reading cannot
   produce `C` on any arm, because `C` is only read beyond
   `1.6 x rise_p90` and `rise` inflates from ~3 px to 20-30 px on the treated
   arms. `rise` is `inside.max() - inside.min()` over profile samples between
   10% and 90% of amplitude, so *any* added structure or noise near the edge
   inflates it — it reads like catastrophic blurring and is not (see §5.3).
3. **`C` is structurally blind below ~8 px** (§1), so it cannot register a rim
   that has been reduced into that range.

My reading is that the instrument is being confounded by the detail recovery
that is the point of the fix. **That is an interpretation, not a result**, and it
is exactly the kind of claim that should not be believed without a verifier.

### 5.3 Sharpness regression — the fix is not a blur

> **VOID — see §13.2.** This subsection's evidence is `hp_energy`, and
> `hp_energy` cannot support a sharpness conclusion in either direction. V-HALO
> killed this claim; §13.2's commissioning then showed the statistic is also
> nearly blind to the artefact V-HALO cited it for. The conclusion may well be
> right — §13.4 re-derives it on a seam-excluded statistic and it survives —
> but **nothing below this line is evidence for it.** Left in place because a
> deleted claim cannot be audited.

The failure mode to rule out is buying the halo with softness. Checked by
comparing gradient-magnitude statistics over the whole plane, before vs after,
with the top decile and p99.9 carrying the fine detail:

| subject | `grad_mean` | `grad_p99` | `grad_top_decile_mean` | `grad_p999` |
|---|---|---|---|---|
| `bee-3-cpl` | 1.032 | 1.011 | 1.017 | 1.005 |
| `flower-inner-edge-cpl` | 1.023 | 1.015 | 1.013 | 1.006 |
| `flower-bud-…-fern-cpl` | 1.015 | 1.008 | 1.011 | 1.004 |

**Every statistic moved up.** A blur drives all of these down, hardest at the
top of the distribution; nothing here is below 1.0. The fine-detail tail
(`grad_p999`) is up 0.4-0.6%, so no sharpness was spent.

`grad_mean` rising 1.5-3.2% while the detail tail rises only ~0.5% is the
signature of a small amount of added noise in the treated band, which is
consistent with the miscalibrated gate discussed below. For scale, the
abandoned support-shrinking approach put this figure at **+31.4%**.

---

## 6. What still fails

- **The halo is reduced, not gone.** See the crops: a light rim is still visible
  against the background on the bee's claw and the flower bud's edge. I have not
  quantified what remains in a way I trust — see §5.2 for why the obvious
  statistic will not do it.
- **M121's `C` cannot adjudicate this.** It is not paired, it is blind below
  ~8 px, and its `rise` gate degenerates on the treated arms. **A verifier needs
  a paired, fixed-edge-set instrument**, ideally reading the `bright` component
  on edges located once in the baseline and reused for both arms. That
  instrument does not exist yet and I did not build it, because building it
  would have been the research the owner halted.
- **`FOCUS_NOISE_SD = 0.015214` is calibrated for radius 13 with the radius-8
  regulariser.** Under masked support the effective sample count at a treated
  pixel is lower, so the gate is miscalibrated there — it will admit fewer
  frames and leave a slightly noisier band near edges. Unquantified. This is a
  real, known, undischarged cost.
- **Six depth bins is a quantisation.** Two surfaces whose depths fall in the
  same bin are not separated, and a bin boundary running through a smooth depth
  ramp is a discontinuity the operator invents. A bilateral grid would normally
  interpolate between adjacent bins; this does not. Nearest-bin was chosen for
  cost and it is the most likely source of any patchiness in the output.
- **Only measured at `--gate 0`,** where the merge degenerates to pure selection.
  That is the worst case for election noise and the cleanest case for reading the
  halo, but M121's published headline was taken at gate 4, so my baseline is not
  numerically comparable to fact 1778 — only to my own control.
- **Alignment off** throughout, to keep the comparison clean. Untested with
  `STREHL_ALIGN=1`.

---

## 7. Reproducing

```powershell
$env:STREHL_ALIGN = "0"
$env:STREHL_EDGE_AWARE = "1"      # 0 for the shipped path
.\target\release\strehl.exe stack D:\personal\macro\bee-3-cpl --gate 0 -o out.tif
```

Knobs: `STREHL_EDGE_TAU`, `STREHL_EDGE_CONF`, `STREHL_WINDOW_RADIUS`.

Measurement, in M121's own units, using M121's own `scan()`:

```powershell
python experiments\BUILD-HALO\measure.py --baseline base=before.tif --arm after=after.tif --json out.json
python experiments\BUILD-HALO\crops.py --before before.tif --after after.tif --out crops --tag subject
```

`crops.py` deliberately emits the sharpness regression alongside the crops, so a
halo claim cannot be made without the blur check attached.

---

## 8. A note on measuring while another agent is editing the tree

Three renders of the *same* command with the *same* merge code produced three
different files during this work. The cause was `BUILD-RENDER` live-editing
`crates/strehl-cli/src/image_out.rs`, which I do not own; it changed twice inside
ten minutes while I watched. Per-channel ratios between two such renders were
1.38 / 1.43 / 1.49, which is a photometric change, not a merge change.

**Any A/B whose two arms were built at different times during a concurrent
session is confounded.** Every comparison in this document has both arms rendered
back-to-back from one binary for that reason. The earlier `WINDOW_RADIUS` ladder
is internally consistent for the same reason — all seven rungs came from one
build.

---

## 9. The frozen-ROI campaign — the authoritative result

Section 5 measured with M121's `scan()`, which re-detects edges per arm and is
therefore unpaired. BUILD-RENDER has since frozen a ROI plan
(`C:\dev\strehl-out\roi-plan.json`) and captured a 26-subject baseline. That is a
genuinely **paired** instrument at fixed coordinates, which is what §5.2 said was
missing. Everything below uses it, via BUILD-RENDER's `scripts/crop_set.py` — its
code, not a reimplementation.

### 9.1 The baseline is reproducible from this tree

The confound recorded in §8 is **resolved**. `bee-2-cpl` rendered from HEAD with
`STREHL_EDGE_AWARE` unset is **byte-identical** to BUILD-RENDER's frozen
baseline (`D2DC0272 8033E359 035C5BB1 C122A5F8`). Their colour work genuinely
moves zero pixels on the measurement path, and the frozen baseline can be used
as the "before" arm without re-rendering it.

All numbers below are at the **product default gate (4.0)**, not the gate 0 used
in §5. `MeanNeff` is unchanged by the fix (66.5 -> 66.9 on `bee-2-cpl`), so the
gate is not disturbed. Cost at the default gate is **2.07x** wall clock
(51.5 s -> 106.8 s), better than the 3.3x measured at gate 0.

### 9.2 Sharpness: clean, again

> **VOID — see §13.2 and §13.4.** "0 of 15 worse, mean +6.7%" is an `hp_energy`
> reading, and V-HALO showed the same statistic rises +16.8% on *flat* crops —
> regions selected for having no structure — so it was scoring the artefact as
> detail. §13.2 then found `hp_energy` is also ~blind to invented edges (+0.1%)
> and is dominated by noise (+76.6% for a +33% noise SD), which means the
> +6.7% here is largely the **+4.6% noise rise reported in the next sentence**,
> counted twice and with the sign flipped. §13.4 re-derives the claim properly.

Over 15 detail crops on 5 subjects, `hp_energy` (std of the Laplacian):
**0 of 15 worse, mean +6.7%**, range +0.0% to +23.1%. Flat-region `noise_sd`
rises **+4.6%**, consistent with masked support lowering the effective sample
count at treated pixels (the `FOCUS_NOISE_SD` miscalibration in §6). **The fix
is not a blur; it costs a little background noise.**

### 9.3 Halo: uneven, and the scalar cannot see it

`edge_overshoot` over 15 edge crops: **3 improved** (-97.9%, -102.5%, and one
marginal), **12 unchanged within +/-0.2%**.

**Do not read that as "no effect."** The operator masked 9-20% of the plane on
every subject, and the pictures show large changes at ROIs the scalar reports as
unchanged. `flower-inner-edge-cpl` edge0 scores **+0.1%** while the composite
shows the dark background going from a muddy grey-green veil to genuinely dark
with crisp trichome silhouettes — one of the clearest improvements in the set.
`edge_overshoot` is `max(g[band]) - p90(g)`: a **single-pixel** statistic, which
on these subjects is pinned by a specular highlight that the merge never
touched. BUILD-RENDER already warned it disagrees with the eye and must not be
gated on; this is a second, independent confirmation from the other direction.

### 9.4 Where it works and where it does not — the real boundary

Sorted by how much of the plane the operator treated:

| subject | masked | verdict by eye |
|---|---|---|
| `bee-2-cpl` | 19.97% | veil around claw substantially reduced; hairs crisper |
| `bee-3-cpl` | 19.43% | improved |
| `flower-inner-edge-cpl` | 17.19% | **large** — dark background recovered |
| `flower-bud-…-fern-cpl` | 10.62% | **rim not removed** |
| `lavendar-cpl` | 9.15% | minimal change |

The two subjects where the halo survives are the two where the operator barely
fires, which looked like a too-conservative guard. **It is not.** Re-rendering
`flower-bud` with the confidence veto at 1.15 instead of 2.0 raised firing
**10.62% -> 16.81%** and the thick white sheath around the bud is **unchanged**
by eye.

That is the honest boundary of this fix:

- it removes **veiling** halo — the smoky, low-contrast wash the box window
  drags across a defocused background, whose lobed/scalloped boundary is the
  window's own footprint;
- it does **not** remove a **tight bright sheath** hugging a high-contrast
  silhouette, as on `flower-bud`. That rim is a few px wide, narrower than the
  radius-4 guide, so the guide is itself haloed at that scale and assigns the
  rim to the foreground layer — the mask cannot exclude what it has already
  mislabelled. Fixing it needs a guide that resolves finer than the rim, or
  fix 3/4 from the brief (bimodality / two-layer unmixing).

### 9.5 New artefact introduced

Mild **blotchiness** at treated transitions, visible on `bee-2-cpl` edge2. This
is the `N_LAYERS = 6` bin quantisation with no interpolation between bins. It is
much less objectionable than the halo it replaces but it is not nothing, and a
verifier should look for it.

### 9.6 Verdict

**Not print-worthy yet.** The disqualifier is materially reduced on 3 of 5
subjects and one of those is a large, obvious win, but it survives on
`flower-bud-…-fern-cpl` and `lavendar-cpl`. Reported as PARTIAL.

Artefacts: `C:\dev\strehl-out\BUILD-HALO\compare-halo-on\` (45 side-by-side
composites at frozen ROIs), `…\compare-conf115\`, `…\halo-on\<subject>\linear.tif`
(16-bit linear), `…\halo-off\bee-2-cpl\linear.tif` (byte-identity control).

---

## 10. v2: interpolated grid + feathered treatment

Addresses ORCH decisions (a) blotchiness and (b) the noise cost. Both landed;
(b) turned out to be mostly a symptom of (a).

### 10.1 Two separate discontinuities, not one

The blotching had **two** causes and I initially only saw the first:

1. **Quantised depth axis.** `bin` was a hard `floor()`, so two neighbours whose
   guide winners differed by one DN used two unrelated supports. Fixed with a
   proper bilateral-grid **tent splat**: every pixel contributes to the two
   bins straddling it with weights summing to 1 (`tent`, `straddle`), and the
   gather blends the same two. Cost is unchanged -- same number of box filters.
2. **Hard treatment switch.** `layer[i]` was treated-or-not, so a fully masked
   pixel sat directly against a fully full-window neighbour. **Interpolating the
   depth axis cannot fix this** -- the discontinuity is in *whether* the pixel
   is treated, not in *which bin* it landed in. Fixed by making all three guards
   ramp (`smoothstep`) instead of veto, and blending the masked response toward
   the shipped one by `blend[i]`.

`FEATHER = 1.25` and it is load-bearing in a way a unit test caught. The three
guards **multiply**, so at `FEATHER = 2.0` a pixel had to clear twice the depth
step *and* twice the confidence floor *and* twice the support floor to be
treated at full strength -- and essentially none did. That would have applied
the fix at partial strength everywhere and quietly left halo on the plate.
`treatment_fades_in_rather_than_switching_on` failed on exactly that and is kept
as the guard against re-widening it.

### 10.2 The noise cost was the cliff, not the gate

ORCH routed (b) as recalibrating `FOCUS_NOISE_SD` for the masked support. That
was not where the noise was coming from. Flat-region `noise_sd` versus baseline:

| subject | v1 hard switch | v2 feathered | `hp_energy` v2 vs baseline |
|---|---|---|---|
| `bee-2-cpl` | +8.9% | **+4.5%** | +3.4% |
| `flower-inner-edge-cpl` | +5.3% | **+1.3%** | +1.9% |
| `flower-bud-…-fern-cpl` | +5.5% | **+1.1%** | +0.2% |

**The noise penalty fell by 65-80% with no change to the gate at all**, because
most of it was the two discontinuities injecting high-frequency structure, not
the sample-count miscalibration. ~~`hp_energy` stays above baseline on all three,
so v2 is still not a blur.~~ **That inference is VOID — see §13.2.** The
`hp_energy` column tracks the `noise_sd` column almost exactly (+4.5/+3.4,
+1.3/+1.9, +1.1/+0.2), which is what §13.2 predicts if it is measuring the
noise and not detail. It is the *same quantity twice*, not a sharpness result
next to a noise result. The caution below was right and did not go far enough:

Some of v1's *higher* `hp_energy` was the blotch
edges themselves reading as detail -- a caution against treating that statistic
as pure goodness.

The `FOCUS_NOISE_SD` miscalibration is **real and still unfixed**; it is simply
much smaller than the +4.6% originally attributed to it.

### 10.3 What did NOT get fixed, and what it actually is

**The bright blobs hugging silhouettes survive v2 essentially unchanged.** They
are visible on `bee-2-cpl` edge2 in `cmp-hard-vs-feather/`. I attributed them to
quantisation in §9.5 and **that attribution was wrong.**

They are the **coverage boundary of the fix itself**. In the baseline that
region is one smooth grey veil. The operator lifts the veil where a pixel's
window still holds enough background to average -- and withdraws where it does
not, which is precisely the pixels closest to the silhouette, via
`MIN_LAYER_FRACTION`. The result is a patchwork: veil-removed (bright) against
veil-remaining (grey), with the blob edge sitting exactly on the support floor.
Feathering that floor softened it and did not remove it, because the underlying
quantity being thresholded genuinely does fall off a cliff as the window fills
with foreground.

This is the same structural wall as §9.4: **near the silhouette there is not
enough background in a 13 px window to reconstruct the background from.** No
amount of masking or feathering creates information that is not in the window.
That is what fix 3/4 (bimodality / two-layer unmixing) is for, and it is why
ORCH's decision (c) is the right next move rather than more tuning here.

### 10.4 Status

Off-path byte identity re-verified after all v2 edits: `bee-2-cpl` with
`STREHL_EDGE_AWARE` unset is still `D2DC0272…`, identical to the frozen
baseline. 388 core tests pass (4 added in v2).

Artefacts: `C:\dev\strehl-out\BUILD-HALO\halo-feather\` (renders),
`…\cmp-base-vs-feather\` (v2 vs baseline, 27 composites),
`…\cmp-hard-vs-feather\` (v1 vs v2, isolates the artefact work).

**Still not print-worthy.** Veiling halo is materially reduced; the tight rim
and the coverage-boundary blobs remain.

---

## 11. (c) Through-focus bimodality — the detector, and the green light

ORCH's question was precise, and so is the answer: **does the through-focus
response go bimodal on the pixels the masked-support fix still fails** — the
tight rim (§9.4) and the coverage blobs (§10.3)? If yes, build the unmixing.
If no, stop and report, because then the forward model is wrong too.

**It does. It replicates on three subjects, monotonically, in every distance
band.** All numbers UNVERIFIED.

### 11.1 The statistic that was wrong first

The obvious detector is the ratio of the second through-focus peak to the
first. It is wrong, and it is wrong in a way worth recording because the same
defect has now bitten this project three times.

Measured on `bee-2-cpl`, `r2/r1` fires on **54.2% of clean defocused ground**
— ground 41 px from any silhouette. Worse, at any threshold that controls that
false-positive rate, near-silhouette pixels fire **3–4× LESS** than clean
ground:

| FPR on clean ground | threshold | blob pixels | treated | enrichment |
|---|---|---|---|---|
| 10% | 0.990 | 2.72% | 3.22% | 0.27× |
| 1% | 0.999 | 0.26% | 0.31% | 0.03× |

The reason is that on featureless background **neither peak is real**. Both are
noise, so the ratio tends to 1 by construction. `r2/r1` measures *the absence
of a dominant peak*, not the presence of two — and featureless ground has the
least dominant peak of anything in the frame.

This is the same defect as `edge_overshoot` (§9.5): **an unnormalised ratio
reports whatever dominates its denominator.** Normalising against
`FOCUS_NOISE_SD` would not have rescued it either, because that constant is
calibrated for `WINDOW_RADIUS = 13` and the guide runs at radius 4 — a
constant that does not transfer, which is this project's whole thesis.

The fix is to refer **both** peaks to the pixel's own through-focus baseline
first: `z = (r − μ) / σ` over that pixel's own curve. Self-normalising at any
radius, on any scene, with no calibrated constant. That inverts the result.

### 11.2 The dose-response

The instrument is the one that settled the mechanism in §1: a ladder, not a
single number. The axis is distance from a depth step in the guide field —
external to the fix, and the axis the halo itself lives on.

`z2/z1`, the balance between the two modes, from the silhouette outward:

| distance | `bee-2-cpl` | `flower-bud…fern-cpl` | `flower-inner-edge-cpl` |
|---|---|---|---|
| 0–2 px | **0.838** | **0.873** | **0.751** |
| 4–6 px | 0.368 | 0.649 | 0.461 |
| 9–13 px | 0.260 | 0.507 | 0.350 |
| 18–26 px | 0.220 | 0.378 | 0.278 |
| 80–400 px | 0.115 | 0.166 | 0.086 |
| **swing** | **7.3×** | **5.3×** | **8.8×** |

Monotonic in every band in all three, including the owner's new stack
(`flower-inner-edge-cpl`) and the tight-rim subject.

Mode **separation** tells the same story: 93.7 → 43.1, 97.2 → 47.9, 72.3 →
56.8 frames. At the silhouette the two modes are not merely both present, they
are nearly a hundred frames apart — the foreground coming sharp at one end of
the bracket and the background at the other, inside one 13 px window.

### 11.3 The confound, refuted rather than argued

The obvious objection is that *anything* looks elevated near an edge because
there is more contrast near an edge. That predicts the **first** mode rises at
the rim too.

It does the opposite, in all three subjects:

| | rim (0–2 px) | far (80–400 px) |
|---|---|---|
| `bee-2-cpl` | 3.17 | **6.28** |
| `flower-bud…fern-cpl` | 3.01 | **5.57** |
| `flower-inner-edge-cpl` | 3.32 | **7.41** |

`z1` is *weakest* at the rim and strongest on open ground. The second mode is
therefore not riding a general rise in contrast — the two move in opposite
directions, and the ratio's 5–9× swing is the difference between them.

### 11.4 What the picture shows that the rate does not

`bimodal_look.py` puts render, detector, firing mask and fix coverage in one
window at the frozen edge ROIs
(`C:\dev\strehl-out\bimodal\bee-2-cpl-where-it-fires.tif`).

The detector map shows **clean bright ridges hugging every silhouette**, with
black (unimodal) foreground interiors — structurally exactly right. But the
*thresholded* map is swamped by background speckle, and per-pixel recall at a
1%-false-positive threshold is only ~8%.

So the honest reading is: **the signal is real, correctly located, and
continuous — but weak per pixel.** Hard-thresholding it into a binary mask
throws most of it away. It should be used as a continuous weight, which is
what the unmixing wants anyway, since α is continuous.

That also means the earlier `blend`-stratified reading (untreated 41% /
boundary 58% / treated 64%) is the weak instrument and should not be quoted:
the coverage map is derived from the guide, which is itself haloed, so
stratifying by it is circular. The distance profile is the instrument.

### 11.5 Cost

20 B/px — two `f32` peaks, two `u16` frame indices, two `f64` moments —
**constant in the frame count**, riding the guide pass at no extra decode.
230.8 MB on an 8.2 Mpx plane at 299 frames. Allocated only when
`STREHL_BIMODAL_DUMP` names an output directory; a normal render pays nothing.

### 11.6 Verdict

**Green light for two-layer unmixing.** The forward model
`I_k = α·(F⊛PSF_k) + (1−α)·(B⊛PSF_k)` is not an assumption at these pixels —
its signature is measured, replicated and dose-responsive.

`mode_balance()` (`z2/z1`) is the quantity to build on, and `LayerSupport`
already computes the other half: `fractions[l]` is the tent-weighted share of
each window belonging to each depth layer, which is a direct estimate of α.

**The halo is still not gone and this changes nothing about that yet** — §11
is a detector and a decision, not a fix. The rim is still on the plate.

---

## 12. `FEATHER` chosen from images, and a hard number on what remains

ORCH ordered `FEATHER` re-chosen from real composites rather than the single
synthetic probe it came from, calling a synthetic-picked load-bearing constant
a liability. The sweep was run at 1.25 / 1.6 / 2.0 on two subjects, **all arms
from one frozen binary back-to-back** (§8). All numbers UNVERIFIED.

`FEATHER = 1.0` cannot be swept: `feather()` asserts `v > 1.0`, because at 1.0
the guards are hard switches again and the treatment boundary is the cliff §10
existed to remove. The hard-switch control is `e5e62d4`, already measured.

### 12.1 The result: it is not load-bearing

| arm | flat noise | edge noise | pixels differing vs 1.25 | max delta |
|---|---|---|---|---|
| 1.25 | — | — | — | — |
| 1.6 | -0.09% | -0.57% | 3.64% | 11377 DN |
| 2.0 | -0.42% | -0.64% | 5.12% | 12951 DN |

Large *local* deltas, negligible global ones — so the metric cannot adjudicate
and the composites were the instrument, per the standing rule. The composites
(`C:\dev\strehl-out\feather\*-feather-compare.tif`) show the arms differ
**only along the boundary of the treated region**, which is exactly what a
feather width should touch and nothing more.

The decisive measurement is the rim veil itself:

| arm | rim 0-4 px | far 80+ px | **rim/far** |
|---|---|---|---|
| 1.25 | 15665 | 6686 | **2.3431** |
| 1.6 | 15665 | 6686 | **2.3431** |
| 2.0 | 15667 | 6686 | **2.3433** |

Identical to four decimal places. **`FEATHER` has no effect on the halo at
all.** Its influence is confined to the blob-boundary artefact it was
introduced for.

So the value stays at **1.25** — but the useful outcome is not the value, it
is that the constant has been **demoted**: it is not a liability for the
deliverable, because the deliverable does not depend on it. It still matters
for §10's blotching, and there the narrow setting remains right on the
multiplication argument.

### 12.2 What remains, in a paired number

Veil profile: mean brightness of each distance band, over distant background.
Both arms use the **same** pass-zero guide, so although the absolute ratio is
*not* interpretable as halo strength (near-silhouette pixels are genuinely
near a bright subject, and the guide mask is haloed exactly where it is being
asked about), **the delta between arms is a valid paired measurement.**

| subject | 0-2 px | 2-4 px | 4-6 px | 9-13 px |
|---|---|---|---|---|
| `bee-2-cpl` | -0.0% | -0.1% | -0.2% | -0.1% |
| `flower-bud...fern-cpl` | -0.0% | -0.1% | -0.1% | +0.0% |
| `flower-inner-edge-cpl` | **+1.4%** | +1.2% | +0.6% | +0.1% |

**The shipped masked-support fix changes near-silhouette background brightness
by <=0.2% on two of three subjects**, while treating 20.29% and 10.70% of those
planes respectively. That is consistent with §9's frozen-ROI result (halo
improved at 3/15 ROIs, unchanged at 12/15) and it is the same wall as §10.3
from a third direction.

`flower-inner-edge-cpl` is the exception and the sign is instructive: the
plane-averaged change is *positive*, yet the visible win at that subject's
`edge0` is large and real. **Plane-averaged statistics wash out localised
wins** — which is the third time on this build that a scalar has disagreed
with the picture, and the third time the picture was right.

### 12.3 Verdict

**The halo is not gone. The stacks are not print-worthy.** The masked-support
fix is real but narrow: it works where a 13 px window still holds enough
background to average, and does essentially nothing at the tight rim, which is
where the owner's eye goes first.

That is not a tuning deficit and no further tuning will move it — §10.3 and
§11 reach the same wall independently. The rim needs the background
**reconstructed**, not selected, and §11 establishes that the information
needed to do so is present and measurable.

---

## 13. (d) landed, and the sharpness claim re-derived after V-HALO killed it

Everything in this section is **UNVERIFIED** — my own measurements on my own
change. It exists to be attacked.

### 13.1 (d): `--linear-srgb` and the described measurement write

Two commits, `9695b3c` (code) and `170433b` (re-baseline).

`fdb69ba` published `OutputSpace`/`Develop` and carried `space` into
`MergeOptions`, but nothing read it: `write_merged` still took `srgb: bool`,
and every write site still asked `if srgb` for a question that is really two —
*move to colorimetric primaries?* and *apply a transfer curve?* Welding those
together is precisely why the one mode measurement needs was unaskable. The
write sites now read `space`, the matrix rides with `wants_matrix()`, and both
developed sites build their `Develop` through `OutputSpace::develop` so the
space→development mapping exists once, in `image_out`, rather than being
re-spelled here.

`write_merged` re-derives `srgb` from `space` on the **first line of its body**,
so the byte-frozen encoder below it was not edited — not semantically and not
textually.

**HEAD did not compile before `9695b3c`.** `main.rs` sets `space:`, and that
field has existed in `MergeOptions` since `fdb69ba`, but the `main.rs` side was
never committed, so `cargo build` at `3afa801` fails with E0063. I carried that
wiring in. It is BUILD-RENDER's work, not mine, and I committed it only because
a shared tree nobody can build blocks everyone. My one edit there is the
deletion of the four-statement interim guard, which BUILD-RENDER's own comment
authorised.

That guard was protecting a real failure and it does not simply evaporate. If
the body has no characterisation there is no matrix, and `--linear-srgb`
degrades silently to camera-native. The measurement branch now **warns** when
reached with a non-measurement space, so the degradation is loud rather than a
file that merely looks right.

**Both freeze rows moved and neither moved a pixel.**

| row | before | after |
|---|---|---|
| `coffee-bean-20-gate2-unaligned` | `D99F5D82…76CA` | `89958637…C218` |
| `coffee-bean-20-gate2-sidecar`   | `119936E6…D709` | `2DB8A978…46E5` |
| bytes | 49449626 | 49450019 (+393) |

Checked, not asserted — "only the tag moved" is exactly the claim that is cheap
to get wrong:

- a **pinned** build of `3afa801` (`git archive` of the explicit SHA, built in
  isolation) reproduced **both** previous hashes exactly. That is what
  *commissions* the comparison: a post-change binary is incapable of producing
  those two hashes, so reproducing them proves the pin resolved to pre-change
  sources.
- `tifffile.imread` of old and new is `array_equal` at `uint16` for both rows.
  Not a hash comparison, and not PIL, which would have silently downconverted
  three-channel 16-bit to 8.
- `--linear-srgb` was then commissioned in the other direction: it differs from
  the default (so the matrix really applies), and `srgb_encode(--linear-srgb)`
  agrees with `--srgb` to **max |d| = 3 DN, mean 0.26 DN** out of 65535. It is
  exactly `--srgb` minus the curve, which is what it claims to be.

### 13.2 The instrument problem — and a correction that cuts both ways

V-HALO killed the v1 "not a blur" claim: `hp_energy` rose **+16.8%** on flat
crops and **+93.6%** on `flower-bud flat1`, inside regions the ROI plan chose
*because they contain no structure*. Its verdict — *"its own sharpness evidence
is measuring the artefact it introduced"* — was right that the claim was void,
and I accept that without reservation.

**But I then commissioned the replacement instrument on synthetic arms, and the
commissioning says `hp_energy` does not support V-HALO's inference either.**
Flat ROI, noise only, one artefact injected per row:

| arm | `hp_energy` | `hp_ncc` | `d_ac1` |
|---|---|---|---|
| one invented hard edge | **+0.1%** | 0.9997 | **+0.995** |
| blotch seams (the v1 signature) | +4.4% | 0.9786 | **+0.739** |
| a soft invented rim (σ=8) | **+0.0%** | 1.0000 | **+0.996** |
| **more noise** (a real regression) | **+76.6%** | 0.7537 | +0.001 |
| less noise (an improvement) | −51.0% | 1.0000 | +0.003 |
| smoothed (a blur) | −96.4% | −0.2559 | −0.165 |

An invented hard edge moves `hp_energy` by **+0.1%**. Raising the noise moves it
by **+76.6%**. So a flat-ROI `hp_energy` rise is nearly *blind* to the artefact
it was cited as evidence for, and is almost entirely a **noise** statistic —
energy goes as variance, so a +33% noise SD gives +77% energy.

The background noise rise of this fix was already measured and already
reported: **+8.9%** at v1, which predicts **+18.6%** energy against V-HALO's
observed **+16.8%**. That is a close enough match that I think the flat-crop
number is mostly the known noise regression, not invention.

**This does not exonerate v1 and I am not offering it as a defence.** My claim
was void because `hp_energy` cannot support *any* sharpness conclusion. The
same fact voids the counter-claim. And it changes nothing about the artefact
itself, because **V-HALO saw the invented edge in a picture**, and the standing
rule for this build is that the picture wins. What is wrong is only the number
that was offered alongside it — by both of us, in opposite directions.

### 13.3 The replacement statistics

`experiments/BUILD-HALO/fidelity.py`. No single column is a verdict.

- **seam-excluded `hp_energy`** — the fix can only change a pixel it treats, so
  injected structure lives at treatment boundaries. Measure energy *outside* a
  dilated boundary band. Blur still shows (blur is not confined to boundaries);
  injection is excluded by construction rather than by hoping it is small.
- **`hp_ncc`** — correlation of the two arms' high-pass bands. Blur removes
  detail from one arm; injection adds structure to one arm with no counterpart
  in the other. **Both push it down.** Two-sided on purpose.
- **`d_ac1`** — lag-1 spatial autocorrelation of the difference. This is the one
  that adjudicates, and the table above is why: noise is incoherent (≈0.00),
  invented structure is coherent (0.74–0.996). It separates the two things
  `hp_energy` and `hp_ncc` provably cannot.

### 13.4 The re-derived result

Three subjects, six arms, **all rendered back-to-back from one binary**
(`5C4D7351…`), 299 frames each, `--gate 4.0`, alignment solved, binned linear —
never `--srgb`. Frozen ROI plan, used as-is; `plan --force` never run.

Median by ROI class, `off` → `on` (v2):

| class | `hp_e` | **seam-excluded `hp_e`** | `hp_ncc` | `d_sd` (DN) | `d_ac1` | treated% |
|---|---|---|---|---|---|---|
| edge | +2.6% | **+0.3%** | 0.9531 | 77.2 | 0.826 | 14.98 |
| detail | +3.5% | **+0.0%** | 0.9694 | 217.9 | 0.808 | 6.63 |
| flat | +0.9% | **−0.0%** | 0.9825 | 54.9 | 0.836 | 4.53 |

**The "not a blur" claim, re-derived: outside the treatment boundaries the fix
moves high-frequency energy by +0.3% / +0.0% / −0.0%.** A blur would show there
and does not. This is the honest version of the claim, and unlike the v1
version it is made with an instrument that injected structure cannot satisfy.

**And the whole `hp_energy` rise is at the seams.** `bee-2-cpl edge3` is +99.2%
raw and +10.6% seam-excluded; `flower-inner-edge-cpl flat2` is +31.5% raw and
**−2.4%** seam-excluded. The energy was never detail.

**`d_ac1` is 0.6–0.9 wherever the fix does anything.** In *edge* and *detail*
ROIs that is expected and wanted — lifting a veil is a coherent change. In
**flat** ROIs it is the artefact, and it is real.

### 13.5 V-HALO's invented hard edge: confirmed, and measured

`experiments/BUILD-HALO/whatyousee.py` characterises the difference as
connected components against a visibility threshold set at 3× the *local* grain
of the untreated arm — local, because 200 DN is glaring in smooth background and
invisible in foliage.

`flower-inner-edge-cpl`, flat ROIs — regions the plan selected for having no
structure:

| roi | visible % | blobs | biggest | length | width | **elongation** | peak DN |
|---|---|---|---|---|---|---|---|
| flat1 | 1.21 | 13 | 956 px | 122.3 | 14.8 | **8.28** | 1309 |
| flat2 | 2.04 | 15 | 1241 px | 134.4 | 18.6 | **7.22** | 6451 |
| flat3 | 0.77 | 23 | 138 px | 20.1 | 9.8 | 2.05 | 2057 |

Long, thin, coherent, and clearing 3× the local grain. **That is V-HALO's
invented hard edge, and it is a line, not noise.**

**And its width is 15–19 px, which is `SOBEL_RADIUS + WINDOW_RADIUS`.** The
artefact I introduced has the width of my own support — the same signature as
the halo it was built to remove. §1's law applies to the fix as well as to the
defect. That is not a coincidence and it is not tunable: it is the coverage
boundary of a window-based treatment, which is the same wall as §10.3 and §11.

`bee-2-cpl flat2` shows the *other* artefact — 92 components, biggest 524 px,
elongation **1.28**, peak 14304 DN. Compact, not linear: the coverage blob.
Two different shapes, one cause.

`bee-2-cpl flat1` and `flat3` are clean (0.06% and 0.00% visible).

### 13.6 `lavendar-cpl`: the guards are firing. The subject has almost no edges.

ORCH asked me not to assume it simply has no halo. It does have one, and the
guards are not silently failing.

Firing: `lavendar-cpl` is treated at **7.25–12.41%** of pixels in its three edge
ROIs, with **0.21–1.07%** of pixels visibly changed. That is the same order as
`flower-inner-edge-cpl` (14.98–19.85% treated). **This is not the
partial-strength failure the `FEATHER` unit test was written to catch.**

What is different is the subject. The M121 edge detector finds, per frame:

| subject | bright edges | dark edges | **paired** |
|---|---|---|---|
| `bee-2-cpl` | 216 | 187 | **174** |
| `flower-inner-edge-cpl` | 118 | 119 | **103** |
| `lavendar-cpl` | 33 | 31 | **12** |

**`lavendar-cpl` has 12 paired occluding edges against 103 and 174.** There is
far less of the defect present to remove, which is why the effect is small.

Two of its three flat ROIs have a visibility threshold of **16.9 and 19.7 DN**
against 200–1000 DN everywhere else, and the fix moves them by **0.0 DN**.
Those ROIs are essentially grainless — near-black or fully smooth — so there is
nothing there to either fix or damage.

### 13.7 The halo, in M121's own units, before and after

Paired, same measurement path as M121 (`measure.py`, `C` = the contaminated
rim):

| subject | read | C peak off | C peak on | Δ | w50 off → on | cutoff off → on | n |
|---|---|---|---|---|---|---|---|
| `bee-2-cpl` | own | +0.1837 | +0.1652 | **−10.0%** | 14.75 → 14.25 | 20.75 → 19.50 | 174/149 |
| `flower-inner-edge-cpl` | own | +0.2075 | +0.1855 | **−10.6%** | 20.00 → 18.50 | 28.75 → 30.00 | 103/91 |
| `lavendar-cpl` | **donor** | +0.1877 | +0.1924 | **+2.5%** | 13.75 → 13.50 | 30.00 → 30.00 | 12 |

For `lavendar-cpl` the **donor** read is the one to believe: it re-measures the
*same 12 edges* in both arms. Its `own` read shows +31.9%, but that re-detects
edges independently per arm (12 vs 11 survive), so it compares different edge
sets — and the bootstrap CIs, `[−0.033, +0.370]` against `[+0.020, +0.405]`,
overlap almost completely. **`lavendar-cpl` is unchanged**, which is exactly
what V-HALO said.

**A caveat I cannot resolve and will not paper over:** the donor read returned
`nan` for C on `bee-2-cpl` and `flower-inner-edge-cpl`, because the donor edges
re-measured in the treated arm have a 10–90 rise `p90` of 18.50 and 26.20 px
against 4.55 and 5.50 in the untreated arm, which pushes the C read start
beyond the profile. Median rise is unchanged (3.25 → 3.50), so the *typical*
edge is not softened — but roughly a tenth of donor edges are behaving very
differently under treatment. That could be genuine dislocation at treatment
boundaries or a failure of the profile recentring. **I have not determined
which, and the −10.0% / −10.6% figures above should be read as the `own`-read
numbers they are.** This is the first thing a verifier should attack.

### 13.8 Where this leaves the deliverable

**Still not print-worthy, and by a wide margin.**

- The rim amplitude falls about **10%** on the two subjects where it moves, and
  **not at all** on the third. `w50` falls 0.5–1.5 px out of 14.75–20.
- The fix is **not a blur** — that claim is now re-derived on an instrument the
  artefact cannot feed (+0.3% / +0.0% / −0.0% seam-excluded).
- It has introduced **a new visible artefact in smooth background**: line-like
  on `flower-inner-edge-cpl` (elongation 7–8, up to 6451 DN), blob-like on
  `bee-2-cpl` (elongation 1.28, up to 14304 DN). On a print that is worse than
  the veil it replaces, because a viewer forgives softness and does not forgive
  structure that is not in the subject.
- **The new artefact is 15–19 px wide, which is the support radius.** The fix
  is subject to the same law as the defect. No masking or feathering escapes
  it, because the boundary of a window-based treatment is a window-wide object.

That is the third independent arrival at the same wall (§10.3, §11, and now
§13.5): **near a silhouette there is not enough background inside the window to
select from, so it must be reconstructed.** §11's detector establishes the
information is present. Two-layer unmixing is the remaining route and I have
not built it.

### 13.9 I did not look at the pictures, and I must say so

The instruction for this build is to judge on pictures. **I cannot render an
image into my own eyes in this environment**, and I am not going to claim
otherwise — a claim with no instrument under it is the exact failure this
project keeps catching.

So §13.5 and §13.6 are a *description*, in numbers a human can check against
the file, of the things a human would be looking for: how much of the ROI
changed visibly against local grain, whether the change is a line or a blob,
how long and how wide, how suddenly it arrives, and how bright it peaks. That
is the most look-like instrument I could build. **It is not a substitute for
the owner or a verifier opening the files**, and the invented-edge finding in
particular should be confirmed by eye before it is acted on.

The 16-bit panels are at `C:\dev\strehl-out\v2-crops\` as
`<subject>-crop<N>-y<Y>-x<X>-before-after-diff3x.tif` — `before | after | 3×
signed difference`, 384 px tall, at the frozen ROI centres. 8-bit viewable
versions are under `C:\dev\strehl-out\v2-crops\view\`; **those are
sRGB-encoded for looking at only, and nothing in this report was measured on
them.**

The ones to open first:

- `flower-inner-edge-cpl-crop7-y949-x959-*` — flat2, the invented line.
- `bee-2-cpl-crop7-y929-x842-*` — flat2, the coverage blobs.
- `lavendar-cpl-crop0-y499-x995-*` — edge1, where least happens.

---

## 14. The mandate: full-frame, default-on, and what the pictures said

Everything in this section was judged on **clean full-frame renders at ~1400 px
wide**, not on crops at frozen ROIs. That change of instrument is the reason
this section reaches different conclusions from the ones before it.

### 14.0 Two defects that made this build blind

**The fix was never on.** It sat behind `STREHL_EDGE_AWARE`, default OFF, from
the day it was built. Every render anyone looked at -- including every render
the owner judged -- was the untreated arm. It was measured, committed, reported,
and never once applied to a picture. It is now **default ON**; the variable
selects an arm (`off` / `acuity` / `layer`) for A/B only.

**The previews were not viewable.** Earlier scripts wrote 8-bit output with
`tifffile.imwrite()` to paths ending in `.png`. `tifffile` ignores the
extension, so every "PNG" this build produced was a TIFF with a PNG's name --
magic bytes `49 49 2A 00`, not `89 50 4E 47`. No ordinary viewer would open
them. `fullframe.py` writes real PNGs and **asserts the magic bytes**, because
a deliverable nobody can open is not a deliverable.

### 14.1 Mandate (A): the direction was right, the mechanism was not

(A) asked for a per-pixel radius `min(r_noise, r_geom)`, with `r_noise` the
smallest radius whose through-focus peak clears the calibrated noise floor.
Built, then rendered against `r_geom` alone as the only difference -- three arms
of `bee-2-cpl` back-to-back from **one** binary.

| `bee-2-cpl` background sd | shipped | `min(r_noise, r_geom)` | `r_geom` only |
| --- | --- | --- | --- |
| flat patch A | 1.000 | 0.986 | **0.878** |
| flat patch B | 1.000 | 1.070 | **1.005** |
| flat patch C | 1.000 | **1.187** | 0.996 |

The noise term costs up to **+18.7% background noise for no visible gain** --
at 1:1 the two treated arms' halos are indistinguishable. The cause is
structural, so no margin would have fixed it: contamination needs a window
spanning two depths, which happens only near a silhouette, and there the
geometric cap already binds. Everywhere else the shrink trades noise for
nothing.

**The window size IS the halo radius** (confirmed). **Shrinking it everywhere
is not the fix** (refuted). Refusing to let it cross a silhouette is.

### 14.2 What was deleted

`ACUITY_MARGIN`, `STREHL_ACUITY_MARGIN`, `acuity_margin()`, the `excess` and
`margin` parameters, and the confidence veto (`FLOOR_Q`, `conf`) which this path
never needed. `from_acuity` became `from_silhouettes`, whose signature has
nowhere to put a signal term. Deleted rather than tuned to zero: a constant that
must be zero is a disabled feature waiting for someone to read its name instead
of its measurement.

The replacement test asserts **monotonicity of radius in distance from the
step** rather than a number. Distance is monotone as you walk away from a step;
signal strength is not. Any term that reads the image rather than the guide
breaks the walk.

### 14.3 What the pictures show

`bee-2-cpl`: the broad bright aura tracing the whole silhouette -- the thing the
owner saw first -- is **gone** at full-frame scale. A **tight bright sheath**
still hugs the claws and the lower-left leg, and it is still faintly visible at
1400 px. Not yet the bar.

`flower-inner-edge-cpl`: the milky veil along the petal/stamen boundary has
lifted, stamens separate cleanly from the petal, greens are deeper. **No rim
visible** on this subject.

### 14.4 Mandate (B): the detector fails its own gate. STOPPED.

The instruction was explicit: produce the firing overlay first, and if it does
not land on the rim, **stop and report -- do not force it**. It does not.

The per-band table looks like a green light, and it is not:

| radius | % of plane | fires | | radius | % of plane | fires |
| --- | --- | --- | --- | --- | --- | --- |
| r1 | 25.03% | **99.80%** | | r1 | 3.49% | 98.18% |
| r2 | 6.30% | 91.96% | | r2 | 4.32% | 88.18% |
| r4 | 7.07% | 62.08% | | r4 | 10.15% | 61.61% |
| r8 | 7.81% | 41.44% | | r8 | 13.00% | 41.54% |
| r13 | 53.78% | **13.42%** | | r13 | 69.05% | 15.59% |

(`bee-2-cpl` left, `flower-inner-edge-cpl` right.) Monotone in both, 7.4x
enrichment, and **wrong**. The full-frame overlay shows it firing on **45.62%
of the plane, including the entire empty background**. On flat ground far from
any silhouette: **54-87% firing**, mean `z1` 3.32-4.39.

The mechanism is a shared cause, not specificity. Over featureless ground no
frame is in focus, so the guide's argmax is noise, its local range is ~N frames,
the range test reads a depth step, **and** the mode statistics are noise with a
tiny sigma that both z-scores clear. Radius collapse and bimodality firing are
both driven by an unreliable guide over dead ground, so they correlate
beautifully without either one locating a silhouette.

This is the **same defect as the first `r2/r1` detector** (fired on 54.2% of
clean ground) in a different dress. The z-score fixed the normalisation and did
not fix the specificity.

Gating unmixing on this would apply a two-layer model to half the image
including flat background -- inventing structure in exactly the no-structure
regions V-HALO already flagged. **Not built. Reported instead.**

### 14.5 The honest defect in the shipped rule

`from_silhouettes` over-collapses over dead ground: mean radius **3.64-5.86**
where it should be 13, **45-61%** at r1, on background far from any silhouette.
It is harmless to the image -- where no frame has content, every frame renders
the pixel alike, which the noise table above confirms -- and that is why it
ships. It is **not** harmless to inference, and it cost this build the wrong
conclusion in 14.4. **The radius map is not a rim mask.**

### 14.6 Method

Pinned `git archive` of an explicit SHA, built in isolation, **commissioned with
a planted sabotage** before being trusted: breaking the geometric cap failed
exactly `the_window_collapses_at_a_silhouette...` and nothing else; breaking the
guided filter's edge term failed exactly
`domain_transform_does_not_carry_focus_across_a_luma_step` while the flat-region
smoothing test still passed. Every arm rendered back-to-back from one binary.

---

## 15. Two mechanisms? Neither. The wide aura is not ours.

ORCH looked at a full frame of `lavendar-cpl`, saw an aura far wider than
`SOBEL_RADIUS + WINDOW_RADIUS` could explain, and proposed a second mechanism:
defocus spill from the near subject veiling the backdrop over the blur radius,
present in every frame and therefore unfixable by any selector. The proposed
consequence was that two-layer unmixing was promoted from optional to
mandatory. The test was: measure the aura's radial extent and compare it
against (a) `SOBEL + WINDOW` and (b) the defocus blur diameter.

**It matches neither, because the wide feature is not produced by the merge at
all.** ORCH's observation was right and the attribution was wrong.

### 15.1 The measurement needs no PSF model

Mechanism (i) has a **hard ceiling**. The focus measure is a box mean of radius
`WINDOW_RADIUS` over a gradient of radius `SOBEL_RADIUS`, so a pixel further
than their sum from a depth edge has *no* foreground content in its window --
not weakly, not attenuated, none. Window contamination cannot reach past 14 px.

So the only thing needed is a reference with no election in it. `STREHL_ONLY_FRAME`
renders one frame of the bracket; one frame is trivially its own winner at
every pixel. An aura present there is optics and no selector can remove it; an
aura in the merge and absent from every frame is entirely ours.

Four arms per subject -- `off`, `on`, `frame000`, `frame298` -- all rendered
back-to-back from one pinned binary (`0BB7BCDD4A58`, `git archive` of an
explicit SHA, commissioned with a planted sabotage that went red), all four
byte-distinct.

### 15.2 The answer, from a raw line cut with no segmentation

Across `lavendar-cpl` rows 800 and 1150, from open backdrop into the left
silhouette:

| x, native | 150 | 300 | 450 | 600 | 655 (silhouette) |
| --- | --- | --- | --- | --- | --- |
| `off` | 1.000 | 1.006 | 1.024 | 1.038 | steps to 0.85 |
| `on` | 1.000 | 1.006 | 1.025 | 1.040 | steps to 0.85 |
| `frame000` (no election) | 1.000 | 1.005 | 1.022 | 1.035 | declines smoothly |
| `frame298` (no election) | 1.000 | 1.007 | 1.026 | 1.042 | stays ~1.02 |

The backdrop brightens ~4% over ~470 px approaching the subject, and **all four
arms are superimposed within noise over that entire span** -- including two
arms that contain no election whatsoever. A feature identical in a single
exposure and in the merge is not something the merge did. It is the scene's own
illumination field (and/or lens veiling glare), and it is ~34x the mechanism
(i) ceiling because it is not an artefact of any kind.

The merged arms depart from the single frames **only within ~10-20 px of the
silhouette**, which is the mechanism (i) zone and nowhere else.

### 15.3 What this kills

**Do not build two-layer unmixing to chase the wide aura.** There is nothing
there to unmix. Fitting `I_k = a(F conv PSF_k) + (1-a)(B conv PSF_k)` to that
region and "removing the foreground's contribution" would be *editing the
scene's real illumination gradient out of the photograph* -- inventing a
change, in the smooth regions where V-HALO has already caught this build
inventing structure once.

This is the second gate in a row that the pictures failed after the summary
statistics passed. Section 14.4's bimodality table was monotone and beautiful
and wrong; this one had a plausible mechanism, a named prediction and an
authoritative source, and the raw line cut refuted it in one plot.

### 15.4 The instrument failed twice first, silently, and both were caught by drawing it

The radial profile needs a silhouette, and segmentation is where this nearly
went wrong:

1. Threshold at a multiple of the backdrop spread, pooled over four corners.
   The frame has an illumination gradient, so the pooled spread measured the
   difference *between* corners (3377 DN) rather than noise within one. The
   threshold landed outside the data range: **0.00% of the plane selected.**
   Loud, caught immediately.
2. Otsu on luma. **Reported a plausible 39-49% and was garbage:** the backdrop
   gradient exceeds the subject-to-backdrop step in places, so Otsu split *the
   backdrop's own gradient* and labelled the entire right half of the empty
   background as subject. Drawing the contour showed it running through open
   sky.

Failure 2 is the dangerous one, and nothing but `maskcheck.py` -- which draws
the boundary on the picture -- would have caught it. Brightness cannot separate
these classes because the illumination gradient is confounded with them.
**Local standard deviation can,** and it is invariant to any additive
low-frequency field, which is precisely the thing that broke both attempts. It
also fails in the right direction: the halo is a smooth glow with no texture,
so it lands on the backdrop side, which is what makes "distance 0" the
silhouette rather than the outer edge of the thing being measured.

### 15.5 Per-channel election: refuted as posed, but there is a real per-plane path

The winner field is computed on a **single luma plane** -- green-only,
`L = (G1+G2)/2` -- so R, G and B cannot elect different frames. The gate's
`continue` is at *pixel* scope, above the plane loop, so the admitted frame set
and the weight `wt` are per-pixel scalars shared by all four CFA planes. R/G/B
diverging by differential selection is **structurally impossible**.

One real per-plane path survives, and it lands exactly where the fringing was
seen. `Estimator::value` substitutes `CONTAINER_MAX_DN` verbatim for a plane
whose *winner's own sample* was pinned, while sibling planes return their
weighted means -- so at a pixel where one plane clips and its siblings do not,
the three channels come from different estimators and the colour exists in no
frame. It activates only on the `fold_censored` path, which ships, and only at
clipped samples: specular highlights and bright fine hairs.

**Not changed.** It is M109's deliberate highlight design, it is outside this
mandate, and its own doc already flags that the post-warp clip test under-counts
"which is where the residual fringe lives". Routed to ORCH rather than touched.


## 16. The paired subject, and the defect it exposed in my own fix

ORCH sent a paired-subject test: `flower-bud-with-background-fern-cpl` has a
hard, tight, crisp cut-out rim; `lavendar-cpl` has a soft, wide, diffuse glow.
Prediction: flower-bud matches `SOBEL_RADIUS + WINDOW_RADIUS`, lavender matches
the defocus blur diameter. Built-in control: **(A) should materially change
flower-bud and barely touch lavender.**

I agree with the visual classification completely. The fern reads as a sticker
pasted onto the backdrop, with a crisp inner *and* outer boundary. Lavender's
glow has no boundary at all.

The attribution still fails, for the reason in section 15: lavender's glow is
present, identically and within noise, in single frames rendered with no
election whatsoever. It is the scene's illumination, not a mechanism.

### 16.1 The control fires, and it fires against my fix

| subject | rim (<=14 px) | far (>150 px) | ratio |
|---|---|---|---|
| `flower-bud-with-background-fern-cpl` | 0.748 | 0.784 | 0.95 |
| `lavendar-cpl` | 0.582 | 0.538 | 1.08 |
| `bee-2-cpl` | 0.166 | 0.184 | 0.90 |

Mean `|off - on|` in backdrop sd, after a 9 px box on **both** arms.

By ORCH's own stated criterion this is a failure: the change is not confined to
the window on any subject. Far backdrop is more than ten window-radii from any
silhouette, where the focus window provably cannot reach, and it moves as much
as the rim does.

**The smoothing is what makes it readable, and I nearly missed it.** My first
run was raw per-pixel `|off - on|` and read 0.777 / 0.631 / 0.197 with the same
~1 ratios. I called that a noise re-roll -- electing a different but
statistically equivalent frame changes every pixel without changing the picture
-- and cited the background sd ratios (0.878 / 1.005 / 0.996) as proof the noise
level was unchanged. That reasoning was sound and the conclusion was wrong. A
9 px box removes uncorrelated noise by about 9x; the numbers barely moved. It is
a **systematic level shift over the whole backdrop**.

This is the third time in this build a difference statistic has produced a
confident wrong reading, after `edge_overshoot` and `hp_energy`. The pattern is
always the same: the statistic is satisfied by something that is not the defect.

### 16.2 It is visible, which settles it

`ff-flower-bud-with-background-fern-cpl-on.png`, full frame: the fern still has
its hard white outline, **and its interior is now blotchy**, with white patches
smeared inside the leaf.

ORCH asked me to confirm rather than assume that the fern's plastic look is
because it sits outside the focus bracket. Under that reading the two findings
are one finding. Outside the bracket, no frame has the fern in focus, so the
narrow guide's argmax there is noise spanning the whole bracket, its local range
reads as a depth step everywhere, the radius collapses across the fern's whole
area, and the election goes per-pixel random. Dead ground *inside a subject*.

### 16.3 Retraction

`from_silhouettes` shipped with a doc comment stating the over-collapse was
"**harmless to the image**", on the grounds that where no frame has content
every frame renders the pixel almost identically. **That claim is retracted.**
It was supported by a noise measurement, and noise was the one thing it did not
damage.

### 16.4 The veto, and why it is not the one I deleted

`from_guide` needed a confidence veto with a tuned `FLOOR_Q`, and I deleted it
along with `from_guide`. I was right that a mask cannot create information and
wrong that no veto was needed.

This veto tests a **second, independent signal**: a depth step in a photograph
is accompanied by a luma step. A pixel may cap at a radius only where the guide
range exceeds `tau` **and** the luma range at that same radius exceeds what pure
noise would reach there.

The luma threshold is not tuned. It is the closed-form expected range of `n`
Gaussian samples, `2*sigma*sqrt(2*ln n)`, with `sigma` measured from the plane's
own adjacent-pixel differences via the MAD -- robust, because real structure is
a minority of adjacent pairs and would inflate a standard deviation. Given
`sigma` each radius has one right answer, and it grows with the box exactly as
the spurious range over dead ground does. **No new constant enters the build.**

Featureless backdrop is smooth in luma and is vetoed. The fern's interior is
smooth in luma and is vetoed. A real occluding edge steps in both and is not.

### 16.5 Asserted as behaviour, not as a number

`a_guide_step_without_a_luma_step_is_dead_ground_and_must_not_collapse` gives two
fixtures an **identical** guide step and differs only in the luma. One must
collapse; the other must not.

It has to be a behaviour test. The old failure was invisible to every metric in
use -- background noise unchanged or better, halo numbers fine -- while the rule
rewrote the entire background. A numeric assertion would have passed.

The featureless fixture is dithered by +/-1 DN rather than left constant. A
constant plane makes `sigma` zero, which passes the veto for a degenerate reason
instead of the one under test.

### 16.6 A commissioning trap worth recording

Commissioning the pin caught the sabotage (RED, rc=101) and then reported the
**restore** as failing with a byte-identical histogram to the sabotage.

That is not a restore failure. `shutil.copy2` preserves the backup's mtime,
which is the original's -- older than the artifacts the sabotaged build just
wrote. Cargo compares mtimes and reused the sabotaged object. An `os.utime` after
the restore fixes it.

The direction of the failure is the lucky one: it made a good restore look bad.
Reversed -- a sabotage that failed to trigger a rebuild -- it would have printed
a confident GREEN for a pin that never compiled the defect at all.


### 16.7 The veto is active, and it does not work. Two reasons, both mine.

Rendered from pin `1fbf95c` (`git archive` of the SHA, commissioned with a
planted sabotage that went RED rc=101). Controls: the `on` arm changed
(`779ABB028E55` -> `DC995B3603B8`) so the veto is live, and the `off` arm is
**byte-identical across both pins** (`6C9A92A82DF5`), which is the untouched
path agreeing bit-for-bit and confirms the two pins are otherwise equivalent.

The control, re-measured after the veto:

| subject | far, before | far, after |
|---|---|---|
| `flower-bud-with-background-fern-cpl` | 0.784 | 0.777 |
| `lavendar-cpl` | 0.538 | 0.494 |
| `bee-2-cpl` | 0.184 | 0.183 |

Ratios still 0.94 / 1.02 / 0.89. And the picture is unchanged: the fern still
has its hard white outline and its blotchy interior.

**Reason one: the threshold passes half of dead ground by construction.**
`2*sigma*sqrt(2*ln n)` is the *expected* range of `n` Gaussian samples -- near
the median of the range distribution. So pure noise exceeds it about half the
time. As a veto that is close to useless, and no amount of correctness in the
derivation rescues a quantity chosen at the wrong point of its own
distribution. A veto needs an upper tail, not a mean. The honest version has to
control the false-pass rate across all `N` pixels of the plane, not the `n`
samples of one box.

**Reason two, and the deeper one: luma contrast is not focus signal.** The fern
is a dark object on a bright field. It has enormous luma range in *every* frame,
including all the frames in which it is hopelessly defocused. A dark blob
against white is still a large luma step. So the veto passes exactly where it
was built to refuse.

That kills the premise, not just the constant. "A depth step is accompanied by a
luma step" is true, but the converse is what a veto actually needs and it is
false: a luma step is not evidence that anything here is in focus.

**The right quantity is already in hand and I walked past it.** The call site
holds `guide_resp`, the peak through-focus response per pixel, returned
alongside the guide by `guide_winner_field`. Over the fern that response is flat
-- no frame is sharp -- and that is precisely the `starved` state this engine
already claims to detect and report. Testing the peak response against the
calibrated noise floor asks the question the veto is for: *is there focus
information at this pixel at all?*

That is a confidence veto, which is the thing I deleted with `from_guide`. I was
right that it could not be `from_guide`'s -- a tuned `FLOOR_Q` quantile is not a
measurement -- and wrong that none was needed. The difference now is that the
threshold comes from `FOCUS_NOISE_SD`, which is calibrated, and that there is
direct evidence of the failure it prevents rather than an assumption.

**None of this touches the deliverable.** All of section 16 is about the
backdrop level shift and the fern. The bee's tight bright sheath -- the leg, the
free claws, the antenna, the wing tips -- is the thing that disqualifies the
print, and it is unchanged by every arm here. The broad aura is gone; the sheath
is not, and I can see it without looking for it.


## 17. The texture guard rejects the fix

ORCH made `couch-fibers-cpl` a required do-no-harm guard: a pure-texture subject,
dense fibres filling the frame, **no depth silhouettes anywhere**, currently good.
If it gets worse the change is rejected regardless of what it does to the halo.

Rendered `off` and `on` back-to-back from pin `1fbf95c`, judged at **100%** --
identical crop origin (1310, 722), identical display gain 4.0318, and the two
arms share a pixel grid, so this is a fair paired look.

**It gets worse.** The `on` arm is softer: adjacent filaments are less separated,
the specular glints along the fibres are duller, and micro-contrast is down
across the crop. It is not subtle once the two are seen side by side, and it is
invisible in the 1400 px full frame, because downsampling is a low-pass filter
and this is a high-frequency loss.

**The change is rejected on this evidence.** No halo result outweighs it.

### 17.1 Why it fails there, and why that unifies the whole section

`couch-fibers-cpl` is a subject where **every pixel is a depth step**: a tangle of
fibres at many depths, interleaved at pixel scale. So `from_silhouettes` finds a
step nearly everywhere and collapses the radius nearly everywhere -- and a 1 px
focus measure on a noisy texture is a bad estimator. The winner field goes noisy
at fine scale, the election is wrong at fine scale, and the result is mush.

That is exactly the failure ORCH predicted for this guard ("an adaptive window
that shrinks too far"), and it is the **same root cause as section 16**, seen
from the opposite side:

- over **dead ground** the radius collapses because the guide is noise;
- over **dense texture** it collapses because there genuinely are steps
  everywhere;
- in both cases collapsing **buys nothing** and costs the estimator.

So the rule is not "collapse where the guide varies". It has to be **collapse
only where collapsing buys something** -- at a genuine occluding boundary, where
a large window would straddle two depths that are actually separated. Local guide
variation does not distinguish that case from either failure above, and every
veto attempted so far has been an attempt to patch that one deficiency from
outside.

### 17.2 What this retracts, and what it does not

Section 16.2 attributed the fern's blotchy interior to the dead-ground collapse.
**Partly wrong.** Comparing the arms full-frame, the fern renders blotchy in the
`off` arm too -- shipped baseline, no adaptive radius at all -- so the blotches
are mostly the out-of-bracket fern itself, not something this rule did. That also
answers ORCH's standing question about the fern: it is not the merge destroying
texture, it is a subject with no sharp frame anywhere in the bracket.

The **cut-out sticker outline is likewise present in the `off` arm**, and there
it is *thicker* and carries a dark band outside it that the `on` arm reduces. So
the sticker edge is not the radius quantisation either, and the adaptive window
does help the rim -- just not nearly enough, and now at a price this guard says
is too high.

What section 16 still establishes stands: the control ratios of ~1, the
retraction of "harmless to the image", and the two reasons the luma veto fails.


## 18. `through_focus.rs` is the seam, and it already contains the fix I failed to build

ORCH assigned ownership of `crates/strehl-core/src/through_focus.rs` to this
workstream, with BUILD-SHARP consuming it read-only. Reading it first was the
right instruction: it already carries `bimodality`, `bimodality_sigma`,
`far_index`, `posterior_perplexity`, `at_bracket_boundary`, `PEAK_SEPARATION`
and a calibrated `FINE_FOCUS_NOISE_SD`. Nothing below needs a new constant.

### 18.1 I had the polarity backwards, and that is why the detector failed

`bimodality` is documented as **an upper bound, not an estimate** -- it is
`far_max - floor`, where true prominence would subtract the curve's minimum
*between* the peaks, so it can only read high. The doc states the consequence
exactly:

> Its complement is what is trustworthy: a small value **proves** there is no
> separated secondary peak of that size.

My `(B)` gate used it in the **untrustworthy** direction: *collapse where
bimodal*. An upper bound used as a positive detector fires on everything that
could possibly be bimodal, which is why it read 45.62% of the plane including
empty background. That was not a tuning failure, it was a misuse of a
one-directional statistic, and no threshold would have fixed it.

Section 17 independently concluded the rule must be **"collapse only where
collapsing buys something"** -- which is a *veto*, and a veto needs precisely the
direction this statistic can prove. The two findings meet.

### 18.2 The rule

Collapse the selection radius at pixel `i` only where all three hold:

1. **`hi[i] - lo[i] > tau`** -- the existing geometric test. Necessary, not
   sufficient: it locates candidate boundaries and is what over-fires today.
2. **`bimodality_sigma(i)` does not prove unimodality** -- the new veto, in the
   statistic's trustworthy direction. Where it is small there is provably no
   separated second layer, so there is nothing for a small window to separate
   and collapsing only costs the estimator.
3. **not `at_bracket_boundary(i)`** -- no frame in focus, so no depth to resolve.

Predicted behaviour on the three subjects that currently break the rule:

| subject | posterior | rule 2 | outcome |
|---|---|---|---|
| `couch-fibers-cpl` | one fibre, one depth per pixel: single peak | proves unimodal | **vetoed, radius stays 13, texture preserved** |
| dead backdrop | response is noise; the difference is noise-sized in sigma units | proves unimodal | **vetoed, no level shift** |
| the fern | flat, no sharp frame anywhere | rule 3 | **vetoed** |
| a true rim | two genuinely separated layers | does not prove unimodal | **collapse allowed** |

Dense texture is the interesting case and the one that makes this more than a
patch. A tangle of fibres varies in depth *between* pixels, so the guide range
test fires, but **within** a pixel's own through-focus curve there is one depth
and one peak. The guide range cannot tell that from an occlusion; the posterior
shape can. That is the discrimination sections 16 and 17 both concluded was
missing.

### 18.3 Wiring, and the one real obstacle

The two-pass structure ORCH mandated largely exists: `merge_cmd.rs:2915` already
builds `ThroughFocus::new(&p1.stats)` and there is already a gather pass, both
gated on `opts.stats`.

**The obstacle is ordering, and it is the whole cost of this change.** Today:

    guide pass -> SelectionScale -> pass 1 -> ThroughFocus(p1.stats)

but the rule needs the posterior *before* the scale exists:

    guide pass -> ThroughFocus(guide stats) -> SelectionScale -> pass 1

So `guide_winner_field` has to fold a `ThroughFocus` and return it, alongside the
winner field it already returns. It folds `FocusStats` per chunk and absorbs
across chunks, and `ThroughFocus` already has `absorb`, so the shape matches; the
work is threading the fine and regularised fields into the fold and widening the
return. This is bounded per-pixel statistics, not retained frames, so the
never-materialise discipline holds.

Note the guide is deliberately NARROW (`GUIDE_RADIUS = 4`), which is the right
scale here for the same reason the existing detector uses the fine field: a 13 px
window smears the foreground and background modes into one peak, destroying the
signal being tested for.

### 18.4 A warning in the source that binds this

`bimodality_sigma`'s doc records that a **global** mean against a
frame-permutation null cannot detect occlusion -- permutation manufactures
multi-peakedness and saturates the comparison, so the ratio is pinned below 1
whatever the scene does. M18 concluded "no bimodality enrichment" from a 0.86x
global ratio where M21, conditioned on an independent depth-step map, measures
**4.38x** against a null of 1.01x.

So this must never be reported as a plane-wide fraction. It is binned on an
independent depth-step map or it is not reported. That is also the error that
made my `(B)` per-band table look monotone and beautiful while the overlay showed
it firing on empty background.

## 19. The acceptance measurement, for any merge

ORCH has opened a second arm (BUILD-BLEND, a Laplacian-pyramid multi-band
merge) on a different representation. This section exists so that both arms are
judged by the same yardstick and neither of us grades our own homework. It is
written to be run by someone who did not build either fix.

Nothing here is specific to the selection representation. It measures **a merged
image**, whatever produced it.

### 19.1 What is being accepted, and what is explicitly NOT the artefact

The occluding-edge artefact has two features that were confused with each other
for most of this build, and only one of them is ours.

| feature | extent | is it ours? | evidence |
|---|---|---|---|
| the **rim** | ~10-20 px, the window zone | **yes** | the merge departs from every single frame there |
| the **wide aura** | 400+ px, ~4% rise | **no, it is the scene** | present identically in renders with no election in them |

The aura is the subject's own illumination field. `off`, `on`, `frame000` and
`frame298` superimpose within noise across 470 px and all rise by the same ~4%
(section 15); two of those arms contain no election at all, and **a feature
identical in a single exposure and in the merge cannot have been produced by the
merge**. ORCH's independent attempt corroborates the number from the other
direction: his radial profile died on a background gradient of ~10 DN over
100 px against a base of ~220 DN, which is ~4.5% over the same distance scale,
on a different subject, measured a different way. His confound was this
illumination field.

**Therefore: a merge that removes the wide aura has FAILED, not passed.** It has
edited the photograph's real lighting. Any acceptance metric that rewards
flatness far from the silhouette is disqualified, and that includes fitting and
subtracting a smooth background. This is the single most expensive thing this
build learned and it cost three retracted hypotheses, two of them mine.

### 19.2 The reference is a single frame, not another merge

`STREHL_ONLY_FRAME=k` renders one frame with **no election at all**. It is the
reference a merge-versus-merge comparison structurally cannot provide: two
merges differ only in what their selectors did, so neither can tell you what the
right answer was. A single frame contains the optics, the illumination field and
the noise, and contains no selection artefact by construction.

Choose `k` from **data, not intuition**: dump the winner field with
`STREHL_DUMP_ELECTION`, and take the median election of the far background. That
is the background-focused frame by the engine's own reckoning. On
`flower-bud-with-background-fern-cpl` it is frame 221 and on `lavendar-cpl` it is
frame 247; a guessed `k` silently changes the reference level and every number
downstream.

### 19.3 The halo measurement

Run `experiments/BUILD-HALO/trade_measure.py`. In full, so it can be rebuilt if
that file is lost:

1. **Silhouette from depth, frozen.** Segment the subject on *depth coherence*
   in the election map (`depth_profile.depth_mask`): dead ground elects noise
   spanning the bracket, a real object elects coherently. Two luminance
   thresholds failed on these subjects before this worked -- a white flower on
   mid grey defeats a global threshold, and a median-over-focus image is smeared
   by the very defocus under study.
   **Compute it once, from the `off` arm, and freeze it across every arm.**
   Recomputing per arm lets a fix move its own goalposts: a stronger collapse
   changes the winner field, which changes the silhouette, which changes which
   pixels get measured.
2. **Distance transform on `~mask`.** `distance_transform_edt` returns 0 *inside*
   a mask, so without the complement the first band swallows the entire subject
   and reports the subject's own brightness as background. That produced a
   3.9 M-pixel first band here before it was caught.
3. **Near band `1 <= d < 20 px`**, background side only. This is the window zone
   from 19.1, not a tuned choice.
4. **Far reference `d > 300 px`.**
5. **halo = median(merge - frame_k)[near] - median(merge - frame_k)[far]**, in DN
   of 65535.

The far referencing is not optional and it is not cosmetic. It cancels two
things at once: the global exposure offset between any two renders, which is
-1400 to +1800 DN here and roughly an order of magnitude larger than the
artefact being looked for; and the illumination field of 19.1, which is common
to the merge and the frame. An unreferenced radial profile cannot separate a
few-DN artefact from a 10-DN scene gradient, which is exactly how ORCH's
verification of his own hypothesis came back ambiguous.

**Report the signed value.** Its sign is diagnostic -- it flips with scene
polarity -- and an absolute value throws that away.

### 19.4 The texture guard, which is a placebo and not a metric

`couch-fibers-cpl` **has no depth silhouettes**. There is nothing there for an
edge-aware or depth-aware merge to treat, so the correct behaviour is a no-op
and the guard needs no threshold and no interpretation:

- **`rms dev`** and **`p99.9`**: deviation from the `off` arm, in DN. Any
  deviation at all is damage.
- **`px moved`**: fraction of pixels that moved by more than 0.5 DN.
- **`SD ratio`**: median local standard deviation (3 px) over textured pixels,
  arm divided by `off`. Below 1 is softer.

The first three cannot be gamed, because zero is the target and any change in
either direction counts against. The `SD ratio` is a high-frequency statistic
and therefore *is* gameable by injected structure -- read it **only for its
direction**, and only next to the deviation numbers. It is there to say whether
damage is softening or sharpening, not to say whether there is damage.

This guard is genuinely double-edged. It rejected this lane's own fix at
`859edac` (section 17), which is why it is trustworthy enough to hand to another
arm.

### 19.5 Instruments that are banned here, each because it failed here

| banned | why |
|---|---|
| gradient / high-pass energy as a **halo** score | satisfied by injected structure; it has already fooled two agents on this exact artefact |
| merge-versus-merge comparison | cannot see what a selector should have done; only a no-election reference can |
| unreferenced radial profile | cannot separate the artefact from the illumination field of 19.1 |
| a **luminance** silhouette | failed twice; once it put the "background" annulus on the subject and manufactured a 596,000x anisotropy that read exactly like a directional shadow |
| a plane-wide bimodality fraction | a global mean against a permutation null is pinned below 1 whatever the scene does; bin it on an independent depth-step map or do not report it |
| `--srgb` renders | the transfer curve moves every ratio a metric computes. Measure on `--linear-srgb` |
| judging severity from `baseline-full\lavendar-cpl.png` | that file has debug ROI overlays burned into it |

Two of those were caught only by **drawing the mask and looking at it**
(section 15.4). Any new segmentation gets an overlay PNG before its numbers are
believed.

### 19.6 Pass criteria

An arm passes when all four hold, measured back to back from one commissioned
binary:

1. **Halo.** `|halo|` on `flower-bud-with-background-fern-cpl` is within the
   noise of the near band. Anything short of that is reported as a percentage of
   the `off` arm and is a *reduction*, not a pass.
2. **Aura preserved.** The far-field profile beyond 100 px still matches the
   single-frame reference to within noise. A flattened aura is a failure
   (19.1).
3. **Texture guard.** `couch-fibers-cpl` deviation from `off` is at or near
   zero, and `SD ratio` is not below 1.
4. **The picture.** A full-frame developed PNG at ~1400 px of `bee-2-cpl` and
   `flower-inner-edge-cpl` in which the owner cannot see a rim.

**Criterion 4 outranks 1-3 and is the actual deliverable.** Every scalar in this
section exists to make 4 diagnosable when it fails, and to stop an arm claiming
a win the pictures do not show. This lane has already published a sharpness
claim it had not looked at (section 13.9); the numbers are the servant here.

### 19.7 The knob has to be commissioned, not just the binary

A dose-response is worthless if the dose is not connected. If the strength
parameter were ignored, every arm would come back byte-identical and a flat
trade curve would read as "there is no trade" rather than "the knob is dead".
`trade_ladder.ps1` therefore hashes every arm and reports the distinct count.

On `couch-fibers-cpl` identical hashes are the *correct* result, because the fix
is meant to be a no-op there. On the halo subject they are a dead knob. Same
observation, opposite meaning, which is why the ladder prints both subjects
separately rather than one pass/fail.

## 20. The trade, measured: there is no good setting, and the knob is not the cause

ORCH asked for the trade quantitatively -- how much halo reduction at how much
`couch-fibers` softening, across the range of the fix's strength -- and said a
clean negative would be a result. It is a clean negative, and it is worse than
a bad trade: **the dose-response is flat, the shipped arm is worse than no fix
on BOTH axes, and the mechanism aimed at the halo is not what is causing it.**

One binary, `C:\dev\strehl-pin-ce2c793\target\release\strehl.exe`, SHA256
`17E5A234...9137`, all fifteen renders back to back. Measured by section 19.

### 20.1 The ladder

`STREHL_EDGE_TAU` is the strength knob: a pixel's support collapses when the
guide winner field varies by more than tau frames across its box, so LOW tau =
more pixels read as a silhouette = more collapse = stronger fix. Swept 64 -> 4,
a 16x range, against a shipped default that solves to 36.8 on this bracket.

| arm | halo (DN) | vs off | paired vs off | tiles worse | texture SD | px moved |
|---|---|---|---|---|---|---|
| `off` | **+129.5** | 100% | -- | -- | 1.0000 | 0.00% |
| `default` (tau 36.8) | +146.1 | 113% | +28.9 `[+15.7,+64.0]` | 97% | 0.9902 | 54.24% |
| tau 64 | +145.9 | 113% | +28.8 | 97% | 0.9903 | 54.21% |
| tau 32 | +146.1 | 113% | +28.9 | 97% | 0.9902 | 54.22% |
| tau 16 | +146.4 | 113% | +28.9 | 97% | 0.9902 | 54.29% |
| tau 8 | +146.5 | 113% | +28.9 | 97% | 0.9900 | 54.47% |
| tau 4 | **+146.6** | 113% | +28.8 | 97% | 0.9896 | 54.74% |

**There is no setting where the halo is acceptable and the texture is intact,
and there is no setting where the halo is even improved.** Every arm sits at
113% of the unfixed baseline. The paired per-tile comparison makes that
unambiguous: the arm is further from the no-election reference than `off` is on
**97% of 37 tiles**, at every strength.

Across the whole 16x sweep the halo moves by 0.7 DN out of 146 -- **0.5%**.

### 20.2 The knob is live, so the flatness is a result and not a dead parameter

This is exactly the failure section 19.7 exists to catch, so it was checked
before the table was believed. All seven arms are byte-distinct on both
subjects, and the collapse statistics move as designed on the halo subject:

| arm | admitted | mean radius | at full r13 |
|---|---|---|---|
| `default` (tau 36.8) | 10.65% | 12.98 px | 99.66% |
| tau 8 | 10.65% | 12.77 px | 96.83% |

The radius collapse fires on **0.34%** of pixels at the shipped default and
**3.17%** at tau 8 -- a **9x change in dose** -- and neither axis moves.

### 20.3 What is actually causing it, isolated by the dose-response

The `Acuity` arm bundles two changes, and the ladder separates them because
only one of them depends on tau.

1. **The adaptive radius collapse** -- the mechanism aimed at the halo. Depends
   on tau. Fires on 0.07-3.17% of pixels. **Contributes ~0.5% of the arm's
   effect.**
2. **The luma-guided regulariser**, which replaces the shipped radius-8 box
   with a domain transform at the same nominal scale. **Independent of tau.**

Everything measured here is tau-independent, so **effectively 100% of both the
+13% halo regression and the texture damage comes from (2)**.

`couch-fibers-cpl` settles it on its own, with no ladder at all. There the
radius collapse touches **0.07%** of the plane (`mean radius 13.00 px`, i.e.
the shipped flat radius to two decimals) -- and **54% of the frame's pixels
move anyway**. A mechanism that touches 0.07% of pixels cannot move 54% of
them. The only other thing that changed is the regulariser.

### 20.4 Why luma is the wrong guide, in one line of source

`merge_cmd.rs:1180` passes **`&scratch.luma`**: the domain transform is guided
by each frame's own brightness. `merge.rs`'s own doc for `regularise_guided`
says that away from a luma step this is the shipped operator -- which is true,
and is precisely the problem, because **the two subjects that matter are
nothing but luma steps.**

- **At a halo rim there IS a luma step.** The guided filter therefore *stops
  smoothing across it* and **preserves the rim** instead of averaging it away.
  The regulariser was introduced to keep the narrow window's win from being
  undone by the second cascade; on the actual artefact it protects the artefact.
  That is the +13%.
- **On `couch-fibers` luma steps are everywhere and depth steps are nowhere.**
  The filter stops regularising across every fibre, so the plane gives up much
  of fact 84's -35% absolute-error benefit exactly where there was no depth
  discontinuity to respect. That is the 54% of pixels and the 1% softening.

**The guide signal is brightness where the question is depth.** This is the same
discrimination failure as sections 16-18: a luma edge is not an occluding edge,
and a fibre tangle is the subject that separates them.

### 20.5 What follows

The immediate consequence is not a tuning change, because there is nothing to
tune -- the curve is flat. It is that **the shipped default is net harmful on
both axes** and, on this evidence, `EdgeArm::Acuity` should not be the default
in its current form. Turning it off recovers the full 13% of halo and returns
`couch-fibers` to byte-identical.

That flip is **not** made here, and deliberately so: it moves the byte-freeze a
third time in one day, and it moves the baseline BUILD-BLEND is currently being
compared against, with five agents live in the tree. It is a coordination
decision, and the measurement above is what ORCH needs to make it.

The repair, if the arm is to stay, is to guide the regulariser by **depth**
rather than luma. The guide winner field is already computed one pass earlier
and is already handed to `SelectionScale::from_silhouettes`; a step in it is a
genuine occluding silhouette rather than a brightness change. That would smooth
freely across `couch-fibers`' texture, because it has no depth steps, while
still stopping at a true silhouette. It is a signal swap at `merge_cmd.rs:1180`
plus the plumbing to get the field there, and it is the frequency-selective --
strictly, structure-selective -- move ORCH asked whether I could see.

## 21. The 191-frame index jumps are anti-coincident with the rim

BUILD-CHROMA found adjacent-pixel election-index jumps of up to 191 frames in a
299-frame bracket and ORCH routed it here as a candidate rim mechanism, asking
one falsifiable question: do the extreme jumps overlay the silhouette?

**They do not. They are depleted to exactly zero at the silhouette and enriched
in the open background.** Picture: `C:\dev\strehl-out\JUMP\JUMP-overlay.png`.

### 21.1 The measurement, binned on an election-independent map

The obvious binning map is wrong. `depth_profile.depth_mask` segments on the
local standard deviation of the election map, and a large adjacent-pixel jump
IS large local SD -- binning the jump field on that mask is binning a statistic
on itself and would manufacture the coincidence. The silhouette here is
therefore taken from `f221`, a `STREHL_ONLY_FRAME` render with **no election in
it at all**, so it is independent of the election map by construction.

The threshold is the plane's own 99.9th percentile, which fixes the extreme
population at 0.1% by construction and leaves only its *location* free to vary.

| band (px) | background px | extreme | enrichment |
|---|---|---|---|
| 1-6 | 69,201 | **0** | **0.00x** |
| 6-12 | 68,716 | **0** | **0.00x** |
| 12-20 | 93,693 | **0** | **0.00x** |
| 20-28 | 92,183 | **0** | **0.00x** |
| 28-40 | 138,623 | 49 | 0.24x |
| 56-78 | 255,034 | **0** | **0.00x** |
| 150-208 | 633,929 | 1,051 | 1.12x |
| 288-400 | 871,086 | 2,086 | **1.62x** |

Zero extreme jumps in 231,610 background pixels within 20 px of the silhouette.
Not "few" -- zero.

### 21.2 What the jumps actually are

They are **dead ground**. A featureless backdrop has no focus signal, so the
argmax is noise spanning the whole bracket and adjacent pixels elect unrelated
frames. This is not a new finding here; it is the *defining property* section
19.3's segmentation already relies on -- "dead ground elects noise, a real
object elects coherently". BUILD-CHROMA measured the selector's noise floor on
textureless regions, which is real and worth knowing, and it is not a cliff at
depth boundaries.

### 21.3 The consequence that matters, and it is a reframing

Enrichment *below* base rate near the silhouette is not a null result, it is a
positive one with the opposite sign. Near a real occluding edge there is
genuine contrast, so the election is better determined than average: **the rim
is not where the selector is uncertain. It is where the selector is confident
and wrong.**

That kills a whole family of approaches at once -- anything of the form "detect
low-confidence or incoherent pixels and repair them" is aimed at a population
that does not overlap the artefact. It also explains why the veto-gated
collapse of section 18 could be correct in its logic and still do nothing: a
confidence-shaped gate cannot find a defect that is not confidence-shaped.

### 21.4 The averaged-index mechanism does not exist in this code

ORCH's proposed mechanism was that a box filter on the index field averages 40
and 231 to 135, landing a pixel between two depths. **The regulariser is a box
on the FOCUS field, not on the index field** (`merge.rs::regularise` ->
`box_mean(focus, ...)`); the winner is then an argmax over frames of the
regularised focus field, so the elected index is always one some frame actually
attained and an intermediate index can never be synthesised.

Measured rather than merely read off the source: the subject elects 96 and the
far background 210, and only **11.8%** of near-band pixels elect the middle 60%
of that gap -- far below the 60% a filled distribution would give. The
near-band election is bimodal, not averaged.

Fact 86's non-monotonicity (width 3 worse than none) therefore still needs an
explanation, but averaging across a bimodal index field is not it.

### 21.5 Cost

One hour, no renders -- it reused the `TRADE` ladder's `off` and `f221` arms and
the existing election map. Either answer would have been progress; this one is
a refutation, and the picture is the report.

## 22. The backdrop's election is a ramp driven by distance from the subject

ORCH measured a broad dark aura on `flower-bud-alone-cpl` and proposed that
focus breathing moves the silhouette so that backdrop pixels are OCCLUDED by
the subject in many frames and those samples are averaged in. I proposed a
rival: dead-ground pixels admit ~55 frames, most of which carry the subject's
defocus veil, so the average is pulled dark.

**Both are wrong, and the truth is worse than either.** Picture:
`C:\dev\strehl-out\AURA\AURA-election.png`.

### 22.1 The aura reproduces independently

Measured with a different silhouette, a different far-field reference (d=500-900
px rather than ORCH's 300-400, which is partly inside the feature it is meant to
reference) and a different script: **merge - sharp frame = -3787 DN** over
d=64-260 px. ORCH measured -4293 DN at d=117; this run gives -4478 DN at
d=96-140. **Confirmed.**

The control is the load-bearing part. In the subject-free field the merge and
the sharp frame differ by **6 DN** against the aura's 3787 DN, a margin of
**630x**. The instrument is silent where there is nothing to see.

### 22.2 Breathing is dead, and its measurement had a specific defect

The warp sidecar is inspectable text and prints `scale-1` per frame:

| frame | `g` (scale-1) | dx | dy |
|---|---|---|---|
| 0 | `+5.58e-5` | +0.025 | -0.383 |
| 204 | `+1.28e-8` | -0.005 | -0.045 |

**Post-alignment silhouette motion between the ends of the bracket is ~0.4 px**,
and the scale term is 0.0056%, not 13.7%. Independently: the solve reports
`held-out err 0.352 px` over spans up to 128 frames, and a real 13.7% breathing
would put a span-128 pair ~150 px apart at the frame edge. ORCH's "common to
every edge" caveat does not cover a drift that is monotone in frame index.

The 13.7% came from thresholding subject AREA. A dark subject that is defocused
thresholds LARGER. ORCH anticipated this and ruled it out on monotonicity --
blur should enlarge both ENDS of the bracket. That control fails here because
**the subject's focus is near frame 153, not the middle**: the d=6 px spill runs
f000 -11306, f051 -10868, f102 -8887, f153 -5327, f204 -5770. Blur is monotone
across ~75% of the bracket, so a monotonicity test cannot discriminate.

### 22.3 Uniform averaging explains only 31%

Nine `STREHL_ONLY_FRAME` arms spanning the bracket were already on disk. Each is
self-referenced and therefore IDENTITY-warped, so a reconstruction built from
them contains no registration, and hence no breathing, **by construction**.
Their uniform mean closes only **31.2%** of the gap between the sharp frame and
the merge. Averaging contributes; it is not the driver.

### 22.4 The actual mechanism, measured

`STREHL_DUMP_ELECTION` on ORCH's own pin (`859edac`, `DF209CE0`). Median elected
frame against distance from the silhouette:

**CORRECTED 2026-08-25.** The table first published here carried every distance
at 2x its true value. `distance_transform_edt` runs on the full-resolution
7040x4688 mask, so its values are TIFF px; subsampling with `[::2, ::2]` changes
which pixels are kept but NOT the distances they carry, and the band thresholds
were divided by 2 anyway. The corrected table is below. The shape of the finding
is unchanged and the ramp is if anything sharper; only the length scale moves.
Caught by a cross-check against `aura_reconstruct.py`, which uses the full-res
mask and is correct by construction: the two now agree to 4 significant figures
(d=96-140: -5061.4 vs -5063.2; d=200-260: -3293.7 vs -3295.2) across two
different merge renders.

| d (px) | 1-8 | 16-32 | 32-64 | 64-96 | 96-140 | 140-200 | 200-260 | 260-320 | 320-400 | 400-500 | 700-1000 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| median frame | 109 | 101 | 86 | 64 | 41 | 11 | 1 | 5 | 99 | 107 | 116 |
| IQR/bracket | .19 | .18 | .19 | .15 | .14 | .13 | **.03** | .44 | **.57** | **.54** | **.53** |

**The backdrop's elected frame is a smooth monotone function of its distance
from the subject, sweeping the entire 205-frame bracket, and tightly determined
the whole way** -- most tightly of all at d=200-260, where the IQR is 3% of the
bracket and 95% of pixels elect frame <=40. Past d~320 px it collapses into
dead-ground noise, which is section 21's result appearing here as a built-in
control on the same plane.

The ramp and the aura terminate together. The aura reads -3294 DN at d=200-260,
-1322 at 260-320, -500 at 320-400: it dies exactly where the election stops
ramping and starts electing noise. That correspondence is the strongest single
piece of evidence that the ramp causes the aura.

A flat white card lies at one depth. It should elect one frame, or noise. Its
selection is instead dictated by proximity to an object it does not touch.

### 22.5 Why: Tenengrad counts a ramp as focus

`focus.rs` line 6 is explicit:

```text
focus(p) = box_mean_13(|grad I|)(p) / sigma_L(p)
```

At a backdrop pixel the only structure in any frame is the subject's defocused
edge ramp. **A ramp is a region of coherent, constant gradient.** The 27x27 box
mean averages the random noise gradient down by sqrt(729) ~ 27 while preserving
the coherent ramp in full, so the ramp beats the noise floor. The frame that
maximises it is the one whose blur radius places its ramp at that exact
distance -- which is why the elected index ramps with distance, and why the
aura terminates at the subject's maximum blur radius rather than at any
selection scale.

The election is not tolerating the veil. **It is seeking it**, and each backdrop
pixel elects the frame that veils it most.

### 22.6 The consequence for the fix

This is the frequency-selective move section 20 concluded was needed and could
not find in the winner field, and it sits one level lower, in the measure
itself. A ramp has CONSTANT gradient; genuine texture has VARYING gradient.
High-passing at the window scale separates them exactly: a box mean of a linear
ramp reproduces that ramp, so `I - box_mean_13(I)` is identically zero on a
ramp while fine texture passes untouched.

It is scale-selective by construction -- it rejects everything coarser than the
window, where the veil lives, and keeps everything finer, where `couch-fibers`
texture lives. That is the trade section 20 measured as unresolvable in the
winner field, and it is resolvable here because a measure has a scale and a
winner field does not.

### 22.7 What is NOT yet explained

The elected frame at d=96-140 is 78, whose own profile there is about -1044 DN,
while the merge reads -5063 DN. Neither the winner alone nor a uniform mean
accounts for that amplitude. The gate's admitted SET is not dumped and has not
been measured, so the amplitude accounting is open. The distance-driven ramp in
22.4 is measured directly and does not depend on resolving it.

## 23. A quarter of the aura is exposure drift, and it is one flag away

### 23.1 The bracket drifts 18.3% and the shipped merge does not correct it

The nine single-frame arms, read in RAW DN at a frozen far-field pixel sample:

| arm | f000 | f025 | f051 | f102 | f153 | f204 | spread |
|---|---|---|---|---|---|---|---|
| far-field DN | 17576 | 17950 | 18372 | 19278 | 20183 | 21106 | **3530 DN = 18.3%** |

Monotone with frame index. The engine's own photometric fit agrees from a
different direction: `gain span 1.2350 (max/min across 205 frames)`.

`main.rs` states the consequence in its own words -- "a gated average without
this term is reading an exposure change as a signal change" -- and **`off` is
the shipped default.** M24's worst measured drift was coffee-bean at 11.70%;
M122 measured the flag HELPING tweezers-cpl at 13.765%. This stack drifts more
than either.

### 23.2 It broke a measurement, and the broken result was mine

Referencing each arm to **its own** far field -- which ORCH's spill table and my
`aura_hull.py` both did -- divides every arm by a different number when the arms
differ by 3530 DN. That alone manufactured this reading:

| test | merge below EVERY sampled frame |
|---|---|
| referenced to each arm's own far field | **76.92%** of pixels |
| raw DN, no reference anywhere | **2.09%** of pixels |

The referenced number says the estimator loses to its own inputs, which would be
an invariant violation that no reweighting could repair. **It is an artefact.**
In raw DN the merge is inside the hull of its inputs at 98% of pixels, median
depth below it 40 DN. A convex combination cannot be darker than its darkest
input, and this one is not.

The merge's own far field sits 32.5 DN from the mean of the nine frames' far
fields, which independently confirms section 22's dead-ground control: out there
the election really is a broad mix.

### 23.3 The decomposition, measured by one flag

`--photometric on`, same pin, same gate, same stack, everything else fixed:

| d (px) | 1-32 (rim) | 64-96 | 96-140 | 140-200 | 200-260 | 260-320 | 320-400 |
|---|---|---|---|---|---|---|---|
| OFF (shipped) | -6618 | -4844 | -5061 | -4556 | -3294 | -1322 | -500 |
| ON | -6735 | -4330 | -4127 | -3157 | -1603 | -727 | -388 |
| aura removed | **-1.8%** | 10.6% | 18.5% | 30.7% | **51.3%** | 45.0% | 22.4% |

**Over the aura band d=64-260 px, 25.6% of the aura is exposure drift.** The
fraction rises with distance, reaching 51% at d=200-260 -- which is exactly
where the election ramp bottoms out at frame 1 and the exposure difference from
the far field's broad mix is largest. The two curves are the same curve.

The rim (feature 1) gets 1.8% WORSE. It is a different defect and this does not
touch it.

### 23.4 The control that makes it a decomposition rather than a coincidence

**The election ramp is bit-identical between the two arms** -- 107, 101, 86, 64,
41, 11, 1, 5, 99, 107 in both. Photometric correction rescales frame levels and
does not perturb the selection at all. So the 25.6% is the exposure term being
removed from a fixed election, not a different election being run.

That splits the aura cleanly:

* **~26% -- the per-frame exposure ramp, sampled by the distance-driven
  election ramp.** Free today, one flag, no new code.
* **~74% -- genuine veiling.** The defocused subject really does spill onto the
  backdrop, and the election preferentially selects the frames where it spills
  most. This is the part ORCH's outlier/envelope estimator has to remove.

Both act through the same election ramp of section 22.4, which remains the
single upstream cause.

### 23.5 What this does to the 109MSDCF negative control

`109MSDCF` has **22 frames and 0.91% drift** (M24). `flower-bud-alone-cpl` has
**205 frames and 18.3% drift**. The negative control differs from the positive
by 9x in bracket length and 20x in exposure drift, not only by depth separation.
Since a quarter of this aura is now measured to BE exposure drift, that
confound is real and not hypothetical. The dose-response across paint strokes
still isolates subject luminance correctly within `109MSDCF`; what it cannot do
is carry a conclusion ACROSS to a stack that differs in two other large ways.

### 23.6 The estimator ceiling, which survives all of the above

At d=140-200, per-pixel across the nine frames:

| p0 | p25 | p50 | p75 | p100 | dark tail | light tail | skew |
|---|---|---|---|---|---|---|---|
| -4122 | -1248 | -568 | -485 | **-379** | 3306 DN | 250 DN | **13.2x** |

Heavily skewed dark, which is what ORCH predicted and what justifies an upper
envelope. Delivered values on that band: merge **-4549**, best single frame
**-474**, upper envelope **-379**. The unveiled backdrop IS recoverable from the
stack, and the envelope beats the single-frame floor rather than merely matching
it.

## 24. The middle-frame arm: section 15 stands, and the defect is not general

ORCH objected that section 15.2's four arms (`off`, `on`, `frame000`,
`frame298`) used END frames as its only election-free references, and the end
of a bracket is where the subject is furthest from focus and spilling hardest.
A merge that elects end-like frames, compared against two end frames, would
agree with them for the worst possible reason. The objection is correct and the
missing arm is the MIDDLE frame.

Rendered it: same pin `0BB7BCDD4A58`, same flags, same rows, one arm added.

### 24.1 The objection is real -- and it strengthens section 15 rather than killing it

`lavendar-cpl`, near-backdrop level as a ratio to each arm's own far backdrop
(gain-invariant, which matters because the five arms span 24.3% in raw DN):

| arm | f000 | off (merge) | f298 | f149 (middle) |
|---|---|---|---|---|
| near-backdrop ratio | 1.0164 | 1.0359 | 1.0404 | **1.0475** |

ORCH's mechanism is confirmed in sign and ordering: the middle frame is the
cleanest and `f000` -- the most defocused end -- is the most veiled, suppressing
3.0% of the gradient.

**But the conclusion it was supposed to overturn survives, because the
least-veiled arm shows the feature MOST.** The backdrop brightening is 4.75% in
the middle frame against 3.59% in the merge. An artefact of the merge cannot be
larger in a single frame that contains no election at all. The ~4% gradient is
scene. The merge's own penalty against the best available reference is 1.1%.

### 24.2 A dramatic result on bee-2 that the picture killed in one look

The same test on `bee-2-cpl` produced, on pixels the sharpest frame calls open
backdrop: **the merge below EVERY single frame by up to 36.5%**, and its 50%
edge crossing displaced **139 px** into the backdrop while the three single
frames agreed among themselves within 64 px. In gain-invariant ratio space, so
no exposure argument could reach it.

**It is not a defect. It is the stacker working.** The crop
(`bee2-smear.png`) shows the merge rendering the bee's hairs and legs sharply
across exactly that band, where `f149` and `f298` show smooth blur. A thin dark
hair spread over a large blur disc contributes almost nothing per pixel; sharp,
it is a black line. A merge BELOW the hull of its inputs is the correct and
desired outcome wherever fine dark structure is resolved.

The rebuttal I had written for this confound was wrong in a specific, reusable
way. I argued that a real object at x=650 would darken `f149` too, so `f149`
reading 1.00 proved the object absent. That assumes `f149` is the sharpest view
OF THAT OBJECT. On a subject with real depth it is not: the middle of the
bracket is the middle of the bracket, not the focus of every feature in frame.

### 24.3 The control that makes the retraction rigorous

Same test, same rows, restricted to hair-free open backdrop (x=100..460):

| row | 600 | 750 | 900 | 1050 |
|---|---|---|---|---|
| px where merge is below every frame | **0** | **0** | **0** | **0** |
| worst deficit vs the brightest frame | 1.9% | 2.5% | 2.2% | 2.7% |

**On genuinely open backdrop `bee-2`'s merge is clean.** The whole 36% signal
came from resolved hairs.

### 24.4 What this does to the scope of the defect

| subject | backdrop | merge deficit on open backdrop |
|---|---|---|
| `bee-2-cpl` | textured, hairs throughout | **2.7%** |
| `lavendar-cpl` | textured | **1.1%** |
| `flower-bud-alone-cpl` | **featureless white** | **22.8%** |

**Bracket depth is not the risk factor; a featureless backdrop is.** `bee-2` is
a 299-frame stack, deeper than flower-bud's 205, and it is an order of
magnitude cleaner. The proposal that all eleven 299-frame stacks carry a worse
version of this is not supported by the one member of that list that has been
measured.

This is exactly what section 22's mechanism predicts and is the strongest
confirmation of it so far. Where the backdrop carries real focus signal the
election locks onto it and the merge is fine. Where the backdrop is featureless
there is no signal, and the only coherent gradient available to a Tenengrad
measure is the subject's own defocused edge ramp -- so the argmax chases the
veil, monotonically with distance, exactly as section 22.4 measured.

### 24.5 The fix this points to, and why it retires the trade

The discriminator is not distance, not window support, and not jump size. It is
**whether a pixel's through-focus response carries any real signal at all.**
Where every frame's focus measure sits at the noise floor, the argmax is
meaningless and must not be trusted; where it does not, the current selector is
already doing the right thing and must not be touched.

That is why this can be built without the section 20 trade. `couch-fibers` has
genuine focus signal everywhere, and `bee-2`'s hairs have it in abundance; a
validity gate is a no-op on both by construction. It only fires on dead ground,
which is precisely and only where the aura lives.
