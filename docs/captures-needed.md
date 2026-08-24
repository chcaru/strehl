# Captures needed from the owner

Measurements that are blocked on data no existing file can supply. Each entry
says exactly what to shoot, why, and what it unblocks.

---

## 0. Shooting advice — stop shooting at marked f/11

Not a capture request. A change to how the existing rig is used, and the
largest single quality lever measured anywhere in this project.

**Marked f/11 is optically f/33** on this rig (fact 28: the body writes the
marked aperture into EXIF and applies no bellows correction for working at 2:1).
At that effective aperture the diffraction cutoff falls to 0.2762 cyc/px against
a Nyquist of 0.5, so **MTF at Nyquist is exactly 0.000** (fact 12, measured).
More than half the band the sensor can record is empty before any software runs,
and no stacker — this one included — can put it back. Critical sampling is at
**marked f/6.21**.

Measured cost, at matched focus-axis sampling and fixed subject depth
(`research/M20-deconvolution-ceiling-measured.md` §4.4):

| marked | optical `N_eff` | contrast at 4-px detail | vs f/11 |
| --- | --- | --- | --- |
| f/4 | 12.0 | 0.5977 | **12.9x** |
| f/5.6 | 16.8 | 0.4467 | **9.6x** |
| f/8 | 24.0 | 0.2416 | **5.2x** |
| f/11 | 33.0 | 0.0463 | 1.0x |
| f/16 | 48.0 | 0.0000 | zero |

**The trade is frame count, not light.** Depth of field scales with `N_eff`, so
covering the same subject depth at f/5.6 instead of f/11 needs about **2x the
frames**. It does not need more total light — a wider aperture more than pays
for the extra frames. At a fixed total capture time the end-to-end SNR at 4-px
detail is **13.5x** better at f/5.6; even holding total light constant it is
**6.9x** better.

**Try it on the next stack.** Same subject, two brackets: one as usual at f/11,
one at f/5.6 with twice the frames. That pair is also a genuinely useful capture
for the project — see §7.

*Caveat, stated honestly: the table is DERIVED from a diffraction model gated
against facts 12, 27 and 28 (agreement to 3-4 digits), not from a side-by-side
shot. The two-bracket pair above is what would turn it into a measurement.*

**External corroboration, added after M19's literature survey.** The *shape* of
this ceiling is not our claim — it is proved. Levin et al. (*ACM TOG* 28(3),
2009, Claim 2) bound the worst-case defocus MTF power over a depth range by
`β(ω)·A³/(S·|ω|)` with `β ∈ [0.93, 1]`, and note that under Fourier rather than
geometric optics the budget "**decreases with the diffraction-limited MTF**" —
so where the diffraction MTF is zero, the budget is zero (fact 403). That is an
independent, published derivation of the thing this section is telling you to
avoid: **no merge, however clever, recovers a band no frame observed.** It is
also why aperture outranks algorithms here. Every hour spent improving the merge
before this section is acted on is an hour spent optimising underneath a ceiling
you could simply have raised.

---

## 1. Dark frames — DELIVERED

**Status:** delivered and measured. Results in
`research/M4-fpn-measured.md`. Nothing depends on this entry any more.

### What was actually supplied

| | Requested | Supplied |
| --- | --- | --- |
| ISOs | 2 (100 and 400) | **11** — 50, 100, 200, 250, 400, 500, 640, 800, 1000, 1600, 2000 |
| Frames per ISO | 20 | 22, first 2 discarded as stabilisation shots -> **20 used** |
| Total | 40 | **242 captured, 220 analysed** |
| Shutter | ~1/100 s | 1/100 s, uniform across all 242 |
| Location | — | `D:\macro-dark-frames\{118..128}MSDCF`, one folder per ISO |

The folder-to-ISO mapping was not supplied and was discovered from EXIF. Every
folder proved internally uniform in both ISO and exposure. All eleven passed
the light-leak sanity gate.

**The over-delivery is why the dual-gain result exists.** Two ISOs can only show
that ISO 400 differs from ISO 100. Eleven ISOs, five of them bracketing the
switch (200 / 250 / **400** / 500 / 640), show a *discontinuity*: noise in DN
rises to ISO 250, drops 45% at ISO 400, then resumes rising. That is
model-free evidence for a second base ISO, and it needed the extra nine folders.

### What it unblocked

- **The central design pillar, answered.** Raw dark-frame averaging follows a
  slope of -0.289, not -0.5, and hits a fixed-pattern floor of 0.377 DN at
  N ≈ 7. With a disjoint master bias subtracted the slope is -0.5019 and every
  point is within 0.5% of ideal. The pillar holds, conditionally.
- **Dark-frame subtraction is worth shipping**, with a measured design rule: the
  master must be built from at least `(sigma_temporal/sigma_FPN)^2` frames —
  7 at ISO 100, 42 at ISO 2000 — or it injects more noise than it removes.
- **`SYNTHESIS.md` fact 14 confirmed** model-free.
- **`SYNTHESIS.md` §7 risk 8 downgraded** at short exposures: zero pixels sit
  50 DN above black at base ISO. Still unverified for long exposures.

### What it did not unblock

The photon-transfer curve. **PTC is impossible from dark frames** — it needs
signal variance against signal level and a dark frame has no signal. `g` remains
`DERIVED` from an unmeasured relation and `SYNTHESIS.md` §10 item 6 stays open.
See §4 below.

> **Superseded, 2026-08-23 — and the lesson generalises.** A *usable* PTC did
> arrive, from **stacks already on disk**, without any new capture. M25 measured
> `g` by photon transfer on `109MSDCF`, `119MSDCF` and `coffee-bean` — 8×8 tiles
> on one green plane, 5th-percentile variance per mean bin, using the scene's
> own tonal range as the signal ladder. It recovered `g` = **0.3273 at ISO 160**
> against the relation's 0.3663 and found a **2.05× error at ISO 50**, now fixed
> in shipped code (`2a4f5c5`, fact 550). SYNTHESIS §10 question 8 is **closed**.
>
> **This paragraph was wrong in a specific and instructive way.** "PTC is
> impossible from dark frames" is true. "Therefore `g` needs a flat-field
> capture" does not follow, and nobody checked it — the requirement was
> *inherited from the textbook procedure* rather than derived from what this
> measurement actually needs, which is signal variance against signal level from
> **any** source. A photograph is such a source.
>
> **Before adding anything to this file, ask what the measurement needs rather
> than what the standard procedure prescribes, and try the corpus first.** The
> owner's time behind a camera is the scarcest input this project has.
>
> The flat-field campaign in §4 is **still worth shooting** — it measures PRNU
> and vignetting, which no existing capture can give, and it yields a *clean*
> intercept. This PTC's intercept is **not** trustworthy: residual scene texture
> inflates it to 6.9 e⁻ at ISO 160 against fact 14's 4.20 e⁻, so it constrains
> the **slope only** and says nothing about `RN_e`.

### What to shoot (kept for reference / repeat captures)

| | |
| --- | --- |
| Lens or body cap | **On.** No light may reach the sensor. |
| Room | Dark. Cover the viewfinder if shooting with the EVF exposed. |
| Mode | Manual. |
| Shutter | ~1/100 s (match a typical stacking exposure). |
| Aperture | Irrelevant — the cap is on. |
| Format | **RAW (.ARW).** Not JPEG, not compressed-lossy. |
| Noise reduction | **All off.** Long-exposure NR and high-ISO NR both. |
| Count | 20+ frames per ISO of interest. |
| Between frames | Change nothing. Do not move the camera or touch settings. |

### Why it could not come from existing files

The plan was to get this free from the sensor's optically-masked border pixels,
which see no light by construction and are therefore a dark frame embedded in
every RAW. **`rawler` does not expose them:** it reports `blackareas` as empty
for Sony, and crops the masked border away during decode. What remains outside
the active area is synthetic zero padding, not sensor data. Verified in
`research/M1-decode-measured.md` §3 — probed 3,544,448 pixels, all exactly 0.

---

## 2. Rail-captured stack — DEFERRED, no hardware

**Status:** owner has no focus rail. Rail support is deferred from v1
(`research/SYNTHESIS.md` §9). Not blocking anything currently planned.

If a rail is ever borrowed: one stack of a subject with **visible depth
discontinuities** — overlapping structure where a near surface occludes a far
one, not a smooth continuous surface. That is the case affine cannot model, and
it is where the parallax and occlusion claims need testing.

---

## 3. Not needed

Recorded so nobody asks twice.

- **Flat fields for vignetting.** Not on the v1 path. (Flat fields *are* now
  wanted for a different purpose — see §4. This entry refers only to lens
  vignetting correction.)
- **A focus-bracketed stack.** Already have 22 frames in
  `C:\dev\macro\test\109MSDCF` plus 2310 further ARWs, all verified decodable.
- **A second deep stack, for the fact-43 shrinkage calibration.** Was the one
  outstanding *photographic* request after M10. **Already satisfied** by
  `D:\personal\macro\112MSDCF` (79 frames) and `113MSDCF` (63 frames) — see §5.

---


## 4. Flat fields — **DELIVERED 2026-08-23**
### What was actually supplied — read this before using it

`D:\personal\macro\flat-fields`, **484 ARW frames in three directories**, all
`ILCE-7CM2` + `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, **ISO 100, marked f/5.6,
FocalLength 200 mm** (the body composes the TC — fact 26).

| dir | n | structure | span |
| --- | --- | --- | --- |
| `flat-fields/` | **360** | **9 exposures x 40 frames.** 1/250, 1/125, 1/60, 1/30, 1/20, 1/13, 1/10, 1/8, 1/5 s | 16:41:30 -> 16:50:32 (**9m02s**) |
| `subject-focus-sweep-with-cpl/` | 62 | single exposure 1/5 s, focus swept out-through-out | 16:31:55 -> 16:32:38 |
| `subject-focus-sweep-no-cpl/` | 62 | single exposure 1/5 s, focus swept out-through-out | 16:51:17 -> 16:51:56 |

**Subject:** two stacked sheets of white A5 printer paper taped to a window. Lens front
**~9 cm** from the paper, **~28 cm** subject-to-sensor. That is near the composed path's
minimum focus, so **m is near the 2.0 maximum** and the field is roughly **18 x 12 mm** of paper.

**The owner reports the session as: sweep-with-CPL, then 8 exposure sets of 20 with CPL,
then the same without, then sweep-no-CPL.** EXIF says **9** exposures x **40** frames, which
is consistent: **each 40 is 20 CPL + 20 no-CPL at the same shutter speed**, and the owner
counted 8 rather than 9. **CPL state is NOT recorded in EXIF.** It must be recovered from
capture time (CPL first) and cross-checked against signal level, since a CPL costs ~1.5-2
stops and the two halves should separate cleanly at matched shutter speed. **Recovering the
split is the first task and it is self-validating; do not assume the owner's count of 8.**

### Confounds the owner flagged, and one they did not

1. **Illumination was not stable and the owner said so.** Seattle August overcast, *"some
   minor patches of blue sky"*, clouds moving slowly, no direct sun, *"possibly varied light
   over the whole duration"* — over **9 minutes**. Within one 20-frame set at 1 s intervals
   the drift window is ~20 s; between sets it is minutes. **Global drift is a per-frame
   scalar and divides out by normalising each frame to its own spatial mean; that
   normalisation is mandatory before any temporal-variance estimate.** Residual excess
   variance after normalising is then evidence the drift had *spatial* structure, which is a
   result in itself, not a nuisance.
2. **The confound the owner did not flag, and it is the serious one: at m~2 the paper's own
   fibre texture is resolved, and multiplicative paper texture is exactly what PRNU looks
   like.** Both are fixed and both scale with signal, so **they are not separable by the
   photon-transfer argument alone.** Two levers exist in the delivered data:
   - **Spatial frequency.** PRNU is near-white per pixel; paper fibre structure is
     correlated over ~10s of microns, which at m~2 is several pixels. The corpus already has
     validated spectral-domain separation machinery (facts 27, 29).
   - **Defocus, which is the clean one.** Defocus blurs paper texture and **leaves PRNU
     untouched.** The two 62-frame sweeps run from out of focus, through focus, and back
     out, at the same aperture and magnification as the flats — so **the most defocused
     frames carry the same PRNU with the least paper texture.** That is a direct
     experimental handle and it is already in the delivered set.
   **Any PRNU number produced without addressing this is not a PRNU number.**
3. **Focus position during the 360 flats is unrecorded.** If the paper was left in focus,
   texture dominates; if left defocused, it does not. **Determine this from the data before
   trusting any spatial statistic.**

### Unexpected bonus — this may partially satisfy §8

The two focus sweeps are **through-focus series on a planar subject at known magnification**.
A plane taped to a window and shot handheld-ish will carry **some tilt**, and tilt on a plane
is **analytic depth**: the through-focus peak should move linearly across the field. That is
the instrument §8 asks for. **It is not a substitute for a deliberate §8 capture** — the tilt
is unknown and uncontrolled, and paper is a low-contrast broadband target rather than a
resolution chart — but it is the first physical target in the corpus with a *known depth
model*, and it is directly useful to focus-correctness and through-focus work.

### Status of what §4 was blocking

- **PRNU (kappa) for `sigma^2(S) = gS + (RN*g)^2 + (kappa*S)^2`** — unblocked **subject to
  confound 2 above**.
- **A second independent photon-transfer curve** across a **50x** signal range at one ISO,
  to cross-check facts 27/29 — unblocked, this is the cleanest thing in the set.
- **Illumination/vignetting profile and CPL transmission + any CPL-induced angular
  non-uniformity** — unblocked, with the drift caveat.
- **Dust map**, fixed in sensor coordinates — unblocked.
- **NOT unblocked: PRNU at other ISOs.** Everything here is ISO 100.


**Status:** **owner is shooting these in daylight, next opportunity** (agreed
2026-08-22). Raised by `research/M4-fpn-measured.md` §7 and §8.3. Not blocking
experiment 3; blocking two things that are currently guesses.

### Daylight-specific notes

Daylight is a good light source for this — bright enough to keep exposures
short, and free of the flicker that makes artificial sources risky. It has one
failure mode the generic spec below does not cover.

**The trap: illumination that drifts during a level.** The whole measurement is
a *temporal* variance per pixel at a known mean. If the light changes while the
16 frames of one level are being taken, that change enters the per-pixel
temporal variance and is indistinguishable from sensor noise. It inflates the
variance, which inflates the fitted gain, which corrupts every electron figure
downstream. Drift *between* levels is harmless; drift *within* a level is not.

Three mitigations, in order of how much they help:

1. **Shoot in open shade or under overcast, not direct sun**, and point at a
   diffuser rather than at the sky itself. Sun through moving cloud is the worst
   case; a bright overcast is nearly ideal.
2. **Take each level as a fast burst**, so all 16 frames sit inside a few
   seconds. Take the time between levels, not during one.
3. **It is recoverable in analysis if it happens** — normalise each frame by its
   own global mean before computing the temporal variance, which removes a
   spatially-uniform illumination change while leaving per-pixel noise intact.
   Treat this as a safety net, not a licence to be careless: it only removes the
   *uniform* component, and a moving shadow or a changing sky gradient is not
   uniform.

**Check before analysis, not after:** the frame-to-frame global means within a
level should be flat to well under 1%. If they trend, that level is suspect and
should be reshot.

### What to shoot

| | |
| --- | --- |
| Subject | An **evenly lit featureless surface** filling the whole frame. |
| How | Easiest reliable method: a sheet of white paper or an opal/white acrylic sheet held a few cm in front of the lens, lit indirectly. A cloudless sky through a diffuser also works. An LCD showing a white screen does **not** — it has pixel structure and PWM flicker. |
| Focus | **Manual, set to infinity or fully defocused.** The point is that nothing in the frame is sharp. |
| Aperture | f/8 or so. Keep it identical across the whole set. |
| ISO | **100**, fixed. Do not let it move. |
| Format | **RAW (.ARW).** Noise reduction all off. |
| Exposure levels | **7 levels**, by shutter speed only, spaced roughly a stop apart, targeting mean raw values of about **500, 1000, 2000, 4000, 7000, 11000, 14000 DN** above black. Overexposing one is fine and useful; clipped frames are simply dropped. |
| Frames per level | **16.** Change nothing between them. |
| Teleconverter | **Irrelevant — leave it on.** Gain and PRNU are sensor properties, and the vignetting the TC changes is fitted out by the smooth-surface normalisation below. Just keep it identical across the whole set. |
| Between levels | Change **only** the shutter speed. Do not move the camera, refocus, or alter the lighting. |

Roughly 112 frames. If that is too many, 8 frames per level at 5 levels is
still enough, with wider error bars.

**How to hit those levels in practice.** The camera's histogram is of the
embedded JPEG, not the raw, so do not try to hit the DN targets by eye. Meter
one exposure that looks like a bright mid-tone, then bracket **+-3 stops in
1-stop steps** around it. That gives the 7 levels. **Err wide deliberately** —
clipped frames cost nothing because they are simply dropped, whereas a set that
never approaches the white level leaves the top of the curve unmeasured.

**Discard the first 2 frames after touching the camera**, the same habit used
for the dark-frame set.

Also useful and nearly free: repeat one mid-level (say 4000 DN) at **ISO 400**,
16 frames. That gives a second gain point either side of the dual-gain switch.

### Why this cannot come from existing files

Every existing corpus is of real subjects. A photon-transfer curve needs the
variance of a *uniform* signal at a known level; any scene texture contributes
spatial variance that is indistinguishable from noise. The uniformity is the
measurement.

### What it unblocks

1. **The gain `g`, measured rather than assumed.** Photon shot noise obeys
   `variance = g * signal`, so the slope of variance against mean over the
   exposure series *is* the gain, in DN per electron. Right now `g = ISO/436.8`
   is inferred from reproducing the camera's white level to 0.23% — a
   consistency check on one relation, not a measurement. This closes
   `SYNTHESIS.md` §10 item 6 and upgrades every electron figure in M4 §8.3 from
   `DERIVED` to `MEASURED`, including the read-noise numbers that decide whether
   the noise model needs one calibration point or two.

2. **PRNU — and this is the more important one.** M4 measured the *offset*
   fixed-pattern floor at 0.377 DN and showed it never binds in a normally
   exposed frame. It could say nothing at all about **PRNU**, the per-pixel gain
   variation, because a dark frame has no signal for a gain to act on. PRNU is
   multiplicative, grows with signal, and does **not** average away. At a
   textbook 0.3–1% and a mid-tone of 5000 DN it would be 15–50 DN of fixed
   pattern against 7.6 DN of 20-frame-averaged shot noise — two to seven times
   larger than the noise it competes with, sitting exactly in the lit,
   low-contrast regions where M2 measured the argmax defect.

   If PRNU is at the high end, averaging in lit regions asymptotes just as raw
   dark-frame averaging does, and the merge stage needs flat-field correction
   and not merely bias subtraction. **That is a design-changing possibility that
   is currently unmeasured in either direction.**

   **Method correction (found while re-checking this spec; the original recipe
   was wrong).** This entry previously said to estimate PRNU as the per-pixel
   temporal mean divided by **the frame mean**. That does not work. Dividing by
   a single global scalar leaves **vignetting** — a smooth, low-spatial-frequency
   gain roll-off — entirely intact in the residual, and vignetting across a full
   frame is typically several percent, an order of magnitude larger than the
   0.3-1% PRNU being measured. The resulting map's standard deviation would be
   almost pure vignetting, and would have "confirmed" a large PRNU no matter
   what the sensor actually does.

   **Correct procedure:** normalise each per-pixel temporal mean by a **smooth
   low-order surface** fitted to (or a heavily blurred copy of) that same flat,
   so only pixel-to-pixel structure survives. Then remove the residual temporal
   noise in quadrature — `sd_PRNU^2 = sd_measured^2 - sigma_temporal^2 / N` —
   rather than ignoring it. Confirm PRNU by its defining signature: it is
   **multiplicative**, so `sd_PRNU` must scale **linearly with signal level**
   across the seven exposure levels. A fixed pattern that does not grow with
   signal is offset FPN, which M4 already measured, not PRNU.

   **16 frames per level is sufficient** for this. PRNU is fixed, so only the
   temporal term shrinks, and with ~8.2M plane pixels the standard-deviation
   estimate is precise to well under 0.05% — the quadrature subtraction, not the
   frame count, is what has to be right.

   **One capture-side consequence: do NOT clean the sensor before shooting these.**
   Dust motes render sharply in a flat field and appear as localised dark blobs.
   They are spatially clustered, so the smooth-surface normalisation above will
   *not* remove them, and they would be counted as PRNU — so they must be masked
   before the PRNU statistic is taken. But they are no longer only a nuisance:
   M29 makes the dust map a **deliverable**, and cleaning the sensor first would
   destroy the only evidence of the dust that is in the existing corpus.
   **Shoot the flats dirty, mask for PRNU, keep the mask as the dust map.**

3. **The dust / static-defect map — added by M29, and now a specification
   rather than a request.** M29 established three things that together make this
   the only way to get dust at all. The merge does **not** dilute it (`D = 0.999`
   at `n_eff ≈ 3`, fact 230, so it must be handled explicitly); it **cannot** be
   detected from subject stacks (limit 32–50% shadow depth against real dust of
   1–15%, fact 232); and the floor that blocks it is **scene texture, which does
   not fall with frame count** (exponent +0.025 over a 16× sweep, fact 233). A
   flat has `g/blur(g) ≡ 1` by construction, which is exactly the factor that
   attenuates the response on a subject (`R ≈ 0.92·g/blur(g)`, fact 231).

   **Specification, from the calibrated noise model with no free parameters:**

   | frames | floor | a 5% shadow is |
   | --- | --- | --- |
   | 8 | 0.190% | 26σ |
   | **16** | **0.134%** | **37σ** |
   | 20 | 0.120% | 42σ |
   | 64 | 0.067% | 75σ |

   at ISO 100 with the mid-tone at **8,000–12,000 DN**. The §4 set above already
   satisfies this at its upper levels, so **the PRNU set doubles as the dust set
   at no extra cost** — nothing additional needs shooting for the f/8 case.

   **What does need shooting separately: one short set per working aperture.**
   Dust visibility scales with aperture — a stopped-down lens renders motes
   sharply, a wide one smears them — so a map measured at f/8 does not transfer
   to f/16. **16 frames at one level (8,000–12,000 DN), at each aperture you
   actually shoot.** Changing only the aperture between sets means the exposure
   must be re-metered each time; that is fine, only the level matters.

   **Timing caveat, and it is a real limitation.** Dust moves. A map measured
   today describes the sensor today, and **cannot be applied to the existing
   corpus**, which was shot months earlier. Flat fields correct the stacks shot
   near them in time and nothing else. This is not a reason to delay — it is a
   reason to shoot a short flat set as *routine practice* alongside real work,
   which is cheap enough (16 frames, one level) to be habitual.

---

**STOP -- READ THIS BEFORE SHOOTING THE FLATS (added 2026-08, before capture).**

Your optical path includes a **Breakthrough X4 CPL circular polariser**, which was
not known when the section above was written. It changes this capture in two ways
and one of them will quietly ruin it.

1. **Do not shoot a sky flat through the polariser.** Blue sky is strongly
   linearly polarised, and the degree of polarisation varies across the sky with
   angle from the sun. A CPL pointed at it imposes a large, rotation-dependent
   brightness gradient across the frame. **That gradient would be recorded as if
   it were the lens's vignetting**, and every frame divided by the flat would then
   be wrong in a smooth, plausible-looking way that is very hard to detect
   afterwards. Shoot against an **unpolarised diffuse source** instead: an
   electroluminescent panel, a white surface lit by several sources, or several
   layers of diffuser over a window -- **not** open sky.

2. **Shoot the whole set TWICE -- once with the filter on, once with it off.**
   This replaces the earlier instruction to simply leave it on. You have since
   confirmed the polariser was **not** on for every stack, and the EXIF dates make
   the split a clean rule: everything from **25 May onward is CPL-on**
   (`coffee-bubbles`, `foam`, `wrapped-text-1/2`, `bee-1/2/3`), everything up to
   **17 May is CPL-off** (`112`, `113`, `119`, `109`). `coffee-bean` (10 May) sits
   on the off side of the boundary but you could not recall it, so it is unknown.

   A flat describes an *optical path*, not a sensor. **One flat therefore cannot
   cover this corpus** -- applying the CPL-on flat to the May stacks would divide
   out vignetting that was never there. The two sets differ only by whether the
   filter is mounted; change nothing else, and do not rotate it between them.
   Cost is one extra set of the same shots.

   Doing both also delivers something better than a correction: **the ratio of the
   two flats IS the polariser's transmission map**, measured on your own copy of
   the filter. That prices the confound instead of caveating it forever, and it is
   free once both sets exist.

If an unpolarised source is not practical, **shoot the filter-off set only, and
skip the filter-on set entirely.** A flat without the filter is valid; a flat with
the filter against sky is not -- and a wrong flat is worse than no flat, because
it corrupts smoothly and plausibly rather than obviously.

---

## 5. Deep stacks with deliberate scene variation — REQUESTED

**Status:** requested. Not urgent, not blocking anything today, but **two
separate open questions now need the same capture**, so one afternoon of
shooting closes both.

**Why.** The corpus is five stacks, and two independent results have run out of
road on exactly that:

- **Fact 53 — the shrinkage mechanism is unexplained.** Short-baseline alignment
  edges under-report magnification change by anywhere from **1.03x to 3.26x**,
  and it is a property of the *scene*, not the optics (fact 51). Ten candidate
  predictors were tested against the edge sets and **none** of them predicts
  which stacks shrink. With five stacks, no correlation can reach significance —
  the critical value is ρ = 0.600 at n = 5.
- **Question 18 — one cell behaves unlike every other.** The `119MSDCF`
  horizontal texture pair puts its focus-window optimum at w8 at *all five*
  depth steps, the only cell with a constant argmin, and it is the source of
  every head-to-head loss the recommended window suffers. One texture pair per
  stack cannot tell an occlusion-geometry effect from a texture effect.

Both are asking the same question: **which property of a subject drives this?**
That cannot be answered by analysis, only by more stacks that vary the property
on purpose.

### What to shoot

**8-12 stacks**, same rig and same method as the existing corpus (in-camera
focus bracketing; no rail needed). Depth 40+ frames each so the long-baseline
anchors exist. The point is **deliberate variation**, so vary these on purpose
rather than shooting a dozen of the same thing:

| Axis | Span it |
| --- | --- |
| **Subject depth** | Something almost flat (a coin, a leaf face-on) through something deep (a flower head, a pine cone, an insect). This is the axis most likely to matter and the corpus barely varies it. |
| **Texture scale** | Fine high-frequency detail (fabric weave, sand, chitin) *and* smooth low-contrast surfaces (a petal, a polished shell). |
| **Occluding edges** | At least three subjects with **genuine occlusion** — a near element in front of a far one with real separation, e.g. a stem crossing in front of a background, or hairs standing off a surface. This is the configuration the whole window result turns on and the corpus has almost none of it. |
| **Depth-gradient direction** | Not everything front-to-back. Include subjects whose depth runs left-right and diagonally. `119MSDCF`'s anomaly is specifically in a *horizontal* geometry. |

**Keep constant:** aperture, ISO, lighting and magnification within each stack,
as now. Vary them *between* stacks if convenient — that is useful, not harmful.

**Note the subject in the folder name** (e.g. `pine-cone-deep`,
`petal-smooth`, `stem-occlusion`), because the whole point is correlating
behaviour against subject properties, and EXIF does not record what was in
front of the lens.

**Do not** shoot the same subject twice at different densities and label it two
stacks — fact 50 records how that misled us once already, and fact 69 records a
directory mirrored to a second path being mistaken for a second sample.

---

## 6. Dark frames at working exposure — REQUESTED, very cheap

**What:** the same lens-cap routine you already did, but at the **shutter speeds
you actually shoot**, not 1/100 s. 12–16 frames at each of roughly 1/8 s, 1 s
and 2.5 s. ISO can stay at one value (160 is representative); exposure time is
the variable that matters here, not gain. Lens cap on, body cap is even better,
in a dark room. The first two frames are still discarded, so shoot 14–18.

**Why:** the 242 darks you delivered are all **1/100 s**, but your real stacks
run from 1/60 s to 2.5 s — up to **250×** longer
([M22](research/M22-hot-pixels-measured.md) §4). Dark current accumulates with
time, so a pixel with moderate dark current is invisible at 10 ms and plainly
visible in a 1.3 s frame. The delivered set is a complete map *for the wrong
exposure*.

This is not hypothetical. A cross-scene test with a shift control finds roughly
**839 scene-independent defects** at a 4σ bar, of which the 1/100 s map contains
**5** (M22 §5).

**What it unblocks:** a correct hot-pixel map, and the offset term that goes with
it. Note this is a **low-urgency** request — M22 measured the in-situ impact of
the currently-known defects at ≤ 0.39σ, so nothing is being held up. It is listed
because it is nearly free and because the existing darks cannot answer it.

**What it does NOT affect:** M4's read-noise and FPN results are
exposure-independent and stand as measured.

**Corroborated, and the argument for it is now stronger** (M48c, 2026-08). An
independent census of the same darks by a different criterion finds 0.0414% of
pixels defective (M22 found 0.0346%), 99.8% of them isolated singletons with the
largest cluster on the sensor being 3 pixels -- so the subsystem this unblocks is
a coordinate list and a neighbour median, nothing more. What changed is the case
for building it at all: the merge was measured against a contrast-matched control
and its defect-specific amplification is **1.00 +/- 0.08**. It lifts a hot pixel
and genuine detail of the same contrast by the same factor. **The estimator will
never remove these, so they cannot be left to it.** The urgency is still low --
in-situ impact is <= 0.39 sigma -- but the request is no longer only about
completeness.

**One near-free addition, if you are shooting this anyway.** Shoot the same
frames a second time at **ISO 1000** as well as at ISO 160. Cost: one dial, same
session, same cap. Why: the delivered darks turned up a **2.17x step in
dark-current electrons falling exactly at the ISO-400 dual-gain switch**, which
says the shipped DN-to-electron conversion is extrapolated above ISO 400 (facts
790-795). A long exposure makes dark current 100-250x larger, so the same step
measured there has far better signal than the 1/100 s frames could give it, at a
completely different exposure. If the step is an artefact of the short exposure it
will not survive; if it is a conversion-gain property it will reproduce. Either
outcome is worth the dial.

---

## 7. Aperture pair — REQUESTED, cheap, high value

**Status:** requested. One afternoon. Turns §0's derived table into a
measurement, and §0 is currently the largest quality claim in the project
resting on a model rather than on data.

**What to shoot.** One subject, two brackets, back to back, nothing else changed:

| | Bracket A | Bracket B |
| --- | --- | --- |
| Aperture | **marked f/11** (as currently shot) | **marked f/5.6** |
| Frames | as you would normally shoot it | **about 2x** bracket A |
| Depth covered | identical | identical |
| ISO, lighting, magnification, subject | identical | identical |
| Exposure | metered normally | metered normally (it will be shorter) |

Choose a subject with **fine high-frequency detail** — chitin, fabric weave,
sand, hairs. Smooth subjects cannot show the difference because they have no
energy at the frequencies diffraction is removing.

**Do not** try to match total exposure time or total light between the two.
The comparison the project needs is the one a photographer would actually make:
the same subject, shot the way each aperture wants to be shot.

**What it settles.** Whether the 9.6x contrast figure in §0 survives contact with
a real lens. The model assumes a diffraction-limited system; a real lens at f/5.6
also has aberrations that f/11 suppresses, and the model does not know about
them. If aberrations dominate at f/5.6 the advantage shrinks — and that is
exactly the number nobody has.

If it is convenient, a third bracket at **marked f/8** makes it a curve rather
than a pair.

### Added by M35 — frame count is now load-bearing, and it settles a second question

**This same shoot also answers question 70**, but only if the brackets are
**denser than normal**. Shoot **at least 2.5× your usual frame count** for the
subject — roughly **80–120 frames** rather than 30–40 — at each aperture.

The reason is a gate M33 wrote and M35 applied. A dense bracket is used as its own
ground truth by decimating it and asking what the sparser version lost; that is
honest only if the dense grid's **own** sampling deficit is much smaller than the
one being measured. `coffee-bean` (105 frames) clears it at **3.62×**.
[M35](research/M35-fit-generality-measured.md) measured the two existing stacks
that would otherwise have answered question 70 and **both failed**:

| stack | frames | marked f | headroom | |
| --- | --- | --- | --- | --- |
| `119MSDCF` | 33 | f/5.6 | **2.18×** | ❌ too coarse to be its own reference |
| `112MSDCF` | 79 | f/11 | **2.10×** | ❌ too coarse to be its own reference |

So the aperture question cannot be answered from what is already on disk, and the
shortfall is frames, not light. `119MSDCF` also has **7.38%** of its pixels
peaking at the very edge of the bracket, which means the 33 frames did not cover
the subject's depth at all.

Practically: pick a subject shallow enough that 100 frames still covers it
comfortably end to end, and let the bracket run past the subject on both sides.
Depth coverage and frame density are both required; neither substitutes for the
other.

---

## 8. Tilted planar target — REQUESTED, cheap

**Status:** requested. Not blocking, but it is the only source of **analytic
ground-truth depth** available without a rail, and the project currently scores
every depth and merge result against plants it made up itself.

**What to shoot.** A **flat, densely textured, rigid surface**, positioned at a
steep angle to the sensor plane so that focus sweeps across it, captured as an
ordinary in-camera focus bracket.

| | |
| --- | --- |
| Target | Flat and rigid: fine sandpaper, a printed noise/grid pattern on card, a banknote, a ceramic tile with texture. **Not** paper that can curl. |
| Texture | Dense and broadband. A printed random-dot or noise pattern is ideal; a regular grid is acceptable but aliases. |
| Angle | Steep — roughly **30-60 degrees** to the sensor plane, so the near and far ends of the frame are several depths of field apart. |
| Frames | 40+, covering near edge to far edge. |
| Aperture | Shoot it **twice**, at marked f/5.6 and marked f/11, if that is cheap. This makes it serve §7 as well. |
| Also record | Roughly what the tilt angle was, and the approximate near and far distances. Rough is fine — the *planarity* is what matters, not the numbers. |

**Why it is worth an afternoon.** A plane is the one subject whose true depth map
is known in closed form up to three parameters, and those three parameters can be
fitted from the data itself. So:

- **Depth accuracy becomes measurable**, not merely plausible. Fit a plane to the
  estimated depth map; the residual *is* the error, per pixel, with no oracle.
- **The confidence map becomes testable.** Confidence claims to predict where the
  estimate is wrong. On a plane that is a direct check: does predicted uncertainty
  correlate with actual residual?
- **It is a null for occlusion.** A plane has no depth discontinuities anywhere,
  so any bimodality, halo or occlusion flag the pipeline raises on it is a **false
  positive**, by construction. The project has no such null today.
- **It calibrates the focus axis.** Depth is linear across the frame, so the
  fitted per-frame focus position must be monotone and smooth — an independent
  check on fact 54's pixel-measured focus index and on the depth-from-breathing
  idea.
- **It is the only thing that makes per-pixel focus *admission* correctness
  measurable on real frames.** M67 measured whether the shipped merge admits the
  frames actually in focus at each pixel — `H` = 99.955 % on a simulated tilted
  plane — and could not run that measurement on a single real stack, because
  `H` needs a per-pixel true in-focus index and no corpus stack has one. A plane
  supplies it without an oracle: fit the three plane parameters from the data,
  convert to a per-pixel focus index, and `H`, the miss distance and the
  admitted-set defocus all become real numbers instead of simulated ones. That
  converts M67's headline from an **idealised-PSF upper bound** into a
  measurement. See `docs/research/M67-focus-correctness.md` §8.
  **For this use the two f-stops matter more than usual** — the whole
  uncertainty in M67's result is optical, and a second aperture is a second
  through-focus curve to check the merge against.

**One trap.** Fill the frame with the target and nothing else. A visible edge,
background or mount reintroduces exactly the depth discontinuity the null is
supposed to exclude.

---

## 9. Corpus locations — read-only

**Never write to any of these.**

| Path | Contents |
| --- | --- |
| `C:\dev\macro\test\` | The original three stacks: `109MSDCF` 22, `119MSDCF` 33, `coffee-bean` 105. |
| `D:\macro-dark-frames\` | 11 ISO subdirectories x 22 frames = 242 darks. §1. |
| `D:\personal\macro\` | Seven stacks. Three are **byte-identical duplicates** of `C:\dev\macro\test` (verified by count, size and MD5) — do not treat them as independent evidence. Four are new. |

The four new stacks, all on the same rig (`LensType3` 33094), characterised in
fact 49:

| Stack | Frames | Focus sweep | Pace | Use |
| --- | --- | --- | --- | --- |
| `112MSDCF` | 79 | 0.3189 → 0.3297 m | 0.51 s/frame | **The fact-43 pair.** Same subject and same sweep as `113MSDCF`, preview-NCC **+0.9961**. Fit the span-dependent shrinkage on one, test on the other. |
| `113MSDCF` | 63 | 0.3189 → 0.3297 m | 0.52 s/frame | As above. |
| `foam` | 100 | 0.2707 → 0.2841 m | 2.52 s/frame | **Not an alignment benchmark.** The scene evolves across the 249-second capture: it decorrelates *within itself* to 0.087/0.122/0.243 where `coffee-bean`, an equally deep sweep, holds 0.979/0.941/0.970. Useful only as a hard case for non-rigid scenes. |
| `coffee-bubbles` | 19 | **none** (0.2841 m throughout) | 3.33 s/frame | A *soft* null for the aligner — at fixed focus any reported transform is drift or estimator bias, not parallax. Contaminated by real bubble motion (0.947 first-to-last), so it bounds bias from above rather than measuring it. |

---

## 10. Two frames at ISO 64 — REQUESTED, trivial, closes a guess in shipped code

**Status:** requested 2026-08-23. **Thirty seconds of work.** It is the only
item in this file that removes a constant I had to guess at rather than measure.

**What to shoot.** Point the camera at anything with a bright area — a window, a
lamp, a sheet of paper. Then, **without moving anything or changing exposure**:

- 2 frames at **ISO 64**
- 2 frames at **ISO 80**
- 2 frames at **ISO 50** and 2 at **ISO 100** as the brackets

Any subject, any aperture, handheld is fine. It does not need to be sharp, flat,
or well-composed. It needs *signal* and it needs the four ISOs to see the same
scene. Untouched RAW.

**Why.** Sony ISO 50 is an **extended / pull** setting: the sensor reads out at
base-ISO-100 analogue gain and the stop is taken in exposure. So `g = ISO/436.8`
is wrong by **2.05×** at ISO 50, which corrupts the noise floor the merge gate is
denominated in — measured, and fixed in `2a4f5c5` by clamping `g` at a
`base_iso` of 100.

**But the clamp's location is a guess.** ISO 50 is measured wrong and ISO 100 is
measured right. **The corpus contains nothing in between**, so `max(ISO, 100)` is
the simplest rule consistent with the evidence, not a located transition. ISO 64
and 80 are the only two settings between them. Two frames each and the guess
becomes a measurement.

**How it will be read.** Per-pixel temporal variance across the frame pair at
matched mean, compared against the ISO 50 and ISO 100 brackets. If ISO 64 reads
at the ISO-100 level it is also a pull setting and the clamp is right. If it
reads at 64/436.8, the clamp is wrong and the transition is real.

**One trap.** *Do not* change shutter or aperture to compensate for the ISO — let
the frames get brighter. The measurement compares noise at a **known analogue
gain**, and re-exposing to equalise brightness destroys exactly the difference
being measured.

## 11. Dark frames at ISO 160 -- REQUESTED, trivial, closes a hole in a shipped constant

**Cost: about a minute, indoors, lens cap on. No daylight, no subject, no rail.**

`read_noise_e_low = 4.20` is a shipped sensor constant. It governs every frame the
camera takes below ISO 400, and in this corpus that means **ISO 50 and ISO 160**.

It has been checked at ISO 50 and ISO 100 and is accurate there (-2.5% and -2.3%).
**It has never been checked at ISO 160**, because the 242-frame dark set delivered
earlier has no ISO-160 row -- while the corpus has **22 real captures** at that ISO.
The constant is validated everywhere except the setting it is used at most.

This is not expected to be a large error. It is a hole in a claim, and the claim is
cheap to close.

### What to shoot

**22 frames at ISO 160, lens cap on, in a dark room, same shutter speed as the other
dark sets.** Identical procedure to the darks already delivered:

- Lens cap on, and the body's own cap if the lens is off. Total darkness matters more
  than the room being dark -- any light leak invalidates the whole set.
- **Discard the first two frames.** The earlier set was shot this way and it was the
  right call; the sensor settles.
- Same shutter speed and same body temperature regime as the existing darks, or the
  comparison against ISO 50 and ISO 100 is not like-for-like.

### Why this cannot come from existing files

Read noise is measured from frames with **no signal**. Every ISO-160 frame in the
corpus is a photograph of something, so its variance is dominated by shot noise from
the subject. There is no way to recover a read-noise floor from a lit frame at the
precision this needs. The 242 delivered darks cover ISO 50, 100, 200, 250, 320, 400,
500, 640, 800, 1600 and 2000 -- **160 is the gap, and it is the one that matters.**

### What it unblocks

Answers question 172 and closes fact 732. Either the constant is accurate at ISO 160,
in which case a shipped number stops being a guess at the setting it is used at most,
or it is not, in which case the corpus has been carrying a measurable error on 22 of
its frames and the shape of the correction becomes visible.

**One trap.** Do not change the ISO by using a different exposure mode that might pull
or push. Set ISO 160 explicitly. The whole point is the analogue gain at that specific
setting, and an ISO the body reaches by a different route is a different measurement.

**M69 corroboration (2026-08).** M69 re-measured read noise on the delivered darks
across 11 ISO groups and found the shipped model over-predicts it by **8-27%** at
every ISO measured -- empirical read noise runs 0.73x-0.92x the model's `RN*g`, and
the deficit grows with ISO (0.9225 at ISO 50 and 100, 0.7306 at ISO 1600). ISO 160
is still the gap, it is still the ISO of M62's own certified plant, and the
discrepancy this would resolve is now known to be larger than "not expected to be a
large error" assumed. See
[`docs/research/M69-focus-noise-sd.md`](research/M69-focus-noise-sd.md) fact 24.


## 12. Static repeat burst -- REQUESTED, 30 seconds, highest value per unit effort

**Status:** requested 2026-08, in response to the owner asking what else would
help. **Nothing in the corpus can substitute for it and nothing else on this list
is as cheap.**

**M69 corroboration (2026-08, urgency raised).** M69 was chartered on the
understanding that this burst had been delivered. It has not. M69 established
that the quantity `FOCUS_NOISE_SD` measures -- the response noise of the focus
operator -- **is not measurable at all from a focus sweep**, at any effort, by
any estimator of the family tried: macro depth of field is one to two frames
wide by design, so a per-pixel through-focus curve is a narrow peak that no
smoothing window wide enough to average down the noise can follow. M69's arm A5
was voided by its own pre-registered control for exactly this reason. This is the
difference between *not measured* and *not measurable*, and it now blocks a
shipped constant that every gate, every published `n_eff`, `DEFAULT_GATE = 4.0`
and the certified acceptance result are denominated in. See
[`docs/research/M69-focus-noise-sd.md`](research/M69-focus-noise-sd.md) facts
26-27.

**One clarification, because the two claims look contradictory.** M62 found that
a static burst has **no focus variation and therefore no interior optimum**, so a
burst cannot arbitrate a *gate*. That is correct and it does not weaken this
request. A burst is the only capture that can arbitrate a *noise level*, and for
precisely the same reason: with focus held still, every frame-to-frame response
difference is noise by construction. The two findings are complementary.

**A second, sharper argument, added after M69's amendment.** Every synthetic
replicate experiment in this corpus freezes a single real frame as its latent.
But a real frame is `T + eta`, so the frozen latent carries `2 s^2` of gradient
energy that the true scene does not, and every response-noise number measured
that way is inflated by it. M69 measured the size of that inflation by planting
extra frozen realisations and watching the number climb (its facts 39-40): on
M62's own plant it accounts for roughly a quarter to a half of the excess. **The
defect-free latent cannot be constructed from one frame at all** -- the only way
to observe a scene without a frozen noise realisation in it is to average many
frames at one focus position, which is exactly this capture. Until it exists,
every replicate study in the corpus carries a bias whose size can be estimated
but not removed.

### What to shoot

| | |
| --- | --- |
| Subject | **A real macro subject with fine texture** -- any of the ones already shot is ideal. Not a test chart, not a flat surface. |
| Frames | **30**, back to back. |
| Focus | **Do not touch it.** No bracketing, no refocus, no drift. One focus position for all 30 frames. |
| Everything else | **Change nothing.** Same aperture, same ISO, same shutter, same light, tripod, electronic shutter or 2-second self-timer. |
| Exposure | **A working exposure** -- whatever you would really use, in the 1/8 s to 2.5 s range the real stacks use. |
| Format | RAW (.ARW), all noise reduction off. |
| Repeat | If cheap, do the same 30 frames again at **ISO 400** without moving anything. |

Discard the first 2 frames, as with the darks.

### Why this is worth more than another focus stack

**It is the only capture that gives the merge a problem whose right answer is
known exactly.** Every frame is a sample of the *same* latent image, so the true
merge output is the scene itself and the true noise reduction is exactly
`sqrt(N)`. Nothing else in the corpus has that property: in a focus stack, every
frame differs both in noise *and* in focus, and the two cannot be separated
without a model -- which is the very thing under test.

That gives four things at once, none of which the project currently has:

1. **An empirical null for the entire estimation thesis.** The merge must return
   `sqrt(30)` = 5.48x noise reduction here. Any shortfall is the estimator's own
   inefficiency, measured directly rather than argued. The corpus currently prices
   the gated mean at 0.534x (fact 19) against a *reference* that is itself
   estimated; this measures it against arithmetic.
2. **A placebo that can actually fail.** Discipline 250 records that this corpus
   has already shipped three checks incapable of failing. A merge that secretly
   selects rather than estimates will score ~1.0x here while a true estimator
   scores 5.48x. **No existing test separates those two outcomes.**
3. **Sigma at working exposure, which no delivered capture provides.** The 242
   dark frames are all 1/100 s, but real stacks run 1/8 s to 2.5 s -- a 12x to
   250x longer integration. That gap is the binding limitation on the whole
   sensor model (fact 808: only ~5 of ~839 real defects appear in the dark map).
   A repeat burst measures the per-pixel temporal noise at the exposure that
   actually matters, and does it on a real scene rather than in the dark.
4. **The hot-pixel and dust map at working exposure, for free.** Both are fixed in
   sensor coordinates and both survive averaging over a static burst, so they
   stand out against a scene that does not move. This is the capture that makes a
   defect map possible, and fact 800 established the merge is blind to defects
   (D_defect/D_control = 1.00 +- 0.08) and therefore cannot be relied on to hide
   them.

**The ISO 400 repeat, if taken, straddles the dual-gain boundary on a fixed
scene** -- the same instrument as `bee-2`/`bee-3` (fact 847) but with focus held
constant too, which removes the last confound from question 184's split.

### 12b. A second contrast level on the same static burst -- REQUESTED by M69

**Cost: 30 more frames, same session, same setup, one thing changed.**

If §12 is shot, shoot it **twice more on the same subject at two clearly
different contrast levels** -- easiest by changing the light (diffuse versus
raking) rather than the subject, so the texture's *spatial* statistics are held
and only its *amplitude* moves. Focus untouched throughout, as above.

**Why one contrast level is not enough.** M69 measured that the focus operator's
response noise does not vary with signal-to-noise the way the shipped model
assumes. It varies by **4.06x** on a controlled plant -- from `0.28x` to `1.14x`
the shipped constant -- driven by whether the deterministic gradient *direction*
stays coherent across the operator's 27x27 window, not by contrast. A burst at
one contrast level measures a point; two levels on the same texture separate the
two candidate mechanisms M69 could not separate:

- **direction coherence** (M69 fact 19, DERIVED) predicts response noise barely
  moves between the two contrast levels, because the texture's geometry is
  unchanged;
- **rectification of a noisy gradient** (the pointwise model M69 refuted, and the
  one the shipped constant implicitly assumes) predicts it rises with contrast
  toward a fixed ceiling.

They differ by a factor of about three on this capture and by nothing at all on a
single-contrast burst. **This is the capture that decides whether the shipped
scalar can be replaced by a derived per-pixel field**, which M69 fact 32 prices as
a 1.09x-1.72x change in `n_eff` -- 20 to 50 times larger than correcting the
constant's value.

**One trap.** Change the light, not the exposure. Re-exposing to compensate
restores the amplitude and measures nothing.

---

## 13. Three variations on stacks you have already shot -- REQUESTED, cheap

Each is one stack, and each buys something structural. Roughly in value order.
All three should be shot **with the polariser in a known, recorded state**.

**13a. Half-step interleave.** Reshoot any subject you have already stacked, with
the focus step **halved** -- or simply shoot the same range twice, the second pass
offset by half a step. Doubling the sampling density along the focus axis is what
lets a reconstruction-based merge recover detail between frames rather than
picking the best of them. It also directly tests whether the current step size is
already adequate, which is currently assumed and never measured.

**13b. Without the teleconverter.** The same subject at 100 mm, **2x TC removed**.
Every stack in the corpus is at 200 mm with the converter fitted, so the
converter's contribution to the point-spread function is entangled with the
lens's and neither has ever been observed alone. This separates them, and it tests
the `N_eff = N_marked * (1 + m/p)` model at a genuinely different magnification
instead of extrapolating it.

**13c. A deliberate occluding edge.** A pin, wire, bristle or blade of grass held
**in front of** a well-textured background at a clearly different depth, then
focus-bracketed through both. Occluding edges are where every focus stacker on the
market produces halos, and the corpus contains them only incidentally, never by
design. A capture that isolates one turns the halo from an anecdote into a
measurable quantity with a known correct answer -- the background is genuinely
visible in some frames, so the truth is recoverable.

---

## 14. What is NOT needed, so you do not waste a session

- **Another ordinary focus stack of a new subject.** The corpus has 12 stacks and
  1,568 frames. More of the same adds subjects, not information; every item above
  adds a *degree of freedom the corpus currently cannot separate*.
- **Anything requiring a focus rail.** Deferred permanently, per section 2.
- **Higher-resolution or more careful versions of existing stacks.** Nothing on
  this list is blocked by capture quality.
