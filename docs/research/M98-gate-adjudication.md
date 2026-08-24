# M98 — the gate, adjudicated: two milestones, two metrics, one photograph

**Milestone:** M98
**Question as dispatched:** `--gate` is the single most user-visible knob, and
M85 (fact 1196) and M92 (fact 1245) disagree about it in the direction the owner
cares about. Is the shipped default costing him sharpness?
**Status:** pre-registration committed; measurement not yet begun.

---

## 0. PRE-REGISTRATION

The full pre-registration is `experiments/M98-gate/PREREG.md`, committed **before
any number in this milestone existed** (rule 12). This section is the summary; the
file is the authority, and any departure is declared in §9 as a departure.

**HEAD:** `45ba18ba6ed71daa21802b9d45274ee49abe7892`. The working tree is **not
clean** — other agents hold uncommitted edits to `crates/strehl-core/src/robust.rs`
and four `crates/strehl-cli/examples/*`. My binary is built from that tree;
`robust.rs` is not on the default merge path. Recorded so the build is
attributable rather than assumed.

### Hypotheses and their falsifiers

| # | Hypothesis | Falsifier |
|---|---|---|
| **H1** | M85's ladder predates alignment (default-ON at `885e9f7`), so part of the measured gate cost was misregistration. With alignment ON the sharpness-vs-gate curve is **flatter**. | the aligned arm's gate contrast is **≥** the FOV-matched unaligned arm's, top detail tercile, `bee-3-cpl` |
| **H2** | M92's −0.61753 px is largely axis mismatch plus missing registration. On the **shipped** `--gate` axis with the shipped binary and alignment ON, `112MSDCF`'s gate-0 → gate-4 edge-width contrast is **< 0.31 px**. | it is ≥ 0.31 px |
| **H3** | The gate's cost is not one number. Mean `n_eff` is a global average dominated by low-detail regions: top-tercile local `n_eff` at gate 4 is **< ⅓** of the global mean. | it is ≥ ⅓ |
| **H4** | On a millimetre ruler — a-priori known tick spacing — gate 0 → 4 costs **< 10%** of the comb modulation. | it costs ≥ 10% |

### Two assertions about the prior milestones, to be re-verified not assumed

1. **They are not on the same axis.** `m57lib.py:510` `merge_subset` uses
   `acc = cf >= (gate * peak)` — a **fractional peak-height** gate. The shipped
   gate (`merge.rs:319`) thresholds on `T·√2·FOCUS_NOISE_SD`, in calibrated-noise
   units, and its default is **4.0**. Fact 1245 calls 0.50 "the shipped gate".
   `strehl stack --gate --help` already carries the caveat; the fact does not.
2. **M92's half-merges are unregistered** — `merge_subset` gathers `cube[idx]`
   with no warp. Averaging more frames of an unregistered bracket blurs by the
   drift spread, which reads exactly like a gate cost.

Both are *mechanisms that would produce M92's sign without the gate being at
fault*. They are hypotheses at pre-registration time, not findings.

### Instruments

Everything is a **cross-power between two half-merges with independent noise**
(parity frame split), because the gate changes noise ~6.6× and a single-render
band-power metric cannot separate signal from noise. From the *same* two
half-merges:

- `A_hf(T)` — band-integrated ring cross-power over `f ∈ [0.15, 0.2762]` cyc/px.
  **M85's quantity, made noise-free.**
- `dsig(T_a → T_b)` — `m57lib.dsig`, equivalent-Gaussian-blur difference in px
  over `f ∈ [0.05, 0.2762]`. **M92's quantity.**

Measuring both on identical data is what makes the adjudication possible.
All numbers are on the **binned linear camera-native** output, never on
`--srgb`/`--demosaic`.

### Arms

`ALN` (registration on, the shipped default) against `ZOOM` (`STREHL_ALIGN=zoom`
— field-of-view- and resampler-matched, registration discarded). `zoom` rather
than `STREHL_ALIGN=0` because magnification reads as sharpness (discipline 606).

### Stratification, declared in advance

24 ROIs of 512×512 on a procedural 6×4 lattice, split into **detail terciles by
`hp_sd`** measured once on the gate-0 `ALN` render. A conclusion that holds on the
top tercile and reverses on the bottom is **two conclusions, not one**
(discipline 603).

### Controls, each with its failing input

`EQ` at exactly `100.000000%` · `NC1` the negative control made to go red at
exactly `99.999996%` (one pixel, 1 LSB) · `PC` power control, planted σ = 0.30 px
must be recovered in `[0.25, 0.35]` px or **no null in this milestone means
anything** · `PL1` re-render placebo, exactly `0.000000` px · `PL2` half-label
swap, `< 1e-9` px · `FLAT` rule-9 flat-ROI control run **first** · `INERT` the
ruler comb must clear its sidebands by ≥ 3× or the ruler is no evidence ·
`AXIS` re-verify the axis-mismatch claim on the shipped binary.

### Decision rule, fixed in advance

Top detail tercile, `bee-3-cpl`, arm `ALN`, all controls green:

- **R-KEEP — the shipped default is correct:** `A_hf(4)/A_hf(0) ≥ 0.95` **and**
  `|dsig(0 → 4)| ≤ 0.10 px` **and** `sigma_flat(4)/sigma_flat(0) ≤ 0.5`.
  0.10 px is one unit of fact 1243's corrected single-ROI real-dark null.
  **Its failing value is `|dsig(0 → 4)| > 0.10 px` or `A_hf(4)/A_hf(0) < 0.95`.**
- **R-LOWER — the default is too high:** `|dsig(0 → 4)| ≥ 0.20 px` at
  `|mean|/SE ≥ 3.0`, **and** a knee `T*` exists with `|dsig(0 → T*)| ≤ 0.05 px`
  while `sigma_flat(T*)/sigma_flat(0) ≤ 0.5`.
- **R-INCONCLUSIVE** otherwise, or on any red control. A clean negative result is
  an acceptable outcome and will not be dressed up.

### Registered wrong predictions, to be scored

(a) `dsig(0 → 4)` `ALN` top tercile in `[0.00, 0.15]` px · (b) `ZOOM`'s
`dsig(0 → 4)` ≥ 1.5× `ALN`'s · (c) top-tercile local `n_eff` at gate 4 under 20
against the global 60.86 · (d) `A_hf(4)/A_hf(0)` reproduces M85's 0.985× to ±0.03
on `ZOOM` · (e) the ruler comb keeps ≥ 0.90 of its gate-0 modulation at gate 4.

### Read-only guarantee

`D:\personal\macro` and `D:\macro-dark-frames` are never written to. The shipped
merge caches a solved sidecar at `<dir>/warpmap.txt` (`align_cmd.rs:788`), which
would be a write into the read-only tree, so **every run operates on copies**
under `C:\dev\strehl-out\M98\frames\`.

---

*Sections 1 onwards are written after measurement.*
