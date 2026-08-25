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
