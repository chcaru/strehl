"""Append section 56 to ORCH-veiling.md, idempotently and anchor-checked.

Refuses to run unless the file currently ends at section 55 and does not
already contain a section 56 heading.
"""
import sys
from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "research" / "ORCH-veiling.md"

ANCHOR = "## 55. A night of corrections, and one of them is a habit rather than a fact"
NEW_HEADING = "## 56. A flat subject is a within-image control, and it says the dark side is blurred"

SECTION = r"""

## 56. A flat subject is a within-image control, and it says the dark side is blurred

Three things landed in the same hour and they belong together, because the first
is a measurement I could not have got any other way, the second is the third
instance tonight of the same structural failure, and the third is a hole in a
rule I wrote myself and have been enforcing on everyone else.

### 56.1 The ruler

I have been treating "the output is soft" as one fact about the tool. It is not
one fact. Looking at 1:1 print-QA crops across the delivered `SHIP-V1` masters,
the pattern is specific and it is not global:

**Bright textured regions are excellent. Dark and low-contrast regions are
blurred. In the same image, at the same depth, tens of pixels apart.**

The subject that shows it is `flat-on-ruler-cpl`, and it shows it because the
subject is **flat**. A flat subject is the degenerate case for a focus stacker:
a ruler lying in the focal plane has no depth to resolve, every pixel wants the
same one or two in-focus frames, and the merge has no hard decision to make
anywhere. Whatever softness appears there is the pipeline, not the focus
decision. In one 700 px crop:

| site, same crop | gradient | appearance at 1:1 |
| --- | --- | --- |
| brushed-metal grain | **0.05282** | razor sharp; individual brush striations, discrete specular sparkles |
| black engraved mark, ~50 px away | -- | **blurred**; edge fades over ~10-15 px, boundary mottled |

For scale, 0.05282 is *higher* than `bee-3-cpl`'s best site at 0.03072, and
`bee-3-cpl` is the subject I judged print-worthy. So the metal here is as good
as anything the tool has produced, and the mark 50 px away is not.

Corroborating in the same direction, from the same pass: `pencil-steep-angle-cpl`
renders beautifully -- individual wood fibres, crystalline structure in the wood,
a clean graphite/wood boundary, gradient 0.02860. Against that, `flowers-cpl` is
mush at its own sharpest site (0.00939, 3.3x less than `bee-3-cpl`) and
`lavendar-cpl`'s hairs read as low-microcontrast white spaghetti.

**Why this observation is worth more than the several dozen numbers above it.**
It is a *within-image* control. The sharp metal and the blurred mark share the
same subject, the same plane, the same frame set, the same merge invocation, the
same tone treatment, the same alignment solve, the same binary, and they are 50
px apart. Nearly every confound that has produced a retraction in this document
-- two binaries, two black points, one arm toned and one linear, a scene
difference standing in for a treatment difference -- is excluded **by
construction** rather than by care. I have spent this night discovering that my
instruments were measuring across boundaries they should not have crossed. A
within-image control cannot cross one.

> **When a defect can be sited twice inside a single frame, once where it appears
> and once where it does not, prefer that comparison to any comparison between
> two renders. The confounds are excluded by construction rather than by
> discipline, and discipline is what has failed here repeatedly.**

**The mechanism I suspect, tagged ARGUED and handed to the gate lane to kill.**
Where the focus measure has poor signal-to-noise, the noise gate widens and
admits more frames into the average. On a *flat* subject shot as a focus
bracket, most frames are out of focus -- only one or two are sharp. So a gate
that opens wide in a low-SNR region is not averaging redundant in-focus frames
and winning noise; it is averaging **defocused** frames and losing sharpness.
Dark regions have low `S`, hence low SNR under `sigma^2(S) = gS + (RN*g)^2`,
hence a wide gate, hence blur. If that is right, the gate is not trading noise
against noise in these regions; it is trading away resolution exactly where the
picture is darkest.

I am explicit that this is ARGUED and that I can name a competing explanation I
cannot exclude by eye: the mark may be ragged in reality, since paint settling
into brush grooves would genuinely have a soft mottled boundary. So the test I
registered is not "gate 2.0 versus gate 4.5, pick the nicer one". It is against
the invariant the project already claims:

> the merge must never be worse than the best single frame.

Find the source frame sharpest **at the mark's location**, bring it into the
merged geometry through the merge's own alignment, and compare edge profiles in
camera-linear space from one binary -- with the sharp metal site as the built-in
control. If the instrument reports the merge losing sharpness at the *metal*
too, it is measuring misregistration or resampling loss and the mark result
means nothing. If the merge matches the single frame at the metal and is
materially softer at the mark, that is a hard invariant violation localised to
low-SNR regions, and it is the best candidate yet for the owner's complaint.

### 56.2 The third instance, and the first black-box detector for it

`--photometric` is **inert on the shipped path**. Measured by hash, one binary,
one subject, everything else fixed:

| arm | SHA-256 |
| --- | --- |
| unset / `--photometric=on` / `--photometric=off` | all `CF48D6E2...1C2482` |
| `--merge estimator`, unset | `2AA68069...A857EA` |
| `--merge estimator --photometric off` | `180CBA77...A94956` |

The positive control fires, so the identity is the product's, not the harness's.
The photometric fit lives only in `run_estimator`; the default backend is
`Pyramid`; the flag reaches nobody.

That is the **third** instance tonight of work not reaching the product, by a
third distinct route, and the table from section 54.2 now needs a fourth row:

| section | how it fails to reach the product | signature |
| --- | --- | --- |
| 49, 51 | instrument and product on opposite sides of a transformation | measurements do not predict the render |
| 52 | the stage exists but the backend skips it | the tool prints `not applied: ...` |
| 54 | compiles, complete, self-testing, **never called** | nothing at all -- invisible |
| **56** | **the flag is accepted, and silently changes nothing** | **only a hash comparison shows it** |

The last of those is the one worth generalising, because it needs no reading of
the call graph, cannot be fooled by a module that merely compiles, and yields an
artefact that survives argument:

> **A flag is a promise. To find out whether the tool keeps it, set the flag to
> each of its values with everything else fixed and hash the outputs. Byte
> identity across every setting means the promise is not kept -- provided a
> positive control in the same run proves the harness can see a change at all.**

I have commissioned a full census of every flag `stack` accepts on this basis,
with the outcomes required to partition exhaustively -- *changes output*,
*inert*, *refused with the refusal quoted*, *not examined with the reason* --
summing to the number of flags the CLI actually defines. Refusal is honest
behaviour and is not a defect; the quarry is the flag that is accepted and does
nothing.

### 56.3 Two rules, one of which corrects me

**A ratio hides an additive defect in proportion to its baseline.** The
photometric gate `K2` scores a high-frequency energy *ratio*. Its corpus-worst
stack is `foam` at **-50.41 DN**, which `K2` scores at 1.0129 because the
baseline there is 3667.6 DN -- so the gate **mis-orders its own two worst
stacks**. Corpus totals: +33.03 DN removed, -92.48 DN added, net **-59.45 DN**.
The build agent caught this in its own draft, which is the hard direction to
catch it in.

> **Any gate that admits inputs with different baselines must report absolute
> units alongside the ratio. A ratio is a comparison to a denominator you did
> not choose.**

**And the correction to me.** I have been telling every agent to commit
path-scoped -- `git add -- <paths>` then `git commit -- <paths>` -- as the
defence against concurrent agents in one working tree. It is a real defence and
it is not the one I thought it was. `git commit -- <path>` commits the
**current worktree content** of that path, bypassing the index. So it protects
*other files* from your commit, and gives **zero** protection to *your file*
from another agent's commit: two agents editing one file will commit each
other's half-finished work in whichever order fires first. That is exactly what
happened when `6430fb2` swept an uncommitted `merge_cmd.rs` change belonging to
a different agent.

> **Path-scoped commits protect other files from you. They do not protect your
> file from anyone. The only defence against two agents in one file is that
> there are never two agents in one file.**

`merge_cmd.rs` presently violates that, with several agents in it. It is my
allocation error, not theirs, and it is the reason at least one measured result
tonight had to be re-derived.

### 56.4 What this changes about the finish

It narrows it. The five stages the pyramid backend announces it skips looked
like five pieces of work. On the evidence they are mostly not:

| stage | status |
| --- | --- |
| photometric gain | **measured harmful** -- net -59.45 DN, gate fired, three routes agree. Do not port. |
| halo correction | ring **measured gone** on this backend, and confirmed by eye. Not needed. |
| clip census | hull clamp **verified live** on the delivered masters. Not needed. |
| outlier rejection | need **being measured** -- does anything in this corpus actually move? |
| through-focus statistics | wanted for confidence as a *product feature*, not to fix a defect. |

So the remaining quality work is not a five-stage port. It is: whether the gate
blurs the dark side, and whether the unwired restoration recovers the 1.43x the
gather throws away. Two questions, both in flight, both with registered tests.
"""


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    if NEW_HEADING in text:
        print("append56: section 56 already present; nothing to do (idempotent).")
        return 0
    if ANCHOR not in text:
        print(f"append56: ANCHOR NOT FOUND: {ANCHOR!r}", file=sys.stderr)
        return 2
    if text.count(ANCHOR) != 1:
        print(f"append56: anchor is not unique ({text.count(ANCHOR)}x)", file=sys.stderr)
        return 2
    before = len(text)
    text = text.rstrip("\n") + "\n" + SECTION.rstrip("\n") + "\n"
    DOC.write_text(text, encoding="utf-8", newline="\n")
    after = len(DOC.read_text(encoding="utf-8"))
    print(f"append56: {before} -> {after} bytes (+{after - before})")
    if NEW_HEADING not in DOC.read_text(encoding="utf-8"):
        print("append56: POST-CHECK FAILED, heading absent after write", file=sys.stderr)
        return 3
    print("append56: post-check OK, heading present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
