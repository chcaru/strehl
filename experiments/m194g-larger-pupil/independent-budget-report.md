# Independent affected-budget verification

2026-09-07. **VERIFIED: 53/53 affected controls pass** on the prospectively
committed amendment implementation. This is the injected-clock and actual
input-entry commission, not a measured intended population or geometry/CFA
rerun. The original 60-second cost refusal and stopped profile diagnostic
remain unchanged.

The root committed the amendment and concrete independent design at
`01d4e52b`, then committed implementation/driver/command release
`5eb0968da80b56315ebe9fc9d1edfb883d86161e` before executing the command below.
The root reported collecting exit 0. This reviewer subsequently read all 53
result rows, the saved source diff, actual partial clock records and exact
source snapshots; no duplicate control invocation was needed.

## What was checked

The full old/new source comparison permits exactly the five named textual
replacements implementing the narrow allowlist: new fixture pin, amendment
pin, the two default elapsed values, amendment source-ledger inclusion, and
the amendment entry check. Eleven function/class bodies remain textually and
structurally unchanged, including Budget, actual point cuts, stream encoding,
count/coverage, model construction and completion validation. The candidate
fixture differs from the historical one only at its two elapsed fields.
Selector, loader and original preregistration bytes are unchanged.

The actual Budget constructor, subsequent check, and actual 2×1 full-mask
traversal accept CPU 179.999/180 and wall 239.999/240, and refuse 180.001 and
240.001 respectively. Old-policy destroyers using 60/120 refuse independently
valid new-budget companions at CPU 90 and wall 180. Thus the new-limit tests
would not pass through an implementation accidentally retaining the old
allowance.

Separate injected clocks accumulate across cells, frames and arms. The actual
counter refuses CPU `[90.0005,180.001]` and wall `[120.0005,240.001]` after
2, 4 and 8 observed cells respectively. The complete stationary-clock
companion has eight distinct analytic-only cell visits across two frames and
two arms, with no numerical rule/cut or radiance helper call. These are
controlled clock inputs, not measured execution times or intended coverage.

Unchanged strict point/node checks accept 7,999,999 and 1,199,999,999 charges,
and refuse their respective 8,000,000 and 1,200,000,000 boundaries. These
are Budget charges, not millions of allocated points or evaluated angular
integrals. A 1,024-byte owner and overlapping views remain one allocation
under the real storage cap; a deliberately smaller private 1,023-byte cap
refuses it. The historical wider ownership evidence is not relabeled as a
newly executed population.

Actual copied `run()` entry paths admit an unchanged source/input closure
only as far as an explicit private count exception sentinel. No intended
cells execute and no successful synthetic completion is emitted. Missing or
changed amendment bytes, the old fixture, a changed new fixture, and a supplied
rehash of the changed fixture all refuse before the count sentinel. The exact
amendment appears in both source ledgers; changed bytes after startup are
recorded as a before/after difference while the sentinel remains the primary
refusal. That case tests recording of a change, not a separate isolated
post-count success-path gate. An additional final source-capture error is
retained separately without replacing the original count sentinel. Both valid
entry companions reach the expected sentinel.

## Exact evidence

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194g-larger-pupil/work/cache-independent-budget-1 experiments/m194g-larger-pupil/independent-budget-controls.py --output experiments/m194g-larger-pupil/independent-budget-1
```

The actual original interpreter arguments match the registered suffix in
`budget-controls-release-1.json`; the root saved `independent-budget-1.log`.
The result records Python 3.12.10, NumPy 2.4.4, the fresh cache path and four
numeric-library thread settings of 2. Every one of ten before/after source
hashes is unchanged and matches both current bytes and its saved source
snapshot. There was no actual failed invocation or source correction in this
affected control run. Its intentionally refused cases remain individually
saved.

| Artifact | SHA256 |
| --- | --- |
| `independent-budget-1/result.json` | `e1d308f95eea671a665529aebc891595e14c2be0cbe8aca8a82d36870c449e95` |
| Independent driver | `14fe92cca70b25ec98719ed5c8d0ae1f9c5f38f3642c6eb894b1222923e57b99` |
| Candidate preflight | `c162c2651b1fd3e8345f08c0c9cd5edf5e100d94d7958c5dedde1d791a18763c` |
| Candidate fixture | `e84f0bbbda9bef039da86616c9f051d416929f4dbe78477cc5b3fc21206856bb` |
| Amendment | `205ba1ac42e8325eb7d1ede41e05399776eddf7d80a99ecb3ba12b1931f73a99` |

This commission supports the changed elapsed/input boundaries and reuse of
unchanged source-path evidence. It does not promise that the full count fits
180 CPU/240 wall seconds. An independent read of the next real terminal
population remains required. Even a complete cost pass would not by itself
commission expected-electron arrays, physical optics, noise, CFA, production
quality or SOTA status.
