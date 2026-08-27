# PRE-REGISTRATION — delivered exposure gain, arms C/D and A/B of 47-exposure-liveness

Written and committed BEFORE the regression was run. The point of committing it
separately is that the git timestamp makes the prediction unfalsifiable after
the fact; a prediction produced in the same commit as its confirmation is not a
prediction.

Derived from `crates/strehl-cli/src/image_out.rs` (READ ONLY; not my file),
`Tone::from_luminance` at :972 and `Tone::gain` at :1057. Derivation, not guess.

## The derivation

Let `g` be a pure linear exposure gain applied upstream of the tone stage, so
every linear sample `v` becomes `g*v` and luminance `l` becomes `g*l`.

`from_luminance` sorts the luminance sample and takes order statistics:

    black     = at(TONE_BLACK_PCT) * TONE_BLACK_FRACTION
    white_src = at(TONE_WHITE_PCT)
    white     = black + (white_src - black).max(1e-4) / TONE_WHITE_TARGET

`g > 0` does not reorder a sorted array, so `at(p)` selects the SAME element and
returns `g` times its old value. Hence `black -> g*black` and, since the whole
expression for `white` is homogeneous of degree 1 in the samples,
`white -> g*white`. (The `.max(1e-4)` is the one non-homogeneous term. It binds
only when the linear range falls below 1e-4; the corpus range is ~0.6, and even
at -3 stops it is ~0.075, so it does not bind here.)

`Tone::gain`:

    s    = 1/(white - black)          ->  s/g
    y    = (l - black) * s            ->  (g*l - g*black)*(s/g) = y      INVARIANT
    soft = 0.5*(y + sqrt(y^2+TOE^2))  ->  soft                          INVARIANT
    gain = min(soft/l, s)             ->  min(soft/(g*l), s/g) = gain/g

`TONE_TOE` is documented at :926 as "a fraction of the black-to-white OUTPUT
range", i.e. a constant in the normalised `y` space, so it does not scale and
the toe cancels with everything else. The `min(., s)` cap cancels because both
of its branches carry the same `1/g`.

Output pixel:

    (g*v) * (gain/g)  =  v * gain     <-- THE ORIGINAL PIXEL, EXACTLY

The cancellation is EXACT, not approximate, and it is exact term by term.

## Predictions, falsifiable

P1. Regressing arm D (`--srgb --exposure -3`) against arm C (`--srgb --exposure 3`),
    LSQ through the origin over all pixels: slope = **1.000** to at least four
    decimals, despite a commanded span of 64x. NOT 1/64 = 0.015625.

P2. Regressing arm A (`--srgb --auto-exposure`, banner "+2.61 stops, gain
    6.105x") against arm B (`--srgb`, no gain): slope = **1.000**, not 6.105.

P3. THE RESIDUALS ARE ULP-SCALE. This is the prediction that distinguishes my
    hypothesis from "the flag is ignored". The flag is NOT ignored: the gain is
    applied and then divided back out, in f32, so the round trip does not land
    on the same bits. I predict the arms differ by a handful of least
    significant counts in the 16-bit output -- order 1e-5 relative, not zero --
    with no systematic component. That is exactly enough to move a SHA-256 and
    nowhere near enough to be a delivered exposure change.

P4. Therefore my own `47-exposure-liveness` verdict "the path is LIVE" was
    produced by an instrument that detected floating-point rounding noise and
    reported it as liveness. A hash is sensitive to any change and specific to
    none. If P1-P3 hold, that verdict is withdrawn and the correct statement is:
    the flag reaches the pixels and is then cancelled by the auto-tone.

## What would falsify this

- slope(D vs C) near 0.0156, or slope(A vs B) near 6.105  -> the gain is
  delivered, the cancellation hypothesis is wrong, V-NEVERWORSE's result needs
  a different explanation.
- slope exactly 1.000 AND bitwise-identical arms -> the gain never reaches the
  tone stage at all; the flag is inert upstream, which is a different defect
  from cancellation and would make my four distinct hashes inexplicable.
- a systematic, luminance-dependent residual -> partial cancellation, e.g. the
  `.max(1e-4)` clamp or a clip binding somewhere I have not accounted for.

## Commissioning, to be run BEFORE the real pairs

The regression must be shown able to report a gain it is given, in both
directions, or a null from it means nothing:

  - plant 2.0x  -> estimator must return 2.000   (can it see a gain at all)
  - plant 0.5x  -> estimator must return 0.500   (is it bounded below at 1, or
                                                  direction-blind -- the
                                                  "perverse metric" arm)
  - plant 1.0x  -> estimator must return 1.000   (null control)

An estimator that returns 1.000 on all three is measuring nothing, and would
have produced this document's predicted answer for a reason that has nothing to
do with the tone stage.
