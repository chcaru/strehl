# V-CA-anti — PRE-REGISTRATION

**Committed before any anti-arm data exists.** Commissioned by ORCH to test the *sign* of the
shipped CA correction in the render domain. Scope: one arm. It does **not** reopen the
default-on question; V-CA's verdict remains **NO**.

## 0. A constraint ORCH must know about before results arrive

**I cannot edit `crates/`** — standing instruction, and `optics.rs` is M107's. The anti profile
needs a const there. **Resolution: the patch is applied ONLY inside a detached worktree**
(`git worktree add --detach C:\dev\strehl-out\V-CA-anti-wt HEAD`), built there, used there, and
the worktree is destroyed afterwards. **The patch is never committed and never touches the
shared tree.** If ORCH wants the arm reproducible later, the patch must be routed to M107
separately; this registration records it verbatim so it can be.

## 1. The patch (registered verbatim, applied only in the worktree)

```rust
// beside A7C2_FE100GM_2XTC_X4CPL_RADIAL (~optics.rs:377)
pub const A7C2_FE100GM_2XTC_X4CPL_ANTI: OpticalProfile = OpticalProfile {
    key: "a7c2-fe100gm-2xtc-x4cpl-anti",
    eps_r: 704.5e-6,          // NEGATED. Identical resampling, aberration doubled.
    translation: (0.0, 0.0),
    ..A7C2_FE100GM_2XTC_X4CPL
};
// in profile_from_setting, after the block at :457-459
if raw == A7C2_FE100GM_2XTC_X4CPL_ANTI.key {
    return Ok(Some(&A7C2_FE100GM_2XTC_X4CPL_ANTI));
}
```

**Not added to `PROFILES` (`optics.rs:332`)** — that array is printed as "known profiles" at
`:403`, and advertising a deliberately-wrong correction is a footgun.

## 2. Design — established by code reading, before any render

- **CA is applied at MERGE time, not baked into the sidecar.** `merge_cmd.rs:1031` is the only
  production call of `warp_frame_in_place`; `align_cmd.rs:1399-1456` are Gate W8 test code.
  Confirmed by the sidecar header, which records `resampler` but **no CA field**.
- **Therefore: ONE shared warp sidecar, six merges.** Align cost is zero — I reuse the existing
  `M110-sheet/bee-3-cpl/default.warp.json`. This also removes align as a confound: the *only*
  thing differing between arms is `STREHL_FIX_CA`.
- **Measurement space: the default output — BINNED, LINEAR, CAMERA-NATIVE** (`main.rs:78`).
  **No `--srgb`, no `--exposure`.** Per discipline 847 and ORCH's instruction.
- Subject `bee-3-cpl`, 299 frames. Cost ≈ 53 s/merge × 6 ≈ **5.3 min** plus one release build.

## 3. Arms

| arm | `STREHL_FIX_CA` | role |
|---|---|---|
| `unset` | *(absent)* | reference `H0` |
| `zero` | `0` | inert positive control |
| `off` | `off` | inert positive control |
| `false` | `false` | inert positive control |
| `correct` | `a7c2-fe100gm-2xtc-x4cpl` | shipped correction |
| `anti` | `a7c2-fe100gm-2xtc-x4cpl-anti` | **the test** |

Four inert arms, matching M107b's shape (discipline 919). All four are `Ok(None)` by
`optics.rs:453`. *(`""` is omitted: PowerShell cannot set an empty env var distinguishably from
unset, so it would not be a real fifth arm.)*

## 4. Metric — fixed now, no discretion later

- Stencil: green-plane gradient `|dx| + |dy|`, **top decile**, computed **once on the `unset`
  arm** and reused unchanged for every arm.
- Statistic: `mean |R − Y|` over those pixels, `Y = 0.2126R + 0.7152G + 0.0722B`.
- Reported as **% change vs `unset`**. This is "raw edge chroma (band 0)", the same member
  measured at **−16.00 %** for `correct` in Addendum 5.
- Reader: `tifffile.imread` with `assert a.dtype == np.uint16` immediately after load.

## 5. Predictions — derived, with a conservative floor

From `c10_rings.json` (v15): `bee-3-cpl` uncorrected **−529.9 ppm**; `correct` leaves
**+132.3 ppm** (applied 662.2). Therefore `anti` leaves **−529.9 − 662.2 = −1192.1 ppm**.

| arm | \|residual\| vs OFF | geometric change |
|---|---|---|
| `correct` | 132.3 / 529.9 = 0.250 | **−75.0 %** |
| `anti` | 1192.1 / 529.9 = 2.250 | **+125.0 %** |

`correct`'s −75.0 % geometric gave −16.00 % chroma → transfer **0.213** chroma-% per geometry-%.
Applied to `anti`: **central prediction +26.7 %**.

**PRE-REGISTERED, in advance:**

1. **`anti` edge chroma vs `unset` is ≥ +8.0 %** (worse). Central estimate +26.7 %; floor set
   well below to allow sub-linearity.
2. **`anti` − `correct` ≥ +20 pp.** Central estimate +42.7 pp.
3. **Signs oppose:** `correct` < 0 < `anti`.

## 6. The failure that matters, and the discriminator

**If `anti` comes back indistinguishable from `correct`, the correction is not reaching the
render and this entire audit's measurement chain is inert.** Threshold:
**|anti − correct| < 2.0 pp**.

Hashes (SHA-256 of the output TIFF) tell the two apart — fact 1775 / discipline 918:

| prediction | meaning if it holds | meaning if it fails |
|---|---|---|
| `H(unset) == H(zero) == H(off) == H(false)` | **discriminator can return "inert"** — the positive control | my harness cannot detect inertness; nothing else is interpretable |
| `H(correct) != H(unset)` | correction reaches the render | **structurally inert** |
| `H(anti) != H(correct)` and `!= H(unset)` | anti reaches the render | **structurally inert** |
| bytes differ but metric flat | **measurably useless** | — |

**Bonus check, registered:** `default.warp.json` and `ca.warp.json` should be byte-identical if
CA is truly merge-only.

## 7. Declarations

- **I will not self-verify.** ORCH sends an independent verifier, as V-CA was sent for M107.
- **No `--srgb` render is measured.** No `PIL.Image.open` + `np.asarray` on 16-bit RGB.
- **If cost exceeds one build plus six merges, I stop and report** rather than expanding.
- Outputs under `C:\dev\strehl-out\V-CA-anti\`. **Nothing is written to `D:\`.**

---

# RESULTS — appended after the registration above was committed at `42270f4`

Binary: patched worktree build, `Compiling strehl-core` present, **16/16 optics tests pass**
including `the_two_profiles_differ_only_in_translation`. Six merges, one shared sidecar,
default binned-linear output, `assert dtype == np.uint16` on every read.

## R1. The discriminator table — every hash prediction holds

| arm | SHA-256 (16) | bytes | verdict |
|---|---|---|---|
| `unset` | `C38FFBA98E211565` | 49 449 626 | reference |
| `zero` | `C38FFBA98E211565` | 49 449 626 | **identical** |
| `off` | `C38FFBA98E211565` | 49 449 626 | **identical** |
| `false` | `C38FFBA98E211565` | 49 449 626 | **identical** |
| `correct` | `64914FAF1D554B5C` | 49 449 626 | **diverges** |
| `anti` | `22DBB9C7AA42D08D` | 49 449 626 | **diverges, and from `correct`** |

**The positive control passes** — four inert arms byte-identical, so the discriminator *can*
return "inert". **The correction is NOT structurally inert.** The failure ORCH ranked as most
important did not occur.

## R2. The pre-registered test — PASS on all three

| arm | mean \|R−Y\| DN | vs `unset` |
|---|---|---|
| `unset` / `zero` / `off` / `false` | 729.10 | 0.000 % |
| `correct` | 630.58 | **−13.513 %** |
| `anti` | 1006.08 | **+37.989 %** |

1. `anti` >= +8.0 % -> **+37.989 % PASS**
2. `anti − correct` >= 20 pp -> **+51.501 pp PASS**
3. signs oppose -> **PASS**
4. failure-that-matters (|gap| < 2 pp) -> **not triggered**

**The shipped sign is correct in the render domain.** Fact 1784's open concern is retired.

## R3. The number that does not fit

I pre-registered **+26.7 %**; measured **+37.99 %** — I under-predicted by 11.3 pp. The transfer
is **asymmetric**: 0.180 chroma-% per geometry-% in the helpful direction, **0.304 in the harmful
one (1.7x)**. Mechanism, consistent with Addendum 5 §5.2: this subject carries a blue/yellow
fringe at **1.356x** the red/cyan one, which `eps_b = None` cannot touch. That is a **floor**
under how far chroma can fall, and no ceiling on how far it can rise.

## R4. The odd/even decomposition — what discipline 816 was actually asking for

A correction is **odd** in `eps`; resampling blur is **even** (both arms resample identically).
Two arms separate them:

| r | `correct` | `anti` | **ODD** (correction) | **EVEN** (interpolation) | % correction |
|---|---|---|---|---|---|
| 0.0–0.1 | −0.57 % | +1.44 % | 1.00 | 0.44 | 69.6 % |
| 0.1–0.2 | +1.74 % | +8.74 % | 3.50 | 5.24 | 40.0 % |
| **0.2–0.3** | **+8.53 %** | **+28.59 %** | **10.03** | **18.56** | **35.1 %** |
| 0.3–0.4 | +0.66 % | +49.46 % | 24.40 | 25.06 | 49.3 % |
| 0.4–0.5 | −15.75 % | +37.95 % | 26.85 | 11.10 | 70.7 % |
| 0.5–0.6 | −7.69 % | +39.75 % | 23.72 | 16.03 | 59.7 % |
| 0.6–0.7 | −17.30 % | +44.59 % | 30.94 | 13.65 | 69.4 % |
| 0.7–0.8 | −30.08 % | +39.01 % | 34.55 | 4.46 | 88.6 % |
| **0.8–0.9** | **−31.25 %** | **+38.35 %** | **34.80** | **3.55** | **90.8 %** |
| **whole edge** | **−13.51 %** | **+37.99 %** | **25.75** | **12.24** | **67.8 %** |

**Three findings, none of which the on-vs-off comparison could produce.**

**(a) On-vs-off UNDERSTATES this correction, it does not overstate it.** The pure correction is
**−25.75 %**; resampling gives back **+12.24 %**; the observable net is −13.51 %. **Interpolation
opposes the correction rather than masquerading as it** — the opposite of what discipline 816
was written to catch. On-vs-off understates the true effect by **1.9x**.

**(b) Addendum 5 §5.2's mid-field lobe is PROVEN to be interpolation.** At r 0.2–0.3 *both* arms
are positive (+8.53 and +28.59) — an **even** function of `eps`, which a correction cannot be.
My §5.2 alternative reading was right, and this is the control that proves it rather than
arguing it.

**(c) There is a radius below which the correction is net-harmful, and nobody has stated it.**
Inside r ~ 0.4 the interpolation penalty **exceeds** the correction benefit (at r 0.2–0.3,
18.56 vs 10.03) and net chroma **rises**. Beyond r 0.7 correction dominates 9:1.
`support_r_max = 0.788` is declared, unenforced, and is an **upper** bound — the measurement says
the missing guard is a **lower** one.

## R5. Verdict

**Unchanged: NO to default-on** — R1–R4 retire one limb (the untested sign) and touch none of
the others: no author recommends it, the 0.950/0.541 transfer split, the **23.6 %** scene spread,
the half-closed dispatch gap, `wrapped-text-1`'s reversal, and §6.4's finding that the shipped
coefficient over-corrects **both** subjects ever fitted.

**But the correction is better at the corner than anyone has measured** (−31.25 % at r 0.8–0.9,
90.8 % of it real), and **worse in the mid-field than anyone has measured**. That trade is new,
and it is an argument for a radius-gated correction rather than for on-or-off.

**One subject, one arm, not self-verified.** Cost was one build plus six merges, as estimated.
