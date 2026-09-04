# What the program needs from Chris

One page, decision-ready. Everything here is verified at source; citations are
in `docs/STATUS.md` §2.9.28-2.9.30 and the lane reports named below.

Maintained by the orchestrator. Last updated after lanes M130-M134.

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
being worked now.

---

## What is being done without you

No action needed on any of these. They cost nothing and need none of your time.

| lane | what | why it matters |
| --- | --- | --- |
| **M130** | Build `crop-early` | Every one of the ten blocked axes carries blocker `(b)`. Nothing can be unlocked without this. |
| **M134** | Clamped-cubic resampler | The M8 failure is entirely the Catmull-Rom kernel. Bilinear fixes it exactly but costs `0.3404` dex of detail. This builds a third option that should cost far less. |
| **M12** | Formal memory/determinism run | Queued for a quiet host, ~3.5 hours. Free. Should close **before** any purchase. |

---

## Ask 1 — send one email. **$0, five minutes.** Do this first.

**This is the highest-leverage thing you can do, and it protects the $189.**

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

## Ask 2 — the capture session. **$0, 45-60 minutes.**

Clears blockers `(a)` and `(c)` **together**, which with `crop-early` reaches
**`4 of 12`**.

Full protocol: `docs/capture-requests/2026-09-319-frame-session.md`.
Needs one dry-run rehearsal at 1.30x first — see blockers 1 and 2 in that file.

**This step is now known to come before the purchase.** Lane M131 ruled that
Candidate 2 — the one route that might have cleared `(a)` from stacks already on
disk, at no cost to you — **does not work**. Its synthetic result is genuine and
survives audit, but it does not transfer to natural renders. Had it survived,
$189 alone would have bought `6 of 12` with none of your time and the order
would have reversed. It did not, so the free step goes first.

---

## Ask 3 — buy Zerene. **$189, or $289 depending on Ask 1.**

Only after Ask 1 answers. Clears `(d)` and, with the above, reaches **`12 of 12`**.

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
