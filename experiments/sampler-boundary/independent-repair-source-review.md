# Independent sampler repair source review

PASS_SOURCE_REVIEW_ONLY, 2026-09-08. Reviewer: coordinate_verification,
independent of the existing samplers and proposed repair. I authored the new
public-API test; its source is independently reviewed by the repair author and
root. This note reviews the repair, not my own test results. No sampler, test,
control, Cargo build, image or product was executed. Original align.rs stays
unchanged until root admits and archives the actual baseline.

## Exact reviewed buffers

| Role | Bytes | SHA256 |
|---|---:|---|
| Original crates/strehl-core/src/align.rs | 147932 | 6d33f0e24f21d4370ccd8df0bf618e54a5ad615b838bc265469b4f85051c2786 |
| repair.patch | 4873 | dbf4396c2b52e52fc369061c0f0dc73a6d03d8ec7341fe9b396b6e411b4968ff |
| Candidate, reconstructed in memory only | 148796 | e5003cf05a2805a0a6a72b6f59f2724bcc8873ebbcc8bbb95a69120bda7a24a1 |
| repair-rationale.md | 9734 | 4746f07b0ccd9adffa5334fbd6f2154dd3b6650c439c1391c88abc1b9bc177be |
| Unchanged crates/strehl-core/src/warpmap.rs | 54829 | 9d2198eeab5e8a941e297cf8fcd8a217d2454390220433ae19cc6b07e6fd721b |

A metadata-only unified-diff reader independently checked every old hunk
against the original bytes, constructed the candidate in memory, checked its
pin, and reversed all six hunks to recover every original byte. It wrote no
candidate file. There are39 added and15 removed lines. Five coordinate/base
selections and the checked finite-coordinate guard are the only changes.
Coefficients, weight normalization, accumulation order, clamped-cubic limiter,
support literals, size-guard dispatch, Nearest, strict correlation bilinear,
public enum, existing tests, gather and defaults remain outside the delta.
Mixed patch newline representation is intentional: application must verify the
candidate bytes, rather than normalize the original source.

## Independent choice of edge contract and index bounds

The consumer's coverage promise concerns the requested source coordinate.
M136's actual-stencil hull census repeats the coordinate clamp; it cannot
supply that oracle. I read the charter, named prior-art passages, the original
samplers and PlaneRef constructor, and the public gather consumer. The scalar
sample-pitch gauge is retained; native CFA conversion and physical alignment
are different claims. The common-TIFF identity path is not sampler evidence.

I independently choose the full legal final interpolation cell. It extends
Bilinear over[0,W-1], four-tap kernels over[1,W-2], and Lanczos3 over[2,W-3].
This is a compatibility decision for unchecked calls, not an inference that
all old outputs are invariant. Keeping the old plateau while preserving the
new checked half-cell would create a drop on crossing the checked boundary;
shrinking checked coverage would discard legal stencils. Neither substitutes
for the charter's requested-coordinate contract.

For one axis, re-derive bounds directly from actual tap addresses:

| Family | Minimum dimension | Legal base range | Tap offsets | Maximum tap |
|---|---:|---|---|---|
| Bilinear | 2 | 0..W-2 | 0,1 | W-1 |
| CatmullRom/ClampedCatmullRom/Lanczos2 | 4 | 1..W-3 | -1..2 | W-1 |
| Lanczos3 | 6 | 2..W-4 | -2..3 | W-1 |

At the new endpoint, capped base U and phase1 retain the last legal stencil;
merely raising the coordinate clamp without capping the base would not.
At the minimum dimensions these are exactly the full2-,4-,6-sample supports.
The same bounds apply independently to height, including rectangular planes.
Every size guard precedes subtraction. PlaneRef requires positive dimensions
and exact checked-multiplication storage length; the resulting row/tap indices
stay within that slice. This is a source argument, not executed memory testing.

Checked finite bounds remain[s-0.5,W-0.5-s], inclusive. Their high endpoint is
U+0.5: the repair preserves its fractional phase without advancing beyond U.
At low bounds, integer bases, interior and signed zero, the new finite guard
and unchanged comparisons do not alter coverage. When both coordinates stay
within the old inner range, clamp/base values and subsequent statements are
unchanged. Arithmetic accuracy and compiler behavior still require actual
regressions, rather than this textual argument.

## Cases beyond the principal high-edge rows

Unchecked values in(U,U+1] change deliberately, and all values above U+1 now
extend that endpoint. Positive infinity already becomes the clamp endpoint
and therefore also changes; negative-infinite lower extension does not.
There is no new unchecked NaN guarantee. Checked NaN or either infinity now
refuses before dispatch, including on tiny planes. This guard does not make
nonfinite source samples valid or alter the cubic's existing overflow/NaN
limiter policy. Finite sinc evaluation also does not justify promising exact
Lanczos integer bits or affine first moments.

For deficient width OR height, fallback dispatch is unchanged but its values
can change when a lower sampler reaches the repaired edge. Lanczos3 can reach
CatmullRom, then Bilinear, then Nearest; the two cubic variants and Lanczos2
can reach Bilinear then Nearest. A checked refusal cannot demonstrate any of
those inner outputs. Before freeze, independent test review identified this
coverage gap and root fixed20 unchecked rectangular fallback cases, with
literal effective endpoints and an old-plateau discriminator where applicable.
The gather destroyer was also narrowed to an actually completed count/mask
population, preventing a panic/sentinel buffer from claiming rejection power.
These were source-review corrections made before any sampler results.

## Admission limits

No remaining source blocker found for the held patch and explicit extension
contract. This is permission to proceed to the root-controlled evidence sequence,
not a measured repair pass. Require the original344-row public test to retain
an actual exercised boundary failure, then the repaired complete population
and the thirteen exact existing unit regressions, with separate source/artifact,
exit and resource evidence. The existing clamped-cubic hull and in-hull identity
predicates remain required; a hull-only pass cannot certify coordinates.

The new test/spec have separate independent source reviews. Their finite
literal and same-phase oracles do not establish every possible signal, huge
coordinate magnitude, arbitrary sample nonfinites, image quality, performance,
physical correspondence, a kernel ranking, restoration eligibility or a new
default. In particular, do not describe preserved dispatch as preserved
fallback output or general unchecked identity. Root retains release authority.
