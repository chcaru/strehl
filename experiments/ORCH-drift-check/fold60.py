"""Fold M104c's P5/P6/P7 and the fix at b843a3f.
Facts 1363-1366, disciplines 678-679.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1363, "**THE NAIVE BASELINE WAS RENDERED AT HALF THE ESTIMATOR'S RESOLUTION FOR 9 MILESTONES, AND THE BIAS "
           "RAN TOWARD THIS PROJECT'S OWN THESIS.** MEASURED by M104c (P6): M95 migrated `stack --srgb` to full "
           "sensor resolution with a Malvar-He-Cutler demosaic but never migrated `argmax-baseline --srgb`, which "
           "kept binning each 2x2 CFA quad to one pixel. On `coffee-bean --limit 12` the estimator emitted "
           "**7032 x 4688** while its own control emitted **3516 x 2344**. Fixed at `b843a3f` by giving "
           "`argmax-baseline` the identical resolution rule -- `demosaic \\|\\| (srgb && !binned)` -- after which both "
           "emit 7032 x 4688 on the same stack.",
     "**These two subcommands exist for exactly one purpose: to be compared against each other.** "
     "`argmax-baseline` is the naive per-pixel selector that the whole estimation thesis is measured against, and "
     "it was being shown at half the linear resolution of the estimator that beats it. Magnification reads as "
     "sharpness (discipline 606), so this was not symmetric noise in the comparison -- **it ran in one direction, "
     "and that direction was toward the conclusion the project wants to be true**. Every side-by-side taken "
     "between M95 and `b843a3f` flattered the estimator by an amount nobody had measured. The defect was not in "
     "the estimator, the metric or the data; it was in the *control*, which is the one component nobody re-reads "
     "after it is written.",
     "M104c (MEASURED, P6); ORCH (fix and verification at `b843a3f`)"),

    (1364, "**`7032 x 4688` IS A `bee-3-cpl` MEASUREMENT, NOT AN INVARIANT OF THE TOOL.** MEASURED by M104c (P5) "
           "on `flat-on-ruler-cpl`, which emits **7040 x 4688**, and independently corroborated by ORCH: "
           "`flowers-cpl` and `leaf-2-cpl` render **7040 x 4688** while `bee-3-cpl` and `coffee-bean` render "
           "**7032 x 4688**. The real guarantee is **exactly twice the binned dimensions in each axis**, which is "
           "stack-invariant; the literal figure is not.",
     "**A number that is stable across the stacks you happen to test is not thereby a constant** -- this is fact "
     "section 4.1's demolition of \"constants\" arriving in a new place. The figure had already been written into "
     "`README.md` as though it were a property of the tool. Any freeze check, test or document that hard-codes "
     "7032 x 4688 will pass on two stacks and fail on the next one for a reason that has nothing to do with the "
     "code under test. The verification of fact 1363 was written against the doubling relation for this reason, "
     "not against the literal size.",
     "M104c (MEASURED, P5); ORCH (independently corroborated on 2 further stacks)"),

    (1365, "**`--demosaic --binned` RESOLVED SILENTLY TO DEMOSAIC.** MEASURED by M104c (P7): the two flags request "
           "opposite things, and passing both caused one to be discarded without any message. Fixed at `b843a3f` "
           "with `conflicts_with` on both subcommands; the pair now exits **2** with *\"the argument '--demosaic' "
           "cannot be used with '--binned'\"*.",
     "Small, but it is the exact shape of defect this project exists to remove: **a decision made silently on the "
     "user's behalf, with no record in the output that it was made.** Anyone who had reached for `--binned` to "
     "force the frozen half-resolution path while also passing `--demosaic` would have received full-resolution "
     "output and had no way to know from the run itself.",
     "M104c (MEASURED, P7); ORCH (fix at `b843a3f`)"),

    (1366, "**THE FIX'S DIMENSION CHECK COULD NOT SEE THE ONE WAY THE FIX COULD BE WRONG.** The new branch "
           "hard-codes an RGGB interleave (R, G1 on the even row; G2, B on the odd), and **a transposed interleave "
           "produces output of exactly the right size**, so the resolution-parity check that motivated the whole "
           "commit is blind to it. MEASURED separately at `b843a3f` (`cfa_interleave_check.py`, bars registered "
           "first) against the merge path's render of the same stack: worst per-channel mean difference "
           "**0.29 %**, R > G > B rank preserved in both, and the two renders confirmed **not** byte-identical so "
           "that both algorithms are known to have run.",
     "**The check that proves a change did what you wanted is rarely the check that would catch it doing "
     "something else.** Sizes matching is necessary and nowhere near sufficient for \"the demosaic is correct\". "
     "Registered limitation, stated rather than hidden: this check compares against the merge path, so **a shared "
     "interleave bug in both paths would pass it**. It is a parity check, not a ground-truth check; the "
     "ground-truth statement lives in `CfaPlane::rggb_at`.",
     "ORCH (MEASURED at `b843a3f`; limitation registered, not resolved)"),
]

DISCIPLINES = [
    (678, "**Audit the control's render path with the same suspicion as the treatment's.** When two code paths "
          "exist in order to be compared against each other, any asymmetry between them is a thumb on the scale, "
          "and the *control* is the side nobody revisits -- it was written once, it is \"the naive thing\", and it "
          "attracts no further attention. `argmax-baseline --srgb` stayed at half resolution for nine milestones "
          "after `stack --srgb` was migrated, biasing every side-by-side toward the estimator. **Where two "
          "subcommands must agree on a rendering decision, express the decision once and make it impossible to "
          "change one without the other**; the fix duplicates the literal rule `demosaic || (srgb && !binned)` in "
          "both arms so that a future divergence requires editing both. Facts 1363, 1364."),
    (679, "**A passing check on the property you changed says nothing about the properties you did not think "
          "about.** The commit's headline check was resolution parity, and the branch it added could have "
          "transposed the CFA interleave while satisfying that check perfectly -- right size, wrong colours. "
          "Before claiming a branch correct, ask what a *different* defect in the same branch would look like to "
          "the check you just ran, and add the check that would see it. **Then state what your new check still "
          "cannot see** -- here, a bug shared by both compared paths. Fact 1366."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1362 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^677\. ", l))
    assert disc_idx > fact_idx, f"fact {fact_idx}, disc {disc_idx}"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes, need 5"
        rows.append(row)

    drows = [f"{did}. {body}" for did, body in DISCIPLINES]

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1363-1366 after line {fact_idx}, disciplines 678-679 after line {disc_idx}")


if __name__ == "__main__":
    main()
