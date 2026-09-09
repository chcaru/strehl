# Native sensor transfer stage runner contract

Status: SOURCE REVIEW CANDIDATE. This document defines a future finite execution; it records no build, control, RAW decode, numerical result or performance measurement. Root owns the release and actual execution. The native producer remains the independently reviewed Crop consumer in source/implementation-contract.md; this runner adds no operator, image reader, estimator or quality gate.

## 1. Reuse and scope

run-stage.py adapts the held common-TIFF dimensions runner (33,546 bytes, SHA256 442226bd08b128f8bb97460fab6f8ab6280fd0950d1912313b87d583b7a33940). It loads only the already commissioned M194h module at experiments/m194h-pedestal-causality/build-and-run.py (40,626 bytes, b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410). Its main is never invoked. Source-only AST comparison found need, bootstrap, file_ref, source_check and child_call identical to the predecessor; a one-guard reverse recovered the helper's complete predecessor source text exactly. The reused pieces are authenticated readers/writers, source closure, Budget, environment filtering and closed Job API selection. The copied child_call body retains durable child publication before admission, sampled parent CPU, terminal Job CPU counted once, strict cleanup checks and the compile-only exception.

The new bounded-build-process.py derives from the dimensions helper (16,517 bytes, 1d52b3cd9a4f218b886049f9fcc29b95164e64eb7afb2717a1f3f9646987f31d). Only its exact Cargo command guard changes. Owned suspension/Job assignment, pipe drain, error handling, remaining-PID observations and intentional owned descendant cleanup are unchanged. That policy is selected only for child zero of build-on/build-off. Every native and reader child uses the unchanged strict experiments/m193c-output-grid/bounded-process.py through the held loader. PID observations are never independent kill targets.

The existing dimensions scratch-scan.py (2,991 bytes, 3a1aa413fd4c9d37bccb973a419e3f4c03291903d44b7198c53992e7b00d3e46) is reused without edits. It delegates retained scans strictly and substitutes its no-follow/strict-resolve private path only for the selected fresh build scratch root. Nothing skips arbitrary ValueError, permissions, reparse paths or size failures. Its disappearance census is not an atomic snapshot or peak measurement.

capture-stage.py adapts the existing 3,870-byte dimensions external wrapper. Changes are the five fixed stage names, schemas, timeouts, attempt one, a preextent+1 bounded read, and checking the outer JSON extent/full write before publication. It starts only the controller. The controller owns all subsequent child Jobs. No former source or evidence is edited.

## 2. Exact release and provenance

The root-authored runner release has exactly ten keys:

schema, stage, source_bindings, inputs, originals, command, children, binaries, reader_release, prerequisites.

Schema is native-sensor-transfer-stage-release-v1. All five stages run once under work/STAGE-release-1.json. command is the exact Python executable followed by -I -S -B, the absolute run-stage.py path, --release, the absolute release path, --release-sha256 and ACTUAL_RELEASE_SHA256, which is replaced with the actual held release SHA. sys.orig_argv must equal it.

source_bindings maps canonical repository-relative paths to positive {bytes,sha256}. Each entry is at most 4 MiB, at most 512 entries and 16 MiB total. The mandatory list is literal in REQUIRED: runner/helper/capture/contract/review; charter and scope amendments 2/3; producer implementation contract, adapter, core hook and source review. Held M194h/process/Job/scratch sources and input-bindings-1.json are also mandatory. Controls and verify additionally require independent-read.py; its own reader release must carry the current full source map, including its independent modules, protocol, design and reviews. Root must finish those review files before the associated release. Build releases can precede unrelated checker completion.

All current map entries are read and authenticated at entry and again before completion. The inherited source_closure traverses actual repository Cargo/Rust inputs and literal experiment includes. The actual returned compiled_source_closure is recorded. Every prerequisite's recorded compiled closure must equal the current one. This is the compiled-input property; unrelated later Python/checker files need not share a build's map.

Each prerequisite's actual release is separately opened by its retained FileRef. Its stage and exact command must match the actual result/invocation. The actual external runner FileRef is matched to that historical release's own runner pin, which is authenticated from the current unchanged runner file. This does not replace historical provenance with the current map. Editing that runner after a build requires a separately reviewed recovery; routine checker source completion does not.

inputs is a bounded unique list of tool FileRefs, at most 64 MiB each/256 MiB total. Current Python is required, and builds also require the actual resolved Cargo/rustc paths. Tools are hashed before and after the stage. They are not a full transitive runtime/DLL closure.

originals must equal the exact 27 refs in input-bindings-1.json, 7,119 bytes, SHA256 ab4017907d5ff243ca36883a9e5ff7335717c4f7da4678b01eacab98b3d98b4a. This was separately hashed by root; the runner opens only that metadata and checks the fixed 27 paths, positive extents and aggregate 926,855,168 bytes. It does not repeat original payload binding or decode anything. Originals cannot be smuggled into the repeatedly hashed tool list. The producer hashes each actually visited original, and the independent reader authenticates/decode-checks the fixed originals separately.

Each child entry is exactly {command,expected_exit_code}; expected_exit_code is typed integer zero. No automatic retries or build/generator fallback exist.

Build flag ruling: the source-only metadata inspection found all fourteen applicable Cargo configuration candidates absent: both config and config.toml under the repository and every ancestor .cargo directory through C:/, plus the actually selected Cargo home. Each build repeats the same bounded lstat absence check before launch and after completion and retains all fourteen path/absence records. Any present config is refused, including a dangling entry. CARGO_HOME is recorded as supplied or as the selected user-home default; it is never silently assumed when supplied. This is the narrow fixed current configuration, not a recursive config resolver.

The child environment additionally removes CARGO_BUILD_*, CARGO_TARGET_*, CARGO_PROFILE_*, CARGO_UNSTABLE_* and the listed Rust flags/compiler wrapper/bootstrap variables. Exact argv contains no --config. These checks exclude inherited reassociation/fast-math flags through these configuration/environment mechanisms; they do not claim hermetic compiler, linker, dependency build scripts or native runtime closure. Configuration search and rustflags/environment precedence were source-checked against the [official Cargo configuration reference](https://doc.rust-lang.org/cargo/reference/config.html). That documentation was read; no Cargo process was invoked. The initial fourteen-path inspection read zero configuration payload bytes and found no selected build override environment keys.


## 3. Fixed stages and commands

| Stage | Required prior six-ref bundles | Output |
| --- | --- | --- |
| build-on | none | build-on-1 |
| build-off | build-on | build-off-1 |
| controls | build-on, build-off | controls-1 |
| native | build-on, build-off, controls | native-1 plus native-run-0 through native-run-8 |
| verify | build-on, build-off, controls, native | verify-1 |

Build-on command: cargo test -p strehl-cli --bin strehl --no-run --features native-sensor-transfer --jobs 2 --target-dir ABS/target/native-sensor-transfer-on-1 --message-format=json-render-diagnostics --locked --offline.

Build-off command is identical except it omits --features native-sensor-transfer and uses ABS/target/native-sensor-transfer-off-1. Both target roots and stage outputs must be absent. Each build executes exactly one Cargo child. Admission requires actual Compiling strehl-core and Compiling strehl-cli lines, one successful build-finished record and a unique fresh compiler-artifact for the strehl bin test executable. The exact target/src_path/manifest_path/profile.test and feature vector are checked. The executable is copied, hashed and read back as build-on-1/cli-tests.exe or build-off-1/cli-tests.exe. artifacts has executable, compiled_original, compiler_message and build_finished. No list or trial invocation is added.

Native executes exactly nine commands:
EXE --ignored --exact merge_cmd::native_sensor_transfer::fixed_native_sensor_transfer_pair --nocapture --test-threads=1.

Invocations 0..6 use feature_on; 7..8 use feature_off. The exact per-child environment is recorded before the call and contains RAYON_NUM_THREADS=4, STREHL_PYRAMID_WORKERS=4 and NATIVE_SENSOR_TRANSFER_INVOCATION equal to that ordinal. Other inherited STREHL/M194H/NATIVE_SENSOR_TRANSFER and numerical-library overrides are removed. The actual producer result must confirm the invocation, feature, observer, decode/fold counts and complete paired population.

| Invocation | Inputs | Observer | Feature |
| --- | --- | --- | --- |
| 0 | paper five | on | on |
| 1 | dark twenty-two | on | on |
| 2 | paper five | off | on |
| 3 | paper five | placebo | on |
| 4 | first two dark | on | on |
| 5 | first two dark | off | on |
| 6 | first two dark | placebo | on |
| 7 | paper five | absent | off |
| 8 | first two dark | absent | off |

This preserves 50 producer native decodes, 100 folds, 50 real placed warps, 50 full-frame synthetic probe warps, nine process-local BandGain initializations and eighteen existing writer calls. There is no 27-by-ROI replay. The separate independent decoder remains 27 originals. No-map versus geometrically placed identity remains distinct because native MHC/WB/CA work is preserved.

controls/verify each run exactly:
PY -I -S -B ABS/independent-read.py --mode MODE --release ABS/work/MODE-reader-release-1.json --release-sha256 SHA.

Their reader release is the independent ten-key native-sensor-transfer-reader-release-v1: schema, mode, source_bindings, originals, builds, native, controls, output, limits, command. builds has feature_on/feature_off six-ref bundles. native/controls are null for controls; both are actual completed bundles for verify. Output is MODE-1/check. Each reader child has OPENBLAS_NUM_THREADS, OMP_NUM_THREADS, MKL_NUM_THREADS and NUMEXPR_NUM_THREADS set to 1, retained in operations.environment. These additions do not apply to native calls.

Reader final result.json and actual combined raw child log must be byte-identical and at most 128 KiB. The expected schema is native-sensor-transfer-independent-result-v1. Controls admits only PASS_PRIVATE_CONTROLS_PENDING_ACTUAL; verify admits only PASS_CONDITIONAL_NATIVE_DIAGNOSTIC with software_associations_complete true. physical_model_pass must stay null. The controls result is reused by verify; this runner does not rerun its private controls.

## 4. Evidence and failure semantics

Every stage retains fixed result.json, parent-tail.json, child-NN.json and child-NN.log. Native artifacts.traversals is exactly nine ordered {invocation,result} entries pointing to actual native-run-I/result.json. These are metadata associations; this parent does not decode/rehash all arrays or TIFFs. Independent saved checking remains necessary. Controls/verify publish artifacts.independent_result.

A prerequisite is exactly {result,tail,outer,stdout,stderr,exit}. Result schema is native-sensor-transfer-owned-stage-v1; success status COMPLETE_STAGE_UNVERIFIED. Tail schema is native-sensor-transfer-parent-tail-v1. Actual external schema is native-sensor-transfer-stage-external-v1 with exactly schema, command, source, exit_code, timeout_terminated, elapsed_wall_seconds, stdout, stderr, exit, stdout_bytes, stderr_bytes, scope. Raw files are work/STAGE-external-1-{stdout.bin,stderr.bin,exit.txt,outer.json}.

The parent advertisement is exact canonical raw JSON {status,result,tail}, at most 8 KiB. The external outer must bind that exact stdout, the separate stderr (including empty) and actual exit file. Success needs actual exit zero, no timeout, complete zero-active Job terminal accounting, clean direct exit plus EOF/drain and actual whole controller wall within both stage cap and sampled tail wall+3. Intentional owned compile descendant cleanup is admitted only by the two compile children; failure cleanup never promotes a child to success.

INITIAL_INCOMPLETE is written before sources/prerequisites or a child are processed. Each child receipt and its Job disposition are durable before assertions admit it. A child attempt is recorded before launch. Any refusal stops that stage; dependent stages refuse its bundle. Full stage reservations and failed artifacts are retained; no useful-prefix refunds or hidden retries.

The complete parent CPU is sampled, with a 2 CPU/3 wall final publication reserve, not a measurement of exact terminated parent CPU. Actual terminal user+kernel Job CPU is counted once; no CPU is inferred from wall. The external wrapper measures its directly launched controller interval through exit/wait. Its own setup/publication is outside that interval: root must retain wrapper completion evidence and any separately allocated outer accounting, rather than call it an exact whole-wrapper CPU measurement.

The capture wrapper retains direct raw streams and checks their finite extents after the direct child finishes. It is the existing small wrapper, not a new Job controller; online arbitrary-output prevention and bounded OS/filesystem stalls are not claimed. Timeout cleanup can consume a further finite wait and cause refusal/overshoot. The owned stage has its inherited child cleanup reservation. Parent/source assertion or publication failures can leave only incomplete/prior child evidence and raw terminal output. Producer writer extents are checked only after the unchanged native writer returns, and producer panic need not create failure.json. Attempted-but-unpublished counts remain unknown.

## 5. Prospective finite allowances and normal layout

| Stage | CPU seconds | Wall seconds | Child Job memory | Whole retained family | Build scratch |
| --- | ---: | ---: | ---: | ---: | ---: |
| build-on | 600 | 300 | 3 GiB | 128 MiB | 4 GiB |
| build-off | 600 | 300 | 3 GiB | 128 MiB | 4 GiB |
| controls | 120 | 180 | 1 GiB | 64 MiB | 0 |
| native | 1800 | 1200 | 2 GiB | 256 MiB | 0 |
| verify | 1200 | 900 | 1 GiB | 96 MiB | 0 |

These are conservative prospective ceilings, not prior measured peaks or a timing experiment. Each stage is separately released once. CPU and wall admission reserve the inherited publication tail and remaining child cleanup. Native children use the remaining cumulative stage bound; there is no accidental inherited twenty-second render limit. Reader children additionally cap controls at 100 CPU/150 wall and verify at 1000 CPU/850 wall. Reader memory is at most 1 GiB. Reader read_bytes is a separately explicit positive release bound, not a parent RAW hash permission.

Controls reader write_bytes is at most 62 MiB inside its 64 MiB stage; its current fixed controls declare only bounded final metadata, not RAW arrays. Verify reader write_bytes is at most 64 MiB inside 96 MiB. Reader logical write accounting includes its own final/stdout; the parent separately scans actual physical files.

The original 208 MiB producer allocation remains intact. The native scan explicitly combines native-1 and all nine native-run-I directories; scanning only the parent would omit the producer payload. All retained scans are strict. Nine logs at 1 MiB, nine child records at 32 KiB and less than 2 MiB common parent/external slots keep the declared normal native family below 220 MiB, within 256 MiB. The producer's own 198.6875 MiB complete slot calculation plus its margin is in the implementation contract, including all trace, original/prepared ROI, frame/result/failure, writer and orphan-stage slots.

Each build retains at most a 64 MiB copied executable, a 16 MiB compile log and less than 2 MiB common metadata, below 82 MiB. The original executable remains within the separate 4 GiB scratch census. Controls uses at most 62 MiB reader allocation plus less than 2 MiB common evidence. Verify's 64 MiB reader plus metadata/log reserve is below 66 MiB; the full 96 MiB remains charged.

Common metadata physical slots include the inherited three 256 KiB terminal reservations (canonical/current stage/final allowance), a 32 KiB child record per child, 8 KiB tail, 64 KiB outer, 8 KiB stdout, 32 KiB stderr and 1 KiB exit. Build logs are 16 MiB, native logs 1 MiB each and independent reader logs 128 KiB. The budget's retained scan subtracts all three terminal reservations before launch; those slots are not silently borrowed.

Source-derived normal parent JSON envelope, not an executed candidate or arbitrary maximum: assume actual fixed ASCII paths no longer than 512 characters, FileRefs at most 1 KiB, the fixed 27/9/4 prerequisite population and exact source-defined schemas. Reserve 27 KiB originals; 24 KiB prerequisite FileRefs; 1 KiB release; 9 KiB child refs; 9 KiB traversal refs; 40 KiB ten-member strict inventory; 18 KiB nine operation/env rows; 8 KiB environment; 18 KiB compiler witness plus refs; 32 KiB UTF-8 error/timing/schema remainder and 12 KiB build configuration evidence. Even combining mutually exclusive build/native fields gives 198 KiB, below the 256 KiB canonical cap. Tail under the same path bound reserves 4 KiB within 8 KiB; raw advertisement 4 KiB within 8 KiB. Each write still checks its actual encoding; arbitrary path/error growth may refuse. No separately executed size constructor or universal failure envelope is claimed.

## 6. Source preparation and review boundary

Only source text construction, exact helper-delta comparison and AST parsing are authorized here. They do not import the new or old candidate modules and do not commission process helpers again. Root integrates the reviewed producer patch, freezes actual source/tool/input maps and reviews this runner before any build. Independent checker review and its own current source freeze precede controls. The nine native calls await completed controls, and saved verify awaits all native calls. Completing these operational stages cannot by itself establish physical sensor calibration, real alignment accuracy, full-frame seven-band behavior or SOTA quality.
