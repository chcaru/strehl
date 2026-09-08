# Startup attribution 2: committed-memory amendment

SOURCE-ONLY amendment. No new process, control, sampler or audit has run under
this revision. The previous startup protocol remains normative in full except
for the changes stated here. Preserve the original attempt and its negative
audit unchanged. This is one new private attempt, not a retry inside attempt 1.

## Exact inherited sources and observed failure

All paths in this document are relative to experiments/m192e-campaign-runner.
The original committed runner is startup-attribution-run.py, 24534 bytes,
SHA256 48698b704042766c24aaeb5fe674d493e628cc58397ec0823e4c10a4a30afe44.
The inherited full protocol is startup-attribution-preregister.md, 12750 bytes,
SHA256 fbd2d8425ccace3229a65d4159f203ecaa3d1ecd9d94c630ce3bd25db14fa492.
The original saved-metadata checker is startup-attribution-audit.py, 37387 bytes,
SHA256 ff31a1edf0a632d487329f06923cde85be2dc1f8d1dfa36903216be2f140674e.

OBSERVED in the retained child receipt: peak_job_memory_used_bytes=561917952
against a committed-memory limit of 536870912; the error is
ValueError('child committed-memory bound'). The owned tree was terminated,
cleanup_errors is empty and terminal active_processes is zero. This is a
committed-memory refusal, not a measurement of RSS or a startup timing defect.
No arm record exists; the saved checker retains all five arms unvisited.
Its status is VERIFIED_PRIVATE_STARTUP_NOT_COMMISSIONED, with
verified_record_complete=true, subject_complete=false and commission_pass=false.
A complete negative saved-record audit is not successful startup commissioning.
No planted-delay, observer or timing result follows from this attempt.

| Retained attempt-1 evidence | Bytes | SHA256 |
| --- | ---: | --- |
| startup-attribution-plan-1.json | 6151 | fbf293dffc9c6da8e73852fc4d2e0563e0d0965a9f3be25ea3e76287fb92a5f4 |
| startup-attribution-1/parent/result.json | 32768 | 60739d48a4288a4eeee0c84f84d3f6e56f4ab5408f288daecbfa76c32fe60c24 |
| startup-attribution-1/worker/result.json | 32768 | 30b039fc3c4e5c140e6618160d8751551def4f1ea54efddbab4e51de57186ded |
| startup-attribution-1/child.json | 1737 | 7c0fa886e5d4cae9e94774b63205fb0b7c221e1fd7ff623bc30ab7d62547f7a1 |
| startup-attribution-1-launch-outer.json | 725 | 9cb4f98ef32cd7c2046ca484695f06bb8e51510d2c06241dbe464e2df76769d2 |
| startup-attribution-1-launch-stdout.bin | 505 | 7d14fc4ef49d9cd1b131b5f3b37f75ae5e3bd3936e12c111a23302fb00baf2cf |
| startup-attribution-1-launch-exit.txt | 2 | 4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865 |
| startup-attribution-1-audit-stdout.bin | 8575 | c1b06f21c545bfd895b3e6494ce6decb21acb15e6556933bdf355c5a58cfa7df |
| startup-attribution-1-audit-outer.json | 1730 | e94cfd446112ddd249f6b549ef69ba54c49f9ef724817193de07841f05fd02da |
| startup-attribution-1-audit-exit.txt | 2 | 4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865 |
| startup-attribution-1-audit-progress.json | 2766 | b4e9150fe814851a925df0861b009f63834a2b18a2f881b9d336621559210393 |

The failed attempt's full allocations remain consumed:20 CPU seconds/30 wall
seconds/4 MiB source and subject evidence, plus10 CPU seconds/20 wall seconds/
1 MiB audit family. Small observed samples do not refund these allocations.
The actual saved Job CPU is0.171875 seconds; the old checker separately reports
sampled parent plus Job plus its0.25-second publication reserve as0.59375 CPU
seconds. These samples do not imply measured terminal parent CPU completeness.

## Only executable amendment

The new subject is startup-attribution-run-2.py, 24537 bytes,
SHA256 a6bd95a2f6194e9bc3f0c74c06a7377bdbe5b4c9cebafe8e91adb8b4c5eaac82. It is copied from the exact committed original. It changes
only SPEC to startup-attribution-preregister-2.md and the containing worker
Job's committed_bytes from512*(1<<20) to1024*(1<<20), exactly1073741824 bytes.
The inherited process helper still reads back the actual installed limit and
compares actual peak committed usage to it; a peak above1 GiB must refuse and
retain cleanup. This ceiling is an explicit resource choice, not a claim that
1 GiB is necessary, sufficient on every machine, or a measured optimum.

The new checker is startup-attribution-audit-2.py. Its SELF derives from its
actual __file__; the CLI --source-sha256 and the exact new plan source binding
must both identify those bytes. Its only edits are required runner/protocol
filenames and their exact pins, and the three fixed512*MIB Job-limit/readback/
peak predicates to1024*MIB. It retains every original metadata, native-call
wrapper, literal-output, interval, child-timestamp, refusal, publication and
accounting predicate. No scientific or timing threshold changes.

DERIVED source-only proof: the two subject string substitutions have exactly
one occurrence each. Reversing them restores the entire original UTF-8 source
byte for byte; both reversed ASTs are identical with location attributes
excluded. The checker makes one SOURCE_PIN replacement, one SPEC_PIN replacement,
one required runner-name replacement, one required protocol-name replacement,
and exactly three512*MIB replacements. Reversing those edits likewise restores
the entire original checker bytes and AST. These proofs parse source; they do
not import, execute or independently verify the subject. Independent reviewers
must inspect the exact new bytes before release.

## Fresh release and unchanged scope

Use fresh output startup-attribution-2 and plan startup-attribution-plan-2.json.
The plan retains the original seven-key m192e-startup-attribution-plan-v1 schema,
the same six actual failed-rehearsal baseline refs and the same Python identity.
Bind the original source/protocol/checker, this amendment, the new subject and
checker, both independent new source reviews, and the positive attempt-1
metadata records above in source_bindings within its64-record/1 MiB aggregate.
Do not put empty stdout/stderr evidence in the positive source namespace.
The source-bound amendment retains their historical context; no new baseline
schema or source loading is introduced. Parent and worker commands must point
to the new subject and fresh plan; worker appends only --worker. Existing exact
sys.orig_argv, current-directory, -B, plan and source-hash checks remain active.

The five fixed arms remain off, on, placebo, before-popen-delay and
after-resume-delay. The only child task is the held null child. Keep original
sampling origin,10 ms cadence,100 ms maximum-gap and90 percent coverage bars;
keep both150 ms delays,140 ms lower witness bar and independent child-time
position checks. Keep whole nonempty output/log hash identity and the known
wrong-byte/restoration check. No RAW, TIFF, product, model, camera or133-case
campaign work is admitted. All operational or untreated control failures and
unvisited arms remain visible; only complete five-arm correct dispositions
may commission these private seams.

Allocate an additional, nonrefundable20 CPU seconds/30 wall seconds and4 MiB
for this source/subject phase (source1 MiB, output3 MiB), and10 CPU seconds/
20 wall seconds/1 MiB for its independent saved-metadata audit. The old attempt
remains charged separately. No CPU, wall, file-count, cleanup, log, phase or
audit-publication allowance changes. Keep parent sampled CPU plus the whole
owned Job once, without adding nested null-child Job CPU again; retain the
0.25 CPU/0.5 wall publication reserve and require actual outer-exit/tail checks.
The old auditor's source-derived metadata envelope remains applicable:5 large
arm summaries,51 file rows,64 sources and512-character absolute paths yielded
17800 bytes of progress,26034 including the full8 KiB error reserve, and72086
bytes for a conservative final result. New path suffixes remain inside that
path allowance. Fixed progress32 KiB/final128 KiB/family296 KiB caps are unchanged.
