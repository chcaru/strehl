# Research guide

Start here to find earlier work. Reports keep their historical filenames and
paths; this navigation adds topics and document roles without renumbering facts,
rewriting conclusions or changing experiment authorization.

| Need | Entry point |
| --- | --- |
| Current product behavior and build | [Main README](../../README.md) and [architecture](../ARCHITECTURE.md) |
| Decisions, facts, disciplines and open questions | [SYNTHESIS](SYNTHESIS.md); read complete entries and source columns |
| Reports by topic | [Report index](report-index.md) — includes every report in this directory |
| Experiments and their results/reviews/plans | [Experiment index](experiment-index.md) — includes directories with no top-level notes |
| Historical annotated reading list | [Earlier research index](../agents/research-index.md), with its stale-claim cautions |
| Prior refusals and source-code test names | Existing prior-art command below |
| Milestone identities and owned paths | [Allocation ledger](../agents/milestone-ledger.md) |
| Measurement, review and folding procedure | [Research workflow](../agents/research-workflow.md) |

SYNTHESIS and older reports contain historical proposal/default statements.
They are a decision record, not a current build guide. A report's original
headline can survive a later retraction: read amendments and independent reviews
before using it as evidence. Topic tags and roles are navigation hints, never
execution status, certification or permission to resume an experiment.

## Search across reports and experiments

From the repository root, with Python only (no installation, service or database):

```powershell
python scripts/research.py search blur alignment
python scripts/research.py search coherent pyramid --scene marigold --kind result
python scripts/research.py search M103 --area reports
python scripts/research.py search "noise model" --phrase
python scripts/research.py search outlier robustness --any --limit 20
python scripts/research.py browse --topic noise --kind review
python scripts/research.py topics
```

The default matches **all query words**, regardless of order; `--any` matches
any word and `--phrase` matches the entire phrase across punctuation/line wraps.
Paths and titles rank above headings and capped body repetition. Results show
source paths and matching line numbers so you can read the original context.
Snippets are shortened: they are locators, not a substitute for the full source.
Use `--json` for machine-readable results, `--limit` to show more, `--area
reports` or `--area experiments` to narrow the corpus, and `--scene` for a
capture family. Run `--help` after a command for all filters.

The search reads live source documents each time. Its explicit scope is:

- `docs/research/*.md`, excluding this guide and the two generated indexes;
- `experiments/*.md` and Markdown immediately inside `experiments/*/`;
- experiment directories without immediate Markdown, searchable by name only.

It does not recurse into build trees, output images, RAW files, copied source
snapshots or deeper experiment subdirectories. No match establishes only that
this scope and these filters found nothing. Check other retained paths when the
question requires them; do not infer that no prior work exists.

## Browse by topic

The indexes list each report/experiment once under an inferred primary topic,
with additional topic tags alongside it. Search filters match all inferred tags.
Broad reviews can span several topics; classifications use names and titles,
with curated hints for opaque historical IDs, not an interpretation of every
conclusion in the body.

| Topic | Reports | Experiments |
| --- | --- | --- |
| Alignment and geometry | [Browse](report-index.md#alignment) | [Browse](experiment-index.md#alignment) |
| Merge and reconstruction | [Browse](report-index.md#reconstruction) | [Browse](experiment-index.md#reconstruction) |
| Focus evidence and admission | [Browse](report-index.md#focus) | [Browse](experiment-index.md#focus) |
| Noise and sensor calibration | [Browse](report-index.md#noise) | [Browse](experiment-index.md#noise) |
| Optics and capture design | [Browse](report-index.md#optics) | [Browse](experiment-index.md#optics) |
| RAW, color and development | [Browse](report-index.md#color-raw) | [Browse](experiment-index.md#color-raw) |
| Artifacts and source visibility | [Browse](report-index.md#artifacts) | [Browse](experiment-index.md#artifacts) |
| Detail metrics and ground truth | [Browse](report-index.md#quality) | [Browse](experiment-index.md#quality) |
| Performance and execution | [Browse](report-index.md#systems) | [Browse](experiment-index.md#systems) |
| Architecture and extensions | [Browse](report-index.md#architecture) | [Browse](experiment-index.md#architecture) |
| Comparators and scorecards | [Browse](report-index.md#comparators) | [Browse](experiment-index.md#comparators) |
| Verification and research integrity | [Browse](report-index.md#integrity) | [Browse](experiment-index.md#integrity) |
| Other/uncategorized | [Browse](report-index.md#general) | [Browse](experiment-index.md#general) |

## Starting points in published research

- [Alignment and per-frame placement](M103-halfdrift.md): read the amendments alongside the original headline.
- [The R3 Wiener/deconvolution experiment](M41-r3-kill-measured.md): read the stated refusal and its scope before reopening the approach.
- [Sensor clipping and declared white level](M54-clip-mask-measured.md).
- [Election regularization and the value-admission gate](M65-election-gate-measured.md).

These are reading entry points, not a current product verdict. Use the topic
indexes and matching independent reviews to follow subsequent corrections.
The [dispatch history](../agents/experiment-history.md) preserves prior scopes
and stopping points, including work whose source notes may exist only locally.

## Before new work and when adding notes

Keep the existing mechanical dispatch check, which also searches source-code
test names and surfaces refusal sentences:

```powershell
python experiments/ORCH-drift-check/prior_art.py <subject words>
```

Also use the unified search for experiment notes, then read matching sources
and relevant reviews. Generated navigation is excluded from both searches so
it cannot be mistaken for another corroborating report.

Give new documents a descriptive H1. Keep results, plans and independent reviews
separate and clearly named beside the experiment. In `scripts/research.py`, add
vocabulary to `TOPICS`/`SCENES` or a subject hint in `TOPIC_OVERRIDES` when needed.
Then refresh the navigation:

```powershell
python scripts/research.py catalog
python scripts/research.py catalog --check
```

Catalog generation rewrites only `report-index.md` and `experiment-index.md`.
`--check` is read-only and fails if either index is stale, including when a new
report or experiment has not yet been listed. Existing source documents and
SYNTHESIS numbering remain unchanged.
