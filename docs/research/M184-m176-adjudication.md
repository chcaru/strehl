**Q3/Q4: APPLY only the replacements below. Core corrections are verified; M176's exact Route 1 omits uncertified D9 lineages, and Route 2's "Landing it repairs" is unproven before an N7-qualified certificate.**

Committed scorecard §M8 defines M8-R at the linear pre-merge `f32` gather. In committed source `76b3d9cc`, `sample_checked` fills `scratch.dst`; the committed trace injector inserts immediately there, before inverse gain/rounding. Only afterward does `BandWorker` call `add_frame_with_gain`, worker parts `absorb`, and `finish` produce output. Thus the Catmull-Rom gather precedes the final fold. M165's committed verifier hashes file bytes, TIFF payload, decoded `u16`, and merge-facing input planes; its optional one-frame `finish` is checked only for finite geometry, not byte identity. The original four-item sentence is: common-input **wrong**; dominance manifest **wrong** (blocked record, no candidate render); shipping freeze **right only at recorded W=4**; V-MOTE **right that a worker condition is needed, but its unconditional causal bound is unprovable** because W was absent.

D9 code separates worker-independent canonical chunks from execution threads and absorbs in fixed order. The scorecard requires both complete-file and canonical-pixel identity over W=1/2/4/8/16. Therefore landing code alone cannot retire a pin; proof is executable-lineage-specific and cannot alter historical bytes. Both exact wrapped anchors below occur once in current `docs/STATUS.md` (blob `5e505452`).

## Q1 — withdrawal

HEAD `5270e0ee` asserted `REDUCTION_ORDER`: W changed chunking `[19]` versus `[10,9]`, changing `f32` reduction order; affected W1/W2 moved **3,430 / 8,241,504 pixels = 0.041619%**, at most 1 DN16; fixed W1/W2 were byte-identical because both used `[5,5,5,4]`. The uncommitted rewrite (clean blobs report `8e70eab7`, audit `9381307d`) contains none of those findings and says they were "dropped in full." It supplies no better reproduction/localization evidence and does not call them false. This is **merely dropped**, neither retracted nor superseded. Conservative withdrawal is legitimate; deleting the prior wording rather than preserving a retraction is a defect.

## Q2 — accounting

Sound. The 22 table/JSON rows are exactly `6+8+2+2+2+2`; IDs are unique and each has one primary outcome. Candidate paths partition disjointly as `49 mapped + 100 generic-pruned + 3 named-pruned = 152`; all mappings target counted rows. The five outside-lane nonclaim rows are separate. No candidate is skipped into a pass. `verify.py` returned 15/15; 11 tests passed; commissioning killed 15/15 substantive mutations and preserved its inert arm.

## Q5 — N7

Complementary, not identical: M176 specifies the positive end-to-end certificate; N7 additionally requires that same gate to fail on the unrepaired binary. A never-red gate cannot satisfy an accepted certificate under N7.

## Q6 — scorecard insertion

Safe. `### 1.1 Freeze before outputs` and the exact two-line `RUN-MANIFEST.json` bullet each occur once. The insertion operationalizes the existing pre-output worker-count freeze and registered worker treatment; it changes no numeric or success bar and contradicts none found.

## Route 1 — anchor (exactly once)

```text
**Every hash pin in this repository is therefore
conditioned on a worker count that was, in most cases, never recorded** — the
common-input byte-identity check, the dominance manifest, the shipping-default
byte-freeze, the dust-correction "a wrong map renders byte-identical to OFF"
downside bound.
```

**Replacement:**

**Only Pyramid final-render byte/hash claims from pre-D9 executables—or from D9 executables not yet covered by an accepted end-to-end certificate—require a common-worker condition.** M8-R and M165 stop before that boundary, M8-O v1.5 is unmeasured, and M164 has no candidate render. The shipping Scale + Catmull-Rom freeze remains a recorded W=4 witness; V-MOTE's WRONGMAP/OFF identity is conditional because its worker count was not recorded.

## Route 2 — anchor (exactly once)

```text
Landing it
repairs one of M12's two bars and simultaneously makes every hash pin in the
repository unconditional.
```

**Replacement:**

Landing D9 does not by itself make any hash pin unconditional. The same-worker pin retires only for a frozen executable lineage proven to contain D9 after an accepted end-to-end W=1/2/4/8/16 complete-file and canonical-pixel identity certificate satisfying N7. Historical unpinned hashes are not repaired retroactively, and non-render hashes were never conditioned on D9.

## Unverified

The withdrawn render measurements were not rerun; their truth is unverified, not refuted. No accepted complete post-D9 M12 certificate was found. The two M176 working-tree blobs are uncommitted dependencies and may change.
