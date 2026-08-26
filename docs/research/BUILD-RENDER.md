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

> The byte-freeze claim here was checked by a run at the time. The identical
> claim later made in §8 was **not**, and is corrected there. The freezes were
> subsequently broken by `debc8ea` in another lane.

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
corpus is still measured on exactly the pixels it was measured on before.**

> **CORRECTION.** The sentence that stood here also claimed "both byte-freeze
> rows still hold". That was **false when it was published**, in this document
> and in commit `5d7a7ba`'s message. I asserted it from the placement argument
> rather than from a run. V-TONE bisected the actual failure to `debc8ea`, a
> commit in BUILD-HALO's lane, and ORCH has routed the rebaseline there — so the
> break is not mine, but the unchecked claim was. What *is* confirmed, by hash
> rather than by reading, is the narrower and more useful statement: the
> camera-linear and `--linear-srgb` outputs are byte-identical between the tone
> and no-tone binaries, which is the property the placement argument actually
> supports. The lesson is the ordinary one and I had already been told it: a
> claim about bytes is only worth what the command that checked it is worth.

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

## 13. The tone defect — a scalar black point is not a black point

V-TONE audited §8's tone rendering, confirmed it as a large net win, and found a
HIGH-severity defect in it that destroys one subject outright. It is the more
instructive half of the tone story, so it gets its own section.

### What was wrong

`Tone::from_luminance` derives **one scalar** black point from `luma709`, and
`develop_pixel` then subtracted it from **every channel**:

```rust
(v[c] - t.black) / (t.white - t.black)      // the defect
```

That does not preserve chromaticity. Subtracting a constant from R, G and B
changes their ratios — `(R−b)/(G−b) ≠ R/G` — and the error explodes as a channel
approaches `b`. On a saturated subject the weak channels sit *below* the
luminance-derived black over most of the frame and hard-clamp to zero.

`coffee-bubbles` is dark red liquid with `black = 0.01563` sitting above its
green and blue nearly everywhere. At 88% zero-blue the render had stopped being
a colour image: under a fixed ×6 boost the untoned arm is a neutral, finely
detailed surface and the toned arm is a flat saturated single-channel red field
with the swirl texture and the scratches gone. On `foam` the crushed pixels were
not noise either — in the untoned arm their median was 3360 DN with a median 3×3
local range of 847 DN against a global median local range of 1774 DN, about half
the frame's typical structure. That was signal, and the tone deleted it.

### Why no test caught it, which is the part worth keeping

Every tone test in the crate used neutral or scalar-ramp inputs.
`the_tone_curve_does_not_tint_a_neutral` exercises only
`develop_pixel([v, v, v], …)`. My own doc-comment shows I considered the
luminance-scalar versus per-channel choice and picked the scalar *specifically*
so that it could not tint a neutral. That reasoning is sound as far as it goes.
The consequence I did not follow through is that a luminance-derived scalar black
cannot tint a neutral **by construction** — so the test could never fail, for any
implementation, correct or not. The suite proved the one property the design was
incapable of violating, and the guard I built is the reason the defect was
invisible.

This is the same shape as §8's blind spot and it is worth stating as one rule:
**a test whose property is entailed by the design cannot detect a defect in the
design.** §8 was invisible because every measurement was on linear crops; this
was invisible because every test was on neutral inputs. Both were manufactured
by a discipline that was otherwise correct.

### The fix

Place black and white on **luminance**, then scale the colour vector by the
ratio. `Tone::gain` computes `L_out / L_in`; `develop_pixel` multiplies all three
channels by that one number. Chromaticity is exactly preserved, hue and
saturation cannot shift, and no channel can be driven to zero unless luminance
itself is zero. The existing neutral test still passes and still means what it
meant. The per-channel display-space `s_curve` is kept — it is what restores
saturation, and it cannot zero a channel, since `s_curve(0) = 0` and it is
monotonic on `[0, 1]`.

Moving to per-channel black points from per-channel percentiles was considered
and rejected: it reintroduces exactly the neutral tinting the scalar was
protecting against, and on a saturated subject a per-channel percentile measures
the *scene* rather than the flare — the same defect in different clothes.

Two things on top:

- **`TONE_BLACK_FRACTION = 0.85`** — remove most of the floor, not all. The floor
  is flare, not black-level error: G 0.0035 > R 0.0017 despite red white-balance
  gains of 2.13–2.86×, which is the wrong direction for a DN offset. Flare is
  not uniform across the frame, so a single global subtraction is the wrong
  model for it regardless, and is always too large somewhere.
- **`TONE_TOE = 0.004`** — a soft toe instead of a hard clamp at zero, because a
  hard clamp is unrecoverable. The first toe I wrote made the knee proportional
  to the black point, which is fine on real captures but lifted the synthetic
  test's floor to 17% grey — worse than the original veil. The test caught it.
  The shipped form is a smooth maximum with a *fixed* narrow knee and a `.min(s)`
  cap; the cap says the tone may never brighten a pixel more than exposure alone.

A quieter bug the tests caught: the black fraction leaked into the white point.
Computing `white` from the *measured* floor while subtracting only a *fraction*
of it put the white percentile at 0.911 instead of 0.90 — a silent exposure
shift. `Tone.black` is now the effective post-fraction value.

### Result

Matched pairs, `--srgb`, both arms built from base `a59ad57` differing only in
`image_out.rs`, all ten renders back-to-back from those two binaries:

| subject | zeroG% | zeroB% | median luminance |
|---|---|---|---|
| `coffee-bubbles` | 1.5296 → **0.0004** | 88.0512 → **0.0229** | 0.0184 → 0.0348 |
| `foam` | 0.1519 → **0.0030** | 0.4499 → **0.0213** | 0.1001 → 0.1031 |
| `flower-inner-edge-cpl` | 0.0992 → **0.0000** | 40.3647 → **11.8354** | 0.3941 → 0.3958 |
| `couch-fibers-cpl` | 0.1339 → **0.0000** | 0.1116 → **0.0000** | 0.6922 → 0.6970 |
| `lavendar-cpl` | 0.1239 → **0.0000** | 0.4927 → **0.0000** | 0.7371 → 0.7404 |

Judged on the pictures, which is what decides it. Panels at
`C:\dev\strehl-out\vtone-ab\panels\`, three rows each: full frame, 100% crop, and
the same crop at ×6. The crop is chosen automatically as the tile carrying the
most zeroed pixels in the *before* arm, so the comparison is forced onto the
ground where the defect actually lived rather than onto flattering ground.

- **`coffee-bubbles`** recovers. The before's ×6 crop looks contrasty, but that
  contrast is manufactured by clipping — values slamming into zero create edges
  that are not in the scene. The after has genuine three-channel structure and
  the surface mottle is back.
- **`flower-inner-edge-cpl`** keeps §8's confirmed win intact: full frames are
  indistinguishable at viewing scale and the median luminance moves 0.4%. The
  anthers read slightly less electric-yellow, which is blue being restored.
- **`couch-fibers-cpl`**, the do-no-harm control, holds — and at ×6 the colour
  fringing on the dark fibres is slightly *reduced*.
- **`foam`** holds, with more structure surviving in the deep cell interiors.

### The residual blue, and a metric that cannot see what it is being asked

`flower-inner-edge-cpl` returns to 11.8354% zero-blue, the genuine pre-tone
value, which confirms V-TONE's reading that the 40.5% was this defect and not a
gamut problem. The residual is **not** destroyed colour, and this is a trap worth
recording: `gamut_map` moves an out-of-gamut pixel by the *smallest* blend toward
neutral that brings it in range, which lands the offending channel **exactly on
zero**. A correctly boundary-mapped pixel and a hard-clamped one both read
`B == 0`. **`zeroB%` counts them identically and cannot distinguish them**, so it
must not be read as damage on its own — which is also why "0.26% of pixels moved"
and "11.8% of pixels are out of gamut" are both true at once: most excursions are
shallow enough that the blend moves R and G by less than one 16-bit step.

What the number *can* still say is where those pixels live, and that is worth
knowing: their median luminance is 0.3293 and 10.83% of the whole frame is
zero-blue above 20% luminance, with median R 0.3734 and G 0.3493. These are lit
midtone anthers, not shadows. They are outside sRGB and they are being held on
its boundary, correctly. The real remedy is a **wider output gamut** — Display P3
or ProPhoto — not a different mapping, since print gamuts exceed sRGB in exactly
this yellow-green region. That is a colour-management feature, not a bug fix, and
it is flagged in §7 rather than done here.

### Withdrawn: peak memory

V-TONE flagged `peak_mb` as not a measurement — 5 MB for a 205-frame 33 MP stack.
It is worse than that. Probed on identical work (`coffee-bubbles`, 19 frames, one
binary) across five runs and two polling methods — the cached `Process` object
with `Refresh()`, and a fresh `Get-Process` each poll — it reported **11, 16, 16,
84, 87, 163, 1180 and 1658 MB**. One run returned `PeakVirtualMemorySize64` as 0,
which is impossible for a live process, so the counters are not being read
reliably through `Start-Process` at all.

The column is **removed** from `gallery.ps1` and the figures in the delivered
render table are **withdrawn**, including the ones in §1. The reliable route is
for the binary to report its own peak via `GetProcessMemoryInfo` at exit, which
is a code change rather than a script change. Until then the honest statement is
the one that was always the point: nothing has ever run out of memory — 26/26
subjects, up to 299 frames at 33 MP, all exit 0.

### Per-channel clipping is now in the heartbeat

`manifest.tsv` gains `zeroRGB` and `blownRGB`, measured on the 16-bit render
rather than the JPEG, **per channel and never combined**. V-TONE's point stands
and generalises: an all-three-channels "blown" or "crushed" count conceals
single-channel clipping completely, and single-channel clipping is precisely the
shape this defect had. Had the gallery been reporting these columns, one glance
at `coffee-bubbles` at 88% zero-blue would have caught it the day it landed
instead of a verifier finding it by reading the code. The two implementations —
`gallery_view.py` and the independent `experiments/BUILD-RENDER-tone/vtone_ab.py`
— agree to four decimals on the same file.

Also from V-TONE and accepted: the `crushed 0.118%` figure in §8 does not
reproduce under the natural reading (V-TONE measures 0.0518%, and ≈0.105% only
under an undocumented 8-bit threshold). Treat it as unreliable; the per-channel
columns above supersede it.

---

## 14. The sharpness metric was reading the tone curve

§12's tripwire — gradient RMS at viewing scale, subtracted between two dated
gallery runs — reported **20 of 26 subjects "SOFTER"** on the run that carried
the §13 tone fix. It was substantially wrong, and the way it was wrong is worth
recording because the same trap is available to anyone who measures sharpness on
a developed image.

**Gradient RMS scales linearly with global contrast.** Multiply an image by 0.95
and the statistic reports 0.95, with no blur anywhere. A tone change and a
defocus are therefore *indistinguishable* under it. `TONE_BLACK_FRACTION = 0.85`
removes less of the flare floor than the previous code, which makes
`white − black` larger and the gain smaller, so the fix lowers global contrast by
1–3.5% across the library — and the tripwire dutifully called that a
library-wide regression and told everyone to stop and bisect.

The isolation was already available: the §13 A/B pair, two binaries from base
`a59ad57` differing only in `image_out.rs`. Measured on it —

| subject | raw | **norm** | global contrast |
|---|---|---|---|
| `couch-fibers-cpl` | 0.9806 | **1.0020** | 0.9787 |
| `flower-inner-edge-cpl` | 1.0247 | **1.0344** | 0.9907 |
| `foam` | 0.9906 | **1.0021** | 0.9885 |
| `lavendar-cpl` | 0.9701 | **1.0044** | 0.9658 |
| `coffee-bubbles` | 0.9549 | 0.9840 | 0.9705 |

— where `norm` is the same statistic after standardising each image to zero mean
and unit variance. Raw falls; normalised **holds or rises**. There is no blur.
`coffee-bubbles` is the one genuine drop and it is the correct one: its "before"
carried 88% zero-blue, and clipping manufactures edges, so removing the clipping
removes false high-frequency content. That is detail the render never had.

`trend.py` now computes both and **takes its verdict from the normalised ratio**,
printing the raw one beside it. A large gap between them earns the note
`tone only`, which is itself a useful signal: it says the tone moved and the
optics did not. Re-run on the same two directories, the count falls from **20
softer to 11**, and `couch-fibers-cpl`, `foam`, `lavendar-cpl` and
`flower-inner-edge-cpl` are all correctly reclassified — matching the isolated
A/B on every one.

Two consequences, and neither is comfortable:

- **The 11 that remain are real, and they are not mine.** That window contains
  commits from two other lanes. This is routed to ORCH rather than investigated
  here, because those files are not mine to bisect.
- **§12's finding inherits the caveat.** "17 of 26 softer, bisected to
  `57e4554`" was measured with the confounded statistic. That conclusion was also
  confirmed by looking at 100% crops, which is why I still believe it, but the
  *magnitude* quoted there should be treated as an upper bound until it is
  re-measured with the normalised ratio.

The general form is the one this project keeps re-learning: **a statistic
computed on a developed image measures the development as well as the thing you
meant to measure.** It is the same error as measuring quality on an `--srgb`
render, which this project already has a rule against, wearing different clothes.

---

## 15. The visible coloured speckles are lateral CA, and the correction was off

The gallery JPEG of `foam` has isolated magenta, orange and cyan dots scattered
over a subject that is physically black foam. ORCH's standing instruction on hot
pixels was that repair stays deferred *unless the gallery shows them*. The
gallery showed something. This is what it turned out to be.

### It is not hot pixels, and the null control is what says so

My earlier deferral quoted "0 material at ISO 100, 90-130 at ISO 1000". That was
misfiled. Re-reading `hotpixels/materiality.json`, the 90 and 130 are **`foam`
and `coffee-bubbles`** -- two of the three acceptance subjects -- with
`hot_max_dn` of 561 and **1255 DN against a 15871 DN range, i.e. 7.9%**, against
control p99 of 62 and 55. On its face that is a strong case to build repair.

It is still the wrong answer, and only the null control shows it. Detecting
isolated outliers on the camera-linear `foam` render (brighter than all eight
neighbours by >= 250 DN) and colocating them against the 8685 persistent-hot
sites from `D:\macro-dark-frames`:

| | hits | rate |
|---|---|---|
| speckles within +/-2 px of a persistent-hot site | 33 / 4000 | 0.83% |
| **random positions, identical detector and tolerance** | 31 / 4000 | 0.78% |

**Enrichment 1.06x. That is chance.** A hot map of 8685 sites will collect
speckles by coincidence, and without the random-position arm the 0.83% would
have read as confirmation and I would have built the wrong fix. Hot-pixel repair
stays deferred, now for a measured reason rather than an assumption.

### It is not demosaic either

Rendering `foam` with and without `--demosaic` (the second is quad-binned, with
no interpolation at all) and cropping the same region at 1:1: the fringing is
present in **both**, with the same sign and the same orientation. Demosaic is
exonerated.

### It is lateral CA, and the correction already existed

The corpus had this the whole time. SYNTHESIS fact 1414: lateral CA on this path
is *a clean one-parameter radial magnification error of -704.5 ppm in red, R^2 =
0.9969, worth ~3 output pixels at the corner*. Fact 1449 records that measured,
tested subsystems have **no consumer in the render path**.

`optics.rs` implements it and `merge.rs` and `align_cmd.rs` consume it, selected
by the `STREHL_FIX_CA` environment variable. Unset means silently off. It was
unset in `gallery.ps1`, in `render_all.ps1`, and in every render the owner has
ever been shown. The algorithm was finished months ago; nothing turned it on.

### Measured, two subjects, one binary, back-to-back

Mean `|R-G|` at strong edges, normalised by local green, by radial band --
camera-linear, never `--srgb`:

| subject | 0.00-0.17 | 0.17-0.33 | 0.33-0.50 | 0.50-0.67 | 0.67-0.83 | 0.83-1.00 |
|---|---|---|---|---|---|---|
| `flat-on-ruler-cpl` off | 0.070 | 0.074 | 0.106 | 0.150 | 0.164 | **0.227** |
| `flat-on-ruler-cpl` on | 0.068 | 0.075 | 0.084 | 0.086 | 0.087 | **0.089** |
| `foam` off | 0.167 | 0.209 | 0.278 | 0.348 | 0.418 | **0.461** |
| `foam` on | 0.148 | 0.125 | 0.127 | 0.126 | 0.124 | **0.152** |

The signature of a correct radial correction is not that a number falls. It is
that **the radial growth is removed and a flat non-radial floor is left behind**,
and that is what both subjects show. Corner improvement is -61% and -67%. The
residual flat floor is the achromatic edge chroma that is not radial in origin:
demosaic, noise, and axial CA.

`|B-G|` moves by under 4% in either direction, which is the correct behaviour
rather than a shortfall -- SYNTHESIS fact 1515 records that no blue lateral
displacement is supported on this path, and the profile corrects red only.

**`foam` is not a CPL subject**, so it doubles as the out-of-sample transfer
test for a profile keyed `a7c2-fe100gm-2xtc-x4cpl`. It transfers, which is what
a lens-plus-teleconverter aberration should do: a CPL is plane-parallel and adds
no radial magnification difference.

### The pictures, which are what decides

`experiments/BUILD-RENDER-hotpix/ca_ab.py` crops **fixed fractional ROIs**
weighted to the corners, because lateral CA is zero on axis and a comparison
that crops the middle of the frame is guaranteed to show nothing. The ROIs are
stated in the output so two runs are comparable, and they are not chosen by
searching for a flattering tile.

- `flat-on-ruler-cpl` corner BR: the dark bar has a cyan rim on one edge and a
  warm red rim on the other. With the correction on, both edges are neutral.
- `foam` corner BR: the bright cell-wall speculars go from red- and
  cyan-fringed to neutral silver. This is the gallery defect, resolved.
- **Centre is unchanged in both.** That is the built-in null: lateral CA is zero
  at the optical axis by construction, so a correction that changed the centre
  would be doing something other than what it claims. Detail is fully preserved
  at every radius -- it removes colour, not sharpness.

A residual rainbow remains on `foam`'s transparent cell walls. Part of that is
real dispersion in the material. Part is **axial** CA, which SYNTHESIS fact 1413
records as baked permanently into every render because the election is computed
from `green_luma` alone and the single winning index is reused across all four
CFA accumulators. That is the merge's lane, not mine, and it is routed rather
than touched.

### Wired

`gallery.ps1` gains `-FixCa`, defaulting to the owner's profile, recorded in
`RUN.txt`. Commissioned both ways before being believed: a deliberately bogus
key **fails the render with exit 1**, and the real key renders, so the variable
demonstrably reaches the binary rather than being assumed to. The binary
refusing an unknown key instead of silently rendering uncorrected is good design
by whoever wrote `profile_from_setting`, and it is what makes the negative
control possible.

Still an environment variable rather than a `--fix-ca` flag on the CLI. That is
the right next step for the product and it is in my lane; it is not done yet.

**Update: done.** `--fix-ca <PROFILE>` now exists on `stack`, commissioned four
ways rather than assumed — it appears in `--help`, a bogus key exits 1 with the
list of known profiles, the real key renders, and **the same subject rendered
with and without the flag produces different bytes** (`F4B35407…` vs
`F85A0950…`). The fourth is the one that matters: a flag that parses and does
nothing passes the first three, and this project has been burned by inert plants
before. It is deliberately *not* on by default, because the profile describes one
specific camera, lens, teleconverter and filter stack and applying it elsewhere
would add an aberration rather than remove one. `gallery.ps1` still passes the
environment variable, which keeps it working with older pinned binaries.
84 tests pass; the byte-freeze rows are untouched because the flag defaults to
`None` and sets nothing.

The `couch-fibers-cpl` guard is expected to fire on the next run. That is the
guard working: the develop path changed on purpose.

---

## 15b. The teleconverter caveat is detectable, and now enforced

ORCH corroborated the CA finding interventionally (`coffee-bean` EDGE chroma
−6.34%, `flower-bud-with-background-fern-cpl` −9.13%, flat placebo −0.41% and
+0.33%) and asked for the profile to be switched on in the gallery — where it
already was, defaulted since `b914f31`.

Carried with it was a caveat: the profile names a 2× teleconverter and "there
is no way to detect from the frames whether a given stack was shot with it."

**There is.** It is not even in the maker notes — `LensModel` is a standard EXIF
tag and it spells the converter out in full:

```
[EXIF] LensModel : FE 100mm F2.8 Macro GM OSS + 2X Teleconverter
[EXIF] Model     : ILCE-7CM2
```

`ILCE-7CM2` is the profile key's `a7c2`, and `+ 2X Teleconverter` is its
`2xtc`. Three of the key's four components are machine-checkable. Only the CPL
is not, and a flat filter is not a plausible source of a radial per-channel
scale — `foam` is non-CPL and the correction transfers to it at −61%.

### The corpus, surveyed per frame

Not one frame per subject — **every frame**:

| frames surveyed | distinct optical paths |
|---|---|
| **4825** | **1** — `ILCE-7CM2` / `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` / 200.0 mm |

So for this library the caveat is not merely detectable, it is **moot**: there
is no stack the coefficient fails to describe. That is a stronger statement than
the one the caveat asked for, and it took ninety seconds to establish.

### Made an invariant rather than a note

A caveat in `RUN.txt` has to be read by someone who is already suspicious, and
the failure it guards against is silent: applied to the wrong glass, a
per-channel radial rescale does not fail to help, it **adds** an aberration that
was never in the frame — a new defect wearing the appearance of a real one.

`gallery.ps1` now reads `Model` and `LensModel` from the first frame of each
subject every run and compares them against the path the profile names. On a
mismatch the correction is disabled **for that subject only**, and the reason is
recorded in the `ca` column of `manifest.tsv` and in that JPEG's own comment.
Failing to uncorrected is the safe direction: no correction is a known
quantity. Without `exiftool` the profile is applied as asked and `RUN.txt` says
`UNVERIFIED` rather than pretending a check happened.

Commissioned both ways, because a guard that never fires is indistinguishable
from a guard that cannot. A frame was copied to a scratch subject and its
`LensModel` rewritten to `FE 90mm F2.8 Macro G OSS`:

| subject | planted lens | `ca` recorded |
|---|---|---|
| `109MSDCF` | (genuine) | `a7c2-fe100gm-2xtc-x4cpl` |
| `coffee-bubbles` | (genuine) | `a7c2-fe100gm-2xtc-x4cpl` |
| `fake-lens` | `FE 90mm F2.8 Macro G OSS` | **`off:path`** |

`RUN.txt` named it without being asked: `PARTIAL: CA disabled on 1 stack(s) --
fake-lens [ILCE-7CM2 / FE 90mm F2.8 Macro G OSS]`. The other two were
unaffected, which is the part that matters — the guard is per subject, not a
global kill switch.

When BUILD-CHROMA's self-measured per-stack coefficient lands this check becomes
unnecessary for correctness, but it stays useful as provenance: the `ca` column
still records what was actually applied to each picture.

---

## 16. The gallery had no provenance and no atomicity

ORCH found `gallery\` holding two binaries' output at once: 14 JPEGs from one
pin and 12 from another, a `RUN.txt` asserting "subjects: 26", and a manifest
with 11 rows. Judgements were made on it and had to be discarded, because
nothing in the directory said which file came from which binary.

My own detached run then reproduced it exactly, which is the useful part: it
died at 11 of 26 on `dry-erase-marker-head-cpl` with
`memory allocation of 33003520 bytes failed` → Rust abort → exit
`0xC0000409`, and left `gallery\` holding 16 JPEGs from the pre-CA binary
underneath 10 from the CA binary. So this is not a rare race. It is what
happens *every* time a run does not reach its own cleanup code.

**That is why "be careful when overwriting" is not a fix.** Rendering in place
mixes precisely when the process is no longer there to tidy up. The failure has
to be made impossible, not detected.

### What changed

Every render now goes to `<OutDir>.staging-<sha8>-<stamp>\` and `gallery\` is
replaced **wholesale** at the end. A staging directory can only ever hold one
binary's output, so whatever reaches `gallery\` is coherent even if the run
died. The property being enforced is **coherence, not completeness**: a gallery
missing a subject is fine as long as it says so and nothing stale fills the
gap; a gallery holding two binaries with no way to tell them apart never is.

- **Per-file provenance.** `manifest.tsv` gains a `binary` column per row, and
  `gallery_view.py` writes the full binary SHA-256, the CA profile, the
  timestamp and the complete tone/colour description into the JPEG's own
  comment segment — then reads it back off disk and exits non-zero if it did
  not survive. One JPEG carried out of the directory can still say what made
  it. This also fixes V-TONE's "tone parameters are not in the file": `black`,
  `white`, black fraction and contrast now ride in the deliverable.
- **Two sentinels, opposite polarity.** `COMPLETE.txt` is written *last* and
  only on success, so a run that dies cannot claim to have succeeded.
  `INCOMPLETE.txt` is written *first* and deleted on success, so a run that is
  **killed** still leaves a directory that announces itself. `try/finally`
  cannot do the second one — nothing in-process runs when the process is gone,
  which is exactly the OOM-abort case above.
- **`RUN.txt` states what it achieved,** not what it intended: `subjects
  planned` and `subjects rendered: N of M` as separate lines, plus the failure
  list. The old file asserted a count it never reached.
- **`-Only` never swaps.** A subset promoted to canonical would delete every
  subject it did not render, which is the same mixing in a different order.
- **A totally failed run does not publish.** Zero coherent subjects does not
  beat the last full gallery.
- **A partial run publishes but keeps the fallback.** The previous gallery is
  moved to `<OutDir>.prev-<stamp>` and, when the new run is incomplete, is
  *kept* rather than deleted.

### Commissioned six ways, on a two-subject library

A miniature library of directory junctions (`coffee-bubbles`, `109MSDCF`) makes
the full swap path testable in ~2 minutes instead of ~50.

| # | scenario | required behaviour | result |
|---|---|---|---|
| A | clean full run | swap in, `COMPLETE.txt`, per-row `binary` | pass |
| B | `-Only coffee` | `gallery\` byte-identical, output left in staging | pass |
| C | every subject fails | `gallery\` byte-identical, not published | pass |
| D | 2 of 3 (corrupt RAW) | publish, `INCOMPLETE.txt`, `prev` preserved | pass |
| E | + a frameless folder | skipped and named in `RUN.txt`, not a failure | pass |
| F | clean run again | `COMPLETE`, `INCOMPLETE` gone, no leftover dirs | pass |

Test C is the one that mattered: it caught a real bug rather than confirming a
belief. `Split-Path $jpg -Leaf` throws on an empty string, so the **first**
failing subject threw out of the render loop, skipped the remaining subjects,
and never reached the reconciliation block — meaning the run that most needed
to announce itself was the one that could not. Fixed two ways: the per-subject
body is now wrapped so one bad subject costs only itself, and the loop-scoped
variables are reset each iteration so a failed subject cannot inherit the
previous subject's numbers into its own manifest row. That last one is the same
class of defect as the mixed directory — stale data wearing the right name.

A frameless directory is now skipped rather than failed (test E). Left in the
plan it fails every run forever, and a marker that is always on means nothing.

### Not fixed here

The OOM itself. The planner budgets 6144 MB assuming it owns the machine, and
four agents share it. `stack.rs` is my lane but a headroom check is a
behavioural change to the planner, and ORCH has not called the re-render yet —
flagged rather than done.

`peak_mb` was already gone before ORCH asked (`80a12d5`), removed for the same
reason: polled on identical work it reported 11, 16, 16, 84, 87, 163, 1180 and
1658 MB, and once returned 0 for a live process. A column that reads as
measurement and is not is worse than no column. Getting it right needs the
binary to report its own peak via `GetProcessMemoryInfo` before exit.

---

## 17. Where the tone rendering puts each subject, and one number that was stale

ORCH profiled the library and reported `coffee-bubbles` at median luma 0.016
with 63.9% of pixels below 0.02, calling it "independent confirmation at full
scale" of the black-point defect V-TONE found on a crop.

It reproduces exactly — **on a file written 74 minutes before the fix**.

| `coffee-bubbles` | median | <0.02 | zeroG | zeroB |
|---|---|---|---|---|
| `ORCH-tone\...-view.png`, 13:18 (**pre-fix**) | **0.0164** | **64.60%** | 56.17% | 82.89% |
| `gallery\...jpg`, 16:43 (**post-fix**) | 0.0313 | **0.60%** | 0.11% | 13.47% |

The chromaticity fix (`1cacb61`, 14:32) cut the crushed fraction **108×** and
the dead-green fraction **511×**. ORCH's other figures (`foam` 0.105 vs my
0.102, `fern` 0.875 vs 0.872, `flower-bud-alone` 0.935 vs 0.939) match the
current gallery, so a single stale file was mixed into an otherwise current
set — the same provenance failure §16 was written about, recurring in an
analysis directory that has no stamping either. It is not a lapse of care; it
is what happens to any directory of images that does not carry its own origin.

### `scripts/tone_profile.py`

Built as asked: median, p1/p99/p99.9, upper span and crushed fraction for every
JPEG in a directory, sorted by median so both tails are visible at a glance. It
**reports and never gates** (always exits 0) — a harness that fails the build on
a legitimately bright subject gets switched off, and then it protects nothing.

Live results across 26 subjects: 25 unflagged, one `WASHED`.

### The one flag is a false positive, and the reason matters

`flower-bud-alone-cpl`: median 0.939, upper span 0.040. My own tool flagged it
independently of ORCH, which was mildly convincing. **Then I looked at the
picture, and the picture disagrees.** The bud has near-black bract tips,
saturated greens and crisp trichomes — full tonal range where the subject is.
The compressed upper half is a white sweep, and a smooth white sweep occupying
a narrow band near white is what a white sweep *is*.

What actually reads wrong at viewing scale is two other things:

| measurement on the viewing render | value |
|---|---|
| backdrop, three corners | 0.9625 / 0.9583 / **0.9123** |
| dark veil outside the silhouette | ~0.10 display, over ~50 px |

The corner spread is **vignetting, not tone**: 0.05 of display range across a
plain white field, which is exactly the "dirty, uneven, chalky" impression, and
no black/white placement can fix an error that varies across the frame. The
outstanding **flat-field campaign is the fix for this**, and this is a concrete
reason to raise its priority — it cleans the backdrop without touching the
curve.

### Why I did not raise the white point, which would have "fixed" it

Lifting the sweep to clean white would remove the chalky look in one line. It
would also compress the rim into the same few percent as the backdrop and make
BUILD-HALO's defect substantially harder to see.

ORCH measured the tone curve amplifying the rim ~4× (+984 DN linear at d=6
against +3748 DN at d=10 in display), warned that shoulder shape trades
directly against halo visibility on bright backdrops, and said explicitly *"I am
not asking you to hide it."* Raising the white point on a white-backdrop subject
is precisely that operation. **The cosmetic fix for the wash and the concealment
of the halo are the same edit**, so the tone curve stays where it is until the
rim is fixed in the merge. Noted here so that nobody later reads "washed" in a
report and helpfully corrects it.

---

## 18. The guard was anti-correlated with its own purpose

ORCH found the `couch-fibers-cpl` guard firing `MOVED` on a clean `1cacb61`
pin, looked at the diff, and reported it as entirely edge-structured —
ambiguous between "the fibres got softer" and "the tone curve landed", because
raising contrast scales every edge amplitude. The diagnosis was right and the
consequence was the one that kills guards: it fires forever, and a guard that
always fires is worse than none, because it launders a real regression through
an alarm everyone has learned to ignore.

This is the **same confound already fixed in `trend.py`** (§14), where the
un-normalised form called a library-wide regression that was nothing but the
tone curve landing. `guard.py` never got the correction. That is on me: I fixed
the instrument I was looking at and left its twin alone.

### The verdict now comes from a tone-invariant statistic

`guard.py` decides on **contrast-normalised gradient RMS** — each image
standardised to zero mean and unit variance before the gradient is taken. A
monotonic global rescale divides out; a blur does not, because it lowers the
gradient far more than the variance. The raw pixel delta is still printed as
context for the human who looks at the picture, and a third verdict `held*`
was added for the honest middle case: *pixels moved, detail did not.*

### Commissioned before re-seeding, both directions

A guard that never fires cannot be told from a guard that cannot fire, so both
halves were planted. A linear contrast scale turned out to be the wrong null —
it clips on a real photograph, and clipping destroys detail, so the null would
have failed for a real reason at the wrong moment. The assertion caught it. The
planted tone changes are therefore strictly monotonic S-curves and gammas, which
is also what the real tone rendering is, and is the harder test: exact
invariance holds only for a linear rescale.

| arm | sharp ratio | verdict | raw mean Δ |
|---|---|---|---|
| identity | ×1.000 | held | 0.00 |
| S-curve t=0.35 | ×0.996 | held | **7.04** |
| S-curve t=0.60 | ×0.996 | held | **12.33** |
| gamma 0.85 | ×1.008 | held | 10.03 |
| gamma 1.18 | ×0.995 | held | 12.21 |
| blur σ=0.5 | ×0.886 | **MOVED** | **0.73** |
| blur σ=0.8 | ×0.724 | **MOVED** | 2.42 |
| blur σ=1.5 | ×0.495 | **MOVED** | 5.26 |
| unsharp +90% | ×1.497 | **MOVED** | 5.22 |

9 of 9. Worst null ×0.995 against mildest positive ×0.886, so the ×0.98
threshold sits four times the null noise away from one side and 5.7% clear of
the other.

**The right-hand column is the finding.** The old guard decided on that number.
It is **7.04 DN for a harmless tone change and 0.73 DN for a real blur** — ten
times more sensitive to the thing it should ignore than to the thing it exists
to catch. It would have ranked a genuine softening as a *smaller* event than a
tone tweak. Not a noisy instrument: an instrument pointed the wrong way. Nobody
had noticed because until the tone fix landed, nothing had ever exercised it.

Over-sharpening is now a regression too (×1.497 fires). Ringing on
high-frequency texture is a plausible way for a deconvolution lane to damage
this subject, and a one-sided guard would have called it an improvement.

### Re-seeded deliberately, with the reason stored beside it

`gallery-guard\RESEED.txt` records the source render, the binary SHA
(`1cacb61`, ORCH's clean `git archive` pin), the sha256 of the reference, the
commissioning table, and the caveat that `1cacb61` predates the lateral-CA
correction — so if the next CA-enabled run moves this, that is real information
about what CA costs in edge amplitude and should be looked at, not re-seeded
away.

---

## 19. Honest state of the product

Stated the way ORCH framed it, because it is a narrower and more useful claim
than "the output is bad":

**Sound on subjects without hard occlusion boundaries. Disqualified on subjects
with them.**

| judgement | subjects | by |
|---|---|---|
| print-worthy now | `113MSDCF` (frost dendrites, 63 frames), `119MSDCF` | ORCH, at 100% |
| sound machinery, localised defect | `couch-fibers-cpl`, `coffee-bubbles` | BUILD-RENDER + V-TONE |
| subject print-quality, silhouette disqualifying | `bee-1-cpl` — hairs and eye facets are there, and a hard bright outline traces the whole silhouette "like a badly cut-out sticker" | ORCH |
| tone extreme, but a false alarm | `flower-bud-alone-cpl` — §17 | BUILD-RENDER, by looking |

What changed the framing was the tone fix. The veil was masking the boundary
between "this subject is finished" and "this subject is not", so everything read
as uniformly mediocre. Removing it made the remaining defect legible and
**local**: the rim at depth discontinuities, which is BUILD-HALO's lane, plus
outline ghosting on `bee-1-cpl` routed to BUILD-SHARP as registration rather
than rim.

Two corrections to carry, both from ORCH via BUILD-HALO:

- **`C:\dev\strehl-out\gallery\` is not an unfixed baseline.** At `859edac`
  the adaptive-radius edge work was already default ON, so "the halo is
  undiminished" was measured on the *treated* arm.
- **`gallery\couch-fibers-cpl.jpg` from that run is the softened render** the
  guard rejected. It is not a texture reference. The guard was re-seeded from
  ORCH's clean `1cacb61` pin instead (§18), which sidesteps it entirely.

Nothing in my lane is currently the disqualifier. The remaining items I own are
cosmetic or preventative: vignetting on white sweeps (§17, wants the flat-field
campaign), `coffee-bubbles` residual zero-blue at 13.47%, and `109MSDCF` at
7.58% zero-red.

---

## 20. The correction is on by default, and blue now moves too

§15 found that lateral-CA correction worked and that nothing turned it on.
`b914f31` switched it on in `gallery.ps1`; `993f0cc` added a `--fix-ca` flag.
Neither was a fix. A flag declared `Option<String>` still defaults to `None`,
and the product still shipped the correction off — the difference was only that
the owner now had a thing he could type instead of a variable he could export.

`96571ee` moves the default into the binary. `align_cmd.rs:1393` called
`active_profile()`, which reads `STREHL_FIX_CA` and returns `None` when unset;
it now calls BUILD-CHROMA's `profile_for_capture_env`, which applies the profile
**iff the body model and composed lens id in the file match the ones it was
measured on**. `main.rs` needed no code change at all: `--fix-ca` already sets
the environment variable, so `--fix-ca off` routes through `profile_from_setting`
to `Ok(None)` and remains the escape hatch, and a typo still hard-errors. Only
its help text changed, because it described the flag as the way to enable a
correction that is now on.

Default-on is defensible **only because the guard is three-valued**. `Unknown`
declines. An unreadable file gets an uncorrected render, never a stranger's
measured aberration applied at full strength to glass it was not measured on.

### Commissioned on pixels, not on a log line

A log line saying "profile applied" is a claim the binary makes about itself.
Four arms from one pinned binary compared by file hash is a claim about the
image, and the two disagree exactly when the wiring is broken.

| arm | flag | `flat-on-ruler-cpl` | `foam` |
| --- | --- | --- | --- |
| default | *(none)* | `510A1DF0…` | `922E07E1…` |
| explicit | `--fix-ca a7c2-…` | `510A1DF0…` | `922E07E1…` |
| off | `--fix-ca off` | `201DAD59…` | `3D792AB5…` |
| typo | `--fix-ca not-a-profile` | exit 1, no output | exit 1, no output |

7/7 checks on both subjects. The identity pair is the load-bearing one:
*default ≠ off* alone is satisfied by any change at all, including a bug. Pairing
it with *default = explicit* pins down **which** of the two states the default
landed in.

### The radial-band table, re-run with `283ccf4`

ORCH predicted that BUILD-CHROMA landing `eps_b: None → Some(174.4e-6)` would
make `|B−G|` flatten the way `|R−G|` did, and that a failure would mean one of
the two lanes was wrong. Measured in camera-linear, never on an `--srgb` render.

| subject | channel | centre (null) | corner | growth centre→corner |
| --- | --- | --- | --- | --- |
| ruler | `\|R−G\|` | 0.07036 → 0.06803 | 0.22684 → 0.08810 (**−61.2%**) | 3.22× → **1.29×** |
| ruler | `\|B−G\|` | 0.04187 → 0.04089 | 0.10555 → 0.06292 (**−40.4%**) | 2.52× → **1.54×** |
| foam | `\|R−G\|` | 0.16682 → 0.14800 | 0.46104 → 0.15077 (**−67.3%**) | 2.76× → **1.02×** |
| foam | `\|B−G\|` | 0.14298 → 0.14041 | 0.22409 → 0.14071 (**−37.2%**) | 1.57× → **1.002×** |

Blue moved, from the <4% ceiling §15 reported to −40.4% and −37.2% at the corner.
The prediction holds.

**A free internal control came with it.** §15's red numbers were measured on a
pre-`283ccf4` binary: ruler 0.070→0.227 becoming 0.068→0.089, foam 0.167→0.461
becoming 0.148→0.152. The red columns above reproduce those to 3–4 decimal
places on both subjects. Since `283ccf4` only added `eps_b`, red *must* be
unchanged, and it is — so blue is demonstrably the only thing that moved between
the two binaries. That is a stronger statement than either table alone, and it
cost nothing.

The acceptance signature I set in §15 was that a correct radial correction does
not merely lower a number, it **removes the radial growth and leaves a flat
non-radial floor**. Foam now shows that for both channels: blue reads 0.14041,
0.13625, 0.13455, 0.13106, 0.12843, 0.14071 across the six bands — flat to
within the noise, growth 1.002×.

### What the pictures say, which is more than the numbers

`ca-ruler-283ccf4.png` and `ca-foam-283ccf4.png`, fixed fractional ROIs, 1:1.

In the corners of the **off** arm every bright grain on the ruler carries an
opposite-signed fringe *pair*, cyan on one flank and orange on the other, and the
dark bar has a cyan edge on one side and a warm edge on the other. On foam every
specular strut carries a hard red flank and a cyan flank. In the **on** arm those
are neutral.

The detail that matters: they are neutral, **not merely less red**. Correcting
red alone would have left a blue/yellow residual fringe of its own. It doesn't.
That is picture-level confirmation of `eps_b` that owes nothing to the table.
The centre control is visually identical in both arms on both subjects, which is
what a correction that is zero on axis has to look like.

Honest caveat, unchanged: this is a correction for a **lens**. It is orthogonal
to the halo and to the tone work and fixes neither.

### The byte-freeze move, and a defect the default flip created

One row moved: `coffee-bean-20-gate2-sidecar`. `coffee-bean-20-gate2-unaligned`
did not, and that is the localisation this project's freeze header predicts —
the correction is applied during **warp application**, so a row that applies no
warp cannot see it. A change that moved both rows would have been a merge-core
change and would not have been mine.

Attribution followed the standard BUILD-HALO set on this row: **isolate the
variable, do not blame a commit range.** Pinning a parent commit can only show
bytes differ *across* a boundary. From a clean `git archive` pin of `96571ee`,
re-rendering the row's own recorded invocation with `STREHL_FIX_CA=off`
reproduces the superseded baseline `6325922C…27D8F` bit-exactly, and unset
reproduces `88154E2D…461E` bit-exactly. Both arms are required — "off reproduces
the old bytes" alone is also satisfied by a build that ignores the flag and moves
nothing. As a side effect this clears every other commit since `2525e08`, and the
four files other agents had uncommitted in the shared tree at the time, of
touching these bytes.

**`RENDER_ENV` was missing `STREHL_FIX_CA`.** That is the same unrecorded-input
defect as the `STREHL_ALIGN` and `EDGE_AWARE` entries, with a twist that
generalises past this project:

> The variable is old, and the omission never bit while unset meant off, because
> the only reachable ambient state matched the recorded pipeline. **Defaulting it
> on turned a dormant unrecorded input into a live one with nothing in that file
> changing.** A clear-list is not made safe by being complete on the day it was
> written.

This is not hypothetical: `scripts/gallery.ps1` sets that very variable, so "ran
the gallery, then ran the tests, in one shell" is a real path to a mismatched
hash.

Commissioned rather than assumed, because a clear-list entry nobody exercises is
precisely the defect class ORCH named. With the entry removed and an ambient
`STREHL_FIX_CA=off`, the freeze test **fails** (exit 101, 1 failed); with it
present under the same pollution it passes 5/5. The mutation is anchored on a
unique full-line string and hard-errors if it does not land, and the source is
restored from a `$env:TEMP` copy and asserted byte-identical.

### The limitation, carried rather than buried

BUILD-CHROMA's caveat stands and default-on is written knowing it: **the gear
guard has never declined a real file.** All 26 corpus stacks are the same body,
lens and teleconverter, so the negative path has no natural test case. The three
synthetic negatives exercise the *matcher*; what is untested is the *parse* —
whether a genuine non-TC ARW yields `lens_type3 == Some(32893)` rather than
`None`. The guard is correct by construction, not by experiment. A short bracket
shot without the teleconverter is on the capture list and would settle it.

Note that §15b's per-subject EXIF check in `gallery.ps1` is a second, independent
layer over the same question, and it *has* been exercised both ways against a
planted mismatch. It is not a substitute — it guards the gallery script, not the
binary — but the binary is no longer the only thing standing between a foreign
lens and a misapplied coefficient.

### The default flip broke my own guard, in the quietest possible way

§15b added a per-subject optical-path check to `gallery.ps1`: read `Model` and
`LensModel` from each subject's first frame, and disable CA for that subject
alone on a mismatch. It expressed "disable" by **removing** `$env:STREHL_FIX_CA`.

That was correct while unset meant off. After `96571ee` unset means *"let the
binary's own gear guard decide"* — so a subject the script had just rejected
would have been rendered **with** the correction and recorded `off:path` beside
it in the manifest and in the JPEG's own provenance comment. Not a crash, not a
wrong picture necessarily: a **provenance lie**, which is the exact failure the
per-subject check was built to prevent. The guard would have gone on reporting
that it was working.

Worth naming as a pattern, because it is the mirror of the `RENDER_ENV` finding
above and it landed within an hour of it: **flipping a default silently inverts
every consumer that encodes "off" as absence.** Both defects are the same shape,
and neither is visible in the diff that causes them. Grepping for the variable
finds the sites; only knowing what absence *used* to mean tells you which ones
are now wrong.

Fixed by saying it out loud — `$env:STREHL_FIX_CA = 'off'` — and commissioned on
a comparison that cannot be satisfied by a run that does nothing. Two subject
directories hold **byte-identical frames**; only the first frame's EXIF
`LensModel` differs, which is the one field the script probes and which the
binary does not read at all (it reads maker-note `LensType3`, unchanged in both).
Identical input, different label:

| check | result |
| --- | --- |
| planted labelled `off:path`, genuine labelled with the profile | PASS |
| `RUN.txt` names the rejected stack | PASS |
| **outputs differ** ⇒ the off branch really disabled CA | PASS |

5/5. Had the bug still been present, both arms would have received the
correction and the two JPEGs would have been **identical** — so this is a
positive and a negative control in a single comparison.

It also documents the intended relationship between the two guards, which read
different fields on purpose: the script reads the `LensModel` display string,
the binary reads `LensType3`. They almost always agree; where they disagree the
stricter must win, and an explicit `off` is how that is guaranteed rather than
hoped for.

### V-CA caught a third instance of the same defect, in my own flip

An independent auditor reviewed the flip within the hour and found that
`merge_cmd.rs` reported CA status by reading the **raw environment variable**
rather than the guard's decision. `"off"` is non-empty and not `"0"`, so it
satisfied the old guard clause. Both directions wrong, on the one switch the
flip makes load-bearing:

| operator sets | what the render did | what the log printed |
| --- | --- | --- |
| nothing | **CORRECTING** | `off (--fix-ca / STREHL_FIX_CA unset)` |
| `off` | **not correcting** | `CORRECTING, profile "off"` |

This is not a cosmetic slip, and the reason is uncomfortable: **the
recommendation to flip the default cited this very line as evidence that the
correction was active.** It happened to be true there only because the operator
had set the variable explicitly. Before default-on, switch state and behaviour
were the same thing and reading either was correct; the flip decoupled them and
left the reporting behind.

That is now three instances in one night of a single shape — `RENDER_ENV`,
`gallery.ps1`, and this — and they suggest a sharper statement of ORCH's defect
class than "no consumer in the render path":

> **Flipping a default silently invalidates every consumer that inferred
> behaviour from the switch.** Absence used to mean off; now it means *ask the
> guard*. Every site that read the variable to learn what the render was doing
> became wrong at that instant, and none of them appear in the diff that caused
> it.

Fixed by resolving through exactly the call the render makes, from the same
first frame.

**A second gap surfaced while fixing the first**, and it was the worse of the
two: only the **pyramid** prologue printed a CA line at all. The estimator — the
default path, the one the gallery uses — printed none. So on the backend most
renders actually use, a correction that is now always on was reported nowhere.
Both prologues now call one shared helper, because two copies are free to
disagree.

Verified against the **pixels** rather than against its own logic, which is the
thing that just failed. Three arms, two backends, one binary:

| arm | status line | output |
| --- | --- | --- |
| default | `CORRECTING … (gear matched; default on)` | `783868835F50906E` |
| `--fix-ca a7c2-…` | `CORRECTING … (operator asked for …)` | `783868835F50906E` |
| `--fix-ca off` | `off (operator asked for "off")` | `0D97FCAEE3474454` |

The two lines that claim to be correcting produce byte-identical output; the one
that claims to be off does not.

---

## 7. Not done

- **Hot-pixel *repair* in the Rust IO path.** Characterisation is done and the
  site map is stored (§5); repair is deliberately deferred. §15 makes the reason
  stronger than it was: the visible speckles that would have justified it are
  **not** hot pixels (1.06x enrichment over chance against a random-position
  null), so repair would not have fixed the defect anyone can see.
- **Axial CA.** SYNTHESIS fact 1413: baked permanently into every render,
  because the election is computed from `green_luma` alone and the one winning
  index is reused across all four CFA accumulators. It is the residual colour on
  `foam`'s transparent cell walls after lateral CA is corrected (§15). **This is
  the merge's lane, not mine** — routed to ORCH, not attempted here.
- **A wider output gamut.** §13 measures 10.83% of `flower-inner-edge-cpl` held
  on the sRGB blue boundary at above 20% luminance. That is correct behaviour
  for sRGB and it is still a real limit: those are lit midtone anthers whose
  colour the output space cannot represent, and print gamuts exceed sRGB in
  exactly that yellow-green region. Display P3 or ProPhoto as a selectable
  output space, properly tagged, is the remedy. Not a bug fix.
- **Peak memory reported by the binary itself**, via `GetProcessMemoryInfo` at
  exit. The polled figure was withdrawn in §13 as unreliable by two orders of
  magnitude, so there is currently no memory number at all.
- **Tone parameters in the gallery JPEG.** The TIFF carries them in
  `ImageDescription` since §13, but `gallery.ps1` deletes the TIFF unless
  `-KeepTiff`, so the artifact the owner actually opens still records nothing.
  Copying the description into the JPEG comment is the fix. Not started — and
  `gallery_view.py` must not be edited while a gallery run is in flight.
- The measurement-path colour tag and the highlight-ceiling loss in §4.
- The FOV upsample in §1.3.
- The silent-success-on-refused-alignment in §1.1.

**Done since this list was last written:** lateral-CA correction is now reachable
as `--fix-ca <PROFILE>` and is on by default in the gallery (§15).

### Note on the shared tree

At the time of writing, the working tree **does not compile**: `merge_cmd.rs`
calls `regularise_scaled` and `FocusField::compute_scaled`, which do not yet
exist in `focus.rs` / `merge.rs`. That is BUILD-HALO's lane mid-edit and is not
a defect I should fix. All verification above was therefore run in a scratch
copy at `C:\dev\strehl-out\verify-tree`, built from the live `image_out.rs`
plus **HEAD** versions of BUILD-HALO's four in-flight files, so the numbers
describe my change alone. No file outside my lane was modified to do this — the
restore happened in the copy, never in the repo.

## A/B: estimator vs pyramid, six subjects, one binary (gallery-ab)

Output: `C:\dev\strehl-out\gallery-ab\` -- `index.html`, `RUN.txt`,
`manifest.tsv`, `crops/` (48 composites), `fullframe/`.
Binary `e42ab13`, sha256 `9CDD4AB2AE7BFC58...`, only `--merge` differs.
12/12 renders ok, 3002 frames, ~31 min.

The defect is structural, not a veil. At 100% the estimator stamps whole
regions of a wrong frame in with hard straight geometric boundaries: a
rectangular block on flower-bud-with-background-fern-cpl, a lumpy white blob
that eats the bristles on dry-erase-marker-head-cpl, a ghosted double hair on
lavendar-cpl, and polygonal tone-patches tiling the background. The pyramid arm
has none of it, resolves the sharp site at least as well, leaves the
tweezers-cpl placebo unchanged, and is ~25% faster on 12/12 renders.

Two instrument defects were found by the rule failing on the subject that
mattered most, and are fixed in `709b535`: an all-zero silhouette grid made
`argmax` return the image CORNER and crops.py wrote that corner labelled
`silhouette` -- it now refuses; and the texture-adjacency radius is now a
fixed ascending ladder (7,15,31,63) reported in SITES.txt, because a single
constant returned EXACTLY 0.000% overlap on that subject against 0.332% on
bee-1-cpl, which `why_no_silhouette.py` attributed to a tolerance of 3579 vs
14416 leaving the mask hugging the blown core of the sweep.

`polarity.py` picks the subject list by rule rather than memory and
CONTRADICTS the polarity hypothesis: tweezers-cpl is dark-on-bright (0.357) and
is the good subject, flower-bud-with-background-fern-cpl is worst by eye yet
ranks last of eleven (0.192), and couch-fibers-cpl measures 0.004. Global
polarity does not rank this defect; silhouette perimeter against bright ground
is the better candidate and is untested.

---

## Ordering the 26, and two statistics that failed before one worked

**Task.** ORCH: emit a contact sheet ordered strongest-first, because the
shipped sheet is alphabetical and `the tool's best work sits between its worst`.
Supply a better ordering statistic than `contactsheet.py`'s p95 gradient
proxy, which ranks `foam` first at 0.216 -- ORCH's read being that `a p95
gradient cannot distinguish fine texture from read noise`.

### ORCH's premise about `foam` is REFUTED [MEASURED]

`foam` was described as `a dark, noisy, flat subject`. It is not noisy. At
100% it is a soap film with resolved thin-film interference bands, specular
rims and crisp bubble walls. Its noise fraction sigma/grad is the LOWEST in the
whole corpus at 0.072, while `flowers-cpl` -- the subject everyone agrees is
mush -- is the HIGHEST at 0.201. `foam` is dark and finely textured.

The p95 proxy IS fooled by noise (planted noise raises it +0.75%, confirmed),
so the diagnosis of the instrument was right. The diagnosis of the subject was
not, and the defect that actually promoted `foam` was sparsity, not noise.

Crops: `C:\dev\strehl-out\BUILD-RENDER-rank\look\`.

### Two failed statistics, each caught by a different control [MEASURED]

**v1, `P90(|grad|)/sigma`.** Passed the null. Passed ORCH's planted-noise arm.
Backwards: blur RAISED it **+2358%**, because Immerkaer's kernel is a high-pass
and blur drives sigma toward zero, so the ratio explodes exactly when the
picture gets worse. Only the positive control caught it. Had I run only the arm
ORCH asked for, it would have shipped looking green.

**v2, `detail/mean(luminance)`.** Passed all four arms and was still wrong on
the real corpus: ranked `coffee-bubbles` 1st and pushed `bee-3-cpl`, an
award-quality frame, to 12th of 26. Mechanism derived, then confirmed: for a
detailed fraction f of the frame, `detail ~ sqrt(f)*G` and `level ~ f*L`, so
the ratio goes as **1/sqrt(f)** and rewards SPARSITY. `coffee-bubbles`'s median
tile sits at level 0.0030 -- near black -- so the division put image-wide detail
that lives in the bright bubbles over an average dominated by black background.

### The lesson is bigger than either bug [ARGUED]

v2's four arms -- null, noise, blur, rival -- were **all same-subject
perturbations**. They establish how a statistic responds to a change in ONE
image and say nothing about whether two DIFFERENT images are comparable. A
ranking is precisely a cross-subject claim, so the commissioning did not test
the thing the statistic was for.

Corollary worth carrying: **a global gain and a genuinely dark subject are the
same multiplication**, so no global normaliser can distinguish them, and any
statistic invariant to the first is inflated by the second. v2's exposure
normalisation could not have been fixed; it had to be removed.

### v3, and its commissioning [MEASURED]

    resolved = P90 over 512px tiles of sqrt(max(0, mean|grad L|^2 - sigma^2))

in linear light, sRGB curve inverted exactly first. Per-tile, because a macro
stack is mostly out-of-focus surround by construction and a frame average
measures how much background a subject has, not how well it was resolved.

Six arms on `bee-3-cpl`, all PASS: null +0.00% exactly; planted noise
-0.09%; blur -30.42%; **sparsity -44.10%**; v2 +49.1% under sparsity; p95
proxy +0.75% under noise.

The sparsity arm's size was **predicted from the mask alone before measuring**
-- `sqrt(mean m^2)/mean(m) = +52.3%`, measured **+49.1%**. That agreement
confirms the mechanism rather than the symptom, and simultaneously proves the
smoothed tile boundaries add no gradient of their own.

Anchors after the fix: `bee-3-cpl` 12 -> **5** (bee-1 4, bee-2 6);
`flowers-cpl` **26/26**; `foam` 1 -> **11**; `coffee-bubbles` 1 -> **10**.

### A negative result on my own validation, kept [MEASURED]

`duplicate_coherence.py` tests whether near-duplicate captures rank together.
Pre-registered filename-only grouping: v3 gap 6.000 vs chance 9.000, **p=0.054
-- a miss** against the declared 0.01 bar. Excluding `MSDCF` (Sony's DCIM
folder code, not a subject name) all three statistics pass and the **retracted
v2 comes out tightest**, 2.833 against v3's 3.000. The ordering reverses
between arms.

The test is confounded by construction: near-duplicates share darkness,
sparsity and texture, which is exactly what every candidate statistic keys on.
**It is not evidence for v3 and must not be cited as such.**

### Presentation path

`finalpass.ps1` now emits master + faithful 8-bit viewable + graded
presentation JPEG + manifest columns. `New-Presentation` is idempotent and
runs on the RESUME branch, without which a once-failed grading could never be
repaired -- the master would exist, the subject would skip, and the failure
would be permanent and invisible.

Commissioned: faithful vs graded sha256 **DIFFER** on both smoke subjects
(a "graded" file that is not graded is the V-TONE defect one file over);
re-run reports skip/skip.

**Observation ORCH should weigh:** the *faithful* `bee-3-cpl` is already
print-worthy -- every hair resolved, venation crisp, tarsal claws sharp, clean
field. The grade is a modest lift, not the difference between horrible and
award-quality. On this subject the render carries it, not the grade.

Artifacts: `C:\dev\strehl-out\BUILD-RENDER-present\contactsheet-ranked.png`
(26 tiles, graded, strongest-first), `ranking.tsv`,
`BUILD-RENDER-rank\look\` (100% crops).

---

## SHIP-V2: the full 26-subject render, and what it proved

Rendered 26/26 ok, 0 failed, 4,825 frames in **62.8 min** (0.78 s/frame), peak
189 MB per subject. One binary, built by `git archive` from `b9b6921` so no
other lane's uncommitted work could enter it: sha256
`CF33AE080F438C6473034EC5078D0AB4C0AA9B53421747A3F765008DDDF0D6E6`. Flags
identical on every subject: `--merge pyramid --pyramid-gate 4.5 --srgb
--auto-exposure`. Output `C:\dev\strehl-out\SHIP-V2`.

### The headline result: byte-identical to SHIP-V1 on all 26 [MEASURED]

sha256 of every master against its SHIP-V1 counterpart: **identical 26,
differs 0, missing 0.**

This is not trivial, and I checked that before reporting it. **51 commits
touched `crates/` in the preceding 24 hours**, across `main.rs`,
`merge_cmd.rs`, `pyramid.rs`, `merge.rs`, `stack.rs`, `optics.rs`,
`restore.rs`, `edgeaware.rs`, `halo.rs` and `image_out.rs` -- the whole shipped
render path. The output did not move by one byte.

Three consequences, in descending order of how much they should change
somebody's plan:

1. **The owner's verdict was formed on exactly these pixels, and no re-render
   can address it.** Only the pending work -- restoration wiring, hull-clamp
   policy -- can change what he is looking at. Re-rendering is not a lever.
2. **SHIP-V1's provenance gap is now closed from the other end.** Its
   single-binary claim rested on file mtimes (a contiguous 27.6-min pass, max
   gap 2.5 min), which is consistent with one build but is not evidence of one.
   All 26 of its masters are now shown to be bit-reproducible by one named
   binary. Whatever built it was functionally identical on this path.
3. The project's own `crates/strehl-cli/tests/byte-freeze.rs` exists to enforce
   exactly this stability on one frozen stack. This is an independent instance
   of the same check across 26 real subjects.

### A bug that would have destroyed the gallery, found by smoke-testing first

`finalpass` names masters `<subject>--<arm>.tiff` (so `accept.py` can group
arms); presentation JPEGs are `<subject>.jpg`. The ranking key therefore
carried the arm suffix and matched no image. The one-subject smoke reported
`placed 0  missing 1`; at full scale that is **a 26-tile sheet of MISSING
tiles**, delivered to the owner. SHIP-V1's masters have no arm suffix, which is
why it had never surfaced.

Fixed with `--strip-arm`, off by default so existing rankings keep their
identities, with collisions fatal rather than last-write-wins. Commissioned:
plant (`coffee-bean--ARMA` + `--ARMB`) fires and names both files, exit 1;
null (two distinct subjects) does not fire and falls through to
`ranked 0 / failed 2 / total 2`.

**The transferable part is not the bug, it is that a 30-second smoke on the
smallest subject caught a defect that a 63-minute run would have delivered.**

### What I saw at 100%, as pictures [MEASURED by eye, on masters]

- **`bee-3-cpl`** -- wing membrane and venation. Every microtrichion is a
  distinct stroke; veins crisp. Critically, **no rim on the dark-vein against
  bright-membrane boundaries**, which is precisely the geometry that produces
  one. Print-worthy without qualification.
- **`tweezers-cpl`** -- ground-metal striations individually resolved, tip
  clean against dark ground, no rim. Print-worthy.
- **`highly-angled-ruler-mm-cpl`** -- **confirms ORCH's caution independently.**
  Sharp at 1:1, individual machining striations resolved, crisp graduation
  edge. It reads poorly on every thumbnail only because it is grey-on-grey.
  A contact sheet cannot carry a print verdict.
- **`flower-inner-edge-cpl`** -- soft at its own best tile. But **no hard
  bright rim on the silhouette**: the veil defect does look genuinely fixed.
- **`flowers-cpl`** -- at its *own maximum-detail* tile it is a granular wash
  with wholly unresolved pollen. Visibly mush even at thumbnail size.

### The presentation problem I would not fix unilaterally

The sheet opens with **`flat-on-ruler-cpl`, a calibration target**, and then
`tweezers-cpl`. Both are correct rankings -- they genuinely carry the most
resolved detail -- and both are *test targets*, so a photographer's first
impression is of a machine-shop chart. The award-quality bees sit at #4-6,
below the first row. The statistic ranks resolved detail, which is what it
claims and not photographic interest; reconciling those two is a product
decision, so it is flagged rather than taken.

Near-duplicate captures also occupy adjacent prime slots (#9/#12 wrapped-text,
#18/#19 pencil, #20/#21 MSDCF, #13/#17 leaf, #14/#24 flower-bud), spending the
top of the sheet twice on the same subject.

---

# Colour management on the output path: real ICC profiles

**Commit `96b7e119`. All MEASURED unless marked ARGUED.**

## The defect, as the code itself had already stated it

`image_out.rs:118-129` diagnosed this and never acted on it: the colour space
was declared only in `ImageDescription`, a human-readable text tag that no
colour-managed application reads. ORCH confirmed it on a shipped master --
`bee-3-cpl.tiff`, `ICC profile present: False`. A correct sRGB render and a
camera-native render were therefore **byte-indistinguishable to any tool that
opened them**, and for the camera-native file every reader would assume sRGB
and be completely wrong.

## What was decided, per render path

`color_description` has four cases. Two are colorimetric and two are not.

| `(matrix, srgb)` | render | profile | why |
| --- | --- | --- | --- |
| `(Some, true)` | `--srgb` | sRGB v2, 2716 B | defined space, so state it machine-readably |
| `(Some, false)` | `--linear-srgb` | sRGB primaries + identity TRC, 696 B | same primaries, gamma 1.0 |
| `(None, true)` | camera + curve | **none** | no characterisation exists to be truthful about |
| `(None, false)` | camera-native | **none** | ditto; this is the byte-frozen measurement file |

**The camera-native `None` is a deliberate answer, not an unhandled case.**
`Develop::matrix`'s own documentation says `None` also means "the decoder has no
characterisation for the body", so there is nothing to build a truthful profile
from. Writing sRGB there would replace a loud text warning that a human can read
with a machine-readable assertion a RIP obeys silently -- converting a visible
mislabel into an invisible corruption, which is strictly worse than today.

Other decisions: **v2, not v4** -- a v4 profile a RIP silently ignores is worse
than a v2 it honours. **Constructed, not vendored** -- published IEC 61966-2-1
colorimetry, so there is no licence to check. **TIFF type UNDEFINED (7)**, per
the ICC technote, not the BYTE that `[u8]` encodes as by default; this needed a
`TiffValue` impl. **Creation date fixed at 2026-01-01**, not read from the
clock, because this project's epistemics rest on byte-freezes.

## Verification

Both arms were built from **one `git archive` of one SHA**, differing by
`image_out.rs` alone -- verified by hashing every file in both trees: **1 file
differs, 0 others**. The diff is **479 insertions and 0 deletions**.

- **Pixel null.** Decoded arrays, not file bytes -- adding a tag shifts every
  data offset, so a byte comparison would fail for the wrong reason.
  `--srgb`, `--linear-srgb` and camera-native all give **`max|A-B| = 0`** on a
  4688x7032 render. Only metadata moved: **+2728 / +708 / +0 bytes**.
- **Byte-freeze registry HOLDS**, both rows, identical size 49450019 B. Both are
  `srgb = no` and route the untagged writer, so they could not have moved.
- **Read back out of a real file** with `tifffile`, not asserted at write time.
- **Independent tools.** `exiftool` reports `ProfileDescription`, `ProfileVersion
  2.1.0` and the three matrix columns; Pillow/LittleCMS2 recovers the colorants
  and white point. Camera-native: "(no ICC tags reported)" from exiftool.
- **Potency control.** Same pixels, three embedded profiles, all transformed
  through LittleCMS to a *stock* sRGB profile:

  | embedded profile | mean shift | max | pixels moved |
  | --- | --- | --- | --- |
  | correct sRGB | **0.00 DN** | **0** | **0.0%** |
  | wrong: linear TRC | 50.39 DN | 73 | 99.5% |
  | wrong: R/B colorants swapped | 11.58 DN | 152 | 64.3% |

  The correct arm is **the exact identity against LittleCMS's own sRGB profile**,
  which independently validates the whole derivation: an implementation I did
  not write agrees the constructed profile *is* sRGB, to zero DN.
- **The unit tests are commissioned**: 6 planted defects (no chromatic
  adaptation, transposed matrix, TRC stored backwards, sRGB profile on
  camera-native, clock-derived date, stale size field) -- **6 caught, 0 missed**,
  and a comment-only null stayed green. `experiments/BUILD-RENDER-icc/commission.py`.

## Is sRGB the right MASTER space? A measurement.

Method: the delivered `--srgb` masters are already clipped and cannot say what
was lost, so camera-native and `--linear-srgb` were rendered **from one binary**
and the colour matrix recovered by least squares from unclipped pixel pairs.
The recovery is falsifiable against a prediction the *source* makes --
`camera_to_srgb` documents that every row sums to 1.

**The recovery is good to ~0.3%, not exact** (median residual ~1e-4, above the
1.5e-5 quantisation floor), so it is cross-checked by a **model-free** route: a
coloured pixel clamped to exactly 0 in the delivered `--linear-srgb` file *is*
out of gamut by definition, no matrix involved. The two routes **agree 9/9**.

Out-of-gamut share of coloured pixels:

| subject | sRGB | Display P3 | Adobe RGB | ProPhoto | model-free sRGB |
| --- | --- | --- | --- | --- | --- |
| `flower-inner-edge-cpl` | **9.73%** | 0.000% | **0.165%** | 0.000% | **10.71%** |
| `leaf-2-cpl` | 0.004% | 0.000% | 0.000% | 0.000% | 0.002% |
| `flowers-cpl` | 0.003% | 0.000% | 0.000% | 0.000% | 0.003% |
| other 6 incl. `bee-3-cpl`, `lavendar-cpl`, `flower-bud-alone-cpl` | 0.000% | 0.000% | 0.000% | 0.000% | 0.000% |

Cost of the clipping, CIEDE2000 on the affected pixels only (the metric was
validated against **Sharma et al.'s published vectors, max error 4.2e-5**,
before being used): `flower-inner-edge-cpl` median **0.46**, p99 **1.58**, max
**2.47**. Roughly one JND, on a contiguous tenth of the subject.

**Subset control.** The census used 24-frame renders. Re-rendering the headline
subject at full depth: **10.713% (24 frames) vs 10.608% (299 frames)** -- 0.105
points. The subset did not bias it.

**It is a picture, not a score.** `gamut-pictures/` flags the clipped pixels.
They land **exactly on the olive-yellow anther bodies**, tracing individual
structures, while the grey background and the green shadows between them are
untouched. At 100% the clipped areas are solid with a stippled boundary -- the
signature of a gamut wall. Mean clipped colour is R74 G71 **B0**: saturated
yellow, blue driven negative. A dead blue channel would not respect anatomy.

**Posterisation, the hazard ORCH named.** One 16-bit code step at mid-grey:

| space | dE per 16-bit step | the same step at 8 bits |
| --- | --- | --- |
| sRGB | 0.0047 | 1.20 |
| Display P3 | 0.0055 | 1.41 |
| Adobe RGB | 0.0056 | 1.44 |
| ProPhoto | 0.0076 | 1.96 |

At 16 bits every candidate is **130-210x below a JND**, so the risk does not
bite. At 8 bits ProPhoto is 2 dE per step and would visibly posterise.

### Recommendation

1. **Keep sRGB as the default master.** 8 of 9 subjects clip *zero* pixels, and
   it is the most compatible thing to hand a print shop.
2. **Add Display P3, not Adobe RGB, as the wide option.** This is the part that
   contradicts the reflex: the excursion here is saturated **yellow**, and
   measured, **P3 holds 100% of it while Adobe RGB still clips 0.165%**. Adobe
   RGB's extension is toward green/cyan and is aimed at the wrong direction for
   this corpus.
3. **ProPhoto buys nothing here** -- identical 0.000% to P3, with the coarsest
   quantisation. Not worth its hazards.
4. **Any 8-bit derivative must stay sRGB.** The posterisation risk is real, just
   not at 16 bits.
5. Adding a P3 output path means a new `OutputSpace` variant, which touches
   `main.rs` -- **BUILD-WIRE's file**. Routing decision is ORCH's.

**Scope caveat.** 9 subjects, not 26, chosen as the most saturated plus
controls. That biases the 1-in-9 rate **upward**, so the corpus-wide rate is
lower, not higher. ARGUED, not measured.

## Environment finding: `*>` corrupts `git archive | tar -x`

The first launch of the SHIP-V2-ICC render died with `tar.exe: Damaged tar
archive (bad header checksum)`, looping. Cause: wrapping the driver in
`powershell -File ... *> log` puts PowerShell's redirection in the path of the
**binary** stream between `git archive` and `tar`, and it re-encodes it. Same
class as the known `git show HEAD:path > tmp` corruption on this machine.

Measured both ways: with the redirect, endless bad-header retries; without it,
`rc=0` and **6842 files extracted**. Any harness that builds a pin must not run
under a global stream redirect.

## Correction (2026-08-26): two ORCH numbers retracted; my lever list shortens

ORCH retracted the "hull clamp costs 15.5% of microcontrast" figure (dead by its
own author in BUILD-HULL S17 `ba5f234`, independently refuted by V-HULLCOST
`6222142e` at ~3.1%) and the "88.8% of the clamp's change is in the 2px/4px
bands" figure (its instrument weighted band k by coefficient count, under-
weighting by 4^k). Neither number appears anywhere in this lane record and no
measurement of mine rests on either -- checked by grep over this file, not from
memory. The gamut census, the ICC pixel nulls and the potency control are colour
and metadata results; none is a sharpness statistic, so the claimed "15% haircut
upstream of every sharpness number" never bore on them.

One thing above **does** change. The entry at "Only the pending work --
restoration wiring, hull-clamp policy -- can change what he is looking at" named
two remaining levers on the owner's verdict. With KEEP THE CLAMP settled,
hull-clamp policy is off that list. The conclusion survives and sharpens: the
default-path pixels the owner judged are still not reachable by re-rendering,
and the sole remaining lever on them is BUILD-BLEND's base-band fix, since
BUILD-WIRE's restoration lands behind a flag defaulting off.

### MEASURED: the chromatic-aberration change lies outside b9b6921e..96b7e119

ORCH's still-valid warning is that two binaries built at different points in the
tree differ by a CA correction leaving green bit-identical while red moves up to
3902 DN, so cross-build RGB comparisons must be restricted to green. The
SHIP-V2 -> SHIP-V2-ICC pixel comparison in `verify_ship.py` is such a
cross-build comparison, and it does not need that restriction, because it came
back identical on the very channel the warning is about:

| | |
|---|---|
| SHIP-V2 binary | `CF33AE08...D6E6` at `b9b6921e` |
| SHIP-V2-ICC binary | `0B3B6F19...DBEC` at `96b7e119` |
| commits in window | 54 |
| `crates/` files touched | `image_out.rs`, `merge_cmd.rs`, `halo.rs`, `demosaic.rs`, `election_coherence.rs`, `lib.rs`, `merge.rs`, `restore.rs` |
| result, 26/26 subjects | max per-channel abs diff = 0 on R, G **and** B |

`verify_ship.py:96-100` takes the max over each channel separately and prints
"identical RGB" only when all three are zero, so this is a per-channel null and
not a luminance proxy. Two consequences. First, the CA correction did not land
in this window -- it is either before `b9b6921e` or after `96b7e119`, which
bounds it for anyone else pricing a cross-build A/B. Second, 54 commits touching
eight Rust files including the demosaic and merge cores moved the default-path
output by zero bytes, which is a third independent instance of the stability
already recorded above.

### Correction to my own report

I opened my last report to ORCH with "everything below is from one binary". That
is true of the ICC A/B, the potency control, the gamut census and the render
itself, but not of the SHIP-V2 pixel comparison, which is inherently two. The
scope of the claim was wrong even though its value was not, and ORCH had asked
every agent to state which comparisons were same-binary. Recorded here so the
imprecision is not inherited.

## MEASURED: lateral CA is ON in every shipped master, and it matters at the corners

ORCH proposed an A/B of `--fix-ca <profile>` against **unset**. That comparison
is degenerate and would have returned a null: unset IS on. The binary's gear
guard defaults the correction on when the gear matches, so both arms would have
carried it and the null would have read as "CA does nothing". The correct
disabled arm is `STREHL_FIX_CA=0`, which the binary acknowledges in its banner
as `off (operator asked for "0")`.

Rendered `foam` both ways from ONE binary (96b7e119) in `--linear-srgb`, so no
tone curve is in the way and no green restriction is needed.

Two instruments, and the first one FAILED ITS OWN CONTROL, which is why it is
recorded here rather than cited. A brightness-gated edge-chroma statistic gave a
61.7% corner reduction against a 12.1% centre control -- but its flat-region
control also fell 34.7%, only 1.8x less than the rims against a pre-registered
2x threshold. A CA warp resamples R and B, and resampling smooths noise by an
amount that grows with the shift, which grows with radius; that mimics radial
fringe removal exactly. The statistic could not separate the two and was not
cited. Its first version was worse still: it normalised by green over ALL edge
pixels on a dark subject, so it measured shadow noise, and its crops rendered
solid black. Looking at the picture caught that; the numbers had looked fine.

The number comes instead from ORCH's `ca_radial.py`, which passed its own
pre-registered controls including a sub-pixel plant, copied verbatim into this
lane as `ca_radial_foam.py` with only its two path constants changed (diff
proven to be exactly those two lines) because its input directory holds M114's
files and must not be clobbered:

| bin | r | n | median fringe delta | worse |
|---|---|---|---|---|
| NULL | 0.045 | 180 | -0.92% | 38% |
| r0.20 | 0.200 | 180 | -14.53% | 7% |
| r0.35 | 0.350 | 180 | -31.38% | 0% |
| r0.50 | 0.500 | 180 | -41.88% | 0% |
| r0.65 | 0.650 | 102 | -51.55% | 0% |
| r0.75 | 0.752 | 86 | -56.34% | 0% |
| r0.83 | 0.830 | 36 | -57.67% | 0% |

Monotonic in radius, null at the optical centre where lateral CA is zero by
construction, and worse in 0% of windows from r=0.35 outward. R/B opposition
falls 0.755 -> 0.526; opposition is R and B displacing in OPPOSITE directions,
which is the specific signature of lateral CA and the one thing resampling
smoothing cannot manufacture. This independently corroborates the registry's
61-67% claim on a different subject.

By eye at 1:1, which is the deliverable: at the corner the disabled arm carries
obvious cyan-teal and magenta fringes on the specular rims and the corrected arm
reads close to neutral. At the centre the two arms are indistinguishable. The
iridescent speckle inside the cells survives identically in both arms and at
both radii -- so the subject supplied its own discrimination exactly as ORCH
predicted: what the correction removed was aberration, and the real thin-film
colour is untouched.

Consequence: the shipped masters already carry this. Turning CA off would be a
57% fringe regression at the corners of a 61 MP frame examined at 1:1.

## Backend applicability in provenance: an absent stage is not a disabled one

MEASURED. Same binary (0B3B6F19), same subject, two arms.

ORCH read `STREHL_PHOTOMETRIC` and `STREHL_FIX_HALO` as quality switches
defaulting OFF, and my own sidecar was printing exactly the string that
supports that reading: `(unset) [built-in default: off]`. Both stages are
estimator-path; the shipping backend is the pyramid, which never reaches them.
"Off" and "not present on this path" are different facts and my provenance was
collapsing them into one line.

ORCH attributed this to the registry carrying no notion of backend. That is not
what the file says. `scripts/check-defaults.py` declares `Declared.backend` at
:130 (default `"any"`), populates `backend="estimator"` on five entries
(:172, :263, :425, :449, :466), and its own comment at :81 already uses the word
INAPPLICABLE. The field is consumed in exactly ONE place -- :782, which PRINTS
it. No check branches on it. So the data is correct and the consumer is missing;
that is a smaller fix than adding the notion, and it is ORCH's file.

`finalpass.ps1` now parses `backend=` alongside `default=` and reports every
switch against the backend the render actually ran.

Potency control, because a marker that paints everything says nothing:

| arm | flags | switches | set | INAPPLICABLE |
|---|---|---:|---:|---:|
| PROVTEST2 | `--merge pyramid` | 33 | 1 | **5** |
| PROVTEST3 | `--merge estimator` | 33 | 0 | **0** |

The five move to zero when the backend that can run them is the one that ran.
Within the pyramid arm the marker also discriminates: `STREHL_FIX_CA` is
`backend="any"` and is NOT marked, and still reads
`built-in default: on (gear-matched)`.

The set-and-inapplicable case is the one worth having: with
`STREHL_PHOTOMETRIC=1` exported, the pyramid arm prints
`= 1 [ENVIRONMENT -- and this harness does not clear it; INAPPLICABLE --
estimator-only, this render was pyramid]`. Both facts survive. A reader learns
the operator asked for it AND that it could not have acted, which is precisely
the pair of facts whose conflation cost this project an evening.

REGISTRY GAP, ORCH's file, not fixed by me: `STREHL_FIX_HALO` carries
`backend="estimator"` but `STREHL_FIX_HALO_DELTA` does not, so the delta still
prints as `built-in default: off` on a pyramid render. It is the same stage.
Five entries are classified; at least a sixth belongs.
