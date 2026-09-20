# Local through-focus edge motion: bounded audit

Read-only audit, 2026-09-19. **Decision: no source-selection implementation or
real-data motion campaign yet.** Local normal displacement is a distinct,
apparently untested observable in the searched record; it is not an identified
source-direction or ownership cue. RAW-affinity's fixed rule remains closed.

**Existing evidence, read by content.** The search command was
`python experiments/ORCH-drift-check/prior_art.py phase flow motion MTF`, followed
by targeted report/source reads. `M-PHASE0-PHASE/PREREGISTRATION.md` Amendment A10
concerns alias reconstruction and placement accuracy, not ray motion: its final
verdict is NOT ROBUST, with a retracted earlier kill. `M183-rho-convention.md`
retains that verdict after pinning the convention. `M-PHASE0-XSPEC.md` tested
complex odd-defocus phase, phase-ramp registration and an inversion guard. Its
nominal reads were adverse, but population/floor failures prohibit a permanent
kill; none tested local edge trajectories as support ownership. M70 measured
modulus, not complex trajectories. M78 shows that interpolated shifts can change
the supposed phase evidence through filtering. M97's max-gradient tracker
selected a different physical feature. M-PHASE0-SLANTEDGE rejects MTF50 as a
standalone resolution claim; M57's phase-only single-ring rejection concerns a
quality metric, not a displacement instrument. The existing defect-map motion
test separates sensor-fixed dust from travelling subject content, a different
coordinate question. No exact prior empirical closure of this proposed local
cue was found.

**Why motion alone is insufficient (DERIVED/ARGUED).** A centred symmetric blur
leaves an ideal isolated step's midpoint stationary while changing its spread.
The two sides of a genuine narrow ridge can move apart under defocus just as
glint contours can; movement does not make the ridge false detail. Conversely,
for stationary overlapping components a local complex coefficient is
`z_k = a_k z_u + b_k z_v`: changing their relative amplitudes rotates its phase
without either component translating. Different-depth occlusion, specular
variation and clipping can supply those changes. A phase-derived displacement
therefore needs a valid local translation/correspondence model. Phase wrapping,
near-zero coefficients and contrast inversion can break that model; the aperture
problem leaves tangential motion unknown. Neither stationarity nor outward
motion identifies the focused donor.

**Only surviving minimal falsifier, if commissioned separately.** Freeze one
local directional complex-band normal-displacement estimator and test it on
three short generated sequences through the actual rounded CFA gather: a
centred glint with increasing optical spread; a stationary genuine thin/radial
feature at another depth crossing that spread; and two stationary unresolved
features whose relative amplitudes change, with a no-spread twin. Use the same
sampling phases/maps and injected noise. Require a useful signed displacement
on the spread positive while the stationary-mixture and genuine-feature cases
remain stationary or explicitly unknown; an all-unknown result fails utility.
Known translation commissions sign/units; a matched held-map perturbation tests
placement leakage. Judge correspondence against planted feature positions,
not gradient energy, MTF, or a phase-coherence score. If the positive and
destroyer are indistinguishable, close this cue for standalone ownership rather
than adding another fitted threshold. Passing would license only a local motion
measurement, not donor election or a merge.

The four retained wide source witnesses cannot establish temporal derivatives,
continuity or phase unwrapping. Any later real measurement must state native vs
quad units, held reference gauge, pair baseline, CFA aliases and gather-induced
phase/filtering; residual placement can imitate the signal. No new measurement,
RAW read, test execution, quality claim or quantitative result is made here.
