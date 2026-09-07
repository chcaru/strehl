# M194g independent preflight component verification

2026-09-07. **VERIFIED, bounded component scope:** the final independent run
passes 94/94 checks against preflight source
`829669612359e5f60a1610fbc36604eb4cef5647911df604124de9e13160b485`.
This lane did not execute the intended 320×240 population or any radiance
calculation. It supplies no float-model, CFA, production-quality or SOTA
admission. The root must separately inspect the actual intended cost result.

The literal private choices were recorded in
`independent-preflight-controls-design.md` before reading or executing the
author implementation, and committed at `5d23e652`. The protocol/fixture
release was `a59a1c47`. The independent source is
`independent-preflight-controls.py`, SHA
`7d5872de9083359eaaadf5c6a2240ae14c76ca4c432b4b8b18d1db9cf47b1e9c`.

## Actual population and independent choices

The private population is 9×6 cells, five frames and three arms. It uses a
nonidentity dyadic similarity, a different mask normal/offset, and inverse
foci giving negative, zero and positive foreground defocus. The independently
constructed Cartesian set and exact dyadic branch predicate match all 810
distinct actual `(arm, index, x, y)` records. Foreground/background/numerical
branch totals are 282/306/222, so none of the three branch checks is inert.

`private_nominal_reference` independently loops over that grid, reuses the
frozen geometric rule primitives, and constructs the point cuts from the
inverse-then-dot arithmetic. Its 15 frame rows agree with the actual counter's
root, low/high point, interval and angular-node counts. The actual wrapper
calls consume 167,040 point records in 2,088 low/high batches with orders
4, 8 and 16; the corresponding nominal angular-node total is 39,819,840.
These are counted work units, not evaluated angular integrals or a timing
estimate. The principal run uses stationary injected clocks deliberately.

Actual traps on `Field.evaluate`, `evaluate_rays`, `render_points`,
`angular_integrand` and `render_cell` remain untouched while the live rule
and cut counters are nonzero. This confirms the tested counter traversal
does not invoke those radiance paths. It is not a new physical-optics test.
Zeno owns the complementary independent tangency, rounded-height cancellation
and signed-cut mathematical controls; this report does not claim those as
its own independent observations.

The source and boundary checks inspect the loaded model/render function
identity despite a preexisting foreign bare `model` module, restoration of
that module, unchanged copied-source companions, and changed/missing source
refusals. Fixture mutations include unknown/missing keys, wrong schema,
bool/float dimensions, duplicate frame/arm and changed geometry. The intended
fixture is admitted only by its fixed full-file hash: those fixture refusals
demonstrate input identity protection, not a general semantic JSON parser.

Coverage faults remove or duplicate cells, substitute invalid coordinates,
omit frame/arm completion or change work totals. Valid reversed enumeration
preserves the population and geometric counts while changing the ordered
digest and the actual final coordinate. A root omission, a relative mass
change of 1e−6, omitted low-rule point and omitted cut record all refuse on
the actual counter path, without renormalization.

Point/node limits accept 16 with a strict ceiling of 17 and refuse equality.
Separate CPU and wall clocks cross the whole-run ceiling across analytic-only
cells, frame transitions and arm transitions. They refuse rather than reset.
Two overlapping views correctly count one 1,024-byte owner; retaining another
owner crosses that storage limit, and a released owner ceases to count.
Actual small traversals also refuse point, node and array limits. This is
tracked reachable ndarray backing storage. It excludes RSS, Python objects
and frozen-helper temporary allocations. An insufficient rational bit budget
falls back to numerical handling without changing the scene coefficients.

## Actual failures and corrections

All three run directories, source snapshots and raw logs are retained.

| Run | Outcome | Disposition |
| --- | --- | --- |
| `independent-preflight-1` | 49 checks completed, then exit 1 | Independent driver mistake: an inner `numpy.float64` point height shadowed the integer grid height. The grid-height variable use was corrected; no author code changed for this failure. |
| `independent-preflight-2` | 86/91 checks pass, exit 1 | Four real completion-boundary false accepts and one independent test expectation error, detailed below. |
| `independent-preflight-3` | 94/94 pass, exit 0 | Repaired author boundary; corrected traversal metadata comparison; three additive count/index/work falsifiers. Source hashes unchanged during the invocation. |

On source `ac130bfe0dca3c9d4162c0d5b776c54f7dcd91fdd1832357e5a821f5f53223bc`,
actual `run()` accepted float width `320.0`, float completed-cell count
`1152000.0`, boolean row frame index `True` in place of 1, and float row
visited count `76800.0`. Python equality alone let these values satisfy the
declared integer completion contract. The fixtures used an explicitly named
private completion stub, not a real large traversal or genuine authority.
Unchanged valid companions passed before and after the faults.

Curie repaired `validate_completion` with strict real-integer/nonnegative
checks. The original four faults now refuse, as do the added top-level
boolean frame index, float low-point count and cancelling negative-low/
positive-high work pair. These additions challenge the repaired boundary;
they do not enlarge the intended population or alter any scientific bar.

The fifth run-2 failure belonged to the independent test: it compared whole
frame-row dictionaries after reversing enumeration, including
`last_coordinate`. The normal traversal ends at `[1,0]` and the reverse at
`[0,0]`. The corrected comparison explicitly excludes only that order-dependent
field, requires a different ordered digest, and still compares every other
frame field. The original failed assertion remains in run-2 evidence.

Actual private `run()` failure paths also preserve the original counter error
when final source capture itself fails, recording the capture error
separately. A final capture failure alone refuses. Startup failures before
`run()` remain a separate outer-launch-log responsibility.

## Reproduction and evidence

Run from the repository root with a fresh output directory. The deciding
invocation was:

```powershell
$env:OMP_NUM_THREADS='2'
$env:OPENBLAS_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
$env:NUMEXPR_NUM_THREADS='2'
python -B -X faulthandler -X pycache_prefix=experiments/m194g-larger-pupil/work/independent-preflight-cache-3 experiments/m194g-larger-pupil/independent-preflight-controls.py --output experiments/m194g-larger-pupil/independent-preflight-3 *> experiments/m194g-larger-pupil/independent-preflight-3.log
```

The earlier commands had suffixes `1` and `2` in both output and cache paths.
Each result records `sys.orig_argv`, interpreter/library versions, environment,
source snapshots and before/after hashes. The fresh cache choice and exact
source-byte loader establish which source was exercised; this is not a Cargo
rebuild claim. The control driver retained its actual CPU/wall accounting,
but no performance comparison uses it.

| Artifact | SHA256 |
| --- | --- |
| Run 1 result | `86dedfca30ff12682ba7d58035c5386d3e2357453f2afa9dafa95ddb743473b3` |
| Run 2 result | `976c39a766d3ec104f1725318f9a73fcb0eaaef135ab5f15601fd1f7b948ce62` |
| Run 3 result | `4b7320ed7382b61a8c581d93bd565283a749394530540ca23c7503db5372594d` |
| Frozen loader | `222fab4a932fe236c120d8a48e4521747474e2ef57ba58781bf5c59f644f4f76` |
| Selector | `24b812071b8b6189423b9792a22c55abd9a4f4a78921a9d558ab24489f1923b3` |
| Final counter | `829669612359e5f60a1610fbc36604eb4cef5647911df604124de9e13160b485` |
| Intended fixture | `fc36b5f252c5efeda1cba753312dd061ebf5583856ec45466f61b0f66dc31ef2` |
| Preregistration | `d0c570ec892a2c3e40b90c0f7eef2a9ff0649dd53bc34adee6b6bc65280f14c8` |

The actual deciding arrays of metadata are retained as `private-reference.json`,
`private-actual.json` and `private-observed-cells.json` within run 3. There are
94 check rows, not 94 independent scenes or large-population replications.
Private controller completion stubs have `fixture_only` scope. The intended
1,152,000-cell count, its real elapsed limits, and later numerical admission
remain separate work.
