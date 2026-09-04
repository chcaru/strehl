# M135 burned-slide physical commissioning preregistration

Status: **FROZEN BEFORE ANY M135 READ OF THE AUTHORIZED DEVELOPMENT SESSION**

Scope: instrument development only. No value from this experiment may populate
M1, qualify a comparator, or be described as a score.

## 1. Authorization and holdout boundary

The orchestrator has deliberately burned the complete uninterrupted
`2026-09-02` subject/session at:

```text
D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl
```

M135 may read it only after the M139 host-quiet lock is explicitly released.
Everything under `D:\` remains read-only. The holdout unit is the subject plus
the complete uninterrupted session, so all four named stacks and every other
frame from that sitting are development material together. No result below is
score-bearing.

Expected inventory, taken from repository records rather than an M135 read:

| stack | expected frames | intended development role |
|---|---:|---|
| `tilted-sw4-cpl` | 182 | finer focus-sampling arm |
| `tilted-sw10-cpl` | 92 | coarser focus-sampling arm |
| `flat-sw4-cpl` | 186 | flat/source-null diagnostic |
| `very-tilted-all-axis-sw10-cpl` | 197 | geometry stress arm, not a repeat |

An inventory mismatch is reported; it is not repaired by silently changing the
population.

## 2. Questions frozen before inspection

This run answers, in order:

1. Do the `sw4` and `sw10` stacks cover the same focus-encoder range?
2. Does the session actually contain all independent roles needed to identify
   the full `J_TR` optical-improvement contrast?
3. If not, what narrower physical fact does the `sw4`/`sw10` pair establish?
4. Does the flat source remain quiet under the frozen extraction, or does
   repeatable flat structure appear?

The allowed terminal answers include `COULD_NOT_DETERMINE`. A missing reference
role is not converted into a negative detail result.

## 3. Stage A — inventory and focus-range audit

After host release, enumerate only regular `.ARW` files below the four named
directories. Sort each stack by `DateTimeOriginal`, subsecond time, then
filename. Extract at least:

- filename and byte size;
- image dimensions;
- capture timestamp including subseconds;
- exposure time, ISO, f-number and reported focal length;
- lens identity;
- `FocusPosition2` and any finer focus-position field present;
- stabilization state when present; and
- the raw orientation field.

### 3.1 Coarse encoder predicate

Report the complete `FocusPosition2` histogram for both tilted stacks. The
repository claim `COARSE_ENCODER_RANGE_EQUAL` passes only if:

```text
min(FocusPosition2_sw4)  = min(FocusPosition2_sw10)
max(FocusPosition2_sw4)  = max(FocusPosition2_sw10)
```

with no missing value in either stack. Equal minima and maxima establish only
the camera's coarse reported range; they do not establish equal physical
endpoints.

### 3.2 Image-derived coverage predicate

Before reading any high-frequency outcome, freeze an implementation that:

1. decodes camera-linear green data without rendering either candidate;
2. registers the two stacks from low-pass input structure only;
3. detects the common slide quadrilateral below `0.10 cyc/native px`;
4. places a fixed `8 x 8` lattice in normalized slide coordinates;
5. estimates each site's focus-peak frame from an input-only focus curve capped
   at `0.25 cyc/native px`; and
6. robustly fits

```text
u10 = a + b * u4,
```

where `u4` and `u10` are the peak locations normalized to `[0,1]` within each
ordered stack.

Call the physical ranges equivalent only if at least 48 of 64 sites have an
interior peak in both stacks and the fixed equivalence bounds hold:

```text
|a|              <= 0.02
|b - 1|          <= 0.04
q95(|residual|)  <= 0.03.
```

Report the node-density ratio over the common eligible interval. These bounds
are development screens, not a scorecard bar. If the implementation cannot
produce stable common sites without output-derived tuning, report
`IMAGE_RANGE_UNDETERMINED`.

## 4. Full `J_TR` identifiability gate

The full M135 construction needs, for the same physical sites:

- two independently rendered output captures `Y1/Y2` for each optical arm;
- two independently exposed and independently calibrated reference
  realizations `R1/R2`;
- a reference/scored subject-sampling lower bound of at least `2.0`;
- disjoint output/reference flat and dark lineages;
- at least 64 eligible nonperiodic sites; and
- matched flat evidence.

The four named stacks do not satisfy those roles merely by having real photons.
In particular:

- `tilted-sw4-cpl` may not be both the claimed improvement and its truth;
- odd/even or other splits of one focus ladder may not be relabeled as an
  independently captured higher-sampling reference;
- `very-tilted-all-axis-sw10-cpl` may not be called a repeat because its
  geometry differs; and
- the public periodic checker pattern may not be treated as concealed truth.

Therefore the preregistered full-instrument outcome is
`REFERENCE_ROLE_ABSENT` unless file-level evidence reveals a separately
captured, same-site fixed-focus reference and disjoint calibration roles that
are not present in the repository inventory. No source-derived oracle,
super-resolution fit, dense-stack output, or analytic checker template may
fill the missing role after outcomes are seen.

If the gate returns `REFERENCE_ROLE_ABSENT`, **no `J_TR(sw4)/J_TR(sw10)` ratio
is identifiable from this session**. That is a finding about the capture, not
a failure of either arm.

## 5. Real-optics arm and flat diagnostics

If Stage A passes, the session establishes a real pre-sensor intervention:
independent `sw4` and `sw10` exposures over an equivalent focus range, with
fresh downstream noise in both arms and approximately denser z sampling in
`sw4`. Report this as `REAL_OPTICAL_ARM_PRESENT`.

It does not by itself establish that `J_TR` moves in the improvement direction.
That direction needs the common independent reference frozen in section 4.
Using `sw4` as that reference would make the positive control circular and is
forbidden.

A separate camera-linear source diagnostic may be implemented after its code,
site manifest algorithm, bands and hashes are frozen. It may report local
focus-curve coverage and noise-corrected raw transfer as
`DEVELOPMENT_DIAGNOSTIC`; it may not be renamed `J_TR`, used to bind M138, or
substitute for the missing reference.

For `flat-sw4-cpl`, report:

- the three exposure groups separately;
- high-band power through `0.25 cyc/native px`;
- repeatable sensor-coordinate structure; and
- whether a fixed four-way temporal split produces `NO_DETAIL` in the core
  arithmetic.

Because this session lacks disjoint flat/dark A/B masters for all four
lineages, the public certificate must still refuse physical binding even if
the arithmetic flat diagnostic is quiet. A non-quiet flat is a physical
commissioning failure; a quiet diagnostic is necessary but not sufficient.

## 6. Required reporting

The report must distinguish:

1. verified frame count and metadata range;
2. coarse encoder equality;
3. image-derived range equivalence or `IMAGE_RANGE_UNDETERMINED`;
4. full `J_TR` identifiability;
5. presence of a real optical intervention;
6. flat diagnostic state; and
7. the explicit label **DEVELOPMENT — NEVER A SCORE**.

No one number may conflate these states. Any implementation and result artifact
must be committed under `experiments/M135-slide-physical-commissioning/`.
