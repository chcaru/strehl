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
