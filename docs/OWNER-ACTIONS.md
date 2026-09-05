# What the program needs from Chris

One page, decision-ready. Everything here is verified at source; citations are
in `docs/STATUS.md` §2.9.28-2.9.52 and the lane reports named below.

Maintained by the orchestrator. Last updated after lane M175.

> # ✅ HOLD LIFTED — go ahead and shoot Ask 2a
>
> **Status as of lanes M166 (commit `db5379b8`) and M164 (commit `ec7fa237`):
> the hold is lifted and Ask 2a is unchanged. Shoot it whenever suits you.**
>
> Yesterday I stopped you because M164 ruled the `2.0x` sampling test necessary
> but not sufficient, and I did not know whether the repair was an analysis
> change or a change to what you must photograph. **The answer is: a change to
> what you must photograph — but it lands on the big scored session, not on the
> two frames.** Two lanes settled it from different directions:
>
> - **The magnification target did not move.** M166 checked whether the new
>   condition pushes the TC0 target off `1.32x` and led with *"TARGET HOLDS AT
>   1.32x."* Your two frames measure the right thing at the right placement.
> - **You do not need to buy a different lens.** M164 asked whether the
>   reference can ever be provably more informative than the scored path when
>   both pass through the same Sony prime, and answered `SHARED OBJECTIVE
>   SUFFICIENT` on the measurable band. That was the outcome that would have
>   cost money, and it did not happen.
>
> **What Ask 2a can and cannot do.** M166 is explicit: the two-frame pair
> *"can establish scale and field only. It cannot establish `I_R/I_S` or
> `|H_R|/|H_S|`."* So passing it confirms the placement and clears the way — it
> does **not** license the scored session. Something else now stands in
> between, and you should know about it before you plan a long evening.
>
> **The scored session grew, and a rehearsal now sits in front of it.** The
> session goes from `891` to `1,215` registered frames: three reference strips
> become four (`+32`), the physical `S_1/S_2` witness adds `164`, and held-out
> calibration adds `128`. Before any of that counts, M166 requires an
> **exact-configuration non-holdout rehearsal** that must pass the new
> condition in every measured cell. M166's zero-frame release gate is explicit:
> *"The owner must not start the `1,092`-frame rehearsal from the current
> repository state."*
>
> **Corrected once, before you shot it — the witness was wrong, not just
> small.** I first told you this session was `1,147` frames, with a `96`-frame
> converter-off witness. M164's frozen witness contract then ruled that `S_1`
> and `S_2` must each be *one complete independently acquired scored-path input
> set*, and a fixed-focus burst is inadmissible when the renderer receives a
> focus stack. So the `96`-frame block could not serve as the witness at all.
> It is replaced by two complete candidate-excluded copies of both registered
> focus-stack budgets — `55 + 55 + 27 + 27 = 164` — which is `+68` frames. In
> M166's words: *"The correction is `+68` frames, so the combined score is
> `1,215`, not `1,147`."* **The `1,147` figure is superseded; ignore
> it wherever you still see it.**
>
> **One thing to know before you shoot that block, because the mistake is
> unrecoverable.** Those `164` witness frames are a *second, separate* set of
> `55 + 55 + 27 + 27` — the scored session already contains a `164`-frame block
> with exactly the same budget. They are not the same frames and cannot be shared:
> M166 requires that *"No `TC0-DOM-*` RAW may appear in a candidate or comparator
> manifest. Equal budgets do not make the files interchangeable."* Using one set
> for both would make the witness identical to what the candidate consumed, which
> voids the whole comparison — and it would not announce itself until the score
> run, long after the sitting was over. **I will label them distinctly on the
> bench sheet so this cannot happen by accident.**
>
> **The rehearsal is `1,092` registered frames, and it is not yet releasable.**
> That is a real evening, only `123` frames short of the scored session itself.
> It is currently **STOP at zero frames** until the production dominance
> manifest is frozen. **That freeze was attempted, and it failed honestly.**
> Lane M164 built the manifest, its launcher and a fail-closed reader, then
> refused to mark the record `FROZEN` (commit `146d6048`) — run against it, the
> reader exits `2` with 17 explicit refusals instead of yielding a usable gate.
> **I earlier called that freeze "software work on my side"; that was
> incomplete.** Its missing inputs span several producers, and one named gap is
> that M147 has no accepted real scale and field result — **that is Ask 2a, so
> your two frames may sit on the critical path of the very gate that is blocking
> the rehearsal.** **CONFIRMED — M164 has now answered, and the answer is yes.**
> Its ruling reads `ASK 2A IS A MANIFEST INPUT: it resolves the accepted
> M_work, measured reference/scored sampling-ratio bound, common-field mapping,
> and viable target scale/carrier geometry`, and it states plainly that *"Ask 2a
> is consequently a direct critical-path input, not a side errand."* **Your five
> minutes with the shutter is the highest-leverage thing on this page.** One
> honest limit, in M164's words: it *"does not by itself freeze or fabricate the
> final target"* — software still has to compute the geometry, generate the
> artwork and commission the payload generator afterwards. It unblocks that
> chain; it does not complete it. **This does not affect Ask 2a below: M166 is explicit that _"The
> two-frame M147 preflight may still be completed; it establishes scale and
> field only."_ Shoot the two frames. Do not start the rehearsal.**
>
> **Why a rehearsal is worth your time rather than an annoyance.** The margin
> the whole route depends on is thin. From diffraction alone the reference
> beats the scored path by only `1.03405x` at the weakest measured frequency,
> and M166 says plainly that *"Viltrox aberration, transmission loss, focus
> error, or bare-lens pupil behavior can erase or reverse it. Diffraction
> arithmetic cannot admit the rig."* Nothing in the existing `10,509`-frame
> archive can settle it — every inventoried frame is converter-on. **So this
> can still fail, and the rehearsal exists so that it fails on a throwaway
> sitting instead of on the holdout one.** A rehearsal is not holdout, so a
> failure there costs you an evening rather than the experiment.
>
> I am writing the full rehearsal and revised session specification into Ask 2
> next. **Ask 2a below is current and needs no changes — that part you can do
> now.**


> # DO THIS FIRST — two frames, five minutes
>
> **If you read nothing else on this page, shoot Ask 2a** (full instructions
> below). It is two exposures of one flat calibration slide that must not move
> between them.
>
> **It is the only blocker on the big session that needs you rather than me.**
> The rest of what stands in front of the 891-frame scored session is mine to
> clear. This one is not, and nothing in the archive can substitute for it:
> across the full inventory of **10,509** frames, every single one was shot
> through the teleconverter. There is no bare-lens frame in the archive at all.
>
> **Why it matters more than its size suggests.** The preflight that sets the
> session's magnification target has so far been commissioned only against a
> *synthetic* plant. The lane that built it is refreshingly blunt about the
> limit: those plants resample one real capture, so *"source pixels are
> correlated and interpolation adds non-optical blur"*, and they *"do not
> predict the interval of a real converter change"*. The real-optics interval
> near `2.03x` is **"the gating unknown"**, and the lane's own warning is that
> the program *"must not infer it from the synthetic pass"*.
> These two frames settle it.
>
> If they come back wide, **the magnification target moves, not the bar** — and
> learning that from two frames is enormously cheaper than learning it from 891.

---

> **CORRECTION, and it is mine.** An earlier version of this page told you the
> capture session reaches `4 of 12` and that buying Zerene reaches `12 of 12`.
> **Both were wrong and both overstated what your money and time buy.** I had
> credited the capture session with clearing blocker `(a)`. It does not. `(a)`
> is *"missing admissible detail instrument"* — a **statistic**, not a capture.
> The session supplies that instrument's required *inputs*; it cannot supply the
> instrument. Corrected numbers are below, re-derived mechanically from the
> scorecard's own table. The short version: **do not buy anything yet.**

---

## The one thing that actually gates this program

**Blocker `(a)`, an admissible detail/transfer instrument, is attached to eight
of the twelve axes by the current scorecard. A better capture is not a way
around it -- capture supplies the outside information the only usable
instrument needs, which makes it a precondition rather than a workaround. M1 is
the one route with a practical path today, not the only mathematically possible
one. It has already defeated several attempts.**

> ### Updated 2026-09-06, and this is the first genuinely good news on this blocker
>
> **Two things changed today, and together they move the detail blocker from
> "must be invented" to "must be commissioned and shot once."**
>
> **First, the goal is smaller than this page has been telling you.** Your plan's
> printable end-state sentence is six clauses, but one clause carries two axes,
> so it licenses **seven**: M1, M2, M3, M8, M9, M10, M11. It names no instrument
> for M4, M5, M6, M7 or M12. My scorecard had made all five fatal to publication
> anyway, and separately had made **Helicon mandatory** where your plan says
> *"Helicon if obtainable"* — which was blocking eight axes on a product you never
> asked for. Both were my inventions, not your requirements, and both are
> corrected (commit `6b966d8c`). **The five extra axes remain engineering gates
> and their results will still be published; they no longer gate your claim.**
> The `12 of 12` row in the table below is therefore the *engineering* target.
> **Your claim needs seven.**
>
> **Second, the detail instrument now exists as a design and has been ruled
> admissible — and the route costs `$0`.** The instrument was blocked on a
> reference captured at twice the scored sampling, which nothing on hand
> provided, and the proposed fix was a manufactured coded target plus a second
> calibrated optic. Your own plan already contained a cheaper escape: **score the
> *lower* magnification and use the higher one as the truth.** That inverts the
> problem and needs no new hardware at all — **a second macro optic is not
> required.**
>
> **One correction, and it is mine.** I wrote that this yields `2.8/1.4 = 2.0`
> exactly. Those are **lens labels, not measured magnifications**. On your
> measured rig the conservative converter-on ratio is `2.7015`, so a nominal
> `1.40x` scored state gives `1.9296` — **below the bar, not at it.** The route
> survives on a tighter scored state: a `1.32x` target with a hard `1.33x`
> maximum gives `2.0312`. **This is already in the capture request; there is
> nothing for you to compute and nothing for you to buy.**
>
> **What this does not mean.** The instrument is designed and ruled, not
> commissioned. It measures *detail recoverable through your shared prime*, not
> absolute object truth, and any published claim will say so. Its state is
> `BLOCKED_ON_PHYSICAL_COMMISSIONING_AND_FRESH_INVERTED_CAPTURE`. **Do not shoot
> yet** — the commissioning run has to clear first, and it is queued behind a
> timing-sensitive campaign currently holding the machine.

Here is what each step really reaches. This is a mechanical re-derivation from
the blocker table at `docs/proposals/2026-09-sota-scorecard.md:423-434`, not a
summary of one:

| after | clears | reaches | which axes |
| --- | --- | --- | --- |
| `crop-early` — **DONE, free** | `b` | **`2 of 12`** | M8, M12 |
| \+ capture **sessions** (`$0`, **two sittings, 2,307 frames** — see note) | `b+c` | **`3 of 12`** | M8, M10, M12 |
| \+ **Zerene `$189`** + a colour target | `b+c+d` | **`4 of 12`** | M7, M8, M10, M12 |
| \+ a working detail instrument | `a` | **`12 of 12`** | all |

> **Note on that middle row, because it used to say "45-60 min" and that was
> wrong.** The `45-60 min` figure described the old **603**-frame single-sitting
> design. That design no longer exists. The ask is now **two** sittings —
> a **1,092**-frame non-holdout rehearsal and a **1,215**-frame scored session,
> **2,307** frames in total — for the reasons set out under *"The capture ask is
> now two sittings, not one"* below. **The `768` / `891` / `1,659` figures this
> row carried until now are superseded** by lane M166's re-derivation (commits
> `a195bc63`, `ff99afc8`); the causes are in the banner at the top of this
> document. Ignore `1,659` wherever you still see it.
>
> **The duration is under revision and the old number was optimistic.** Lane
> M150's re-derivation puts the *shutter-time floor alone* for the scored
> sitting at roughly **28.5-35.4 minutes**, and that excludes setup, framing,
> the mid-session teleconverter removal, and calibration handling. Its finding,
> in its words: **"45 minutes is not credible."** Completion inside 60 minutes
> is unverified and conditional on the rehearsal. I have not yet had that
> arithmetic independently checked, so treat it as a floor rather than an
> estimate — **but do not plan either sitting around 45 minutes.**

> ### One decision from you is worth four axes, and it costs nothing
>
> **Every number in the table above assumes a rule I wrote and never checked
> against your plan.** I have since had it audited: the rule says no comparator
> can define a noise, artifact, speed or memory result until a new detail
> instrument exists. **It appears nowhere in your plan.** I added it.
>
> A mechanical re-derivation of all sixteen blocker combinations shows what it
> costs you:
>
> | after | with my rule | without it |
> | --- | --- | --- |
> | Zerene + colour target | `2 of 12` | **`6 of 12`** |
> | \+ the capture session | `4 of 12` | **`8 of 12`** |
>
> **Same money. Same shooting. Twice the scoreboard.** The reason is that four
> axes — noise, artifact, flat power and throughput — do not actually need a
> detail instrument to be scored; my rule was blocking them anyway. Four others
> (M1, M5, M6, M9) genuinely do need one, and those stay blocked either way.
>
> **The honest case for keeping it:** it stops a deliberately blurred fast mode
> from being crowned the quality comparator, which is a real way to fake a win.
> **The honest case against:** your plan asks only for comparators *"at matched
> output"*, and it is not my place to spend four axes of your money enforcing a
> stricter bar you never asked for.
>
> **What I need from you: keep it, narrow it, or drop it.** I am not going to
> quietly pick, because I am the one who benefits from the stricter version —
> it makes the eventual claim stronger while costing *you* the axes. **It
> changes nothing today** (with only `crop-early` done, all three answers leave
> exactly M8 and M12 scoreable), so there is no rush — but it should be your
> call before you spend anything.


**Read the third row carefully. $189 buys exactly one additional axis** — M7,
colour accuracy — and the scorecard says of M7 that *"No traceable colour target
exists"*, so even that one needs a further purchase before it can be scored.

There is a second, independent reason not to buy yet. The scorecard's decision
rules say a comparative quality gate must use a **qualifying** comparator, and:

> Once a replacement M1 is admitted, a comparator mode may define a noise,
> artifact, speed, or memory envelope only if it passes the input/output
> transfer audit and retains at least `98%` of the highest replacement-M1
> information score achieved by any registered mode on that capture. [...]
> **In v1.7 no mode can yet be quality-qualified.**
> (`docs/proposals/2026-09-sota-scorecard.md:94-98`)

**Zerene cannot be lawfully qualified as a comparator until the detail
instrument exists.** Buying it today purchases a tool the scoring rules will not
yet let us use for five of the axes it is meant to unlock. The money is not
wasted, but it is early, and nothing is lost by spending it later.

**So the program's critical path is not your wallet and not your time. It is a
measurement problem, and it is mine to solve.** That work is now the top
priority lane.

> **Late addition, and it may be good news.** After writing the above I went and
> read *your* plan rather than the scorecard derived from it, and
> `2026-08-sota-path.md` **already specifies a detail instrument** — `D8`,
> split-stack self-calibration, which it calls *"the best-commissioned
> instrument in the corpus"*.
>
> **Retracted within the hour — it is not good news, and I was wrong.** I found
> `D8`'s own registered gate, `docs/research/M-PHASE0-SPLIT.md`, and its verdict
> is **KILL**. The M115 numbers reproduce exactly, but *"their controls do not
> transfer"*. Worse, the very figure I was about to reassure you with — the
> `0.54%` invariance — turns out to be the metric being **structurally unable to
> see** the filter rather than resisting it. The published resolution crossing
> was withdrawn (`9/12` values were a fallback returned when there was **no**
> crossing, and a *flat* patch scored the same). And an adversary that simply
> averages two renders scores **perfect** on it while throwing away `29.6%` of
> real detail.
>
> **So the scorecard was right and I was wrong.** `(a)` is a genuine research
> problem, exactly as stated above. I read the plan's prose without first
> checking whether its own gate had already fired, and I should have.
>
> **The one piece of real news is better than the false one, and it concerns
> you.** The kill names its own repair: *"the repair is a second independent
> capture, not another FRC threshold."* Two halves of **one** stack share sensor
> fixed-pattern structure, which is what defeated it. **Two independent brackets
> of the same scene do not.** Your registered session already shoots exactly
> that — two independent sw4 passes and two independent sw10 passes at matched
> geometry, IBIS off.
>
> **That makes Ask 2 more important, not less.** It is no longer just "inputs for
> a future instrument"; it is the specific repair for the specific confound that
> killed the last one. Whether the repaired form is admissible is still open and
> is being ruled on now — a second capture does not by itself defeat every
> failure that killed D8, and I will not tell you it does.

---

## Where the program actually stands

**`0 of 12` scorecard axes pass. `1 of 12` has ever been scored. That one is a
FAIL.**

That is a correction, not a setback. Every earlier summary said `2 of 12`, but
`2 of 12` was the count of axes that were *measurable*, not *measured* — a
distinction the scorecard's own legend warns about and which the scorecard
itself then got wrong about its only score.

The one scored axis is **M8, the source-hull certificate**: the rule that the
stacker must never emit a value that was not in its source data. We violate it
on `1.030569%` of resampler samples, against a bar of exactly `0.0000%`. The
checker was commissioned in both directions before it ran, so the failure is
real and not an instrument artifact.

> **Corrected 2026-09-06, and the correction is in your favour.** This
> paragraph used to add "and `1.326144%` of output samples". That second number
> has been withdrawn. Lane M136 proved constructively that the bar it was
> measured against was **impossible** — not demanding, but unsatisfiable by any
> program ever written, because `977,684` of the required checks demanded an
> output value larger than the output format can represent. Reporting it as a
> failure told you strehl fell short of a standard, when the truth is it was
> being measured against a standard nothing could meet. **That overstated how
> badly we are doing, and it was my error to leave standing.**
>
> The bar has since been repaired, and the repair is not a softening: a clean
> resampling kernel now scores **exactly zero** violations out of `74,173,536`
> checks, independently zero in red, green and blue, while our shipping kernel
> does not pass. So the new bar still bites. **We have not yet run our own code
> against it** — that measurement is a two-minute job sitting in a queue behind
> a long-running lane, and I will report the number when it exists rather than
> quoting a provisional one.
>
> **The `1.030569%` failure above is untouched by all of this**, and an
> independent audit confirms *its* bar is achievable. M8 still fails. It just
> fails on one count rather than two.

**Nothing you can buy or shoot fixes M8.** It is a software defect and it is
being worked now. Tonight's picture changed twice: a promising repair looked
excellent, then failed the control I demanded of it. The honest summary is that
**we no longer have evidence that fixing M8 costs any image quality at all** —
which is better news than it sounds. See the M137 row.

---

### Added 2026-09-06, second update — four lanes converged on one fact

**M1 is the keystone, and almost nothing else can move until it does.**

Four independent lanes arrived at the same place tonight from different
directions. M2's comparator clause, M3's *"no worse than best comparator"* and
M11's *"twice the fastest qualifying comparator"* all inherit comparator
qualification — and qualification routes through M1. **Four axes are therefore
unadjudicable by any amount of measurement until M1 has an admissible bar.**
This is not a measurement backlog. No amount of compute clears it.

**A stronger version of the same finding arrived hours later.** A lane was asked
to repair M2, whose statistic currently *improves* when the image is blurred. It
came back with something better than a repair: a proof that no repair of that
kind exists. Given two rendered images where one is a smoothed version of the
other, the identical bytes are equally consistent with two opposite stories —
that the smoother one lost real detail, or that the smoother one is faithful and
the difference was noise correctly removed. **No statistic computed from only
those two images can reward one and reject the other.** It needs an observation
from outside them.

That sounds like bad news and is not, because it points at exactly the escape
route your own plan already contained: score the lower magnification and use the
higher one as the truth. **The identifying information has to come from outside
those images, and capture is the only usable source of it we have.**

**That proof has now been independently attacked, and it held.** A separate lane
reproduced every number from source — byte-identical to the committed artifact —
built its own counterexample from scratch, and confirmed the core argument. It
also caught the first lane overselling two things around it, and I have corrected
both in the plan rather than letting them stand: the impossibility is *not* a
universal statement about every conceivable metric, and M1 is *not* the only
anchor that could work in principle. In practice nothing cheaper exists — no
adequately powered, independently calibrated reference is sitting in the archive —
so **M1 is still the only route with a path to a real result, and Ask 2a is still
the best five minutes you can give this program.** What I withdrew was a claim
that it was mathematically forced, which this program never needed and could not
support.

**What this means for you, concretely.** It raises the value of the two frames
in Ask 2a and lowers the value of everything else on this page. Those two frames
are the falsification gate for a `1,602`-frame session — if the optics cannot
reach the required ratio, the whole session is cancelled before it is shot, and
if they can, the keystone starts moving. **It is still five minutes and it is
still the best thing you can do for this program.**

### Also added 2026-09-06 — a machine problem you should know about

This host measured a mean of **`93.2%`** CPU across three samples tonight, with
the agent processes themselves the top consumer. **Absolute timing cannot be
validly measured while the program is running.** Any wall-clock number taken
under that load carries an uncontrolled covariate, so a standing quarantine now
applies to every timing figure until it is reproduced on a quiet machine.

This is not costing you anything today, because the plan already ranks speed
work strictly behind the resolution claim. But it does mean the speed axes will
eventually need the machine to itself — and the repaired M11 specification also
calls for genuine reboots between runs. **When that comes due it will be an ask
on your time, not your wallet.** It is not due yet.

## What is being done without you

No action needed on any of these. They cost nothing and need none of your time.

| lane | what | why it matters |
| --- | --- | --- |
| **M130** | Build `crop-early` — **landed** | Every one of the ten blocked axes carries blocker `(b)`, so nothing could be unlocked without this. **Done, verified by me independently, and committed.** The usable area of a cropped stack goes from **64.60% to 96.22%** of the frame — it now passes the ≥80% gate it used to fail — and existing default output is byte-for-byte unchanged. This was one of only two gates on resuming any new build; the other is now running. |
| **M137** | Clamped resampler — **good news, then retracted** | The fear was that fixing M8 costs sharpness. A clamped kernel scored **zero violations across 6,131,678,976 samples** while keeping `99.76%` of what we were calling detail. Then I made it test the measurement itself against a **blank patch of image** — and the blank patch scored *higher* than the detailed one. So that number was never measuring detail; it was measuring amplified noise. Claim withdrawn. **The silver lining is real: we no longer have any evidence that fixing M8 costs image quality.** |
| **M138** | Re-examining a design we declared dead | Phase 1 of the plan — the merge rule the whole roadmap was built on — was declared refuted in September, leaving the plan with no bridge at its first step. **The test that killed it was self-contradictory.** It required a single fixed setting to match a comparator whose own setting deliberately changes across seven frequency bands, to within 5%, and threw out every candidate that failed *before* it ever measured quality. I verified that in the test's own source code. The refutation is withdrawn — **Phase 1 is untested, not dead**, which is a far better place to be. |
| **M135** | A detail measurement we can trust | **Now the single most important thing in the program.** Two separate attempts to measure image detail have now failed the same test: both scored a blank patch as highly as a detailed one. Until we can measure detail honestly, we cannot make a resolution claim at all — and a resolution claim is the whole point. **A better capture is not an alternative to the instrument; it supplies the external identifying information that the current usable instrument requires.** |
| **M136** | The M8 bar itself — **ruled, and the bar was broken** | We were scoring the resampler for something it cannot control: at long exposures the output format physically cannot represent the correct value, so it counted as a violation no matter what. This turned out to be worse than a quirk — the bar was **impossible**, failing on `977,684` checks that demanded a value larger than the format can hold. Ruling: repairing it is a **legitimate repair, not moving the goalposts**. The repaired bar still bites, and that is measured, not asserted: a clean kernel scores **exactly `0` out of `74,173,536`**, independently zero in red, green and blue, while our shipping kernel does not pass. **Our own score against the repaired bar does not exist yet** — a two-minute run, queued. I am not quoting the provisional figure; the lane's own report calls it a diagnostic rather than a score, and I hold this file to the same line I hold the lanes to. |
| **M12** | Formal memory/determinism run | Superseded by the **M139** row below — its blocker has cleared. |
| **M138** | Re-examining a design we declared dead | Phase 1 of the plan — the merge rule the whole roadmap was built on — was declared refuted in September and the plan has had no bridge at its first step ever since. **Answered tonight: the test that killed it was self-contradictory.** See the row above. |
| **M139** | Formal memory/determinism run | Free, ~3.5 hours, no input from you. **Now unblocked** — `crop-early` landed and I verified and committed it. |

---

## Ask 1 — send one email. **$0, five minutes.** No deadline, but do it before any purchase.

**It costs nothing, and it protects the $189 whenever you do spend it.**

> **⚠ The "8 of 12" figure below is under audit and may be substantially too
> high.** Lane M169 (commit `7ae6dac3`) re-derived your plan's comparator
> requirement from source and found that the scorecard — my document, not yours —
> requires *all three* comparator arms for *every* comparative axis, while your
> plan assigns them **by claim**: PMax and DMap to detail, DMap to depth, the fork
> to the speed quote. Your own axis table records noise as *"Nothing — quotable
> now"* and speed/memory as *"Hold the line"* — **neither names a licence.** If
> that is right, a purchase clears fewer axes than this section claims, and some
> axes were never blocked by it at all. I have flagged the rule rather than
> quietly relaxing it, and I am not scoring anything under the looser reading
> until you rule on it.
>
> **⚠⚠ THE HOLD IS WITHDRAWN — and not because the audit above resolved.** It
> has not. I previously ended this block with *"hold the $189 until I give you
> the corrected number."* **Ignore that instruction. It was wrong twice over.**
>
> **First, the figure is wrong.** `$189` is Prosumer, and Ask 3's correction
> `D3` establishes from the licence text that a published competitive benchmark
> belongs on **Professional at `$289`**. There was never a `$189` to hold.
>
> **Second — and this is the substantive reversal — the purchase acquired a
> second, independent justification tonight that does not depend on the
> contested "8 of 12" figure at all.** Lane M164 ruled `LICENCE ON CRITICAL
> PATH` for the `1,092`-frame rehearsal itself. Not for an axis count — for the
> *release of the capture evening*. Its reasoning, which I have read at
> `M164-dominance-manifest.md:16-26`, is that M166 turned the manifest into a
> broader M1 configuration freeze, and under it *"the concealed target seed may
> be selected only after every renderer binary/setting/hash is frozen"* —
> Zerene's included. **So holding the purchase now holds the rehearsal, which
> holds the scored session behind it.**
>
> **State of that ruling, stated honestly.** M164 tags it `INFERRED BY READING`,
> not `VERIFIED BY RUNNING`. It is a chain of contract reading, not a
> measurement, and I am giving it to you with its marker intact rather than
> promoting it. But the inference is independently corroborated by your own
> plan, which pins *"licensed Zerene (PMax **and** DMap — DMap has never
> rendered here and is A5's true comparator)"* at `2026-08-sota-path.md:1535`
> and rules at `:2302` that an open-source stacker *"clears **no** blocker."*
> **The purchase is required by your plan, not merely by my scorecard.** What
> the audit above contests is only *how many axes it clears* — which changes
> the size of the prize, not whether the purchase is needed.
>
> **So: send the email first — it settles the edition and the benchmarking
> question — then buy Professional. Do not wait on the axis-count audit.**

Blocker `(d)` — the Zerene/Helicon comparison — gates **8 of the 12 axes**. The
entire point of it is to *publish* a comparison. Lane M132 read both vendors'
current licence terms with a browser user-agent and audited them for
benchmarking clauses. The finding:

> **Both EULAs are completely silent on publishing benchmark or comparative
> results.**

Silence is not permission. It is also not prohibition — but we would be
spending money and then building eight axes on top of an assumption. One email
resolves it, and it also resolves the edition question below.

### The edition question, which the same email settles

Zerene's **Prosumer ($189)** carries this restriction, quoted verbatim:

> Prosumer Edition can be used for educational instruction and preparation of
> instructional materials. However, Prosumer Edition cannot be used to support
> any other corporate, organizational, or government activity, including funded
> research and documentation of scientific collections, or in connection with
> any other activity that produces income or other tangible reward greater than
> the cost of a Professional Edition license.

**Professional ($289)** instead carries an explicit clearance:

> There are no restrictions on the use of images produced by Professional
> Edition licenses, unless such restrictions are listed as Special Terms within
> the license key.

A personal, unfunded, non-income project reads as squarely inside Prosumer, and
a public technical write-up is arguably "preparation of instructional
materials". But `strehl` publishes through a blog, and if that blog ever carries
income the reading changes. **The extra $100 buys unambiguous clearance to
publish the output images.** Ask, and you will not have to guess.

### The technical question, which the same email also settles — added 2026-09-06

**Buying the licence does not close this blocker.** Lane M157 audited Zerene's
public documentation for the one thing the scorecard actually requires — that
every program emit a *native-size 16-bit linear TIFF* — and returned
**[NOT FOUND]**:

> Neither statement is explicitly attached to **Save Adjusted Input Images**.
> Across the FAQ, how-to page, modification history and batch documentation, the
> linear/16-bit contract for that specific command is undocumented.

What *is* verified is only that the feature exports the aligned and
brightness-corrected **input images** rather than a PMax or DMap result, and
that Zerene supports high-bit-depth TIFF generally. Neither establishes that
this command writes native-size, 16-bit, *linear* data with a known colour
profile — and if it silently applies a tone curve, resizes, or writes 8-bit,
the common-input contract fails and the comparison cannot be run at all.

So the honest position is: **a Zerene purchase clears the licence gate but
should not be recorded as closing the common-linear-input gate.** That needs
either a written vendor answer or a licensed witness run. The email is free and
comes first.

### Draft — send to Zerene Systems

> Subject: Licence question — publishing a technical comparison
>
> Hello,
>
> I am developing my own focus-stacking software as a personal, unfunded
> project, and I would like to publish a technical write-up comparing its
> output against Zerene Stacker on identical input images.
>
> Two questions:
>
> 1. Do your licence terms permit publishing such a comparison, including
>    sample output images produced by Zerene Stacker and measured performance
>    or image-quality results?
> 2. Which edition would I need for that? I would be using "Save Adjusted
>    Input Images" so that both programs work from the same aligned inputs.
>    The project is personal and produces no income, but it would be published
>    publicly.
>
> And one technical question, which decides whether the comparison is possible
> at all:
>
> 3. When using "Save Adjusted Input Images", what exactly is written? I need
>    to confirm five things: that the images are **native size** with no
>    resizing or cropping; that they can be written as **16-bit** TIFF; whether
>    the data is **linear**, or whether a gamma or tone curve is applied on the
>    way out; which **ICC profile / colour space** is embedded; and whether the
>    export can be driven from the **batch or command-line** interface rather
>    than only the GUI.
>
> Thank you,
> Chris

**If they say yes:** buy the edition they name — *provided* answer 3 confirms
native-size 16-bit linear output. **`(d)` clears only after both licensed PMax
and DMap actually produce common-input outputs that pass §1.3**, not on purchase.
The third arm is already done: lane M175 rebuilt the retained fork, froze its
hash before rendering and passed §1.3, so Zerene is the only thing still
missing. If answer 3 comes back as "gamma-encoded" or "8-bit only", tell me
before buying; the comparison protocol would need rebuilding around whatever it
does emit, and that is a design change rather than a purchase.
**If they say no:** you have saved $189 and, far more importantly, we have not
built eight axes on an unpublishable comparison. We would then re-scope `(d)`.

---

## Ask 2 — the capture session. **$0.** *Do not shoot yet. One tool has to exist first.*

> **STOP — this changed after the section below was written, and the change is
> blocking.** The lane that designed the instrument this session feeds (M135)
> has ruled that **you should not shoot until an in-field preflight exists**,
> and I agree with its reasoning. The session is still the most valuable thing
> you can do; it is simply not yet safe to do it. **I am having the preflight
> built now.** I will tell you the moment it is ready. **There is now one small
> thing you can do that genuinely helps: see § *Ask 2a* immediately below — two
> frames, five minutes, and it is what lets the preflight be trusted at the
> ratio that matters.** Read § *The blocking finding* if you want the full
> reason for the stop.

### Two things changed on 2026-09-06, and one of them would have wasted the whole session

> **Read this before you plan anything.** Neither item asks you to do something
> new tonight. Both change what the session has to contain.

**1. The calibration frames were missing from every plan, including mine.**

The lane building the common input contract (M165) finished tonight and
delivered a working, commissioned converter: frozen `rawpy 0.27.0` / LibRaw
`0.22.1`, and TIFFs *measured* rather than assumed to be 16-bit, linear
(ICC TRC `1.0`), ProPhoto D50, uncompressed, at native `7028x4688`. Its
byte-identity check is real — a single flipped bit fails it.

Then it reported the thing nobody had noticed:

> **PATTERN MAP: Does not exist.** M1/M9 remain `UNMEASURED`; matching
> body/ISO/exposure/temperature darks and matching lens/aperture/focus flats
> are required.

In plain terms: the pipeline needs a map of your sensor's fixed pattern, and
that map is built from **dark frames and flat frames that match the session**.
Matching is the hard word — the darks have to match body, ISO, exposure time
and temperature, and the flats have to match lens, aperture and focus.

**As the plans stood, you could have shot the entire session, executed the
protocol perfectly, and still been unable to score two axes**, because the
frames that make the session interpretable were in neither plan. The capture
lane and the input-contract lane were designed separately and each assumed the
other had it covered. I have folded the requirement into the capture plan and
recorded it as a demonstrated failure mode rather than a hypothetical one.

You do not need to do anything about this yet. I am telling you because it is
the clearest example so far of why I keep refusing to send you a capture
request the moment a lane produces one.

**2. The M1 session is much larger than Ask 2a. I sent it back, and it came
back staged — with your two frames as its first gate.**

The lane that owns the hardest axis quoted its first honest minimum for a
capture that would make M1 measurable: roughly **1,661 exposures.** That is not
a typo and it is not padding — M1 needs an external truth reference at higher
sampling, and there is no cheap substitute.

**I did not forward that, and I would not have.** A non-refundable request of
that size, against a protocol never exercised end to end, is how a month gets
lost. I sent it back with three demands: stage it so each step has a go/no-go
gate, make the earliest stage capable of *falsifying the design* before you
shoot the expensive part, and **exhaust the frames you have already shot before
asking for a single new one.**

**On reusing your existing frames, the answer is no, and the reason is one you
can check yourself.** Every capture family was ruled on individually. They all
fail for the same reason: M1's reference has to be shot with the **teleconverter
removed**, and across the full inventory of **10,509 RAWs there is not one
bare-lens frame** — every file reads `200 mm` through the 2× teleconverter, with
stabilization on. Physical reproduction ratio is recoverable for **zero** stacks.
So the credit against the new capture is `0` frames, and I am reporting that
rather than pretending the number could be smaller. The corpus is not useless —
it has already paid for a great deal of software development — but development
frames and protocol photons are not interchangeable.

**What you can do right now has not changed, and it matters more than it
looks.** Ask 2a below — two frames, five minutes — **is Stage 0 of this plan.**
Not a warm-up for it: the actual first gate. Converter on, then the same slide
physically unmoved with the converter off. If that pair says the optics cannot
support the required sampling ratio, **the entire 1,602-frame session is
cancelled before it is ever shot**, and you will have spent five minutes to
learn it. That is the best-value capture on the board by a wide margin.

**The staged shape, so you can see the off-ramps.** Nothing after Stage 0 is
released until the previous verdict is on disk and accepted:

| gate | new frames | cumulative |
| --- | ---: | ---: |
| Stage 0M — contract gate, **zero frames** | `0` | `0` |
| **Stage 0 — your two-frame kill test** | `2` | `2` |
| Stages 1–5 — rehearsal, released one block at a time | `896` | `898` |
| Stage 6 — the sealed M1 score | `704` | **`1,602`** |

If you later choose to preserve the combined M1/M5/M9 holdout instead, the
sealed block grows and the total becomes `1,917`.

**These totals are not final yet and I am not asking you to accept them.** They
assume two dark-temperature classes and two flat-focus classes; every extra
focus class adds `96` flat frames and every extra temperature class adds `96`
darks. Freezing those counts is work I have assigned, and **no calibration
capture is executable until it lands.** You will get a final number, once, when
it is real.

> **⚠ Read this before you use any number in this section.** The `896`, `704`,
> `1,602` and `1,917` figures above come from lane M164's staged-capture design
> and **predate lane M166's re-derivation** (commits `a195bc63`, `ff99afc8`),
> which puts the rehearsal at **`1,092`** and the scored session at **`1,215`**,
> **`2,307`** together. I have not silently overwritten M164's staging here,
> because the two are structured differently — M164 stages a `704`-frame sealed
> M1 score, M166 sizes the full M1/M5/M9 session — and picking a winner by
> arithmetic alone is how a wrong number reaches you. **The reconciliation is
> assigned.** Until it lands, treat `1,092` / `1,215` / `2,307` as the current
> ask and this section's staging *shape* — the off-ramps, Stage 0 as a kill test
> — as the current intent. **Do not add any two of these totals together.**



> **This changed tonight and it changes what you should budget.** The session
> was described above as one uninterrupted 45–60 minute sitting. It is now
> **two separate sittings**, and they cannot be merged. Nothing was added
> carelessly; the second sitting exists because merging them would silently
> destroy the first.

| sitting | frames | may be read? | purpose |
| --- | ---: | --- | --- |
| **1 — rehearsal** | **1,092** | **yes, and must be** | proves step widths, commissions the detail instrument, binds its physical allowances |
| **2 — scored session** | **1,215** | **no, sealed until the registered score run** | the actual measurement M1, M5 and M9 are scored from |
| **total** | **2,307** | | plus the two frames of Ask 2a |

> **Superseded, 2026-09-07.** This table read `768` / `891` / `1,659` until lane
> M166 re-derived both sittings (commits `a195bc63`, `ff99afc8`). The rehearsal's
> current composition is `676` dominance kernel + `224` exact candidate execution
> + `192` physical controls = **`1,092`**. The `768`-frame breakdown further down
> this section is the superseded composition and its rows no longer sum to the
> ask; it is retained only so the change is visible.

**Why they cannot be the same sitting.** The detail instrument requires two
mandatory *physical* control arms — a deliberately blurred capture and a
genuinely sharper one — and those controls are measured **against the
converter-on reference block**. That is the same reference the scored value
depends on. Commissioning reads it, and the governing rule
(`docs/proposals/2026-09-sota-scorecard.md:345-349`) is unambiguous:

> The holdout unit is **subject plus uninterrupted capture session**, not a
> directory or step width. Rendering, tuning, or reading an outcome on any
> member burns every member of that unit.

So reading the controls burns the scored session. The rehearsal must be shot,
read, and its allowances **frozen and hashed before** the scored session begins.

**Two cheap shortcuts were considered and both are invalid.** I record them
because they look reasonable and someone will suggest them again:

1. **Selecting the blur arm from frames already in the `sw4`/`sw10` ladders.**
   Invalid — deciding after the fact which captured frames count as "blurred"
   is outcome-dependent selection. It converts a control into a result.
2. **Using the converter-on reference as the improvement arm.** Invalid — it
   makes the reference both the truth *and* the improved output, which is
   circular.

**The rehearsal's 768 frames**, block by block, sum verified:

| block | frames |
| --- | ---: |
| TC0 `sw4-A/B` and `sw10-A/B` | 164 |
| TC0 P/S/E witnesses for G0–G3 | 60 |
| Rehearsal TC0 flats/darks A/B | 128 |
| Rehearsal converter-on `R1/R2` atlas | 96 |
| Rehearsal converter-on flats/darks A/B | 128 |
| `TC0-CTRL-SHARP` near/mid/far, 32 each | 96 |
| `TC0-CTRL-BLUR` near/mid/far, 32 each | 96 |
| **total** | **768** |

Induce the blur by **focus offset**, not by changing aperture, exposure or
adding optics. Focus offset changes one variable and reuses the rehearsal's own
calibration; any of the alternatives forces another 128 calibration frames and
makes the rehearsal **896**.

**None of this is shootable yet** — the preflight of § *Ask 2a* still gates
both sittings, and the working magnification is still unset. This section is
here so that when it *is* shootable you are not surprised by the size of it.

### Ask 2a — **two frames. Five minutes. This is the one thing you can usefully shoot right now.**

> **This is new, it is cheap, and it unblocks the most expensive thing on the
> board.** It is not the session. It is two exposures of a flat target, and it
> is the difference between the 891-frame session being shootable and being
> guesswork.

> **Before you start:** this is one preflight attempt, normally two RAW files.
> It may require a second two-frame attempt if the first placement misses the
> gate or either file is refused. Do not begin the rehearsal or scored session
> from these frames alone.

**What to shoot:**

1. Use the **high-resolution calibration slide's regular dot grid** used for the
   existing `high-res-calibration-slide-cpl` captures — not the ruler, the older
   calibration-grid target, or a nonperiodic patch. Mount it rigidly, flat, and
   as square to the sensor as you can. Choose one grid intersection near frame
   centre and keep that same physical point centred in both frames. Make the
   grid fill most of both frames.
2. Set **M mode, ISO 100, 1 s, camera-indicated/marked f/5.6, fixed white
   balance, EFCS, and full-resolution 14-bit lossless-compressed ARW**. Turn
   **body SteadyShot/IBIS OFF** and the lens **OSS switch OFF**. Keep the light
   warmed and fixed. Leave the CPL/polarizer fitted and do not rotate it. Do not
   use crop mode, digital zoom, autofocus, focus bracketing, or an in-camera JPEG
   for either requested frame.
3. Fit and fully seat the 2× converter. Put the sliding focus ring in **FULL MF**
   and set the lens to its native **1.4:1 / minimum-focus end stop**; that is
   "maximum reproduction" here. Do not change focus on the lens after setting it.
   Move the complete camera/lens assembly **only along the optical axis on the
   rail** until the grid is critically sharp. Lock the tripod head and rail,
   confirm the selected grid intersection is centred, and take one frame.
   Identify the untouched original as `TR-REF-PREFLIGHT.ARW`.
4. Do not touch the slide, target tilt, light, polarizer, tripod head, camera
   height, camera lateral position, roll, or yaw. Remove the converter and mount
   the 100 mm lens directly. Put the lens in FULL MF and use its magnification
   scale to aim near **`1.32x`**, on the lower-magnification side rather than
   above the **`1.33x` ceiling**. This scale is only the initial placement; the
   RAW measurement, not the printed mark or EXIF, decides acceptance.
5. Keep that lens setting fixed. Refocus **only by moving the complete
   camera/lens assembly axially on the rail**. Do not pan, tilt, roll, yaw,
   raise, or shift sideways. Keep the same physical grid intersection centred and
   the same grid plane in view. Take one frame and identify the untouched
   original as `TC0-PREFLIGHT.ARW`.
6. If the slide, tripod head, camera centre, light, polarizer, aperture, ISO,
   shutter, or RAW mode changed — or if either frame is not critically sharp —
   discard **both** frames and restart at step 1. Never combine one frame from
   before a shift with one from after it.
7. Record or phone-photograph the bare-lens magnification-scale indication and
   rail/working-distance reading. Leave the rig locked and unchanged while the
   two original ARWs are checked. Send the originals, not exports. If the rig
   cannot remain locked, say so; a live pair must be repeated before the later
   session.

**Why this is needed, and why nothing in the corpus can substitute.** The
preflight measures the *ratio* of the two states' sampling. To trust it at the
ratio that matters, it has to be tested at that ratio on real optics. It cannot
be: **every frame you have ever shot was taken through the teleconverter.** I
checked this myself rather than taking it on report — across the full inventory
of **10,509 ARWs**, every lens string reads
`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` and every focal length reads
`200 mm`. **There is not one bare-lens frame in the archive.** The TC0 state the
design depends on is an optical configuration your rig has never been recorded
in.

**What it settles.** These files test the one physical placement you captured.
The checker divides the same grid's measured periods, so it does not need grid
pitch, sensor pitch, focal-length metadata, or an EXIF magnification value. It
does **not** infer absolute `1.32x` from metadata.

There are three possible first results:

- **Numerical PASS:** the measurement is valid and its unrounded lower bound is
  at least `2.0`. Keep the setup unchanged while the result is reviewed. A
  provisional console `PASS` is not permission to start either session; wait for
  an explicit go-ahead.
- **Numerical FAIL:** the pair was measured, but this placement lacks enough
  margin. We may ask you to lower bare-lens magnification and repeat **both**
  frames.
- **REFUSED / no ratio:** focus, exposure, grid coverage, target plane, camera
  pose, or input format was not measurable. Correct the named problem and repeat
  **both** frames; this is not an optical-design verdict.

A lower TC0 setting is usable only if the required target field and detail
frequencies still fit. If no setting satisfies all three conditions — sampling
ratio, common field, and carrier frequency — the present shared-lens reference
design stops rather than lowering the `2.0` bar. These files can therefore save
the large shoot, require one corrected pair, or show that this design must
change.

**The synthetic result is not proof and I will not present it as one.** Making a
synthetic `2x` frame means resampling a real one, and resampling injects
interpolation blur into exactly the quantity being measured. The lane that built
it says so plainly and I agree: the synthetic pass *is not yet a commissioned
gate*. Two real frames replace an argument with a measurement.

**What it costs you if you skip it.** The session is 891 frames in one
uninterrupted sitting. If the magnification is fractionally off, nothing
announces it at the time — reproduction ratio is not recoverable from metadata
for any of your 68 existing stacks — and it surfaces only in analysis, after the
sitting is gone.

**No rush and no deadline.** Whenever you are next at the rig.

### The blocking finding — why shooting tonight could waste the whole session

The design compares two optical states of your rig: a **reference** state with
the teleconverter fitted at about `2.7015x`, and the **TC0** state with it
removed at a target of `1.32x`, ceiling `1.33x`. The instrument requires the
reference to oversample the test by at least `2.0x`. As designed,
`2.7015 / 1.33 = 2.031203...x`. That is `0.031203...x` above the `2.0x` gate:
**`1.560%` relative to the required value, or `1.536%` relative to the achieved
ratio.** The shorthand `1.54%` used below takes the latter denominator.

You set that magnification **by hand**. M135's ruling is blunt: **`1.54%` is not
enough for blind hand-setting.** Placement repeatability here is `UNMEASURED`,
and the one figure that looked reassuring — M84b's `0.188%` statistical and
`~0.36%` absolute — measures *recovery*, not *placement*, so it does not cover
this.

**Why that is dangerous rather than merely tight:** M141 established that
physical reproduction ratio is metadata-recoverable for **0 of 68** of your
existing stacks. So if the achieved scale lands more than `1.54%` low, **nothing
in the files announces it.** You would shoot the full session, and the problem
would surface only later, with the session already spent.

**The good news, and the reason this is a delay rather than a redesign.** Both
optical states image the same coplanar grid. The gate is therefore a *ratio* of
two magnifications measured against that one grid — and in a ratio the grid
pitch, the sensor pixel pitch and the EXIF reporting all **cancel**. I checked
that argument independently and it holds. So the achieved ratio is measurable
from the frames themselves, with no absolute calibration required. It just has
to be measured **before** you commit to the session rather than after, which is
exactly what the preflight is for: shoot one grid frame in each state, run one
command, and it tells you `PASS` or `FAIL` with the direction to adjust.

### M135's other capture decisions, now settled

These answer the four questions that were holding the session:

| Question | Ruling |
|---|---|
| Teleconverter | **On** for the reference passes, **off** for TC0. |
| Magnification | Retain **`1.32x`** target, **`1.33x`** ceiling — *conditional on the preflight passing.* |
| Frame count | **891 registered frames** — this is the real number, not 448. |
| The committed 603-frame request | **Superseded.** |
| Stabilisation | **IBIS and OSS off throughout** — consistent with finding 1 below. |

**Action item on me, not you:** the protocol document
`docs/capture-requests/2026-09-319-frame-session.md` still describes the
superseded session. **Do not shoot from it in its current state.** I will
reconcile it against the 891-frame design before I tell you the session is
ready, so that what you shoot from is a single unambiguous document.

Once cleared, this session clears blocker `(c)`, which with `crop-early` reaches
**`3 of 12`** (M8, M10, M12).

**But its real value is larger than that number.** The session is also where the
*inputs* for the detail instrument come from — the dense checker-only reference,
the two matched sw4 passes, the two matched sw10 passes, the darks and flats and
the non-periodic sentinel (`docs/proposals/2026-09-sota-scorecard.md:544-551`).
Since the detail instrument is now the program's critical path, **this session
feeds the critical path.** It is the one owner action that unblocks the work
that unblocks everything else.

The scorecard is explicit that the existing material cannot be used for the
scored value: the burned grid and the development-only slide *"may commission a
new instrument but may never provide its scored value"*. So the session is not
optional, and no amount of cleverness on existing stacks substitutes for it.

Full protocol: `docs/capture-requests/2026-09-319-frame-session.md`.
Needs one dry-run rehearsal at 1.30x first — see blockers 1 and 2 in that file.

### Before you shoot — three things that changed tonight

**1. Stabilisation. Every frame you already own has it ON, and the protocol
requires it OFF.**

VERIFIED tonight against your library: all **68** stack directories and all
**10,509** ARWs report `image_stabilization: On`, across all **154** setting
segments, with no exceptions
(`experiments/M141-capture-inventory/capture-manifest.json`). The protocol
requires body SteadyShot and lens OSS **off**
(`docs/capture-requests/2026-09-319-frame-session.md:497-500`).

I want to be precise about what this does and does not prove. Metadata alone
cannot tell me whether the switches were physically on, or whether this body
simply always writes `On` for this tag. **What it does establish is that no
frame you own demonstrates the required state** — so this is unresolved either
way. Please physically confirm both switches before the session. It costs thirty
seconds and it is the difference between a usable session and shooting it twice.

**2. Do not rehearse the magnification yet — the target is moving as I write.**

The line above says 1.30x. That instruction is under active revision tonight:
one lane is proposing an inverted design that leaves your existing
maximum-reproduction session untouched and instead shoots **bare lens, converter
removed**, at a **1.32x** target with a hard 1.33x ceiling. Converter on versus
converter off is not a detail you can adjust for afterwards.

**Wait for me to confirm the magnification and the converter state before you
rehearse or shoot.** I expect to settle it shortly. Rehearsing to 1.30x with the
converter fitted may be rehearsing the wrong session entirely.

**3. The new calibration slide set: genuinely useful, but it does not reduce
this ask.**

You asked whether `high-res-calibration-slide-cpl` helps. Ruling: **BURNED —
deliberately spent development, not holdout.** It is one **657-frame** session
already designated and spent as development
(`docs/proposals/2026-09-sota-scorecard.md:363-379`; `docs/STATUS.md:2535-2547`),
and the program record states verbatim that it was *"burned deliberately and
knowingly"* and *"must not be used for any scored result"*.

That is not a loss and it is not a mistake you made — it was spent on purpose,
before you sent it, and it is doing real work: it can **commission** instruments,
which is exactly what the critical-path detail instrument needs. It simply
cannot supply a **scored** value. Those are different jobs.

**Coverage as of tonight: zero, under both live designs.** Of the committed
603-frame design's **24** blocks, **0** are satisfied by existing material. Of
the proposed 448-frame design's **21** blocks, **0** are satisfied
(`docs/research/M141-capture-inventory.md`;
`experiments/M141-capture-inventory/capture-design-coverage.json`). Nothing on
disk substitutes for this session, and I checked properly rather than assuming.

One further protective note: **35 of your 68 stack directories have no row in
the scorecard's evidence table at all.** They are recorded as
`INDETERMINATE — DO NOT ASSUME CLEAN` rather than quietly promoted to holdout.
Sixteen rows remain registered clean holdout and I am protecting them.

**Why this comes before the purchase.** Lane M131 ruled that Candidate 2 — the
one route that might have cleared `(a)` from stacks already on disk, at no cost
to you — **does not work**. Its synthetic result is genuine and survives audit,
but it does not transfer to natural renders. Had it survived, $189 alone would
have bought `6 of 12` with none of your time and the order would have reversed.
It did not.

---

## Ask 2c — three short flat captures for M4. **$0.** *New tonight, and the only capture finding that changed.*

**Good news first: M3 no longer needs anything from you.** I had been carrying
occlusion-halo and broad-veil as capture-blocked. A frozen input-only census
(M152, `docs/research/M152-site-census.md`) counted what your archive actually
contains and found **1,233 broad-eligible edges** where M3 needs 500 — 221 duck
tape, 399 chia, 511 flower/fern, 102 razor — every site carrying the full 400
native-pixel background reach, every capture clearing the 50-per-capture floor.
**M3's input requirement is met with photons already on disk.** That census was
frozen and hash-stamped before a protected pixel was decoded, and it read no
output of any kind.

**M4 is short, and only on one arm.** Its edge arm is comfortable: `10,355`
eligible sites against a need of 250. Its *flat* arm is not. The archive holds
**178 eligible flat tiles**, but supplies only **138 of the 250 flat sites M4
scores**, because the bee background's 123 eligible tiles are capped at its
quota of 83:

| flat subject | eligible tiles | frozen quota | selected |
|---|---|---|---|
| medication pill | 55 | 84 | 55 |
| exact bee background | 123 | 83 | 83 |
| foam | **0** | 83 | **0** |
| | | `250` | **`138`** |

Eligible and selected are different populations and I nearly quoted the wrong
one: `178` is what qualifies, `138` is what scores. That is `388` of `500`
scored sites overall, and the edge surplus is deliberately unable to dilute the
missing flat population.

**What would close it — three short sittings, none of them a full stack.**

1. A fresh, untouched **medication-pill** flat/background session supplying at
   least `84` qualifying tiles.
2. A fresh, untouched **foam** flat/background session supplying at least `83`.
3. A **separate, deliberately non-holdout development** flat session supplying
   at least `100` tiles, for commissioning the checker.

**Item 3 is not padding and it cannot be folded into items 1 and 2.**
Commissioning an instrument on a protected capture burns that capture for
scoring. Coffee bubbles and every existing flat-slide stack supply zero
qualifying tiles, so there is currently nothing to commission against at all.

**How to shoot them.** Reserve broad, truly featureless background; keep each
`128x128` tile above the ten-sigma black floor and below clipping; avoid
`20–60 px` texture in every focus frame. These are backgrounds, not subjects —
they should be quick, and they are independent of the 891-frame session.

**One choice here is genuinely yours, and I am flagging it rather than taking
it.** The near-equal `84/83/83` split is M152's, frozen before any pixel was
decoded. The scorecard itself asks only for `500` sites overall and `50` per
scored capture. Under that literal rule your existing medication capture
already clears `50`, and **one** new protected flat session supplying `>=72`
sites would close the 250-flat total — two sittings saved. **But changing the
quotas now, after seeing that foam returned zero, is a post-hoc population
change**, and that is precisely the move that makes a scorecard stop meaning
anything. It may still be right, because the `50`-per-capture rule predates the
census and is the more firmly pre-registered of the two. M152 declined to make
this call after seeing the result, which was correct of it. I am declining too:

- **Option A — shoot all three.** Keeps M152's pre-decode quotas untouched.
- **Option B — shoot one protected flat session of `>=72` sites, plus the
  development session.** Falls back to the scorecard's own literal minimum,
  recorded openly as a post-hoc population version.

I recommend **B if sittings are expensive to you, A if they are not.** Either
way item 3 is required, and neither option is urgent: M4 also needs a scorer
that does not yet exist.

---

## Ask 2d — one fresh tilted-ruler capture, with the tilt actually measured. **$0.** *One of three things M10 needs — and the only one that needs you.*

**The angle on record does not qualify, and the unit it describes is already
burned.** Both halves are new tonight (M154, `docs/research/M154-m10-angle.md`).

The README for `8-tilted-planar` records *"approximately 10.26deg (measured
about: 10cm run against 1.81cm rise)"*. That derives `10.259461685 deg`
correctly — the arithmetic is right — but it records no instrument, no least
count, no endpoint definition, no repeatability and no camera-relative frame.
**Decimal places in a derived display value are not measurement precision.**
M10 requires `theta_ext` frozen with uncertainty contributing at most `2.5%`
slope error, and nothing in the record bounds it at all.

Separately, **all three of those ruler stacks are burned.** M-PHASE0-CURV read
scored outcomes from f/5.6, f/8 and f/11, and M-PHASE0-LCA read another metric
from f/11, before the scorecard ever labelled them holdout. I have relabelled
them `BURNED — DEVELOPMENT ONLY` (`6915fe44`). They stay useful for
development; they cannot score.

**How precise, concretely.** The admissible band is
`[10.014357, 10.516727] deg` — about `±0.25 deg`. That sounds demanding and it
is not, provided you measure over a long baseline, because the tolerance on the
rise scales with the run:

| run | nominal rise | tolerance on rise |
|---|---|---|
| `100 mm` | `18.10 mm` | `-0.44 / +0.46 mm` |
| `300 mm` | `54.30 mm` | `-1.32 / +1.39 mm` |
| `500 mm` | `90.50 mm` | `-2.21 / +2.32 mm` |

**That table is the whole problem with the original measurement.** It was taken
over a `10 cm` run, where qualifying means knowing the rise to better than half
a millimetre — and *"about 1.81 cm"* plainly is not that. Measure the same
incline over `50 cm` and you need only `±2.3 mm`, which a careful tape
measurement gives you comfortably. Nothing here needs a laboratory.

**What to write down at capture time:**

1. The instrument and its least count or stated accuracy. A digital
   inclinometer specified to `<=0.1 deg` qualifies on its own.
2. The run and the rise as measured, with the baseline length stated.
3. Which physical features on the rig the endpoints were taken from.
4. A repeat measurement, so repeatability is evidence rather than assumption.
5. That the measurement is independent of image focus. **Image-derived focus
   may not certify the angle it is being tested against.**

**One caution that costs nothing.** Freeze the pose measurement *before* any
output from the new stack is read, and shoot it as its own uninterrupted
session. The old unit was lost to scoring precisely because outcomes were read
from it before anyone declared it protected.

**Not urgent, and I have corrected this heading since I first wrote it.** I
originally called this capture *"the whole of M10"*. It is not, and there are
now **three** things between M10 and a score:

1. **This angle** — yours, cheap, and the only one of the three that needs you.
2. **A depth product that does not yet exist** — mine. M10 scores something
   `strehl` does not currently emit.
3. **The M10 instrument itself is void** — mine, and newly found. Lane M161
   replaced every reported uncertainty with zero, then infinity, then random
   values, and **every M10 pass/fail quantity stayed identical.** The instrument
   does not read one of its own mandatory inputs, so today it would return the
   same verdict no matter how good or bad the depth product was. Lane M163 is
   repairing it.

None of that makes this capture less worth doing — it stays cheap, it is
genuinely blocking, and item 3 is being fixed without you. It does mean **do
not expect an M10 number soon after you shoot it.**

---

## Ask 2b — one more free email, this time to ISA. **$0.** *Do this instead of spending $660.*

**I owe you a correction first.** I have been describing the `$660` as buying a
better reference. **It does not.** It is one matte **ISA ColorGauge Nano** target
(`$330`) plus its calibration-certificate option (`$330`), and it serves **M7,
colour accuracy** — not the detail reference. Nothing in the `$925` improves the
detail work that is currently the critical path. I had this wrong in my own head
until a lane checked it, and you may have been reading it the same way.

**Verdict: do not spend the `$660` yet.** It changes no current verdict. M7 has
no capture, and — decisively — **ISA has not published the certificate's
numerical uncertainty**, so nobody can yet say whether the certificate is precise
enough to matter (`docs/research/M144-reference-uncertainty.md`).

Buying a ruler before knowing its precision is the mistake here, and it is
avoidable for free.

**The email, and it is falsifiable.** Ask ISA for three things at `$0`:

1. a sample of the exact certificate supplied with the matte Nano option;
2. confirmation that it is serial-linked to the delivered unit;
3. the per-patch covariance or expanded uncertainty.

**Then the decision makes itself.** Reject the purchase if any scored patch, or
any required patch-to-patch difference, carries `U95 > 0.25 ΔE00`. If ISA
reports only independent equal per-patch uncertainties, each must be at most
`0.1414 ΔE00`. A conforming certificate **reverses** this recommendation and I
will tell you to buy it; a missing or larger uncertainty confirms it. Today the
answer is no, and it is no for a reason that a reply from ISA can overturn.

**Why this matters more than it sounds.** The largest quantified term in the M7
reference budget is not sensor noise — it is variation between individual target
units. Modelled from ISA's own nominal batch statistics, the worst patch sits at
**p95 `2.6445 ΔE00`** and **p99 `3.4567 ΔE00`**, against bars of `1.0` median and
`2.0` p95. That figure is a screening model rather than a measurement of the paid
certificate, and it is exactly why the free nominal values cannot carry a scored
result — and why the certificate's *actual* uncertainty is the whole question.

---

## Ask 5 — reshoot the calibration slide, eventually. **$0.** *Not urgent. I spent your existing one, deliberately, and you should know why.*

**What I did.** Your 2026-09-02 `high-res-calibration-slide-cpl` session — 657
frames across `tilted-sw4` (182), `tilted-sw10` (92), `flat-sw4` (186) and
`very-tilted-all-axis-sw10` (197) — has been **deliberately burned for instrument
development.** Under this program's holdout rule, reading any outcome on one
member of a capture session burns every member of it, so those 657 frames can no
longer be used to *score* anything.

**Why I spent it rather than protecting it.** That session contains something no
other capture here does and nothing this program ever asked for: a **genuine
optical improvement pair.** `tilted-sw4` against `tilted-sw10` is the same
subject over the same focus-encoder range at a finer focus step — real added
detail, from real photons, with fresh noise in both arms. That matters because
every detail metric this program has built was retired after being tested only
against *simulated* improvements, and a simulated improvement is exactly what a
sharpening filter can fake. **Six candidate families across eight implementations
were all discarded without a real optical arm ever being run against them.** With
no detail instrument existing at all, the choice was between protecting a capture
I could not yet use and spending it to build the thing that would let me use
anything. I spent it, and I would make the same call again.

**What I need back, and when.** A fresh equivalent sitting — the same slide, the
same rig, the same four stacks — to serve as the **scoring** holdout once the
instrument commissions. It is a static target on unchanged equipment, so it is
`$0` and reproducible on demand.

**Do not shoot it yet, and do not shoot it in the same sitting as the main
session.** It is only needed after commissioning clears, and shooting it early
risks it drifting into the development set the same way the first one did. I
will fold the exact shot list into the capture request when the instrument is
commissioned, so that you shoot from one document rather than from this note.

**One thing to know about what that session can and cannot settle.** Even burned,
it cannot finish the detail question on its own: the four stacks lack the
independent repeat lineages the instrument needs, and using the finer-step stack
as its own truth would be circular. It commissions the instrument. It cannot
score it. That limitation was reported by the lane that wanted the result, against
its own interest, which is the reason I trust it.

## Ask 3 — buy Zerene **Professional, $289**. *Necessary either way, and the only thing on the board that unblocks an axis.*

> **CORRECTION — the third time I have had to correct this ask, and this one
> changes what it is for. Read it before the pricing table below.** Three
> defects, each verified against a primary source, plus one dependency I had
> never traced end to end. *Bold inside the quotations below is mine.*
>
> **D1 — "a licence bought now starts ageing" is false for Zerene.** That is
> reason 2 below, and it does not survive contact with the licence text.
> `C:\Program Files\ZereneStacker\License.txt` states a duration in exactly
> one place: clause 1, the free trial. The purchased-licence clauses — `2a`
> Professional, `2b` Prosumer, `2c` Personal, `2d` Student — each restrict
> *how many machines* a licence may run on and *what the images may be used
> for*, and **not one of them states a duration, a renewal, or a subscription
> term.** What we lost in June was a trial clock. Buying is the thing that
> ends that class of loss, not a repetition of it.
>
> **D2 — this ask bundles two unrelated purchases, then lets the wrong one
> decide both.** The table below totals a comparator licence together with an
> M7 colour target and an illuminant meter. But **Zerene unlocks no part of
> M7**, and the colour target unlocks no part of the comparator. Reason 3 —
> the one I called *"sufficient"* — is entirely about whether a `$660`
> ColorGauge can support M7's median `ΔE00 ≤ 1.0`. That argument is sound and
> it still governs the `$660` and the `$76`. **It has no bearing at all on the
> comparator licence.** I should not have priced two independent decisions as
> one, because doing so let an unresolved colour-metrology question hold up
> something colour has nothing to do with.
>
> **D3 — the table names the wrong Zerene edition.** It lists Prosumer at
> `$189`. Clause `2b` forbids Prosumer use "in connection with any other
> activity that produces income or other tangible reward greater than the cost
> of a Professional Edition license", and forbids supporting "funded research
> and documentation of scientific collections". Clause `2a` says Professional
> alone carries "no restrictions on the use of images produced". **A published
> competitive benchmark whose entire purpose is a public comparison against
> Zerene belongs on Professional.** `docs/STATUS.md:2641` had already reached
> that conclusion independently. The `$189` row, and therefore the `$925`
> total, understates the real figure.
>
> **AND THE COST OF WAITING IS NO LONGER ZERO.** Below I wrote *"nothing is
> lost by the delay."* That was true of a program with other axes in flight.
> It is not true now:
>
> - M140 ruled **M12** the one axis "scoreable now".
> - The scorecard's **M12-S** bar requires "exactly one distinct hash across
>   all five worker counts at every N, **and the 16-worker output must
>   simultaneously pass M11**."
> - **M11** requires warm common-input throughput `≥ 2.00x` **the best
>   comparator**.
> - That comparator must be licensed and able to save output. Ours is an
>   expired trial which, by this page's own note below, "cannot save output at
>   all."
>
> **So M12-S sits behind this purchase, and M12 as a whole sits behind
> M12-S.** The honest position is not "zero of twelve axes scored" — it is
> **zero of twelve axes currently completable**. The only thing finishable
> today without your shutter or your wallet is the **M12-D sub-bar**, and a
> sub-bar is not an axis.
>
> **AND NOW THE PART THAT CHANGES YOUR ANSWER.** I was one paragraph away from
> telling you this purchase might buy nothing. The thing that corrected me is
> your own plan. The scorecard demands the newest stable build of **both**
> named comparators and rules that "if **either** product cannot produce a
> linear output that passes §1.3, the named-comparator requirement is unmet
> and the SOTA verdict remains `UNMEASURED`." Helicon is not installed here at
> all — I checked four install locations and searched both Program Files trees
> by name — and the section below says the export we need from it exists only
> in a beta. Read together, those make the comparator bars unreachable at any
> price.
>
> **But that rule is not yours.** `docs/proposals/2026-08-sota-path.md` pins
> the comparators as "licensed Zerene", "the fork rebuilt at its best-known
> build", and — in its own words — "Helicon if obtainable". *If obtainable.*
> Optional. Where it names this very purchase it says "licence a commercial
> comparator", singular, and specifies that the export we need, *Save Adjusted
> Input Images*, "is licensed only to **Prosumer ($189)** or **Professional
> ($289)**". **I hardened your "if obtainable" into a mandatory comparator
> whose absence voids the entire verdict, and then let that invention block
> your purchase.** This is the third time the scorecard has manufactured a
> blocker your plan does not contain — after rule 4 and the `98%` threshold,
> both caught by M146.
>
> **So the verdict is: buy it, and buy Professional.** A licensed Zerene is
> required by your plan no matter how the Helicon question lands, so this
> purchase is necessary either way. Under your plan's own reading it is also
> *sufficient*: it unblocks M11's comparator ratio and, through M12-S,
> unblocks M12 — the closest thing to a first score this program has. Nothing
> else you own, and nothing you could shoot tonight, does that. Take
> Professional over the `$189` Prosumer for the licence-terms reason in D3
> above.
>
> ---
>
> > **D4 — added after M139 closed. One of the two reasons above died tonight,
> > and a stronger one replaced it. I am recording both movements, including
> > the one that costs me an argument.**
> >
> > **WITHDRAWN: "it unblocks M12."** The paragraph above says this purchase
> > *"unblocks M11's comparator ratio and, through M12-S, unblocks M12 — the
> > closest thing to a first score this program has."* **That is now false, and
> > it is false for reasons no purchase can repair.** Lane M139 ran the
> > registered M12 campaign to completion (commit `2ba256aa`) and returned a
> > **formal M12 FAIL** on two bars, neither of which involves a comparator:
> >
> > - **Absolute memory: FAIL.** The bar is `6 GiB`. The strongest accepted
> >   scored observation peaked at `33.4283 GiB` — **`5.57x` over the
> >   ceiling.**
> > - **Cross-worker determinism: FAIL.** `N=33` produced five distinct output
> >   hashes across workers `1/2/4/8/16`, and `N=105` independently produced
> >   five more. (Same worker count, run six times, gives one hash — so this is
> >   a real defect, not noise.)
> >
> > M12 is conjunctive, so either failure alone is decisive. **A licence cannot
> > move either number.** M12 is no longer a purchase away from a score; it is
> > a code fix away from being re-measurable. I have that fix assigned. **Do
> > not buy this licence expecting M12.**
> >
> > **REPLACED BY, and this one is worth more: the licence now gates your
> > capture evening.** Lane M164 ruled `LICENCE ON CRITICAL PATH` for the
> > `1,092`-frame rehearsal, because M166 turned the dominance manifest into a
> > broader M1 configuration freeze in which *"the concealed target seed may be
> > selected only after every renderer binary/setting/hash is frozen"* — and
> > Zerene is one of those binaries. **Until it is bought and hash-frozen, the
> > rehearsal cannot be released, and the scored session sits behind the
> > rehearsal.**
> >
> > M164 tags that ruling `INFERRED BY READING` rather than `VERIFIED BY
> > RUNNING`, and I am passing it to you with the marker intact. But it does
> > not stand alone: your own plan pins *"licensed Zerene (PMax **and** DMap)"*
> > at `2026-08-sota-path.md:1535` and rules at `:2302` that an open-source
> > stacker *"clears **no** blocker."*
> >
> > **Net effect on your decision: unchanged in direction, stronger in
> > urgency.** The purchase was previously justified by an axis count that is
> > under audit and may shrink. It is now justified by a release gate on the
> > one capture this program is waiting for. Buy Professional after the email.
>
> **One thing I need back from you, and it costs nothing.** Ratify or reject
> this reading: *Helicon is optional, so a licensed Zerene plus the fork
> satisfies the named-comparator requirement.* Ratify it and I correct the
> scorecard and the comparator question closes. Reject it and the comparator
> bars stay `UNMEASURED` until Helicon ships that export in a stable build,
> and no purchase changes that. **I am not going to quietly relax a
> pre-registered bar on my own authority** — a scorecard I can edit when it
> becomes inconvenient is not a scorecard. Lane M157 is confirming the
> edition, price, and whether *Save Adjusted Input Images* can be driven from
> a script, which the timed runs require.
>
>

**Correcting myself again, and this one is worth reading.** I previously wrote
that `$189` gets you from `3 of 12` to `4 of 12`. That was wrong, and it was
wrong in your favour to know: **the single axis the $189 buys is M7, colour
fidelity — and M7 needs hardware nobody had priced.**

The scorecard's readiness note for M7 is one sentence: *"No traceable colour
target exists."* So the purchase unlocks an axis that is itself blocked. Priced
properly, the floor for `4 of 12` is:

| item | cost | why |
|---|---|---|
| Zerene Prosumer | `$189` | clears `(d)`, the comparator |
| ISA ColorGauge Nano, matte, with NIST-traceable certificate | `$660` | the only target that **physically fits** at 1.3x |
| Sekonic C-800 illuminant meter, 3-day rental | `$76` | M7 requires a *measured* illuminant |
| **total** | **`$925`** | plus tax and shipping |

`$849` if you already have a usable illuminant meter; **`$2,748`** if you buy
the C-800 outright at `$1,899` rather than renting.

**One genuinely good piece of news in that table.** M7 *is* shootable at your
magnification, which was not obvious. Your sensor field is about
`27.62 x 18.38 mm`; the ColorGauge Nano is `20.64 x 17.46 mm` and fits with
hundreds of pixels per patch after erosion. **Ordinary ColorCheckers do not
fit at all**, and the Calibrite Nano would need `62.64°` of tilt and
`35.52 mm` of depth travel to be usable. So the axis is not impossible — it
just needs the right, and more expensive, target.

**Three reasons to wait. I am withdrawing the first one, and the other two carry
the decision on their own:**

1. **~~The scoring rules will not let us use it yet.~~ Withdrawn — that rule was
   mine, not yours.** I previously argued that no comparator can be
   quality-qualified until a replacement detail instrument is admitted, so five
   of the axes Zerene unlocks would stay blocked with it sitting installed. An
   independent audit checked that rule against your actual plan and found **it
   appears nowhere in it** — I wrote it into the scorecard myself, along with
   the `98%` threshold it depends on. It may still be a *good* rule and I may
   ask you to ratify it, but **it is not a fact about the world and it should
   not be counted as a reason to delay your own purchase.** I am flagging it
   because it was load-bearing: it also shapes which axes get marked blocked,
   and therefore the order I have been recommending you spend in.
2. **A licence bought now starts ageing against a program whose gating work is
   measured in research, not weeks.** We already lost one trial that way.
3. **We cannot yet prove the `$660` target would even clear the bar.** M7 demands
   median `ΔE00 ≤ 1.0`. A chart whose *own reference values* carry uncertainty
   near `1.0` cannot support that bar at any price — and the published data does
   not yet state its uncertainty. NIST is explicit that *"traceability alone does
   not signify or guarantee fitness for purpose"*. Worse, our own scorecard
   **specified no uncertainty budget for reference values at all**, which was a
   gap on our side.

   **That gap is now closed, and the answer is still wait.** A lane has since
   built the budget (`docs/research/M144-reference-uncertainty.md`). It turns
   this reason from a shrug into a number: the largest term is not sensor noise
   but variation between individual target units, whose worst patch models at
   **p95 `2.6445 ΔE00`** against a p95 bar of `2.0`. That is a screening model
   rather than a measurement of the certified unit, which is exactly why the
   certificate's real uncertainty is now the whole question — and why the answer
   arrives by email rather than by purchase.

**Reason 3 alone is sufficient**, and it is the one that actually protects your
money: the `$189` unlocks exactly one axis, that axis is M7, and M7 cannot be
scored without a `$660` target we have not yet confirmed is good enough.

**That `$0` step is now written up as Ask 2b above, with a decision rule
attached.** Ask ISA for the sample certificate and its numerical uncertainty,
which they supply at no charge. **Reject if any scored patch or required
patch-difference carries `U95 > 0.25 ΔE00`**; a conforming certificate reverses
this recommendation and I will tell you to buy. If the certificate does not
support a `ΔE00 ≤ 1.0` bar, the `$660` is dead money and the `$189` buys
nothing — and we will have learned that for free.

Buy when the detail instrument is admitted, the capture exists, and the
certificate checks out. Nothing is lost by the delay.

Zerene is already installed here at `1.04T2026-05-04-0750`, but its trial is
**consumed and expired** (`License category = TRIAL`, expired `2026-06-06`), so
it currently cannot save output at all.

### Do not buy Helicon yet

Helicon Focus **9 Pro** does have what we need — `Export Layers → Aligned source
images without transparency` — and it is cheaper at **$55 one-year / $200
lifetime**. But that capability is only in **9.0.5 Beta**; current stable
8.3.11 documents no alignment bypass. Its trial here appears unused, and
starting it now would burn a 30-day clock before the inputs are ready, which is
exactly how the Zerene trial was wasted. **Reserve it. Reconsider when Helicon 9
reaches stable release.**

## Ask 4 — one definitional call. **$0, and it is genuinely yours to make.** *Correction: it is not worth four axes. I was wrong.*

> **CORRECTION, and it is to my own argument.** When I first wrote this ask I
> told you rule 4 was costing you four scoreable axes. **That was false**, and
> an independent audit (M146, `docs/research/M146-unlock-audit.md`, commit
> `68ea3b95`) established it. I have rewritten the section below to the honest
> version. The question is still real and still yours — but the prize I
> attached to it does not exist, and you should not decide this expecting to
> gain four axes.

**The situation.** I wrote a rule into the scorecard that is not in your plan. It
is rule 4, and an independent audit confirmed it appears nowhere in
`2026-08-sota-path.md`. It is flagged `UNRATIFIED` in the scorecard for that
reason. **You should decide it, not me, because it is a question about what
counts as a fair comparison — and that is a judgement about the claim you want
to make, not a fact I can measure.**

**What it says.** A competing program's mode may set the noise, artifact, speed
or memory bar only if it **(i)** passes an input/output transfer audit **and**
**(ii)** retains at least `98%` of the best detail score any mode achieved on
that capture. The intent was to stop a deliberately blurred, fast, quiet mode
from becoming the yardstick.

**What it costs — the corrected version.** Conjunct **(ii)** needs the detail
instrument we do not yet have, so rule 4 does attach that blocker to four axes.
**What I got wrong is the claim that rule 4 is the *only* thing attaching it.**
It is not. Those axes are coupled to the detail instrument through clauses that
have nothing to do with my rule, and removing my rule leaves the couplings
standing.

**M11 is the cleanest refutation, and it was my own sharpest example.** I told
you M11 was blocked "purely because I said a comparator must be
quality-qualified first." That is wrong on the literal document. The scorecard's
comparator-envelope definition says *"For speed it is the fastest mode that
passes the complete quality scorecard"* (the comparator-envelope clause), and
M11's own computation step 7 independently repeats *"the fastest mode that
passes all quality gates"* (M11 "Exact computation", step 7). **Neither clause
is rule 4.** I
re-verified both against the scorecard directly; cite the named clause rather
than the line number, which drifts with every insertion. Strike
rule 4 tomorrow and M11 is still blocked, because M11's own bar demands a
quality-qualified comparator in its own words. M2, M3 and M4 have comparable
independent couplings.

| | rule 4 as written | rule 4 narrowed or removed |
|---|---|---|
| comparator bought | **2 axes** | **2 axes** — *no change* |
| comparator + capture | **4 axes** | **4 axes** — *no change* |

**So the honest position: narrowing rule 4 unlocks nothing today.** M146 tested
all four axes against the archive and returned `NEEDS_NEW_CAPTURE` or
`BLOCKED_FOR_ANOTHER_REASON` for every one. That is a genuinely useful negative:
it confirms you gain nothing by narrowing rule 4 now, and that you lose nothing
by leaving it alone while the detail instrument is built.

> **STALE SENTENCE, CORRECTED.** This paragraph used to end by saying that
> *"Ask 3's advice to wait on the `$925` is correct and now independently
> confirmed."* **Ask 3 no longer advises waiting.** Your plan asks for
> *"a commercial comparator"* and lists *"Helicon if obtainable"*, so the
> `$925` both-products figure was never something you had to clear; Ask 3 now
> advises buying **Zerene Professional at `$289` now** and not buying Helicon.
> What M146 confirmed is narrower than the sentence claimed: it confirmed that
> *rule 4* is not worth spending on, not that the comparator is not. Rule 4 is
> unaffected by the purchase either way.

**Why I am still asking.** Rule 4 remains an unratified rule I inserted into
your scorecard, and it still changes what a passing claim *means* even though it
no longer changes what is scoreable today. It is a question about what counts as
a fair comparison, and that is a judgement about the claim you want to make
rather than a fact I can measure. It just is not urgent, and it is not worth
four axes.

**The part I got wrong the first time, which still stands.** I originally
justified rule 4 as rigour. It is not. Because rule 3 already picks the
comparator in the *comparator-favouring* direction — the fastest for speed, the
quietest for noise — excluding degenerate modes makes every affected bar
**easier for us, not harder**. Rule 4 buys *fairness*, and it pays for it in
scoreability. That much was true when I wrote it and is still true.

**Two errors in one ask is worth noting.** I over-claimed the benefit and I
mis-stated the mechanism, and in both cases a lane found it rather than my own
review. I would rather show you that than quietly rewrite the section.

### What I recommend: publish both, and decide nothing

Score each affected axis **twice** — once against the rule-4-qualified
comparator envelope, once against every mode that passes the transfer audit —
and publish both numbers.

- It costs **nothing extra**: no additional capture, no additional renders. Both
  envelopes come from comparator runs we already have to do.
- It **unblocks the four axes now**, because the all-modes envelope needs only
  conjunct (i), which does not require the detail instrument.
- It makes a pass **stronger than either rule alone**. Beating both envelopes is
  unimpeachable. Beating only the qualified one is still a real result, and it
  gets stated as exactly that rather than hidden by a definition.
- It stops me from settling a definitional question by authorship, which is the
  failure this program keeps repeating.

**Your options, in the order I would pick them:**

1. **Publish both envelopes.** My recommendation, for the reasons above.
2. **Narrow it:** keep conjunct (i), drop conjunct (ii). Unblocks the same four
   axes and keeps a single number per axis.
3. **Ratify as written.** Legitimate if you want every published comparison to be
   against a mode genuinely attempting the same job. Costs four axes until the
   detail instrument lands.
4. **Reject it entirely.** Maximum axes, but a draft mode could then set the
   speed bar, which may fail us for no useful reason.

**If you say nothing, I will proceed with option 1**, because it changes no bar,
softens nothing, and is strictly more informative than any single choice. I will
not treat silence as ratification of the rule itself.

**This is not urgent and it does not block your shoot.** With only blocker `(b)`
cleared, all four options leave exactly M8 and M12 scoreable today. It matters
the moment the detail instrument or the capture lands, which is why I would
rather you saw it now than be asked at the worst moment.

---

---

## What is explicitly *not* being asked

- **No new hardware.** The 2x Viltrox converter every existing capture was shot
  through is the correct part; nothing needs replacing.
- **No re-shooting of existing stacks.** The 68 stacks on disk remain usable.
- **No decision on M8.** It is a software defect and it is mine to fix.
