# M192 continuation — recover the certification runner

## Before the repair

The registered certificate is still incomplete. The interrupted M192 directory
contains 35 durable records, ending at `native-n33-w1-r6`, sequence index 34.
Its abort record reports `[Errno 22] Invalid argument` at
`2026-09-05T08:38:16.306950+00:00`, without a traceback. The preceding product
record completed at `08:38:15.982404+00:00`. No N105 product log was created.

**INFERRED historical cause, not established:** `execute()` appends the durable
record and then calls `progress()`, which writes to stdout with `flush=True`.
An unavailable Windows stdout can raise this error there. The missing traceback
prevents identifying the historical failing statement. A successful product
must not be invalidated solely because its terminal disappeared; an evidence
file failure must remain fatal.

The bounded repair does not change `protocol.json`, scored thresholds, product
flags, the inherited monitor, or frozen executable lineage. The existing aborted
directory is preserved. A new run still starts from zero and must supply all
133 registered invocations; the 35 old records cannot enter its certificate.

## Falsifiers registered before implementation

The focused tests must fail if any of these defects is present:

1. Progress on an invalid stdout (`OSError` errno 22), broken pipe, bad file
   descriptor, or closed terminal aborts a successfully journaled operation.
2. Healthy stdout changes the journal bytes relative to unavailable stdout;
   progress ceases to be an observer in that case.
3. Failure to append or synchronize the durable diagnostic file is swallowed,
   or an unexpected exception from the terminal is swallowed.
4. A fatal error loses its traceback/type/errno, is reported as success, or is
   followed by a secondary terminal error that hides the original diagnosis.
5. Selecting a fresh campaign directory changes the old interrupted directory,
   permits a campaign path outside M192, or enables resume of a nonempty run.

The tests use synthetic records and temporary files, never RAW captures. A
passing terminal-failure test proves this code defect is reproducible; it does
not retrospectively prove that it caused the old abort.

## Runtime planning evidence

Read-only calculation from `work/records.jsonl`: the 35 N33 invocations total
`2791.172087000101` seconds. Mean seconds per invocation at W1/2/4/8/16 are
`159.29766747140926`, `96.12066241431914`, `61.95930842857342`,
`45.052048885729164`, and `36.30918237141201`.

**DERIVED scheduling estimate, not a performance claim:** linear scaling of
these means by frame count predicts `36961.884909668006` seconds for the full
native matrix and `3003.759632544084` seconds for the modulo arm:
`11.101567928392248` hours, excluding setup and commissioning. Host contention,
the different N105 scene, and fixed overhead can move this estimate. M179's
partial history independently contains a `1484.5106025000568`-second N299/W1
warm-up, so an uninterrupted two-hour reservation is not a credible plan for
this implementation. M179's interrupted rows are scheduling observations only.

## Validation

**MEASURED fault injection:** the committed `744a5c10` implementation of
`progress()` raises errno 22 on the injected unavailable terminal. This is a
negative control on the old code path, separate from the historical-cause
inference above. The repaired path retains byte-identical scored journals
under healthy, invalid, broken, closed, and absent stdout conditions.

The implementation appends and synchronizes `work/progress.jsonl` before
displaying status; expected unavailable-terminal failures are recorded there.
Unexpected terminal exceptions and diagnostic disk errors remain fatal.
Abort records retain exception type, representation, errno, Windows error, and
traceback. A no-resume refusal no longer overwrites an earlier abort record.
`--campaign-dir` permits a fresh directory strictly inside the M192 experiment
without relocating the old one. It does not enable resume.

Commands run from the repository root:

```powershell
python -B experiments/M192-m12-certify/test-recovery.py
python -B experiments/M192-m12-certify/verify.py --self-test
git diff --check -- experiments/M192-m12-certify/campaign.py
```

The verifier self-test remains `COMMISSIONED`: all nine planted defects are
caught and its inert label survives. The initial recovery-test invocation hit
Windows access-denied errors in Python's private temporary directories; that
run supplies no product evidence. Test fixtures now inherit workspace directory
permissions and delete only their checked, unique test directory.

**Independent review found a second failure after the first seven tests passed.**
The root verifier closed the actual stdout descriptor and called the repaired
display helper. Although it caught the write error, Python later flushed the
still-broken `TextIOWrapper` at interpreter shutdown and exited **120**. The
fake-stream tests had no power to find this. Adding the legacy-code negative
control made eight tests; it did not cover interpreter shutdown either.

The correction redirects the failed stdout/stderr descriptor to `os.devnull`.
It preserves that descriptor for the original wrapper, including references in
`sys.__stdout__` and `sys.__stderr__`. If opening the null device reuses the
just-closed descriptor, the wrapper retains ownership instead of closing it
again. Errors establishing this fallback still propagate.

The final suite has **nine passing tests**, including real subprocess arms that
close stdout and stderr separately. Both subprocesses exit **0**, retain the
diagnostic event, and produce exactly the same scored journal bytes as their
healthy-stream controls. Healthy streams still display the message. The disk
failure and unexpected-exception tests remain red controls with exact expected
exceptions. This additional failure and correction do not establish the cause
of the historical abort.

**Independent verification completed by the root orchestrator:** all nine tests
passed. Its separately chosen real-descriptor stdout and stderr shutdown
controls now exit **0** with empty stderr; the prior implementation exited
**120**. The unchanged verifier still catches **9/9** planted defects and
preserves its inert label. Root also checked that `protocol.json` and the two
production memory/reduction source files have no diff. This is acceptance of
the bounded runner repair, not a product certificate.

The root owns the fresh full campaign launch. No certificate or scorecard
promotion is claimed by this continuation.
