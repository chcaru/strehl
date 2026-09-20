# Independent review of the control correction

**Accepted as a test-lifecycle correction, not a relaxed acceptance bar.** The
fresh final CLI controls and full-image baseline guard remain required before
the photographic triplet. No tests, builds or RAW reads were performed by this
reviewer; this decision inspects the saved root diagnostics, lean run and source.

Corrected controls SHA256:
`6c30205b996d7800b03ee93537087ed85192882d7f01ea2493d8ddf1625d7aff`.
The experimental core remains
`7326f08951a939763313f80ae511bdfc22247089eaf8e6317216930c69c158f0`
and full adapter remains
`39f46f632fb4ed57e6c7c4b4cb189d252122548960c61750eb13d67acb6795e3`.
The lean receipt binds the same compiled core, the corrected controls included
verbatim, and the actual geometry functions extracted verbatim. Its passing
result is a bounded linked-core check, not proof of final CLI integration.

The retained first failure explicitly requires
`ones_error <= 0.003 && excursions >= 4`. Both limits remain in the corrected
test, now separately asserted and printed. The original source fixture is
retained. Root's same-core diagnostic isolates one change:
`FrameWorkspace::next_frame()` before each source. Without it, cached colour
pyramids from source0 were reused for all three frames. Actual BandWorker
already resets that cache. The source correction matches that lifecycle rather
than changing candidate fusion or choosing easier inputs.

The added regression has independent rejection power: it constructs fresh
Pyramid objects for each original source, requires source bases to differ by
more than100DN from source0, and compares their sequential arithmetic mean
against the actual resolved terminal base bit for bit. It fails the original
cache omission even when both an expected finish and an actual finish share
the same incorrect accumulators. Collapse of the resolved baseline plus an
independently computed input hull also matches actual baseline finish exactly.

Saved `lean-1/controls/process.log` establishes these exercised cases:

- Original all-ones fixture: four pre-hull excursions, roughly595–608DN above
  the shared source pin; actual clamped values equal the pin exactly. Whole
  image error is0DN, under the unchanged0.003DN limit.
- Added constant-donor fixture: four excursions exceed1000DN; collapse reaches
  approximately2329/2429/2529/2629DN where the common input values are
  1000/1100/1200/1300DN. Actual finish clamps to those exact values. This makes
  the clamp witness robust against roundoff-sized accidental participation.
- Independent three-source mean-base error is0DN. All-ones AC replacement
  preserves the terminal base exactly and differs from both baseline and direct
  donor at25,984 samples. It is not an inert copy of either arm.
- The identical-mask late donor changes25,984 samples. Joint mask normalization
  is active at every level; shared-plane coefficient error is0.00003052DN and
  final image error0.00024414DN, both below the unchanged0.003DN limit.
- Off/zero and observer-after baseline outputs remain bit-identical; original
  arrays remain unchanged. Expected refusal panics are caught negative controls,
  followed by an actual two-test passing status, not an ignored failure.

These are operator checks, not image-quality statistics. In particular, many
changed late-arm pixels establish that the donor intervention is live, not that
one donor is better. The original failed receipt remains useful evidence that
the clamp-participation guard rejected a broken fixture. Neither that failure
nor the lean recovery changes the fixed photographic masks, source labels,
transition inspection or competing-structure requirement.
