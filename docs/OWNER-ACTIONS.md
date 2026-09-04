# What the program needs from Chris

One page, decision-ready. Everything here is verified at source; citations are
in `docs/STATUS.md` §2.9.28-2.9.30 and the lane reports named below.

Maintained by the orchestrator. Last updated after lanes M130-M134.

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

**Blocker `(a)`, a working detail instrument, is required by 8 of the 12 axes.
It is the only blocker that cannot be bought, shot, or coded around. It has to
be invented, and it has already defeated several attempts.**

Here is what each step really reaches. This is a mechanical re-derivation from
the blocker table at `docs/proposals/2026-09-sota-scorecard.md:423-434`, not a
summary of one:

| after | clears | reaches | which axes |
| --- | --- | --- | --- |
| `crop-early` (in progress, free) | `b` | **`2 of 12`** | M8, M12 |
| \+ capture session (`$0`, 45-60 min) | `b+c` | **`3 of 12`** | M8, M10, M12 |
| \+ **Zerene `$189`** + a colour target | `b+c+d` | **`4 of 12`** | M7, M8, M10, M12 |
| \+ a working detail instrument | `a` | **`12 of 12`** | all |

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
on `1.030569%` of resampler samples and `1.326144%` of output samples, against
a bar of exactly `0.0000%`. The checker was commissioned in both directions
before it ran, so the failure is real and not an instrument artifact.

**Nothing you can buy or shoot fixes M8.** It is a software defect and it is
being worked now. Tonight's picture changed twice: a promising repair looked
excellent, then failed the control I demanded of it. The honest summary is that
**we no longer have evidence that fixing M8 costs any image quality at all** —
which is better news than it sounds. See the M137 row.

---

## What is being done without you

No action needed on any of these. They cost nothing and need none of your time.

| lane | what | why it matters |
| --- | --- | --- |
| **M130** | Build `crop-early` — **landed** | Every one of the ten blocked axes carries blocker `(b)`, so nothing could be unlocked without this. **Done, verified by me independently, and committed.** The usable area of a cropped stack goes from **64.60% to 96.22%** of the frame — it now passes the ≥80% gate it used to fail — and existing default output is byte-for-byte unchanged. This was one of only two gates on resuming any new build; the other is now running. |
| **M137** | Clamped resampler — **good news, then retracted** | The fear was that fixing M8 costs sharpness. A clamped kernel scored **zero violations across 6,131,678,976 samples** while keeping `99.76%` of what we were calling detail. Then I made it test the measurement itself against a **blank patch of image** — and the blank patch scored *higher* than the detailed one. So that number was never measuring detail; it was measuring amplified noise. Claim withdrawn. **The silver lining is real: we no longer have any evidence that fixing M8 costs image quality.** |
| **M138** | Re-examining a design we declared dead | Phase 1 of the plan — the merge rule the whole roadmap was built on — was declared refuted in September, leaving the plan with no bridge at its first step. **The test that killed it was self-contradictory.** It required a single fixed setting to match a comparator whose own setting deliberately changes across seven frequency bands, to within 5%, and threw out every candidate that failed *before* it ever measured quality. I verified that in the test's own source code. The refutation is withdrawn — **Phase 1 is untested, not dead**, which is a far better place to be. |
| **M135** | A detail measurement we can trust | **Now the single most important thing in the program.** Two separate attempts to measure image detail have now failed the same test: both scored a blank patch as highly as a detailed one. Until we can measure detail honestly, we cannot make a resolution claim at all — and a resolution claim is the whole point. This cannot be bought or shot around. |
| **M136** | The M8 bar itself — **ruled** | We were scoring the resampler for something it cannot control: at long exposures the output format physically cannot represent the correct value, so it counted as a violation no matter what. Ruling: fixing that is a **legitimate repair, not moving the goalposts** — and critically, the repaired bar **still fails our current code** (`31,148` violations) while a clean kernel scores zero. It still bites. |
| **M12** | Formal memory/determinism run | Superseded by the **M139** row below — its blocker has cleared. |
| **M138** | Re-examining a design we declared dead | Phase 1 of the plan — the merge rule the whole roadmap was built on — was declared refuted in September and the plan has had no bridge at its first step ever since. **Answered tonight: the test that killed it was self-contradictory.** See the row above. |
| **M139** | Formal memory/determinism run | Free, ~3.5 hours, no input from you. **Now unblocked** — `crop-early` landed and I verified and committed it. |

---

## Ask 1 — send one email. **$0, five minutes.** No deadline, but do it before any purchase.

**It costs nothing, and it protects the $189 whenever you do spend it.**

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
> Thank you,
> Chris

**If they say yes:** buy the edition they name and `(d)` is cleared.
**If they say no:** you have saved $189 and, far more importantly, we have not
built eight axes on an unpublishable comparison. We would then re-scope `(d)`.

---

## Ask 2 — the capture session. **$0, 45-60 minutes.** *Now the most valuable thing you can do.*

Clears blocker `(c)`, which with `crop-early` reaches **`3 of 12`** (M8, M10,
M12).

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

**Why this comes before the purchase.** Lane M131 ruled that Candidate 2 — the
one route that might have cleared `(a)` from stacks already on disk, at no cost
to you — **does not work**. Its synthetic result is genuine and survives audit,
but it does not transfer to natural renders. Had it survived, $189 alone would
have bought `6 of 12` with none of your time and the order would have reversed.
It did not.

---

## Ask 3 — buy Zerene. **Not $189. The real figure is $925.** *Not yet. Wait.*

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

**Three reasons to wait, none of which is about the money:**

1. **The scoring rules will not let us use it yet.** No comparator can be
   quality-qualified until a replacement M1 is admitted, so five of the axes
   Zerene is meant to unlock stay blocked with it sitting installed.
2. **A licence bought now starts ageing against a program whose gating work is
   measured in research, not weeks.** We already lost one trial that way.
3. **We cannot yet prove the `$660` target would even clear the bar.** M7 demands
   median `ΔE00 ≤ 1.0`. A chart whose *own reference values* carry uncertainty
   near `1.0` cannot support that bar at any price — and the published data does
   not yet state its uncertainty. NIST is explicit that *"traceability alone does
   not signify or guarantee fitness for purpose"*. Worse, our own scorecard
   **specifies no uncertainty budget for reference values at all**, which is a
   gap on our side that I need to close before recommending you spend anything.

**So there is a new `$0` step ahead of this ask:** request ISA's sample
certificate and its numerical uncertainty, which they supply at no charge, and
let me confirm the scorecard accepts a non-Calibrite target. If the certificate
does not support a `ΔE00 ≤ 1.0` bar, the `$660` is dead money and the `$189`
buys nothing — and we will have learned that for free.

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

---

## What is explicitly *not* being asked

- **No new hardware.** The 2x Viltrox converter every existing capture was shot
  through is the correct part; nothing needs replacing.
- **No re-shooting of existing stacks.** The 68 stacks on disk remain usable.
- **No decision on M8.** It is a software defect and it is mine to fix.
