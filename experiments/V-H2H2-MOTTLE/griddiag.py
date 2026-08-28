"""V-H2H2: what resolution does the merge actually DECIDE on, and is it forced?

ORCH asked three things about the 3516x2344 decision grid: (a) confirm it and
say FORCED or INCIDENTAL, (b) state the cost in cyc/output px and whether the
finest output octave is selected on interpolated evidence, (c) do not rewrite
the merge.

This script is the evidence for (a) and (b). Every claim below is pinned to a
verbatim line of source. If an anchor does not land the script RAISES rather
than printing a cheerful answer from a stale premise -- a claim whose anchor has
silently moved is the failure mode this campaign has paid the most for.

Nothing here modifies anything. It reads source and does arithmetic.
"""

import os
import re
import sys
from pathlib import Path

# Defaults to the real tree. The override exists so the conclusion-reversal
# audit can run this script through its SHIPPED ENTRY POINT against a COPY of
# the sources: this working tree is shared by ~12 lanes and briefly sabotaging
# merge_cmd.rs to test my own verifier would corrupt whatever they are building.
ROOT = Path(os.environ.get("STREHL_GRIDDIAG_ROOT",
                           r"C:\dev\blog\death-of-software\projects\strehl"))
MERGE = ROOT / "crates/strehl-cli/src/merge_cmd.rs"
ALIGN = ROOT / "crates/strehl-cli/src/align_cmd.rs"
PYR = ROOT / "crates/strehl-core/src/pyramid.rs"

# MEASURED, not assumed: from a real render banner at binary B2EC8293,
# `stack D:\personal\macro\coffee-bean --merge pyramid -l 2 --srgb`.
OUT_W, OUT_H = 7032, 4688
COARSEST_W, COARSEST_H = 28, 19
BANDS = 7


def anchor(path: Path, needle: str, label: str) -> int:
    """Return the 1-based line number of `needle`, or raise. Never guesses."""
    text = path.read_text(encoding="utf-8", errors="replace")
    idx = text.find(needle)
    if idx < 0:
        raise AssertionError(
            f"ANCHOR NOT FOUND [{label}] in {path.name}:\n    {needle!r}\n"
            "The source has moved. This script's conclusion is VOID until the "
            "anchor is re-established -- do not read the verdict below."
        )
    if text.find(needle, idx + 1) >= 0:
        raise AssertionError(
            f"ANCHOR NOT UNIQUE [{label}] in {path.name}: {needle!r}. "
            "Pin it to a longer string; a non-unique anchor cannot attribute."
        )
    return text.count("\n", 0, idx) + 1


print("=" * 72)
print("ANCHORS -- every claim below is pinned to one of these")
print("=" * 72)

checks = [
    # Anchored with its newline and exact indent. The bare expression is NOT
    # unique: `merged_luma[i] = 0.5 * ...` at :5701 contains it as a substring,
    # and the uniqueness guard caught that on the first run.
    (MERGE, "\n        luma[i] = 0.5 * (planes[1][i] + planes[2][i]);\n",
     "decision variable is (G1+G2)/2, ONE sample per quad"),
    (MERGE, "const BAND_PLANES: usize = 4;",
     "merge folds 4 CFA planes"),
    (MERGE, "/// [`MergeBackend::Pyramid`] output: four collapsed planes in",
     "pyramid output is on the quad grid"),
    (MERGE, "decision per quad. Interpolated -- do not measure resolution on it.",
     "the tool's OWN banner admits one focus decision per quad"),
    (PYR, "/// made on green luma only",
     "selection is green-luma only, shared by all planes"),
    (ALIGN, "    // 2. Demosaic to three full-resolution channel planes.",
     "a FULL-RESOLUTION demosaic already exists per frame"),
    (ALIGN, "    drop(mos);",
     "the full-res mosaic is dropped inside the warp"),
]
for path, needle, label in checks:
    ln = anchor(path, needle, label)
    print(f"  {path.name}:{ln:<6} {label}")

# The full-res planes are function-locals of `warp_frame_in_place_fullres`, so
# they die at its end. Confirm they are locals and never returned.
atext = ALIGN.read_text(encoding="utf-8", errors="replace")
for name in ("rp", "gp", "bp"):
    if f"let mut {name} = vec![0f32; fw * fh];" not in atext:
        raise AssertionError(f"full-res plane `{name}` is no longer a local -- claim VOID")

# The declarations alone do NOT establish the claim. A function may declare a
# local and still hand it back; `let mut rp = vec![...]` would sit there
# unchanged while the planes escaped. What forbids escape is the RETURN TYPE:
# the function yields a scalar, so no plane can leave through it. Until this
# check existed the conclusion was true but untested -- green by luck.
sig = re.search(r"pub fn warp_frame_in_place_fullres\((?:[^)]*)\)\s*->\s*([^\{]+)\{",
                atext, re.S)
if not sig:
    raise AssertionError("warp_frame_in_place_fullres signature not found -- claim VOID")
ret = sig.group(1).strip()
if ret != "Result<f64>":
    raise AssertionError(
        f"warp_frame_in_place_fullres now returns `{ret}`, not `Result<f64>`. "
        "A non-scalar return can carry the full-res planes out of the function, "
        "so 'built, sampled, dropped' is VOID until re-established.")
print(f"  align_cmd.rs        rp/gp/bp are function-locals; return type is "
      f"`{ret}`, a scalar, so no plane can escape")

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("GEOMETRY -- measured from the render banner, checked for consistency")
print("=" * 72)

quad_w, quad_h = OUT_W // 2, OUT_H // 2
print(f"  output                 : {OUT_W} x {OUT_H} px")
print(f"  merge / decision grid  : {quad_w} x {quad_h} quads  (pitch = 2 output px)")

# Self-check: the banner's coarsest level must follow from the quad grid.
w, h = quad_w, quad_h
for _ in range(BANDS):
    w, h = (w + 1) // 2, (h + 1) // 2
if (w, h) != (COARSEST_W, COARSEST_H):
    raise AssertionError(
        f"coarsest level from a {quad_w}x{quad_h} base is {w}x{h}, but the banner "
        f"printed {COARSEST_W}x{COARSEST_H}. The merge base is NOT the quad grid; "
        "the whole analysis is void."
    )
print(f"  {BANDS} halvings of the quad grid -> {w} x {h}, and the banner printed "
      f"{COARSEST_W} x {COARSEST_H}  [CONSISTENT]")

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("THE COST, in cycles per OUTPUT pixel")
print("=" * 72)

out_nyq = 0.5
dec_nyq = 0.5 / 2.0  # decision lattice pitch is 2 output px
print(f"  output Nyquist                  : {out_nyq:.3f} cyc/output px")
print(f"  decision-lattice Nyquist        : {dec_nyq:.3f} cyc/output px")
print(f"  finest merge band (level 0)     : {dec_nyq / 2:.3f} - {dec_nyq:.3f} cyc/output px")
print()
print(f"  UNDECIDED OCTAVE                : {dec_nyq:.3f} - {out_nyq:.3f} cyc/output px")
frac = (out_nyq - dec_nyq) / out_nyq
print(f"    -> {frac * 100:.0f}% of the output's linear frequency range, and the")
print("       ENTIRE finest octave, has no merge coefficient of any kind.")

print()
print("  What the GREEN sites alone could have supported:")
print("    G1 at (1,0) and G2 at (0,1) in a quad = a quincunx lattice, x+y odd.")
print("    Its representable set is |fx| + |fy| <= 0.5 cyc/output px, so green")
print("    reaches 0.500 cyc/output px along the horizontal and vertical axes")
print("    -- the FULL output Nyquist -- and 0.250 along the diagonal.")
print("    merge_cmd.rs averages G1 and G2 into one per-quad sample BEFORE the")
print("    decision, which is a 2-tap low-pass along the diagonal followed by")
print("    decimation to quad pitch. That discards evidence the sensor supplied.")

print()
print("=" * 72)
print("VERDICT")
print("=" * 72)
print("""  INCIDENTAL, not forced -- but the two halves must be separated:

  1. THE EVIDENCE is band-limited incidentally. Three independent reasons:
     - a full-resolution demosaic (rp/gp/bp, 7032x4688) is ALREADY built per
       frame inside warp_frame_in_place_fullres and then dropped, so full-res
       green exists in the pipeline at the moment of the warp;
     - the green quincunx alone reaches 0.5 cyc/output px on the axes and is
       averaged away at merge_cmd.rs by a deliberate 2-tap mean;
     - the stated reason for luma-only selection is that CHROMA noise must not
       drive the decision. That argues for using GREEN. It does not argue for
       using green at HALF RESOLUTION. Those are independent choices.

  2. THE APPLICATION GRANULARITY -- one winner per quad -- is closer to forced.
     Letting the four CFA sites of a quad come from different frames is exactly
     the chroma-speckle failure the shared-luma rule exists to prevent, and
     pyramid.rs has a test asserting the planes share one selection.

  So the cheap, safe change is NOT 'decide at full resolution'. It is: compute
  the focus evidence on the finer green lattice, then pool to the quad and keep
  applying ONE decision per quad. That is strictly more evidence at zero
  coherence risk. Whether it helps is an open measurement, not a claim.""")

print()
print("  (c) Is the finest output octave selected on INTERPOLATED evidence?")
print("      No -- it is not selected AT ALL. There is no decision variable")
print("      above 0.25 cyc/output px. Its content is carried passively from")
print("      whichever frame won the quad on evidence band-limited to <=0.25,")
print("      and with the full-res gather on, those values are demosaic")
print("      interpolations. The finest output octave is therefore interpolated")
print("      content that no selection decision ever examined.")
