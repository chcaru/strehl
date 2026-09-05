# M178 — M12-S / M11 plan-precedence adjudication

**VERDICT: `UNRATIFIED_ADDITION`.**

The governing proposal does **not** make a formal M12-S result conditional on
M11 passing. It requires warm memory `<=6 GiB`, bytes invariant to worker count,
and a flat N-mod-4 cost profile as coequal systems bars
(`docs/proposals/2026-08-sota-path.md:1973-1985`). The strongest plan-derived
coupling runs in the other direction: worker-invariant bytes make the
production-speed path legitimate. The scorecard later added the reverse rule
that M12-S must wait for all of M11
(`docs/proposals/2026-09-sota-scorecard.md:797,1995-2001`).

Under the stated precedence rule, M12-S is therefore adjudicable without a
licence. Its measured byte property is **FAIL**, and M12 overall is **FAIL**
today.

## 1. Decisive source reading

The plan's own registered systems targets are:

> “memory ≤6 GiB warm; bytes invariant to worker count (D9a); the staircase
> gone (per-frame cost flat in N mod 4).”

(`docs/proposals/2026-08-sota-path.md:1973-1985`)

Nothing in that list conditions byte invariance on comparator throughput. The
plan later parses the scorecard readiness table and says:

> “Two axes -- M8 and M12 -- are measurable today.”

(`docs/proposals/2026-08-sota-path.md:2251-2263`)

That amendment post-dates the scorecard's M11/M12 coupling and still assigns no
licence blocker to M12. The scorecard itself also classifies M12 as `(e)` and
says its hashes and process-tree memory need “no detail, comparator or holdout”
(`docs/proposals/2026-09-sota-scorecard.md:809-835`).

Against that, the scorecard says:

> “M12-S requires exactly one distinct hash across all five worker counts at
> every N, and the 16-worker output must simultaneously pass M11.”

(`docs/proposals/2026-09-sota-scorecard.md:1995-2001`)

Its own attribution sentence claims proposal authority for “the M12 6-GiB bar,
and byte invariance,” but does **not** include the M11 conjunct; it separately
labels only the ratio and N-mod-4 numeric thresholds as scorecard additions
(`docs/proposals/2026-09-sota-scorecard.md:799-804,1995-2000`). The reverse
dependency is thus an added cross-axis prerequisite left unlabelled at its
operative clause.

There is a second, independent logic problem with M139's disposition. The
scorecard words M11 as a **success conjunct**, not as an eligibility or
measurement-validity precondition (`docs/proposals/2026-09-sota-scorecard.md:1995-2001`).
Once the byte term is measured false, the conjunction is false regardless of
an unknown M11 term. M139's own frozen harness accordingly records mechanical
M12 `FAIL`; `BLOCKED-BY-LICENCE` arose only from a later orchestrator reporting
directive (`docs/research/M139-m12-campaign.md:11-18,273-277`).

## 2. Disconfirming evidence checked

### 2.1 Does the plan make the axes a conjunctive product?

The plan's printable end-state sentence is conjunctive at the **overall SOTA
claim** level: detail, noise, invention, veil, trust/depth, and CPU speed appear
in one sentence (`docs/proposals/2026-08-sota-path.md:189-197`). That does not
say an individual axis lacks a value until every other axis passes.

The only plan section expressly titled “the blockers are conjunctive” concerns
readiness codes `(a)` through `(d)` and execution scheduling, not cross-axis
metric validity. It immediately identifies M8 and M12 as measurable with no
blocker cleared (`docs/proposals/2026-08-sota-path.md:2251-2278`). This is
disconfirming, not supporting, evidence for an M11 prerequisite.

### 2.2 Do D5 or D9 make invariance meaningful only at speed?

D5 says determinism has kept parallelism locked and calls D9 the hinge into the
offensive speed program (`docs/proposals/2026-08-sota-path.md:1648-1668`).
D9 then specifies a fixed reduction lattice so bytes become worker-invariant
and `available_parallelism()` becomes usable, refunding the measured `1.29x`
worker-cap cost (`docs/proposals/2026-08-sota-path.md:1747-1764`).

That is a real coupling, but its direction is **invariance enables a valid fast
arm**. It supports requiring the timed M11 output to match the slower worker
outputs. It does not support withholding M12-S until M11's commercial
comparator, hybrid, cold-start, and live-latency limbs all pass. The plan's
standing constraints likewise list the D5 wall-clock budget and worker-invariant
freeze rows side by side rather than making either one's measurement conditional
on the other's verdict (`docs/proposals/2026-08-sota-path.md:2104-2113`).

### 2.3 Is 16 workers meaningful only if 16 workers is performant?

The plan's 16-core section says `8→16` had **never been measured** and calls for
an idle-box `1→32` sweep. It describes the decompositions as byte-safe once D9a
lands (`docs/proposals/2026-08-sota-path.md:1908-1930`). It does not state that a
16-worker hash is valid only after a throughput verdict. D15 does not single out
16 workers at all when it registers the memory and byte bars
(`docs/proposals/2026-08-sota-path.md:1973-1985`).

The narrow anti-cheat rule is legitimate: M11's claimed production-speed output
must be the same product across workers. The reverse all-M11 prerequisite on
M12-S is not.

### 2.4 Did the owner ratify the scorecard wholesale?

No documentary ratification was found. `docs/OWNER-ACTIONS.md` says a full
ratification instrument “is being prepared” and that the owner must rule on the
identified additions (`docs/OWNER-ACTIONS.md:480-483`). It also says silence
will not be treated as ratification (`docs/OWNER-ACTIONS.md:1707-1720`).

The tracked owner-question/answer log,
`docs/research/OWNER-QUESTIONS.md`, last changed on 2026-08-23, before the
scorecard and the conjunct existed, and contains no `scorecard` occurrence
(`experiments/M178-m12s-adjudication/audit.json:174-187`). An exact search of
tracked Markdown found no statement that the owner ratified, approved, or
accepted the scorecard wholesale (`experiments/M178-m12s-adjudication/audit.json:174-187`).
Git author identity alone is not contrary documentary evidence of owner
ratification; both introducing commits carry a Copilot co-author trailer
(`experiments/M178-m12s-adjudication/audit.json:99-126`).

### 2.5 Did an earlier plan revision or another proposal contain it?

No. A whitespace-collapsed search of all ten Git revisions of
`2026-08-sota-path.md` found zero occurrences of `M12-S`, `must simultaneously
pass M11`, or `while 16 workers passes M11`
(`experiments/M178-m12s-adjudication/audit.json:191-195`). Across current
`docs/proposals/*.md`, both exact conjunct phrasings occur only in the scorecard
(`experiments/M178-m12s-adjudication/audit.json:2-13`).

The later next-build proposal points the other way: it says exact cross-worker
hashes involve “no detail statistic, comparator, new capture, or holdout
reading,” and defines the formal M12 gate entirely from fixed-worker and
cross-worker hashes (`docs/proposals/2026-09-next-build-path.md:100-123`).

## 3. Git provenance

`git log -S"must simultaneously pass M11"` identifies:

- **Commit:** `986c46535fc082395831724f1d45c33a1d974390`
- **Date:** `2026-09-02T23:32:20-07:00`
- **Message:** `Tighten scorecard anti-cheat constraints`

That commit introduced the joint M11/M12 row and changed M12 from plain
cross-worker byte identity to identity “while the 16-worker run passes M11”
(`docs/proposals/2026-09-sota-scorecard.md@986c465:79,296-303,818-821`). Its
message and the scorecard revision note describe the change as adding joint
anti-cheat constraints (`docs/proposals/2026-09-sota-scorecard.md:90-93`). It
did **not** claim proposal authority for the reverse dependency: in the same
patch, the authority sentence names only the M12 6-GiB bar and byte invariance
(`docs/proposals/2026-09-sota-scorecard.md@986c465:299-303`).

`git log -S"while 16 workers passes M11"` identifies the later wording commit:

- **Commit:** `dd957dd5f8ef36af99065db5aa52065171556adf`
- **Date:** `2026-09-03T02:27:41-07:00`
- **Message:** `scorecard: separate M12 determinism from scaling invariance`

It split M12-D from M12-S and produced the current row and metric-card wording
(`docs/proposals/2026-09-sota-scorecard.md@dd957dd:390-397,974-978`). It retained
the same limited authority sentence and made no owner-ratification claim. The
pickaxe outputs and full commit metadata are frozen in
`experiments/M178-m12s-adjudication/audit.json:95-127`.

## 4. Relationship to M169

This is a **separate mechanism** from M169's universal comparator conjunction,
but it is **not a new tenth unratified instance**. M169 already ruled that only
the forward M11 identity guard is plan-authored and that the reverse dependency
is a separate unratified addition (`docs/research/M169-ratification-stakes.md:295-311`).
Its complete census records this exact rule as **R9 — new**, one of the seven
additional families inside the report's total of nine
(`docs/research/M169-ratification-stakes.md:313-344`).

Thus M169's §4.1 direct paid-arm count correctly omitted M12 from the seven axes
reached by the universal comparator rule. M12 is reached by distinct R9, which
M169's full §6 census already counted. The present ruling confirms M169; it does
not further weaken the licence rationale beyond M169's complete census.

## 5. Consequent M12 disposition under the plan

The completed machine record and M139 report agree on the measured properties:

- **M12-D: PASS.** All 15 fixed-worker cells have six accepted repetitions and
  one TIFF plus one pixel hash (`docs/research/M139-m12-campaign.md:217-238`).
- **M12-S byte invariance: FAIL.** N=`33`, `105`, and `299` each produced five
  distinct TIFF hashes and five distinct pixel hashes across workers
  `1/2/4/8/16` (`docs/research/M139-m12-campaign.md:240-249`).
- **Warm peak memory: FAIL.** Maximum sampled process-tree private commit was
  `35.65724182128906 GiB`; the corresponding Job Object peak was
  `35.65745162963867 GiB`, against `6 GiB`
  (`docs/research/M139-m12-campaign.md:279-285`). The sampled value is
  `5.9428736369x` the ceiling
  (`experiments/M178-m12s-adjudication/audit.json:151-168`).
- **N-mod-4: FAIL under the registered operationalization.** The spread was
  `7.618677%` against `2%`
  (`docs/research/M139-m12-campaign.md:307-320`). The plan's word “flat” has no
  independent numeric tolerance; that does not affect the overall ruling
  because the exact memory and byte-invariance bars already fail.
- The `299/33` ratio remains
  `UNMEASURED_SAMPLING_COVERAGE`; it is a separately labelled scorecard numeric
  addition and is unnecessary to this disposition
  (`docs/research/M139-m12-campaign.md:287-305`;
  `docs/proposals/2026-09-sota-scorecard.md:1995-1997`).

**Plan-faithful result: M12-D PASS; M12-S FAIL; M12 overall FAIL.** No Zerene
licence can change any of the three measured hard failures. The frozen campaign
harness already records the mechanical overall result as `FAIL` from absolute
memory, cross-worker invariance, and N-mod-4 spread
(`docs/research/M139-m12-campaign.md:273-277`;
`experiments/m12-scorecard/out/campaign-8009447e-m139/closeout.json:806-823`).

This is an M12 disclosure-axis verdict. It does not by itself adjudicate M11 or
the complete owner SOTA claim.

## 6. Verified versus assumed

**VERIFIED:** all quoted current source lines; all ten historical plan blobs;
current-proposal phrase uniqueness; both pickaxe histories and commit metadata;
M169's census placement; the M139 closeout JSON's campaign-complete flag, hash
counts, memory maximum, modulo spread, and mechanical verdict. The reproducible
audit is `experiments/M178-m12s-adjudication/audit.py`, whose output is
`audit.json`.

**ASSUMED:** M139's accepted-run admission, host-validity, process-monitoring,
and artifact-integrity checks are sound. I did not rerun 294 attempts or open
any capture. The decision-relevant values were cross-checked against the
committed machine closeout rather than accepted from prose alone
(`experiments/m12-scorecard/out/campaign-8009447e-m139/closeout.json:1-170,780-923`).

**COULD NOT DETERMINE:** whether any unrecorded, off-repository owner
communication purported to ratify the scorecard. No repository evidence of
such ratification exists, and the maintained owner document says the ruling is
still pending (`docs/OWNER-ACTIONS.md:480-483,1707-1720`).

## 7. Exact replacement text routed to the orchestrator

No source outside M178 ownership was edited.

### Scorecard row at `docs/proposals/2026-09-sota-scorecard.md:797`

```text
| M12 | Memory, determinism, and scaling invariance | Warm peak process-tree memory `<=6 GiB`; 299/33-frame peak ratio `<=1.10`; every fixed-worker repeat is byte-identical and the outputs at 1/2/4/8/16 workers are mutually byte-identical; N-mod-4 per-frame spread `<=2%`. |
```

### M12 success text at `docs/proposals/2026-09-sota-scorecard.md:1997-2001`

```text
`peak_N299/peak_N33<=1.10` and N-mod-4 per-frame spread `<=2%`. M12-D requires
exactly one distinct hash in every fixed-worker six-run cell. M12-S requires exactly
one distinct hash across all five worker counts at every N. A product may pass M12-D
while failing M12-S; the two verdicts must never be conflated.
```

The forward anti-cheat remains at
`docs/proposals/2026-09-sota-scorecard.md:337`: the M11 production-speed output
must match the worker ladder.

### M139 header at `docs/research/M139-m12-campaign.md:3-18`

```text
**Status:** the registered campaign is complete. **M12-D PASS. M12-S FAIL.
M12 overall FAIL.** The absolute-memory bar is **FAIL**, the observed
N=299/N=33 memory ratio misses its numeric bar but is formally
**UNMEASURED_SAMPLING_COVERAGE**, and the N-mod-4 timing bar is **FAIL**.
**HOST RELEASED.**

The frozen harness's conjunctive adjudication yields **M12 FAIL** from the
measured hard failures. The scorecard's reverse dependency making M12-S wait
for all of M11 is an unratified addition not present in the governing proposal;
under plan precedence it does not withhold the measured M12-S result.
```

### M139 adjudication at `docs/research/M139-m12-campaign.md:251-277`

```text
The scorecard additionally says that the 16-worker output must pass all of M11.
That reverse dependency is an unratified scorecard addition, not a validity
precondition in the governing proposal. The plan-faithful forward rule remains:
any production-speed M11 output must be byte-identical across worker counts.

Accordingly:

- measured and formal M12-S status: **FAIL**;
- overall M12 verdict: **FAIL**.

A future licensed M11 run cannot change the cross-worker byte failure at this
measured commit. The frozen harness's generic conjunctive rule independently
records M12 **FAIL** because cross-worker invariance, absolute memory, and
N-mod-4 timing are hard failures.
```

### Stale owner-facing M139 bullets at `docs/OWNER-ACTIONS.md:1473-1479`

```text
> > - **Absolute memory: FAIL.** The bar is `6 GiB`. The maximum accepted
> >   sampled process-tree peak was `35.65724182128906 GiB`, with a Job
> >   Object peak of `35.65745162963867 GiB` — **`5.94x` over the ceiling.**
> > - **Cross-worker byte invariance: FAIL.** Every registered N (`33`, `105`,
> >   and `299`) produced five distinct TIFF hashes and five distinct pixel
> >   hashes across workers `1/2/4/8/16`. Same-worker six-run cells each
> >   retained one TIFF hash and one pixel hash.
```
