# M110-sheet — a reproducible comparison-sheet harness

**Status:** delivered. Harness committed at `66ba510`; sheets produced tonight against
`HEAD 5e4fbc4b74b2`.

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
coordinates), `render` (all arms, all subjects, writes the manifest), `figure` (builds the
PNGs). `--subject <name>` restricts; `--limit N` renders a short stack for a smoke test.

Adding an arm is adding a dict to `ARMS` in `sheet.py`:

```python
{"name": "ca-corrected", "align": [], "merge": ["--some-flag"], "env": {}, "note": "..."}
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
