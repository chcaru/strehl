# M172: M12 scoreability after D9 and bounded memory

**Audit cut:** 2026-09-04 22:50 PDT.

**Strict answer:** M12 is resource-reachable without blocker `(a)` or `(d)`.
Every required capture exists, and none of its terms asks whether an image is
sharper or better than a comparator. It is not, however, a current PASS. The
admitted result remains the pre-repair M12 FAIL, while a complete, single-pin
post-repair campaign is still running. A pass is plausible, not established.

## 1. Full conjunctive bar

The complete one-line bar is verbatim at
`docs/proposals/2026-09-sota-scorecard.md:817`:

> Warm peak process-tree memory `<=6 GiB`; 299/33-frame peak ratio `<=1.10`;
> every fixed-worker repeat is byte-identical and the outputs at 1/2/4/8/16
> workers are mutually byte-identical; N-mod-4 per-frame spread `<=2%`.

The title has three named components, but the operative success text at
`:2015-2020` contains five conjuncts:

1. absolute warm process-tree peak `<=6 GiB`;
2. `peak_N299/peak_N33<=1.10`;
3. M12-D: one TIFF hash and one decoded-pixel hash in every six-repeat
   fixed-worker cell;
4. M12-S: one TIFF hash and one decoded-pixel hash across all five workers at
   every registered N;
5. N-mod-4 per-frame spread `<=2%`.

All five must be measured and pass. Passing the three hash/memory headlines
while leaving the ratio or modulo term unread is not an M12 pass.

## 2. No hidden detail or comparator term

No M12 term reduces to "is this sharper?" or "is this better than product X?"
The values are process-tree bytes, exact output hashes, and elapsed-time
scaling. Exact identity says nothing about image quality; it only says that
worker topology did not change the product bytes.

Scorecard v1.11 removed the reverse dependency that made M12-S wait for M11
(`docs/proposals/2026-09-sota-scorecard.md:11-26`). The remaining M11 language
at `:1984-1989` is forward anti-cheat: an M11 speed claim must use a
cross-worker-identical product. It does not make comparator qualification a
precondition for reading M12. Therefore blocker `(d)` does not bind M12.
Blocker `(a)` is absent because no detail inference is performed.

## 3. Standing of every term

| Term | Admitted standing | Post-repair evidence | Current conclusion |
|:--|:--|:--|:--|
| Absolute memory | **FAIL** at `35.65745162963867 GiB` on the pre-repair registered campaign | Diagnostic Job peaks are about `2.864 GiB` | Promising but not a formal current-pin matrix pass |
| N299/N33 peak ratio | **UNMEASURED_SAMPLING_COVERAGE**; observed pre-repair maximum about `1.46157` | Single-pin diagnostic `1.000121238` | Promising but not a formal six-repeat all-worker result |
| M12-D determinism | **PASS** on all 15 pre-repair cells | No complete repaired-code matrix yet | Historical PASS cannot certify a changed binary |
| M12-S scaling invariance | **FAIL** with five hashes at every N on pre-repair code | The commissioned negative control fires; repaired N33 is invariant | N105 and N299 complete six-repeat ladders still required |
| N-mod-4 spread | Pre-repair value `0.07618677189815302`, numerically **FAIL** against `0.02`; M139 separately quarantined its host validity | No repaired-code result yet | Unresolved and capable of preventing a pass |

The scorecard's currently admitted row remains **M12 overall FAIL**
(`docs/proposals/2026-09-sota-scorecard.md:851`). The D9 control at
`97e5ad9cd5fdb0f47cdffc7a1c7a9418d6df89a8` repairs the evidentiary defect:
pre-D9 N33 has five worker hashes while post-D9 N33 has one, and the same
contrast exists immediately after `BandMerge::finish`. It does not substitute
for the registered N33/N105/N299 six-repeat campaign.

At this audit cut, M179's live campaign had no generated `summary.json`,
`verdict.json`, or committed report. Its partial rows are not used here as a
verdict.

## 4. What is still missing

**Capture-bound: nothing.** The native inputs already cover N33, N105, N299,
and the N96-N99 prefixes. No protected holdout, new photograph, detail target,
or comparator output is needed.

**Compute-bound:**

- finish one hash-bound binary's complete 133-position protocol: 15 fixed-cell
  warm-ups, 90 fixed-cell scored runs, four modulo warm-ups, and 24 modulo
  scored runs;
- prove all 15 repaired-code M12-D cells and all three repaired-code M12-S
  ladders;
- measure the scored maximum Job peak and the N299/N33 ratio for every worker,
  with the registered process-tree sampling coverage;
- obtain an admissible N96-N99 timing result;
- re-derive the verdict, run the planted controls, and commit the evidence.

The timing item is compute-bound but not automatic. The scorecard still names
an uninterrupted quiet-host run at `:2047-2053`. M139's later protocol analysis
requires either that environment or a commissioned contention-robust witness.
Merely logging host CPU cannot prove that external load did not flatten or
distort a passing spread. A loaded-host result therefore needs the governing
host amendment to be admitted explicitly; otherwise the modulo term remains
unmeasured even if its number is below `0.02`.

## 5. The 3,074,965,504-byte reading

`3,074,965,504 B` is `2.863785 GiB`, leaving
`3,367,485,440 B = 3.136215 GiB` below the `6,442,450,944 B` ceiling. The
number is credible diagnostic evidence, but not a pass:

- the N33 ladder and N299 cell that first supplied it were measured at
  different commits, so they cannot form a memory-scaling result
  (`docs/STATUS.md:7487-7500`);
- it was not the maximum of six scored repetitions across all 15 cells;
- it did not establish the N299/N33 ratio at every worker count.

M182 subsequently put N33/W16 and N299/W16 on the same `a9727581` binary and
measured Job peaks `3,074,424,832 B` and `3,074,797,568 B`, ratio
`1.000121238` (`docs/research/M182-memory-budget.md:114-128`). Those are still
one diagnostic run per N, not the registered matrix.

Making memory formal requires fresh measurements, not a prose promotion:
one pinned binary containing both repairs, six post-warm-up scored repetitions
in every N/worker cell, whole-Job accounting plus passing sample coverage, a
maximum no greater than `6 GiB`, and every N299/N33 worker ratio no greater
than `1.10`. The harness, captures, and commissioned meter exist, so this is
execution and verification work rather than new engineering or owner action.

## 6. Answer

- **Can M12 be scored without `(a)` or `(d)`? Yes.** It is a systems-only axis
  and has all required inputs.
- **Can existing recorded evidence award a repaired-code PASS today? No.** The
  full current-pin matrix and modulo result do not yet exist.
- **Can the current implementation plausibly pass once computed? Yes, but not
  by assumption.** Memory and N33 invariance have strong diagnostic margins;
  N105/N299 invariance, full-matrix memory, and especially N-mod-4 timing remain
  capable of returning a genuine FAIL.
