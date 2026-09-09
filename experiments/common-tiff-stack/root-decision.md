# Root decision: common-TIFF stack-to-image integration

2026-09-08. Authorized development under the owner's autonomous research and
implementation program. M194h is complete at evidence6d61340d/report58765d8b.
Its local cutoff explained the selected error and lost broader benefit; no P0
product change or automatic quality sweep is scheduled.

Implement the existing next-consumer proposal: three ordered128x96 common RGB16
frames, known identity grid, explicit HardFloor three-band merge, simulation-only
injected RGB noise, truthful linear-ProPhoto/D50 output. The native CFA path and
HardFloor default remain the current product path. Unknown developed-RGB noise,
real geometry and comparator color semantics stay unresolved.

## Fixed admission and population

Adopt the recipes and twelve ordinals in independent-controls-spec.md and the
closed source-contract.md. These were written before any fixture generation,
build, product invocation or checker. Before execution the exact final source
bytes and command/input maps must be held in a hashed release. Sources may be
completed/reviewed now; this note alone does not launch a stage.

The six positive runs are constant contributors; identical asymmetric address/
color; mixed noiseless; mixed noisy off/on/placebo. Six negative runs are
unsupported provenance, actual variance1, wrong profile, camera-native output,
wrong-size third input, and altered third payload. The last two must exercise
exactly two earlier folds. No extra images, seed search or parameter sweep.
A failed version remains a failed version; preserve its artifacts before any
separately justified source correction or later experiment.

The distinct constant mean must be literal(17000,23000,29000), unlike every
input. InputRange makes the identical-image output oracle exact; that property
only tests address/color transmission and does not certify reconstruction.
Shared accumulated-denominator counts come from actual averaged_fraction(),
one value per level, not per RGB plane or frame. Exclude the always-mean base
from the powered mixed-population criterion. Actual injected variance and
BandGain values, not manifest descriptions alone, must be verified.
Noise-model algebra is derived simulation law, not camera calibration.

The independent Python author uses own standard-library TIFF construction and
reading, differing strip/IFD layout and literal pixel oracles. The reviewer may
reject source choices before release. A report status without actual command,
source, binary, exit, raw stdout, complete prefix and terminal process evidence
cannot admit a run. Output observer off/on/placebo must preserve whole bytes.

## Separate finite execution allocations

| Stage | Aggregate CPU seconds | Whole wall seconds | Owned child Job committed-memory cap | Retained file cap | Scratch |
|---|---:|---:|---:|---:|---:|
| build | 600 | 300 | 3GiB | 128MiB | 4GiB observed census |
| prepare fixtures | 60 | 120 | 512MiB | 16MiB | none |
| twelve renders/refusals | 60 | 120 | 512MiB stage backstop | 16MiB | none |
| independent saved verification | 60 | 120 | 512MiB | 16MiB | none |

Render children additionally cap at15CPU/15wall/256MiB each. Aggregate caps take
precedence and include parent CPU plus every owned child Job once. The final
parent tail reserves2CPU/3wall; cleanup is carved out before launch. No claims of
zero resource overshoot or atomic disk peak. The build scratch census uses the
commissioned disappearance-tolerant scratch-only scanner; retained artifacts
remain strict. Small source/fixture preparation metadata uses an additional
20CPU/30wall/8MiB total allocation, separate from numerical/product stages.
Per-product file plan reserves1MiB, including immutable prefix and incomplete
receipt. Existing refused/complete experiments' allocations are untouched.

Reuse the held owned Job/process primitives. Build uses only the reviewed
compile-only completion policy after actual direct zero exit and EOF. Product
refusal expects exit1 and still requires clean terminal Job accounting, EOF,
zero active processes and no emergency termination. Do not kill peer processes.
No host exclusivity is claimed. Source reads establish a conservative explicit
data bound; actual Job memory is a process backstop, not a native memory
certificate.

One fresh Cargo build of the named binary must retain actual Compiling and
fresh:false executable evidence, copying and hashing that executable. Do not
run ordinary native binaries or old science tests. Product environment removes
STREHL_/M194H_ overrides; no M194h/native FIXED_ENV settings are inherited.
Pin local worker count2. Final releases bind the complete owned Rust/module/
manifest/source closure and exact fixture commands; check bytes before/after.
No executable will be committed or distributed.

## Ownership and next decision

Implementation owns the common-input dispatch and new bin/common-stack modules.
Independent controls own fixtures, literal readers, corruptions and final saved
verification. A separate controller author owns source-bound stage execution.
Root reviews release/resource scope and resulting evidence, preserves exact owned
files, and requests independent final interpretation. The author does not verify
their own product.

Passing admits this bounded software consumer; failure identifies the next
specific repair. Neither outcome changes a SOTA scorecard axis or permits a
physical RGB noise claim. After closure, choose the next concrete program task
from the evidence and continue without waiting for the sleeping owner.

## Build1 refusal and separately scoped build2 correction

The first actual build ran once after source commit5344e81c and releasea187fd93.
It refused on the owned child's committed-memory bound: observed peak Job memory
3,287,552,000 bytes exceeded the unchanged3GiB (3,221,225,472 bytes) limit.
The Job recorded53 total processes and32 active before its owned termination;
final active count0, no cleanup errors, and terminal CPU5.171875 seconds.
Direct exit and EOF were not observed; compile-only cleanup was UNVISITED.
Only12 raw log bytes ('   Compiling') exist, with no compiler artifact or
product executable. Actual external wall1.657 seconds, parent CPU sample1.265625.
This is an actual failed build, not a product/scientific result.

The source-family archive was verified before editing and after ZIP readback:
156 files/5,217,607 source bytes; work/frozen-source-1.zip5,265,631 bytes,
SHA256e63e9a7e5dd227b8de097588194e07224b0bcbf224559c08e4fff01da7c81db3.
All build1 records, allocation and refusal are retained; build1 is never rerun.

ARGUED correction: limit Cargo to exactly two jobs, using --jobs 2 immediately
after --bin strehl-common-input. The owned process count is observed; the number
of compiler workers within it is not separately identified. Restricting compiler
concurrency is a targeted resource mitigation to test on fresh build2, not a
proven historical process-role diagnosis. Keep3GiB/600CPU/300wall/128MiB retained/
4GiB observed scratch. Allocate this separate build2 slice without refunding
build1. The source/metadata lane gains one5CPU/7.5active-wall preparation slot,
so five total slots including build1 fit25CPU/37.5active-wall. Its8MiB file cap
still holds with the source archive. Other stage caps and all scientific bars
remain unchanged.

Use target/common-tiff-stack-2 and build-2 for the fresh binary. The controller,
compile helper, metadata wrappers and independent checker's expected binary
path change accordingly. Freeze2 supplies the common source map to all future
stages. Prepare-1/render-1/verify-1 remain unvisited; exactly twelve product cases
and sixteen saved verifier controls remain fixed. No Rust product, input recipe,
noise setting, observer, gate or writer code changes. Fresh compilation and all
later positive/refusal controls remain necessary.
