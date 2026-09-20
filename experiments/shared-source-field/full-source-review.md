# Independent full adapter source review

2026-09-19. full_context_placement; read-only inspection, no build, generated
execution, RAW read or photograph judgment. **No source blocker found.** This
permits the frozen mechanical/quality screen, not an unconditional full run.
The root runner requires actual screen admission before the ignored full test.

Reviewed SHA256:

| File | SHA256 |
| --- | --- |
| full-stack.rs | f834b0010a51581e8756b7295f497a4d2ffe77520d44e4234b2f665b37c6388e |
| full-adapter-note.md | 7194d28282629b0ae8cdbdbb93a64742477b8815d7acf8dd2b581a1204d9c298 |
| core-bridge.rs | 5ecabd9e80e0eea748654073a59d4a51a9401e301d17c5fda319b7c967b629c7 |
| costs.rs | 1ee7a2c7c6b652c3620583eafebac169345bf7fb8741f4aab0369ac3772eb879 |
| implementation.rs | c8ed6cf75f69d10a407a7abac0c83dd5bda90ea3d4b2edb6b6288dd5029ceb55 |

**Baseline and evidence.** The adapter uses the existing four-plane planning
formula and explicitly requires18,18,18,16 source groups. It preserves the
first-move/subsequent-left-absorb reduction through `absorb_chunk`, resetting
the worker between groups, not frames. Actual `BandWorker::fold` performs its
per-frame workspace invalidation. Immediately after that fold, the bridge
reads retained finest Laplacian/variance, recomputes production `smooth5(L0²)`,
and uses `gate * beta_for(current frame,0) * max(V0,0)`. Neither the later-band
scratch energy nor an estimated private floor enters the field.

The guide is exactly .5 times the completed, post-hull baseline G1+G2, in
black-subtracted DN. The actual four-plane developer writes the baseline;
6920x4612 RGB16 shape, sample count, one page and fixed decoded little-endian
pixel hash must pass before spatial aggregation/replay. Container hash and
Software tag remain distinct. Canonical grouping is therefore structurally
preserved and has a falsifiable complete pixel identity guard; source review
alone does not assert that runtime guard has passed.

**Original sources and placement.** The map hash, complete ordered70 files,
active geometry/stride, ISO, black/white levels, normalized WB bits, matrix,
CA profile key, crop and developer tone are held. Source identity includes the
map's stack check plus original length/mtime checks. Each frame's active u16
hash is recorded before/after pass1 and matched to an independent second
decode. Pass2 calls the same actual rounded GPU gather with that map placement
and crop. All four plane hashes must equal the actual pass1 planes before
replay; their hashes and source u16 hashes are checked again afterward.
This catches a source-gauge/CA/rounding difference instead of relying on two
nominally equivalent sampler formulas. Inputs are opened for reading only.

**Consumer.** The shared replay uses one membership per source/quad for all
four CFA planes, full-context source Laplacian collapse with only the terminal
base zeroed, and canonical source order. Finish computes the frozen f32
`Bpre + (sum(q*sourceAC) - alpha*BAC)` and the original sample hull. It starts
from actual `merge.finish`; alpha0 pixels retain those bits, and all-zero
activation returns that result directly. Coverage must agree with alpha
within8e-6. The unchanged terminal mean base is an algebraic/consumer property,
not a promise that rearranged floating arithmetic is exact everywhere.

**Lifetimes and bounds.** Original frames and gathered planes are local to each
source iteration. Worker scratch is dropped before the second scalar volume.
The two scalar arrays total4,468,105,600 bytes by checked multiplication; D is
released after memberships form, and membership storage is dropped before
final reconstruction. Replay retains four AC sums and current-source pyramid
scratch, not an N-source image/pyramid collection. Baseline accumulators remain
necessary through finish. The second gather may temporarily clone the current
original; this is bounded per source. Peak process memory and time remain
UNMEASURED and subject to the root's16GiB/600-second limits. Sequential path
aggregation and pixel-major membership extraction can be bandwidth-expensive;
source inspection does not establish SOTA speed.

The full adapter has no independent image observer switch. Its added E/F and
hash reads are covered operationally by the retained complete baseline pixel
guard. Generated controls separately cover exact Off/zero fallback, actual
replay arithmetic and source immutability. A passing mechanical screen still
does not establish correct source ownership: max-across-N noise coupling,
coherent late-only rays, equal-mean depth boundaries and real coloured thin
features are independent reasons the frozen quality screen can refuse.
