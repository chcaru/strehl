# Independent result-check preparation record

Source-only preparation on2026-09-07; no decoder, private instrument, numerical
module or result-check command has been executed. Python's standard-library
`ast.parse` accepted the source bytes. The proposed comparison population and
tolerances are in `independent-quality-result-check-design.md`.

First final-review source pin:
`7187ea826c456966b39454d6d4cb203ee7c75b3725b5b616ab42dd333f608251`.
Design pin:
`ac63bc5b1de13a885826815d23195f4f306cede85a61f925f32f9d8a897d4cbd`.

Static corrections before any execution are retained here:

- Local inspection caught set objects passed to the canonical JSON identity
  helper; schema/source-set comparisons now use explicit set equality.
- Root caught the own-noise-off row contract: it contains bias/MSE/RMSE/site
  fields, not temporal decomposition fields. Those saved fields are checked
  separately; actual variance remains checked through the independent batch
  statistics and reported variance tables.
- Root required numerical coordinate-tie handling only for eight-repeat mean
  images. Individual u16-derived pairs require exact native coordinates.
- The flat wave assertion now occurs before the textured private wave fit.
  Wrapped phase checks use atan2(sin(delta),cos(delta)), including a +/-pi
  periodicity companion within the existing restored-wave check.
- Private control records are appended to the terminal result's live list
  before they can fail. Actual read/scene references likewise survive a later
  exception. There are21 private checks and9 private parser attempts;70 genuine
  TIFF attempts give79 under the96-attempt ceiling. Rejected decoder attempts
  count. The legal green-code mutant must decode its actual changed value/hash.
- Root requested explicit runtime provenance. The result records Python and
  NumPy versions, executable, platform system/machine and the four named
  thread settings, with no full environment or hermetic-runtime claim.

These are static preparation defects/corrections, not measured failures or
successful numerical controls. Root must independently review the held source,
freeze the exact fresh-cache command and inputs in a committed execution release,
then run it. Preserve any first actual refusal without changing the tolerances.

Only this standard-library syntax command has run:

```text
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -c "import ast, pathlib; p=pathlib.Path(r'experiments/m194g-larger-pupil/independent-quality-result-check.py'); ast.parse(p.read_text(encoding='utf-8')); print('AST_ONLY_OK; no target-module import or execution')"
```

It printed `AST_ONLY_OK; no target-module import or execution` and exited0.

## Final individual-error amendment before execution

After the first hold, root found a scope gap: checking paired MSE differences
alone would miss an equal common error in both modes and would not directly
verify the published noise-off RMSE. No scientific execution had occurred.
The authorized amendment now compares all378 flat and486 textured
`individual_errors` rows: noise-off plus the eight seeds, both modes, RGB,
all seven ideal regions and each separate admissible textured endpoint region.
The literal ordered key population is checked both against the saved table and
against the actual independently calculated rows. These computations use the
already loaded arrays and add no TIFF read.

Root also caught an unpowered private uncertainty path: directly supplying
`-.75*d*d` to the SE helper bypassed the actual error calculation. The same
`paired-mse-literal` control now constructs each offset/half-offset image pair,
uses the genuine independent `errors` helper, checks signed bias/MSE/RMSE/site
counts against literals, and derives all eight differences and their uncertainty
from those actual helper returns. The expected formula is only the oracle.
The private population remains21 controls and9 parser attempts; with70 genuine
attempts the complete total remains79.

The mean-repeat decomposition and negative-allowed squared-bias estimate are
also compared from the independently obtained values, explicitly labeled
arithmetic consistency rather than additional independent evidence. Tolerances,
ROIs, seeds, target selection and the execution budget are unchanged.

Final held source:50,432 bytes, SHA256
`6c69efa777efccca740901edac9e633deb9a16f3dbe539d66c4e6337994e8539`.
Final design:8,069 bytes, SHA256
`0a6efc5a3266f4c0b1cd9b3f35ea7927a7106ec5dd3dc6abdc9dcf2878ff1b2e`.
The same standard-library AST-only command above was run on this final source
and again exited0 with the same success line. No module import, decoder,
instrument, numerical helper or actual result-check command has run.
