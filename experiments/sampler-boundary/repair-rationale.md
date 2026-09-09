# Sampler boundary repair rationale

SOURCE ONLY. Candidate patch under charter commit 08a3bd56. The original
align.rs remains unchanged for the independently authored baseline tests.
No Rust code, sampler, build or numerical control was executed by this author.
Application waits for root's committed baseline failure and independent review.
An already-answered/no-change outcome remains valid if that evidence defeats
this proposal.

## Prior answers retained

Root's actual prior_art.py query and its report list are recorded in charter.md.
I read the relevant report passages and the current strict bilinear and cubic
tests. This is not a claim that the repository has no prior border work.

- ORCH-clamp-default-decision.md sections 2, 4-8 and Amendment 1 separate an
  exact value-hull invariant from detail preservation and prohibit changing
  the resampling kernel simply to turn a score green. No kernel/default
  selection, restoration admission, quality bar or M8 status changes here.
- M136-m8-passability.md sections 2-4 and M136-m8-census-groundtruth.md section 1
  establish the hull of the actual consumed stencil and the shared checked
  population. The historic census reproduces coordinate validity and sampling
  support. Its value-hull theorem does not establish that a covered value
  represents the requested fractional coordinate. Its historical findings
  remain bound to their original sources and data.
- BUILD-BLEND.md's reconstruction-hull and exponent-clamp findings concern
  different stages; a clamp that preserves bounds can still alter ordering or
  content. They do not justify altering those merge mechanisms here.
- M194e-joint-pupil.md supplies an independently checked geometric formation
  model with identity per-frame geometry and explicitly limited physical
  scope. It is not a high-edge sampler certificate.
- M-PHASE0-VEIL2.md retains a refused pedestal interpretation and an independent
  Catmull half-pixel predicate that rejected a different cubic parameter.
  Preserve this coefficient distinction rather than swapping kernels.
- align.rs:940 sample_bilinear_strict already refuses a stencil that cannot
  be indexed and preserves phase when it can. It is a correlation primitive
  with a different domain/expression, not a drop-in replacement for the
  renderer's sampler. It is left unchanged.
- Current cubic tests cover exact support hull, in-hull bit identity, integer
  and constant response, unchanged clamped-vs-ordinary checked masks and a
  widened-hull destroyer. Keep them. Their support helper and random-point
  ranges follow the old coordinate clamp; do not reuse that clamp as the
  independent oracle for newly accepted high-edge phase.

## Consumer and exact change

warpmap::gather_checked (warpmap.rs:441) returns a coverage bit for every Some
sample. Placements pull reference coordinates into source coordinates without
inversion. The native full-resolution route (align_cmd.rs:2113) explicitly
converts its plane coordinates by a factor of two before sampling. The new
tests use scalar plane sample pitches, not native sensor pixels. The completed
identity common-TIFF path does not call these samplers.

For one axis of width W, let U be the last legal integer stencil base:

| Kernel | Lower coordinate | U | New upper coordinate |
| --- | --- | --- | --- |
| Bilinear | 0 | W-2 | W-1 |
| CatmullRom / ClampedCatmullRom / Lanczos2 | 1 | W-3 | W-2 |
| Lanczos3 | 2 | W-4 | W-3 |

The draft clamps the coordinate to [lower,U+1], then caps floor(coordinate)
at U. Phase remains coordinate minus that base. For the new final cell,
base=U and phase is in [0,1]. At U+1 it is exactly 1 on the last legal stencil,
rather than floor advancing and reading an unavailable tap. The same rule
applies independently to y.

This repairs checked coordinates in (U,U+0.5], which the existing declared
support mask admits. Their original taps already fit. The finite checked
predicate, its inclusive endpoints, support values and all fallback dispatch
conditions are unchanged. Both cubic variants select the same new stencil;
the clamped variant's actual min/max collection, accumulator and value limiter
are byte-for-byte unchanged after that selection.

Separately, sample_checked rejects either nonfinite coordinate before support
tests or sampler dispatch. This is an explicit domain guard, not a change to
kernel arithmetic. Finite samples, including signed zero, retain the old
coverage predicate. Nonfinite sample data is not covered by this coordinate
guard; the existing clamped-cubic accumulator policy remains unchanged.
Unchecked sampling receives no new nonfinite-input guarantee.

## Unchecked extension is an intentional compatibility change

Unchecked public sampling previously flattened every x>U to the value at U.
The proposed behavior evaluates the final legal cell through U+1 and extends
the result at U+1 constantly beyond it. It therefore changes unchecked
high-side values, including a positive-infinite coordinate that the existing
clamp converts to the upper endpoint. Negative-side extension is unchanged.
This is not a claim of universal unchecked byte identity.

The choice completes the full legal cell and makes the central interpolation
range symmetric: [0,W-1] for bilinear, [1,W-2] for four taps, [2,W-3] for six.
It does not extrapolate a missing source tap. Low/high end regions outside this
range still use endpoint extension, rather than tap replication or a different
kernel. Lanczos coefficients, normalization and accumulation order stay fixed;
normalization is not a proof of exact affine reproduction or exact integer
bits under finite sinc evaluation.

Narrowing sample_checked to U would avoid misleading coverage only by
discarding valid stencils. That is a distinct containment policy with a
coverage/crop cost, not this repair. Repairing just the admitted half-cell
while keeping the old unchecked plateau would drop from the value at U+0.5
back to U on crossing the checked boundary. Capping all unchecked calls at
U+0.5 would instead tie extension to the conservative coverage margin and
leave half a legal cell unused. Neither alternative is selected just to make
one assertion pass; root must explicitly accept the full-cell extension
semantics and its regression evidence.

## Bounds, endpoints and small planes

The existing size guards run before subtraction. Bilinear requires both
dimensions >=2 and otherwise calls Nearest; four-tap kernels require >=4 and
otherwise call Bilinear; Lanczos3 requires >=6 and otherwise calls CatmullRom.
Those branches are unchanged, but a reached fallback inherits the corrected
lower kernel's high-edge values. Do not describe that as unchanged fallback
output.

At the minimum admitted unchecked dimensions, the last base is respectively
0, 1 or 2. Adding offsets gives exactly indices 0..1, 0..3 or 0..5. At the
new upper endpoint, phase 1 does not advance that base. The declared checked
mask still refuses planes too small for its named support; it is not widened
because an unchecked fallback could return a value. PlaneRef::new rejects
zero dimensions and mismatched storage. These are source-derived index
arguments, not executed memory-safety evidence.

The patch preserves sampler computations for finite coordinates when neither
selected axis exceeds its old U: the coordinate clamp and base are numerically the same,
and downstream statements are unchanged. Actual unchanged-region bit identity
and full support-hull behavior remain tests, not author-certified results.

## Independent evidence required before admission

Coordinate_verification owns the exact fixed rows and tolerances. The charter
requires the original public API to produce an actual failing assertion and
to retain every baseline row. The repair author does not run or solely verify
it. The relevant re-choices are literal affine truth for bilinear/cubic;
same-phase translated stencil equivalence for Lanczos; high x/y/corners;
low/interior/integer/null/outside cases; nonfinite refusal; tiny valid planes;
and a public gather with independently enumerated coverage and values.

Unchecked last-cell, exact endpoint and beyond-end behavior must be checked
explicitly, including the named compatibility change and reached fallbacks.
Do not require Lanczos affine equality merely because its weights normalize.
Retain the existing cubic hull/in-hull bit/integer/constant tests. A narrowed
mask or a value-hull-only pass cannot substitute for coordinate truth. No
production diagnostic is added, no physical alignment maps are admitted,
and no new render, default or SOTA claim follows.

## Exact source delta

Original align.rs: 147932 bytes, SHA256
6d33f0e24f21d4370ccd8df0bf618e54a5ad615b838bc265469b4f85051c2786.

repair.patch: 4873 bytes, SHA256
dbf4396c2b52e52fc369061c0f0dc73a6d03d8ec7341fe9b396b6e411b4968ff.

Candidate buffer, not applied: 148796 bytes, SHA256
e5003cf05a2805a0a6a72b6f59f2724bcc8873ebbcc8bbb95a69120bda7a24a1.

Six functions change: the five public interpolators' coordinate/base selection
and sample_checked's finite guard. The diff adds 39 lines and removes 15.
A source-only constructor reversed the six named substitutions and recovered
every original byte. It checked that the on-disk original remained unchanged.
No tests, defaults, coefficients, strict bilinear, nearest, merge or warp-map
functions change. Context/addition lines retain the original CRLF source
bytes; unified-diff headers use LF. Application must verify the exact resulting
buffer rather than normalize the source. A first constructor's non-unique
reverse-fragment assertion refused before file creation; the completed check
uses full function-scoped fragments. This was metadata construction only.
