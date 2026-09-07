# M194d independent component and actual-consumer verification

**VERIFIED within the registered component scope:** the independent core tests
and both actual-consumer gather paths pass. All 40 retained TIFFs were decoded
and checked. The first Python reader run was invalid because it overlooked a
libtest output prefix; that failed result and reader are retained and the same
outputs pass the corrected reader. No Rust change, new render, fixture change
or acceptance change was needed. The committed design is
`independent-design.md` in preregistration commit `5f55c9ee`.

The first broader full suites completed with 559 core tests and 138 CLI tests
passed (three CLI tests ignored), including these controls, under Curie's
`checks-1` records. Clippy then requested equivalent `.is_multiple_of(2)` spelling at two
independent stripe-parity expressions. That test-only cleanup changes no input
or assertion meaning; it is recorded before the final build rather than hidden
behind the earlier source hash.

## Choice and source boundaries

The independent test choices precede implementation results. Five 80x64
alternating-row component frames use amplitude10/background4096 and fixed
floors99.9375/100/100.0625, followed by the separately chosen amplitude96
strong-signal control. The predicted response is derived from a period-two
stripe annihilated by the lowpass, not from evaluating the candidate helper
and asserting its own returned weight. Actual energy planes must have the
registered values. The cutoff placebo uses real per-frame BandMerge partials,
erases only below-floor band numerator/denominator, and calls actual absorb
and finish. It is labelled test-only and never available to the scored mode.

The zero-reset harness is retained as a named expected panic: omitting
FrameWorkspace::next_frame caches the first constant colour plane while the
later luma varies. The normal control must follow the correct lifecycle.
The first M194c failures and corrections remain in that milestone's evidence;
they are not rewritten here.

The extreme input is independently chosen as two stripe frames with
amplitude16384/background24576,p8,F1. Finite u16-range input samples and finite
capped weights do not guarantee finite weighted sums. Separate fault injection
tests the absorb and resolved/collapse guards. These tests commission explicit
refusal before hull projection; they do not claim that the extreme fixture is
a physical camera scene or a member of the fixed quality matrix.

The actual-consumer stimulus deliberately reuses our independently authored
M194c frame construction, five nonlinear similarity transforms, full/cropped
geometry and equivalent padded/odd layouts. It changes only the declared mode
to FloorPedestalV1 and adds a test-source read counter. Both gathered/native
paths use the production PreparedPyramid consumer and actual CameraLinear TIFF
writer. The repeat matrix, truth references and quality scoring are root's
separate task; these small derivative stimuli do not replace them.

See `independent-observer-clarification.md` for the counter on/off/placebo
proof added before independent execution. The initial include's source is
preserved in Curie's author-run-1 snapshot. Product/Rust sources were held
unchanged during that first build. Prepared-Pyramid stats flags are unused.

## Reproducible command and evidence boundary

The runner accepts external SHA-256 bindings for a separate core test build
and the final CLI test build. It independently checks actual Compiling lines,
JSON compiler-artifact target/test metadata, original artifact and copied
executable bytes, before/after source maps including external Rust includes,
and current source hashes. It refuses stale compiler artifacts rather than
substituting an arbitrary self-hashed executable. No compile is launched by
this runner.

```text
python experiments/m194d-band-admission/independent-run.py --core-build experiments/m194d-band-admission/author-run-2/core-build.json --core-sha256 930f82d7bd19f6dfcc61b4fd0cbf24a54de093971f791aa934f680827200d5e3 --cli-build experiments/m194d-band-admission/author-run-2/versioned-cli-build.json --cli-sha256 973a0fb48edb88d52b9a6e1037e0fc75e58c495af1aa0e1e9f8e74ca8f2005b0 --output experiments/m194d-band-admission/independent-run-1

python experiments/m194d-band-admission/independent-recheck.py --run experiments/m194d-band-admission/independent-run-1 --run-sha256 58c49988eb1c90bf79191e876209b8ab1a7244cced002b333bf44e30f28a864f --output experiments/m194d-band-admission/independent-recheck-1.json
```

Both commands above ran. The first used the preserved `independent-run-v1.py`
bytes before the prefix correction; use a fresh output directory for a new
run. Python was 3.12.10 (MSC v.1943 AMD64), NumPy 2.4.4 and tifffile 2026.5.2.
The execution was 2026-09-07 11:34:17–11:34:25 UTC; that is provenance, not a
performance result. All ambient STREHL variables are removed; the run fixes
defect/CA off, two workers and two Rayon threads, and runs the independent
module with test-threads1. The core process is separate from the CLI binary.
CLI processes independently select fullres gather0 and1. Observer counters
are local per-source parameters, not process-global environment edits.

The Python reader decodes every actual retained TIFF. It checks RGB16
dimensions, camera-linear description/WB disposition, orientation1,
uncompressed contiguous RGB, absence of ICC/transfer tags, and actual varying
pixels. Layout, poison and counter comparisons require both identical whole
TIFF bytes and identical decoded-pixel hashes. Active-site/model/warp controls
require both to change. The counter arm must record one read per frame;
off/placebo must show their separately specified counter values.

Failures will remain in their original packages. Source changes, if a
compiler/API mistake requires them, need a fresh build binding. A passing
control group cannot clear an unrelated failure. These controls support a
bounded implementation claim; only the separate fixed output comparison can
describe detail, noise and colour tradeoffs, and neither closes a SOTA gate.

## Independent outcomes

| Control | MEASURED / VERIFIED result and restriction |
| --- | --- |
| Actual near-floor stripe | At F99.9375, candidate even-row output4098 DN versus legacy and cutoff-placebo4106 DN; independently predicted share0.200000062578. Maximum error0.0000006257824 DN against the unrounded prediction, below registered0.004 DN. The exact and higher floors give4098 DN for all arms. Every tested interior energy was asserted, so an inactive branch cannot pass this control. |
| Strong-signal destroyer | Independently predicted preferred share0.999519557443 exceeds0.999. Actual maximum formula error0.00022404801 DN; error to the mean destroyer76.754105 DN. The component retains strong preference while smoothing its near-floor discontinuity. This is not a camera-noise/quality observation. |
| Preserved lifecycle failure | The deliberately omitted next_frame call produces the named expected panic. The correctly reset stripe control passes. The expected-failure test is not evidence that the broken source is correct. |
| Numerical formula and units | Thirty independent scalar comparisons pass across p1,2,2.8,3.92,8. Weights are finite and nondecreasing; the above1 floor unit-covariance control passes and the below1 counterexample remains unequal as expected. Eight invalid helper inputs refuse. No common physical constant is calibrated by these tests. |
| Numeric refusal before a clamp | The finite input/finite weight but overflowing product refuses at the accumulator. Finite partial-sum overflow and three injected nonfinite accumulator fields refuse at absorb. Finite-state division overflow refuses at resolved coefficients; finite coefficients whose collapse overflows refuse before the final hull. All seven faults retain the specific error messages. |
| Configuration/storage | Ten unsupported configurations and mixed-mode absorb refuse. Existing reported accumulator/workspace float counts agree between modes for one/three bands. Source review confirms no new retained image arrays; this count is not RSS or an M12 certificate. |
| Equivalent actual layouts | Both gather paths and full/cropped domains yield16 whole-TIFF and decoded-pixel equalities for padding, active origin and unused/odd-tail poison. These reuse the committed independent M194c scene rather than claiming a new physical population. |
| Powered actual changes | All12 active-site/model/warp comparisons change decoded pixels as well as TIFF hashes. A single consumed CFA value is a live input. None of these deliberate changes is scored as an image-quality improvement. |
| Real counter observer | Eight off/placebo comparisons preserve TIFF and pixel bytes. Counting records one read per supplied frame; off records zero; placebo increments the separate counter five times with zero indexed counts. Stats flags are unused, so this is an active observer proof. |

The actual output shapes are274x190 native pixels for full geometry and224x156
for the crop, with three u16 channels. All carry `strehl 0.0.0`, the fixed
CameraLinear/WB description, orientation1 and no ICC/transfer tag. The four
baseline file hashes are retained in `independent-recheck-1.json`, along with
all comparison hashes and counter dispositions.

Source review also distinguishes *numeric dependency* from literal execution:
the loop still calculates the legacy significance-floor temporary before its
mode branch. Candidate weights do not consume it or NU_SMOOTH; this experiment
does not commission the old significance calibration. No request to alter that
unchanged temporary is implied.

## Artifact lineage and retained instrument failure

| Artifact | SHA-256 |
| --- | --- |
| Independent core Rust | `89718084f205e087819fb7aa7d8073ca9977d2182fe246e9833e720133d060ae` |
| Independent consumer Rust | `1942370ba982c6a5bf07e99fd6eda3af28830b63a06dbafa75b24d20fb4248f1` |
| Product pyramid source | `848b485271abc48ee496ee69d70a1e01f45074bfbccde7a7ca076ded90f77d9e` |
| Pinned core executable,6,799,872 bytes | `564611211888221fcbf00a037571e9a0ad104c6e0cecb79a984db3c1c13f85d6` |
| Pinned CLI executable,9,949,184 bytes | `8fe0f83b263424338c704388dfe20219a6ae77ac607ad1e12300d5d4a3bbe46c` |
| Original run/result, retained false | `58c49988eb1c90bf79191e876209b8ab1a7244cced002b333bf44e30f28a864f` |
| Original reader, preserved as independent-run-v1.py | `4bed6490c83d2fc77ecfc31b4a3dd8c542ba4168d7f84a5f15381d6f3120e6e4` |
| Corrected reader independent-run.py | `9e0ddc2609218136a3eb11b4bc2fd4fc43e2cc0fe6af9cf43ba3118fdf3c2751` |
| Recheck of the same retained40TIFFs | `aa0e847f221b94fedcfbd2bbcbd0ad29f6fcbe6c859fc56f9be82675bb67f93b` |

The runner validated103 core and106 CLI source bindings, the original Cargo
artifacts and their identical copies, then found source and executable hashes
unchanged after execution. `independent-stale-bundle-control.json` separately
retains a deliberate read of the stale first build: it refuses at the changed
original artifact. That multiply-stale bundle tests refusal, not each binding
mechanism in isolation.

The first artifact reader required each JSON emission to start its stdout line.
Libtest prefixes the first emission with the exact test name and ` ... `,
so the parser counted19 records instead of20 and refused both completed Rust
runs. The correction accepts only that exact known preamble, retains the
strict20 unique records, binds every original file and reads the unchanged
payloads. The recheck passes; the old aggregate remains false. This is an
instrument-format correction, not a rescued scientific fixture.

The root-owned original-entry default render,40 HardFloor byte controls and40
candidate quality outputs remain separate evidence. This report does not
pre-announce their outcome or infer real-scene SOTA from the component passes.
