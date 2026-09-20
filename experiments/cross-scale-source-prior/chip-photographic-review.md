# Independent complete-chip photographic review

**VISUAL: a useful, limited contact/border improvement on this chip; not a
general-quality pass.** I inspected both complete1617x1075 overviews first,
then all seven fixed unresampled native pairs, before receiving root's visual
verdict. Baseline is left and candidate right in every pair. I did not inspect
all27.8 million pixels individually at100%, select a new ROI, compute a new
quality score, rerender, or change any source/parameter.

The complete candidate separates the upper-left repeated contacts more cleanly
and makes the central rectangular compartment boundaries more compact. This is
visible in the whole scene, not only an attractive isolated crop. The gain is
the reduced broad spread around existing structures and clearer separation of
their interiors/borders; I cannot identify a newly recovered finest trace or
claim that increased contrast is new resolved information.

The colour stipple in the central compartments persists and becomes more
conspicuous in places. Bright cyan/yellow fringes remain around contacts and
rails. The result is neither a broad colour repair nor a noise-clean image.
The large yellow/green/red field structure and the visible scratch network
remain recognizable in the whole views; I see no obvious widespread erasure.
That observation is weaker than a guarantee of true colour/detail retention.

| Fixed native region | Independent observation |
| --- | --- |
| Upper-left contact grid | Clearest local benefit. Contact blocks look better separated, with more compact dark interiors and less broad coloured spread into the gaps. Strong bright green/cyan edges and fine coloured granularity still remain. |
| Rail crossing | Vertical rails and adjoining repeated small contacts have cleaner separation and less diffuse coloured material around their boundaries. Rail paths and nearby scratch traces remain visible. This is not evidence that every colour change is accurate. |
| Upper colour | Small change. Dark component interiors and some edges look slightly more distinct; the same fine patterns and broad gold separator remain. No substantial new feature is resolved here. |
| Central stipple | Compartment walls/gaps look more definite, but red/blue stipple remains and is more contrasty/prominent. I do not count that extra texture prominence as improvement or label all existing colour texture an artifact. |
| Lower array | Repeated cell boundaries and cell positions remain; changes are mostly modest contrast/colour differences. No clear loss of a cell or partition is apparent, and no major benefit is established. |
| Lower colour | The diffuse green spread above the dark components remains. Some internal lines appear more distinct, but this window does not support a general spread-removal claim. The small bright point remains. |
| Surface scratches | The diagonal scratch, upper curved branch, short branches and bright points remain visible with similar geometry. No obvious missing trajectory appears. This is structured surface data, not a calibrated flat-noise control. |

Within these fixed views there is enough contact/border gain to retain this as
an optional-mode research direction. There is no defensible claim that all
genuine colours or lines are preserved everywhere, that the method matches
Helicon B, or that the central stipple has been solved. No new vendor local
comparison was attempted: its registration refusal and different input/colour
pipeline still prevent that inference. The observed benefit does not identify
the vendor's internal mechanism.

**The original rejection is unchanged.** Both ISO generated qualifications are
still false; the rule lost about72% of genuine far/coarse component recovery
and damaged real glint structure. The broad-contact outside-spill positive was
unexercised. This separately authorized photographic result shows that the
same failed general rule can help some real structures; it does not make the
screen pass, establish opaque-scene eligibility, warrant a default, or establish
SOTA. Any further optional-mode work must keep those measured tradeoffs visible.

## Actual comparison and output bindings

MEASURED/VERIFIED from the completed root run and saved receipts:

- Both masters are full6468x4300 RGB16 outputs from all299 original sources,
  with the held crop[141,97,3234,2150], warp/reference149, WB/matrix/tone and
  ordinary optical CA. Complete Current pixels equal the historical baseline
  hash `7df99f8f54339711c189380cca45cd63fd8106a2a196162bf562ecc60fbfd7db`;
  its collapsed-plane hashes also equal the historical full receipt.
- I independently compared all299 active-u16 and beta records with the retained
  phase-packed baseline receipt. Every record matches; all per-source replay,
  input-unchanged and held-state flags are true, and finest weight hashes match.
  Complete held-state/replay checks pass. Those are accumulator/consumer
  invariants, not a proof that final visible fine appearance is unchanged.
- Candidate RGB16 pixels hash to
  `739ccc91c206ad4a6728d3c534fd8cba7dc916f54e521ae4945ecf12accdc996`.
  Both TIFF masters, native whole PNGs, whole overviews and all seven pairs are
  retained. The view receipt confirms common ICC
  `238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b`, fixed
  high-byte conversion, exact unresampled crop halves and no automatic contrast.
- Root's complete process exits0 with terminal job accounting and no cleanup
  errors:400.563s wall,999.25s accumulated CPU,5,470,801,920 bytes peak job
  commitment. These are operational readings, not a performance benchmark.
- Full receipt SHA256:
  `190d045e23d4b59f14c6f2c33722153729aeaec643977fa11b70d4ab961e79cc`.
  Full completion:
  `fc44e5549d72b8160454923ce9e1373b1fcdcca42342475381381e83285710c2`.
  View completion:
  `8a900544f9a494ac7147c56905fa5803c951b0686f8a723ba8f3f45c3f56dbd3`.

Root executed the frozen `chip-run.py full` with chip-build-1/chip-controls-1/
chip-cost-1 into chip-full-1, followed by `finalise` into chip-views-1.
The preserved masters are [Current](chip-full-1/output/baseline.tiff) and
[candidate](chip-full-1/output/candidate.tiff); the complete views are
[Current overview](chip-views-1/baseline-overview.png) and
[candidate overview](chip-views-1/candidate-overview.png). No new execution was
performed by this independent reviewer.
