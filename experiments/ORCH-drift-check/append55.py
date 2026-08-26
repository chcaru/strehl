"""Append section 55 to ORCH-veiling.md. One-shot; idempotent by anchor check."""
import sys
from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "research" / "ORCH-veiling.md"

ANCHOR = "## 55. A night of corrections, and one of them is a habit"

SECTION = """

## 55. A night of corrections, and one of them is a habit rather than a fact

Four of my own records were corrected tonight by agents I had sent to check
them. Three are simple errata. The fourth is a reasoning error I want named,
because I will otherwise make it again.

### 55.1 The CA census is correctly signed -- confirmed, not merely assumed

The open worry was that section 46's "25 improved, 0 worsened, 1 no-op" might
have been labelled from the status line that was later found to be lying, in
which case the whole gallery would carry the correction **backwards**.

**It does not.** `GALLERY-FINAL` is CA **off**, `SHIP-V1` is CA **on**, and the
verdict stands. Proven three independent ways: the published numbers match in
direction; the radial physics is right (edge R-G rises **4.2x** from centre to
corner in the off arm and is flat in the on arm, which is what lateral CA does
and what a mislabelled pair could not fake); and a ground-truth control using
`--fix-ca off` against a named profile matches to 3-4 significant figures at
every radius. `cacensus.py` parses **no log line at all**, so the lying status
line could not have reached it, and section 46's arms came from `strehl stack`
rather than from the harness that carried the defect.

Worth recording that the verifier's own first run reported "0/3 plants caught",
which it then traced to `--exact` selecting **zero tests** -- `0 passed` reading
as success. **A vacuous green inside the instrument built to detect vacuous
greens.** It caught it because it checked how many tests ran, not just whether
any failed.

### 55.2 The aperture census I recorded was wrong, and wrong in the direction that costs the owner a shoot

I recorded **5x f/5.6, 1x f/8, no f/11**. A full EXIF census of the corpus finds
**20x f/5.6, 3x f/8, 3x f/11** -- and the f/11 material exists in
`109MSDCF`, `112MSDCF` and `113MSDCF`. My count was right for the six stacks I
happened to look at and wrong as a statement about the corpus, which is what I
wrote it as.

The consequence was nearly a wasted session for the owner: I had priced the f/11
point as a capture request. `docs/captures-needed.md` had **already** self-
corrected this in its own errata -- *"no aperture variation in the corpus" should
have read "none among the CPL stacks"* -- and section 7's aperture-pair request
survives the correction intact, because it asks for something genuinely absent:
a **paired** shoot at matched depth and density. M35 measured that both existing
candidates fail the self-reference gate (`119MSDCF` 2.18x, `112MSDCF` 2.10x,
against `coffee-bean`'s 3.62x), so the request is about **density**, not about
apertures the corpus lacks. **The request was right for a reason I had stated
wrongly.**

### 55.3 A units error that strengthened the argument it was found in

Section 50 priced a chroma residual at **0.1199 px**. The figure is
**0.1731 px**: `caprice.py` returns `1.4826 x MAD`, an *amplitude*, and the
corpus text at line 3782 says "HF amplitude" -- I converted as though it were a
variance-like quantity. The corrected number sits **further** inside the
radially-varying field it needed to fit within, so the conclusion is better
supported than when I wrote it.

### 55.4 The habit: I called a definition a convergence

This is the one that matters beyond tonight.

Section 50 reported, as independent corroboration, that one agent's green figure
of 0.69 times another's 0.6813 gives **0.470**, matching a third measurement of
R/B at 0.47. I presented the agreement of two lanes as evidence the number was
right.

**It is not evidence of anything.** Both quantities derive from the *same
kernel* evaluated at the *same frequency*. "R/B equals green times the co-site
factor" is how those terms are defined; the arithmetic could not have come out
any other way, and no possible measurement could have made it come out
differently. A prediction that cannot fail is not a test, and two lanes agreeing
because they share an input are not two lanes.

> **Before citing an agreement as corroboration, ask what result would have
> counted as disagreement.** If no measurement could have produced one, the
> agreement is a restatement of a definition and carries no evidential weight.

The reason this is a habit and not a slip: an unfalsifiable agreement *feels*
exactly like a strong one, and it arrives with the emotional signature of
independent confirmation -- which is precisely when a claim stops being
examined. I logged it under the same heading as genuine cross-lane convergence,
and nothing in my own record distinguished the two.

### 55.5 One capability confirmed live, by artefact rather than by argument

Against the run of the night, a positive result. The `Hull::InputRange` clamp is
**genuinely applied on the delivered gallery.** Counting exact-zero RGB pixels
in the shipped masters -- a quantity that survives any monotone tone curve and
so needs no cross-path comparison:

| subject | zero RGB px | `lum<500` | unclamped expectation |
| --- | ---: | ---: | --- |
| `flower-bud-alone-cpl` | **0** | 0.009% | 122,416 px / 0.371%, `lum<500` 1.310% |
| `dry-erase-marker-head-cpl` | **0** | 0.000% | 1.048% |
| `bee-3-cpl` | 0 | 0.003% | -- |
| `coffee-bean` | 0 | 0.000% | -- |

I checked this specifically **because** section 54 had just found a documented,
tested, defaulted-looking capability that does not run. `Hull::InputRange` has
the same profile -- an excellent doc comment, a passing potency control, and the
word "default" -- and after `restore.rs` that profile no longer constitutes
evidence. It happens to be true here, and now it is true *measured on the
artefact* rather than inferred from an enum.

**Instrument note:** the cheapness of this test is the point. Exact zero is
preserved by every monotone tone curve, so it is one of the very few quantities
that can be read straight off a `--srgb` master without violating the rule
against measuring across a tone curve. When a defect has a signature that
survives the transformations between instrument and product, the path boundary
stops mattering -- **look for such signatures first.**

### 55.6 An open packaging question

The masters are not all the same size. `flower-bud-alone-cpl` and
`dry-erase-marker-head-cpl` are `(4688, 7040, 3)`; `bee-3-cpl` and `coffee-bean`
are `(4688, 7032, 3)` -- same height, 8 px apart in width. Presumably a
per-subject crop falling out of the alignment solve. Not a quality defect, but a
gallery whose members have different pixel dimensions is a wart for anyone
printing a set, and if the variation tracks alignment drift it is a free
diagnostic. Routed to triage rather than answered here.
"""


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    if ANCHOR in text:
        print("already present; no change")
        return 0
    if not text.endswith("\n"):
        text += "\n"
    DOC.write_text(text + SECTION.lstrip("\n"), encoding="utf-8")
    print(f"appended; file now {len(DOC.read_text(encoding='utf-8'))} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
