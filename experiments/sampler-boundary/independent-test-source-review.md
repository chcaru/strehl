# Independent source review of sampler boundary controls

PASS_SOURCE_REVIEW_ONLY for the exact candidate below. No build, sampler,
test, numerical fixture or candidate/helper execution by this reviewer.
Tests: coordinate_verification. This reviewer authored the unapplied repair,
not these tests; root separately reviews and controls release. This is not
verification of a repair outcome.

## Held identities

- crates/strehl-core/tests/sampler-boundary.rs: 31524 bytes,
  SHA256 7dbe20def772279cc012a21dc1d15a742011654c83f150a1049350585ba6d1e9.
- experiments/sampler-boundary/independent-test-spec.md: 15697 bytes,
  SHA256 e9c6c64f3ae2070105be88fc76bd50280bf492e8dcdaec12ebda0475bc514010.
- Original crates/strehl-core/src/align.rs: 147932 bytes,
  SHA256 6d33f0e24f21d4370ccd8df0bf618e54a5ad615b838bc265469b4f85051c2786;
  still unchanged. repair.patch remains outside crates and unapplied.

## Choice review and findings resolved

The requested-coordinate oracle is distinct from the existing clamp and
support-hull helper. Bilinear and both cubic variants compare the actual
public result with literal F(x,y)=1000+8x+16y. Lanczos uses separately indexed,
bit-matching translated stencils and actual same-phase calls; it does not
mistake normalization for exact affine reproduction. These paired calls
establish translation behavior, not absolute kernel fidelity. Unchanged
coefficients remain a separate source-delta requirement.

The 1/32 code-unit tolerance is fixed prospectively. A lost quarter phase
changes the literal ramp by 2 code units in x or 4 in y, materially larger
than that allowance. Finite comparisons reject NaNs. Constant/integer controls alone cannot diagnose
phase loss; actual wrong-translation and wrong-phase calls must differ >0.25. The former changes every translated sample; the
latter changes fractional phase. Stencil mismatch and actual finite output
differences are required, then the correct pair is restored. No coefficient
formula is reused as the Lanczos oracle.

The cubic step checks actually require raw under-hull, in-hull and over-hull
branches, with literal limited values 0/50/100. Three affine cases require
actual in-hull values and raw/limited bit identity. Coordinate truth remains
separate, so shared wrong coordinates cannot turn hull containment into
spatial fidelity. Existing M136 and ORCH default/quality limits remain.

Two concrete findings were sent before hold and repaired:
1. The opposite-direction gather destroyer could previously pass from sentinel
   buffers after a panic/error. Its exercise guard now requires successful
   actual gather, returned/mask count agreement, exact mask and refused NaNs.
   Wrong values are then compared against the independent opposite map.
   The positive coordinate test still separately gates all correct values.
2. The original 48 checked tiny rows never reached a fallback. Twenty explicit
   unchecked-tiny rows now visit all fallback edges with one deficient axis:
   Bilinear -> Nearest; cubic/clamped/Lanczos2 -> Bilinear -> Nearest;
   Lanczos3 -> CatmullRom and the lower chain. Independent literal effective
   endpoints, not lower-kernel calls, define the oracle. Actual endpoint and
   far-high calls must match it and each other by bits. Reached Bilinear/Cubic
   cases must also reject the old plateau by more than 0.25. Checked admission is not widened.

The full gather is one reference-to-source quarter translation on a 128x96
scalar plane. Direct enumeration yields x=1..126, y=1..94: 11844 covered and
444 refused. Both the requested and sign-reversed masks have that count;
their literal values differ. Full f32 bits and masks are retained; count alone cannot certify it.

## Population, API and retention

Source counts total 344: support6, boundary126, null18, nonfinite36, tiny48,
unchecked60, unchecked-tiny20, constructors4, Lanczos18, limiter6, gather2.
Group counts and unique IDs are required. The labelled high-corner duplicates
are not independent replications. Per-call panic capture retains failed rows;
the final aggregate assertion follows all rows, full gather operands and
summary. Baseline must fail as an actual test, with a visited public boundary
failure; it is not relabelled a pass. Repair admission requires complete
passing population and independent evidence review.

I checked imports, public Cx/Similarity fields and constructors, PlaneRef,
Resampler methods, PlaneGeometry and gather_checked Result against the current
crate. The Rust 2024 / 1.98 declaration supports the used language/library
features. No compilation/API mismatch was found by reading; this does not
replace compilation. The index correspondence handles small planes by explicit
bounds; checked insufficient support refuses before fallback, while the new
unchecked table names legal effective endpoints. Nonfinite coordinates are
encoded as integer bits in JSON. Actual nonfinite returns, refusal and panic
are differentiated for the primary call.

The fixed transcript envelope is 344*768 +8192 +114688 =387072 bytes,
under 512KiB, with a 1MiB raw-log backstop.
Terminal/exit evidence is still required; a printed summary is insufficient.
No process or capacity control was executed for this review.

## Existing regressions and exact invocation

The existing tests were read in align.rs and warpmap.rs. The root-adopted
separate library-test invocation selects these thirteen full names:

```text
align::tests::catmull_rom_reproduces_the_samples_at_integer_positions
align::tests::clamped_catmull_rom_stays_inside_the_exact_support16_hull
align::tests::clamped_catmull_rom_is_bit_identical_until_catmull_leaves_the_hull
align::tests::clamped_catmull_rom_preserves_integer_samples_and_constant_planes_exactly
align::tests::clamped_catmull_rom_has_catmull_support_and_checked_domain
align::tests::a_widened_clamp_makes_the_hull_guard_fail
align::tests::a_gather_under_the_identity_is_the_identity
align::tests::lanczos3_is_interpolating_and_preserves_dc
align::tests::lanczos3_support_matches_its_reach
align::tests::lanczos2_is_interpolating_and_costs_no_extra_border
warpmap::gather_tests::gather_marks_uncovered_pixels_instead_of_clamping
warpmap::gather_tests::gather_refuses_a_geometry_mismatch
warpmap::gather_tests::gather_refuses_a_refused_frame
```

They cover integer/DC behavior, limiter containment and live destroyer,
in-hull bit identity, support, identity-gather interior and consumer refusal.
The identity-gather test explicitly requires its unchecked outer border to
differ; it does not promise whole-image identity. The existing support helper
is not repurposed as the new high-edge truth oracle. The high-frequency
comparison test is outside this required set and supplies no quality claim.

Both fresh build commands include --lib and --test sampler-boundary before
freeze. Bind the separately emitted library-test executable. The direct argv
is [that absolute executable, "--exact", "--nocapture", "--test-threads=1",
the thirteen names above as thirteen separate arguments]. No Cargo delimiter,
list process or broad substring sweep is needed. Require exactly those thirteen
named outcomes, exit0 and clean owned terminal accounting. The charter's
separate 30CPU/60wall/512MiB/16MiB invocation bound applies without retry;
build and tail allowances remain separate.

Multiple positional filters use OR semantics, and --exact matches full names,
as documented by the [official Rustc Book](https://doc.rust-lang.org/rustc/tests/index.html#filters).
The [official parser](https://doc.rust-lang.org/src/test/cli.rs.html#280)
retains all free arguments; the
[official filter implementation](https://doc.rust-lang.org/src/test/lib.rs.html#529-557)
selects any exact match. --nocapture is the documented supported alias of
--no-capture. These were source/documentation reads, not a test-binary query.

No remaining blocking source finding on the held pair. This review licenses
source freeze consideration only, not execution success, physical alignment,
image quality, performance, a changed default or application of the repair
before baseline evidence is committed.
