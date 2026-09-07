# M194f independent compiled input verification

2026-09-07. **192/192 independent checks pass on amendment1's pinned build4.**
The focused invocation passes seven tests: six independent input groups and
the author's separate default/configuration control. The complete CLI suite
passes145 tests with five tests requiring separate controlled invocations ignored. Source and executable
bindings are identical before/after both runs. This commissions input parsing,
recorded authority, actual source decoding, plan consistency and reread
behavior. It does not admit an intended TIFF population or image quality.

## Choice points and observed behavior

The original153-check population below remains the build2/build3 history.
Amendment1 adds39 checks within the existing plan/reread group, bringing that
group from11 to50; its actual results and command are recorded at the end.

The prospective [input design](independent-input-design.md) precedes the new
adapter's implementation read and execution. It re-chooses actual frame order,
typed metadata, current-source versus declared-source binding, whole-chain
relocation, same-length file corruption, plan offset and second-read faults.

| Independent group | Checks | Deciding input or observation |
| --- | ---: | --- |
| Gate and child authority | 29 | Genuine chain passes; fixture/nonterminal/type/count/binding/source omissions refuse. Actual source hashes are checked at the file-binding boundary. |
| Bounded JSON/CFA | 13 | Exactly1MiB valid JSON and6144-byte payload pass; an appended byte, duplicate keys, nonfinite/trailing/malformed JSON and false hashes refuse. |
| Relocated chain | 9 | Original hashes admit unchanged copied manifest/CFA/gate/result files; changed copied CFA, substituted child or resealed untrusted gate refuse. |
| Manifest and paths | 41 | Wrong phase, same-count swapped geometry, bool/float indices, sensor/model/rounder/source changes, missing/reordered frames and escaping paths refuse. |
| Plan and confidence reread | 11 | Resealed same-size false native offset and changed settings/source/levels refuse; actual second-decode path and private live refusal occur. |
| Actual source/observer | 50 | All active samples match independently decoded little-endian bytes in order `[3,0,4,1,2]`; off/count/placebo counts and real between-read corruption are checked. |

The metadata validators intentionally do not re-derive optical mathematics.
For example, syntactically valid but false source hashes are exercised at
`Bindings::read`, while exact source-name closure is exercised at the pure
validator. This targets the actual consumed check rather than demanding that
each layer duplicate every other layer. Rehashed private parsed records are
API controls and never become genuine authority.

`read_bounded` opens once, limits the read to limit+1, then checks size.
The JSON and source decoders hash the same bounded buffers they parse/decode.
The exact-bound and appended-byte cases exercise this path. This establishes
the code's bounded-read contract, not a process-RSS measurement or adversarial
operating-system race-freedom proof.

The actual computed cover is quad `(5,4,22,17)`, native offset `(10,8)`, with
levels22×17 and11×9. Its intended genuine RGB extent is therefore44×34 and
its confidence grid22×17. This is the observed prepared plan; no favorable
full64×48 output extent was assumed. It realizes one Laplacian band plus base,
as scoped in the preregistration.

Observer off/count/placebo return identical complete decoded sample vectors.
After one reordered pass, success counts are all zero/one/zero and hook calls
are0/5/5 respectively; after a second complete pass they are zero/two/zero
with0/10/10 hooks. Planning reads remain excluded. A real private file change
after frame3's first success refuses on its next bounded read; the failure
leaves one successful decode and one hook. Restoring the bytes permits a
second success. Rebinding a separately constructed private source to changed
valid bytes produces different actual samples, so the decoder control is live.

The actual confidence-pass companion first performs five explicit manual
decodes, then runs production `confidence_pass`; all counts reach2 and all374
quad sites have seen5. This companion writes no TIFF. The distinct failure
arm runs the actual prepared production fold with confidence enabled and an
explicit private attempt2 fault at original index3. It reports
`frame 3: M194f injected decode failure at index 3, attempt 2` with attempts
`[2,2,2,2,2]`, successes `[2,2,2,1,2]` and nine hooks. Neither RGB nor Gray
output exists. This is the observed second-read failure, not a fault inserted
before the first fold decode. Intended healthy RGB/Gray identity and values
remain the later root/Zeno population's responsibility.

## Build, commands and preserved revisions

Build1's macro-recursion failure was retained by root before Rust type checking.
The author split the large plan expression without changing its fields.
Build2 then explicitly compiled and passed the153 checks and145-test suite.
Those records remain at `independent-input-run-1/result.json`, SHA
`6df33bcf47dfaf989246bf1c78f4e2cff401296186788ed2ad13c233af6aa96c`,
and `independent-cli-run-1/result.json`, SHA
`edaba70f5003021a57675a30a7fbc482306c52ff403372b5f1dca5481cbbac99`.

Lint cleanup then replaced fixed two-byte `chunks_exact` iteration with
`as_chunks::<2>().0.iter()` in the adapter and independent decoder. The byte
interpretation remains explicit little-endian; no test predicate changed.
Final independent Rust source is
`8e20987c3ecd1aaa74b4f8d38574f7e5be2b8533407ade73dfc40ce765b86bd7`.
The earlier source snapshots preserve the previous passed revision.

Root supplied final `build-3.json` externally with SHA
`69a8979821c074d247514f1deae3fb38dce3b8246013a19dc2f9beb8eceb7fcc`.
The independent launcher checked the actual compiler log's explicit CLI
compilation, both actual compiler/copied binaries, the complete current source
set and the own Rust include binding before running only fixed arguments.
It records source/executable checks again afterward; it executes no command
taken from an untrusted artifact. The launcher source is
`44163c961cfcd7c8f7d547c232b624ab0bf7f158dd76deb2656d7144d9a81776`.

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194f-production-bridge/work/independent-input-run-cache-2 experiments/m194f-production-bridge/independent-run-inputs.py --build-record experiments/m194f-production-bridge/build-3.json --build-sha256 69a8979821c074d247514f1deae3fb38dce3b8246013a19dc2f9beb8eceb7fcc --output experiments/m194f-production-bridge/independent-input-run-2 *> experiments/m194f-production-bridge/independent-input-run-2.log
python -B -X faulthandler -X pycache_prefix=experiments/m194f-production-bridge/work/independent-cli-run-cache-2 experiments/m194f-production-bridge/independent-run-inputs.py --build-record experiments/m194f-production-bridge/build-3.json --build-sha256 69a8979821c074d247514f1deae3fb38dce3b8246013a19dc2f9beb8eceb7fcc --output experiments/m194f-production-bridge/independent-cli-run-2 --suite *> experiments/m194f-production-bridge/independent-cli-run-2.log
```

Both exit0. Final focused record SHA:
`622e30cbfbbb8ef8785b1e2ac202467ae314b6c3b33397ce7fe20b600f7c669e`.
Final CLI record SHA:
`854f0fdd0f88a01c0642d82080a5d4e1db1024ff2d62f972638579a08b51daa2`.
Each record binds six actual independent child result files, full check rows,
raw logs, exact interpreter/environment and unchanged source/executable bytes.
No new RAW, optical image, scoring bar, merge default or numerical-source
change was made by this lane.

## Amendment1: actual MHC, exposure refusal and separate WB bindings

The original intended exposure+1 arm was impossible on CameraLinear and
correctly refused after root's first four intended RGB outputs. Earlier
stubbed schedule checks did not discover that semantic mistake. The retained
first population has no completed index. Amendment1 and both independent
design reviews were committed at `b0b55909` before implementation; this lane's
[prospective review](independent-amendment-1-review.md) distinguishes the
sampled-site writer predicate from an invalid all-pixel WB oracle.

**VERIFIED component and input scope.** The same six independent groups now
contain192 passing checks. Actual `Exposure::resolve(false,1,false)` returns
`NeedsSrgb`; zero returns `None`. Exposure1,2 and255 refuse before a bridge
plan. Both registered WB modes and their own recomputed plans pass; malformed
modes and cross-mode plan reuse refuse. Five modified plan fields are tested
both with a stale checksum and after recomputing that checksum: writer red
gain, frame WB, mode, green gain and blue gain. Every rehashed mutant refuses
against the independently supplied actual settings. All five decoded genuine
frames still return baseline WB while the red-double plan records distinct
writer WB and unchanged frame WB.

The direct10×8 **DN-valued f32 Mosaic** calls the actual `demosaic_row`, with
the demosaic override absent. It performs no normalization or TIFF writing.
The registered non-affine fixture produces these exact component values:

| Site/channel | Baseline DN | Red-sites-doubled DN |
| --- | ---: | ---: |
| R at(4,4) | 1064 | 2128 |
| Interpolated G at(4,4) | 1052 | 1084 |
| Interpolated B at(4,4) | 1048 | 1096 |
| Interpolated R at(5,4) | 1082 | 2114 |
| G at(5,4) | 1080 | 1080 |

Thus the wrong all-pixel red-doubling oracle fails by50DN at(5,4), and wrong
G/B identity fails by32/48DN at(4,4). The same actual dispatcher on the
constant companion yields RGB1000/1000/1000 before and2000/1000/1000 afterward
at all80 pixels, including reflected borders. These live and inert cases
commission the component distinction; the delivered writer's sampled-site
rounding/clipping predicate remains Zeno's independent actual TIFF check.

Build4 SHA is
`b1930156c50817df7d801f3ff6585fb9f6b965f047adfdcc61e8520192c362bd`.
Independent Rust SHA is
`1428f4e870da36c39e50f2d58e96f87e26454d00221a9ecd8e19a0491d8573a7`.
Both commands below exit0 on the actual pinned copy and verified compilation
record, with unchanged source and executable bindings. Focused tests pass7,
ignore2; the complete CLI suite passes145, ignores5. The independent launcher
is unchanged from the previous revision.

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194f-production-bridge/work/independent-input-run-cache-3 experiments/m194f-production-bridge/independent-run-inputs.py --build-record experiments/m194f-production-bridge/build-4.json --build-sha256 b1930156c50817df7d801f3ff6585fb9f6b965f047adfdcc61e8520192c362bd --output experiments/m194f-production-bridge/independent-input-run-3 *> experiments/m194f-production-bridge/independent-input-run-3.log
python -B -X faulthandler -X pycache_prefix=experiments/m194f-production-bridge/work/independent-cli-run-cache-3 experiments/m194f-production-bridge/independent-run-inputs.py --build-record experiments/m194f-production-bridge/build-4.json --build-sha256 b1930156c50817df7d801f3ff6585fb9f6b965f047adfdcc61e8520192c362bd --output experiments/m194f-production-bridge/independent-cli-run-3 --suite *> experiments/m194f-production-bridge/independent-cli-run-3.log
```

Focused result SHA:
`79a47aeb77641384e2c9091c2da1a4ab2c97ca8974cfccd40e792bb7d1ab6271`.
CLI result SHA:
`b1c76fca03cf7a0c0d6fd84a67dad585ca877685fd02101f5494c9324087bcc7`.
No intended new TIFF or optical authority is issued by these controls.
