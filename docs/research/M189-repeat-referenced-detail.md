# M189 — repeat-referenced detail

**Status: NO-GO BEFORE IMPLEMENTATION.** The proposed mechanism does not
survive a signal-plus-independent-noise derivation, and the route is not new.
Independent repeats can support an acquisition-information coordinate, but
repeats alone cannot produce a stand-alone delivered-detail instrument that
falls under common output blur without rising under common output sharpening.
No M189 candidate or holdout measurement was run.

## 1. Corpus search and prior disposition

The search was performed over committed `HEAD` artifacts in `docs/research/`
and `experiments/`, including a whitespace-collapsed search for wrapped phrases.
The route is the existing repeat-pair FRC/coherence family, not a distinct
seventh family:

1. The microscopy survey states the same hypothesis almost verbatim: FRC uses
   two independent noisy realizations, and invented detail should receive no
   credit because it is uncorrelated between them
   (`docs/research/G-edof-deconvolution.md:609-612`).
2. M46 actually evaluated two independent captures of the same subject. Its
   assignment expected the independent captures to decorrelate read noise
   (`docs/research/M46-detail-metric-measured.md:23-27`), but the measured
   result says the pair "`did not decorrelate anything`"
   (`docs/research/M46-detail-metric-measured.md:43-50`). The flat FRC was
   `+0.7310`, higher than the within-capture `+0.6569`, and the flat/detail
   ratio was `0.7714` (`docs/research/M46-detail-metric-measured.md:129-152`).
3. `M-FRC-VIABILITY` is the later repeat-pair adjudication. It allows
   commissioning only, says common post-noise filtering is an ideal null, and
   says FRC is not a complete resolution instrument
   (`docs/research/M-FRC-VIABILITY.md:1-13`). Its final scope is
   "`repeatable scene-information bandwidth under independent acquisition
   noise`", explicitly not stand-alone visual resolution or transfer
   (`docs/research/M-FRC-VIABILITY.md:564-570`).
4. M135 asks the exact question, "`Does an independent repeated bracket rescue
   D8?`", and answers no as M1
   (`docs/research/M135-detail-instrument.md:99-111`). Its revised ruling keeps
   repeat-pair FRC only as a possible information/noise coordinate and says it
   cannot supply M1 by itself
   (`docs/research/M135-detail-instrument.md:476-533`).
5. The independent M167 battery subsequently rejected the surviving D8 FRC
   implementation on the flat null and signed post-render blur: detail and flat
   were both censored above Nyquist, and two blur rungs moved upward
   (`docs/research/M167-detail-battery.md:118-145`).

The nearby `M-PHASE0-XSPEC` route is distinct. It uses complex cross-spectra
*through focus* for registration, defocus sign, pupil retrieval, and a
contrast-inversion refusal guard; it is not a cross-repeat absolute-detail
statistic (`docs/research/M-PHASE0-XSPEC.md:41-56`).

**Ruling:** repeat-referenced normalized agreement is already retired as a
stand-alone delivered-detail instrument. It remains an auxiliary
acquisition-information diagnostic only.

## 2. Independent derivation

Consider one registered Fourier cell. Let two independently acquired repeats be

\[
A=S+N_A,\qquad B=S+N_B,
\]

where \(S\) is the shared scene term and \(N_A,N_B\) are zero-mean independent
temporal-noise realizations, each independent of \(S\). For equal noise power
\(P_N\), the population cross-repeat coherence is

\[
\rho(A,B)
=\frac{E[AB^*]}
       {\sqrt{E|A|^2E|B|^2}}
=\frac{P_S}{P_S+P_N}.
\]

Now apply the same post-acquisition linear filter \(K\) to both repeats:

\[
A'=K(S+N_A),\qquad B'=K(S+N_B).
\]

Then

\[
\begin{aligned}
E[A'B'^*] &= |K|^2P_S,\\
E|A'|^2 &= |K|^2(P_S+P_N),\\
E|B'|^2 &= |K|^2(P_S+P_N),
\end{aligned}
\]

and therefore

\[
\rho(A',B')=\rho(A,B).
\]

The same conclusion holds for unequal repeat-noise powers because the common
\(|K|^2\) factor cancels from both denominator factors. Noise independence is
needed to interpret the cross term, but it does not make a common filter
decorrelate the repeats.

The other obvious estimators give the complementary failure:

\[
\begin{aligned}
P_{\rm cross}' &= E[A'B'^*]=|K|^2P_S,\\
P_{\rm diff}'  &= \tfrac12E|A'-B'|^2=|K|^2P_N,\\
P_{\rm cross}'/P_{\rm diff}' &= P_S/P_N.
\end{aligned}
\]

Thus:

- normalized agreement or signal/noise ratios are exactly unchanged by a
  common post-noise USM, but also by a common post-noise blur;
- absolute coherent power responds to blur, but a USM gain \(|K|>1\) raises it
  by \(|K|^2\);
- subtracting or dividing by repeat-difference noise does not create a third
  behavior. It returns either the amplitude-sensitive or invariant branch.

This independently reproduces the dichotomy recorded by M135: `P_sig` sees
blur and sharpening alike, while normalized SNR/FRC sees neither common
post-render intervention
(`docs/research/M135-detail-instrument.md:372-387`).

### 2.1 Pooling does not rescue the sign

Finite windows, frequency rings, and spatial pooling prevent exact
factorization when \(K\) varies within the pool, but the residual has no safe
sign. For the two-mode vectors

\[
A=(1,1),\qquad B=(1,-1),
\]

the normalized correlation is zero. A common mode gain \(K=(2,1)\) changes it
to

\[
\frac{4-1}{4+1}=0.6.
\]

A common filter can therefore raise a pooled correlation merely by reweighting
modes. Windowing, boundaries, clipping, tone curves, and adaptive sharpening
add more uncontrolled terms, not a proof of non-increase. The committed
ring-level analysis reaches the same result
(`docs/research/M-FRC-VIABILITY.md:261-330`).

### 2.2 Pre-noise optics are a different estimand

If transfer occurs before fresh downstream noise,

\[
A=HS+N_A,\qquad B=HS+N_B,
\]

then

\[
\rho_H=\frac{|H|^2P_S}{|H|^2P_S+P_N},
\]

which falls under optical attenuation and rises under genuine pre-sensor
improvement. A later common USM still cancels. This is why repeat FRC can
measure acquisition-information bandwidth. It does **not** rescue a
delivered-detail statistic: a renderer can low-pass both completed outputs and
leave ideal coherence unchanged. M-FRC records this intervention-point
distinction directly (`docs/research/M-FRC-VIABILITY.md:369-430`), and M135
states that a separate transfer veto is still required
(`docs/research/M135-detail-instrument.md:498-533`).

The hypothesis's proposed mechanism is therefore false. USM amplifies each
repeat's independent noise, but it amplifies the shared signal by the same
per-mode transfer. The cross-repeat correlation does not fall. A repeats-only
observer cannot tell whether \(K\) was output sharpening, output blur, or part
of a redefined shared scene/noise spectrum.

## 3. Available repeat data

M189 enumerated filenames with `Get-ChildItem -Force` and read metadata only on
already-developed non-holdout stacks. M189 decoded no ARW pixels, read no new
quality outcome, and did not access
`D:\personal\macro\requests\7-aperture-pairs\`.

| Directory or pair | Exact frames present | What it supplies | Why it is not an admissible new route |
|---|---:|---|---|
| `D:\personal\macro\requests\12-bee-iso-var-no-bracket-32-repeat-diff-light` | **576 ARWs** | Two passes × nine ISOs × 32 fixed-focus repeats. The designated ISO-100 groups are `DSC00328.ARW`–`DSC00359.ARW` and `DSC00584.ARW`–`DSC00615.ARW`, 32 each, 1.6 s, f/5.6 (`docs/proposals/2026-09-sota-scorecard.md:634`; full manifest at `docs/research/M-PHASE0-SPLIT2.md:19-35`). | **QUALITY holdout**, not development material. It is fixed-focus rather than two full bracket lineages. The bright geometry gate passed, but the second-light gate failed `0.107703 > 0.10`; no real FRC was retained (`docs/research/M-PHASE0-SPLIT2.md:1-14,65-87`). |
| `D:\personal\macro\112MSDCF` + `D:\personal\macro\113MSDCF` | **79 + 63 ARWs** | Same-subject replicate and same per-frame focus step (`docs/research/M12-shrinkage-measured.md:710-718`). | Not matched exposure: both ISO 500/f/11/200 mm, but 1/60 s versus 1/30 s (`docs/research/M46-detail-metric-measured.md:89-111`). This is also the pair on which the independent-repeat decorrelation prediction was already refuted (`docs/research/M46-detail-metric-measured.md:129-152`). |
| `D:\personal\macro\bee-2-cpl` + `D:\personal\macro\bee-3-cpl` | **299 + 299 ARWs** | Matched content, subject, start distance, aperture, and frame count (`docs/captures-needed.md:2166-2173,2193-2198`); first-frame NCC is `0.9562` (`docs/research/M63-bimodality.md:1947`). | ISO 400 versus ISO 100, so not matched acquisition noise. No disjoint A/B calibration lineage exists for archive-only scoring. |
| `D:\personal\macro\wrapped-text-1` + `D:\personal\macro\wrapped-text-2` | **130 + 120 ARWs** | Two nominally related text captures. | Not a repeat: first-frame NCC is `0.3834`; the committed ruling calls it a re-framing, not a re-capture (`docs/research/M63-bimodality.md:1947-1948`). |
| `D:\personal\macro\coffee-bubbles` | **19 ARWs** | Fixed focus at 0.2841 m. | Real bubble motion lowers first-to-last agreement to `0.947`; it is only a soft alignment null (`docs/captures-needed.md:1786-1791`). |
| `D:\personal\macro\requests\10-paper-iso-var` and `requests\6-11-extended-dark-frames` | **110 + 506 ARWs** | Independent flat/noise and dark/fixed-pattern controls (`docs/proposals/2026-09-sota-scorecard.md:635-636`). | No positive scene-detail arm. |

The archive therefore contains repeat material, but no unused, matched,
fully-calibrated pair of complete focus-stack lineages that could make this
route claim-bearing. The later route ledger reaches the same practical
conclusion: archive-only same-resolution reference is closed because the
required matched calibration and A/B/V acquisition lineage cannot be
reconstructed (`docs/research/M180-detail-route.md:106-112`).

More frames would not repair the structural result. Averaging temporal noise
can make stable DSNU/PRNU a *larger* fraction of repeat correlation; the
committed model gives the mechanism and expected floors
(`docs/research/M-FRC-VIABILITY.md:461-538`).

## 4. Decision

No candidate is proposed and no `experiments/M189-repeat-referenced-detail/`
harness is created. The prerequisite analytical discrimination failed:

- post-noise USM does not decorrelate normalized repeat structure;
- an amplitude-sensitive repeat statistic rewards it;
- a normalized statistic cannot see common output blur;
- finite pooling replaces exact invariance with an unsigned, gameable residual;
  and
- existing repeats add fixed-pattern and calibration confounds rather than an
  identifying observation.

A pre-noise repeat-information coordinate remains possible, but it needs a
separate delivered-transfer witness and disjoint calibration. That is the
already-owned M135 route, not an independent repeats-only solution. No owner
capture request is justified for M189 because capture cannot repair this
identifiability failure.
