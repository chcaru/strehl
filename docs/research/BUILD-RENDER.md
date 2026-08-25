# BUILD-RENDER: what the product actually does on the owner's library

Implementation notes, not a research paper. Written by BUILD-RENDER, whose lane
is the CLI entrypoint, RAW decode and IO, alignment *plumbing*, output writing,
colour on the output path, and QA tooling. The focus measure, the merge and the
winner-field/election code belong to BUILD-HALO and nothing here touches them.

Everything below was produced by one binary built from a frozen copy of the
tree at commit `23bdfca`, kept at `C:\dev\strehl-out\baseline-src\`, so that
none of it moves when BUILD-HALO lands.

---

## 1. The render table

**Every one of the 26 subjects in `D:\personal\macro` renders, unattended, with
no crash, no hang, and no out-of-memory.** That includes all three stacks the
owner added today (`pencil-flatter-angle-cpl`, `pencil-steep-angle-cpl`,
`flower-inner-edge-cpl`). `flat-fields` is excluded: it is a 484-frame
calibration campaign, not a stack.

Linear, binned, no `--srgb`. Peak memory is the OS `PeakWorkingSet64` polled at
200 ms; it is a true high-water mark but the last poll races process exit, so
read it as a tight lower bound. Wall clock is external and the machine was
running other agents' builds, so treat timings as indicative.

```
subject                               frames  status  wall_s  peakMB  mean n_eff  fov     alignment
------------------------------------- ------- ------- ------- ------- ----------- ------- --------------------------------
coffee-bubbles                        19      ok      11.3    5315    3.385       0.9887  ON (solved) 19/0 refused [UNVERIF]
109MSDCF                              22      ok      8.7     5767    4.850       0.9870  ON (sidecar) 22/0 refused [UNVERIF]
119MSDCF                              33      ok      14.1    5980    4.672       0.9916  ON (solved) 33/0 refused [UNVERIF]
113MSDCF                              63      ok      26.5    7187    8.438       0.9809  ON (solved) 63/0 refused [UNVERIF]
flat-on-ruler-cpl                     79      ok      31.5    5256    1.154       0.9708  ON (solved) 79/0 refused
112MSDCF                              79      ok      34.1    6577    11.861      0.9765  ON (solved) 79/0 refused
tweezers-cpl                          100     ok      38.7    6501    31.121      0.9726  ON (solved) 100/0 refused
foam                                  100     ok      26.2    6262    1.398       0.8761  ON (sidecar) 100/0 refused
coffee-bean                           105     ok      30.0    6627    27.355      0.9652  ON (sidecar) 105/0 refused
wrapped-text-2                        120     ok      48.4    8620    1.502       0.9404  ON (solved) 120/0 refused
lead-1-cpl                            123     ok      47.1    7437    7.864       0.9564  ON (solved) 123/0 refused
wrapped-text-1                        130     ok      35.7    7914    1.183       0.9474  ON (solved) 130/0 refused
flowers-cpl                           176     ok      49.0    7766    45.876      0.9368  ON (solved) 176/0 refused [UNVERIF]
leaf-2-cpl                            182     ok      49.6    9327    10.614      0.9344  ON (solved) 182/0 refused
flower-bud-alone-cpl                  205     ok      57.5    9641    134.971     0.9970  ON (solved) 205/0 refused
dry-erase-marker-head-cpl             299     ok      45.8    6887    81.851      0.9476  ON (sidecar) 299/0 refused
pencil-steep-angle-cpl                299     ok      87.5    16438   149.127     0.9578  ON (solved) 299/0 refused
bee-1-cpl                             299     ok      86.6    14218   70.223      0.9225  ON (solved) 299/0 refused
pencil-flatter-angle-cpl              299     ok      89.8    14790   162.583     0.9562  ON (solved) 299/0 refused
flower-bud-with-background-fern-cpl   299     ok      89.6    11853   126.410     0.9195  ON (solved) 299/0 refused
bee-3-cpl                             299     ok      49.9    6848    55.321      0.9315  ON (sidecar) 299/0 refused
couch-fibers-cpl                      299     ok      90.1    12936   2.645       0.8850  ON (solved) 299/0 refused
flower-inner-edge-cpl                 299     ok      120.0   14959   4.071       0.8428  ON (solved) 299/0 refused
lavendar-cpl                          299     ok      127.1   13399   170.492     0.9386  ON (solved) 299/0 refused
highly-angled-ruler-mm-cpl            299     ok      19.9    6374    183.600             REFUSED - merged unregistered
bee-2-cpl                             299     ok      87.0    14776   66.545      0.9044  ON (solved) 299/0 refused [UNVERIF]
```

`ok` means the pixels reached the disk. It does **not** mean the picture is
good; see §3.

### What the table surfaced

1. **`highly-angled-ruler-mm-cpl` merges unregistered.** The aligner refuses
   ("a tilted subject; a global similarity cannot describe it"), and the merge
   then proceeds anyway, printing "expect softness that grows with radius" and
   citing 232.7 px of drift. A knowingly-degraded image is produced with exit
   code 0. It is also the fastest 299-frame render in the table (19.9 s vs
   ~88 s) purely because it skips the warp. **This should not silently
   succeed.**

2. **Peak RSS scales with frame count although the design says it must not.**
   The binary prints `in-flight frames: 13 peak, bound 13 (never O(N))` and a
   6144 MB budget, yet peak working set runs 5.3 GB at 19 frames and
   **16.4 GB at 299** (`pencil-steep-angle-cpl`). Whatever the in-flight bound
   governs, it is not the process's actual footprint. Nothing OOM'd on this
   machine, but the budget does not predict the number, so it cannot be used to
   size a smaller one.

3. **The field of view is cropped and then upsampled back.** To guarantee every
   frame covers every output pixel, the FOV is scaled and the result is
   resampled up to keep the nominal dimensions. That factor reaches **0.8428**
   on `flower-inner-edge-cpl` — 15.7 % of the frame width discarded and the
   remainder stretched over the original pixel grid. That is a real, unstated
   resolution loss on the output path, applied to every aligned render.

4. **Registration is mostly self-declared UNVERIFIED.** Six subjects print
   "this solve could not certify itself" because the held-out protocol had no
   long-span edges to work with. The registration those renders used carries no
   error bar.

---

## 2. The instrument

`scripts/crop_set.py`. The rule it is built around is that this project has a
history of green metrics over bad images, so **the output is pictures**.

Three crop classes, because three defects live in three places:

| class    | where it looks                                | what it catches            |
|----------|-----------------------------------------------|----------------------------|
| `edge`   | occluding boundaries                          | halo                       |
| `flat`   | low-texture regions                           | merge noise                |
| `detail` | the sharpest structure in the frame           | a "fix" that is a blur     |

**Coordinates are frozen.** They are chosen once from the baseline render and
written to `C:\dev\strehl-out\roi-plan.json`, then reused unchanged. Re-choosing
per render would let a change move the crop onto flattering ground, which is
precisely the failure the instrument exists to catch. The display gain is frozen
in the same file, so two renders are always shown identically.

**Finding an occluding edge needs more than contrast.** The first version scored
`gradient x span` and picked the bee's *compound eye* — the highest-contrast
thing in the frame, surrounded by more texture, carrying no halo at all. A halo
needs a sharp subject edge with **smooth, defocused background on one side**, so
the score is now weighted by the fraction of the neighbourhood that is flat.
That moves the crop onto the silhouette, where the defect actually is.

**Measurement is linear; only display is converted.** Input is the default
`--out` file (linear, camera-native, no transfer curve). `--srgb` is never
rendered and never measured — several results here have been retracted for
exactly that.

### Re-running it

```powershell
# 1. render everything (~26 min for the whole library)
powershell -File scripts\render_all.ps1 -Exe <strehl.exe> -OutDir C:\dev\strehl-out\<run>

# 2. rebuild the table from the artifacts, without re-rendering
powershell -File scripts\render_table.ps1 -OutDir C:\dev\strehl-out\<run>

# 3. crops at the frozen coordinates
python scripts\crop_set.py --plan C:\dev\strehl-out\roi-plan.json crops `
    --renders C:\dev\strehl-out\<run> --out C:\dev\strehl-out\<run>-crops --label <run>

# 4. side-by-side against the frozen baseline  <-- this is the one that matters
python scripts\crop_set.py --plan C:\dev\strehl-out\roi-plan.json compare `
    --baseline C:\dev\strehl-out\baseline --candidate C:\dev\strehl-out\<run> `
    --out C:\dev\strehl-out\compare-<run>

# whole-frame previews with the crop boxes drawn on
python scripts\crop_set.py --plan C:\dev\strehl-out\roi-plan.json full `
    --renders C:\dev\strehl-out\<run> --out C:\dev\strehl-out\<run>-full
```

Do **not** pass `plan --force` before judging a fix; that unfreezes the
coordinates and voids the comparison.

### Stored artifacts

| what | path |
|---|---|
| frozen baseline binary + source | `C:\dev\strehl-out\baseline-src\` (HEAD `23bdfca`) |
| baseline renders + logs + timings | `C:\dev\strehl-out\baseline\` |
| render table | `C:\dev\strehl-out\baseline\render-table.tsv` |
| **frozen ROI plan** | `C:\dev\strehl-out\roi-plan.json` |
| **baseline crop set (26 x 9 = 234)** | `C:\dev\strehl-out\baseline-crops\` |
| baseline full-frame previews | `C:\dev\strehl-out\baseline-full\` |
| gate sweep + composites | `C:\dev\strehl-out\gate-g{0.5,1.0,2.0}\`, `compare-gate*\` |

---

## 3. Print-worthiness verdict

**No. Not print-worthy.** One disqualifier, and it is the same one in every
affected frame.

### Disqualifier: a bright halo traces every occluding edge

On any subject with a hard silhouette against a smooth, defocused background,
the subject is wrapped in a light envelope that follows its outline. At full
frame it reads as a **cut-out sticker pasted onto the backdrop**; at 100 % it is
a bright fringe around every hair and every leg.

The clearest examples in the baseline set:

- `baseline-full/flower-bud-with-background-fern-cpl.png` — the fern frond on
  the left is outlined in hard white and looks pasted on. This is the single
  most damning image in the set.
- `baseline-full/bee-1-cpl.png` — every leg, antenna and the whole body
  silhouette carries a white glow.
- `baseline-crops/bee-2-cpl/edge0.png` — at 100 %, each hair sits in its own
  bright envelope and groups of hairs are enclosed in blobby white outlines.

It is not universal, and the pattern is diagnostic: **`couch-fibers-cpl` is
clean** because it is dense texture edge to edge with no silhouette against a
smooth background, and `flower-inner-edge-cpl` (new today) is largely clean for
the same reason. The defect is specific to occluding boundaries.

### What is *not* the cause — a negative result

I expected the gate. `mean n_eff` in the table is alarming: the shallow stacks
the corpus was built on average 1.2–4.9 frames per pixel, near the documented
target of 3, but the deep 299-frame stacks average **150–184**, and the default
gate is documented in the binary's own help as `UNCALIBRATED`. Averaging 150
defocused frames into every pixel is an obvious blur hypothesis.

It is wrong. A gate sweep on `flower-bud-with-background-fern-cpl` gives
n_eff 3.04 / 8.97 / 43.6 / 126.4 at gates 0.5 / 1.0 / 2.0 / 4.0, and in
`compare-gate0.5/`:

- the **halo is unchanged** at n_eff 3 versus n_eff 126;
- the **detail crops are visually identical**;
- the only difference is the background, which is clean at gate 4.0 and
  heavily grainy at gate 0.5.

So the high `n_eff` is dominated by flat background where averaging is the
correct thing to do and costs no sharpness, **the default gate of 4.0 is doing
its job, and the halo is independent of it.** The halo is a merge/occlusion
defect, which is BUILD-HALO's lane, and lowering the gate would only add noise
without touching it.

### The numeric halo proxy does not work — do not gate on it

`crop_set.py` emits an `edge_overshoot` number per edge crop. **It disagrees
with the eye and should not be used as an acceptance criterion.**
`coffee-bubbles` tops the ranking at 0.977 on specular highlights that are not
halo at all, while `bee-2-cpl`, which has the worst halo I can see anywhere in
the corpus, ranks fifteenth at 0.142. It is kept as supporting context only.
This is the exact failure mode the project has a history of; the pictures are
the instrument.

### Secondary issues, not the disqualifier

- The FOV crop-and-upsample (§1.3) costs up to 15.7 % of linear resolution
  before anything is printed.
- `highly-angled-ruler-mm-cpl` is unregistered and soft by the binary's own
  admission (§1.1).
- Highlight-clipping information is destroyed by the writer (§4).

---

## 4. Colour on the output path

The colour *maths* in `strehl-core/src/color.rs` is in good shape and I did not
need to change it. I ported `camera_to_srgb` into the harness and it reproduces
the module's own documented green row `[-0.115, +1.489, -0.374]` exactly, with
every row summing to 1 and neutral mapping to neutral. The harness renders
display crops to a **stated** target: linear sRGB / BT.709-6 primaries, D65,
then the sRGB transfer curve, gain applied in linear light before the curve.

Two real gaps remained on the output path. **The first is now fixed for the
renders a human actually looks at**; the second is not.

1. **The written TIFF stated no colour space at all — now fixed on the viewing
   path.** `image_out.rs` emitted bare `RGB16` with no ICC profile and no
   colorimetry tags. Every downstream tool — including a print shop's — assumes
   sRGB when it meets that. For an `--srgb` render the assumption is
   accidentally right; for the **default linear camera-native render it is
   completely wrong**, and the two files were byte-indistinguishable to any
   reader.

   `write_rgb16_described` now writes `ImageDescription` and `Software` on
   every developed render, naming the exact target — sRGB (IEC 61966-2-1),
   BT.709-6 primaries, D65 — or, for the camera-native states, saying in
   capitals that the file **is not sRGB**. The white-balance ordering is stated
   in the same sentence rather than left as a footnote, because the noise model
   is calibrated in raw DN *before* any gain: a reader who assumes the opposite
   order mis-scales per-channel noise by the WB gains, which run 2.13–2.86x in
   red on this body. A unit test asserts the four `Develop` states describe
   themselves differently and that both camera-native states carry the warning.

   **Deliberate remaining gap:** the measurement encoder `write_rgb16` is still
   untagged. It is the encoder behind `merge_cmd.rs`'s measurement branch, and
   its output is pinned by both rows of `tests/byte-freezes.tsv`. Tagging adds
   ~393 bytes of metadata and moves both hashes **without changing a pixel** —
   and those rows are being moved concurrently by BUILD-HALO for a much larger
   reason. Re-baselining them from here would publish a hash that is stale on
   arrival and a `why` describing the wrong change, which that registry
   explicitly calls worse than an empty one. Closing it is a one-line switch to
   `write_rgb16_described` plus one coordinated re-baseline, once the merge core
   stops moving. The gap is documented at the function itself, not just here.

2. **The linear file destroys the highlight-clipping information.** The writer
   clamps post-white-balance values to `[0, 1]` before quantisation, so every
   channel's ceiling reads back as exactly 1.0. M109's magenta fix depends on a
   *per-channel* ceiling derived from the container maximum and the WB gains,
   and that per-channel structure is not recoverable from the file. The harness
   reconstructs it approximately (treat any channel at the container top as
   pinned, pull all three to the minimum channel) and says so in the code.
   Not fixed.

There is also no CLI route to "matrix applied, no transfer curve" — the
`Develop` struct supports it and `caveat()` even has a string for it, but the
`stack` flags only offer camera-native-linear or matrix-plus-curve. That mode is
exactly what the measurement rule wants: a **stated colorimetric space that is
still linear**. Wiring it needs an edit in `merge_cmd.rs`, which is BUILD-HALO's
file, so it is flagged rather than done.

Verified for this change: all 71 `strehl-cli` unit tests pass, **both byte-freeze
rows still HOLD**, and the viewing render is pixel-identical before and after
tagging (`np.array_equal` on the `uint16` arrays, read with `tifffile`). Run in
an isolated copy of the tree at HEAD for BUILD-HALO's in-flight files, because
the live tree does not currently compile — see §6.

There is also no CLI route to "matrix applied, no transfer curve" — the
`Develop` struct supports it and `caveat()` even has a string for it, but the
`stack` flags only offer camera-native-linear or matrix-plus-curve. That mode is
exactly what the measurement rule wants: a **stated colorimetric space that is
still linear**. Wiring it needs an edit in `merge_cmd.rs`, which is BUILD-HALO's
file, so it is flagged rather than done.

---

## 5. Hot pixels — measured, and mostly not the problem

I characterised the sensor's fixed pattern from `D:\macro-dark-frames`
(11 ISO folders, 50–2000, 22 frames each; the first 2 of every folder discarded
as stabilisation shots, per the brief). Averaging the 20 usable frames beats
read noise down by √20 and leaves the fixed pattern. Hot photosites are found
**within each CFA phase separately** — the four Bayer positions have different
offsets, and mixing them would flag every red site as hot — against a local
same-phase median, thresholded in MAD-scaled sigma.

Result: **8685 photosites** are hot at half or more of the ISOs, 183 at every
ISO, out of 33 MP.

That count on its own is misleading, and it would have been easy to stop there
and "fix" something. Two things kill it:

1. **The amplitude is tiny at low ISO.** At ISO 100 the median persistent hot
   pixel sits **2.1 DN** above its neighbours — 0.013% of range. Exactly *two*
   photosites in the whole sensor exceed 0.1% of range, and *none* exceed 0.5%.
2. **The dark campaign is at the wrong exposure to answer the question.** All
   242 darks are 1/100 s. The owner's stacks run **1/40 s to 2.5 s** — up to
   250× longer — and dark current accumulates with exposure. A count from these
   darks does not transfer to the library.

So I measured it on the real frames instead. Within a focus bracket the scene is
static and only focus changes, so a per-pixel **minimum** across frames keeps
whatever is constant (the fixed pattern) while real detail, sharp in only a few
frames, falls to its defocused floor. A random 200k-pixel sample is the control.

| stack | exposure / ISO | hot p99 | control p99 | sites > 1% of range |
|---|---|---:|---:|---:|
| `lead-1-cpl` | 2.5 s, ISO 100 | 25 DN | 10 DN | **0** |
| `bee-1-cpl` | ISO 100 | 40 DN | 36 DN | **0** |
| `foam` | 1.6 s, ISO 1000 | 276 DN | 62 DN | **90** |
| `coffee-bubbles` | 2.5 s, ISO 1000 | 406 DN | 55 DN | **130** |

**The verdict: hot pixels are real, but they are not why the stacks are
unusable.** At ISO 100 — 14 of the 26 subjects, including every subject that
shows the halo — the hot sites are indistinguishable from the scene floor even
at a 2.5 s exposure (40 DN against a 36 DN control). They become material only
at ISO 1000, which is exactly **two** subjects, `foam` and `coffee-bubbles`,
and neither of those is a subject the halo disqualifies.

I therefore did **not** wire repair into the Rust IO path. It would be real work
for two subjects while the actual disqualifier sits elsewhere, and the brief
orders me to bias toward a visible result sooner. The expensive half is already
done and stored: the persistent-site map is at
`C:\dev\strehl-out\hotpixels\hot-persistent-xy.npy`, so the repair itself is a
short job whenever it is wanted.

**Capture request for ORCH** (`docs/captures-needed.md` is ORCH's file, so this
is flagged, not filed): *the dark-frame campaign is mis-specified for its
purpose.* It is 11 ISOs at a single 1/100 s exposure, but exposure — not ISO —
is what drives dark current, and the library shoots 1/40 s to 2.5 s. Darks at
the **exposure times actually used** (≥1 s, at ISO 100 and ISO 1000) would let
this be settled directly instead of by extrapolation.

### Re-running it

```powershell
python scripts\hotpixels.py characterise --out C:\dev\strehl-out\hotpixels
python scripts\hotpixels.py materiality --frames 25 `
    "D:\personal\macro\lead-1-cpl" "D:\personal\macro\coffee-bubbles" `
    "D:\personal\macro\foam" "D:\personal\macro\bee-1-cpl"
```

---

## 6. Speed — recorded, not acted on

Per the brief, nothing was optimised. Whole library: **4825 frames across 26
subjects in roughly 26 minutes** on a machine simultaneously running other
agents. Decode-dominated; the binary reports 160–1049 MB/s depending on whether
the RAW is compressed and whether an alignment sidecar was cached. A cached
sidecar is worth roughly 1.8x on a 299-frame stack (`bee-3-cpl` 49.9 s vs
`bee-2-cpl` 87.0 s). Nothing here is GPU-accelerated yet.

---

## 8. The haze — the develop path had no tone rendering

The owner opened the full-frame renders and said: *"i'm very disappointed. these
look horrible."* ORCH then looked at a whole frame personally — the first time
anyone had, rather than reading crop-level agent reports — and described a milky
veil over the entire image, a white petal rendering as flat grey, saturated
green anthers rendering as muddy olive, and lifted blacks. *"It looks like a
scan, not a photograph."*

### The single-frame control: which lane owns it

The defect could have been in develop (mine) or in the merge contributing a
low-frequency lift from defocused frames (BUILD-HALO's). ORCH asked for that
partition before any change, and it costs one render: push a **single frame**
and the **full stack** through the identical develop path and compare.

| | luminance p0.1 | luminance p99.9 |
|---|---|---|
| single frame (`--limit 1 --srgb`) | 0.0836 | 0.7479 |
| full stack (`--srgb`) | 0.0576 | 0.8219 |

**The single frame is hazier than the stack.** The merge is not adding the
veil — if anything it removes a little. The defect is in develop, which is this
lane. That is the whole of the partition, and it took ninety seconds.

### The cause

The develop path was, verbatim from the binary's own report:

```
black, as-shot WB, demosaic, matrix, clamp, sRGB curve
```

and it stopped there. **There was no tone rendering at all.** That is
colorimetrically defensible and photographically dead, because the sRGB transfer
function is an *encoding*, not a *rendering*. Every camera and every raw
developer applies a tone rendering on top of it.

Measured on `flower-inner-edge-cpl` in **linear sRGB** (never on an `--srgb`
render):

- The darkest 0.01% of the frame sat at **0.0038 linear**, not 0. The sRGB toe
  is steep, so 0.004 linear encodes to ≈0.058 — **a 6% grey floor over the whole
  picture.** That is the milk.
- The 99.9th percentile sat at **0.641**, leaving **0.64 stops** of output range
  simply unused.
- With no contrast rendering, midtones stayed flat, and flat midtones read as
  desaturated. The greens were never a colour problem.

One detail worth recording because it rules something out: the floor is **not**
a uniform DN offset surviving black subtraction. If it were, white balance would
amplify it most in red (gains run 2.13–2.86×), but the measured floors go the
other way (G 0.0035 > R 0.0017). It is consistent with real lens flare and
matrix mixing. The fix is the same either way — a photographic render needs an
explicit black point regardless of whether the floor is the scene's or ours.

Separately, **12% of pixels (973,235) clamp to zero blue** after the matrix.
That is a gamut question, not a tone question, and it is untouched here.

### Why 1786 recorded facts missed it

Every measurement this project has ever taken was on **16-bit linear crops**.
The veil is invisible in a linear crop by construction: it is a small additive
offset that only becomes a visible grey floor once the transfer curve's toe
expands it, and the rule "never measure on an `--srgb` render" — which is a
correct rule, and which has saved results here — guarantees nobody was ever
looking at the space where it shows. The measurement discipline that kept the
numbers honest is exactly what hid this. It took opening a picture.

### The fix

`Tone { black, white, contrast }` in `image_out.rs`, measured per image from a
subsample of linear luminance, and **printed** with the other develop parameters
so any render can be reproduced:

```
tone            : black 0.00470, white 0.71107 (linear), contrast 0.55
```

- **Black and white are placed in linear light**, where the statement is
  physical: a measured flare floor and a measured exposure. Black is p0.1 —
  deliberately not the minimum, which a single dead pixel would pin. White reuses
  the p99.9 → 0.90 rule that M100 *measured* over 7 percentiles × 5 targets × 2
  statistics, rather than inventing a second, competing convention.
- **Contrast is a smoothstep S-curve applied in display space**, after the
  transfer curve, which is where raw developers put it and where it belongs: an
  S-curve in linear light crushes shadows violently, because linear light is not
  perceptually spaced. It fixes 0, 0.5 and 1 exactly and is monotonic, so it
  cannot fold or clip. Applied **per channel**, which is what brings the colour
  back — a per-channel contrast curve stretches the distance between channels as
  well as between tones, and that is perceived as saturation.

The safety argument is the *placement*, not the arithmetic. Tone rides with
`OutputSpace::applies_curve()`, so it is on for `--srgb` and off for
`--linear-srgb`, camera-linear and `Develop::measurement`. **Every number in the
corpus is still measured on exactly the pixels it was measured on before, and
both byte-freeze rows still hold.**

### Result

Both arms were rendered from binaries built from **one source tree differing
only in `image_out.rs`**, so the merge code is byte-identical across them. This
matters: three renders of one command previously produced three different files
because other agents landed builds mid-run.

| | before | after |
|---|---|---|
| black floor (p0.1, R/G) | 5.1% / 6.2% of range | 0.0% / 0.3% |
| white (p99.9, R) | 79.6% | 95.8% |
| pixels blown in all 3 channels | 0.000% | **0.000%** |
| pixels crushed in all 3 channels | 0.000% | 0.118% |

0.118% crushed is the 0.1 percentile that was asked for, plus the S-curve's toe.
Nothing is blown.

But the numbers are not the argument. **Look at
`C:\dev\strehl-out\tone-ab\before-view.png` and `after-view.png`.** Before: the
petal is a flat grey-green, the anthers are olive, the frame has no depth.
After: the petal is white, the anthers are yellow-green and separated, the tips
are translucent. It is a photograph.

---

## 9. The gallery — the thing the owner opens

Every full-frame image this project produced had coloured ROI rectangles and
text labels burned into it, and those were the images the owner was shown. He
had never once seen a clean render of his own photographs. `crop_set.py full`
drew the boxes unconditionally into a directory called `full`, which reads like
a deliverable and was treated as one.

Worse, there was no way to look at the product at viewing scale at all.
Judgement happened at 100% crops and through scalars — which is precisely how a
veil over every frame survived §8 for so long.

```powershell
pwsh -File scripts\gallery.ps1 -Exe <pinned strehl.exe>
```

Renders every subject in `D:\personal\macro`, full frame, through the real Rust
develop path, downsampled to 2400 px long edge, as clean JPEGs in
`C:\dev\strehl-out\gallery\`. Beside them:

- `RUN.txt` — the binary's path, size, mtime and **SHA-256**, and the exact
  render command. Without this a gallery is unfalsifiable: you cannot tell an
  improvement from a different binary.
- `manifest.tsv` — subject, frames, seconds, peak MB, exit code, and the tone
  parameters chosen for that image. Written every iteration, so a run that dies
  at subject 19 still leaves 18 rows of evidence.

`-Only <substring>` renders one subject for iteration. `-KeepTiff` keeps the
16-bit intermediates.

**Annotated variants are a sibling, never the gallery.** `crop_set.py full` now
writes to `annotated/` and takes `--clean`. Those previews deliberately stay on
the *linear measurement view* rather than the product's tone rendering, because
they are compared against a frozen baseline and the comparison only means
anything if the view is fixed. So an annotated preview looks flatter than the
gallery **on purpose**: the gallery shows the photograph, the overlay shows the
measurement.

`gallery_view.py` does nothing to the pixels but downsample and drop to 8 bits.
If it started adjusting images the gallery would stop being a picture of what
`strehl` produces, which is the only thing it is for. It reads with `tifffile`
and asserts `uint16`; `PIL.Image.open` silently downconverts 16-bit RGB TIFFs
and has corrupted results in this project before.

### The run

`C:\dev\strehl-out\gallery\`, binary SHA-256
`AE5F7FA2…` built from a `git archive` of `5d7a7ba`.

**26 of 26 subjects rendered, every one exit 0.** No crash, no hang, no OOM, no
garbage. 4825 frames, roughly 55 minutes wall clock on a machine simultaneously
running two other implementation agents, so the per-subject times in
`manifest.tsv` are contended and are **not** a speed measurement.

`tweezers-cpl` rendered in 70 s, 100 frames, exit 0. It has now been rendered
successfully three separate times. It was never broken: `--sat` is a flag of
BUILD-HALO's own `experiments/BUILD-HALO/measure.py`, not of `strehl`.

The `peak_mb` column is **unreliable and should not be quoted** — the 250 ms
sampler misses the peak on short renders, which is why some rows read 5–11 MB.
Treat only the large values as meaningful, and take a real measurement before
anyone claims a memory number.

### Hot pixels: still deferred, now checked against the pictures

ORCH's condition was that repair stays deferred unless the gallery shows them.
It does not. `foam` and `coffee-bubbles` — the two ISO 1000 subjects, the only
two where §5 measured hot pixels as material — show no hot-pixel trails at
viewing scale. Caveat stated plainly: the gallery downsamples about 3×, so this
is a statement about **viewing scale**, not about 100% crops. The §5 numbers
still stand at 100%.

### Verdict after the tone fix

The tonal defect is fixed. `pencil-steep-angle-cpl` and `112MSDCF` are, tonally,
photographs anyone would be happy to print — deep blacks, saturated colour,
detail that reads as detail.

**But the stacks are still not print-worthy, and the reason is now easier to see
than it has ever been.** Removing the veil removed the thing that was masking
the halo. On `coffee-bean` the bean silhouette carries a **pink-magenta glowing
rim** against the white background, with a bright band outside it, running the
entire circumference. On `bee-1-cpl` every leg, every antenna and the whole hair
mass carry a bright outline, and to the left of the left legs there are pale
**outline ghosts** — the leg edge appearing more than once.

Two things in that are worth routing to BUILD-HALO:

1. **The halo has a colour cast**, it is not a neutral luminance rim. A
   magenta-tinted halo is per-channel asymmetric, which is a constraint on what
   can be causing it.
2. **At viewing scale it is not "a tight bright rim".** It is the first thing
   the eye lands on. That description came from crop-level judgement; the whole
   frame does not support it.

This is the gallery earning its keep on the first run: it is the same defect
already known, but its severity and its colour were both wrong in the record.

---

## 10. The blue clipping — and how my own tone fix quadrupled it

I found this while diagnosing the haze, logged it as "a gamut question, not
tone", and moved on. That was the wrong call and ORCH overruled it. What
follows is what measuring it actually showed, including the part that is my
fault.

### 10.1 Three candidate causes, and how they were separated

A channel clamping to zero on 12% of a frame has at least three explanations
and they want three different fixes:

1. **Genuinely out-of-gamut colour** — the scene contains saturated hues
   sRGB cannot hold. Fix: map the gamut.
2. **White-balance applied on the wrong side of the matrix.** Fix: reorder.
3. **A wrong matrix.** Fix: correct the matrix.

`experiments/BUILD-RENDER-gamut/diagnose.py` separates them by asking *where*
in the frame the negatives are and *how far* under they go, because the three
causes have incompatible signatures. An ordering or matrix error is systematic:
it would show up on every subject and it would be worst where the signal is
strongest. Real out-of-gamut colour is the opposite — it lives on the brightest,
most saturated pixels and goes deeply negative.

On `flower-inner-edge-cpl`, before the tone stage:

| quantity | value |
| --- | --- |
| pixels with blue < 0 | 11.80% |
| median excursion | −0.0018 |
| p1 excursion | −0.0065 |
| min | −0.0231 |
| below −0.01 | 0.002% of frame |
| below −0.05 | 0.000% |
| of the negatives: dark / mid / **lit** | 10.7% / 89.3% / **0.0%** |

Not one lit pixel is out of gamut. The excursions are a thousandth of the
range. And the decisive control: **`coffee-bean` and `lavendar-cpl` show 0.00%
negative blue** on the same code path. A wrong matrix or a wrong ordering
cannot be subject-selective, so causes 2 and 3 are dead.

What is left is arithmetic. The camera-native medians are R 0.1083, G 0.0938,
**B 0.0341** — blue sits at a third of red, because this is a yellow-green
scene. The blue row of the forward matrix is `1.3283·B − 0.3235·G`, so wherever
green exceeds roughly four times blue, the result is negative. That is not a
bug; it is what a colorimetric matrix does at the dark end of a scene with
almost no blue in it. sRGB's blue primary cannot be reached from those camera
values without going outside the cube.

### 10.2 The part that is my fault

ORCH predicted the tone fix would make this worse. It does, by more than either
of us guessed. `experiments/BUILD-RENDER-gamut/tone_interaction.py`:

| subject | blue < 0 before tone | after tone |
| --- | --- | --- |
| `flower-inner-edge-cpl` | 11.80% | **40.49%** |
| `coffee-bean` | 0.00% | 2.73% |
| `lavendar-cpl` | 0.00% | 0.41% |

The mechanism is direct: the tone stage subtracts a black point in linear
light, blue is the channel already nearest zero, so subtraction necessarily
pushes more of it under. Red moves 0.30% and green 0.05% by the same operation.
The asymmetry is the whole story.

`lavendar-cpl` is the interesting one. Only 0.41% of pixels move, but they move
by p99.9 = **0.5127** — half the range. That is the other population entirely:
genuinely saturated purple, genuinely outside sRGB, and catastrophically
damaged by a clamp. One frame contains both failure modes and they need the
same fix to handle both.

### 10.3 The defect is the response, not the excursion

A per-channel clamp is the one answer that is certainly wrong, for two separate
reasons:

- **It moves hue.** It changes only the offending channel, so the ratio between
  the other two shifts relative to it. The colour that comes out is not a less
  saturated version of the colour that went in; it is a different colour.
- **It moves luminance.** Raising a negative blue to zero makes the pixel
  *lighter* than the value it stands in for. On `flower-inner-edge-cpl` that is
  40% of the frame being silently lifted — which is, in miniature, the same
  class of defect as the veil in §8.

Measured luminance error against the unclamped ideal, p99.9:

| response | luminance error |
| --- | --- |
| per-channel clamp | 0.00117 |
| luminance-preserving map | **0.00000** |

Exactly zero, by construction, not by tuning.

### 10.4 The map

`gamut_map()` in `image_out.rs`: blend toward the grey of the same BT.709
luminance, by the smallest `t` that brings every channel inside `[0, 1]`.

For `v[c] < 0` the requirement is `t ≥ −v/(y−v)`; for `v[c] > 1` it is
`t ≥ (v−1)/(v−y)`; take the max over channels, guard the denominator. Hue
direction survives because a straight line to the neutral axis in linear light
is a desaturation and nothing else. Luminance survives because the endpoint has
the luminance of the start. Both ends of the range are handled together, since
a highlight pinned at 1.0 is the same defect as a shadow pinned at 0.0.

Where nothing is out of gamut it is **exactly** the identity — the same safety
property `clip_highlights` has, tested over an 11³ lattice.

### 10.5 What it does to the picture

Muted, which is correct for a fix whose job is to stop a distortion rather than
add a look:

| subject | pixels changed | mean \|Δ\| on movers (R/G/B, DN16) | max Δ |
| --- | --- | --- | --- |
| `flower-inner-edge-cpl` | 40.48% | 136 / 84 / **0.1** | 27851 |
| `lavendar-cpl` | 0.76% | 371 / 106 / 671 | 42785 |

The blue delta of 0.1 on the flower is not a null result, it is the mechanism
made visible: because the blend is *minimal*, the negative channel arrives at
exactly zero — the same place the clamp put it. What changes is that red and
green come **down** to keep the luminance honest. The clamp was lightening 40%
of the frame; the map does not.

At full frame and at the worst-change crop on `lavendar-cpl`, before and after
are near-indistinguishable to the eye. That is the intended result. A gamut
map that visibly restyles the image is over-reaching.

### 10.6 Measurement neutrality, proven rather than asserted

The map rides with the tone rendering, so `--linear-srgb`, camera-linear and
`Develop::measurement` keep the per-channel clamp they have always had.
Verified on the exact frozen invocation `stack coffee-bean --limit 20
--gate 2.0`, against a binary built from the *same* HEAD: `480A6B81…7C51` both
arms, byte-identical.

That "same HEAD" qualifier is load-bearing. My first neutrality test reported
DIFFER, and it was wrong: the comparison tree predated a commit another lane
had landed, so I was measuring their change and attributing it to mine. HEAD's
own hash also moved between two builds of the same code during this session
(`C8A2995A` → `480A6B81`). **Every arm of a comparison must come from one
binary, built from a pinned `git archive` of an explicit SHA.** This is now the
third independent time that rule has been proven in this repository by
violating it.

### 10.7 Still open

`--linear-srgb` still hard-clips — 11.8% of blue on `flower-inner-edge-cpl`.
That is deliberate: it is the frozen measurement space and changing it would
move every stored number. But it means **colour measured there is clipped
colour**, and any future colorimetric claim taken in that space has to say so.
Flagged for ORCH rather than fixed unilaterally.

---

## 11. The regression guard

`couch-fibers-cpl` was audited and found genuinely good — sharp to individual
filaments, no artefacts. That makes it the control proving the core machinery is
sound and the remaining defects are localised to depth boundaries. It also makes
it the subject most likely to be damaged *silently*, because work aimed at a
depth boundary can soften high-frequency texture while the subject it was tuned
on improves.

`scripts/guard.py`, wired into `gallery.ps1`, compares it against a stored
reference on every run and prints `MOVED` or `held`. On a move it writes an
8× amplified difference map and a before/after strip, because a scalar cannot
distinguish an improvement from a degradation and this project has a documented
history of green numbers over bad images.

The reference was seeded from the exact gallery image ORCH audited, not from
the next render — a guard that quietly baselines itself against whatever it
finds is worse than no guard.

This is not hypothetical: BUILD-HALO's own texture guard rejected its halo fix
(`859edac`) for softening this subject, from the other direction, on the same
day.

---

## 12. The gallery as heartbeat — and what its first comparison found

Run 2 of the gallery, binary `DF209CE0…` pinned from `859edac`:

**26 of 26 subjects rendered, exit 0, 4825 frames, 59 min 26 s wall.**
Zero failures. `tweezers-cpl` rendered in 71 s — the fourth independent
demonstration that it was never broken.

Run 1 is archived at `gallery-history\2026-08-25-tone-fix\`, run 2 at
`gallery-history\2026-08-25-1327\`. `gallery\` is always the latest, so "open
the gallery" never changes meaning.

### 12.1 Seventeen of twenty-six subjects got softer

The point of keeping the runs is to be able to subtract them. Doing that for
the first time, on gradient RMS at viewing scale (run 2 ÷ run 1):

| subject | sharpness ratio | subject | sharpness ratio |
| --- | --- | --- | --- |
| `bee-1-cpl` | **0.9287** | `flower-bud-with-background-fern-cpl` | 0.9739 |
| `highly-angled-ruler-mm-cpl` | **0.9398** | `lead-1-cpl` | 0.9782 |
| `dry-erase-marker-head-cpl` | **0.9398** | `coffee-bean` | 0.9783 |
| `bee-2-cpl` | **0.9493** | `pencil-flatter-angle-cpl` | 0.9801 |
| `bee-3-cpl` | **0.9510** | `flower-bud-alone-cpl` | 0.9827 |
| `pencil-steep-angle-cpl` | **0.9578** | `foam` | 0.9874 |
| `couch-fibers-cpl` | **0.9604** | `flower-inner-edge-cpl` | 0.9877 |
| `leaf-2-cpl` | 0.9692 | `coffee-bubbles` | 1.0279 |
| `lavendar-cpl` | 0.9711 | (8 others) | 0.996–1.010 |
| `flowers-cpl` | 0.9726 | | |

Seventeen subjects lost sharpness. Nothing gained more than 2.8%. That is a
systemic loss across the owner's library in roughly two hours of work, and
nothing in the commit log announces it — the commits in that window are about
halos and about alignment priors.

This is the argument for the harness in one table. Every one of those changes
was reasonable, several were reported as improvements on the subject they were
aimed at, and the aggregate effect on the library was negative. No crop-level
report would have shown this, because no crop-level report covers 26 subjects.

### 12.2 The regression bisects cleanly to one commit, and it is not mine

`couch-fibers-cpl` is the do-no-harm control, so it is the one worth costing
properly. All arms rendered back-to-back, each from a binary built from a
pinned `git archive` of the SHA named:

| build | gradient RMS ratio vs the audited reference |
| --- | --- |
| `5d7a7ba` (the audited-good reference) | 1.0000 |
| `57e4554` — *halo: delete the noise-driven window shrink* | **0.9342** |
| `70934bb` — *sharp: track-smoothness prior on by default* | 0.9330 |
| `859edac`, my gamut map **off** | 0.9323 |
| `859edac`, my gamut map **on** (= the gallery) | 0.9376 |

**`57e4554` accounts for essentially the whole loss.** Everything landed after
it adds 0.2% more. The commit deleted the noise-driven focus-window shrink on
the argument that the geometric cap subsumes it; on this subject it does not,
and the cost is 6.6% of the gradient energy of the sharpest control in the
library.

My own change was ruled out by direct isolation rather than by argument: two
binaries from the *same* SHA `859edac`, differing only in whether `gamut_map`
is called, rendered back-to-back. It touches 0.26% of pixels on this subject
and moves sharpness by **+0.56%** — the wrong sign to explain a softening. The
0.26% is what the theory predicts: `gamut_map` is the identity unless a channel
leaves `[0, 1]`, and `couch-fibers-cpl` is a neutral white subject with no
systematically low channel.

At 100% on the sharpest tile (`isolate\couch-100pct-ref-vs-57e4554.png`) the
softening is visible, not merely measurable: filament edges are less crisp and
adjacent fibres blend into one another. Tile gradient RMS 1920.6 → 1827.1.

Routed to ORCH. `merge_cmd.rs` and `edgeaware.rs` are BUILD-HALO's lane and I
have not touched them.

### 12.3 What the pictures say now

The tone rendering is holding across the whole library — the run-2 images read
as photographs. The disqualifier is unchanged and it is not mine:

- **`coffee-bean`** has a bright pink-magenta rim tracing the entire silhouette
  of the bean against the white ground. At viewing scale it is the first thing
  the eye lands on. Tonally the bean is now excellent — rich browns, visible
  surface texture, real shadow in the crease — which is exactly what makes the
  rim so conspicuous.
- The **sharpness regression above** is now a second, independent disqualifier,
  and it is the more dangerous of the two because it is invisible on any single
  image. You cannot see 6% softer without something to compare against.

Verdict unchanged: **not print-worthy**, halo first. But the library is now
also moving in the wrong direction on sharpness, and that was only visible
because two dated runs existed to subtract.

---

## 7. Not done

- **Hot-pixel *repair* in the Rust IO path.** Characterisation is done and the
  site map is stored (§5); repair is deliberately deferred, with the measured
  reason given there. Detection is *not* a gap — it was measured and answered.
- The measurement-path colour tag and the highlight-ceiling loss in §4.
- The FOV upsample in §1.3.
- The silent-success-on-refused-alignment in §1.1.

### Note on the shared tree

At the time of writing, the working tree **does not compile**: `merge_cmd.rs`
calls `regularise_scaled` and `FocusField::compute_scaled`, which do not yet
exist in `focus.rs` / `merge.rs`. That is BUILD-HALO's lane mid-edit and is not
a defect I should fix. All verification above was therefore run in a scratch
copy at `C:\dev\strehl-out\verify-tree`, built from the live `image_out.rs`
plus **HEAD** versions of BUILD-HALO's four in-flight files, so the numbers
describe my change alone. No file outside my lane was modified to do this — the
restore happened in the copy, never in the repo.
