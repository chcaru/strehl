# Independent review of vitamin-C weight ancestry

## Decision

The strongest source-visible fan is also selected strongly in the **finest**
merge band. A coarse-only repair or propagation of unpooled fine weights is
therefore not justified by this trace. Spatial pooling of fine evidence remains
a testable candidate, but must first show that its pooled score reverses the
actual compact-core/fan ordering without borrowing a neighbouring surface's
focus. Coarse-band late arg indices alone do not establish late-source
dominance: their leading shares here are usually only a few percent.

## Executed inspection and exact scope

Root fixed six cropped-output-native points before the observer results.
The compact output is 6920x4612; no original active-origin offset is added.
The observer's `completion.json` reports byte identity against the original
complete baseline, TIFF SHA256
`2593ecdaa7bcaa34217b595bd3cdf3622637a3dae115c5e014ff6c6a9635bdf4`.
This independent command then read only sparse diagnostic samples, no RAW
files or TIFF pixels:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B experiments/quality-september19/vitamin-c-weight-trace-review-1/inspect-support.py
```

Exit zero. `result.json` retains the exact native MHC taps and every potentially
influencing band coefficient coordinate, dominant index, concentration and
participation ratio. The small ancestry derivation is commissioned against a
separate forward impulse expansion through odd extents; nearest-coefficient
substitution is explicitly distinguished. This verifies the inspection math,
not image quality or camera calibration.

The actual expansion in `pyramid.rs:236` is separable. An even output coordinate
uses coefficients c-1,c,c+1 with weights 1/8,3/4,1/8; an odd coordinate uses
c,c+1 with weights 1/2,1/2. Repeating that ancestry at each level gives the
collapse support. Final MHC in `demosaic.rs:413` adds the channel/phase-specific
native stencil, with offsets through two pixels. For these points its union
contains six quad positions at band0 and 12-16 at higher bands. The selected
fan points are G2 sites: their green values consume the centre quad directly
at band0, making that particular coefficient an unambiguous fine-band witness.

`darg` is the frame with the largest weight, not an exclusive source label.
The current serial canonical fold and ordered absorption make these zero-based
indices correspond to the input sequence; all seventy frames were retained.
At a diagnostic arg of -1 the default fallback is the unweighted mean, not
missing image data. Band7 is that mean everywhere.

## Measurements

The table gives the band0 coefficient at the native point's own quad. These
are **selection-weight** measurements, not whole-pixel radiance fractions.

| Fixed point | Output-native coordinate | Largest-weight index | Its share | Effective frames |
| --- | --- | ---: | ---: | ---: |
| Facet core | 2624,2906 | 23 | 0.539470 | 2.494849 |
| Facet fan | 2602,2945 | 57 | 0.265402 | 5.998378 |
| Facet structural rim | 2760,2998 | 58 | 0.481776 | 3.376821 |
| Dark core | 3080,2150 | 32 | 0.143628 | 11.839051 |
| Dark fan | 3102,2203 | 69 | 0.956702 | 1.090619 |
| Nearby dark-region structure | 3240,2070 | 25 | 0.591722 | 2.400580 |

The independent MHC neighbourhood strengthens the dark-fan observation: all
six band0 quad ancestors have largest-weight index69, with shares 0.381767
through 0.956702. The exact quad set is
`(1551,1100),(1550,1101),(1551,1101),(1552,1101),(1550,1102),(1551,1102)`.
The facet-fan neighbourhood also has late leading indices throughout (55-61),
but shares only 0.171664-0.315595. It is a mixed contribution, not winner-take-all.

At the dark fan, its own green quad's band1 ancestry is exactly four equal
expansion taps: `(775,550),(776,550),(775,551),(776,551)`. Their leading indices
are 57,57,61,61 and shares 0.123545-0.203383. The wider MHC colour ancestry
includes other indices, so that four-tap statement is not extended to every
output colour. At the facet fan, the own-quad band1 ancestry instead has early
leading indices 0,1,2,6. A single global story across all bands is unsupported.

At bands4-6, late indices also lead at cores and nearby real structure, generally
with only 0.02-0.08 share and broad participation. Thus late `arg` values there
do not distinguish fan retention from normal coarse mixing. The dump lacks
signed source coefficient values, so even an exact interpolation-weighted
summary cannot measure their contribution to the visible ray. The final
InputRange clamp and output tone further prevent reading these as final-pixel
ownership. The report's inference is confined to actual weighting preference.

## Consequence for the proposed fixed support

The initially suggested radius13 **quad** box does not reach either selected
core from its fan: offsets are 22x39 native pixels for the facet and 22x53 for
the dark region. That suggestion is withdrawn before implementation. Radius32
quads would cover both with margin, but is only a declared starting choice,
not a fitted optimum or an M13 result. Wider spatial support increases the risk
of selecting a neighbour at another depth.

The cheapest explicit candidate pools the current finest-band energy and its
injected measured beta0 noise floor separately at that fixed support, then
Gaussian-reduces both fields to each merge level. The existing per-band
exponents and admission rule read those fields; the base remains a mean.
Do not propagate exponent8 weights directly into coarse levels, or compare a
reduced fine-energy field with beta[k]'s coarse-coefficient floor. Those would
introduce additional changes or mismatched units.

Before a complete RAW replay, the real compact core must beat the fan under
this one pooled score on the available diagnostic sources. Failure is useful:
it would reject the proposed mechanism cheaply. A passing small actual-consumer
test must also preserve a nearby genuine coloured thin feature at another
depth, cover an occluding depth step, and retain a real sharp radial feature
that resembles a fan. A flat-noise control must accompany truth error and
true-component recovery; gradient magnitude, reduced chroma power, smoother
winner maps and half-stack agreement cannot certify the result. Include a
smooth/coarse-only target because finest-band evidence can be absent there.

## Prior-art boundary

This is not an exact already-rejected implementation in the reports read.
`BUILD-BLEND.md:933-951` explicitly identifies wrong-focus coarse energy from
defocused bright features as a surviving limitation. `BUILD-ELECT` sections11-14
reject high-pass selection alone for its historical manufactured seam, then
close that seam through the pyramid; that does not prove a source-visible
defocus fan is fixed. Conversely it warns against replacing the pyramid with
hard spatial frame ownership. The current BUILD-BLEND file ends at section17.5;
there is no section18 in this checkout.

M13 requires a depth discontinuity to expose the cost of spatial support; its
old Tenengrad radius does not transfer numerically to this fine-band guide.
V-DILUTE closes the winner-dilution premise, and V-SELECT/V-SOFTCHECK close
half-stack disagreement as a quality discriminator. M28/M89 do not authorize
a generic burst outlier mask for intended defocus variation. BUILD-CHROMA
does not attribute these fans to longitudinal CA, and M54/M97c require actual
capture clipping evidence before a clipping or chroma-neutralization remedy.
