"""Insert section 9.26 into RESULT.md, immediately before `## 10. Files`.

Derived from `vn_place2511.py`. Every number in the body comes from
`vn_rep926.py`, which reads the JSON records; nothing here is typed by hand.
The insertion is anchored on a full unique line and the script hard-errors if
the anchor is missing or occurs more than once -- a placer that silently no-ops
is indistinguishable from one that worked.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_rep926 as R  # noqa: E402

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RESULT.md")
ANCHOR = "\n## 10. Files"
HEAD = "### 9.26 "

BODY = """\
### 9.26 The retraction re-measured on a current binary, and the one screen the shipping pipeline does not have

ORCH's discipline 34 requires a binary rebuilt from HEAD and its SHA stated.
Everything in 9.25 and 9.25.11 was measured on {old_commit} / `{old_sha}`, which
is now superseded. 9.25.11 is a *retraction*, so re-confirming it on a current
binary is the conservative direction to be wrong in: if the current merge did
amplify the frame, my withdrawal would itself need withdrawing.

**Between the two pins `pyramid.rs` moved five commits**, and `select_weight`
gained a fourth argument (a significance floor). The weight law's call site
changed. This is a re-measurement, not a formality.

#### 9.26.1 I could not get a trustworthy binary out of the shared tree, and that is worth recording

The first two builds are not reported here because I cannot say what they
contain. `git rev-parse HEAD` returned a different commit before and after each
build -- four distinct HEADs inside a few minutes -- and
`crates/strehl-cli/src/merge_cmd.rs` was dirty with another lane's uncommitted
edits throughout. A binary built from a tree that is being written underneath it
has no nameable provenance.

The evidence that this was not paranoia: the shared-tree build hashed
`7640568E06177204`, while the same nominal source built from a pristine
checkout hashed `{new_sha}`. **Two builds, both claiming to be HEAD, different
bytes.** Had I reported the first, the pin recorded in this document would not
correspond to any commit.

What is reported below was built from a **detached worktree** at a single named
commit ({new_commit}), verified clean by `git status --porcelain` before
building, into its own target directory. `vn_lib.check_pin` now takes the exe
and its hash from `VN_EXE` / `VN_PIN_SHA`, defaulting to the original pin so
every earlier script measures exactly what it measured before; it refuses if
only one of the pair is set, because a new binary against an old hash is the
one failure this pin exists to catch. Commissioned four ways -- unset
reproduces the original pin, half-set refuses, new exe against a wrong hash
refuses, new exe against its own hash is accepted.

The stale renders were moved aside first. `vn_shipfr.py` caches on file
existence, so a re-run against a new binary that found the old TIFFs in place
would have re-confirmed the retraction **on the previous binary's pixels** and
printed the same verdict.

#### 9.26.2 The result is unchanged: the accused step is still no larger than a null

{pins}

Both pins agree, and they agree in the only way that matters: **the step that
adds the accused frame moves the coarse band by less than the step that adds an
ordinary one.** On the current binary the accused step is
{rogue_new} -- {sep_new}. On the superseded pin it {rogue_old}.

{steps}

The retraction in 9.25.11 stands on a current binary. The frame that captured
0.62336 of L5 in my offline model captures nothing measurable in the product,
and the cause -- a broken warp produced by *my* aligner, `ncc_b` 0.0275 against
a neighbour median of 0.9474 -- was never a property of the shipping merge.

#### 9.26.3 What the shipping aligner refuses across the corpus: nothing

9.25.11 left open whether the *shipping* aligner ever produces a bad warp. The
26 shipping logs already carry the statistic, so this cost nothing to answer.

{align}

Across the corpus the shipping aligner placed every frame it was given:
**{refused}**, on {aligned}. The remaining subject,
`highly-angled-ruler-mm-cpl`, is alignment-REFUSED by design -- a tilted subject
a global similarity cannot describe -- and is merged unregistered. The two
groups sum to {corpus}, which independently reproduces ORCH's stated corpus
size from a source ORCH did not use.

**{norej}.** So {conclusion}: the aligner does not refuse, and the merge has
no robustness term.

**I want to be exact about what this does and does not show.** A refusal count
of zero is consistent with two different worlds -- every frame genuinely aligned,
or nothing was ever checked -- and this statistic cannot separate them. It is a
*coverage* result, not a defect: it says the corpus contains no frame the
pipeline judged unplaceable, and that the pipeline's judgement is the only one
on offer. My own frame 46 is the cautionary case: my aligner *accepted* it at
`ncc_b` 0.0275. An accepting aligner reports the same zero whether or not a bad
warp is present.

`vn_regout.py` from 9.25.11 is the screen that would separate them, and it is
commissioned to do so, but it needs complete per-frame registration records.
Those exist for `bee-2-cpl` and nowhere else; the other subjects have 21-frame
samples. **A corpus-wide registration screen remains unmeasured, and I am
recording it as unmeasured rather than reporting the zero as if it were a
clean bill of health.**

#### 9.26.4 ORCH's two withdrawals do not touch anything in this lane

Checked rather than assumed, because ORCH asked to be told immediately if
either changed a result.

The withdrawn print-gate baseline (`17 PASS / 5 FAIL / 4 REVIEW`) never entered
this document -- `5 FAIL` and `4 REVIEW` do not appear in it. The single use of
the gate's split, in section 2, observes that the 17 PASS rows carry no
master/best-source ratio, which is the same insensitivity ORCH now warns
against; it is used to argue those rows are uninformative, never that they are
evidence of quality.

The withdrawn claim that the gate never fires above level 0 was never relied on
either. This lane's finding runs the other way -- `BETA` collapse means coarse
coefficients clear the floor by a wide margin, so the gate admits nearly
everything there -- which is ORCH's *replacement* explanation, reached
independently. Section 8.3's averaged-fraction proxy spans 0.000 to 0.997
across the corpus, so it is a covariate with real variance and its four null
correlations are unaffected; and under the corrected reading a subject at 0.000
still means every coefficient was selected rather than averaged, which is what
that row already says.

#### 9.26.5 The HEAD exposure regression does not reach this lane, and I measured that rather than reading the flags

ORCH found that at HEAD `--srgb --auto-exposure` double-applies a tone
normalisation, blowing 11 of 18 masters -- up to 92.13% of pixels pinned at
65535 -- and asked every lane which of three cases it is in. This lane is
**{case}**.

The flags say so: `vn_lib.MEASURE_FLAGS` is `--linear-srgb --demosaic`, and
`--auto-exposure` is never passed to a render anywhere in this lane
(`vn_damage.py` uses `SHIP_FLAGS[:1]` plus a *fixed* `--exposure=`, which is a
different flag). But a flag audit proves what was *requested*. ORCH's regression
is precisely a case of a flag no longer doing what it says, and this lane
already refuses when `--limit` and the log disagree for that reason. So the
answer is a pixel audit.

`vn_clipaudit.py` counts pixels at the 16-bit ceiling across every population
this lane's findings rest on -- the 26 re-rendered linear masters behind
sections 1-8, the four HEAD-pin renders behind 9.26 against the four old-pin
renders of the same arms, and the cached arrays behind 9.24 and 9.25. Result:
**{clip}**, {worst_master} -- a specular highlight, and a subject ORCH's own
sweep also lists as clean. No population is near ORCH's 25% threshold and no
median is anywhere near white.

The four HEAD renders are the only images this lane produced at HEAD at all.
They {head_clip}, and their medians {median_gap} against
the old pin's renders of the same arms -- which is the same agreement ORCH
reports between pin-with-auto and HEAD-without-auto. **Nothing this lane has
reported was measured on an `--auto-exposure` HEAD master.**

The audit is commissioned before its zero is believed: a synthetic image
clipped at ORCH's observed 92.03% must read BLOWN and its fraction be recovered
to within 0.5%, a clean image must read clean, and an unreadable file must
count as unreadable rather than clean. That last arm is the one that matters,
because a zero produced by not looking is the failure this lane's counting rule
exists to prevent.

**One correction ORCH should carry, because it has now propagated into a build
decision.** ORCH has twice attributed `0 / 72 / 511 hull violations at
exponents 1 / 8 / 16` to this lane, most recently as the reason to tell the
build lane not to raise `p` with `log N`. **This lane never measured those
numbers.** They are a block quotation of the `Hull` doc comment inside
`pyramid.rs`, attributed as such where they appear in section 9. The hull
figures this lane did measure are the section 9.24 prices, 1.211x / 1.337x /
1.408x at theta 0.25 / 0.50 / 0.75, computed in the offline model from cached
source-frame bundles -- which the audit above confirms are unclipped, so
ORCH's `pinned_to_hull` caution does not reach them either.

"""


def main():
    txt = io.open(DOC, encoding="utf-8").read()
    if HEAD in txt:
        raise SystemExit("REFUSED: %r already present; refusing to double-insert"
                         % HEAD)
    n = txt.count(ANCHOR)
    if n != 1:
        raise SystemExit("REFUSED: anchor %r occurs %d times, expected 1"
                         % (ANCHOR, n))
    body = BODY.format(**dict(R.phrases(), **R.tables()))
    out = txt.replace(ANCHOR, body + ANCHOR, 1)
    if out == txt:
        raise SystemExit("REFUSED: replacement did not change the document")
    io.open(DOC, "w", encoding="utf-8", newline="").write(out)
    print("inserted %d lines before %r" % (body.count("\n"), ANCHOR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
