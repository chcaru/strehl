# Independent source review of the separate chip observation

VERIFIED by source inspection only; no build, controls, RAW decode or image
judgement by this reviewer. No material blocker remains in the frozen adapter
and runner below. This is permission to execute the explicitly rescoped
observation, not a reversal of the rejected generated qualification.

The only shared-operator change is `FinestSum::full_chip`: exactly the held
3234x2150 seven-band pyramid, count1 or299. The existing generated constructor
and all add/finish/source/apply arithmetic remain unchanged. D0 accumulates
in ascending original source order across chunk boundaries; it is not a sum
of chunk sums. The same SourcePrior applies the same reduced normalized weights,
including exact unsupported bypass and uniform mixed-support contributions.

Pass1 builds Current with canonical75/75/75/74 reductions and records active
u16, known4, guide, variance, beta, E/F and every canonical weight hash. It writes
and checks the complete historical RGB16 baseline before starting pass2.
Pass2 re-decodes one original at a time in the same index/count299 probe gauge,
checks all those hashes/bits, and sends altered coarse weights through the
existing `core::add_fields`, which calls `next_frame()` itself. Candidate and
replayed Current use matching canonical chunks. Finest/base/fallback/hull
state is compared after each source and after final absorption; the repeated
Current collapsed-plane hashes must match pass1. These exact invariants do
not guarantee visible fine-detail retention, as the failed screen demonstrated.

Geometry, crop, metadata/WB/matrix/tone, ordinary optical CA, actual rounded GPU
gather and injected probe stay bound. The all-source support check is the
existing conservative full-source check. Both outputs use the same four-plane
MHC/development writer. No source/image/weight cube is retained: only current
source fields, merge state, D/support pyramids and small per-source receipts.
Several accumulator copies coexist in pass2; the empirical memory cap remains
necessary rather than being inferred from the streaming description.

Cost uses source149 at its original index with the299-frame map/probe identity,
but a count1 prior. Since its prior is exactly one everywhere, full-route
candidate/Current CFA and RGB16 equality is a meaningful no-op requirement.
It does not commission multi-source quality. The runner requires fresh CLI/core
compilation, immutable source/executable bindings, all original12 screen cases
semantically identical with admission still false, then the bounded cost job.
Full permission requires the fixed padded time estimate <=1500s and cost peak
<12GiB; hard full limits remain1800s/7200CPU-s/16GiB. A one-source estimate is
not a guarantee or a benchmark. The adapter reports both source passes and
separate finishing time, including the repeated-Current collapse.

Runner/adapter schema now agrees on `generated_photographic_replay_admitted`.
The runner also checks every replay/held/source boolean, actual source-index
order and historical active-u16/beta receipts, cost exactness, output TIFF hashes,
and complete historical baseline pixels/planes. Original file metadata and
source149 whole-file hash are checked before/after. Read-only imported helper
sources are bound. This review is included in source bindings when present
before build, which is the required execution sequence here.

Finalisation requires the successful complete receipt and exact baseline again.
It retains both TIFF masters and creates complete/native/overview views plus
all seven fixed native pairs with common ICC and exact unresampled pair halves.
Its RGB8 convention is shared within this pair; it is not the vendor comparison's
rounded convention. No gain decision controls which images are shown. All
completions retain false generated admission and an unset visual verdict.

Frozen SHA256 bindings:

| File | SHA256 |
| --- | --- |
| chip-implementation.rs | 5ebb49dce387d3e0e99416e6ac8d1fc033d8dda2070caa37a785e71720e530ed |
| chip-design.md | 37f136fe05ffba1e93c3d9be64f696b0e3836712bfce9ee2597622478d4ea7d6 |
| implementation.rs | 15eb9c445561baf65093f229c0f0acfe3d5d22dc26b67caea2a76a85134c7eba |
| chip-run.py | 1748eaa15c21b46059a934cfbfc34fecf96912091a1b9270a538f03682c564cc |
| chip-runner-plan.md | 3c8100b4386e1852c7f5e3ff79db433155f1180380164ce6bb7e396163296842 |
| observational-plan.md | 9529c92e36b1c722f907e5772a927b01a95666234abdbec2a92f13ed7b4a448f |

The known72% far-component loss and glint damage remain explicit reasons to
reject a general replacement. A useful photographic contact result could only
justify further optional-mode work under the observational plan, not eligibility,
SOTA, an opaque-scene classifier or an explanation of Helicon's behavior.
