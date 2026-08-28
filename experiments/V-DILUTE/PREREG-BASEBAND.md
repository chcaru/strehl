# V-DILUTE — Pre-registration: the base-band blur hypothesis (Assignment 2)

Written before any render exists. Committed before any arm is scored.

## The hypothesis under test (ORCH's, stated in his words)

> If the default band count leaves real structure in the base band, then that
> structure is combined by a PLAIN MEAN ACROSS ALL FRAMES — including every
> badly defocused one. That is not a merge, it is a blur, and it is applied to
> whatever acuity the base band still carries.

And its N-scaling corollary: it "should get **worse with N**, because a deeper
stack contributes more defocused frames to that mean."

## PREMISE OBJECTION, registered before measuring

I believe the premise is false, and I am registering the reasons in advance so
that the measurement can overturn *me* rather than be read as confirming me.

The hypothesis has a load-bearing precondition: **the base band must carry
acuity-band structure at the default band count.** Four independent sources say
it carries *tone* instead.

1. **Geometry.** `DEFAULT_BANDS = 7`, and `pyramid.rs:129-136` states the
   resulting size: "Seven octaves takes a 3516 x 2344 quad plane down to a
   **28 x 19 base**." A 28-wide base over a 3516-wide plane resolves nothing
   above ~1/125 px⁻¹ = **0.008 cyc/px**. The qualified SIGNAL band is
   **0.17-0.25 cyc/px**, i.e. **21x to 31x higher in frequency**.

2. **The help text ORCH quoted, read to its end.** He quoted "Too shallow and
   the base band still holds structure" and stopped. The sentence finishes:
   "`--pyramid-bands 2` **keeps acuity but loses the darkest densities — grey
   ink instead of black.**" The stated failure of a base band that holds
   structure is **density, not softness**, and acuity is explicitly *kept*.

3. **The design intent, stated at the constant.** "That is deliberately deep:
   the whole point of the exercise is that the **low frequencies must be
   blended rather than switched**, and stopping at four or five levels leaves a
   band at ~100 px scale still being selected, **which is visible as exactly
   the halo this is meant to remove.**" Mean-combining the base is not an
   oversight; it is the halo fix. The direction the hypothesis implies —
   select/weight more of the low frequencies — is the defect that was removed.

4. **The flip record ORCH cited** (`pyramid.rs:3105-3112`). The quantities
   measured are "**global level**" and "**position-dependent structure**",
   both in **DN**, and it records "**with no difference in aura removal**".
   Those are tone quantities. Nothing there is an acuity measurement.

5. **ORCH's own scorer agrees.** `contrast_ms.py` uses SIGMAS up to 16.0, whose
   cut is `1/(2*pi*16)` = **0.00995 cyc/px**, and designates that band the
   **INSTRUMENT NULL** — the band that must read ~1.000 "or the two arms differ
   globally and the comparison is void." The base band's entire content lies at
   or below that cut. The mechanism is being proposed inside the band the
   instrument reserves for detecting global offsets.

ORCH's fair point survives all of this and is *not* what I am contesting: the
default was chosen on **one subject**, so its corpus-wide generality is genuinely
untested. That is a separate question from whether the blur mechanism exists,
and I will report it separately.

## What I will measure

The only difference between `--pyramid-base mean` and `--pyramid-base weighted`
at fixed `--pyramid-bands` is how the base band is combined. Therefore the
**decoded difference between those two renders is exactly the base band's
contribution difference**, isolated by flags with no source change. I will
measure *where in frequency that difference lives*.

Arms, per subject:

| arm | flags | role |
|---|---|---|
| M7 | `--pyramid-bands 7 --pyramid-base mean`     | shipping default |
| W7 | `--pyramid-bands 7 --pyramid-base weighted` | base-band treatment flipped |
| M2 | `--pyramid-bands 2 --pyramid-base mean`     | POTENCY: base holds structure |
| W2 | `--pyramid-bands 2 --pyramid-base weighted` | POTENCY pair |

`M2/W2` is the commissioning arm demanded by the `--fix-ca` lesson: at
`bands 2` the base band is a lowpass at 4 px and reaches to **0.125 cyc/px**,
so base-band treatment *can* reach near the signal band there. If `M7-W7` is
null but `M2-W2` is large, the null at default settings is a **measurement**,
not a dead gauge.

## Kill conditions — stated before the data exists

**The base-band blur hypothesis SURVIVES if**, at the default `--pyramid-bands 7`:

- the `M7` vs `W7` band-1 (0.17-0.25 cyc/px, qualified SIGNAL) EDGE ratio
  departs from 1.000 by **more than 0.02**, i.e. base-band treatment measurably
  moves acuity; **and**
- the spectral difference `|M7 - W7|` places a material share of its energy
  (say **>= 5%**) at or above 0.17 cyc/px, rather than being confined to the
  coarse/tone region.

**The hypothesis is DEAD if**, at the default band count:

- the band-1 EDGE ratio between `M7` and `W7` is within **0.02** of 1.000, and
- the difference energy is confined to the coarse bands (below ~0.01 cyc/px),

**while the potency arm `M2` vs `W2` shows a clearly larger band-1 departure** —
proving the comparison could have detected base-band acuity had it been there.

**The N-corollary is DEAD if** the `M7`-vs-`W7` band-1 EDGE departure does not
grow with N across the depth range tested.

**The instrument is VOID on any row** whose coarsest EDGE ratio is outside
0.005 of 1.000 — except for the `--pyramid-base` contrast itself, where a
coarse-band move is the *expected signal* rather than a fault. I will therefore
report the coarse band as a measurement on those rows and state that explicitly
rather than silently suspending ORCH's rule.

## Standing guards carried from Assignment 1

- Every master gets `clipcheck.py` **and** a black-rail check (`%==0`, `%==max`,
  median) before it is scored. A structural metric reads CLEAN at both rails.
- No sharpness number is quoted without a noise number on the same pixels.
- Compare **decoded arrays**, never file digests.
- Renders are linear camera-native: **no** `--auto-exposure`, **no** `--srgb`.
- `--merge pyramid` is passed explicitly on every arm.
- No `.rs` file is edited. `pyramid.rs`, `merge.rs`, `merge_cmd.rs`,
  `align_cmd.rs`, `defect_map.rs` are owned by other lanes.
