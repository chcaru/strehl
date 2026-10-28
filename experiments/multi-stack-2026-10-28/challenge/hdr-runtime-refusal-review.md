# Independent analysis of candidate-5 HDR refusal

VERIFIED by read-only inspection of outputs/multi-stack/slide-hdr-5 and its
run receipt. No RAW pixels, new geometry solve, render, threshold change or
product edit was performed in this review. The pipeline correctly withheld
master.tiff and completed.json after require_gains refused the session.

## Precise cause

The chosen anchor is pass 2, the 6-second stack. Pass 0 (1 second) was not
photometrically tested: its pairs array is empty. Alignment supplied 66 nearest
scale proposals between passes 0 and 2, of which 59 were mutual nearest. Every
mutual pair exceeded the existing quarter-step proposal bar, so the calibrator
nominated zero pairs and consequently had zero compatible measured pairs.

The permitted log-scale gap was 0.0000784064548627332, defined as 0.25 times the
smaller of the two median within-pass scale steps. Observed mutual gaps ranged
from 0.00008639696515377882 to 0.00012750724607876567, with median
0.00011087754732545026. In units of that smaller step these are 0.27548 to 0.40656,
median 0.35353. The proposals cover the entire 1-second rank range, so this is not
missing global placement or a lack of overlapping track length. It is a focus
sampling offset relative to the fixed geometric proposal policy.

All 186 frames were placed from 1,396 native edges in one component with 1,211
anchor-component cycles. All candidate validated_same_focus flags remain false.
Scale remains a proposal coordinate, not optical focus truth. The failure is
therefore insufficient nomination evidence under the current conservative
contract; it is NOT a measured 1-second lighting, clipping or texture failure.
No arithmetic, mask or index bug was found in this path. The prior nine-source
broad-patch preflight cannot supply the missing same-focus certificate.

## What passed

Pass 1 (2.5 seconds) had 65 nearest proposals, 61 mutual, and 48 meeting the
quarter-step screen. The deterministic bounded selection sampled nine pairs,
and all nine passed both photometric and textured compatibility checks.

- Corrected gain into the 6-second anchor units: 2.5338838, versus nominal 2.4.
- Additional exposure correction: +0.0783158 EV.
- Across-pair correction variation: 0.93951225%, below the 2% bar.
- Accepted rank span: 75% of the anchor track and 80% of the source track.
- Final pass-wide held-out residual: median 0.37964582%, 95th percentile
  1.1830122%, maximum 2.0793319%, over 744 color/patch observations.

Every pair used 39-43 of the fixed 48 patches. The only patch exclusion was
original clipping, affecting 5-9 whole patches per pair. There were no recorded
coverage, signal-margin or contradictory-radiometry refusals. Each pair retained
21-23 textured patches. Reported texture residuals are zero AFTER subtraction
of the configured generous noise allowance and flooring; this does not imply
identical pixels or exact focus correspondence. The flat-noise control ensures
flat agreement alone is not admitted as a texture witness.

Pass 2 itself retains anchor gain 1.0. Although pass 1 was individually accepted,
calibrated_gains for the session is None because pass 0 failed. That prevents
partial successful evidence from silently enabling nominal HDR for an untested
pass. No output recovery or photographic-gain claim follows from this run.

## Honest product handling

Aligned Layers is the correct current remedy for the full three-pass input: it
preserves all captures and makes the lack of calibrated fusion explicit. A
separate two-pass 2.5-second plus 6-second HDR session is also a concrete useful
next validation candidate: those passes already supplied accepted radiometric
and textured evidence, and the sampled 2.5-second originals were unclipped.
A changed session still needs its own bound geometry/calibration execution;
this review does not assume the new run succeeds or authorize one.

The refusal text can be more precise without changing any gate: distinguish
"no mutual scale proposals meet the quarter-step screen; no photometric pairs
were sampled" from "sampled pairs contradicted the scalar model." Reporting
proposal, nominated, sampled and accepted counts would make the current reason
actionable. Purpose-taken exposure passes at matching optical focus positions
would address the missing evidence; widening the quarter-step bar based on this
capture would be threshold tuning and is not recommended here.

## Exact run and provenance

Root ran from C:/Users/chris/.codex/worktrees/multi-stack/strehl:

    outputs/multi-stack/candidate-5/strehl.exe session stack outputs/multi-stack/manifests/slide-hdr.json --out-dir outputs/multi-stack/slide-hdr-5 --cache outputs/multi-stack/hdr-source-cache --threads 16 --memory-limit-gib 16

Executable SHA256:
44b95bf12b9013ae564e85fde2b390a3f778de8bb53fd4acfd1cf3f93f45ce60.
Exit 1 was an intentional evidence refusal. Elapsed time was 198.986 s, including
189.790 s of geometry. There were zero source decodes and 370 disk-cache hits.
Peak sampled process private memory was 8,270,196,736 bytes. The run explicitly
records concurrent repeat rendering/build activity and is not an isolated
calibration performance benchmark. Calibration reported 200,024,320 numerical
workspace bytes plus 443,440 retained-report bytes, separately from the original
source cache and alignment phase.

The machine-readable read-only audit is
outputs/multi-stack/slide-hdr-5/independent-refusal-analysis.json. It binds the
actual photometry/alignment hashes, command, build identity and withheld-output
checks. The observed numeric evidence supports the stated refusal and the
2.5-second/6-second validation opportunity; it does not establish HDR recovery.
