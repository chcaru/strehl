# Minimal source and full-image integration plan

Root owns shared hooks, fresh build, generated execution and complete RAW run.
This author edits only this folder. Independent review precedes adoption.

1. A core test/feature-gated child module `band_source_agreement_diagnostic`
   includes `core-bridge.rs`. Its only access is the existing private smooth5;
   it changes no production arithmetic. Reuse the existing
   `rb_own_guide_diagnostic::{Fields,canonical_fields,add_fields}` and
   `cross_scale_source_prior_diagnostic::held_state_bit_exact` surfaces.
2. A CLI test/feature-gated `band_source_agreement` includes `implementation.rs`.
   That file includes `operator.rs`, uses the existing two-pass generated
   native adapter, and includes separately authored independent controls.
   No shared file is edited by the operator author.
3. The full adapter should be a small owned adaptation of the existing complete
   source-prior adapter, not a second gather or writer. Accumulate denominators
   for each coarse AC grid in pass1. Pass2 reuses exact canonical fields, checks
   all source/known4/guide/variance/beta/energy/floor/weight hashes and applies
   Agreement before actual add_fields. Keep canonical worker chunk absorption
   and assert finest/base/fallback/hull identity. Only one source's memberships
   and one filtered band are retained; no aligned N-frame volume.
4. Bind the **current** complete corrected chip production master under
   `outputs/quality-september25/chip-fixed`, its299 ordered sources, map,
   reference149 and actual crop[133,89,3250,2166] (6500x4332 output). Do not
   silently reuse the older adapter's crop[141,97,3234,2150] or historical
   current RGB hash. Compare new baseline whole RGB16 and ICC to current
   production. Pin actual resolved baseline tone bits for the candidate using
   the existing fixed-development writer helper; do not resolve separate tone.
5. Reuse root's established bounded runner/source binding and the independent
   current chip target manifest. Produce both complete TIFFs, whole display
   views, and existing native regions. Reject stale source/binary/config
   identities. No default, new detector, adaptive mask, or parameter sweep.

The generated implementation, arithmetic bridge and full-adapter.rs are now
prepared for review. The latter captures baseline development through
highlight_rendering::with_arm(Current), reuses the exact pinned_write recipe
from marigold-source-pure, and requires whole RGB16/ICC identity for the pinned
baseline rewrite plus identical resolved metadata in both writer arms. Its
cache metadata explicitly describes automatic baseline followed by exactly
pinned candidate development. Nothing here reports an executed build.
