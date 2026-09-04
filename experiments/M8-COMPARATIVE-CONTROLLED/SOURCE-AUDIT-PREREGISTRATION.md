# `focus-stack` source audit and crash-diagnostic preregistration

Frozen before reading implementation bodies, interpreting new source evidence,
or running any new comparator diagnostic. The prior full-size control failure
in commit `4940581b` is an already-recorded fact, not a new outcome.

## Questions and decision rules

The audit answers, in this order:

1. Does `--no-align` omit alignment tasks/warps, schedule identity work, or
   merely suppress some transform classes?
2. For 92 inputs, what creates the 93 progress labels beginning with `Align`,
   and what code path owns the apparent extra label?
3. If an alignment task receives exact identity, does it bypass resampling, or
   invoke an interpolator anyway? If it invokes Catmull-Rom at integer phase,
   verify from weights/code that the result is exact identity with zero
   negative mass; do not treat the task name itself as disqualifying.
4. Is depth-map construction load-bearing for the selected merge, or can an
   existing documented flag omit it while retaining a merged image?

An identity contract passes the source audit only if every input reaches the
merge either without a warp or through a code path proven to use exact
integer-identity sampling. A default-constructed identity object is not enough
if a later content-dependent transform can replace it.

The source audit is stronger than an adjusted-input export for the narrow fact
it directly proves: which operator path the audited build executes. It still
requires binary/source provenance and executable controls. Source readability
does not excuse a crashing full-size control.

## Frozen source selection

The executable remains:

```text
C:\dev\macro\focus-stack\dist\focus-stack.exe
SHA-256 0ABA0CF0936AF8B1CACE2681CA43D49729D253E8ED1F786F2A8960B7974CA45D
```

Audit the clean local repository at:

```text
C:\dev\macro\focus-stack
commit 864ff08862414682e75d58245a1e7f1d25cf3315
origin https://github.com/chcaru/macro.git
```

This local fork is the primary source candidate because it contains the
selected binary and its expanded linear/HDR flags. Establish provenance rather
than assuming that commit produced the executable.

For upstream comparison, inspect public
`PetteriAimonen/focus-stack` at frozen master
`0cd289e224fe24aead5b146faeaa46950775f346`.

Within each tree, start with all tracked `src/*.cc` and `src/*.hh` files
reachable from exact symbols or option strings containing:

```text
no-align, no-transform, align-only, Align, Task_Align,
depthmap, Task_Depthmap, Compose, merge
```

Follow only direct callers, constructors, scheduler/dependency edges,
interpolator calls, and output gates needed to answer the four questions.
Record repository, commit, file, and 1-based line range for every conclusion.
Do not copy or commit third-party source.

## Non-scored diagnostic matrix

All diagnostic inputs are synthetic. They are never evidence about output
quality and are exempt from subject admission. They may diagnose only the
crash and control executability.

The already-failed arm is:

```text
N=92, 3392x2262, byte-identical aperiodic inputs, exact registered invocation
```

Run these new arms in order, stopping once the fault boundary is explained:

| ID | N | dimensions | input relation | purpose |
| --- | ---: | --- | --- | --- |
| `I02-S` | 2 | `256x192` | identical | minimum ordinary stack |
| `I08-S` | 8 | `256x192` | identical | one full merge batch |
| `I92-S` | 92 | `256x192` | identical | separate N from memory/size |
| `V92-S` | 92 | `256x192` | deterministic `+ordinal mod 7` DN offset | test zero-range degeneracy |
| `I02-F` | 2 | `3392x2262` | identical hard links | separate full dimensions from N |

The pixel generator, dimensions, N, relation, executable hash, exact argv,
stdout, stderr, return code, and output existence are retained. No threshold
is fitted. A successful reduced arm does not admit the subject.

If source identifies an existing flag that bypasses an optional depth-map
artifact while preserving the selected merged image, first run it on `I08-S`.
Only if that diagnostic succeeds may a separate preregistration freeze a new
full `N=92`, `3392x2262` identity-control invocation. Do not run the subject in
this task.

## Host-load gate

Before every comparator process, measure five one-second total-CPU samples and
physical memory. The measurement must be no more than ten minutes old.

* Small diagnostics require mean CPU `<= 50%` and available memory `>= 8 GiB`.
* Full-size diagnostics require mean CPU `<= 35%` and available memory
  `>= 24 GiB`.
* Every comparator run remains capped at six threads.

If a gate fails, do not ask another lane to idle. Wait and remeasure.

## Free/open comparator survey

Survey, without running:

* Hugin `align_image_stack` plus `enfuse`;
* CombineZP;
* Fiji/ImageJ stack-focusing plugins;
* this `focus-stack` build/upstream.

For each, report only:

1. **identity:** documented alignment omission or source-proven exact identity;
2. **domain:** lossless linear 16-bit RGB input and output without a mandatory
   display transfer/tone map;
3. **readability:** publicly inspectable merge implementation.

Use `YES`, `CONDITIONAL`, `NO`, or `UNKNOWN`, with one citation per material
claim. A tool is a manufactured-contract candidate only if all three can reach
`YES` after controls. “Free to download” does not imply readable source.

## Zerene conclusion rule

Separate two claims:

* **evidentiary necessity:** Zerene is not logically necessary if a readable
  comparator passes the complete manufactured contract;
* **market relevance/governance:** the current SOTA proposal still names
  licensed Zerene PMax and DMap. Replacing them requires registrar action, and
  comparison with the market-leading tool remains desirable even if its
  black-box contract is weaker.

