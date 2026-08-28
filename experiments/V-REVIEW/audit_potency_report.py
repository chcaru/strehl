import io
P = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\AUDIT-potency.md"
T = """# Potency audit: does each user-facing control do anything?

Companion to `AUDIT-user-surface.md`. Updated after the exposure wiring landed.

**Gauge.** Decoded pixel arrays, never file hashes. **Both commissioning arms
passed on the exact files used**: the renderer is deterministic, and a
known-potent control moves a large fraction of samples. Where a gain is
measured, the tone chain is inverted first -- see the correction below.

**Binaries.** Working tree HEAD `6c36106c` built to an isolated target dir.
Subjects `109MSDCF` (22 frames) and `coffee-bubbles` (19 frames).

---

## Part 1 -- the exposure fix WORKS. Verdict: the wiring claim is confirmed.

`--exposure` now reaches the pixels on the shipping path.

| subject | frames | samples moved by `--exposure 1` |
| --- | --- | --- |
| `109MSDCF` | 4 | 97.6762% |
| `coffee-bubbles` | 3 | 99.9849% |

**The delivered gain is exact wherever the render is not highlight-limited.**
Measured in linear light between adjacent settings:

| pair | commanded | delivered | error |
| --- | --- | --- | --- |
| -2 to -1 stops | 2.000000 | 2.0000001 | +0.0000% |
| -1 to 0 stops | 2.000000 | 2.0000002 | +0.0000% |

Seven-decimal agreement. **The cancellation defect is gone**, and the mechanism
confirms it: the tone anchors now scale *exactly* with the commanded gain
(`white` reads 0.04067, 0.08134, 0.16267, 0.32534, 0.65069 at -2, -1, 0, +1, +2
stops), so the tone normalisation is scale-invariant and the gain survives it.

### A correction to my own gauge, before the overshoot

My first measurement of this reported a delivered slope of **1.5285570** against
a commanded 2.0 and I nearly filed it as a defect. **It was the wrong domain.**
A regression on sRGB-encoded, tone-mapped code values does not measure a gain
applied in linear light before the curve; the compressive curve is most of what
it measures. The arithmetic was right and the question it answered was not the
one asked.

Re-derived by building the inverse chain from **the Rust source**
(`image_out.rs:1035`, `s_curve(x, strength) = x + (x*x*(3-2x) - x) * strength`,
contrast 0.55 read from the render banner) rather than from the author's Python,
then **commissioned on planted gains**:

```
planted 2.0 -> recovered 2.0000001   planted 0.5 -> recovered 0.5000000
planted 1.0 -> recovered 1.0000000   planted 1.3 -> recovered 1.3000001
```

## Part 2 -- the overshoot is neither constant nor proportional to the gain

It is **attached to the brighter render**, not to the commanded ratio. Three
pairs whose upper endpoint is `+1` return the *same* error against three
different commanded gains:

| pair | commanded | delivered | error |
| --- | --- | --- | --- |
| 0 to +1 stops | 2.000000 | 2.1654121 | +8.2707% |
| -1 to +1 stops | 4.000000 | 4.3308265 | +8.2707% |
| -2 to +1 stops | 8.000000 | 8.6616530 | +8.2707% |

A gain error that scaled with the gain would differ across those rows. A
constant offset would differ too. **An error identical to four decimal places
across a 2x, a 4x and an 8x command is a property of the `+1` render itself.**

It is **level-driven**, and it concentrates in the bright end:

| samples included | delivered vs commanded 2.0 | error |
| --- | --- | --- |
| all unclipped | 2.1654121 | +8.2707% |
| both arms below half ceiling | 2.0274856 | +1.3743% |

**This is why my number is not the author's `+0.664%`.** That figure is measured
in a mid-tone band; mine is over every unclipped sample. Neither is wrong and
they are not in conflict -- **the error is a function of which samples you keep**,
which is itself the finding. The author's own caveat that clipping "drags toward
1.0 and so cannot explain an overshoot" is correct and is why this needs a
different explanation from clipping.

**Recommended framing: this is a highlight-rendering defect, not a gain-constant
defect.** The gain is exact to seven decimals in the shadows and at every
setting at or below 0 stops. It should not inherit the fixed verdict, and it
should not be described with a single percentage without naming the band.

## Part 3 -- the test critique, applied to the new call sites

**The new test is structural, and it says so honestly.**
`every_writer_develop_carries_the_exposure_gain` counts writer sites against
gain-carrying sites in the source text. Its own docstring states the split: the
behavioural claim lives in
`image_out::tests::an_exposure_request_changes_the_pixels_and_not_only_the_banner`,
and it notes that test "passes happily while this file forgets to pass the gain
in, because it never sees this file." That is an accurate self-assessment and
the guard is well-built.

**But the shape I flagged is unchanged one layer up.** At HEAD the behavioural
test still constructs `srgb: false, contrast: 0.0` -- **the configuration the CLI
refuses**, since `--exposure` requires `--srgb`. So:

- the wiring guard proves a **call site exists**, from source text;
- the behavioural test proves the **arithmetic is right** in a state no user can
  request;
- **no test drives `--srgb --exposure` end to end.**

Together they would not catch the +8.27% highlight error, because neither runs
the configuration in which it appears. The only things that have measured the
user-facing path are the author's script and this audit, and **neither is in
CI**.

---

## Part 4 -- potency table, gaps now closed

| flag | backend | samples moved | verdict |
| --- | --- | --- | --- |
| `--photometric off` | estimator | 97.20% | potent |
| `--resampler nearest` | pyramid | 97.17% | potent |
| `--focus laplacian-w13` | estimator | 97.42% | potent |
| `--pyramid-gate 8.0` | pyramid | 96.96% | potent |
| `--pyramid-select hard-max` | pyramid | 96.40% | potent |
| `--gate 8.0` | estimator | 96.30% | potent |
| `--focus ring-1-3-w13` | estimator | 96.23% | potent |
| `--pyramid-sharpen 1.0` | pyramid | 96.19% | potent |
| `--resampler lanczos3` | pyramid | 96.08% | potent |
| `--pyramid-bands 3` | pyramid | 95.96% | potent |
| `--focus brenner-w13` | estimator | 95.94% | potent |
| `--pyramid-exponent 4.0` | pyramid | 84.08% | potent |
| `--pyramid-base weighted` | pyramid | 31.92% | potent |
| `--exposure 1` | pyramid | 97.68% | **now potent** |
| `--confidence-tail` | pyramid | 0.00% | **INERT** |
| `--stats-placebo` | estimator | 0.00% | inert BY DESIGN |
| `--index-map` | estimator | 0.00% | inert BY DESIGN |
| `--n-eff-map` | estimator | 0.00% | inert BY DESIGN |
| `--target-n-eff 2` | estimator | 0.00% | inert BY DESIGN |
| `--flat-roi`, `--detail-roi` | estimator | 0.00% | inert BY DESIGN |
| `--stats` | estimator | 0.00% | inert BY DESIGN |
| `--fix-ca <profile>` | pyramid | 0.00% | redundant, not broken |
| `--demosaic` | pyramid | 0.00% | implied by `--srgb` |

### `--confidence-tail` remains the one real inert flag, now at two subjects

Swept `0.02` to `0.90` -- a 45x range -- it produces **one bit-identical
confidence map** on `109MSDCF`, and moves no pixel on `coffee-bubbles` either.
The map is **proven responsive on the same run**: `--pyramid-gate 8.0` moves it
16.27%, `--pyramid-bands 3` moves it 9.66%. The null is readable and it holds at
n=2 subjects.

### Gaps closed since the last report

- **`--stats-placebo` is not inert and was never a defect.** It is a **bare
  switch**, not a directory argument -- the `<DIR>` in the usage line is the
  positional subject directory. I misread that and reported it as unverified;
  the correct invocation runs, emits its placebo arm into the report
  (`placebo : mean 1.334 sigma, median 0.811, p99 13.460`) and moves no pixel,
  which is right for a diagnostic.
- **`--focus` is potent** across all three operator ids, from `strehl focus list`.
- **`--index-map` and `--n-eff-map`** write their artefacts and leave pixels
  alone, which is correct for side outputs.

---

## Instrument defects in this round

1. **I measured a linear-light gain in sRGB code space** and got 1.5286 against a
   commanded 2.0. Had I filed it, it would have been a false conviction of a
   working fix. Caught because the error was *systematically compressive across
   the whole range* -- +48% at -1 stop and -42% at +2 -- which is a curve
   signature, not a defect signature.
2. **I misread a clap usage line** and reported `--stats-placebo` as taking a
   `<DIR>`. It is a switch. That error propagated into the previous report.
3. **My first `--confidence-tail` sweep was invalid** -- it asked for
   `--confidence-map` under the estimator, which the tool refuses. It failed
   loudly on all six settings rather than returning a convenient null.

## Gaps

- **The mechanism of the +8.27% highlight error is not isolated.** It is
  localised to bright samples in positive-gain renders and is not the gain
  constant; the specific stage is not identified here.
- **`--srgb`, `--linear-srgb`, `--binned`** change container or geometry, so a
  same-shape pixel comparison does not apply.
- **No CI test covers the user-facing exposure path**, so this verdict is a
  snapshot of HEAD `6c36106c` and nothing prevents its regression.
"""
io.open(P,"w",encoding="utf-8",newline="\n").write(T)
print("wrote", P)
