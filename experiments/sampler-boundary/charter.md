# Checked-sampler boundary commission

2026-09-08. Root-owned bounded engineering continuation after common-TIFF
integration completed at evidence4f085b86/reportc9b4f4e5. The exact164 common
execution sources are archived. Do not rerun any completed common-TIFF image,
M194h, M194g or M193c audit. This commission may alter owned sampler code only
after its original behavior has been exercised by independently authored tests.

## Question and consumer

Can the existing checked sampler return a value for the requested high-edge
fractional coordinate while retaining its declared coverage mask and legal
stencil? Source inspection finds accepted coordinates clamped earlier than
their tap support requires. This is DERIVED, not yet a measured defect.

Consumer: warpmap::gather_checked writes Some as covered and None as NaN/false.
Fixtures use integer-centered128x96 scalar planes in plane-sample-pitch units.
Native align_cmd samples full-resolution planes after its explicit factor-two
conversion; no new native render or real map is part of this investigation.
The identity common-RGB consumer does not call these resamplers.

Preserve kernel coefficients, the clamped cubic's separate value limiter,
storage/noise rules and kernel/default selection. Preserve the finite checked
domain initially. Narrowing coverage is a different outcome and must be
reported, not substituted to satisfy a value assertion. Nonfinite-coordinate
refusal is a separate named checked-domain requirement. No quality/SOTA claim.

## Prior-art search performed before this commission

Root actually ran, exit0:

    python experiments/ORCH-drift-check/prior_art.py sample_checked bilinear CatmullRom boundary clamp

The tool surfaced ORCH-clamp-default-decision.md, BUILD-BLEND.md,
M136-m8-passability.md, M194e-joint-pupil.md and M-PHASE0-VEIL2.md; secondary
mentions were ORCH-veiling.md, BUILD-HULL.md, M136-m8o-bar.md,
M136-m8-census-groundtruth.md, M87-occlusion.md and V-hull.md. These reports are
under docs/research. Root then searched all of them for the exact checked/
coordinate-clamp/border terms and read the directly relevant M136 sections and
the clamp-default decision. Source tests surfaced sample_bilinear_strict and
the cubic support-hull, bit-identity, integer and constant-plane tests.

M136's census explicitly reproduces coordinate clamping and validity before
testing the value hull. Its reported hull invariant does not establish that
an accepted value describes the requested fractional coordinate. This new
question is about coordinate preservation, not a new hull-quality/default
decision. ORCH's anti-score-gaming rule and M136's limits remain binding.
An already-answered finding, with no justified change, is a successful outcome;
do not assume the absence of prior work from a filename search.

## Fixed control design before execution

The prospective detail is in ../common-tiff-stack/work/next-sampler-boundary.md.
The independent test author must freeze the exact finite rows/tolerances and
show that each named property is exercised before either baseline or repaired
code runs. No parameter sweep or image/RAW/model population.

Use literal affine truth for Bilinear and both cubic variants. For Lanczos2/3,
use same-phase translated stencil equivalence; normalization does not imply
exact first moments. Include both axes and corners at quarter/half phases,
low boundary/interior/last integer/exact checked upper boundary, just/distant
outside positions and a flat null. Include a wrong translation or phase as a
destroyer with an actual changed-input witness. Nonfinite coordinates must
refuse without indexing; tiny valid planes cover declared-support refusal.
One fixed public gather must compare actual coverage entries, refusal NaNs and
values to an independently enumerated reference-to-source map.

Preserve every baseline row even if some fail; do not stop after the first
discrepancy and label the rest covered. The original public API path must
produce an actual failing assertion for the defect. The author of the repair
does not author or solely verify that test. Current full-support cubic hull
and interior/integer/null tests remain regression requirements.

## Ownership and finite execution

Independent tests: separate Rust integration-test source, with source-only
design reviewed by root and a second agent. Repair author: draft a patch outside
crates first, preserving the original source until baseline evidence commits.
Controller author: new bounded Cargo/test execution using held owned-process
primitives; do not modify any old controller or source archive.

Authorize two separately frozen fresh test builds, original then repaired:
each600CPU/300whole-wall/3GiB owned Job/128MiB retained/4GiB observed scratch,
exactly two Cargo jobs, offline locked dependencies. Each actual test-binary
invocation is separately capped30CPU/60whole-wall/512MiB/16MiB retained.
Reserve the existing finite parent tail and owned cleanup. No retries within
an attempt. Failed stages keep their costs and artifacts. Up to four
metadata-only5CPU/7.5active-wall slices reserve20CPU/30active-wall/8MiB.
No real capture, performance comparison, workspace-wide campaign or new SOTA
bar is authorized by these test allocations.

All exact source files, command/arguments/environment and input rows must be
held and committed before execution. Keep actual Compiling/fresh artifact
evidence, exact child exit, raw output, complete row population and terminal
Job accounting. The original test failure is not a success and the repaired
run must not overwrite it. A repaired candidate that loses coverage or changes
unrelated interpolation behavior is not admitted merely because one test passes.

After independent final review, preserve exact owned source/results, report
any behavior change and choose the next concrete consumer task. Continue under
the owner's autonomous instruction.
