# M192b — bind systems evidence to its recorded execution

**VERIFIED within recorded-artifact consistency scope.** The prospective
verifier accepts the completed M192 package with its unchanged **one PASS,
zero FAIL, three UNMEASURED** product-bar result. Author commissioning rejects
24 altered packages; separate review rejects 12 independently chosen altered
packages. Both suites include valid controls. All 300 original artifact files
remain byte-identical.

This implements the missing automated bindings identified by
[M192 terminal verification](M192-terminal-verification.md). The preregistration
is [here](../../experiments/m192b-verifier/preregistration.md). The consumer is
the interpretation of the saved campaign evidence, not its image-quality,
memory or speed verdict. A bad package is a verification failure; a correctly
recorded product failure is valid evidence.

## Implementation and trust boundary

[`verify.py`](../../experiments/m192b-verifier/verify.py) adds a separate entry
point. It checks the frozen verifier's source against commit `4e6b4572` and
uses that unchanged verifier for the registered bar reductions. Its checks
bind the complete invocation, binary metadata, pinned declared environment
domain, cleared values and active paths, campaign identity, terminal witness
membership, log bytes and terminal archive membership. The same invocation
validator serves scored and commissioning runs.

Input records must retain their 404 distinct files, directory populations,
byte totals and matching before/after entries. Sidecars must match the frozen
protocol, complete placed indices and registered membership. Commissioning
labels must follow their recorded observations and archived logs. CPU sweeps
must retain actual interval samples, order and run bindings, valid exact types,
and consistent derivable summaries. Recomputed sampling summaries must agree
with the certificate. Candidate paths must stay inside the artifact package.

The trust anchor is the frozen repository lineage. The tool reads artifacts;
it never executes their recorded command or opens their referenced RAW files.
This is consistency checking, not authentication against someone fabricating
every observation and supporting log coherently. The deleted output TIFFs
cannot be rehashed: their pixel/file hashes remain saved campaign receipts.
The tool requires this repository history to resolve its pinned source.

M192 did not retain raw sweep boundary CPU counters. The exact enclosing CPU
mean therefore cannot be reconstructed from the arithmetic mean of interval
percentages. The new check rejects an impossible all-idle boundary span
containing busy intervals, and the converse. It does not pretend that this
endpoint contradiction test validates every possible boundary mean. M192c's
prospective sampler retains the raw host boundary counters.

## Executed controls

Commands run from the repository root, all exit zero on the final source:

```powershell
python -B experiments/m192b-verifier/verify.py --artifact experiments/M192-m12-certify/recovery-20260906-163253/results --output experiments/m192b-verifier/baseline-verification.json
python -B experiments/m192b-verifier/commission.py
python -B experiments/m192b-verifier/independent-verify.py
```

The last command was run by the separate `roadmap_audit` reviewer. See the
[independent report](../../experiments/m192b-verifier/independent-review.md)
for its choices, retained earlier failures and final source hash.

**MEASURED author controls:** 24 negative full-package controls reach the
public `verify_artifact` function. Mutations cover command/worker/environment,
campaign IDs, manifest members and input totals, binary/sidecar/cache binding,
commission logs and unsupported labels, CPU trace deletion/duplication and
summaries, sampling-summary inconsistency and escaping paths. Each mutation
recomputes the record hash chain, certificate links and terminal hashes.
The unchanged package and an inert additional record label are accepted.
A package with coherently recomputed bars for a planted 7 GiB product reading
is accepted as valid evidence with overall **FAIL**. Thus the instrument can
both reject contradictions and retain an adverse product result.

**VERIFIED independent controls:** the reviewer initially found six accepted
contradictions, and after the first repair found four more. These are retained
in `independent-first-pass.json`, `independent-first-recheck.json` and
`independent-second-pass.json`; they are not silently replaced by the final
passing record. The complete shared invocation validation, exact CPU types,
commission log binding and impossible-boundary check fix those paths.
The final suite rejects all 12 chosen cases while keeping baseline and inert
controls admissible. No corresponding inconsistency was found in the original
campaign.

These are deterministic fixture dispositions, not statistical effect estimates.
Their failure directions are explicit: a checksum-only reader can accept a
coherently rehashed contradiction; an over-restrictive reader can reject a
valid product failure or inert metadata. Both directions are exercised.

An initial author commissioning invocation failed before any control ran:
Windows sandbox access to a `tempfile.mkdtemp` directory was denied. The harness
now uses a uniquely named ordinary workspace directory, verifies its resolved
containment, and cleans only that directory. No product/evidence conclusion was
drawn from the failed setup.

## Disposition

Accept this prospective verifier as the consistency layer for the retained
M192 artifact format. It does not launch a campaign, relax a bar, certify a new
observer, or turn recorded memory/timing readings into admitted passes.
New campaign instrumentation must be frozen and commissioned separately.

Applicable-rule execution: realizable contradictions and inert/adverse controls
(11/20/35/36); distinct verifier and re-chosen settings (12/24); complete
commands and artifact/source hashes (8/47); original package hash comparison
before/after; exact source lineage and retained failed reviews (31); allocated
continuation and named prior evidence (40/41); no capture access, process
intervention, image metric, Rust rebuild, scorecard change or SYNTHESIS fold.
