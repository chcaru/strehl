# M194h build and execution contract

SOURCE ONLY, 2026-09-08. This is the new pedestal-causality experiment's operational contract. It does not authorize execution. Root releases each exact stage only after independent source review. No M193c resource grant is reopened, and no old executable, input, result, or target directory is overwritten.

## Fixed population and source seam

Read experiment-decision.md and the held M194g pedestal proposal together. The feature m194h-pedestal-causality is disabled by default; the CLI forwards the core feature. The new core hook is included from pyramid.rs and the ignored production test is included beneath the existing noise_pupil_bridge module. No user-facing option or normal default changes.

The core test is exactly:

    pyramid::m194h::controls::fixed_threshold_null_and_observer_controls

It makes26 tiny merges/130 frame folds plus one rejected entry, as declared by component-controls.rs. This is one new component test through the actual hook. None of the old broad intake/control campaigns is repeated.

The production test is exactly:

    merge_cmd::known_scene_benchmark::noise_pupil_bridge::pedestal_causality::m194h_fixed_pedestal_case

Its12 cases are fixed in ordinal order: seed743 H off/on/placebo, seed743 P off/on/placebo, seed743 P0 off/on/placebo, then noise-free H/P/P0 off. Each is one original full-five-CFA consumer call. There are no plan-only invocations, extra seeds, changed floors, texture runs, or automatic retries. A failed case stops the remaining schedule and retains every completed/refused prefix. The complete12 population remains a prerequisite for a complete scientific interpretation.

Every product process receives exactly M194H_GRANT, M194H_GRANT_SHA256 and M194H_CASE plus the inherited fixed settings RAYON_NUM_THREADS=2, STREHL_PYRAMID_WORKERS=2, STREHL_DEFECT=off, STREHL_FIX_CA=off, STREHL_FULLRES_GATHER=1. All other STREHL/M194H/Rayon/numerical thread overrides are removed. The original source uses its fixed Count mode for actual five per-index receipts; this setting is the same in every case. The new observer off/on/placebo scope is the feature-gated core trace.

## Prior build evidence and separate envelopes

DERIVED planning evidence comes from the immutable M194g bridge-build-2 result/log and a Force metadata census of target/m194g-noisy-bridge-2. The old fresh debug CLI build took25.063 seconds; its copied executable was12,767,744 B, and its compiler log182,883 B. The unchanged target contained2,217 files and1,674,906,257 B. These records have no complete CPU or peak-memory observation. Disk size is not memory use, and these timings are not a benchmark of the new hook.

Root accepted the following finite prospective maxima:

| Stage | CPU seconds | Whole wall seconds | Child committed-memory ceiling | Retained files |
| --- | ---: | ---: | ---: | ---: |
| Metadata preparation |30|60|not a numerical stage|8 MiB |
| Two builds and two listings |300|240|8 GiB|128 MiB, plus separate4 GiB fresh scratch |
| One component test |60|60|1 GiB|2 MiB |
| All12 renders |120|180|1 GiB|16 MiB |
| Independent saved checker, pending its final ledger |60|120|1 GiB|16 MiB |

Each render also has20 CPU/20 wall seconds maximum. Per-child allowance can be smaller when the aggregate remaining budget requires it. Aggregate render120 CPU is not12 times20 CPU. Build scratch is target/m194h-pedestal-causality-1, which must not exist before the first compiler invocation. No clean/copy/restore is performed on old targets.

The resource-ledger.json records all byte families. Build reserved103,481,344 B leaves30,736,384 B of its128 MiB; components688,128 B leaves1,409,024 B of2 MiB; render12,681,216 B leaves4,096,000 B of16 MiB. These are predeclared bounds, not measured actual costs. Unused reserve never authorizes another call.

Render case slots total856 KiB each: plan128, trace binary128, trace header16, TIFF512, canonical result32, simultaneous result-stage32, failure8 KiB. Twelve slots cost10,518,528 B. Twelve64 KiB logs, twelve32 KiB child terminal receipts,192 KiB parent publication slots,512 KiB controls/metadata/tail and256 KiB external receipts are separate. Empty off/placebo trace.bin is legitimate evidence and is not admitted into a positive-only source namespace.

Trace capacity is32,768 original u32 words=128 KiB, enforced before core appends. It is not a promise that an arbitrary128-site-per-level trace will fit. The fixed two native5x5 MHC envelopes have source-derived support counts18,18,15,16. The trace payload has8,064 words before absorb/reset records, plus4 words per absorb and3 per reset. Even bounding each of those lifecycle calls by5 gives8,099 words=32,396 B, well within128 KiB. The independent checker must confirm the support and actual lifecycle from retained records; this is a DERIVED source bound, not an executed trace measurement. No trace support is dropped to fit the file cap.

## Minimal reusable owned-process instrument

build-and-run.py uses immutable experiments/m193c-output-grid/bounded-process.py, SHA25647b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b. Only its generic run function is used. The controller never calls that module's load_job_api, which would execute the whole historical M12 harness and import numerical/image dependencies.

The Windows Job API comes from the already commissioned, closed AST selection of the original m12-harness.py: kernel32/ntdll initialization, four required accounting/limit structures, constants, create/assign/query helpers and the exact argtypes/restype assignments including NtResumeProcess. The required list is explicit in the new source. All excluded harness declarations remain unexecuted. New controller imports are stdlib only.

The unchanged runner creates the child suspended, installs owned Job memory limits, assigns then resumes, retains merged bounded logs, polls accounting, observes direct exit/pipe EOF, drains the whole Job and closes only its own handles. Existing cleanup may spend up to5s termination +5s wait +1s thread join; the new launcher subtracts a separate12s cleanup reserve and3s parent publication reserve from aggregate remaining wall before every launch. This does not promise recovery from an unbounded OS/filesystem stall.

New live accounting observes the same returned Job record without mutation, validates actual integer nonnegative user/kernel/total/active fields, requires total=user+kernel and monotone total, then checks parent process CPU + previously completed Jobs + current Job once. No parent verification Git subprocesses are spawned. An invalid accounting record blocks further ordinary work.

The exact final child record is written/fsynced/read back into its fixed32 KiB slot and linked from the parent BEFORE terminal CPU, stage cap or successful-exit admission. Thus an overrun can retain its actual observation; bounded failure publication never authorizes further science. Terminal Job active_processes must equal0 for complete current-run CPU. A lost/incomplete Job record is not invented or replaced by a measured-complete claim.

New metadata controls run before the first child in each stage. They check typed Job components, wrong-total/negative/bool rejection, the same aggregate CPU predicate on4+95=99 and6+95=101 against100, finite-overflow/duplicate JSON rejection, actual prewrite overflow preserving a prior canonical slot, and same-slot restoration. These are explicitly injected accounting and metadata-path controls, not actual Windows process-boundary or scientific evidence. The existing OS instrument is reused without another intake commissioning campaign.

## Exact build and artifact proof

Root's build-stage release fixes these four children, in this order (paths are absolute in the actual release):

    cargo test -p strehl-core --lib --features m194h-pedestal-causality --target-dir C:\dev\blog\death-of-software\projects\strehl\target\m194h-pedestal-causality-1 --no-run --message-format=json-render-diagnostics --locked --offline
    cargo test -p strehl-cli --bin strehl --features m194h-pedestal-causality --target-dir C:\dev\blog\death-of-software\projects\strehl\target\m194h-pedestal-causality-1 --no-run --message-format=json-render-diagnostics --locked --offline
    <build-1/core-tests.exe> --list
    <build-1/cli-tests.exe> --list

The two selected builds are necessary because a CLI dependency does not compile core's cfg(test) component test. Neither build executes tests. No -q suppresses compiler evidence. Each actual compiler log must contain Compiling for its selected crate and a unique compiler-artifact message with matching manifest/source/test target, fresh=false and the new feature. Both test artifacts are copied only to fresh fixed names; original/copy bytes must match. Their actual test listings must contain the exact respective new test. The retained cargo/rustc command files are inputs, with Cargo.lock, offline/locked flags and observed environment. This is source-to-artifact evidence, not a hermetic transitive toolchain certificate.

The source closure includes the scoped .gitattributes (* -text), workspace Cargo.toml/Cargo.lock, the explicit compiled core/defect-map-ILCE-7CM2-dust.txt literal input, current owned crates' Rust/manifests, build.rs where present, recursively resolved literal include!(concat!(env!("CARGO_MANIFEST_DIR"),...)) and #[path] files, both new feature manifests, new core/bridge/component sources, all controller/protocol/ledger and independent checker/review sources, and the unchanged Job instrument/harness. The inherited explicit include forms are not claimed to be a general Rust macro parser. Root freezes complete source closure before building; the controller authenticates every positive binding before and after work.

Whole-TIFF identity remains required against the archived H/P and noise-free endpoints. The actual camera-linear branch writes measurement Software="strehl 0.0.0", so a new build does not require weakening historical whole-file equality. Canonical pixel bytes are checked too. Current noisy off/on/placebo whole-file hashes must match for each arm; the independent checker additionally requires actual enabled/disabled hook counts and the complete consumer/trace identities.

## Stage and science authorities

The driver release is a separate closed9-key object:

- schema: m194h-owned-stage-release-v1.
- stage: build, components or render.
- source_bindings: canonical repository-relative path to closed {bytes,sha256}; positive, <=4 MiB each, <=16 MiB aggregate.
- inputs: at most64 closed FileRefs for exact tool/held evidence; <=64 MiB each and <=128 MiB aggregate, checked before payload hashing. The current Python executable is mandatory, and build also binds resolved cargo/rustc command files.
- command: exact Python controller argv; ACTUAL_RELEASE_SHA256 is its only substituted token.
- children: exact ordered argv arrays above or the one component/12 case arrays.
- binaries: empty before build, then exact core/cli copied executable FileRefs.
- subject_grant: null except render; exact FileRef to the bridge's closed8-key grant.
- prerequisites: complete earlier stage terminal/outer bundles, not canonical positive alone.

Actual controller command is fixed as selected Python -I -S -B build-and-run.py --release <absolute release> --release-sha256 ACTUAL_RELEASE_SHA256. Metadata preparation is root-owned; it must construct exact stage releases and retain commands/closures, rather than infer a grant from this document. No release or prior-work file is created by the driver.

The bridge grant is unchanged: schema=m194h-pedestal-causality-release-v1, source_bindings, noise_admission, matrix_index, quality_verification, binary, commands, cases. Sources/binary must agree with the driver, and commands contains the one exact binary test argv. The driver iterates the fixed12 case environment ordinals; the bridge independently validates case settings.

Root must bind the fixed original noise-admission1082 B/088272bf...,38-case matrix66801 B/03e7ffe9... and independent quality result317942 B/5a0c6dcc... and their existing input/endpoint closure. This does not re-authorize a new decode population: the only data are the admitted original five noisy/full-CFA files and their existing noise-free counterparts. No runtime discovery, model download or new independent stack is involved.

## Terminal admission and pending independent choices

Parent result.json is a bounded64 KiB canonical record initialized INCOMPLETE. Per-child receipts are detached; source closure is a digest/reference rather than a repeated registry. Publication stages are fully written, fsynced and read back before replacement. A failed publication or stdout flush cannot be retracted, so actual outer nonzero/missing association always defeats a stale positive.

After canonical publication, parent-tail.json records the later whole-parent process CPU sample, completed child Job CPU once, whole elapsed wall and2 CPU/3 wall reserved external tail. Root retains exact raw stdout/stderr/exit plus the actual outer command/interval; the next-stage reader requires their associations. A current parent CPU sample is never called the exact whole terminated process CPU. The established root wrapper has no whole-parent CPU field, so the sampled CPU plus reserved conservative tail remains explicit; CPU is never inferred from wall. Source status COMPLETE_STAGE_UNVERIFIED means only this stage finished its declared operations; independent science verification still has to run.

The prerequisite is a closed {result,tail,outer,stdout,stderr,exit} FileRef bundle. External schema=m194h-stage-external-v1 has command, source FileRef, exit_code, timeout_terminated, elapsed_wall_seconds, stdout/stderr/exit FileRefs, stdout_bytes, stderr_bytes and scope. The reader checks exact source/argv, exit0/no timeout, all raw associations, canonical raw advertisement bytes, tail-result identity, whole elapsed<=sample+3 and the unchanged stage wall/CPU envelope. Empty stderr is valid bounded evidence, never a positive source.

A normal parent terminal has at most60 path-bearing FileRefs in the render case (36 case refs,12 child refs,12 prerequisite refs); declared paths are ASCII and <=384 characters. Allow512 bytes per canonical ref,4 KiB argv,8 KiB bounded environment and8 KiB fixed bookkeeping:50 KiB total. Build substitutes two <=8 KiB compiler messages and fewer refs, also below60 KiB. Every write still enforces64 KiB, and detailed refusal is allowed to fall back to an earlier canonical record with actual nonzero outer disposition. Metadata control records have separate8/16 KiB slots; raw stdout<=8 KiB, tail<=8 KiB. These are source-derived finite bounds, not candidate execution.

Before source hold: independent readers must confirm exact compiled include closure, complete trace word bound, stage prerequisite external schema, normal terminal size/fallback capacity, and the new accounting/metadata controls' power. Those are concrete source-review dependencies, not permissions for a new scientific variant. Preserve all refusal evidence; root must issue a new finite reviewed grant for any future corrective attempt.
