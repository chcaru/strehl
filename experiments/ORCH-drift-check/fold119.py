"""Fold M107b's lateral-CA report, which had 0 citations in SYNTHESIS.

Facts 1534-1540, disciplines 793-796.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1533 |")
disc_line = full_line(raw, "792. ")

NEW_FACTS = [
    (
        1534,
        "MEASURED",
        "M107b",
        "**The fitted lateral coefficient removes 97.1 % of the red-green displacement IN "
        "SAMPLE** (1.4274 -> 0.0412 plane px) while removing **-1.5 %** from the `G1-G2` "
        "null. Out of sample it transfers at **0.950** of in-sample when fitted on 12 ROIs "
        "and **0.541** when fitted on 8 -- neither direction makes the aberration worse, "
        "so the registered falsifier did not fire, but **the 0.541 arm is a registered bar "
        "reported as FAILED rather than narrowed to fit**. Transfer control: the same "
        "transfer applied to `null_dG` removes 5.3 % one way and is **118 % worse** the "
        "other, so the arm is not trivially improving everything it touches. **Honest "
        "status: lateral CA transfers, but 8 ROIs are not enough to fit a transferable "
        "profile.**",
    ),
    (
        1535,
        "ARGUED",
        "ORCH",
        "**Fact 1534 and ORCH's 1.444 over-correction are measured in DIFFERENT DOMAINS, "
        "and together they localise the defect to the application path.** 97.1 % in-sample "
        "removal is a **fit-domain** statement -- the fitted model applied to measured ROI "
        "displacements -- and is consistent with `r_squared = 0.9969`. ORCH's 1.444 is a "
        "**render-domain** statement, measured on output pixels by phase correlation. "
        "**These are compatible**, and their difference is exactly the code between the "
        "coefficient and the pixel. M107b's own render-domain measurements (P35: 9.76 % "
        "edge-chroma reduction) score **chroma**, not displacement -- so **nobody had "
        "measured render-domain displacement before ORCH did**, and that is precisely the "
        "gap where a scale error survives. This raises H3 (application-path scaling) above "
        "H1 (wrong coefficient) and H2 (applicability) in fact 1530, without settling it.",
    ),
    (
        1536,
        "MEASURED",
        "M107b",
        "**THE SHIPPED CORRECTION'S SIGN WAS INVERTED, AND IT SURVIVED 9/9 GREEN UNIT TESTS "
        "PLUS INDEPENDENT MUTATION TESTING.** The unit committed at `d551488` applied its "
        "correction in the wrong direction, making the aberration **7.2 % WORSE** on a real "
        "render. **The coefficients were right; only the application direction was wrong.** "
        "It was caught in a **render-domain preview**, not by the suite. Repaired, and the "
        "repair is backstopped by two tests phrased in physical terms "
        "(`a_planted_magnification_is_actually_undone`) that are **shown to fail on the "
        "defect**. This is a direct precedent for fact 1535: this exact correction has "
        "already shipped one application-path defect that fit-domain evidence could not see.",
    ),
    (
        1537,
        "MEASURED",
        "M107b",
        "**A red/cyan fringe pair is RED misregistration, so `eps_b = None` does not halve "
        "the fix for it.** Cyan is the *absence* of red: a radial scale error in red puts a "
        "red edge on one side of a boundary and a cyan edge on the other, so **correcting "
        "red alone removes both sides**. The unmeasured blue coefficient bites on "
        "**blue/yellow** fringing instead, which is a distinct defect. **This REFUTES "
        "ORCH's repeated claim that 'real fringes have a warm edge and a cool edge, so at "
        "most half of each fringe can be corrected'**, which ORCH had written into "
        "`docs/captures-needed.md` -- the user-facing morning brief -- and which is now "
        "corrected in both places it appeared there.",
    ),
    (
        1538,
        "MEASURED",
        "M107b",
        "**Lateral-CA correction is exactly FREE.** A radial magnification about a point is "
        "itself a `Similarity`, and `Similarity` is closed under composition, so the "
        "correction folds into the transform the gather already applies -- verified to "
        "**<= 1e-12 relative over 20 000 randomised transforms and points**. There is **no "
        "second interpolation**, so the trade ORCH asked to be watched for -- a second "
        "resample costing more sharpness than the fringing it removes -- **does not "
        "arise**. Note this also means fact 1519's placebo problem is structural: there is "
        "no separable 'resampling step' to control for, because the correction never adds "
        "one.",
    ),
    (
        1539,
        "MEASURED",
        "M107b",
        "**On `bee-3-cpl` the correction reduces edge chroma 9.76 % while moving flat "
        "chroma -0.04 %**, and is structurally incapable of global chroma suppression. "
        "Per-channel mean displacement is **R 540 DN vs G 50 / B 54**, confirming only red "
        "moved. **Visibly better at 1:1** -- cyan outlines on the spicules largely "
        "disappear. The default path is **byte-identical across the wiring**: the wired "
        "binary with the switch off reproduces a pre-wiring binary's render at a different "
        "commit to a full SHA-256 match (cross-binary, not A/A).",
    ),
    (
        1540,
        "MEASURED",
        "M107b",
        "**The 'optical centre' of a 3-parameter lateral-CA fit is mathematically "
        "degenerate with a uniform channel translation**, and on this instrument the fitted "
        "value reads either as a physically implausible **51 %-of-half-diagonal** "
        "decentring *or* as a **(+0.629, -0.424) px** translation of the same order as the "
        "**~0.5 px/axis CFA co-siting offset**. Dropping the term costs **5.37x** in "
        "residual so it must be kept -- but **calling it optical is an attribution the "
        "measurement does not support**, and it is recorded as unattributed in the shipped "
        "profile.",
    ),
]

NEW_DISCS = [
    (
        793,
        "**A test that cannot express a direction cannot fail on one.** M107b's L1 (zero "
        "correction is bitwise identity), L5 (green untouched) and L6 (exact composition) "
        "are all **sign-symmetric** -- every one holds identically for `+eps` and `-eps`. "
        "Three more tests **hardcoded the implementation's own expression** "
        "`1.0 / (1.0 + p.eps_r)`, and a test that restates the code cannot disagree with "
        "it. A seventh asserted against `displacement_at()`, **built from the same "
        "convention as the code under test**, so it agreed because it was derived from it. "
        "**Nine green tests, and not one had the power to catch a global sign inversion.**",
    ),
    (
        794,
        "**A mutation that stays inside the defect's own convention cannot reveal the "
        "defect.** The independent verifier's mutation testing changed `1/(1+eps)` to "
        "`1-eps` -- **both are the same wrong direction**, so the mutant died against tests "
        "that were themselves wrong, and the matrix reported health. Mutation testing "
        "measures whether tests detect *perturbations of the written code*; it says nothing "
        "about a convention error shared by the code and its tests. **Mutation coverage is "
        "not a substitute for one measurement in the output domain.**",
    ),
    (
        795,
        "**Verify a correction where its pixels land, not only where its coefficients are "
        "fitted.** M107b's sign inversion was caught in a **render-domain preview** after "
        "the unit suite was 9/9 green (fact 1536); ORCH's 1.444 scale discrepancy is "
        "visible only in the render domain and invisible to a fit reporting "
        "`r_squared = 0.9969` (fact 1535). **The same correction has now produced two "
        "distinct application-path defects that fit-domain evidence could not see.** Any "
        "geometric correction needs at least one end-to-end measurement of the quantity it "
        "claims to remove, taken on output pixels.",
    ),
    (
        796,
        "**Check a report's citation count before assuming its findings are in the "
        "corpus.** `M107b-lateral-correction.md` is 82 KB, contains a shipped sign "
        "inversion, a registered bar reported as failed, and a refutation of a claim ORCH "
        "had put in the user-facing brief -- and had **zero** citations in `SYNTHESIS.md` "
        "for hours while ORCH re-derived part of it independently. **A written report is "
        "not a folded finding.** Sweep `docs/research/*.md` against the corpus "
        "periodically; the cost of the check is one command.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

for block in (fact_block, disc_block):
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert out != raw, "fact insertion did not land"
prev = out
out = out.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert out != prev, "discipline insertion did not land"

for fid, _, _, _ in NEW_FACTS:
    assert out.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert out.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
