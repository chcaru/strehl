# M97 — the warped merge, independently verified, and a null with a mechanism

**Milestone:** M97
**Question as dispatched:** wire the M86 warp sidecar into `strehl stack`, so the
merge gathers every frame through its registration before merging it.
**Question as answered:** the wiring landed while I was building it. So: *is the
shipped registration correct, and does it measurably improve the photograph?*

**Headline (MEASURED):** the wiring is correct — it survives an inverted-warp
control, an identity placebo, a wrong-stack control and a whole-frame NaN sweep.
It also **does not measurably improve the photograph**, judged by a metric that
is demonstrably able to see 18 px of planted misregistration, and it costs
**2.58x** end-to-end. The most likely mechanism is named in §7 and it is
testable: the merge was **already** robust to smooth focus-breathing drift, which
is the only kind of drift these brackets actually have.

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

## 7. The mechanism: the merge was already robust to the drift it actually has

**DERIVED**, from measurements in hand; the falsifying experiment is named below.

The puzzle: the ruler metric sees **18 px of planted jitter** loudly (+4.25 px)
and **111 px of real unregistered drift** not at all (+0.04 px). A metric that
sees the small thing and not the large thing is either broken or is telling us
the two errors are *different in kind*.

They are. Focus-breathing drift is **smooth and monotone in frame index**:
consecutive frames are almost perfectly co-registered, and the 111 px (232.7 px
on bee-3) accumulates only across the *whole* sweep. Planted jitter is
**non-smooth**: adjacent frames disagree instantly.

`strehl`'s merge is a **noise-gated average**. It admits only frames the
calibrated noise model cannot distinguish from the elected winner — and the
frames that matter at any given output pixel are the ones *near that pixel's
winning focus index*, which are precisely the frames that are **already**
co-registered under smooth drift. The gate never had to fight breathing; it only
ever had to fight disagreement, and smooth drift produces very little local
disagreement.

The supporting `n_eff` (bee-3, MEASURED):

| arm | mean `n_eff` | `n_eff=1` % |
|---|---|---|
| UNALIGNED | 23.043 | 46.57% |
| **ALIGNED** | **19.182** | 51.15% |
| ZOOMNULL (matched null) | 18.622 | 50.67% |

Against the matched null, registration buys **+3.0% `n_eff`** — real, in the
right direction, and far too small to see. Against `UNALIGNED` it is a **17%
loss**, which is the resample's doing, not misregistration's.

If this is right, then registration **converts a large smooth error (232.7 px)
into a small non-smooth one** — the solver's 11.56 px held-out residual, which
is scattered, not monotone. The merge is more sensitive to the second kind. That
would explain every null in this report and in M86c's without either of us
having mismeasured anything, and it predicts alignment's benefit is close to a
wash on brackets whose only misregistration is breathing.

**The experiment that would falsify this:** plant a *smooth* ramp of the same
magnitude as the jitter (~18 px accumulated, monotone in index) and measure `S`.
The mechanism predicts the smooth ramp reads **near null** while the equal-sized
scattered jitter reads **+4 px**. If the smooth ramp also reads +4 px, the
mechanism is wrong and the nulls need another explanation. **I did not run this**
(§10) and it is the single highest-value follow-up in this report.

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

## 9. Two defects in the shipped code

### Defect 1 — rendering a bracket **writes into the read-only corpus** (MEASURED)

`align_cmd::sidecar_path` is `dir.join("warpmap.txt")`, and `load_or_solve`
caches a fresh solve there on a miss. `D:\personal\macro\` is the owner's
capture corpus and is read-only by rule.

**Measured:** `D:\personal\macro\bee-2-cpl\warpmap.txt` and
`bee-3-cpl\warpmap.txt` exist, created 02:58:34 and 03:12:36 tonight, by
`strehl stack` runs. **Merely rendering a photograph mutates the corpus.**

`align_cmd.rs` is not mine. Verbatim patch in §11.

Note the caching itself is *good* — a 7.2 s solve should not be repeated — the
defect is only the location.

### Defect 2 — one refused frame destroys the whole render (MEASURED, §5/P6)

Recommendation: **drop refused frames from the merge** rather than aborting, and
report the drop in the alignment line and in `n_eff`. Abort only if the placed
count falls below a floor. I have deliberately **not implemented this**: it
touches the fold/`n_eff` path in `merge.rs`, which M87 and M93 are both live in
tonight, and a 05:00 refactor of a contended file is how a good night becomes a
bad merge. Flagging beats breaking.

---

## 10. Not measured

- **The smooth-ramp plant of §7.** The mechanism is DERIVED, not MEASURED.
- **Graduation spacing** as a second geometry metric: the tick-detection
  instrument returned unstable counts across arms (14/14/16/18/14), so it is
  measuring its own thresholding, not the image. **Reported as instrument
  failure, not as a result.** No number from it appears in this report.
- **Frame-level refusal on real data.** It has never fired on a real bracket;
  every refusal here was planted. M86's 0.0% / 13.2% / 16.2% figures are
  *edge*-level, not frame-level.
- **Whether registration helps a genuinely non-smooth bracket** — handheld, or
  wind. Every stack available is a rail sweep. This is the regime where
  alignment should pay, and there is no capture that tests it.
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

and the write site made non-fatal, since a cache that cannot be written is not a
reason to fail a render:

```rust
    if let Err(e) = std::fs::create_dir_all(path.parent().unwrap_or(Path::new(".")))
        .map_err(anyhow::Error::from)
        .and_then(|()| map.save(&path))
    {
        eprintln!("  note          : could not cache the warp map ({e}); it will be re-solved next run");
    }
```

**I have not applied this and have not compiled it** — `align_cmd.rs` is the
orchestrator's file. It needs `dunce` (already a dependency of `strehl-cli`) or
`std::fs::canonicalize` if not. **Until it is applied, the corpus write is
live**, and `STREHL_WARPMAP` is the only way to render without it.

---

## 12. Status / Changes / Verified / Not verified / Notes

### Status

**DONE, as a verification with a negative result.** The dispatched work
(wiring) was completed by M86c in `885e9f7` before I could land it; I verified it
independently instead, ran the ground-truth geometry experiment M86c named as
their top follow-up, priced the feature, found two defects, and disqualified a
metric I had built and was about to trust.

**The registration is correct and I could not show that it improves the
photograph.**

### Changes

- `crates/strehl-cli/src/merge_cmd.rs` (+62/-2) — added `WARPMAP_ENV`
  (`STREHL_WARPMAP`) and `alignment_for()`, and pointed the call site at it.
  Needed for three things `load_or_solve` cannot do: consume a **planted**
  sidecar, **never write** to the capture directory, and **hard-refuse** a bad
  sidecar rather than silently re-solving a different registration than the one
  named. `STREHL_ALIGN=0` still wins. No behaviour change when the variable is
  unset.
- `experiments/M97-warped-merge/**` — `PREREG.md`, 10 scripts, render logs and
  JSON for 10 renders.
- `docs/research/M97-warped-merge.md` — this report.
- **No changes** to `merge.rs`, `warpmap.rs`, `align.rs`, `align_cmd.rs`,
  `lib.rs`, `main.rs`, or any other milestone's tree.

### Verified

- `cargo build --release -p strehl-cli` — clean.
- P1 responsiveness **PASS** (plant moves `S_block` +4.252 px vs +0.038 px
  signal; ~110x margin).
- P2 **NULL** (registration does not straighten the ruler).
- P3 **PASS** (0.00000% black in 33 MP, whole frame and outer annulus, true
  16-bit, all 8 arms — with an 18-pixel plant recovered exactly, so the null is
  measured rather than a dead probe).
- P4 **PASS** (identity placebo, k = 0.9974).
- P5 **PASS** (wrong-stack sidecar hard-refused, both digests named).
- P7 **2.58x** (alternating medians, 3 runs each).
- Detail metric **disqualified** by its own plant (worse registration reads
  +5.6% better).
- `n_eff` +3.0% aligned vs matched null.
- `flat-on-ruler-cpl` re-checked after every run: **79 ARW files, no sidecar** —
  the read-only guarantee held for every render I performed.
- The output images, **opened and looked at**, side by side.

### Not verified

- P6 **FAILS the pre-registered bar**: refused frames abort the render rather
  than being dropped. Measured, not fixed (§9).
- The §7 mechanism is **DERIVED**; its falsifying experiment (a smooth ramp
  plant) was not run.
- Graduation spacing: **instrument failure**, no number reported.
- Frame-level refusal has never been exercised on real data by anyone.
- The §11 patch is **uncompiled**.

### Notes

- **A number in my dispatch was wrong and I was asked to say so:** "`merge.rs`
  and `merge_cmd.rs` contain zero references to `warpmap`" was true at writing
  and false ~20 minutes later. Not the orchestrator's error — a race. But the
  night's largest quality lever had already been pulled, and it did not move the
  image.
- Three instrument defects (§3) plus one in my own timing harness. The Pillow
  16-bit truncation is the one most likely to bite another milestone: it is
  silent, and it makes every 16-bit render look like an 8-bit one.
- **Recommendation for the next milestone.** Alignment is correct, costs 2.58x,
  and buys ~3% `n_eff` on rail-swept brackets. Before spending more on the
  solver (M86's 11.56 px against a 9.07 px floor), run the smooth-ramp plant in
  §7. If it confirms, the honest move is to make alignment **off by default for
  smooth brackets** and keep it for the non-smooth captures — which do not exist
  in the corpus yet and should be requested.
- "Those stacks don't look too good yet" remains **unexplained**. It is not
  registration. That is worth knowing at 05:00 rather than at the end of another
  milestone.
