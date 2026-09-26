# Stock selectivity audit before another quality intervention

VERIFIED read-only audit on2026-09-25. No implementation, build, RAW decode,
new render or quality measurement was performed. Commands below were run.

**Finding:** I found no recorded complete native chip or new marigold comparison
that changes only the existing selection ramp. Recent experiments hold that
default fixed. This is a bounded repository/provenance search, not proof that
such a run never existed elsewhere. A stock-CLI ablation is therefore still a
possible local diagnostic, conditional on the pending actual-source trace.

## Correct the premise first

Current `MergeConfig::exponent_at` caps the ramp at `MAX_EXPONENT=8`. For seven
AC bands, the coarse-to-fine ladder is approximately
`2,2.8,3.92,5.488,7.6832,8,8`; the uncapped finest15.059 is **not consumed**.
The current source explicitly documents this and the actual default ramp1.4.
`--pyramid-sharpen` controls selection weights, not a rendered-image sharpening
filter. Band count and the actual truncated depth must remain fixed.

## What was already tried

- `docs/research/BUILD-BLEND.md`, exponent-ramp discussion: historical visual
  choice compared ramp1.0/1.4/2.0 on80-frame subsamples of couch fibres and a
  flower/fern scene. Ramp1.0 looked softer;1.4 and2.0 were indistinguishable.
  This is an existing photographic rationale, so do not call the ramp arbitrary
  or say it was never visually compared. It predates the current native route
  and the new chip/marigold captures.
- `docs/research/BUILD-HULL.md`§14.5: a fixed2×2 of band count6/7 and ramp1/1.4
  on205-frame flower-bud showed both knobs change hull excursions but neither
  eliminates them. A flat exponent does **not** make weights equal across
  bands; it tests severity, not coefficient-consistent ownership.
- `docs/research/V-GATHER.md`§12: flat exponents1,2,4,8,16 and the historical
  default were run on nine subjects. Its reported ceiling-excess axis moved
  with exponent, but residuals survived flat1. Do not transport that historical
  scalar score as current native quality truth or claim selectivity is the
  complete mechanism.
- `docs/research/BUILD-OUTPUT.md`§12 and
  `experiments/BUILD-RECERT/flatexp.py`:52 complete historical renders compared
  default against flat1 (`--pyramid-exponent 1 --pyramid-sharpen 1`) on26subjects.
  The report rejects a default change because its noise reduction comes with
  structure loss; it also records auto-tone bias and the unmeasured hull side
  of the trade. Preserve that closure. It is not a current native chip test,
  and its scalar structure/noise results alone do not establish which current
  photographic contours are true.
- `docs/research/V-DILUTE.md`: generic increasing-depth dilution and terminal
  base-as-acuity hypotheses are already rejected on their tested paths. No
  exponent sweep, plain-mean rescue or base-weighting retest follows here.

## What the current new-stack evidence actually holds fixed

All11 retained `render-process.json` records containing the new chip or marigold
RAW paths use exponent2 and ramp1.4 and exit0: the September14 chip baseline,
September25 chip-before/chip-fixed pair, and the eight marigold base/rendering
variants. Source-controlled current baseline scripts use the same arguments.
The September25 pipeline audit independently records those settings.

The newer complete chip CA-ordering, twelve-plane, local-placement and
cross-scale-prior experiments alter other stages and retain the normal merge
configuration. Full donor and boundary-wavelet adapters explicitly assert the
same defaults. The periodic wavelet screen changes transform, depth, ramp and
boundaries together; the quality path names that confounding, so it is not a
stock-ramp ablation. The complete current coarse-prior chip comparison has a
limited contact/border benefit but retains stipple and its generated far-detail
failure; new marigold/mineral prior trials were negative. None proves the
default selectivity is photographically optimal for the new captures.

## One possible next action, conditional on the source trace

If the trace identifies source-supported signed hair/contact structure being
lost or reversed in selected AC bands0–5, with the causal contribution residing
in weight concentration rather than the terminal mean, clamp or geometric
misplacement, a single whole-chip **ramp-off** comparison is a reasonable cheap
counterfactual: retain exponent2 and every existing production argument, replace
only `--pyramid-sharpen 1.4` with `--pyramid-sharpen 1.0`. This tests flat2 against
the consumed capped ladder. It is not the rejected historical flat1 recipe.

Use the actual299-source chip, held current map/reference149, native crop
`[133,89,3250,2166]` and6500×4332 output, same corrected executable and route.
Start from the checked `outputs/quality-september25/chip-fixed/render-process.json`
command, put the candidate in a fresh directory, preserve originals and the
complete baseline, and keep automatic tone changes explicitly separate from
local-structure claims. A fixed baseline-tone replay is preferable for fine
comparison if the existing cache/writer path is used. Earlier6468×4300 manual
inset outputs are a different crop and cannot silently substitute as baseline.

Before any claimed gain, inspect both whole outputs and the existing seven
fixed native chip regions. Require actual contact separation/boundary benefit
while retaining scratches, fine tracks, contact interiors and genuine colours.
Smoother colour stipple, weaker contrast, fewer clipped samples or a quieter
texture alone fails; these can be purchased by blur. Do not make a flat-noise
claim from the textured chip. A visible loss closes this fixed arm without a
strength sweep. A benefit would justify one independent marigold transfer with
both real hair depths protected, not a default change.

Do **not** run this ablation as the explanation if the trace instead assigns
the relevant loss to the unchanged coarsest AC band6, terminal base7, a live
clamp, or correspondence failure; flat2 leaves band6 and base7 unchanged and
does not repair geometry. If the frozen profiles are inadequate, report that
null and do not claim this audit found a mechanism. No arm has been rendered or
shown to improve quality by this audit.

## Read-only commands executed

```text
python -I -B experiments/ORCH-drift-check/prior_art.py exponent ramp selectivity sharpen
rg -n 'pyramid-sharpen|sharpen_per_octave|selectivity' <current experiment/report paths>
rg -l --glob '*render-process.json' --glob '!**/out/**' 'uncapped-IC-chip|flower-marigold' experiments outputs
```

The returned render-process command arrays were parsed with PowerShell
`ConvertFrom-Json` and their explicit exponent/ramp/exit fields listed; all11
were2/1.4/0. Current source and the named historical report sections were read.
No image-quality metric or rendering command was run.
