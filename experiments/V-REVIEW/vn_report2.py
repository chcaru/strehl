import io
P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-REVIEW-noise-verification.md"
T = """

## 11. The publishable table, on one named gauge

**The gauge is: container-matched, shift-corrected.** Every ratio is comparator
over strehl, where strehl has first been placed in **the comparator's own
container**, and both arms are registration-corrected by the same 49-candidate
integer search driven on luma. Against `enfuse` the requantisation is a no-op,
both being 16-bit. Against `focus-stack` strehl is requantised to 8 bits.

**Why this convention and not a penalty divisor.** A quantisation penalty is not
a property of the container. MEASURED, the same 8-bit requantisation of the same
strehl arm costs **+16.4%** luma on the raw gauge and **+29.8%** luma on the
shift-corrected gauge. Both are correct. Quantisation adds an independent
variance floor, so the same absolute floor is a larger fraction of a smaller
baseline, and the shift correction lowers strehl's luma noise from 0.07985 to
0.05296. The floor recovered from one gauge predicts the other to within 3.5%,
0.2% and 0.4% in the three channels, which confirms one phenomenon rather than
two measurements.

A divisor therefore only means anything on the gauge it was measured on.
Container-matching never divides: the quantisation lives inside an arm, and the
bootstrap propagates its uncertainty for free. Commissioned before use:
requantising an already-8-bit arm changes the statistic by exactly **0.000e+00**,
and the identity ratio is exactly 1.000000000000.

**The four cells.** MEASURED, 110 shadow tiles, 4000 tile resamples, percentile
intervals.

| cell | channel | corrected value | 95% interval | clear of parity |
|---|---|---|---|---|
| vs `enfuse` | luma | **1.62x cleaner** | 1.51 to 1.71 | yes |
| vs `enfuse` | chroma | **1.61 to 1.81x cleaner** | 1.53 to 1.97 | yes |
| vs `focus-stack` | luma | **1.48x cleaner** | 1.40 to 1.51 | yes |
| vs `focus-stack` | chroma | **1.64 to 1.66x cleaner** | 1.55 to 1.76 | yes |

Per channel, so the chroma cells cannot be mis-mapped: `enfuse` B-Y 1.606, R-Y
1.813; `focus-stack` B-Y 1.640, R-Y 1.661. Every one of the six individual
channel intervals has a lower bound above 1.0.

One sentence per cell, quotable:

- **`enfuse`, luma.** Both arms sit in the same 16-bit container and both are
  registration-corrected, so this is an algorithm comparison on shadow
  luminance grain; it covers one 63-frame stack and says nothing about midtone
  or highlight noise.
- **`enfuse`, chroma.** The span is the two opponent chroma channels rather
  than an uncertainty, and each channel is separately bounded away from parity.
- **`focus-stack`, luma.** strehl is placed in `focus-stack`'s own 8-bit
  container before the ratio is taken, so the number is algorithm against
  algorithm and not 16-bit against 8-bit.
- **`focus-stack`, chroma.** This replaces the published 2.03 to 2.24x, which
  divided by a quantisation penalty measured on a different gauge from the
  ratio it was applied to.

**The sentence replacing the struck paragraph.**

> Sharpness is level with `enfuse` at 0.977, and at that matched detail strehl
> leaves measurably less shadow noise than either open-source comparator --
> about 1.6x less than `enfuse` and 1.5 to 1.7x less than `focus-stack` -- with
> every interval clear of parity on two independent implementations.

The matched-detail half of that sentence comes from the sharpness measurement in
`docs/research/V-LINEAR2.md`, **not** from the noise measurement. Keeping the two
sources visible in one sentence is what stops it becoming the circular claim it
replaces.

**Also worth labelling.** The README's existing luma cell, `[1.02, 1.54]`, is not
a confidence interval. DERIVED from M127's own section 4: 1.021 is its raw ratio
and 1.540 its shift-corrected one, so the bracket is the **distance between two
gauges** presented in the notation of an uncertainty. The chroma cell
`1.54-1.76x` is a channel span, which is legitimate but should say so. Both
replacements above carry real resampling intervals.

## 12. A correction to section 4 of this document

Section 4 reported that M127 under-applies its own 8-bit penalty and that **the
error runs in strehl's favour**. The first half stands. **The second half was
itself a cross-gauge comparison and is withdrawn.**

I compared corrected ratios I had computed on the **raw** gauge, 1.088, 1.623
and 1.627, against M127's published values, which are on the **shift-corrected**
gauge. That is the same fault I convicted its section 2 table of, committed by me
one section later. On the single container-matched gauge of section 11:

| channel | M127 published | mine, one gauge | direction of M127's error |
|---|---:|---:|---|
| luma | 1.161 | 1.475 | **understates** strehl's advantage |
| R-Y | 2.028 | 1.661 | overstates strehl's advantage |
| B-Y | 2.237 | 1.640 | overstates strehl's advantage |

So the error is **not uniformly in strehl's favour**. It flatters strehl on
chroma by roughly 0.4x and penalises it on luma by roughly 0.3x. ORCH was told
the favourable direction in my summary and should replace all three cells rather
than only the chroma ones.

The mechanism is the gauge-dependence measured in section 11: M127 measured a
penalty on one gauge and divided a ratio computed on another by it. Because the
luma penalty is much larger on the corrected gauge than the raw one, dividing by
the raw-gauge figure removes too little, and because its applied chroma factors
were smaller still than either measurement, it removes far too little there. The
two errors happen to point in opposite directions once the ratio itself is
recomputed on a consistent gauge.

None of this touches section 8. Those ratios never involved a quantisation
divisor and all six remain inside their intervals.
"""
io.open(P, "a", encoding="utf-8", newline="\n").write(T)
print("appended")
