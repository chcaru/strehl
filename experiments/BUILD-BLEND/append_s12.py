"""Append section 12 (ORCH's noise finding, reconciled and re-run) to the report."""
import io

DOC = "docs/research/BUILD-BLEND.md"
MARK = "12. ORCH's flat-region noise finding"

NOTE = """
### 12. ORCH's flat-region noise finding, reconciled against the shipping arm

ORCH asked me to stop treating the flat-region noise number as a cost, on the
evidence that the added energy is correlated structure rather than white noise.
Two things needed checking before accepting that: the +12.3% they attribute to
me, and whether their attribution holds on the arm that actually ships.

**The +12.3% is mine and I had already retracted it.** This report's own
preamble records the retraction: the ratio reads **1.0015** on
`couch-fibers-cpl` and 0.989 / 0.991 / 0.998 / 1.002 across four subjects. So
ORCH is defending a number that its author had already withdrawn -- worth saying
plainly, because a retracted figure that keeps circulating is a cost of its own.

**The reconciliation ORCH said they had not done.** Their three candidates were
different tiles, different high-pass radius, different renders. The first can be
eliminated by reading their code rather than guessing: `flatnoise.py:40` selects
tiles **once, on the mean of the two arms**, explicitly so that neither arm's
own residual drives the choice. My prior suspicion of selection bias was wrong
and their design is the correct one.

That leaves the renders, which is separable by running **their instrument,
unmodified, on my renders** (`experiments/BUILD-BLEND/flatnoise_on_mine.py`
imports `flatnoise.py` and redirects one constant):

| couch-fibers-cpl | result |
|---|---|
| ORCH's instrument, ORCH's pinned renders | **+32.1%** |
| ORCH's instrument, this arm's renders | **+3.6%** |
| this report's instrument, this arm's renders | **+0.15%** |

The instruments differ by ~3 points. **The renders differ by ~29.** ORCH's two
pinned binaries are not the two arms that ship, which is the same stale-pin
failure that produced the `merge_cmd.rs` grep in section 10. A pin is a claim
about a commit and needs to carry one.

**The attribution, re-run on the shipping arm** (`detail_on_mine.py`, ORCH's
`noise_vs_detail.py` unmodified):

| subject | sigma B | sigma A | rho_A | rho_add | if noise |
|---|---|---|---|---|---|
| 109MSDCF (placebo) | 71.5 | **44.2** | — | — | *adds no energy at all* |
| coffee-bean | 46.3 | 72.2 | +0.391 | +0.157 | +0.299 |
| couch-fibers-cpl | 202.0 | 212.8 | +0.800 | +0.372 | +0.763 |
| flower-bud-alone-cpl | 46.6 | 70.9 | +0.468 | +0.436 | +0.221 |
| lavendar-cpl | 28.0 | 90.2 | +0.399 | +0.368 | +0.067 |

**ORCH's conclusion holds on the shipping arm.** Every subject that gains energy
reads as structure against the measured white-noise reference of -0.0035, and
the placebo `109MSDCF` -- no depth separation -- adds **no** energy: sigma falls
71.5 -> 44.2, **-38.3%**. A change that manufactured noise could not be quiet on
the placebo and loud only where there is depth.

**A reporting defect in that script, and a correction against myself.** Two rows
above have `rho_add` *below* the "if noise" column, which on first reading looks
like the verdict contradicting its own evidence. It does not. `rho_if_noise =
cb*vb/va` is the counterfactual for **rho_A**, not for `rho_add`, so the two
adjacent columns are not comparable and the verdict test -- `rho_add` against
the white reference -- is the right one. The valid paired comparison is `rho_A`
vs `if noise`, which passes on all four (+0.391 > +0.299, +0.800 > +0.763,
+0.468 > +0.221, +0.399 > +0.067). **I was one step from reporting a bug in
ORCH's code that does not exist.** The defect is presentational, but it is not
harmless: ORCH published exactly this table as their evidence, and on renders
where the two columns cross it reads as a self-contradiction.

**Accepted, with the boundary stated.** The noise number comes off the blocker
list, re-characterised as *"attributed to recovered detail on four subjects; the
placebo adds no energy."* This bounds the character of the aggregate, not of
every component -- a real noise increase can ride underneath a larger detail
increase -- and that caveat is ORCH's, kept deliberately. Nothing in this arm
will be blurred or denoised to move the number.
"""

src = io.open(DOC, encoding="utf-8").read()
if MARK in src:
    raise SystemExit("section already present -- refusing to duplicate")
io.open(DOC, "w", encoding="utf-8", newline="").write(src.rstrip("\n") + "\n" + NOTE)
print("appended section 12;", len(io.open(DOC, encoding="utf-8").read().splitlines()), "lines")
