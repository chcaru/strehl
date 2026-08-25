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
the sample-count miscalibration. `hp_energy` stays above baseline on all three,
so v2 is still not a blur. Some of v1's *higher* `hp_energy` was the blotch
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
