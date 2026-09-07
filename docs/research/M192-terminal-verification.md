# M192 recovery: independent terminal verification

**VERIFIED, 2026-09-07:** `recovery-20260906-163253` is a complete, internally
consistent 133-invocation campaign. The unchanged official verifier accepts
its artifact integrity. Independent checks agree with its **one PASS, zero
FAIL, three UNMEASURED** partition and overall **UNMEASURED** verdict. This
does not promote M12 or supersede the historical failing lineage.

This is a takeover review, not a new milestone or a SYNTHESIS fold. The reviewer
did not author the campaign or runner repair, change the protocol, open RAW or
sealed captures, render new product outputs, or interrupt another process.

## Four bars and their supported meaning

| Frozen bar | Independently checked observation | Disposition |
|---|---|---|
| Full TIFF and canonical pixel byte identity | Each of 15 N/worker cells contains six scored runs with one file hash and one pixel hash; all 30 runs at each N agree across workers | **PASS** |
| Warm process-tree peak <=6 GiB | Job peak 3,077,963,776 bytes, or 2.866577 GiB; sampled private-commit peak 3,077,955,584 bytes | **UNMEASURED_SAMPLING_COVERAGE** |
| Peak N299 / peak N33 <=1.10 | Maximum matched-worker ratio is 1.000789758 from Job peaks and 1.000796424 from sampled peaks | **UNMEASURED_SAMPLING_COVERAGE** |
| N-mod-4 per-frame spread <=2% | Raw-minimum spread 0.355694%; reversal-pair upper spreads 5.687910%, 0.499110%, and 0.797242% | **UNMEASURED_HOST_CONTENTION** |

**MEASURED readings, with failed admission kept separate:** all 90 native scored
runs exceed 99% sampling coverage, but `native-n299-w8-r3` has a 1163.699700-ms
maximum gap and `native-n299-w8-r6` has a 399.434000-ms gap. Both exceed the
independent 100-ms requirement. Their coverage ratios are 0.990392427 and
0.997140077. Good aggregate coverage cannot satisfy the maximum-gap condition.
The favourable kernel peaks do not authorize waiving the frozen sampling rule.

The timing envelope crosses 2%: its upper bound cannot pass, and its lower
bound cannot establish the registered failure. `HOST_CONTENTION` names this
protocol disposition; it does not identify a physical cause. Removing the first
pair or replacing individual repetitions would change the experiment after
seeing its result. The [measurement diagnosis](../../experiments/review-m192-measurement/findings.md)
properly leaves the observed execution-state transition unexplained.

The identity result concerns the **pinned native-RAW production merge** at
N=33/105/299 and workers=1/2/4/8/16 on the recorded host and binary. It uses
pyramid gate 2.0, Catmull-Rom gathering, `--cover scale`, linear sRGB, MHC
demosaicing, and the seven preregistered alignment sidecars. Recorded outputs
are 7032x4688 RGB16 TIFFs, 197,798,956 bytes each. Logs consistently report four
canonical chunks, one reusable frame worker, and one retained plus one scratch
accumulator. Worker count controls the spatial execution pool in that path.

This establishes repeat and worker invariance for this tested matrix. It does
not establish invariance for arbitrary data/hardware, test the live alignment
solver, score the comparative common-TIFF M11 route, or measure image quality.
N33 and N299 use bee-1-cpl; N105 uses coffee-bean. The modulo arm uses
bee-1-cpl N96/97/98/99 at W16. These are two subjects, not three independent
subjects or a new population sample.

## Independent provenance and completeness checks

The independent script constructs the schedule literally instead of using
`verify.py::expected_runs`: 15 native warmups, 90 native scored runs, four
modulo warmups, and 24 modulo scored runs, with every prescribed reversal.
It checks every sequence index and canonical record hash from the all-zero
initial link to terminal link
`7848A3DED245B0D5250F2443D6C3AA741DE8B644115B6E924DE0B3F06D6ED69E`.
Run IDs are unique; records, start receipt, certificate, and completion agree
on campaign ID `4c72e520-b93e-4781-999f-0947486ddc44`. The launch and start
receipts identify PID 22556; recorded product parents agree. Completion is
explicit at `2026-09-07T07:30:52.981852+00:00`, with no interruption/resume.

The re-chosen checks also cover:

- Every recorded command, executable path/hash, worker environment, sidecar
  path, successful return, and actual stderr witness; local retained binaries
  still match their recorded hashes. Both build logs visibly compile
  `strehl-cli`. The official verifier separately checks committed ancestry and
  equality of the repair-owned source paths after the bounded-memory repair.
- All 266 product log children and 11 commissioning log children, including
  exact path sets, byte lengths and SHA-256; all seven sidecars against the
  frozen protocol and local retained copies, with exact placed indices
  0 through N-1; the exact 12-member terminal artifact-hash mapping.
- All 404 unique before/after input entries: 299 bee-1-cpl and 105 coffee-bean,
  totaling 15,489,310,720 bytes. Names, sizes, mtimes, and hashes match, and the
  manifests bracket the runs. This verifies the **recorded before/after
  evidence**; it is not a fresh corpus hash sweep.
- Commissioning evidence beyond boolean labels: unrepaired W1/W2 file and
  pixel hashes differ; unrepaired N33/W4 Job peak is 9,587,433,472 bytes;
  allocation/null peaks are 7,544,754,176 / 80,883,712 bytes with child
  membership observed; the one-LSB plant changes both hash channels.
- Independent grouping for identity, exact rational arithmetic for peak
  ratios, independently expressed arithmetic/geometric timing reductions,
  and inspection of all seven actual CPU traces and their run bindings.

All **300 original result files** have identical before/after inventory hashes
around the independent review. The TIFFs were deliberately removed after the
campaign parsed and hashed them; this review checks those archived receipts
and logs, not pixels that are no longer retained.

The campaign's `* -text` Git attribute preserves the hash-bound protocol and
generated evidence without line-ending conversion. This is byte preservation,
not a claim of a standalone reproducible product run: the official verifier
also needs the repository's pinned protocol and Git lineage, and the additional
local checks in this review use retained `work/` launch/build/sidecar evidence.

## Generic verifier hardening, separate from this result

**MEASURED negative controls:** after re-sealing the record chain, the current
`validate_record_structure` accepts a scored command with pyramid gate `999`,
accepts a scored worker environment of `999`, and accepts all campaign IDs
being absent. The first two fields are not compared with the protocol; the
last is converted to the nonempty string `"None"`. These are in-memory calls
to the **record validator**, not claimed successful forgeries of the whole
artifact verifier. The inert original rows pass as expected.

The independent checks above bind all three fields correctly in the actual
package. **No corresponding inconsistency was observed here.** The omissions
therefore warrant strengthening prospective verification, not changing this
certificate's recorded dispositions.

Source inspection also shows `verify_artifact` checks the declared input count
without counting the list, trusts commissioning gate booleans, and iterates
the terminal hash mapping without requiring its exact key set. It hashes the
commissioning-log manifest but does not follow all of its child bindings.
Those contents were checked separately here. Future verification should reject
re-sealed configuration drift, compare nonempty campaign identifiers across
the package, enforce complete manifest membership, derive commissioning gates
from retained evidence, and validate raw CPU trace completeness rather than
only its summary flags. Keep these new checks prospective and add a negative
control for each; do not alter acceptance thresholds or frozen originals.

The current plan's step 1, campaign notice, STATUS notice, and recovery-report
terminal appendix accurately distinguish artifact acceptance from M12
acceptance and limit the production scope. Commissioning timestamped gaps,
query latency, allocation/null/stall controls, short-child detection, and
observer on/off output hashes is a bounded next systems action. A further
full campaign is not justified before that measurement work. Pausing the
follow-up remains an orchestrator action, not something this review verifies.

## Reproduce

The verifier was inspected before execution: artifact verification only reads
the package; this invocation directs its output into the new review directory,
leaving the campaign's own verification receipt intact.

Commands run from the repository root, using Python 3.12:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/M192-m12-certify/verify.py --artifact experiments/M192-m12-certify/recovery-20260906-163253/results --output experiments/review-m192-completed/official-verifier.json
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/review-m192-completed/audit.py
```

Both exit **0**. Outputs are
[`official-verifier.json`](../../experiments/review-m192-completed/official-verifier.json)
and [`independent-audit.json`](../../experiments/review-m192-completed/independent-audit.json).
The latter includes the complete preservation inventory and source hashes.
The first reviewer draft incorrectly compared an unweighted CPU trace mean
with the endpoint-counter mean; inspection of `HostCpuSampler.finish` corrected
the review to compare the separately recorded trace mean. That was a reviewer
check error, not a campaign defect. Endpoint system counters are not retained
in `sweeps.json`, so the boundary mean cannot be re-derived from that file.

| Binding | SHA-256 |
|---|---|
| Measured executable (`e93f0bde695961d53cbd66587a060a41552b4a63`) | `89482ACD60C4E39A22F763B2E722754804430E955546EA96F7AE7CA4C7EA1032` |
| Frozen protocol bytes | `E10723DDEF7D60D7A4C202E726ED998BB4CC7FF95FB3B6ABAA203D98219D9898` |
| Records file | `790D87CA85DAAE79709769A7D6D1B249542B6B235647C5C5A5019B206D3B5568` |
| Certificate | `7608BF76CB834E6286934FC02260E679E519C43D43A9D7A6015B5C6AC8576814` |
| Unchanged official verifier | `8F4D307A2AD1F9055836DA16712C560BB67A690DA8F836F054E77866CE4E669C` |

No original experiment, scorecard, or SYNTHESIS file was modified by this
review. The review author did not commit these artifacts.
