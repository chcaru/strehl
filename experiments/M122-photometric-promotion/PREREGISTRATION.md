# M122-photometric-promotion — PRE-REGISTRATION

Written and committed **before any drift number, any blotch number and any
correlation exists**. Nothing below may be narrowed, widened or reinterpreted
after a number exists. If a bar fails it is reported as FAILED.

Author: M122 (measurement milestone). Reports to ORCH.
Written: 2026-08-24, before the campaign.

---

## 0. THE QUESTION

SYNTHESIS open question **203**: *does blotch severity track measured level
drift across the corpus?* Fact 1640 makes this the deciding measurement for
flipping `STREHL_PHOTOMETRIC` on by default.

Fact 1640's chain, restated so that the link this milestone can break is
explicit:

1. frames differ in level by 3.2–8.4 % peak-to-peak (fact 1633, corroborating M24);
2. the difference is a smooth ramp a per-frame gain fit removes (fact 1634);
3. the merge elects different frames in different regions;
4. **so regions inherit different frame levels and smooth background acquires
   plateaus** (fact 1638's blotches);
5. and fitting the gain removes them (facts 1637, 1638).

Link 4 is the only one that predicts a **proportionality**: a subject should
show the defect in proportion to its level drift. That is what is measured here.

## 0.1 PRIOR WORK SEARCHED (AGENTS.md rules 40 and 43)

`docs/research/` was grepped for photometric/drift work before writing this.
Found and read: `M24-photometric-drift-measured.md`, `M91-photometry.md`,
`M97q-photometric-wiring.md`, `M99-photometric.md`, `M116-promotion.md`,
`M111-waxy-blobs.md`. SYNTHESIS facts 1633–1640 and disciplines 829, 831, 832,
834, 835 were read in full at `docs/research/SYNTHESIS.md`. **No milestone has
correlated per-stack drift against per-stack blotch response**; fact 1640 says
so in its own `Untested:` clause, and question 203 is open. This milestone makes
no assertion of absence beyond that one, which is established by the grep and by
the open question itself.

**M116 is not wrong and is not reported as wrong.** Its bar was a sharpness bar
(`Q = D − N`, +0.010 dex) and the defect under test here is tonal (fact 1639,
discipline 834). Both measurements stand.

---

## 1. PINNED BUILD, VERIFIED BEFORE USE

```
worktree : C:\dev\strehl-out\M116-tree           (git worktree, detached)
commit   : 4beac7300e318f6f0aaf10b6a88e57f311b9e814   (verified: git log -1, clean status)
binary   : C:\dev\strehl-out\M116-tree\target\release\strehl.exe
sha256   : 51B9235B7ACA203A1B171C69B6A5198E1EF2034F7E5446CE4891250AF7BBB078
bytes    : 8959488
mtime    : 2026-08-24 17:39:26
identity : `strehl --help` run, exit 0, four subcommands as expected
```

Using M116's own binary is deliberate: it makes every number here directly
comparable to M116's, and it makes the three shared subjects a **reproduction
check** (§7 R1). The shared working tree is **not** built in and is not used for
any number. `cargo` is invoked only for the §9 default-flip test, and only in a
separate pinned tree.

All output goes to `C:\dev\strehl-out\M122\`. **`D:\` is read-only and is never
written.** This is checked, not asserted: §7 R6.

---

## 2. STACKS

Every subject directory under `D:\personal\macro` containing ARW frames.
Enumerated before registration (a census, not a result):

| stack | ARW | L = min(100, N) |
|---|---:|---:|
| `109MSDCF` | 22 | 22 |
| `112MSDCF` | 79 | 79 |
| `113MSDCF` | 63 | 63 |
| `119MSDCF` | 33 | 33 |
| `bee-1-cpl` | 299 | 100 |
| `bee-2-cpl` | 299 | 100 |
| `bee-3-cpl` | 299 | 100 |
| `coffee-bean` | 105 | 100 |
| `coffee-bubbles` | 19 | 19 |
| `couch-fibers-cpl` | 299 | 100 |
| `dry-erase-marker-head-cpl` | 299 | 100 |
| `flat-on-ruler-cpl` | 79 | 79 |
| `flower-bud-alone-cpl` | 205 | 100 |
| `flower-bud-with-background-fern-cpl` | 299 | 100 |
| `flowers-cpl` | 176 | 100 |
| `foam` | 100 | 100 |
| `highly-angled-ruler-mm-cpl` | 299 | 100 |
| `lavendar-cpl` | 299 | 100 |
| `lead-1-cpl` | 123 | 100 |
| `leaf-2-cpl` | 182 | 100 |
| `tweezers-cpl` | 100 | 100 |
| `wrapped-text-1` | 130 | 130 → 100 |
| `wrapped-text-2` | 120 | 120 → 100 |

23 stacks. `flat-fields` holds 0 ARW and is excluded by that census, not by
judgement. `109MSDCF` is the pre-declared **low-drift control** (M24: 0.91 %,
the quietest stack in the corpus).

`--limit 100` is uniform so that runtime is bounded and the frame count, which
`STREHL_WARPMAP` validates, is one value per subject. **Stated limitation:** on
the eleven stacks with more than 100 frames this is a partial sweep, and drift
is therefore measured over exactly the frames merged (first L in filename
order) and over no others. No claim is made about frames beyond L.

---

## 3. ARMS

Solved once per subject and frozen, so registration is held constant and cannot
be a confound:

```
align : strehl align <dir> --limit L --out C:\dev\strehl-out\M122\warp\<S>-l<L>.txt
        env: STREHL_CACHE_DIR=C:\dev\strehl-out\M122\cache   (fresh solve, isolated
             from any cache another agent may have written), all other STREHL_* cleared
```

```
A0 : strehl stack <dir> --limit L --gate 4 --out ...\measure\<S>__A0.tif
     env: STREHL_WARPMAP=<the frozen sidecar>; every other STREHL_* variable CLEARED
A1 : strehl stack <dir> --limit L --gate 4 --photometric --out ...\measure\<S>__A1.tif
     env: STREHL_WARPMAP=<the frozen sidecar>; every other STREHL_* variable CLEARED
```

Flags left at default, recorded because a default is not a record (rule 47):
`--srgb` off, `--demosaic` off, `--binned` off, `--exposure 0`,
`--auto-exposure` off, `--index-map` unset, `--n-eff-map` unset, `--stats` off,
`--stats-placebo` off, `--flat-roi`/`--detail-roi` unset,
`--confidence-tail 0.05`, thread count default. Environment variables the tool
reads and that are **explicitly cleared** on every invocation: `STREHL_ALIGN`,
`STREHL_PHOTOMETRIC`, `STREHL_SOFT_GATE`, `STREHL_FIX_CA`, `STREHL_FIX_HALO`,
`STREHL_FIX_HALO_DELTA`, `STREHL_SMOOTH`, `STREHL_SMOOTH_HUBER`,
`STREHL_DUMP_NEFF`, `STREHL_DUMP_ELECTION`, `STREHL_DUMP_MERGE_STATE`,
`STREHL_FREEZE_REQUIRE`, `STREHL_CAPTURES` (plus `STREHL_WARPMAP` and
`STREHL_CACHE_DIR`, which are set per arm as above).

For every invocation the driver records: argv, the environment record, exit
code, wall seconds, output SHA-256 and byte count (rule 47). Exit codes are
captured into a variable on the line after the call and no pipeline containing
`Select-Object -First` sits between the process and the status (rules 46, 47).

Measurement is on the **default** output — binned, linear, camera-native 16-bit
RGB — because `stack --help` states the `--srgb` file is not to be measured.
All TIFF reads use `tifffile.imread` with `assert dtype == np.uint16` on the
next line (`PIL.Image.open` downconverts 16-bit RGB TIFFs and has already
invalidated measurements in this project).

---

## 4. THE TWO MEASURED QUANTITIES

### 4.1 Drift, `Dpp` — primary

Per-frame mean of the CFA green plane, over exactly the L frames merged, in
filename order:

```
level_k = mean( raw_image_visible[0::2, 1::2] - 512 )      for frame k
rel     = level / mean(level)
Dpp     = 100 * (max(rel) - min(rel))          # per cent peak-to-peak
```

This is **M24's estimator verbatim** (`experiments/m24-photometric-drift/src/01-levels.py`),
which is why it is the primary: it is commissioned against four independently
folded numbers (§7 R2) rather than against itself. `raw_image_visible` is used,
not the full decoded buffer (rule 7), and the slice is copied inside the
`with rawpy.imread(...)` block on the same line as the cast (rule 32).

It is also the estimator least exposed to question 202's breathing confound:
defocus and magnification redistribute light within the frame but conserve it,
so a whole-visible-plane mean is close to invariant to both, while a fixed
window is not.

**Secondary drift estimator, `Dwin`:** the same per-frame levels taken over six
widely separated fixed 256-px background windows on the raw green plane
(`level_drift_budget.py`'s window scheme, generalised to any stack), reported as
the median per-window peak-to-peak. Reported for agreement with `Dpp`; it does
not enter the primary criterion.

### 4.2 Blotch response, `B12` — primary

`photometric_ab.py`'s statistic and its **window-selection rule unchanged**,
generalised only in which files it opens:

```
scan   : S=256 windows, BORDER=400, STRIDE=128, over the SYMMETRIC MEAN (A0+A1)/2
         -- so neither arm chooses the pixels it is judged on (discipline 831, fact 1630)
pool   : windows whose mean >= the 80th percentile of all window means  (background is bright)
SMOOTH : the 12 lowest-`w[::8,::8].std()` windows of that pool
hf(w)  : RMS of the 4-neighbour laplacian of w
B12    : median over the 12 SMOOTH windows of hf(A1)/hf(A0)          <- PRIMARY
B6     : median over the 6 smoothest of them                          (secondary; the
         subset fact 1637 quotes as 0.632-0.812 on tweezers-cpl)
sdd    : sd after removing a best-fit plane; `Sdd12` is its median ratio (secondary)
```

`B12 < 1` means the photometric arm carries **less** manufactured fine
structure in smooth background. `S`, `BORDER`, `STRIDE`, `NWIN`, the 80th
percentile and the `[::8,::8]` smoothness probe are **fixed here and are not
tuned per stack**.

**Direction it can be fooled in (rule 18):** `hf` falls when an arm removes
manufactured structure *and* when an arm simply blurs. It is therefore
inadmissible alone and is only ever read beside the texture control §5.3. It
also has a **floor**: an arm cannot go below the sensor/merge noise floor, so a
stack whose A0 smooth windows already sit at that floor cannot produce
`B12 < 1` however much drift it has. That floor is a live alternative
explanation for any correlation and is tested in §6.2, not waved at.

### 4.3 Texture control, `T12`

From the same scan of the same symmetric mean, the 12 windows with the
**highest** `w[::8,::8].std()` — no brightness gate, because texture may be
dark. `T12` = median `hf(A1)/hf(A0)` over them. The effect must be confined to
smooth windows and absent here.

---

## 5. CONTROLS THAT MUST RUN, WITH THE INPUT THAT WOULD FAIL EACH (rule 20)

### 5.1 The commissioning triple, per stack, on that stack's own pixels
`photometric_ab.py`'s controls, unchanged, run inside the scoring run:

| control | requirement | what failure means |
|---|---|---|
| NULL `hf(w)/hf(w)` | **exactly** 1.0000 (`< 1e-12`) | the statistic is not a ratio of the same thing |
| PLANT+ voronoi-over-base | `> 1.30` on `hf` and `sdd` | it cannot see manufactured plateaus |
| PLANT− base-over-voronoi | `< 0.77` on `hf` and `sdd` | **it cannot see a REDUCTION, which is the direction under test** |

PLANT− is the control that matters. A stack whose commissioning fails is **not
interpretable** and is excluded from the correlation, named, with its numbers.

### 5.2 Bit-identity, per stack
`SHA256(A0) != SHA256(A1)`. If they are equal the flag did nothing and any null
on that stack is a **plumbing null, not a physics null**; the stack is excluded
and reported as such.

### 5.3 Blur control, per stack that shows an effect
Required on every stack with `B12 < 0.97`: `T12 >= 0.97`. If laplacian RMS falls
in textured windows too, the arm is blurring and the result is a defect, not a
fix.

**Power check for the blur control (rule 20), run on every stack:** score
`gaussian_filter(A0, sigma=0.5)` as if it were the test arm. It **must** read
`< 0.90` in the TEXTURED set. If it does not, the texture control has no power
on that stack and the blur control is reported as unable to fire there.

### 5.4 Low-drift control
`109MSDCF` (M24: 0.91 %) is pre-declared as the quietest stack. The mechanism
predicts it shows little or no benefit. Registered as a criterion in §6.1 P5 on
whichever stack **measures** lowest, so that the control is not decided by a
prior number.

### 5.5 Correlation instrument self-test
The Spearman + permutation code is run first on two synthetic pairs and must
return: a perfectly monotone pair → `rho = 1.0`, `p < 1e-3`; an independent
random pair → `|rho| < 0.5`, `p > 0.05`. Without this the correlation is
arithmetic, not evidence.

### 5.6 Reproduction of M116 (§7 R1)
On `bee-3-cpl`, `foam`, `tweezers-cpl` the A0 and A1 outputs must be
**byte-identical to M116's** committed hashes. Byte-identity is a consistency
check, not independent evidence (discipline 20) — but a mismatch means the
pipeline is not the one M116 measured and nothing downstream is comparable.

---

## 6. THE ANSWER TO QUESTION 203, AND THE CRITERION

### 6.1 Primary test

Spearman rank correlation across all usable stacks between

```
x = Dpp            (per cent peak-to-peak level drift over the merged frames)
y = 1 - B12        (blotch reduction; positive = the photometric arm removes structure)
```

`p` by **20 000 random permutations of the stack labels**, reported one-sided in
the pre-registered direction (positive) and two-sided, with the permutation
null's sd (rule 39: no ratio without the null it is measured against).

**PROMOTE** requires **all** of:

- **P1** at least 12 usable stacks;
- **P2** `rho >= +0.50` and one-sided permutation `p < 0.05`;
- **P3** no harm: `B12 <= 1.03` on **every** usable stack;
- **P4** blur control clean: every stack with `B12 < 0.97` has `T12 >= 0.97`;
- **P5** low-drift control: the usable stack with the **lowest measured** `Dpp`
  has `B12 >= 0.97`.

**KEEP-OFF** if **any** of:

- **K1** `rho < +0.20`, or one-sided permutation `p >= 0.05`;
- **K2** any usable stack has `B12 > 1.03`;
- **K3** any stack with `B12 < 0.97` has `T12 < 0.97`.

Anything else is **INCONCLUSIVE**.

**Power check, registered now so it cannot be invoked selectively:** if the
inter-quartile range of `B12` across usable stacks is `< 0.02`, the corpus
carries no blotch-response variation for drift to correlate with, the test had
no power, and the verdict is INCONCLUSIVE **whatever `rho` reads**. The same
applies if the IQR of `Dpp` is `< 1.0` percentage points.

### 6.2 What would say fact 1640 has a broken link

Registered in advance, either of:

- **L1** `|rho| < 0.20` with `p >= 0.05` **while** at least one stack reads
  `B12 < 0.85`. The blotch is real and does not track drift, so link 4 —
  *regions inherit different frame levels* — is not what sets its severity.
- **L2** any stack with `Dpp < 1.5 %` reads `B12 < 0.85`: a strong fix where
  there is almost no drift to fix. One such stack is enough; the mechanism
  cannot produce a large correction from an absent input.

A null here is a **result**, not a failure, and will be reported as the headline
if that is what the data say.

### 6.3 Adversarial analyses, registered before the numbers exist

- **A1 (the floor confound).** Report `hf(A0)` in the SMOOTH set per stack.
  Compute `rho(Dpp, hf(A0))` and the **partial** Spearman of `(Dpp, 1-B12)`
  controlling for `hf(A0)`. If the partial `rho` falls below `+0.20`, the
  headline correlation is reported as **confounded by baseline structure**: high
  drift stacks would simply be the ones with room to fall.
- **A2 (absolute, not ratio).** `dHF = median(hf(A0) - hf(A1))` in counts, which
  has no floor-induced ceiling in the way a ratio does, correlated against `Dpp`.
- **A3 (second statistic).** `Sdd12` — the plane-detrended sd ratio — correlated
  against `Dpp`, as an independent read on the same defect.
- **A4 (drift estimator choice, discipline 829).** `Dwin` against `Dpp`. If they
  disagree, the analysis is repeated with the estimator that **argues against**
  the conclusion, and both are reported.
- **A5 (the arm's own predictor).** Fitted per-frame photometric gain spread as
  printed by the binary on A1, where it prints one, against `Dpp`.

### 6.4 Exclusion rules, fixed now

A stack is excluded from the correlation only for: align or either arm exiting
non-zero (E2); `SHA256(A0) == SHA256(A1)` (E3); commissioning failure (E4);
fewer than 12 windows in the scan (E5). Every exclusion is named in the report
with its numbers. **No stack is excluded for being inconvenient.**

---

## 7. RUNS, CHECKS AND THEIR IDENTIFIERS

- **R1** M116 reproduction: A0/A1 SHA-256 on the three shared subjects.
- **R2** drift-instrument commissioning: my `Dpp` against M24's published
  `109MSDCF` 0.91 %, `119MSDCF` 2.88 %, `112MSDCF` 6.84 %, `coffee-bubbles`
  8.93 %, `coffee-bean` 11.70 %. M24 subsampled (`sub` = 1/2/3) and capped at
  `nmax = 40`; **my run uses the merged frame set instead**, so agreement is
  expected in magnitude and ordering, not to the digit. Registered now: I re-run
  M24's exact sampling as a separate arm so that the comparison is like for
  like, and report both.
- **R3** the commissioning triple, per stack.
- **R4** bit-identity, per stack.
- **R5** blur control and its power plant, per stack.
- **R6** read-only guarantee: a recursive `Get-ChildItem -Force` file count and
  byte total of `D:\personal\macro` before and after the campaign (rule 14:
  without `-Force` this under-reports and looks like evidence of modification).

---

## 8. IMAGES

Shared-stretch before/after sheets (`photometric_look2.py`'s scheme) for the
stack with the largest `|1 - B12|` and for the lowest-drift stack, at the
smoothest window and at a textured window. **Both panels of every pair share one
stretch, taken from the A0 arm.** Independent per-panel stretching makes the
comparison meaningless and is not done.

---

## 9. THE DEFAULT FLIP

Attempted **if and only if** §6.1 returns PROMOTE.

Before touching `crates/strehl-cli/src/main.rs`: run `git status` and
`git log -3 --oneline`; if that file carries uncommitted modifications or a very
recent commit by another agent, **do not edit it** — the exact patch goes in the
report, marked blocked on ownership. If it is clean: flip the default, add or
update a test that pins the new default, and build and run the narrowest test
covering it in a **separate pinned worktree**, never in the shared tree. `cargo
test` output is read for the `Compiling` line, and `-q` is never used (rule 33).

If the verdict is KEEP-OFF or INCONCLUSIVE, **no file under `crates/` is
touched**, and the report says so.

---

## 10. WHAT THIS MILESTONE WILL NOT CLAIM

- Nothing about frames beyond `--limit L` on the eleven deep stacks.
- No claim that `hf` is a perceptual quality measure. It is a laplacian RMS with
  two stated failure directions and a floor.
- No claim that M116 was wrong. Its bar was on a different axis (fact 1639).
- No claim about `--photometric` in combination with any other instrument. The
  soft gate, the CA fix and the halo fix are not arms.
- No claim that the correlation identifies the *cause* of the blotch. A
  correlation over 23 stacks with one manipulated variable is evidence about
  link 4 of fact 1640's chain and nothing more; sufficiency is not attribution
  (fact 1635 says this of its own number and it is repeated here).
- No claim about question 202 (illumination versus breathing). `Dpp` is chosen
  to be robust to it, not to resolve it.
