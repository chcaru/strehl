# M110-sheet — a reproducible comparison-sheet harness

**Status:** delivered, and readied for the standby run. Harness committed at `66ba510`,
readiness pass at `c11e0e7`; sheets produced against `HEAD 5e4fbc4b74b2`. §8 covers the
second dispatch — the blown-highlight crop site, the pending CA arms, two further subjects,
and the controls on the new readout.

**Scope.** This is not a milestone with a hypothesis. ORCH asked for an instrument: a
one-command way to render the owner's real stacks under a named arms matrix and emit
crops a human can judge, so that the morning's images can be regenerated rather than
archived. It exists because of my own P10 finding, restated here because it is the whole
motivation:

> *the archived B6 TIFFs no longer reproduce — `strehl.exe` was rebuilt eight minutes
> after the renders. In a shared tree an archived render has a shelf life of minutes.*

Six agents are editing this tree tonight. Any sheet I hand over as a file is stale before
the owner wakes up. A sheet that can name the binary that produced it is not.

---

## 1. How to regenerate

```
cd experiments/M110-sheet
python sheet.py all
```

Subcommands run separately when you want them to: `scout` (pins exposure and crop
coordinates), `render` (all enabled arms, all subjects, writes the manifest), `figure` (builds
the PNGs), `recrop` (re-choose crops from bytes already on disk, no re-render), `survey`
(which subjects can currently demonstrate the magenta-clipping fix). `--subject <name>`
restricts; `--limit N` renders a short stack for a smoke test.

Adding an arm is adding a dict to `ARMS` in `sheet.py`; **arming a pending one is filling in
its flags and flipping one boolean:**

```python
{"name": "ca", "align": [], "merge": ["--some-flag"], "env": {}, "enabled": True,
 "note": "..."}
```

`align`, `merge` and `env` are applied per stage, so M107's CA work and M97's merge wiring
drop in as data without touching any logic.

**The sheet produced tonight:**

```
C:\dev\strehl-out\M110-sheet\bee-3-cpl\SHEET-bee-3-cpl-100.png          1:1
C:\dev\strehl-out\M110-sheet\bee-3-cpl\SHEET-bee-3-cpl-200.png          x2 NEAREST
C:\dev\strehl-out\M110-sheet\wrapped-text-1\SHEET-wrapped-text-1-100.png
C:\dev\strehl-out\M110-sheet\wrapped-text-1\SHEET-wrapped-text-1-200.png
C:\dev\strehl-out\M110-sheet\manifest.json
```

---

## 2. What the harness guarantees

**Self-dating (requirement 1).** Every sheet carries, in the image header and in
`manifest.json`: `git rev-parse HEAD`, the dirty flag *and the list of dirty files*, the
**sha256 of the `strehl.exe` that produced it** with its mtime and size, the full argv of
every stage of every arm, the host, and wall-clock in both UTC and local time.

Tonight's run: `HEAD 5e4fbc4b74b2`, **dirty, 81 files**, binary sha256 `680cd59c379ed9c6…`
built `2026-08-24T13:51:49`, generated `2026-08-24T14:16:35-07:00`.

That dirty flag is not a blemish, it is the finding. With 81 modified files from six live
agents, **`HEAD` does not identify this render and never could.** The binary sha256 is the
only field in the manifest that actually pins what ran. A provenance block that records
only the commit would have looked complete and been worthless — which is precisely the
shape of the P10 failure.

**1:1 only (requirement 2).** `load8` takes the high byte, exactly as `sheet3.py` does; the
paste is 1:1 and the magnified variant is integer NEAREST. No resize, no sharpening, no
tone change anywhere in the figure path, and the header says so. Fact 1359 is the reason:
a Laplacian metric rated a visibly mosaicked render 2.73x sharper than the correct one, and
only 100% crops caught it.

**Frozen, principled crops (requirement 3).** `scout` chooses five roles **once, on the
default arm**, writes them into `subjects.json`, and every arm is then cut at those same
coordinates, which are printed on every tile.

| role | rule |
| --- | --- |
| detail | max mean \|gradient\| |
| silhouette | max luma p95−p05 |
| specular | max luma p99.9 |
| smooth | min \|gradient\| among tiles above p20 brightness |
| corner | geometric, 48 px inset, radial max |

I deliberately did **not** reuse `sheet3.py`'s `sharpest_crop`. It is content-adaptive, so it
re-picks per image — which would let each arm choose the window where it happens to look
best. That is not a comparison. The corner role is geometric rather than content-chosen
because **lateral CA is radial and zero at centre**: a centre-only sheet cannot see M107's
work at all.

Exposure is pinned for the same reason. `--auto-exposure` is scene-dependent and M100
declined to make it default because "a silent, scene-dependent gain makes two renders
incomparable" (`merge_cmd.rs:3156`). `scout` reads the printed `--exposure=X.XX` off the
default arm and pins it for every arm; `color.rs:1481-1487` asserts that flag round-trips
bit-exactly, so the pin is exact and not a re-quantisation.

**Cache-collision guard.** `StackIdentity` covers neither `reference` nor `resampler`
(fact 1446) and this matrix varies `resampler` deliberately, so this is the most
cache-exposed thing in the tree. Each arm gets its own explicit output path, and
`cmd_render` **fails the run** if any two arms of a subject produce identical bytes. Two
arms secretly being the same file is exactly what the unkeyed cache produces, and it would
read as *"the kernel makes no difference"* — a false negative that looks like a result.

Tonight: `distinct_hashes_ok` **true for both subjects**, `failures: []`.

**Requirements 4 and 5** are met by the `ARMS` matrix above and by carrying two subjects
with opposite character: `bee-3-cpl` (299 frames, thousands of hair silhouettes, the
adversarial case for a negative-lobe kernel) and `wrapped-text-1` (130 frames, hard printed
edges, where ringing is easiest to see and hardest to excuse).

---

## 3. MEASURED — tonight's arms

| subject | arm | seconds | sha256 | sidecar records |
| --- | --- | --- | --- | --- |
| bee-3-cpl | default | 209.3 | `e400a63aa9f6` | catmull-rom |
| bee-3-cpl | lanczos3 | 518.6 | `dc6555bcdae0` | lanczos3 |
| wrapped-text-1 | default | 41.4 | `6774f0085445` | catmull-rom |
| wrapped-text-1 | lanczos3 | 146.1 | `128e5c40ed2f` | lanczos3 |

Pinned exposure `--exposure=1.54` (bee) and `--exposure=2.27` (text). Frozen crops:

- bee-3-cpl — detail (840,0), silhouette (840,2520), specular (2800,0), smooth (6440,280), corner (48,4080)
- wrapped-text-1 — detail (4760,1680), silhouette (840,1960), specular (4480,0), smooth (0,2520), corner (6424,4080)

**MEASURED: lanczos3 costs 2.478x (bee) and 3.529x (text) the wall-clock of catmull-rom.**
The corpus has priced this kernel in dex of high-band loss and, as far as I can find, never
in seconds. It is not free, and on the owner's largest stack it is the difference between a
three-and-a-half minute render and a nine-minute one.

---

## 4. My by-eye verdict on lanczos3

ORCH asked for this specifically because I did not author the kernel claim, and asked me
not to coordinate with M113-kernel-verify so the two reads stay uncorrelated. I have not
looked at M113's work or its numbers.

**MEASURED (by eye): lanczos3 looks better, not merely different.** At x5–x7 NEAREST on
real hairs it is a clear improvement, not a subtle one. On the bee's wing at (900,60) the
spicules are distinctly separated where the default smears them together, the diagonal hair
strands resolve as individual strands rather than a merged smudge, and the vein edge is
tighter. On printed text at (4850,1750) the paper fibre and the ink boundary are both
better resolved. I would take the lanczos3 render of either subject over the default.

**MEASURED (by eye): I could not see ringing on hair silhouettes.** I went looking for it at
four hand-picked sites, including the two hardest edges I could find, and I did not find a
visible halo band hugging any edge. A luminance profile on the identical row, taken to check
my eye against the pixels rather than as an independent metric:

| site | edge | default overshoot | lanczos3 overshoot | delta |
| --- | --- | --- | --- | --- |
| bee (300,4200) | soft hair | 2.70 | 3.02 | +0.32 |
| bee (900,60) | wing vein | 5.46 | 3.99 | **−1.47** |
| bee (900,2620) | low-contrast hair | 3.99 | 4.46 | +0.47 |
| text (4850,1750) | ink/paper | 47.14 | 48.28 | +1.14 |

**The sign is not consistent — lanczos3 overshoots *less* than the default on the hardest
edge of the four.** Largest excursion 1.47 on a 0–255 scale, i.e. 0.58% of range. Nothing
resembling a 9.9x effect is present in these merged renders.

**I am not claiming this refutes fact 1374, and it should not be read that way.** Fact
1374's 9.902x is a kernel-level quantity. Mine is end-to-end through the merge, and the
merge elects a single frame per pixel in detailed regions (fact 1393) rather than
convolving, so there is no reason the two numbers should be comparable. Four hand-picked
sites is an eye, not a survey. **The correct reading is: whatever the kernel does in
isolation, I could not see it in the render — and the default should still not move on my
say-so.**

**The finding I did not expect, and it matters more than the kernel.** At x6 the dominant
visible artefact on `bee-3-cpl` is not sharpness and not ringing, it is **lateral chromatic
aberration**. Every spicule on the wing carries a cyan side and a red side; the corner crop
of `wrapped-text-1` shows coloured fringes on every letter edge. It is far more objectionable
to my eye than any difference between the two kernels — and **lanczos3 makes it worse in
appearance by making it crisper**, turning smeared fringes into well-defined coloured dots.

**ARGUED: if the owner's complaint is "the renders don't look good", the CA is a better
candidate than the kernel, and shipping lanczos3 before M107's correction lands could read
as a regression to him** even though it is resolving more real detail. The two want to land
together, and that ordering is ORCH's to sequence, not mine. This is an argument from four
crops on two subjects; it is the kind of claim M107 can settle and I cannot.

---

## 5. Constraints honoured

- `D:\personal\macro` and `D:\macro-dark-frames` read-only; every write went to
  `C:\dev\strehl-out\M110-sheet\`.
- Wrote only `experiments/M110-sheet/**` and this file. **No `crates/` change was needed** —
  the harness drives the shipped CLI as-is.
- Default resampler untouched. `align_cmd.rs` still `default_value = "catmull-rom"`.
- Did not edit `SYNTHESIS.md`; proposed facts and disciplines are in §7 for ORCH to fold.
- Path-scoped commits, three named files, no `git add -A`, not pushed.
- No `$LASTEXITCODE` read follows any pipeline containing `Select-Object -First`. Every
  render is driven from Python, where `subprocess.returncode` is structurally immune to the
  rule-47 corruption; that was a deliberate choice, not a coincidence.
- `python scripts/corpus_lint.py` — **OK, no violations.**

---

## 6. What I could not verify

1. **I did not verify my own work and this section is not a substitute for a verifier.** The
   by-eye verdict in §4 is one pair of eyes on four sites.
2. **The sheets were produced from a dirty tree** (81 modified files, six live agents). The
   binary sha256 pins *what ran*, but nothing pins *what source it came from*, because that
   source was never committed. This is inherent to rendering in a shared tree tonight, not a
   defect in the harness — the harness is what makes it visible rather than silent.
3. **The fact-1446 guard proves the arms differ, not that each arm is the configuration it
   claims.** The sidecar's self-reported `resampler` field (`catmull-rom` / `lanczos3` in the
   table above) is the only evidence of the latter, and it is the binary reporting on itself.
   An independent check would need the cache defect fixed first; M97 owns that.
4. **Crop selection is frozen but not neutral.** The rules in §2 are stated so they can be
   argued with, and a different set of rules would put the windows elsewhere. The four zoom
   sites in §4 were hand-picked by me, which is weaker still, and I have said so there.
5. **Render timings are wall-clock on a machine running six other agents** and should be
   treated as a ratio, not an absolute.

---

## 7. For ORCH — proposed facts and disciplines

I do not own `SYNTHESIS.md`. Numbered for folding, not for pasting.

**Facts**

1. **MEASURED: `lanczos3` costs 2.478x the wall-clock of `catmull-rom` on `bee-3-cpl`
   (518.6 s against 209.3 s, 299 frames, full-res sRGB) and 3.529x on `wrapped-text-1`
   (146.1 s against 41.4 s, 130 frames).** The corpus has priced this kernel in dex of
   high-band loss but not in seconds. Manifest at `C:\dev\strehl-out\M110-sheet\manifest.json`,
   binary sha256 `680cd59c379ed9c6…`.
2. **MEASURED (by eye, one reader): at x5–x7 NEAREST on real hairs and real print,
   `lanczos3` resolves visibly more detail than the shipped default and no ringing halo was
   visible at four hand-picked sites**, including the two hardest edges available. Edge
   overshoot moved by at most 1.47/255 (0.58% of range) and **changed sign across sites** —
   `lanczos3` overshot *less* on the bee's wing vein (3.99 against 5.46). **This does not
   refute fact 1374**, whose 9.902x is a kernel-level quantity while this is end-to-end
   through a merge that elects one frame per pixel (fact 1393).
3. **MEASURED (by eye): the dominant visible artefact on `bee-3-cpl` at x6 is lateral
   chromatic aberration, not kernel sharpness and not ringing** — every wing spicule carries
   a cyan/red pair, and letter edges in the `wrapped-text-1` corner crop are fringed.
   **`lanczos3` makes the fringes more conspicuous by sharpening them.** ARGUED consequence:
   landing the kernel before M107's CA correction may read to the owner as a regression.
4. **MEASURED: a comparison sheet rendered in this tree tonight cannot be identified by
   `git HEAD`** — HEAD was `5e4fbc4b74b2` with **81 modified files** from six concurrent
   agents. The sha256 of the producing binary is the only field that pins the render. This
   is P10 generalised.
5. **MEASURED: the `experiments/M110-sheet` harness passed its own fact-1446 guard** —
   `distinct_hashes_ok` true for both subjects, `failures: []` — so tonight's kernel
   comparison is not a cache artefact.

**Disciplines**

6. **A comparison sheet must record the sha256 of the binary that produced it, not just the
   commit.** In a shared tree the commit does not identify the render and a provenance block
   that records only the commit looks complete while being worthless.
7. **Crop windows and exposure must be chosen once, on one arm, and frozen.** A
   content-adaptive crop chooser re-picks per image, which lets every arm show itself at its
   best; that is not a comparison. State the selection rule in the artefact so it can be
   argued with.
8. **Any A/B that varies a field absent from the cache key must assert that its arms'
   outputs differ.** Two arms silently sharing bytes is the failure that unkeyed caching
   produces, and it presents as "the change makes no difference" — a false negative wearing
   the costume of a result.
9. **A comparison sheet must include a corner crop.** Lateral CA is radial and zero at
   centre, so a centre-only sheet is structurally blind to it — and on this corpus CA is the
   most visible artefact there is.
10. **Drive renders for measurement from Python, not PowerShell.** `subprocess.returncode` is
    structurally immune to the rule-47 `$LASTEXITCODE` corruption, which under Windows
    PowerShell 5.1 is both silent and satisfies a naive `-ne 0` gate.
11. **Do not compare a kernel-level number with an end-to-end one.** Ringing measured on a
    resampling kernel and ringing seen in a merged render are different quantities, because
    the merge elects a single frame per pixel rather than convolving.

---

## 8. Readiness pass — the standby configuration

Second dispatch: get the harness able to render the morning's answer in one command, without
running the expensive matrix while `HEAD` moves. All of this is configuration and controls;
**no arm matrix was run.** No `crates/` file was touched.

### 8.1 The blown-highlight crop site

`clipped` is now a sixth role. It is selected on the **physical condition** — the tile with
the greatest fraction of pixels where **red *and* blue both sit at or above 99% of full
scale** — and explicitly *not* on how magenta the tile looks. Selecting on the defect's
appearance would pick the window where the defect is loudest, which is choosing the answer.
Selecting on blown-ness picks the place where the render is *obliged* to be neutral, which
is a fair test both before and after a fix. If a subject has nothing genuinely clipped the
role falls back to the brightest tile and the artefact says so.

Every `clipped` tile is stamped with its blown fraction and its **green offset**, mean
`(G − (R+B)/2)` over blown pixels in full-scale units. A neutral blown highlight reads
`0.0000`; M109 measured green pinned ~`−0.10`. So the before/after is a number on the sheet,
not an impression.

### 8.2 MEASURED — the readout is controlled, and it is one-sided

`neutrality_control.py`, **7/7 bars**, bars registered before running:

| bar | result |
| --- | --- |
| N1 null | recomputes `+0.000442`, exactly the printed value |
| P2 linearity −0.02 | recovered `−0.020005` |
| P2 linearity −0.05 | recovered `−0.050004` |
| P1 positive −0.10 | recovered `−0.100008` |
| S1 sign | `−0.040009` from a −0.10 baseline: moved **positive** by +0.06 |
| H1 headroom | mean green headroom `0.00034`, **96.7%** of blown px already at full scale |
| M1 mask | moved `+0.000000000` when planting off-mask |

**H1 exists because an earlier version of S1 failed.** It planted `+0.06` directly and
recovered `+0.000344`. That is not sign-blindness: on a genuinely blown pixel green is
*already* at the ceiling, so a positive plant has nowhere to go. I measured the ceiling
rather than loosening the bar, and the recovered `+0.000344` matches the measured mean
headroom `0.00034` to within a part in ten thousand — the diagnosis is confirmed, not
asserted.

**MEASURED: the green-offset readout is one-sided by construction.** It measures green
*deficit* (magenta) faithfully — a planted `−0.10` returns to within `1e-5` — and is
**structurally blind to green excess**, because green has 0.034% headroom at the clip point.
Consequence worth stating plainly: **if M97's fix overshoots into green, this sheet will
under-report it.** A by-eye check of the clipped tile remains necessary and the number is
not a substitute for it.

### 8.3 MEASURED — none of the four subjects currently shows the magenta defect

`python sheet.py survey`, read off the frozen `clipped` tile of each full-stack default arm,
binary sha256 `680cd59c379ed9c6…` built `2026-08-24T13:51:49`:

| subject | blown % of tile | green offset |
| --- | --- | --- |
| bee-3-cpl | 0.176% | `+0.0004` |
| wrapped-text-1 | 0.181% | `+0.0004` |
| tweezers-cpl | 0.555% | `−0.0034` |
| flat-on-ruler-cpl | 0.856% | `−0.0004` |

Every one is neutral within `0.0034`, **about 29x smaller than the `−0.10` M109 reported.**

I tested the obvious alternative — that the defect lives in a pixel population my mask does
not select — by profiling the whole frame against highlight brightness rather than only the
clipped tile:

| min(R,B) bin | tweezers-cpl | flat-on-ruler-cpl |
| --- | --- | --- |
| [0.60, 0.75) | `+0.0057` | `−0.0002` |
| [0.75, 0.85) | `+0.0037` | `+0.0028` |
| [0.85, 0.90) | `+0.0042` | `+0.0176` |
| [0.90, 0.95) | `+0.0049` | `+0.0226` |
| [0.95, 0.98) | `+0.0066` | `+0.0133` |
| [0.98, 0.99) | `+0.0028` | `+0.0047` |
| [0.99, 1.01) | `−0.0012` | `−0.0002` |

**No brightness bin, on either subject, is anywhere near `−0.10`.** Individual pixels reach
`−0.3092` and `−0.2861`, but isolated pixels at that level are as consistent with genuinely
magenta content as with a defect.

**I am not claiming M109 is wrong, and this must not be read that way.** My binary was built
at 13:51:49 and M97 was landing the fix afterwards, so the most likely explanations are that
M109 measured under different flags — I render `--srgb` with a pinned `--exposure`, and
`--srgb` implies `--demosaic` — or on a subject or exposure where it manifests. **The
actionable point is narrower and it is for ORCH: on these four subjects at these exposures,
the clipped site currently has nothing to show, so a before/after here may legitimately look
like no change.** `python sheet.py survey` re-answers this in one command once M97 lands,
and that is the check to run before putting a magenta claim in front of the owner.

### 8.4 The missing kernel control is a product defect

`strehl stack` has **no `--resampler` flag at all**. A merge's kernel is set *entirely* by
whichever sidecar the cache hands it. The harness already drives this correctly, by setting
the kernel on the `align` stage and naming the sidecar explicitly, and I have not added the
flag — that file is not mine.

**ARGUED: this is a product defect independent of which kernel wins.** A user who has read
that Lanczos-3 recovers real detail has no supported way to ask for it from the command that
produces their picture; the only route is to run `align` separately and know that `stack`
silently consumes the sidecar. Whichever kernel becomes the default, a user-facing control on
the command that renders the image is the difference between a switchable feature and an
implementation detail.

It also **upgrades the byte-distinctness assertion from prudent to mandatory**, and the
reason is that the exposure is **one-sided**: a lone arm can silently inherit a kernel from
an unrelated earlier command, and with no second arm to disagree with it nothing in its own
log would say so. Two changes follow, both landed:

- `render_arm` now **asserts** the sidecar records the kernel the arm asked for, and fails
  the arm if it does not.
- A run producing **fewer than two arms is flagged as unguarded**, because byte-distinctness
  across one arm is vacuous and reads as a pass.

### 8.5 Subjects, arms, and two harness fixes

**Two subjects added**, chosen on the axes that matter here rather than on convenience:
`tweezers-cpl` (100 frames; polished metal, the subject most likely to hold genuinely blown
neutral speculars, and where lateral CA is loudest) and `flat-on-ruler-cpl` (79 frames;
printed graduations filling the frame to the corners, so there is content out at the radius
where **M107's fit is extrapolated past its supported r = 0.788**). Both scouted at full
stack; neither needed the no-clipping fallback.

**Two arms added as data-only slots**, `ca` and `ca+lanczos3`, both `enabled: False`. They are
skipped loudly rather than guessed. `OpticalProfile` has zero consumers outside its own file,
so an invented flag would render bytes identical to the default and the sheet would report
*"the correction does not help"* — a silent no-op wearing the costume of a result, and the
exact false negative the fact-1446 guard exists to catch. **Arming them is filling in
`align`/`merge`/`env` with M107's exact string and flipping one boolean; nothing else
changes.** `ca+lanczos3` is present because it is the actual candidate configuration: the two
interact, since sharpening makes fringes more conspicuous, so neither alone answers the
owner's question.

**eps_b is None.** M107 fitted red only and every ROI was red, while real fringes are
red/cyan pairs. The sheet must not imply a full correction, and the `ca` arm's note carries
that caveat inline so it travels with the configuration rather than living only here.

Two defects in my own harness, found and fixed while readying it:

1. **A partial `render` replaced the whole manifest**, so re-rendering one subject silently
   deleted the others' entries and `figure` then skipped them. It now merges.
2. **Provenance was global.** A partial re-run happens under a *different binary* than the
   rest — which is P10 exactly — and one shared block would have stamped every sheet with the
   last binary to run. Provenance is now recorded **per subject** and the figure stamps the
   subject's own.

Also added: `recrop` (re-choose crops from bytes already on disk, recording their sha256, for
when the role list changes and a fresh render would be pure cost) and `survey` (§8.3).

### 8.6 Corrections to my own earlier text

**The kernel gain figure I should quote from here on is `+0.083` to `+0.099` dex end-to-end
through the shipped merge, not `+0.1343`.** I did not quote a gain figure in §1–§7, so nothing
above needs amending, but the adjusted number is recorded here so this report does not become
a source for the stale one.

**My §4 reasoning was independently confirmed.** M113, which did not coordinate with me,
measured excess-extrema ratios of `0.9924`, `0.9938`, `1.0039`, `1.0048` — **1.00x, not
9.902x** — and supplied the mechanism I did not have: mean `n_eff` is **55.3**, so each output
pixel averages ~55 independently-warped frames at ~55 different sub-pixel phases. **Ringing is
phase-dependent and averages down; passband gain is not and does not.** That is why a
single-frame half-pixel-phase number does not transfer to a merge. I drew the
distinction in §4 without the mechanism; the mechanism is M113's.

---

## 9. For ORCH — further facts and disciplines

Continuing the numbering from §7.

**Facts**

12. **MEASURED: the blown-highlight green offset is neutral within `0.0034` on all four
    subjects** — bee-3-cpl `+0.0004`, wrapped-text-1 `+0.0004`, tweezers-cpl `−0.0034`,
    flat-on-ruler-cpl `−0.0004`, at their frozen `clipped` tiles under binary
    `680cd59c379ed9c6…`. **About 29x smaller than M109's `−0.10`.** A whole-frame profile
    against highlight brightness finds no bin between 0.60 and clipping worse than `+0.0226`
    on either new subject, so the defect is not merely in a pixel population the mask misses.
    Most likely a difference in flags or subject, **not** evidence against M109 — but on these
    subjects the crop site currently has nothing to show.
13. **MEASURED: the green-offset readout is one-sided by construction.** Green has mean
    `0.00034` headroom on blown pixels and **96.7%** are already at full scale, so it measures
    magenta faithfully (planted `−0.10` recovered to `−0.100008`) and is **blind to green
    excess**. If a highlight fix overshoots into green, a sheet using this number will
    under-report it.
14. **MEASURED: `neutrality_control.py` passes 7/7 registered bars**, including recovery of a
    planted `−0.10` to within `1e-5`, correct sign discrimination from a planted baseline, and
    exactly zero movement when the plant is placed off-mask.
15. **ARGUED: the absence of a `--resampler` flag on `strehl stack` is a product defect
    independent of which kernel wins.** The kernel is set entirely by whichever sidecar the
    merge consumes, so a user has no supported way to ask the command that renders their
    picture for the kernel they want.

**Disciplines**

16. **Choose a defect-demonstration crop on the physical condition that makes the defect
    possible, never on the defect's appearance.** Selecting the window where the artefact
    looks worst is choosing the answer; selecting where the render is *obliged* to be correct
    is fair before and after the fix.
17. **Before a sheet claims to demonstrate a fix, measure that the defect is present in the
    chosen window.** A before/after on a window that was already correct shows nothing, and
    reads to a viewer as the fix having failed.
18. **A pending arm must be skipped loudly, never approximated with a guessed flag.** If the
    feature has no consumer, the guessed arm renders bytes identical to the control and the
    comparison reports "no effect" — a false negative indistinguishable from a result.
19. **When a control fails, measure the ceiling before loosening the bar.** The failing sign
    bar here was the instrument meeting a clip limit, and measuring that limit turned a
    failed bar into a stated bound on what the sheet can be trusted to show.
20. **Record provenance per artefact, not per run.** In a shared tree a partial re-run happens
    under a different binary than the rest, and one global provenance block silently stamps
    every artefact with the last binary to execute.
21. **An assertion across a single arm is vacuous and should say so.** Byte-distinctness with
    one arm passes trivially; where a field is set out-of-band, a lone arm can inherit it from
    an unrelated earlier command with nothing to contradict it.

---

## 10. A two-sided highlight readout, and the magenta question re-answered

ORCH asked for this because of a caveat I attached to my own null in §8.3: the readout had
headroom in one direction only. That blindness became load-bearing the moment `e9ad010`
ported a guarded clip onto the **default** render path on the strength of a measurement
taken on a **different** path, because the only instrument watching the default path could
not see the direction in which a bad port would fail.

### 10.1 Why the old readout was worse than under-reporting

`neutrality()` selected on **red AND blue** both pinned, then measured green against them.
Reading the `e9ad010` diff makes the consequence concrete. It applies a saturation ceiling
to the colour matrix, so the mechanism runs:

- the sensor saturates, raw R = G = B = max;
- white balance (R ≈ 2.0, B ≈ 1.5, G = 1.0) carries **red and blue past the container max**
  while green stays pinned at it;
- the matrix sees red and blue relatively larger than green → **magenta**.

So a ceiling computed **too low** clamps **red and blue down**. In that failure red and blue
fall *below* the 99% threshold and the old mask **selects nothing**. The instrument does not
merely under-report a bad port — it goes **silent exactly when the port is worst**, and
prints `too few blown px to score`.

That is not a prediction. Bar **H2** exercises it: on a planted `+0.10` green overshoot the
one-sided readout **emitted nothing at all**, its red-AND-blue mask having emptied, while the
two-sided one recovered `+0.100008`.

### 10.2 The replacement, and its dynamic range

`highlight_stats()` selects **channel-agnostically** — blown in at least one channel — which
is the physical condition "this is a blown highlight" and survives both failure directions:

| failure | pinned | low | `off` |
| --- | --- | --- | --- |
| magenta | R, B | G | **< 0** |
| green overshoot (bad ceiling) | G | R, B | **> 0** |

Whichever channel is low is the one carrying the signal, so it has the container's full range
available. The earlier blindness came from *selecting* on red and blue being pinned, which
forced the comparison baseline to the ceiling itself.

**Plants are applied by LOWERING a channel, never by raising one.** That is not a
convenience. It is how both real failures arise — magenta leaves green low, a low ceiling
leaves red and blue low — and lowering has room where raising hits the container. Raising is
what made the §8.3 sign bar fail.

Alongside `off`, the readout now reports per-channel pinned fractions `c_r`, `c_g`, `c_b` and
`asym = c_g − (c_r + c_b)/2`. This is the most diagnostic single output: **neutral clipping
pins all three channels together**, magenta spares green, a low ceiling spares red and blue.

### 10.3 MEASURED — the instrument, in both directions

`neutrality_control.py`, **14/14 registered bars**, bars fixed before running:

| quantity | old (one-sided) | new (two-sided) |
| --- | --- | --- |
| plant `−0.10` recovered | `−0.100008` | **`−0.100008`** |
| plant `+0.10` recovered | **went silent** | **`+0.100008`** |
| symmetry \|+\| − \|−\| | n/a | **`−0.000000`** |
| headroom, magenta | `0.00034` | **`0.9542`** |
| headroom, green | `0.00034` | **`0.8892`** |

Headroom is the 5th percentile of available range: 95% of region pixels have at least this
much room. The green direction gains a factor of **2615x**. Linearity holds at `±0.02` and
`±0.05` to within `5e-6`, and an off-mask plant moves the statistic by exactly `0`.

**A registered bar failed first, and diagnosing it produced a result.** P1/P2/P4 initially
recovered a *constant* offset — `−0.00517` magenta, `+0.00340` green — identical at every
plant size. Constant with plant size means **bias, not gain error**. The cause: the mask is
**not invariant under the thing it measures**. Lowering a channel can push a pixel below the
threshold and out of the population, moving the mean for a reason that is not the neutrality
of the pixels that remain.

The repair separates the two quantities rather than hiding either. Gain bars run on a mask
**frozen** on the unplanted tile; new bars **B1/B2** then measure the float-mask systematic
itself, on the code path that actually ships:

- **B1**: the free mask biases the reading by `−0.00518…−0.00517` (magenta) and
  `+0.00340…+0.00340` (green).
- **B2**: that bias varies by `0.000004` across plants from `0.02` to `0.10` — a constant
  offset, confirmed, not a gain error.

**So the shipping statistic carries a known systematic of about `0.005`, and everything below
should be read against that floor.**

### 10.4 MEASURED — the default path, at a HEAD containing `e9ad010`

`e9ad010` is an ancestor of HEAD (`git merge-base --is-ancestor` → 0) and landed
`15:07:57`. Rebuilt at HEAD, binary `8b913a415ffe1d9f…` (`15:35:18`), and re-rendered the
`default` arm on all four subjects.

| subject | blown % | `off` | one-sided | `c_r` | `c_g` | `c_b` | `asym` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bee-3-cpl | 0.819% | `+0.0165` | `+0.0004` | 0.590 | 0.766 | 0.410 | `+0.266` |
| wrapped-text-1 | 0.601% | `+0.0173` | `+0.0004` | 0.548 | 0.888 | 0.443 | `+0.392` |
| tweezers-cpl | 1.210% | `+0.0101` | `−0.0034` | 0.632 | 0.767 | 0.761 | `+0.070` |
| flat-on-ruler-cpl | 1.250% | `+0.0075` | `−0.0004` | 0.782 | 0.871 | 0.850 | `+0.055` |

**No magenta, and no green overshoot.** Every reading is positive, between `+0.0075` and
`+0.0173` — at or barely above the `0.005` systematic of §10.3, and far below the `0.02`
threshold in either direction. **The port did not overshoot.**

**And the renders are byte-identical.** The four TIFFs produced by the post-port binary have
the same sha256 as the pre-port TIFFs they replaced — `e400a63aa9f6ab1f…`,
`6774f00854452745…`, `a8c07ccdf4fd9947…`, `c461c0a635f4d835…`, `Δoff = +0.00000` on all
four. **This independently reproduces M97's byte-freeze 5/5 HOLD from an instrument that
shares nothing with it: the conditional never fires on these stacks.**

**Stated plainly, as ORCH asked: `e9ad010` changes nothing on the path the owner actually
runs. That is a fact about the product, not a failure of the measurement.**

### 10.5 MEASURED — the positive control that was missing, on real data

A synthetic plant proves the statistic responds to a number I injected. It cannot
distinguish *"there is no defect here"* from *"the instrument cannot see the defect on this
path"*. So I rendered the same subjects through **`argmax-baseline`** — `stack.rs`,
`Command::ArgmaxBaseline`, the path where the defect was actually measured and fixed
(`3e58676`) before being ported.

Same tile, same raws, same statistic; the only difference is which merge command made the
pixels:

| subject | default | argmax | swing | def `c_g` | arg `c_g` |
| --- | --- | --- | --- | --- | --- |
| bee-3-cpl | `+0.0165` | `+0.0036` | `−0.0129` | 0.766 | 0.180 |
| wrapped-text-1 | `+0.0173` | `+0.0171` | `−0.0002` | 0.888 | 0.870 |
| **tweezers-cpl** | `+0.0101` | **`−0.0271`** | **`−0.0372`** | 0.767 | **0.495** |
| flat-on-ruler-cpl | `+0.0075` | `+0.0030` | `−0.0045` | 0.871 | 0.834 |

**`tweezers-cpl` reads magenta on the argmax path and neutral on the default path.** The
signature is textbook: green pinned on only **49.5%** of the blown region against red's
**81.0%**, `asym = −0.2288`, and the *one-sided* readout agrees at `−0.0197`. The swing of
`−0.0372` is **7.2x** the `0.005` systematic.

**This is what the §8.3 null was missing.** The instrument can see magenta on real pixels —
it just did — so the default-path null is a statement about the default path, not about the
readout. The two paths genuinely disagree about highlights on this subject.

I will not over-claim what that means. `3e58676` is in HEAD, so the argmax path is nominally
fixed and still reads `−0.0271`; that is **13x smaller than M109's `−0.10`** and I cannot
separate a residual defect from scene colour without a build at `3e58676^`, which needs a
checkout I must not perform in a shared tree. **What is established is the contrast, not its
cause.**

### 10.6 A defect in my own instrument, found by its own control

The control at §10.4 nearly passed on bad evidence. I compared the before/after binaries out
of the two snapshot files and got **`binaries identical: True`** — because both snapshots ran
`provenance()` *after* the rebuild, so each recorded the *current* binary rather than the one
that made its TIFF. Byte-identity between renders by the same binary is trivial and proves
nothing; the control said so and refused the result.

The underlying gap: **`render_arm()` recorded no binary at all.** Provenance existed per
*run*, so a preserved arm could not say what produced it. That is **P10 — my own finding —
biting the instrument built to prevent P10**, and it is the second time in this milestone
that per-run provenance has been wrong where per-artefact provenance was needed.
`render_arm()` now stamps `binary_sha256`, `binary_mtime` and `rendered_utc` into **each arm
result**.

The consequence for §10.4 is honest and worth stating: the pre-port TIFFs' binary
(`680cd59c379ed9c6…`, built `13:51:49`, before `e9ad010` at `15:07:57`) is documented in
§8.3 of this report, **not** in a per-arm record, because the field did not exist when they
were rendered. The byte-identity result rests on that committed text. From now on it will
not need to.

### 10.7 Harness changes

- `highlight_stats(win, region=None)` — the two-sided readout, with an optional frozen mask
  so gain and population shift can be measured apart.
- `neutrality()` retained and marked one-sided, so §8.3's numbers stay comparable **and its
  silence under a green plant stays reproducible**.
- `sheet.py survey` and the `figure` clipped-tile stamp now report `off`, per-channel pinned
  fractions and `asym`, colour-coded for both failure directions.
- `sheet.py render --arm NAME` — a deliberate single-arm run records
  `comparison_guarded: false` and `deliberate_single_arm: true` without being logged as a
  failure, preserves the arms it did not run, and marks them `stale` with the HEAD they are
  stale against. The fact-1446 duplicate check now compares only arms rendered in the same
  run, since a stale arm's hash came from another binary and agreeing with it says nothing.
- `highlight_snapshot.py before|after|diff` — before/after with hashes and provenance.
- `argmax_control.py`, `compare_paths.py` — the real-data positive control of §10.5.

### 10.8 What I could not verify

1. **I did not verify my own work.** §10 needs a verifier like the rest of this report.
2. **I cannot attribute the argmax/default contrast to any single commit.** The two paths
   differ in far more than highlight handling — per-pixel election against a ~55-frame
   average — so `−0.0372` is a difference between *paths*, not a measurement of `e9ad010`
   or `3e58676`.
3. **`−0.0271` on tweezers/argmax is unexplained.** It may be a residual defect after
   `3e58676`, or scene colour. Separating them needs a build at `3e58676^`.
4. **Byte-identity in §10.4 spans more than `e9ad010`.** Other agents' commits landed
   between the two binaries, so what is shown is that the default render is unchanged
   *across that whole interval*, which is a stronger claim in one sense and a less
   attributable one in another.
5. **The `0.005` systematic is measured on one tile** (bee-3-cpl `clipped`). I did not
   re-measure it per subject.

---

## 11. For ORCH — further facts and disciplines

Continuing the numbering from §9.

**Facts**

22. **MEASURED: the one-sided highlight readout does not under-report a green overshoot, it
    goes SILENT.** On a planted `+0.10` it emitted nothing at all — its red-AND-blue mask
    empties, because the failure it must detect is precisely one that pulls red and blue
    below the mask threshold. **An instrument that falls quiet exactly when the fault is
    worst is more dangerous than one that reads low**, because silence is indistinguishable
    from "no data" and invites re-running rather than alarm.
23. **MEASURED: the two-sided readout recovers `−0.100008` and `+0.100008` from planted
    `∓0.10`, symmetric to `−0.000000`, with headroom `0.9542` (magenta) and `0.8892`
    (green)** against the old `0.00034` — a **2615x** gain in the blind direction. 14/14
    registered bars.
24. **MEASURED: the shipping statistic carries a constant systematic of `≈0.005`**
    (`−0.00518` magenta, `+0.00340` green), because the blown-pixel mask is not invariant
    under the thing it measures — lowering a channel pushes pixels out of the population.
    It is a bias, not a gain error: constant to `0.000004` across plants from `0.02` to
    `0.10`. **Read every highlight number in this report against that floor.**
25. **MEASURED: `e9ad010` changes nothing on the default render path.** At binary
    `8b913a415ffe1d9f…` built from a HEAD containing it, all four subjects read neutral
    (`+0.0075` to `+0.0173`, no magenta and no green overshoot) and **all four TIFFs are
    byte-identical to their pre-port renders**. This reproduces M97's byte-freeze 5/5 HOLD
    from an unrelated instrument: **the conditional never fires on these stacks.**
26. **MEASURED: `tweezers-cpl` reads magenta `−0.0271` on `argmax-baseline` and neutral
    `+0.0101` on the default path — same tile, same raws, same statistic, a swing of
    `−0.0372` (7.2x the systematic).** Green is pinned on 49.5% of the blown region there
    against red's 81.0%, `asym = −0.2288`, and the one-sided readout independently agrees at
    `−0.0197`. **The instrument can see magenta on real pixels, so the default-path null is a
    fact about the default path and not about the readout.**
27. **MEASURED: the magenta residual on the argmax path is `13x` smaller than M109's
    `−0.10`**, at a HEAD that already contains `3e58676`. Whether this is a residual defect
    or scene colour is **not** established and needs a build at `3e58676^`.

**Disciplines**

28. **An instrument's failure mode must not be silence.** Before trusting a null, ask what
    the instrument does when the fault is *worst*, not merely when it is present. A mask
    defined on the same channels the fault suppresses will empty precisely then.
29. **Plant a synthetic fault by LOWERING a channel, never by raising one.** Raising hits the
    container ceiling and the recovered value measures the headroom rather than the plant.
    Lowering also matches how both real failures arise.
30. **A synthetic plant cannot validate a null; only a neighbouring real path can.** A plant
    proves the statistic responds to an injected number. It cannot separate "no defect here"
    from "blind on this path". Render the code path where the defect is *known* to have
    existed, with the same subject and the same statistic.
31. **When a control returns a constant offset independent of the planted magnitude, it is a
    bias and the population moved.** Check whether the selection criterion is invariant under
    the quantity being measured; usually it is not. Freeze the mask to measure gain, then
    measure the float-mask systematic separately and report it — do not choose one.
32. **Provenance belongs to the artefact, not the run** — restated because it recurred.
    Recording the binary at run level means a partial re-run stamps every preserved artefact
    with the last binary to execute, and a later before/after comparison silently compares a
    binary against itself. **The control that catches this must assert the two binaries
    DIFFER**, because byte-identity from one binary is trivially true.
33. **Preserved artefacts from an earlier run must be marked stale, and cross-run assertions
    must exclude them.** A hash from another binary neither agrees nor disagrees usefully
    with one from this run.

---

## 12. Applying ORCH's two fleet corrections

### 12.1 Rule 47 — re-audited under deliberate priming

The corrected mechanism is that `$LASTEXITCODE` is **not updated** after a truncated
pipeline, so it retains the *previous* command's code and a plausible-looking value is not
evidence the read was live. Re-auditing every gate in this milestone:

**No gate here was ever read through a truncated pipeline.** Two commands were truncated
(`... | Select-Object -Last 3` on the control run, `-Last 6` on the build), but neither was
followed by an exit-code read — both were judged on a **literal** printed by the program
(`14/14 bars passed`, ``Finished `release` profile``), which is what discipline 20 of
M110-track-jitter §3.1 requires and is immune to this entirely.

Re-run anyway, with the shell **primed by a deliberate failure** so that a live read is
provable rather than merely plausible:

| gate | primed | read | live? |
| --- | --- | --- | --- |
| `neutrality_control.py` | `1` | **`0`** | yes — could not have inherited |
| `scripts/corpus_lint.py` | `1` | **`0`** | yes |
| `ctrlchar_scan.py --selftest` | `1` | **`0`** | yes |

**No number in this report is invalidated.**

### 12.2 The here-string hazard — measured, not relayed, and it is less detectable than stated

`herestring_probe.ps1` writes the same six-backtick line through `@"..."@` and `@'...'@` and
dumps the bytes. **On PowerShell 5.1.26100.9168:**

| span | double-quoted result | bytes |
| --- | --- | --- |
| `` `bee-3-cpl` `` | `\x08ee-3-cpl` | `08 65 65 2D…` |
| `` `experiments/` `` | `experiments/` | **no control char** |
| `` `foam` `` | `\x0coam` | `0C 6F 61 6D` |

Single-quoted preserved **all 6** backticks and produced **0** control characters, confirming
the prescribed fix.

Two things follow that the fleet advice does not cover:

1. **The corruption is shell-version dependent.** `` `e `` became an escape in PowerShell 6,
   so on 5.1 the backtick is dropped and the `e` **survives** — `` `experiments/` `` came out
   as intact text. The same script therefore corrupts differently on 5.1 and 7.x. The 0x1B
   found in `M105b-exposure-ship.md` could only have been written under 7.x. **A scan that
   passes on one shell does not clear text authored on the other.**
2. **A control-character scan catches at most a third of the damage.** Of the six backticks,
   **zero survived**, but only **two** left a control character. The other four were deleted
   **with no forensic trace at all** — a markdown code span silently downgraded to plain
   text. **`corpus_lint` S7 cannot see this class**, because there is no control character to
   find, and it is the *more* common outcome.

`ctrlchar_scan.py` covers both classes, plus the gap S7 has by construction: it scans **git
commit message bodies**, which are neither markdown nor Rust and which is exactly where both
of tonight's M110 messages were built — in `@"..."@`, the hazardous form.

**For the silent class it counts backticks per **paragraph** and matches runs by CommonMark's
rule.**

**Result: 2 commit messages and 14 text files, clean** — for control characters and for
unmatched backtick runs alike.

**Its negative control fired three times before it passed**, and every failure was found by
**real corpus text, not by the control** — the control passed at 6/6 and again at 8/8 while
the check was still wrong:

- The **plant was wrong.** It deleted *both* ends of a span, leaving an **even** count and no
  signal. Deleting exactly one backtick made it fire. This is the standing rule that a
  positive control's plant must actually produce the quantity being detected.
- **Counting per line** flagged two real lines in `M110-track-jitter.md` where a code span
  legitimately **wraps across a line break**. Fixed by counting per paragraph.
- **Counting raw backticks** flagged two paragraphs of *this* report, because markdown's own
  way of writing a literal backtick — the ``  `e  `` form — makes a paragraph's raw count
  odd while being perfectly well formed.
- **Pairing runs by length** flagged the same two paragraphs again, because the inner single
  backtick of ``  `e  `` was counted as its own run instead of being consumed as span
  content. Fixed by CommonMark's actual rule: a run of N backticks is closed by the next run
  of exactly N, and everything between is content.

`--selftest` is now **9/9**: green → RED on plant → green on byte-identical restore, the
silent class shown invisible to the control-character scan and visible to the backtick
check, no false positive on a wrapped span, on the ``  `e  `` literal form, or on the exact
§12.2 paragraph shape that defeated the two previous versions — and it still fires on a
double-backtick span that has genuinely lost a delimiter.

**The lesson is about the control, not the check.** A synthetic self-test that passes does
not validate a check against real prose; the corpus is a better adversary than any plant I
wrote, and it found every one of these.

---

## 13. For ORCH — further facts and disciplines

Continuing from §11.

**Facts**

34. **MEASURED (PowerShell 5.1.26100.9168): the here-string hazard is shell-version
    dependent.** `` `b `` and `` `f `` fire (0x08, 0x0C) but `` `e `` does **not**, because it
    became an escape only in PowerShell 6 — `` `experiments/` `` survived intact on 5.1. The
    same script corrupts differently on 5.1 and 7.x, and the 0x1B in
    `M105b-exposure-ship.md:1312` could only have been written under 7.x. **A scan that
    passes on one shell does not clear text authored on the other.**
35. **MEASURED: a control-character scan catches at most a third of the damage.** Of six
    backticks written through `@"..."@`, **zero survived**, but only **two** left a control
    character; the other four were deleted with **no forensic trace**, silently downgrading a
    markdown code span to plain text. **corpus_lint S7 cannot detect this class by
    construction**, and it is the more common outcome. Single-quoted `@'...'@` preserved all
    six and produced zero control characters.
36. **MEASURED: no M110 artefact is affected.** Both M110 commit messages — built in
    `@"..."@`, the hazardous form — and all 14 text files scan clean for control characters
    **and** for unbalanced backticks.
37. **MEASURED: all three M110 gates are live reads.** Primed with a deliberate exit 1, each
    returned 0, so none inherited a stale code. No gate in this milestone was ever read
    through a truncated pipeline; the two truncated commands were judged on printed
    literals. **No number in this report is invalidated by the rule-47 correction.**

**Disciplines**

38. **A control-character check is a partial defence against here-string damage, not a
    complete one.** The silent-deletion class leaves nothing to find. Check that backtick
    runs pair up as well — **per paragraph, by CommonMark's rule** (a run of N closes with
    the next run of N, everything between is content), because code spans wrap across line
    breaks and ``  `e  `` legitimately makes a raw count odd.
39. **Scan commit message bodies too.** They are neither markdown nor Rust, so no corpus
    check covers them, and they are frequently built in exactly the shell construct that
    causes the damage. Read them as **bytes** via `git log --format=%B` through
    `subprocess`, never through a PowerShell redirect, which re-encodes the stream.
40. **Prove an exit-code read is live by priming the shell with a deliberate failure.** Under
    the corrected rule-47 mechanism a plausible code is not evidence of a live read; a `0`
    obtained after priming with `1` could not have been inherited. Cheap, and it converts an
    assumption into a measurement.
41. **A passing self-test does not validate a text check; run it against the real corpus.**
    This scanner's synthetic control passed at 6/6 and again at 8/8 while the check was still
    wrong, and **real prose caught every one of the three defects** — wrapped spans, the
    ``  `e  `` literal form, and inner backticks needing to be consumed as span content. Add
    each real counter-example to the control as it is found, so the control grows toward the
    corpus instead of staying where it was written.


