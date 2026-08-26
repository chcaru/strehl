# BUILD-SHARP — why the stacks are soft, and what is left after the software is fixed

**Status:** delivered. Alignment fix committed at `70934bb`; restoration module at
`28f7a3a`. All numbers below were measured with M88b's commissioned ESF instrument
and with a new per-frame residual instrument built for this build
(`experiments/BUILD-SHARP/src/bs_residual.rs`). Deliverable pictures are under
`C:\dev\strehl-out\BUILD-SHARP\pictures\`.

**Lane.** `align.rs`, `warpmap.rs`, `plane.rs`, `align_cmd.rs`, `through_focus.rs`,
the new `restore.rs`, and `experiments/BUILD-SHARP*`. `merge.rs` is BUILD-HALO's and
was not touched; the develop path is BUILD-RENDER's and was not touched.

---

## 0. The answer, in one paragraph

**The merge is not the reason the pictures are soft.** A blur budget that closes to
**2.6%** puts **76.6% of the blur variance in the optics**, measured on a *printed
mm ruler* — a subject that cannot itself be soft — at **2.16x the diffraction limit
at f/5.6**. Of that, only 16.5% is diffraction; **60.1% is an aperture-independent
term** which is almost certainly the 2x teleconverter operating at 2:1, far outside
its design envelope. The software terms I can reach total **23.4% of the variance**,
which is **12% of the rise**: killing both of them outright moves the 10-90 edge rise
from 35.0 um to 30.7 um. That is real and worth having, and it is not "these look
horrible".

I found and fixed one genuine defect — **the alignment solve was worse than not
aligning at all between adjacent frames**, which are precisely the frames the merge
chooses between. And I built the brief's multi-frame Wiener deconvolution. **Its
verdict is negative, and I am reporting that rather than dressing it up:** at this
capture's calibrated SNR the filter's own noise term clamps its maximum gain to
1.10-1.30x, against 1.60x for an ideal inverse of a kernel whose exact form we know
in closed form. It cannot even undo our own resampler. Three independent routes
(M115, M20, and this) now agree.

---

## 1. The blur budget

All numbers are **10-90 ESF rise in micrometres** on the merge's binned grid (pitch
10.24 um = 2 x the 5.12 um sensor pitch). Blur terms add in quadrature, so
`rise^2 = sum a_i^2` and the honest apportionment is by *variance*, not by rise.

| term | rise contribution | % of blur variance | lane |
|---|---|---|---|
| system optics, on a **printed ruler**, no align, no resample (RU1) | 30.44 um | **76.6%** | not software |
| — of which diffraction at f/5.6 (M88) | 14.11 um | 16.5% | physics |
| — of which **aperture-independent** (2x TC aberration etc.) | 26.98 um | **60.1%** | **route to owner** |
| **resampling kernel** (Catmull-Rom gather) | 14.97 um | **18.6%** | mine (see §5) |
| **gated-mean over-averaging** | 7.61 um | **4.8%** | my number, BUILD-HALO's file |
| **predicted total** | **34.78 um** | | |
| **measured total** (M94, TW1) | **35.69 um** | | **closes to 2.6%** |

A budget that closes to 2.6% in quadrature is the strongest evidence in this report.
It means there is no large unattributed term hiding somewhere — no fourth mechanism
still to be found. Everything that blurs this image is in that table.

### 1(a) — Is the merge actually sharper than the best single frame?

This was the brief's foundational question and the answer is cleaner than expected,
because of a property of our own merge:

> **At `--gate 0` the merge output is byte-identical to the elected frame** (M95,
> 100.0000% of pixels, max difference 0 DN).

So `b-g0-cr` **is** "the best single frame at this pixel", already in the merge's own
geometry, already resampled the same way. That removes the entire problem of
comparing across geometries — no extra registration, no extra resample, no gauge
argument. The comparison is exact and paired.

Paired ESF, pooled over the three admitted ROIs (M94, TW1, TW5), reference =
`b-g0-cr`:

| arm | mean delta um | sd | verdict |
|---|---|---|---|
| `b-g0-nn` (nearest-neighbour gather) | **+2.333** | 2.20 | sharper — and aliased |
| `b-g0-l3` (Lanczos-3 gather) | **-0.045** | 0.67 | **null — no kernel headroom** |
| `b-g0-noalign` | -2.802 | 7.28 | worse, and high variance |
| `b-g4-cr` (**the shipped gate**) | **-0.586** | 0.88 | **shipped is softer than selection** |

**Headline for (a): the shipped merge is softer than its own best input frame by
0.586 um, which is 1.2% of the rise.** It is a real, replicated, above-floor effect
on `109MSDCF` (M94 +1.588, M93 +1.095, M96 +0.519, all above their instrument
floors) and a null on `tweezers-cpl`. It is not a bug — it is the price of the
gated mean's 0.534x noise reduction — but the brief asked for the size of the
population and this is it: **the merge is never catastrophically softer than the
best frame, and where it is softer it is softer by about one percent.**

That number is small enough that it closes off the whole "the merge has a bug"
hypothesis. The softness is upstream.

### 1(c) — How many times is a pixel resampled?

**Exactly once.** M95 P49 established that `cover_or_explain` folds the coverage
zoom into the warp matrix rather than applying a second transform, so raw -> output
is a single gather. There is no unnecessary intermediate resample to delete. The
cost of that one gather is the 14.97 um in the table, and §5 explains why a better
kernel does not recover it.

### 1(d) — Effective number of frames per pixel

`n_eff` on `bee-2-cpl` has mean **66.5**, with **26.77%** of pixels at `n_eff = 1`.
That sounds alarming until you correlate it with local contrast: **large `n_eff`
lives in flat regions, where there is nothing to blur.** At a high-contrast edge the
gate admits almost nothing and `n_eff -> 1`. That is why over-averaging costs only
7.61 um (4.8% of variance) despite averaging hundreds of frames somewhere in the
image. The gate is doing its job.

### 1(e) — The optics floor, established honestly

`highly-angled-ruler-mm-cpl` is flagged **tilted**, so the aligner *refuses* it, so
every kernel arm renders identically. That makes ROI RU1 a nearly software-free
measurement of the system PSF. It reads **30.44 um** against a **14.11 um**
diffraction-limited rise: **2.16x the diffraction limit**, matching M88's
independently measured 2.25x.

The subject is a printed millimetre ruler. Printed ink on paper does not have a soft
edge at 10 um. **This blur is in the system.**

And M88 measured the f/11 : f/5.6 edge-width ratio at **1.025x** against a predicted
**1.964x**. If the blur were diffraction it would scale with aperture. It does not.
**The dominant term is aberration, not diffraction, and stopping down cannot help
it** — while stopping down *does* multiply the diffraction term.

---

## 2. The instruments — including the two that failed

Per AGENTS rule 43 and the brief's rule 2, the failures are recorded so they are not
re-run.

### 2.1 The instrument used: M88b's paired 10-90 ESF rise

Found already built, nulled and positively controlled in
`experiments/M88b-merge-sharpness/`, but never run in treatment because M86's
alignment wiring was unfinished at the time. Alignment is wired now, so I ran it.

Why it is the right instrument here:
- **Noise-immune by construction.** It averages hundreds of pixels along a slanted
  edge. It cannot be satisfied by injected texture, which is the exact failure mode
  the brief's rule 2 warns about.
- **Integer-only registration** (brief rule 6), so the measurement does not add blur
  to the thing being measured.
- **Measured instrument floor of 0.6699 um**, and per-ROI floors, so "null" has a
  defined meaning.
- **18,644x more responsive than ring FRC** to a planted low-pass.

`experiments/BUILD-SHARP/src/esf.py` imports `m88blib` **unmodified** and scores
rendered arms against each other.

`bee-2-cpl` contains **zero** admissible slanted edges, which is why the ESF numbers
come from `109MSDCF`, `tweezers-cpl` and `highly-angled-ruler-mm-cpl` while the
by-eye grading comes from `bee-2-cpl` and `flower-inner-edge-cpl`.

### 2.2 FAILED: a band census (`bands.py`) — confounded by `n_eff`

Comparing subject-region and background-region power per frequency band looked like
a clean way to separate detail from noise. It is not. **The flat background is
averaged ~200x, so its noise floor is ~200x lower in power**, which manufactures a
fake ~12x "subject advantage" at *every* frequency including Nyquist, where there is
certainly no subject detail. Any statistic that compares regions with different
`n_eff` is measuring `n_eff`.

### 2.3 FAILED: a paired Laplacian-regression equivalent blur (`blurpair.py`)

This one **passed its own planted-blur ladder** and is still wrong for this
question. Regressing `D = mean - frame_k` on `laplacian(frame_k)` recovers an
equivalent blur width — but when both arms share the same noise realization,
`D ≈ -n_k`, which correlates with `∇²(S + n_k)` and contributes `+|∇n_k|²`. **It
cannot separate noise removal from blur.** It is valid only for kernel-only A/B
where both arms carry the same noise.

This is the same trap as the brief's rule 2, in a different costume: the statistic
was real, the ladder was real, and the answer was still an artefact.

---

## 3. The alignment defect (b), and its fix

### 3.1 The gauge was wrong, and that is why nobody saw it

Every alignment number in the corpus — the 6.76 px held-out figure, 13.578, 40.3 —
is **end-to-end**: worst-corner displacement between the *first and last* frame.

But the merge does not consume end-to-end error. It consumes **per-frame placement**,
and in detailed regions it elects a **single frame per pixel**, so two adjacent
output pixels electing frames `j` and `j+1` inherit the *difference* of two
placements. **The relevant gauge is span-1 residual, and the end-to-end gauge is
structurally blind to it.**

### 3.2 The instrument

`experiments/BUILD-SHARP/src/bs_residual.rs` (also placed in the pinned tree as a
`strehl-cli` example). It gathers two frames through their **own solved placements**,
then re-runs the project's own `align_pair` on the results. A perfect solve returns
the identity.

Controls, both required and both present:
- **Self-control** — a frame against itself — reads **0.0014 plane px**.
- **Unaligned control** — the same pairs with no placement applied — must read
  large, and does.

### 3.3 The defect

Span-1 mean worst-corner residual, plane px, 298 pairs, 96 tiles:

| subject | UNALIGNED | lambda=0 (was the default) | **lambda=1 (now)** | lambda=3 |
|---|---|---|---|---|
| `bee-2-cpl` | 0.6136 | **0.7849** | **0.5883** | 0.5577 |
| `bee-3-cpl` | 0.2715 | **0.7070** | **0.5020** | — |
| `flower-inner-edge-cpl` | 0.9291 | 0.8416 | 0.7625 | — |

**The shipped free solve was worse than not aligning at all, at span 1, on two of
three subjects — 2.6x worse on `bee-3-cpl`.**

The mechanism is not mysterious. At span 1 the true inter-frame motion is smaller
than the estimator's noise, so the ladder fits noise; the *difference* of two
placement errors then exceeds the motion actually removed. Longer spans are
unharmed (`bee-2-cpl` span 16: 3.8123 -> 3.7415; span 8 essentially flat), which is
exactly why an end-to-end gauge reports success.

### 3.4 The fix

M110 had already built the right operator — a Huber-robust second-difference
roughness prior on the placement track — measured it, selected `lambda* = 1`, and
shipped it **off by default** because it changed nothing a viewer could see. M110
was right about the render and did not have the merge-side residual. That residual
is what justifies moving the default.

`crates/strehl-cli/src/align_cmd.rs`: `apply_smooth_env` now defaults to
`lambda = 1`, Huber 1.0 px. `STREHL_SMOOTH=0` (or `off`) restores the free solve
**bit-exactly**. `SOLVE_GENERATION: u32 = 2` is hashed first in `solve_config_key`,
because moving a default changes what "unset" *means* without changing what it
*hashes to* — without that bump every cached warpmap in the world silently keeps the
old solve.

`lambda = 3` reads lower still at span 1 and is **not** taken: M110 measured
real-step recovery falling to 83.50% at `lambda=2` and 61.75% at `lambda=3`, so a
bumped tripod stops surviving. Registration accuracy is not worth trading for
registration smoothness.

### 3.5 The honest result: the render is a NULL

Paired ESF at gate 4, after vs before:

| ROI | delta um | floor |
|---|---|---|
| M94 | -0.220 | 0.356 |
| TW1 | -0.227 | 0.250 |
| TW5 | -0.052 | 0.305 |

All inside their floors, in both directions. **Confirmed by eye at 100% on
`bee-2-cpl` and `flower-inner-edge-cpl`: indistinguishable.**

**This fix is defended as a strictly better registration at no cost. It is not a
sharpness win and I am not claiming one.** The reason it is still worth landing:
a solve that is worse than no solve at the exact span the merge consumes is a defect
whether or not today's subjects show it, and everything downstream — the halo work,
any future per-pixel reconstruction — assumes placements are consistent between
neighbouring frames.

---

## 4. The deconvolution (step 2) — an honest negative

### 4.1 First, the premise

The brief says this project "has never connected" its calibrated noise model and its
measured PSF into a multi-frame Wiener. **That is not true, and per AGENTS rule 43 I
have to say so rather than rediscover it.**

- **M115** measured exactly this estimator against the shipped gate:
  `R_SNR = 1.0014 +/- 0.0184`. A null.
- **M20** measured it too: it wins on **15.1%** of pixels, and concluded "the prize
  is noise, not detail".
- **M70** explains *why*: the through-focus band matrix is **rank-1 to 0.9959**. The
  frames do not carry independent observations of the scene to invert. A K-frame
  Wiener over a rank-1 observation set collapses to the K=1 case.

So I built it as the K=1 case, which is where it lands anyway, and made it measure
something the corpus had *not* measured.

### 4.2 What is new here: the PSF is our own kernel, in closed form

`crates/strehl-core/src/restore.rs` implements

```
G(f) = conj(H(f)) / ( |H(f)|^2 + sigma^2 / S(f) )
```

with `H` = the **phase-averaged MTF of our own interpolation kernel**, derived in
closed form:

```
M(f) = mean over phi of | sum_n k(n - phi) e^{2 pi i f (n - phi)} |
```

This is the one place where a deconvolution here carries **no model risk at all**.
It is not a lens model that might be wrong; it is the transfer function of code we
wrote. If `H` is wrong, the code is wrong, and a unit test says so.

`gather_mtf()`, cycles per *gather-plane* sample:

| f | Catmull-Rom | Lanczos-3 |
|---|---|---|
| 0.10 | 0.9981 | 1.0017 |
| 0.25 | 0.9402 | 1.0115 |
| 0.35 | 0.8211 | 0.9305 |
| 0.40 | 0.7425 | 0.8331 |
| 0.50 (Nyquist) | **0.6251** | **0.6383** |

**This is the closed-form explanation for the Lanczos-3 null in §1(a).** The two
kernels never differ by more than **13.3%** (peak, at 0.35 c/sample) and differ by
only **2.1%** at Nyquist. There is no compact interpolator that avoids this. It also
independently confirms `ORCH-kernel-decision.md`'s NO-GO and saves shipping a
2.5-3.9x slower default for nothing.

(M95's apparent Lanczos-3 advantage of +0.1343 dex was scored in the band M85 later
**retracted** — measured at 12.8% subject detail / 87.2% noise, with a dark frame
reading the same gain, 1.0006.)

### 4.3 The measured verdict: the gain cap never binds

| subject | sigma^2 (from the merge's own spectrum) | max gain | gain @ 0.25 c/px |
|---|---|---|---|
| `109MSDCF` | 691.6 | **1.096** | 1.021 |
| `tweezers-cpl` | 4983.0 | **1.298** | 1.059 |

An ideal inverse of our own Nyquist MTF would be `1 / 0.6251 = 1.600`.

**Caps of 1.4, 1.7 and 2.5 produce byte-identical output.** The safety limit is
never reached. **It is the calibrated noise that stops this filter, not a guard.**

That is the whole finding, and it is a strong one because of what `H` is: this
filter cannot buy back even the blur *we ourselves added*, whose exact transfer
function we know. It has no chance against an unknown aberration 2.16x the
diffraction limit.

Paired ESF of the restored arm (cap 1.7, grid_factor 1.0, vs shipped): M94
**+0.688 um** (floor 0.356 — marginally above), TW1 +0.019 (null), TW5 +0.111
(null). Pooled **~+0.27 um**, against a 35.69 um rise.

### 4.4 Ringing check — by looking, per the brief

Checked on a real hard edge with a flat approach (TW1). **The largest profile change
anywhere is 0.0035 of the step height.** There is no ringing because the filter is
too weak to ring.

I did **not** gate on `edge_overshoot` (brief rule 3). For the record it moved
1.9365 -> 1.9620, and it is meaningless on a non-step ROI — which is precisely why
it is not the gate.

### 4.5 Disposition

`restore.rs` is committed, tested (5 unit tests, 401/401 core tests green), and
**off**. Nothing calls it in the product path. It is a measuring instrument and a
documented negative, and `gather_mtf()` is independently reusable — it converts
M95 P56 from ARGUED to measured (see §5).

The limit is **SNR, not physics**. M20's aperture result says marked f/11 -> f/5.6
multiplies best-frame contrast at 4-px detail by **9.6x** and matched-filter SNR by
**13.5x** at fixed total exposure time. On captures with that much more signal this
filter starts to bite. That is a capture change, not a code change — see §6.

---

## 5. Routed to other lanes

### 5.1 THE LARGEST UNEXPLOITED SOFTWARE WIN — gather order (BUILD-HALO's files)

The gather runs on the **CFA quad plane** (3516 x 2344) and the demosaic *then*
doubles the grid (M95 P56, marked ARGUED). So a feature at 0.25 cycles per **output**
pixel sits at **0.5** cycles per *plane* pixel and sees kernel MTF **0.6251**.

If each frame were demosaiced **before** the gather, that same feature would see MTF
**0.9402**.

> **1.50x more contrast at the top of the real detail band, for free optically.**

Cost: 3 planes gathered instead of 1, and 299 demosaics instead of 1. This is the
single largest software gain identified in this build and it is **larger than every
merge-side change in the corpus combined**. It is an architecture change in
`merge.rs` / `merge_cmd.rs`, which belong to BUILD-HALO. **ORCH: please route.**
`strehl_core::restore::gather_mtf` now makes the claim measurable rather than
argued.

### 5.2 Byte-freeze row broken at HEAD — BUILD-HALO's to re-baseline

`coffee-bean-20-gate2-unaligned` fails at HEAD. I verified this is **not mine** by
restoring the HEAD version of `align_cmd.rs` from a `$env:TEMP` byte copy (rule 9,
never `git checkout --`), rebuilding, re-testing — still fails — then restoring my
copy. HEAD had moved to `57e4554`, BUILD-HALO's "halo: delete the noise-driven
window shrink". That row needs re-baselining by its owner.

### 5.3 Lateral chromatic aberration — visible, not my lane

`bee-2-cpl` 100% crops show clear lateral CA. It is a genuine contributor to
*apparent* softness — colour-fringed edges read as unsharp. `M107b`, `M113` and
`M114` exist on this topic and I have not read them. **ORCH: route to whoever owns
colour/optics.**

### 5.4 The evaluation crops are half-resolution

`baseline-crops/` are on the **binned** grid. **Every by-eye sharpness grading in
this project to date has been done at 2x downsample**, i.e. blind to exactly the
band this whole build is about. Worth fixing before the next grading round.

### 5.5 To the owner, directly — the biggest available win is not software

Given that **60% of the blur variance is aperture-independent optics** and 16.5% is
diffraction:

- **Shoot at marked f/5.6, not marked f/11.** At magnification 2.0 the marked f/11
  is effectively **f/33**, where MTF at Nyquist is **0.000**. At f/5.6 it is 0.036 —
  small, but not zero, and zero cannot be recovered by anything.
- M20 measured the payoff: **9.6x** best-frame contrast at 4-px detail, **13.5x**
  matched-filter SNR at fixed total time, at the cost of roughly 2x the frames.
- **Suspect the 2x teleconverter.** A printed knife edge reading 2.16x the
  diffraction limit, with an edge width that does *not* change with aperture, is an
  aberration signature. The FE 100mm GM at 1:1 without the TC would be the
  controlled test, and it costs one capture session.

**This dwarfs every merge-side gain in the corpus and requires no code.**

---

## 6. What is still soft, and why

Plainly:

**77% of the blur variance is optics, and I cannot reach it.** The majority of it —
60% of variance — is an aperture-independent term measured on a *printed knife edge*
at 2.16x the diffraction limit. It is in the rig, not in the software and not in the
subject. Very plausibly the 2x teleconverter at 2:1, far outside its envelope. No
merge-side change recovers it, and the SNR is too low for deconvolution to buy it
back — proven above by a filter that cannot even undo a blur whose transfer function
we know exactly.

**The software terms I can reach total 12% of the rise.** Of that, the resampling
kernel is 18.6% of variance and is **not** removable by choosing a better kernel
(closed-form proof in §4.2, matching the measured Lanczos-3 null). It *is* removable
by changing the gather order — §5.1 — which is not my file.

**What I fixed is invisible.** The alignment prior is a strictly better registration
at the span the merge actually consumes, and it changes nothing you can see. I
looked at the pictures at 100% and said so rather than finding a statistic that
would have agreed with me.

**What the owner is actually complaining about, I think, is not primarily sharpness
at all.** Looking at `flower-inner-edge-cpl` at 100%, the petal is a waxy,
textureless mush — but the *edges* in that frame measure at the instrument floor.
That is not a resampling-kernel defect and it is not an alignment defect. It reads
like low-contrast micro-texture being lost under the veil BUILD-RENDER is chasing,
plus the CA in §5.3, plus the optics floor. On `bee-2-cpl` the hairs are reasonably
sharp and are wrapped in a bright veil — again not a sharpness failure.

If the three lanes land — halo gone, veil gone, gather order moved — the remaining
softness will be the optics, and the only lever left is the capture.

---

## 7. Reproducing this

Everything ran from a **pinned build**: `git archive` of an explicit SHA into
`C:\dev\strehl-out\BUILD-SHARP\pin-70934bb\`, outside the working tree, commissioned
with a **planted sabotage** — `env!("STREHL_PIN_TAG")` in `main.rs`, verified RED
(exit 101, "environment variable `STREHL_PIN_TAG` not defined") then GREEN (the
binary prints `BUILD-SHARP-PIN <path>` on every run). Without that, the pin is a
directory you hope is right; with it, the compile cannot succeed unless it names the
pin's own path. Three renders of one unchanged command produced three *different*
files in this tree before pinning.

```
# residual instrument (in the pin)
cargo run --release --example bs_residual -- --stack bee-2-cpl --span 1 --lambda 1
cargo run --release --example bs_residual -- --stack bee-2-cpl --span 1 --control none

# render an arms matrix, back to back from one binary
C:\dev\strehl-out\BUILD-SHARP\run-render.ps1 -Smooth default

# score them
python experiments/BUILD-SHARP/src/esf.py --ref b-g0-cr --arms b-g4-cr b-g0-l3 b-g0-nn

# the closed-form kernel MTFs
python experiments/BUILD-SHARP/src/restore.py --mtf-table
python experiments/BUILD-SHARP/src/restore.py --selftest

# the pictures
python experiments/BUILD-SHARP/src/pictures.py
```

### Deliverable pictures

Under `C:\dev\strehl-out\BUILD-SHARP\pictures\`. Clean — no debug annotations, no
ROI rectangles. **One shared display gain, derived from the BEFORE arm only** (M20
C3: an information-free gain moved a gradient metric 8.25x, so the arms must never
be independently stretched).

| file | what |
|---|---|
| `bee-2-cpl\align-full-{BEFORE,AFTER}.png` | 1800 px full frame, alignment fix |
| `bee-2-cpl\align-crop-roi{0,1,2}-{BEFORE,AFTER,PAIR}.png` | 600 px at 100% |
| `bee-2-cpl\restore-full-{BEFORE,AFTER}.png` | 1800 px full frame, restoration |
| `bee-2-cpl\restore-crop-roi{0,1,2}-{BEFORE,AFTER,PAIR}.png` | 600 px at 100% |
| `flower-inner-edge-cpl\align-full-{BEFORE,AFTER}.png` | 1800 px full frame |
| `flower-inner-edge-cpl\align-crop-roi{0,1,2}-{BEFORE,AFTER,PAIR}.png` | 600 px at 100% |

`-PAIR` images are the two arms side by side at 100% so the comparison needs no
blinking between files.

**Both A/B pairs are visually indistinguishable at 100%, and both were predicted to
be by their own measurements.** That agreement — instrument says null, eye says null
— is the reason to trust the instrument when it says something is *not* null.

---

## 8. Do-no-harm guard — `couch-fibers-cpl` (owner-mandated)

The owner audited the full frames and found `couch-fibers-cpl` **good**: pure dense
texture, no depth silhouettes anywhere, sharp down to individual filaments. It is now
a required regression guard, judged **by looking**, and a change that degrades it is
rejected regardless of what it does elsewhere. `109MSDCF` and `bee-1-cpl` ride along.

**Verdict: PASS. No degradation on any of the three, at full frame or at 100%.**

`restore.rs` is on no product path, so it cannot appear in either arm — this run
tests **the alignment default only**. Both arms of all three subjects were rendered
back to back from the one pinned binary (`pin-70934bb`, still printing its own path
on every run), differing only in `STREHL_SMOOTH`: `0` = the free solve = HEAD before
`70934bb`; unset = shipped, `lambda = 1`.

**Discrimination check first.** All three BEFORE/AFTER pairs have distinct MD5s. A
guard that compares a file to itself passes trivially and proves nothing.

Because three frozen ROIs can miss a localised defect in a 7040x4688 frame,
`experiments/BUILD-SHARP/src/worst_tile.py` ranks 256 px tiles by inter-arm
disagreement and crops the **worst** ones at 100%. The statistic only chooses *where
to look* — it does not deliver the verdict.

| subject | max abs delta | pixels > 1% FS | at the frame's **worst** tile |
|---|---|---|---|
| `couch-fibers-cpl` | 16.4% FS | **0.234%** | indistinguishable |
| `109MSDCF` | 5.3% FS | **0.004%** | indistinguishable |
| `bee-1-cpl` | 49.3% FS | **13.376%** | changed — see below |

**`couch-fibers-cpl`, the guard proper:** full frame identical; the three frozen
detail ROIs identical; and at the single worst-disagreeing tile in the whole frame,
identical. Filament definition preserved, no added noise, no ringing. **PASS.**

**`109MSDCF`** happens to be the best free ringing control in the set — a hard
high-contrast edge with genuinely flat approaches on both sides (flat cyan / white
ridge / flat red). Neither flat field gains an overshoot band or a dark rim.
Unchanged.

**`bee-1-cpl` is the one that moved, and it is honest to say why.** Its worst tile is
the tarsus, and it carries **the bright cut-out halo the owner described — in both
arms, at the same severity.** What my change moves is *where the election patchwork
polygons fall around it*, not the artefact's presence or amplitude. So that 13.4% is
BUILD-HALO's defect being perturbed, not BUILD-SHARP degrading detail. Two things
follow: the guard still passes (AFTER is not worse), and **`bee-1-cpl` is a poor
guard for anyone until the halo lands** — its inter-arm delta is dominated by an
artefact rather than by the change under test.

One cautious observation, offered as an observation and **not** as a claim: at
`bee-1-cpl`'s second-worst tile — thin hairs crossing pale cuticle — several hairs in
the BEFORE arm show small stepped lateral jogs where they cross an election boundary,
and in AFTER they run continuously. That is exactly the local geometric incoherence
M103 measured and the prior was built to remove, now visible. I am not upgrading the
§3.5 null on the strength of it: the ESF instrument measures edge rise on straight
slanted edges and is structurally insensitive to lateral jogs in thin filaments, so
the two do not actually disagree — they measure different things. It would need its
own instrument and its own control before it counted.

```
C:\dev\strehl-out\BUILD-SHARP\guard.ps1
python experiments/BUILD-SHARP/src/worst_tile.py --subject couch-fibers-cpl --top 2
```

Pictures: `<subject>\guard-full-{BEFORE,AFTER}.png`,
`<subject>\guard-crop-roi{0,1,2}-PAIR.png`, `<subject>\guard-worst{0,1}-PAIR.png`.

---

## 9. Architecture decision — compliance, and one API request

ORCH ruled `through_focus.rs` a single shared seam owned by BUILD-HALO, consumed
read-only by me. **Complied with, and there is nothing to unwind:**
`git log -- crates/strehl-core/src/through_focus.rs` shows no BUILD-SHARP commit and
the file is clean in the working tree. `restore.rs` duplicates none of its
statistics — it is a pure transfer-function module over resampling kernels and does
not touch the focus axis at all.

### 9.1 Two of ORCH's premises are already true, which de-risks the decision

**The two-pass decision is not a change — it is a ratification, and the count is
three.** The shipped pipeline already runs *pass zero* (depth guide for the
edge-aware election), *pass one* (regularised winner field) and *pass two* (gated
average). Measured on `couch-fibers-cpl`, 299 frames:

| pass | decode, summed across workers | per frame |
|---|---|---|
| zero | 23.7 s | — |
| one | 20.9 s | 69.9 ms |
| two | 20.1 s | 67.1 ms |

So "a second pass is cheap" is not a projection here, it is a measurement that has
already been paid three times. Nobody has to be talked into it.

**And `ThroughFocus` is closer to what both lanes need than the brief implies.** It
already carries `triple` (the fine response at `k*-1, k*, k*+1`), `floor`, `top_val`,
`top_idx`, `far_val`/`far_idx`, and the posterior sums `z`/`w`. I needed to add
nothing to it to state my request below.

### 9.2 The one thing I want, and it costs no storage and no fold time

The Wiener estimator self-calibrates the per-frame OTF from **the width of the
through-focus response curve** — the brief's own instruction not to make a lens model
load-bearing. That width is already computed inside `through_focus.rs` and then
thrown away.

`subframe_deficit` fits a log-domain quadratic through the baseline-subtracted triple
and forms `a = 0.5 * (ln l + ln r) - ln c`. It uses `a` only to bound the height
deficit and discards it. **That `a` is the curve width**: for a locally Gaussian
through-focus response, `f(k) ~ f_peak * exp(a * (k - k*)^2)` with `a < 0`, so the
width in frames is `sigma_k = 1 / sqrt(-2a)`.

Nothing else in the file exposes it. `bimodality_sigma` is a peak *height* above the
floor, not a width. So the exact request, for ORCH to route to BUILD-HALO:

```rust
// In `impl ThroughFocus`, alongside `subframe_deficit`.

/// Curvature of the log-domain through-focus fit, in reciprocal frames squared.
///
/// Strictly negative where it exists. The local through-focus response is
/// `f(k) ~ f_peak * exp(a * (k - k*)^2)`, so `1 / sqrt(-2a)` is the curve's
/// Gaussian width in frames — the local PSF scale as sampled by the focus
/// operator, which is what a self-calibrated OTF needs.
///
/// `None` under exactly the conditions `subframe_deficit` returns `None`:
/// incomplete triple, non-positive baseline-subtracted sample, or a fit that
/// is not concave.
pub fn log_curvature(&self, i: usize) -> Option<f32>;
```

**Please implement it by extracting the shared fit rather than by copying it**, so
the two cannot drift:

```rust
/// The concave log-domain quadratic through the baseline-subtracted triple,
/// as `(a, b)` in `q(x) = a x^2 + b x + ln c`. The single fit behind both
/// `subframe_deficit` and `log_curvature`.
fn log_fit(&self, i: usize) -> Option<(f32, f32)>;
```

`subframe_deficit` then becomes `self.log_fit(i).map(|(a, b)| 1.0 - (b * b / (4.0 *
a)).exp())` and is unchanged in behaviour — which a byte-freeze row will confirm.

**Cost: zero.** Pure function of `triple` and `floor`, both already stored. No new
per-pixel bytes, no change to `fold` or `absorb`, no effect on
`bytes_per_pixel()`. It cannot perturb bimodality.

### 9.3 Priority: LOW. Please do not let this preempt bimodality

I have to be straight about this rather than bank the API on momentum. **The Wiener
estimator is a measured negative at this capture's SNR** (§4): its gain cap never
binds, it cannot undo even our own resampling kernel whose transfer function we know
exactly, and it scores +0.27 um pooled on a 35.69 um rise. It does not ship.

So `log_curvature` is **not load-bearing for anything that currently ships.** It is
what the estimator would need *if* the SNR moved — which §5.5 says it can, by a
factor of 9.6x in contrast, from a capture change. Schedule it at the bottom of
BUILD-HALO's queue. If it is not there by morning, nothing of mine is blocked.

If ORCH would rather I not have it at all until the Wiener earns its place, that is a
reasonable call and I will not argue it.

### 9.4 The decision ORCH should make NOW, while the merge is being rewritten once

ORCH's own reason for deciding two-pass now — *"deciding this late means rewriting
the merge once"* — applies with more force to **gather order** (§5.1), and that one
has a much larger payoff:

> Gathering on the CFA quad plane puts a feature at 0.25 cycles/**output**-px at 0.5
> cycles/plane-px, where the kernel MTF is **0.6251**. Demosaicing each frame before
> the gather puts it at **0.9402** — **1.50x more contrast at the top of the real
> detail band**, optically free.

That is larger than every merge-side sharpness change in the corpus. **If the merge
is rewritten for two-pass and the gather order is not moved at the same time, it gets
rewritten twice.** This is the moment.

I said "for free" in §5.1 about the *optics*. The *compute* is not free and I have
now measured it rather than estimating it:

| | measured |
|---|---|
| Malvar-He-Cutler demosaic, 7032x4688 | **549 ms/frame** best, 724 ms mean |
| 299 frames, summed across workers | **216 s** |
| for scale: one decode pass | 20 s summed, 67 ms/frame |

So a per-frame demosaic costs about **8x a decode**, and the gather itself becomes
**3x** its current work (three full-resolution planes instead of one quad plane).
Against a ~170 s render wall, expect roughly +20 s wall from the demosaic plus the
gather multiplier. That is the honest price of the 1.50x.

Two notes for whoever costs this: `demosaic_bilinear_row` already exists and is much
cheaper — whether a bilinear gather-time demosaic keeps the MTF win is **untested and
I am not claiming it does**, but it is the obvious first thing to benchmark if cost
is the blocker. And `strehl_core::restore::gather_mtf` now makes the whole claim
measurable rather than argued, which is what turned M95 P56 from ARGUED into a
number.

Bench: `pin-70934bb/crates/strehl-cli/examples/bs_demosaic_cost.rs` (pin tree only —
it touches nothing shared).

## 10. Routed defect — the "outline ghosts" on `bee-1-cpl`

ORCH routed a visible symptom found by BUILD-RENDER: *"pale outline ghosts left
of the left legs — a leg edge appearing more than once"*, with the hypothesis
that the per-frame scale term is **measured but not applied** at render time,
which would produce doubling that grows with image radius.

**Verdict: the hypothesis is false, and the ghost is not registration. Alignment
at those legs is sub-pixel. The cause is in the merge, not the geometry.**

ORCH asked to be told quickly if that turned out to be the case. It is the case.

### 10.1 "Measured but not applied" is false — checked in code

`align_pair` (`align.rs:1448`) fits a full `SimilarityParams` including the
scale term `g`, with the explicit comment *"Scale and rotation are dimensionless
and carry unchanged."* `warpmap.rs` stores a full `Similarity` and `gather_into`
applies it. Scale is fitted **and** applied. There is no measured-but-dropped
term, and my span-1 residual instrument was therefore never blind to one.

### 10.2 The scale ladder is monotone to 1e-5 — `ladder.py`

Focus breathing is a lens property: over a bracket the focus group moves in one
direction, so magnification must change **monotonically**. That gives a free,
model-independent error estimator with no image processing in it at all. Read
the per-frame ladder `g_k` straight out of the warpmap sidecar and split it into
an isotonic (exact L2 monotone, PAVA) trend plus a residual. The trend is
physics; every bit of the residual is fit error that is applied to pixels.
A residual `w` displaces a feature at radius `r` by exactly `w * r` px.

`bee-1-cpl`, 299 frames, total breathing **8.015%** magnification:

| solve | wobble RMS | spurious shift @ r=2100 | span-16 applied | span-16 error |
|---|---|---|---|---|
| free (`STREHL_SMOOTH=0`) | 2.44e-5 | 0.051 px | 7.985 px | 0.027 px |
| shipped (λ=1) | 9.75e-6 | **0.020 px** | 7.978 px | **0.007 px** |

Monotonicity violations fall from 25/298 to 7/298 under the λ=1 prior — an
independent confirmation, on a different gauge, that the §3 fix was real.

The ~8 px of magnification correction applied across a 16-frame span at the
frame corner is **genuine breathing, correctly applied**. The spurious component
is 0.007 px. Scale is exonerated.

### 10.3 Span-1 pixel residual — alignment removes most of the radial term

`ghost.py` gathers adjacent frames both aligned and unaligned, and projects the
per-tile residual onto the **signed radial** direction, because direction
discriminates breathing (radial, grows with r) from jitter (isotropic) where
magnitude alone cannot.

One confound had to be removed first. The aligned arm gathers through a
placement that displaces content by tens of pixels at large radius, so a corner
tile can be partly filled from *outside* the source plane. Border fill
correlates with itself and is read as a residual the identity-gathered arm never
sees. Excluding a 200 px margin **changed the verdict**, from "alignment is 15×
worse at the corner" to the table below. The unexcluded reading was an artefact
of my instrument, not a property of the aligner.

Radial slope, px per 1000 px of radius, margin 200:

| pair | unaligned | aligned | radial term removed |
|---|---|---|---|
| 60 | +1.775 | +0.399 | 78% |
| 120 | +1.532 | +0.054 | 96% |
| 180 | +0.808 | −0.221 | 73% |
| 240 | +0.989 | −0.393 | 60% |

Residual after alignment is **0.33–0.42 px mean**, and its **tangential
component exceeds its radial component** (0.16–0.20 vs 0.01–0.10) — the
isotropic-jitter signature, not the breathing signature. The plant control has
the opposite ratio (7:1 radial-dominant), which is what a true scale error looks
like.

*Not claimed:* the aligned slope's sign flips across the stack (+0.40, +0.05,
−0.22, −0.39). At n≈81–105 tiles I have not put an error bar on that, so I do
not report progressive over-correction as a finding.

### 10.4 A third failed instrument — `ghost.py` is invalid at span 16

The merge elects across the whole stack, not just adjacent frames, so I repeated
the measurement at span 16. It returned an alarming result: paired on identical
tiles, aligned was **1.07–2.72× worse** than unaligned, with the radial slope
flipping to large negative. Read naively that says the aligner over-corrects
scale by 3–4× and is the ghost's cause.

It is not. It is my instrument failing, and the positive control caught it.

I applied the aligner's **own recorded correction** to the unaligned pair
analytically — same structure as the treatment (pure magnification about the
scale centre), known-correct magnitude. If the instrument measures registration,
the correct correction must reduce the residual.

| span-16 pair 240, margin 200 | mean shift |
|---|---|
| uncorrected | 1.328 px |
| + true correction (+dg) | 4.534 px |
| + true correction (−dg) | 4.337 px |

**Both signs make it worse, by nearly the same amount.** A pure magnification
cannot worsen registration in both directions; that is arithmetically
impossible. The instrument is not measuring registration at this span.

Two further tells, both visible in the same run and both missed on first read:
the reported `slope` (+9.1 px/kpx) is inconsistent with the reported
`mean_radial` (+0.84 px) from the same tiles; and the unaligned far bin reads
|shift| = 0.053 px at r=1400–1800 while the near bin reads 3.53 px — backwards
for breathing, which must grow with radius.

The mechanism is defocus-induced correlation bias. At span 16 the two frames
differ in **content**, not just placement, because they differ in focus. Plain
correlation cannot separate a change in what is sharp from a shift, and the
tile-admission gate then selects on that same changed content. At span 1 the
content is nearly identical, which is why the instrument commissions cleanly
there (self = 0.0000 exactly; plant ×1.0005 recovers slope 4.63–5.04 against an
expected 5.00) and why only the span-1 numbers are reported above.

Recorded as the third failed instrument in this workstream, alongside the band
census and the paired Laplacian regression of §2. Measuring inter-frame
registration at large focus separation remains **unsolved** here; it needs a
focus-invariant feature, not correlation.

### 10.5 What the legs actually show — the pictures

`pictures/bee-1-cpl/ghost-legs-{A,B}.png`, 100% crops, no annotations. Two
distinct artefacts, and neither is an edge appearing twice from misregistration:

1. **Flat grey polygonal patches** pasted over the leg, with hard straight
   boundaries and no internal texture — election patchwork. The boundaries are
   tile-shaped, not anatomy-shaped.
2. **Pale halo outlines** standing off in the empty background, displaced
   roughly **50–150 px** from the hairs that cast them.

Set that against the measured span-1 residual of **0.33–0.42 px**: the offending
displacement is **two orders of magnitude** larger than any residual I can
measure. Registration cannot produce it. A 0.42 px shift cannot separate an edge
from itself far enough to read as a second edge — that needs several pixels at
minimum, and these are at 50–150 px, which is **defocus-blur scale** at 2:1
magnification.

### 10.6 Routing

- **The ghost is BUILD-HALO's.** It is election patchwork plus defocus-scale
  halo, at defocus scale, on a subject with depth silhouettes — consistent with
  the owner's own audit that every silhouette subject is ruined while the pure
  texture subject `couch-fibers-cpl` is good.
- `experiments/M120-patchwork.md` exists in the corpus and is unread by me; it
  should be routed to BUILD-HALO, as the name matches the first artefact exactly.
- **Still owed from §9:** the demosaic-before-gather decision (1.50× contrast,
  549 ms/frame) should be taken in the *same* merge rewrite as ORCH's two-pass
  decision, or the merge gets rewritten twice.
## 11. RETRACTION — my "polygonal election patchwork" reading was wrong

In section 10.5 I described the `bee-1-cpl` leg artefacts as "flat, textureless
grey polygonal patches with hard straight boundaries -- election patchwork.
The boundaries are tile-shaped, not anatomy-shaped." **That is retracted.** I
observed it on crops of 900x700 and 700x600.

ORCH pointed me at corpus fact 1372, which records the identical mistake being
made and overturned once already: a 520 px crop read as flat-shaded grey with
hard piecewise-linear boundaries, and enlarging the same region to 1100x900
"refuted it outright: **there is no polygon.** Every boundary is curved and
organic and follows the subject silhouette."

Re-cropped at 1400x1100 (`pictures/bee-1-cpl/legs-1400.png`), fact 1372 is right
and I was wrong. Every boundary is curved and follows the hair silhouettes.
There are no tiles. **This is now the fourth occasion in this project where a
smaller view produced a confident wrong answer that a larger view overturned**
(facts 1359, 1362, 1372, and this). The discipline is not "look at the picture";
it is "look at a large enough picture", and 900 px is not large enough.

What is actually there, on `bee-1-cpl` and `bee-3-cpl` alike, is **flat pale
ghost copies of the subject's own features** -- hair-shaped and segment-shaped
lozenges -- pasted into the defocused background, displaced from their parents
and with soft curved boundaries. This is one artefact with three names in this
project: BUILD-RENDER's "outline ghosts", the corpus's "patchwork", and my own
retracted "polygons".

**And the flat background is not crazy paving.** Choosing the flattest 1100 px
window of `bee-3-cpl` by a rule that consults only the reference arm
(`flat.py`), the background at 100% is a **smooth gradient** with a handful of
soft blob ghosts in it. There are no visible brightness steps between flat
regions. Corpus fact 1682's `Q` bound proves the merge manufactures structure
and I do not dispute it -- but the structure's visual character is **localised
ghost copies, not crazy paving**, and the corpus's description should be
corrected.

## 12. `--photometric` does not fix it — hypothesis dead, cheaply

ORCH's proposal: the gate averages 166.8 of 299 frames per pixel (fact 1685) and
per-frame photometric drift is 0.91% peak-to-peak, so neighbouring regions
averaging different subsets land on different means and step visibly. The cure
(`photometric.rs`) is written and defaults to `Off`, and had only ever been
judged on statistics.

Six renders, `bee-1-cpl` and `bee-3-cpl` x {off, on, auto}, back to back from one
commissioned pin at `b001f22`, all `--linear-srgb` with the viewing curve applied
afterwards **identically** across arms -- because photometric correction changes
brightness and a per-arm `--auto-exposure` would have normalised away the very
difference under test.

| | mean level shift | spatial residual | flat-crop SD | flat-crop lapRMS |
|---|---|---|---|---|
| `bee-1-cpl` off→on | +0.016% | 2.59% | 0.063868 → 0.063670 | 4.421e-3 → **4.681e-3** |
| `bee-3-cpl` off→on | +0.737% | 3.47% | 0.009382 → **0.010686** | 1.801e-3 → 1.766e-3 |

`auto` is **byte-identical to `off`** on `bee-1-cpl` (MD5 `398C5BCA…`), so Auto
decides OFF there and there are really two arms, not three.

**Verdict: dead.** The correction is not inert -- it restructures the image by
2.6-3.5% of mean level, far more than the 0.016-0.74% global shift -- but it does
not touch the ghosts, which are visually unchanged. And on `bee-3-cpl` the flat
background's SD gets **14% WORSE**, independently reproducing corpus fact 1678's
"6.4% worse on the low-drift stack" on a different metric. M122's KEEP-OFF
verdict survives contact with a photograph.

The mechanism fails because the artefact is not a brightness step between
subsets. It is a **geometric** mis-selection: the merge is electing, for a
background pixel, a frame in which a defocused foreground feature covered that
pixel. No photometric correction can fix a wrong-content choice.

## 13. Deconvolution, round 2 — the target is real, the noise calibration is not

ORCH is right that section 4's negative was too narrow. That arm set `H` to the
**resampling kernel** MTF, which is nearly perfect, so there was nothing to
invert. The optics are a different matter: aperture-independent aberration is
**60.1% of the blur variance**, and at the merged image's measured 35.69 um rise
(sigma = 2.72 px on the 5.12 um full-res grid) the modelled MTF is **0.232 at
f=0.10 and 0.037 at f=0.15 c/px**. There is real contrast to buy back.

**Attempt 1 — scalar noise SD. Catastrophic, and I looked.** Laplacian-MAD gives
sigma = 8.45e-5 on `bee-1-cpl`, the Wiener denominator barely throttles, and the
filter runs to **29.4x peak gain, 23.6x at f=0.15**. The result
(`pictures/deconv/legs-ringing.png`) is destroyed -- covered in ring and worm
artefacts. **A high-pass energy metric would have scored this as a large
sharpness win.** It is the exact failure corpus fact 1359 warns about, and the
only reason it did not become a reported success is that the standing rule made
me open the file.

**Why it ran away.** The Laplacian-MAD estimator assumes **white** noise. The
noise in a merged frame is strongly **correlated** -- it is an average of ~167
frames resampled through a Catmull-Rom kernel, both of which suppress high
frequency. Measured, by fitting the image's own power spectrum above f=0.28
where the optics guarantee no signal survives, the noise spectral exponent is
**-3.53** on `bee-1-cpl` and **-1.52** on `couch-fibers-cpl`. White noise would
be **0.00**. So a scalar sigma taken from a high-pass operator under-reports the
noise at exactly the mid frequencies the filter amplifies.

**Attempt 2 — measured noise power spectrum. Over-corrects.** Replacing the
scalar with the fitted spectrum removes the runaway but replaces it with the
opposite failure: peak gain falls to **0.70x on `bee-1-cpl`** -- the filter now
attenuates. Extrapolating a slope of -3.53 from f=0.28 down to f=0.05 inflates
the low-frequency noise estimate by roughly 470x, and the power-law fit is not
valid that far outside the band it was fitted in.

**So the two calibrations bracket the answer uselessly: 29.4x and 0.70x.** I am
not going to pick a number between them and call it calibrated.

**What the picture does support.** Throttled empirically to **2.29x** peak gain,
`bee-1-cpl` shows genuinely crisper hairs with the worms gone
(`pictures/deconv/legs-2x.png`) -- but new **dark rims appear at the
high-contrast leg silhouettes**, and the veil boundaries are **hardened**.
Deconvolution sharpens the artefact as readily as the detail, which is an
argument for fixing the ghosts before restoring anything.

**Do-no-harm guard: PASS.** On `couch-fibers-cpl` the noise-spectrum calibration
yields 2.68x gain and the fibres at 100% are crisp with **no ringing and no
worms** (`pictures/deconv/guard-couch-{base,ns}.png`). Notably the guard also
passes at the attempt-1 settings, but for an instructive reason: that subject's
measured noise is **7.3x higher**, so the same filter collapses to gain 1.0001 --
the identity. The safety property ORCH predicted does hold; it is the
*calibration*, not the *guard*, that is unresolved.

**The correct next instrument, costed.** Stop inferring the noise spectrum from
the signal. Measure it: render two merges from **disjoint halves** of the frame
set and difference them. The difference contains only noise, at every frequency,
with no extrapolation and no dead-band assumption. Two extra renders per subject
at ~290 s each. This is the experiment that would settle it, and it is the one I
would run next.

## 14. The optics floor, as capture advice for the owner

Passing these up as requested; they are measurements, not opinions.

- On a **printed ruler** (target RU1) the system's 10-90 edge rise is **30.44 um**
  against a **14.11 um** diffraction limit at f/5.6 -- the rig is **2.16x**
  worse than diffraction-limited. This independently matches M88's 2.25x.
- **Stopping down does not help.** The measured f/11 : f/5.6 edge-width ratio is
  **1.025x**, where diffraction alone predicts **1.964x**. A system whose blur
  is unchanged by aperture is aberration-limited, not diffraction-limited.
- Apportioned by variance, **76.6%** of the total blur is optics, of which
  **60.1% is the aperture-independent part** and only 16.5% is diffraction.

The practical readings: closing the aperture further is spending light and
diffraction for nothing, so the sharpest aperture on this rig is the widest one
that still gives the depth step needed. And since the aberration term is
**2.16x diffraction and does not respond to aperture**, the 2x teleconverter is
the first thing to test by removal -- a bare-lens bracket of target RU1 at the
same magnification would separate the converter's contribution from the prime's
in a single afternoon. I would want that measurement before advising a purchase.

---

## 15. Correction to the owner's brief (`captures-needed.md` §29)

ORCH asked two provenance questions before this goes to the photographer. Both
answers weaken the brief, and one of them **inverts a piece of the advice**. This
section is the correction.

### 15.1 -- "one bracket or several?" **One. n = 1.**

The 30.44 um system-optics figure is **a single ROI (`RU1`) in a single stack
(`ruler`)**. `esf-tw-ru-vs-shipped.json` carries four `RU1` rows, but they are four
*kernel arms* of the same ESF fit and `rise_ref_um` is identical across all four to
16 significant figures (`30.441454828260458`). There is no replicate, no second ROI
on the ruler, and no second bracket. **No sample standard deviation can be formed
from it**, because there is no sample -- only an instrument floor (0.3859 um for
this ROI).

So my §14 phrase "one measurement, one printed target" was exact, and it should be
carried into the brief in those words rather than softened.

### 15.2 -- Uncertainty on 1.025x: random error is fine, the **systematic is disqualifying**

Propagating the ESF floor as random error:

| floor used | ratio | vs 1.000 (no aperture effect) | vs 1.964 (diffraction-limited) |
|---|---|---|---|
| 0.386 um (RU1's own) | 1.025 +/- 0.017 | 1.43 sigma -- **indistinguishable** | 53.9 sigma |
| 0.670 um (paired-ESF scale) | 1.025 +/- 0.030 | 0.83 sigma -- **indistinguishable** | 31.0 sigma |

Read that carefully, because the two columns say different things:

- **"This rig is not diffraction-limited" is overwhelming** (31-54 sigma). That
  survives.
- **"Stopping down does not help" is not a measurement at all.** 1.025 sits within
  1.4 sigma of 1.000 on random error -- but random error is not the limiting term.

**The systematic confound is disqualifying, and the corpus already recorded it.**
Fact 1183:

> **NO APERTURE BRACKET ON A FIXED SUBJECT EXISTS ANYWHERE IN THE CORPUS -- ALL 23
> STACKS WERE SURVEYED.** [...] the two stacks share ROI coordinates but differ by
> **2.15 degrees in edge angle**, **1.91x in contrast**, and were shot **8 days
> apart** -- so the `c` term does not cancel and the two-aperture ratio result
> (1.025 against 1.9643 predicted) **FAILs weakly rather than cleanly**.

My own paired instrument is trustworthy precisely because contrast cancels within a
pair. M88's two-aperture comparison is **unpaired** -- different stacks -- so it
does not. A 1.91x contrast difference on a contrast-sensitive rise estimate is a
first-order confound, not a rounding error.

**And I quoted it as if it were clean.** My §1 and §14 say "M88 measured the
f/11 : f/5.6 edge-width ratio at 1.025x" without the audit attached. That is my
error, upstream of ORCH's brief.

### 15.3 -- The correction that matters: **"non-diffraction" was measured, "aperture-independent" was inferred**

These are not synonyms, and they point opposite ways.

- **Measured:** the system's blur is ~2.2x larger than diffraction alone predicts.
  Two independent measurements agree -- M88's 31.70 um (2.25x) and my RU1's
  30.44 um (2.16x), different data, 4% apart. **This is solid.**
- **Inferred:** that the excess is *aperture-independent*. That rests entirely on
  the confounded 1.025x ratio and on nothing else.

The consequence is the part I want changed. **Most aberrations get better when you
stop down** -- spherical, coma, astigmatism and field curvature all fall with
aperture. So a large non-diffraction blur term, taken on its own, is an argument
for stopping down **more**, not less, until diffraction overtakes it. Only the
confounded ratio says otherwise.

> **Therefore "open up, you are spending two stops for nothing" may be exactly
> backwards, and it is the one item in the brief that would change how he shoots.**
> I recommend withdrawing it, or reducing it to: *we cannot yet tell whether
> stopping down helps you, and here is the one capture that would settle it.*

### 15.4 -- A caveat neither of us has stated: the target's own edge

`RU1` is a **printed** ruler. At the binned pitch of 10.24 um the measured rise is
~3 px, and the ink-spread/dot structure of a printed edge is itself tens of um.
**I have not subtracted the target's own unsharpness, and I cannot, without a
proper edge.** So:

> **76.6% is an upper bound on the optical share, not a point estimate.** Some
> unknown part of the 30.44 um belongs to the piece of paper.

Fact 1183 independently asks for "a hard edge (razor blade or chrome-on-glass)" --
the corpus already knows the current target is not good enough for this.

A second, smaller dependency: the **16.5% / 60.1% split within the optics** rests
on M88's computed 14.11 um diffraction figure and its effective-f-number assumption
at magnification. I have not re-derived it. The *total* 76.6% does not depend on
it; the split does.

### 15.5 -- What I will stand behind, in the owner's language

| claim | status |
|---|---|
| The rig is ~2.2x softer than diffraction alone would make it | **Supported**, two independent measurements |
| Most of the softness is optical, not software | **Supported as an upper bound** (76.6%), target unsharpness not subtracted |
| Software cannot fix it by *selection*; only reconstruction can | **Supported** -- follows from the above |
| f/11 is no sharper than f/5.6 | **NOT supported.** Confounded, unpaired, corpus-flagged weak FAIL |
| Therefore shoot nearer wide open | **Withdraw.** May be backwards |
| Shoot one bracket without the 2x teleconverter | **Stands** -- and is still the single most valuable capture |

**Add one capture request:** an aperture bracket on a *fixed* subject -- same
scene, same light, same session, f/5.6 / f/8 / f/11, ideally on a razor edge at
3-7 degrees. Fact 1183 predicts rises of 13.65 / 11.97 / 10.37 um if diffraction
governs. That single afternoon settles the "open up" question, retires a
corpus-level gap flagged across all 23 stacks, and it costs him nothing but time.

---

## 16. The disjoint-halves noise measurement (assignment 1)

**Verdict: a real measurement, an honest negative on the goal.** It refutes the
calibration that failed in §13 and explains exactly why it failed, but it does NOT
deliver a usable Wiener calibration, and I am not going to pretend otherwise.

### 16.1 -- Mechanism, and why no code change was needed

`stack` takes a DIRECTORY, and `--limit` is a prefix. Disjoint selection therefore
needs no CLI change at all: two directories of NTFS **hardlinks** (no admin, no disk
cost) holding the even and the odd frames. Even/odd, never first-half/second-half --
both arms must span the same focus range or the halves differ in content by
construction and nothing cancels.

Four renders from the commissioned pin `b001f22`, back to back, `--gate 4.0
--linear-srgb --demosaic`: `bee-1-cpl` A(150)/B(149), `couch-fibers-cpl`
A(150)/B(149), plus `Q0`(75)/`Q2`(75) on bee-1 for the scaling control. The full
merges already on disk from the §12 run share that pin and those settings exactly.

The instrument (`halfspec.py`) was commissioned on synthetic data first, 5/5:
signal rejection to 0.2%, level linearity 3.98 against 4.0, flatness 1.10,
**correlation detection** (slope -2.61 blurred against -0.004 white -- the
capability the whole exercise depends on), and a planted 3,-2 px offset recovered
exactly.

### 16.2 -- The whole-frame difference is a photograph of the bee

`pictures/halves/bee1-diff-full.png`. Every hair, both legs, the wing, and the
eye's ommatidia lattice beating as **moire** against a sub-pixel registration
difference between the arms. An integer offset of `dx=1` was measured and removed;
what remains is sub-pixel and is not removable without resampling, which would blur
the very quantity under measurement.

Two mechanisms put signal there and both are structural, not bugs:

1. **The halves elect different winner frames.** Adjacent focus steps genuinely
   differ in content wherever there is fine detail.
2. **The two half-merges are not mutually registered.** Each aligns within its own
   frame set.

So `P_D` is the noise spectrum **only where the scene is flat**.

### 16.3 -- A statistic failed, and the picture caught it

`structure_score` (8x8 box-mean variance over total variance) returned **0.2594**.
Calibrated against pure noise of known slope it should have read **0.7396** at the
measured slope -- so the statistic said the field was *less* structured than pure
noise, i.e. clean. **The picture is a legible bee.** Box-averaging destroys exactly
the fine hair detail that dominates, so the statistic is blind to the contamination
it was built to detect.

> **Failed instrument #4.** Recorded, not quietly discarded. It is also the
> cleanest possible restatement of the house rule: the number said clean, the
> picture said bee, and the picture was right.

### 16.4 -- The "dead band" is not dead. This is the finding.

§13 fitted a power law to the image spectrum above `f=0.28` on the premise that the
optics guarantee no signal there, got slope **-3.53**, and extrapolated it down to
`f=0.05` -- inflating low-frequency noise ~470x and producing the 0.70x
attenuating calibration.

Measured directly in flat windows, the noise fraction above `f=0.28` is only
**0.46 to 0.56**, and after the contamination correction of 16.6 it is **0.22 to
0.27**.

> **The band that was assumed to be pure noise is roughly three-quarters SIGNAL,
> even in the flattest parts of the frame.** The -3.53 slope was fitted mostly to
> signal. That is why the two calibrations disagreed by 42x.

Directly measured, the noise spectrum is **not a power law at all**: slope about
**-2.85** at low frequency, flattening to about **-1.47** near Nyquist. It is white
noise shaped by the gather kernel and the demosaic, which is flat at low frequency
and rolls off -- exactly the shape a single power law cannot represent. Fitting one
in a narrow high band and extrapolating two octaves was wrong in its premise, its
slope and its direction.

### 16.5 -- couch-fibers-cpl: the method does not work there at all

Every one of its 8 flat-ranked windows is legible fibre
(`pictures/halves/couch-flatdiff.png`), per-window sd 453-979 DN with `max/median`
only 1.20 -- uniformly contaminated rather than a clean subset. A pure-texture
subject has no flat region anywhere, so **this route cannot measure its noise**.
Stated rather than papered over: the guard subject is exactly where I most want a
noise number and cannot get one this way.

### 16.6 -- The scaling control, which quantifies what is left

Quarter-set merges admit about half as many frames per pixel, so the noise term
doubles while any scale-independent floor does not:

    P_half = u + S ,  P_quarter = 2u + S ,  f = S/(u+S)   =>   r = 2 - f

| window | sd half | sd quarter | r | f = 2-r | by eye |
|---|---|---|---|---|---|
| 0 | 63 | 73 | 1.366 | 0.634 | clean |
| 1 | 78 | 93 | 1.440 | 0.560 | clean |
| 2 | 72 | 92 | 1.599 | 0.401 | clean |
| 3 | 65 | 79 | 1.498 | 0.502 | clean |
| 4 | 253 | 551 | 4.729 | **-2.729** | contaminated |
| 5 | 431 | 478 | 1.226 | 0.774 | contaminated |
| 6 | 265 | 850 | 10.275 | **-8.275** | contaminated |

**Clean windows: r = 1.476, f = 0.524.** So **52% of the difference power in the
windows that LOOK like clean noise still does not scale with frame count, and
therefore is not noise.** The contaminated windows return impossible negative `f`,
which is a useful internal check that the arithmetic detects contamination rather
than absorbing it.

Caveat that bounds this: the two comparisons needed different integer offsets
(`[0,1]` against `[2,-3]`), so the arms are not in identical geometry in both runs
and `S` is not guaranteed equal between them. `f = 2 - r` assumes it is. Indicative,
not exact.

### 16.7 -- Why this still does not calibrate the Wiener

The measurement is squeezed from both sides and lands on no point estimate:

- **Lower bound.** Flat windows are where the gate admits the MOST frames
  (`n_eff` is maximal), so their noise is the floor of the whole image. Where the
  detail is -- the only place deconvolution matters -- `n_eff -> 1` and the noise is
  far higher. The halves cannot reach there because signal dominates the difference.
- **Upper bound.** Even the clean windows are ~52% contaminated (16.6).

Combining flat-window noise with whole-frame signal power gives a noise fraction
below 1% even at Nyquist, which would license near-total inverse filtering -- the
runaway that visibly destroyed the picture in §13. **That combination is invalid**,
and I flag it here precisely because it is the number a less careful reading of this
data would have shipped.

### 16.8 -- The route that should work, using assets the project already has

Stop trying to measure merged noise empirically. Compute it:

    sigma^2(x) = sigma_frame^2( level(x) ) / n_eff(x)

shaped spectrally by the gather and demosaic transfer functions, which are known
analytically -- `gather_mtf` already exists in `restore.rs` from §4.

Every term exists today: the **calibrated per-frame sensor noise model**, the
per-pixel **`n_eff`** the estimator already computes, and the **kernel MTF**. That
is a per-pixel, spectrally-correct, fully calibrated noise model requiring no
extrapolation and no dead band, and it is correct precisely where the halves method
fails -- at high-detail pixels, because `n_eff` is smallest exactly there.

**The disjoint-halves measurement then becomes the validation instrument rather
than the calibration**: predict the flat-window noise from the model and check it
against the 63-78 DN measured here. That is the next step, and it needs `n_eff` on
the render path -- see the hook request in 16.9.

### 16.9 -- Hook needed for the merge integration pass

Adding to the list held for the single-writer `merge.rs` pass:

> **Expose per-pixel `n_eff` alongside the merged image**, as an optional
> side-channel the render path can emit. `Estimator::n_eff()` already returns
> `&[u16]` (`merge.rs:1279`) and `soft_n_eff_at` the fractional form -- nothing new
> needs computing, only surfacing. Without it the calibrated noise model cannot be
> evaluated per pixel, because `sigma^2 = sigma_frame^2 / n_eff` needs `n_eff`.

### 16.10 -- Assignment 2 preparation: what an upper envelope must cost

Before BUILD-HALO's fix is measured, the prediction is on record
(`ordstat.py`, 400,000 trials):

| estimator | bias | sd | vs shipped |
|---|---|---|---|
| shipped gated mean over 166.8 frames | +0.0000 sigma | 0.0774 sigma | -- |
| **upper envelope of 3** | **+0.845 sigma** | **0.748 sigma** | **9.7x noisier** |

A maximum is not an unbiased estimator of a mean. Both effects point the wrong way
here: the bias is **upward** and the defect being removed is a **darkening**, so an
undebiased envelope removes part of the veil *arithmetically* rather than
physically -- and would show an improvement on a stack with no veil at all.

At a plausible background `sigma_frame` of 200 DN that bias is **+169 DN**, which is
the same order as the whole **-177 DN** aura on `109MSDCF`. **The placebo is
therefore the discriminator**: 109MSDCF has no depth separation and so no veil, and
any background LEVEL SHIFT there is bias, not repair. I will measure the level, not
only the aura.

## 17 -- Assignment 2: the veil-or-light harness, commissioned before the fix exists

`experiments/BUILD-SHARP/src/veilorlight.py`, commissioned by
`veilorlight_commission.py`, **6/6**.

Written and commissioned before BUILD-HALO's fix exists, deliberately. An
instrument built after seeing the result it must judge is an instrument fitted to
that result.

### 17.1 -- The one quantity that cannot lie

The veiling defect is a **darkening** of the backdrop near the subject. The
candidate fix replaces a gated mean with an order statistic across frames, and
§16.10 predicts that an undebiased order statistic **brightens** the backdrop by
+0.845 sigma whether or not it removes any veil.

So an undebiased envelope satisfies the veiling number, satisfies the aura number,
and satisfies every ratio. ORCH put it exactly right: the failure mode here is a
green result on every metric. Only one quantity separates the two explanations:

> **the absolute backdrop level, in DN, on a subject that has no veil.**

Every number this harness prints is therefore in absolute DN, and **nothing is
normalised to its own arm's far field**. That convention -- which is the natural
one, and the one my own earlier profiles used -- cancels a uniform brightening
perfectly and is precisely how the bias would hide.

### 17.2 -- Three signatures, measured together

1. **Far-field level shift (DN)** -- the discriminator. A genuine repair does
   nothing far from the subject; a biased estimator adds light everywhere.
2. **Background noise sd ratio** -- the fingerprint of an order statistic *even if
   someone debiased the level*. Predicted 9.7x for an envelope of 3.
3. **Near-field recovery (DN)** -- the intended effect, reported last, because on
   its own it cannot distinguish the two.

Signature 2 also **closes the prediction with no free parameter**. If the shipped
arm is a mean over `n_admit` frames then `sigma_frame = sd_baseline *
sqrt(n_admit)`, so the bias an undebiased envelope *would* produce is computable
from the baseline arm alone and is printed next to the measured shift.

The subject mask is derived from the **baseline arm only**. Deriving it from the arm
under test would let the fix move the geometry the measurement is defined against.

### 17.3 -- Commissioning: six plants into the real verification subject

Source `flower-bud-alone-cpl` full-frame linear -- the actual subject the harness
will judge, not a stand-in -- with plants applied outside the subject mask.
`bee-3-cpl`, used first, has no bright neutral backdrop at all and the harness
**refuses** it; that refusal is correct behaviour, and it is why the commissioning
moved onto the real subject.

| # | plant | far shift | **pedestal** (want) | sd ratio mean/per-chan (want) | |
|---|---|---|---|---|---|
| 1 | null | +0.0 | **+0.0** (+0.0) | 1.00 / 1.00 (1.00/1.00) | PASS |
| 2 | pure bias +200 DN | +200.0 | **+200.0** (+200.0) | 1.00 / 1.00 | PASS |
| 3 | pure repair, exp decay tau=90 px | +0.8 | **+0.0** (+0.0) | 1.00 / 1.00 | PASS |
| 4 | **repair + 120 DN** | +120.8 | **+120.0** (+120.0) | 1.00 / 1.00 | PASS |
| 5a | 9.7x noise, chroma-correlated | -0.6 | -0.3 (+0.0) | **10.97 / 9.71** (10.96/9.70) | PASS |
| 5b | 9.7x noise, per-channel independent | -0.4 | -0.4 (+0.0) | **6.38 / 9.70** (6.38/9.70) | PASS |

**Cases 3 and 4 are the whole point.** They differ *only* by an additive 120 DN.
Every self-normalised profile, every ratio, and every "percent of veil recovered"
score rates them identically; the harness separates them exactly.

The **pedestal** -- the delta in the outermost band, d = 700-1200 px -- is what the
verdict turns on, not the mean far-field shift. A repair with a long tail still
moves the mean far field (case 3 gives +0.8 DN) but its pedestal is spent
(**+0.0 DN**), while an additive bias is flat all the way to the frame edge. Shape
separates a tail from a pedestal; magnitude alone does not.

### 17.4 -- What the commissioning caught in the harness itself

Case 5 failed on the first run: a planted 9.7x noise increase read **5.67x**.

That was not a plant error, it was an instrument property. The harness measured
noise on the **channel mean**, and averaging three channels attenuates noise that is
uncorrelated between them by `sqrt(3)` while leaving chroma-correlated noise alone.
Predicted `sqrt(1 + 9.648^2/3) = 5.660`; measured **5.662**. The monochrome control
gave 9.713 against 9.700 predicted. The arithmetic is exact, so the mechanism is not
in doubt.

Two consequences, both fixed:

- **The harness now reports both noise numbers**, channel-mean and per-channel. The
  true ratio is bracketed by the pair, so the real measurement needs no assumption
  about how the fix correlates noise between channels. Had only the channel mean
  been kept, a genuine 9.7x noise increase would have been reported as 5.7x -- a
  **42% under-read of the exact defect this instrument exists to catch**.
- **The predicted bias now uses the per-channel sd.** A bias is a *level shift*, and
  a level shift does not average down across channels the way noise does. Deriving
  `sigma_frame` from the channel mean under-predicted the bias by `sqrt(3)`, which
  would have made a real bias look like a smaller fraction of prediction than it is.

Both errors pointed the same way: **toward declaring a biased fix acceptable.**
That is failed instrument #5, and unlike the previous four it was caught by
commissioning rather than after the fact.

A third correction followed from the same case. The expected channel-mean ratio is
**neither 9.7 nor 9.7/sqrt(3)**: it depends on how chroma-correlated the *baseline*
noise already is. Measuring that as `k = sd_chan/sd_mean` gives **1.131** on
flower-bud (against 1.732 for perfectly independent and 1.000 for perfectly
correlated -- so the merged noise is largely, not wholly, chroma-correlated, as
demosaic implies). The commissioning now **derives** its expectation from the
measured `k` rather than asserting a hardcoded constant, and predicts 10.96 and
6.38 against 10.97 and 6.38 measured. Deriving it made the plant a stricter test,
not a looser one: it now asserts the instrument's channel arithmetic exactly.

### 17.5 -- What the commissioning caught in the SUBJECTS: two masks were wrong

The mask defines every distance in the measurement, so a wrong mask corrupts
everything downstream silently. **Both failures were found by looking at the mask,
not at its area** -- the area was unremarkable in both cases.

- **`coffee-bean`**: a shaded region of the white paper is darker than the
  threshold and touches the bean, so the largest-connected-component rule
  swallowed a large piece of **backdrop into the subject**. Every distance in that
  region was wrong.
- **`109MSDCF`**: the subject is several paint strokes of *different* luminance, so
  a single luminance threshold selects a different subset at every threshold, and
  the largest-component rule kept only one stroke. Mask area ran 10.1% / 17.5% /
  43.0% across a +/-0.1 threshold sweep -- a 4.3x swing.

Defining the **backdrop** instead of the subject fixes both, because on these
captures the backdrop is one thing -- bright and neutral -- while the subject is
merely "not that", and need be neither dark, nor connected, nor of one tone. Two
guards now run automatically:

| subject | mask | threshold instability | verdict |
|---|---|---|---|
| `flower-bud-alone-cpl` | 22.40% | 1.20x | usable, backdrop FLAT (index 1.39) |
| `109MSDCF` | 50.97% | 1.03x | usable, backdrop FLAT (index 1.16) |
| `coffee-bean` | 63.11% | 1.18x | usable, backdrop **STRUCTURED** (3.86) |
| `couch-fibers-cpl` | **99.49%** | 1.00x | **REFUSED** |

**`couch-fibers-cpl` has no backdrop at all** -- it is pure fibre texture edge to
edge. That is a category error, not a tuning problem: the quantity this harness
measures does not exist on that subject, and the harness now **refuses to return a
number** rather than returning an arbitrary one. It stays in the verification as a
do-no-harm guard judged by `worst_tile.py`, the ESF machinery and by looking.

On `coffee-bean` the far-field tile residual is scene texture rather than noise
(contamination index 3.86, where the index is the median tile residual sd over its
10th percentile). The `sigma_frame` chain is therefore **withheld** there. The
measured shift is still valid on that subject, because it is a difference between
two arms of the *same scene* and the scene cancels out of it -- which is also why
the error of the shift is now computed from **per-tile deltas** rather than from
each arm's own scatter. Taking each arm's scatter and adding in quadrature would
overstate the error of the difference by an order of magnitude on a busy subject.

### 17.6 -- The baseline profiles, and a correction to 16.10's predicted bias

Measured on the pinned baseline arms, absolute DN, backdrop level by distance:

| subject | d=4-12 | d=120-200 | d=700-1200 | near-field deficit |
|---|---|---|---|---|
| `flower-bud-alone-cpl` | 15271 | 15694 | 18937 | **-3666 DN** |
| `109MSDCF` | 7780 | 9051 | 8793 | **-1014 DN** |
| `coffee-bean` | 41210 | 53504 | 55406 | **-14196 DN** |

The harness independently reproduces the two published veiling numbers: flower-bud
at d = 120-200 gives **-3243 DN** against ORCH's -4066 DN, and 109MSDCF's aura
appears at **-1014 DN** against ORCH's -177 DN. The flower-bud agreement is close;
the 109MSDCF disagreement is a real difference and it matters, see below.

**Correction to 16.10.** That section estimated the undebiased-envelope bias at
**+169 DN** from an assumed `sigma_frame` of 200 DN. Measured, it is far larger,
and it is an interval rather than a number:

| subject | sigma_frame | max of 3 chosen | mean of top 3 of all n |
|---|---|---|---|
| `flower-bud-alone-cpl` | 1169 DN | **+994 DN** | **+2898 DN** |
| `109MSDCF` (n=22) | 634 DN | **+511 DN** | **+914 DN** |

Two things were wrong in 16.10 and both are corrected here.

1. **The assumed `sigma_frame` was ~6x too small.** The measured bias is 994-2898
   DN on flower-bud, not 169 DN. This *strengthens* the warning considerably:
   ORCH's -149 DN residual is not merely comparable to the predicted bias, it is
   an order of magnitude smaller than it.
2. **"Upper envelope of 3" has two readings that differ by 3x**, and 16.10 quoted
   one without saying which. The *maximum of 3 chosen frames* is +0.848 sigma; the
   *mean of the top 3 of all 205* is +2.471 sigma. 16.10's +0.845 sigma was the
   first reading. Which applies depends on how the fix is implemented, so the
   harness now reports the **interval** and does not pick an endpoint.

`sigma_frame` is itself an upper bound, since `n_admit` defaults to the full frame
count and the gate admits fewer. A large predicted bias makes a measured shift look
like a small fraction of it, which is the unsafe direction -- so **the verdict is
not taken from this number at all**. It is taken from the shift against zero and
the pedestal shape, both of which are model-free. The prediction is context.

### 17.7 -- Acceptance bar and pin

Bar, as set by ORCH and refined by §16.10:

- `flower-bud-alone-cpl`, d = 120-200 px: must beat **-247 DN**, what frame 102
  achieves alone. The merge currently gives -4066 DN.
- `109MSDCF`: **placebo**. 22 frames, dark subject on a bright backdrop but no depth
  separation and only a -177 DN aura. Any far-field level shift here is bias.
- `coffee-bean`: **second control**. Carries the veil at -38.2% but has no ring
  (+0.23% at d=450 px against flower-bud's +12.0% at d=18 px), so it separates the
  two defects for free.
- `couch-fibers-cpl`: do-no-harm guard, pure texture, no flat region anywhere.
  **Not measurable by this harness** -- see 17.5. Judged by `worst_tile.py`, the
  ESF machinery, and by looking at the picture.

**One caveat on the placebo, which I am flagging before the fix lands rather than
after.** 109MSDCF is a *veil* placebo, not an *aura* placebo. With the corrected
mask covering all the paint strokes, its near-field deficit measures **-1014 DN**,
not the -177 DN in the brief, and its profile is non-monotonic: it dips at d = 4-12,
rises *above* the far field at d = 120-200, and settles. That is not a veil shape
and is consistent with a local edge effect at thick paint strokes rather than
defocused occlusion. Its placebo role survives intact, because that role depends
only on there being **no depth-separated foreground to veil the backdrop**, so any
*far-field* level shift there is still bias and nothing else. But the -177 DN figure
should not be used as an acceptance threshold on this subject, and I would rather
say so now than explain it afterwards.

The **22-frame vs 205-frame** difference between 109MSDCF and flower-bud is a second
discriminator for free: an order-statistic bias grows like `sqrt(2 ln n)`, so a
percentile-based fix must show a *smaller* bias on 109MSDCF than on flower-bud, in a
ratio the harness can predict in advance.

**Pin.** All arms render from one binary, stated by SHA-256 in
`veil/run-<arm>.log`, with `--linear-srgb --demosaic --gate 4.0` and **no
`--auto-exposure`** -- a per-arm exposure choice would normalise away the additive
bias under test. Baseline arms for this shakedown come from `pin-b001f22`, SHA-256
`34D784478C16EBC837BC3240B3CD5D613F210B170D03B4E5C61EFCDBA4049D68`, with frame
counts 205 / 22 / 105 / 299 taken from the render logs. The verification arms will
be re-rendered from a single pin built at BUILD-HALO's fix commit, and the baseline
re-rendered from that same commit with the fix disabled, so that BUILD-BLEND's
multi-band default and BUILD-RENDER's lateral-CA default cannot enter the
comparison.
## 18. VERDICT: BUILD-HALO's veil envelope is right on the subject it was built for and destroys `coffee-bean`

I am the independent verifier for `1b6f2fb`. The harness of section 17 was
commissioned 6/6 **before the fix existed**, so nothing below was tuned to the
thing it judges.

**Headline. The fix passes its acceptance bar and passes the placebo, and it
also pushes 13.8% of the `coffee-bean` frame into hard clipping. Both are true.
It must stay opt-in, and it needs one guard that the codebase already has the
machinery for.**

### 18.1 Design: one binary, two arms, so no other lane can enter the comparison

The fix is env-gated, which is better than a two-commit comparison and I used it.
Both arms are the SAME binary, built at `5e320be`, SHA-256
`64AEDD96B08282A5F973117DD5379F3DB5F65F01C13CC66CC183E082E3081C4F`:

* **Arm A** `STREHL_PHOTOMETRIC=on`, veil unset. Confirmed inert: **0** `veil:`
  lines in `run-A.log`.
* **Arm B** `STREHL_PHOTOMETRIC=on STREHL_VEIL=1.5`, the shipped configuration
  from BUILD-HALO section 26.1.

Both carry photometric, because `STREHL_VEIL` refuses to run without it and an
arm that differed in two things could not attribute anything. BUILD-BLEND's
multi-band default and BUILD-RENDER's lateral-CA default are therefore
irrelevant to every number here. `--linear-srgb --demosaic --gate 4.0`, no
`--auto-exposure`. Potency was checked before spending the render budget: the
two arms differ by SHA-256 on the cheapest subject.

### 18.2 The debias constant was NOT fitted. That question is closed.

ORCH's instruction was that "a debiasing constant fitted to null the veiling
number *is* the artifact". It was not fitted. `merge.rs:2101` is

```rust
let debias = (2.0 * frames.max(2.0).ln()).sqrt() as f32;
```

with `frames` taken from `max_index`, the population being debiased, rather than
from a caller. It has **no free parameter**. The engine printed 2.49 / 3.05 /
3.26 / 3.38 on the 22 / 105 / 205 / 299 frame stacks, against
`sqrt(2 ln n)` = 2.4864 / 3.0509 / 3.2628 / 3.3765. All four match.

**But it is the wrong closed form, in the safe direction.** `sqrt(2 ln n)` is the
*mode* of the maximum of n normals, not its *expectation*. Monte Carlo,
400,000 trials per n:

| n | `sqrt(2 ln n)` | measured `E[max]` | over-subtraction |
|---|---|---|---|
| 22 | 2.4864 | 1.9088 +/- 0.0008 | **0.578 sigma** |
| 105 | 3.0509 | 2.5241 +/- 0.0007 | **0.527 sigma** |
| 205 | 3.2628 | 2.7542 +/- 0.0006 | **0.509 sigma** |
| 299 | 3.3765 | 2.8765 +/- 0.0006 | **0.500 sigma** |

So every applied pixel has about half a single-frame sigma of real light
subtracted from it. Against a *darkening* defect that is the conservative
direction, and it means the fix under-corrects rather than adds light. It is not
a bug to fix ahead of section 18.7, but it should be recorded rather than
discovered later.

### 18.3 The operator cannot add light by extreme-value bias. This is structural.

The substitution test at `merge.rs:2174` is `est > current + margin * sigma`
with `est = pmax - debias * sigma`, so the operator fires only where

    pmax - mean > (debias + margin) * sigma  =  6.263 sigma at n = 205.

Under i.i.d. normal noise `pmax - mean` has mean 3.26 and sd 0.42, so 6.263 is
roughly a 7 sigma event. Monte Carlo, **2,000,000 trials per stack at the
engine's own measured mean n_eff** of 4.87 / 27.24 / 138.72 / 2.73:

| subject | n | n_eff | threshold | null firing rate | observed `applied` | ratio |
|---|---|---|---|---|---|---|
| `109MSDCF` | 22 | 4.87 | 5.486 | 8.5e-06 | 0.60% | 706x |
| `coffee-bean` | 105 | 27.24 | 6.051 | < 5e-07 | 25.46% | > 5e5 |
| `flower-bud-alone-cpl` | 205 | 138.72 | 6.263 | < 5e-07 | 12.49% | > 2e5 |
| `couch-fibers-cpl` | 299 | 2.73 | 6.377 | 4.5e-06 | 13.08% | 2907x |

This is a genuine exoneration of the worry I myself raised in section 16.10 and
that ORCH escalated: **on clean Gaussian backdrop the envelope is not merely
debiased, it is effectively inert**, the closest call being 706x. Any far-field
shift observed below is therefore NOT extreme-value bias. It is either real veil
or a non-Gaussian sample population, and section 18.7 shows it is the second.

The same arithmetic inverts into a diagnostic. To fire at the observed rate by
noise alone, the true per-frame spread would have to be **1.45x** the calibrated
noise model on `109MSDCF`, **1.94x** on flower-bud, **2.16x** on `coffee-bean`
and **1.73x** on `couch-fibers`. All are well above 1, so the operator is
responding to real frame-to-frame content rather than to noise.

**One correction to my own first pass here.** I originally ran this with
`n_eff` guessed as most of the frame count and reported "zero firings
everywhere". The engine prints the real mean n_eff and it is 4.87, not 18, on
`109MSDCF`; a noisier gated mean makes `pmax - mean` wider and the null rate is
then 8.5e-06 rather than zero. The conclusion is unchanged and the margin is
still three orders of magnitude, but "zero" was an artefact of my input, not a
property of the operator. `veilnull.py` now derives that sentence from its own
table rather than asserting it alongside.

### 18.4 Results, in absolute DN, nothing normalised to its own arm's far field

| subject | role | applied | far-field shift | pedestal (outer band) | far-field noise sd ratio | output clipped A -> B |
|---|---|---|---|---|---|---|
| `flower-bud-alone-cpl` | target | 12.49% | **+8.6 +/- 1.3 DN** | +6.0 DN, flat | 1.13x | 0.000% -> 0.000% |
| `109MSDCF` | placebo | 0.60% | **+1.4 +/- 0.4 DN** | +1.6 DN | 0.99x | 0.000% -> 0.000% |
| `coffee-bean` | veil control, no ring | 25.46% | **+3656 +/- 117 DN** | **+3553 DN, RISING** | 0.59-0.77x | **1.41% -> 15.20%** |
| `couch-fibers-cpl` | do-no-harm | 13.08% | harness REFUSES (no backdrop) | -- | -- | 0.000% -> 0.000% |

### 18.5 `flower-bud-alone-cpl`: the bar is met, and it is met by removing veil rather than adding light

| d (px) | A | B | delta |
|---|---|---|---|
| 30-60 | 15233.1 | 15644.2 | +411.0 |
| 60-120 | 15446.2 | 17383.7 | **+1937.5** |
| 120-200 | 16827.9 | 18560.8 | **+1733.0** |
| 300-450 | 18714.8 | 18720.2 | +5.4 |
| 700-1200 | 18920.1 | 18926.1 | +6.0 |

**Acceptance.** At d=120-200 the deficit against far field goes **-1914.0 ->
-189.7 DN**, beating the -247 DN bar. Against a *common* reference (arm A's far
field, so the convention cannot flatter the fixed arm) it is **-181.1 DN**. The
verdict does not depend on the convention.

**And it is a repair, not a lift.** The near-field recovery is +1937 DN while the
pedestal 1200 px away is **+6.0 DN**. That is a ratio of **323:1**, and the
delta decays monotonically to it. An additive bias is flat to the frame edge by
construction; this is not. Predicted undebiased-envelope bias on this stack was
+572 to +1668 DN and the measured pedestal is **0.4% of the lower endpoint**.

The picture agrees: the difference map is a tight halo following the silhouette
and decaying smoothly to black, and the grey aura visible on white paper in A is
gone in B. **Subject-region gradient changes by +0.13%**, so nothing was done to
the subject.

**Decomposition, measured by me on one subject.** Section 17's baseline had
photometric OFF and read -3066.7 DN at d=120-200. So of the total repair,
photometric normalisation alone is **40.1%** and the envelope is **59.9%**.
(Those two arms are from different pins, `b001f22` and `5e320be`, so treat the
split as indicative.)

### 18.6 `109MSDCF`: the placebo is genuinely inert

Every band moves between **+0.1 and +1.6 DN** on a level of 8835 DN, that is
0.016%. Gradient +0.49%. Noise ratio 0.99x. It is +3.5 sigma from zero because
1153 tiles make the standard error small, and that is the harness working, not a
defect: 1.4 DN is a no-op by any photographic standard. **This is the arm that
could have caught added light and it did not.**

Note, as flagged in section 17.7 before any of this was measured, that
`109MSDCF` is a *veil* placebo and not an *aura* placebo, and that its -177 DN
figure from the brief must not be used as a threshold.

### 18.7 `coffee-bean`: FAIL. The maximum is the wrong statistic next to the sensor ceiling.

The far field rises **+3656 DN**, and the shape is diagnostic in the opposite
direction to flower-bud: the delta **grows** with distance, +2832 at d=300-450 to
**+3553 at d=700-1200**, the outermost band being the largest. **A veil decays
with distance from the subject. This does the reverse.** Output clipping goes
**1.41% -> 15.20% of the frame**, 4.5 million pixels destroyed to pure white,
and the whole-frame p95 goes 62532 -> 65535.

**The mechanism, from the engine's own clipping census in `run-A.log`:**

| subject | raw pixels clipped in >= 1 frame | clipped in EVERY frame | outcome |
|---|---|---|---|
| `flower-bud-alone-cpl` | 0.0000% | 0.0000% | clean repair |
| `109MSDCF` | 0.0000% | 0.0000% | inert |
| `couch-fibers-cpl` | 0.0000% | 0.0000% | mild, section 18.8 |
| `coffee-bean` | **8.8283%** | **0.0000%** | **15.2% clipped output** |

`pmax` is a per-pixel maximum over every frame. At a pixel that clips in some
frames and not others, **the maximum is by definition the clipped sample**, and
`always clipped = 0.0000%` says an unclipped, recoverable sample existed at
every one of those pixels. The estimator selects the one value known to be
wrong. The debias cannot help: it subtracts noise sigma, and clipping is not
noise.

This also explains the distance dependence. `coffee-bean`'s backdrop is a lit
receding surface that brightens away from the bean, so the population near the
ceiling grows with d, which is exactly the profile measured.

**Strength of this claim.** The subject split is 4/4 with a mechanism stated in
advance, correct in sign, and correct in order of magnitude, and the failing
subject is the only one whose backdrop sits at 87% of full scale. I have **not**
isolated it interventionally, because the change needed is in `merge.rs`, which
is not my file. The test I am handing BUILD-HALO is one line of exclusion and one
re-render, in section 18.11.

**The near field on `coffee-bean` is a genuine success and I want that on the
record too**: at 1:1 the grey aura along the bean's shoulder is removed cleanly.
The defect is entirely in the far field.

### 18.8 `couch-fibers-cpl`: applied at 13.08% on a subject that has no backdrop at all

The harness refuses this subject, correctly: the backdrop mask covers 99.49% of
the frame because `couch-fibers` is pure fibre texture edge to edge, and a
"backdrop level near a subject" does not exist. The do-no-harm instruments give:
median level **+1.94%**, p95 +0.49%, p1 and p5 unchanged, gradient **+6.12%**,
no clipping. BUILD-HALO reported +2.33% level lift; I measure +1.94% at the
median, so their number stands.

**A rising gradient here is not detail and must not be read as one.** The
difference map is scattered patches whose own boundaries add gradient, which is
BUILD-HALO's section 25.5 warning about manufacturing a step, arriving on a
subject they did not aim at. This is a real but modest harm, and it argues the
focus ceiling admits pure texture.

### 18.9 The noise cost is real, and it is larger in gradient than in level

On flower-bud, far-field noise sd goes 44.88 -> 50.49 DN, **1.13x**. But mean
absolute gradient in the same region goes **+32.0% at d=300-450 and +35.1%
beyond 1200 px**, while the level there moved 6 DN. A 6 DN level change cannot
raise gradient by a third: **the envelope injects high-frequency grain into the
backdrop across the entire frame, including regions the veil never reached.**

This is far below the 9.7x I predicted in section 16.10 for an undebiased
envelope of 3, because the debias plus the 3 sigma margin fire on only 12.49% of
pixels rather than everywhere. So the answer to "did they debias it" is yes, and
the answer to "does it still cost noise" is also yes, at about a third more grain
on a clean white backdrop. On a print that is visible.

### 18.10 Two corrections to my own record

* **Section 17.6's sigma_frame values are overestimates.** They used
  `n_admit = frames`, documented at the time as an upper bound. The engine
  prints the real mean n_eff at gate 4.0: **138.7 / 4.87 / 27.2 / 2.73** for
  flower-bud / 109MSDCF / coffee-bean / couch, not 205 / 22 / 105 / 299.
  Flower-bud's sigma_frame is 674.8 DN, not 1169 DN. Every predicted-bias
  bracket built on it shrinks by the same factor. The verdicts above do not
  use those predictions, which is why they were not the gate.
* **Section 16.10's "+169 DN" remains wrong, and section 17.6's replacement
  bracket was too alarming.** The correct statement is that the prediction is
  worth about a factor of two and the model-free shape test is worth the verdict.

### 18.11 Verdict and what I am asking for

**PASS on the target subject and the placebo. FAIL on `coffee-bean`. Keep it
default OFF.** It is currently default OFF, which is the correct state, and
nothing here argues for flipping it.

For BUILD-HALO, in priority order:

1. **Exclude clipped samples from `pmax`.** The `Estimator` already carries
   `censor`, `clip_w` and `fold_censored` for precisely this population, and the
   clipping census is already computed and printed. A pixel with
   `always clipped = 0%` has a valid sample; take the maximum over the valid
   ones. **Acceptance for that change: `coffee-bean` output clipping returns to
   1.41% and the far-field delta stops rising with distance.** That is the
   interventional test I could not run in my own lane.
2. **Consider `E[max]` rather than `sqrt(2 ln n)`** if the 0.5 sigma
   over-subtraction ever matters. It currently helps, so this is a note, not a
   request.
3. **The focus ceiling admits pure texture** (`couch-fibers`, 13.08%). A
   luminance floor cannot catch that case because the fibres are bright.

**Pin.** Everything in section 18 comes from one binary,
`C:\dev\strehl-out\BUILD-SHARP\pin-5e320be\target\release\strehl.exe`, SHA-256
`64AEDD96B08282A5F973117DD5379F3DB5F65F01C13CC66CC183E082E3081C4F`, built at
`5e320be`. Arm logs with per-arm SHA and argv are at
`C:\dev\strehl-out\BUILD-SHARP\veil\run-{A,B}.log`.

**Deconvolution stays deferred.** Section 18.7 is a live artefact that grows with
distance and clips, and section 18.9 is a third more backdrop grain. Sharpening
either would score as a win on any high-pass metric. The sequencing ORCH and I
agreed still holds.

---

## 19. `restore.rs`: the module had no applicator, and once written it clears the floor by 3.1x

ORCH's reachability sweep found `restore.rs` dark -- 357 lines, zero references
outside its own file -- and routed it to me as "the single largest piece of
measured, unclaimed sharpness in this codebase". Three of that framing's four
claims survived contact. The fourth did not, and neither did the module's own
recorded verdict.

### 19.1 What was actually there

`selftest()` runs and passes. The arithmetic is sound: I re-derived
`gather_mtf` by simulating a real Catmull-Rom gather and fitting the amplitude
by least squares against a `[cos, sin]` basis rather than trusting the module's
own analytic tap DFT, and it **CONFIRMS to 5e-5** at 0.25, 0.40 and 0.50 cycles
per gather sample. A bilinear-kernel plant in the same checker is CAUGHT, so
that confirmation is not vacuous.

But the module was not built-and-unwired. It was **characterised and never
built**. It had `gather_mtf`, `RestoreConfig`, `gain`, `gain_2d` and
`selftest` -- everything needed to describe the filter and nothing that applies
it to an image. There was no applicator. "Wire it in" was not a wiring job; the
filter had to be written first.

That also explains the module's recorded negative, and the explanation is worse
than the negative. `restore.rs` reports gain caps of 1.4, 1.7 and 2.5 producing
byte-identical output, and reads that as the filter being too weak to matter. I
hashed the three arms it was measured on:

| arm | SHA-256 of `109MSDCF/*/linear.tif` |
| --- | --- |
| `b-g4-cr` (reference) | `215B2BEE...E7B41452` |
| `b-g4-cr-rest1.4` | `7D7BAE73...A18C1E17` |
| `b-g4-cr-rest1.7` | `7D7BAE73...A18C1E17` |
| `b-g4-cr-rest2.5` | `7D7BAE73...A18C1E17` |

The three restore arms are byte-identical **to each other** while differing
from the reference. So something ran, and it was completely insensitive to its
own gain cap across a 1.4x to 2.5x range. A filter whose output does not move
when its principal control moves by 79% is not a weak filter, it is a
disconnected control. The recorded ESF nulls (+0.688, +0.019, +0.111 um) are
measurements of that disconnected path, and they do not bear on the filter as
now written.

### 19.2 The ceiling, stated before measuring

ORCH's brief quotes 18.6% of the merge's blur variance. That is a variance
share, and edge width goes as its square root, so a **perfect** correction is
worth `1 - sqrt(1 - 0.186)` = **9.78% of edge width**, not 18.6%. At the noise
levels the module itself recorded it is nearer **3.2%**. I said so before
running anything, and I am recording the prediction here because the result
lands inside it.

### 19.3 What I built

A separable, zero-phase FIR applicator in `restore.rs`: `autocorrelation`
(Wiener-Khinchin, no FFT dependency added), `power_at`, `design_fir`,
`fir_response`, `restore_plane`, and a `RestoreReport`. `S(f)` is estimated
from the image's own autocorrelation, so the filter remains self-calibrating
and no lens model is load-bearing.

Two properties are structural rather than fitted:

* **DC gain is exactly 1.** Substituting `g0 = 1 - 2 sum_k g[k]` gives
  `G(f) = 1 + 2 sum_k g[k] (cos(2 pi f k) - 1)`, which is 1 at `f = 0` for any
  `g[k]`. The least-squares fit cannot trade DC accuracy for passband accuracy.
  Measured `|dc_gain - 1| = 0.000e+00` on every arm of every subject, and mean
  delta `+/-0.003 DN` on 33 MP frames. This filter cannot become an exposure
  change, which is the failure mode section 18 caught in a different estimator.
* **Zero phase.** `H` is real and non-negative, so the kernel is symmetric and
  an edge cannot move. Confirmed on real data: `esf.py` reports the registered
  shift as `0,0` on every ROI of every arm.

One defect found in my own first draft: the least-squares fit tracks its target
at the fit points and **overshoots between them**. A cap of 1.1 was fitted and
the designed filter realised 1.1107. The cap is now enforced on the realised
response by scaling the outer taps by `lambda = (cap - 1)/(realised - 1)`,
which scales `G(f) - 1` exactly and leaves `G(0) = 1` exact.

### 19.4 Commissioning the tests

Six mutations, each naming the single test that must go red.

| plant | named test | result |
| --- | --- | --- |
| zero-phase broken (one tap asymmetric) | edge does not move | CAUGHT |
| DC normalisation 1.98 instead of 2.0 | DC gain is exactly 1 | CAUGHT |
| realised-cap rescale removed | DC gain is exactly 1 | CAUGHT |
| identity broken on all three routes | `gain_cap = 1.0` is byte-identical | CAUGHT |
| design returns the identity kernel | 10-90 width is recovered | CAUGHT |
| CONTROL, expected inert: short-circuit only | (must stay green) | HELD |

**5/5 lethal plants caught by their named test, 1/1 inert control held, 5 + 1 =
6 of 6 planted.** Two failures of my own instrument are worth recording, since
both would have reported a false result:

* The first version of plant 4 changed `gain_cap > 1.0` to `> 1.0001`, which
  makes the short-circuit fire **more** readily rather than less. It was inert
  by construction and reported a MISS that I nearly read as redundancy in the
  code. A mutation must be checked for potency in the direction intended, not
  merely for being a change.
* Chasing that MISS did establish a real fact: with `gain_cap = 1.0` the
  identity is defended three separate times -- the explicit short-circuit, the
  clamp in `gain()` which zeroes the least-squares right-hand side, and
  `design_fir`'s rescale whose `lambda` is exactly 0 when `cap` is 1. Plant 6
  now demonstrates that redundancy instead of asserting it, and goes red if it
  is ever lost.

### 19.5 The measurement, in um

Paired 10-90 ESF rise, `esf.py`, against `b-g4-cr` on M88b's frozen admitted
ROIs. Positive is sharper. **Instrument floor 0.6699 um.**

| sigma^2 | n | mean delta_um | sd | mean rise_ref | mean rise_arm | vs floor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 4 | **+2.331** | 1.342 | 44.972 | 42.641 | 3.5x |
| 691.6 | 4 | **+2.100** | 1.227 | 44.972 | 42.872 | 3.1x |
| 2000 | 4 | **+1.986** | 0.626 | 44.972 | 42.986 | 3.0x |
| 4983 | 4 | +1.008 | 1.054 | 44.972 | 43.964 | 1.5x |
| 20000 | 4 | +0.496 | 1.051 | 44.972 | 44.476 | below |

Every admitted ROI moves the right way at every setting bar one (`RU1` at
`sigma^2 = 20000`, `-0.264 um`, inside the floor). Per-ROI at `sigma^2 = 691.6`:
`M94 +1.502`, `TW1 +2.272`, `TW5 +0.891`, `RU1 +3.733 um`.

**The result lands inside the ceiling predicted in 19.2 before it was
measured.** At `sigma^2 = 691.6` the pooled rise goes 44.972 -> 42.872 um, which
is **4.67% of edge width**, between the 3.2% expected at recorded noise levels
and the 9.78% perfect-correction bound. The prediction was made from a variance
share and an independent instrument confirmed it.

The instrument cannot be fooled the easy way here. Its documented weakness is
that it reads wider on an arm of genuinely lower contrast; the per-arm edge
contrast is unchanged (`c_ref 7769` vs `c_arm 7764` on M94), and the registered
shift is `0,0` everywhere.

### 19.6 Cost columns, all four, as run

`python C:\dev\strehl-out\ORCH-CLAMP\accept.py <dir> --ref b-g4-cr`.
Gate: `clip <= 0.02%`, `acuity >= 98% ref`, `micro >= 98% ref`, `p1 rise <= 2% range`.

| subject | arm | clip% | acuity | microC | p1 |
| --- | --- | ---: | ---: | ---: | ---: |
| 109MSDCF | `b-g4-cr` | 0.0000 | 131.6 | 71.11 | 482 |
| 109MSDCF | `s2-691.6` | 0.0000 | 148.4 | 76.68 | 481 |
| ruler | `b-g4-cr` | 0.0000 | 201.9 | 23.23 | 2567 |
| ruler | `s2-691.6` | 0.0000 | 244.6 | 26.40 | 2576 |
| tweezers | `b-g4-cr` | 0.0000 | 827.4 | 437.04 | 1960 |
| tweezers | `s2-691.6` | 0.0004 | 1110.4 | 519.16 | 1904 |

**15 candidate arms judged, 15 PASS, 0 FAIL, 0 subjects unjudgeable. GATE:
PASS.** Acuity rises 12.8% to 34.2% and micro-contrast rises on all three
subjects, which is what was bought.

Two costs that did move, reported because ORCH asked for all four columns
whatever they say:

* **`p1` rises on one of three subjects.** Ruler goes `2567 -> 2576` at
  `sigma^2 = 691.6` and `2567 -> 2580` at `sigma^2 = 100`. It falls on 109MSDCF
  (482 -> 481) and on tweezers (1960 -> 1904). ORCH's instruction was that `p1`
  must not rise; on ruler it rises by 9-13 DN. That is inside the gate but it
  is not zero and I am not going to describe it as zero.
* **Clipping rises on tweezers**, `0.0000% -> 0.0004%`. Inside the 0.02% gate by
  a factor of 50, and it is the subject with specular metal highlights already
  at the top of the range.

### 19.7 Ringing: the numbers and the picture

Ringing is the failure mode, and a high-pass metric scores overshoot as a win,
so this is measured two ways and both have to agree. The probe is the excursion
beyond the reference's own local 9x9 `[min, max]` window -- the arm landing at a
level the reference never reached anywhere nearby.

| subject | max overshoot | p99.99 | mean frac at strong edges | p99 frac | pixels overshooting |
| --- | ---: | ---: | ---: | ---: | ---: |
| ruler | 4539 DN | 623 DN | 0.082% | 3.23% | 2.95% |
| tweezers | 10800 DN | 2779 DN | 0.232% | 7.79% | 4.45% |

Then I looked, at 1528 x 760 px, at the strongest edge in each frame. **No
visible ringing on either.** On the ruler the graduation edges tighten and the
paper texture resolves, with no bright rim beside the black bars. On tweezers
the machining striations become legible and the dark field adjacent to the
bright metal edge stays clean -- which is precisely where an overshoot would be
most visible. The large `max` figures sit on specular highlights, where a
contrast boost pushing toward the local extreme is the intended behaviour
rather than ringing.

This is bounded by construction and that is the reason it looks like this.
Because `H >= 0.6251` across the whole band for our own gather kernel, even a
**full inverse** is capped at 1.60x gain. There is no `sigma^2` at which this
runs away, which is the structural difference from section 13's defocus-OTF
inversion that destroyed the picture.

### 19.8 On the knob

ORCH said: if you find yourself choosing `sigma^2/S(f)` to make a number land,
stop and say so. I did not choose it. Constructing a `NoiseModel` requires the
profile chain the CLI assembles and I could not reach it from a `strehl-core`
example without touching another lane, so instead of substituting a number I
liked, **I swept it and reported the whole curve including the settings that do
not help**. `sigma^2 = 20000` is in the table at +0.496 um, below the floor,
because a response curve with its unhelpful end deleted is not a response
curve.

For context and not for selection, the green plane's Laplacian-MAD noise scale
is `sigma^2 = 686` on 109MSDCF, 508 on ruler, 2154 on tweezers -- so the
module's own recorded 691.6 sits in the right place on two of three subjects
without having been fitted to them. **The correct `sigma^2` should come from
`NoiseModel::averaged_green_luma_sigma` at the merged pixel's own level and
`n_eff`, and that is the integration ask below.**

### 19.9 Integration point

The filter corrects **our own gather kernel**, so it belongs as close to the
gather as possible, applied once, to a plane that has been resampled exactly
once.

* **Correct point: post-gather, pre-demosaic, on the merged plane, with
  `grid_factor = 1.0`.** At that point the plane has been resampled exactly
  once and `H` is exactly the kernel that resampled it.
* **Measured point: post-merge on linear RGB with `grid_factor = 2.0`**, which
  is what the numbers above are. It works and clears the floor by 3.1x, but it
  is second best: at `grid_factor = 2.0` image frequency `f` maps to gather
  frequency `2f`, so the whole correction is confined below `f = 0.25` and
  gain at image Nyquist is only 1.02.

`merge.rs` is BUILD-HALO's and `pyramid.rs` is BUILD-BLEND's, so **I have not
touched either.** The hook I need, routed to ORCH:

1. Call `restore::restore_plane` on each merged plane after the gather and
   before demosaic, with `grid_factor = 1.0`.
2. Set `sigma2` from `NoiseModel::averaged_green_luma_sigma(median_level, n_eff, rho_warp)`
   squared, not from a literal. This is the connection between the calibrated
   noise model and the restoration that the project has never made.
3. Default `gain_cap = 1.7`. `gain_cap = 1.0` is the exact off switch: byte
   identical, not merely close, and defended three ways.
4. Env surface `STREHL_RESTORE=<cap>` with `0` or `off` meaning `1.0`.

### 19.10 Two things ORCH should know

**The framing overstated the prize, and the module understated it.** 18.6% of
blur variance is 9.78% of edge width perfectly corrected, not 18.6%; the
realised 4.67% is less than ORCH's brief implies. But the module's own recorded
verdict of "negative, too weak to ring" was measuring a path that ignored its
own gain cap, and it is wrong in the other direction. The honest number is
+2.100 +/- 1.227 um pooled, 3.1x the instrument floor, at a real cost of 9-13 DN
of `p1` on one subject of three.

**I am the author of `restore.rs`** (commit `28f7a3a`) and now of its
applicator, so by this project's own rule I must not be its only verifier. The
ESF instrument, the plant harness and the overshoot probe are all mine. An
independent agent should re-run 19.5 and 19.6 before this ships default-on. I
note that my bias here ran toward under-claiming -- I predicted the result would
fall below the instrument floor and it did not -- but that is an argument about
direction, not a substitute for a second pair of eyes.

## 20. The resampling chain, priced in amplitude

HEAD `e718c46fa157e90d67e33bd014f8252a3eeb52ec`. Instruments:
`experiments/BUILD-SHARP/src/resample_audit.py` (new) on top of
`resample_price.py` (committed `142f3fb`).

ORCH's framing, which is the right one and not the one I would have chosen
unprompted: a resample *count* proves nothing, because two resamples at 0.04 px
cost under 2% together. The finding that matters is **a resample at large
phase**. So the deliverable is a phase distribution and a composed amplitude,
not a tally.

### 20.1 Coverage, as counted outcomes

Eight sites found. Every one lands in exactly one bucket and the buckets sum to
eight, so a site I skipped cannot be read as a site I cleared.

| outcome | n | sites |
| --- | ---: | --- |
| PRICED | 2 | alignment gather; chroma co-site |
| NOT-ON-THIS-PATH | 4 | demosaic; pyramid reduce/expand; align-solve downsample; lateral-CA warp |
| NOT-A-RESAMPLE | 2 | 2x2 quad binning; `edgeaware::gather_levels` |
| COULD-NOT-INSTRUMENT | 0 | -- |
| **TOTAL** | **8** | |

Three of the four NOT-ON-THIS-PATH entries are conditional and I want them
recorded as conditional rather than dismissed. `pyramid` is off the path only
because ORCH's reachability sweep found it DARK; the moment BUILD-BLEND lands
its CLI wiring it becomes a priced site. The lateral-CA warp is off the path
only because `--fix-ca` defaults off at this HEAD; when ORCH flips that default
it becomes a priced site whose phase is already known -- red 0.152 px, blue
0.039 px, from ORCH's own radial/tangential decomposition. Demosaic is off the
binned path because a quad collapse never demosaics.

### 20.2 The alignment gather is a genuinely large-phase resample

Measured, not assumed, from a real 20-frame sidecar
(`coffee-bean-20.warpmap.txt`, 3516x2344). The warp is stored as a complex
similarity `z' = a z + b`, so evaluating it over a 64-px grid across every
placed frame reproduces the coordinate the gather actually samples rather than
modelling it. 40,700 samples.

The phase histogram is near-uniform over [0,1) -- ten bins between 3666 and
5803, with a mild pile-up in [0.9,1.0). That is the expected signature: the
per-frame scale term `g ~ 2e-3` over a 3516 px plane sweeps the displacement
through several whole pixels across the field, so the phase cycles many times
and no single number summarises it.

    distance to nearest integer: mean 0.2369  median 0.2373  p90 0.4470  p99 0.4942
    fraction further than 0.2 from an integer: 57.3%

A uniform phase is the worst case short of a fixed half-pixel, and it is what we
have. This is not a defect -- the frames genuinely need moving -- but it prices
the floor that everything else stacks on top of.

### 20.3 The composed cost, and it is worse for red and blue

Serial application costs the product of the stages.

| f (cyc/px) | align (2-D) | co-site (2-D) | **G retained** | **R/B retained** |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | 0.88986 | 0.88135 | **0.88986** | **0.78428** |
| 0.35 | 0.69055 | 0.68133 | **0.69055** | **0.47050** |
| 0.50 | 0.42096 | 0.47266 | **0.42096** | **0.19897** |

ORCH asked what number would redirect the softness effort. It is this one: at
f = 0.35 the viewable render retains **69% of green and 47% of red and blue**.
That is not an optics floor, it is arithmetic on our own interpolator, and
roughly half of the red/blue deficit is recoverable.

Largest single contributor: the **chroma co-site** at f = 0.25 and f = 0.35
(11.87% and 31.87% of amplitude); the alignment gather takes over at Nyquist.

Scope, stated precisely because it decides who cares: co-siting runs only
inside `write_binned`, which both callers reach only within `if let Some(m) =
matrix`. So it is on the **viewable** render and not on the byte-frozen
measurement path that `write_rgb16` serves. My section 19 ESF numbers were taken
on `linear.tif` and therefore do **not** include this cost -- but the owner's
"these look horrible" is about the viewable render, which does. That gap is
itself a finding: our sharpness instrument has been measuring a path the
photographer never sees.

### 20.4 Potency -- the audit is not merely quiet

`--plant PHI` injects an extra resample at a stated phase into the chain. The
expected amplitude is computed independently of the audit's own accounting and
the two are compared.

    planted phi=0.5 both axes
      f=0.25  priced 0.781250  expected 0.781250  MATCH
      f=0.35  priced 0.402210  expected 0.402210  MATCH
      f=0.50  priced 0.000000  expected 0.000000  MATCH

The plant also re-ranks the "largest contributor" line from the co-site to the
PLANT at all three bands, so the ranking logic responds too and is not a
constant. The audit sees a large-phase resample when one is there.

### 20.5 The fix, and why it is free -- ROUTE, do not merge

`gather_checked` (`warpmap.rs:441`) takes a **single plane** and a
`Similarity`, and evaluates `t.apply_at(px, py, cx, cy)` per pixel. The
co-site is a constant translation of +/-0.25 on both axes applied to R and B
**after** that gather, by a second interpolation
(`image_out.rs:956-957`). Two warps applied serially; one composed warp
available.

Composing is exact: replace `t` with `t` composed with the constant co-site
translation for the R and B planes only, leaving G untouched (G is not
co-sited today and must not start being resampled). The sample count, the
kernel and the cost are unchanged -- only the coordinate differs.

It commutes with the merge. The shift is a fixed geometric property of the CFA
quad, identical for every frame, so it passes through any per-pixel weighted
mean and through argmax selection alike. Doing it per-frame before the merge
and doing it once after are the same operation on a linear combination.

Control, because "free" is a claim: adding a constant 0.25 to a near-uniform
phase distribution should not change the gather's own mean cost, and it very
nearly does not -- ratios 0.9942 / 0.9800 / 0.9471 at the three bands, the
residual being the [0.9,1.0) pile-up rather than the offset. Netting that
against the removed stage:

| f | serial (today) | folded | gain | amplitude recovered |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | 0.78428 | 0.88469 | 1.128x | +10.0 pts |
| 0.35 | 0.47050 | 0.67678 | **1.438x** | **+20.6 pts** |
| 0.50 | 0.19897 | 0.39867 | 2.004x | +20.0 pts |

`image_out.rs` is not my lane and neither is the aligner, so this is a routing
request, not a patch I am landing. What it needs is a per-plane co-site offset
threaded into the gather call and the `resample_shift` calls deleted -- not
`resample_shift` itself, which the non-composed path may still want.

### 20.6 What I did not establish

The 1.438x is a **predicted** amplitude gain from the composition, computed on
the measured phase distribution. It is not yet an ESF measurement on a rendered
frame, because rendering it requires the code change that is not mine to make.
When it lands, the check is the section 19 ESF instrument run on the *viewable*
render rather than `linear.tif`, and the prediction to falsify is that red and
blue sharpen while green is bit-identical. Green's bit-identity is the built-in
placebo and it should be asserted, not eyeballed.

I have also not priced the 2x2 bin itself. It is a real MTF cost and it is
larger than anything above, but it is a decimation that defines the output
lattice rather than an interpolation at a phase, so folding it into this table
would be double counting a different quantity. It deserves its own section and
does not have one yet.

## 21. The two conditional sites have fired: CA and pyramid, priced

HEAD `049589fc71d466ad303ef4164e3e937862414940`. Instrument:
`experiments/BUILD-SHARP/src/resample_audit2.py` (new), reusing §20's
`resample_audit.py` and `resample_price.py`.

§20 classified the lateral-CA warp and the pyramid as NOT-ON-THIS-PATH
*conditionally* and named the conditions. Both have now fired. Pricing them.

### 21.0 A correction to §20 first, in the conservative direction

§20 evaluated the gather coordinate as `a z + b`. `Similarity::apply_at`
(`align.rs:290`) is **centre-relative**: `a (z - c) + b + c`. The difference is a
constant offset `c - a c`, about 3.5 px here, and on a near-uniform phase
distribution a constant offset should not move the mean amplitude. It barely
does -- **+0.29% / +1.04% / +3.17%** at f = 0.25 / 0.35 / 0.50. §20's table
stands and if anything slightly **overstated** the loss. The model is exact now
regardless.

### 21.1 Q1 and Q2 -- the CA warp is already folded, and it was designed that way

ORCH asked whether the shipped default is a net sharpness loss, expecting the
CA cost to be small against the co-site recovery. The answer is stronger than
"small": **it is structurally zero**, and I did not need to measure it to find
that out, only to read `optics.rs`.

`OpticalProfile::compose` (`optics.rs:297`) returns **one** `Similarity` doing
alignment and CA together, and `align_cmd.rs:1430` calls it per CFA plane and
hands the result straight to `gather_checked`. The module's own header states
the reasoning under the heading *"Why applying it is free"*: a radial
magnification about a point is itself a similarity, similarities are closed
under composition, so the correction rides the gather's existing interpolation.

That is the same move I prescribed for the co-site in §20.5, already built, in
this codebase, by someone else, for the neighbouring channel correction. So Q2's
answer is: **it not only composes, it already does.**

CA's real cost is therefore only what the composed scale does to the phase
distribution of the one gather:

| f | align only | + CA red | + CA blue | red cost |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | 0.89241 | 0.88871 | 0.89276 | **-0.41%** |
| 0.35 | 0.69776 | 0.68718 | 0.69914 | **-1.52%** |
| 0.50 | 0.43431 | 0.41484 | 0.43844 | -4.48% |

Blue is *positive* at two of three bands, which is not a result, it is the
phase distribution being re-dealt. Treat both as zero.

The counterfactual is the number that matters. Had CA been applied as its own
pass at ORCH's measured displacements, red would have paid **0.94587 / 0.85720 /
0.76637** -- a 14.3% amplitude loss at f = 0.35, which is nearly half the
co-site's 31.87% and would have been a real question. **That cost is avoided,
not paid.**

**Q1 answer: the shipped CA default is not a net sharpness loss. It is
amplitude-neutral, and the fringing removal on 25/26 subjects is free.**

### 21.2 A latent collision I want on the record before BUILD-COSITE lands

`A7C2_FE100GM_2XTC_X4CPL` carries `translation: (0.6294, -0.4240)` plane px, and
its own field docs say the term is *"the same order as the ~0.5 px/axis that CFA
co-siting predicts"* and is **unattributed** -- it may be lattice, may be
optical, and the instrument cannot say which.

That is the *same physical quantity* BUILD-COSITE is about to add to the gather.
Today there is no collision, because `resolve_for_capture` returns the
`_RADIAL` twin (`optics.rs:570` and `:597`) whose translation is exactly
`(0.0, 0.0)`. So the co-site is genuinely uncorrected and §20's prescription is
sound.

But the two are one selection away from double-correcting, and the failure would
be silent -- a sub-pixel red shift, in the direction that looks like slightly
worse CA. **If anyone ever wires the non-radial profile, the co-site offset must
be removed from one of the two.** Recording it here rather than in a comment
because the profile and the gather are owned by different lanes.

### 21.3 Q3 -- the pyramid costs exactly nothing, and that is provable

The Laplacian is *defined* as the residual `L_i = G_i - expand(G_{i+1})`, so
collapsing an unmodified pyramid is algebraically the identity. Measured on
512x512 white noise, 7 bands:

    max |collapse(analyse(x)) - x| = 4.441e-16      (float64 round-off)

and per-band amplitude through analysis and synthesis is **1.000000** at all
three of f = 0.25 / 0.35 / 0.50.

This is the important structural point and it generalises: `reduce` and `expand`
are heavily blurring operators individually -- `[1,4,6,4,1]/16` is a severe
low-pass -- but they appear only in a **perfect-reconstruction filter bank**,
where the blur that `expand` introduces is exactly the blur that was subtracted
out to form the Laplacian. **A blurring kernel inside a PR filter bank is not a
resampling loss.** Pricing it as one, by looking at the kernel alone, would have
produced a large and entirely fictitious number.

Potency, because a measurement that returns exactly 1.000000 three times is
precisely the shape of an instrument that is not connected: scaling the finest
Laplacian band by 0.80 returns **0.800000 / 0.800350 / 0.800128**, MOVED at all
three bands. The instrument responds.

So the pyramid contributes a factor of **1.000000** to every cell of the chain.
Its sharpness behaviour is entirely in *which frame wins which band*, which is a
merge question and belongs to BUILD-BLEND, not a resampling question.

### 21.4 Revised partition, shipped configuration

| outcome | n |
| --- | ---: |
| PRICED | 3 |
| NOT-A-RESAMPLE | 2 |
| NOT-ON-THIS-PATH | 2 |
| COULD-NOT-INSTRUMENT | 1 |
| **TOTAL** | **8** |

The COULD-NOT-INSTRUMENT entry is new and it is honest: I looked for a
downstream output-scaling step and did not find one, but "I did not find one"
is not the same as "there is none", and §20's own rule says a site I could not
clear must not be counted as cleared. It is one site and it is named.

### 21.5 The shipped chain

| f | G | R/B today | R/B folded | gain |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | 0.89241 | 0.78326 | 0.88871 | 1.135x |
| 0.35 | **0.69776** | **0.46820** | 0.68718 | **1.468x** |
| 0.50 | 0.43431 | 0.19608 | 0.41484 | 2.116x |

Unchanged in substance from §20 with both new sites priced in: **the co-site is
still the only removable loss in the chain, and it is still the whole of it.**

### 21.6 On the 4.5% tile deficit -- one decisive question, not an answer

ORCH asks whether 47% R/B retention at f = 0.35 could explain a survey finding
only 4.5% of detail tiles have merge >= best single frame. I will not adjudicate
a result I have not seen, but there is a single question that decides whether my
numbers are even relevant, and it is cheap:

**Is the "best single frame" in that survey the aligned frame, or the original?**

* If the comparison frame is taken **after** the alignment gather, then both
  sides pay the same gather and it **cancels**. My numbers cannot explain the
  deficit and it is a real merge finding.
* If the comparison frame is the **original, unwarped** frame, then the single
  frame pays **zero** resamples while the merge pays the full chain. On green
  that alone hands the single frame a **1.43x** advantage at f = 0.35
  (1 / 0.69776); on red and blue, **2.14x**. A survey built that way would
  report the merge losing on the great majority of textured tiles **even if the
  merge were perfect**, and 4.5% is entirely consistent with that.

The second case would also explain why the deficit concentrates in *detail*
tiles: the handicap is frequency-dependent and vanishes at low frequency.

So this is testable without re-running anything: read the survey's reference
arm. If it is the unwarped original, the instrument has the §20 disease --
**comparing across a path boundary** -- and the fix is to warp the reference
through the same gather before comparing. That is the same class of error as
"our sharpness instrument has been measuring a path the photographer does not
see", which ORCH is already promoting to a rule, and I think it is the same rule.

## 22. Retraction, and the demosaic priced on the delivered pixels

HEAD `a2582514044b9b7acea6a963d8ff7d784a86a87e`. New instruments:
`crates/strehl-core/examples/demosaic-plane.rs` and
`experiments/BUILD-SHARP/src/demosaic_price.py`.

### 22.1 The retraction, verified from the artefact rather than accepted

§20 stated that the co-site runs on the **viewable** path and that ESF numbers
taken on `linear.tif` therefore excluded a cost the product paid. That is wrong.
ORCH's correction is right and I checked the crux from the artefact rather than
take a second report on trust, which is the whole lesson:

    SHIP-V1/109MSDCF.tiff   (4688, 7032, 3) uint16
    SHIP-V1/112MSDCF.tiff   (4688, 7032, 3) uint16
    SHIP-V1/113MSDCF.tiff   (4688, 7032, 3) uint16

A quad collapse is 2344 x 3516. That is full sensel resolution, so
`write_binned` did not produce it, so the co-site never touched it.

**The sign of my instrument-bias finding is inverted.** ESF on `--linear-srgb`
does not miss a cost the product pays; it pays a cost the product does not, and
therefore **understates** delivered R/B. The finding survives as a finding --
the instrument and the product are on different paths -- but every consequence I
drew from its direction was backwards.

I want the proximate cause recorded, because it was not a reasoning error. The
`image_out.rs` header called `write_binned` *"the 'for looking at' render"*. I
read that sentence and treated it as a fact about the call graph. It was a claim
by an absent author about code that had changed. The artefact was on disk the
whole time and I never looked at its shape.

### 22.2 What §20's prescription actually is

The co-site fold is a **measurement-path-only** change. It does not touch a
delivered pixel. Its 1.468x at f = 0.35 is real and was independently
reproduced to within 1.8% with green bit-identical, but it improves the file the
ESF instrument reads, not the file the photographer prints.

That reclassifies it from "the largest single quality win available" to "a
correction to an instrument". It is still worth having for exactly that reason,
but it must not be sold as a product improvement and I sold it as one.

### 22.3 The demosaic, priced -- and it is not COULD-NOT-INSTRUMENT

ORCH offered that bucket. I declined it: the demosaic is drivable directly.
`examples/demosaic-plane.rs` runs `strehl_core::demosaic` on a synthetic mosaic,
so this is the **shipped Rust**, not a transcription. That is the gap §21 left
on the pyramid and it is not left again.

The information ceiling first, because it decides how to read everything below.
Red is known at one site per quad, so in output coordinates red is sampled at
period 2 and its Nyquist is **0.25 cyc/px**. Above that, no red was measured;
anything delivered there is inferred from green under the slowly-varying-chroma
assumption. Two scene families bracket that assumption instead of averaging over
it: `neutral` (R = G = B, assumption exactly true) and `chroma` (R varies, G and
B flat, assumption maximally violated).

**Red, neutral scene.** `gain` is MTF at the signal frequency; `false` is the rms
of everything else, which catches a demosaic that delivers amplitude in the
wrong place.

| f | malvar gain | false | bilinear gain | red lattice alone |
| ---: | ---: | ---: | ---: | ---: |
| 0.10 | 1.0387 | 0.025 | 0.9044 | 0.9978 |
| 0.15 | 1.0606 | 0.032 | 0.7935 | 0.9970 |
| 0.20 | **1.0534** | 0.043 | **0.6567** | 0.9954 |
| 0.25 | **0.8750** | 0.000 | **0.0000** | **0.0000** |
| 0.35 | 0.7657 | 0.448 | 0.2047 | ambiguous |

Three things, and none of them is "Malvar loses":

1. **Below red's Nyquist it is essentially lossless.** Against the information
   present in the merged red plane *before* re-interleaving (the last column,
   ~0.995), Malvar delivers 1.00 to 1.06. It gives back what the red plane held.
   ORCH's question (b) answers **no measurable loss**.
2. **It beats the direct upsample by a wide margin** -- 1.0534 against 0.6567 at
   f = 0.20, a factor of **1.60x**. Question (a) answers decisively for Malvar.
3. **At exactly f = 0.25 the red lattice sees literally nothing.** A tone at
   0.25 cyc/px sampled at period 2 lands on zero crossings, so red-only and
   bilinear both deliver **0.0000** -- and Malvar delivers **0.8750**. Every bit
   of that is borrowed from green. Blue, on the (1,1) lattice, delivers
   **1.1250** at the same frequency; the two are phase-opposite about a mean of
   exactly 1.0, which is the two lattices' offset showing up in the correction
   term and is a nice internal check that this is real structure and not noise.

**Red, chroma scene.** When green is flat, Malvar is not merely similar to
bilinear, it **is** bilinear:

    max |malvar - bilinear| = 0.0        np.array_equal = True

The gradient correction is a term in green's Laplacian, so a flat green makes it
identically zero and the algorithm degenerates exactly. This is the single most
useful fact in this section: **Malvar's entire R/B advantage is borrowed from
green, and it is worth precisely what green's detail is worth.**

**Green.** Quincunx sampling, so green genuinely carries information above 0.25:

| f | malvar gain | false | bilinear gain |
| ---: | ---: | ---: | ---: |
| 0.25 | 1.0000 | 0.000 | 0.7500 |
| 0.30 | 0.8989 | 0.072 | 0.6727 |
| 0.35 | **0.7667** | 0.165 | 0.6031 |
| 0.40 | 0.6341 | 0.259 | 0.5477 |
| 0.50 | 0.0000 | 0.000 | 0.0000 |

Potency, 3 of 3. A separable `[t, 1-2t, t]` blur planted on the demosaiced red
has closed-form response `1 - 2t(1 - cos 2*pi*f)`, and the measured ratio against
the unplanted table matches it:

| f | unplanted | planted | ratio | closed form |
| ---: | ---: | ---: | ---: | ---: |
| 0.15 | 1.0606 | 0.8420 | **0.79389** | **0.79389** |
| 0.25 | 0.8750 | 0.4375 | **0.50000** | **0.50000** |
| 0.35 | 0.7657 | 0.1573 | 0.20543 | 0.20611 |

One honest caveat on the last column of the red table. Above f = 0.25 the "red
lattice alone" arm retains amplitude but **cannot assign it a frequency** -- the
samples are equally consistent with the tone and with its alias. That is what
aliasing is, and it is why I have written *ambiguous* rather than the 0.995 the
arithmetic returns. The `false` column is where that ambiguity becomes visible
as actual error: 0.45 at f = 0.35 for Malvar.

### 22.4 The delivered chain, which is the number that was wanted

Composing the alignment gather (§21), the pyramid (1.000000, §21) and the
demosaic. Multiplying MTFs assumes shift-invariance; Malvar is linear and
shift-invariant *within a CFA phase*, which is the condition, so this composes,
but it is a composition of separately measured stages and not an end-to-end
render.

| f | align x pyramid | demosaic G | **delivered G** | demosaic R/B | **delivered R/B** |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.25 | 0.8924 | 1.0000 | **0.8924** | 1.0000 (R+B mean) | **0.8924** |
| 0.35 | 0.6978 | 0.7667 | **0.5350** | 0.7657 | **0.5262** |
| 0.50 | 0.4343 | 0.0000 | **0.0000** | 0.0000 | **0.0000** |

**The demosaic costs 23.3% of green amplitude at f = 0.35.** That is the same
order as the alignment gather's 30% and it was entirely unpriced. ORCH's instinct
that it was the largest unpriced term on the delivered pixels is correct.

It is also the *least* avoidable of the three in its current form, but not
unavoidable: Malvar beats bilinear by 1.27x at f = 0.35 (0.7667 against 0.6031),
and the published adaptive methods beat Malvar on exactly this axis. That is now
a quantified target rather than a preference, and `demosaic.rs`'s own header
already lists what it declined and why -- worth re-reading against a number it
did not have.

The deeper structural point: **delivered R/B detail is a function of green's
chain, not of R/B's.** Malvar hands green's detail to red and blue, so the two
delivered columns above are within 2% of each other on luma-textured content
despite red carrying half the samples. Anything that sharpens green sharpens all
three channels; anything that sharpens only R/B moves almost nothing.

### 22.5 Why folding the co-site damaged the demosaic, as measured

ORCH measured sd(R-G) x1.235 and HF(R-G) x1.313 when the fold was applied ahead
of the demosaic. The mechanism follows directly from 22.3 and I would now
predict the sign in advance.

Malvar's stencils do not interpolate red in isolation. They reconstruct red
through a **chroma difference against green**, and every stencil coefficient
assumes red and green sit on their nominal CFA lattices. Co-siting moves red off
that lattice by 0.25 px while the stencil keeps differencing it against green as
though it had not moved. The difference is then taken between points that no
longer coincide, so a real chroma difference is manufactured where the scene has
none -- which is exactly an increase in sd(R-G) and in HF(R-G), in both channels,
which is what was measured.

This is not a rigid translation the demosaic could absorb, because Malvar is
shift-invariant only *within* a CFA phase, and the fold moves a sample across
phases by a fraction. ORCH's note that it is "sensitive to sample position in a
way that is not a simple translation" is precisely that.

And the conclusion that follows is stronger than "do not fold": **on the shipped
path the co-site is redundant.** Its job is to move red and blue from their CFA
corners to the quad centre. The demosaic already places red and blue at *every*
output pixel, corners included. Co-siting is a pre-correction for a lattice
offset that the next stage handles from first principles. It belongs on the
binned measurement path, where there is no demosaic to do it, and nowhere else.

### 22.6 Revised partition -- 9 sites, the shipped render path

Two rows change from §20 and §21 and both are corrections; two rows are new.

| outcome | n | sites |
| --- | ---: | --- |
| PRICED | 3 | alignment gather + CA; **demosaic (was NOT-ON-THIS-PATH -- wrong)**; pyramid |
| NOT-ON-THIS-PATH | 3 | **chroma co-site (was PRICED/viewable -- wrong)**; 2x2 quad binning; align-solve downsample |
| NOT-A-RESAMPLE | 2 | `edgeaware::gather_levels`; **re-interleave to mosaic** (data movement, no interpolation) |
| COULD-NOT-INSTRUMENT | 1 | downstream output scaling, if any exists |
| **TOTAL** | **9** | |

The COULD-NOT-INSTRUMENT entry is unchanged and still honest: I have not found a
downstream scaling step and I have not proved there is none.

### 22.7 What I would not claim

The chain in 22.4 composes three separately measured stages; I have not rendered
a frame end to end and measured it. The demosaic numbers are from synthetic
tones on a 512 x 512 grid, which is the right instrument for an MTF and the wrong
one for artefact behaviour on real texture -- the `false` column says artefacts
exist above red's Nyquist but not what they look like on a bee. And I did not
measure the merge's own contribution at all; §21.6's question about whether the
per-tile survey compares against a warped or unwarped reference is still open and
still cheap, and it is the one I would spend the next hour on.

## 23. Wiring `restore.rs`: three sub-tasks settled, the seam re-measured, and two of my own predictions refuted

Assignment: `crates/strehl-core/src/restore.rs` is finished, self-testing, and
has zero callers in any shipped binary. Wire it behind a flag, default off,
and report the trade. Pinned HEAD `ab0d71a5810667c66dcb2a8641b15c5174937c57`.

This section reports what is settled. **The flag is not landed and the trade
curve is not measured.** Both reasons are given in 23.5, and the first is a
correction to the seam I reported to ORCH as narrow.

### 23.1 `selftest()` runs, and the "known defect" is in the brief, not the code

The working tree does not compile -- another agent's edit at `merge.rs:2865`
calls `est.enable_veil(1.5, 3.0, 0.5)` against a four-argument signature. I
built a clean tree with `git archive ab0d71a5 | tar -x` at
`C:\dev\strehl-out\BUILD-SHARP\pin-ab0d71a5` and ran there:

    cargo test -p strehl-core --lib restore    ->  10 passed, 0 failed

`kernels_are_interpolating_and_preserve_dc` calls `selftest().unwrap()`, so
`selftest` is on the tested path rather than merely present.

ORCH reported a defect: `restore.rs:573`'s constants documented at f = 0.35 but
actually at f = 0.40. **There is no defect.** I re-derived the phase-averaged
Catmull-Rom MTF from the basis polynomials, independently of the module:

| f | 0.25 | 0.35 | 0.40 | 0.50 |
| --- | --- | --- | --- | --- |
| phase-averaged CR | 0.94024 | 0.82113 | 0.74255 | 0.62500 |

Line 573 reads `[(0.25, 0.9402), (0.40, 0.7425), (0.50, 0.6251)]`. Every
abscissa is correctly labelled. The header's separate claim -- that the
Lanczos-3 / Catmull-Rom ratio peaks at 13.3% -- I located at **f = 0.350**
(ratio 1.1300), also correctly labelled. `docs/research/V-chroma2.md:388-404`
had already reached this conclusion by a different route. Three independent
derivations agree, so the mislabel is in the brief. No code change.

### 23.2 `sharpen_per_octave` is orthogonal to restoration -- confirmed, by structure

ORCH asked whether `MergeConfig::sharpen_per_octave` (default 1.4) is partly
compensating the gather loss by accident, in which case wiring restore on top
would over-sharpen. Read at `pyramid.rs:772-825`: the ramp is an **exponent on
a convex combination across frames within a band**, bounded by
`Hull::InputRange`. A convex combination cannot exceed the largest input, so
the band's output amplitude is bounded by the **best single frame's** amplitude
in that band.

The gather loss is **common-mode**: every frame is resampled, so every frame
has already lost the amplitude before the combination runs. A selectivity
exponent redistributes weight among frames that have all paid the same cost; it
cannot recover an amplitude that is absent from all of them. The two knobs
therefore address disjoint quantities and are not redundant. This is a
structural argument, not a measurement, and it is falsifiable: if restore at
unit gain measurably changes with `--pyramid-sharpen`, I am wrong.

### 23.3 Placement: (b), and the reason is not the one I argued

`experiments/BUILD-SHARP/src/restore_placement.py`. The restoration is run by
the shipped Rust (`restore-plane.exe` from the pinned tree), not transcribed.

**My prediction, on record before running:** `restore_plane` is a symmetric
FIR, hence linear and shift-invariant, hence it commutes exactly with a
fixed-weight mean, hence placement cannot change noise and ORCH's prior for (b)
would be right only on cost.

**Refuted.** At fixed equal weights, K=8, on a 2600 DN signal:

    max |R(mean) - mean(R)| = 4.408e+01 DN     float precision would be < 1e-3

`RestoreConfig::gain(f, signal_power)` is Wiener and `design_fir` fits the
filter to the spectrum of the plane it is handed. Restore is **data-adaptive**,
not a fixed operator, and adaptive operators do not commute with averaging.

The direct measurement, flat field, absolute DN:

| arm | flat sd | flat mean |
| --- | --- | --- |
| unrestored merge | 11.074 DN | 400.01 DN |
| **(b) merge then restore** | **12.205 DN** | 400.01 DN |
| (a) restore then merge | 14.390 DN | 400.04 DN |

**(b) wins on measured noise**, by 18% against (a), for the same operator.
Means are reported alongside because a ratio hides an additive bias; they agree
to 0.03 DN, so the sd comparison is between arms at the same level. ORCH's
prior was right and my argument for indifference was wrong. Placement is (b).

### 23.4 The mechanism is NOT established, and my second attempt at it also failed

I first attributed the non-commutation to per-frame noise inflating each
plane's S(f). Probe: divide the per-frame noise by 100. The gap fell only to
**x0.8923**. That refuted the attribution, and I had written the conclusion
into the script's output before running it -- the script printed a claim its
own numbers contradicted. That is the failure this project keeps logging and I
reproduced it.

So I ran a factorial, `experiments/BUILD-SHARP/src/restore_commute_2x2.py`,
separating the two live candidates -- the per-plane spectral fit (isolated by
giving every frame the same blur phase) and the `gain_cap` nonlinearity
(isolated by raising the cap out of reach):

| | cap = 1.4 | cap = 1e6 (off) |
| --- | --- | --- |
| varied phase, noisy | 4.310684e+01 | 4.596555e+01 |
| varied phase, quiet | 6.934738e-02 | 8.224487e-02 |
| EQUAL phase, noisy | 4.451508e+00 | 4.451508e+00 |
| **EQUAL phase, quiet (null)** | **5.493164e-04** | **4.882812e-04** |

Readings:

- **The null passes.** Identical planes commute to 5.5e-4 DN, below the 1e-3
  float floor. The harness is sound, so the large numbers are findings.
- **`gain_cap` is refuted as the cause.** Removing it changes nothing; the
  equal-phase-noisy row is bit-identical at 4.451508 both ways.
- **Both noise and phase variation contribute, and they interact.** Quiet rows
  are ~0, so noise is necessary; but at equal noise, varied phase is 43.1
  against 4.45, a factor of ten.
- **This contradicts the noise/100 probe of the previous paragraph**, and the
  discrepancy is my error: that probe held the `sigma2` *parameter* at 144
  while the data noise went to 0.12, so it varied the data and the regulariser
  independently without saying so. Here `sigma2` tracks the data.

My current hypothesis is that the Wiener design's sensitivity to the per-plane
spectrum is largest when sigma^2 is comparable to the signal power -- which is
the regime the calibrated model actually puts us in -- so the filter genuinely
differs plane to plane. **I am labelling this UNRESOLVED rather than asserting
it.** I have been wrong twice on this operator's mechanism in one sitting.

**The placement verdict does not depend on it.** 23.3 is a direct measurement
of noise in both arms; it stands whatever the mechanism turns out to be.

### 23.5 The seam is wider than I told ORCH, and that is why nothing is landed

I reported the wiring point as a ~15 line edit at `merge_cmd.rs:5824`. Having
now read it properly, that was wrong in two ways.

1. **`write_merged` has no `NoiseModel` in scope.** Its signature at
   `merge_cmd.rs:5611` is `(merged, levels, wb, xyz_to_cam, space, demosaic,
   exposure, path)`. The only locals near the seam are `range`, `gains`,
   `black`. ORCH's instruction is that sigma^2 must come from the calibrated
   model and not be chosen; `profile::noise_model_for` is called at
   `merge_cmd.rs:2724` and `:4242`, both far above. So sigma^2 has to be
   threaded in. The narrowest form is to compute it in the caller, where
   `noise` is live, and pass one `Option<RestoreConfig>` parameter -- a type I
   own, keeping the noise logic out of the shared file.
2. **There are three writers, not one.** `write_merged` is called at
   `merge_cmd.rs:3859` and `:4485`, and `stack.rs:1109-1178` carries a
   *mirrored copy* of the same demosaic branch, by its own comments. Wiring one
   and not the others produces a build where the flag silently does nothing on
   some paths, which is the exact class of defect this assignment exists to fix.

ORCH's constraint is "keep your edit to the narrowest possible seam" in a file
with several live agents. A signature change plus three call sites plus a
mirrored branch in `stack.rs` -- which is not my file -- is not that. **I am
handing the routing decision back rather than taking it unilaterally.**

What I need from ORCH: either (i) confirmation that I may change
`write_merged`'s signature and touch `stack.rs`, with the other agents in those
files told, or (ii) a decision to wire only the `blend-render` gallery path,
which is what the reference renders actually use, and accept that `stack` is
unflagged for tonight.

### 23.6 Not done, and not to be read as done

- **The trade curve is not measured.** No strength sweep, no A/B render.
- **The overshoot guard is not run.** ORCH pre-registered it and it is the one
  way this change can make the owner's loudest complaint worse. The baseline to
  beat is on record: monotonic from d=1 to d=275 px with no interior local
  maximum on `flower-bud`. I do not have camera-linear renders of
  `flower-bud-alone-cpl` or `lavendar-cpl`; `BUILD-SHARP/renders/` has neither,
  so this needs a re-render before it can be run at all.
- **`accept.py` cost columns are not run.**
- **The flag does not exist.** Nothing in this section changed any shipped code
  path; `restore.rs` is still unreachable from every binary.

Standing, unchanged: `restore.rs` needs an independent verifier and I authored
both it and the applicator, so 23.1's "no defect" finding is mine to report and
not mine to close.

### 23.7 What I would tell the owner

The restoration is real, its transfer function is the best-characterised of any
sharpness lever here, and it is measurably safe to place at (b). But an
unmeasured sharpener shipped on a night when the complaint is halos is a bad
trade at any gain, and the guard that would catch that has not been run. My
recommendation on the default is therefore **off**, and it will stay off until
the overshoot trade curve exists -- not because I doubt the module, but because
ORCH asked for the default to be set by measurement and the measurement is the
part I did not reach.

## 24. The restoration is wired, default off, and MEASURED INERT at the sigma^2 I gave it

Landed: `crates/strehl-core/src/restore.rs` gains `RESTORE_ENV`,
`gain_cap_from_env` and `RestorePlan` (commit `794e605`, newline fix `a2d5a81`);
`crates/strehl-cli/src/merge_cmd.rs` threads one `Option<RestorePlan>` into
`write_merged` and restores the four CFA planes before interleaving.
`cargo check -p strehl-cli` rc=0. The flag is `STREHL_RESTORE`, whose value IS
the strength, because `gain_cap = 1.0` is a documented no-op and that makes
"off" the same code path as "on at zero" rather than a second one that can
drift.

Placement is (b), per 23.3: once on the merged CFA planes, before the demosaic.

### 24.1 It reaches the code, and it changes nothing. Both halves measured.

Sweep on `flower-bud-alone-cpl`, 205 frames, one binary
(`pin-a2d5a811/target/release/strehl.exe`), one shared warp cache so alignment
is identical across arms, camera-linear and demosaiced, no `--srgb`:

    strehl stack <dir> --out linear.tif --resampler catmull-rom --demosaic --pyramid-gate 4.5

Provenance read from the logs, not the filenames, and identical on every arm:
`merge backend : pyramid`, `levels : black 512, white 15360`,
`held-out err : 0.352 px  resampler: CatmullRom`, output
`7040 x 4688, 16-bit RGB, linear camera-native RGB`.

The flag fires. At cap 1.5 the writer logs, per plane:

    restore R  : cap 1.500, max gain 1.0000, at Nyquist 1.0000, recovered 0.0000, mean 1291.3 DN
    restore G1 : cap 1.500, max gain 1.0000, at Nyquist 1.0000, recovered 0.0000, mean 3500.6 DN
    restore G2 : cap 1.500, max gain 1.0000, at Nyquist 1.0000, recovered 0.0000, mean 3497.5 DN
    restore B  : cap 1.500, max gain 1.0000, at Nyquist 1.0000, recovered 0.0000, mean 2302.8 DN

`max gain 1.0000` at every plane and every cap. I did not take that from the
log, because a log is an author's claim; I took it from the artefact:

| arm | SHA-256 (first 16) | bytes |
| --- | --- | --- |
| off | 20D67637515491F4 | 198023291 |
| 1.2 | 20D67637515491F4 | 198023291 |
| 1.5 | 20D67637515491F4 | 198023291 |

**Byte-identical.** The restoration is reachable, executes, and is a complete
no-op on real data.

### 24.2 Why, exactly, and it is my error and not the module's

From `RestoreConfig::gain`, gain exceeds 1 only where

    h / (h^2 + sigma^2/S)  >  1     i.e.    sigma^2/S  <  h(1 - h)

At f = 0.35 the gather MTF is h = 0.82113, so the entire budget is
h(1-h) = **0.1476**. The filter has to be handed a plane whose signal power at
that frequency is at least 6.8x its noise variance before it will lift a finger.

I supplied `NoiseModel::variance(plane, mean_dn)` -- the **single-frame**
variance -- and wrote in the doc comment that this "OVERSTATES what is actually
present" and that the direction was "deliberate", because over-regularising
cannot cause overshoot. That is true and it is beside the point. **This merge
combined 205 frames.** Over-regularising cannot cause overshoot and it equally
cannot cause sharpening, and at up to 205x too much variance it does not clear
0.1476 anywhere in the frame.

The reasoning error is worth naming because it is not arithmetic. sigma^2 in the
Wiener form is the noise **of the plane in the filter's hand**. The plane in the
filter's hand is a 205-frame merge. Substituting a single frame's noise is not a
conservative version of the right number, it is a different quantity, and
"conservative" was the word that stopped me checking it.

### 24.3 What the trade curve is, and why it is not the deliverable ORCH asked for

**There is no trade curve to report.** Sharpness gain is 0.0000 at every cap
tested, so the overshoot guard is trivially passed and the pass means nothing:
an operator that does not run cannot put a local maximum into the
signed-distance profile. Reporting "monotonic, guard passed" here would be a
skipped check dressed as a passed one, which is precisely the failure this
project has a rule about. **The guard is NOT RUN, not PASSED.**

### 24.4 The fix, and the part of it that is not mine

sigma^2 must be the merged plane's noise. The calibrated model already exposes
the right shape -- `NoiseModel::averaged_green_luma_sigma(luma_dn, n,
rho_warp)` takes the frame count and the warp correlation, so this stays inside
the calibration and does not become a tuning knob. `n` is a fact of the render
(205 here), not a number chosen to make a result land.

The honest complication, and it is real: the pyramid merge is a **convex
combination whose effective n varies per pixel**. In flat regions it approaches
205; on detail pixels the selection is nearly winner-take-all and n_eff
approaches 1, where the single-frame variance I used is exactly right. So a
single scalar is wrong everywhere except at one extreme, and the correct input
is a per-pixel n_eff map from the merge. **That map is inside `pyramid.rs` and
`merge.rs`, which are not my files.** I need either an n_eff plane exposed at
the writer, or ORCH's routing to whoever owns those.

Until then the conservative scalar keeps the flag inert, which is a safe state
for a default-off flag but is not a shippable sharpener.

### 24.5 Recommendation

**Default OFF, and now for a second and stronger reason than in 23.7.** Then it
was unmeasured; now it is measured to do nothing. Turning it on tonight would
ship a flag that parses, logs four confident lines per render, and cannot change
a pixel -- the exact failure `merge --help` already warns about in its own text
("a flag that parses and does nothing is indistinguishable from one that works,
and this project has shipped that failure before").

The wiring itself is sound and worth keeping: it is one parameter in the shared
file, it is `None` on every existing path, and it produces byte-identical output
when off -- which the table in 24.1 demonstrates rather than asserts.

### 24.6 Corrections and standing items

- The `restore.rs:573` "known defect" is **still not a defect**, restated here
  because the brief has now asked for it twice. Phase-averaged Catmull-Rom is
  0.94024 at f=0.25, **0.74255 at f=0.40**, 0.62500 at f=0.50, matching L573's
  labels exactly; the header's 13.3% Lanczos ratio peaks at **f=0.350**. Three
  independent derivations agree, including `V-chroma2.md:388-404`, which reached
  it before I did.
- `sharpen_per_octave` remains ARGUED, not MEASURED (23.2). The measurement I
  proposed -- vary it and see whether restore's effect moves -- **cannot be run
  while restore's effect is zero.** It is blocked behind 24.4, not forgotten.
- I committed once with `corpus_lint` FAILING (S3, missing trailing newline)
  because my script ran `git commit` unconditionally instead of gating on the
  lint's exit code. Caught and fixed in `a2d5a81`. The lint had told me on the
  previous line and the shell had printed `lastbyte=125`; I read neither.
- `restore.rs` still needs V-RESTORE. 24.2 is a defect in the wiring I wrote
  around the module, not in the module, and it does not substitute for that read.

## 25. Handover to BUILD-WIRE: placement, and the landing-blocker that is not placement

ORCH has moved the wiring to BUILD-WIRE. `restore.rs` stays mine. This section
is the judgement BUILD-WIRE asked for, conclusions and citations only.

### 25.0 Read this first: the wiring already exists, and sigma^2 is the blocker

**The wiring is already in HEAD.** ORCH's grep reporting "zero references in
`crates/strehl-cli/**`" is stale. `git grep -c strehl_core::restore HEAD --
crates/strehl-cli/src/` returns `merge_cmd.rs:6`, and `git merge-base
--is-ancestor 794e605 HEAD` returns 0. `write_merged` already takes
`Option<RestorePlan>` and already restores the four CFA planes before
interleaving, default off behind `STREHL_RESTORE`. **Do not build it again.**

**The remaining work is not wiring, it is sigma^2, and it is a landing-blocker.**
Measured in 24.1: with the flag on at caps 1.2 and 1.5, output is
**byte-identical** to off (`20D67637515491F4`, 198023291 bytes, three arms, one
binary). The module executes and every plane logs `max gain 1.0000, recovered
0.0000`.

The reason, from `RestoreConfig::gain` (`restore.rs:230`): gain exceeds 1 only where

    sigma^2 / S(f)  <  h(1 - h)

At f = 0.35, h = 0.82113, so the entire budget is **0.1476**. I passed
`NoiseModel::variance(plane, mean_dn)` -- the **single-frame** variance -- to a
plane that is a **205-frame merge**. Up to 205x too much regularisation; the
gain never clears 1.0 anywhere in the frame.

**If BUILD-WIRE keeps that sigma^2, the flag ships inert.** The correct input is
the noise of the merged plane. `NoiseModel::averaged_green_luma_sigma(luma_dn,
n, rho_warp)` (`noise.rs:343`) has the right shape and keeps the number inside
the calibration, with `n` a fact of the render rather than a knob. The honest
complication: the pyramid merge is a convex combination whose effective n varies
per pixel -- near 205 in flat regions, near 1 on detail pixels where selection
is winner-take-all -- so a scalar is wrong everywhere except at one extreme.
**The right input is a per-pixel n_eff map, which lives in `pyramid.rs` /
`merge.rs` and is neither mine nor BUILD-WIRE's.** ORCH has to route that.

### 25.1 Placement: (b). MEASURED, and ORCH's reason for it is wrong.

**(b) once on the merged CFA planes, before the demosaic, per plane
(R, G1, G2, B).** That is where it is already wired.

ORCH's reason -- "the operator is linear and shift-invariant, so applying it
once at the end is very nearly equivalent" -- is the argument I made myself, and
**it is false**. `experiments/BUILD-SHARP/src/restore_placement.py`, running the
shipped Rust: at fixed equal weights, `max |R(mean) - mean(R)| = 4.408e+01 DN`
on a 2600 DN signal where float precision would be `< 1e-3`. Restore is
**data-adaptive**: `design_fir` fits the filter to the spectrum of the plane it
is handed, so it does not commute with averaging. Placement is a real decision,
not a near-equivalence.

The decision still goes to (b), on the direct measurement (23.3), flat field,
absolute DN:

| arm | flat sd | flat mean |
| --- | --- | --- |
| unrestored merge | 11.074 DN | 400.01 DN |
| **(b) merge then restore** | **12.205 DN** | 400.01 DN |
| (a) restore then merge | 14.390 DN | 400.04 DN |

Means agree to 0.03 DN, so this is not a black-point artefact. (b) is 18%
quieter than (a) at equal operator, and costs one pass instead of N.

**One API trap for BUILD-WIRE:** `RestoreConfig::grid_factor` is **1.0** on the
CFA planes, because those planes *are* the gather grid -- one sample per quad
per plane. If anyone moves the call after the demosaic it must become **2.0**.
Getting it backwards halves or doubles the correction (`restore.rs:208`). And
restoring after the interleave is simply wrong: neighbouring mosaic samples are
different colours.

### 25.2 `sharpen_per_octave` does not double-count. ARGUED, and the measurement is blocked.

**ARGUED, not MEASURED.** From `pyramid.rs:772-825`: the ramp is an exponent on
a **convex combination across frames within a band**, bounded by
`Hull::InputRange`. A convex combination cannot exceed its largest input, so a
band's output amplitude is bounded by the **best single frame's** amplitude in
that band. The gather loss is **common-mode** -- every frame was resampled, so
every frame has already paid it -- and a selectivity exponent redistributing
weight among equally-degraded frames cannot restore an amplitude absent from all
of them. Selectivity and amplitude are disjoint quantities. **Not a
landing-blocker.**

I could not promote this to MEASURED, and the reason is 25.0: the test is to
vary `--pyramid-sharpen` and see whether restore's effect moves, and **restore's
effect is currently zero**. It unblocks the moment sigma^2 is fixed, and it
should be run then, because if I am wrong here the failure mode is ringing.

### 25.3 `restore.rs:573` is not a defect. Fourth confirmation, now enforced in code.

The brief has asked three times for a fix to constants "documented at f = 0.35
but actually at f = 0.40". **There is nothing to fix.** The confusion is a
conflation of two true claims in the same file: the module header's 0.35 is
where the **Lanczos-3 / Catmull-Rom ratio** peaks (1.1300), a statement about
two kernels; the test's 0.40 is a point on the **Catmull-Rom MTF itself**.

Rather than change correct constants, I made the file refuse the misreading. The
test now carries the 0.35 row explicitly and the full derived table, with the
conflation spelled out:

    0.25 -> 0.94024   0.35 -> 0.82113   0.40 -> 0.74255   0.50 -> 0.62500

`cargo test -p strehl-core --lib restore` -> **10 passed, 0 failed**, including
the new `0.35 -> 0.8211` row checked against the shipped `gather_mtf`. That is a
fourth independent confirmation, after my re-derivation from the basis
polynomials, ORCH's own, and `docs/research/V-chroma2.md:388-404`. **BUILD-WIRE
should build against the file as it stands.**

### 25.4 Strength range, and where it will ring

The knob is `gain_cap`, and it has a **hard ceiling that is not arbitrary**: the
Wiener gain cannot exceed the inverse filter, `1/h`. So

| f | h | max achievable gain |
| --- | --- | --- |
| 0.25 | 0.94024 | 1.064 |
| 0.35 | 0.82113 | 1.218 |
| 0.50 | 0.62500 | 1.600 |

**A cap above ~1.6 can never bind** -- it is not a stronger setting, it is an
inoperative one, and a sweep that includes 2.0 and 3.0 is sweeping nothing. Mine
did; that is partly why 24.1 read flat.

Sweep **1.05, 1.15, 1.25, 1.40, 1.60**. Expect the useful operating point near
**1.2-1.3**: that is where f = 0.35 saturates, and f = 0.35 is where the
compounded loss actually lives (gather 0.82 x demosaic 0.767 on green, §22).

**Where it will overshoot:** the gain is largest where `sigma^2/S` is smallest,
i.e. in **high-SNR regions**, and the sharpest transitions in a high-SNR region
are exactly the **silhouette edges** ORCH is guarding. A symmetric FIR with gain
> 1 at high frequency has negative side lobes; that is the ring. So the guard
must be read at the bright side of a dark silhouette on a bright ground --
`flower-bud-alone-cpl` -- and it must be read from the **profile rows**, not a
verdict line. Baseline to preserve: monotonic d = 1 to 275 px, no interior local
maximum.

**One prediction on record, so it can be scored:** because the cap binds first
at the highest frequencies, I expect the ring to appear at **small d (2-6 px)**
and to appear in **green before red or blue**, since green carries the most
signal power and therefore the least regularisation. If it shows up first in
chroma at large d instead, my model of this operator is wrong again and the
strength question should come back to me before anyone ships it.

### 25.5 What I am NOT claiming

The overshoot guard is **NOT RUN**. 24.1 passed it trivially because an
operator that does not execute cannot put a maximum into a profile, and I am not
recording that as a pass. `restore.rs` still has no independent read; V-RESTORE
is outstanding, and 24.2 was a defect in the wiring I wrote around the module,
not evidence about the module.

## 26. The `SonyFNumber2` lead is CLOSED. The aligner fits magnification per frame, and the held-out error refutes the premise.

Cheap check first, as ORCH asked. `experiments/BUILD-SHARP/src/align_scale_span.py`,
read straight off the sidecar the 205-frame `flower-bud-alone-cpl` merge actually
used (`flower-bud-alone-cpl-4c58ad95fe89ce86.warpmap.txt`).

### 26.1 Item 4 answered: magnification is a fitted parameter of the warp

The aligner's per-frame transform is a `Similarity`, and
`SimilarityParams::g` (`align.rs:238-241`) is documented as *"Scale minus one.
`+0.01` is a 1% magnification."* Magnification is **not** something a separate
ladder has to contain; it is solved for per frame, alongside translation and
rotation, in the bundle adjustment.

Worth recording because it is what made the lead plausible: **"scale ladder" is
overloaded in this repository.** `photometric.rs:33` uses it for a per-frame
*gain* ladder, `align.rs:556` for the coarse *decimation* ladder of the search
pyramid, and `edgeaware.rs:763` for a multi-scale selection ladder. None of the
three is the magnification model.

### 26.2 What the aligner actually fitted, MEASURED

| quantity | value |
| --- | --- |
| placements parsed | 205 (frames 0..204) |
| merge plane | 3520 x 2344, half-diagonal **2115 px** |
| fitted scale, min | 0.99991182 |
| fitted scale, max | 1.00010753 |
| **fitted span** | **0.00019572 = 0.0196 %** |
| span as corner displacement | **0.41 px** |
| held-out error (sidecar header) | **0.3519 px** |

**The null passes and it could have failed.** If the aligner did not fit scale,
every `|a|` would be exactly 1.0. Measured: **205 distinct values**, exactly
**one** equal to 1.0 — frame 102, which the header names as the reference. The
instrument was capable of reporting "no scale is fitted" and did not.

### 26.3 The premise is arithmetically impossible, and the arbiter is the held-out error

The relayed claim was ~13% magnification drift, essentially unmodelled. The
decisive quantity is not the fitted span — a small fitted span is equally
consistent with "the aligner missed a big ramp" and "the ramp is genuinely
small". It is the **held-out error**: 0.3519 px, measured on frames excluded
from the fit, which is precisely a bound on unmodelled misregistration.

A 13% unmodelled magnification ramp would put the extreme frames ~275 px apart
at this plane's half-diagonal (ORCH's ~450 px used r = 3500; the merge plane is
binned, so the true half-diagonal is 2115 px — the conclusion is unchanged and
the correction makes it no better for the claim). **A 275 px unmodelled error
cannot coexist with a 0.3519 px held-out error.** The two are not in tension;
they are contradictory.

ORCH reached the same place from the pictures — `bee-3-cpl` resolving antenna
sensory pits is not the output of a stack misregistered by hundreds of pixels —
and the sidecar agrees with the pictures.

So the error is in item 1 or item 2 of ORCH's list (the EXIF-to-magnification
conversion, or a silhouette measurement whose "independent agreement" was never
shown capable of disagreeing), **not item 4**. Item 4's answer is that the
ladder is essentially the whole story and it is correctly small. **I am not
chasing items 1-2**; the lead is closed for the purpose it was routed to me for,
which was whether registration is a hidden third contributor to softness. It is
not.

### 26.4 What this does and does not exonerate

**MEASURED:** residual scale-induced displacement across the whole 205-frame
bracket is 0.41 px at the extreme corner, and total held-out registration error
is 0.3519 px. Sub-pixel. Registration is **not** a third amplitude-loss term
hiding behind the gather and demosaic numbers.

**NOT claimed:** that 0.35 px is free. It is not zero, and a sub-pixel residual
still costs amplitude through the same phase-averaged kernel priced in §20 —
that cost is already inside the 0.6978 gather figure rather than additional to
it. And this is one stack; the finding is that the *model* absorbs
magnification, which generalises, rather than that every stack registers to
0.35 px, which does not.

## 27. Demosaic vs gather: composition, and a 1.30x recoverable shortfall

Scope note: this section is the whole of my remaining assignment. It answers
ORCH's two questions -- do the two losses compose, and is the demosaic loss
correctable -- and it corrects a unit error of my own in s22.4.

Instrument: `experiments/BUILD-SHARP/src/compose_price.py`, driving the shipped
`strehl_core::demosaic` through `crates/strehl-core/examples/demosaic-plane.rs`
and the shipped `Resampler::sample` gather. Green channel, per-axis horizontal,
gather phases averaged over a uniform grid.

### 27.1 The unit error in s22.4, and its size

s22.4 multiplied a gather MTF quoted at f = 0.35 by a demosaic MTF quoted at
f = 0.35 and reported the product. Those are two different physical
frequencies. The gather runs on CFA planes at half sensor resolution, so its
argument is cycles per CFA sample; the demosaic runs on the mosaic, so its
argument is cycles per sensor pixel. **CFA f = 0.35 is sensor f = 0.175.** The
s22.4 product is withdrawn.

Everything below is in **one variable: cycles per SENSOR pixel**, per-axis.

### 27.2 Composition -- MEASURED, and they do multiply

| f (cyc/sensor px) | D (demosaic) | G (gather) | GD (both) | G*D | GD/(G*D) |
|---|---|---|---|---|---|
| 0.10 | 1.0270 | 0.9819 | 0.9872 | 1.0084 | 0.9790 |
| 0.15 | 1.0395 | 0.8690 | 0.9397 | 0.9034 | 1.0402 |
| 0.20 | 1.0604 | 0.7434 | 0.7889 | 0.7883 | 1.0008 |
| 0.25 | 1.0000 | 0.6230 | 0.6230 | 0.6230 | 1.0000 |
| 0.30 | 0.9058 | 0.7434 | 0.6668 | 0.6734 | 0.9903 |
| 0.35 | 0.7713 | 0.8690 | 0.6913 | 0.6702 | 1.0314 |
| 0.40 | 0.6228 | 0.9819 | 0.6112 | 0.6115 | 0.9996 |

`GD/(G*D)` stays inside [0.979, 1.040] with a median of 1.000. **The two
losses compose as the naive product**, to within 4% worst case and 1% typical.
Neither masks the other. That is the answer to ORCH's second question.

Commissioning. The **null** is an integer-shift gather (phase 0): G must be
exactly 1 and GD must equal D. Measured `G = 1.000000` and `GD - D = 0.00e+00`
at both f = 0.20 and f = 0.35 -- exact, not approximate. The **potency** arm is
the bilinear/Malvar contrast in 27.4, which the instrument separates by 1.27x
at f = 0.35, so a real difference in the demosaic does move it.

### 27.3 G is not monotone in sensor units, and this rescales the gather claim

The G column falls to a minimum of **0.6230 at f = 0.25** and comes back up to
0.9819 at f = 0.40. That is not an error. A CFA plane samples at spacing 2, so
sensor frequency f is CFA frequency 2f, and above CFA Nyquist the response
folds: sensor 0.25 is CFA 0.50 (Catmull-Rom MTF 0.62500, measured 0.6230);
sensor 0.35 is CFA 0.70, which folds to 0.30 (CR 0.8892, measured 0.8690).

Consequence, and BUILD-WIRE needs this before it picks a strength: **at sensor
f = 0.35 the gather costs 13.1%, not the 30% implied by 1/0.6978 = 1.43x.**
The 1.43x figure is a 2-D CFA-plane number at CFA f = 0.35, i.e. sensor
f = 0.175 -- a feature twice as coarse as the label suggests. Restoration sized
to recover 1.43x at fine detail is oversized by roughly 1.24x, and an oversized
Wiener FIR at a silhouette is a halo.

### 27.4 Correctability -- MEASURED, and the shortfall is reconstruction, not information

Green is sampled on a quincunx lattice, whose support is the diamond
|fx| + |fy| <= 0.5. A horizontal f = 0.35 is **inside** that support, so the
amplitude is present in the samples. An oracle least-squares fit to the
quincunx green samples alone:

| f | Malvar (shipped) | bilinear | ceiling | headroom |
|---|---|---|---|---|
| 0.20 | 1.0604 | 0.8342 | 1.0000 | 0.943 |
| 0.25 | 1.0000 | 0.7500 | 1.0000 | 1.000 |
| 0.30 | 0.9058 | 0.6796 | 1.0000 | 1.104 |
| 0.35 | 0.7713 | 0.6078 | 1.0000 | **1.297** |
| 0.40 | 0.6228 | 0.5366 | 1.0000 | **1.606** |
| 0.45 | 0.5385 | 0.5145 | 1.0000 | 1.857 |

The ceiling is exactly 1.0000 at every frequency. **The shipped demosaic's loss
at f = 0.35 is a reconstruction shortfall of 1.297x, not destroyed
information.** At sensor f = 0.35 the demosaic (0.7713) is the **larger** of the
two losses, bigger than the gather's 0.8690.

ARGUED, and the limit of this result: the ceiling arm is an oracle. It fits a
known frequency, noiseless, globally, on a purely horizontal grating. It bounds
what is *available* in the samples; it does not prove an implementable filter
reaches it, and noise will cut into it. Treat 1.297x as a ceiling, not a
forecast.

### 27.5 Recommendation for BUILD-WIRE

**Which interpolator.** Directional green interpolation -- the AHD / DLMMSE /
LMMSE class. The reason is specific rather than generic: Malvar is a fixed 5x5
linear filter whose passband is a square, so it cannot use the corners of the
quincunx diamond. A directional method interpolates green *along* the locally
flat direction, which is exactly the operation that harvests the diamond. The
1.27x that bilinear-to-Malvar already buys (27.4) is evidence that this axis
has real spread and is not saturated.

**What it costs.** Effectively nothing in context. The demosaic runs **once**,
on the merged CFA planes at write time, not per frame -- a 205-frame stack
spends ~200 s in alignment and merge. A directional demosaic is single-digit
multiples of a Malvar pass on one image.

**What it buys at f = 0.35.** Up to 1.297x per-axis on green, bounded above by
the ceiling in 27.4 and reduced by noise. Unlike restore it is an
*interpolation* rather than a *deconvolution*: it does not divide by a small
number, so it does not carry restore's failure mode. V-RESTORE measured restore
pushing 3.75% of pixels up to 7107 DN outside their own input support; a
directional demosaic has negative taps like Malvar already does, but no
noise-amplifying denominator. Lower overshoot risk, not zero.

**Landing-blocker for the restore strength.** Because the losses multiply
(27.2), the delivered loss at sensor f = 0.35 is 0.6913 and it factors cleanly:
0.7713 demosaic x 0.8690 gather. Restore corrects the **gather** term only.
Sizing it at 1/0.6913 = 1.45x would be correcting the demosaic term with a
deconvolution as well, and that is double-counting into the halo. The gather
term alone at sensor f = 0.35 asks for **1.15x**.

## 28. Units of the f column, and what actually owns the top of the band

ORCH relayed V-bestframe's question with a two-branch dichotomy: is my `f`
column in output pixels (in which case I under-price the gather) or in
gather-plane samples (in which case `f = 0.35` is really `0.175`)? **Neither.
The answer is a third branch and it is settled by construction in my own
harness, not by argument.**

### 28.1 The units, with the lines that fix them

**`f` is cycles per OUTPUT pixel.** Four lines of
`experiments/BUILD-SHARP/src/compose_price.py` pin it, and they are the same
four lines that make the half-resolution plane a modelled feature rather than
an oversight:

| line | what it fixes |
|---|---|
| `:114-117` | `truth()` builds the grating on `np.arange(N)` at **full** resolution: `f` is cycles per output pixel by construction, before any CFA structure exists |
| `:120-127` | `cfa_planes()` takes `full[0::2, 0::2]` and siblings -- the four sub-lattices at **half** resolution, which is V-bestframe's stride-2 deinterleave |
| `:91-100` | `resample_x()` rolls the **plane**, so gather taps sit one plane sample = **two output pixels** apart, which is V-bestframe's `2 * px` |
| `:103-111` | `amp_at(..., step=2)` multiplies the sample index by 2 when reading a plane, converting plane indices back to output-pixel coordinates so one `f` means one thing throughout |

So the `G` column of the s27 table **already contains** the half-resolution
gather. It is not under-priced, and `f = 0.35` is genuinely 0.35 cycles per
output pixel -- **2.86 output pixels per cycle**, not six.

**Restated with units and dimensionality attached, as asked:** the shipped
demosaic's green loss is **22.9% (D = 0.7713) at f = 0.35 cycles per OUTPUT
pixel, per-axis horizontal**. The 23.3% I reported earlier is the same quantity
from the earlier harness; the 0.4 pp is harness difference, not a unit change.
Both were already output-pixel, per-axis. **The two-dimensional figure is not
measured and cannot be obtained by squaring**, because Malvar is a
non-separable 5x5 cross-channel filter.

### 28.2 Independent corroboration of the half-resolution fact

I did not know V-bestframe's result when s27 was measured, and the s27 table
contains its fingerprint. `G` is non-monotone: it falls to a minimum of
**0.6230 at f = 0.25** and rises again. `f_out = 0.25` is exactly the gather
plane's Nyquist under `grid_factor = 2.0`, and Catmull-Rom's MTF at plane
Nyquist is **0.62500**. Measured 0.6230 against predicted 0.62500, from a
harness that was never told where the fold should land. Two routes, one number.

### 28.3 Where I must correct ORCH -- MEASURED

ORCH's framing: *"the plane cannot represent detail there; whatever exists
above f_out = 0.25 was manufactured by the demosaic interpolator rather than
attenuated by the resampler."*

**Both halves are refuted by measurement already in s27.4, and the correction
matters because it decides whether the headroom is real.**

1. **Not manufactured.** G1 and G2 are two planes offset by one pixel -- a
   quincunx, whose support is the diamond |fx| + |fy| <= 0.5. Their individual
   aliases are in antiphase and cancel on recombination. The oracle fit to the
   **green samples alone** returns exactly **1.0000 at f_out = 0.35, 0.40 and
   0.45** (s27.4). If that band were manufactured by the interpolator, a fit to
   the samples would return approximately zero. It returns unity. The
   information is in the sensor data.
2. **The gather is still a limiter up there, just at the folded frequency.**
   Measured `G(0.35) = 0.8690`; Catmull-Rom at the folded plane frequency
   (2 x 0.35 -> 0.30) is 0.8892. Agrees to 2%. A 13.1% attenuation is not
   "not the limiter at all".

**ORCH's operational conclusion is nonetheless correct, for a different and
stronger reason.** Restoration as wired acts on the four CFA planes
**separately** (R, G1, G2, B, before interleave -- `merge_cmd.rs`, `write_merged`).
A per-plane filter is defined only up to that plane's own Nyquist,
`f_out = 0.25`. It therefore **structurally cannot reach the quincunx
recombination band at all**, whatever strength it is given. The top half of the
output band is the demosaic's alone -- not because the detail up there is fake,
but because no per-plane operator can address it.

### 28.4 The interpolator, scoped to the band that is actually mine

**What is available above f_out = 0.25** (s27.4, oracle vs shipped Malvar):
1.104x at 0.30, **1.297x at 0.35**, 1.606x at 0.40, 1.857x at 0.45. Real, and
rising exactly through the scales the owner calls soft.

**What it costs in wall-clock -- MEASURED, and the 299-frame count is a red
herring.** The demosaic runs **once, at write time, on the merged CFA planes**,
not per frame. Timed at true gallery resolution 7032 x 4688 on the shipped
`demosaic-plane` example, best of three: **Malvar 1.284 s, bilinear 0.860 s**,
and both figures include 132 MB of read and 396 MB of write, so the kernel
itself is a fraction of a second. A 299-frame stack spends minutes in alignment
and merge. **A directional demosaic 20x the cost of Malvar would add ~25 s to a
multi-minute render** -- under 1% of wall clock. Cost is not a consideration
here and should not be treated as one.

### 28.5 Reconciling my 1.30x with V-bestframe's 0.4-5.4% ladder

These look incompatible and are not. V-bestframe scored LINEAR 0.946, VNG
0.972, PPG 0.985, DCB 0.996 against AHD -- a spread of a few percent, against
my 30% at f_out = 0.35. The reconciliation is **band dilution**, and it is
quantitative rather than hand-waved: my measured bilinear/Malvar ratio at
f_out = 0.35 is 0.6078 / 0.7713 = **0.788**, whereas V-bestframe's
LINEAR-vs-AHD is **0.946**. A comparison of the same class, restricted to the
top band, is 3.9x further from unity than the aggregate. That is the signature
of a whole-image aggregate diluting a gain that lives only in the top of the
spectrum.

**Consequence, and it is the practical one: an aggregate demosaic score is the
wrong selection metric for this project.** It will rank interpolators by their
behaviour on the bulk of the spectrum, where they barely differ, and be nearly
blind to the band the owner is complaining about. ARGUED, but it follows
directly from the two measured numbers above. **Select on high-band response.**

**Recommendation, unchanged in direction and now bounded on both sides:**
directional green interpolation (AHD / DLMMSE / DCB class). Ceiling 1.297x at
f_out = 0.35 (oracle, so an upper bound, and noise will cut it); cost under 1%
of render wall-clock; no noise-amplifying denominator, hence not restore's
failure mode -- against which V-RESTORE has measured 3.75% of pixels pushed
outside their own input support by up to 7107 DN.

## 29. Response to the cross-build and hull-clamp warnings

### 29.1 Cross-build -- checked, not asserted; no conclusion moves

Every arm in s27 and s28 came from **one** executable,
`pin-a2d5a811/.../demosaic-plane.exe`, SHA256 `77C058F9...D87A2`, and the
gather half is pure NumPy (`compose_price.py:91-100`) with no binary in it at
all. The scenes are synthetic, so no artefact rendered earlier tonight is
reused as a reference anywhere.

One exposure did exist and is now closed by measurement rather than by
argument. The **earlier** demosaic figure (s22's 23.3%) may have been run
against the worktree build, SHA256 `2766ECD7...56979`. I fed both binaries the
same input and compared per channel:

| arm | R | G | B |
|---|---|---|---|
| malvar | 0 | 0 | 0 |
| bilinear | 0 | 0 | 0 |

**Bit-identical on all three channels**, not merely on green. The comparison
was not vacuous: the two binaries have **different SHA256**, so a disagreement
was possible. The reason is structural -- the chromatic-aberration correction
BUILD-HULL found lives in `optics.rs` and is not on the `demosaic` path that
`demosaic-plane` exercises. **No cross-build contamination in any number I have
reported.**

### 29.2 Hull clamp -- one conclusion is now incomplete, and it is mine

Nothing in s27/s28 is invalidated: my instruments are synthetic and never enter
`pyramid.rs`, so the clamp is absent from both arms of every A/B I ran, and the
measured ratios stand as measured.

**But s27.5's factorisation is incomplete and I am flagging it rather than
letting it be read as total.** I wrote that the delivered loss at
f_out = 0.35 is 0.6913 and "factors cleanly: 0.7713 demosaic x 0.8690 gather".
That is the loss of the **resample-and-demosaic pixel path only**. If the
default hull clamp costs 15.5-18.9% of microcontrast on `coffee-bean`
(measured by BUILD-HULL, matched-pair, one binary, determinism null 0 DN), then
it is a **third multiplicand upstream of both of mine**, and the delivered
figure is worse than 0.6913 -- plausibly nearer 0.57 if the clamp cost carries
to this band, which I have not measured and will not, because it is owned.

Two consequences, both in the direction of my lane rather than against it:

1. **The absolute headroom is larger than s27 implies**, exactly as ORCH says.
   My 1.297x is a ceiling on the demosaic term alone and composes with whatever
   the clamp policy returns.
2. **The restore-strength bound in s27.5 is unchanged and still binding.**
   It was derived from the ratio 0.8690, and a common upstream factor divides
   out of a ratio. Restore still corrects the gather term only, still asks for
   **1.15x at f_out = 0.35**, and -- per s28.3 -- still cannot reach above
   f_out = 0.25 at any strength because it acts per CFA plane.

I have not touched `pyramid.rs` and have not re-derived the clamp cost.

## 30. s29.2 withdrawn -- s27.5's factorisation is complete after all

**s29.2 is withdrawn in full.** It rested on a hull-clamp cost of 15.5-18.9%
of microcontrast, since retracted by its own author (BUILD-HULL s17,
`ba5f234`) and independently refuted by V-HULLCOST (`6222142e`) at ~3.1%. The
measured position is that at the finest octave the clamp removes **0.29σ** on
`coffee-bean` and **0.42σ** on `flower-bud-alone` against the merge's own noise
floor -- less than the noise already present at every scale where detail lives.

Three corrections follow, and the middle one is a defect of mine rather than an
inherited one:

1. **s27.5's factorisation is complete, not incomplete.** The delivered loss at
   f_out = 0.35 is `0.7713 demosaic x 0.8690 gather = 0.6913`, and there is no
   third multiplicand at detail scale. The clamp is a base-octave tone
   operation -- confirmed by the corrected band shares, residual 45.14% against
   bands 0-1 at 16.8% -- so it does not sit in the band s27 measures.

2. **My "plausibly nearer 0.57" was an extrapolation and should not have been
   written.** The 15.5% I was given had been measured as an aggregate
   microcontrast figure; I carried it into a *specific band at a specific
   frequency* where it had never been measured, and produced a number by
   multiplication. Being sourced from a named agent made the input citable, not
   the extrapolation sound. **A number is only valid in the band it was
   measured in**, and that is the discipline I failed here, independently of
   the input turning out to be wrong.

3. **The headroom claim reverses.** s29.2 said the absolute headroom is larger
   than s27 implies because of a free 15% upstream. There is no free 15%. The
   demosaic's **1.297x at f_out = 0.35** (s27.4) is not competing with a larger
   free win sitting above it; on the current board it **is** the largest
   measured ring-free sharpness lever in the project.

Unchanged by any of this, because each was derived from a ratio or from
single-binary synthetic data: the restore bound of **1.15x at f_out = 0.35**,
restore's structural ceiling at **f_out = 0.25** (s28.3), the demosaic loss of
**22.9% at f_out = 0.35 cycles per output pixel, per-axis** (s28.1), and the
cross-build check in s29.1, which was bit-identical on all three channels
between two binaries of differing SHA256.

## 31. The directional demosaic was built, measured on the owner's own captures, and REJECTED. s27/s28's headline is refuted.

**Status: this section retracts my own headline.** ORCH asked me to ship a better
interpolator on the default path because I had told it the demosaic was the
largest measured ring-free sharpness lever on the board. I built it, rendered
it on two of the owner's real stacks, and it is a **regression**. The default
has been reverted to Malvar. This is the honest negative, with the numbers and
the pictures.

### 31.1 What was built

Malvar's green stencil at a red/blue site is

```
F_G = (G_l + G_r + G_u + G_d)/4 + (4K - K_ll - K_rr - K_uu - K_dd)/8
```

and the load-bearing algebraic fact behind s27.4's 1.297x is that this is
**exactly the arithmetic mean** of the two Hamilton-Adams directional
estimates

```
H = (G_l + G_r)/2 + (2K - K_ll - K_rr)/4
V = (G_u + G_d)/2 + (2K - K_uu - K_dd)/4
```

since (H + V)/2 = F_G identically. On a horizontal grating V is *exact* and H
is attenuated; averaging them therefore throws away half of an exact answer,
and that is where the measured 22.9% per-axis loss at f_out = 0.35 comes from.
Selecting the better direction instead of averaging recovers it: synthetically
the directional estimator scores > 0.97 where Malvar scores < 0.85.

The implementation is Hamilton-Adams green with chroma carried as colour
differences, in `crates/strehl-core/src/demosaic.rs`. It is retained behind
`STREHL_DEMOSAIC=directional` so that **one binary can render both arms** and
so that this measurement is reproducible; it is **not** the default.

### 31.2 The measurement that killed it

One binary, SHA256 `88DEABFF7406C6E44A585D0BF72E33CBF353CECCE6AD4A98F8AE058581DB45B9`,
both arms, shared alignment cache per subject, green plane only. Tiles of
128x128 ranked by the **Malvar** arm, so tile selection cannot be biased by the
arm under test. Ratios are directional / malvar; > 1 means the directional arm
has more.

| band | metric | `bee-3-cpl` | `tweezers-cpl` |
|---|---|---:|---:|
| flattest 5% -- out of focus, no detail exists to recover | mean gradient | **1.1512** | **1.0650** |
| | HF power | **1.5016** | **1.1698** |
| median 10% | mean gradient | 0.9988 | 0.9915 |
| | HF power | 1.0297 | 1.0314 |
| sharpest 5% -- detail sites | mean gradient | **0.9903** | **0.9831** |
| | HF power | 1.0259 | **0.9582** |

Read the two ends together, because either alone is ambiguous and the pair is
not. **Where there is nothing to recover, the directional arm adds up to 50% more
high-frequency power. Where the detail actually is, it delivers slightly
less.** That is the signature of an estimator manufacturing structure from
noise, and it is the exact failure the module header's property 1 was written
to prevent. The header was right and I overrode it.

`experiments/BUILD-SHARP/src/demosaic_noise_or_detail.py`.

### 31.3 The picture, which is worse than the number

This project's standing rule is to look at the crops as pictures, and here the
picture carries a finding the statistics did not. Crops in
`experiments/BUILD-SHARP/src/demosaic_crops.py`; both arms stretched with the
**same** black/white points taken from the malvar arm, so a visible difference
is a difference in the data and not in the normalisation. Non-vacuity was
asserted before looking: `max|malvar - directional|` on green is **4491 DN** on
`bee-3-cpl` and **7873 DN** on `tweezers-cpl`, so the arms genuinely differ.

- **Out-of-focus tile, `bee-3-cpl` (1408, 6656).** The malvar arm is smooth
  defocus carrying quincunx noise. The directional arm carries a **maze /
  labyrinth pattern** -- the classic directional-demosaic artifact, where the
  H-vs-V decision flips from pixel to pixel in the absence of a real gradient
  and the flips organise into connected walls. This is materially worse than
  the "+50% HF power" number suggests, because the added energy is
  **structured and correlated**, not white. Correlated false texture reads as
  detail to a viewer and survives sharpening, tone mapping and print. It is
  the same class of defect as the halo the owner complained about.
- **Detail tile, `bee-3-cpl` (3072, 5632)** -- hair and its specular
  highlights, the finest real structure in the frame. The two arms are
  **visually indistinguishable**. There is no recovered detail to weigh
  against the artifact above.

### 31.4 Ringing: checked, and not the reason for rejection

I say what I checked rather than that I checked. A ringing detector was built
and **commissioned before use**: null 0.0000 on an unmodified edge, and planted
overshoots of 5% and 15% recovered as **0.0500 and 0.1500 exactly**. It caught
five defects in itself that inspection had not:

1. a quantile edge threshold that degenerates when all edges share one
   amplitude, returning zero edges;
2. plateau windows placed on the transition, hiding overshoot inside the
   measured amplitude;
3. a **wrong plant** rather than a wrong detector -- overshoot planted where a
   soft sigmoid had not yet reached plateau, recovered as 1.85% of a 5% plant;
4. top-N-by-gradient admitting edge shoulders whose window straddles rather
   than spans the transition, which broke the null at n_cand = 40000; fixed by
   requiring a gradient local maximum;
5. division by a near-zero plateau difference on textured data, fixed with an
   amplitude floor and a **counted `rejected` partition**, so that a skipped
   edge cannot read as a passed one.

Result on real data: malvar p99 **10.7303**, directional **10.6058** on
`bee-3-cpl` -- the directional arm is very slightly *lower*. **The directional
green does not add classical edge overshoot.** Its artifact is the maze, not
the halo. The absolute values here remain inflated by textured plateaus and are
**not trustworthy in absolute terms**; only the malvar-vs-directional
comparison is, and that comparison exonerates it on ringing specifically.

So the rejection is not "it rings". It is "it manufactures structure where
there is none and recovers nothing where there is".

### 31.5 What this retracts

**s27.4 and s28 claimed the demosaic was the largest measured ring-free
sharpness lever in the project. That claim is refuted by contact with real
data and I withdraw it.**

The 1.297x was correctly measured and I stand by the synthetic number. What was
wrong was the inference from it. It was measured on a **full-contrast grating
at f_out = 0.35**, and the whole burden of s1 and s14 is that this optical path
**cannot deliver that stimulus**: at magnification 2.0 the MTF at Nyquist is
0.036 at f/5.6 and 0.000 beyond, and the marked f/11 the owner shoots is
effectively f/33. The directional estimator's advantage over Malvar exists
only where a strongly-oriented high-frequency edge exists to be detected. On
this rig, at those frequencies, **what is present is noise, and the estimator
duly oriented itself to the noise.**

This is the same error as s30, in a new place, and I should have seen it
coming: **a number is only valid in the band -- and on the stimulus -- it was
measured in.** In s30 I carried an aggregate figure into a specific band. Here
I carried a synthetic-stimulus figure onto an optical path that cannot produce
that stimulus. The correction is the same one and I am recording it as such.

### 31.6 Consequences for other lanes

- **BUILD-WIRE: do not deprioritise restore on my advice.** I told ORCH the
  demosaic was the better lever because it carried no overshoot risk where
  restore does. The demosaic lever is not there. Restore's overshoot cost
  (V-RESTORE: 7.82% 1-D, 16.25% 2-D, 3.75% of pixels outside their own input
  support) must now be weighed against a board on which no free ring-free
  alternative exists, not against a 1.297x that does not survive contact with
  the sensor.
- **Unchanged and still valid**, because they are ratios or structural facts
  rather than stimulus-dependent gains: composition measured at
  `GD/(G.D)` in [0.979, 1.040], median 1.000, i.e. **the gather loss and the
  demosaic loss multiply** (s27); `f` is **cycles per output pixel** (s28.1);
  the gather is non-monotone in output units with its minimum **0.6230 at
  f_out = 0.25** (s28.2); restore acts per CFA plane and therefore
  **structurally cannot reach above f_out = 0.25** at any strength (s28.3);
  restore's legitimate target is **1.15x at f_out = 0.35**.
- **The optics floor is now the live hypothesis for the residual softness**,
  which is item (e) of my original mandate. Selection cannot recover what the
  optics destroyed, a better interpolator cannot either, and this section is
  the measurement that says so on the owner's own pixels rather than in
  principle. The remaining levers are capture-side (s14) and reconstruction
  with a calibrated sigma (s13, s24 -- where the restoration was measured
  **inert** at the sigma^2 it was given, which is now the most valuable open
  thread on the board rather than a footnote to the demosaic).

### 31.7 State of the code

The default path is **Malvar, unchanged in behaviour**. This was verified
rather than asserted: rendering `tweezers-cpl` with no environment override
after the revert produced a file **byte-identical (MD5) to the malvar arm** and
**different from the directional arm**, so the check is non-vacuous. Test suite
**467 passed, 0 failed**.

One test needed care rather than widening. `a_linear_ramp_survives_exactly_in_
the_interior` regressed at margin 2 because the directional estimator has
support radius **3** against Malvar's 2. Rather than move the margin until the
test passed, it now *proves* the reason: Malvar exact at margin 2, directional
exact at margin 3, and the margin-2 ring asserted **inexact** with every
inexact pixel required to lie on that ring.

## 32. V-DEMOSAIC's defects, answered: three accepted, one closed negative by measurement, and s27.4's headroom column retracted

V-DEMOSAIC returned DEFECTS FOUND on s27/s28. **Three of the findings are
correct and I have reconfirmed two of them with my own instruments rather than
taking them on report.** One -- the suspected units collision, which was the only
item that could have been degrading shipped pixels -- is **closed negative by
measurement**. One item was already overtaken by s31.

Order below is ORCH's priority order, not the report's numbering.

### 32.1 The suspected units collision in `restore.rs`: MEASURED, and there is no defect

**Answer: there is no collision, in either mode, and the shipped path could not
exhibit one even if there were.**

The premise of the charge was that `design_fir`'s basis lags `k` index plane
samples while `cfg.gain`'s `f` is an output frequency. Reading the module
settles the convention differently: **`f` is cycles per sample of the array
being restored** -- the same array whose lags `k` index -- and `grid_factor`
converts that to gather-grid units **for the `gather_mtf` lookup only**
(`restore.rs:269`). Under that reading both modes are self-consistent:

- `grid_factor = 1.0`: the array is the CFA plane, which **is** the gather grid,
  so `f` needs no conversion. This is what the shipped path uses --
  `RestorePlan::config` hardcodes it at `restore.rs:1321` with the comment "the
  CFA planes ARE the gather grid", consumed at `merge_cmd.rs:6000-6001`.
- `grid_factor = 2.0`: the array is the demosaiced output, `f` is output
  cycles/px, and the gather loss is correctly looked up at `2f`.

But that is reading, and this project has been wrong from reading three times
tonight. So it was measured on the real Rust, through
`crates/strehl-core/examples/restore-plane.rs`, which calls `restore_plane`
itself -- no Python reimplementation that could only prove itself consistent.
Pure tones were planted at known frequencies of the restored array and the
realised gain measured. `experiments/BUILD-SHARP/src/restore_units.py`.

**The measurement scores two rival predictions, because reporting only the one
I expected would be the same defect as the ceiling arm in 32.2:**

```
H0 (no collision)  realised(phi) == fir_response(taps, phi)
H1 (collision)     realised(phi) == fir_response(taps, 2*phi)
```

| grid_factor | worst \|realised - H0\| | worst \|realised - H1\| | max separation H0 vs H1 | verdict |
|---|---:|---:|---:|---|
| 1.0 (shipped) | **0.00000** | 0.39401 | 0.39401 | H0 -- no collision |
| 2.0 (control) | **0.00000** | 0.41563 | 0.41563 | H0 -- no collision |

The separation column is what makes this evidence: the two hypotheses differ by
up to **0.416**, so the test could have reported a collision and did not.

A second, independent discriminator used the `roll_off` taper's zero rather
than the taps. At `grid_factor = 2.0` the excess gain is driven to exactly zero
at design `f = 0.5`, so if the applied axis were half the design axis, array
Nyquist would land on the **knee** -- maximum boost -- instead:

```
realised gain at array Nyquist      : 1.00133
predicted if applied axis IS design : 1.00133
predicted if applied axis is HALF   : 1.19971
```

At `grid_factor = 1.0` the same discriminator **reported itself VACUOUS** --
`knee()` returns 0.5, no taper engages, and the two predictions coincide at
1.43287. It is recorded here as vacuous rather than as a third pass, per the
project rule that a skipped check must not be readable as a passed one.

**Item routed to BUILD-WIRE, not fixed by me** (`restore.rs` is theirs): at the
shipped `grid_factor = 1.0`, `knee()` returns 0.5 and `roll_off` therefore
**never engages**. The correction runs untapered to the plane's Nyquist -- in
this harness `gain_at_nyquist` reached **1.43287**. That is a strength question
and possibly a correct one; it is stated because the anti-folding guard
`the_response_never_rises_above_the_knee` is written at `grid_factor = 2.0` and
so does not exercise the configuration that ships.

### 32.2 s27.4's ceiling arm is DEGENERATE, and the headroom column is retracted

**Accepted, and independently reconfirmed by my own instrument.**

First, the arithmetic, which needs no instrument at all. Dividing my own
published table:

```
f=0.20  malvar 1.0604  1/malvar 0.9430  published 0.943  |d| 0.00004
f=0.25  malvar 1.0000  1/malvar 1.0000  published 1.000  |d| 0.00000
f=0.30  malvar 0.9058  1/malvar 1.1040  published 1.104  |d| 0.00000
f=0.35  malvar 0.7713  1/malvar 1.2965  published 1.297  |d| 0.00049
f=0.40  malvar 0.6228  1/malvar 1.6057  published 1.606  |d| 0.00035
f=0.45  malvar 0.5385  1/malvar 1.8570  published 1.857  |d| 0.00001
rows where published headroom != 1/malvar : 0 of 6
```

**The headroom column is 1/D_malvar at every row.** The ceiling arm contributed
the constant 1.0000 and therefore contributed nothing. The column measures
Malvar's loss and then *asserts* that something could have recovered all of it.
That assertion was the thing requiring measurement and it is the one thing the
table does not contain.

Second, why the oracle is degenerate -- reconstructed and commissioned here
rather than taken on report (`experiments/BUILD-SHARP/src/ceiling_commission.py`).
Three cases whose answers are fixed by construction:

| case | fx, fy | \|fx\|+\|fy\| | truth | ceiling returns |
|---|---|---:|---|---:|
| in-diamond | 0.20 / 0.35 / 0.45, 0 | <= 0.45 | 1.0, recoverable | 1.0000 |
| **out-of-diamond** | 0.35,0.35 | 0.70 | **NOT 1.0 -- outside the support** | **1.0000** |
| **out-of-diamond** | 0.40,0.40 | 0.80 | **NOT 1.0** | **1.0000** |
| **out-of-diamond** | 0.45,0.30 | 0.75 | **NOT 1.0** | **1.0000** |
| alias pair | 0.35,0 + alias | -- | NOT 1.0 -- sum is ambiguous | 0.0000 |

**3 of 3 out-of-diamond cases return exactly unity where the information is
provably absent.** The quincunx support is |fx| + |fy| <= 0.5; at 0.70 the tone
is indistinguishable from its alias and no reconstruction can recover it. An
instrument that returns 1.0 there is fitting three parameters to 21,632 samples
at a *known* frequency and reporting the fit, not the information. And on the
alias pair -- where the truth is that the single-component amplitude is **not**
recoverable -- it returns 0.0000, so it is not merely optimistic, it is
uncorrelated with the answer.

**RETRACTED: the `ceiling` and `headroom` columns of s27.4, and every
downstream use of "1.297x" as a measured ceiling.** The `Malvar` and `bilinear`
columns stand; they are direct measurements of two real filters.

**RETRACTED: s28.3 point 1's inference.** It argued "if that band were
manufactured by the interpolator, a fit to the samples would return
approximately zero; it returns unity." It returns unity unconditionally for a
single tone. The conclusion may still be true -- the antiphase-cancellation
argument for G1/G2 is independent of the oracle and I still believe it -- but
**this measurement is not evidence for it** and I withdraw it as such.

**The rule, stated because I applied it to others' instruments tonight and not
to my own: an arm that returns the same value on every input has not been
commissioned.** Two statistics were killed by their own commissioning earlier
this session and I wrote the commissioning for both. This one I published
without it, and its constancy should have read as a symptom rather than a
result.

### 32.3 The factorisation was arithmetically inconsistent; corrected it is STRONGER

**Accepted.** s27.5 wrote `0.7713 x 0.8690 = 0.6703` and then equated the
product to `0.6913` in the same sentence -- a 3.1% mismatch inside a claim of
clean factorisation.

The root cause is a real defect in my estimator, and V-DEMOSAIC found it
exactly: `compose_price.py`'s `amp_at` projected **without removing DC**, against
a scene carrying a 0.5 pedestal, so Dirichlet leakage off the pedestal biased D,
G and GD by different amounts and manufactured an apparent interaction term. Its
sibling `demosaic_price.py:project` had always removed the mean; the two
estimators disagreed and I never compared them. Fixed at
`compose_price.py:amp_at`.

Corrected, per-axis, green, cycles per output pixel:

| f_out | D (demosaic) | G (gather) | GD | G*D | GD/(G*D) |
|---|---:|---:|---:|---:|---:|
| 0.10 | 1.0368 | 0.9707 | 1.0112 | 1.0064 | 1.0047 |
| 0.15 | 1.0596 | 0.8892 | 0.9435 | 0.9421 | 1.0014 |
| 0.20 | 1.0541 | 0.7388 | 0.7826 | 0.7787 | 1.0050 |
| 0.25 | 1.0000 | 0.6230 | 0.6230 | 0.6230 | 1.0000 |
| 0.30 | 0.8995 | 0.7388 | 0.6678 | 0.6645 | 1.0050 |
| **0.35** | **0.7660** | **0.8892** | **0.6820** | **0.6811** | **1.0014** |
| 0.40 | 0.6330 | 0.9707 | 0.6174 | 0.6145 | 1.0047 |

The null still passes exactly: an integer-shift gather gives `G = 1.000000` and
`GD - D = 0.00e+00` at both probe frequencies.

**Composition is much cleaner than published.** `GD/(G*D)` was `[0.979, 1.040]`,
a spread of 6.1 points; it is now `[1.0000, 1.0050]`, a spread of 0.50 points --
a **12x tightening**, and the residual is one-sided at +0.5%. I do **not**
reproduce V-DEMOSAIC's exact 1.0000 at all frequencies; my own number is
1.0014-1.0050 and I report mine. The losses multiply; the earlier claim
survives on better evidence than it was published with.

**Numbers that move, and every downstream user of them should update:**

| quantity | published | corrected |
|---|---:|---:|
| demosaic loss at f_out = 0.35, per-axis | 22.9% | **23.4%** (D = 0.7660) |
| gather loss at f_out = 0.35, per-axis | 13.1% | **11.1%** (G = 0.8892) |
| restore's legitimate target at f_out = 0.35 | 1.15x | **1.1246x** |
| delivered green at f_out = 0.35 | 0.6913 | **0.6820** |

An unlooked-for corroboration falls out of the corrected table: **G is now
symmetric about f_out = 0.25** -- 0.9707 at both 0.10 and 0.40, 0.8892 at both
0.15 and 0.35, 0.7388 at both 0.20 and 0.30. That is exactly the fold
`H(f) = H(0.5 - f)`, arriving from my own estimator, and it is the mechanism of
32.4 below. The corrected `G(0.35) = 0.8892` also lands on the Catmull-Rom
closed form at the folded frequency **exactly**, where s28.3 point 2 could only
claim agreement "to 2%" with the uncorrected 0.8690.

### 32.4 s28.3's "structural ceiling at f_out = 0.25" is FALSE. Correction routed to BUILD-WIRE.

**Accepted.** s28.3 concluded that a per-CFA-plane restoration "structurally
cannot reach the quincunx recombination band at all, whatever strength it is
given", and that "the top half of the output band is the demosaic's alone". I
gave that to BUILD-WIRE as a constraint on where restoration may legitimately
act. **It is wrong.**

The mechanism is the fold, and my own corrected table in 32.3 exhibits it. Plane
sample spacing is 2 output px, so an output frequency f appears on the plane at
2f; a real symmetric FIR is even and 1-periodic in plane cycles, hence

```
H_out(f) = H_out(0.5 - f)
```

A per-plane filter reaches f_out = 0.35 **through its 0.15 twin**. V-DEMOSAIC
measured a per-plane symmetric FIR, placed exactly where `merge_cmd.rs` runs
`restore_plane`, changing delivered f_out = 0.35 green amplitude by **1.2618x**,
matching the fold prediction H(0.30) = 1.2618 to four decimals.

**The defensible claim is non-selectivity, not unreachability:** f and 0.5 - f
necessarily receive identical gain, so a per-plane filter cannot boost
f_out = 0.35 without boosting f_out = 0.15 by exactly the same factor. That is a
real and severe constraint -- it is why a per-plane restoration cannot be tuned
to the band the owner is complaining about without equally amplifying a band
four times coarser -- but it is a different constraint from the one I stated,
and BUILD-WIRE should be working from it rather than from mine.

This also partly reverses s28's framing that the top half of the band belongs to
the interpolator alone. It does not; it belongs to the interpolator **and** to
whatever the per-plane filter does to its low-frequency twin.

### 32.5 s28.5 mischaracterised its comparand -- but the rule survives on better evidence than I gave it

**Accepted.** V-bestframe's 0.9462 is not "an aggregate demosaic score". It is a
Difference-of-Gaussians **band** statistic, `DoG(1,2)`, medianed over 352 tiles.
Measured, that band peaks at 0.153 cyc/px with half-max 0.072-0.269 and only
**3.3% of its power above 0.30**. So s28.5's phrase "nearly blind to the band in
complaint" is literally true -- 96.7% of the weight sits below it -- but the
**mechanism I gave was wrong**: it is a mis-centred passband, not whole-spectrum
aggregation. My "3.9x further from unity" also compared my synthetic
bilinear-vs-Malvar against their real LINEAR-vs-AHD: different pair, different
data, different band. Apples-to-apples on the same real tiles it is **1.37x**.

**The rule is nonetheless earned, by a sign flip rather than by a ratio:**

| statistic | bilinear/malvar | ha/malvar |
|---|---:|---:|
| V-bestframe's exact DoG(1,2) | 0.8746 | **0.9897 -- HA scores WORSE** |
| truth-referenced 0.30-0.40 wedge | 0.8293 | **1.0966 -- HA 9.7% BETTER** |

A DoG-style statistic would **reject** the candidate that a band-correct
statistic would **select**. That is far stronger than any ratio, and it is
directly actionable: any demosaic selection made on a DoG-style statistic
anywhere in this project is choosing on a band nobody is complaining about.

**And there is a second lesson in that table which is mine, not V-DEMOSAIC's,
and which s31 supplies.** The band-correct wedge selected Hamilton-Adams at
1.0966 -- and s31 then measured HA on the owner's real captures and found it
delivers **nothing** at detail sites while adding maze artifacts in defocus.
So the wedge was right about the band and still wrong about the picture.
**Measuring in the correct band is necessary but not sufficient; the stimulus
has to exist in the real data too.** That is the s30/s31 rule extended one step,
and it is the single most transferable thing in this section.

### 32.6 The s27.4 generator

**Accepted with a correction of fact.** `demosaic_price.py` **is** committed, at
`f1bc28d8`, and contains a `ceiling_arm` -- but that is the **red** ceiling
(red lattice, period 2) from s22, not the green quincunx oracle of s27.4. The
green oracle is genuinely not in the repository, and V-DEMOSAIC is right that
s27.4 is not reproducible from it.

I am not resurrecting it. The column it produced is retracted in 32.2, and
committing a degenerate generator would invite someone to re-run it. What is
committed instead is `ceiling_commission.py`, which reconstructs the oracle
exactly as s27.4 describes it and **demonstrates why its output must not be
used** -- the instrument that should have existed before the table was
published.

### 32.7 Hamilton-Adams: already rejected before the report arrived, and V-DEMOSAIC's data strengthens the rejection

V-DEMOSAIC measured a tree that had moved. The "+286 uncommitted lines of
Hamilton-Adams green" were landed as the default in `d67fe13b` and then
**reverted in `0c236d85`**, before this report was routed to me. `demosaic.rs`
is clean, the default is Malvar, and the revert was verified by rendering rather
than asserted: with no environment override the output is **byte-identical
(MD5)** to the malvar arm and **differs** from the directional arm, so the check
is not vacuous.

Their evidence and mine agree and were reached independently, from opposite
directions:

| source | finding |
|---|---|
| V-DEMOSAIC, synthetic, off-axis | ha/malvar 1.304 at fy = 0, 1.002 at fy = 0.15, **0.650 at fy = 0.20** |
| V-DEMOSAIC, 8 real stacks | mean **1.099**, median 1.119, range **0.991**-1.161; **1.045** over all orientations |
| BUILD-SHARP s31, 2 real stacks | **no gain at detail sites** (0.9903, 0.9831 gradient); **+50% HF power in defocus**; maze artifacts visible in the crop |

A synthetic advantage that is 1.304x on-axis, 0.650x off-axis and 1.045x over
all orientations is exactly what would deliver nothing on a real subject whose
edges point in every direction -- which is what s31 measured on the picture.
**No guard is needed, because it is not landing.** The one-line answer to
"should it land with a per-orientation characterisation" is no: at 1.045x over
all orientations it is not worth a maze artifact, and the maze is not a
frequency-domain cost that a characterisation would have exposed.

The moving-SHA256 note is mine and is accepted: `demosaic.rs` changed twice
under V-DEMOSAIC. It is now landed and clean.

### 32.8 Net effect on the board

**Dead**: the 1.297x ceiling and every headroom figure derived from it; s28.3's
structural ceiling at f_out = 0.25; s28.5's aggregation mechanism and its 3.9x;
Hamilton-Adams as a shipping candidate.

**Alive and now better founded**: the losses multiply, with the residual
interaction cut 12x; D = 0.7660 and G = 0.8892 at f_out = 0.35; restore's target
of **1.1246x**; the units of the f column; the non-selectivity constraint on any
per-plane restoration; and the rule that a demosaic must not be selected on a
DoG-style statistic.

**Unchanged**: s31's conclusion. The demosaic is not the sharpness lever this
project needs, and with the ceiling retracted there is no longer even a
synthetic number claiming it might be. The binding constraint at the scales the
owner calls soft remains the **optics floor**, and the most valuable open thread
remains s24's restoration measured **inert** at the sigma^2 it was given.

## 33. s24 revisited: the restoration is not inert, it is subject-dependent

ORCH's brief said the restoration is "shipped, enabled, and doing nothing" and
asked me to establish or refute inertness on real subjects at the shipped
configuration. Three of those four words turn out to be wrong, and the fourth is
wrong on half the subjects tested.

Everything below is one pinned binary,
`BD5EB01318F98162998FCF0F0374EB344FC4AB0FAD19258B96A6ADEB60A6109F`, with a
shared alignment cache per subject, rendered
`--resampler catmull-rom --demosaic --pyramid-gate 4.5`.

### 33.1 First correction: it is not enabled

`restore.rs:1228` gates the whole path on `STREHL_RESTORE`, and
`gain_cap_from_env` returns `None` when the variable is absent. **The shipped
default is OFF.** Nothing in a default render reaches `restore_plane` at all, so
"a correction that is shipped, enabled, and doing nothing" describes a
configuration that does not exist. It is a flag that is off. That is a weaker
problem than the one I was sent to fix, and it should be said before any number.

### 33.2 The inertness replicates -- and the switch is proved live

On `112MSDCF` (79 frames), restore ON at the calibrated sigma^2 is
**byte-identical** to restore OFF:

| arm | MD5 |
|---|---|
| restore OFF (shipped default) | `ED0F92649C19C97B2E93757979D80FE6` |
| restore ON, cap 4.0, calibrated sigma^2 | `ED0F92649C19C97B2E93757979D80FE6` |

s24 reached the same verdict on `flower-bud-alone-cpl`, so this is a
replication on a second subject and a later tree.

**But s24 proved the flag "fires" only from its own log, and a log line is not a
pixel.** Byte-identity is equally consistent with a switch that is not wired at
all, which is the exact failure `merge --help` warns about in its own text. So
before reading the identity as a result I made the switch change the picture:

| control | result |
|---|---|
| cap 4.0, `STREHL_RESTORE_SIGMA=0.000001` | MD5 `0997FC08...`, **changed** |

The switch is live. The inertness is a property of the arithmetic, not of the
wiring. Banner at the calibrated value, all four planes: `max gain 1.0000 (2-D
1.0000), at Nyquist 1.0000, recovered 0.0000`.

### 33.3 Second correction, and it refutes s24.4's own proposed fix

s24.4 named the cause as sigma^2 -- a single frame's variance handed to a
205-frame merge -- and proposed the merged plane's noise as the fix. The corpus
records the gated mean at **0.534x noise in amplitude**, which is **0.285x in
variance**. So s24.4's fix is worth a factor of about 3.5x.

The sweep measures where inertness actually breaks. `STREHL_RESTORE_SIGMA`
scales the variance linearly (banner: 221.1, 110.6, 55.3, 22.1 DN^2 at 1.0,
0.5, 0.25, 0.1), so the scale column is directly comparable to 0.285:

| sigma^2 scale | result | max gain (1-D) | 2-D | recovered |
|---|---|---:|---:|---:|
| 1.0 (shipped) | INERT, byte-identical | 1.0000 | 1.0000 | 0.0000 |
| 0.5 | INERT, byte-identical | 1.0000 | 1.0000 | 0.0000 |
| **0.285 (s24.4's fix)** | **falls between two measured-inert points** | -- | -- | -- |
| 0.25 | INERT, byte-identical | 1.0000 | 1.0000 | 0.0000 |
| 0.1 | changed | 1.0474 | 1.0970 | 0.1170 |
| 0.05 | changed | 1.1868 | 1.4086 | 0.4805 |
| 0.02 | changed | 1.4032 | 1.9689 | 0.7770 |
| 0.01 | changed | 1.4842 | 2.2028 | 0.8834 |

**The correct merged-plane sigma^2 does not wake the filter.** 0.285 is bracketed
above and below by arms measured byte-identical to OFF. Inertness breaks between
0.25 and 0.1, so the shipped sigma^2 is overstated by somewhere between **4x and
10x**, and s24.4's 3.5x does not reach it.

Worse for that fix: s24.4 wanted a per-pixel `n_eff` map, noting `n_eff`
approaches 1 on detail pixels where the single-frame variance is already
correct. A per-pixel map would therefore make the filter **more** inert exactly
where detail is. The direction of that fix is wrong on its own reasoning.

### 33.4 The other term is S, and the two corrections compose

Wiener has two inputs and s24 only audited one. `design_fir` takes S from
`power_at(r, f)`, a statistic of the **whole plane**. A macro frame is not
homogeneous. Measured on the delivered green plane, 400 tiles of 256x256:

| subject | band | plane mean | sharpest 5% | flattest 5% | sharp/mean |
|---|---|---:|---:|---:|---:|
| 112MSDCF | 0.19-0.29 | 1058.6 | 3880.1 | 15.2 | **3.67x** |
| 112MSDCF | 0.29-0.39 | 335.1 | 1096.4 | 7.3 | **3.27x** |
| tweezers-cpl | 0.19-0.29 | 29748.3 | 131950.4 | 8.2 | **4.44x** |
| tweezers-cpl | 0.29-0.39 | 2996.1 | 13183.3 | 7.7 | **4.40x** |

I have to correct my own framing here before using this. I first wrote that the
whole-plane mean is "dominated by background". **It is not** -- the mean sits
about 70x *above* the flattest 5%, not near it. The distribution is heavy-tailed
and the defensible claim is narrower: **the whole-plane fit underestimates the
detail population by 3.3x to 4.4x.**

Composed with the sigma^2 error, that is `3.5 x 3.4 = 11.9x` on 112MSDCF --
equivalent to a sigma^2 scale of about 0.084, which lands on the firing side of
the measured 0.1 threshold. **Neither correction alone crosses it; together they
do.** That is the answer to ORCH's question 2, and it is none of the four
candidates offered: it is not miscalibration alone, not the wrong stage, and not
correct-but-small. It is two compounding errors in the same criterion.

The caveat that bounds this: these powers are measured on the delivered green
plane, not the pre-restore CFA plane `power_at` actually sees, so the levels are
not the levels. The quantity read is the **ratio between tile populations**,
which is a property of the scene's layout. Instrumenting `power_at` directly
needs a hook in a file I do not own.

### 33.5 The finding that overturns the assignment: inertness is subject-dependent

I registered this prediction before rendering it: if S is estimated over the
whole plane, then a bright subject that fills the frame with in-focus structure
should have a far larger whole-plane S and should be **less** inert at the
shipped sigma^2. `tweezers-cpl` is that subject; `112MSDCF` is dendrites on
black.

**Confirmed.** Same binary, same flags, shipped sigma^2 scale 1.0:

| subject | mean DN | sigma^2 DN^2 | shipped-sigma result | max gain | recovered |
|---|---:|---:|---|---:|---:|
| 112MSDCF | 191.4 | 221.1 | **INERT, byte-identical** | 1.0000 | 0.0000 |
| tweezers-cpl | 2486.6 | 570.2 | **changed, 70.2% of pixels** | 1.0739 | 0.1868 |

The mechanism is quantitative, not hand-waving: tweezers' whole-plane S in band
1 is **28x** higher (29748 vs 1059) while its sigma^2 is only **2.6x** higher
(570.2 vs 221.1), so `S/sigma^2` is about **11x** more favourable. The Wiener
criterion is doing exactly what it should; the subjects differ.

**So "the restoration is MEASURED INERT" is not a property of the restoration.**
s24 measured one subject and I generalised it, ORCH inherited the
generalisation, and it survived until a second subject was tried. This is the
band rule again one level up, and I am recording it in that form: **a number is
only valid on the subject population it was measured on.**

### 33.6 What it buys where it fires, and why that closes nothing

`tweezers-cpl` at the shipped sigma^2 is the only arm in this section that is
both non-inert and honestly configured, so it is the only arm with a shipping
claim. Amplitude ON/OFF, tiles ranked by the OFF arm:

| population | 0.19-0.29 | 0.29-0.39 |
|---|---:|---:|
| flattest 5% (no detail present) | 1.0484 | **1.0550** |
| median 10% | 1.0508 | 1.0483 |
| sharpest 5% (detail sites) | 1.0496 | **1.0485** |

Two things follow, and both are negative.

**It is not detail-selective, and it cannot be.** `restore_plane` applies one
symmetric FIR to the whole plane: it is linear and shift-invariant, so it has no
way to know where detail is. The measurement agrees to within noise, and on this
subject the flattest 5% gains **more** than the sharpest 5% in the upper band
(1.0550 against 1.0485). Whatever it adds in defocus is noise, because there is
nothing else there.

**It does not close the head-to-head deficit.** That gap needs 1.20x-1.31x in
these bands. This delivers about **1.05x**. Even the 50x-understated arm reaches
only 1.36x while amplifying defocus by the same factor. **Restore is not the
lever for the comparator deficit** and should not be sold to ORCH as one.

### 33.7 Ringing: a paired detector, commissioned, and what it says

`demosaic_ab.edge_overshoot` picks its edge population from the image handed to
it. Run independently on two arms that is a confound -- a sharper arm produces
different gradient peaks, so the two runs measure different edges. I built a
paired variant (`restore_ring.py`) that chooses sites and the amplitude floor
**once from the OFF arm** and measures the same profiles in every arm.

New code, so it is commissioned before it is read:

```
NULL  (arm IS the reference)   max |d| = 0.000000   PASS
PLANT a=0.05  recovered median = 0.0500   PASS
PLANT a=0.15  recovered median = 0.1500   PASS
PLANT a=0.30  recovered median = 0.3000   PASS
```

The plant is calibrated, not merely positive: `[-a, 1+2a, -a]` places exactly
`a*A` beyond the plateau of an ideal step, so recovery of `a` itself is the
demand.

`tweezers-cpl`, the dark-groove-on-bright-metal geometry ORCH named:

| arm | paired edges | worse | d p99 | max d |
|---|---:|---:|---:|---:|
| OFF (null) | 29382 | **0.0000** | 0.0000 | 0.0000 |
| shipped sigma^2 | 29265 | 0.7036 | 0.0504 | 6.6534 |
| sigma^2 x 0.05 | 28947 | 0.7131 | 0.0795 | 10.4219 |
| sigma^2 x 0.02 | 28900 | 0.7107 | 0.1206 | 13.0766 |

`worse` is the fraction of paired edges overshooting more than the reference; a
pixel shuffle gives 0.5. **Every firing arm sits at 0.70-0.71**, and `d p99`
rises monotonically with aggressiveness. The restoration does increase edge
overshoot on the majority of real edges.

**I am not reading the absolute p99 (14.7) as an overshoot fraction.** Real
subjects have no true plateaux, so that denominator is unreliable -- a standing
caveat in this document and the reason the detector was built paired. Only the
paired columns are read.

### 33.8 Looking at the pictures, which is the part that decides it

s31 is why this section exists: there the statistic said +50% HF power and the
picture said maze artifact, and the picture was right. Crop sites are chosen
from the **OFF** arm so no arm picks the crop that flatters it, and both halves
are stretched with the same window.

- **Shipped sigma^2, tweezers grooves**: marginally crisper, grooves slightly
  better separated. **No visible rim, no halo.** Consistent with gain 1.0739.
- **Shipped sigma^2, defocused region**: essentially indistinguishable.
- **sigma^2 x 0.05, grooves and 112MSDCF dendrites**: a real and visible acuity
  gain. Filaments separate that were merged; speculars tighten. **No maze.**
  This is not the s31 failure mode.
- **sigma^2 x 0.05, defocused region**: **a pronounced pixel-level crosshatch**
  that the OFF arm does not have. This is the hard finding of the section.

That crosshatch is diagnostic, not cosmetic. The banner for that arm reads `at
Nyquist 1.5189` -- **full gain at plane Nyquist with no taper** -- and a
per-CFA-plane filter at full gain at plane Nyquist is precisely how a
checkerboard is manufactured. It is the visible consequence of the `roll_off`
finding already routed to BUILD-WIRE: at the shipped `grid_factor = 1.0`,
`knee()` returns 0.5 and `roll_off` never engages, and the anti-folding guard
that would catch it is written at gf = 2.0 and does not exercise what ships.

**The picture found the same defect the code reading found, independently.**

### 33.9 Recommendation

**Default OFF stands, for a third reason.** It was unmeasured in 23.7; measured
inert in 24.5; it is now measured to be **inconsistent** -- inert on one real
subject and altering 70% of pixels on another at identical settings. A flag
whose effect depends on subject brightness in a way no user can predict is not
shippable even when its output is benign.

**Do not pursue restore as the answer to the comparator deficit.** 1.05x
delivered against 1.20x-1.31x needed, non-selective by construction, and the
aggressive arms that reach the number pay for it in visible Nyquist noise.

**If it is to be fixed, both terms must be fixed together**, and the S term is
the one nobody has looked at. A detail-weighted or locally-fitted S plus the
merged-plane sigma^2 reaches the firing threshold at an honest noise level
rather than by understating it 20x. That is a real design and it needs the
`n_eff` hook s24.4 already asked for plus a local S -- both in files I do not
own.

**Unchanged**: the binding constraint at the scales the owner calls soft remains
the optics floor. Nothing measured here moves it.

## 34. Commissioning the restore switch: the cap cannot answer the question

ORCH read s33's null against a fact I did not have -- that `STREHL_RESTORE` is
off by default on the shipping backend -- and asked the right question: **a
stage that changes nothing when you switch it on is more likely unwired than
truly null.** The demand was a potency arm: set an absurd gain cap, render, hash
against the unset render.

I ran it. **The proposed instrument is degenerate**, and it would have returned
the wrong verdict. The reason is worth more than the result.

### 34.1 Which backend, answered first

Every number in s33 and s34 is the **pyramid** backend. From the render's own
log, not from assumption:

```
merge backend   : pyramid (inferred from --pyramid-gate; pass --merge estimator to override)
strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)
```

`DEFAULT_MERGE_BACKEND` is `MergeBackend::Pyramid` (`merge_cmd.rs:402`), the
plan is built at `:5128` inside `run_pyramid` and applied by `restore_plane` at
`:6488`. That is the guard ORCH named. All four planes emitted `restore` banner
lines on every arm, so the stage was entered.

### 34.2 The 2x2: does the cap move it, or only sigma?

One binary `BD5EB013...109F`, `112MSDCF`, shared cache, `--resampler
catmull-rom --demosaic --pyramid-gate 4.5`. OFF (flag unset) is
`ED0F92649C19C97B2E93757979D80FE6`.

| arm | gain cap | sigma^2 | result | max gain (1-D) | 2-D | recovered |
|---|---:|---|---|---:|---:|---:|
| A | 4.0 | calibrated | **IDENTICAL to OFF** | 1.0000 | 1.0000 | 0.0000 |
| B | **1e6** | calibrated | **IDENTICAL to OFF** | 1.0000 | 1.0000 | 0.0000 |
| C | **1e6** | x 1e-6 | **CHANGED** `0997FC08` | 1.5704 | 2.4660 | 0.9940 |
| D | 4.0 | x 1e-6 | **CHANGED** `0997FC08` | 1.5704 | 2.4660 | 0.9940 |

Read it by rows and by columns.

**A vs B**: the cap moves by a factor of 250,000 and the output is
byte-identical. **C vs D**: the cap moves by the same 250,000 and the output is
byte-identical *to each other*, same MD5, same gain to four decimals. The cap is
inert across its entire useful range at both noise levels.

**B vs C** is the controlled pair that matters: identical absurd cap, only
sigma^2 differs, and the picture changes. **sigma^2 alone controls the outcome.**

### 34.3 Why the cap cannot respond, and why that is not a wiring defect

The banner for arm B reads `cap 1000000.000`. The environment variable was
parsed, reached `RestorePlan`, and was carried into `restore_plane`, which
printed it. **The stage ran and produced byte-identical output**, which is
precisely the outcome ORCH's protocol assigns to "not running".

The mechanism is that `gain_cap` is an **upper clamp on a value that is already
1.0000**. At the calibrated sigma^2 the Wiener expression returns unity before
any clamp is consulted -- s24.2's budget algebra says gain exceeds 1 only where
`sigma^2/S < h(1-h)`, and that condition fails everywhere on this subject. A
clamp above a quantity that never rises cannot change it. Raising the ceiling of
a room does not lift the floor.

So the proposed test has a **false-negative mode on a correctly wired stage**,
and this is not hypothetical: arm B *is* that false negative, measured. Had I
run only ORCH's arm I would have reported a wiring defect that does not exist,
and s33's genuine algorithmic negative would have been thrown away.

**The switch is commissioned, by sigma^2 rather than by the cap.** Arms C and D
respond. s33's positive control did the same before ORCH asked. The stage is
wired on the shipping backend and **s33's null stands as an algorithmic result**,
not a harness artifact.

### 34.4 Two further findings that fall out of the 2x2

**The cap is effectively dead on this path.** With sigma^2 driven to `0.0 DN^2`
the gain saturates at **1.5704** (1-D) / **2.4660** (2-D). That is below the
default cap of 4.0, so the cap does not bind even at zero noise. The ceiling on
this restoration is set by the FIR basis, not by the cap and not by the noise.
Whatever the cap is for, it is not limiting anything reachable.

**The second clause of ORCH's pass criterion would also have been ambiguous.**
The protocol says the potency arm "must visibly wreck the image (ringing,
overshoot, obvious haloing)". Looked at, arm C is **subtly grainier and nothing
more** -- no wrecking, no obvious halo, on the flat, sharp or edge crop. A
correction whose maximum possible excursion is 1.57x per axis cannot wreck a
picture. Only the hash was decisive. **A criterion that requires a visible
catastrophe cannot commission a stage whose whole dynamic range is modest**, and
requiring one would have produced the same false negative a second way.

### 34.5 Routed, not fixed

- **`merge_cmd.rs:419-422`** (BUILD-WIRE's file) tells the user, in a
  user-facing error, that `estimator` is "the default". `DEFAULT_MERGE_BACKEND`
  at `:402` is `Pyramid`, and the banner at `:481` says so. **The error message
  names the wrong default.** Same family as the `roll_off` guard: a doc block
  describing a configuration the default does not use.
- The `gain_cap` non-binding result above is also BUILD-WIRE's call site.
- I have **not** changed the default and do not recommend flipping it. s33.9's
  reasoning is unaffected by anything here: the stage is wired, it is
  subject-dependently inert, it is non-selective by construction, and it
  delivers about 1.05x against a 1.20x-1.31x deficit.

### 34.6 The rule this earns

s32.2 said an arm that returns the same value on every input has not been
commissioned. This is the dual, and it cost a false verdict to find:

**A potency arm must move the knob the mechanism is actually sensitive to.
Choosing the wrong knob produces a silent instrument, and a silent instrument
reads exactly like a dead stage.**

## 35. The trace ORCH asked for: reachable, and `STREHL_RESTORE=1` is the no-op

ORCH's `check-potency.py` reports `STREHL_RESTORE=1` byte-identical on two
binaries and concludes the flag "reaches no pixel on either build", then asks me
to determine by reading the code whether the stage is **structurally
unreachable** or **measurably useless**.

**It is neither.** It is reachable, it reaches pixels, and the null is an
instrument artifact with a one-line cause.

### 35.1 `STREHL_RESTORE=1` is rejected by an explicit guard

`restore.rs:1240`:

```rust
if cap.is_finite() && cap > 1.0 { Some(cap) } else { None }
```

**The value is a gain cap, not a boolean.** `1` parses to `1.0`, `1.0 > 1.0` is
false, and the function returns `None` -- the identical state to the variable
being unset. The module's own doc comment says so above the constant: "`1.0` is
a documented no-op", and above the function: "`None` ... also when the cap is
not above `1.0`".

So the potency arm compared **off against off**. Byte-identity was guaranteed by
construction, on any binary, on any subject, at any setting. Nothing about the
render path was tested.

### 35.2 The full trace, every branch named

| # | site | condition | ORCH's arm |
|---|---|---|---|
| 1 | `restore.rs:1234` | `env::var(RESTORE_ENV).ok()?` | passes |
| 2 | `restore.rs:1236` | empty, `0`, `off` -> `None` | passes |
| 3 | **`restore.rs:1240`** | **`cap > 1.0` -> else `None`** | **DIES HERE** |
| 4 | `merge_cmd.rs:5128` | `.and_then(..)`, needs `alignment` | not reached |
| 5 | `merge_cmd.rs:6476` | `if let Some(plan) = restore.as_ref()` | not reached |
| 6 | `merge_cmd.rs:6488` | `restore_plane(&mut v, ..)` -- **the pixel write** | not reached |

`restore_plane` takes `&mut v`, and `v` is the plane pushed into `planes` and
written out. That is a write into pixel data, six steps from the `env::var`
read. There are exactly **two** branches that can silently disable the stage:
the `cap > 1.0` threshold and the `alignment.is_some()` requirement at step 4.

### 35.3 Straddling the threshold, at maximum aggression

One binary `BD5EB013...109F`, `112MSDCF`, pyramid backend quoted from each
render's own banner. Every arm holds `STREHL_RESTORE_SIGMA=0.000001`, so a
byte-identity cannot be blamed on a weak setting. Baseline (unset) is
`ED0F92649C19C97B2E93757979D80FE6`.

| `STREHL_RESTORE` | result | **restore banner lines** | max gain |
|---|---|---:|---:|
| `1` (ORCH's value) | **IDENTICAL** `ED0F9264` | **0** | -- |
| `1.0000001` | **CHANGED** `721BEB99` | **4** | 1.0000 |
| `4.0` | **CHANGED** `0997FC08` | **4** | 1.5704 |

**A change of 1e-7 in the flag value flips the stage from completely dead to
live.** That is the `cap > 1.0` threshold and nothing else. A structurally
unreachable stage does not have a threshold you can straddle.

**The banner count is the part ORCH could have read without me.** The product
already distinguishes the two cases in its own output: `1` emits **zero**
`restore` lines because the plan is `None` and `restore_plane` is never called;
`1.0000001` emits **four**, one per CFA plane. ORCH's house rule is "quote the
banner rather than your intent". The banner was quiet, and the quiet was the
answer.

### 35.4 What ORCH should and should not retract

**Do NOT retract `check-defaults.py`.** Its RED is correct and its subject is
real: the restoration exists, is reachable, reaches pixels, and is off by
default. ORCH offered to retract it if the trace showed unreachability. The
trace shows the opposite, so the check stands on its own terms.

**DO retract `check-potency.py`'s verdict on this flag.** It is repairable in
one character: any value above 1.0. The rule the checker encodes -- "a flag is
not wired until an absurd value has changed the output" -- is sound; the flag
was never given an absurd value. For a *cap*, absurd means large, and `1` is the
minimum meaningful setting rather than an extreme one.

**Neither of M126's two patterns applies.** This is not `robust.rs:64`, whose
constants are correct and whose code never executes; and it is not `outlier.rs`,
reachable only from `examples/`. `restore_plane` executes on the shipping
pyramid path and writes pixels, which s33 and s34 measured before this section
was written.

### 35.5 The defect that is real, and fixed here

The flag is a numeric gain cap wearing the costume of a boolean. `=1` reads to
any engineer as "enable" and means "disable" to the code, **silently**. That
trap has now produced a false verdict at the orchestration level, and it had
already produced two degenerate potency arms of my own in s34 -- three misfires
on one knob.

`restore.rs` is mine, so I have made the no-op **announce itself** rather than
be silent:

```
restore        : STREHL_RESTORE=1 is the documented NO-OP (the value is a gain
cap and 1.0000 is not above 1.0), so the restoration will NOT run and the
output will be byte-identical to leaving it unset. Pass a cap above 1.0
(e.g. 4.0) to enable it.
```

A non-numeric value gets the same treatment; previously `STREHL_RESTORE=yes`
also returned `None` without a word.

**This is diagnostic only and changes no pixel.** Verified: with the warning in
place, `STREHL_RESTORE=1` still renders `ED0F92649C19C97B2E93757979D80FE6`,
byte-identical to the baseline. `cargo test -p strehl-core --release`: **480
passed, 0 failed**. Binary carrying the fix is
`ADECDAD8B92A528B0224D8E5B477E2A49306AD38DCB0C720DCDCFA3E867B63EB`; every
measurement above was taken on the earlier pin `BD5EB013...109F`, which does not
contain it.

I have **not** touched the algorithm, the default, or any call site, per ORCH's
instruction to keep the two effects separable.

### 35.6 The rule

s34.6 said a potency arm must move the knob the mechanism is sensitive to. This
is the sharper form, and it cost a verdict at two levels to learn:

**Before trusting a potency arm, confirm the value you set was accepted. A flag
that silently rejects your input is indistinguishable from a stage that ignores
it -- and the product's own banner usually already knows which.**

## s36. The soft subject: the gate is exonerated, and the decision grid is half resolution

ORCH routed `flower-bud-alone-cpl` to me as the largest open quality gap: worst
in the corpus at a V-bestframe median merge-to-best-frame ratio of **0.82**, and
independently the one subject of twenty-six that ORCH flagged by eye as visibly
soft. Two cautions came with it -- a clipped highlight and a magenta fringe --
and I was asked not to measure three things at once.

I arrived with a hypothesis and it was wrong. This section records the
refutation first, because it was mine.

### s36.1 The hypothesis I brought, and the measurement that killed it

The subject is high-key: a dark green bud on a large bright white field. That
geometry produces veiling glare, glare lowers local contrast, and the render's
own banner states the consequence of low contrast without ambiguity:

    noise gate      : 4.50 x the modelled band-noise power. Below it, NO frame
                      may win and the merge averages.

A mean across 205 frames of differing focus is much softer than the best single
frame. So: glare pushes band power under the gate, the gate forbids selection,
the merge averages, and merge-to-best-frame lands at 0.82. It is a tidy chain
and it connects ORCH's eye to V-bestframe's statistic.

One pinned binary `ADECDAD8B92A528B0224D8E5B477E2A49306AD38DCB0C720DCDCFA3E867B63EB`,
205 frames, one variable. Banner quoted on every arm rather than intent, and the
gate value is echoed back so the arm cannot be degenerate in the way s35
records:

| arm | banner backend | banner gate | md5 |
| --- | --- | --- | --- |
| `--pyramid-gate 4.5` (shipped) | `pyramid (--merge)` | `4.50 x` | `0473E5E9` |
| `--pyramid-gate 1.0` | `pyramid (--merge)` | `1.00 x` | `5349C2CE` |
| `--pyramid-gate 0.0` | `pyramid (--merge)` | `0.00 x` | rendered |

The flag is live and the arms differ. Band power ratios, tiles ranked once on
the shipped arm so that no arm chooses its own tiles (s33.5), in cycles per
output pixel:

| population | 0.05-0.10 | 0.10-0.20 | 0.20-0.30 | 0.30-0.40 |
| --- | ---: | ---: | ---: | ---: |
| flattest 5% | 1.90 | 6.06 | **10.16** | 8.04 |
| median 10% | 4.04 | 11.82 | **15.11** | 10.91 |
| sharpest 5% | 1.00 | 1.02 | **1.27** | 1.61 |

The flattest tiles gain ten times the power in the band where we are losing to
the comparators; the sharpest gain 1.27x. By the standing s31 rule -- measuring
in the right band is necessary but not sufficient, the stimulus must exist in
the real data too -- this is not detail recovery.

### s36.2 Why it is not, stated in a quantity the two hypotheses disagree about

The ratio table alone cannot separate "recovered detail" from "the same noise
measured against a smaller denominator". A uniform additive noise floor raises
every tile by the same ABSOLUTE power, which reads as a huge ratio in a flat
tile and a small one in a sharp tile -- exactly the observed 10.16 / 1.27 split.
So the ratio is the wrong statistic and I replaced it with absolute delta, which
the two hypotheses do disagree about: additive noise is constant across
populations, recovered detail grows with the detail already present.

Gate 1.0 minus gate 4.5, band 0.20-0.30, absolute delta power:

| population | reference power | ABS delta | ratio |
| --- | ---: | ---: | ---: |
| flattest 20% | 8,352,762 | **146,590,200** | 18.55 |
| 2nd quintile | 13,701,753 | 219,948,577 | 17.05 |
| 3rd quintile | 18,072,611 | 254,690,058 | 15.09 |
| 4th quintile | 22,624,956 | 234,255,012 | 11.35 |
| sharpest 20% | 77,091,581 | **54,644,724** | 1.71 |

The delta is largest where there is no detail and smallest where the detail is.
It is not merely uncorrelated with content, it is anti-correlated with it.

The mechanism is the interesting part and it is a defence of the gate rather
than an indictment. **Where the detail is, band power already exceeds the gate
at 4.50, so the gate was never binding there.** Lowering it cannot sharpen a
region it was not acting on. All the gate ever did was protect the low-SNR
field, and removing that protection floods the field with noise at 18.55x while
moving the detail by 1.71x -- and even that 1.71x is delta 54.6M against the
flat population's 146.6M, so it is the tail of the same flood.

**The gate is correctly targeted. My hypothesis is refuted and the gate is not
the softness lever.**

### s36.3 The picture agrees, which is the standard I set in s31

Three-way 1:1 crops, sites chosen once on the shipped arm so a change cannot
also select where it is displayed. Across all three sites the hairs are
indistinguishable between gate 4.50, 1.00 and 0.00 -- equally soft, equally
resolved, no acuity gained anywhere. What visibly changes is the white field,
which at gate 1.00 becomes plainly grainy and mottled where the shipped arm is
clean. The eye and the delta table report the same thing, and neither reports
recovered detail.

### s36.4 The fringe is not lateral CA, and my own discriminator was too weak

ORCH gave the correct discriminator: lateral CA is antisymmetric and radial,
clipping asymmetry is neither. I measured the subpixel R-versus-B edge
displacement against signed distance from the image centre, on 58,890 accepted
vertical edges with 1,110 rejected for weak amplitude in one channel and both
counts reported, so a rejected edge cannot read as a measured one.

The null control -- the same statistic computed G against G -- returns exactly
`0.0000` in every radius bin. The instrument does not manufacture a trend.

The R-versus-B displacements are `+0.033, +0.011, -0.013, +0.006, -0.047,
-0.021` px across the bins. **The bound is what matters: lateral R-B
displacement is at most about 0.05 px, and a visible magenta fringe requires
roughly 0.5 to 2 px.** The fringe is not lateral misregistration.

I must also retract my own flag rather than let it stand. The script printed
`ANTISYMMETRIC? YES` on the strength of `mean_left * mean_right < 0`, comparing
`+0.0103` against `-0.0209`. **Two noisy numbers of no particular size satisfy
that test half the time.** It is a discriminator that cannot fail, which is the
same defect class as every uncommissioned instrument this report has caught, and
it is not evidence. The defensible result here is the 0.05 px bound and the
exact null, not the flag.

Consequence for routing: `optics.rs:562` carries a lateral-CA profile named
`a7c2-fe100gm-2xtc-x4cpl`, which is the owner's exact rig, and it is default off
(`unset / "" / "0" -> Ok(None)`, a silent no-op). It is tempting to reach for
it. **It would not fix this fringe**, because it is a radial term correcting a
displacement that is measured here to be 0.05 px. Whatever the fringe is, it is
chromatic in amplitude rather than in position -- longitudinal CA, defocus
fringing, or a chroma artifact -- and none of those are lateral.

### s36.5 A correction owed to ORCH: the render is not clipped

ORCH's first caution was that this subject's highlight is clipped. Of the
delivered render that is false: the clipping census returns **0.0000 per cent of
pixels at the ceiling on all three channels**, with a maximum green of 64,516 of
65,535. The caution may still be true of the raw frames, which I have not
examined. It is not true of the picture that was looked at.

### s36.6 The structural finding: strehl never makes a focus decision at the scale of the deficit

Having exonerated the gate I read the render path, and the product's own banner
says the thing that matters:

    Full sensor resolution: every CFA site estimated, one focus
    decision per quad. Interpolated -- do not measure resolution on it.

Traced to the code (`merge_cmd.rs:6302` and `:6553-6565`). `merged.value(p, i,
black)` reads one merged structure indexed by quad `i`, returning a value for
each of R, G1, G2, B; the four planes are then woven into a mosaic of `mw = 2 *
geom.width` by `mh = 2 * geom.height` and Malvar-He-Cutler demosaics last. So:

1. The merge runs on **four planes at half the output dimensions in each axis**.
2. Every per-plane operation -- the pyramid bands, the noise gate, the s33
   restoration -- is therefore band-limited to **plane Nyquist, 0.5 cycles per
   plane pixel, which is 0.25 cycles per OUTPUT pixel**.
3. All four planes share **one focus decision per 2x2 quad**, so the decision
   grid is half the output resolution. (This is a point in the design's favour:
   G1 and G2 cannot select different frames, so the interleaved green is
   coherent rather than a beat between two frames' focus.)
4. Everything in the output above `f_out = 0.25` is produced by interpolation
   from a mosaic whose every quad was chosen by a half-resolution sharpness
   measurement.

Set that against the head-to-head deficit, converted into `f_out` as s33 records
(`V-HEADTOHEAD/spec.py:70` computes cycles per PRIOR pixel; strehl scale
1.035063):

| comparator band | as `f_out` | vs fork | vs Zerene | relative to plane Nyquist 0.25 |
| --- | --- | ---: | ---: | --- |
| 0.20-0.30 | 0.193-0.290 | 0.833 | 0.735 | **straddles it** |
| 0.30-0.40 | 0.290-0.387 | 0.766 | 0.843 | **entirely above it** |

**The two bands where we lose 17 to 27 per cent are the two bands at and above
the frequency where our merge stops having any information.** A 3-pixel feature
is 0.33 cyc/px_out; our focus decision grid has a 2-pixel pitch. We are being
beaten precisely and only where we never made a decision. This also explains why
every lever I have tested inside the merge -- restore in s33, the gate in s36.1
-- moves the picture by a few per cent against a deficit of twenty: they all
live below 0.25 and the deficit does not.

It is consistent with the comparators' architecture. The fork demosaics each
frame with OpenCV and then merges at full RGB resolution, so its focus decision
is made at full resolution on data that already has a full-resolution estimate
at every site. Zerene likewise operates on developed RGB.

### s36.7 What I have NOT established, and the test that would decide it

I will not let s36.6 become the answer on the strength of its own tidiness. It
predicts the SHAPE of the deficit, which is not the same as being its cause, and
there is a rival hypothesis that predicts the same shape and that this project
has a specific obligation to test:

> The comparators' extra power above `f_out = 0.25` is not resolution. It is
> overshoot. `cv::INTER_LANCZOS4` rings, and Zerene PMax is a contrast-
> maximising method with a known artifact signature. Both add high-frequency
> power that a band-power statistic scores as a win and that a print scores as a
> defect.

This is the hypothesis ORCH explicitly invited, and it is the same failure mode
I caught in myself in s31, when Hamilton-Adams delivered 1.5016x the HF power in
the flattest five per cent and the picture was a maze. **A comparator that wins
a band-power ratio by ringing looks identical, in that table, to one that wins by
resolving.** The two are separated by the paired ringing detector commissioned in
s33 -- null exactly `0.000000`, plants recovered at exactly `0.0500 / 0.1500 /
0.3000` -- and by opening the comparator outputs at 1:1.

I do not hold the comparator renders; they are V-HEADTOHEAD's. **This is the
measurement I am asking ORCH to route**, and it is cheap for whoever has those
files. Until it is done, the honest statement of the head-to-head is that we
lose band power at 3-5 px features, not that we lose resolution there.

Both hypotheses are worth the same effort and they have opposite consequences.
If the comparators are genuinely resolving, the fix is architectural and large:
the focus decision has to move to full resolution. If they are ringing, the
finding is that this rig cannot deliver contrast at 0.30 cyc/px, nobody's
software can, and we should stop chasing it -- and that is a result worth as
much as a win.

## s37. Commissioning against a stranger's render, and `flowers-cpl` is not ours

Two assignments. The first produced the more important result, and it is a
result about an instrument rather than about the product.

### s37.1 The ringing detector, commissioned on comparator output

ORCH's objection was exact: my plants were injected into strehl's own images,
and a detector that fires on synthetic ringing in a strehl render has not been
shown to fire on `INTER_LANCZOS4` output at a different noise level and grade.
So `restore_ring.py` gained a `--commission-on <real.tif>` mode that runs the
same two demands -- an exact null and a calibrated plant -- on whatever file
will actually be measured.

Run on the fork's own render and on a strehl render:

| render | null max abs d | recovers | baseline p99 |
| --- | ---: | ---: | ---: |
| synthetic ideal steps | 0.000000 | **1.00x** | (0 by construction) |
| fork `smoke.tif` | 0.000000 | **0.38x** | 0.7390 |
| strehl `flowers-cpl` linear | 0.000000 | **0.08x** | 2.0857 |

**The detector is 4.75x more sensitive on the fork's render than on ours.**

Had I done what the assignment literally asked -- measure overshoot on both and
compare -- the fork would have read as roughly five times ringier than strehl
**with no ringing present anywhere**, purely because the instrument responds
differently to the two images. That number would have confirmed the hypothesis I
was sent to test. It is the confirmatory failure mode ORCH named: an instrument
whose error resembles its intended output reads as a success every time it
breaks.

The mechanism is physical rather than a bug. The plant `[-a, 1+2a, -a]` is
calibrated on an IDEAL step, where it deposits exactly `a` beyond the plateau
and recovery is exact. Real edges are blurred across several pixels, so the
kernel's negative lobes sit on intermediate values instead of the plateau and
the same ringing yields proportionally less overshoot. Sensitivity therefore
scales with how step-like a render's edges are, which is itself a property that
differs between stackers -- which is precisely the quantity under dispute. **The
instrument is confounded with its own subject.**

I did NOT loosen the pass criterion to make the arms pass, because the criterion
was not wrong about ideal steps; it was being applied outside the domain it was
calibrated on. What the commissioning now demands is what a usable instrument
needs -- an exact null, a strictly monotone response, and a clear direction --
and it REPORTS the recovery fraction as the sensitivity every later number on
that image inherits.

**The protocol this forces on the strehl-versus-comparator comparison**, and it
is not optional:

1. Both renders must be of the **same subject**. The two files above are not --
   `smoke.tif` is `flat-on-ruler-cpl` and mine is `flowers-cpl` -- so the 4.75x
   confounds subject, grade and pipeline and attributes to none of them.
2. Each render must be commissioned **separately**, and its measured overshoot
   divided by its own recovery fraction before the two are compared.
3. Absolute magnitudes may never be compared across images. Paired `worse` and
   paired delta remain valid within one image.

Without step 2 the comparison measures edge blur and calls it ringing.

One incidental catch worth recording because it nearly cost the instrument: the
first run printed `amplitude floor 0.0 DN` and I took it for a degenerate image.
The floor was 0.00815; the file is float32 in [0.0175, 0.2333] and I had
formatted it `:.1f`. **A display format in my own commissioning output almost
produced a false verdict about a working detector.** Now printed `:.6g`, with
the units stated as the file's own rather than assumed to be DN.

### s37.2 `flowers-cpl`: the merge is not losing anything the data holds

ORCH's reading was that the subject extends deeper than the capture covered.
The decisive comparison is the merge against the best frame available per
region, and it took three instruments because the first two were confounded.

**Attempt 1, retracted.** A contrast-normalised gradient over the raw frames,
max across the bracket. It returned argmax frame **0** for 20 of 24 regions. On
a 176-frame focus bracket the first frame being sharpest almost everywhere is a
statement about the instrument, and I did not report it. Its verdict logic was
also one-sided -- it tested only for a pileup at the LAST frame, so a sweep that
ran out at the NEAR end would have been classified "every region has an interior
optimum", the same defect class retracted in s36.4.

**Attempt 2, also retracted, with the cause found.** Keeping the whole
through-focus curve instead of its maximum showed every region declining
MONOTONICALLY across all 176 frames, and the exposure trace showed the frame
mean rising 6671.4 -> 7908.9 DN, an **18.5% ramp**. `mean|grad I| / mean I` is
invariant to a global gain in its signal term but not in its noise term: photon
noise scales as sqrt(I), so its contribution falls as 1/sqrt(I), predicting an
~8.8% decline over that ramp by itself against observed declines of 10-15%. The
statistic was tracking the lamp. A second statistic was computed precisely to
catch this and agreed on 22 of 24 regions -- **two statistics agreeing is not
independence when both are normalised by intensity and both are being moved by
the same ramp.**

**Attempt 3, which answers the question.** `argmax-baseline` is strehl's own
negative control and it selects per pixel the frame with the highest
NOISE-NORMALISED Tenengrad measure, so an exposure ramp cannot move its choice
the way it moved mine. It is binned rather than demosaiced and its output is
linear. It is not a candidate output and is not proposed as one -- it does not
align -- but as evidence about what the INPUT contains it is exactly right: if a
region is soft in the best-frame composite, no captured frame holds it sharp.

The acutance table said the merge was at 0.19-0.69x of the baseline, worst
region 0.186, which read as a catastrophic merge deficit. **It is not, and the
tell was in the table.** The baseline's acutance is nearly FLAT across the
frame, left/right 1.254, while the merge falls 3.359x. A genuinely detail-rich
best-frame composite cannot be uniform on a subject that is visibly soft on the
right, so the baseline's acutance is not detail.

Opening both at 1:1 settled it. The baseline is not sharper: it is **blotchy** --
irregular flat patches with hard boundaries, the unregularised per-pixel winner
map, exactly the artifact this subcommand's own help says it exists to
demonstrate. **Those patch boundaries are what my acutance statistic was
counting as gradient.** Underneath them the content carries the same blur as the
merge, and in the right-hand regions both are equally soft.

**Verdict for routing: `flowers-cpl` is not a second instance of the
`flower-bud-alone-cpl` defect.** Pure per-pixel selection over the same frames
recovers no detail the merge lacks. The merge is doing what the data permits.

**What I did NOT establish, and will not imply.** I have not shown the bracket
is incomplete. That claim needs a valid through-focus census and mine was
confounded by the exposure ramp; I retracted it rather than repair it under
time. The measured statement is the narrower one -- selection over these frames
does no better than our merge -- which is enough to answer whether `flowers-cpl`
counts against the tool, and not enough to explain why it is soft. The 18.5%
exposure ramp is itself worth routing to whoever owns capture advice.
