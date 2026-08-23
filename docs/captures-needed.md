# Captures needed from the owner

Measurements that are blocked on data no existing file can supply. Each entry
says exactly what to shoot, why, and what it unblocks.

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


## 4. Flat fields — SCHEDULED

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

   **One capture-side consequence: clean the sensor first.** Dust motes render
   sharply in a flat field and appear as localised dark blobs. They are spatially
   clustered, so the smooth-surface normalisation above will *not* remove them,
   and they would be counted as PRNU. If any remain they must be masked before
   the statistic is taken.

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

## 6. Corpus locations — read-only

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

