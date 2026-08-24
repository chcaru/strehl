# M80 — repair the argmax-biased detail invariant

**VERDICT — MEASURED/ARGUED. REPAIRED, WITH THE PRODUCT TOLERANCE STILL
UNCLAIMED.** M80 directly reproduces M77's reported `RETENTION` of **9.963×**
and **8.819×** on M77's two noise controls. The ideal i.i.d. order-statistic
correction does **not** turn either reading into approximately one: it
over-subtracts both and clamps both to zero. The shipped replacement therefore
measures the actual selection-conditioned gradient power on a contemporaneous
flat control, cross-fits that nuisance estimate, and compares every candidate
with the full-stack selector at equal noise. Both registered real noise controls
now read **1.000×–1.006× `STRUCTURE`**, while both registered real-detail
controls remain above **3.20× `STRUCTURE`**. A deliberate blur is also detected,
so this is not a statistic repaired into reading one everywhere.

**VERDICT — ARGUED.** M80 fixes the comparison site for
`DETAIL_COLLAPSE_FLOOR = 0.90`: it now means a ten-percent equal-noise gradient-
amplitude loss from the full-stack selector, rather than a ratio to one
arbitrary middle frame. M80 does not claim that ten percent is the correct
product tolerance.

## M80 §1 — Source, ordering, and ownership

**MEASURED.** I read M77's own report at M77 §9, M77 §12, M77 Addendum B,
M77's own fact 35, and M77 §21; I then read the implementation in
`crates/strehl-cli/src/merge_cmd.rs` and its invocation in
`crates/strehl-cli/src/main.rs`. No number below was taken from a SYNTHESIS
summary.

**MEASURED.** The acceptance bars and the unrun reproduction script were
committed first, at M80 commit `35a362b`. The reproduction evidence was
committed separately at M80 commit `7330c3c`. The implementation and controls
were committed at M80 commits `df71d3e` and `968300c`. The path audit for those
commits contains only M80's owned `merge_cmd.rs` and
`experiments/M80-invariant-repair/`.

**MEASURED.** M80 did not edit `crates/strehl-cli/src/main.rs`,
`crates/strehl-core/src/merge.rs`, M77's experiment, `AGENTS.md`, or
`docs/research/SYNTHESIS.md`. M81 changed its owned files concurrently; final
measurements therefore use a private source snapshot and name its exact commit,
tree, source hashes, and binary hash in M80 §7.

## M80 §2 — Direct reproduction from M77's logs

**MEASURED.** `experiments/M80-invariant-repair/src/01-reproduce-and-derive.py`
parses M77's own `out/07-B2-wrapped-text-1.log` and
`out/07-B2-wrapped-text-2.log`. The first execution selected no reference row
because M77's source text has a space before the colon in `single frame 65 :`;
the parser was corrected before a result was accepted.

| Claim class | M77 stack and depth | M77 gate | M77 printed `RETENTION` | M80 from displayed corrected operands | M80 verdict |
| --- | --- | ---: | ---: | ---: | --- |
| MEASURED | `wrapped-text-1`, M77 `N = 130` | M77 gate `0` | **9.963×** | 9.962495× | reproduced |
| MEASURED | `wrapped-text-1`, M77 `N = 130` | M77 gate `4` | **9.188×** | 9.188039× | reproduced |
| MEASURED | `wrapped-text-2`, M77 `N = 120` | M77 gate `0` | **8.819×** | 8.818838× | reproduced |
| MEASURED | `wrapped-text-2`, M77 `N = 120` | M77 gate `4` | **6.791×** | 6.790876× | reproduced |

**MEASURED.** M77's first gate-zero quotient is 0.000005× beyond M80's
registered 0.0005× recomputation bar if the already-rounded, four-decimal
operands are treated as exact. Propagating their displayed ±0.00005
quantisation gives `[9.962373, 9.962617]`, which contains the rounding boundary
for M77's printed 9.963×. This interval treatment did not change the registered
bar; it accounts for information absent from the printed operands. The other
three displayed-operand quotients round directly to M77's printed values.

**MEASURED.** M80 therefore explicitly reproduces both requested gate-zero
values, **9.963× and 8.819×**, as well as M77's shipped-gate values **9.188×
and 6.791×**. Full parsed operands and intervals are in
`out/01-reproduce-and-derive.json`.

## M80 §3 — The analytic inflation term and its residual

**DERIVED.** For i.i.d. samples with CDF \(F\), the maximum has CDF
\(F_{\max}(x)=F(x)^N\). For scalar Gaussian noise
\(Z_i\sim\mathcal N(0,\sigma^2)\), its exact expectation is

\[
E[\max_i Z_i]
 = \sigma N\int_{-\infty}^{\infty}z\,\phi(z)\Phi(z)^{N-1}\,dz ,
\]

**DERIVED.** That scalar location shift grows asymptotically like
\(\sigma\sqrt{2\log N}\), but it is not the term to subtract from a spatial
gradient power: a common selected intensity offset can cancel in a difference.
The statistic M77 identified subtracts a *variance*, so M80 evaluated the
corresponding ideal gradient-energy order statistic.

**DERIVED.** Let one frame's ideal noise gradient be
\(g_i=(d_x,d_y)\), with independent components
\(\mathcal N(0,s^2)\). Then
\(X_i=\lVert g_i\rVert^2/(2s^2)\sim\operatorname{Exp}(1)\), and with
\(V=E[\lVert g_i\rVert^2]=2s^2\),

\[
E[\max_i \lVert g_i\rVert^2] = V H_N,\qquad
H_N=\sum_{j=1}^{N}\frac1j .
\]

**DERIVED.** Relative to an unselected sample, the ideal selector's excess
noise power is therefore \((H_N-1)V\). If an output averages the vectors
associated with the largest \(n\) energies and their directions remain
symmetric, the expected sum of those energies is
\(nV(H_N-H_n+1)\). Its variance inflation over an ordinary \(n\)-sample mean is
therefore

\[
I^2(N,n)=H_N-H_n+1 .
\]

**MEASURED/DERIVED.** M80 applied that term to M77's gate-zero operands before
choosing the repair:

| Claim class | M77 stack | M77 depth | \(H_N\) and ideal amplitude | observed excess | ideal excess | signed power after subtraction | residual relative to the single-frame target | corrected `RETENTION` |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MEASURED/DERIVED | `wrapped-text-1` | M77 `N = 130` | 5.448591; 2.334222× | 1,971.419 DN² | 2,720.066 DN² | −728.582 DN² | **−748.647 DN², −37.975%** | **0.000× after clamp** |
| MEASURED/DERIVED | `wrapped-text-2` | M77 `N = 120` | 5.368868; 2.317082× | 2,551.533 DN² | 13,596.355 DN² | −11,011.587 DN² | **−11,044.823 DN², −432.870%** | **0.000× after clamp** |

**MEASURED.** The ideal term is 137.975% and 532.870% of the respective
observed selection excesses. Equivalently, M77's observed gate-zero raw/model
gradient-amplitude ratios are only 2.063254× and 1.352980×, against ideal
\(\sqrt{H_N}\) values of 2.334222× and 2.317082×.

**ARGUED.** The ideal order statistic gets the mechanism class and its
\(N\)-growth right, but not the shipped operator's magnitude. The merge elects
on a regularised spatial focus field, then this invariant differentiates
neighbouring selected intensities; those selected neighbours are correlated,
heteroscedastic, and are not the i.i.d. two-component vectors in the derivation.
The signed residuals above are the honest remainder: there is no positive
unexplained residue to hand-wave away, but substantial *over*-subtraction.

**MEASURED/ARGUED.** M80's registered analytic arm A1 therefore fails on both
stacks. An \(H_N\) correction would turn M77's approximately ten-on-nothing
reading into zero-on-nothing, not one-on-nothing, so it is rejected rather than
shipped.

## M80 §4 — The repair

**ARGUED.** The replacement estimates the nuisance created by the actual stack,
focus operator, gate, noise model, and frame count. It transfers no fixed bar
between M77's `N = 120`, M77's `N = 130`, or the wider corpus range.

**DERIVED.** Split both flat and detail ROIs into disjoint left and right
gradient-anchor sets. For measured gradient power \(P\) and model gradient-noise
power \(V\), fit

\[
k_L^2=P(\mathrm{flat}_L)/V(\mathrm{flat}_L),\qquad
k_R^2=P(\mathrm{flat}_R)/V(\mathrm{flat}_R).
\]

**DERIVED.** Apply each scale only to the opposite detail half, combine by its
sample count, and retain signed resolved power:

\[
V_{\mathrm{cf}}
 = \operatorname{weightedMean}\!\left(
 k_R^2V(\mathrm{detail}_L),\,
 k_L^2V(\mathrm{detail}_R)\right),\qquad
Q=P(\mathrm{detail})-V_{\mathrm{cf}} .
\]

**ARGUED.** When the detail ROI is the flat ROI, as in M77 arm B2, no gradient
anchor both fits and evaluates its own nuisance scale. This cross-fit prevents
the null from being made true by self-calibration.

**MEASURED.** During the existing second decode pass, M80 captures only the two
small ROIs from the completed full-stack winner map. The memory is constant in
stack depth and is charged to the worker plan. M81's gate-zero tie repair,
present in the final measured snapshot, makes that winner capture exactly the
gate-zero output even when focus responses tie.

**DERIVED.** Let the controlled selector have powers \(P_0,V_0\). M80 reports

\[
\mathrm{STRUCTURE}=\sqrt{P/V_{\mathrm{cf}}},\qquad
\mathrm{RETENTION}
 =\sqrt{\frac{\max(Q+V_0,0)}{P_0}} .
\]

**DERIVED/ARGUED.** This compares candidate and selector resolved signal at the
same selector-noise power. Pure noise has \(E[Q]=0\), while at high structure
the common \(V_0\) becomes negligible and `RETENTION` approaches a resolved
gradient-amplitude ratio. The selector remains a reference, but its selected
power is never interpreted raw as detail: its nuisance is measured by the same
cross-fitted control.

**MEASURED.** The implementation is at `merge_cmd.rs:353–516`; selector capture
is at `merge_cmd.rs:531–614`; capture memory is priced at
`merge_cmd.rs:631–720` and `merge_cmd.rs:948–968`; reporting is at
`merge_cmd.rs:1492–1636`; and the synthetic controls are at
`merge_cmd.rs:2774–2862`.

**ARGUED.** M80 rejected a fixed \(H_N\) subtraction because M80 §3 falsifies
its magnitude; rejected one fitted multiplier because both \(N\) and gate
change the nuisance; rejected even/odd or half-stack held-out merges because
they change the accepted subject to an approximately half-depth stack; and
rejected the old middle-frame and a best-frame denominator because the former
drifts with defocus and the latter is another uncorrected selected statistic.
A truly independent repeated exposure at every focus position would permit a
held-out measurement, but this corpus does not contain that paired capture.

## M80 §5 — Falsifiable noise and detail controls

**MEASURED.** The final private binary reran M77's exact real arm-B2 noise ROIs
and arm-B1 detail ROIs. M80's registered real bars all pass:

| Claim class | stack/control | selector `STRUCTURE` | M80 gate-zero `STRUCTURE` | M80 gate-four `STRUCTURE` | M80 gate-four `RETENTION` | registered verdict |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| MEASURED | `wrapped-text-1` B2 noise | 1.002× | 1.002× | **1.006×** | **1.003×** | M80 N1 pass |
| MEASURED | `wrapped-text-2` B2 noise | 1.000× | 1.000× | **1.000×** | **1.000×** | M80 N1 pass |
| MEASURED | `wrapped-text-1` B1 detail | 3.499× | 3.499× | **3.522×** | **0.996×** | M80 P2 pass |
| MEASURED | `wrapped-text-2` B1 detail | 3.306× | 3.306× | **3.201×** | **0.970×** | M80 P2 pass |

**ARGUED.** Gate-zero `RETENTION` is one by reference identity and is not
evidence. The falsifiable real null is the independently reported
`STRUCTURE`, plus gate-four `STRUCTURE` and `RETENTION`, where candidate and
selector differ.

**MEASURED.** The real gate-zero fitted nuisance amplitudes differ materially:
M77's `wrapped-text-1` control measures \(k_L/k_R=1.951/2.165\), while M77's
`wrapped-text-2` control measures \(1.337/1.369\). That is the actual
stack-specific term the ideal \(N\)-only calculation missed.

**MEASURED.** M80's deterministic checkerboard positive control used
independent Gaussian noise and selection-inflation scales at registered depths
`N = 22`, `N = 130`, and `N = 299`. The registered three-by-three blur retained
only 0.369038× gradient amplitude, a 63.0962% planted loss:

| Claim class | M80 synthetic depth | noise `STRUCTURE` | noise `RETENTION` | clean detail `STRUCTURE` | clean detail `RETENTION` | blurred detail `RETENTION` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MEASURED | `N = 22` | 0.997701× | 0.997434× | 5.950740× | 1.000332× | **0.425848×** |
| MEASURED | `N = 130` | 1.000482× | 0.998817× | 5.208819× | 1.000717× | **0.449006×** |
| MEASURED | `N = 299` | 0.999476× | 0.998303× | 4.940328× | 0.999482× | **0.457904×** |

**MEASURED.** The clean-retention range across M80's three depths is
0.001235×, inside the registered 0.05× bar. Every clean `STRUCTURE` exceeds the
registered 3.0× bar, and every blurred `RETENTION` is below the registered
0.80× bar. The statistic therefore preserves a noise null and still responds
strongly to deliberately removed detail.

**MEASURED.** The synthetic fitted nuisance amplitudes also increase with
depth: \(1.395/1.394\) at M80 `N = 22`, \(1.598/1.595\) at M80 `N = 130`, and
\(1.685/1.693\) at M80 `N = 299`. The repair remeasures these values; it does
not transfer any one of them.

## M80 §6 — A control made to fail

**MEASURED.** `src/02-negative-control.py` constructs a byte-string mutation
that replaces the opposite-half scales `(scale_right, scale_left)` with
`(1.0, 1.0)`. It requires exactly one anchor and one marker, writes the plant,
and re-reads the exact bytes before invoking Cargo.

**MEASURED.** On the final M80 source, the original had SHA-256
`f81ec3500f57055ade9a515f8f65c8fcdd6d782fb07cb7ae9d199393419ae7cc`;
the read-back plant had SHA-256
`50fd313b4c52abeadbdf2f8e060da02f1741a1daafdcd72d8baa75d05ddbb3d9`,
with one exact marker and one exact replacement.

**MEASURED.** The planted test exited **101** and said:

> `noise null N=22: STRUCTURE must read 1, got 1.391267`

**MEASURED.** The script restored the original SHA-256 exactly, removed its
backup, touched the Rust source so Cargo recompiled it, and reran the identical
command. The restored run exited **0** and reported the targeted test `ok`.
Both `red control pass=True` and `restored green pass=True` are recorded in
`out/02-negative-control.log`.

## M80 §7 — Provenance, non-perturbation, and checks

**MEASURED.** The final real controls used a clean Git archive captured at
integrated commit `cfa9c75e5477ca59a6641a33807e4d2527188b9a`, tree
`5723ba2fc50b31b8f90f19bf216d5123414f9717`, not the live shared checkout.
The archived `merge_cmd.rs` SHA-256 is
`6c6cb6aa1a36f7a6a040708f139d52893cd13e4fa70431aa4042d63e30a5e663`.
The private release binary SHA-256 is
`ef52ae761d175deede3be8b4636c3b2dcff4ad0c62baf588835766378b377a2a`.

**MEASURED.** M80's registered observer non-perturbation control ran the same
M80 gate-four, 22-frame merge once without ROIs and once with the repaired
invariant. Both TIFFs were 49,449,626 bytes and both had SHA-256
`48dfb69c00f0107f71adeec1c76820e16c6c4d18c0ad0c0544b88fa5a7fd4c49`.
The diagnostic is byte-non-perturbing on that control.

**MEASURED.** On the same committed source snapshot, `cargo fmt --all --check`
exited zero; all 22 `merge_cmd::tests` passed; and the private release build
completed. Evidence is in `out/08-build-snapshot.log` and
`out/09-snapshot-verification.log`.

**MEASURED.** The repository-required UTF-8 corpus lint checked 106 Markdown
files and 31 Rust files and reported `OK — no violations`.

**MEASURED.** Strict `cargo clippy -- -D warnings` reached M81-owned
`main.rs:366` and exited 101 solely on that concurrent function's
`clippy::too_many_arguments` warning. M80 did not edit `main.rs`. Re-running
with only `clippy::too_many_arguments` allowed exited zero; M80's own
`cross_fitted_detail` had already been reduced to two arguments after the same
strict check identified its earlier eight-argument form.

**ARGUED.** The strict Clippy tree is therefore not green at the measured
snapshot, but the remaining diagnostic is outside M80's ownership and is not
required by this repair. No broader lint class was suppressed.

## M80 §8 — The third bare constant

**MEASURED.** M77 §9 and M77 §12 correctly found that
`DETAIL_COLLAPSE_FLOOR = 0.90` was compared with a ratio to an arbitrary middle
frame. M77's own fact 24 measured that comparison tolerating 19.2%–99.3%
detail loss across its five stacks.

**MEASURED/ARGUED.** M80 removes the arbitrary-frame denominator. The
unchanged M80 floor now acts on equal-noise retention from the full-stack
selector. On the two real positive controls, M80 gate-four retention is
0.996× and 0.970×; the deliberate blur reads 0.426×–0.458× and trips the floor.
The specific 19.2%–99.3% failure mode is repaired.

**ARGUED.** The numeric value remains a separate product-policy question. M80
has no truth-referenced real bracket from which to infer whether a ten-percent
resolved-gradient loss is the right acceptance boundary, so changing `0.90`
from these same observations would be post-measurement tuning. M80 leaves the
value unchanged and routes its calibration as **unclaimed**.

## M80 §9 — Boundaries of the verdict

**ARGUED.** The cross-fit prevents a sample from calibrating its own null, but
it does not prove that a geographically separate flat ROI has exactly the same
selection-conditioned nuisance scale as a detail ROI. Flat contamination or a
spatially changing noise model can bias that transfer. The CLI already requires
the sibling flat-structure invariant; callers must continue to treat a
non-flat control as a failed precondition, not as calibration data.

**ARGUED.** M80 repairs the acceptance statistic, not the merge estimator and
not the choice of operating gate. It makes the observable interpretable: a
noise control reads approximately one, real detail remains visible, and a
destructive blur fails. It does not turn those controls into a truth-referenced
proof that any particular merge is optimal.

## M80 §10 — Evidence map

**MEASURED.** The durable evidence is:

- **MEASURED.** Pre-registration:
  `experiments/M80-invariant-repair/PREREGISTRATION.md`.
- **MEASURED.** M77 reproduction and analytic residual:
  `out/01-reproduce-and-derive.{log,json}`.
- **MEASURED.** Byte-confirmed red/restore/green control:
  `out/02-negative-control.log`.
- **MEASURED.** Final M77 arm-B1 and arm-B2 reruns:
  `out/03-*.log` and `out/03-run-real.json`.
- **MEASURED.** Registered real-control decisions:
  `out/04-evaluate-real.{log,json}`.
- **MEASURED.** Observer non-perturbation:
  `out/05-nonperturbation.{log,json}`.
- **MEASURED.** Synthetic null and positive controls:
  `out/06-plants.log`.
- **MEASURED.** Private snapshot build and verification:
  `out/08-build-snapshot.log` and `out/09-snapshot-verification.log`.
- **MEASURED.** Required repository lint: `out/10-corpus-lint.log`.
