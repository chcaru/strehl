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
