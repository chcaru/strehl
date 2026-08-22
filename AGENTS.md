# AGENTS.md — strehl

Noise-aware RAW focus stacker. Rust. CFA-native. Pluggable focus measures, merge
strategies and alignment models. Camera and lens knowledge is a **profile** — a
data file, not a plugin: measurement kept reclassifying "camera constants" as
per-stack quantities that are cheaper and more accurate to fit at runtime. See
`SYNTHESIS.md` §3.4.2 for exactly what survives.

Read [`docs/research/SYNTHESIS.md`](docs/research/SYNTHESIS.md) before changing
anything architectural. It is the decision record and it lists what lost.

## Licence discipline — read this before opening any other repository

This project is **MIT OR Apache-2.0**. Reading GPL source would contaminate it.

**Never open, read, browse, or copy from:**

| Project | Licence |
| --- | --- |
| enfuse / enblend | GPL-2.0 |
| `align_image_stack`, Hugin | GPL-2.0 |
| EPFL Extended Depth of Field | GPL-3.0 |
| ChimpStackr | GPL-3.0 |
| darktable (**including `exif.cc`**) | GPL-3.0 |
| RawTherapee, ART, Filmulator | GPL-3.0 |
| `librtprocess` | GPL-3.0 |
| ExifTool Perl source | GPL-3.0 |
| `rawler` / `dnglab` **source** | LGPL-2.1 — link only, do not read |

**Safe to read:** PetteriAimonen/focus-stack, z-stackr, stackaroni, `rawkit`
(all MIT/Apache-2.0).

**Do not link:** `dssim` (AGPL). Use `ssimulacra2` and `butteraugli` instead.

ExifTool's *tag tables* are not an independent specification — the pages are
generated from GPL source. Tag IDs, offsets and enum values are uncopyrightable
facts and may be used; the surrounding prose may not. Never read the Perl.

`rawler` is LGPL-2.1 and we link it. Ship it dynamically linked, or publish
object files or a reproducible build. Do not statically link it into a
monolithic binary and ship only that binary.

## Rules

1. **Storage is u16 CFA. Arithmetic is f32.** Never store f16 — a 10-bit
   mantissa gives ~8 LSB steps on linear 14-bit data.
2. **Never materialise aligned frames.** Gather at consumption inside each
   kernel. Materialising 60 aligned RGB frames is 24 GB and demosaics 60 times
   instead of once.
3. **The noise model is injected, never re-derived per stage.** A private
   per-stage noise estimate is the exact mechanism behind the prior project's
   2–5x defect.
4. **Never let a merge reference be a raw per-band argmax.** Argmax over N
   frames returns 1.95–2.61x single-frame noise. Use a regularised focus field.
   Measured: regularising drops speckle 34.4% -> 0.87% and noise 1.253x ->
   1.075x — necessary, and **still above 1.0**. A regularised selector is still
   a selector; the noise-gated average is the other half.
5. **Fit geometry at runtime; do not bake it.** Scale drift and the scale
   centre are per-stack quantities. Only sensor calibration belongs in a
   profile, and profiles live in data files.
6. **Never chain alignments.** Align every frame against a fixed reference,
   never against its predecessor. Measured: chaining 21 adjacent pairs
   underestimates drift by 32%, which is 25 px at the sensor corner, because
   sub-pixel pixel locking is a systematic bias that compounds. Direct fits are
   also embarrassingly parallel. See `docs/research/M3-alignment-measured.md`.
7. **Never compute statistics over the full decoded buffer.** `rawler` returns
   7168x5120 for the A7C II but fills only the 7032x4688 active area. The rest
   is synthetic zeros, not black level.
8. **Every performance or quality claim needs a command that was run.** Label
   claims MEASURED / VERIFIED / DERIVED / ARGUED / UNVERIFIED.
9. **Pair every sharpness metric with a flat-ROI control.** A sharpening pass
   raises gradient energy on featureless foam; that is how the prior project
   fooled itself.
10. **Never compare a spatial sd to a temporal sigma.** They are different
    physical quantities. A spatial sd over an image region carries scene
    structure; a temporal sigma across frames does not. High-pass first, or
    compare like with like. This error has now caused **two** retractions —
    the prior corpus's 1.10x correlated-noise claim, and M2's "unexplained"
    1.46x model gap, which was 1.01x once matched properly.
11. **Every claimed defect needs a placebo, and every headline number needs a
    regression test on its own code path.** What proved argmax was the cause of
    M2's 1.253x was not a better measurement of argmax — it was a *different
    merge rule* on identical data (mean, 0.534x) and a selector with the same
    winner histogram but no noise coupling (0.981x). Without those it was only
    correlational. And the 1.253x itself had 52 tests behind the library and
    zero covering the code that produced it.
12. **The author never verifies their own work.** M2 was self-verified
    thoroughly and still shipped five wrong supporting numbers, two of them in
    the direction that loses an argument. See `docs/research/M2-verification.md`.
13. **kebab-case** for directories and files. Crates are `strehl-*`.

## Layout

| Path | What |
| --- | --- |
| `crates/strehl-core/` | Types, noise model, tile views, geometry |
| `crates/strehl-raw/` | RAW decode behind `rawler` |
| `crates/strehl-cli/` | The binary |
| `docs/captures-needed.md` | **Data owed by the owner.** Read before asking for captures. |
| `docs/research/` | Research corpus and decision record |

## Research corpus

| File | What |
| --- | --- |
| `SYNTHESIS.md` | **Start here.** Decision record, revised after review. |
| `REVIEW.md` | Adversarial review that corrected four design errors |
| `REVIEW-plugin.md` | **Plugin-architecture critique.** Cordis verified against the PDF; four blocking interface fixes; camera/lens plugins are profiles |
| `M2-rss-resolved.md` | **Tiebreak.** Two docs disagreed 2.2x on peak RSS; resolved by measurement. Peak tracks live concurrency, and the 8 GB ratchet is at 89% by N=105 |
| `M1-decode-measured.md` | Measured decode throughput and sensor constants |
| `M2-baseline-skeleton.md` | The naive argmax baseline, and the measured defect it exposes |
| `M2-verification.md` | **Independent re-derivation of M2.** Headline confirmed and causally proven; five supporting numbers refuted |
| `M3-alignment-measured.md` | Measured alignment cost, motion model, and why chaining is dead |
| `M4-fpn-measured.md` | Dark-frame noise: sigma-vs-N, the fixed-pattern floor, read noise vs ISO |
| `A-prior-corpus.md` | The prior attempt, filtered; includes retractions |
| `B-algorithms-sota.md` | Algorithmic state of the art per stage |
| `C-landscape.md` | Competitors, licensing, artifact taxonomy |
| `D-rust-and-hardware.md` | Crates, versions, hardware envelope |
| `E-plugin-architecture.md` | Plugin design space and Rust API |
| `F-camera-lens-optics.md` | Optics of the reference rig; DoF tables |

Claims inherited from `C:\dev\macro` are suspect by default. Several were
retracted under scrutiny — including a headline noise finding that measured
*spatial* sigma while labelling it *temporal*, and three fabricated citations.
`A-prior-corpus.md` records which survived.

## Build

```
cargo build --release
cargo test
cargo clippy --all-targets -- -D warnings
cargo fmt --check
```

## Reference rig

Sony A7C II (`ILCE-7CM2`) + Sony FE 100mm F2.8 Macro GM OSS (`SEL100M28GM`).
Pixel pitch 5.12 um. RGGB. Black level 512, white level 15360, active area
7032x4688. Confirmed by measurement, not by documentation.

**v1 targets in-camera focus bracketing only** — camera fixed, focus moves, so
frames differ by magnification and occlusion never changes.

Focus rails translate the camera, producing genuine parallax and occlusion. Rail
support is **deferred**: no rail hardware is available to test against, and an
untested geometry model would violate rule 8. The `CaptureMode` enum and mode
detection stay in place because that is the one seam the rail case genuinely
needs. Never silently apply the breathing model to rail data — detect from EXIF
plus fitted residual signature, and warn. Never trust a user flag alone.
