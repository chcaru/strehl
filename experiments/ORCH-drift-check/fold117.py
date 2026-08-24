"""Fold ORCH's own provenance check on the CA gain, plus the HEAD baseline.

Facts 1528-1531, disciplines 787-790.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1527 |")
disc_line = full_line(raw, "786. ")

NEW_FACTS = [
    (
        1528,
        "MEASURED",
        "ORCH",
        "**HEAD `f304899` builds clean and is green: 437 tests pass, 0 fail, 1 ignored, "
        "across eight test binaries.** Verified in an **isolated detached worktree** at "
        "`C:\\dev\\strehl-out\\ORCH-headcheck`, release profile, `cargo build "
        "--workspace` exit 0 with no warnings and `cargo test --release --workspace` "
        "exit 0 in 1m52s + test time. This is the baseline every concurrent agent's "
        "work is measured against, taken while **five agents held uncommitted Rust "
        "edits** -- notably M97 with ~294 uncommitted lines in `merge.rs`. A worktree is "
        "used rather than the shared tree precisely so that a green result describes "
        "**HEAD**, not the union of everyone's work in progress.",
    ),
    (
        1529,
        "MEASURED",
        "ORCH",
        "**There is no strength or scale knob on the lateral-CA correction anywhere in "
        "the codebase.** `git grep strength` over all `.rs` at HEAD returns only prose in "
        "doc comments. `STREHL_FIX_CA` selects a **named profile** whose coefficients are "
        "`&'static` constants (`optics.rs:309`); the values `0`, `off`, `false` and the "
        "empty string resolve to `None`, which disables the correction **entirely, "
        "including its resampling step**. **Consequence: the measured over-correction "
        "cannot be tested or shipped by configuration** -- it requires a source change in "
        "`optics.rs`. This is why fact 1519's placebo gap exists and why ORCH could not "
        "run the 0.692 arm without M107.",
    ),
    (
        1530,
        "ARGUED",
        "ORCH",
        "**The 1.444 over-correction is AMBIGUOUS between two hypotheses that demand "
        "opposite fixes, and ORCH drew its conclusion before reading the profile's "
        "provenance.** `optics.rs:309` records `measured_from: \"20 gated ROIs over "
        "tweezers-cpl and bee-3-cpl\"` and `measured_at: None` -- aperture and "
        "magnification at fit time were deliberately not guessed -- while the struct's own "
        "doc states **lateral CA varies with aperture and magnification**. ORCH's gain was "
        "measured on a **different subject**. So: **H1, a coefficient error** (scale "
        "`eps_r` by ~0.69 and every stack improves) versus **H2, an applicability error** "
        "(the coefficient is right for its fit conditions, and scaling it would break the "
        "very stacks it was fitted on). **Nothing measured so far distinguishes them.** "
        "The decisive experiment is to measure the gain **on the fitting stacks "
        "themselves**; dispatched to M114.",
    ),
    (
        1531,
        "ARGUED",
        "ORCH",
        "**H1 is in tension with the fit's own reported quality, which points at the "
        "application path rather than at the fitted number.** The red fit reports "
        "`r_squared = 0.9969`, `permutation_p = 0.0005`, `residual_rms_sensel = 0.073` "
        "over `n_regions = 20`. **A least-squares fit that over-predicts its own training "
        "data by 44 % while reporting a 0.073-sensel residual is close to a "
        "contradiction.** That raises a third possibility ORCH had not considered: **the "
        "coefficient is correct and the code that applies it scales it wrong** -- a "
        "normalised-radius convention, a centre or half-pixel convention, or a "
        "full-resolution-versus-output-resolution factor. This would produce exactly the "
        "observed signature (right radial shape, wrong scale, flat in radius) while "
        "leaving the fit blameless.",
    ),
]

NEW_DISCS = [
    (
        787,
        "**A correction cannot be validated on the data it was fitted to; the residual "
        "nulls by construction.** ORCH came within one command of synthesising a "
        "0.692-scaled correction from the *same* image pair the 1.444 gain was measured "
        "on, and reporting that it nulled the residual. It would have nulled exactly, it "
        "would have looked decisive, and it would have carried **zero** information -- the "
        "scale factor was defined as the thing that makes that residual vanish. **Any "
        "validation of a fitted correction must use data the fit has never seen.**",
    ),
    (
        788,
        "**Read a fitted artifact's provenance BEFORE interpreting any discrepancy "
        "against it.** ORCH measured a 44 % over-correction and concluded 'the "
        "coefficient is wrong' without checking which captures the coefficient was fitted "
        "from or under what conditions. The profile records both fields, and one of them "
        "is explicitly `None` **as information** (fact 1530). **The fitting conditions "
        "decide whether a discrepancy means a wrong number or a correctly-fitted number "
        "applied out of range** -- and those two diagnoses call for opposite code changes, "
        "one of which is a regression.",
    ),
    (
        789,
        "**Locate a discrepancy in the fit or in the application before shipping a "
        "corrective scalar, because a scalar that silently compensates an application bug "
        "will break the moment anyone fixes the bug.** A fitted fudge factor absorbs "
        "whatever is wrong upstream of it and leaves no trace of what that was. When the "
        "reported fit quality is inconsistent with the observed error (fact 1531), the "
        "application path is the first suspect, not the last.",
    ),
    (
        790,
        "**A render log that does not name its input is not reproducible.** M114's "
        "`r1.log` records the arm, the environment value, the exit code, the wall time and "
        "an output hash -- everything except **which stack was rendered**. ORCH could not "
        "recover it from the log, the filenames or the directory, and had to interrupt the "
        "agent to ask. The output hash pins *that* the run is reproducible without "
        "recording *what* it reproduces.",
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
