# M109 — highlight clipping: pre-registration

Written **before** any render, any build, and any edit to `crates/`. Working tree at
`2c13138b4ac6b5e5588ae3f40ebbd001de8e2ce3` (`M108: re-verify A/B/C against the new schema, and add check F`).
`color.rs`, `image_out.rs`, `stack.rs`, `main.rs` all clean at that SHA — no other agent is mid-edit in them.

Rule 20 binds this document: every bar below states the input that would make it **FAIL**.
Discipline 706 binds B3: a control that has never been shown to fail is not a control.

---

## 0. The defect, and the render path it lives in

`strehl stack --srgb` renders blown neutral highlights **magenta**. ORCH measured 2.002 % of a
33 MP render of `dry-erase-marker-head-cpl` affected, against an independent LibRaw decode that
renders the same region neutral white.

**Operation order, read from source, not assumed.** `strehl stack` dispatches to
`merge_cmd::run` → `merge_cmd::write_merged` (`merge_cmd.rs:2733`), **not** `stack.rs`:

1. `norm(raw, gain) = (raw - levels.black).max(0.0) * gain * exposure_gain / levels.range()`,
   `range = white - black = 15360 - 512 = 14848`. **Deliberately not clamped above.**
2. co-siting (`image_out::develop_binned`, red `+0.25`, blue `-0.25`, Keys `a = -1/2`) or
   Malvar–He–Cutler demosaic (`image_out::write_demosaiced`).
3. `color::apply(matrix, lin)` — the camera → linear-sRGB matrix.
4. `clamp(0, 1)`.
5. `color::srgb_encode`, then `(x * 65535 + 0.5) as u16`.

So: **black → green-normalised as-shot WB → exposure gain → resample → matrix → clamp → curve →
quantise.** The only clamp is at step 4, *after* the matrix; `image_out.rs`'s module doc defends
that placement ("clipping before the matrix would clip in the wrong space and shift hue"), and for
in-gamut colour it is right. It is wrong for a **container-pinned** sample, which is not a colour
measurement at all.

**Root cause (DERIVED from the code above, CONFIRMED numerically in `src/mechanism.py`).**
`levels.white` is 15360 but the container saturates at `CONTAINER_MAX_DN = 16383` (`clip.rs`, which
says in bold *do not unify them* — this fix does not). A pinned sample therefore lands at
`K0 = (16383 - 512) / (15360 - 512) = 1.068898` in render units, times its WB gain and the exposure
gain. Green's gain is 1.0 by construction; red's is 2.687 and blue's 1.532. So green stops at
`1.0689 · eg` while red and blue are carried to `2.87 · eg` and `1.64 · eg`. Step 3's green row
`[-0.1152, +1.4890, -0.3738]` is then dominated by the *unpinned* red and blue terms, green lands
below 1, red and blue clamp at 1 — **magenta**.

Feeding fact 1432's own raw means through this reproduces ORCH's triple:

| | R | G | B |
|---|---|---|---|
| `mechanism.py`, single point | 1.0000 | 0.8947 | 1.0000 |
| fact 1432, region mean | 0.9944 | 0.8915 | 0.9943 |

---

## 1. Predicates, fixed now

**Magenta fraction** `f_m`. On the written 16-bit TIFF, scaled to `0..1` by `/65535`, over **all**
pixels, the fraction satisfying `(R - G > 0.06) && (B - G > 0.06)`. This is ORCH's predicate from
`experiments/ORCH-drift-check/marker_wholeframe.py`, adopted verbatim so the before number is
comparable. No ROI: discipline 713 — let the predicate find the region.

**Green deficit** `d_g = max(R - G)` over the same pixels. Reported alongside `f_m` because `f_m` is
a thresholded statistic and can be gamed by a change that moves pixels to 0.0599.

---

## 2. Bars

### B1 — headline. Magenta must go.

`f_m` on `dry-erase-marker-head-cpl` must fall from **2.002 %** to **< 0.10 %**, and `d_g` from
**0.4490** to **< 0.10**.

*Fails if*: `f_m` stays above 0.10 %, or `d_g` above 0.10, or if the fix clears `f_m` by darkening
the render (guard: the 99th-percentile green of the after-render must stay within ±0.02 of before).

**B1 has two arms because of a file-ownership blocker, declared here in advance:**

* **B1-stack** — ORCH's exact reproduce command. The fix cannot reach it without ~3 lines in
  `merge_cmd.rs`, which **M97 owns and I may not edit** (§5). If that patch is not routed to me,
  B1-stack records as **BLOCKED**, not PASS and not FAIL, and the report says so plainly.
* **B1-argmax** — `strehl argmax-baseline --srgb`, whose writer (`stack.rs`) I do own. Same scene,
  same colour path, same predicate, run before and after.

**Pre-registered prediction for B1-argmax, and it is not the same number.** `argmax-baseline` has
**no exposure knob** (`StackOptions`, `stack.rs:166`, has no exposure field), so it renders at
`eg = 1`. `mechanism.py` measured that at `eg = 1` the blob's mean renders `(1.0000, 0.9629, 1.0000)`
— `R - G = 0.0371`, **below the 0.06 predicate**. Negative exposure *amplifies* the defect 2.8×
(0.0371 → 0.1053) because the two clamped channels cannot move down while the pinned one can.
So I predict **B1-argmax's before-`f_m` is well under 2.002 %** — non-zero, because ORCH measured
`d_g = 0.4490` and pixels far out in that tail still trip the predicate at `eg = 1`, but smaller.
I am registering that prediction now so that a small before-number is not read afterwards as the
fix having nothing to do.

### B2 — null. An unsaturated stack must not move by one byte.

`109MSDCF` (22 frames; `clip.rs` documents it as having **zero** saturated pixels) rendered
`--srgb`, SHA-256 before == SHA-256 after.

*Fails if*: a single byte differs. **This bar has already changed the design.** The obvious fix —
clamp every channel at the neutral ceiling unconditionally — is *not* the identity on unsaturated
data: it clips red above `raw ≈ 6420 DN` and blue above `≈ 10863 DN`, and 109MSDCF's maxima are
39–61 % of white, so it would clip real data and B2 would fail. The fix is therefore **conditional**
(§3), which makes B2 hold *by construction* rather than by observation.

### B3 — negative control, shown red before it is trusted.

Plant a defect that expresses **this specific failure**, confirm B1-argmax's harness turns red, then
remove it. The plant: force the ceiling to `+inf` in `color::saturation_ceiling`, i.e. restore
exactly the shipped behaviour while leaving every other line of the fix in place.

*Requirements*: the mutation is anchored on a **unique full-line string** and the script
**hard-errors** if the anchor does not match exactly once (rule 29). Restore is by copy from
`$env:TEMP`, never `git checkout`, and the restored file gets `LastWriteTime = Get-Date` (rule 33).

*Fails if*: the harness still reports PASS with the defect planted. That would mean B1 is measuring
something other than what I think.

### B4 — byte-freeze.

`cargo test -p strehl-cli --test byte-freeze` still passes.

*Fails if*: any frozen hash moves. Predicted to hold **by construction**: both rows in
`byte-freezes.tsv` are `srgb=no`, so they take the `write_rgb16` branch, which no part of this fix
touches. Predicted-by-construction is not evidence, so it is still run.

### B5 — LibRaw cross-check.

Decode `DSC00150.ARW` with `rawpy` (LibRaw) and compare the blob region against strehl's after-fix
render. Not required to match — LibRaw applies its own highlight logic — but a **large residual
disagreement is a finding I must report**. Threshold for "must explain": mean `|ΔR-G|` > 0.05.

### B6 — the owner's eye.

100 % crop montage of the affected region, before and after, to
`C:\dev\strehl-out\M109\`. Per discipline 708 the montage carries an exposure-matched panel so the
change cannot be mistaken for a brightness change.

---

## 3. The fix, stated before it is written

**At any pixel where some channel is at or above its own container ceiling, clamp every channel to
the neutral ceiling, in white-balanced camera space, before the colour matrix. Elsewhere, identity.**

```
ceil_c = K0 * gain_c * exposure_gain          per channel
K      = min_c ceil_c                          the neutral ceiling
if any_c ( v_c >= ceil_c )  then  v_c := min(v_c, K)  for all c
```

Why it renders blown neutral as neutral: `camera_to_srgb`'s rows each sum to 1, so an equal-channel
input is an equal-channel output by construction (`image_out.rs` already has a test for that
property). A blown neutral has all three channels above `K`, so all three become exactly `K`.

Why the null is exact: if no channel reaches its own ceiling the branch never fires, so the
transform is literally `identity` on every pixel of an unsaturated stack.

Why `min(v_c, K)` and not "set all channels to `K`": a pixel where green pins but red is genuinely
low is a blown *coloured* highlight, not a blown neutral. `min` leaves the low channel alone and
keeps the hue direction; "set all" would turn saturated cyan into white.

**The cost, stated up front.** At a pinned pixel the headroom above `K` in the unpinned channels is
discarded. For a genuinely saturated *red* object (red pinned, green and blue low) this desaturates
slightly — `mechanism.py` measures the green output rising `0.0000 → 0.2681`. That is the honest
price: a pinned channel is not a measurement of how red the object was, and preserving `2.87 · eg`
would be fabricating saturation the sensor never recorded.

**Alternatives rejected, with reasons:**

1. **Clamp camera-space at 1.0 as well as after the matrix.** Rejected on measurement: at `eg = 1`
   it happens to work, but the defect is exposure-dependent (`mechanism.py` Q2), so a fixed 1.0 is
   the right ceiling only at one exposure. It also throws away more in-gamut headroom than `K`.
2. **Post-matrix desaturation keyed on out-of-gamut output.** Rejected: it cannot distinguish a
   genuinely magenta object from a blown neutral, because after the matrix the two look identical.
   The ceiling is the only thing that carries "this was pinned".
3. **Data-derived ceiling (detect the green histogram's plateau).** Rejected as too clever for the
   evidence: it introduces an estimator with real failure modes (partial pinning across a 299-frame
   stack, G1/G2 averaging, plateaus that are not clipping) to replace two numbers the decoder
   already knows exactly.
4. **Highlight reconstruction** (estimate the pinned channel from the unpinned ones). Attractive —
   it recovers detail rather than discarding it — but it invents pixels the sensor never measured,
   needs a neighbourhood pass, and needs validation this milestone cannot afford. Recorded as
   follow-up, not attempted.

**Known residual, predicted now.** The blob *interior* should clear exactly. The "coloured fringing
along specular edges" is made of **partially** pinned pixels — green averaged over frames or over
G1/G2 lands just below `K` — and a hard threshold will **not** clear those. I expect a non-zero
residual `f_m` concentrated on edges, and I will report it rather than tune the threshold to hide
it (discipline 710).

---

## 4. Invocations, by value, including defaults (rule 47)

```
CARGO_TARGET_DIR = C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m109
STREHL_ALIGN     = (unset)      STREHL_FIX_HALO = (unset)
STREHL_WARPMAP   = C:\dev\strehl-out\M109\warpmap-m109.txt   (rule 45 isolation)
$ErrorActionPreference = "Continue"

B1-stack  (BLOCKED unless merge_cmd.rs is routed):
  strehl.exe stack "D:\personal\macro\dry-erase-marker-head-cpl" --srgb --auto-exposure
      --gate 4 --out <path>
  defaults in force: --limit unset (299 frames), --demosaic implied by --srgb,
      --binned false, --memory-model m8

B1-argmax:
  strehl.exe argmax-baseline "D:\personal\macro\dry-erase-marker-head-cpl" --srgb --out <path>
  defaults in force: --limit unset, --demosaic implied by --srgb, --binned false,
      --index-map none, --flat-roi none, --memory-model m8

B2 null:
  strehl.exe argmax-baseline "D:\personal\macro\109MSDCF" --srgb --out <path>
  (and, if routed, the same stack via `stack --gate 4`)
```

Every hash recorded in the report carries its full invocation, its byte count, and the commit SHA.

---

## 5. Declared blocker

`merge_cmd.rs` is M97's. The fix is built so that **merge_cmd.rs keeps compiling and keeps rendering
byte-identically without being touched** — `camera_to_srgb` changes return type from
`Option<[[f32;3];3]>` to `Option<color::Render>`, where `Render` is the matrix plus a ceiling that
defaults to `+inf` = "this caller stated no ceiling" = today's behaviour exactly. Activating it on
`strehl stack` is then 3 lines, given in the report for ORCH to route. Until they land, B1-stack is
BLOCKED and the shipped default keeps the defect. I will not edit that file.
