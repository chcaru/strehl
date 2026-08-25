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
