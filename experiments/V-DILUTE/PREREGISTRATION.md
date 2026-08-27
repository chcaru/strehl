# V-DILUTE — pre-registration

Written **before any render**. Binary: `C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe`,
sha256 `44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095…` — verified, matches the required `44C2F2CD2E5B2894`.
Subject: `bee-3-cpl` (299 frames), the stack fact 1790 (V-LINEAR) measured `0.180`/`0.060` on.
Every run passes `--merge pyramid` **explicitly**, because the CLI infers the *estimator*
backend from any estimator-only flag when `--merge` is absent.

## The hypothesis under test (ORCH)

`share_winner = 1 / (1 + SUM_{k!=winner} (e_k/e_winner)^p)`. `N` is absent from the
expression but the sum has `N-1` terms, so a fixed exponent gives less selection as the
stack deepens. Verified against the pin source before writing this: `pyramid.rs` weight law
and `select_weight` match ORCH's quote verbatim, and `accumulate_level` under
`SelectMode::SoftPower` accumulates `den += w`, `num += w*lv`, so the output is `num/den` —
a normalised weighted mean, exactly the modelled quantity.

## Instrument, and its known N-dependent bias

`--confidence-map` writes `v = 1 - 2*|below/seen - 0.5|` in milli-units, per pixel, where
`below` counts observations under the merged luma (`merge_cmd.rs:4695`, `confidence_pass`).
0 = merge sat at an extreme (committed), 1000 = dead centre (averaged).

**Pre-registered confound, and the reason this experiment is not a simple one:** the rank is
estimated from `N` observations, so it carries sampling noise that *shrinks* with `N`. For a
merge that averages **identically** at every depth, `below/seen → Binomial(N,½)/N`, so
`E[v] ≈ 1 - sqrt(2/(pi*N))`: **≈787 at N=22 but ≈942 at N=299.** Confidence therefore drifts
toward "averaging" as N grows *even when nothing about the merge changes.* **A raw rise of
confidence with N is NOT evidence for the hypothesis and I will not report it as such.**

Control: bracket every N with two arms that fix the ends of the scale at that same N —
- committed floor: `--pyramid-select hard-max` (the textbook argmax control arm)
- averaged ceiling: `--pyramid-exponent 0.05 --pyramid-sharpen 1.0` (weights ≈ equal → gated mean)

and report the **normalised commitment index**
`CI(N) = (conf_default - conf_hardmax) / (conf_meanarm - conf_hardmax)`, which is
dimensionless and absorbs the rank-sampling bias because floor and ceiling carry it too.

## Kill conditions — Experiment A

- **A-KILL-1:** if `CI(N)` does **not** rise materially from N=22 to N=299 (i.e. the default
  sits at the same relative position between the committed floor and the averaged ceiling at
  both depths), the dilution hypothesis is **dead** as this instrument can see it.
- **A-KILL-2 (instrument void, not a null):** if `hard-max` and `default` confidence
  distributions are not separated at fixed N, the map cannot see selection strength at all
  and Experiment A reports **VOID**, never "no effect". Anticipated mechanism: `--pyramid-base`
  defaults to `mean`, so the output's low frequencies are a plain mean at every N, and this
  rank is computed on full-res luma which low frequencies dominate.

## Kill conditions — Experiment B, and a pre-registered objection to its design

**I do not accept ORCH's Experiment B as specified.** The two arms are
*every 2nd frame* (N=150, full range) versus *first 150 frames* (N=150, half the range).
The first-150 arm **does not contain in-focus observations for the far half of the subject
at all**. It will be blurrier there for a reason that has nothing to do with dilution, and
**every** model — including "no dilution whatsoever" — predicts the full-range arm wins
globally. As specified the comparison cannot discriminate the hypothesis, and a global
win for the x2 arm must **not** be read as support for it.

Repaired design, which does discriminate:
- run ORCH's two arms exactly as specified, and report the global number he asked for;
- **restrict the decisive comparison to the common-focus ROI** — pixels whose best-focus
  frame index is `< 150`, taken from an independent per-pixel index map (estimator backend
  `--index-map`, a different backend from the one under test). Inside that ROI both arms own
  the pixel's true in-focus frame, N is equal at 150, and the *only* difference is that the
  x1-step arm has twice the near-focus competitor density.
- **B-KILL:** inside the common-focus ROI, if the x2-step arm is **not** sharper and more
  committed than the x1-step arm, the competitor-density mechanism is **dead**.

**B2, the duplication null (my addition, the cleanest control available).** Merge the first
150 frames, then merge a directory holding each of those same 150 frames **twice** (N=300).
Focus sampling, range and subject are identical; only the frame count doubles. A uniform
duplication multiplies numerator and denominator equally, so the dilution model predicts
**exactly no change**, while any "deep stacks are softer because N is large" story predicts
softening. This separates *N per se* from *competitor density* at equal range.
- **B2-KILL:** if duplication materially softens the render, damage tracks raw `N` and
  ORCH's specific mechanism is not what is acting.

## Experiment C

Sweep `--pyramid-exponent` × `--pyramid-sharpen` on `bee-3-cpl` at N=299, including the
shipped default (2.0 / 1.4) and the uniform-high arm (8.0 / 1.0). Diagnostic only — a higher
exponent is **not** proposed as a fix (a separate lane measured hull violations 0/72/511 at
exponent 1/8/16).
- **C-KILL:** if the uniform-high arm does not raise detail on `bee`, the exponent is not the
  axis the failure lives on.

## Metrics — fixed now, before any pixels exist

Rule 3: **no sharpness number is reported without a noise number on the same pixels**, with
band, subject and frame count named. Measured on the default output (binned, linear,
camera-native RGB — the file this project's corpus is measured on), never on `--srgb`.

- `detail` = mean radial power of the green plane in **0.30–0.35 cyc/px** (the band
  V-SOFTCHECK's 63-vs-32 result used), also reported at **0.20–0.25 cyc/px** (M127's band),
  over a fixed set of **textured** tiles.
- `noise` = mean radial power in **0.40–0.50 cyc/px** over a fixed set of **flat** tiles.
- Tiles are chosen **once**, from a single fixed reference render, and the identical tile
  coordinates are reused for every arm, so tile selection cannot respond to the arm.
- Arms may differ in output geometry (alignment shrinks the FOV ~7–10% and the arms have
  different frame sets). All comparisons are made on a **common centred crop** at the minimum
  common dimensions, and any arm whose geometry differs is reported as such.
- Comparisons are on **decoded arrays**, never file digests (rule 5).

## Commissioning, before any of the above is believed

1. **Null:** identical flags twice ⇒ bit-identical decoded arrays.
2. **Potency:** `--pyramid-exponent 4.0` must move ≈90.98 % of samples against the default
   (the known-potent control ORCH supplied).
3. The confidence instrument gets its own potency arm (hard-max vs default at fixed N).

A metric that cannot respond looks exactly like a metric reporting "no change"; nothing below
is believed until it has both a null and a potency arm.
