# Captures needed from the owner

Measurements that are blocked on data no existing file can supply. Each entry
says exactly what to shoot, why, and what it unblocks.

---

## START HERE — one session, in value order

*This index was added 2026-08-24 overnight. There are now 18 open requests across
this document and that is not a list anyone can act on over coffee. **Shoot the
first two and stop** if you only have twenty minutes — everything below them is
genuinely useful and none of it is blocking a fix that is already written. (Note
that #2 is an afternoon, not twenty minutes; if you only have twenty, shoot #1
and #3.)*

| # | what | time | what it unblocks |
| --- | --- | --- | --- |
| **1** | **§24** — flat, **achromatic** (grey/black/white, *no colour in the target*), **corner-to-corner** detail, square-on and never moved, shot **normal + red + green + blue** (gels or coloured light) | ~10 min | **Design changed again overnight, and it is now a controlled experiment.** The spectral hypothesis I built this on was tested against eight of your existing stacks and **the correlation came out backwards** (rho −0.69, n=8). What survived is bigger: the correction really does vary by subject, **27.3%** against a 19.5 ppm noise floor, cause unknown. Four rival explanations died on your existing data; aperture and the teleconverter died on your EXIF (**every `-cpl` stack is f/5.6 + 2× TC — there is no aperture variation among the CPL stacks**, so no teleconverter set is needed). A **flat** target makes the stacker a measured 4.8 ppm no-op, so what this sees is optics. See below. |
| **2** | **§26** — a **bright** subject against a **deeply defocused dark** background, exposed **1–2 stops down** so nothing clips, 100–300 frames | ~1 afternoon | **The halo.** As of last night the rim around every edge in your renders has a measured fingerprint — it is exactly as wide as the software's frame-choosing window — but **two explanations survive that predict the same thing on every stack you already own.** They differ only on bright-object-on-dark-ground edges, and your corpus contains **5** usable ones. This is the capture that separates them, and the halo is the largest visible defect in your pictures. |
| **3** | **§25** — one deliberately **clipped, strongly saturated** subject, plus one clipped neutral | ~5 min | Whether tonight's blown-highlight fix generalises past the one case it was measured on |
| 4 | **§12** — static repeat burst, no movement between frames | 30 s | Highest value per unit effort in the whole document — and it **went up in value overnight**: it is the *trap* arm for the election gate now being wired. See the box below. |
| 5 | **§19** — one hard edge at three apertures | ~10 min | The remaining aperture question |
| 6 | **§20** — a grey card somewhere in the frame | ~20 s | Add it to *any* session from now on; costs nothing |
| 7 | **§21** — a straight edge inside a real bracket | — | Decides whether the alignment verdict is about optics or arithmetic |

### Before you read any number below: I had my own bookkeeping audited, and it leans one way

Every number in this document reaches you through one step nobody had ever
checked — me summarising a subordinate's report into a one-line "fact". Last
night I put a verifier on that step, told it to re-derive the underlying data
rather than re-read my summaries, and gave it 25 of my entries.

**8 of the 25 were wrong in some detail. All 8 were wrong in the direction that
made the result sound better than it was.** None weakened a claim. (The verifier
went looking for a weakening error, found two candidates, and killed both — the
code they described turned out to have been written *after* I wrote the entry, so
they were true when written.) Under a coin-flip null, 8-out-of-8 landing on the
flattering side is p = 0.0039.

Two of those errors were in **this document** and are fixed above: a tolerance
I quoted as "±15 ppm" had been lifted from a different experiment and the real
figure is 5× looser; and "no aperture variation in the corpus" should have read
"none among the CPL stacks" — `coffee-bean`, `coffee-bubbles` and `foam` are
f/8, and the `MSDCF` sets are f/11.

**What this means for you practically:** the *direction* of the findings here has
held up well under verification — where I say something is broken, it is broken.
The *magnitudes* are the part to discount. When a number below sounds
impressively precise, assume the honest version is somewhat less impressive, and
ask me for the artefact it came from. I have started citing those instead of my
own summaries.

The failure mode is worth naming, because it is not lying and it is not
sloppiness with labels: every one of the 8 sat in an entry correctly marked
MEASURED, resting on a real measurement. What went wrong was **scope** — a rate
measured at one location described as if it were general, a control presented as
if it were a null, an exception list quietly dropped. That is invisible to any
check that reads the summary, and only visible to one that reopens the data.

### Overnight, 2026-08-25: why your stacks don't look good yet

I found the answer, and it is embarrassing rather than hard. **The project keeps
diagnosing a defect, building the cure, measuring it, writing it up — and never
connecting it to the code that renders your photo.**

I enumerated every module in the codebase and counted what actually calls it.
Of 25, **two were unreachable from the binary**: `outlier.rs` (1094 lines) and
`robust.rs` (544 lines). Both compile. Both have passing tests. Neither had ever
run when you pressed go. The reason they were invisible is a Rust detail —
marking a module `pub` silences the compiler's dead-code warning — so every green
signal was telling the truth about code that did nothing. A third,
`photometric.rs` (1365 lines, 24 passing tests), had **no caller at all** until
one was added, and is still off by default.

**Corrected at dawn, and the correction is small but it is the kind I said I
would start flagging.** `robust.rs` is **no longer unreachable** — a gate was
wired to it at 20:00 last night and `merge.rs` now imports it directly. It is
still **off unless switched on**, which is the thing that actually matters to
your pictures, but "unreachable" is no longer the right word and I had written it
as though nothing had changed. `outlier.rs` (1094 lines) *is* still absent from
the render path — though not unused: four measurement programs import it, which
is how its behaviour came to be measured at all.

**And this turns out to be the general shape of the problem, not a one-off.** I
went through the render path gate by gate this morning. Of the six **switchable**
improvements this project has measured and built, **exactly one is switched on
when you run the tool.** Alignment is on. Chromatic-aberration correction, robust
election, the smoothing prior, the soft gate and photometric normalisation are all
present, all tested, and all **off by default** — so the render you have been judging is
very nearly the unimproved one. Nobody had ever measured what happens with them
on, which is a strange gap for a project this careful, and that measurement is
now running.

**One correction to that paragraph, and I am flagging it because it is the second
time in one night I have made the same mistake.** "Switchable" is doing real work
in that sentence and my first draft left it out. There is at least one measured
improvement that is **not** behind a switch and *is* running in your renders: the
magenta-highlight fix. Blown neutral whites used to render magenta, because white
balance pushes red and blue past the point where green has already pinned at the
sensor's maximum, and the colour matrix then reads that as a strong colour. The
fix brings a clipped pixel back under a neutral ceiling **before** the matrix sees
it, and it measured **2.00 % of pixels affected down to 0.51 %**, with the
overshoot eliminated entirely. It is safe by construction rather than by tuning:
where nothing is clipped it is exactly the identity, so an unsaturated stack
cannot move by a single bit. So the fair summary is that the *switchable*
improvements are almost all off, not that only one improvement exists in your
output. Two cautions on it, both already found: switching everything on is
*not* obviously right — on a stack that drifted, the merge measurably **loses**
to a single frame — and at least one gate is a **silent no-op** unless another is
also on, which means a naive test of it would have read "does nothing" and been
believed.

`robust.rs` is the one that matters, because of something already measured on
your `foam` stack. When a subject moves between frames, the moved frame shows a
**displaced** edge — and a displaced edge is *sharper* than the correctly-focused
stationary one. So motion doesn't just survive the "pick the sharpest frame"
step, **it wins it**. **4.78 % of that stack's output pixels come from a frame
more than 8 sigma out of agreement with its neighbours.** That is a sharp, wrong
pixel, and it is exactly the kind of thing that makes a render look subtly bad
without looking obviously broken.

The same measurement priced the fix at two possible places: catching it at the
election removes **100 %** of those pixels, catching it later in the averaging
recovers **6 %**. `robust.rs` is the election-time version.

**Update, later the same night: I said this was being wired in tonight. It is
not, and the reason is worth more to you than the fix would have been.**

I commissioned the work. It came back with a flat refusal to ship, and the
refusal is well-argued. Tested against your real captures rather than a
synthetic test case, the detector **fires on 29.55% of a perfectly stationary
subject** — and fires **4.3× *less* on the moving subject than on the stationary
one.** It is backwards. What looks like a motion detector is substantially a
**texture** detector: it separates motion from defocus by 2.12× in a case where
the actual displacement separates by 0.96×, which is to say not at all. It also
does not react to a planted displacement anywhere below a full pixel. Four of
its six pre-registered criteria failed.

**This is now the fourth time this project has built or specified this mask and
then declined to ship it** — and that is the part I got wrong. Three prior
milestones had already tested it on real captures and reached the same place;
one of them had *derived* why the answer must be no; and the module's own source
code carries a regression test whose name says so outright. **I commissioned a
fourth attempt without reading the three that came before it, which is a rule
this project has written down and which I broke.** The agent found them in
twenty minutes, said so, and refused to re-ask the closed question.

So: **the moved-frame problem above is real and remains unfixed.** What I told
you about the defect stands. What I told you about the cure was premature, and I
would rather correct it here than have you discover it by finding the switch
missing.

**And a fifth confirmation landed overnight, on a different mechanism, which
makes this about as settled as anything in the project.** Everything above
concerns one detector. A *separate* piece of machinery — the one that picks
which frame wins at each pixel — was wired up behind a switch and tested against
a deliberately unfair pair of your own stacks: a stack **with** real motion
(`foam`, bubbles moving) and a stationary tripod stack (`coffee-bean`) where any
firing is wrong by definition, because a frame that disagrees there disagrees
only because **it is the only frame that resolves that pixel**. The result was
the same shape as before: it changed **7.4%** of the stationary stack and
**0.34%** of the moving one — **21.5× more activity on the subject that never
moved.** The report's own verdict is that this is not a threshold wanting
tuning, it is a statistic aimed at the wrong quantity.

**Why I am telling you about a negative result twice.** Two different mechanisms,
built by different agents from different starting points, both fired hardest on
the stack with nothing wrong with it. That is no longer bad luck. It says the
*idea* — spot the odd frame out by how much it disagrees — cannot work here,
because in a focus stack the frame that disagrees most is usually the frame that
is **right**: it is the one in focus. That is peculiar to focus stacking and it
is why techniques borrowed from ordinary burst photography keep failing on this
problem. The moved-antenna defect is still real and still unfixed; what is now
well established is which family of cures does not apply to it.

### The answer changed by morning, and you should read this instead

The section above says the reason your stacks don't look good is *unwired code* —
cures that were built and never connected. I spent the night testing that, and
**it is not the main answer.** Three of the four things I expected to wire up
were measured and refused: the motion mask (above), the soft gate (rejected a
fourth time), and — the big one — **the sharpening idea I had been building the
whole roadmap around.**

That last one deserves a plain statement, because it changes what I can promise
you. I had a thesis that at your magnification no stacker can produce a sharp
image by *choosing* the best frame, and that sharpness had to be *reconstructed*
across frames instead. Measured against what your stacker already ships, it buys
**nothing** — a signal-to-noise ratio of 1.0014, with an error bar tight enough
to rule the effect out rather than merely fail to find it. The apparent
sharpening was 2.5× more contrast bought with 2.0× more noise, and roughly a
third of its output pixels were values **that appear in none of the source
frames** — invented.

**So here is the honest headline, and it is a demotion.** There is currently
**no known route to producing more detail than the sharpest frame you actually
shot.** The remaining work is not about out-resolving your camera. It is about
not degrading what you already captured — which, on the evidence of tonight, the
merge is doing in two specific and now well-characterised ways:

1. **The halo** around every leg and edge. Structural — but as of the last hour
   of the night it is no longer *unexplained*, and that changes what happens
   next. See *"The halo finally has a cause"* immediately below.
2. **The background patchwork.** Structural, and as of tonight **proved** rather
   than asserted — see the correction further down. Caused by the blending
   recipe changing from place to place across the frame.

#### The patchwork has a mechanism too, and it is in the render you have

The blotchy, faceted look in your out-of-focus backgrounds is now measured
rather than guessed at, and the first thing to say is a correction: **it is in
the tool's normal output**, not only in the debug image I had been looking at.
I had told you the shipped render was clean. It isn't, and the file I based that
on turned out to be a different geometry.

There is now a **proof-backed test** for it, which is better than a threshold
somebody picked. If every pixel of the output were blended the same way, a
particular contrast ratio cannot mathematically exceed **1.284**. Your render
measures **4.337** — so the blending demonstrably varies from place to place,
and no amount of arguing changes that. A plain average scores 0.343 and a single
frame 0.308, both comfortably legal. It reproduces on a second subject.

**The cause is subtler than I expected, and it explains why it has been so
stubborn.** The software is not confused about focus — the winning frame stands
at 15× the noise floor, so it genuinely knows what is sharp. The problem is that
the *runner-up* is almost as good: the gap between first and second place is
small, and frames that are nearly tied in focus can differ in **brightness by up
to 28%**. So the set of frames blended shifts slightly from pixel to pixel, and
each set averages to a slightly different level. That is a **bias, not noise** —
which is why it survives averaging **167 frames per pixel** and would survive
any number.

**What fixes it, and what doesn't.** Normalising the frames' brightness before
blending is the largest measured lever: it takes 4.337 down to **1.697**, a 61%
reduction — but 39% of the excess remains, still over the legal bound. The
smoothing-style gate is predicted to roughly halve it and also not to clear the
bound. Turning the gate up until it *does* clear only works by averaging
everything, which throws away the focus stacking. **So the honest position is
that we know the mechanism, we have one lever worth more than half of it, and
the last part is not yet solved.** That last part is real work, not a switch.

#### One suspect left, and finding out which it is settles the whole question

By dawn the search for your missing sharpness had narrowed to a single
possibility, which is worth more than any of the individual results that got it
there. Four candidates went in; three are now closed:

- **Reconstruction is out.** The measurement is complete and null (above).
  There is no clever mathematics that recovers detail the optics never passed.
- **The blending is out.** A milestone spent the night proving, pixel by pixel,
  that where the software picks a frame it reproduces **that frame's pixels
  exactly** — 180,697 pixels checked, 100.0000% identical, maximum error zero.
  It also proved the check can fail: pixels the software *didn't* pick match at
  0.0519%. So nothing is being lost or muddied in the act of combining.
- **The halo is not a blending problem either.** Two milestones, working from
  opposite directions and different statistics, independently concluded the rim
  comes from *choosing* rather than from *averaging*.

**What is left is the choosing itself.** The software provably delivers the frame
it selected — but nobody has yet checked whether it selects the *best* frame. If
its focus detector systematically settles one or two frames off the true peak,
every pixel would be faithfully, exactly, reliably slightly soft, and every test
above would still pass. That measurement is now running.

**Why this is good news rather than bad.** A selection error is *cheap to fix* —
it is a better focus detector, not new physics, and the machinery to test one
already exists. It is also the one remaining explanation consistent with what you
said you saw: results that look *close* to right rather than obviously broken.
If it comes back clean, then the tool is already extracting everything your
captures contain, and the remaining gains are in how you shoot rather than in
the software.

#### The halo finally has a cause

For weeks the honest answer about the bright rim around every leg and antenna
was "we can see it, we can measure it, we don't know what makes it." That ended
tonight. Two measurements, and they agree:

**It is exactly as wide as the patch the software uses to decide which frame is
sharpest.** The rim's half-width measures **10.0 px**, it dies out by **13.3
px**, and the region where the frame-choice disagrees with its surroundings
measures **10.5 px** — against a decision window whose radius is **13 px**,
written into the code as a fixed constant. Nothing else in the pipeline has that
size: not the blur, not the focus step, not the bugs. The rim also *ends*, which
matters — a lighting gradient would not.

**And it is a choosing problem, not a blending problem.** Turn the blending off
entirely — pick one winning frame per pixel, no averaging at all — and the halo
is unchanged (**+0.066** against **+0.063**). So the rim is not something the
merge paints on. It is the software **electing the wrong frame** in a band around
every edge, because the patch it looks at straddles both sides of the edge and
sees the foreground's sharp contrast leaking across.

That is a real diagnosis and it names the direction of a fix — make the decision
patch aware of edges rather than a fixed square. I want to be careful about one
thing, though, because the agent that found this argued against itself and was
right to: **a window-sized mark only proves a window is involved, not which
window effect it is.** My own proposed explanation was tested against a
held-out class of edges and **rejected**. So there is a fix direction, and there
is not yet a fix.

**There is a ten-minute capture that would settle it** — see §26 at the bottom.
It is the highest-value thing you could shoot this week.

**A third measurement landed at the end of the night, and it is the bluntest one
yet.** An independent check re-rendered *all 100 frames* of three of your stacks
and scored the merge against the best single frame — not on sharpness alone,
which turns out to reward leftover noise, but on sharpness *minus* what the merge
does to your flat backgrounds. Both sides were run **with alignment switched
off**, so this is not a verdict on the default path, and I want that limitation
in the sentence rather than in a footnote. With that said:

| your stack | lighting drift | merge vs. best single frame |
| --- | --- | --- |
| `bee-3-cpl` | 1.6% | **merge wins, and not narrowly** — 0.61 vs 0.15 |
| `tweezers-cpl` | 13.8% | **the single frame wins** — 0.84 vs 0.37 |

On `bee-3-cpl` the merge does exactly what it should: it *quietens* the
background while keeping detail. On `tweezers-cpl` it does the opposite — it
makes the background **worse** than the single frame it started from, and that
is the blotching you can see. Two subjects is not a law, but it points the same
way as the 14-stack result below, from a completely different statistic: **the
merge is helping you on stacks where the light held still, and hurting you on
stacks where it moved.** That is the most useful thing I learned all night,
because it tells you which of your own pictures to trust it on today.

And one genuine gain, the only thing tonight that both explains a defect you can
see *and* hands you something to do about it: **the background blotching is
caused by your lighting drifting between frames**, confirmed across 14 of your
stacks. There is a switch for it, it is a large win on stacks where the light
really moved, and it slightly *hurts* on stacks where it didn't. The rule and
your own stack names are under *"When to turn the exposure fix on"* below.

I would rather hand you an accurate demotion than an optimistic roadmap. The
architecture is sound and the measurement discipline is doing its job — three
bad ideas died last night before they could ship, and each of them would have
shipped in a project that didn't test its own cures.

**Then I found a third instance of the same pattern, and this one is the most
likely single reason your photos look the way they do.** Code being unreachable
is one failure. Code being reachable and *switched off* is the same failure
wearing a disguise, and no compiler or test will ever mention it. So I read every
quality switch on the render path and wrote down its default. **There are seven.
One is on.** Registration is on. The halo correction, the exposure-drift
correction, the chromatic-aberration correction, the soft admission gate and both
alignment-smoothing terms are all off. What you have been looking at is
*registration plus a plain average* — the honest baseline the project was built
to improve on, with essentially every improvement it has measured left switched
off.

#### The seven switches, by name

*Added later the same night. The paragraph above told you seven switches exist
and then didn't tell you what any of them were called, which is a report rather
than something you can use. Here is the switchboard. Every one is an environment
variable, so you can try any of them without a rebuild.*

| switch | what it does | default | verdict tonight |
| --- | --- | --- | --- |
| `STREHL_ALIGN` | registration | **on** | Leave it. Setting `0` disables it, which is a negative control, not an option. |
| `STREHL_PHOTOMETRIC` | per-frame exposure-drift fit | off | **The one to try — but not on every stack.** Now measured across 14 stacks: it removes manufactured blotches **when your frames actually drifted in exposure**, and mildly *worsens* them when they didn't. The rule and the numbers are in *"When to turn the exposure fix on"* below. Also available as `--photometric`. |
| `STREHL_SMOOTH` | alignment track prior | off | Honest verdict, quoting the code: the win was measured *on the solve* but **could not be shown in a render**. Try it; expect to see nothing. Takes a number, e.g. `1.0`. |
| `STREHL_SMOOTH_HUBER` | robust threshold for the above | 1.0 when `STREHL_SMOOTH` is on | Don't set it independently. It only does anything when the line above is on. |
| `STREHL_FIX_HALO` | fringe around silhouettes | off | **Leave off.** Off for a good reason, unlike the rest — see the withdrawal above. It replaces the fringe with a milky scalloped band and fires hardest on scenes with no halo in them. |
| `STREHL_SOFT_GATE` | soft frame-admission gate | off | **Leave off.** Rejected twice now, by two independent methods. It scores beautifully and it is a blur — see tonight's near-miss below. |
| `STREHL_FIX_CA` | chromatic aberration | off | **Worth turning on for your own frames — but it is not set like the others.** The audit landed; see below. It takes a **profile name**, not `1`. Two known bugs: typing `STREHL_FIX_CA=1` is a deliberate *error* (it refuses to guess which lens you used), and it is a **silent no-op when `STREHL_ALIGN=0`** — byte-identical output, no warning. |

So of seven switches, **two** are worth flipping this morning — the
exposure-drift fit on any stack, and the chromatic-aberration correction on
frames shot with your own rig — two are actively harmful, one does nothing you
can see, one is subordinate to another and one is already on. That ratio is the
honest state of the project: the measurement machinery is far ahead of what has
been proven safe to ship.

To try the first of those two:

```powershell
$env:STREHL_PHOTOMETRIC = "1"
```

and unset it with `Remove-Item Env:\STREHL_PHOTOMETRIC`. It costs about
**+3.7 s** on a stack, and on `tweezers-cpl` it was actually *faster* than the
default. **Look at it at 100% on a smooth out-of-focus background** — it is a
correction to flat areas and it is invisible at full-frame scale.

#### The chromatic-aberration correction: turn it on for *your* frames

*The audit finished after I wrote the table above, and it changed the verdict
from "pending" to a qualified yes — plus it caught me overstating the case.*

**The correction is finished and it works.** It is off by default because it was
fitted on your gear alone, and the software has no way to tell whether a given
file came from that gear. On your A7C II + FE 100 GM + 2× TC + X4 CPL shots:

```powershell
$env:STREHL_FIX_CA = "a7c2-fe100gm-2xtc-x4cpl"
```

**Type it exactly** — the key is case-sensitive, and `STREHL_FIX_CA=1` is a
deliberate *error* rather than an on-switch, because the code refuses to guess
which lens you were using. A typo is also an error rather than a silent
no-op, which is the right call. One real bug to know about: with
`STREHL_ALIGN=0` it does nothing at all and says nothing about it.

**One more thing about that key, found overnight, and it changes when you should
use it.** The name claims four pieces of gear — body, lens, teleconverter,
polariser. Your camera records the first three: every one of your 24 stacks says
`ILCE-7CM2` and `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, and the
teleconverter is even recorded twice, in two independent fields. **But the CPL is
invisible.** Your `-cpl` stacks and your bare stacks are *byte-identical* in every
identity field — a filter screwed onto the front of the lens is not something the
body can see. So the software cannot check the last quarter of that key, and I
have to tell you what follows from that: **every chroma number I quoted you was
measured on frames shot through the CPL.** Whether the same correction is right
for a frame shot *without* it is untested, and — this is the uncomfortable part —
**not something the tool can detect and warn you about.** Use it on CPL frames,
where it is evidenced. On bare-lens frames, treat it as a guess and compare.

What you should expect to see: edge chroma down **~29%** right at the fringe,
**~20%** in the near-edge region, and **~5%** across the whole frame on
`bee-3-cpl`. Two agents and I looked at 5× crops and independently thought it
clearly better.

**Three caveats, and I want to be straight about the third.** Fringes get
**fainter, not thinner** — the width is unchanged. What residual remains is
**red-biased** rather than neutral. And it has never been tested against the one
control that would prove the improvement comes from the correction rather than
from the resampling it happens to do along the way.

**I also have to correct myself here.** I earlier described this as a "61.0%
edge chroma reduction". The audit established that number is real but that I
described it wrongly, and that I had quoted **the largest of five available
numbers for the same effect** without the qualifier that makes it mean what it
means: it is the fall in edge-localised chroma *excess*, measured as a contrast
against a baseline five pixels away — not the amount of chroma removed. The
honest numbers are the ~29% / ~20% / ~5% above. This is the second time tonight
that a headline in this document turned out to be the most flattering member of
a family of numbers, and both times it was an agent auditing my work that caught
it rather than me.

**Worth turning on for your own frames. Not safe as a default for anyone
else's** — and that distinction is the whole reason it stays off.

**One more reason to turn it on, which arrived later the same night.** A separate
milestone tested a sharper resampling kernel (`lanczos-3`) against the one that
ships, and a non-author looking at 1:1 and ×3 crops found it **visibly crisper**
on ink grain and on the bee's ommatidia, with no dark rim on silhouettes. It also
found that the sharper kernel makes **colour fringing more conspicuous** — which
is the second independent sighting of something this project predicted: the
kernel that currently ships has been **hiding the fringing with blur**. So the
chromatic-aberration correction is not a side tidy-up. **It is a prerequisite for
ever shipping a sharper render**, and tonight is the first night both halves
exist.

You cannot try the sharper kernel yet — there is no `--resampler` flag on
`strehl stack`, so its 2.9–3.9× cost cannot be declined, and the milestone that
measured it correctly refused to promote something you have no way to turn off.
That flag is the next small thing to land. I mention it because it is the one
place tonight where two separate results **compose** into a path forward rather
than cancelling each other out, and there has been little enough of that.

#### The near-miss: why the soft gate says "leave off" twice

*This is the most instructive thing that happened tonight and it is the reason
the table above has only one recommendation in it.*

Having found that the exposure-drift fix removes the background blotches, I
scored the other candidates on the same statistic to see whether any did better.
**Three of them did — all of them, on every subject, by a wide margin.** Lower is
better here, since the number is how much of the blotchiness survives:

| switch | on `bee-3-cpl` | on `tweezers-cpl` |
| --- | --- | --- |
| exposure-drift fit (the one I'd just verified) | 1.064 | 0.710 |
| soft gate, gaussian | **0.808** | **0.553** |
| soft gate, exponential | 0.819 | 0.562 |
| both together | 0.809 | **0.544** |

On the numbers I had just used to promote a fix, the soft gate beat it
everywhere. I came very close to writing it up as the better answer.

**It is a blur.** The check that caught it costs almost nothing: alongside the
smooth patches where blotches live, measure a **textured** patch where removing
detail is forbidden. The exposure-drift fix leaves texture alone — **1.037** on
bee, **1.027** on tweezers, i.e. untouched. The gaussian soft gate cuts the
textured patch by **30.5%**, as much as it cuts the smooth ones. Then I looked at
it: leg hairs smeared, a small highlight gone entirely. It scores well on
"blotchiness removed" for the same reason a smear of vaseline would.

Two things worth taking from this:

- **It agrees with a completely separate rejection.** An earlier milestone had
  already turned the soft gate down using a different statistic, on different
  pixels, for a different reason. Two independent methods reaching the same
  verdict is far stronger evidence than either alone, and it is why that row says
  "leave off" rather than "not yet".
- **The general form, which now applies to every future candidate here:** any
  measure that rewards *removing* something is maximised by removing
  everything. It has to be paired with somewhere removal is forbidden — and that
  pairing has to **decide the ranking, not sit beside it as a footnote.** Had I
  reported the control as a caveat rather than a gate, the table above would be
  recommending a blur to you this morning.

I then built the check so it cannot be skipped next time — one script that scores
both things at once and refuses to pass anything that fails the texture side. It
reproduces the verdicts above with nobody looking at the pixels, and before it
will report on a real candidate it has to be handed a **deliberate blur** and
caught it. It catches it on all three of your stacks.

**Doing that turned up something I had not seen, and it is the part worth
remembering.** The soft gate only reveals itself as a blur on **one of your three
stacks** — the bee. On `foam` it does nothing measurable either way. And on
`tweezers-cpl` it not only passes the texture check, it posts **the best scores
of any candidate I have measured**, better than the fix I am actually
recommending. Tweezers is also the stack where the exposure-drift win showed up,
so it is the obvious one to test on. **Had I tested on your tweezers stack alone
— the natural choice — I would have promoted the blur, and its own control would
have cleared it.** Averaging across the three does the same damage, because two
of them are silent and dilute the one that saw it. So the rule is now: take the
*worst* stack, never the average, and a candidate that blurs anywhere is not
excused by scoring well elsewhere. This is the strongest practical argument for
you shooting the variety of subjects you have — a defect that is invisible on two
of three stacks is not a rare defect, it is a defect you got lucky about.

**I then spent two hours promoting the wrong one, and the correction is worth
recording because you would otherwise have read it here as fact.** I picked out
the halo correction — the fringe around silhouettes — because its source notes
record it removing **87.9 %** and **84.6 %** of the halo on two of your stacks. I
wrote that it was the thing you would actually see, and put it first in tonight's
measurement queue. Then one of my own agents checked the claim against the report
it came from and found three things I had not read:

- **Those numbers are from a pipeline that does not ship.** They are crops of an
  unaligned merge with the gate off. On the path you actually run, the figure is
  **72.9 %** — I quoted a number fifteen points high.
- **The report's author explicitly recommends against enabling it.** The relevant
  section is *titled* "why I am telling you not to enable it." The fringe gets
  replaced by a **smooth, milky, scalloped band**, and the author's verdict is
  that **it looks worse**.
- **It fires hardest where there is nothing to fix.** On a test scene with no
  occlusion at all, it moves **100 %** of the pixels it looks at, against 39 % on
  a real occluding edge — two and a half times more aggressive on a scene with no
  halo in it. Its error against known truth rises monotonically with dose while
  its apparent improvement does not.

So the halo correction is off, and unlike the other five it is off **for a good
reason**. I have withdrawn it from the top of the queue.

### Then I looked at your photos, and it reordered everything

This is the part I am least proud of and it is the most useful thing in this
document. The project has run 120 milestones, written 156 research reports and
recorded 1600 facts. **Tonight was the first time I opened one of the rendered
images and looked at it.**

Ten minutes of looking found a defect that had no milestone, no metric and no
name anywhere in the corpus. I then spent the rest of the night measuring it, got
it wrong once in a way worth telling you about, and ended up **reordering the list
of what is actually wrong with your pictures.**

#### What I found: the background is partly crazy paving

**Open `C:\dev\strehl-out\ORCH-morning\AB-SHARED-STRETCH.png`.** Three panels,
same pixels, same contrast stretch, so a smoother panel genuinely looks smoother.
The right-hand panel is one of *your* frames straight out of the camera: a soft,
slightly grainy, out-of-focus background. The left-hand panel is what a stacker
with its safety switch turned off does to it: **hundreds of flat polygons with
hard edges.** Crazy paving. It is not photographic — a smoothly out-of-focus
background is a smooth gradient and cannot contain hard-edged polygons.

I built a detector for it, and the number I trust most is this one: run it over
**one of your unmerged frames** and it reads **0.05**. Run it over the merged
output and it reads **34**. The signature is not in your photographs. The
software is putting it there.

#### Then I got it wrong — repeatedly — and the corrections matter to you

I spent several hours measuring that mosaic before checking what the file I was
measuring actually *was*. It turned out to be a **deliberate negative control** —
a build with the protection switched off, which the project keeps around
precisely because it is supposed to look bad. I had been carefully measuring a
known-bad configuration and describing it as your stacker.

Then I built a detector to find the mosaic in the real render, and **the detector
turned out to fire on your unmerged photographs too** — three times out of
twelve, harder than it fired on the merge. And the comparison I had been quoting
put a render of *one* subject against a frame of a *different* subject, which
compares nothing at all.

So I threw all of that out. I would rather hand you a smaller true result than a
larger one I cannot stand behind. Six things I claimed tonight are now formally
withdrawn in the project record, and — this is the part I found genuinely
interesting — **every single one of the six was an error in what I was comparing
to what, not in how I measured it.** The arithmetic was right every time.

#### What actually survives, measured on identical pixels

The one comparison that holds everything constant — same scene, same geometry,
same pixels, one contrast stretch shared across all panels — is
**`C:\dev\strehl-out\ORCH-morning\AB-SHARED-STRETCH.png`**. Open it. Three
panels:

- **Right:** one of your frames straight from the camera. Soft, slightly grainy,
  out of focus. What a background should look like.
- **Left:** the same pixels with the protection switched off. Crazy paving.
- **Middle:** the same pixels as your stacker actually ships. **The paving is
  gone.**

Numerically, against the noisiest of your own input frames, the amount of
structure the stacker adds that is in none of your photographs falls from
**2.13x to 1.11x** when the shipped protection is on, and the number of sampled
patches that fail the test falls from **12 of 12 to 7 of 12**. So: the shipped
stacker is much better than the crippled one, and **it is still measurably
inventing texture in more than half the background patches I sampled.**

#### Correction, later the same night: "the paving is gone" was too strong

A milestone went back over this with a better instrument and I have to walk that
sentence back. **The paving is not gone from the shipped render. It is reduced.**
That milestone also retracted its own earlier claim that the shipped render was
clean, so we both had it wrong in the same direction.

What makes the new measurement better than mine is that it does not rely on
comparing your render to anything. It **derives a ceiling**. Take a patch of
background where *all 299 of your frames are featureless* — nothing there, in any
of them. Any stacker that works by blending whole frames together with a fixed
recipe **cannot** produce more than a certain amount of fine structure in that
patch. That ceiling works out to **1.284** on their scale, where one of your own
frames sits at 0.31 and a plain average of all 299 sits at 0.34.

**Your shipped render reads 4.337.** That is **3.4× above a ceiling it should not
be able to cross at all.**

That is a proof rather than an opinion, and it is worth more than my earlier
number because nobody can argue with it on taste. It says something specific:
the structure is not coming from your photographs, and it is not coming from the
blending *recipe* either — it is coming from the recipe **changing from place to
place across the frame**. Neighbouring areas get built from different mixtures,
and the seam between two mixtures is a visible edge.

Three other things they nailed down, all of which kill explanations I had offered
you:

- **It is not that the background is "just noise" and the stacker is guessing.**
  I had assumed the out-of-focus background carries no real signal, so the
  software picks essentially at random. Wrong: the signal there stands **15×**
  above the noise floor. It is choosing on real information.
- **It is not that each patch comes from one different frame.** I said that too.
  In fact the shipped stacker averages **167 of your 299 frames** at each pixel.
  Averaging 167 photographs is supposed to be what makes artifacts *disappear* —
  this one survives it, which makes it a more serious defect than I described.
- **Turning the quality gate up does not fix it.** It reduces it by 39% and
  leaves it far above the ceiling.

The honest summary: **this defect is real, it is in the picture you are actually
getting, it is now proved rather than asserted, and I do not have a fix for it.**
It sits alongside the halo as an open structural problem, and unlike the halo I
now at least know exactly what to blame — spatially varying weights — which is a
better starting point than I had this morning.

#### And that demoted the mosaic, because the halo is worse

The same comparison answered a question I had not thought to ask. The protection
that removes the mosaic **leaves the halo completely untouched** — the bright
outline tracing every hair, leg and antenna, the "cut-out sticker" look. In the
middle panel the paving is gone and every hair still has a bright rim around it.

That flips the ranking. The halo is on **every** silhouette in **every**
configuration, and **we have no working fix for it** — one candidate works and
makes the picture look worse, the other does nothing at all.

**The ranking by eye, which is now the ranking I am working to:**

| | defect | status |
| --- | --- | --- |
| **1** | Bright halo tracing every silhouette — the "cut-out sticker" look | Real, severe, on every edge, in every configuration. **No working fix.** One candidate looks worse, the other is a no-op. A dedicated agent is on the mechanism tonight. |
| **2** | Background texture the stacker invents | Real: 1.11x more fine structure than any of your frames, in 7 of 12 patches. **A fix is now measured and it works — see "One thing I fixed tonight" below.** |
| **3** | Lateral chromatic aberration — coloured fringes on bright edges | Confirmed by my own eye. Correction exists, switched off, **under audit** — see below. |
| **4** | General softness | Expected: at your magnification the optics are the limit, not the software. |

On **#1**, one correction to something I told you earlier tonight: I said the halo
fix was the thing you would see. It is not, and I checked that myself rather than
taking an agent's word for it — I compared before and after by eye and the
"after" is milky, with background detail washed away. The report's author was
right and I was wrong to overrule him. But **the halo itself is real**, and
withdrawing the cure is not withdrawing the diagnosis: look at
`C:\dev\strehl-out\crop-leg-halo.png` and you will see a bright scalloped band
tracing the whole leg and both claws.

On **#3**, I am deliberately *not* telling you to turn the chromatic-aberration
correction on yet. I promoted one correction tonight on a headline number that
turned out to be fifteen points wrong and to come from a section whose title was
"why I am telling you not to enable it." A second agent is auditing the CA
numbers the same way before I put them in front of you again. If it clears, that
is a real win and it is one line to enable.

**What this needs from you: §12.** A static repeat burst is the arm that proves
the protection *doesn't* fire when nothing moved. Right now that has to be
simulated. Thirty seconds of your time replaces a simulation with your actual
camera, your actual sensor, your actual noise.

**Also running tonight:** a campaign measuring every default-off improvement on
your real captures and writing before/after 1:1 crops to `C:\dev\strehl-out\M116\`
— look there first in the morning.

### One thing I fixed tonight — look at this first

**Open `C:\dev\strehl-out\ORCH-morning\PHOTOMETRIC-tweezers-cpl-smooth-912x400.png`.**

Left is what the stacker ships today. Right is the same pixels with one switch
turned on. Both panels have exactly the same brightness stretch, so what you are
seeing is a difference in the picture and not in how I displayed it.

The left panel is a patch of out-of-focus background and it is covered in dozens
of soft oval blotches. **Those blotches cannot be real.** An out-of-focus region
is blurred, and blurring cannot put structure *into* a picture — so anything at
that scale was manufactured by my software. On the right they are gone, and you
get the smooth gradient a defocused background is supposed to be.

**Why it happens.** Your frames are not all the same brightness. Across one of
your brackets the level drifts by 3 to 8 percent from the first frame to the
last, smoothly, and I measured the same thing on four of your other stacks. The
stacker picks a different frame for different parts of the picture — that is its
job — but it was pasting those pieces together without correcting for the fact
that they were lit differently. Each patch arrived at its own brightness, and
you get blotches. Fitting a per-frame brightness before merging removes them.

**It is not blurring the picture to get there** — that was the first thing I
checked, because it is the obvious way to fake this result. In
`PHOTOMETRIC-tweezers-cpl-textured-400x656.png` the tweezer edge, its grain and
the speckled texture are identical on both sides. It costs about 4 seconds on a
50-second stack, and on one of the three subjects it was actually *faster*.

**Set your expectations before you look at the whole frame.** I also put the two
full pictures side by side in `OWNER-tweezers-cpl-full.jpg`, and at that size
**you will not be able to tell them apart** — I can't either. This is a
correction to smooth, out-of-focus areas viewed at 100%, not a change to the
photograph as a whole. It is worth having because manufactured texture in
backgrounds is the kind of thing that looks like grain or mush when you print
big, but I am not going to pretend it transforms the image. The thing that
*would* transform the image is the halo at #1, and I do not have that yet.

### When to turn the exposure fix on — the rule, measured across 14 of your stacks

Later the same night a separate milestone asked the question I should have asked
before recommending anything: **is the blotch actually caused by exposure drift,
or does the fix just happen to help on the one subject I looked at?**

**It is caused by exposure drift.** Across 14 of your stacks, how much the fix
helps tracks how much your frames drifted, at a correlation of **+0.70** with a
1-in-285 chance of arising from luck. Two other things back it up independently:
the correction the code fits for itself tracks the drift just as strongly
(+0.77), and the obvious objection — *"smooth backgrounds are just smooth"* —
was written down in advance and then **refuted**, with the relationship coming
out *stronger* once baseline smoothness was accounted for, not weaker.

**But it is not free on every stack, and this is the part that changes your
advice:**

| your stack | how much it drifted | what the fix does to the blotch |
| --- | ---: | --- |
| `tweezers-cpl` | 13.8 % | **29 % less blotch** — the big win you can see in the PNG above |
| `coffee-bean` | 12.1 % | 9 % less |
| `bee-1-cpl` | 11.3 % | 5 % less |
| `113MSDCF` | 8.0 % | **7 % worse** |
| `bee-3-cpl` | 1.6 % | **6 % worse** |

**So: turn it on when the light actually moved between frames; leave it off when
it didn't.** Flash or steady continuous light on a short bracket won't drift, and
there the fix has nothing real to correct and gently makes things worse. Daylight
changing, a battery-powered lamp sagging, or anything long enough for the light
to wander — that is where it pays, and it pays *well*.

That failure on two stacks is exactly why it is still off by default: a
pre-registered rule said *no stack may get more than 3 % worse*, and those two
broke it. **The cause is confirmed; the fix is not yet good enough to impose on
everyone.** Those are two different questions and I want to be careful not to let
the strength of the first one argue for the second.

**One honest caveat about your own headline picture:** `bee-3-cpl` — the bee — is
one of the two that gets *worse*. Its light barely moved (1.6 %). So for the bee,
leave this off. For the tweezers, turn it on.

**What I am not claiming.** I have this on one of three test subjects. On the
other two the switch does nothing visible — and for the bee I know why: its
background is already cleaner than the *fixed* version of the tweezers shot, so
there was never anything there to remove. That is consistent with the
explanation rather than a hole in it, but "consistent with" is not "measured".
A campaign is running now across every stack you have given me, to check whether
the blotches really do track the brightness drift. **If they do, this becomes the
default and you never have to think about it again.**

One more thing worth saying plainly: another agent measured this same switch
tonight, with a careful pre-registered campaign, and concluded *leave it off*. It
was not wrong. It scored the switch on **sharpness**; the switch does not change
sharpness, so it failed a sharpness threshold — while doing something quite
visible to **tone**, which nothing was measuring. Its own numbers never went
below zero on any subject. I only found this because I went looking with a
different ruler.

### The big idea I was betting on died last night, and you should know it

**This is the most important thing I learned overnight and it is bad news, so I
want it stated plainly rather than buried in a fact table.**

The outside review of this project made five ranked recommendations. Its number
three — and the one I agreed with most, and had already started building toward
— was that at your magnification **no amount of picking the sharpest frame can
produce a sharp image, because the sharpness isn't in any frame to begin with.**
The optics argue it well: at 2:1 on your rig, contrast at fine detail is
essentially zero at every aperture before any software runs. The proposed answer
was *reconstruction* rather than selection — a multi-frame Wiener deconvolution
that uses this project's two genuine assets, the measured lens blur and the
calibrated noise model, to buy back contrast the optics destroyed. The argument
was that those two assets are exactly what makes aggressive deconvolution safe
here and unsafe everywhere else.

I had a milestone measure it rather than build it. **It failed, and it failed
cleanly:**

- Against the gated average **the stacker already ships**, the signal-to-noise
  ratio came out at **1.0014**, with a 95% confidence interval of
  **[0.965, 1.038]**. That interval contains no useful gain in either direction.
  It is not a close call that better tuning would rescue.
- It looks sharper because it **moves information around rather than adding
  any**: contrast up 2.51×, noise up 2.03×. That is the trade every
  sharpening slider in every photo editor already offers you.
- It rings. Between **29.5% and 36.4%** of output pixels landed *outside the
  range of values present anywhere in the source frames* — meaning invented
  detail — with the halo peaking at **70.7%** in the ring 8–16 px out from an
  edge. Every non-deconvolution arm tested scored exactly **0.0000%** on that
  same measure.
- The safety guard the reviewer proposed — having the algorithm calibrate the
  blur from the stack itself, so no lens model has to be trusted — **was tested
  and does not work.** It over-estimates the blur width by 1.9–2.2×, and in one
  band it claims a value of 0.021 where direct measurement reads 0.638.

There is a detail here I want to flag because it nearly went the other way. The
milestone's *own primary measurement channel* — the one it registered in advance
as the thing it would judge by — **failed its control in the exact direction of
its hypothesis.** It reported a signal-to-noise ratio of 84.9 on a capture with
no scene in it at all, understating noise by a factor of 73. Had that channel
been trusted, every number in the report would have favoured deconvolution by
roughly an order of magnitude, and I would be writing you an excited paragraph
this morning instead of this one. It was caught because the control was built
before the result was wanted.

**Final number, landed overnight.** The measurement is now complete and it is a
clean null: the headroom deconvolution could recover is **1.0014**, against a
spread of ±0.0184. One point one four *thousandths* of a percent, inside noise.
The reason this is a real answer and not just a quiet instrument is that the same
estimator was made to prove it can respond: planted, known effects come back
through the identical channel at **0.9938–0.9974**, and the checking harness that
polices the whole measurement was itself commissioned by planting thirteen
deliberate defects in it and confirming it caught all thirteen. So the tool
demonstrably *can* see an effect of this kind; there is not one here to see.

**What this means for you.** The honest position is now that **this project has
no known route to making your photos sharper than the sharpest frame you shot.**
Everything it can currently do is about *not degrading* what you captured —
removing the mosaic, the halo, the blotches, the wrong-frame pixels — which is
worth doing and is where the remaining work goes. But if you were expecting the
stacker to eventually out-resolve your optics, it will not, and I would rather
tell you that in August than let you discover it in December. It also means the
practical advice in §0 (**stop shooting at marked f/11**) matters more, not less:
contrast you don't capture is now definitively contrast you don't get.



Two independent by-eye reads on 1:1 crops of your own stacks — one by an agent
that had never seen the chromatic-aberration work, one by me — independently
concluded that **the worst thing in your renders is lateral chromatic
aberration**: coloured fringes on every bright edge. Not softness, not noise, not
ringing. That diagnosis still stands and is now confirmed on two stacks by two
independent methods.

**What changed is the fix.** Earlier tonight I measured the correction
over-shooting by 1.444× and recommended scaling the red coefficient by 0.692.
**An independent check refuted that, and it was my error, not the checker's.** I
had measured on an `--srgb` render — and lateral CA is a *cross-channel* quantity,
while that file has had two cross-channel operations applied to it: a colour
matrix that mixes 10–20 % of one channel into another **at zero displacement**,
and a demosaic whose stated assumption is that `R − G` is smooth, which is
precisely what a colour fringe is not. The tool's own help text for `--srgb` says
**"For looking at, NOT for measuring."** It was right and I ignored it.

Re-measured properly, the correction over-shoots by **1.25×** on one of your
stacks and **1.06×** on another. **And that spread is the real finding: there is
no single number to fix.** The two stacks need corrections 23.6 % apart through
the same lens, because how far a colour separates depends on the *effective
wavelength* of each channel — which depends on the **colours in the scene**. Your
bee and your couch fibres are lit differently and coloured differently, so they
genuinely need different corrections.

**The practical news is better than any of that, and it is available now: the
correction is switched off.** It is one of the six quality gates that default to
off. Your renders have had *no* chromatic-aberration correction applied at all —
which is why the fringes are the most obvious thing in them. Turning it on was
measured overnight on your own captures: edge-localised colour excess falls
**61.0 %** on one subject and **58.7 %** on another, and an independent by-eye
check on 1:1 crops found the corrected version *"visibly cleaner"*, with the
red/cyan speckle across a wing's fine dot texture largely gone and what remains
reading as neutral grey rather than opposed colour. A 1.06–1.25× over-shoot is a
small residual on top of a correction that is doing most of its job.

One honest caveat on what it does: it makes fringes **fainter, not thinner**. The
peak of the fringe drops faster than its tail, so edge contrast improves markedly
while the fringe's width is unchanged.

**And I have to withdraw something I said earlier tonight.** I reported that the
correction "recoloured rather than removed" the fringes — that it flipped their
colour instead of eliminating them — and treated that as a defect for most of the
night. It was a defect in **the test**, not the correction. The test counted how
many fringes changed colour sign. Measured properly: **62.9 % of fringes flip
sign, but only 9–19 % get bigger.** Most flips are fringes being pushed *through*
neutral toward grey, which is exactly what a working correction does. A perfect
correction would score close to total failure on that test. Two agents reached
this from different directions and their numbers agree.

**Which is exactly why the coloured-gel sets in §24 are now the point of the
shoot.** Shooting the same flat target under red, green and blue light measures
that spectral dependence directly, on your lens, at your magnification. It is the
difference between a correction that is right on average and one that is right on
your photograph. Nothing else in this document can substitute for it.

Everything below about the fit's missing support still applies, and still
matters:

- The fit spans **r = 0.208 to r = 0.788** of the frame radius. **Both outer
  annuli are empty** — `0.80-0.90` *and* `0.90-1.00`. Lateral CA is **zero at the
  centre by construction and grows with field height**, so the correction is least
  supported exactly where the aberration is largest. At the corner, 2.35 sensels
  of the 2.98-sensel correction sit at or below a measured radius; **the remaining
  0.63 is the model's shape, not data.**
- **Every fitted region was red.** The blue coefficient is not estimated as zero —
  it is **not estimated at all**. **This is less damaging than I first wrote here,
  and the correction is worth stating carefully:** the red/cyan fringes you can
  see are *red misregistration*, because cyan is simply the absence of red. A
  radial scale error in red puts a red edge on one side of a boundary and a cyan
  edge on the other, so **correcting red alone removes both**. The missing blue
  coefficient does not halve that fix — it bites on **blue/yellow** fringing,
  which is a separate defect.

Both of your best subjects (`tweezers-cpl`, `bee-3-cpl`) are macro subjects in a
band with defocused background past r ~ 0.7. **Their corners are not measured
clean; they are not measured.** No amount of reprocessing creates signal where the
photograph has none — which is why this needs a *flat, repeating subject that
fills the frame corner to corner*, under full-spectrum light, rather than another
beautiful bee.

**Overnight this stopped being a theoretical gap and became the whole question.**
I pulled the two 1:1 crops of `bee-3-cpl` where the fringing is unmistakable —
the hairs and the wing edge — and worked out where they actually sit in the
frame. On the 7032 × 4688 render they are at **r = 0.879** and **r = 0.822**.
Both are **past 0.788**, so both are being corrected by extrapolated model shape
rather than by anything measured. The one crop comfortably inside the fitted
zone, at r = 0.62, is a low-contrast patch where the fringing is barely visible
anyway.

**LATER THE SAME NIGHT — that question is now answered, and the answer is not the
one this section was written to expect.** I built an instrument to measure it
directly rather than wait for the capture: phase correlation on gradient
magnitude, giving the sub-pixel red-minus-green displacement, projected onto the
radial direction. It is validated against a positive control that plants a known
shift by **integer pixel roll** — which moves data without resampling it, so the
plant cannot change sharpness and contaminate the answer. Recovery error **0.045
px over ±2 px**, n = 40 per level.

Measured on a byte-controlled `on`/`off` pair of your own frames — **and then
refuted by an independent check. Read the correction, not the original claim:**

- **What I originally reported: the correction overshoots by 1.444×.** Right
  radial *shape*, wrong *scale* — removing the fringe and then continuing ~44 %
  past zero with the sign flipped. Implied fix: scale the red coefficient by
  **0.692**.
- **That number was wrong, and the reason is that I measured it in the wrong
  colour space.** Lateral CA is a *cross-channel* quantity — it is about where
  red sits relative to green. I measured on an `--srgb` render, and that file has
  had two cross-channel operations applied to it: a colour matrix that mixes
  **10.4 %** of camera green into output red and **20.3 %** of camera red into
  output green **at zero displacement**, and a demosaic whose documented
  assumption is that `R − G` is smoother than either channel — which is exactly
  what a colour fringe violates. The tool's own help text for `--srgb` reads
  **"For looking at, NOT for measuring."**
- **How it was caught, which is worth knowing because it is reusable.** The
  correction applies a *known constant* from the source code. So the amount
  applied has a ground truth, and comparing applied-versus-known measures the
  whole imaging chain end to end. That ratio came out **1.31 in sRGB, 0.70 after
  demosaic, and 0.94–0.98 in the clean binned space** — the two processed spaces
  wrong by **+31 % and −30 %**, in opposite directions. No internal consistency
  check could have found that; only the external constant could.
- **The corrected numbers: 1.25× on `bee-3-cpl`, 1.06× on `couch-fibers-cpl`.**
  The needed correction is **529.9** and **654.9 ppm** against a shipped
  **704.5**.
- **`0.692` must not ship.** On `couch-fibers-cpl` it would convert a 5.6 %
  over-correction into a **27.0 % under-correction** — worse than the problem.
- **And no other single number would work either.** The two stacks disagree by
  **23.6 %** while the per-ring noise is under 4 %, so that gap is real. How far
  a colour separates depends on each channel's *effective wavelength*, which is
  set by the **colours present in the scene**. This is the finding that redirects
  §24 toward the coloured-gel sets.

**What survived the refutation, and is now better supported than when I claimed
it:**

- **The radial shape is correct** — flat across r = 0.11 to 0.87.
  **Corrected overnight:** an audit of my own notes found the "±15 ppm" figure I
  previously quoted here was **spliced in from a different experiment** (a
  single-scene run), and the real scatter is much larger at the inner radius —
  the bootstrap sd on the innermost ring is **80 ppm**, not 15. The *shape*
  finding survives; the tightness I claimed for it did not.
  The model's form is right; only its magnitude and its scene-independence were
  wrong.
- **`RECOLOURED, NOT REMOVED` is real**, now confirmed on **two** stacks under
  **two independent estimators**: the residual flips sign in both.
- **The over-extrapolation hypothesis is still dead**, and now on 111
  outside-support windows rather than the single ring I originally used.

**So why is §24 still the first thing to shoot?** Because it is the capture that
settles this, and three further things that only a real capture can reach:

1. **It is the only way to measure condition-dependence.** If the correction
   turns out to be right at one magnification and wrong at another, the fix is
   not a better constant — it is a profile that knows the conditions. §24 asks
   for a set **with the 2x teleconverter** precisely because that is the largest
   change of conditions in your kit.
2. **My number rests on one scene**, and a scale error is exactly the kind of
   finding that can be an artifact of a single subject's structure.
3. **Blue is still not estimated at all** — not by the original fit, and not by
   me: **0 of 10 rings** cleared my noise floor, so I have no claim in either
   direction. **Correcting an earlier version of this note:** this does *not*
   mean only half of each fringe can be fixed. The red/cyan fringing in your
   renders is red misregistration — cyan is the absence of red — so the red
   coefficient addresses both sides of it. What the missing blue coefficient
   leaves untouched is **blue/yellow** fringing, a distinct defect. §24 is still
   the capture that would measure it.

And a fourth reason that emerged from my own failure tonight: **the first metric
I built for this measured scene hue instead of chromatic aberration.** It
produced a beautiful radial table and a textbook null, and died on its positive
control. A colour-separated capture is immune to that entire class of error **by
construction** — with only one channel lit, there is no scene hue left to
mistake for a fringe. That is now the strongest argument for shooting §24 the way
it is specified.

And a fourth reason that emerged from my own failure tonight: **the first metric
I built for this measured scene hue instead of chromatic aberration.** It
produced a beautiful radial table and a textbook null, and died on its positive
control. A colour-separated capture is immune to that entire class of error **by
construction** — with only one channel lit, there is no scene hue left to
mistake for a fringe. That is now the strongest argument for shooting §24 the way
it is specified.

**Ten minutes of a flat corner-to-corner subject decides it.** It is the only
request on this list that unblocks a fix which is otherwise stuck guessing.

**Already delivered, nothing needed:** dark frames (§1), flat fields (§4,
delivered 2026-08-23), and the twelve labelled stacks in §16.

---

## 0. Shooting advice — stop shooting at marked f/11

> **AMENDED 2026-08-24 — read §17 before quoting any number in this section.**
> Two things have changed. (a) **The owner has already acted on this advice**:
> all current stacks are f/5.6 marked, and f/5.6 is *wide open* with the
> teleconverter fitted, so this lever is spent rather than pending.
> (b) **The `N_eff` column below assumes m = 2.0 and p = 1, and both are now
> measured false.** Magnification is **2.7198 ± 0.0051** and pupil magnification
> is **p ∈ [1.31, 1.94]**, with **p = 1 excluded** (facts 1151, 1152). Using M5's
> *measured* bellows factor instead, **critical sampling is at marked f/6.08–7.72,
> and f/5.6 wide open already sits above it** — the opposite of what an earlier
> version of this banner said. The section's *direction* is unchanged; its
> arithmetic is superseded by §17.

Not a capture request. A change to how the existing rig is used, and the
largest single quality lever measured anywhere in this project.

**Marked f/11 is optically f/33** on this rig (fact 28: the body writes the
marked aperture into EXIF and applies no bellows correction for working at 2:1).
At that effective aperture the diffraction cutoff falls to 0.2762 cyc/px against
a Nyquist of 0.5, so **MTF at Nyquist is exactly 0.000** (fact 12, measured).
More than half the band the sensor can record is empty before any software runs,
and no stacker — this one included — can put it back. Critical sampling is at
**marked f/6.21**.

Measured cost, at matched focus-axis sampling and fixed subject depth
(`research/M20-deconvolution-ceiling-measured.md` §4.4):

| marked | optical `N_eff` | contrast at 4-px detail | vs f/11 |
| --- | --- | --- | --- |
| f/4 | 12.0 | 0.5977 | **12.9x** |
| f/5.6 | 16.8 | 0.4467 | **9.6x** |
| f/8 | 24.0 | 0.2416 | **5.2x** |
| f/11 | 33.0 | 0.0463 | 1.0x |
| f/16 | 48.0 | 0.0000 | zero |

**The trade is frame count, not light.** Depth of field scales with `N_eff`, so
covering the same subject depth at f/5.6 instead of f/11 needs about **2x the
frames**. It does not need more total light — a wider aperture more than pays
for the extra frames. At a fixed total capture time the end-to-end SNR at 4-px
detail is **13.5x** better at f/5.6; even holding total light constant it is
**6.9x** better.

**Try it on the next stack.** Same subject, two brackets: one as usual at f/11,
one at f/5.6 with twice the frames. That pair is also a genuinely useful capture
for the project — see §7.

*Caveat, stated honestly: the table is DERIVED from a diffraction model gated
against facts 12, 27 and 28 (agreement to 3-4 digits), not from a side-by-side
shot. The two-bracket pair above is what would turn it into a measurement.*

**External corroboration, added after M19's literature survey.** The *shape* of
this ceiling is not our claim — it is proved. Levin et al. (*ACM TOG* 28(3),
2009, Claim 2) bound the worst-case defocus MTF power over a depth range by
`β(ω)·A³/(S·|ω|)` with `β ∈ [0.93, 1]`, and note that under Fourier rather than
geometric optics the budget "**decreases with the diffraction-limited MTF**" —
so where the diffraction MTF is zero, the budget is zero (fact 403). That is an
independent, published derivation of the thing this section is telling you to
avoid: **no merge, however clever, recovers a band no frame observed.** It is
also why aperture outranks algorithms here. Every hour spent improving the merge
before this section is acted on is an hour spent optimising underneath a ceiling
you could simply have raised.

---

## 1. Dark frames — DELIVERED

**Status:** delivered and measured. Results in
`research/M4-fpn-measured.md`. Nothing depends on this entry any more.

### What was actually supplied

| | Requested | Supplied |
| --- | --- | --- |
| ISOs | 2 (100 and 400) | **11** — 50, 100, 200, 250, 400, 500, 640, 800, 1000, 1600, 2000 |
| Frames per ISO | 20 | 22, first 2 discarded as stabilisation shots -> **20 used** |
| Total | 40 | **242 captured, 220 analysed** |
| Shutter | ~1/100 s | 1/100 s, uniform across all 242 |
| Location | — | `D:\macro-dark-frames\{118..128}MSDCF`, one folder per ISO |

The folder-to-ISO mapping was not supplied and was discovered from EXIF. Every
folder proved internally uniform in both ISO and exposure. All eleven passed
the light-leak sanity gate.

**The over-delivery is why the dual-gain result exists.** Two ISOs can only show
that ISO 400 differs from ISO 100. Eleven ISOs, five of them bracketing the
switch (200 / 250 / **400** / 500 / 640), show a *discontinuity*: noise in DN
rises to ISO 250, drops 45% at ISO 400, then resumes rising. That is
model-free evidence for a second base ISO, and it needed the extra nine folders.

### What it unblocked

- **The central design pillar, answered.** Raw dark-frame averaging follows a
  slope of -0.289, not -0.5, and hits a fixed-pattern floor of 0.377 DN at
  N ≈ 7. With a disjoint master bias subtracted the slope is -0.5019 and every
  point is within 0.5% of ideal. The pillar holds, conditionally.
- **Dark-frame subtraction is worth shipping**, with a measured design rule: the
  master must be built from at least `(sigma_temporal/sigma_FPN)^2` frames —
  7 at ISO 100, 42 at ISO 2000 — or it injects more noise than it removes.
- **`SYNTHESIS.md` fact 14 confirmed** model-free.
- **`SYNTHESIS.md` §7 risk 8 downgraded** at short exposures: zero pixels sit
  50 DN above black at base ISO. Still unverified for long exposures.

### What it did not unblock

The photon-transfer curve. **PTC is impossible from dark frames** — it needs
signal variance against signal level and a dark frame has no signal. `g` remains
`DERIVED` from an unmeasured relation and `SYNTHESIS.md` §10 item 6 stays open.
See §4 below.

> **Superseded, 2026-08-23 — and the lesson generalises.** A *usable* PTC did
> arrive, from **stacks already on disk**, without any new capture. M25 measured
> `g` by photon transfer on `109MSDCF`, `119MSDCF` and `coffee-bean` — 8×8 tiles
> on one green plane, 5th-percentile variance per mean bin, using the scene's
> own tonal range as the signal ladder. It recovered `g` = **0.3273 at ISO 160**
> against the relation's 0.3663 and found a **2.05× error at ISO 50**, now fixed
> in shipped code (`2a4f5c5`, fact 550). SYNTHESIS §10 question 8 is **closed**.
>
> **This paragraph was wrong in a specific and instructive way.** "PTC is
> impossible from dark frames" is true. "Therefore `g` needs a flat-field
> capture" does not follow, and nobody checked it — the requirement was
> *inherited from the textbook procedure* rather than derived from what this
> measurement actually needs, which is signal variance against signal level from
> **any** source. A photograph is such a source.
>
> **Before adding anything to this file, ask what the measurement needs rather
> than what the standard procedure prescribes, and try the corpus first.** The
> owner's time behind a camera is the scarcest input this project has.
>
> The flat-field campaign in §4 is **still worth shooting** — it measures PRNU
> and vignetting, which no existing capture can give, and it yields a *clean*
> intercept. This PTC's intercept is **not** trustworthy: residual scene texture
> inflates it to 6.9 e⁻ at ISO 160 against fact 14's 4.20 e⁻, so it constrains
> the **slope only** and says nothing about `RN_e`.

### What to shoot (kept for reference / repeat captures)

| | |
| --- | --- |
| Lens or body cap | **On.** No light may reach the sensor. |
| Room | Dark. Cover the viewfinder if shooting with the EVF exposed. |
| Mode | Manual. |
| Shutter | ~1/100 s (match a typical stacking exposure). |
| Aperture | Irrelevant — the cap is on. |
| Format | **RAW (.ARW).** Not JPEG, not compressed-lossy. |
| Noise reduction | **All off.** Long-exposure NR and high-ISO NR both. |
| Count | 20+ frames per ISO of interest. |
| Between frames | Change nothing. Do not move the camera or touch settings. |

### Why it could not come from existing files

The plan was to get this free from the sensor's optically-masked border pixels,
which see no light by construction and are therefore a dark frame embedded in
every RAW. **`rawler` does not expose them:** it reports `blackareas` as empty
for Sony, and crops the masked border away during decode. What remains outside
the active area is synthetic zero padding, not sensor data. Verified in
`research/M1-decode-measured.md` §3 — probed 3,544,448 pixels, all exactly 0.

---

## 2. Rail-captured stack — DEFERRED, no hardware

**Status:** owner has no focus rail. Rail support is deferred from v1
(`research/SYNTHESIS.md` §9). Not blocking anything currently planned.

If a rail is ever borrowed: one stack of a subject with **visible depth
discontinuities** — overlapping structure where a near surface occludes a far
one, not a smooth continuous surface. That is the case affine cannot model, and
it is where the parallax and occlusion claims need testing.

---

## 3. Not needed

Recorded so nobody asks twice.

- **Flat fields for vignetting.** Not on the v1 path. (Flat fields *are* now
  wanted for a different purpose — see §4. This entry refers only to lens
  vignetting correction.)
- **A focus-bracketed stack.** Already have 22 frames in
  `C:\dev\macro\test\109MSDCF` plus 2310 further ARWs, all verified decodable.
- **A second deep stack, for the fact-43 shrinkage calibration.** Was the one
  outstanding *photographic* request after M10. **Already satisfied** by
  `D:\personal\macro\112MSDCF` (79 frames) and `113MSDCF` (63 frames) — see §5.

---


## 4. Flat fields — **DELIVERED 2026-08-23**
### What was actually supplied — read this before using it

`D:\personal\macro\flat-fields`, **484 ARW frames in three directories**, all
`ILCE-7CM2` + `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, **ISO 100, marked f/5.6,
FocalLength 200 mm** (the body composes the TC — fact 26).

| dir | n | structure | span |
| --- | --- | --- | --- |
| `flat-fields/` | **360** | **9 exposures x 40 frames.** 1/250, 1/125, 1/60, 1/30, 1/20, 1/13, 1/10, 1/8, 1/5 s | 16:41:30 -> 16:50:32 (**9m02s**) |
| `subject-focus-sweep-with-cpl/` | 62 | single exposure 1/5 s, focus swept out-through-out | 16:31:55 -> 16:32:38 |
| `subject-focus-sweep-no-cpl/` | 62 | single exposure 1/5 s, focus swept out-through-out | 16:51:17 -> 16:51:56 |

**Subject:** two stacked sheets of white A5 printer paper taped to a window. Lens front
**~9 cm** from the paper, **~28 cm** subject-to-sensor. That is near the composed path's
minimum focus, so **m is near the 2.0 maximum** and the field is roughly **18 x 12 mm** of paper.

**The owner reports the session as: sweep-with-CPL, then 8 exposure sets of 20 with CPL,
then the same without, then sweep-no-CPL.** EXIF says **9** exposures x **40** frames, which
is consistent: **each 40 is 20 CPL + 20 no-CPL at the same shutter speed**, and the owner
counted 8 rather than 9. **CPL state is NOT recorded in EXIF.** It must be recovered from
capture time (CPL first) and cross-checked against signal level, since a CPL costs ~1.5-2
stops and the two halves should separate cleanly at matched shutter speed. **Recovering the
split is the first task and it is self-validating; do not assume the owner's count of 8.**

### Confounds the owner flagged, and one they did not

1. **Illumination was not stable and the owner said so.** Seattle August overcast, *"some
   minor patches of blue sky"*, clouds moving slowly, no direct sun, *"possibly varied light
   over the whole duration"* — over **9 minutes**. Within one 20-frame set at 1 s intervals
   the drift window is ~20 s; between sets it is minutes. **Global drift is a per-frame
   scalar and divides out by normalising each frame to its own spatial mean; that
   normalisation is mandatory before any temporal-variance estimate.** Residual excess
   variance after normalising is then evidence the drift had *spatial* structure, which is a
   result in itself, not a nuisance.
2. **The confound the owner did not flag, and it is the serious one: at m~2 the paper's own
   fibre texture is resolved, and multiplicative paper texture is exactly what PRNU looks
   like.** Both are fixed and both scale with signal, so **they are not separable by the
   photon-transfer argument alone.** Two levers exist in the delivered data:
   - **Spatial frequency.** PRNU is near-white per pixel; paper fibre structure is
     correlated over ~10s of microns, which at m~2 is several pixels. The corpus already has
     validated spectral-domain separation machinery (facts 27, 29).
   - **Defocus, which is the clean one.** Defocus blurs paper texture and **leaves PRNU
     untouched.** The two 62-frame sweeps run from out of focus, through focus, and back
     out, at the same aperture and magnification as the flats — so **the most defocused
     frames carry the same PRNU with the least paper texture.** That is a direct
     experimental handle and it is already in the delivered set.
   **Any PRNU number produced without addressing this is not a PRNU number.**
3. **Focus position during the 360 flats is unrecorded.** If the paper was left in focus,
   texture dominates; if left defocused, it does not. **Determine this from the data before
   trusting any spatial statistic.**

### Unexpected bonus — this may partially satisfy §8

The two focus sweeps are **through-focus series on a planar subject at known magnification**.
A plane taped to a window and shot handheld-ish will carry **some tilt**, and tilt on a plane
is **analytic depth**: the through-focus peak should move linearly across the field. That is
the instrument §8 asks for. **It is not a substitute for a deliberate §8 capture** — the tilt
is unknown and uncontrolled, and paper is a low-contrast broadband target rather than a
resolution chart — but it is the first physical target in the corpus with a *known depth
model*, and it is directly useful to focus-correctness and through-focus work.

### Status of what §4 was blocking

- **PRNU (kappa) for `sigma^2(S) = gS + (RN*g)^2 + (kappa*S)^2`** — unblocked **subject to
  confound 2 above**.
- **A second independent photon-transfer curve** across a **50x** signal range at one ISO,
  to cross-check facts 27/29 — unblocked, this is the cleanest thing in the set.
- **Illumination/vignetting profile and CPL transmission + any CPL-induced angular
  non-uniformity** — unblocked, with the drift caveat.
- **Dust map**, fixed in sensor coordinates — unblocked.
- **NOT unblocked: PRNU at other ISOs.** Everything here is ISO 100.


**Status:** **owner is shooting these in daylight, next opportunity** (agreed
2026-08-22). Raised by `research/M4-fpn-measured.md` §7 and §8.3. Not blocking
experiment 3; blocking two things that are currently guesses.

### Daylight-specific notes

Daylight is a good light source for this — bright enough to keep exposures
short, and free of the flicker that makes artificial sources risky. It has one
failure mode the generic spec below does not cover.

**The trap: illumination that drifts during a level.** The whole measurement is
a *temporal* variance per pixel at a known mean. If the light changes while the
16 frames of one level are being taken, that change enters the per-pixel
temporal variance and is indistinguishable from sensor noise. It inflates the
variance, which inflates the fitted gain, which corrupts every electron figure
downstream. Drift *between* levels is harmless; drift *within* a level is not.

Three mitigations, in order of how much they help:

1. **Shoot in open shade or under overcast, not direct sun**, and point at a
   diffuser rather than at the sky itself. Sun through moving cloud is the worst
   case; a bright overcast is nearly ideal.
2. **Take each level as a fast burst**, so all 16 frames sit inside a few
   seconds. Take the time between levels, not during one.
3. **It is recoverable in analysis if it happens** — normalise each frame by its
   own global mean before computing the temporal variance, which removes a
   spatially-uniform illumination change while leaving per-pixel noise intact.
   Treat this as a safety net, not a licence to be careless: it only removes the
   *uniform* component, and a moving shadow or a changing sky gradient is not
   uniform.

**Check before analysis, not after:** the frame-to-frame global means within a
level should be flat to well under 1%. If they trend, that level is suspect and
should be reshot.

### What to shoot

| | |
| --- | --- |
| Subject | An **evenly lit featureless surface** filling the whole frame. |
| How | Easiest reliable method: a sheet of white paper or an opal/white acrylic sheet held a few cm in front of the lens, lit indirectly. A cloudless sky through a diffuser also works. An LCD showing a white screen does **not** — it has pixel structure and PWM flicker. |
| Focus | **Manual, set to infinity or fully defocused.** The point is that nothing in the frame is sharp. |
| Aperture | f/8 or so. Keep it identical across the whole set. |
| ISO | **100**, fixed. Do not let it move. |
| Format | **RAW (.ARW).** Noise reduction all off. |
| Exposure levels | **7 levels**, by shutter speed only, spaced roughly a stop apart, targeting mean raw values of about **500, 1000, 2000, 4000, 7000, 11000, 14000 DN** above black. Overexposing one is fine and useful; clipped frames are simply dropped. |
| Frames per level | **16.** Change nothing between them. |
| Teleconverter | **Irrelevant — leave it on.** Gain and PRNU are sensor properties, and the vignetting the TC changes is fitted out by the smooth-surface normalisation below. Just keep it identical across the whole set. |
| Between levels | Change **only** the shutter speed. Do not move the camera, refocus, or alter the lighting. |

Roughly 112 frames. If that is too many, 8 frames per level at 5 levels is
still enough, with wider error bars.

**How to hit those levels in practice.** The camera's histogram is of the
embedded JPEG, not the raw, so do not try to hit the DN targets by eye. Meter
one exposure that looks like a bright mid-tone, then bracket **+-3 stops in
1-stop steps** around it. That gives the 7 levels. **Err wide deliberately** —
clipped frames cost nothing because they are simply dropped, whereas a set that
never approaches the white level leaves the top of the curve unmeasured.

**Discard the first 2 frames after touching the camera**, the same habit used
for the dark-frame set.

Also useful and nearly free: repeat one mid-level (say 4000 DN) at **ISO 400**,
16 frames. That gives a second gain point either side of the dual-gain switch.

### Why this cannot come from existing files

Every existing corpus is of real subjects. A photon-transfer curve needs the
variance of a *uniform* signal at a known level; any scene texture contributes
spatial variance that is indistinguishable from noise. The uniformity is the
measurement.

### What it unblocks

1. **The gain `g`, measured rather than assumed.** Photon shot noise obeys
   `variance = g * signal`, so the slope of variance against mean over the
   exposure series *is* the gain, in DN per electron. Right now `g = ISO/436.8`
   is inferred from reproducing the camera's white level to 0.23% — a
   consistency check on one relation, not a measurement. This closes
   `SYNTHESIS.md` §10 item 6 and upgrades every electron figure in M4 §8.3 from
   `DERIVED` to `MEASURED`, including the read-noise numbers that decide whether
   the noise model needs one calibration point or two.

2. **PRNU — and this is the more important one.** M4 measured the *offset*
   fixed-pattern floor at 0.377 DN and showed it never binds in a normally
   exposed frame. It could say nothing at all about **PRNU**, the per-pixel gain
   variation, because a dark frame has no signal for a gain to act on. PRNU is
   multiplicative, grows with signal, and does **not** average away. At a
   textbook 0.3–1% and a mid-tone of 5000 DN it would be 15–50 DN of fixed
   pattern against 7.6 DN of 20-frame-averaged shot noise — two to seven times
   larger than the noise it competes with, sitting exactly in the lit,
   low-contrast regions where M2 measured the argmax defect.

   If PRNU is at the high end, averaging in lit regions asymptotes just as raw
   dark-frame averaging does, and the merge stage needs flat-field correction
   and not merely bias subtraction. **That is a design-changing possibility that
   is currently unmeasured in either direction.**

   **Method correction (found while re-checking this spec; the original recipe
   was wrong).** This entry previously said to estimate PRNU as the per-pixel
   temporal mean divided by **the frame mean**. That does not work. Dividing by
   a single global scalar leaves **vignetting** — a smooth, low-spatial-frequency
   gain roll-off — entirely intact in the residual, and vignetting across a full
   frame is typically several percent, an order of magnitude larger than the
   0.3-1% PRNU being measured. The resulting map's standard deviation would be
   almost pure vignetting, and would have "confirmed" a large PRNU no matter
   what the sensor actually does.

   **Correct procedure:** normalise each per-pixel temporal mean by a **smooth
   low-order surface** fitted to (or a heavily blurred copy of) that same flat,
   so only pixel-to-pixel structure survives. Then remove the residual temporal
   noise in quadrature — `sd_PRNU^2 = sd_measured^2 - sigma_temporal^2 / N` —
   rather than ignoring it. Confirm PRNU by its defining signature: it is
   **multiplicative**, so `sd_PRNU` must scale **linearly with signal level**
   across the seven exposure levels. A fixed pattern that does not grow with
   signal is offset FPN, which M4 already measured, not PRNU.

   **16 frames per level is sufficient** for this. PRNU is fixed, so only the
   temporal term shrinks, and with ~8.2M plane pixels the standard-deviation
   estimate is precise to well under 0.05% — the quadrature subtraction, not the
   frame count, is what has to be right.

   **One capture-side consequence: do NOT clean the sensor before shooting these.**
   Dust motes render sharply in a flat field and appear as localised dark blobs.
   They are spatially clustered, so the smooth-surface normalisation above will
   *not* remove them, and they would be counted as PRNU — so they must be masked
   before the PRNU statistic is taken. But they are no longer only a nuisance:
   M29 makes the dust map a **deliverable**, and cleaning the sensor first would
   destroy the only evidence of the dust that is in the existing corpus.
   **Shoot the flats dirty, mask for PRNU, keep the mask as the dust map.**

3. **The dust / static-defect map — added by M29, and now a specification
   rather than a request.** M29 established three things that together make this
   the only way to get dust at all. The merge does **not** dilute it (`D = 0.999`
   at `n_eff ≈ 3`, fact 230, so it must be handled explicitly); it **cannot** be
   detected from subject stacks (limit 32–50% shadow depth against real dust of
   1–15%, fact 232); and the floor that blocks it is **scene texture, which does
   not fall with frame count** (exponent +0.025 over a 16× sweep, fact 233). A
   flat has `g/blur(g) ≡ 1` by construction, which is exactly the factor that
   attenuates the response on a subject (`R ≈ 0.92·g/blur(g)`, fact 231).

   **Specification, from the calibrated noise model with no free parameters:**

   | frames | floor | a 5% shadow is |
   | --- | --- | --- |
   | 8 | 0.190% | 26σ |
   | **16** | **0.134%** | **37σ** |
   | 20 | 0.120% | 42σ |
   | 64 | 0.067% | 75σ |

   at ISO 100 with the mid-tone at **8,000–12,000 DN**. The §4 set above already
   satisfies this at its upper levels, so **the PRNU set doubles as the dust set
   at no extra cost** — nothing additional needs shooting for the f/8 case.

   **What does need shooting separately: one short set per working aperture.**
   Dust visibility scales with aperture — a stopped-down lens renders motes
   sharply, a wide one smears them — so a map measured at f/8 does not transfer
   to f/16. **16 frames at one level (8,000–12,000 DN), at each aperture you
   actually shoot.** Changing only the aperture between sets means the exposure
   must be re-metered each time; that is fine, only the level matters.

   **Timing caveat, and it is a real limitation.** Dust moves. A map measured
   today describes the sensor today, and **cannot be applied to the existing
   corpus**, which was shot months earlier. Flat fields correct the stacks shot
   near them in time and nothing else. This is not a reason to delay — it is a
   reason to shoot a short flat set as *routine practice* alongside real work,
   which is cheap enough (16 frames, one level) to be habitual.

---

**STOP -- READ THIS BEFORE SHOOTING THE FLATS (added 2026-08, before capture).**

Your optical path includes a **Breakthrough X4 CPL circular polariser**, which was
not known when the section above was written. It changes this capture in two ways
and one of them will quietly ruin it.

1. **Do not shoot a sky flat through the polariser.** Blue sky is strongly
   linearly polarised, and the degree of polarisation varies across the sky with
   angle from the sun. A CPL pointed at it imposes a large, rotation-dependent
   brightness gradient across the frame. **That gradient would be recorded as if
   it were the lens's vignetting**, and every frame divided by the flat would then
   be wrong in a smooth, plausible-looking way that is very hard to detect
   afterwards. Shoot against an **unpolarised diffuse source** instead: an
   electroluminescent panel, a white surface lit by several sources, or several
   layers of diffuser over a window -- **not** open sky.

2. **Shoot the whole set TWICE -- once with the filter on, once with it off.**
   This replaces the earlier instruction to simply leave it on. You have since
   confirmed the polariser was **not** on for every stack, and the EXIF dates make
   the split a clean rule: everything from **25 May onward is CPL-on**
   (`coffee-bubbles`, `foam`, `wrapped-text-1/2`, `bee-1/2/3`), everything up to
   **17 May is CPL-off** (`112`, `113`, `119`, `109`). `coffee-bean` (10 May) sits
   on the off side of the boundary but you could not recall it, so it is unknown.

   A flat describes an *optical path*, not a sensor. **One flat therefore cannot
   cover this corpus** -- applying the CPL-on flat to the May stacks would divide
   out vignetting that was never there. The two sets differ only by whether the
   filter is mounted; change nothing else, and do not rotate it between them.
   Cost is one extra set of the same shots.

   Doing both also delivers something better than a correction: **the ratio of the
   two flats IS the polariser's transmission map**, measured on your own copy of
   the filter. That prices the confound instead of caveating it forever, and it is
   free once both sets exist.

If an unpolarised source is not practical, **shoot the filter-off set only, and
skip the filter-on set entirely.** A flat without the filter is valid; a flat with
the filter against sky is not -- and a wrong flat is worse than no flat, because
it corrupts smoothly and plausibly rather than obviously.

---

## 5. Deep stacks with deliberate scene variation — REQUESTED

**Status:** requested. Not urgent, not blocking anything today, but **two
separate open questions now need the same capture**, so one afternoon of
shooting closes both.

**Why.** The corpus is five stacks, and two independent results have run out of
road on exactly that:

- **Fact 53 — the shrinkage mechanism is unexplained.** Short-baseline alignment
  edges under-report magnification change by anywhere from **1.03x to 3.26x**,
  and it is a property of the *scene*, not the optics (fact 51). Ten candidate
  predictors were tested against the edge sets and **none** of them predicts
  which stacks shrink. With five stacks, no correlation can reach significance —
  the critical value is ρ = 0.600 at n = 5.
- **Question 18 — one cell behaves unlike every other.** The `119MSDCF`
  horizontal texture pair puts its focus-window optimum at w8 at *all five*
  depth steps, the only cell with a constant argmin, and it is the source of
  every head-to-head loss the recommended window suffers. One texture pair per
  stack cannot tell an occlusion-geometry effect from a texture effect.

Both are asking the same question: **which property of a subject drives this?**
That cannot be answered by analysis, only by more stacks that vary the property
on purpose.

### What to shoot

**8-12 stacks**, same rig and same method as the existing corpus (in-camera
focus bracketing; no rail needed). Depth 40+ frames each so the long-baseline
anchors exist. The point is **deliberate variation**, so vary these on purpose
rather than shooting a dozen of the same thing:

| Axis | Span it |
| --- | --- |
| **Subject depth** | Something almost flat (a coin, a leaf face-on) through something deep (a flower head, a pine cone, an insect). This is the axis most likely to matter and the corpus barely varies it. |
| **Texture scale** | Fine high-frequency detail (fabric weave, sand, chitin) *and* smooth low-contrast surfaces (a petal, a polished shell). |
| **Occluding edges** | At least three subjects with **genuine occlusion** — a near element in front of a far one with real separation, e.g. a stem crossing in front of a background, or hairs standing off a surface. This is the configuration the whole window result turns on and the corpus has almost none of it. |
| **Depth-gradient direction** | Not everything front-to-back. Include subjects whose depth runs left-right and diagonally. `119MSDCF`'s anomaly is specifically in a *horizontal* geometry. |

**Keep constant:** aperture, ISO, lighting and magnification within each stack,
as now. Vary them *between* stacks if convenient — that is useful, not harmful.

**Note the subject in the folder name** (e.g. `pine-cone-deep`,
`petal-smooth`, `stem-occlusion`), because the whole point is correlating
behaviour against subject properties, and EXIF does not record what was in
front of the lens.

**Do not** shoot the same subject twice at different densities and label it two
stacks — fact 50 records how that misled us once already, and fact 69 records a
directory mirrored to a second path being mistaken for a second sample.

---

## 6. Dark frames at working exposure — REQUESTED, very cheap

**What:** the same lens-cap routine you already did, but at the **shutter speeds
you actually shoot**, not 1/100 s. 12–16 frames at each of roughly 1/8 s, 1 s
and 2.5 s. ISO can stay at one value (160 is representative); exposure time is
the variable that matters here, not gain. Lens cap on, body cap is even better,
in a dark room. The first two frames are still discarded, so shoot 14–18.

**Why:** the 242 darks you delivered are all **1/100 s**, but your real stacks
run from 1/60 s to 2.5 s — up to **250×** longer
([M22](research/M22-hot-pixels-measured.md) §4). Dark current accumulates with
time, so a pixel with moderate dark current is invisible at 10 ms and plainly
visible in a 1.3 s frame. The delivered set is a complete map *for the wrong
exposure*.

This is not hypothetical. A cross-scene test with a shift control finds roughly
**839 scene-independent defects** at a 4σ bar, of which the 1/100 s map contains
**5** (M22 §5).

**What it unblocks:** a correct hot-pixel map, and the offset term that goes with
it. Note this is a **low-urgency** request — M22 measured the in-situ impact of
the currently-known defects at ≤ 0.39σ, so nothing is being held up. It is listed
because it is nearly free and because the existing darks cannot answer it.

**What it does NOT affect:** M4's read-noise and FPN results are
exposure-independent and stand as measured.

**Corroborated, and the argument for it is now stronger** (M48c, 2026-08). An
independent census of the same darks by a different criterion finds 0.0414% of
pixels defective (M22 found 0.0346%), 99.8% of them isolated singletons with the
largest cluster on the sensor being 3 pixels -- so the subsystem this unblocks is
a coordinate list and a neighbour median, nothing more. What changed is the case
for building it at all: the merge was measured against a contrast-matched control
and its defect-specific amplification is **1.00 +/- 0.08**. It lifts a hot pixel
and genuine detail of the same contrast by the same factor. **The estimator will
never remove these, so they cannot be left to it.** The urgency is still low --
in-situ impact is <= 0.39 sigma -- but the request is no longer only about
completeness.

**One near-free addition, if you are shooting this anyway.** Shoot the same
frames a second time at **ISO 1000** as well as at ISO 160. Cost: one dial, same
session, same cap. Why: the delivered darks turned up a **2.17x step in
dark-current electrons falling exactly at the ISO-400 dual-gain switch**, which
says the shipped DN-to-electron conversion is extrapolated above ISO 400 (facts
790-795). A long exposure makes dark current 100-250x larger, so the same step
measured there has far better signal than the 1/100 s frames could give it, at a
completely different exposure. If the step is an artefact of the short exposure it
will not survive; if it is a conversion-gain property it will reproduce. Either
outcome is worth the dial.

---

## 7. Aperture pair — REQUESTED, cheap, high value

**Status:** requested. One afternoon. Turns §0's derived table into a
measurement, and §0 is currently the largest quality claim in the project
resting on a model rather than on data.

**What to shoot.** One subject, two brackets, back to back, nothing else changed:

| | Bracket A | Bracket B |
| --- | --- | --- |
| Aperture | **marked f/11** (as currently shot) | **marked f/5.6** |
| Frames | as you would normally shoot it | **about 2x** bracket A |
| Depth covered | identical | identical |
| ISO, lighting, magnification, subject | identical | identical |
| Exposure | metered normally | metered normally (it will be shorter) |

Choose a subject with **fine high-frequency detail** — chitin, fabric weave,
sand, hairs. Smooth subjects cannot show the difference because they have no
energy at the frequencies diffraction is removing.

**Do not** try to match total exposure time or total light between the two.
The comparison the project needs is the one a photographer would actually make:
the same subject, shot the way each aperture wants to be shot.

**What it settles.** Whether the 9.6x contrast figure in §0 survives contact with
a real lens. The model assumes a diffraction-limited system; a real lens at f/5.6
also has aberrations that f/11 suppresses, and the model does not know about
them. If aberrations dominate at f/5.6 the advantage shrinks — and that is
exactly the number nobody has.

If it is convenient, a third bracket at **marked f/8** makes it a curve rather
than a pair.

### Added by M35 — frame count is now load-bearing, and it settles a second question

**This same shoot also answers question 70**, but only if the brackets are
**denser than normal**. Shoot **at least 2.5× your usual frame count** for the
subject — roughly **80–120 frames** rather than 30–40 — at each aperture.

The reason is a gate M33 wrote and M35 applied. A dense bracket is used as its own
ground truth by decimating it and asking what the sparser version lost; that is
honest only if the dense grid's **own** sampling deficit is much smaller than the
one being measured. `coffee-bean` (105 frames) clears it at **3.62×**.
[M35](research/M35-fit-generality-measured.md) measured the two existing stacks
that would otherwise have answered question 70 and **both failed**:

| stack | frames | marked f | headroom | |
| --- | --- | --- | --- | --- |
| `119MSDCF` | 33 | f/5.6 | **2.18×** | ❌ too coarse to be its own reference |
| `112MSDCF` | 79 | f/11 | **2.10×** | ❌ too coarse to be its own reference |

So the aperture question cannot be answered from what is already on disk, and the
shortfall is frames, not light. `119MSDCF` also has **7.38%** of its pixels
peaking at the very edge of the bracket, which means the 33 frames did not cover
the subject's depth at all.

Practically: pick a subject shallow enough that 100 frames still covers it
comfortably end to end, and let the bracket run past the subject on both sides.
Depth coverage and frame density are both required; neither substitutes for the
other.

---

## 8. Tilted planar target — REQUESTED, cheap

**Status:** requested. Not blocking, but it is the only source of **analytic
ground-truth depth** available without a rail, and the project currently scores
every depth and merge result against plants it made up itself.

**What to shoot.** A **flat, densely textured, rigid surface**, positioned at a
steep angle to the sensor plane so that focus sweeps across it, captured as an
ordinary in-camera focus bracket.

| | |
| --- | --- |
| Target | Flat and rigid: fine sandpaper, a printed noise/grid pattern on card, a banknote, a ceramic tile with texture. **Not** paper that can curl. |
| Texture | Dense and broadband. A printed random-dot or noise pattern is ideal; a regular grid is acceptable but aliases. |
| Angle | Steep — roughly **30-60 degrees** to the sensor plane, so the near and far ends of the frame are several depths of field apart. |
| Frames | 40+, covering near edge to far edge. |
| Aperture | Shoot it **twice**, at marked f/5.6 and marked f/11, if that is cheap. This makes it serve §7 as well. |
| Also record | Roughly what the tilt angle was, and the approximate near and far distances. Rough is fine — the *planarity* is what matters, not the numbers. |

**Why it is worth an afternoon.** A plane is the one subject whose true depth map
is known in closed form up to three parameters, and those three parameters can be
fitted from the data itself. So:

- **Depth accuracy becomes measurable**, not merely plausible. Fit a plane to the
  estimated depth map; the residual *is* the error, per pixel, with no oracle.
- **The confidence map becomes testable.** Confidence claims to predict where the
  estimate is wrong. On a plane that is a direct check: does predicted uncertainty
  correlate with actual residual?
- **It is a null for occlusion.** A plane has no depth discontinuities anywhere,
  so any bimodality, halo or occlusion flag the pipeline raises on it is a **false
  positive**, by construction. The project has no such null today.
- **It calibrates the focus axis.** **Careful: it is *inverse* depth that is
  affine in image coordinates, not depth** — a tilted plane in object space maps
  to `1/Z` linear in `(x, y)`, and fitting `Z` itself linearly is a systematic
  error that grows with tilt (M84b, fact 1159; M84b measured this on the ruler,
  where a linear-in-`Z` fit is wrong by a measurable margin at 77° tilt). Fit
  `1/Z`, then invert. Done that way, the fitted per-frame focus position must be
  monotone and smooth — an independent check on fact 54's pixel-measured focus
  index and on the depth-from-breathing idea. **This bullet said "depth is linear
  across the frame" until 2026-08-24; that was wrong, and the same error is in
  both M84 briefs.**
- **It is the only thing that makes per-pixel focus *admission* correctness
  measurable on real frames.** M67 measured whether the shipped merge admits the
  frames actually in focus at each pixel — `H` = 99.955 % on a simulated tilted
  plane — and could not run that measurement on a single real stack, because
  `H` needs a per-pixel true in-focus index and no corpus stack has one. A plane
  supplies it without an oracle: fit the three plane parameters from the data,
  convert to a per-pixel focus index, and `H`, the miss distance and the
  admitted-set defocus all become real numbers instead of simulated ones. That
  converts M67's headline from an **idealised-PSF upper bound** into a
  measurement. See `docs/research/M67-focus-correctness.md` §8.
  **For this use the two f-stops matter more than usual** — the whole
  uncertainty in M67's result is optical, and a second aperture is a second
  through-focus curve to check the merge against.

**One trap.** Fill the frame with the target and nothing else. A visible edge,
background or mount reintroduces exactly the depth discontinuity the null is
supposed to exclude.

---

## 9. Corpus locations — read-only

**Never write to any of these.**

| Path | Contents |
| --- | --- |
| `C:\dev\macro\test\` | The original three stacks: `109MSDCF` 22, `119MSDCF` 33, `coffee-bean` 105. |
| `D:\macro-dark-frames\` | 11 ISO subdirectories x 22 frames = 242 darks. §1. |
| `D:\personal\macro\` | Seven stacks. Three are **byte-identical duplicates** of `C:\dev\macro\test` (verified by count, size and MD5) — do not treat them as independent evidence. Four are new. |

The four new stacks, all on the same rig (`LensType3` 33094), characterised in
fact 49:

| Stack | Frames | Focus sweep | Pace | Use |
| --- | --- | --- | --- | --- |
| `112MSDCF` | 79 | 0.3189 → 0.3297 m | 0.51 s/frame | **The fact-43 pair.** Same subject and same sweep as `113MSDCF`, preview-NCC **+0.9961**. Fit the span-dependent shrinkage on one, test on the other. |
| `113MSDCF` | 63 | 0.3189 → 0.3297 m | 0.52 s/frame | As above. |
| `foam` | 100 | 0.2707 → 0.2841 m | 2.52 s/frame | **Not an alignment benchmark.** The scene evolves across the 249-second capture: it decorrelates *within itself* to 0.087/0.122/0.243 where `coffee-bean`, an equally deep sweep, holds 0.979/0.941/0.970. Useful only as a hard case for non-rigid scenes. |
| `coffee-bubbles` | 19 | **none** (0.2841 m throughout) | 3.33 s/frame | A *soft* null for the aligner — at fixed focus any reported transform is drift or estimator bias, not parallax. Contaminated by real bubble motion (0.947 first-to-last), so it bounds bias from above rather than measuring it. |

---

## 10. Two frames at ISO 64 — REQUESTED, trivial, closes a guess in shipped code

**Status:** requested 2026-08-23. **Thirty seconds of work.** It is the only
item in this file that removes a constant I had to guess at rather than measure.

**What to shoot.** Point the camera at anything with a bright area — a window, a
lamp, a sheet of paper. Then, **without moving anything or changing exposure**:

- 2 frames at **ISO 64**
- 2 frames at **ISO 80**
- 2 frames at **ISO 50** and 2 at **ISO 100** as the brackets

Any subject, any aperture, handheld is fine. It does not need to be sharp, flat,
or well-composed. It needs *signal* and it needs the four ISOs to see the same
scene. Untouched RAW.

**Why.** Sony ISO 50 is an **extended / pull** setting: the sensor reads out at
base-ISO-100 analogue gain and the stop is taken in exposure. So `g = ISO/436.8`
is wrong by **2.05×** at ISO 50, which corrupts the noise floor the merge gate is
denominated in — measured, and fixed in `2a4f5c5` by clamping `g` at a
`base_iso` of 100.

**But the clamp's location is a guess.** ISO 50 is measured wrong and ISO 100 is
measured right. **The corpus contains nothing in between**, so `max(ISO, 100)` is
the simplest rule consistent with the evidence, not a located transition. ISO 64
and 80 are the only two settings between them. Two frames each and the guess
becomes a measurement.

**How it will be read.** Per-pixel temporal variance across the frame pair at
matched mean, compared against the ISO 50 and ISO 100 brackets. If ISO 64 reads
at the ISO-100 level it is also a pull setting and the clamp is right. If it
reads at 64/436.8, the clamp is wrong and the transition is real.

**One trap.** *Do not* change shutter or aperture to compensate for the ISO — let
the frames get brighter. The measurement compares noise at a **known analogue
gain**, and re-exposing to equalise brightness destroys exactly the difference
being measured.

## 11. Dark frames at ISO 160 -- REQUESTED, trivial, closes a hole in a shipped constant

**Cost: about a minute, indoors, lens cap on. No daylight, no subject, no rail.**

`read_noise_e_low = 4.20` is a shipped sensor constant. It governs every frame the
camera takes below ISO 400, and in this corpus that means **ISO 50 and ISO 160**.

It has been checked at ISO 50 and ISO 100 and is accurate there (-2.5% and -2.3%).
**It has never been checked at ISO 160**, because the 242-frame dark set delivered
earlier has no ISO-160 row -- while the corpus has **22 real captures** at that ISO.
The constant is validated everywhere except the setting it is used at most.

This is not expected to be a large error. It is a hole in a claim, and the claim is
cheap to close.

### What to shoot

**22 frames at ISO 160, lens cap on, in a dark room, same shutter speed as the other
dark sets.** Identical procedure to the darks already delivered:

- Lens cap on, and the body's own cap if the lens is off. Total darkness matters more
  than the room being dark -- any light leak invalidates the whole set.
- **Discard the first two frames.** The earlier set was shot this way and it was the
  right call; the sensor settles.
- Same shutter speed and same body temperature regime as the existing darks, or the
  comparison against ISO 50 and ISO 100 is not like-for-like.

### Why this cannot come from existing files

Read noise is measured from frames with **no signal**. Every ISO-160 frame in the
corpus is a photograph of something, so its variance is dominated by shot noise from
the subject. There is no way to recover a read-noise floor from a lit frame at the
precision this needs. The 242 delivered darks cover ISO 50, 100, 200, 250, 320, 400,
500, 640, 800, 1600 and 2000 -- **160 is the gap, and it is the one that matters.**

### What it unblocks

Answers question 172 and closes fact 732. Either the constant is accurate at ISO 160,
in which case a shipped number stops being a guess at the setting it is used at most,
or it is not, in which case the corpus has been carrying a measurable error on 22 of
its frames and the shape of the correction becomes visible.

**One trap.** Do not change the ISO by using a different exposure mode that might pull
or push. Set ISO 160 explicitly. The whole point is the analogue gain at that specific
setting, and an ISO the body reaches by a different route is a different measurement.

**M69 corroboration (2026-08).** M69 re-measured read noise on the delivered darks
across 11 ISO groups and found the shipped model over-predicts it by **8-27%** at
every ISO measured -- empirical read noise runs 0.73x-0.92x the model's `RN*g`, and
the deficit grows with ISO (0.9225 at ISO 50 and 100, 0.7306 at ISO 1600). ISO 160
is still the gap, it is still the ISO of M62's own certified plant, and the
discrepancy this would resolve is now known to be larger than "not expected to be a
large error" assumed. See
[`docs/research/M69-focus-noise-sd.md`](research/M69-focus-noise-sd.md) fact 24.


## 12. Static repeat burst -- REQUESTED, 30 seconds, highest value per unit effort

**Status:** requested 2026-08, in response to the owner asking what else would
help. **Nothing in the corpus can substitute for it and nothing else on this list
is as cheap.**

**M69 corroboration (2026-08, urgency raised).** M69 was chartered on the
understanding that this burst had been delivered. It has not. M69 established
that the quantity `FOCUS_NOISE_SD` measures -- the response noise of the focus
operator -- **is not measurable at all from a focus sweep**, at any effort, by
any estimator of the family tried: macro depth of field is one to two frames
wide by design, so a per-pixel through-focus curve is a narrow peak that no
smoothing window wide enough to average down the noise can follow. M69's arm A5
was voided by its own pre-registered control for exactly this reason. This is the
difference between *not measured* and *not measurable*, and it now blocks a
shipped constant that every gate, every published `n_eff`, `DEFAULT_GATE = 4.0`
and the certified acceptance result are denominated in. See
[`docs/research/M69-focus-noise-sd.md`](research/M69-focus-noise-sd.md) facts
26-27.

**M81 corroboration (2026-08, and it is now the only route left).** M81 tested the
last hypothesis that could have avoided this capture: that the gate's dispersion
across stacks was a miscalibrated *unit*, repairable by estimating
`FOCUS_NOISE_SD` per stack from the focus sweep itself. **Refuted, and the
correction made things worse** -- the sibling-stack gate span moved from 3.254x to
3.629x, past its pre-registered 2x line, and the five-stack span is 49.538x, with
three independent estimators agreeing. See
[`docs/research/M81-estimation-merge.md`](research/M81-estimation-merge.md) facts
9-10. **Two milestones have now failed to calibrate the gate from focus-sweep data,
and M81's closing sentence names this burst as the minimum capture for the
remaining route.** It costs thirty seconds.

**M91 corroboration (2026-08, a third milestone, arriving from an unrelated
direction).** M91 was chartered on photometric drift, not on noise, and it
reached this same capture by its own route. It needed to know whether the
per-frame brightness drift is spatially **uniform** across the frame or varies
across it, because that single unknown decides whether a global per-frame gain
recovers **100.0%** of the drift or **13.42%** of it -- measured on plants, and
the reason its verdict is NO SHIP rather than "ship gain-only". It built two
instruments to answer it from the existing stacks and **retired both**: handed a
disturbance uniform by construction, they failed to detect it on 6 of 6 stacks.
The mechanism is the same one M69 hit: **on a focus stack, block-level variation
is dominated by defocus**, so no block-domain statistic can separate a
photometric gradient from the focus sweep. See
[`docs/research/M91-photometry.md`](research/M91-photometry.md) `P6`, `P7`.

**Three milestones, three unrelated charters, one capture.** M69 needed it for
response noise, M81 for the gate, M91 for photometric structure. Each
independently found that the quantity it wanted **cannot be estimated from a
focus sweep at all**, because a focus sweep varies the one thing that has to be
held still. That is not three requests for convenience; it is the same
structural limit met three times.

**One clarification, because the two claims look contradictory.** M62 found that
a static burst has **no focus variation and therefore no interior optimum**, so a
burst cannot arbitrate a *gate*. That is correct and it does not weaken this
request. A burst is the only capture that can arbitrate a *noise level*, and for
precisely the same reason: with focus held still, every frame-to-frame response
difference is noise by construction. The two findings are complementary.

**A second, sharper argument, added after M69's amendment.** Every synthetic
replicate experiment in this corpus freezes a single real frame as its latent.
But a real frame is `T + eta`, so the frozen latent carries `2 s^2` of gradient
energy that the true scene does not, and every response-noise number measured
that way is inflated by it. M69 measured the size of that inflation by planting
extra frozen realisations and watching the number climb (its facts 39-40): on
M62's own plant it accounts for roughly a quarter to a half of the excess. **The
defect-free latent cannot be constructed from one frame at all** -- the only way
to observe a scene without a frozen noise realisation in it is to average many
frames at one focus position, which is exactly this capture. Until it exists,
every replicate study in the corpus carries a bias whose size can be estimated
but not removed.

### What to shoot

| | |
| --- | --- |
| Subject | **A real macro subject with fine texture** -- any of the ones already shot is ideal. Not a test chart, not a flat surface. |
| Frames | **30**, back to back. |
| Focus | **Do not touch it.** No bracketing, no refocus, no drift. One focus position for all 30 frames. |
| Everything else | **Change nothing.** Same aperture, same ISO, same shutter, same light, tripod, electronic shutter or 2-second self-timer. |
| Exposure | **A working exposure** -- whatever you would really use, in the 1/8 s to 2.5 s range the real stacks use. |
| Format | RAW (.ARW), all noise reduction off. |
| Repeat | If cheap, do the same 30 frames again at **ISO 400** without moving anything. |

Discard the first 2 frames, as with the darks.

### Why this is worth more than another focus stack

**It is the only capture that gives the merge a problem whose right answer is
known exactly.** Every frame is a sample of the *same* latent image, so the true
merge output is the scene itself and the true noise reduction is exactly
`sqrt(N)`. Nothing else in the corpus has that property: in a focus stack, every
frame differs both in noise *and* in focus, and the two cannot be separated
without a model -- which is the very thing under test.

That gives four things at once, none of which the project currently has:

1. **An empirical null for the entire estimation thesis.** The merge must return
   `sqrt(30)` = 5.48x noise reduction here. Any shortfall is the estimator's own
   inefficiency, measured directly rather than argued. The corpus currently prices
   the gated mean at 0.534x (fact 19) against a *reference* that is itself
   estimated; this measures it against arithmetic.
2. **A placebo that can actually fail.** Discipline 250 records that this corpus
   has already shipped three checks incapable of failing. A merge that secretly
   selects rather than estimates will score ~1.0x here while a true estimator
   scores 5.48x. **No existing test separates those two outcomes.**
3. **Sigma at working exposure, which no delivered capture provides.** The 242
   dark frames are all 1/100 s, but real stacks run 1/8 s to 2.5 s -- a 12x to
   250x longer integration. That gap is the binding limitation on the whole
   sensor model (fact 808: only ~5 of ~839 real defects appear in the dark map).
   A repeat burst measures the per-pixel temporal noise at the exposure that
   actually matters, and does it on a real scene rather than in the dark.
4. **The hot-pixel and dust map at working exposure, for free.** Both are fixed in
   sensor coordinates and both survive averaging over a static burst, so they
   stand out against a scene that does not move. This is the capture that makes a
   defect map possible, and fact 800 established the merge is blind to defects
   (D_defect/D_control = 1.00 +- 0.08) and therefore cannot be relied on to hide
   them.

**The ISO 400 repeat, if taken, straddles the dual-gain boundary on a fixed
scene** -- the same instrument as `bee-2`/`bee-3` (fact 847) but with focus held
constant too, which removes the last confound from question 184's split.

### 12b. A second contrast level on the same static burst -- REQUESTED by M69

**Cost: 30 more frames, same session, same setup, one thing changed.**

If §12 is shot, shoot it **twice more on the same subject at two clearly
different contrast levels** -- easiest by changing the light (diffuse versus
raking) rather than the subject, so the texture's *spatial* statistics are held
and only its *amplitude* moves. Focus untouched throughout, as above.

**Why one contrast level is not enough.** M69 measured that the focus operator's
response noise does not vary with signal-to-noise the way the shipped model
assumes. It varies by **4.06x** on a controlled plant -- from `0.28x` to `1.14x`
the shipped constant -- driven by whether the deterministic gradient *direction*
stays coherent across the operator's 27x27 window, not by contrast. A burst at
one contrast level measures a point; two levels on the same texture separate the
two candidate mechanisms M69 could not separate:

- **direction coherence** (M69 fact 19, DERIVED) predicts response noise barely
  moves between the two contrast levels, because the texture's geometry is
  unchanged;
- **rectification of a noisy gradient** (the pointwise model M69 refuted, and the
  one the shipped constant implicitly assumes) predicts it rises with contrast
  toward a fixed ceiling.

They differ by a factor of about three on this capture and by nothing at all on a
single-contrast burst. **This is the capture that decides whether the shipped
scalar can be replaced by a derived per-pixel field**, which M69 fact 32 prices as
a 1.09x-1.72x change in `n_eff` -- 20 to 50 times larger than correcting the
constant's value.

**One trap.** Change the light, not the exposure. Re-exposing to compensate
restores the amplitude and measures nothing.

---

## 13. Three variations on stacks you have already shot -- REQUESTED, cheap

Each is one stack, and each buys something structural. Roughly in value order.
All three should be shot **with the polariser in a known, recorded state**.

**13a. Half-step interleave.** Reshoot any subject you have already stacked, with
the focus step **halved** -- or simply shoot the same range twice, the second pass
offset by half a step. Doubling the sampling density along the focus axis is what
lets a reconstruction-based merge recover detail between frames rather than
picking the best of them. It also directly tests whether the current step size is
already adequate, which is currently assumed and never measured.

**13b. Without the teleconverter.** The same subject at 100 mm, **2x TC removed**.
Every stack in the corpus is at 200 mm with the converter fitted, so the
converter's contribution to the point-spread function is entangled with the
lens's and neither has ever been observed alone. This separates them, and it tests
the `N_eff = N_marked * (1 + m/p)` model at a genuinely different magnification
instead of extrapolating it.

**13c. A deliberate occluding edge.** A pin, wire, bristle or blade of grass held
**in front of** a well-textured background at a clearly different depth, then
focus-bracketed through both. Occluding edges are where every focus stacker on the
market produces halos, and the corpus contains them only incidentally, never by
design. A capture that isolates one turns the halo from an anecdote into a
measurable quantity with a known correct answer -- the background is genuinely
visible in some frames, so the truth is recoverable.

**13d. Leave the subject's silhouette in frame.** Not a new capture -- a framing
rule for any of the above. M73 could check whether the stacker admits the right
frames along one axis of a cylindrical subject, but its check was blind to any
error that is constant along that axis. The arm that would have closed the blind
spot needs the subject's **outline against the background**, and every stack in
the corpus is framed tight enough to crop it away. Backing off far enough to keep
even a sliver of background around the subject costs nothing and makes the
geometry of the subject measurable from the image instead of assumed. **The one
failure mode that milestone named in advance is the one it could not test, purely
because of framing.**

---

## 14. One scene at several ISOs -- REQUESTED, one tripod afternoon, separates two axes the corpus welds together

**Status:** requested 2026-08 by M69 Part II, which needed it and could not
synthesise it.

**What to shoot.** **One** static scene -- tripod, focus untouched, framing
identical -- captured at **ISO 100, 400, 1000 and 3200**, roughly 8-10 frames at
each. Exposure compensated by shutter so the rendered brightness matches across
ISOs. Texture should be ordinary macro subject matter, not a chart. Any subject
already in the corpus is ideal, because it makes the comparison direct.

### Why the corpus cannot answer it

**ISO is perfectly confounded with scene in the existing 12 stacks.** M69 fact 63
found its per-pixel noise predictor P2 tracks the directly-measured response to
within +-3.6% on 10 of 12 stacks and fails on exactly two -- `coffee-bubbles`
(1.591x) and `foam` (1.335x). **Those are the corpus's only two ISO-1000 stacks.**
They are *also* the corpus's only two fine, self-similar bubble/foam textures. At
n = 2 with a perfect association, the corpus cannot say which axis is
responsible.

M69 ran arm B6 to break the confound synthetically -- fixed scene, swept
*declared* ISO through the shipped noise model -- and it points clearly at texture
(fact 64: a low-ISO scene driven to declared ISO 1000 stays at 0.990 and 0.986,
nowhere near 1.59). **But B6 sweeps a declared ISO over a frozen latent. It tests
the model's arithmetic, not the sensor's behaviour**, and it cannot see any real
ISO-dependent effect the profile does not already model. That distinction is the
whole reason this capture is owed rather than assumed away.

### What it unblocks

1. **Separates ISO from texture at the capture level**, which settles the domain
   statement M69 owes for P2 (its section 9.1 item 4, corrected by fact 65).
2. **Tests fact 24's 8-27% read-noise over-prediction on the focus response
   rather than on darks.** Fact 24 is measured on dark frames; whether that error
   propagates into `sigma_F` at the ISOs the corpus actually shoots is currently
   unknown, and this is the only capture that would show it.
3. It is **"not measured", not "not measurable"** -- one afternoon with a tripod,
   and no equipment the owner does not already have.

**One trap, and it is the same one as section 11.** Set each ISO explicitly. Do
not let the body reach an ISO by auto or by a pull/push route; `profile.rs:205`
floors gain at `base_iso`, so an extended ISO below 100 is *not* a distinct
measurement (M69 fact 66) and would waste a quarter of the session.

See [`docs/research/M69-focus-noise-sd.md`](research/M69-focus-noise-sd.md)
section 14.6 and facts 63-66.

---

## 15. What is NOT needed, so you do not waste a session

- **Another ordinary focus stack of a new subject.** The corpus has 12 stacks and
  1,568 frames. More of the same adds subjects, not information; every item above
  adds a *degree of freedom the corpus currently cannot separate*.
- **Anything requiring a focus rail.** Deferred permanently, per section 2.
- **Higher-resolution or more careful versions of existing stacks.** Nothing on
  this list is blocked by capture quality.


## 16. DELIVERED 2026-08-23 evening -- twelve new stacks, and three outstanding requests are closed

**Status:** delivered without being itemised. The owner shot these overnight and
renamed several older folders to record the polariser. **Read this section before
citing any capture path written before 2026-08-23.**

### 16.1 A breaking rename -- old paths are dead

**MEASURED.** Folders shot with the circular polariser now carry a `-cpl` suffix.
**`D:\personal\macro\bee-1` no longer exists; it is `bee-1-cpl`.** Verified at
the filesystem. `bee-1` is one of the five stacks M77, M81 and M82 are all
denominated in, so **any script, log or JSON written before this date that names
`bee-1` is now broken**, and any run that silently skipped it is void rather than
merely incomplete. `109MSDCF`, `112MSDCF`, `113MSDCF`, `119MSDCF`, `coffee-bean`,
`coffee-bubbles`, `foam`, `wrapped-text-1` and `wrapped-text-2` are unchanged.

### 16.2 What arrived

**MEASURED via `exiftool`.** All twelve are **f/5.6 marked** at **200 mm** -- the
100 mm macro with the 2x teleconverter -- and each is internally uniform in ISO
and aperture.

| Stack | Frames | ISO | Why it matters |
| --- | ---: | ---: | --- |
| `bee-2-cpl` | 299 | **400** | With `bee-3-cpl`, a **controlled ISO pair on matched content** |
| `bee-3-cpl` | 299 | **100** | Same subject, same 0.2771 m start, same aperture as `bee-2-cpl` |
| `highly-angled-ruler-mm-cpl` | 299 | 100 | **A millimetre ruler at a steep angle -- analytic depth ramp with a metric scale** |
| `flat-on-ruler-cpl` | 79 | 100 | The same ruler flat-on; the zero-tilt control for the above |
| `flower-bud-alone-cpl` | 205 | 100 | With the next row, an **occlusion pair**: the same subject with and without a background |
| `flower-bud-with-background-fern-cpl` | 299 | 100 | Adds a defocused fern behind the bud |
| `dry-erase-marker-head-cpl` | 299 | 100 | Manufactured subject, hard edges |
| `couch-fibers-cpl` | 299 | 400 | Dense fine fibre texture |
| `leaf-2-cpl` | 182 | 400 | Natural texture |
| `lavendar-cpl` | 299 | 200 | Natural subject at a third ISO |
| `flowers-cpl` | 176 | 100 | Natural subject |
| `lead-1-cpl` | 123 | 100 | Pencil lead, fine parallel structure |
| `tweezers-cpl` | 100 | 100 | Specular metal |

### 16.3 Three standing requests are now closed, and one is not

- **Section 8, tilted planar target -- CLOSED, and better than asked.**
  `highly-angled-ruler-mm-cpl` supplies an analytic depth ramp **and** a metric
  scale in the same frame, with `flat-on-ruler-cpl` as the zero-tilt control.
  A ruler gives ground-truth depth *and* a physical length reference, so the
  focus axis can be calibrated in microns without trusting EXIF or a lens model.
- **Section 14, one scene at several ISOs -- CLOSED for the noise question.**
  `bee-2-cpl` (ISO 400) against `bee-3-cpl` (ISO 100) holds subject, distance,
  aperture and frame count fixed and varies only ISO. **This is the strongest
  control the corpus has ever had for anything denominated in sigma**: a
  correctly noise-denominated quantity must be invariant across it, and if it
  is not, the defect is in the sensor model rather than in the algorithm.
  The wider ISO ladder across `lavendar-cpl` (200) and the ISO-400 stacks is a
  bonus but is *not* matched content and must not be read as one.
- **Occluding-edge cells -- CLOSED as a comparison pair.** `flower-bud-alone-cpl`
  and `flower-bud-with-background-fern-cpl` differ by the presence of a
  defocused background. **This is not ground truth for what lies behind the
  occluder** -- the bud is opaque and the alone-version shows a different
  background, not the true one -- but it is a controlled A/B for whether a
  merge's behaviour at the silhouette changes when a background is introduced.
- **Section 12, the static repeat burst -- STILL OPEN.** None of these is a
  static burst: every one is a focus sweep. Two milestones have now failed to
  calibrate the gate from focus-sweep data and both named this capture as the
  minimum for what remains. It is thirty seconds on a tripod with nothing
  moving. **It is still the highest value per unit effort on this list.**

### 16.4 Cautions before anyone uses these

- **MEASURED.** `bee-1-cpl` starts at **0.2707 m** while `bee-2-cpl` and
  `bee-3-cpl` start at **0.2771 m**. The three bee stacks are **not** three
  interchangeable siblings; the clean matched pair is **2 against 3**.
- **ARGUED.** Matching EXIF focus distance is not matching content. Anyone
  treating `bee-2-cpl`/`bee-3-cpl` as a matched pair must **verify the framing
  directly** and report what they found.
- **ARGUED.** ISO 400 against ISO 100 may cross a conversion-gain mode on this
  body. Check the shipped `CameraProfile` carries **measured** values at both
  ISOs, not interpolated ones, before denominating anything in sigma.
- **ARGUED.** These are all f/5.6 marked at 2x teleconversion, so the effective
  aperture is far slower than the marked figure and section 0's diffraction
  arithmetic applies with the teleconverter's magnification included. Nothing
  here has been checked for diffraction-limited detail before use.
---

## 17. Aperture is spent, and the teleconverter is the remaining lever — REQUESTED, one subject, two brackets

> **CORRECTED 2026-08-24, same night, by M84b's measurement.** The first version
> of this section computed `N_eff` with **pupil magnification `p = 1` assumed**.
> That assumption is now **measured false** — `p ∈ [1.31, 1.94]`, and `p = 1` is
> excluded by 0.638 in the bellows factor (fact 1152). **§17.3 originally said
> critical sampling was "unreachable, off the dial". That was wrong and it is
> reversed below: f/5.6 wide open already sits ABOVE critical sampling.** The
> capture request in §17.4 onward is unaffected and still stands. Facts 1151,
> 1152, 1153 and 1157 record the error and its blast radius.

**Added by the orchestrator 2026-08-24 after auditing the rig's optical
ceiling at primary source. Two corrections to this document come first,
because both change what §0 tells you to do.**

### 17.1 §0's advice has already been taken, and the lever is now empty

§0 tells the owner to stop shooting at marked f/11. **They have.** Every stack
in the 2026-08-23 delivery is **f/5.6 marked**. More importantly, `exiftool` on
`bee-3-cpl` reports:

```
FNumber          : 5.6
MaxApertureValue : 5.6
LensSpec         : FE 200mm F5.6 Macro OSS
LensModel        : FE 100mm F2.8 Macro GM OSS + 2X Teleconverter
```

`MaxApertureValue == FNumber` means **f/5.6 is wide open with the teleconverter
fitted.** There is no wider setting. §0's "raise the aperture" lever, which it
correctly called the largest single quality lever in the project, **is fully
spent on the current rig.** Nothing further can be gained along that axis
without changing hardware, and §0 should be read from here as *satisfied*
rather than *pending*.

### 17.2 §0's table is wrong in both directions, because it assumes m = 2.0 *and* p = 1

§0 derives from "working at 2:1", i.e. `N_eff = N × 3`. **Both inputs behind
that are now measured, and they push opposite ways.** Magnification is
**m = 2.7198 ± 0.0051** (M84b, measured from graduation spacing with no lens
model and no EXIF trust) — *higher* than §0 assumed, which would make things
worse. But pupil magnification is **p ∈ [1.31, 1.94]**, with **p = 1 excluded**
— and that makes things *better*, by more than the magnification costs.

The right move is to stop reconstructing `N_eff` from `m` and `p` at all, and
use **M5's directly measured bellows factor `B ≡ N_eff/N ∈ [2.41, 3.06]`**,
which was measured from the cutoff and the marked aperture with **neither `m`
nor `p` as an input**:

| marked | `N_eff` at m=2.0, p=1 (§0) | `N_eff` from M5's measured `B` | §0 was |
| --- | --- | --- | --- |
| f/4 | 12.0 | 9.6 – 12.3 | about right at the top of the range |
| f/5.6 | 16.8 | **13.5 – 17.2** | about right at the top of the range |
| f/8 | 24.0 | 19.3 – 24.5 | about right at the top of the range |
| f/11 | 33.0 | 26.5 – 33.7 | about right at the top of the range |

**§0's numbers turn out to sit at the pessimistic edge of the measured range
rather than being wrong by 25%**, because its two errors largely cancelled.
Its direction and its conclusions stand. Quote the measured range, not the
point estimate.

### 17.3 The consequence: f/5.6 is already better than critically sampled

Critical sampling — diffraction cutoff placed exactly at sensor Nyquist
(97.66 cy/mm at 5.12 µm pitch) — needs `N_eff ≤ 18.62`.

Using M5's measured `B`:

| marked | `N_eff` (B = 2.41 → 3.06) | cutoff `f_c` | vs Nyquist | MTF @ Nyquist |
| --- | --- | --- | --- | --- |
| **f/5.6 (current)** | 13.5 – 17.2 | **106 – 135 cy/mm** | **above** | **0.026 – 0.165** |
| f/6.3 | 15.2 – 19.3 | 94 – 120 | borderline | 0.000 – 0.092 |
| f/7.1 | 17.1 – 21.8 | 84 – 106 | borderline | 0.000 – 0.027 |
| f/8 | 19.3 – 24.5 | 74 – 94 | **below** | 0.000 |

**Critical sampling is at marked f/6.08 – f/7.72**, depending where `B` falls in
M5's measured interval. **f/5.6 wide open already sits above it.** The optics
outrun the sensor at the aperture the owner is already using.

*An earlier version of this section said critical sampling required f/4.95 and
was "off the dial". That was computed at `p = 1` and is **wrong**. The rig is
not aperture-starved; it is correctly, even slightly generously, sampled.*

**The practical advice therefore inverts.** Do **not** stop down for depth of
field — at f/8 the MTF at Nyquist is already zero across the whole measured
range of `B`. There is at most about one stop of headroom and possibly none.
**f/5.6 wide open is the right aperture and should stay there.** Depth of field
should be bought with **more frames at finer focus steps**, which is free in
capture time terms at 23.6 s per 299-frame stack — and which the rig needs
anyway: the current bracket **under-samples its own depth of field by 1.8–2.3×**
(fact 1159, DoF 18.7–23.8 µm at `c` = 1 sensor px against a measured 42.20 µm
mean step).

### 17.4 But removing the converter is *not* obviously right — and this is the capture

The naive reading of §17.3 is "take the teleconverter off". **A subject-referred
calculation says the opposite, and the disagreement is exactly why this needs to
be shot rather than argued.**

Comparing what is resolved *on the subject* (system MTF = diffraction × pixel
aperture, capped at the `m × Nyquist` sampling limit), **recomputed at M5's
measured bellows factor** rather than at the refuted `p = 1`:

| configuration | m | `N_eff` | detail at MTF≥0.2 | finest feature | detail at MTF≥0.5 |
| --- | --- | --- | --- | --- | --- |
| **2× TC, f/5.6 wide open — B = 2.41** | 2.72 | 13.5 | **223.8 cy/mm** | **2.2 µm** | **131.1 cy/mm** |
| **2× TC, f/5.6 wide open — B = 3.06** | 2.72 | 17.2 | **184.1 cy/mm** | **2.7 µm** | 107.6 cy/mm |
| bare lens, max mag, f/2.8 — `p` unmeasured | 1.40 | 5.4 – 6.7 | 136.7 cy/mm | 3.7 µm | 105.9 – 116.5 cy/mm |

**The converter wins on fine detail decisively, and the contrast penalty that an
earlier version of this table reported has largely evaporated.** At `p = 1` the
ordering reversed at MTF≥0.5 (91.3 against 105.9); at the *measured* bellows
factor the TC configuration reaches 107.6–131.1 cy/mm and now ties or beats the
bare lens on contrast as well. Without the converter the *sensor* badly
undersamples the lens — the sampling wall falls at 136.7 cy/mm subject-referred
and the optics are nowhere near it — so the converter moves the binding
constraint from **sampling** to **optics** and buys real detail.

*Two caveats, stated honestly. (1) This is diffraction-only. It **ignores
teleconverter aberrations**, which are real, and the converter is a third-party
Viltrox with no published MTF, so they cannot be bounded from a datasheet. The
table is an upper bound on the converter's case; real aberrations move it toward
the bare lens. (2) **The bare-lens row is not measured.** M5's `B` was measured
with the converter fitted, and a teleconverter changes the system's exit pupil,
so `p` does not transfer. The bare-lens `N_eff` is bracketed over a plausible
`p_bare ∈ [1, 1.5]`, and its ordering against the TC is robust across that whole
range only because the sampling wall — not diffraction — is what binds it.*

**Both caveats are removed by the same capture.** That is the point of §17.4.

### What to shoot

One subject, static, tripod, two brackets back to back. **Do not change the
subject or the lighting between them.**

1. **With the 2x teleconverter**, f/5.6 (wide open), framed as you normally
   would at high magnification. Bracket through the subject's full depth.
2. **Without the teleconverter**, f/2.8 (wide open), **moved closer so the
   subject fills a similar fraction of the frame** if it can; if it cannot,
   frame as tightly as the bare lens allows and note the working distance.
   Bracket through the same depth.

Same ISO, same shutter where possible, same CPL state. Record the working
distance for both. A ruler or any object with a known dimension somewhere in
frame makes the magnification recoverable and costs nothing.

### Why this cannot come from existing files

Every stack in the corpus was shot **with** the converter. There is no bare-lens
capture of any subject at any magnification, so the comparison in §17.4 has no
empirical leg on either side — it is arithmetic against arithmetic.

### What it unblocks

- **Settles §17.4 empirically**, which is currently the largest open question
  about how the owner should shoot, and is unanswerable from theory because the
  deciding term (converter aberrations) is undocumented.
- ~~**Prices the deconvolution thesis on the owner's real gear.**~~ **WITHDRAWN
  2026-08-25 — the thesis it was pricing is dead.** This bullet used to argue
  that a crushed-but-nonzero MTF band is exactly what multi-frame Wiener
  deconvolution is built to exploit. M115 measured that claim directly and it
  failed: `R_SNR = 1.0014` against the **already-shipping** gated average, 95%
  CI **[0.965, 1.038]** — a confidence interval that contains no useful gain in
  either direction. It reallocates information rather than creating it
  (contrast 2.51× bought with noise 2.03×), and it rings, putting **29.5–36.4%**
  of pixels outside the source stack's convex hull with the halo peaking at
  **70.7%** in the 8–16 px shell. **So there is no longer a deconvolution engine
  waiting to be fed, and this capture should not be shot on that basis.**
- **The underlying gear question survives and is the real reason to shoot it.**
  Strip the dead thesis away and what is left still matters to you directly:
  **is the teleconverter costing you resolution you cannot get back?** If
  aberrations have eaten the band, the honest advice is "take the converter
  off," and that is a recommendation about your own shooting rather than about
  the estimator. Note that this is also the only capture that would put **any**
  aperture or converter contrast into the corpus at all — fact 1658 established
  that every `-cpl` stack you have shot is f/5.6 on `FE 100mm F2.8 GM + 2X TC`,
  so both variables are currently held fixed everywhere.
- **Gives the capture advisor its first real recommendation to make**, with a
  measured basis rather than a modelled one.

---

## 18. What M84b needs to finish pinning the rig — REQUESTED, three items, in value order

**Added by the orchestrator 2026-08-24 from `M84b-ruler-metrology.md` §13.** M84b
produced the project's first physical ground truth from the ruler stacks —
**m = 2.7198 ± 0.0051**, a depth map at **8.28 µm** median uncertainty, and the
finding that the focus step **drifts 1.53× across a bracket**. It also stated
plainly what limits it, and none of the three limits is diffraction. **The
binding limit is framing.** These three captures remove them.

### 18.1 A frame-filling diagonal ruler — HIGHEST VALUE, one bracket, ten minutes

**The problem.** M84b had only **13 usable graduations** in frame. Every
uncertainty it quotes is dominated by that, not by optics, not by noise, and not
by the method. More graduations is a direct, linear reduction in the error on
every number it produced.

| Parameter | Value |
| --- | --- |
| Subject | The same millimetre ruler |
| Framing | **Diagonally across the frame, corner to corner**, so the graduations run the full image diagonal rather than a short horizontal span |
| Angle | Same steep tilt as before, roughly 60–80° to the sensor plane |
| Aperture | f/5.6 — wide open, unchanged, and now known to be the right choice (§17.3) |
| Frames | A normal deep bracket, same step as usual |
| Also shoot | The same framing **flat-on** as a zero-tilt control |

**Why the diagonal specifically.** The diagonal is 1.20× the long edge and about
1.80× the short edge, so it buys the most graduations available without moving
the tripod or changing magnification. It also **decorrelates the tilt axis from
the sensor's row and column axes**, which matters because row/column
fixed-pattern noise is anisotropic (M16) and a ruler laid along a sensor axis
confounds the two.

### 18.2 A second angled stack at a different working distance — settles a real disagreement

**The problem.** Two independent milestones measured the same ruler and reached
**opposite verdicts on whether it can serve as ground truth at all** (fact
1156). That disagreement is recorded unresolved rather than reconciled, and it
cannot be settled from the existing captures because both agents analysed the
same two stacks.

A second angled stack at a **different magnification** — say a noticeably closer
or further working distance — gives an independent realisation. It also tests
whether the **1.53× focus-step drift** is a property of the lens's focus
mechanism (in which case it will reproduce, and can be modelled and calibrated
out once, permanently) or a property of that particular bracket (in which case
it must be estimated per stack). **That distinction changes what the aligner has
to do**, so it is worth a bracket.

### 18.3 A pupil-diameter bench measurement — pins `p` outright, no stack needed

**The problem.** Pupil magnification `p` is currently only *bracketed*, at
**[1.31, 1.94]**, inferred from M5's measured bellows factor against M84b's
measured magnification. It was assumed to be 1.0 until tonight, and that
assumption was **wrong by enough to reverse a shooting recommendation** in §17.3
and to nearly ship a false acceptance test to another milestone. Pinning it
removes an inferred quantity from a load-bearing chain.

**This is not a photograph.** It is two measurements with a ruler:

1. Set the lens to the working configuration — **teleconverter fitted**, focus
   at the macro end where the stacks are shot, aperture wide open at f/5.6.
2. Look into the **front** of the lens and measure the apparent diameter of the
   aperture opening. That is the **entrance pupil**.
3. Look into the **back** (with the teleconverter attached, so the rear of the
   TC) and measure the apparent diameter of the same opening. That is the
   **exit pupil**.
4. `p = exit pupil diameter / entrance pupil diameter`.

Photograph both with a ruler laid flat against the barrel and in the same plane
as the pupil, and the numbers can be read off later. **Rough is useful**: even
±10% collapses the current ±19% bracket and, more importantly, it is an
*independent* route to `p` rather than another inference from the same chain.

### What all three unblock

- **Every micron-scale number in the project.** The depth map, the focus-axis
  calibration, the truth-linked estimator loss M81 named as one of only two
  remaining routes to a constant that has now defeated three milestones.
- **The `N_eff` chain, at its root.** `p` currently propagates into diffraction
  cutoff and into the shooting advice in §17. It **used** to propagate into the
  deconvolution ceiling as well; that consumer died on 2026-08-25 (see §17.5),
  so this request is now worth somewhat less than when it was written — but the
  shooting advice is the consumer you actually care about, and it survives
  intact.
- **The M84/M84b disagreement**, which is otherwise permanent.

## 19. A hard edge at three apertures, one session — REQUESTED, the highest-value ten minutes left

**Status: REQUESTED 2026-08-25. Blocks the last inferred quantity in the optical chain.**

**Why this is now the top optical request, above §18.3.** M88 built a validated
slanted-edge instrument to measure the diffraction cutoff directly and could not
use it. The blocker is **identifiability, not precision**. Edge rise obeys
`rise² = d² + c²`, where `d` is the diffraction blur and `c` is everything else
(subject softness, residual aberration). One measurement, two unknowns — and on
every existing capture `c` (~30 µm) is **three times larger** than `d` (7–12 µm),
so *every* candidate cutoff fits the data exactly. More frames cannot fix this.
Better fitting cannot fix this. Only a different capture can.

The instrument itself is not the problem: it was validated to **+1.19% ± 1.50%**
on planted 60–140 cy/mm and reaches **114.6 cy/mm** from a 48.83 cy/mm
sublattice — above the sensor's 97.66 cy/mm Nyquist, which a grid-sampled power
spectrum provably cannot do. **It has nothing sharp enough to point at.**

**The gap is corpus-wide, not a milestone's ROI choice.** All 23 stacks were
surveyed: **no aperture bracket on a fixed subject exists anywhere**. Every
two-aperture comparison so far has also changed subject, pose or session — M88's
own two stacks differed by 2.15° in edge angle, 1.91× in contrast, and were shot
**8 days apart**, which it disclosed against its own passing gate.

### What to shoot

A **genuinely hard edge**: a razor blade, or chrome-on-glass if you have a
target. Backlit, so the edge is a true step rather than a shadow.

1. Fill at least **800 px** of the frame with the edge.
2. Tilt it **3–7° from vertical** — not 0°, not 45°. The slant is what
   supersamples the edge and lets the measurement reach above Nyquist.
3. Shoot at **f/5.6, f/8 and f/11**.
4. **Do not touch the rig between the three.** Not focus, not position, not the
   tripod. This is the entire point of the request: `c` must be *identical*
   across the three so it cancels in the ratio. Change the aperture and nothing
   else.

A single frame at each aperture is enough. This is not a stack.

### Why this works when everything so far has not

The three apertures predict edge rises of **13.65 / 11.97 / 10.37 µm** — a **24%
spread**, measured at ~1.5% precision. That is resolved **16× over**. With `c`
held fixed by construction, three measurements and two unknowns is
over-determined, and the cutoff falls out.

### What it unblocks

- **`p` outright.** The inversion is already built and verified to round-trip
  exactly: `f_c → N_eff → B → p` at M84b's measured `m = 2.7198 ± 0.0051`.
  M88's phrase for its own state is **"machine built, no fuel."** This is the fuel.
- **The optical advisor's dominant ±38% uncertainty**, retired in one step.
- **The 87 vs 106–135 cy/mm question**, which currently has two live answers and
  decides whether the lens or the sensor limits resolution at working
  magnification — and therefore whether full-resolution output is worth its cost.
- **§18.3's bench measurement becomes a cross-check rather than the only route**,
  which is worth more than either measurement alone.

## 20. A grey reference in the frame -- REQUESTED, adds ~20 seconds to any session

**Status:** requested 2026-08 by the orchestrator on M85's behalf. M85 built the
colour pipeline and explicitly declined to file this itself, because
`captures-needed.md` is outside its ownership.

**Why.** M85 shipped camera-to-sRGB conversion using the camera's own
characterisation matrix, cross-checked against a second independent database. The
transform is right. **What cannot be checked is the light.** The rendered
background on `bee-3-cpl` carries an **~8% cyan cast**, and there are three
candidate causes that this corpus cannot separate:

1. the illuminant was not D65,
2. the **circular polariser** has a non-neutral transmission spectrum, or
3. optical brighteners in the subject or backdrop.

**M85 makes no colour-accuracy claim, and cannot, until one of these is ruled
out.** That is the correct position and it is why this is a capture request
rather than a bug.

### What to shoot

Anything neutral and matte, **in the frame, under the same light as the
subject**. A proper grey card is ideal; a **white plastic lens cap, a sheet of
copier paper, or the unprinted back of a business card** all work and all beat
nothing. It does not need to be in focus.

1. Set up a stack exactly as you normally would.
2. Put the neutral object at the edge of the frame, lit by the same light.
3. Shoot **one frame** with it there. Remove it. Shoot the stack as usual.

**The CPL matters here and is worth one extra frame.** If you can, shoot that
one reference frame **twice -- once with the polariser on and once with it off**,
nothing else changed. That single pair separates cause 2 from causes 1 and 3 by
subtraction, and the CPL is in your standard optical path, so its spectrum is a
permanent term in every colour result this project will ever produce.

**What it buys.** A measured white point, which turns the colour pipeline from
"the matrix is correct" into "the output is correct" -- and a characterisation
of your polariser that transfers to every future capture.

## 21. A straight edge inside a real bracket -- REQUESTED, and it decides whether the alignment verdict is about your photographs

**Status:** requested 2026-08 by the orchestrator on M88b's behalf. M88b built
the instrument and correctly declined to file this itself.

**Why this is not section 19.** Section 19 asks for a razor blade on its own, to
measure the optics. This asks for a straight edge **inside an ordinary deep
bracket of a real subject**, to measure whether *alignment* improved the
photograph. They are different captures and neither substitutes for the other.

**The problem, stated plainly.** M88b built a paired A/B instrument that reads a
10-90 edge rise off the merged image, nulled it properly -- determinism, a +/-9%
photometric gain and a planted 3 px shift all read **exactly 0.0000 um** -- and
established a floor of **0.6699 um**, which is sensitive enough to detect 2-4
merge pixels. M86's alignment moves 11.56 px, well inside that.

**Then it could not point the instrument at your bees.** `bee-2-cpl` yields
**zero** usable ROIs. `bee-3-cpl` yields two, and **both fail the null** -- 11.5
and 71.1 um against a 1.0 um bar. The three ROIs that do pass come from `M95`,
`RU1` and `TW5`. **None of them is a bee.**

So when the project reports whether alignment helped, that verdict will be
measured on other subjects and **extrapolated across subject to yours.** That is
exactly the kind of transfer this corpus keeps catching and refusing.

### What to shoot

**One ordinary deep bracket, shot exactly the way you normally shoot an insect**
-- same magnification, same aperture, same step, same depth -- with **one
straight, high-contrast, matte edge placed in the scene.**

The edge must be:

1. **Straight** over at least a few hundred pixels.
2. **Tilted 1.2 to 9 degrees** off vertical or horizontal. Not aligned to the
   pixel grid, and not diagonal. A slight, deliberate cant is the whole trick --
   it is what lets many pixel rows each sample the edge at a slightly different
   sub-pixel offset.
3. **High contrast and matte.** A razor blade, a black anodised edge, a chip of
   matte black card, the edge of an IC package. Avoid anything glossy; a specular
   highlight running along the edge defeats it.
4. **At a depth inside the bracket**, so it comes into focus in some frames.
   Roughly the same distance as the subject.

It does **not** need to be near the subject, or attractive, or in the final
composition. The corner of the frame is fine. The bracket does not have to be a
good photograph.

**What it buys.** The alignment verdict stops extrapolating across subject and
becomes a measurement on your own gear, your own working distance and your own
subject class -- which is the only form in which it answers the question you
actually asked.

**A second instrument now waits on this same capture, which raises its
priority.** M104c built an ISO-12233 slanted-edge MTF estimator and validated it
to **+0.03% and +0.36%** against analytic Gaussians, with a positive control at
+0.33% and a two-crop null at +0.00%. It then found it had nothing to point at:
on `flat-on-ruler-cpl`, **83 of 103** high-contrast vertical candidates sit
within **+/-1 degree** of vertical, median **+0.01 degree**, because the ruler
was placed square to the sensor. Contrast was never the limitation -- the best
edge measured **4555 DN, 60% of the frame's p1-p99 range**. This is the *second*
validated edge instrument in the project with no fuel; M88's cutoff estimator
(section 19) was the first.

So this one bracket feeds three consumers at once: M88b's alignment edge-rise,
M104c's MTF50, and section 19's cutoff work if the edge is also shot on its own.
**The tilt is the entire requirement, and it is free** -- the same blade laid
down at a deliberate slight cant instead of square costs nothing and unblocks
all three. A capture shot square is not a weaker version of this; it yields
**zero** usable ROIs, and the near-zero-degree readings such an instrument
returns (0.005-0.018 c/px) are aliasing artefacts that must never be quoted as
sharpness.

## 22. Expose to the right -- REQUESTED, costs nothing, worth more than any algorithm here

**This is the highest-value change available to this project and it is not a
capture we need, it is a capture setting.** MEASURED across every macro bracket
delivered so far (23 stacks, `experiments/ORCH-drift-check/exposure-survey.py`):

| stack | frames | unused headroom | clipped |
| --- | --- | --- | --- |
| `lead-1-cpl` | 123 | **+4.39 stops** | 0.0000% |
| `leaf-2-cpl` | 182 | +3.91 | 0.0000% |
| `112MSDCF` | 79 | +3.83 | 0.0000% |
| `109MSDCF` / `113MSDCF` | 22 / 63 | +2.86 | 0.0000% |
| `wrapped-text-1` | 130 | +2.71 | 0.0000% |
| `flat-on-ruler-cpl` | 79 | +2.65 | 0.0000% |
| `couch-fibers-cpl` | 299 | +2.35 | 0.0000% |
| `wrapped-text-2` | 120 | +2.31 | 0.0000% |
| `flowers-cpl` | 176 | +2.07 | 0.0000% |
| `flower-bud-with-background-fern-cpl` | 299 | +2.04 | 0.0000% |
| `lavendar-cpl` | 299 | +2.01 | 0.0000% |
| `highly-angled-ruler-mm-cpl` | 299 | +1.82 | 0.0000% |
| `119MSDCF` | 33 | +1.75 | 0.0000% |
| `flower-bud-alone-cpl` | 205 | +1.73 | 0.0000% |
| **`bee-1-cpl` / `bee-2-cpl` / `bee-3-cpl`** | 299 each | **+1.69** | 0.0000% |
| `tweezers-cpl` | 100 | +1.39 | 0.0001% |
| `foam` | 100 | +0.40 | 0.0428% |
| `coffee-bean` | 105 | +0.01 | 0.1283% |
| `coffee-bubbles` | 19 | -0.00 | 0.1225% |
| `dry-erase-marker-head-cpl` | 299 | -0.00 | 3.6726% |

Median **+2.01 stops**. Nineteen of the twenty-three clip **0.0000%** of
pixels -- not "few", none.

### Why this outranks everything else on the roadmap

Two stops is **4.04x the photons**, which is **2.01x less shot noise arriving
at the sensor**, before a single line of strehl runs. For comparison, the
merge's own ceiling on a 30-frame static burst is 5.48x and it is bounded by
frame count (M62); the shipped gate reaches 0.890x flat-ROI noise (fact 320).
**A capture change worth 2.01x is competitive with the entire estimation
machinery this project exists to build**, and unlike the machinery it is free
and available today.

It also compounds: the merge's advantage over selection is largest where the
frames are noisy, so a cleaner capture does not make strehl less useful -- it
raises the floor everything else is measured from.

### What to do

- **Expose to the right.** Raise exposure until the brightest *diffuse* part
  of the subject or the background sits just below clipping. A blown specular
  highlight on a chitin edge is acceptable; a blown diffuse surface is not.
- **The polariser is costing about 1.5-2 stops and the CPL stacks show it** --
  every `*-cpl` bracket except `dry-erase-marker-head-cpl` and `tweezers-cpl`
  is at least 1.7 stops down. If the exposure was not compensated when the CPL
  went on, that is most of the gap.
- **Prefer longer shutter to higher ISO** on a static subject; the noise model
  is read-noise dominated at low signal and this rig is tripod-bound anyway.
- **Do not clip to reach it.** Judge on the RAW histogram, not the JPEG
  preview, which has the camera's tone curve applied and will look brighter
  than the data.

### What it does NOT change

The existing 23 stacks stay valid. Every measured number in this corpus was
taken on them and none is invalidated -- the noise model is calibrated in
electrons and handles a dark capture correctly. This is about the *next*
captures, and about what the shipped product can show.

### Related

- Fact 1253: the render is tonally faithful; `bee-3-cpl`'s dullness is the
  capture, not the merge.
- Fact 1257: this survey.
- M100 is adding `--exposure` / `--auto-exposure` to the **viewing** render so
  existing captures at least *display* correctly. That is a presentation fix
  and it does not recover the photons; only re-shooting does.

## 23. Bracket coverage -- a DIAGNOSTIC you can already run, not a request

Nothing to shoot for this one. It is here because the tool has started
answering a question about your photographs that nobody was reading -- and
because the answer turned out to be about the *subject*, not about your
technique. One of your stacks reads far worse than the others on it, and the
reason is not what it looks like.

### The number

`strehl stack <DIR> --gate 2` already prints a `boundary %` column. It is the
fraction of output pixels whose elected frame sits at the **first or last rung
of the bracket** -- the structural signal for *no frame in this stack is in
focus here*. Measured at `e47cf81`, full resolution, prediction registered
before the run:

| stack | frames | `boundary %` | how it looks |
| --- | --- | --- | --- |
| `flowers-cpl` | 176 | **33.74%** | featureless waxy blob at 100% |
| `bee-3-cpl` | 299 | 1.00% | good |
| `leaf-2-cpl` | 182 | 0.12% | good |

**281x separation between the stack that looks broken and the stack that looks
right**, on a number that was already on screen. The random-election floor is
of order `2/N`, about **1.1%** on a 176-frame stack, so 33.74% is roughly **30x
above** what chance would produce.

### What it is not

It is **not** the merge's fault, and this was checked rather than assumed.
`--gate 0` is pure selection -- verified at mean `n_eff` 1.000 with 100.00% of
pixels taking exactly one frame -- and it contains **no real detail either**, so
no single frame ever held the detail (fact 1358). Saturation is ruled out on the
linear render, where clipping is unambiguous: maximum **0.6002** of full scale,
**0.000%** of the crop within 1% of maximum. The capture is the cause.

### What to do

**Nothing, as it turns out — and this is the part I got wrong first.** My initial
reading of this section told you to re-shoot with a wider sweep. That advice was
wrong and has been withdrawn. See below.

### What it actually is: occlusion, not coverage

The frame-0/frame-last split is lopsided by **165x**: 29.81% of pixels elect
frame **0**, only 0.18% elect frame 175. Neither "under-bracketed" nor "distant
backdrop" predicts that, so I tested a third idea -- that the naive argmax breaks
ties toward the lowest index in flat regions. **That is refuted, and in the
opposite direction:** frame-0 election runs at 6.39% in the lowest-contrast
decile and **49.98%** in the highest, a 7.8x concentration in *high*-contrast
pixels, with a shuffled-map null control reading 1.01x.

Then I looked at the map (`C:\dev\strehl-out\ORCH-flowers\boundary-map.png`),
and the answer was immediate and was in none of the numbers:

> **The boundary pixels are thin curved ribbons tracing the petal edges.**
> They are not a region of the scene. They are *contours*.

That is the occlusion population. At an overlapping petal edge the pixel is a
two-layer composite of a near petal and whatever lies behind it, **no frame
contains a clean measurement of it**, the focus response has no interior
optimum, and the election runs to the end of the range. It lands on frame 0
because that is where the search bottoms out, not because anything is in focus
there.

This independently reproduces, on a different stack and by a different method,
M96's finding that pixels with disconnected competitive sets form *"thin
contours lying exactly along depth and occlusion boundaries"*.

**So `flowers-cpl` is not badly shot. It is geometrically hard.** A flower of
overlapping petals has enormously more occluding edge per unit area than a bee
or a leaf, which is exactly why it reads 33.74% where `leaf-2-cpl` reads 0.12%.
Shooting a wider bracket would not have moved it, because the missing
information is not at either end of the sweep -- it is not in any frame.

### What this changes

- **`boundary %` is closer to an occlusion detector than a coverage statistic.**
  It should not be read as a verdict on your bracketing, and this section no
  longer does.
- **Subject choice is a real variable.** Deeply interleaved, self-occluding
  subjects are the hard case for *every* stacker, this one included. That is
  worth knowing before you blame a render.
- **It hands the occlusion work a large, visible, real-photograph test
  population**, which it did not previously have.
- Genuine bracket-coverage failure would look different: boundary pixels filling
  a contiguous *region* rather than tracing contours, and concentrated in the
  low-contrast decile rather than the high one. Both are now measurable, so the
  distinction can be made rather than guessed.

### The methodological note, because it cost me two wrong answers

The decile ratio came back at **0.13x** and my pre-registered bar read that as
*"independent of contrast -- hypothesis (1) survives"*. **The bar was one-sided
and I had written it assuming the effect could only run one way**, so it
reported a 7.8x dependence as a null. The number was not merely uninformative,
it was actively misleading, and the picture overruled it in about one second.
Second time in one night that a number lost to an image; see fact 1359, where a
Laplacian sharpness metric rated a visible mosaic artifact 2.73x sharper than
the correct render.

### Related

- Fact 1357: the 281x separation and the prediction registered before it.
- Fact 1358: the `--gate 0` control that exonerates the merge.
- **Fact 1360: the boundary population is occlusion contours** -- the 165x
  frame-0/frame-last asymmetry, the 7.8x concentration in high-contrast pixels
  with a 1.01x null, and the map that settled it.
- **Fact 1361: this section's original advice, withdrawn.**
- Fact 1362: the one-sided bar that reported a 7.8x effect as a null.
- Fact 1359: a Laplacian sharpness metric rated selection **2.73x sharper** than
  the correct render on this same crop, because selection's excess energy is
  visible polygonal patchwork. Do not judge these stacks by a sharpness number.

## 24. Colour-separated exposures of one static subject -- REQUESTED by M95/M85, ten minutes, and it closes a gap nobody noticed

> **UPDATED again, later the same night — the subject changed, the gels stayed.**
> I told you above that the coloured-gel sets were now the experiment, because
> they would test whether the colour-fringing correction has to be **spectral**.
> An agent then went and tested that hypothesis against eight of your existing
> stacks instead of waiting for you to shoot it, and **it does not hold.** The
> prediction was that scenes weighted toward longer wavelengths need a larger red
> correction; measured, the correlation is **backwards** (rho **−0.69**, n=8).
>
> **What survived, and got stronger:** the correction genuinely does differ from
> subject to subject — **27.3%** across your eight stacks, against a repeatability
> floor of 19.5 ppm, so this is a real effect roughly fourteen times larger than
> the noise. We simply do not yet know what drives it. Four candidate
> explanations were killed on your existing data: focus distance, magnification,
> subject structure, and the alignment step.
>
> **Aperture and the teleconverter were killed by your own EXIF**, and this is
> worth knowing: **every one of your `-cpl` stacks is f/5.6 on the 100mm GM with
> the 2× teleconverter.** There is no aperture variation among the `-cpl` stacks.
> (Corrected overnight: I previously wrote "no aperture variation anywhere in the
> corpus", which is **wrong** — `coffee-bean`, `coffee-bubbles` and `foam` are
> f/8, and `109/112/113MSDCF` are f/11. All of those are non-CPL, which is why
> the point below still holds, but the wider claim was mine and it was false.)
> So an aperture ladder would be varying something you have in fact been holding
> fixed, and the "second set with the teleconverter" I asked for above is
> confused — the teleconverter *is* your normal configuration.
>
> **So: still shoot the gels, but on a different subject, and the change matters.**
> The design below is now a controlled experiment rather than a fishing trip.

**Every demosaic number this project has produced is measured against a decode,
not against a scene.** That is the gap. When M95 compared demosaic algorithms it
had to treat one algorithm's output as the truth the others were scored against,
because no capture in the library contains a known per-channel ground truth. The
comparison still worked -- CDIFF2 was rejected on its artifact clause, and it is
worse than Malvar-He-Cutler on every channel in pixel error (fact 1422) -- but
the reference was itself a reconstruction.

This also now blocks something larger. M107 measured two chromatic aberration
terms on the shipping render (facts 1413, 1414): a lateral term of **-704.5 ppm**
in red, worth **2.977 output px at the corner**, and an axial term that the merge
**bakes in permanently** because it elects on green and then gathers red and blue
at green's frame. Both fixes are per-channel, and both are currently validated
against demosaiced data rather than against separated channels.

### What to shoot

**A flat, achromatic, high-detail target, square-on to the lens, that never
moves.** All three of those adjectives are doing work and none is fussiness:

- **Flat**, and normal to the axis, so the whole target is in focus at once. On a
  flat subject the stacking merge was measured to be a **4.8 ppm no-op** — it
  changes nothing — so anything the experiment sees is optics, not the stacker.
  A tilted or three-dimensional subject reintroduces the confound the whole
  design exists to remove.
- **Achromatic** — grey, black and white only, **no colour in the target**. This
  is the change from what I asked for before. If the target is coloured *and* the
  light is coloured, the two spectral effects are mixed and neither can be
  measured. A printed resolution chart, a page of small black text, or a grey
  card with fine print all work.
- **Corner-to-corner detail**, because the effect being measured grows with
  distance from the centre and a subject that fills only the middle cannot show
  it.

Then, **without moving anything between exposures**:

1. One normal exposure.
2. One through a **red** filter.
3. One through a **green** filter.
4. One through a **blue** filter.

**If, and only if, that first set shows the correction moving between gels**, a
second set becomes worth shooting: the same four exposures on a **coloured**
target under **fixed white** light. The first set varies the *illumination*
spectrum; the second varies the *subject* spectrum. They are different claims and
the corpus cannot presently tell them apart, which is why they need separate
sets. If the correction does **not** move across gels on the achromatic target,
the spectral explanation is dead outright and the second set is unnecessary —
which is the outcome I would bet on given the −0.69 above, and it is worth ten
minutes to find out.

Then, **without moving anything between exposures**:

1. One normal exposure.
2. One through a **red** filter.
3. One through a **green** filter.
4. One through a **blue** filter.

Gel filters over the lens are fine -- they do not need to be good filters, or
even particularly clean. They need only be strongly band-limiting, and identical
in placement. If you do not have gels, three exposures lit in turn by a red, a
green and a blue light source are equivalent for this purpose and may be easier.

**Compensate exposure per channel so none of the four clips and none is buried in
read noise.** The filters will cost between one and three stops each and they
will not cost the same amount. Shoot at your normal working aperture, and use the
same aperture for all four.

**Do not focus-bracket this.** A single frame per channel is the whole request.

**AMENDED — the frame must have fine detail all the way into the corners, and it
must be shot at your working magnification.** This is an addition from M95/M85,
and it is a geometric requirement the rest of this section does not imply.
Lateral CA is a *radial* magnification error: it is **zero at the optical centre
by construction** and grows toward the edge, which is why fact 1414 quotes it as
"2.977 output px **at the corner**". A subject that fills only the middle of the
frame -- which is what "one static, high-detail subject" naturally produces, and
what a coin or a banknote shot at macro distance guarantees -- contains almost no
signal for the term being measured, however sharp it is.

Concretely, `bee-3-cpl` **cannot** supply this measurement: its lateral CA works
out to **0.0345%**, which exceeds the 200 DN discrimination threshold the
estimator needs. That is not a flaw in the photograph; it is the wrong geometry
for this one question.

So: something **flat and repeating that fills the whole frame corner to corner**
-- graph paper, a printed grid or checkerboard, a screen showing a fine test
pattern, the weave of a fabric, a page of small text. Flat matters, because a
subject with depth puts the corners out of focus and a blurred corner cannot
show a sub-pixel channel offset. Square-on to the sensor, corners in focus,
**at the magnification you actually shoot at** -- the correction is being fitted
for your working configuration, not for an optical bench.

**If you use the 2x teleconverter, shoot a second set with it fitted.** A
teleconverter changes the optical configuration completely, so a profile
measured without it should not be assumed to apply with it, and right now
nothing in the pipeline would notice if it were applied wrongly.

### AMENDED AGAIN -- the shipped coefficient is now measured, and this capture is what would extend it

M107 was asked for the **radial support** of its -704.5 ppm coefficient rather
than its goodness of fit, and answered with the population per annulus (fact
1462). The result sharpens this request from "more corner detail would be nice"
into two specific, checkable requirements:

1. **Both outer annuli are empty, not just the last one.** The fit spans
   `r = 0.208` to `r = 0.788` with **6 of 10 annuli populated**; `0.80-0.90`
   **and** `0.90-1.00` have no data at all. A target that resolves only in the
   extreme corner would still leave the `0.80-0.90` band empty. What is needed is
   detail that is **continuous from centre to corner**, which is why "flat and
   repeating, filling the frame" above is the right instruction and a subject
   with a detailed centre and detailed corners is not.
2. **Shoot it so blue is measurable, because blue is currently not measured at
   all.** Every ROI in the existing fit was **red**. `eps_b` is `None`, so the
   blue-green displacement is uncorrected *by construction* -- not estimated as
   zero, never estimated. Real fringes have both a warm and a cool edge, so at
   present at most half of a visible fringe can be addressed. A neutral or
   full-colour target under full-spectrum light supplies blue at no extra cost;
   a target that is red-on-white does not.

For scale, this is not a request to salvage a bad fit. The corner displacement
decomposes as **2.98 sensels at `r = 1.0`, of which 2.35 is at or below a
measured radius and 0.63 comes from the model's shape.** Roughly a fifth of the
corner correction is extrapolation. This capture converts that fifth into
measurement and adds a channel that has never been fitted.

### Why this cannot come from existing files

A demosaiced RAW cannot serve as ground truth for demosaicing: the quantity being
measured has already been applied to it. Nothing in the library was shot through
a filter, and no amount of processing recovers a per-channel measurement from a
CFA mosaic -- that recovery *is* the algorithm under test.

The support limit has the same character. `tweezers-cpl` and `bee-3-cpl` are the
two subjects the fit could use, and **neither has content past `r = 0.79`** --
the macro subject sits in a band with defocused background beyond it. This is a
property of the frames, not of the method, and no reprocessing creates signal
where the photograph has none.

### What it unblocks

- Demosaic comparison against a **scene** rather than against another algorithm.
- Independent validation of M107's lateral CA coefficient, which currently rests
  on a radial fit through demosaiced edges.
- A direct measurement of the axial term `k_R - k_G` and `k_B - k_G` without the
  green-election confound that produced it.
- The per-channel noise model that fact 1417 names as the prerequisite for
  per-channel election.

### Related

- Fact 1422: the demosaic upgrade rejected on its artifact clause, and the
  signal-only bar that would have shipped a regression.
- Facts 1413, 1414: the two chroma mechanisms, and why they ship in the reverse
  of their discovery order.
- Fact 1415: demosaic co-siting and the resampler are bounded small and are *not*
  the fringing you can see.

## 25. A deliberately clipped, strongly saturated subject -- REQUESTED by M109, five minutes, and it decides a choice I refused to guess

### Why you are being asked

M109 fixed the magenta blown highlights in the shipped renderer (fact 1455:
`strehl stack` was putting **2.0017 %** of the frame into magenta, with green
pinned **0.10** below red and blue where a blown highlight has to be neutral).

It built two versions of the fix. The conservative one shipped. The aggressive
one clears substantially more magenta -- **0.0944 % down to 0.0260 %** -- but
touches **6.56 %** of the frame instead of a fraction of a percent.

It refused to ship the aggressive one, and its reason is the reason for this
request: on `marker` the aggressive variant changed **zero** strongly-coloured
pixels, and on `lavendar-cpl` it changed **zero pixels at all**. That looks like
a clean bill of health and it is not one. **Your existing captures contain almost
no saturated colour that is also clipped**, so they cannot express the risk, and
a test set that cannot express a risk will always report it as absent.

The aggressive variant's danger is specific: it would desaturate genuinely
saturated highlights -- a red so bright it clips is indistinguishable, to the
trigger, from a blown neutral. Nothing you have shot can tell those apart.

### What to shoot

Something **strongly coloured** and **deliberately overexposed**, so that the
coloured region itself clips rather than merely being bright.

- A saturated red, orange or magenta subject fills a good part of the frame.
  Flowers work; so does anything printed in a strong process colour. The
  Breakthrough X4 CPL on a glossy subject is a good way to get a genuinely
  saturated specular.
- Shoot a short exposure bracket of the **same static subject**: correct
  exposure, then roughly +1, +2 and +3 stops. The over-exposed frames are the
  point -- you are being asked for clipping on purpose, which is the opposite of
  section 22's advice, and only for this test.
- **Single frames are fine. This is not a focus bracket.** Nothing needs to be
  in focus except the coloured area, and no rail is involved.
- Repeat once for a **blown neutral** -- a white or grey subject taken well past
  clipping, ideally in the same session and light.

The pair is what matters: a clipped saturated colour and a clipped neutral, shot
under the same conditions. The whole question is whether the fix can tell them
apart.

### What it unblocks

- A decision between M109's conservative and aggressive highlight triggers, made
  on evidence rather than on which number looks better.
- A falsification set for **any** future highlight-reconstruction work, which is
  currently unbuildable from this corpus.
- The colour-management plan more generally, which will meet the same question
  the first time it touches gamut.

### Related

- Fact 1455: the defect, the mechanism, and why the clamp was in the wrong place.
- Fact 1456: auto-exposure amplifies the defect **2.8x** rather than causing it,
  so exposure has to be pinned before any severity number means anything.
- Discipline 739: ship the conservative option when the test set cannot falsify
  the aggressive one, and register the capture that would decide it -- this
  section is that register.
- Section 22 asks you to expose to the right and *avoid* clipping. This section
  deliberately contradicts it, for these frames only.

## 26. A bright subject on a deeply defocused dark ground -- REQUESTED by M121, one afternoon, and it decides the halo

This is the capture I would shoot first if I were you. It is the only outstanding
request that could turn *"we know what size the halo is"* into *"we know what
makes it, so we can remove it."*

### Why you are being asked

The rim around every edge in your stacks has been measured to be exactly as wide
as the software's frame-choosing window (facts 1703, 1704). That proves a window
is involved. It does **not** say *which* window effect it is, and two candidate
explanations survive that predict the **same** rim on the subjects you have
already shot. They differ on one case, and your corpus does not contain it.

Every bright-object edge in the corpus is a **pale hair lying on a dark body** --
same depth, no occlusion. Only **5 of 18** such edges straddle a depth
discontinuity, so the class reads as a flat null under every theory on the table.
It is not evidence; it is a sample that cannot answer the question. One attempt
to fill the gap using `tweezers-cpl` produced a beautiful-looking result that was
then correctly thrown out: the profile never ended, and a single unmerged frame
reproduced its shape, so it was a background gradient rather than a rim.

### What to shoot

- **A bright subject against a dark background that is *far* behind it** -- the
  background must be deeply out of focus, not merely darker. Think a pale insect,
  a light-coloured flower, or bright metal, with nothing within several
  centimetres behind it.
- **Do not clip the highlights.** Expose **1--2 stops down** from your normal
  placement. This is the one requirement that would waste the session if missed:
  a clipped bright side destroys exactly the measurement being made.
- **100--300 frames**, your usual bracket, usual aperture. Nothing exotic.
- Your usual rig. The CPL is fine either way; note in the folder name whether it
  was on.

### Why this cannot come from existing files

Checked directly rather than assumed: across all 24 corpus macro stacks the
bright-object-on-dark-ground class has only five members that straddle a depth
edge, and the one stack that looked like it could supply them (`tweezers-cpl`)
was measured and rejected as a gradient at a separation of 2.8x against 28x on
`bee-3-cpl`.

### What it unblocks

- The halo mechanism, which is the **largest visible defect** in your renders and
  the one thing I have never been able to offer you a route to fixing.
- Whether a fix can be built at all, or whether the rim is a price of choosing
  per-pixel that only a different kind of merge could avoid.

### Related

- Facts 1703--1706; disciplines 867, 868.
- Section 23's occlusion finding is the same geometry seen from the other side.

---

## 27. What moved while you slept -- the short version

Five things landed overnight. Two of them are **negative results, and those are the
two that save you the most time.** Read this section and you have the night.

**1. Nobody is going to build the deconvolution merge, and that is settled.** The
outside review's single biggest proposal was to rebuild the merge around
multi-frame Wiener deconvolution -- the argument being that at your magnification
the optics destroy fine detail before the software ever runs, so only
reconstruction can bring it back. It was a good argument. It is also **wrong on
your own photographs**: measured against the averaging the code already does, the
extra sharpness available is a ratio of **1.0014** -- which is to say **none**,
with an error bar of 0.0184 that is far too tight for the effect to be hiding.
The instrument was checked first by planting known effects and recovering them at
0.9938-0.9974, so this is a real null and not a dead gauge. **That is weeks of
work correctly not started.**

**2. The `odd-frame-out` idea is dead, and the reason is specific to focus
stacking.** This is the fix for your moved antenna. Two different mechanisms,
built by different people from different starting points, were both tested
against a stack that **did** move and a tripod stack that **did not**. Both fired
hardest on the stack with nothing wrong with it -- **21.5x** the wrong way for one,
**4.3x** for the other. The reason generalises and is worth knowing: in a focus
stack the frame that disagrees most with its neighbours is usually the frame that
is **right**, because it is the one in focus. Techniques borrowed from ordinary
burst photography keep failing here for exactly that reason. **The moved-frame
defect is still real and still unfixed** -- what is now well established is which
whole family of cures does not apply to it.

**3. I audited the audit, and the corpus is clean.** I had warned everyone that
one of the switches is silently inert when alignment is off -- meaning anyone who
measured its effect that way measured nothing at all. A full sweep of **163
reports found zero** affected measurements, and the reviewer reproduced the
inertness from the source code independently rather than taking my word for it.
**No published number here is corrupted by it.**

**4. The reviewer found a flaw in its own method and led with it.** Its check for
one hazard read a field that structurally could not record that hazard -- so the
clearance it produced could never have failed, whatever the truth was. It caught
this itself, graded it a defect in its own report, and re-cleared the same
question against evidence that does carry the quantity. **I would rather show you
this than a clean sweep**, because it is the difference between a project that
checks itself and one that only says it does.

**5. Every rule of thumb I issued this week has now been refuted.** Three times, by
three separate milestones, each of which tested the rule instead of obeying it.
The sharpest one lands on this project's own core operation: I had a rule that
would have declared "which frame is sharpest" immune to a certain data hazard,
and it is **not** immune. There is now no rule of thumb -- the standing
instruction is to measure the exposure directly every time. **The right lesson is
not that I was wrong three times; it is that being wrong three times was *caught*
three times, by people who were told the rule and checked it anyway.**

**Nothing here changes the render you already have.** The sharpness question from
the previous section is still open and still narrowed to one suspect. What
changed is that two large and expensive directions are now closed, one worry
about the corpus is closed, and the remaining work is better aimed.
