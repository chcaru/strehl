"""Append section 13 (the exact-zero clip, diagnosed) to the report."""
import io

DOC = "docs/research/BUILD-BLEND.md"
MARK = "13. The exact-zero blue pixels"

NOTE = """
### 13. The exact-zero blue pixels: real defect, already-shipped fix, wrong binary

ORCH measured **723,429 blue pixels at exactly 0 (2.192%)** on
`flower-bud-alone-cpl`, ruled out edge ringing and canvas coverage, rendered the
mask to show the zeros sitting in dark textured shadow on the subject, and
diagnosed a Laplacian reconstruction undershooting where the base band is low.
**That diagnosis is correct in every particular.** It is also a description of
the *unclamped* arm, which stopped being the default on 08-25.

**Their hypothesis about the mechanism, checked and refuted.** They proposed the
reconstruction clamps the accumulated sum, or clamps before the last band is
added. It does not: `pyramid.rs:1284` applies the clamp exactly **once**, after
`collapse()`, to the final image. Per-layer clamping is not happening.

**The A/B.** One binary, one stack, 205 frames, `--linear`, differing only in
`Hull::InputRange` vs `Hull::Unclamped`:

| arm | R == 0 | G == 0 | B == 0 |
|---|---|---|---|
| **clamped (ships)** | **0** | **0** | **0** |
| unclamped | 109,511 | 189,803 | **983,083 (2.979%)** |

The shipping arm has **no exact-zero pixels at all**, in any channel. The
unclamped arm reproduces ORCH's signature: same channel, same order of
magnitude, 2.979% against their 2.192%. **The clamp is the mitigation, not the
cause** -- the exact inverse of the hypothesis.

Neither rail is clipped in the shipping arm: `== 65535` is 0 in R, G and B, and
so is the estimator control, so there is no highlight cost either.

**Why their binary shows it.** ORCH pinned `blend-render.exe` from
`tree-ca-6a51e43`. From git, at that commit:

    enum Hull occurrences    : 0
    Hull::InputRange default : 0
    clamped_fraction present : 0

The `Hull` type **did not exist**. The clamp landed at `275fbd17`, 08-25 23:05
-- **seven hours after** that pin. Their binary cannot clamp because there is
nothing in it to do so. This is the third stale-pin finding in one session, after
the `merge_cmd.rs` grep (section 10) and the +32.1% noise gap (section 12), and
the pattern is now the single largest source of wasted measurement on this
project.

**Two corrections against myself, both from this same investigation.**

1. I reported earlier in this session that the clip "reproduces on my own TIFF"
   because `clip_linear.py` printed `+1.5804 pt CLIPPING IS IN THE MERGE` when I
   passed it my render. **It ignored my argument.** Its summary line reads
   `total compared: 6` -- it globbed ORCH's own `_tiff` directory and reported
   ORCH's data back to me while appearing to answer about my file. An instrument
   that silently ignores argv will confirm whatever you already believed. Check
   that the input count matches the input you supplied.
2. This report's `Hull` documentation says the excursion is rare enough that the
   clamp is nearly inert. It is not.

**The real finding, which is mine and is not fixed.** The per-render diagnostic
reads:

    hull clamp : 8.647% 10.106% 10.105% 10.986%

**The reconstruction puts 8.6-11.0% of output pixels outside the range its own
input frames support.** The clamp catches them, so nothing reaches the file --
but this report's own `clamped_fraction` doc states the interpretation: *"large
means the merge is routinely emitting values no frame observed, which is a
statement about the selection exponent and not about the clamp."* One pixel in
ten is large. The clamp is load-bearing, not a safety net, and a clamp doing
that much work is converting an out-of-hull excursion into a flat spot rather
than into a zero. **ORCH pointed at a real weakness and the pointing stands even
though the measurement was on the wrong binary.** The next work in this lane is
the selection exponent at the coarse bands, not clip handling.

**Also worth re-checking on a current binary:** the C5 gallery result that
flagged `dry-erase-marker-head-cpl` at +2.291 pt and `foam` at +1.020 pt. If
those renders came from the same pin, they are measuring an arm with no clamp.
"""

src = io.open(DOC, encoding="utf-8").read()
if MARK in src:
    raise SystemExit("section already present -- refusing to duplicate")
io.open(DOC, "w", encoding="utf-8", newline="").write(src.rstrip("\n") + "\n" + NOTE)
print("appended section 13;", len(io.open(DOC, encoding="utf-8").read().splitlines()), "lines")
